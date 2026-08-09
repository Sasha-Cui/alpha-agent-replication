#!/usr/bin/env python3
"""Build U.S.-first ICAIF submission macros and figures from locked outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.switch_backend("Agg")


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


def verify_retained_ladder(run_dir: Path) -> dict:
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    for filename, expected in manifest["output_sha256"].items():
        actual = sha256(run_dir / filename)
        if actual != expected:
            raise RuntimeError(f"retained-ladder hash mismatch: {filename}")
    if manifest.get("analysis_label") != "post_hoc_matched_retained_benchmark_ladder":
        raise RuntimeError("retained benchmark ladder has the wrong analysis label")
    if manifest.get("strategy_count") != 50 or manifest.get("paper_count") != 40:
        raise RuntimeError("retained benchmark ladder has the wrong denominator")
    if int(manifest.get("evaluation_months", 0)) != 126:
        raise RuntimeError("retained benchmark ladder has the wrong calendar")
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
    fig.savefig(
        destination,
        bbox_inches="tight",
        facecolor=WHITE,
        metadata={"Creator": "alpha-agent-replication", "CreationDate": None, "ModDate": None},
    )
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
    ladder_dir = root / "paper_runs/submission_evidence/retained_benchmark_ladder"
    source_benchmark_dir = root / "paper_runs/submission_evidence/source_benchmark_audit"
    missing_dir = root / "paper_runs/submission_evidence/usa_missing_return_sensitivity"
    mapping_dir = root / "paper_runs/submission_evidence/mapping_audit"
    forensic_dir = root / "paper_runs/submission_evidence/international_failure_forensics"
    waterfall_path = root / "paper_runs/submission_evidence/replication_scope/work_level_evidence_waterfall.csv"
    paper_dir = root / "docs/paper"
    manifest = verify_run(run_dir)
    verify_run(international_dir)
    broad_manifest = verify_broad_run(broad_dir)
    ladder_manifest = verify_retained_ladder(ladder_dir)
    source_benchmark_manifest = json.loads(
        (source_benchmark_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    if source_benchmark_manifest.get("analysis_label") != (
        "source_paper_benchmark_audit_and_heterogeneity"
    ):
        raise RuntimeError("source-paper benchmark audit has the wrong analysis label")
    for filename, expected in source_benchmark_manifest["output_sha256"].items():
        if sha256(source_benchmark_dir / filename) != expected:
            raise RuntimeError(
                f"source-paper benchmark audit hash mismatch: {filename}"
            )
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
    mapping_audit = pd.read_csv(mapping_dir / "mapping_audit.csv")
    direct_summary = pd.read_csv(root / "paper_runs/repository_ff5mom_metrics_summary.csv")
    missing_summary = pd.read_csv(missing_dir / "policy_summary.csv").set_index("policy")
    ok = primary.loc[primary["status"] == "ok"].copy()
    if len(primary) != 62 or len(ok) != 62:
        raise RuntimeError("U.S. primary family is not 62/62 executable")

    direct_ok = direct_summary.loc[direct_summary["metric_status"] == "computed_jkp_only"].copy()
    if len(direct_ok) != 1 or direct_ok.iloc[0]["candidate_id"] != "quantevolver_return_sharpe_60_proxy":
        raise RuntimeError("direct-code summary does not contain the sole QuantEvolver seed adaptation")
    direct_row = direct_ok.iloc[0]
    expected_direct = {
        "candidate_standalone_oos_sharpe": 0.3159540989730854,
        "alpha_annualized": 0.0032849190887483,
        "alpha_tstat_hac": 0.6514961447297817,
        "n_overlap_months": 305.0,
    }
    for field, expected in expected_direct.items():
        if not math.isclose(float(direct_row[field]), expected, rel_tol=0.0, abs_tol=1e-12):
            raise RuntimeError(f"direct-code {field} changed")

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
    ladder_results = pd.read_csv(ladder_dir / "strategy_benchmark_results.csv")
    ladder_summary = pd.read_csv(ladder_dir / "benchmark_summary.csv")
    ladder_comparison = pd.read_csv(ladder_dir / "strategy_benchmark_comparison.csv")
    top_factor_frequency = pd.read_csv(ladder_dir / "top_jkp_factor_frequency.csv")
    top_factor_rows = pd.read_csv(ladder_dir / "strategy_top_jkp_factors.csv")
    if len(ladder_results) != 200 or ladder_results["candidate_id"].nunique() != 50:
        raise RuntimeError("retained benchmark ladder is not a complete 50 by 4 panel")
    if len(ladder_comparison) != 50 or ladder_comparison["canonical_work_id"].nunique() != 40:
        raise RuntimeError("retained strategy comparison does not cover 40 papers")
    expected_models = {"capm": 1, "ff3": 3, "ff5_mom": 6, "ff5_mom_jkp132": 133}
    observed_models = (
        ladder_results.groupby("benchmark_id")["n_benchmark_returns"].first().to_dict()
    )
    if observed_models != expected_models:
        raise RuntimeError(f"matched benchmark definitions changed: {observed_models}")
    ladder_all = ladder_summary[ladder_summary["implementation_basis"].eq("all_retained")]
    ladder_all = ladder_all.set_index("benchmark_id").loc[list(expected_models)]
    ladder_grounded = ladder_results[
        ~ladder_results["implementation_basis"].eq("in_spirit_reconstruction")
    ]
    ladder_in_spirit = ladder_results[
        ladder_results["implementation_basis"].eq("in_spirit_reconstruction")
    ]
    top_one = top_factor_rows[
        top_factor_rows["factor_rank_by_absolute_correlation"].eq(1)
    ]
    if len(ladder_grounded) != 13 * 4 or len(ladder_in_spirit) != 37 * 4 or len(top_one) != 50:
        raise RuntimeError("retained provenance or top-factor partition changed")
    readable_factors = {
        "betabab_1260d": "Betting-against-beta",
        "prc_highprc_252d": "52-week-high proximity",
        "rvol_21d": "Realized volatility",
        "ivol_capm_252d": "Idiosyncratic volatility",
        "qmj_safety": "Quality-minus-junk safety",
        "ret_12_1": "12--1 momentum",
        "betadown_252d": "Downside beta",
        "ebitda_mev": "EBITDA/enterprise value",
        "ret_3_1": "3--1 momentum",
        "rmax5_21d": "Average five highest daily returns",
    }
    top_factor_table = top_factor_frequency.head(10).copy()
    if len(top_factor_table) != 10:
        raise RuntimeError("top-factor table does not contain ten rows")
    top_factor_table["label"] = top_factor_table["jkp_factor_id"].map(
        readable_factors
    )
    if top_factor_table["label"].isna().any():
        raise RuntimeError("top-factor table contains an unlabeled JKP characteristic")

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
        command("RetainedBacktestPaperCount", 40),
        command("RetainedBacktestStrategyCount", 50),
        command("LadderEvaluationMonthCount", int(ladder_manifest["evaluation_months"])),
        command("LadderCAPMPositiveCount", int(ladder_all.loc["capm", "positive_alpha_estimates"])),
        command("LadderCAPMNominalCount", int(ladder_all.loc["capm", "nominal_positive_5pct"])),
        command("LadderCAPMHolmCount", int(ladder_all.loc["capm", "holm_positive_5pct"])),
        command("LadderCAPMMedianAlphaPct", fmt_pct(float(ladder_all.loc["capm", "median_alpha_annualized"]))),
        command("LadderFFThreePositiveCount", int(ladder_all.loc["ff3", "positive_alpha_estimates"])),
        command("LadderFFThreeNominalCount", int(ladder_all.loc["ff3", "nominal_positive_5pct"])),
        command("LadderFFThreeHolmCount", int(ladder_all.loc["ff3", "holm_positive_5pct"])),
        command("LadderFFThreeMedianAlphaPct", fmt_pct(float(ladder_all.loc["ff3", "median_alpha_annualized"]))),
        command("LadderFFFiveMomPositiveCount", int(ladder_all.loc["ff5_mom", "positive_alpha_estimates"])),
        command("LadderFFFiveMomNominalCount", int(ladder_all.loc["ff5_mom", "nominal_positive_5pct"])),
        command("LadderFFFiveMomHolmCount", int(ladder_all.loc["ff5_mom", "holm_positive_5pct"])),
        command("LadderFFFiveMomMedianAlphaPct", fmt_pct(float(ladder_all.loc["ff5_mom", "median_alpha_annualized"]))),
        command("LadderJKPPositiveCount", int(ladder_all.loc["ff5_mom_jkp132", "positive_alpha_estimates"])),
        command("LadderJKPNominalCount", int(ladder_all.loc["ff5_mom_jkp132", "nominal_positive_5pct"])),
        command("LadderJKPHolmCount", int(ladder_all.loc["ff5_mom_jkp132", "holm_positive_5pct"])),
        command("LadderJKPMedianAlphaPct", fmt_pct(float(ladder_all.loc["ff5_mom_jkp132", "median_alpha_annualized"]))),
        command("LadderMedianFFThreeToJKPAttenuationPct", fmt_pct(float(
            ladder_comparison["alpha_attenuation_ff3_to_jkp132"].median()
        ))),
        command("LadderMedianFFFiveMomToJKPAttenuationPct", fmt_pct(float(
            ladder_comparison["alpha_attenuation_ff5_mom_to_jkp132"].median()
        ))),
        command("LadderMedianTopAbsCorrelation", f"{float(top_one['absolute_correlation'].median()):.2f}"),
        command("LadderTopCorrelationOverHalfCount", int((top_one["absolute_correlation"] >= 0.5).sum())),
        command("LadderUniqueTopFactorCount", int(top_one["jkp_factor_id"].nunique())),
        command("LadderGroundedFFThreePositiveCount", int(
            ladder_grounded.loc[ladder_grounded["benchmark_id"].eq("ff3"), "positive_alpha_estimate"].sum()
        )),
        command("LadderGroundedFFFiveMomPositiveCount", int(
            ladder_grounded.loc[ladder_grounded["benchmark_id"].eq("ff5_mom"), "positive_alpha_estimate"].sum()
        )),
        command("LadderGroundedJKPPositiveCount", int(
            ladder_grounded.loc[ladder_grounded["benchmark_id"].eq("ff5_mom_jkp132"), "positive_alpha_estimate"].sum()
        )),
        command(
            "SourceBenchmarkVerifiedCount",
            int(source_benchmark_manifest["verified_full_text_papers"]),
        ),
        command(
            "SourceBenchmarkNoRegressionCount",
            int(source_benchmark_manifest["verified_without_asset_pricing_regression"]),
        ),
        command(
            "SourceBenchmarkLoadingsOnlyCount",
            int(source_benchmark_manifest["verified_with_multifactor_loadings_only"]),
        ),
        command("SourceBenchmarkAdjustedAlphaCount", int(
            source_benchmark_manifest["verified_reporting_factor_adjusted_intercept"]
        )),
        command("SourceBenchmarkJKPCount", int(source_benchmark_manifest["verified_using_jkp132"])),
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

    top_factor_lines = [
        "% Generated by scripts/build_icaif2026_submission_assets.py; do not edit by hand.",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Most frequent JKP132 analogues of the 50 retained strategy reconstructions. The table reports the JKP factor with the largest absolute return correlation for each strategy, not a factor label claimed verbatim by the source paper.}",
        r"\label{tab:top-jkp-matches}",
        r"\small",
        r"\setlength{\tabcolsep}{7pt}",
        r"\begin{tabular}{@{}lcrr@{}}",
        r"\toprule",
        r"\textbf{Closest JKP analogue} & \textbf{Strategies} & \textbf{Median $\rho$} & \textbf{Median $|\rho|$} \\",
        r"\midrule",
    ]
    for _, row in top_factor_table.iterrows():
        top_factor_lines.append(
            f"{row['label']} & {int(row['n_strategies'])} & "
            f"{float(row['median_signed_correlation']):.2f} & "
            f"{float(row['median_absolute_correlation']):.2f} \\\\"
        )
    top_factor_lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\par\vspace{0.2em}\footnotesize Correlations use 246 common monthly returns from August 2001 through January 2022. Negative $\rho$ denotes exposure opposite to the published JKP factor orientation. These ten analogues cover 39 strategies; eleven additional JKP factors are the closest match for one strategy each.",
        r"\end{table*}",
    ])
    top_factor_path = paper_dir / "tables/top_jkp_factor_matches.tex"
    top_factor_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=top_factor_path.parent, delete=False, encoding="utf-8"
    ) as handle:
        handle.write("\n".join(top_factor_lines) + "\n")
        temp_top_factor_path = Path(handle.name)
    os.replace(temp_top_factor_path, top_factor_path)

    def holm_count(p_values: list[float]) -> int:
        ordered = sorted(float(value) for value in p_values)
        rejected = 0
        for rank, value in enumerate(ordered):
            if value <= 0.05 / (len(ordered) - rank):
                rejected += 1
            else:
                break
        return rejected

    cost_grid_rows = []
    for cost_bps in schedule:
        group = cost_ok.loc[cost_ok["cost_bps_one_way"] == cost_bps].copy()
        material_p = [
            0.5 * math.erfc(
                ((float(row["alpha_annualized"]) - 0.02) /
                 (12.0 * float(row["alpha_se_monthly"]))) / math.sqrt(2.0)
            )
            for _, row in group.iterrows()
        ]
        cost_grid_rows.append({
            "cost_bps": cost_bps,
            "median_alpha": float(group["alpha_annualized"].median()),
            "median_sharpe": float(group["sharpe_annualized"].median()),
            "positive": int((group["alpha_annualized"] > 0).sum()),
            "nominal_positive": int(((group["alpha_annualized"] > 0) &
                                     (group["p_value_two_sided"] <= 0.05)).sum()),
            "holm_positive": cost_holm_counts[schedule.index(cost_bps)],
            "point_material": int((group["alpha_annualized"] >= 0.02).sum()),
            "nominal_material": int(sum(value <= 0.05 for value in material_p)),
            "holm_material": holm_count(material_p),
        })
    observed_cost_counts = [
        (row["cost_bps"], row["positive"], row["nominal_positive"],
         row["holm_positive"], row["point_material"], row["nominal_material"],
         row["holm_material"])
        for row in cost_grid_rows
    ]
    expected_cost_counts = [
        (0, 46, 7, 1, 33, 3, 0),
        (5, 42, 7, 1, 21, 1, 0),
        (10, 30, 6, 1, 16, 1, 0),
        (25, 18, 1, 0, 10, 1, 0),
        (50, 10, 0, 0, 1, 0, 0),
    ]
    if observed_cost_counts != expected_cost_counts:
        raise RuntimeError(f"gross-to-net threshold family changed: {observed_cost_counts}")

    tier_by_candidate = mapping_audit.set_index("candidate_id")["mapping_fidelity_tier"]
    gross_ok = cost_ok.loc[cost_ok["cost_bps_one_way"] == 0].copy()
    net_ok = cost_ok.loc[cost_ok["cost_bps_one_way"] == 10].copy()
    top_row = gross_ok.loc[gross_ok["alpha_annualized"].idxmax()]
    grounded_ids = tier_by_candidate.loc[
        tier_by_candidate != "M0_narrative_translation"
    ].index
    grounded = gross_ok.loc[gross_ok["candidate_id"].isin(grounded_ids)]
    grounded_top = grounded.loc[grounded["alpha_annualized"].idxmax()]
    released_ids = tier_by_candidate.loc[
        tier_by_candidate == "M2_released_seed_expression"
    ].index
    released = gross_ok.loc[gross_ok["candidate_id"].isin(released_ids)]
    if len(released) != 1:
        raise RuntimeError("released-seed mapping family is not one row")
    released_row = released.iloc[0]

    def proxy_code(candidate_id: str) -> str:
        return "P-" + hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:6].upper()

    def paired_metrics(candidate_id: str) -> tuple[pd.Series, pd.Series]:
        gross_rows = gross_ok.loc[gross_ok["candidate_id"] == candidate_id]
        net_rows = net_ok.loc[net_ok["candidate_id"] == candidate_id]
        if len(gross_rows) != 1 or len(net_rows) != 1:
            raise RuntimeError(f"gross/net row missing for {candidate_id}")
        return gross_rows.iloc[0], net_rows.iloc[0]

    anchor_rows = []
    for label, selected in (
        (f"Largest $\\hat{{\\alpha}}$: {proxy_code(str(top_row['candidate_id']))} (M0)", top_row),
        (f"Largest grounded: {proxy_code(str(grounded_top['candidate_id']))} (M1)", grounded_top),
        (f"Released-seed mapping: {proxy_code(str(released_row['candidate_id']))} (M2)", released_row),
    ):
        gross_row, net_row = paired_metrics(str(selected["candidate_id"]))
        anchor_rows.append((label, gross_row, net_row))
    anchor_lines = [
        "% Generated by scripts/build_icaif2026_submission_assets.py; do not edit by hand.",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Gross-to-net alpha thresholds and numerical anchors for Figure~\ref{fig:cost}.}",
        r"\label{tab:alpha-sharpe-anchor}",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{1.65pt}",
        r"\textit{Panel A: familywide threshold audit}\\[-0.2em]",
        r"\begin{tabular}{@{}rrrrrrrrr@{}}",
        r"\toprule",
        (
            "\\textbf{Cost} & \\textbf{Med. $\\hat{\\alpha}$} & \\textbf{Med. $SR$} & "
            "\\multicolumn{3}{c}{\\textbf{$\\alpha>0$}} & "
            "\\multicolumn{3}{c}{\\textbf{$\\alpha>2\\%$}} \\\\"
        ),
        r"\cmidrule(lr){4-6}\cmidrule(l){7-9}",
        (
            " & & & \\textbf{Point} & \\textbf{Raw} & \\textbf{Holm} & "
            "\\textbf{Point} & \\textbf{Raw} & \\textbf{Holm} \\\\"
        ),
        r"\midrule",
    ]
    for row in cost_grid_rows:
        anchor_lines.append(
            f"{row['cost_bps']} bp & {100.0 * row['median_alpha']:.2f}\\% & "
            f"{row['median_sharpe']:.3f} & {row['positive']} & {row['nominal_positive']} & "
            f"{row['holm_positive']} & {row['point_material']} & {row['nominal_material']} & "
            f"{row['holm_material']} \\\\"
        )
    anchor_lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\par\vspace{0.35em}\textit{Panel B: selected gross and 10-bp mapping rows}\\[-0.2em]",
        r"\begin{tabular}{@{}p{0.39\columnwidth}rrrrrr@{}}",
        r"\toprule",
        " & \\multicolumn{3}{c}{\\textbf{Gross (0 bp)}} & \\multicolumn{3}{c}{\\textbf{Net (10 bp)}} \\\\",
        r"\cmidrule(lr){2-4}\cmidrule(l){5-7}",
        (
            "\\textbf{Evidence line} & \\textbf{$SR$} & \\textbf{$\\hat{\\alpha}$} & \\textbf{$t$} & "
            "\\textbf{$SR$} & \\textbf{$\\hat{\\alpha}$} & \\textbf{$t$} \\\\"
        ),
        r"\midrule",
    ])
    for label, gross_row, net_row in anchor_rows:
        anchor_lines.append(
            f"{label} & {float(gross_row['sharpe_annualized']):.3f} & "
            f"{100.0 * float(gross_row['alpha_annualized']):.2f}\\% & "
            f"{float(gross_row['alpha_t_hac']):.2f} & {float(net_row['sharpe_annualized']):.3f} & "
            f"{100.0 * float(net_row['alpha_annualized']):.2f}\\% & "
            f"{float(net_row['alpha_t_hac']):.2f} \\\\"
        )
    anchor_lines.extend([
        r"Direct seed adaptation (gross only) & 0.316 & 0.33\% & 0.65 & --- & --- & --- \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\par\vspace{0.2em}\footnotesize U.S. mapping rows cover 2001--2024. In the $\alpha>0$ columns, Raw means positive $\hat{\alpha}$ with two-sided HAC $p\leq.05$ and Holm adjusts across 62 mappings. For $\alpha>2\%$, Raw and Holm use one-sided HAC tests of $H_0:\alpha\leq2\%$; that materiality threshold was selected after outcomes and remains descriptive. $SR$ annualizes next-month realized returns, which are one-period-ahead but not an independent discovery holdout. The direct released-seed adaptation is a separate gross 1999--2024 path. Panel B rows are selected by evidence role, not significance.",
        r"\end{table}",
    ])
    anchor_path = paper_dir / "tables/alpha_sharpe_anchor.tex"
    anchor_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=anchor_path.parent, delete=False, encoding="utf-8") as handle:
        handle.write("\n".join(anchor_lines) + "\n")
        temp_anchor_path = Path(handle.name)
    os.replace(temp_anchor_path, anchor_path)

    plt.rcParams.update({
        "font.size": 10,
        "font.family": "DejaVu Sans",
        "axes.labelcolor": INK,
        "axes.edgecolor": RULE,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "figure.facecolor": WHITE,
        "savefig.facecolor": WHITE,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    fig, ax = plt.subplots(figsize=(11.2, 4.7), facecolor=WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.15)
    ax.axis("off")

    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

    SLATE = "#66788A"
    PALE_BLUE = "#EAF2FA"
    PALE_TEAL = "#E6F4F2"
    PALE_GOLD = "#FBF2DF"
    PALE_SLATE = "#EEF2F5"

    card_width = 2.42
    top_y, top_height = 2.62, 1.10
    lower_y, lower_height = 1.18, 1.04
    stage_x = [1.40, 4.45, 7.50, 10.55]

    def card(cx, y, height, title, value, detail, color, fill):
        left = cx - card_width / 2
        ax.add_patch(
            FancyBboxPatch(
                (left, y),
                card_width,
                height,
                boxstyle="round,pad=0.03,rounding_size=0.05",
                linewidth=1.1,
                edgecolor=color,
                facecolor=fill,
                zorder=4,
            )
        )
        ax.add_patch(
            Rectangle(
                (left, y),
                0.10,
                height,
                facecolor=color,
                edgecolor=color,
                linewidth=0,
                zorder=5,
            )
        )
        text_x = left + 0.22
        ax.text(
            text_x,
            y + height - 0.22,
            title,
            ha="left",
            va="center",
            fontsize=8.0,
            fontweight="bold",
            color=color,
            zorder=6,
        )
        ax.text(
            text_x,
            y + height - 0.56,
            value,
            ha="left",
            va="center",
            fontsize=11.7,
            fontweight="bold",
            color=INK,
            zorder=6,
        )
        ax.text(
            text_x,
            y + 0.18,
            detail,
            ha="left",
            va="center",
            fontsize=7.7,
            color=INK,
            zorder=6,
        )

    def connector(x0, y0, x1, y1, color, width=1.7, curve=0.0):
        ax.add_patch(
            FancyArrowPatch(
                (x0, y0),
                (x1, y1),
                arrowstyle="-|>",
                mutation_scale=10,
                linewidth=width,
                color=color,
                connectionstyle=f"arc3,rad={curve}",
                shrinkA=2,
                shrinkB=2,
                zorder=2,
            )
        )

    top_center = top_y + top_height / 2
    lower_center = lower_y + lower_height / 2
    half_width = card_width / 2
    for index in range(3):
        connector(
            stage_x[index] + half_width,
            top_center,
            stage_x[index + 1] - half_width,
            top_center,
            BLUE if index < 2 else TEAL,
            width=2.0,
        )
        connector(
            stage_x[index] + half_width,
            top_center - 0.20,
            stage_x[index + 1] - half_width,
            lower_center,
            SLATE if index < 2 else GOLD,
            width=1.25,
            curve=0.08,
        )

    stage_headers = [
        "01  SCREEN",
        "02  SCOPE",
        "03  COVERAGE",
        "04  EVIDENCE",
    ]
    for x, text_value in zip(stage_x, stage_headers):
        ax.text(
            x,
            4.18,
            text_value,
            ha="center",
            va="center",
            fontsize=8.8,
            fontweight="bold",
            color=SLATE,
            zorder=6,
        )
        ax.plot([x - 0.56, x + 0.56], [4.02, 4.02], color=RULE, linewidth=0.9, zorder=2)

    card(stage_x[0], top_y, top_height, "SCREENED CORPUS", "98 works", "103 lineages", NAVY, "#F5F8FB")
    card(stage_x[1], top_y, top_height, "RETAINED METHODS", "69 works", "67 lineages", BLUE, PALE_BLUE)
    card(stage_x[1], lower_y, lower_height, "SCREENED OUT", "29 works", "excluded with reasons", SLATE, PALE_SLATE)
    card(stage_x[2], top_y, top_height, "RECONSTRUCTED", "40 works", "50 mappings", BLUE, PALE_BLUE)
    card(stage_x[2], lower_y, lower_height, "AVAILABILITY ONLY", "29 works", "no alpha imputed", SLATE, PALE_SLATE)
    card(stage_x[3], top_y, top_height, "SOURCE-ANCHORED", "13 partial tests", "from 5 works", TEAL, PALE_TEAL)
    card(stage_x[3], lower_y, lower_height, "NARRATIVE TESTS", "37 mappings", "from 35 works", GOLD, PALE_GOLD)

    audit = FancyBboxPatch(
        (0.20, 0.12),
        11.60,
        0.78,
        boxstyle="round,pad=0.03,rounding_size=0.05",
        linewidth=1.0,
        edgecolor=NAVY,
        facecolor="#F5F8FB",
        linestyle=(0, (4, 3)),
        zorder=3,
    )
    ax.add_patch(audit)
    ax.text(0.48, 0.64, "SEPARATE CODE AUDIT", ha="left", va="center", fontsize=8.4,
            fontweight="bold", color=NAVY, zorder=5)
    ax.text(0.48, 0.38, "overlaps the work corpus", ha="left", va="center", fontsize=7.3,
            color=SLATE, zorder=5)
    audit_metrics = [
        (4.00, "14", "attempts"),
        (6.00, "8 + 6", "retained + diagnostic"),
        (8.05, "0", "native replications"),
        (10.25, "1", "seed adaptation"),
    ]
    for separator_x in (3.05, 4.95, 7.02, 9.13):
        ax.plot([separator_x, separator_x], [0.27, 0.75], color=RULE, linewidth=0.8, zorder=4)
    for x, value, description in audit_metrics:
        ax.text(x, 0.63, value, ha="center", va="center", fontsize=10.6,
                fontweight="bold", color=NAVY, zorder=5)
        ax.text(x, 0.36, description, ha="center", va="center", fontsize=7.5,
                color=INK, zorder=5)

    ax.text(
        6.0,
        4.88,
        "Public-evidence waterfall: from screened works to testable components",
        ha="center",
        va="center",
        fontsize=12.4,
        fontweight="bold",
        color=NAVY,
        zorder=6,
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

    benchmark_order = ["capm", "ff3", "ff5_mom", "ff5_mom_jkp132"]
    benchmark_labels = ["CAPM", "FF3", "FF5 + Mom.", "FF5 + Mom.\\n+ JKP132"]
    benchmark_colors = [BLUE, "#4C8CCB", TEAL, GOLD]
    benchmark_labels = [label.replace("\\n", "\n") for label in benchmark_labels]
    benchmark_data = [
        100.0
        * ladder_results.loc[
            ladder_results["benchmark_id"].eq(benchmark_id),
            "alpha_annualized",
        ].to_numpy(dtype=float)
        for benchmark_id in benchmark_order
    ]
    fig, ax = plt.subplots(figsize=(9.2, 5.5), facecolor=WHITE)
    style_axis(ax)
    boxes = ax.boxplot(
        benchmark_data,
        tick_labels=benchmark_labels,
        patch_artist=True,
        widths=0.58,
        showfliers=True,
        medianprops={"color": INK, "linewidth": 2.0},
        whiskerprops={"color": INK, "linewidth": 1.0},
        capprops={"color": INK, "linewidth": 1.0},
        flierprops={
            "marker": "o",
            "markerfacecolor": WHITE,
            "markeredgecolor": NAVY,
            "markersize": 3.5,
            "alpha": 0.75,
        },
    )
    for patch, color in zip(boxes["boxes"], benchmark_colors):
        patch.set_facecolor(color)
        patch.set_edgecolor(INK)
        patch.set_alpha(0.82)
    ax.axhline(0, color=INK, linewidth=0.9, zorder=0)
    ax.set_ylabel("Annualized one-month-ahead residual mean (%)")
    ax.set_title("Known factors absorb the apparent strategy alpha", pad=12)
    ax.grid(axis="y", alpha=0.35)
    ax.set_axisbelow(True)
    for position, benchmark_id in enumerate(benchmark_order, start=1):
        row = ladder_all.loc[benchmark_id]
        text_value = (
            f"+: {int(row['positive_alpha_estimates'])}/50  "
            f"nom.: {int(row['nominal_positive_5pct'])}  "
            f"Holm: {int(row['holm_positive_5pct'])}"
        )
        ax.text(
            position,
            0.98,
            text_value,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=7.1,
            color=INK,
            bbox={"facecolor": WHITE, "edgecolor": RULE, "alpha": 0.94, "pad": 2.0},
        )
    save_figure(fig, paper_dir / "figures/matched_benchmark_ladder.pdf")

    factor_plot = top_factor_frequency.head(6).iloc[::-1].copy()
    factor_plot["label"] = factor_plot["jkp_factor_id"].map(readable_factors).fillna(
        factor_plot["jkp_factor_id"]
    )
    fig, ax = plt.subplots(figsize=(9.0, 4.6), facecolor=WHITE)
    style_axis(ax)
    bars = ax.barh(
        factor_plot["label"],
        factor_plot["n_strategies"],
        color=TEAL,
        edgecolor=INK,
        linewidth=0.8,
    )
    for bar, correlation in zip(
        bars,
        factor_plot["median_absolute_correlation"],
    ):
        ax.text(
            bar.get_width() + 0.2,
            bar.get_y() + bar.get_height() / 2,
            f"median |r|={correlation:.2f}",
            va="center",
            ha="left",
            fontsize=8.0,
            color=INK,
        )
    ax.set_xlabel("Number of strategies for which factor is the closest JKP match")
    ax.set_title("The closest known exposures concentrate in low-risk and momentum factors")
    ax.set_xlim(0, max(factor_plot["n_strategies"]) + 5)
    ax.grid(axis="x", alpha=0.35)
    ax.set_axisbelow(True)
    save_figure(fig, paper_dir / "figures/top_jkp_factor_matches.pdf")

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
    print(f"wrote {anchor_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
