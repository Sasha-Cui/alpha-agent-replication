#!/usr/bin/env python3
"""Evaluate repository-derived candidates against a configured benchmark panel.

The runner joins JKP-USA proxy candidate returns produced in this repository
with an authorized external benchmark-factor panel. All derived reports and
tables remain inside the repository's configured output directory.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import time
from pathlib import Path
import sys
from typing import Any, Iterable

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from scipy import stats

from alpha_evolve.paths import DEFAULT_FACTOR_PANEL, REPO_ROOT

ANALYSIS_WINDOW_START = pd.Timestamp("1999-07-31")
ANALYSIS_WINDOW_END = pd.Timestamp("2021-12-31")
ANALYSIS_WINDOW_LABEL = "1999-07-31_to_2021-12-31_270m"
TARGET_ANNUAL_VOLATILITY = 0.07
TARGET_VOLATILITY_POLICY = "scale_candidate_and_benchmark_returns_to_7pct_annualized_volatility_on_overlap_sample"
PSEUDOINVERSE_RCOND = 1e-10
MIN_OVERLAP_MONTHS = 24
LONGONLY_MVO_MEANINGFUL_WEIGHT = 0.01

CAPM_FACTOR = "capm_top1000_mkt"
NEWSFACTOR_FACTOR = "newsfactor_top1000_unit_gross"
EXISTING_BOOK_JKP132_FACTOR = "jkp132_top1000_tangency_book"
EXISTING_BOOK_LABEL = "JKP132 + Didisheim/TextBenchmark"
FF5MOM_CHARS = ("be_me", "at_gr1", "market_equity", "ope_be", "ret_12_1")
FF5MOM_COLS = tuple(f"char__{char}" for char in FF5MOM_CHARS)

DEFAULT_ALPHA_ROOT = REPO_ROOT
DEFAULT_CANDIDATE_DIR = DEFAULT_ALPHA_ROOT / "paper_runs/idea_replications/jkp_paper_idea_proxies"
DEFAULT_OUTPUT_DIR = DEFAULT_ALPHA_ROOT / "paper_runs/performance_analysis/textbenchmark"
DEFAULT_REPORT_PATH = DEFAULT_ALPHA_ROOT / "report.md"


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


def target_vol_scale(values: pd.Series | np.ndarray) -> tuple[float, float]:
    ann_vol = annualized_volatility(values)
    if not np.isfinite(ann_vol) or ann_vol <= 0.0:
        return 1.0, ann_vol
    return float(TARGET_ANNUAL_VOLATILITY / ann_vol), ann_vol


def apply_target_volatility(frame: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    out = frame.copy()
    metadata: dict[str, dict[str, float]] = {}
    for col in columns:
        scale, ann_vol_before = target_vol_scale(out[col])
        out[col] = pd.to_numeric(out[col], errors="coerce") * scale
        metadata[col] = {
            "target_vol_scale": float(scale),
            "annualized_volatility_before_target": float(ann_vol_before) if np.isfinite(ann_vol_before) else float("nan"),
            "annualized_volatility_after_target": annualized_volatility(out[col]),
        }
    return out, metadata


def restrict_analysis_window(frame: pd.DataFrame, month_col: str = "month") -> pd.DataFrame:
    out = frame.copy()
    out[month_col] = pd.to_datetime(out[month_col], errors="coerce") + pd.offsets.MonthEnd(0)
    return out[(out[month_col] >= ANALYSIS_WINDOW_START) & (out[month_col] <= ANALYSIS_WINDOW_END)].copy()


def max_tangency_sharpe(frame: pd.DataFrame, factor_cols: list[str]) -> float:
    if not factor_cols:
        return float("nan")
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


def _portfolio_sharpe(returns: np.ndarray, weights: np.ndarray) -> float:
    ret = np.asarray(returns, dtype="float64") @ np.asarray(weights, dtype="float64")
    return annualized_sharpe(ret)


def _longonly_max_sharpe(returns: np.ndarray) -> tuple[np.ndarray, float]:
    arr = np.asarray(returns, dtype="float64")
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    valid = np.isfinite(arr).all(axis=1)
    arr = arr[valid]
    n, k = arr.shape if arr.ndim == 2 else (0, 0)
    nan_weights = np.full(k, np.nan, dtype="float64")
    if n < 2 or k == 0:
        return nan_weights, float("nan")
    if k == 1:
        return np.ones(1, dtype="float64"), annualized_sharpe(arr[:, 0])

    def objective(weights: np.ndarray) -> float:
        sr = _portfolio_sharpe(arr, weights)
        if not np.isfinite(sr):
            return 1e9
        return -float(sr)

    starts = [np.full(k, 1.0 / k, dtype="float64")]
    starts.extend(np.eye(k, dtype="float64"))
    means = np.mean(arr, axis=0)
    positive_means = np.clip(means, 0.0, None)
    if float(positive_means.sum()) > 0:
        starts.append(positive_means / float(positive_means.sum()))

    candidates: list[tuple[np.ndarray, float]] = []
    for start in starts:
        sr = _portfolio_sharpe(arr, start)
        if np.isfinite(sr):
            candidates.append((start, sr))

    try:
        from scipy.optimize import minimize

        constraints = [{"type": "eq", "fun": lambda weights: float(np.sum(weights) - 1.0)}]
        bounds = [(0.0, 1.0)] * k
        for start in starts:
            result = minimize(
                objective,
                start,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 300, "ftol": 1e-12, "disp": False},
            )
            if result.success and np.isfinite(result.fun):
                weights = np.clip(np.asarray(result.x, dtype="float64"), 0.0, 1.0)
                total = float(weights.sum())
                if total > 0:
                    weights /= total
                    sr = _portfolio_sharpe(arr, weights)
                    if np.isfinite(sr):
                        candidates.append((weights, sr))
    except Exception:
        pass

    if not candidates:
        return nan_weights, float("nan")
    weights, sr = max(candidates, key=lambda item: item[1])
    return np.asarray(weights, dtype="float64"), float(sr)


def _msrr_weights(returns: np.ndarray) -> np.ndarray:
    x = np.asarray(returns, dtype="float64")
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    valid = np.isfinite(x).all(axis=1)
    x = x[valid]
    n, k = x.shape if x.ndim == 2 else (0, 0)
    nan = np.full(k, np.nan, dtype="float64")
    if n <= k or k == 0:
        return nan
    y = np.ones(n, dtype="float64")
    xtx_inv = np.linalg.pinv(x.T @ x, rcond=PSEUDOINVERSE_RCOND)
    return xtx_inv @ x.T @ y


def _unconstrained_tangency_weights(returns: np.ndarray) -> np.ndarray:
    arr = np.asarray(returns, dtype="float64")
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    valid = np.isfinite(arr).all(axis=1)
    arr = arr[valid]
    n, k = arr.shape if arr.ndim == 2 else (0, 0)
    if n < 2 or k == 0:
        return np.full(k, np.nan, dtype="float64")
    mu = np.mean(arr, axis=0)
    cov = np.cov(arr, rowvar=False, ddof=1)
    if cov.ndim == 0:
        cov = np.asarray([[float(cov)]], dtype="float64")
    weights = np.linalg.pinv(cov, rcond=PSEUDOINVERSE_RCOND) @ mu
    if not np.isfinite(weights).all():
        return np.full(k, np.nan, dtype="float64")
    gross = float(np.sum(np.abs(weights)))
    if not np.isfinite(gross) or gross <= 0.0:
        return np.full(k, np.nan, dtype="float64")
    return np.asarray(weights / gross, dtype="float64")


def _jkp132_book_returns(frame: pd.DataFrame, jkp_cols: list[str]) -> tuple[pd.Series, dict[str, Any]]:
    weights = _unconstrained_tangency_weights(frame[jkp_cols].to_numpy(dtype="float64"))
    if weights.size != len(jkp_cols) or not np.isfinite(weights).all():
        return pd.Series(np.nan, index=frame.index, dtype="float64"), {
            "existing_book_jkp132_factor_count": len(jkp_cols),
            "existing_book_jkp132_gross_weight": float("nan"),
            "existing_book_jkp132_construction": "unconstrained_tangency_from_jkp132_factor_span_failed",
        }
    returns = frame[jkp_cols].to_numpy(dtype="float64") @ weights
    return pd.Series(returns, index=frame.index, dtype="float64"), {
        "existing_book_jkp132_factor_count": len(jkp_cols),
        "existing_book_jkp132_gross_weight": float(np.sum(np.abs(weights))),
        "existing_book_jkp132_construction": "unconstrained_tangency_from_jkp132_factor_span_on_overlap_sample",
    }


def textbenchmark_delta_mvo_metrics(
    candidate: pd.DataFrame,
    factors: pd.DataFrame,
    *,
    candidate_return_col: str,
    jkp_cols: list[str],
) -> dict[str, Any]:
    nan_fields: dict[str, Any] = {
        "existing_book_label": EXISTING_BOOK_LABEL,
        "existing_book_component_count": 2,
        "existing_book_components": "JKP132,TextBenchmark",
        "existing_book_jkp132_factor_count": len(jkp_cols),
        "existing_book_jkp132_gross_weight": float("nan"),
        "existing_book_jkp132_construction": "unconstrained_tangency_from_jkp132_factor_span_on_overlap_sample",
        "candidate_standalone_oos_sharpe": float("nan"),
        "jkp132_standalone_oos_sharpe": float("nan"),
        "textbenchmark_standalone_oos_sharpe": float("nan"),
        "existing_book_standalone_oos_sharpe": float("nan"),
        "textbenchmark_delta_mvo_n_months": 0,
        "textbenchmark_delta_mvo_overlap_start": None,
        "textbenchmark_delta_mvo_overlap_end": None,
        "longonly_original_mvo_jkp132_weight": float("nan"),
        "longonly_original_mvo_textbenchmark_weight": float("nan"),
        "longonly_original_mvo_candidate_weight": float("nan"),
        "longonly_original_mvo_annualized_sharpe": float("nan"),
        "longonly_all_mvo_jkp132_weight": float("nan"),
        "longonly_all_mvo_textbenchmark_weight": float("nan"),
        "longonly_all_mvo_candidate_weight": float("nan"),
        "longonly_delta_mvo_candidate_weight": float("nan"),
        "longonly_delta_mvo_candidate_weight_meaningful": None,
        "longonly_all_mvo_annualized_sharpe": float("nan"),
        "longonly_delta_sharpe": float("nan"),
        "msrr_original_jkp132_weight_raw": float("nan"),
        "msrr_original_textbenchmark_weight_raw": float("nan"),
        "msrr_all_jkp132_weight_raw": float("nan"),
        "msrr_all_textbenchmark_weight_raw": float("nan"),
        "msrr_all_candidate_weight_raw": float("nan"),
    }
    required_factor_cols = [NEWSFACTOR_FACTOR, *jkp_cols]
    if any(col not in factors.columns for col in required_factor_cols):
        return nan_fields

    merged = candidate[["month", candidate_return_col]].merge(
        factors[["month", *required_factor_cols]], on="month", how="inner"
    )
    merged = merged.rename(columns={candidate_return_col: "candidate_return"})
    merged = merged.replace([np.inf, -np.inf], np.nan).dropna(subset=["candidate_return", *required_factor_cols]).sort_values("month")
    merged = restrict_analysis_window(merged)
    n = int(len(merged))
    base = {
        "existing_book_label": EXISTING_BOOK_LABEL,
        "existing_book_component_count": 2,
        "existing_book_components": "JKP132,TextBenchmark",
        "textbenchmark_delta_mvo_n_months": n,
        "textbenchmark_delta_mvo_overlap_start": str(merged["month"].min().date()) if n else None,
        "textbenchmark_delta_mvo_overlap_end": str(merged["month"].max().date()) if n else None,
        "analysis_window_start": str(ANALYSIS_WINDOW_START.date()),
        "analysis_window_end": str(ANALYSIS_WINDOW_END.date()),
        "analysis_window_label": ANALYSIS_WINDOW_LABEL,
    }
    if n < MIN_OVERLAP_MONTHS:
        return {**nan_fields, **base}

    scaled_jkp, _ = apply_target_volatility(merged[["month", *jkp_cols]], jkp_cols)
    jkp132_book, jkp_meta = _jkp132_book_returns(scaled_jkp, jkp_cols)
    book_frame = merged[["month", "candidate_return", NEWSFACTOR_FACTOR]].copy()
    book_frame[EXISTING_BOOK_JKP132_FACTOR] = jkp132_book.to_numpy(dtype="float64")
    book_frame = book_frame.dropna(subset=["candidate_return", NEWSFACTOR_FACTOR, EXISTING_BOOK_JKP132_FACTOR]).sort_values("month")
    n = int(len(book_frame))
    base = {
        **base,
        **jkp_meta,
        "textbenchmark_delta_mvo_n_months": n,
        "textbenchmark_delta_mvo_overlap_start": str(book_frame["month"].min().date()) if n else None,
        "textbenchmark_delta_mvo_overlap_end": str(book_frame["month"].max().date()) if n else None,
    }
    if n < MIN_OVERLAP_MONTHS:
        return {**nan_fields, **base}

    book_scaled, _ = apply_target_volatility(book_frame, ["candidate_return", NEWSFACTOR_FACTOR, EXISTING_BOOK_JKP132_FACTOR])
    candidate_sr = annualized_sharpe(book_scaled["candidate_return"])
    jkp132_sr = annualized_sharpe(book_scaled[EXISTING_BOOK_JKP132_FACTOR])
    textbenchmark_sr = annualized_sharpe(book_scaled[NEWSFACTOR_FACTOR])
    original_assets = book_scaled[[EXISTING_BOOK_JKP132_FACTOR, NEWSFACTOR_FACTOR]].to_numpy(dtype="float64")
    expanded_assets = book_scaled[[EXISTING_BOOK_JKP132_FACTOR, NEWSFACTOR_FACTOR, "candidate_return"]].to_numpy(dtype="float64")
    original_weights, original_sr = _longonly_max_sharpe(original_assets)
    all_weights, all_sr = _longonly_max_sharpe(expanded_assets)
    original_beta = _msrr_weights(original_assets)
    all_beta = _msrr_weights(expanded_assets)
    jkp_original_weight = float(original_weights[0]) if original_weights.size >= 2 else float("nan")
    text_original_weight = float(original_weights[1]) if original_weights.size >= 2 else float("nan")
    jkp_all_weight = float(all_weights[0]) if all_weights.size >= 3 else float("nan")
    text_all_weight = float(all_weights[1]) if all_weights.size >= 3 else float("nan")
    candidate_weight = float(all_weights[2]) if all_weights.size >= 3 else float("nan")
    meaningful = bool(candidate_weight >= LONGONLY_MVO_MEANINGFUL_WEIGHT) if np.isfinite(candidate_weight) else None

    return {
        **nan_fields,
        **base,
        "candidate_standalone_oos_sharpe": candidate_sr,
        "jkp132_standalone_oos_sharpe": jkp132_sr,
        "textbenchmark_standalone_oos_sharpe": textbenchmark_sr,
        "existing_book_standalone_oos_sharpe": original_sr,
        "longonly_original_mvo_jkp132_weight": jkp_original_weight,
        "longonly_original_mvo_textbenchmark_weight": text_original_weight,
        "longonly_original_mvo_candidate_weight": 0.0,
        "longonly_original_mvo_annualized_sharpe": original_sr,
        "longonly_all_mvo_jkp132_weight": jkp_all_weight,
        "longonly_all_mvo_textbenchmark_weight": text_all_weight,
        "longonly_all_mvo_candidate_weight": candidate_weight,
        "longonly_delta_mvo_candidate_weight": candidate_weight,
        "longonly_delta_mvo_candidate_weight_meaningful": meaningful,
        "longonly_all_mvo_annualized_sharpe": all_sr,
        "longonly_delta_sharpe": all_sr - original_sr if np.isfinite(all_sr) and np.isfinite(original_sr) else float("nan"),
        "msrr_original_jkp132_weight_raw": float(original_beta[0]) if original_beta.size >= 2 else float("nan"),
        "msrr_original_textbenchmark_weight_raw": float(original_beta[1]) if original_beta.size >= 2 else float("nan"),
        "msrr_all_jkp132_weight_raw": float(all_beta[0]) if all_beta.size >= 3 else float("nan"),
        "msrr_all_textbenchmark_weight_raw": float(all_beta[1]) if all_beta.size >= 3 else float("nan"),
        "msrr_all_candidate_weight_raw": float(all_beta[2]) if all_beta.size >= 3 else float("nan"),
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


def single_asset_grs(reg: pd.DataFrame, factor_cols: list[str]) -> dict[str, Any]:
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


def beta_block_summary(beta_map: dict[str, float], cols: Iterable[str], prefix: str) -> dict[str, float]:
    values = np.asarray([float(beta_map.get(col, np.nan)) for col in cols], dtype="float64")
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {
            f"beta_{prefix}_signed_mean": float("nan"),
            f"beta_{prefix}_abs_mean": float("nan"),
            f"beta_{prefix}_rms": float("nan"),
            f"beta_{prefix}_max_abs": float("nan"),
        }
    return {
        f"beta_{prefix}_signed_mean": float(np.mean(values)),
        f"beta_{prefix}_abs_mean": float(np.mean(np.abs(values))),
        f"beta_{prefix}_rms": float(math.sqrt(float(np.mean(values**2)))),
        f"beta_{prefix}_max_abs": float(np.max(np.abs(values))),
    }


def multifactor_value_add(
    candidate: pd.DataFrame,
    factors: pd.DataFrame,
    *,
    candidate_id: str,
    candidate_return_col: str,
    benchmark_label: str,
    factor_cols: list[str],
    jkp_cols: list[str],
    book_metrics: dict[str, Any],
) -> dict[str, Any]:
    cols = ["month", *factor_cols]
    merged = candidate[["month", candidate_return_col]].merge(factors[cols], on="month", how="inner")
    merged = merged.rename(columns={candidate_return_col: "candidate_return"})
    merged = merged.replace([np.inf, -np.inf], np.nan).dropna(subset=["candidate_return", *factor_cols]).sort_values("month")
    merged = restrict_analysis_window(merged)
    n = int(len(merged))
    base: dict[str, Any] = {
        "candidate_id": candidate_id,
        "benchmark_set": benchmark_label,
        "n_benchmark_factors": int(len(factor_cols)),
        "benchmark_factors": ",".join(factor_cols),
        "n_overlap_months": n,
        "overlap_start": str(merged["month"].min().date()) if n else None,
        "overlap_end": str(merged["month"].max().date()) if n else None,
        "target_annual_volatility": TARGET_ANNUAL_VOLATILITY,
        "return_scaling_policy": TARGET_VOLATILITY_POLICY,
        "analysis_window_start": str(ANALYSIS_WINDOW_START.date()),
        "analysis_window_end": str(ANALYSIS_WINDOW_END.date()),
        "analysis_window_label": ANALYSIS_WINDOW_LABEL,
    }
    nan_fields = {
        "status": "insufficient_overlap",
        "old_benchmark_set_annualized_sharpe": float("nan"),
        "new_combined_annualized_sharpe": float("nan"),
        "combined_minus_old_sharpe": float("nan"),
        "alpha_monthly": float("nan"),
        "alpha_annualized": float("nan"),
        "alpha_tstat_hac": float("nan"),
        "residual_monthly_volatility": float("nan"),
        "appraisal_ratio": float("nan"),
        "information_ratio": float("nan"),
        "appraisal_ratio_squared": float("nan"),
        "information_ratio_squared": float("nan"),
        "r_squared": float("nan"),
        "correlation_to_fitted_benchmark": float("nan"),
        "beta_capm_top1000_mkt": float("nan"),
        "beta_ff5mom_signed_mean": float("nan"),
        "beta_ff5mom_abs_mean": float("nan"),
        "beta_ff5mom_rms": float("nan"),
        "beta_ff5mom_max_abs": float("nan"),
        "beta_jkp132_signed_mean": float("nan"),
        "beta_jkp132_abs_mean": float("nan"),
        "beta_jkp132_rms": float("nan"),
        "beta_jkp132_max_abs": float("nan"),
        "beta_newsfactor_top1000_unit_gross": float("nan"),
        "candidate_target_vol_scale": float("nan"),
        "candidate_annualized_volatility_before_target": float("nan"),
        "candidate_annualized_volatility_after_target": float("nan"),
        "grs_f": float("nan"),
        "grs_p_value": float("nan"),
        "grs_reject_5pct": None,
        "grs_reject_1pct": None,
    }
    if n < MIN_OVERLAP_MONTHS or n <= len(factor_cols) + 2:
        return {**base, **nan_fields, **book_metrics}

    merged, target_meta = apply_target_volatility(merged, ["candidate_return", *factor_cols])
    candidate_target = target_meta.get("candidate_return", {})
    y = merged["candidate_return"].to_numpy(dtype="float64")
    x = np.column_stack([np.ones(n, dtype="float64"), merged[factor_cols].to_numpy(dtype="float64")])
    xtx_inv = np.linalg.pinv(x.T @ x, rcond=PSEUDOINVERSE_RCOND)
    x_pinv = xtx_inv @ x.T
    coef = x_pinv @ y
    fitted = x @ coef
    resid = y - fitted
    alpha = float(coef[0])
    resid_vol = float(np.std(resid, ddof=1))
    se_alpha = newey_west_intercept_se(x, resid, xtx_inv)
    appraisal = float(math.sqrt(12.0) * alpha / resid_vol) if resid_vol and np.isfinite(resid_vol) else float("nan")
    appraisal_sq = appraisal**2 if np.isfinite(appraisal) else float("nan")
    old_sr = max_tangency_sharpe(merged, factor_cols)
    new_combined = float(math.sqrt(old_sr**2 + appraisal_sq)) if np.isfinite(old_sr) and np.isfinite(appraisal_sq) else float("nan")
    total_ss = float(np.sum((y - np.mean(y)) ** 2))
    resid_ss = float(np.sum(resid**2))
    r2 = 1.0 - resid_ss / total_ss if total_ss > 0 else float("nan")
    corr = float(np.corrcoef(y, fitted)[0, 1]) if np.std(y, ddof=1) > 0 and np.std(fitted, ddof=1) > 0 else float("nan")
    beta_map = dict(zip(factor_cols, coef[1:]))
    grs = single_asset_grs(merged[["month", "candidate_return", *factor_cols]], factor_cols)

    return {
        **base,
        "status": "ok",
        "old_benchmark_set_annualized_sharpe": old_sr,
        "new_combined_annualized_sharpe": new_combined,
        "combined_minus_old_sharpe": new_combined - old_sr if np.isfinite(new_combined) and np.isfinite(old_sr) else float("nan"),
        "alpha_monthly": alpha,
        "alpha_annualized": 12.0 * alpha,
        "alpha_tstat_hac": float(alpha / se_alpha) if se_alpha and np.isfinite(se_alpha) else float("nan"),
        "residual_monthly_volatility": resid_vol,
        "appraisal_ratio": appraisal,
        "information_ratio": appraisal,
        "appraisal_ratio_squared": appraisal_sq,
        "information_ratio_squared": appraisal_sq,
        "r_squared": float(r2),
        "correlation_to_fitted_benchmark": corr,
        "beta_capm_top1000_mkt": float(beta_map.get(CAPM_FACTOR, np.nan)),
        **beta_block_summary(beta_map, FF5MOM_COLS, "ff5mom"),
        **beta_block_summary(beta_map, jkp_cols, "jkp132"),
        "beta_newsfactor_top1000_unit_gross": float(beta_map.get(NEWSFACTOR_FACTOR, np.nan)),
        "candidate_target_vol_scale": candidate_target.get("target_vol_scale", float("nan")),
        "candidate_annualized_volatility_before_target": candidate_target.get("annualized_volatility_before_target", float("nan")),
        "candidate_annualized_volatility_after_target": candidate_target.get("annualized_volatility_after_target", float("nan")),
        **grs,
        **book_metrics,
    }


def load_factor_panel(path: Path) -> tuple[pd.DataFrame, list[str], dict[str, list[str]]]:
    factors = pd.read_csv(path)
    factors["month"] = pd.to_datetime(factors["month"], errors="coerce") + pd.offsets.MonthEnd(0)
    factors = restrict_analysis_window(factors)
    jkp_cols = [col for col in factors.columns if col.startswith("char__")]
    required = [CAPM_FACTOR, NEWSFACTOR_FACTOR, *FF5MOM_COLS, *jkp_cols]
    missing = [col for col in required if col not in factors.columns]
    if missing:
        raise ValueError(f"Factor panel missing required columns: {missing[:20]}")
    benchmark_sets = {
        "TEXTBENCHMARK": [NEWSFACTOR_FACTOR],
        "CAPM_FF5MOM_TEXTBENCHMARK": [CAPM_FACTOR, *FF5MOM_COLS, NEWSFACTOR_FACTOR],
        "CAPM_FF5MOM_JKP132_TEXTBENCHMARK": [CAPM_FACTOR, *jkp_cols, NEWSFACTOR_FACTOR],
    }
    for label, cols in list(benchmark_sets.items()):
        seen: set[str] = set()
        benchmark_sets[label] = [col for col in cols if not (col in seen or seen.add(col))]
    return factors, jkp_cols, benchmark_sets


def read_candidate(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "month" not in frame.columns or "candidate_return" not in frame.columns:
        raise ValueError(f"{path} must contain month and candidate_return")
    frame = frame[["month", "candidate_return"]].copy()
    frame["month"] = pd.to_datetime(frame["month"], errors="coerce") + pd.offsets.MonthEnd(0)
    frame["candidate_return"] = pd.to_numeric(frame["candidate_return"], errors="coerce")
    return frame.dropna(subset=["month"]).sort_values("month")


def candidate_id_from_path(path: Path) -> str:
    name = path.stem
    prefix = "candidate_returns_"
    if name.startswith(prefix):
        return name[len(prefix) :]
    return name


def load_metadata(candidate_dir: Path) -> pd.DataFrame:
    path = candidate_dir / "paper_idea_proxy_ff5mom_summary.csv"
    if not path.exists():
        return pd.DataFrame(columns=["candidate_id"])
    meta = pd.read_csv(path)
    keep = [
        "candidate_id",
        "paper_ref",
        "paper_idea",
        "proxy_formula",
        "strategy",
        "beats_ff5mom_positive_alpha_5pct",
        "alpha_tstat_hac",
        "appraisal_ratio",
        "alpha_annualized",
        "grs_f",
        "grs_p_value",
        "combined_minus_old_sharpe",
    ]
    keep = [col for col in keep if col in meta.columns]
    meta = meta[keep].copy()
    rename = {
        "alpha_tstat_hac": "ff5mom_alpha_tstat_hac",
        "appraisal_ratio": "ff5mom_appraisal_ratio",
        "alpha_annualized": "ff5mom_alpha_annualized",
        "grs_f": "ff5mom_grs_f",
        "grs_p_value": "ff5mom_grs_p_value",
        "combined_minus_old_sharpe": "ff5mom_combined_minus_old_sharpe",
    }
    return meta.rename(columns={k: v for k, v in rename.items() if k in meta.columns})


def value_from_row(frame: pd.DataFrame, candidate_id: str, benchmark: str, column: str) -> Any:
    row = frame[(frame["candidate_id"].eq(candidate_id)) & (frame["benchmark_set"].eq(benchmark))]
    if row.empty or column not in row.columns:
        return np.nan
    return row.iloc[0][column]


def make_summary(metrics: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    candidate_ids = sorted(metrics["candidate_id"].dropna().unique())
    rows: list[dict[str, Any]] = []
    for candidate_id in candidate_ids:
        text_alpha = value_from_row(metrics, candidate_id, "TEXTBENCHMARK", "alpha_annualized")
        text_t = value_from_row(metrics, candidate_id, "TEXTBENCHMARK", "alpha_tstat_hac")
        text_ir = value_from_row(metrics, candidate_id, "TEXTBENCHMARK", "information_ratio")
        text_lift = value_from_row(metrics, candidate_id, "TEXTBENCHMARK", "combined_minus_old_sharpe")
        text_grs_f = value_from_row(metrics, candidate_id, "TEXTBENCHMARK", "grs_f")
        text_grs_p = value_from_row(metrics, candidate_id, "TEXTBENCHMARK", "grs_p_value")
        text_grs_reject = value_from_row(metrics, candidate_id, "TEXTBENCHMARK", "grs_reject_5pct")

        full_alpha = value_from_row(metrics, candidate_id, "CAPM_FF5MOM_JKP132_TEXTBENCHMARK", "alpha_annualized")
        full_t = value_from_row(metrics, candidate_id, "CAPM_FF5MOM_JKP132_TEXTBENCHMARK", "alpha_tstat_hac")
        full_ir = value_from_row(metrics, candidate_id, "CAPM_FF5MOM_JKP132_TEXTBENCHMARK", "information_ratio")
        full_lift = value_from_row(metrics, candidate_id, "CAPM_FF5MOM_JKP132_TEXTBENCHMARK", "combined_minus_old_sharpe")
        full_grs_f = value_from_row(metrics, candidate_id, "CAPM_FF5MOM_JKP132_TEXTBENCHMARK", "grs_f")
        full_grs_p = value_from_row(metrics, candidate_id, "CAPM_FF5MOM_JKP132_TEXTBENCHMARK", "grs_p_value")
        full_grs_reject = value_from_row(metrics, candidate_id, "CAPM_FF5MOM_JKP132_TEXTBENCHMARK", "grs_reject_5pct")

        row0 = metrics[metrics["candidate_id"].eq(candidate_id)].iloc[0]
        candidate_weight = row0.get("longonly_all_mvo_candidate_weight", np.nan)
        delta_sharpe = row0.get("longonly_delta_sharpe", np.nan)
        rows.append({
            "candidate_id": candidate_id,
            "candidate_standalone_oos_sharpe": row0.get("candidate_standalone_oos_sharpe", np.nan),
            "textbenchmark_alpha_annualized": text_alpha,
            "textbenchmark_alpha_tstat_hac": text_t,
            "textbenchmark_information_ratio": text_ir,
            "textbenchmark_grs_f": text_grs_f,
            "textbenchmark_grs_p_value": text_grs_p,
            "textbenchmark_grs_reject_5pct": text_grs_reject,
            "textbenchmark_combined_minus_old_sharpe": text_lift,
            "full_alpha_annualized": full_alpha,
            "full_alpha_tstat_hac": full_t,
            "full_information_ratio": full_ir,
            "full_grs_f": full_grs_f,
            "full_grs_p_value": full_grs_p,
            "full_grs_reject_5pct": full_grs_reject,
            "full_combined_minus_old_sharpe": full_lift,
            "jkp132_standalone_oos_sharpe": row0.get("jkp132_standalone_oos_sharpe", np.nan),
            "textbenchmark_standalone_oos_sharpe": row0.get("textbenchmark_standalone_oos_sharpe", np.nan),
            "existing_book_standalone_oos_sharpe": row0.get("existing_book_standalone_oos_sharpe", np.nan),
            "longonly_original_mvo_jkp132_weight": row0.get("longonly_original_mvo_jkp132_weight", np.nan),
            "longonly_original_mvo_textbenchmark_weight": row0.get("longonly_original_mvo_textbenchmark_weight", np.nan),
            "longonly_original_mvo_annualized_sharpe": row0.get("longonly_original_mvo_annualized_sharpe", np.nan),
            "longonly_all_mvo_jkp132_weight": row0.get("longonly_all_mvo_jkp132_weight", np.nan),
            "longonly_all_mvo_textbenchmark_weight": row0.get("longonly_all_mvo_textbenchmark_weight", np.nan),
            "longonly_all_mvo_candidate_weight": candidate_weight,
            "longonly_all_mvo_annualized_sharpe": row0.get("longonly_all_mvo_annualized_sharpe", np.nan),
            "longonly_delta_sharpe": delta_sharpe,
            "beats_textbenchmark_positive_alpha_5pct": (
                pd.notna(text_alpha)
                and pd.notna(text_t)
                and pd.notna(text_ir)
                and pd.notna(text_lift)
                and text_alpha > 0
                and text_t > 1.96
                and text_ir > 0
                and text_lift > 0
                and bool(text_grs_reject) is True
            ),
            "survives_full_jkp132_textbenchmark_positive_alpha_5pct": (
                pd.notna(full_alpha)
                and pd.notna(full_t)
                and pd.notna(full_ir)
                and pd.notna(full_lift)
                and full_alpha > 0
                and full_t > 1.96
                and full_ir > 0
                and full_lift > 0
                and bool(full_grs_reject) is True
            ),
            "adds_to_jkp132_textbenchmark_longonly_book": (
                pd.notna(delta_sharpe)
                and pd.notna(candidate_weight)
                and delta_sharpe > 0
                and candidate_weight >= LONGONLY_MVO_MEANINGFUL_WEIGHT
            ),
            "adds_to_jkp132_textbenchmark_strict": (
                pd.notna(full_alpha)
                and pd.notna(full_t)
                and pd.notna(full_ir)
                and pd.notna(full_lift)
                and pd.notna(delta_sharpe)
                and pd.notna(candidate_weight)
                and full_alpha > 0
                and full_t > 1.96
                and full_ir > 0
                and full_lift > 0
                and bool(full_grs_reject) is True
                and delta_sharpe > 0
                and candidate_weight >= LONGONLY_MVO_MEANINGFUL_WEIGHT
            ),
        })
    summary = pd.DataFrame(rows)
    if not metadata.empty:
        summary = summary.merge(metadata, on="candidate_id", how="left")
    sort_cols = [col for col in ["adds_to_jkp132_textbenchmark_strict", "full_alpha_tstat_hac", "longonly_delta_sharpe"] if col in summary.columns]
    if sort_cols:
        summary = summary.sort_values(sort_cols, ascending=[False] + [False] * (len(sort_cols) - 1)).reset_index(drop=True)
    return summary


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if pd.isna(value):
        return None
    return value


def fmt_float(value: Any, digits: int = 3, percent: bool = False) -> str:
    try:
        val = float(value)
    except Exception:
        return ""
    if not np.isfinite(val):
        return ""
    if percent:
        return f"{100.0 * val:.{digits}f}%"
    return f"{val:.{digits}f}"


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
    if frame.empty:
        return "_No rows._"
    show = frame.loc[:, [col for col in columns if col in frame.columns]].head(max_rows).copy()
    for col in show.columns:
        if pd.api.types.is_float_dtype(show[col]):
            if "alpha_annualized" in col:
                show[col] = show[col].map(lambda x: fmt_float(x, 2, percent=True))
            else:
                show[col] = show[col].map(lambda x: fmt_float(x, 3))
    headers = list(show.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in show.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
    return "\n".join(lines)


def render_report(summary: pd.DataFrame, metrics: pd.DataFrame, metadata: dict[str, Any], output_dir: Path) -> str:
    n_candidates = int(len(summary))
    text_sig = int(summary["beats_textbenchmark_positive_alpha_5pct"].sum()) if "beats_textbenchmark_positive_alpha_5pct" in summary else 0
    full_sig = int(summary["survives_full_jkp132_textbenchmark_positive_alpha_5pct"].sum()) if "survives_full_jkp132_textbenchmark_positive_alpha_5pct" in summary else 0
    book_add = int(summary["adds_to_jkp132_textbenchmark_longonly_book"].sum()) if "adds_to_jkp132_textbenchmark_longonly_book" in summary else 0
    strict = int(summary["adds_to_jkp132_textbenchmark_strict"].sum()) if "adds_to_jkp132_textbenchmark_strict" in summary else 0
    positive_delta = int((pd.to_numeric(summary["longonly_delta_sharpe"], errors="coerce") > 0).sum()) if "longonly_delta_sharpe" in summary else 0

    top_text = summary.sort_values("textbenchmark_alpha_tstat_hac", ascending=False)
    top_full = summary.sort_values("full_alpha_tstat_hac", ascending=False)
    top_book = summary.sort_values("longonly_delta_sharpe", ascending=False)

    report = f"""# TextBenchmark Performance Analysis

Generated: `{pd.Timestamp.utcnow().isoformat()}`

## Scope

- Candidate set: `{n_candidates}` alpha_evolve JKP-USA in-spirit paper proxies from `{metadata["candidate_dir"]}`.
- Benchmark factor panel: `{metadata["factor_panel"]}`.
- TextBenchmark column: `{NEWSFACTOR_FACTOR}`.
- Fixed analysis window: `{ANALYSIS_WINDOW_LABEL}`.
- Scaling: all candidate and benchmark return streams are scaled to `{TARGET_ANNUAL_VOLATILITY:.0%}` annualized volatility on the overlap sample before alpha/appraisal/GRS and MVO diagnostics.
- Existing book diagnostic: long-only max-Sharpe allocation over `JKP132 + TextBenchmark`, then over `JKP132 + TextBenchmark + candidate`.
- Input boundary: candidate returns are repository-derived; benchmark returns come from the configured external benchmark-factor panel.

## Headline Counts

| Test | Count |
| --- | ---: |
| Candidates evaluated | {n_candidates} |
| Positive/significant alpha vs TextBenchmark alone | {text_sig} |
| Positive/significant alpha vs CAPM + JKP132 + TextBenchmark | {full_sig} |
| Positive long-only delta Sharpe vs JKP132 + TextBenchmark | {positive_delta} |
| Positive long-only delta and candidate weight >= {LONGONLY_MVO_MEANINGFUL_WEIGHT:.0%} | {book_add} |
| Strict additive to JKP132 + TextBenchmark book | {strict} |

## Top Alpha Versus TextBenchmark Alone

{markdown_table(top_text, [
    "candidate_id",
    "textbenchmark_alpha_annualized",
    "textbenchmark_alpha_tstat_hac",
    "textbenchmark_information_ratio",
    "textbenchmark_grs_f",
    "textbenchmark_grs_p_value",
    "textbenchmark_combined_minus_old_sharpe",
], max_rows=15)}

## Top Alpha Versus CAPM + JKP132 + TextBenchmark

{markdown_table(top_full, [
    "candidate_id",
    "full_alpha_annualized",
    "full_alpha_tstat_hac",
    "full_information_ratio",
    "full_grs_f",
    "full_grs_p_value",
    "full_combined_minus_old_sharpe",
], max_rows=15)}

## Top Book Delta Versus JKP132 + TextBenchmark

{markdown_table(top_book, [
    "candidate_id",
    "longonly_delta_sharpe",
    "longonly_all_mvo_candidate_weight",
    "longonly_original_mvo_annualized_sharpe",
    "longonly_all_mvo_annualized_sharpe",
    "full_alpha_tstat_hac",
    "full_information_ratio",
], max_rows=15)}

## Output Files

- `{output_dir / "alpha_evolve_textbenchmark_candidate_summary.csv"}`
- `{output_dir / "alpha_evolve_textbenchmark_benchmark_metrics.csv"}`
- `{output_dir / "alpha_evolve_textbenchmark_book_delta_mvo.csv"}`
- `{output_dir / "run_metadata.json"}`

## Interpretation

The TextBenchmark-only test answers whether a candidate is different from the NewsFactor/TextBenchmark sleeve. The full-span and long-only book tests are the stricter tests: they ask whether the candidate still adds anything after the JKP132 factor book and TextBenchmark are already in the book.
"""
    return report


def update_main_report(report_path: Path, section: str) -> None:
    if not report_path.exists():
        return
    start = "<!-- TEXTBENCHMARK_PERFORMANCE_ANALYSIS_START -->"
    end = "<!-- TEXTBENCHMARK_PERFORMANCE_ANALYSIS_END -->"
    block = f"{start}\n{section.strip()}\n{end}\n"
    text = report_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"{re.escape(start)}.*?{re.escape(end)}\n?", re.S)
    if pattern.search(text):
        text = pattern.sub(block, text)
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += "\n" + block
    report_path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE_DIR)
    parser.add_argument("--factor-panel", type=Path, default=DEFAULT_FACTOR_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--skip-main-report-update", action="store_true")
    args = parser.parse_args(argv)

    started = time.time()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    factors, jkp_cols, benchmark_sets = load_factor_panel(args.factor_panel)
    candidate_files = sorted(args.candidate_dir.glob("candidate_returns_*.csv"))
    if not candidate_files:
        raise FileNotFoundError(f"No candidate_returns_*.csv files found in {args.candidate_dir}")

    all_rows: list[dict[str, Any]] = []
    book_rows: list[dict[str, Any]] = []
    for path in candidate_files:
        candidate_id = candidate_id_from_path(path)
        cand = read_candidate(path)
        book = textbenchmark_delta_mvo_metrics(cand, factors, candidate_return_col="candidate_return", jkp_cols=jkp_cols)
        book_rows.append({"candidate_id": candidate_id, **book})
        for label, cols in benchmark_sets.items():
            row = multifactor_value_add(
                cand,
                factors,
                candidate_id=candidate_id,
                candidate_return_col="candidate_return",
                benchmark_label=label,
                factor_cols=cols,
                jkp_cols=jkp_cols,
                book_metrics=book,
            )
            all_rows.append(row)

    metrics = pd.DataFrame(all_rows)
    book_df = pd.DataFrame(book_rows)
    candidate_meta = load_metadata(args.candidate_dir)
    summary = make_summary(metrics, candidate_meta)

    metrics_path = args.out_dir / "alpha_evolve_textbenchmark_benchmark_metrics.csv"
    book_path = args.out_dir / "alpha_evolve_textbenchmark_book_delta_mvo.csv"
    summary_path = args.out_dir / "alpha_evolve_textbenchmark_candidate_summary.csv"
    metrics.to_csv(metrics_path, index=False)
    book_df.to_csv(book_path, index=False)
    summary.to_csv(summary_path, index=False)

    run_meta = {
        "candidate_dir": str(args.candidate_dir),
        "factor_panel": str(args.factor_panel),
        "output_dir": str(args.out_dir),
        "report_path": str(args.report_path),
        "analysis_window_start": str(ANALYSIS_WINDOW_START.date()),
        "analysis_window_end": str(ANALYSIS_WINDOW_END.date()),
        "analysis_window_label": ANALYSIS_WINDOW_LABEL,
        "target_annual_volatility": TARGET_ANNUAL_VOLATILITY,
        "return_scaling_policy": TARGET_VOLATILITY_POLICY,
        "existing_book_label": EXISTING_BOOK_LABEL,
        "n_candidate_files": len(candidate_files),
        "n_metrics_rows": len(metrics),
        "n_jkp132_factor_columns": len(jkp_cols),
        "benchmark_sets": benchmark_sets,
        "outputs": {
            "summary_csv": str(summary_path),
            "metrics_csv": str(metrics_path),
            "book_delta_mvo_csv": str(book_path),
        },
        "runtime_seconds": time.time() - started,
    }
    report = render_report(summary, metrics, run_meta, args.out_dir)
    report_path = args.out_dir / "TEXTBENCHMARK_PERFORMANCE_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    run_meta["outputs"]["markdown_report"] = str(report_path)
    (args.out_dir / "run_metadata.json").write_text(json.dumps(json_safe(run_meta), indent=2, sort_keys=True), encoding="utf-8")

    if not args.skip_main_report_update:
        update_main_report(args.report_path, report)

    print(f"Wrote {summary_path}")
    print(f"Wrote {metrics_path}")
    print(f"Wrote {book_path}")
    print(f"Wrote {report_path}")
    print(
        summary[[
            "candidate_id",
            "textbenchmark_alpha_tstat_hac",
            "full_alpha_tstat_hac",
            "longonly_delta_sharpe",
            "longonly_all_mvo_candidate_weight",
            "adds_to_jkp132_textbenchmark_strict",
        ]].head(20).to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
