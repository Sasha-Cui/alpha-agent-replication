#!/usr/bin/env python3
"""Evaluate JKP-built candidate returns against JKP-built FF3/FF5Mom factors."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from .performance import (
    MIN_OVERLAP_MONTHS,
    PSEUDOINVERSE_RCOND,
    TARGET_ANNUAL_VOLATILITY,
    annualized_sharpe,
    max_tangency_sharpe,
    newey_west_intercept_se,
    target_vol_scale,
)

CAPM_FACTOR = "jkp_topn_mkt"
FF3_CHARS = ("be_me", "market_equity")
FF5MOM_CHARS = ("be_me", "at_gr1", "market_equity", "ope_be", "ret_12_1")
BENCHMARKS = {
    "CAPM_JKP": (CAPM_FACTOR,),
    "FF3_JKP": (CAPM_FACTOR, *(f"char__{c}" for c in FF3_CHARS)),
    "FF5MOM_JKP": (CAPM_FACTOR, *(f"char__{c}" for c in FF5MOM_CHARS)),
}


def _safe_cond(matrix: np.ndarray) -> float:
    try:
        return float(np.linalg.cond(np.atleast_2d(matrix)))
    except Exception:
        return float("nan")


def _invert_if_full_rank(matrix: np.ndarray, expected_rank: int) -> tuple[np.ndarray, int, float, bool]:
    mat = np.atleast_2d(np.asarray(matrix, dtype="float64"))
    rank = int(np.linalg.matrix_rank(mat))
    cond = _safe_cond(mat)
    full = rank == expected_rank
    if full:
        try:
            return np.linalg.inv(mat), rank, cond, True
        except np.linalg.LinAlgError:
            pass
    return np.linalg.pinv(mat, rcond=PSEUDOINVERSE_RCOND), rank, cond, False


def single_asset_grs(reg: pd.DataFrame, factor_cols: list[str]) -> dict[str, object]:
    """GRS joint-alpha statistic for one candidate asset versus a factor span."""
    t = int(len(reg))
    n_assets = 1
    n_factors = int(len(factor_cols))
    df1 = n_assets
    df2 = t - n_assets - n_factors
    base = {
        "grs_n_test_assets": n_assets,
        "grs_n_benchmark_factors": n_factors,
        "grs_df1": df1,
        "grs_df2": df2,
    }
    if t <= n_factors + 1 or df2 <= 0 or n_factors <= 0:
        return {
            **base,
            "grs_exact_valid": False,
            "grs_failure_reason": "insufficient degrees of freedom or missing factors",
            "grs_f": float("nan"),
            "grs_p_value": float("nan"),
            "grs_reject_5pct": None,
            "grs_reject_1pct": None,
            "grs_active_ir_annualized": float("nan"),
            "grs_benchmark_theta2_monthly": float("nan"),
            "grs_benchmark_tangency_sharpe_annualized": float("nan"),
        }

    factors = reg[factor_cols].to_numpy(dtype="float64")
    y = reg[["candidate_return"]].to_numpy(dtype="float64")
    x = np.column_stack([np.ones(t, dtype="float64"), factors])
    x_rank = int(np.linalg.matrix_rank(x))
    beta = np.linalg.pinv(x, rcond=PSEUDOINVERSE_RCOND) @ y
    alpha = beta[0, :]
    resid = y - x @ beta
    s_eta = (resid.T @ resid) / float(t - n_factors - 1)
    fbar = np.mean(factors, axis=0)
    demeaned_factors = factors - fbar
    omega = (demeaned_factors.T @ demeaned_factors) / float(t)

    inv_s, rank_s, cond_s, inv_s_exact = _invert_if_full_rank(s_eta, n_assets)
    inv_omega, rank_omega, cond_omega, inv_omega_exact = _invert_if_full_rank(omega, n_factors)
    alpha_quad = float(alpha.T @ inv_s @ alpha)
    theta2 = float(fbar.T @ inv_omega @ fbar)
    exact_valid = bool(inv_s_exact and inv_omega_exact and x_rank == n_factors + 1)
    grs_f = float((t / n_assets) * ((t - n_assets - n_factors) / (t - n_factors - 1)) * (alpha_quad / (1.0 + theta2)))
    p_value = float(stats.f.sf(grs_f, df1, df2)) if exact_valid else float("nan")
    return {
        **base,
        "grs_exact_valid": exact_valid,
        "grs_failure_reason": None if exact_valid else "rank-deficient covariance/design; statistic uses pseudoinverse and p-value is not exact",
        "grs_f": grs_f,
        "grs_p_value": p_value,
        "grs_reject_5pct": bool(p_value < 0.05) if np.isfinite(p_value) else None,
        "grs_reject_1pct": bool(p_value < 0.01) if np.isfinite(p_value) else None,
        "grs_alpha_quad_monthly": alpha_quad,
        "grs_active_ir_annualized": float(math.sqrt(max(12.0 * alpha_quad, 0.0))),
        "grs_benchmark_theta2_monthly": theta2,
        "grs_benchmark_tangency_sharpe_annualized": float(math.sqrt(max(12.0 * theta2, 0.0))),
        "grs_rank_design": x_rank,
        "grs_rank_residual_cov": rank_s,
        "grs_rank_factor_cov": rank_omega,
        "grs_cond_residual_cov": cond_s,
        "grs_cond_factor_cov": cond_omega,
    }


def evaluate(candidate_csv: Path, factor_panel_csv: Path, return_col: str, candidate_id: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    cand = pd.read_csv(candidate_csv)
    if "month" not in cand.columns:
        raise ValueError(f"{candidate_csv} is missing required month column")
    if return_col not in cand.columns:
        raise ValueError(f"{candidate_csv} is missing return column {return_col}")
    cand = cand[["month", return_col]].rename(columns={return_col: "candidate_return"})
    cand["month"] = pd.to_datetime(cand["month"], errors="coerce") + pd.offsets.MonthEnd(0)
    cand["candidate_return"] = pd.to_numeric(cand["candidate_return"], errors="coerce")

    factors = pd.read_csv(factor_panel_csv)
    factors["month"] = pd.to_datetime(factors["month"], errors="coerce") + pd.offsets.MonthEnd(0)
    needed = sorted({c for cols in BENCHMARKS.values() for c in cols})
    missing = [c for c in needed if c not in factors.columns]
    if missing:
        raise ValueError("factor panel missing columns: " + ", ".join(missing))

    merged_raw = cand.merge(factors[["month", *needed]], on="month", how="inner")
    merged_raw = merged_raw.replace([np.inf, -np.inf], np.nan).dropna(subset=["candidate_return"])
    if merged_raw.empty:
        raise ValueError("No candidate/factor overlap")

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
            "factor_source": "jkp_usa_topn_long_short_from_read_only_inputs",
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
        grs = single_asset_grs(reg, factor_cols)
        rows.append({
            **base,
            "status": "ok",
            "alpha_monthly": alpha,
            "alpha_annualized": 12.0 * alpha,
            "alpha_tstat_hac": float(alpha / se_alpha) if se_alpha and np.isfinite(se_alpha) else float("nan"),
            "residual_monthly_volatility": resid_vol,
            "appraisal_ratio": appraisal,
            "information_ratio": appraisal,
            "appraisal_ratio_squared": appraisal_sq,
            "information_ratio_squared": appraisal_sq,
            "old_benchmark_set_annualized_sharpe": old_sr,
            "new_combined_annualized_sharpe": new_combined,
            "combined_minus_old_sharpe": new_combined - old_sr if np.isfinite(new_combined) and np.isfinite(old_sr) else float("nan"),
            "r_squared": 1.0 - resid_ss / total_ss if total_ss > 0 else float("nan"),
            "correlation_to_fitted_benchmark": float(np.corrcoef(y, fitted)[0, 1]) if np.std(y, ddof=1) > 0 and np.std(fitted, ddof=1) > 0 else float("nan"),
            **grs,
            **{f"beta_{name}": float(beta_map.get(name, np.nan)) for name in factor_cols},
        })
    metadata = {
        "candidate_id": candidate_id,
        "candidate_csv": str(candidate_csv),
        "factor_panel_csv": str(factor_panel_csv),
        "return_col": return_col,
        "target_annual_volatility": TARGET_ANNUAL_VOLATILITY,
        "benchmarks": {k: list(v) for k, v in BENCHMARKS.items()},
        "input_policy": "candidate and benchmark returns built only from read-only JKP/return_data_assembly inputs",
    }
    return pd.DataFrame(rows), scaled[["month", "candidate_return"]].copy(), metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-csv", required=True, type=Path)
    parser.add_argument("--factor-panel-csv", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--return-col", default="candidate_return")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    metrics, scaled_returns, metadata = evaluate(args.candidate_csv, args.factor_panel_csv, args.return_col, args.candidate_id)
    metrics.to_csv(args.out_dir / "jkp_ff_benchmark_metrics.csv", index=False)
    scaled_returns.to_csv(args.out_dir / "candidate_returns_scaled_7pct.csv", index=False)
    (args.out_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
