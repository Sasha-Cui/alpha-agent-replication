#!/usr/bin/env python3
"""Matched factor attribution for fidelity-graded formula components."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from run_broad_jkp_crossfit import (  # noqa: E402
    BASE_FACTOR_COLUMNS,
    RIDGE_LAMBDAS,
    hac_mean_se,
    holm_adjust,
    rolling_crossfit_reconstruction,
)


MODEL_SPECS = (
    ("capm", "CAPM", ("capm_top1000_mkt",), (0.0,), 1),
    (
        "ff3",
        "FF3",
        ("capm_top1000_mkt", "char__market_equity", "char__be_me"),
        (0.0,),
        3,
    ),
    (
        "ff5_mom",
        "FF5+Momentum",
        tuple(BASE_FACTOR_COLUMNS),
        (0.0,),
        len(BASE_FACTOR_COLUMNS),
    ),
)


def family_results(
    residuals: np.ndarray, candidate_ids: list[str], months: pd.Index, model: str
) -> list[dict[str, object]]:
    n_months = len(months)
    lags = int(math.floor(4.0 * (n_months / 100.0) ** (2.0 / 9.0)))
    means = residuals.mean(axis=0)
    ses = np.asarray([hac_mean_se(residuals[:, j], lags) for j in range(len(candidate_ids))])
    tstats = np.divide(means, ses, out=np.full_like(means, np.nan), where=ses > 0)
    pvalues = 2.0 * norm.sf(np.abs(tstats))
    holm = holm_adjust(pvalues)
    return [
        {
            "candidate_id": candidate_id,
            "benchmark_id": model,
            "n_months": n_months,
            "sample_start": months.min().date().isoformat(),
            "sample_end": months.max().date().isoformat(),
            "alpha_annualized": 12.0 * means[index],
            "alpha_t_hac": tstats[index],
            "p_value": pvalues[index],
            "holm_p_within_benchmark": holm[index],
            "positive_alpha": bool(means[index] > 0),
            "holm_positive_5pct": bool(means[index] > 0 and holm[index] < 0.05),
            "hac_lags": lags,
        }
        for index, candidate_id in enumerate(candidate_ids)
    ]


def plot_guru_pairs(source: Path, output: Path) -> None:
    data = pd.read_csv(source)
    data = data[(data["series_type"] == "replay") & (data["archive"] == "results_22_24")]
    keep = {
        "official_ff5_momentum_matched_jkp_window": "FF5+Mom",
        "official_ff5_momentum_plus_jkp_bab": "FF5+Mom+BAB",
    }
    data = data[data["benchmark"].isin(keep)].copy()
    wide = data.pivot(index=["agent", "mode"], columns="benchmark", values="alpha_annualized")
    before = "official_ff5_momentum_matched_jkp_window"
    after = "official_ff5_momentum_plus_jkp_bab"
    wide = wide.sort_values(before).reset_index()

    plt.rcParams.update(
        {
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#FFFFFF",
            "savefig.facecolor": "#FFFFFF",
            "text.color": "#111827",
            "axes.labelcolor": "#111827",
            "axes.edgecolor": "#374151",
            "xtick.color": "#111827",
            "ytick.color": "#111827",
            "font.size": 9,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    figure, axis = plt.subplots(figsize=(7.2, 4.6), constrained_layout=True)
    positions = np.arange(len(wide))
    for index, row in wide.iterrows():
        axis.plot(
            [100 * row[before], 100 * row[after]],
            [index, index],
            color="#6B7280",
            linewidth=1.2,
            zorder=1,
        )
    axis.scatter(100 * wide[before], positions, s=34, color="#2563EB", label="FF5+Momentum", zorder=2)
    axis.scatter(100 * wide[after], positions, s=38, marker="s", color="#B45309", label="+ JKP BAB", zorder=3)
    axis.axvline(0.0, color="#111827", linewidth=0.8, linestyle="--")
    labels = [
        f"{row.agent.title()} — {'archived-final' if row.mode == 'archived-final' else 'tool-routing'}"
        for row in wide.itertuples()
    ]
    axis.set_yticks(positions, labels)
    axis.set_xlabel("Annualized alpha (%)")
    axis.set_title("GuruAgents prompt-component replay: paired BAB attribution", color="#111827")
    axis.grid(axis="x", color="#D1D5DB", linewidth=0.6)
    axis.legend(frameon=False, loc="lower right", labelcolor="#111827")
    for spine in axis.spines.values():
        spine.set_color("#374151")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def multiplicity_description(candidate_count: int) -> str:
    return (
        f"Holm across {candidate_count} formula components within each benchmark; not across benchmark specifications"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--component-dir",
        type=Path,
        default=ROOT / "paper_runs/fidelity_formula_components",
    )
    parser.add_argument(
        "--factor-panel",
        type=Path,
        default=ROOT.parent
        / "KnowledgeTemplate/performance_analysis/results/current/multifactor_value_add_20260624/benchmark_factor_panel.csv",
    )
    parser.add_argument("--train-months", type=int, default=120)
    parser.add_argument("--validation-months", type=int, default=24)
    parser.add_argument("--guru-figure-output", type=Path)
    args = parser.parse_args()

    paths = pd.read_csv(args.component_dir / "monthly_return_paths.csv")
    paths["month"] = pd.to_datetime(paths["month"], errors="raise") + pd.offsets.MonthEnd(0)
    wide = paths.pivot(index="month", columns="candidate_id", values="net_excess_return").sort_index()
    candidate_ids = wide.columns.tolist()

    factors = pd.read_csv(args.factor_panel)
    factors["month"] = pd.to_datetime(factors["month"], errors="raise") + pd.offsets.MonthEnd(1)
    characteristic_columns = [column for column in factors if column.startswith("char__")]
    broad_columns = [
        *BASE_FACTOR_COLUMNS,
        *[column for column in characteristic_columns if column not in BASE_FACTOR_COLUMNS],
    ]
    if len(characteristic_columns) != 132 or len(broad_columns) != 133:
        raise ValueError("factor panel must contain market plus 132 JKP characteristic factors")
    merged = factors.set_index("month")[broad_columns].join(wide, how="inner").dropna()
    if len(merged) < args.train_months + 60:
        raise ValueError(f"insufficient matched history: {len(merged)} months")

    specs = list(MODEL_SPECS) + [
        (
            "ff5_mom_jkp132",
            "FF5+Momentum+JKP132",
            tuple(broad_columns),
            tuple(RIDGE_LAMBDAS.tolist()),
            len(BASE_FACTOR_COLUMNS),
        )
    ]
    y = merged[candidate_ids].to_numpy(dtype=float)
    evaluation_months = merged.index[args.train_months :]
    rows: list[dict[str, object]] = []
    for benchmark_id, benchmark_label, columns, lambdas, unpenalized in specs:
        result = rolling_crossfit_reconstruction(
            merged[list(columns)].to_numpy(dtype=float),
            y,
            args.train_months,
            args.validation_months,
            np.asarray(lambdas, dtype=float),
            unpenalized,
        )
        model_rows = family_results(result.residuals, candidate_ids, evaluation_months, benchmark_id)
        for row in model_rows:
            row["benchmark_label"] = benchmark_label
        rows.extend(model_rows)

    results = pd.DataFrame(rows)
    results.to_csv(args.component_dir / "attribution_results.csv", index=False)
    summary = (
        results.groupby(["benchmark_id", "benchmark_label"], sort=False)
        .agg(
            n_components=("candidate_id", "size"),
            median_alpha_annualized=("alpha_annualized", "median"),
            positive_alpha_count=("positive_alpha", "sum"),
            holm_positive_count=("holm_positive_5pct", "sum"),
        )
        .reset_index()
    )
    summary.to_csv(args.component_dir / "attribution_summary.csv", index=False)

    correlations = []
    for candidate_id in candidate_ids:
        values = merged[characteristic_columns].corrwith(merged[candidate_id]).dropna()
        best = values.abs().idxmax()
        correlations.append(
            {
                "candidate_id": candidate_id,
                "closest_jkp_factor": best,
                "correlation": values[best],
                "absolute_correlation": abs(values[best]),
            }
        )
    pd.DataFrame(correlations).to_csv(args.component_dir / "closest_jkp_factors.csv", index=False)
    if args.guru_figure_output is not None:
        plot_guru_pairs(
            ROOT / "paper_runs/prompt_replay/guruagents/performance/replay_attribution_by_candidate.csv",
            args.guru_figure_output,
        )
    output_sha256 = {
        name: sha256(args.component_dir / name)
        for name in (
            "attribution_results.csv",
            "attribution_summary.csv",
            "closest_jkp_factors.csv",
        )
    }
    if args.guru_figure_output is not None:
        output_sha256[str(args.guru_figure_output)] = sha256(args.guru_figure_output)
    manifest = {
        "factor_panel": str(args.factor_panel),
        "n_candidates": len(candidate_ids),
        "n_common_months": len(merged),
        "n_evaluation_months": len(evaluation_months),
        "benchmarks": [spec[0] for spec in specs],
        "multiplicity": multiplicity_description(len(candidate_ids)),
        "output_sha256": output_sha256,
    }
    (args.component_dir / "attribution_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
