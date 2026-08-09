#!/usr/bin/env python3
"""Build U.S.-first ICAIF submission macros and figures from locked outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


WHITE = "#FFFFFF"
INK = "#17212B"
NAVY = "#16324F"
BLUE = "#276FBF"
TEAL = "#1B7F79"
GOLD = "#9A6700"
RULE = "#C7D2DE"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: pd.Series, q: float) -> float:
    ordered = np.sort(values.to_numpy(dtype=float))
    position = (len(ordered) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    if lo == hi:
        return float(ordered[lo])
    return float(ordered[lo] * (hi - position) + ordered[hi] * (position - lo))


def fmt_pct(value: float) -> str:
    return f"{100.0 * value:.2f}\\%"


def command(name: str, value: str | int) -> str:
    return f"\\newcommand{{\\{name}}}{{{value}\\xspace}}"


def verify_run(run_dir: Path) -> dict:
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    for filename in (
        "candidate_primary_results.csv",
        "candidate_cost_alpha_results.csv",
        "hac_lag_sensitivity.csv",
        "turnover_summary.csv",
    ):
        actual = sha256(run_dir / filename)
        expected = manifest["output_sha256"][filename]
        if actual != expected:
            raise RuntimeError(f"hash mismatch for {run_dir.name}/{filename}")
    return manifest


def verify_broad_run(run_dir: Path) -> dict:
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    for filename, expected in manifest["output_sha256"].items():
        actual = sha256(run_dir / filename)
        if actual != expected:
            raise RuntimeError(f"hash mismatch for {run_dir.name}/{filename}")
    if manifest.get("analysis_label") != "post_hoc_exploratory_broad_jkp_crossfit":
        raise RuntimeError("broad-JKP run is not labeled post-hoc exploratory")
    if float(manifest.get("market_alignment_correlation", 0.0)) < 0.99:
        raise RuntimeError("broad-JKP factor panel failed month-alignment validation")
    return manifest


def verify_missing_sensitivity(run_dir: Path) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("analysis_label") != "post_hoc_referee_requested_missing_return_sensitivity":
        raise RuntimeError("missing-return run has the wrong analysis label")
    for filename, expected in manifest["output_sha256"].items():
        if sha256(run_dir / filename) != expected:
            raise RuntimeError(f"missing-return sensitivity hash mismatch: {filename}")
    return manifest


def style_axis(ax) -> None:
    ax.set_facecolor(WHITE)
    ax.tick_params(colors=INK, labelcolor=INK)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)
    ax.title.set_color(NAVY)
    for spine in ax.spines.values():
        spine.set_color(RULE)


def save_figure(fig, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.patch.set_facecolor(WHITE)
    fig.savefig(destination, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)


def candidate_label(row: pd.Series | dict[str, Any]) -> str:
    candidate_id = str(row.get("candidate_id", "unnamed")).strip()
    proxy_code = "P-" + hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:6].upper()
    paper_ref = str(row.get("paper_ref", "")).strip()
    return f"{proxy_code} {paper_ref}" if paper_ref and paper_ref != "nan" else proxy_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    run_dir = root / "paper_runs/submission_evidence/usa_retrospective_corrected"
    international_dir = root / "paper_runs/submission_evidence/g7_ex_us_corrected"
    broad_dir = root / "paper_runs/submission_evidence/usa_broad_jkp_crossfit"
    missing_dir = root / "paper_runs/submission_evidence/usa_missing_return_sensitivity"
    mapping_dir = root / "paper_runs/submission_evidence/mapping_audit"
    forensic_dir = root / "paper_runs/submission_evidence/international_failure_forensics"
    waterfall_path = root / "paper_runs/submission_evidence/replication_scope/work_level_evidence_waterfall.csv"
    paper_dir = root / "docs/paper"
    manifest = verify_run(run_dir)
    verify_run(international_dir)
    broad_manifest = verify_broad_run(broad_dir)
    verify_missing_sensitivity(missing_dir)
    mapping_manifest = json.loads((mapping_dir / "manifest.json").read_text(encoding="utf-8"))
    forensic_manifest = json.loads((forensic_dir / "manifest.json").read_text(encoding="utf-8"))
    for filename, expected in mapping_manifest["output_sha256"].items():
        if sha256(mapping_dir / filename) != expected:
            raise RuntimeError(f"mapping-audit hash mismatch: {filename}")
    for filename, expected in forensic_manifest["output_sha256"].items():
        if sha256(forensic_dir / filename) != expected:
            raise RuntimeError(f"international-forensic hash mismatch: {filename}")

    waterfall = pd.read_csv(waterfall_path)
    if len(waterfall) != 98 or waterfall["canonical_work_id"].nunique() != 98:
        raise RuntimeError("work-level evidence waterfall is not a 98-work partition")
    waterfall_counts = {
        "retained": int((waterfall["screen_decision"] == "retained_formula_or_trading").sum()),
        "excluded": int((waterfall["screen_decision"] == "screened_out").sum()),
        "reconstructed": int((waterfall["good_faith_reconstruction"] == "yes").sum()),
        "availability_only": int((waterfall["reconstruction_fidelity"] == "availability_only").sum()),
        "grounded_works": int((waterfall["reconstruction_fidelity"] == "source_grounded_component_test").sum()),
        "narrative_works": int((waterfall["reconstruction_fidelity"] == "narrative_favorable_stress_test").sum()),
        "retained_code_attempts": int((waterfall["direct_code_route"] == "retained_code_attempt").sum()),
        "diagnostic_code_attempts": int((waterfall["direct_code_route"] == "diagnostic_code_attempt").sum()),
        "mappings": int(waterfall["mapping_count"].sum()),
    }
    if waterfall_counts != {
        "retained": 69, "excluded": 29, "reconstructed": 40,
        "availability_only": 29, "grounded_works": 5, "narrative_works": 35,
        "retained_code_attempts": 8, "diagnostic_code_attempts": 6, "mappings": 50,
    }:
        raise RuntimeError(f"work-level evidence waterfall changed: {waterfall_counts}")

    primary = pd.read_csv(run_dir / "candidate_primary_results.csv")
    costs = pd.read_csv(run_dir / "candidate_cost_alpha_results.csv")
    turnover = pd.read_csv(run_dir / "turnover_summary.csv")
    hac = pd.read_csv(run_dir / "hac_lag_sensitivity.csv")
    missing_summary = pd.read_csv(missing_dir / "policy_summary.csv").set_index("policy")
    ok = primary.loc[primary["status"] == "ok"].copy()
    if len(primary) != 62 or len(ok) != 62:
        raise RuntimeError("U.S. primary family is not 62/62 executable")

    alpha = ok["alpha_annualized"].astype(float)
    cost_ok = costs.loc[costs["status"] == "ok"].copy()
    wide = cost_ok.pivot(index="candidate_id", columns="cost_bps_one_way", values="alpha_annualized")
    schedule = [0, 5, 10, 25, 50]
    wide = wide.reindex(columns=schedule)
    if wide.shape != (62, 5) or wide.isna().any().any():
        raise RuntimeError("U.S. cost panel is not a complete 62 by 5 family")
    if set(missing_summary.index) != {"zero_primary", "position_adverse_100"}:
        raise RuntimeError("missing-return sensitivity lacks the two required policies")
    adverse_missing = missing_summary.loc["position_adverse_100"]
    if int(adverse_missing["n_estimable"]) != 62:
        raise RuntimeError("missing-return sensitivity is not a complete 62-mapping family")
    turnover_values = turnover.loc[turnover["valid_months"] > 0, "median_monthly_traded_notional"].astype(float)
    positive_gross = turnover.loc[turnover["gross_alpha_annualized"] > 0].copy()
    if len(positive_gross) != 46 or positive_gross["alpha_break_even_cost_bps"].isna().any():
        raise RuntimeError("gross-positive break-even-cost family changed")
    broad = pd.read_csv(broad_dir / "broad_jkp_crossfit_results.csv")
    if len(broad) != 62 or int(broad["n_benchmark_factors"].iloc[0]) != 133:
        raise RuntimeError("broad-JKP result is not a complete 62 by 133-factor audit")
    broad_best = broad.sort_values("alpha_annualized", ascending=False).iloc[0]

    lag_counts = []
    for lag in (0, 3, 6, 12):
        group = hac.loc[hac["fixed_hac_lags"] == lag]
        nominal = int(((group["alpha_annualized"] > 0) & (group["p_value_two_sided"] <= 0.05)).sum())
        p = group["p_value_two_sided"].where(group["alpha_annualized"] > 0, 1.0).sort_values().to_numpy()
        rejected = 0
        for index, value in enumerate(p):
            if value <= 0.05 / (len(p) - index):
                rejected += 1
            else:
                break
        lag_counts.append((lag, nominal, rejected))

    cost_holm_counts = []
    for cost_bps in schedule:
        group = cost_ok.loc[cost_ok["cost_bps_one_way"] == cost_bps]
        p = group["p_value_two_sided"].where(group["alpha_annualized"] > 0, 1.0).sort_values().to_numpy()
        rejected = 0
        for index, value in enumerate(p):
            if value <= 0.05 / (len(p) - index):
                rejected += 1
            else:
                break
        cost_holm_counts.append(rejected)

    macros = [
        "% Generated by scripts/build_icaif2026_submission_assets.py; do not edit by hand.",
        "% U.S.-primary values are computed from hash-verified frozen outputs.",
        command("USRegressionMonthCount", int(ok["n_months"].iloc[0])),
        command("USRegressionStartMonth", "August 2001"),
        command("USRegressionEndMonth", "December 2024"),
        command("USMedianAlphaPct", fmt_pct(float(alpha.median()))),
        command("USAlphaIQRPct", f"[{fmt_pct(percentile(alpha, 0.25))}, {fmt_pct(percentile(alpha, 0.75))}]"),
        command("USPositiveAlphaCount", int((alpha > 0).sum())),
        command("USNominalCount", int(((ok["alpha_annualized"] > 0) & (ok["p_value_two_sided"] <= 0.05)).sum())),
        command("USHolmPositiveCount", int(((ok["alpha_annualized"] > 0) & (ok["holm_p_value"] <= 0.05)).sum())),
        command("USMaxTPositiveCount", int(((ok["alpha_annualized"] > 0) & (ok["max_abs_t_p_value"] <= 0.05)).sum())),
        command("USEconomicConfirmedCount", int((ok["simultaneous_ci_low_annualized"] >= 0.02).sum())),
        command("USRealityCheckP", f"{manifest['bootstrap']['white_reality_check_style_p_value']:.4f}"),
        command("USBestAlphaPct", fmt_pct(float(alpha.max()))),
        command("USBestSimultaneousLowerPct", fmt_pct(float(ok.loc[ok["alpha_annualized"].idxmax(), "simultaneous_ci_low_annualized"]))),
        command("USMedianTurnover", f"{float(turnover_values.median()):.2f}"),
        command("USTurnoverIQR", f"{percentile(turnover_values, 0.25):.2f}--{percentile(turnover_values, 0.75):.2f}"),
        command("USMedianCostDragPct", fmt_pct(float((wide[0] - wide[10]).median()))),
        command("USCrossSectionMedianCostShiftPct", fmt_pct(float(wide[0].median() - wide[10].median()))),
        command("USMedianAlphaAtFivePct", fmt_pct(float(wide[5].median()))),
        command("USPositiveAtZero", int((wide[0] > 0).sum())),
        command("USPositiveAtFive", int((wide[5] > 0).sum())),
        command("USPositiveAtTen", int((wide[10] > 0).sum())),
        command("USPositiveAtTwentyFive", int((wide[25] > 0).sum())),
        command("USPositiveAtFifty", int((wide[50] > 0).sum())),
        command("USMedianGrossAlphaPct", fmt_pct(float(wide[0].median()))),
        command("USCostHolmCounts", "/".join(str(value) for value in cost_holm_counts)),
        command("USGrossPositiveBreakEvenMedianBps", f"{positive_gross['alpha_break_even_cost_bps'].median():.1f}"),
        command("USGrossPositiveBreakEvenIQRBps", (
            f"{percentile(positive_gross['alpha_break_even_cost_bps'], 0.25):.1f}--"
            f"{percentile(positive_gross['alpha_break_even_cost_bps'], 0.75):.1f}"
        )),
        command("USMedianCandidateMeanMissingPct", fmt_pct(float(
            adverse_missing["median_candidate_mean_missing_return_gross_weight"]
        ))),
        command("USMaxCandidateMeanMissingPct", fmt_pct(float(
            adverse_missing["max_candidate_mean_missing_return_gross_weight"]
        ))),
        command("USAdverseMissingMedianAlphaPct", fmt_pct(float(
            adverse_missing["median_alpha_annualized"]
        ))),
        command("USAdverseMissingPositiveCount", int(adverse_missing["positive_alpha_count"])),
        command("USAdverseMissingNominalCount", int(adverse_missing["nominal_positive_5pct"])),
        command("USAdverseMissingHolmCount", int(adverse_missing["holm_positive_5pct"])),
        command("USHACLagNominalCounts", "/".join(str(row[1]) for row in lag_counts)),
        command("USHACLagHolmCounts", "/".join(str(row[2]) for row in lag_counts)),
        command("BroadEvaluationMonthCount", int(broad["n_evaluation_months"].iloc[0])),
        command("BroadEvaluationStartMonth", "August 2011"),
        command("BroadEvaluationEndMonth", "January 2022"),
        command("BroadPositiveAlphaCount", int((broad["alpha_annualized"] > 0).sum())),
        command("BroadNominalPositiveCount", int(((broad["alpha_annualized"] > 0) & (broad["p_value_two_sided"] <= 0.05)).sum())),
        command("BroadHolmPositiveCount", int(((broad["alpha_annualized"] > 0) & (broad["holm_p_value"] <= 0.05)).sum())),
        command("BroadMaxTPositiveCount", int(((broad["alpha_annualized"] > 0) & (broad["max_abs_t_p_value"] <= 0.05)).sum())),
        command("BroadEconomicConfirmedCount", int((broad["simultaneous_ci_low_annualized"] >= 0.02).sum())),
        command("BroadBestAlphaPct", fmt_pct(float(broad_best["alpha_annualized"]))),
        command("BroadBestRawP", f"{float(broad_best['p_value_two_sided']):.4f}"),
        command("BroadBestHolmP", f"{float(broad_best['holm_p_value']):.3f}"),
        command("BroadBestMaxTP", f"{float(broad_best['max_abs_t_p_value']):.3f}"),
        command("BroadBestSimultaneousLowerPct", fmt_pct(float(broad_best["simultaneous_ci_low_annualized"]))),
        command("BroadMarketAlignmentCorrelation", f"{float(broad_manifest['market_alignment_correlation']):.3f}"),
        command("MappingNarrativeCount", 49),
        command("MappingPartialCount", 12),
        command("MappingReleasedSeedCount", 1),
        command("MappingAlternativeCandidateCount", int(mapping_manifest["sensitivity"]["candidates_covered_by_existing_alternatives"])),
        command("MappingCombinationCount", int(mapping_manifest["sensitivity"]["one_mapping_per_source_combinations"])),
        command("InternationalFailureEventCount", int(forensic_manifest["failure_events"])),
        command("InternationalFailureCandidateCount", int(forensic_manifest["failure_candidates"])),
        command("InternationalExtremeShortCount", int(forensic_manifest["single_extreme_short_position_dominates"])),
        command("InternationalTwoCellCount", int(forensic_manifest["events_in_two_largest_month_cells"])),
    ]
    paper_dir.mkdir(parents=True, exist_ok=True)
    result_path = paper_dir / "icaif2026_results.tex"
    with tempfile.NamedTemporaryFile("w", dir=paper_dir, delete=False, encoding="utf-8") as handle:
        handle.write("\n".join(macros) + "\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, result_path)

    plt.rcParams.update({
        "font.size": 10,
        "axes.labelcolor": INK,
        "axes.edgecolor": RULE,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "figure.facecolor": WHITE,
        "savefig.facecolor": WHITE,
    })
    fig, ax = plt.subplots(figsize=(11.2, 5.0), facecolor=WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.7)
    ax.axis("off")

    from matplotlib.path import Path as MplPath
    from matplotlib.patches import FancyBboxPatch, PathPatch, Rectangle

    SLATE = "#718096"
    PALE_BLUE = "#EAF2FA"
    PALE_TEAL = "#E6F4F2"
    PALE_GOLD = "#FBF2DF"
    PALE_SLATE = "#EEF1F4"

    def ribbon(x0, x1, source, target, color, alpha=0.25):
        source_low, source_high = source
        target_low, target_high = target
        control = 0.43 * (x1 - x0)
        vertices = [
            (x0, source_low),
            (x0 + control, source_low),
            (x1 - control, target_low),
            (x1, target_low),
            (x1, target_high),
            (x1 - control, target_high),
            (x0 + control, source_high),
            (x0, source_high),
            (x0, source_low),
        ]
        codes = [
            MplPath.MOVETO,
            MplPath.CURVE4,
            MplPath.CURVE4,
            MplPath.CURVE4,
            MplPath.LINETO,
            MplPath.CURVE4,
            MplPath.CURVE4,
            MplPath.CURVE4,
            MplPath.CLOSEPOLY,
        ]
        ax.add_patch(
            PathPatch(
                MplPath(vertices, codes),
                facecolor=color,
                edgecolor=color,
                linewidth=0.7,
                alpha=alpha,
                zorder=1,
            )
        )

    def node(x, span, color):
        low, high = span
        ax.add_patch(
            Rectangle(
                (x - 0.08, low),
                0.16,
                high - low,
                facecolor=color,
                edgecolor=WHITE,
                linewidth=0.7,
                zorder=3,
            )
        )

    def label(x, y, title, detail, color, fill, align="left", title_size=9.5):
        offset = 0.17 if align == "left" else -0.17
        ha = "left" if align == "left" else "right"
        ax.text(
            x + offset,
            y + 0.12,
            title,
            ha=ha,
            va="center",
            fontsize=title_size,
            fontweight="bold",
            color=color,
            zorder=4,
            bbox=dict(boxstyle="round,pad=0.16", facecolor=fill, edgecolor="none", alpha=0.96),
        )
        ax.text(
            x + offset,
            y - 0.18,
            detail,
            ha=ha,
            va="center",
            fontsize=8.3,
            color=INK,
            zorder=4,
            bbox=dict(boxstyle="round,pad=0.12", facecolor=fill, edgecolor="none", alpha=0.96),
        )

    x_screen, x_scope, x_coverage, x_tier = 0.85, 3.55, 6.45, 9.25
    scale = 3.05 / 98.0
    screened = (1.55, 4.60)
    screened_excluded = (screened[0], screened[0] + 29 * scale)
    screened_retained = (screened_excluded[1], screened[1])

    retained = (2.43, 2.43 + 69 * scale)
    excluded = (1.22, 1.22 + 29 * scale)
    retained_availability_source = (retained[0], retained[0] + 29 * scale)
    retained_reconstructed_source = (retained_availability_source[1], retained[1])

    reconstructed = (3.35, 3.35 + 40 * scale)
    availability = (2.12, 2.12 + 29 * scale)
    reconstructed_narrative_source = (reconstructed[0], reconstructed[0] + 35 * scale)
    reconstructed_grounded_source = (reconstructed_narrative_source[1], reconstructed[1])

    narrative = (3.05, 3.05 + 35 * scale)
    grounded = (4.48, 4.48 + 5 * scale)

    ribbon(x_screen, x_scope, screened_retained, retained, BLUE)
    ribbon(x_screen, x_scope, screened_excluded, excluded, SLATE, alpha=0.20)
    ribbon(x_scope, x_coverage, retained_reconstructed_source, reconstructed, BLUE)
    ribbon(x_scope, x_coverage, retained_availability_source, availability, SLATE, alpha=0.20)
    ribbon(x_coverage, x_tier, reconstructed_grounded_source, grounded, TEAL, alpha=0.28)
    ribbon(x_coverage, x_tier, reconstructed_narrative_source, narrative, GOLD, alpha=0.23)

    node(x_screen, screened, NAVY)
    node(x_scope, retained, BLUE)
    node(x_scope, excluded, SLATE)
    node(x_coverage, reconstructed, BLUE)
    node(x_coverage, availability, SLATE)
    node(x_tier, grounded, TEAL)
    node(x_tier, narrative, GOLD)

    stage_headers = [
        (x_screen, "01  LITERATURE SCREEN"),
        (x_scope, "02  SCOPE DECISION"),
        (x_coverage, "03  COMMON-TASK COVERAGE"),
        (x_tier, "04  EVIDENCE TIER"),
    ]
    for x, text_value in stage_headers:
        ax.text(
            x,
            4.95,
            text_value,
            ha="center",
            va="center",
            fontsize=8.5,
            fontweight="bold",
            color=SLATE,
            zorder=5,
        )
        ax.plot([x - 0.62, x + 0.62], [4.82, 4.82], color=RULE, linewidth=0.8, zorder=2)

    label(x_screen, 3.18, "SCREENED CORPUS", "98 works | 103 lineages", NAVY, WHITE, align="right")
    label(x_scope, 3.88, "RETAINED METHODS", "69 works | 67 lineages", BLUE, PALE_BLUE)
    label(x_scope, 1.67, "SCREENED OUT", "29 works", SLATE, PALE_SLATE)
    label(x_coverage, 4.06, "RECONSTRUCTED", "40 works | 50 mappings", BLUE, PALE_BLUE)
    label(x_coverage, 2.46, "AVAILABILITY ONLY", "29 works | no alpha inference", SLATE, PALE_SLATE)
    label(x_tier, 4.56, "SOURCE-GROUNDED", "5 works | 13 component tests", TEAL, PALE_TEAL)
    label(x_tier, 3.58, "NARRATIVE STRESS TESTS", "35 works | 37 favorable mappings", GOLD, PALE_GOLD)

    audit = FancyBboxPatch(
        (2.00, 0.20),
        9.55,
        0.72,
        boxstyle="round,pad=0.04,rounding_size=0.06",
        linewidth=1.15,
        edgecolor=NAVY,
        facecolor="#F5F8FB",
        linestyle=(0, (4, 3)),
        zorder=2,
    )
    ax.add_patch(audit)
    ax.text(
        3.12,
        0.68,
        "OVERLAPPING CODE AUDIT",
        ha="center",
        va="center",
        fontsize=8.3,
        fontweight="bold",
        color=NAVY,
        zorder=4,
    )
    ax.text(
        3.12,
        0.42,
        "not part of the work partition",
        ha="center",
        va="center",
        fontsize=7.4,
        color=SLATE,
        zorder=4,
    )
    audit_metrics = [
        (4.90, "14", "attempts"),
        (6.45, "8 + 6", "retained + diagnostic"),
        (8.25, "0", "native replications"),
        (10.10, "1", "seed adaptation"),
    ]
    for separator_x in (4.25, 5.60, 7.35, 9.15):
        ax.plot([separator_x, separator_x], [0.34, 0.79], color=RULE, linewidth=0.8, zorder=3)
    for x, value, description in audit_metrics:
        ax.text(x, 0.67, value, ha="center", va="center", fontsize=10.2, fontweight="bold", color=NAVY, zorder=4)
        ax.text(x, 0.40, description, ha="center", va="center", fontsize=7.6, color=INK, zorder=4)

    ax.text(
        6.0,
        5.50,
        "Evidence waterfall: from 98 works to 13 source-grounded component tests",
        ha="center",
        va="top",
        fontsize=12.8,
        fontweight="bold",
        color=NAVY,
    )
    ax.text(
        6.0,
        1.02,
        "Ribbon widths are proportional to work counts; availability-only works are never assigned zero returns.",
        ha="center",
        va="bottom",
        fontsize=8.1,
        color=INK,
    )
    save_figure(fig, paper_dir / "figures/claim_to_test_pipeline.pdf")

    fig, ax = plt.subplots(figsize=(9.6, 5.6), facecolor=WHITE)
    style_axis(ax)
    x = np.asarray(schedule, dtype=float)
    for _, row in wide.iterrows():
        ax.plot(x, 100.0 * row.to_numpy(dtype=float), color=BLUE, alpha=0.10, linewidth=0.75, zorder=1)
    quantiles = wide.quantile([0.25, 0.5, 0.75], axis=0)
    q1 = 100.0 * quantiles.loc[0.25].to_numpy(dtype=float)
    median = 100.0 * quantiles.loc[0.5].to_numpy(dtype=float)
    q3 = 100.0 * quantiles.loc[0.75].to_numpy(dtype=float)
    ax.fill_between(x, q1, q3, color=TEAL, alpha=0.20, label="Interquartile range", zorder=2)
    ax.plot(x, median, color=NAVY, linewidth=2.4, marker="o", label="Median", zorder=3)
    ax.axvline(10, color=GOLD, linewidth=1.5, linestyle="--", label="Primary 10 bp", zorder=2)
    ax.axhline(0, color=INK, linewidth=0.9, zorder=1)
    ax.set_xticks(x)
    ax.set_xlabel("One-way transaction cost (basis points)")
    ax.set_ylabel("Annualized U.S. factor alpha (%)")
    ax.set_title("Primary U.S. benchmark: alpha sensitivity to trading costs", pad=12)
    ax.grid(alpha=0.42)
    ax.set_axisbelow(True)
    legend = ax.legend(loc="best", facecolor=WHITE, edgecolor=RULE, framealpha=1.0)
    for label in legend.get_texts():
        label.set_color(INK)
    save_figure(fig, paper_dir / "figures/usa_cost_sensitivity.pdf")

    international = pd.read_csv(international_dir / "candidate_primary_results.csv")
    international_ok = (
        international.loc[international["status"] == "ok"]
        .assign(_alpha=lambda frame: pd.to_numeric(frame["alpha_annualized"]))
        .sort_values("_alpha", ascending=False)
        .reset_index(drop=True)
    )
    international_failed = international.loc[international["status"] != "ok"]
    if len(international) != 62 or len(international_ok) != 27 or len(international_failed) != 35:
        raise RuntimeError("international family is not 62 planned / 27 executable / 35 failed")

    display = {
        "paper_factormad_debate_interpretable": ("FactorMAD", "value + profitability + safety + momentum - leverage - volatility"),
        "guru_graham_deep_value_defensive": ("GuruAgents--Graham", "value + cash + profitability - leverage - volatility - beta"),
        "code_ai_trader_value_quality": ("AI-Trader", "value + quality + profitability + cash - leverage - volatility"),
        "paper_alpha_gpt_interactive_formula": ("Alpha-GPT", "value + momentum + profitability + gross profits - leverage"),
        "guru_greenblatt_magic_formula": ("GuruAgents--Greenblatt", "earnings yield + profitability + gross profits + value"),
        "fama_value_momentum_interpretable": ("FAMA", "value + momentum + profitability - size"),
        "paper_factorminer_memory_diverse_library": ("FactorMiner", "momentum + value + profitability + safety + turnover - risk"),
        "alphaagents_risk_averse_quality_lowrisk": ("AlphaAgents", "quality + profitability + value - volatility - beta - leverage"),
        "paper_factorengine_program_knowledge": ("FactorEngine", "value + profitability + cash flow - accruals - leverage - investment"),
        "repo_alphaprobe_dag_diverse_factor_blend": ("AlphaPROBE", "momentum + value + profitability + safety + turnover - risk"),
        "repo_deepfund_prudent_fund_manager": ("DeepFund", "long-only quality + profitability + cash + momentum - risk"),
    }
    survivors = international_ok.loc[
        (international_ok["alpha_annualized"] > 0) & (international_ok["holm_p_value"] <= 0.05)
    ].copy()
    if len(survivors) != 11 or set(survivors["candidate_id"]) != set(display):
        raise RuntimeError("international Holm-survivor registry changed")
    table_path = paper_dir / "tables/international_holm_survivors.tex"
    table_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for _, row in survivors.sort_values("alpha_annualized", ascending=False).iterrows():
        label, mechanism = display[row["candidate_id"]]
        p_value = float(row["holm_p_value"])
        p_text = "$<.001$" if p_value < 0.001 else f"{p_value:.3f}"
        lines.append(
            f"{label} & {mechanism} & {100*float(row['alpha_annualized']):.2f} & {p_text} & {100*float(row['simultaneous_ci_low_annualized']):.2f}"
        )
    with tempfile.NamedTemporaryFile("w", dir=table_path.parent, delete=False, encoding="utf-8") as handle:
        row_separator = " " + r"\\" + "\n"
        handle.write(row_separator.join(lines) + "\n")
        temp_table = Path(handle.name)
    os.replace(temp_table, table_path)
    y = np.arange(len(international_ok))
    fig, ax = plt.subplots(figsize=(8.0, max(7.4, 0.31 * len(international_ok))), facecolor=WHITE)
    style_axis(ax)
    for index, row in international_ok.iterrows():
        alpha_value = 100.0 * float(row["alpha_annualized"])
        low = 100.0 * float(row["ci_low_annualized"])
        high = 100.0 * float(row["ci_high_annualized"])
        positive = alpha_value > 0
        ax.errorbar(
            alpha_value,
            index,
            xerr=np.array([[alpha_value - low], [high - alpha_value]]),
            fmt="o",
            markersize=4.6,
            markerfacecolor=TEAL if positive else WHITE,
            markeredgecolor=TEAL if positive else BLUE,
            ecolor="#53677A",
            elinewidth=1.0,
            capsize=1.8,
            zorder=3,
        )
    ax.axvline(0.0, color=INK, linewidth=1.0, zorder=1)
    ax.axvline(2.0, color=GOLD, linewidth=1.1, linestyle="--", zorder=1)
    ax.set_yticks(y, [candidate_label(row) for _, row in international_ok.iterrows()], fontsize=7.2)
    ax.invert_yaxis()
    for label in ax.get_yticklabels():
        label.set_color(INK)
    finite_ci = pd.concat(
        [international_ok["ci_low_annualized"], international_ok["ci_high_annualized"]]
    ).astype(float)
    x_low = min(-1.0, 100.0 * float(finite_ci.min()))
    x_high = max(3.0, 100.0 * float(finite_ci.max()))
    margin = 0.08 * (x_high - x_low)
    ax.set_xlim(x_low - margin, x_high + margin)
    ax.set_xlabel("Annualized factor alpha (%)")
    ax.set_title("International extension: 27 executable paths", pad=12)
    ax.grid(axis="x", alpha=0.45)
    ax.set_axisbelow(True)
    ax.text(
        0.01,
        1.005,
        "Dashed gold line: 2 pp threshold; 35 additional family members have no return estimate",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        color=INK,
    )
    save_figure(fig, paper_dir / "figures/g7_alpha_forest.pdf")

    fixed = pd.read_csv(
        root / "paper_runs/submission_evidence/fixed_calendar_diagnostics/fixed_calendar_country_loo.csv"
    )
    paired = fixed.loc[fixed["diagnostic"] == "g7_usa_common_calendar", ["candidate_id", "alpha_annualized"]]
    paired = paired.rename(columns={"alpha_annualized": "alpha_international"}).merge(
        ok[["candidate_id", "alpha_annualized", "paper_ref"]].rename(
            columns={"alpha_annualized": "alpha_usa"}
        ),
        on="candidate_id",
        how="inner",
        validate="one_to_one",
    )
    if len(paired) != 27:
        raise RuntimeError("transport panel does not contain 27 jointly estimable paths")
    x_values = 100.0 * paired["alpha_usa"].to_numpy(dtype=float)
    y_values = 100.0 * paired["alpha_international"].to_numpy(dtype=float)
    correlation = float(pd.Series(x_values).corr(pd.Series(y_values), method="spearman"))
    fig, ax = plt.subplots(figsize=(7.5, 6.7), facecolor=WHITE)
    style_axis(ax)
    ax.scatter(
        x_values,
        y_values,
        s=42,
        c=TEAL,
        edgecolors=WHITE,
        linewidths=0.7,
        alpha=0.90,
        zorder=3,
    )
    low = min(float(x_values.min()), float(y_values.min()))
    high = max(float(x_values.max()), float(y_values.max()))
    margin = 0.08 * max(1.0, high - low)
    low, high = low - margin, high + margin
    ax.plot([low, high], [low, high], color="#53677A", linewidth=1.2, linestyle="--", zorder=1)
    ax.axhline(0, color=INK, linewidth=0.8, alpha=0.7)
    ax.axvline(0, color=INK, linewidth=0.8, alpha=0.7)
    disagreement = np.abs(y_values - x_values)
    for index in np.argsort(disagreement)[-min(8, len(paired)):]:
        ax.annotate(
            candidate_label(paired.iloc[index]),
            (x_values[index], y_values[index]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=7,
            color=INK,
        )
    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_xlabel("Primary U.S. annualized alpha (%)")
    ax.set_ylabel("International-extension annualized alpha (%)")
    ax.set_title(f"Transport among 27 jointly estimable proxies (Spearman {correlation:.3f})", pad=12)
    ax.grid(alpha=0.42)
    ax.set_axisbelow(True)
    save_figure(fig, paper_dir / "figures/usa_g7_transfer.pdf")

    print(f"wrote {result_path}")
    print(f"wrote {paper_dir / 'figures/usa_cost_sensitivity.pdf'}")
    print(f"wrote {paper_dir / 'figures/claim_to_test_pipeline.pdf'}")
    print(f"wrote {paper_dir / 'figures/g7_alpha_forest.pdf'}")
    print(f"wrote {paper_dir / 'figures/usa_g7_transfer.pdf'}")
    print(f"wrote {table_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
