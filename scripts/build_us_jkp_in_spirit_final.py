#!/usr/bin/env python3
"""Build the final visual and audit synthesis for the 69-paper in-spirit study."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


STUDY_ID = "us_jkp_in_spirit_v1"
TERMINAL = {
    "carried_common_evaluation",
    "completed_in_spirit",
    "discarded_structural_mismatch",
}
COLORS = {
    "background": "#F7F8FA",
    "foreground": "#17212B",
    "grid": "#C9D2DC",
    "carried_common_evaluation": "#2563EB",
    "completed_in_spirit": "#D97706",
    "discarded_structural_mismatch": "#7C3AED",
    "zero": "#4B5563",
}
RESULT_COLUMNS = [
    "milestone_id",
    "canonical_work_id",
    "title",
    "system_ids",
    "disposition",
    "evaluation_class",
    "fidelity_label",
    "strict_status",
    "common_jkp_evaluated",
    "native_system_end_to_end_reproduced",
    "native_empirical_claim_tested",
    "primary_cost_bps_one_way",
    "full_months",
    "full_cagr",
    "full_annualized_sharpe",
    "full_maximum_drawdown",
    "average_traded_notional",
    "jkp_excess_measure",
    "jkp_excess_annualized",
    "jkp_excess_t_hac",
    "jkp_excess_p_two_sided",
    "jkp_excess_ci_low_annualized",
    "jkp_excess_ci_high_annualized",
    "holm_rank_among_evaluable",
    "holm_family_size",
    "holm_adjusted_p",
    "holm_reject_5pct",
    "recipe_path",
    "implementation_path",
    "run_manifest_path",
    "monthly_returns_path",
    "metrics_path",
    "verdict_path",
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def csv_bytes(rows: list[dict[str, Any]], columns: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def primary_metric(path: Path) -> dict[str, Any]:
    frame = pd.read_csv(path)
    primary = frame.loc[frame["primary"].astype(str).str.lower().eq("true")]
    if len(primary) != 1:
        raise ValueError(f"expected one primary row in {path}, found {len(primary)}")
    row = primary.iloc[0]
    alpha_schema = "jkp_alpha_annualized" in frame.columns
    prefix = "jkp_alpha" if alpha_schema else "jkp_residual"
    mean_column = f"{prefix}_annualized" if alpha_schema else f"{prefix}_mean_annualized"
    mean = float(row[mean_column])
    se = float(row[f"{prefix}_se_annualized"])
    low_column = f"{prefix}_ci_low_annualized"
    high_column = f"{prefix}_ci_high_annualized"
    return {
        "primary_cost_bps_one_way": float(row["cost_bps_one_way"]),
        "full_months": int(row["full_months"]),
        "full_cagr": float(row["full_cagr"]),
        "full_annualized_sharpe": float(row["full_annualized_sharpe"]),
        "full_maximum_drawdown": float(row["full_maximum_drawdown"]),
        "average_traded_notional": float(row["average_traded_notional"]),
        "jkp_excess_measure": "rolling_jkp_alpha" if alpha_schema else "rolling_jkp_residual_mean",
        "jkp_excess_annualized": mean,
        "jkp_excess_t_hac": float(row[f"{prefix}_t_hac"]),
        "jkp_excess_p_two_sided": float(row[f"{prefix}_p_two_sided"]),
        "jkp_excess_ci_low_annualized": (
            float(row[low_column]) if low_column in frame else mean - 1.959963984540054 * se
        ),
        "jkp_excess_ci_high_annualized": (
            float(row[high_column]) if high_column in frame else mean + 1.959963984540054 * se
        ),
    }


def holm_rows(evaluated: list[dict[str, Any]], family_size: int) -> list[dict[str, Any]]:
    ordered = sorted(evaluated, key=lambda row: (row["jkp_excess_p_two_sided"], row["milestone_id"]))
    adjusted_so_far = 0.0
    still_rejecting = True
    result: list[dict[str, Any]] = []
    for rank, row in enumerate(ordered, start=1):
        multiplier = family_size - rank + 1
        raw = float(row["jkp_excess_p_two_sided"])
        adjusted_so_far = max(adjusted_so_far, min(1.0, multiplier * raw))
        critical = 0.05 / multiplier
        reject = bool(still_rejecting and raw <= critical)
        if not reject:
            still_rejecting = False
        result.append(
            {
                "rank": rank,
                "milestone_id": row["milestone_id"],
                "title": row["title"],
                "evaluation_class": row["evaluation_class"],
                "jkp_excess_annualized": row["jkp_excess_annualized"],
                "raw_p_two_sided": raw,
                "holm_multiplier": multiplier,
                "holm_critical_value_5pct": critical,
                "holm_adjusted_p": adjusted_so_far,
                "holm_reject_5pct": reject,
            }
        )
    return result


def load_results(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Path]]:
    study = root / "paper_runs/us_jkp_in_spirit"
    ledger_path = study / "milestones.json"
    ledger = json.loads(ledger_path.read_text())
    rows = ledger["milestones"]
    if ledger["study_id"] != STUDY_ID or len(rows) != 69:
        raise ValueError("in-spirit ledger identity or paper count changed")
    if any(row["status"] not in TERMINAL for row in rows):
        raise ValueError("all 69 in-spirit milestones must be terminal")
    expected_counts = {
        "carried_common_evaluation": 17,
        "completed_in_spirit": 45,
        "discarded_structural_mismatch": 7,
    }
    actual_counts = {name: sum(row["status"] == name for row in rows) for name in expected_counts}
    if actual_counts != expected_counts:
        raise ValueError(f"final disposition changed: {actual_counts}")

    result_rows: list[dict[str, Any]] = []
    metric_inputs: list[Path] = []
    for milestone in rows:
        status = milestone["status"]
        evaluated = status != "discarded_structural_mismatch"
        evaluation_class = {
            "carried_common_evaluation": "carried_strict_adaptation",
            "completed_in_spirit": "researcher_authored_in_spirit",
            "discarded_structural_mismatch": "structural_discard",
        }[status]
        if status == "carried_common_evaluation":
            metrics_path = milestone["strict_metrics_path"]
            recipe_path = milestone["strict_recipe_path"]
            verdict_path = milestone["strict_verdict_path"]
            strict_rows = pd.read_csv(root / "paper_runs/us_jkp_headline/cross_paper_summary.csv")
            strict = strict_rows.loc[strict_rows.milestone_id.eq(milestone["milestone_id"])].iloc[0]
            implementation_path = "" if pd.isna(strict.implementation_path) else str(strict.implementation_path)
            run_manifest_path = "" if pd.isna(strict.run_manifest_path) else str(strict.run_manifest_path)
            monthly_returns_path = "" if pd.isna(strict.monthly_returns_path) else str(strict.monthly_returns_path)
        elif status == "completed_in_spirit":
            metrics_path = milestone["metrics_path"]
            recipe_path = milestone["recipe_path"]
            verdict_path = milestone["verdict_path"]
            implementation_path = milestone["implementation_path"]
            run_manifest_path = milestone["run_manifest_path"]
            monthly_returns_path = milestone["monthly_returns_path"]
        else:
            metrics_path = recipe_path = verdict_path = ""
            implementation_path = run_manifest_path = monthly_returns_path = ""
        result = {
            "milestone_id": milestone["milestone_id"],
            "canonical_work_id": milestone["canonical_work_id"],
            "title": milestone["title"],
            "system_ids": milestone["system_ids"],
            "disposition": status,
            "evaluation_class": evaluation_class,
            "fidelity_label": milestone["fidelity_label"],
            "strict_status": milestone["strict_status"],
            "common_jkp_evaluated": evaluated,
            "native_system_end_to_end_reproduced": False,
            "native_empirical_claim_tested": False,
            **{column: "" for column in RESULT_COLUMNS[11:27]},
            "recipe_path": recipe_path,
            "implementation_path": implementation_path,
            "run_manifest_path": run_manifest_path,
            "monthly_returns_path": monthly_returns_path,
            "metrics_path": metrics_path,
            "verdict_path": verdict_path,
        }
        if evaluated:
            path = root / metrics_path
            result.update(primary_metric(path))
            metric_inputs.append(path)
        result_rows.append(result)

    evaluated_rows = [row for row in result_rows if row["common_jkp_evaluated"]]
    family = holm_rows(evaluated_rows, 69)
    lookup = {row["milestone_id"]: row for row in family}
    for row in evaluated_rows:
        inference = lookup[row["milestone_id"]]
        row.update(
            holm_rank_among_evaluable=inference["rank"],
            holm_family_size=69,
            holm_adjusted_p=inference["holm_adjusted_p"],
            holm_reject_5pct=inference["holm_reject_5pct"],
        )
    return result_rows, family, metric_inputs


def set_plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": COLORS["background"],
            "axes.facecolor": COLORS["background"],
            "savefig.facecolor": COLORS["background"],
            "text.color": COLORS["foreground"],
            "axes.labelcolor": COLORS["foreground"],
            "axes.edgecolor": COLORS["foreground"],
            "xtick.color": COLORS["foreground"],
            "ytick.color": COLORS["foreground"],
            "font.size": 9,
        }
    )


def save_dispositions(rows: list[dict[str, Any]], path: Path) -> None:
    labels = ["Carried strict\nadaptations", "In-spirit\nreconstructions", "Structural\ndiscards"]
    statuses = list(TERMINAL)
    statuses = ["carried_common_evaluation", "completed_in_spirit", "discarded_structural_mismatch"]
    counts = [sum(row["disposition"] == status for row in rows) for status in statuses]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    bars = ax.bar(labels, counts, color=[COLORS[status] for status in statuses], width=0.62)
    ax.set_ylabel("Paper milestones", color=COLORS["foreground"])
    ax.set_title("All 69 milestones have a terminal, explicitly labelled disposition", color=COLORS["foreground"])
    ax.set_ylim(0, 50)
    ax.grid(axis="y", color=COLORS["grid"], alpha=0.8)
    for bar, value in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1, str(value), ha="center", va="bottom", color=COLORS["foreground"], fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight", metadata={"Software": "alpha-agent-replication"})
    plt.close(fig)


def save_ranked(rows: list[dict[str, Any]], value: str, path: Path, title: str, xlabel: str) -> None:
    evaluated = sorted(
        [row for row in rows if row["common_jkp_evaluated"]],
        key=lambda row: float(row[value]),
    )
    y = np.arange(len(evaluated))
    values = np.array([float(row[value]) for row in evaluated])
    colors = [COLORS[row["disposition"]] for row in evaluated]
    fig, ax = plt.subplots(figsize=(10.2, 14.8))
    ax.scatter(values, y, c=colors, s=28, edgecolor=COLORS["foreground"], linewidth=0.25)
    ax.axvline(0.0, color=COLORS["zero"], linewidth=1.0)
    ax.set_yticks(y, [row["milestone_id"] for row in evaluated], fontsize=7, color=COLORS["foreground"])
    ax.set_xlabel(xlabel, color=COLORS["foreground"])
    ax.set_title(title, color=COLORS["foreground"])
    ax.grid(axis="x", color=COLORS["grid"], alpha=0.75)
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight", metadata={"Software": "alpha-agent-replication"})
    plt.close(fig)


def save_excess_intervals(rows: list[dict[str, Any]], path: Path) -> None:
    evaluated = sorted(
        [row for row in rows if row["common_jkp_evaluated"]],
        key=lambda row: float(row["jkp_excess_annualized"]),
    )
    y = np.arange(len(evaluated))
    mean = np.array([float(row["jkp_excess_annualized"]) for row in evaluated])
    low = np.array([float(row["jkp_excess_ci_low_annualized"]) for row in evaluated])
    high = np.array([float(row["jkp_excess_ci_high_annualized"]) for row in evaluated])
    colors = [COLORS[row["disposition"]] for row in evaluated]
    fig, ax = plt.subplots(figsize=(10.2, 15.2))
    ax.hlines(y, low * 100, high * 100, color=colors, linewidth=1.3, alpha=0.82)
    ax.scatter(mean * 100, y, c=colors, s=28, edgecolor=COLORS["foreground"], linewidth=0.25, zorder=3)
    ax.axvline(0.0, color=COLORS["zero"], linewidth=1.0)
    ax.set_yticks(y, [row["milestone_id"] for row in evaluated], fontsize=7, color=COLORS["foreground"])
    ax.set_xlabel("Annualized rolling JKP excess/residual and 95% HAC interval (%)", color=COLORS["foreground"])
    ax.set_title("No common-benchmark excess estimate is significant after family correction", color=COLORS["foreground"])
    ax.grid(axis="x", color=COLORS["grid"], alpha=0.75)
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight", metadata={"Software": "alpha-agent-replication"})
    plt.close(fig)


def save_scatter(rows: list[dict[str, Any]], path: Path) -> None:
    evaluated = [row for row in rows if row["common_jkp_evaluated"]]
    fig, ax = plt.subplots(figsize=(8.5, 6.2))
    for status, label in (
        ("carried_common_evaluation", "Carried strict adaptation"),
        ("completed_in_spirit", "Researcher-authored in-spirit"),
    ):
        group = [row for row in evaluated if row["disposition"] == status]
        ax.scatter(
            [100 * float(row["full_cagr"]) for row in group],
            [100 * float(row["jkp_excess_annualized"]) for row in group],
            c=COLORS[status],
            label=label,
            s=42,
            edgecolor=COLORS["foreground"],
            linewidth=0.35,
            alpha=0.9,
        )
    ax.axhline(0.0, color=COLORS["zero"], linewidth=1.0)
    ax.axvline(0.0, color=COLORS["zero"], linewidth=1.0)
    ax.set_xlabel("Full-sample CAGR at 10 bp one-way cost (%)", color=COLORS["foreground"])
    ax.set_ylabel("Annualized rolling JKP excess/residual (%)", color=COLORS["foreground"])
    ax.set_title("Positive raw returns need not be distinct from the JKP characteristic benchmark", color=COLORS["foreground"])
    ax.grid(color=COLORS["grid"], alpha=0.7)
    legend = ax.legend(frameon=True, facecolor=COLORS["background"], edgecolor=COLORS["foreground"])
    for text in legend.get_texts():
        text.set_color(COLORS["foreground"])
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight", metadata={"Software": "alpha-agent-replication"})
    plt.close(fig)


def fmt_pct(value: Any) -> str:
    return "-" if value == "" or value is None else f"{100 * float(value):.2f}%"


def compact_extremes(rows: list[dict[str, Any]], value: str) -> list[dict[str, Any] | None]:
    ordered = sorted([row for row in rows if row["common_jkp_evaluated"]], key=lambda row: float(row[value]), reverse=True)
    return [*ordered[:5], None, *ordered[-5:]]


def disposition_table(rows: list[dict[str, Any]]) -> list[str]:
    labels = {
        "carried_common_evaluation": "Carried strict adaptation",
        "completed_in_spirit": "Researcher-authored in-spirit",
        "discarded_structural_mismatch": "Structural discard",
    }
    return [
        "| Disposition | Papers | Common paths | Native claim tested? |",
        "|---|---:|---:|---|",
        *[
            f"| {labels[status]} | {sum(row['disposition'] == status for row in rows)} | "
            f"{sum(row['disposition'] == status and row['common_jkp_evaluated'] for row in rows)} | No |"
            for status in labels
        ],
    ]


def extremes_table(rows: list[dict[str, Any]], value: str, display: str) -> list[str]:
    lines = ["| ID | Class | CAGR | Sharpe | JKP excess/yr | raw p |", "|---|---|---:|---:|---:|---:|"]
    for row in compact_extremes(rows, value):
        if row is None:
            lines.append("| ... | ... | ... | ... | ... | ... |")
        else:
            lines.append(
                f"| {row['milestone_id']} | {row['evaluation_class']} | {fmt_pct(row['full_cagr'])} | "
                f"{float(row['full_annualized_sharpe']):.3f} | {fmt_pct(row['jkp_excess_annualized'])} | "
                f"{float(row['jkp_excess_p_two_sided']):.4f} |"
            )
    return lines


def build_report(rows: list[dict[str, Any]], family: list[dict[str, Any]], visual: bool) -> str:
    evaluated = [row for row in rows if row["common_jkp_evaluated"]]
    carried = [row for row in evaluated if row["disposition"] == "carried_common_evaluation"]
    in_spirit = [row for row in evaluated if row["disposition"] == "completed_in_spirit"]
    positive_cagr = sum(float(row["full_cagr"]) > 0 for row in evaluated)
    positive_excess = sum(float(row["jkp_excess_annualized"]) > 0 for row in evaluated)
    raw_significant = sum(float(row["jkp_excess_p_two_sided"]) < 0.05 for row in evaluated)
    positive_significant = sum(
        float(row["jkp_excess_annualized"]) > 0 and float(row["jkp_excess_p_two_sided"]) < 0.05
        for row in evaluated
    )
    holm_significant = sum(bool(row["holm_reject_5pct"]) for row in evaluated)
    category_rows = []
    for name, group in (("Carried strict adaptations", carried), ("In-spirit reconstructions", in_spirit), ("All evaluated", evaluated)):
        category_rows.append(
            f"| {name} | {len(group)} | {sum(float(row['full_cagr']) > 0 for row in group)} | "
            f"{sum(float(row['jkp_excess_annualized']) > 0 for row in group)} | "
            f"{sum(float(row['jkp_excess_p_two_sided']) < 0.05 for row in group)} |"
        )
    lines = [
        "# Final 69-paper U.S./JKP reconstruction synthesis",
        "",
        "## Executive answer",
        "",
        "The milestone program is complete: **17 carried source-anchored common evaluations, 45 "
        "researcher-authored in-spirit reconstructions, and 7 structural discards**. That yields 62 "
        "executable monthly U.S.-stock paths on the same 305-month universe and accounting contract.",
        "",
        f"At the fixed 10 bp one-way cost, {positive_cagr} of 62 paths have positive full-sample CAGR. "
        f"After rolling reconstruction from the broad JKP characteristic benchmark, {positive_excess} "
        f"have positive annualized excess/residual estimates. {raw_significant} have two-sided HAC "
        f"p-values below 5% ({positive_significant} positive), and {holm_significant} survive Holm's "
        "69-paper family correction.",
        "",
        "The honest interpretation is neither blanket A nor blanket B. We did **not** reproduce any "
        "paper's complete native system and empirical protocol end to end, so these results cannot "
        "declare the original claims true or false. For 17 cases we carried the strict study's best "
        "source-anchored adaptation or central component. For 45 cases we deliberately wrote a "
        "transparent surrogate preserving the headline mechanism. Their common JKP performance asks "
        "whether that implementation transfers; it is not a native replication test.",
        "",
        "Every reconstruction was frozen before its own result and retained when negative or "
        "insignificant. Nevertheless this is retrospective research: prior project outcomes were known, "
        "and the 45 surrogates contain disclosed researcher choices. Treat the table as an auditable "
        "apples-to-apples comparison, not a pristine discovery holdout.",
        "",
        "## 1. Final disposition",
        "",
    ]
    if visual:
        lines.extend(["![Final milestone disposition](visual_figures/disposition_counts.png)", ""])
    lines.extend(disposition_table(rows))
    lines.extend(["", "[Full 69-paper audit table](visual_tables/complete_results_full_audit.csv)", ""])
    lines.extend(
        [
            "## 2. Raw common-path performance",
            "",
            "Sharpe ratios below are descriptive full-path outcomes after the common 10 bp cost. They "
            "do not measure fidelity to each paper's original reported universe or execution.",
            "",
        ]
    )
    if visual:
        lines.extend(["![Ranked annualized Sharpe](visual_figures/sharpe_by_strategy.png)", ""])
    lines.extend(extremes_table(rows, "full_annualized_sharpe", "Sharpe"))
    lines.extend(["", "[Full metric audit](visual_tables/complete_results_full_audit.csv)", ""])
    lines.extend(
        [
            "## 3. JKP benchmark attribution",
            "",
            "The point is the estimated return left after a rolling reconstruction from the frozen broad "
            "JKP panel. Intervals are pointwise HAC intervals; family inference uses 69 planned papers.",
            "",
        ]
    )
    if visual:
        lines.extend(["![JKP excess intervals](visual_figures/jkp_excess_intervals.png)", ""])
    lines.extend(extremes_table(rows, "jkp_excess_annualized", "JKP excess"))
    lines.extend(["", "[Full family-inference audit](visual_tables/family_inference_full_audit.csv)", ""])
    lines.extend(["## 4. Raw return versus benchmark distinctness", ""])
    if visual:
        lines.extend(["![CAGR versus JKP excess](visual_figures/cagr_vs_jkp_excess.png)", ""])
    lines.extend(
        [
            "| Evaluation class | Paths | Positive CAGR | Positive JKP excess | raw p < 5% |",
            "|---|---:|---:|---:|---:|",
            *category_rows,
            "",
            "[Full class summary](visual_tables/evaluation_class_summary_full_audit.csv)",
            "",
            "## 5. Fidelity and claim boundary",
            "",
            "- **Carried strict adaptations (17):** executable, source-anchored common paths already "
            "closed by the strict study. Labels such as `completed_partial` remain intact.",
            "- **In-spirit reconstructions (45):** researcher-authored deterministic or chronological "
            "substitutions. Each recipe lists preserved, approximated, and invented elements.",
            "- **Structural discards (7):** crypto, commodity-ETF, intraday, event-policy, or fixed daily-RL "
            "tasks whose central action geometry is not monthly cross-sectional U.S. stock selection.",
            "- **Native empirical claims (69):** none is adjudicated by this transfer study. Prior dossiers "
            "may verify formulas, source components, author outputs, or individual cells, but zero complete "
            "native systems were reproduced end to end under their original protocols.",
            "",
            "## 6. Metric contract",
            "",
            "| Item | Fixed definition |",
            "|---|---|",
            "| Universe | Top 1,000 U.S. stocks by formation market equity each month |",
            "| Calendar | July 1999 formations through November 2024; 305 realized months |",
            "| Portfolio | Value-weighted long/short signal deciles unless a source-specific adapter feeds that score |",
            "| Primary costs | 10 bp per one-way traded notional |",
            "| Missing returns | Zero without reweighting; adverse -100% path retained as sensitivity |",
            "| JKP attribution | Frozen rolling broad-characteristic reconstruction; 185-month evaluation window |",
            "| Multiplicity | Holm over the declared 69-paper family; discarded papers remain missing, not zero |",
            "",
            "[Complete metric and lineage audit](visual_tables/complete_results_full_audit.csv)",
            "",
            "## 7. Reproducibility and artifact index",
            "",
            "| Role | Artifact |",
            "|---|---|",
            "| Canonical 69-row result table | `visual_tables/complete_results_full_audit.csv` |",
            "| Ordered multiple-testing table | `visual_tables/family_inference_full_audit.csv` |",
            "| Evaluation-class counts | `visual_tables/evaluation_class_summary_full_audit.csv` |",
            "| Figure-first report | `VISUAL_REPORT.md` |",
            "| Table-first report | `REPORT.md` |",
            "| Hash and lineage manifest | `final_manifest.json` |",
            "",
            "Rebuild and validate from the repository root:",
            "",
            "```bash",
            "python scripts/build_us_jkp_in_spirit_final.py",
            "python scripts/validate_us_jkp_in_spirit_final.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(root: Path, destination: Path) -> None:
    rows, family, metric_inputs = load_results(root)
    destination.mkdir(parents=True, exist_ok=True)
    figures = destination / "visual_figures"
    tables = destination / "visual_tables"
    figures.mkdir(exist_ok=True)
    tables.mkdir(exist_ok=True)
    set_plot_style()
    save_dispositions(rows, figures / "disposition_counts.png")
    save_ranked(rows, "full_annualized_sharpe", figures / "sharpe_by_strategy.png", "Common-path annualized Sharpe, sorted", "Annualized Sharpe")
    save_excess_intervals(rows, figures / "jkp_excess_intervals.png")
    save_scatter(rows, figures / "cagr_vs_jkp_excess.png")

    (tables / "complete_results_full_audit.csv").write_bytes(csv_bytes(rows, RESULT_COLUMNS))
    family_columns = list(family[0])
    (tables / "family_inference_full_audit.csv").write_bytes(csv_bytes(family, family_columns))
    class_rows = []
    for status, label in (
        ("carried_common_evaluation", "carried_strict_adaptation"),
        ("completed_in_spirit", "researcher_authored_in_spirit"),
        ("discarded_structural_mismatch", "structural_discard"),
    ):
        group = [row for row in rows if row["disposition"] == status]
        evaluated = [row for row in group if row["common_jkp_evaluated"]]
        class_rows.append(
            {
                "evaluation_class": label,
                "paper_count": len(group),
                "common_path_count": len(evaluated),
                "positive_cagr_count": sum(float(row["full_cagr"]) > 0 for row in evaluated),
                "positive_jkp_excess_count": sum(float(row["jkp_excess_annualized"]) > 0 for row in evaluated),
                "raw_p_below_5pct_count": sum(float(row["jkp_excess_p_two_sided"]) < 0.05 for row in evaluated),
                "holm_reject_5pct_count": sum(bool(row["holm_reject_5pct"]) for row in evaluated),
            }
        )
    class_columns = list(class_rows[0])
    (tables / "evaluation_class_summary_full_audit.csv").write_bytes(csv_bytes(class_rows, class_columns))
    (destination / "VISUAL_REPORT.md").write_text(build_report(rows, family, True))
    (destination / "REPORT.md").write_text(build_report(rows, family, False))

    builder = Path(__file__).resolve()
    input_paths = [
        root / "paper_runs/us_jkp_in_spirit/milestones.json",
        root / "paper_runs/us_jkp_headline/benchmark_contract.json",
        root / "paper_runs/us_jkp_headline/cross_paper_summary.csv",
        *metric_inputs,
    ]
    outputs = sorted(
        path for path in destination.rglob("*") if path.is_file() and path.name != "final_manifest.json"
    )
    evaluated = [row for row in rows if row["common_jkp_evaluated"]]
    manifest = {
        "schema_version": 1,
        "study_id": STUDY_ID,
        "status": "complete",
        "paper_milestones": 69,
        "carried_strict_evaluations": 17,
        "researcher_authored_in_spirit_reconstructions": 45,
        "structural_discards": 7,
        "common_paths_evaluated": 62,
        "full_native_systems_reproduced_end_to_end": 0,
        "native_empirical_claims_tested": 0,
        "positive_full_cagr_count": sum(float(row["full_cagr"]) > 0 for row in evaluated),
        "positive_jkp_excess_count": sum(float(row["jkp_excess_annualized"]) > 0 for row in evaluated),
        "raw_primary_rejections_at_5pct": sum(float(row["jkp_excess_p_two_sided"]) < 0.05 for row in evaluated),
        "holm_family_size": 69,
        "holm_rejections_at_5pct": sum(bool(row["holm_reject_5pct"]) for row in evaluated),
        "claim_boundary": "Common JKP transfers do not reproduce or adjudicate the papers' complete native systems and original empirical protocols.",
        "input_sha256": {str(path.relative_to(root)): sha256_file(path) for path in input_paths},
        "builder_path": str(builder.relative_to(root)),
        "builder_sha256": sha256_file(builder),
        "output_sha256": {
            str(path.relative_to(destination)): sha256_file(path) for path in outputs
        },
    }
    (destination / "final_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")


def compare_outputs(expected: Path, actual: Path) -> list[str]:
    expected_files = {str(path.relative_to(expected)): path for path in expected.rglob("*") if path.is_file()}
    actual_files = {str(path.relative_to(actual)): path for path in actual.rglob("*") if path.is_file()}
    names = sorted(set(expected_files) | set(actual_files))
    return [
        name
        for name in names
        if name not in expected_files
        or name not in actual_files
        or expected_files[name].read_bytes() != actual_files[name].read_bytes()
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    destination = root / "paper_runs/us_jkp_in_spirit"
    if args.check:
        with tempfile.TemporaryDirectory(prefix="us_jkp_in_spirit_final_") as temporary:
            expected = Path(temporary)
            write_outputs(root, expected)
            stale = compare_outputs(expected, destination)
        if stale:
            raise SystemExit(f"stale or missing final synthesis outputs: {', '.join(stale)}")
        print("in-spirit final synthesis is current")
    else:
        write_outputs(root, destination)
        print("wrote final in-spirit synthesis")


if __name__ == "__main__":
    main()
