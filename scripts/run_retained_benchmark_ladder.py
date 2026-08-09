#!/usr/bin/env python3
"""Matched benchmark ladder for the 50 retained strategy reconstructions.

The analysis holds the candidate returns, transaction costs, calendar,
training window, and evaluation months fixed while expanding the benchmark
from CAPM through the market plus all 132 JKP characteristic factors.

The broad specification is a 133-return model, not a 138-return model:
the FF5+Momentum analogues are members of the JKP characteristic panel and
are left unpenalized; the remaining 127 characteristic returns are
ridge-controlled. Results are descriptive because mappings and this
benchmark ladder were designed after U.S. outcomes had been inspected.
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

from build_census_citation_assets import MAPPING_SOURCE_TO_WORK_ID
from run_broad_jkp_crossfit import (
    BASE_FACTOR_COLUMNS,
    RIDGE_LAMBDAS,
    circular_block_indices,
    hac_mean_se,
    holm_adjust,
    rolling_crossfit_residuals,
)


DEFAULT_FACTOR_PANEL = Path(
    "/home/zc362/project_pi_btk22/zc362/factor-data/"
    "benchmark_factor_panel.csv"
)
DEFAULT_USA_RESULTS = Path("paper_runs/submission_evidence/usa_retrospective_corrected")
DEFAULT_MAPPING_AUDIT = Path(
    "paper_runs/submission_evidence/mapping_audit/mapping_audit.csv"
)
DEFAULT_OUTPUT = Path(
    "paper_runs/submission_evidence/retained_benchmark_ladder"
)

MODEL_SPECS = (
    {
        "benchmark_id": "capm",
        "benchmark_label": "CAPM",
        "factor_columns": ("capm_top1000_mkt",),
        "n_unpenalized": 1,
        "ridge_lambdas": (0.0,),
    },
    {
        "benchmark_id": "ff3",
        "benchmark_label": "FF3",
        "factor_columns": (
            "capm_top1000_mkt",
            "char__market_equity",
            "char__be_me",
        ),
        "n_unpenalized": 3,
        "ridge_lambdas": (0.0,),
    },
    {
        "benchmark_id": "ff5_mom",
        "benchmark_label": "FF5+Momentum",
        "factor_columns": tuple(BASE_FACTOR_COLUMNS),
        "n_unpenalized": len(BASE_FACTOR_COLUMNS),
        "ridge_lambdas": (0.0,),
    },
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def implementation_basis(tier: str) -> str:
    if tier == "M2_released_seed_expression":
        return "released_code_component_adaptation"
    if tier.startswith("M1_"):
        return "source_grounded_paper_component"
    if tier == "M0_narrative_translation":
        return "in_spirit_reconstruction"
    raise ValueError(f"Unknown mapping fidelity tier: {tier}")


def retained_crosswalk(root: Path, mapping_path: Path) -> pd.DataFrame:
    mapping = pd.read_csv(mapping_path)
    mapping = mapping[mapping["source_name"].isin(MAPPING_SOURCE_TO_WORK_ID)].copy()
    mapping["canonical_work_id"] = mapping["source_name"].map(MAPPING_SOURCE_TO_WORK_ID)
    mapping["implementation_basis"] = mapping["mapping_fidelity_tier"].map(
        implementation_basis
    )

    preferred = pd.read_csv(
        root / "literature_review/census_v1/primary_record_metadata.csv"
    )
    preferred = preferred[preferred["preferred_citation"].eq("yes")].copy()
    preferred = preferred[
        ["canonical_work_id", "bibtex_key", "title", "year"]
    ].drop_duplicates("canonical_work_id")
    mapping = mapping.merge(
        preferred,
        on="canonical_work_id",
        how="left",
        validate="many_to_one",
    )

    if len(mapping) != 50:
        raise ValueError(f"Expected 50 retained mappings; found {len(mapping)}")
    if mapping["candidate_id"].nunique() != 50:
        raise ValueError("Retained candidate identifiers are not unique")
    if mapping["canonical_work_id"].nunique() != 40:
        raise ValueError("Retained mappings do not cover exactly 40 works")
    if mapping[["title", "year", "bibtex_key"]].isna().any().any():
        raise ValueError("Retained mapping crosswalk has missing publication metadata")
    expected = {
        "released_code_component_adaptation": 1,
        "source_grounded_paper_component": 12,
        "in_spirit_reconstruction": 37,
    }
    if mapping["implementation_basis"].value_counts().to_dict() != expected:
        raise ValueError("Retained implementation-basis partition changed")
    return mapping


def family_statistics(
    residuals: np.ndarray,
    y_eval: np.ndarray,
    bootstrap_indices: np.ndarray,
    hac_lags: int,
) -> dict[str, np.ndarray | float]:
    means = residuals.mean(axis=0)
    ses = np.asarray(
        [hac_mean_se(residuals[:, j], hac_lags) for j in range(residuals.shape[1])]
    )
    tstats = np.divide(
        means,
        ses,
        out=np.full_like(means, np.nan),
        where=ses > 0,
    )
    pvalues = 2.0 * norm.sf(np.abs(tstats))
    holm = holm_adjust(pvalues)

    centered = residuals - means
    bootstrap_t = np.empty(
        (len(bootstrap_indices), residuals.shape[1]), dtype=float
    )
    for rep, indices in enumerate(bootstrap_indices):
        bootstrap_t[rep] = centered[indices].mean(axis=0) / ses
    max_abs = np.nanmax(np.abs(bootstrap_t), axis=1)
    max_p = np.asarray(
        [
            (1.0 + np.sum(max_abs >= abs(tstat))) / (len(max_abs) + 1.0)
            for tstat in tstats
        ]
    )
    critical = float(np.quantile(max_abs, 0.95, method="higher"))
    low = 12.0 * (means - critical * ses)
    high = 12.0 * (means + critical * ses)

    denominator = np.sum(np.square(y_eval), axis=0)
    oos_r2 = 1.0 - np.divide(
        np.sum(np.square(residuals), axis=0),
        denominator,
        out=np.full_like(denominator, np.nan),
        where=denominator > 0,
    )
    return {
        "means": means,
        "ses": ses,
        "tstats": tstats,
        "pvalues": pvalues,
        "holm": holm,
        "max_p": max_p,
        "simultaneous_low": low,
        "simultaneous_high": high,
        "critical": critical,
        "oos_r2_vs_zero": oos_r2,
    }


def strongest_benchmark(row: pd.Series, suffix: str) -> str:
    strongest = "none"
    for benchmark_id in ("capm", "ff3", "ff5_mom", "ff5_mom_jkp132"):
        if bool(row[f"{benchmark_id}_{suffix}"]):
            strongest = benchmark_id
    return strongest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--factor-panel", type=Path, default=DEFAULT_FACTOR_PANEL)
    parser.add_argument("--usa-results", type=Path, default=DEFAULT_USA_RESULTS)
    parser.add_argument("--mapping-audit", type=Path, default=DEFAULT_MAPPING_AUDIT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--train-months", type=int, default=120)
    parser.add_argument("--validation-months", type=int, default=24)
    parser.add_argument("--cost-bps", type=float, default=10.0)
    parser.add_argument("--bootstrap-reps", type=int, default=5000)
    parser.add_argument("--block-length", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260809)
    args = parser.parse_args()

    root = args.root.resolve()
    factor_path = args.factor_panel
    if not factor_path.is_absolute():
        factor_path = root / factor_path
    usa_results = args.usa_results
    if not usa_results.is_absolute():
        usa_results = root / usa_results
    mapping_path = args.mapping_audit
    if not mapping_path.is_absolute():
        mapping_path = root / mapping_path
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir

    crosswalk = retained_crosswalk(root, mapping_path)
    candidate_ids = sorted(crosswalk["candidate_id"].tolist())
    crosswalk_by_id = crosswalk.set_index("candidate_id")

    factors = pd.read_csv(factor_path)
    factors["month"] = (
        pd.to_datetime(factors["month"], errors="raise") + pd.offsets.MonthEnd(1)
    )
    characteristic_columns = [c for c in factors if c.startswith("char__")]
    broad_factor_columns = [
        *BASE_FACTOR_COLUMNS,
        *[c for c in characteristic_columns if c not in BASE_FACTOR_COLUMNS],
    ]
    if len(characteristic_columns) != 132 or len(broad_factor_columns) != 133:
        raise ValueError(
            "Expected market plus 132 JKP characteristic returns; "
            f"found {len(broad_factor_columns)} total factors"
        )
    broad_spec = {
        "benchmark_id": "ff5_mom_jkp132",
        "benchmark_label": "FF5+Momentum+JKP132",
        "factor_columns": tuple(broad_factor_columns),
        "n_unpenalized": len(BASE_FACTOR_COLUMNS),
        "ridge_lambdas": tuple(RIDGE_LAMBDAS.tolist()),
    }
    model_specs = (*MODEL_SPECS, broad_spec)

    current_factors = pd.read_csv(usa_results / "factor_monthly_USA.csv")
    current_factors["month"] = pd.to_datetime(
        current_factors["month"], errors="raise"
    )
    alignment = factors[["month", "capm_top1000_mkt"]].merge(
        current_factors[["month", "jkp_topn_mkt"]],
        on="month",
        how="inner",
    )
    market_alignment_correlation = float(
        alignment["capm_top1000_mkt"].corr(alignment["jkp_topn_mkt"])
    )
    if market_alignment_correlation < 0.99:
        raise ValueError(
            "Factor-panel month alignment failed: market correlation is "
            f"{market_alignment_correlation:.6f}"
        )

    candidate_path = usa_results / "candidate_monthly_USA.csv"
    candidates = pd.read_csv(candidate_path)
    candidates["month"] = pd.to_datetime(candidates["month"], errors="raise")
    candidates = candidates[
        parse_bool(candidates["analysis_eligible"])
        & candidates["candidate_id"].isin(candidate_ids)
    ].copy()
    candidates["net_return"] = (
        candidates["gross_return"]
        - (args.cost_bps / 10000.0) * candidates["traded_notional"]
    )
    wide = candidates.pivot(
        index="month", columns="candidate_id", values="net_return"
    ).sort_index()
    wide = wide.reindex(columns=candidate_ids)
    if wide.shape[1] != 50 or (wide.notna().sum() < args.train_months + 60).any():
        raise ValueError(
            "Retained U.S. return panel lacks sufficient history for one or "
            "more of the 50 strategies"
        )

    merged = (
        factors.set_index("month")[broad_factor_columns]
        .join(wide, how="inner")
        .dropna()
    )
    if len(merged) < args.train_months + 60:
        raise ValueError(f"Insufficient common history: {len(merged)} months")
    eval_months = merged.index[args.train_months:]
    y = merged[candidate_ids].to_numpy(dtype=float)
    y_eval = y[args.train_months:]
    n_eval = len(eval_months)
    hac_lags = int(math.floor(4.0 * (n_eval / 100.0) ** (2.0 / 9.0)))
    rng = np.random.default_rng(args.seed)
    bootstrap_indices = np.vstack(
        [
            circular_block_indices(rng, n_eval, args.block_length)
            for _ in range(args.bootstrap_reps)
        ]
    )

    result_rows: list[dict[str, object]] = []
    residual_frames: list[pd.DataFrame] = []
    model_manifest: dict[str, dict[str, object]] = {}
    for rank, spec in enumerate(model_specs, start=1):
        benchmark_id = str(spec["benchmark_id"])
        factor_columns = list(spec["factor_columns"])
        lambdas = np.asarray(spec["ridge_lambdas"], dtype=float)
        x = merged[factor_columns].to_numpy(dtype=float)
        residuals, chosen = rolling_crossfit_residuals(
            x,
            y,
            args.train_months,
            args.validation_months,
            lambdas,
            int(spec["n_unpenalized"]),
        )
        stats = family_statistics(
            residuals,
            y_eval,
            bootstrap_indices,
            hac_lags,
        )
        means = np.asarray(stats["means"])
        pvalues = np.asarray(stats["pvalues"])
        holm = np.asarray(stats["holm"])
        max_p = np.asarray(stats["max_p"])
        low = np.asarray(stats["simultaneous_low"])

        residual_frame = pd.DataFrame(residuals, columns=candidate_ids)
        residual_frame.insert(0, "month", eval_months.strftime("%Y-%m-%d"))
        residual_frame.insert(0, "benchmark_id", benchmark_id)
        residual_frames.append(residual_frame)

        for j, candidate_id in enumerate(candidate_ids):
            meta = crosswalk_by_id.loc[candidate_id]
            lambda_values, lambda_counts = np.unique(
                chosen[:, j], return_counts=True
            )
            modal_lambda = float(lambda_values[np.argmax(lambda_counts)])
            result_rows.append(
                {
                    "canonical_work_id": meta["canonical_work_id"],
                    "bibtex_key": meta["bibtex_key"],
                    "title": meta["title"],
                    "year": int(meta["year"]),
                    "source_name": meta["source_name"],
                    "candidate_id": candidate_id,
                    "paper_ref": meta["paper_ref"],
                    "proxy_formula": meta["proxy_formula"],
                    "mapping_fidelity_tier": meta["mapping_fidelity_tier"],
                    "implementation_basis": meta["implementation_basis"],
                    "benchmark_rank": rank,
                    "benchmark_id": benchmark_id,
                    "benchmark_label": spec["benchmark_label"],
                    "n_benchmark_returns": len(factor_columns),
                    "n_unpenalized_returns": int(spec["n_unpenalized"]),
                    "n_evaluation_months": n_eval,
                    "evaluation_start": eval_months.min().date().isoformat(),
                    "evaluation_end": eval_months.max().date().isoformat(),
                    "cost_bps_one_way": args.cost_bps,
                    "alpha_annualized": 12.0 * means[j],
                    "alpha_t_hac": np.asarray(stats["tstats"])[j],
                    "p_value_two_sided": pvalues[j],
                    "holm_p_value": holm[j],
                    "max_abs_t_p_value": max_p[j],
                    "simultaneous_ci_low_annualized": low[j],
                    "simultaneous_ci_high_annualized": np.asarray(
                        stats["simultaneous_high"]
                    )[j],
                    "oos_factor_replication_r2_vs_zero": np.asarray(
                        stats["oos_r2_vs_zero"]
                    )[j],
                    "positive_alpha_estimate": bool(means[j] > 0),
                    "nominal_positive_5pct": bool(
                        means[j] > 0 and pvalues[j] < 0.05
                    ),
                    "holm_positive_5pct": bool(
                        means[j] > 0 and holm[j] < 0.05
                    ),
                    "max_t_positive_5pct": bool(
                        means[j] > 0 and max_p[j] < 0.05
                    ),
                    "simultaneous_lower_bound_at_least_2pp": bool(low[j] >= 0.02),
                    "modal_ridge_lambda": modal_lambda,
                }
            )
        model_manifest[benchmark_id] = {
            "benchmark_label": spec["benchmark_label"],
            "factor_returns": len(factor_columns),
            "unpenalized_returns": int(spec["n_unpenalized"]),
            "ridge_lambdas": lambdas.tolist(),
            "max_t_critical_95": float(stats["critical"]),
            "positive_alpha": int((means > 0).sum()),
            "nominal_positive": int(((means > 0) & (pvalues < 0.05)).sum()),
            "holm_positive": int(((means > 0) & (holm < 0.05)).sum()),
            "max_t_positive": int(((means > 0) & (max_p < 0.05)).sum()),
            "median_alpha_annualized": float(np.median(12.0 * means)),
        }

    results = pd.DataFrame(result_rows).sort_values(
        ["benchmark_rank", "canonical_work_id", "candidate_id"]
    )
    if len(results) != 200:
        raise ValueError("Benchmark ladder is not a complete 50 by 4 panel")

    identity_columns = [
        "canonical_work_id",
        "bibtex_key",
        "title",
        "year",
        "source_name",
        "candidate_id",
        "paper_ref",
        "proxy_formula",
        "mapping_fidelity_tier",
        "implementation_basis",
    ]
    comparison = results[identity_columns].drop_duplicates("candidate_id")
    for benchmark_id in [spec["benchmark_id"] for spec in model_specs]:
        group = results[results["benchmark_id"].eq(benchmark_id)].set_index(
            "candidate_id"
        )
        for source, suffix in (
            ("alpha_annualized", "alpha_annualized"),
            ("alpha_t_hac", "alpha_t_hac"),
            ("p_value_two_sided", "p_value_two_sided"),
            ("holm_p_value", "holm_p_value"),
            ("positive_alpha_estimate", "positive"),
            ("nominal_positive_5pct", "nominal_positive"),
            ("holm_positive_5pct", "holm_positive"),
        ):
            comparison[f"{benchmark_id}_{suffix}"] = comparison[
                "candidate_id"
            ].map(group[source])
    comparison["strongest_benchmark_positive"] = comparison.apply(
        strongest_benchmark, axis=1, suffix="positive"
    )
    comparison["strongest_benchmark_nominal_positive"] = comparison.apply(
        strongest_benchmark, axis=1, suffix="nominal_positive"
    )
    comparison["strongest_benchmark_holm_positive"] = comparison.apply(
        strongest_benchmark, axis=1, suffix="holm_positive"
    )
    comparison["alpha_attenuation_ff3_to_jkp132"] = (
        comparison["ff3_alpha_annualized"]
        - comparison["ff5_mom_jkp132_alpha_annualized"]
    )
    comparison["alpha_attenuation_ff5_mom_to_jkp132"] = (
        comparison["ff5_mom_alpha_annualized"]
        - comparison["ff5_mom_jkp132_alpha_annualized"]
    )
    comparison = comparison.sort_values(["canonical_work_id", "candidate_id"])

    paper_rows: list[dict[str, object]] = []
    for work_id, work in comparison.groupby("canonical_work_id", sort=True):
        base = work.iloc[0]
        row: dict[str, object] = {
            "canonical_work_id": work_id,
            "bibtex_key": base["bibtex_key"],
            "title": base["title"],
            "year": base["year"],
            "source_name": base["source_name"],
            "n_strategies": len(work),
            "implementation_bases": ";".join(
                sorted(work["implementation_basis"].unique())
            ),
        }
        for benchmark_id in [spec["benchmark_id"] for spec in model_specs]:
            alphas = work[f"{benchmark_id}_alpha_annualized"]
            row[f"{benchmark_id}_median_alpha_annualized"] = float(alphas.median())
            row[f"{benchmark_id}_max_alpha_annualized"] = float(alphas.max())
            row[f"{benchmark_id}_positive_strategy_count"] = int(
                work[f"{benchmark_id}_positive"].sum()
            )
            row[f"{benchmark_id}_nominal_positive_strategy_count"] = int(
                work[f"{benchmark_id}_nominal_positive"].sum()
            )
            row[f"{benchmark_id}_holm_positive_strategy_count"] = int(
                work[f"{benchmark_id}_holm_positive"].sum()
            )
        paper_rows.append(row)
    paper_summary = pd.DataFrame(paper_rows)
    if len(paper_summary) != 40:
        raise ValueError("Paper summary does not contain exactly 40 retained works")

    summary_rows: list[dict[str, object]] = []
    bases = ("all_retained", *sorted(results["implementation_basis"].unique()))
    for basis in bases:
        subset = (
            results
            if basis == "all_retained"
            else results[results["implementation_basis"].eq(basis)]
        )
        for benchmark_id, group in subset.groupby("benchmark_id", sort=False):
            summary_rows.append(
                {
                    "implementation_basis": basis,
                    "benchmark_id": benchmark_id,
                    "benchmark_label": group["benchmark_label"].iloc[0],
                    "n_strategies": len(group),
                    "positive_alpha_estimates": int(
                        group["positive_alpha_estimate"].sum()
                    ),
                    "nominal_positive_5pct": int(
                        group["nominal_positive_5pct"].sum()
                    ),
                    "holm_positive_5pct": int(group["holm_positive_5pct"].sum()),
                    "max_t_positive_5pct": int(
                        group["max_t_positive_5pct"].sum()
                    ),
                    "median_alpha_annualized": float(
                        group["alpha_annualized"].median()
                    ),
                    "alpha_q25_annualized": float(
                        group["alpha_annualized"].quantile(0.25)
                    ),
                    "alpha_q75_annualized": float(
                        group["alpha_annualized"].quantile(0.75)
                    ),
                    "median_oos_factor_replication_r2_vs_zero": float(
                        group["oos_factor_replication_r2_vs_zero"].median()
                    ),
                }
            )
    benchmark_summary = pd.DataFrame(summary_rows)

    correlation_rows: list[dict[str, object]] = []
    for candidate_id in candidate_ids:
        meta = crosswalk_by_id.loc[candidate_id]
        correlations = (
            merged[characteristic_columns]
            .corrwith(merged[candidate_id])
            .dropna()
            .sort_values(key=lambda values: values.abs(), ascending=False)
        )
        if len(correlations) != 132:
            raise ValueError(
                f"JKP correlation vector is incomplete for {candidate_id}"
            )
        for factor_rank, (factor_column, correlation) in enumerate(
            correlations.items(), start=1
        ):
            correlation_rows.append(
                {
                    "canonical_work_id": meta["canonical_work_id"],
                    "source_name": meta["source_name"],
                    "candidate_id": candidate_id,
                    "mapping_fidelity_tier": meta["mapping_fidelity_tier"],
                    "implementation_basis": meta["implementation_basis"],
                    "factor_rank_by_absolute_correlation": factor_rank,
                    "jkp_factor_column": factor_column,
                    "jkp_factor_id": factor_column.removeprefix("char__"),
                    "correlation": float(correlation),
                    "absolute_correlation": abs(float(correlation)),
                    "n_common_months": len(merged),
                    "common_start": merged.index.min().date().isoformat(),
                    "common_end": merged.index.max().date().isoformat(),
                }
            )
    factor_correlations = pd.DataFrame(correlation_rows)
    top_factors = factor_correlations[
        factor_correlations["factor_rank_by_absolute_correlation"] <= 5
    ].copy()
    top_one = factor_correlations[
        factor_correlations["factor_rank_by_absolute_correlation"].eq(1)
    ].copy()
    top_factor_frequency = (
        top_one.groupby(["jkp_factor_column", "jkp_factor_id"], as_index=False)
        .agg(
            n_strategies=("candidate_id", "size"),
            median_signed_correlation=("correlation", "median"),
            median_absolute_correlation=("absolute_correlation", "median"),
            max_absolute_correlation=("absolute_correlation", "max"),
        )
        .sort_values(
            ["n_strategies", "median_absolute_correlation"],
            ascending=[False, False],
        )
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "strategy_benchmark_results.csv": results,
        "strategy_benchmark_comparison.csv": comparison,
        "paper_benchmark_summary.csv": paper_summary,
        "benchmark_summary.csv": benchmark_summary,
        "benchmark_residuals.csv": pd.concat(residual_frames, ignore_index=True),
        "strategy_jkp_factor_correlations.csv": factor_correlations,
        "strategy_top_jkp_factors.csv": top_factors,
        "top_jkp_factor_frequency.csv": top_factor_frequency,
    }
    for filename, frame in outputs.items():
        frame.to_csv(output_dir / filename, index=False)

    manifest = {
        "analysis_label": "post_hoc_matched_retained_benchmark_ladder",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "interpretation": (
            "descriptive spanning analysis conditional on 50 retained mappings; "
            "not native-agent replication and not confirmatory inference"
        ),
        "factor_panel": str(factor_path),
        "factor_panel_sha256": sha256(factor_path),
        "candidate_monthly": str(candidate_path),
        "candidate_monthly_sha256": sha256(candidate_path),
        "mapping_audit": str(mapping_path),
        "mapping_audit_sha256": sha256(mapping_path),
        "market_alignment_correlation": market_alignment_correlation,
        "strategy_count": 50,
        "paper_count": 40,
        "implementation_basis_counts": crosswalk[
            "implementation_basis"
        ].value_counts().to_dict(),
        "common_months": len(merged),
        "common_start": merged.index.min().date().isoformat(),
        "common_end": merged.index.max().date().isoformat(),
        "train_months": args.train_months,
        "validation_months": args.validation_months,
        "evaluation_months": n_eval,
        "evaluation_start": eval_months.min().date().isoformat(),
        "evaluation_end": eval_months.max().date().isoformat(),
        "cost_bps_one_way": args.cost_bps,
        "hac_lags": hac_lags,
        "bootstrap_reps": args.bootstrap_reps,
        "block_length": args.block_length,
        "bootstrap_seed": args.seed,
        "model_results": model_manifest,
        "factor_correlation_summary": {
            "factor_count": len(characteristic_columns),
            "strategy_factor_pairs": len(factor_correlations),
            "median_top_absolute_correlation": float(
                top_one["absolute_correlation"].median()
            ),
            "top_absolute_correlation_at_least_0_5": int(
                (top_one["absolute_correlation"] >= 0.5).sum()
            ),
            "unique_top_factors": int(top_one["jkp_factor_id"].nunique()),
        },
        "output_sha256": {
            filename: sha256(output_dir / filename) for filename in outputs
        },
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))
    print(
        benchmark_summary[
            benchmark_summary["implementation_basis"].eq("all_retained")
        ].to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
