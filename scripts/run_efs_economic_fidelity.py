#!/usr/bin/env python3
"""Fresh EFS-v1 daily LLM evolution with explicit economic-fidelity boundaries."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from alpha_evolve.economic_fidelity import Factor, daily_account, monthly_compound, normalize, seed_factors, top_weights
from alpha_evolve.openrouter_budget import MeteredOpenRouter, atomic_json, read_key, sha256

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'artifacts/economic_fidelity/v1'
OUT = ROOT / 'paper_runs/economic_fidelity/efs_v1'
SOURCE = Path('/nfs/roberts/scratch/pi_btk22/zc362/efs_paper_audit/source_v1/sections')


def extract_system_prompt(text: str) -> str:
    start = text.index('You are a \\textcolor{promptkey}')
    end = text.index('\\end{tcolorbox}', start)
    text = text[start:end]
    text = re.sub(r'\\textcolor\{[^{}]*\}\{([^{}]*)\}', r'\1', text)
    text = re.sub(r'\\texttt\{([^{}]*)\}', r'\1', text)
    text = re.sub(r'\\hspace\{[^{}]*\}', '', text)
    text = text.replace('\\textbackslash n', r'\n').replace('\\_', '_').replace('\\\\', '\n')
    return text.strip()


def parse_proposals(content: str) -> list[str]:
    content = content.strip()
    if content.startswith('```') and content.endswith('```'):
        content = content.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    value = ast.literal_eval(content)
    if not isinstance(value, list) or not 1 <= len(value) <= 6 or not all(isinstance(code, str) for code in value):
        raise ValueError('expected a list of 1-6 Python function strings')
    return value


def user_prompt(seeds, generated, stats) -> str:
    library = '\n\n'.join(f.code for f in seeds)
    proposals = '\n\n'.join(f.code for f in generated)
    clean_stats = [{k: (round(v, 8) if isinstance(v, float) else v) for k, v in row.items()} for row in stats]
    return ('You are a professional quantitative researcher.\n'
        'Design and optimize alpha factors using ONLY price data.\n\n'
        'Existing Library Factors:\n' + library + '\n\n'
        'Previous LLM-Generated Factors:\n' + proposals + '\n\n'
        'Recent Performance Metrics:\n' + json.dumps(clean_stats, sort_keys=True) + '\n\n'
        'Generate three evolved factors. Each prices input is a one-dimensional array of 30 completed daily normalized closes. '
        'Use the required (prices, window) signature, and only NumPy numerical operations; np is already supplied. '
        'Do not import modules. The permitted windows are 3, 7, 14, and 21. Return only the Python list of function strings.')


class ResearchEngine:
    def __init__(self, prices, dates, tickers, recipe):
        self.prices, self.dates, self.tickers, self.recipe = prices, dates, tickers, recipe
        self.m = recipe.get('feedback_portfolio_assets', recipe['portfolio_assets'])
        self.price_returns = np.full_like(prices, np.nan)
        self.price_returns[1:] = prices[1:] / prices[:-1] - 1
        self.score_cache = {}
        self.daily_metric_cache = {}

    def scores(self, factor, index):
        key = (factor.sha256, index)
        if key not in self.score_cache:
            history = self.prices[index-29:index+1]
            raw = factor.score(history)
            eligible = np.isfinite(history).all(axis=0) & (history > 0).all(axis=0)
            if not np.isfinite(raw[eligible]).all():
                raise ValueError('nonfinite factor on eligible price history')
            self.score_cache[key] = normalize(raw)
        return self.score_cache[key]

    def performance(self, factor, decision_index):
        # Last usable formation is decision_index-2: execute next close, earn the following close return.
        indexes = range(max(29, decision_index-self.recipe['feedback_days']-1), decision_index-1)
        payoffs, baseline, ics, recalls = [], [], [], []
        for j in indexes:
            key = (factor.sha256, j)
            if key not in self.daily_metric_cache:
                scores = self.scores(factor, j)
                mask = np.isfinite(scores)
                if mask.sum() < self.m:
                    continue
                w = top_weights(scores, self.m)
                realized = self.price_returns[j+2]
                if not np.isfinite(realized[w>0]).all():
                    raise ValueError('historical selected return missing')
                payoff = float(np.sum(w[w>0]*realized[w>0]))
                if not np.isfinite(realized[mask]).all():
                    raise ValueError('historical benchmark return missing')
                baseline_return = float(realized[mask].mean())
                x, y = rankdata(scores[mask]), rankdata(realized[mask])
                x, y = x-x.mean(), y-y.mean()
                denom = np.linalg.norm(x)*np.linalg.norm(y)
                ic = float(x@y/denom) if denom > 1e-12 else 0.0
                recall_m = self.recipe.get('recall_assets', self.m)
                predicted = top_weights(scores, recall_m)
                actual = top_weights(np.where(mask, realized, np.nan), recall_m)
                recall = float(np.sum((predicted>0)&(actual>0))/recall_m)
                self.daily_metric_cache[key] = (payoff, baseline_return, ic, recall)
            payoff, baseline_return, ic, recall = self.daily_metric_cache[key]
            payoffs.append(payoff)
            baseline.append(baseline_return)
            ics.append(ic)
            recalls.append(recall)
        if len(payoffs) < 20:
            raise ValueError('insufficient completed feedback outcomes')
        r = np.asarray(payoffs)
        wealth = np.cumprod(1+r)
        return {'factor': factor.name, 'sha256': factor.sha256,
            'mean_return': float(r.mean()), 'std_return': float(r.std()),
            'sharpe_ratio': float(r.mean()/(r.std()+1e-8)),
            'max_drawdown': float(np.min(wealth/np.maximum.accumulate(np.r_[1., wealth])[1:]-1)),
            'final_value': float(wealth[-1]), 'mean_rankic': float(np.mean(ics)),
            'std_rankic': float(np.std(ics)), 'mean_recall_at_'+str(self.recipe.get('recall_assets', self.m)): float(np.mean(recalls)),
            'std_recall_at_'+str(self.recipe.get('recall_assets', self.m)): float(np.std(recalls)),
            'benchmark_mean_return': float(np.mean(baseline)), 'feedback_observations': len(r)}


def rank_pool(pool, stats):
    ranked = sorted(pool, key=lambda key: (-stats[key]['mean_rankic'], -stats[key]['sharpe_ratio'], pool[key].name, key))
    # Preserve both the latest and best versions within each conceptual factor family.
    keep = set()
    for base in {f.base for f in pool.values()}:
        family = [key for key in ranked if pool[key].base == base]
        keep.add(family[0])
        keep.add(max(family, key=lambda key: (pool[key].version, pool[key].created_index)))
    return [key for key in ranked if key in keep]


def run(args):
    recipe = json.loads((OUT/'recipe.json').read_text())
    locked_recipe_hash = sha256(OUT/'recipe.json')
    data_manifest = json.loads((PRIVATE/'data_manifest.json').read_text())
    if sha256(PRIVATE/'efs_us50_daily.parquet') != data_manifest['daily_extract_sha256']:
        raise ValueError('daily input changed')
    if sha256(PRIVATE/'data_manifest.json') != recipe['data_manifest_sha256']:
        raise ValueError('data manifest changed after recipe freeze')
    if sha256(Path(__file__)) != recipe['implementation_sha256']['scripts/run_efs_economic_fidelity.py']:
        raise ValueError('runner changed after recipe freeze')
    for name, expected in recipe['implementation_sha256'].items():
        if sha256(ROOT/name) != expected:
            raise ValueError('implementation changed after recipe freeze: '+name)
    frame = pd.read_parquet(PRIVATE/'efs_us50_daily.parquet')
    tickers = sorted(frame.ticker.unique())
    prices_df = frame.pivot(index='date', columns='ticker', values='adjusted_close').reindex(columns=tickers).sort_index()
    dates = pd.DatetimeIndex(prices_df.index)
    prices = prices_df.to_numpy(float)
    # Scale from each stock's first observed price; no backward fill of IPOs.
    first = np.array([col[np.flatnonzero(np.isfinite(col)&(col>0))[0]] for col in prices.T])
    prices = prices / first * 100
    returns = frame.pivot(index='date', columns='ticker', values='ret').reindex(index=dates, columns=tickers).to_numpy(float)
    execution = np.flatnonzero((dates >= recipe['start']) & (dates <= recipe['end']))
    engine = ResearchEngine(prices, dates, tickers, recipe)
    client = None
    if args.mode == 'llm':
        client = MeteredOpenRouter(ROOT/'runs/economic_fidelity/openrouter', read_key(args.key_env_file),
            recipe['model'], study='efs_v1_daily', study_cap=recipe['api_cap_usd'])
        for name in recipe['historical_usage_journals']:
            client.import_usage(ROOT/name)
    seeds = seed_factors()
    pool = {f.sha256: f for f in seeds}
    all_factors = dict(pool)
    proposals, trace, selections = [], [], []
    targets = np.zeros((len(execution), len(tickers)))
    stats = {}
    accepted_total = calls = 0
    for row, execution_index in enumerate(execution):
        decision_index = execution_index-1
        if decision_index < 29:
            raise ValueError('missing prehistory')
        if row < recipe['warmup_days']:
            eligible = np.isfinite(prices[decision_index-29:decision_index+1]).all(axis=0)
            targets[row, eligible] = 1/eligible.sum()
            chosen = []
        else:
            stats = {key: engine.performance(factor, decision_index) for key, factor in pool.items()}
            ranked = rank_pool(pool, stats)
            pool = {key: pool[key] for key in ranked[:recipe['pool_max']]}
            if (row-recipe['warmup_days']) % recipe['search_interval_days'] == 0 and args.mode == 'llm':
                top = ranked[:recipe['prompt_factors']]
                message = user_prompt([pool[k] for k in top if pool[k].origin=='paper_seed_family'],
                    [pool[k] for k in top if pool[k].origin!='paper_seed_family'], [stats[k] for k in top])
                response, request_hash = client.complete([
                    {'role':'system','content': (OUT/'system_prompt.txt').read_text()},
                    {'role':'user','content': message}], max_tokens=recipe['max_output_tokens'], temperature=recipe['temperature'])
                calls += 1
                raw = response['choices'][0]['message'].get('content') or ''
                round_record = {'round':calls,'decision_date':str(dates[decision_index].date()),
                    'feedback_last_realization':str(dates[decision_index].date()),
                    'execution_date':str(dates[execution_index].date()), 'request_hash':request_hash,
                    'response_id':response.get('id'),'response_model':response.get('model'),'accepted':0,'rejected':0}
                try:
                    codes = parse_proposals(raw)
                except (ValueError, SyntaxError) as exc:
                    codes = []
                    proposals.append({'round':calls,'status':'invalid_response','reason':str(exc),'request_hash':request_hash})
                    round_record['rejected'] += 1
                for code in codes:
                    record = {'round':calls,'request_hash':request_hash,'code':code}
                    try:
                        factor = Factor(code, 'llm_generated', decision_index)
                        if factor.sha256 in all_factors:
                            raise ValueError('duplicate source code')
                        metrics = engine.performance(factor, decision_index)
                        record.update(name=factor.name, sha256=factor.sha256, validation=metrics)
                        # The paper requires new factors to exceed a benchmark; this training-only threshold is disclosed.
                        if metrics['mean_return'] <= metrics['benchmark_mean_return'] or metrics['mean_rankic'] <= 0:
                            raise ValueError('does not exceed training-only equal-universe return and positive RankIC')
                        pool[factor.sha256] = factor
                        all_factors[factor.sha256] = factor
                        stats[factor.sha256] = metrics
                        record['status'] = 'accepted'
                        accepted_total += 1
                        round_record['accepted'] += 1
                    except Exception as exc:
                        record.update(status='rejected', reason=type(exc).__name__+': '+str(exc)[:250])
                        round_record['rejected'] += 1
                    proposals.append(record)
                trace.append(round_record)
                atomic_json(PRIVATE/'progress.json', {'mode':args.mode, 'round':calls,
                    'date':str(dates[decision_index].date()),'accepted_functions':accepted_total,'budget':client.snapshot()})
                atomic_json(PRIVATE/'proposals_live.json', proposals)
                print(json.dumps({'round':calls,'decision':str(dates[decision_index].date()),'accepted':accepted_total,'calls':client.snapshot()['complete_calls']}),flush=True)
            ranked = rank_pool(pool, stats)
            chosen = ranked[:recipe['selected_factors']]
            score_matrix = np.stack([engine.scores(pool[key], decision_index) for key in chosen])
            common = np.isfinite(score_matrix).all(axis=0)
            composite = np.full(len(tickers), np.nan)
            composite[common] = score_matrix[:, common].mean(axis=0)
            targets[row] = top_weights(composite, recipe['portfolio_assets'])
        if not np.isfinite(prices[execution_index, targets[row]>0]).all():
            raise ValueError('selected execution price unavailable; no substitution permitted')
        selections.append({'signal_date':str(dates[decision_index].date()),
            'execution_date':str(dates[execution_index].date()),
            'selected_factor_hashes':'|'.join(chosen), 'selected_llm_factors':sum(pool[k].origin=='llm_generated' for k in chosen),
            'selected_assets':int((targets[row]>0).sum())})
    if args.mode=='llm' and accepted_total==0:
        raise ValueError('no LLM factors accepted; economic mechanism not established')
    if sha256(OUT/'recipe.json') != locked_recipe_hash:
        raise ValueError('recipe changed during run')
    prefix = args.mode
    daily = pd.DataFrame({'date':dates[execution]})
    summaries = []
    monthly = None
    for label, r in [('price', engine.price_returns[execution]), ('total', returns[execution])]:
        for cost in (0,10):
            values, turn, fees = daily_account(targets, r, cost)
            key = f'{label}_cost_{cost}'
            daily[key] = values
            daily[key+'_traded_notional'] = turn
            daily[key+'_fee_drag'] = fees
            m = monthly_compound(dates[execution], values)
            if monthly is None:
                monthly = pd.DataFrame({'month':m.index.to_timestamp('M')})
            monthly[key] = m.to_numpy()
            wealth = np.cumprod(1+values)
            summaries.append({'case':key, 'days':len(values), 'months':len(m),
                'cagr':float(wealth[-1]**(252/len(values))-1),
                'sharpe_zero_rf':float(values.mean()/values.std(ddof=1)*np.sqrt(252)),
                'max_drawdown':float(np.min(wealth/np.maximum.accumulate(np.r_[1.,wealth])[1:]-1)),
                'ending_wealth':float(wealth[-1]),'mean_one_way_traded_notional':float(turn.mean())})
    daily.to_csv(OUT/f'{prefix}_daily_returns.csv',index=False)
    monthly.to_csv(OUT/f'{prefix}_monthly_returns.csv',index=False)
    pd.DataFrame(summaries).to_csv(OUT/f'{prefix}_metrics.csv',index=False)
    pd.DataFrame(selections).to_csv(OUT/f'{prefix}_decisions.csv',index=False)
    pd.DataFrame(targets,index=dates[execution],columns=tickers).to_parquet(PRIVATE/f'{prefix}_daily_weights.parquet')
    atomic_json(OUT/f'{prefix}_factor_library.json', {k:{'name':f.name,'code':f.code,'origin':f.origin,'created_index':f.created_index} for k,f in all_factors.items()})
    atomic_json(OUT/f'{prefix}_proposals.json',proposals)
    atomic_json(OUT/f'{prefix}_llm_trace.json',trace)
    outputs = [p for p in OUT.glob(prefix+'_*') if p.is_file() and p.name!=prefix+'_manifest.json']
    manifest = {'status':'complete','implementation_type':'paper_guided_native_cadence_reimplementation',
        'mode':prefix,'recipe_sha256':locked_recipe_hash,'completed_utc':datetime.now(timezone.utc).isoformat(),
        'full_original_paper_reproduced':False,'independent_human_review_complete':False,
        'confirmatory_result':False,'tickers':len(tickers),'days':len(execution),'months':len(monthly),
        'llm_calls':calls,'accepted_llm_functions':accepted_total,
        'days_using_llm_factors':sum(r['selected_llm_factors']>0 for r in selections),
        'source_daily_extract_sha256':data_manifest['daily_extract_sha256'],
        'private_weights_path':str(PRIVATE/f'{prefix}_daily_weights.parquet'),
        'private_weights_sha256':sha256(PRIVATE/f'{prefix}_daily_weights.parquet'),
        'output_sha256':{p.name:sha256(p) for p in outputs},
        'budget':client.snapshot() if client else None,'python':sys.version.split()[0]}
    atomic_json(OUT/f'{prefix}_manifest.json',manifest)
    print(json.dumps(manifest,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['initial','llm'],required=True)
    parser.add_argument('--key-env-file',type=Path,default=ROOT.parent/'KnowledgeTemplate/.env')
    run(parser.parse_args())
