#!/usr/bin/env python3
"""Evaluate GuruAgents winner sleeves as additions to a long-only JKP factor book.

All returns are built from read-only JKP USA inputs. The existing book is built
from JKP's precomputed raw portfolio legs (`pfs.parquet`): for each
characteristic, use the long side implied by `factor_details.xlsx` direction,
then equal-weight those directed long-only legs.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from alpha_evolve.jkp_performance import single_asset_grs
from alpha_evolve.paths import DEFAULT_JKP_ROOT
from alpha_evolve.performance import PSEUDOINVERSE_RCOND, annualized_sharpe, newey_west_intercept_se

JKP_ROOT = DEFAULT_JKP_ROOT
DEFAULT_USA = JKP_ROOT / 'data/processed/characteristics/USA.parquet'
DEFAULT_PFS = JKP_ROOT / 'data/processed/portfolios/pfs.parquet'
DEFAULT_FACTOR_DETAILS = JKP_ROOT / 'data/factor_details.xlsx'
DEFAULT_NYSE_CUTOFFS = JKP_ROOT / 'data/processed/other_output/nyse_cutoffs.parquet'
DEFAULT_OUT = Path('paper_runs/idea_replications/guru_jkp_longonly_additive')

BASE_COLS = [
    'id', 'permno', 'eom', 'ret_exc_lead1m', 'me', 'size_grp',
    'qmj', 'qmj_growth', 'qmj_prof', 'ope_be', 'gp_me', 'debt_at',
    'be_me', 'cash_at', 'rvol_252d', 'beta_252d', 'ebit_mev', 'gp_mev',
    'ni_me', 'ocf_me', 'oaccruals_at', 'debt_gr1', 'eqnetis_me', 'at_turnover',
    'sale_gr1', 'ebitda_debt', 'betadown_252d',
]

PRIMARY_CANDIDATES = [
    'guru_buffett_quality_compounder',
    'guru_equal_weight_style_ensemble',
]


def safe_num(x: Any) -> float:
    try:
        y = float(x)
    except Exception:
        return float('nan')
    return y if np.isfinite(y) else float('nan')


def ann_vol(s: pd.Series) -> float:
    x = pd.to_numeric(s, errors='coerce').dropna()
    if len(x) < 2:
        return float('nan')
    return float(np.sqrt(12.0) * x.std(ddof=1))


def ann_mean(s: pd.Series) -> float:
    x = pd.to_numeric(s, errors='coerce').dropna()
    if x.empty:
        return float('nan')
    return float(12.0 * x.mean())


def drawdown(s: pd.Series) -> float:
    x = pd.to_numeric(s, errors='coerce').dropna()
    if x.empty:
        return float('nan')
    wealth = (1.0 + x).cumprod()
    peak = wealth.cummax()
    dd = wealth / peak - 1.0
    return float(dd.min())


def cs_rank(frame: pd.DataFrame, col: str) -> pd.Series:
    vals = pd.to_numeric(frame[col], errors='coerce').replace([np.inf, -np.inf], np.nan)
    ranks = vals.rank(method='average', pct=True)
    return 2.0 * (ranks - 0.5)


def build_scores_for_month(frame: pd.DataFrame) -> pd.DataFrame:
    f = frame.copy()
    for col in [
        'qmj', 'qmj_growth', 'qmj_prof', 'ope_be', 'gp_me', 'debt_at',
        'be_me', 'cash_at', 'rvol_252d', 'beta_252d', 'ebit_mev', 'gp_mev',
        'ni_me', 'ocf_me', 'oaccruals_at', 'debt_gr1', 'eqnetis_me', 'at_turnover',
        'sale_gr1', 'ebitda_debt', 'betadown_252d',
    ]:
        f[f'z_{col}'] = cs_rank(f, col)

    f['guru_graham_deep_value_defensive'] = (
        f['z_be_me'] + f['z_cash_at'] + f['z_ope_be']
        - f['z_debt_at'] - f['z_rvol_252d'] - f['z_beta_252d']
    )
    f['guru_buffett_quality_compounder'] = (
        f['z_qmj'] + f['z_qmj_growth'] + f['z_qmj_prof']
        + f['z_ope_be'] + f['z_gp_me'] - f['z_debt_at']
    )
    f['guru_greenblatt_magic_formula'] = f['z_ebit_mev'] + f['z_ope_be'] + f['z_gp_mev'] + f['z_be_me']
    f['guru_piotroski_fscore_proxy'] = (
        f['z_ni_me'] + f['z_ocf_me'] - f['z_oaccruals_at'] - f['z_debt_gr1']
        - f['z_eqnetis_me'] + f['z_at_turnover'] + f['z_sale_gr1']
    )
    f['guru_altman_distress_avoidance'] = (
        f['z_ebitda_debt'] + f['z_cash_at'] + f['z_ni_me']
        - f['z_debt_at'] - f['z_rvol_252d'] - f['z_betadown_252d']
    )
    f['guru_equal_weight_style_ensemble'] = f[[
        'guru_graham_deep_value_defensive', 'guru_buffett_quality_compounder',
        'guru_greenblatt_magic_formula', 'guru_piotroski_fscore_proxy',
        'guru_altman_distress_avoidance',
    ]].mean(axis=1)
    return f


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    x = pd.to_numeric(values, errors='coerce')
    w = pd.to_numeric(weights, errors='coerce')
    ok = x.notna() & w.notna() & (w > 0)
    if not ok.any():
        return float('nan')
    return float(np.average(x[ok], weights=w[ok]))


def build_book_returns(pfs_path: Path, details_path: Path, start: str, end: str) -> pd.DataFrame:
    details = pd.read_excel(details_path)
    details = details.dropna(subset=['abr_jkp', 'direction']).copy()
    details['characteristic'] = details['abr_jkp'].astype(str)
    details['direction'] = details['direction'].astype(int)
    details['significance'] = pd.to_numeric(details['significance'], errors='coerce')
    details = details[['characteristic', 'direction', 'significance']].drop_duplicates('characteristic')

    pfs = pd.read_parquet(pfs_path, columns=['excntry', 'characteristic', 'pf', 'eom', 'ret_ew', 'ret_vw', 'ret_vw_cap'])
    pfs = pfs[pfs['excntry'].eq('USA')].copy()
    pfs['eom'] = pd.to_datetime(pfs['eom'], errors='coerce') + pd.offsets.MonthEnd(0)
    pfs = pfs.merge(details, on='characteristic', how='inner')
    pfs['long_pf'] = np.where(pfs['direction'] > 0, 3.0, 1.0)
    pfs = pfs[pfs['pf'].eq(pfs['long_pf'])].copy()
    pfs = pfs[(pfs['eom'] >= pd.Timestamp(start)) & (pfs['eom'] <= pd.Timestamp(end))]

    def agg_book(df: pd.DataFrame, book_id: str) -> pd.DataFrame:
        out = df.groupby('eom', as_index=False).agg(
            n_factors=('characteristic', 'nunique'),
            book_return_vw_cap=('ret_vw_cap', 'mean'),
            book_return_vw=('ret_vw', 'mean'),
            book_return_ew=('ret_ew', 'mean'),
        )
        out['book_id'] = book_id
        return out

    all_book = agg_book(pfs, 'jkp153_all_metadata_long_only')
    sig_book = agg_book(pfs[pfs['significance'].eq(1.0)].copy(), 'jkp119_significant_metadata_long_only')
    return pd.concat([all_book, sig_book], ignore_index=True).sort_values(['book_id', 'eom'])


def build_candidate_returns(usa_path: Path, nyse_cutoffs_path: Path, start_signal: str, end_signal: str) -> pd.DataFrame:
    raw = pd.read_parquet(usa_path, columns=BASE_COLS)
    raw['signal_month'] = pd.to_datetime(raw['eom'], errors='coerce') + pd.offsets.MonthEnd(0)
    raw['month'] = raw['signal_month'] + pd.offsets.MonthEnd(1)
    raw['ret_exc_lead1m'] = pd.to_numeric(raw['ret_exc_lead1m'], errors='coerce')
    raw['me'] = pd.to_numeric(raw['me'], errors='coerce')
    raw = raw[(raw['signal_month'] >= pd.Timestamp(start_signal)) & (raw['signal_month'] <= pd.Timestamp(end_signal))].copy()
    raw = raw.replace([np.inf, -np.inf], np.nan).dropna(subset=['signal_month', 'month', 'ret_exc_lead1m', 'me'])
    raw = raw[raw['me'] > 0].copy()

    cut = pd.read_parquet(nyse_cutoffs_path, columns=['eom', 'nyse_p80'])
    cut['signal_month'] = pd.to_datetime(cut['eom'], errors='coerce') + pd.offsets.MonthEnd(0)
    raw = raw.merge(cut[['signal_month', 'nyse_p80']], on='signal_month', how='left')
    raw['me_cap'] = np.minimum(raw['me'], pd.to_numeric(raw['nyse_p80'], errors='coerce'))
    raw['me_cap'] = raw['me_cap'].where(raw['me_cap'].notna() & (raw['me_cap'] > 0), raw['me'])

    out_rows = []
    variants = [
        ('jkp_tercile_vw_cap', 2.0 / 3.0, 'me_cap', False),
        ('top_decile_vw_cap', 0.90, 'me_cap', False),
        ('top1000_decile_vw', 0.90, 'me', True),
    ]
    for signal_month, frame in raw.groupby('signal_month', sort=True):
        scored = build_scores_for_month(frame)
        for candidate_id in PRIMARY_CANDIDATES:
            sub_base = scored[[candidate_id, 'ret_exc_lead1m', 'me', 'me_cap', 'size_grp', 'month']].dropna(subset=[candidate_id, 'ret_exc_lead1m']).copy()
            if sub_base.empty:
                continue
            for variant_id, q, weight_col, top1000 in variants:
                sub = sub_base.copy()
                if top1000:
                    sub = sub.sort_values('me', ascending=False).head(1000)
                    ref = sub[candidate_id]
                else:
                    ref = sub.loc[sub['size_grp'].isin(['mega', 'large', 'small']), candidate_id]
                    if ref.notna().sum() < 10:
                        ref = sub[candidate_id]
                if ref.notna().sum() < 10:
                    ret = float('nan')
                    n_stocks = 0
                else:
                    threshold = ref.quantile(q)
                    chosen = sub[sub[candidate_id] >= threshold]
                    ret = weighted_mean(chosen['ret_exc_lead1m'], chosen[weight_col])
                    n_stocks = int(chosen.shape[0])
                out_rows.append({
                    'month': pd.Timestamp(sub_base['month'].iloc[0]) + pd.offsets.MonthEnd(0),
                    'signal_month': pd.Timestamp(signal_month) + pd.offsets.MonthEnd(0),
                    'candidate_id': candidate_id,
                    'construction': variant_id,
                    'candidate_return': ret,
                    'n_stocks': n_stocks,
                })
    ret = pd.DataFrame(out_rows).sort_values(['construction', 'candidate_id', 'month'])
    combo_rows = []
    for construction, grp in ret.groupby('construction'):
        wide = grp.pivot(index='month', columns='candidate_id', values='candidate_return').reset_index()
        if set(PRIMARY_CANDIDATES).issubset(wide.columns):
            combo = wide[['month', *PRIMARY_CANDIDATES]].copy()
            combo['candidate_return'] = combo[PRIMARY_CANDIDATES].mean(axis=1)
            combo['candidate_id'] = 'guru_two_winner_equal_weight_combo'
            combo['construction'] = construction
            combo['n_stocks'] = np.nan
            combo['signal_month'] = combo['month'] - pd.offsets.MonthEnd(1)
            combo_rows.append(combo[['month', 'signal_month', 'candidate_id', 'construction', 'candidate_return', 'n_stocks']])
    if combo_rows:
        ret = pd.concat([ret, *combo_rows], ignore_index=True).sort_values(['construction', 'candidate_id', 'month'])
    return ret


def return_stats(s: pd.Series) -> dict[str, float]:
    x = pd.to_numeric(s, errors='coerce').dropna()
    return {
        'ann_mean': ann_mean(x),
        'ann_vol': ann_vol(x),
        'sharpe': annualized_sharpe(x),
        'max_drawdown': drawdown(x),
    }


def regression_vs_book(df: pd.DataFrame) -> dict[str, Any]:
    reg = df[['month', 'candidate_return', 'book_return']].replace([np.inf, -np.inf], np.nan).dropna().copy()
    n = len(reg)
    if n < 24:
        return {'n_overlap_months': n, 'alpha_status': 'insufficient_overlap'}
    y = reg['candidate_return'].to_numpy(dtype='float64')
    x_factor = reg['book_return'].to_numpy(dtype='float64')
    x = np.column_stack([np.ones(n), x_factor])
    coef = np.linalg.pinv(x, rcond=PSEUDOINVERSE_RCOND) @ y
    fitted = x @ coef
    resid = y - fitted
    xtx_inv = np.linalg.pinv(x.T @ x, rcond=PSEUDOINVERSE_RCOND)
    se_alpha = newey_west_intercept_se(x, resid, xtx_inv)
    resid_vol = float(np.std(resid, ddof=1))
    alpha = float(coef[0])
    ar = float(math.sqrt(12.0) * alpha / resid_vol) if resid_vol > 0 else float('nan')
    grs_input = reg.rename(columns={'book_return': 'jkp_long_only_book'})
    grs = single_asset_grs(grs_input, ['jkp_long_only_book'])
    return {
        'n_overlap_months': n,
        'overlap_start': reg['month'].min().date().isoformat(),
        'overlap_end': reg['month'].max().date().isoformat(),
        'alpha_status': 'ok',
        'alpha_annualized_vs_book': 12.0 * alpha,
        'alpha_tstat_hac_vs_book': float(alpha / se_alpha) if se_alpha and np.isfinite(se_alpha) else float('nan'),
        'beta_to_book': float(coef[1]),
        'residual_ann_vol': math.sqrt(12.0) * resid_vol,
        'appraisal_ratio_vs_book': ar,
        'information_ratio_vs_book': ar,
        'correlation_to_book': float(np.corrcoef(y, x_factor)[0, 1]) if np.std(y, ddof=1) > 0 and np.std(x_factor, ddof=1) > 0 else float('nan'),
        'r_squared_vs_book': float(1.0 - np.sum(resid**2) / np.sum((y - y.mean())**2)) if np.sum((y - y.mean())**2) > 0 else float('nan'),
        'grs_f_vs_book': safe_num(grs.get('grs_f')),
        'grs_p_value_vs_book': safe_num(grs.get('grs_p_value')),
        'grs_reject_5pct_vs_book': grs.get('grs_reject_5pct'),
    }


def best_long_only_blend(book: pd.Series, candidate: pd.Series) -> dict[str, float]:
    weights = np.linspace(0.0, 1.0, 1001)
    best = {'best_candidate_weight': 0.0, 'best_blend_sharpe': -np.inf, 'best_blend_ann_mean': float('nan'), 'best_blend_ann_vol': float('nan')}
    for w in weights:
        blend = (1.0 - w) * book + w * candidate
        sr = annualized_sharpe(blend)
        if np.isfinite(sr) and sr > best['best_blend_sharpe']:
            stats = return_stats(blend)
            best = {
                'best_candidate_weight': float(w),
                'best_blend_sharpe': float(sr),
                'best_blend_ann_mean': stats['ann_mean'],
                'best_blend_ann_vol': stats['ann_vol'],
            }
    return best


def additive_rows(book_returns: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for book_id, book in book_returns.groupby('book_id'):
        book = book.rename(columns={'book_return_vw_cap': 'book_return'})[['eom', 'book_return', 'n_factors']].copy()
        book = book.rename(columns={'eom': 'month'})
        for (candidate_id, construction), cand in candidates.groupby(['candidate_id', 'construction']):
            merged = book.merge(cand[['month', 'candidate_return']], on='month', how='inner')
            merged = merged.replace([np.inf, -np.inf], np.nan).dropna(subset=['book_return', 'candidate_return']).copy()
            if len(merged) < 24:
                continue
            nfac_median = float(merged['n_factors'].median())
            literal = (merged['n_factors'] * merged['book_return'] + merged['candidate_return']) / (merged['n_factors'] + 1.0)
            blend_50 = 0.5 * merged['book_return'] + 0.5 * merged['candidate_return']
            best = best_long_only_blend(merged['book_return'], merged['candidate_return'])
            book_stats = return_stats(merged['book_return'])
            cand_stats = return_stats(merged['candidate_return'])
            literal_stats = return_stats(literal)
            blend50_stats = return_stats(blend_50)
            reg = regression_vs_book(merged)
            rows.append({
                'book_id': book_id,
                'candidate_id': candidate_id,
                'construction': construction,
                'n_overlap_months': int(len(merged)),
                'overlap_start': merged['month'].min().date().isoformat(),
                'overlap_end': merged['month'].max().date().isoformat(),
                'book_n_factors_median': nfac_median,
                'book_ann_mean': book_stats['ann_mean'],
                'book_ann_vol': book_stats['ann_vol'],
                'book_sharpe': book_stats['sharpe'],
                'book_max_drawdown': book_stats['max_drawdown'],
                'candidate_ann_mean': cand_stats['ann_mean'],
                'candidate_ann_vol': cand_stats['ann_vol'],
                'candidate_sharpe': cand_stats['sharpe'],
                'candidate_max_drawdown': cand_stats['max_drawdown'],
                'literal_equal_sleeve_weight': 1.0 / (nfac_median + 1.0),
                'literal_book_plus_candidate_sharpe': literal_stats['sharpe'],
                'literal_delta_sharpe': literal_stats['sharpe'] - book_stats['sharpe'],
                'literal_ann_mean': literal_stats['ann_mean'],
                'literal_ann_vol': literal_stats['ann_vol'],
                'blend50_sharpe': blend50_stats['sharpe'],
                'blend50_delta_sharpe': blend50_stats['sharpe'] - book_stats['sharpe'],
                'blend50_ann_mean': blend50_stats['ann_mean'],
                'blend50_ann_vol': blend50_stats['ann_vol'],
                **best,
                'best_delta_sharpe': best['best_blend_sharpe'] - book_stats['sharpe'],
                **reg,
            })
    out = pd.DataFrame(rows)
    return out.sort_values(['book_id', 'construction', 'best_delta_sharpe', 'alpha_tstat_hac_vs_book'], ascending=[True, True, False, False])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--start-signal', default='1999-07-31')
    parser.add_argument('--end-signal', default='2024-11-30')
    parser.add_argument('--start-book', default='1999-08-31')
    parser.add_argument('--end-book', default='2024-12-31')
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    book = build_book_returns(DEFAULT_PFS, DEFAULT_FACTOR_DETAILS, args.start_book, args.end_book)
    cand = build_candidate_returns(DEFAULT_USA, DEFAULT_NYSE_CUTOFFS, args.start_signal, args.end_signal)
    summary = additive_rows(book, cand)

    book.to_csv(args.out_dir / 'jkp_long_only_book_returns.csv', index=False)
    cand.to_csv(args.out_dir / 'guru_candidate_long_only_returns.csv', index=False)
    summary.to_csv(args.out_dir / 'guru_jkp_longonly_additive_summary.csv', index=False)
    metadata = {
        'input_policy': 'read-only JKP USA inputs only; no China, no external returns, no yfinance, no paper-shipped returns',
        'usa_path': str(DEFAULT_USA),
        'pfs_path': str(DEFAULT_PFS),
        'factor_details_path': str(DEFAULT_FACTOR_DETAILS),
        'nyse_cutoffs_path': str(DEFAULT_NYSE_CUTOFFS),
        'primary_book': 'equal-weight average of directed long-only JKP characteristic legs from pfs.parquet, using ret_vw_cap',
        'book_definitions': {
            'jkp153_all_metadata_long_only': 'all 153 abr_jkp rows with directions in factor_details.xlsx',
            'jkp119_significant_metadata_long_only': '119 abr_jkp rows with significance=1; included because no explicit jkp132 list was found in approved folders',
        },
        'candidate_constructions': {
            'jkp_tercile_vw_cap': 'top tercile by composite Guru score using non-microcap breakpoints and capped value weights; primary match to JKP pfs convention',
            'top_decile_vw_cap': 'top decile by composite Guru score using non-microcap breakpoints and capped value weights',
            'top1000_decile_vw': 'top decile among largest 1000 by me with value weights; closest to earlier exploratory proxy universe',
        },
        'candidate_ids': PRIMARY_CANDIDATES + ['guru_two_winner_equal_weight_combo'],
        'start_signal': args.start_signal,
        'end_signal': args.end_signal,
        'start_book': args.start_book,
        'end_book': args.end_book,
    }
    (args.out_dir / 'run_metadata.json').write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding='utf-8')
    print(json.dumps({
        'book_rows': int(len(book)),
        'candidate_rows': int(len(cand)),
        'summary_rows': int(len(summary)),
        'summary_csv': str(args.out_dir / 'guru_jkp_longonly_additive_summary.csv'),
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
