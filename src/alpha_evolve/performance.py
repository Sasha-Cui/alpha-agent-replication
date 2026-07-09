#!/usr/bin/env python3
"""Evaluate one candidate monthly return series against FF3 and FF5Mom benchmarks.

Input contract: CSV with `month` and a candidate return column, default
`candidate_return`. Returns must be monthly decimal returns. The script aligns to
the fixed external-factor-data 1999-07-31..2021-12-31 window, scales the candidate
and benchmark factor columns to 7% annual realized volatility on the overlap
sample, and reports standalone Sharpe, factor alpha, HAC t-stat, appraisal ratio,
and factor-span delta Sharpe.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .paths import DEFAULT_FACTOR_PANEL
from .policy import LEGACY_NON_JKP_MESSAGE, require_legacy_non_jkp_opt_in

ANALYSIS_WINDOW_START = pd.Timestamp("1999-07-31")
ANALYSIS_WINDOW_END = pd.Timestamp("2021-12-31")
TARGET_ANNUAL_VOLATILITY = 0.07
PSEUDOINVERSE_RCOND = 1e-10
MIN_OVERLAP_MONTHS = 24
FACTOR_PANEL = DEFAULT_FACTOR_PANEL

CAPM_FACTOR = "capm_top1000_mkt"
FF3_CHARS = ("be_me", "market_equity")
FF5MOM_CHARS = ("be_me", "at_gr1", "market_equity", "ope_be", "ret_12_1")
BENCHMARKS = {
    "CAPM": (CAPM_FACTOR,),
    "FF3": (CAPM_FACTOR, *(f"char__{c}" for c in FF3_CHARS)),
    "FF5MOM": (CAPM_FACTOR, *(f"char__{c}" for c in FF5MOM_CHARS)),
}


def annualized_volatility(values: Iterable[float]) -> float:
    arr = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    if arr.size < 2:
        return float("nan")
    return float(math.sqrt(12.0) * np.std(arr, ddof=1))


def annualized_sharpe(values: Iterable[float]) -> float:
    arr = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    if arr.size < 2:
        return float("nan")
    vol = float(np.std(arr, ddof=1))
    if not np.isfinite(vol) or vol == 0.0:
        return float("nan")
    return float(math.sqrt(12.0) * np.mean(arr) / vol)


def target_vol_scale(values: pd.Series) -> tuple[pd.Series, dict[str, float]]:
    ann_vol = annualized_volatility(values)
    if not np.isfinite(ann_vol) or ann_vol == 0.0:
        return values.astype("float64"), {
            "annualized_volatility_before_target": ann_vol,
            "target_vol_scale": float("nan"),
            "annualized_volatility_after_target": ann_vol,
        }
    scale = TARGET_ANNUAL_VOLATILITY / ann_vol
    out = values.astype("float64") * scale
    return out, {
        "annualized_volatility_before_target": ann_vol,
        "target_vol_scale": float(scale),
        "annualized_volatility_after_target": annualized_volatility(out),
    }


def max_tangency_sharpe(frame: pd.DataFrame, factor_cols: list[str]) -> float:
    arr = frame[factor_cols].replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype="float64")
    if arr.shape[0] < 2 or arr.shape[1] == 0:
        return float("nan")
    mu = np.mean(arr, axis=0)
    cov = np.cov(arr, rowvar=False, ddof=1)
    if cov.ndim == 0:
        cov = np.asarray([[float(cov)]], dtype="float64")
    inv = np.linalg.pinv(cov, rcond=PSEUDOINVERSE_RCOND)
    sr2_monthly = float(mu.T @ inv @ mu)
    if not np.isfinite(sr2_monthly) or sr2_monthly < 0:
        return float("nan")
    return float(math.sqrt(12.0 * sr2_monthly))


def newey_west_intercept_se(x: np.ndarray, residual: np.ndarray, xtx_inv: np.ndarray, lags: int | None = None) -> float:
    n = int(len(residual))
    if n < 3:
        return float("nan")
    if lags is None:
        lags = int(math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    lags = max(0, min(int(lags), n - 1))
    v = xtx_inv[:, 0]
    q = x @ v
    z = residual * q
    var = float(np.dot(z, z))
    for lag in range(1, lags + 1):
        weight = 1.0 - lag / (lags + 1.0)
        var += float(2.0 * weight * np.dot(z[lag:], z[:-lag]))
    return math.sqrt(max(var, 0.0))


def evaluate(candidate_csv: Path, return_col: str, candidate_id: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    factors = pd.read_csv(FACTOR_PANEL)
    factors["month"] = pd.to_datetime(factors["month"]) + pd.offsets.MonthEnd(0)
    factors = factors[(factors["month"] >= ANALYSIS_WINDOW_START) & (factors["month"] <= ANALYSIS_WINDOW_END)].copy()

    cand = pd.read_csv(candidate_csv)
    if "month" not in cand.columns:
        raise ValueError(f"{candidate_csv} is missing required `month` column")
    if return_col not in cand.columns:
        raise ValueError(f"{candidate_csv} is missing return column `{return_col}`")
    cand = cand[["month", return_col]].rename(columns={return_col: "candidate_return"})
    cand["month"] = pd.to_datetime(cand["month"]) + pd.offsets.MonthEnd(0)
    cand["candidate_return"] = pd.to_numeric(cand["candidate_return"], errors="coerce")

    needed = sorted({c for cols in BENCHMARKS.values() for c in cols})
    merged_raw = cand.merge(factors[["month", *needed]], on="month", how="inner")
    merged_raw = merged_raw.replace([np.inf, -np.inf], np.nan).dropna(subset=["candidate_return"])
    merged_raw = merged_raw[(merged_raw["month"] >= ANALYSIS_WINDOW_START) & (merged_raw["month"] <= ANALYSIS_WINDOW_END)].copy()
    if merged_raw.empty:
        raise ValueError("No candidate/factor overlap in the fixed analysis window")

    # Scale candidate and each factor on the common candidate overlap, matching the template policy.
    scaled = merged_raw.copy()
    scale_meta = {}
    for col in ["candidate_return", *needed]:
        scaled[col], scale_meta[col] = target_vol_scale(scaled[col])

    rows = []
    for benchmark, factor_cols_tuple in BENCHMARKS.items():
        factor_cols = list(factor_cols_tuple)
        reg = scaled[["month", "candidate_return", *factor_cols]].dropna().copy()
        n = len(reg)
        base = {
            "candidate_id": candidate_id,
            "benchmark_set": benchmark,
            "n_overlap_months": n,
            "overlap_start": reg["month"].min().date().isoformat() if n else None,
            "overlap_end": reg["month"].max().date().isoformat() if n else None,
            "candidate_standalone_oos_sharpe": annualized_sharpe(reg["candidate_return"]),
            "candidate_annualized_volatility_before_target": scale_meta["candidate_return"]["annualized_volatility_before_target"],
            "candidate_target_vol_scale": scale_meta["candidate_return"]["target_vol_scale"],
            "candidate_annualized_volatility_after_target": scale_meta["candidate_return"]["annualized_volatility_after_target"],
        }
        if n < MIN_OVERLAP_MONTHS or n <= len(factor_cols) + 2:
            rows.append({**base, "status": "insufficient_overlap"})
            continue
        y = reg["candidate_return"].to_numpy(dtype="float64")
        x = np.column_stack([np.ones(n), reg[factor_cols].to_numpy(dtype="float64")])
        xtx_inv = np.linalg.pinv(x.T @ x, rcond=PSEUDOINVERSE_RCOND)
        coef = np.linalg.pinv(x, rcond=PSEUDOINVERSE_RCOND) @ y
        fitted = x @ coef
        resid = y - fitted
        alpha = float(coef[0])
        resid_vol = float(np.std(resid, ddof=1))
        se_alpha = newey_west_intercept_se(x, resid, xtx_inv)
        appraisal = float(math.sqrt(12.0) * alpha / resid_vol) if resid_vol and np.isfinite(resid_vol) else float("nan")
        appraisal_sq = appraisal**2 if np.isfinite(appraisal) else float("nan")
        old_sr = max_tangency_sharpe(reg, factor_cols)
        new_combined = math.sqrt(old_sr**2 + appraisal_sq) if np.isfinite(old_sr) and np.isfinite(appraisal_sq) else float("nan")
        total_ss = float(np.sum((y - np.mean(y)) ** 2))
        resid_ss = float(np.sum(resid**2))
        beta_map = dict(zip(factor_cols, coef[1:]))
        rows.append({
            **base,
            "status": "ok",
            "alpha_monthly": alpha,
            "alpha_annualized": 12.0 * alpha,
            "alpha_tstat_hac": float(alpha / se_alpha) if se_alpha and np.isfinite(se_alpha) else float("nan"),
            "residual_monthly_volatility": resid_vol,
            "appraisal_ratio": appraisal,
            "appraisal_ratio_squared": appraisal_sq,
            "old_benchmark_set_annualized_sharpe": old_sr,
            "new_combined_annualized_sharpe": new_combined,
            "combined_minus_old_sharpe": new_combined - old_sr if np.isfinite(new_combined) and np.isfinite(old_sr) else float("nan"),
            "r_squared": 1.0 - resid_ss / total_ss if total_ss > 0 else float("nan"),
            "correlation_to_fitted_benchmark": float(np.corrcoef(y, fitted)[0, 1]) if np.std(y, ddof=1) > 0 and np.std(fitted, ddof=1) > 0 else float("nan"),
            "beta_capm_top1000_mkt": float(beta_map.get(CAPM_FACTOR, np.nan)),
            "beta_ff3_be_me": float(beta_map.get("char__be_me", np.nan)),
            "beta_ff3_market_equity": float(beta_map.get("char__market_equity", np.nan)),
            "beta_ff5mom_at_gr1": float(beta_map.get("char__at_gr1", np.nan)),
            "beta_ff5mom_ope_be": float(beta_map.get("char__ope_be", np.nan)),
            "beta_ff5mom_ret_12_1": float(beta_map.get("char__ret_12_1", np.nan)),
        })
    metadata = {
        "candidate_id": candidate_id,
        "candidate_csv": str(candidate_csv),
        "return_col": return_col,
        "factor_panel": str(FACTOR_PANEL),
        "analysis_window_start": ANALYSIS_WINDOW_START.date().isoformat(),
        "analysis_window_end": ANALYSIS_WINDOW_END.date().isoformat(),
        "target_annual_volatility": TARGET_ANNUAL_VOLATILITY,
        "benchmarks": {k: list(v) for k, v in BENCHMARKS.items()},
    }
    return pd.DataFrame(rows), scaled[["month", "candidate_return"]].copy(), metadata


def main() -> None:
    require_legacy_non_jkp_opt_in()
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-csv", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--return-col", default="candidate_return")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    metrics, scaled_returns, metadata = evaluate(args.candidate_csv, args.return_col, args.candidate_id)
    metrics.to_csv(args.out_dir / "ff_benchmark_metrics.csv", index=False)
    scaled_returns.to_csv(args.out_dir / "candidate_returns_scaled_7pct.csv", index=False)
    (args.out_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
