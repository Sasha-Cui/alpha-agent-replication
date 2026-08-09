#!/usr/bin/env python3
"""Evaluate monthly candidate returns against official Kenneth French FF3 and FF5+Mom factors."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from pandas_datareader import data as web

from alpha_evolve.performance import (
    PSEUDOINVERSE_RCOND,
    TARGET_ANNUAL_VOLATILITY,
    annualized_sharpe,
    max_tangency_sharpe,
    newey_west_intercept_se,
    target_vol_scale,
)
from alpha_evolve.policy import require_legacy_non_jkp_opt_in

MIN_OVERLAP_MONTHS = 24
BENCHMARKS = {
    "FF3_OFFICIAL": ("Mkt-RF", "SMB", "HML"),
    "FF5MOM_OFFICIAL": ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"),
}



def fetch_french_factors(start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / "kenneth_french_monthly_ff3_ff5mom.csv"
    meta = cache_dir / "kenneth_french_monthly_ff3_ff5mom_meta.json"
    if cache.exists():
        out = pd.read_csv(cache)
        out["month"] = pd.to_datetime(out["month"]) + pd.offsets.MonthEnd(0)
        return out
    ff3 = web.DataReader("F-F_Research_Data_Factors", "famafrench", start=start, end=end)[0].copy()
    ff5 = web.DataReader("F-F_Research_Data_5_Factors_2x3", "famafrench", start=start, end=end)[0].copy()
    mom = web.DataReader("F-F_Momentum_Factor", "famafrench", start=start, end=end)[0].copy()
    df = ff5.join(mom, how="inner", rsuffix="_mom")
    # Keep the FF3 SMB/HML for the FF3 row and the FF5 SMB/HML for FF5Mom? To avoid
    # duplicate names, use FF3 from the FF3 file for FF3 and FF5 from the FF5 file for FF5Mom.
    out = pd.DataFrame(index=df.index)
    out["Mkt-RF"] = ff3["Mkt-RF"]
    out["SMB"] = ff3["SMB"]
    out["HML"] = ff3["HML"]
    out["RMW"] = ff5["RMW"]
    out["CMA"] = ff5["CMA"]
    out["Mom"] = mom["Mom"]
    out["RF"] = ff3["RF"]
    out = out / 100.0
    out = out.reset_index().rename(columns={"Date": "month"})
    out["month"] = out["month"].dt.to_timestamp("M") + pd.offsets.MonthEnd(0)
    out.to_csv(cache, index=False)
    meta.write_text(json.dumps({
        "source": "pandas_datareader famafrench Kenneth French Data Library",
        "datasets": ["F-F_Research_Data_Factors", "F-F_Research_Data_5_Factors_2x3", "F-F_Momentum_Factor"],
        "start": start,
        "end": end,
        "returns_are_decimal": True,
    }, indent=2, sort_keys=True), encoding="utf-8")
    return out


def evaluate(candidate_csv: Path, return_col: str, candidate_id: str, out_dir: Path) -> pd.DataFrame:
    cand = pd.read_csv(candidate_csv)
    if "month" not in cand.columns:
        raise ValueError("candidate CSV must include month")
    if return_col not in cand.columns:
        raise ValueError(f"candidate CSV must include {return_col}")
    cand = cand[["month", return_col]].rename(columns={return_col: "candidate_return"})
    cand["month"] = pd.to_datetime(cand["month"]) + pd.offsets.MonthEnd(0)
    cand["candidate_return"] = pd.to_numeric(cand["candidate_return"], errors="coerce")
    cand = cand.dropna(subset=["candidate_return"]).sort_values("month")
    start = cand["month"].min().strftime("%Y-%m")
    end = cand["month"].max().strftime("%Y-%m")
    factors = fetch_french_factors(start, end, out_dir / "cache")
    merged = cand.merge(factors, on="month", how="inner")
    if merged.empty:
        raise ValueError("No overlap between candidate and French factors")
    merged["candidate_excess_return"] = merged["candidate_return"] - merged["RF"]
    needed = ["candidate_excess_return", "Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
    scaled = merged[["month", *needed]].copy()
    scale_meta = {}
    for col in needed:
        scaled[col], scale_meta[col] = target_vol_scale(scaled[col])
    rows = []
    for benchmark, factor_cols_tuple in BENCHMARKS.items():
        factor_cols = list(factor_cols_tuple)
        reg = scaled[["month", "candidate_excess_return", *factor_cols]].dropna().copy()
        n = len(reg)
        base = {
            "candidate_id": candidate_id,
            "benchmark_set": benchmark,
            "factor_source": "kenneth_french_official_monthly",
            "n_overlap_months": n,
            "overlap_start": reg["month"].min().date().isoformat() if n else None,
            "overlap_end": reg["month"].max().date().isoformat() if n else None,
            "candidate_standalone_oos_sharpe_excess": annualized_sharpe(reg["candidate_excess_return"]),
            "candidate_annualized_volatility_before_target": scale_meta["candidate_excess_return"]["annualized_volatility_before_target"],
            "candidate_target_vol_scale": scale_meta["candidate_excess_return"]["target_vol_scale"],
            "candidate_annualized_volatility_after_target": scale_meta["candidate_excess_return"]["annualized_volatility_after_target"],
        }
        if n < MIN_OVERLAP_MONTHS or n <= len(factor_cols) + 2:
            rows.append({**base, "status": "insufficient_overlap"})
            continue
        y = reg["candidate_excess_return"].to_numpy(dtype="float64")
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
            **{f"beta_{name}": float(beta_map.get(name, np.nan)) for name in factor_cols},
        })
    out = pd.DataFrame(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_dir / "ff_official_benchmark_metrics.csv", index=False)
    scaled[["month", "candidate_excess_return"]].to_csv(out_dir / "candidate_excess_returns_scaled_7pct.csv", index=False)
    metadata = {
        "candidate_id": candidate_id,
        "candidate_csv": str(candidate_csv),
        "return_col": return_col,
        "factor_source": "Kenneth French official monthly factors via pandas_datareader",
        "benchmarks": {k: list(v) for k, v in BENCHMARKS.items()},
        "target_annual_volatility": TARGET_ANNUAL_VOLATILITY,
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return out


def main() -> None:
    require_legacy_non_jkp_opt_in()
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-csv", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--return-col", default="candidate_return")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    metrics = evaluate(args.candidate_csv, args.return_col, args.candidate_id, args.out_dir)
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
