#!/usr/bin/env python3
"""Independent daily-account reconstruction and provenance checks for EFS repair."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from alpha_evolve.openrouter_budget import atomic_json, sha256

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper_runs/economic_fidelity/efs_v1'
PRIVATE = ROOT / 'artifacts/economic_fidelity/v1'


def independent_account(weights, asset_returns, fee):
    """Recompute dollars using a bracketed fee-equation solve, independently of runner."""
    positions = np.zeros(weights.shape[1])
    previous_value = 1.0
    cash = 1.0
    result = []
    for target, realized in zip(weights, asset_returns):
        held = positions > 1e-14
        if not np.isfinite(realized[held]).all():
            raise ValueError('missing held return')
        marked = positions.copy()
        marked[held] *= 1 + realized[held]
        before_cost = cash + marked.sum()
        def equation(after_cost):
            return after_cost + fee * np.abs(after_cost * target - marked).sum() - before_cost
        after_cost = brentq(equation, 0, before_cost, xtol=1e-14)
        positions = after_cost * target
        result.append(after_cost / previous_value - 1)
        cash, previous_value = 0.0, after_cost
    return np.array(result)


def validate(mode):
    manifest_path = OUT / f'{mode}_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    recipe = json.loads((OUT/'recipe.json').read_text())
    if manifest['status'] != 'complete' or manifest['full_original_paper_reproduced'] or manifest['confirmatory_result']:
        raise ValueError('invalid completion or claim boundary')
    if manifest['recipe_sha256'] != sha256(OUT/'recipe.json'):
        raise ValueError('recipe hash mismatch')
    for name, expected in recipe['implementation_sha256'].items():
        if sha256(ROOT/name) != expected:
            raise ValueError('implementation changed: '+name)
    for name, expected in manifest['output_sha256'].items():
        if sha256(OUT/name) != expected:
            raise ValueError('output changed: '+name)
    if sha256(OUT/'system_prompt.txt') != recipe['system_prompt_sha256']:
        raise ValueError('source prompt changed')
    if sha256(PRIVATE/'data_manifest.json') != recipe['data_manifest_sha256']:
        raise ValueError('daily data manifest changed')
    if sha256(PRIVATE/'efs_us50_daily.parquet') != manifest['source_daily_extract_sha256']:
        raise ValueError('daily panel changed')
    weights_path = Path(manifest['private_weights_path'])
    if sha256(weights_path) != manifest['private_weights_sha256']:
        raise ValueError('private holdings changed')
    weights = pd.read_parquet(weights_path)
    frame = pd.read_parquet(PRIVATE/'efs_us50_daily.parquet')
    prices = frame.pivot(index='date',columns='ticker',values='adjusted_close').reindex(columns=weights.columns).sort_index()
    total = frame.pivot(index='date',columns='ticker',values='ret').reindex(index=weights.index,columns=weights.columns)
    price_returns = prices / prices.shift(1) - 1
    daily = pd.read_csv(OUT/f'{mode}_daily_returns.csv',parse_dates=['date']).set_index('date')
    monthly = pd.read_csv(OUT/f'{mode}_monthly_returns.csv',parse_dates=['month']).set_index('month')
    if not weights.index.equals(daily.index) or weights.shape[1] != 50:
        raise ValueError('calendar/universe mismatch')
    if not np.allclose(weights.sum(axis=1),1) or (weights.to_numpy()<0).any():
        raise ValueError('invalid long-only weights')
    errors = {}
    for label, returns in [('price',price_returns.reindex(weights.index)),('total',total)]:
        for cost in (0,10):
            key = f'{label}_cost_{cost}'
            independent = independent_account(weights.to_numpy(),returns.to_numpy(),cost/10000)
            error = float(np.max(np.abs(independent-daily[key].to_numpy())))
            if error > 1e-11:
                raise ValueError('independent account mismatch '+key)
            composed = (1+daily[key]).groupby(daily.index.to_period('M')).prod()-1
            if not np.allclose(composed.to_numpy(),monthly[key].to_numpy(),atol=1e-12):
                raise ValueError('monthly compounding mismatch '+key)
            if not np.isclose(np.prod(1+daily[key]),np.prod(1+monthly[key]),rtol=1e-12):
                raise ValueError('daily and monthly wealth differ '+key)
            errors[key] = error
    decisions = pd.read_csv(OUT/f'{mode}_decisions.csv',parse_dates=['signal_date','execution_date'])
    if not (decisions.signal_date<decisions.execution_date).all() or not pd.DatetimeIndex(decisions.execution_date).equals(weights.index):
        raise ValueError('signal/execution timing violation')
    if not (decisions.iloc[recipe['warmup_days']:].selected_assets == recipe['portfolio_assets']).all():
        raise ValueError('sparsity violation')
    if mode=='llm':
        trace = json.loads((OUT/'llm_llm_trace.json').read_text())
        if len(trace) != manifest['llm_calls'] or manifest['accepted_llm_functions'] <= 0 or manifest['days_using_llm_factors'] <= 0:
            raise ValueError('missing real LLM contribution')
        cache = sqlite3.connect(ROOT/'runs/economic_fidelity/openrouter/response_cache.sqlite3')
        for item in trace:
            if not item['feedback_last_realization'] == item['decision_date'] < item['execution_date']:
                raise ValueError('future feedback')
            cached = cache.execute('SELECT body FROM responses WHERE request_hash=?',(item['request_hash'],)).fetchone()
            if cached is None:
                raise ValueError('missing cached response')
            response = json.loads(cached[0])
            if response['response']['id'] != item['response_id'] or response['request']['model'] != recipe['model']:
                raise ValueError('LLM response/model lineage changed')
        ledger = json.loads((ROOT/'runs/economic_fidelity/openrouter/project_spend.json').read_text())
        for item in trace:
            if ledger['calls'][item['request_hash']]['status'] != 'complete':
                raise ValueError('unsettled API call')
    report = {'status':'pass','mode':mode,'daily_account_rows':len(weights),
        'source_universe_size':weights.shape[1],'accounting_cases':4,
        'independent_daily_return_max_errors':errors,'daily_to_monthly_wealth_preserved':True,
        'signal_execution_order_verified':True,'recipe_and_output_hashes_verified':True,
        'independent_human_source_review_complete':False,'full_native_paper_reproduction':False}
    atomic_json(OUT/f'validation_{mode}.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['llm','initial'],required=True)
    validate(parser.parse_args().mode)
