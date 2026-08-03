#!/usr/bin/env python3
"""Post-hoc broad-JKP span diagnostic with strictly past-trained ridge slopes.

The dense same-sample 134-regressor specification in the legacy analysis is
not valid confirmatory evidence.  This diagnostic instead estimates factor
loadings with a rolling 120-month window, chooses ridge regularization using
only the first 96 months of each training window and its final 24 months as a
validation block, and evaluates the next month.  The reported alpha is the
mean of y_t - beta_{t-1}' f_t; the training-period intercept is deliberately
not subtracted, so persistent test-period abnormal return remains in the
estimand.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm


DEFAULT_FACTOR_PANEL = Path(
    "/home/zc362/project_pi_btk22/zc362/external-factor-data/"
    "performance_analysis/results/current/multifactor_value_add_20260624/"
    "benchmark_factor_panel.csv"
)
DEFAULT_USA_RESULTS = Path(
    "paper_runs/submission_evidence/usa_retrospective_corrected"
)
DEFAULT_OUTPUT = Path(
    "paper_runs/submission_evidence/usa_broad_jkp_crossfit"
)
RIDGE_LAMBDAS = np.asarray([0.1, 1.0, 10.0, 100.0, 1000.0], dtype=float)
BASE_FACTOR_COLUMNS = [
    "capm_top1000_mkt",
    "char__be_me",
    "char__market_equity",
    "char__at_gr1",
    "char__ope_be",
    "char__ret_12_1",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def hac_mean_se(values: np.ndarray, lags: int) -> float:
    values = np.asarray(values, dtype=float)
    centered = values - values.mean()
    n = len(centered)
    long_run = float(centered @ centered / n)
    for lag in range(1, min(lags, n - 1) + 1):
        weight = 1.0 - lag / (lags + 1.0)
        gamma = float(centered[lag:] @ centered[:-lag] / n)
        long_run += 2.0 * weight * gamma
    return math.sqrt(max(long_run, 0.0) / n)


def holm_adjust(pvalues: np.ndarray) -> np.ndarray:
    pvalues = np.asarray(pvalues, dtype=float)
    order = np.argsort(pvalues)
    adjusted = np.empty_like(pvalues)
    running = 0.0
    m = len(pvalues)
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * pvalues[idx])
        adjusted[idx] = min(running, 1.0)
    return adjusted


def standardized_ridge_all(
    x_train: np.ndarray,
    y_train: np.ndarray,
    lambdas: np.ndarray,
    n_unpenalized: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[np.ndarray]]:
    x_mean = x_train.mean(axis=0)
    x_std = x_train.std(axis=0, ddof=1)
    x_std = np.where(np.isfinite(x_std) & (x_std > 1e-12), x_std, 1.0)
    z = (x_train - x_mean) / x_std
    y_mean = y_train.mean(axis=0)
    yc = y_train - y_mean
    gram = z.T @ z
    rhs = z.T @ yc
    penalty = np.eye(z.shape[1], dtype=float)
    penalty[:n_unpenalized, :n_unpenalized] = 0.0
    coefficients = [np.linalg.solve(gram + lam * penalty, rhs) for lam in lambdas]
    return x_mean, x_std, y_mean, coefficients


def rolling_crossfit_residuals(
    x: np.ndarray,
    y: np.ndarray,
    train_months: int,
    validation_months: int,
    lambdas: np.ndarray,
    n_unpenalized: int,
) -> tuple[np.ndarray, np.ndarray]:
    n, n_candidates = y.shape
    if train_months <= validation_months + 24:
        raise ValueError("Training window must leave at least 24 pre-validation months")
    residuals = np.full((n - train_months, n_candidates), np.nan, dtype=float)
    chosen = np.full((n - train_months, n_candidates), np.nan, dtype=float)

    for out_row, test_idx in enumerate(range(train_months, n)):
        start = test_idx - train_months
        split = test_idx - validation_months
        x_inner = x[start:split]
        y_inner = y[start:split]
        x_valid = x[split:test_idx]
        y_valid = y[split:test_idx]

        x_mean, x_std, y_mean, inner_coef = standardized_ridge_all(
            x_inner, y_inner, lambdas, n_unpenalized
        )
        z_valid = (x_valid - x_mean) / x_std
        validation_mse = np.vstack(
            [np.mean((y_valid - (y_mean + z_valid @ coef)) ** 2, axis=0) for coef in inner_coef]
        )
        best_idx = np.argmin(validation_mse, axis=0)

        x_window = x[start:test_idx]
        y_window = y[start:test_idx]
        _, x_window_std, _, full_coef = standardized_ridge_all(
            x_window, y_window, lambdas, n_unpenalized
        )
        raw_slopes = [coef / x_window_std[:, None] for coef in full_coef]
        beta = np.column_stack(
            [raw_slopes[best_idx[j]][:, j] for j in range(n_candidates)]
        )
        residuals[out_row] = y[test_idx] - x[test_idx] @ beta
        chosen[out_row] = lambdas[best_idx]

    return residuals, chosen


def circular_block_indices(
    rng: np.random.Generator, n: int, block_length: int
) -> np.ndarray:
    n_blocks = math.ceil(n / block_length)
    starts = rng.integers(0, n, size=n_blocks)
    offsets = np.arange(block_length)
    return ((starts[:, None] + offsets[None, :]) % n).ravel()[:n]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--factor-panel", type=Path, default=DEFAULT_FACTOR_PANEL)
    parser.add_argument("--usa-results", type=Path, default=DEFAULT_USA_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--train-months", type=int, default=120)
    parser.add_argument("--validation-months", type=int, default=24)
    parser.add_argument("--cost-bps", type=float, default=10.0)
    parser.add_argument("--bootstrap-reps", type=int, default=5000)
    parser.add_argument("--block-length", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260803)
    args = parser.parse_args()

    candidate_path = args.usa_results / "candidate_monthly_USA.csv"
    metadata_path = args.usa_results / "candidate_metadata.csv"
    factors = pd.read_csv(args.factor_panel)
    # The legacy factor panel keys each next-month return to its formation
    # month.  The corrected evaluator keys that same return to its realization
    # month.  Shift once here and verify the market series after alignment.
    factors["month"] = pd.to_datetime(factors["month"], errors="raise") + pd.offsets.MonthEnd(1)
    all_characteristics = [c for c in factors if c.startswith("char__")]
    factor_columns = [
        *BASE_FACTOR_COLUMNS,
        *[c for c in all_characteristics if c not in BASE_FACTOR_COLUMNS],
    ]
    if len(factor_columns) != 133:
        raise ValueError(f"Expected CAPM plus 132 JKP characteristic factors; found {len(factor_columns)}")

    current_factors_path = args.usa_results / "factor_monthly_USA.csv"
    current_factors = pd.read_csv(current_factors_path)
    current_factors["month"] = pd.to_datetime(current_factors["month"], errors="raise") + pd.offsets.MonthEnd(0)
    alignment = factors[["month", "capm_top1000_mkt"]].merge(
        current_factors[["month", "jkp_topn_mkt"]], on="month", how="inner"
    )
    market_alignment_correlation = float(
        alignment["capm_top1000_mkt"].corr(alignment["jkp_topn_mkt"])
    )
    if market_alignment_correlation < 0.99:
        raise ValueError(
            "Factor-panel month alignment failed: market correlation is "
            f"{market_alignment_correlation:.6f}, expected at least 0.99"
        )

    candidates = pd.read_csv(candidate_path)
    candidates["month"] = pd.to_datetime(candidates["month"], errors="raise") + pd.offsets.MonthEnd(0)
    candidates = candidates[parse_bool(candidates["analysis_eligible"])].copy()
    candidates["net_return"] = candidates["gross_return"] - (args.cost_bps / 10000.0) * candidates["traded_notional"]
    wide = candidates.pivot(index="month", columns="candidate_id", values="net_return").sort_index()
    candidate_ids = wide.columns.tolist()
    if len(candidate_ids) != 62:
        raise ValueError(f"Expected 62 candidates; found {len(candidate_ids)}")

    merged = factors.set_index("month")[factor_columns].join(wide, how="inner").dropna()
    if len(merged) < args.train_months + 60:
        raise ValueError(f"Insufficient common history: {len(merged)} months")
    x = merged[factor_columns].to_numpy(dtype=float)
    y = merged[candidate_ids].to_numpy(dtype=float)
    residuals, chosen = rolling_crossfit_residuals(
        x,
        y,
        args.train_months,
        args.validation_months,
        RIDGE_LAMBDAS,
        len(BASE_FACTOR_COLUMNS),
    )
    eval_months = merged.index[args.train_months:]
    n_eval = len(eval_months)
    hac_lags = int(math.floor(4.0 * (n_eval / 100.0) ** (2.0 / 9.0)))
    means = residuals.mean(axis=0)
    ses = np.asarray([hac_mean_se(residuals[:, j], hac_lags) for j in range(len(candidate_ids))])
    tstats = means / ses
    pvalues = 2.0 * norm.sf(np.abs(tstats))
    holm = holm_adjust(pvalues)

    centered = residuals - means
    rng = np.random.default_rng(args.seed)
    bootstrap_t = np.empty((args.bootstrap_reps, len(candidate_ids)), dtype=float)
    for rep in range(args.bootstrap_reps):
        idx = circular_block_indices(rng, n_eval, args.block_length)
        bootstrap_t[rep] = centered[idx].mean(axis=0) / ses
    max_abs = np.max(np.abs(bootstrap_t), axis=1)
    max_p = np.asarray(
        [(1.0 + np.sum(max_abs >= abs(t))) / (args.bootstrap_reps + 1.0) for t in tstats]
    )
    critical = float(np.quantile(max_abs, 0.95, method="higher"))
    low = 12.0 * (means - critical * ses)
    high = 12.0 * (means + critical * ses)

    metadata = pd.read_csv(metadata_path).set_index("candidate_id")
    rows = []
    for j, candidate_id in enumerate(candidate_ids):
        meta = metadata.loc[candidate_id]
        lambda_values, lambda_counts = np.unique(chosen[:, j], return_counts=True)
        modal_lambda = float(lambda_values[np.argmax(lambda_counts)])
        rows.append(
            {
                "candidate_id": candidate_id,
                "paper_ref": meta["paper_ref"],
                "proxy_formula": meta["proxy_formula"],
                "n_evaluation_months": n_eval,
                "evaluation_start": eval_months.min().date().isoformat(),
                "evaluation_end": eval_months.max().date().isoformat(),
                "n_benchmark_factors": len(factor_columns),
                "cost_bps_one_way": args.cost_bps,
                "alpha_annualized": 12.0 * means[j],
                "alpha_t_hac": tstats[j],
                "p_value_two_sided": pvalues[j],
                "holm_p_value": holm[j],
                "max_abs_t_p_value": max_p[j],
                "simultaneous_ci_low_annualized": low[j],
                "simultaneous_ci_high_annualized": high[j],
                "holm_discovery_5pct": bool(means[j] > 0 and holm[j] < 0.05),
                "max_t_discovery_5pct": bool(means[j] > 0 and max_p[j] < 0.05),
                "confirmed_alpha_at_least_2pp": bool(low[j] >= 0.02),
                "modal_ridge_lambda": modal_lambda,
            }
        )
    results = pd.DataFrame(rows).sort_values("alpha_annualized", ascending=False)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.output_dir / "broad_jkp_crossfit_results.csv"
    residual_csv = args.output_dir / "broad_jkp_crossfit_residuals.csv"
    results.to_csv(output_csv, index=False)
    residual_frame = pd.DataFrame(residuals, columns=candidate_ids)
    residual_frame.insert(0, "month", eval_months.strftime("%Y-%m-%d"))
    residual_frame.to_csv(residual_csv, index=False)

    summary = {
        "analysis_label": "post_hoc_exploratory_broad_jkp_crossfit",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "factor_panel": str(args.factor_panel),
        "factor_panel_sha256": sha256(args.factor_panel),
        "factor_panel_month_label": "formation month shifted forward one month to corrected evaluator realization month",
        "market_alignment_correlation": market_alignment_correlation,
        "candidate_monthly": str(candidate_path),
        "candidate_monthly_sha256": sha256(candidate_path),
        "benchmark": "unpenalized market plus JKP value, size, investment, profitability, and momentum; ridge-controlled remaining 127 JKP characteristic-factor returns",
        "unpenalized_factor_columns": BASE_FACTOR_COLUMNS,
        "slope_estimator": "rolling partial ridge; six primary factors unpenalized, other factors ridge-regularized with training-only validation and standardization; no training intercept subtracted from test residual",
        "train_months": args.train_months,
        "validation_months": args.validation_months,
        "ridge_lambdas": RIDGE_LAMBDAS.tolist(),
        "cost_bps_one_way": args.cost_bps,
        "n_common_months": len(merged),
        "common_start": merged.index.min().date().isoformat(),
        "common_end": merged.index.max().date().isoformat(),
        "n_evaluation_months": n_eval,
        "evaluation_start": eval_months.min().date().isoformat(),
        "evaluation_end": eval_months.max().date().isoformat(),
        "hac_lags": hac_lags,
        "bootstrap_reps": args.bootstrap_reps,
        "block_length": args.block_length,
        "bootstrap_seed": args.seed,
        "max_t_critical_95": critical,
        "counts": {
            "positive_alpha": int((means > 0).sum()),
            "nominal_positive": int(((means > 0) & (pvalues < 0.05)).sum()),
            "holm_positive": int(((means > 0) & (holm < 0.05)).sum()),
            "max_t_positive": int(((means > 0) & (max_p < 0.05)).sum()),
            "simultaneous_lower_bound_at_least_2pp": int((low >= 0.02).sum()),
        },
        "output_sha256": {
            output_csv.name: sha256(output_csv),
            residual_csv.name: sha256(residual_csv),
        },
    }
    manifest_path = args.output_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(results.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
