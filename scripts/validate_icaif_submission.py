#!/usr/bin/env python3
"""Recompute and audit every ICAIF headline from the frozen evidence package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


LOCK_SHA256 = "dba132b6366e03f65a65b90549ca9d3e7a39313a60d42f43ea00407b0a6694e2"
PROTOCOL_SHA256 = "0a0515cedbb211362356d4a3a28693696ae18edfd89d4298266588ea21fa8285"


class Audit:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks = 0

    def require(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.failures.append(message)

    def equal(self, actual, expected, label: str) -> None:
        self.require(actual == expected, f"{label}: expected {expected!r}, found {actual!r}")

    def close(self, actual: float, expected: float, label: str, tol: float = 5e-5) -> None:
        self.require(math.isclose(actual, expected, rel_tol=0.0, abs_tol=tol),
                     f"{label}: expected {expected}, found {actual}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lo = math.floor(position)
    hi = math.ceil(position)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - position) + ordered[hi] * (position - lo)


def rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for index in order[start:end]:
            result[index] = rank
        start = end
    return result


def spearman(x: list[float], y: list[float]) -> float:
    rx, ry = rankdata(x), rankdata(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    numerator = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denominator = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return numerator / denominator


def holm_rejections(p_values: list[float], alpha: float = 0.05) -> set[int]:
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    rejected: set[int] = set()
    m = len(p_values)
    for rank, (index, value) in enumerate(ordered):
        if value <= alpha / (m - rank):
            rejected.add(index)
        else:
            break
    return rejected


def command_text(command: list[str]) -> str:
    return subprocess.run(command, check=True, text=True, capture_output=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pdf", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    evidence = root / "paper_runs/submission_evidence"
    paper = root / "docs/paper"
    pdf = (args.pdf or paper / "icaif2026_submission.pdf").resolve()
    audit = Audit()

    lock_path = evidence / "analysis_lock.json"
    audit.equal(sha256(lock_path), LOCK_SHA256, "analysis lock SHA-256")
    lock = json.loads(lock_path.read_text())
    audit.equal(lock["file_sha256"]["docs/confirmatory_analysis_protocol.md"], PROTOCOL_SHA256,
                "protocol SHA recorded by lock")
    audit.equal(sha256(root / "docs/confirmatory_analysis_protocol.md"), PROTOCOL_SHA256,
                "protocol SHA on disk")
    for relative, expected in lock["file_sha256"].items():
        target = root / relative
        audit.require(target.is_file(), f"locked file missing: {relative}")
        if target.is_file():
            audit.equal(sha256(target), expected, f"locked file SHA: {relative}")
    audit.equal(lock["schema_version"], 3, "lock schema")
    audit.equal(lock["candidate_family_size"], 62, "candidate family")
    audit.equal(lock["primary_system_denominator_F_plus_T"], 67, "F/T denominator")
    audit.equal(lock["system_registry_total"], 103, "system census")
    audit.equal(lock["system_stratum_counts"], {"B": 23, "C": 5, "F": 29, "M": 8, "T": 38},
                "census strata")
    audit.equal(lock["holdout_label"],
                "geographically external amended validation; overlapping dates, not a pristine temporal holdout",
                "holdout label")
    audit.require(lock["amended_lock_created_after_g7_outcome_access"], "amendment disclosure absent")
    audit.require(not lock["corrected_g7_outputs_viewed_before_this_lock"],
                  "corrected G7 outcomes were marked viewed before V3 lock")

    summary = rows(evidence / "artifact_audit/artifact_audit_summary.csv")
    summary_keyed = {(r["group"], r["metric"]): r for r in summary}
    listed = summary_keyed[("F+T", "public_artifact_listed")]
    reachable = summary_keyed[("F+T", "artifact_reachable_among_all")]
    audit.equal((int(listed["successes"]), int(listed["denominator"])), (20, 67), "listed artifacts")
    audit.close(f(listed, "proportion"), 20 / 67, "listed artifact rate", 1e-12)
    audit.close(f(listed, "wilson_95_lower"), 0.20231511276602715, "listed Wilson lower", 1e-12)
    audit.close(f(listed, "wilson_95_upper"), 0.41655213743643765, "listed Wilson upper", 1e-12)
    audit.equal((int(reachable["successes"]), int(reachable["denominator"])), (18, 67),
                "reachable artifacts")
    for group, expected in {"F": (7, 29), "T": (13, 38), "B": (18, 23), "C": (4, 5), "M": (4, 8)}.items():
        row = summary_keyed[(group, "public_artifact_listed")]
        audit.equal((int(row["successes"]), int(row["denominator"])), expected, f"{group} artifact stratum")

    artifact = [r for r in rows(evidence / "artifact_audit/artifact_audit.csv") if r["main_FT"] == "Y"]
    audit.equal(len(artifact), 67, "artifact audit F/T rows")
    audit.equal(sum(bool(r["observed_licenses"].strip()) and not r["observed_licenses"].endswith("=NOASSERTION")
                    for r in artifact), 9, "observed reuse licenses")
    audit.equal(sum(bool(r["default_branch_head_shas"].strip()) for r in artifact), 18, "resolved Git revisions")
    native = rows(evidence / "native_fidelity_ledger.csv")
    audit.equal(len(native), 67, "native fidelity rows")
    audit.equal(Counter(r["static_tier"] for r in native), Counter({"R0": 49, "R1": 6, "R2": 5, "R3": 7}),
                "F/T static tiers")
    audit.equal(sum(r["native_dated_signal_or_return_shipped"] == "Y" for r in native), 3,
                "dated native outputs")
    audit.equal(sum(r["prespecified_G7_monthly_common_task_compatible"] == "Y" for r in native), 0,
                "compatible native returns")
    audit.equal(Counter(r["fidelity_class"] for r in native),
                Counter({"F0_no_public_artifact": 47, "F1_static_no_native_output": 15,
                         "F2_dated_output_task_incompatible": 3, "F0_artifact_unresolved": 2}),
                "native evidence classes")

    direct = rows(root / "paper_runs/repository_ff5mom_metrics_summary.csv")
    audit.equal(len(direct), 14, "targeted direct-code attempts")
    audit.equal(Counter(r["code_status"] for r in direct),
                Counter({"real_public_code": 12, "ambiguous_unofficial_code": 1,
                         "placeholder_or_empty_repo": 1}),
                "direct-code repository classes")
    computable = [r for r in direct if r["metric_status"] == "computed_jkp_only"]
    audit.equal(len(computable), 1, "computable direct-code JKP paths")
    audit.equal(computable[0]["candidate_id"], "quantevolver_return_sharpe_60_proxy",
                "computable direct-code candidate")
    audit.close(f(computable[0], "alpha_annualized"), 0.0032849190887483,
                "QuantEvolver direct alpha", 1e-12)
    audit.close(f(computable[0], "alpha_tstat_hac"), 0.6514961447297817,
                "QuantEvolver direct alpha t-stat", 1e-12)
    audit.equal(sum(r["beats_ff5mom_at_5pct"] == "True" for r in direct), 0,
                "direct-code FF5+Mom beaters")

    source_ledger = rows(root / "paper_runs/idea_replications/paper_derived_source_replication_ledger.csv")
    audit.equal(len(source_ledger), 55, "claim-bearing source ledger")
    mapped_sources = [r for r in source_ledger if r["source_status"] == "jkp_proxy_tested"]
    audit.equal(len(mapped_sources), 51, "mapped claim-bearing sources")
    audit.equal(sum(int(r["candidate_count"]) for r in mapped_sources), 62,
                "mapped frozen proxy count")

    primary = rows(evidence / "g7_ex_us_corrected/candidate_primary_results.csv")
    ok = [r for r in primary if r["status"] == "ok"]
    alpha = [f(r, "alpha_annualized") for r in ok]
    audit.equal((len(primary), len(ok)), (62, 27), "primary planned/executable")
    audit.close(statistics.median(alpha), 0.0762, "primary median alpha", 5e-5)
    audit.close(percentile(alpha, 0.25), 0.0339, "primary alpha Q1", 5e-5)
    audit.close(percentile(alpha, 0.75), 0.0965, "primary alpha Q3", 5e-5)
    audit.equal(sum(a > 0 for a in alpha), 24, "positive alpha count")
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "p_value_two_sided") <= 0.05 for r in ok), 21,
                "nominal positive count")
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "holm_p_value") <= 0.05 for r in ok), 11,
                "Holm positive count")
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "max_abs_t_p_value") <= 0.05 for r in ok), 12,
                "max-|t| positive count")
    audit.equal(sum(f(r, "simultaneous_ci_low_annualized") >= 0.02 for r in ok), 4,
                "two-percentage-point confirmations")
    audit.close(max(alpha), 0.1225, "best alpha", 5e-5)
    audit.close(min(alpha), -0.0719, "worst alpha", 5e-5)
    audit.equal({r["n_months"] for r in ok}, {"293.0"}, "primary month count")
    audit.equal({r["start"] for r in ok}, {"2000-08-31"}, "primary start")
    audit.equal({r["end"] for r in ok}, {"2024-12-31"}, "primary end")
    manifest = json.loads((evidence / "g7_ex_us_corrected/run_manifest.json").read_text())
    audit.require(manifest["bootstrap"]["white_reality_check_style_p_value"] < 0.001,
                  "global maximum-statistic p-value is not below .001")

    failures = rows(evidence / "g7_ex_us_corrected/candidate_path_failures.csv")
    audit.equal((len(failures), len({r["candidate_id"] for r in failures})), (40, 35),
                "failure events/candidates")
    audit.equal(Counter(r["market"] for r in failures), Counter({"FRA": 31, "CAN": 5, "DEU": 2, "ITA": 1, "GBR": 1}),
                "failure markets")
    audit.equal(Counter(r["month"] for r in failures)["2022-05-31"], 13, "May 2022 failures")
    audit.equal(Counter(r["month"] for r in failures)["2024-11-30"], 12, "November 2024 failures")
    failed_returns = [f(r, "failure_total_return") for r in failures]
    audit.close(min(failed_returns), -19.619, "minimum failure return", 5e-4)
    audit.close(max(failed_returns), -1.015, "maximum failure return", 5e-4)
    audit.close(statistics.median(failed_returns), -2.254, "median failure return", 5e-4)

    hac = rows(evidence / "g7_ex_us_corrected/hac_lag_sensitivity.csv")
    for lag, nominal_expected, holm_expected in [(0, 21, 10), (3, 21, 11), (6, 21, 10), (12, 22, 10)]:
        group = [r for r in hac if int(r["fixed_hac_lags"]) == lag]
        audit.equal(len(group), 27, f"HAC {lag} executable rows")
        nominal = sum(f(r, "alpha_annualized") > 0 and f(r, "p_value_two_sided") <= 0.05 for r in group)
        audit.equal(nominal, nominal_expected, f"HAC {lag} nominal positives")
        p_values = [f(r, "p_value_two_sided") for r in group] + [1.0] * 35
        rejected = holm_rejections(p_values)
        holm_positive = sum(i in rejected and f(r, "alpha_annualized") > 0 for i, r in enumerate(group))
        audit.equal(holm_positive, holm_expected, f"HAC {lag} Holm positives")

    blocks = rows(evidence / "g7_ex_us_corrected/bootstrap_block_sensitivity.csv")
    for length, max_t_expected in [(3, 11), (6, 12), (12, 12)]:
        group = ok if length == 6 else [r for r in blocks if int(r["block_length"]) == length]
        audit.equal(len(group), 27, f"block {length} rows")
        audit.equal(sum(f(r, "bootstrap_alpha_point_monthly") > 0 and f(r, "max_abs_t_p_value") <= 0.05 for r in group),
                    max_t_expected, f"block {length} max-|t| positives")
        audit.equal(sum(f(r, "simultaneous_ci_low_annualized") >= 0.02 for r in group), 4,
                    f"block {length} material confirmations")

    adverse = [r for r in rows(evidence / "g7_missing_adverse/candidate_primary_results.csv") if r["status"] == "ok"]
    audit.equal(len(adverse), 27, "adverse executable count")
    audit.close(statistics.median(f(r, "alpha_annualized") for r in adverse), 0.1077, "adverse median alpha", 5e-5)
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "p_value_two_sided") <= 0.05 for r in adverse), 13,
                "adverse nominal positives")
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "holm_p_value") <= 0.05 for r in adverse), 6,
                "adverse Holm positives")
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "max_abs_t_p_value") <= 0.05 for r in adverse), 8,
                "adverse max-|t| positives")
    audit.equal(sum(f(r, "simultaneous_ci_low_annualized") >= 0.02 for r in adverse), 3,
                "adverse material confirmations")

    turnover = {r["candidate_id"]: r for r in rows(evidence / "g7_ex_us_corrected/turnover_summary.csv")}
    turnover_values = [f(turnover[r["candidate_id"]], "median_monthly_traded_notional") for r in ok]
    audit.close(statistics.median(turnover_values), 0.91, "median traded notional", 5e-3)
    audit.close(percentile(turnover_values, 0.25), 0.74, "turnover Q1", 5e-3)
    audit.close(percentile(turnover_values, 0.75), 1.33, "turnover Q3", 5e-3)
    costs = rows(evidence / "g7_ex_us_corrected/candidate_cost_alpha_results.csv")
    by_cost: dict[int, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in costs:
        if row["status"] == "ok":
            by_cost[int(float(row["cost_bps_one_way"]))][row["candidate_id"]] = row
    paired = sorted(set(by_cost[0]) & set(by_cost[10]))
    drags = [f(by_cost[0][c], "alpha_annualized") - f(by_cost[10][c], "alpha_annualized") for c in paired]
    audit.equal(len(paired), 27, "paired cost paths")
    audit.close(statistics.median(drags), 0.0119, "median 10 bp alpha drag", 5e-5)
    audit.equal(sum(f(r, "alpha_annualized") > 0 for r in by_cost[25].values()), 23, "positive at 25 bp")
    audit.equal(sum(f(r, "alpha_annualized") > 0 for r in by_cost[50].values()), 19, "positive at 50 bp")

    usa = rows(evidence / "usa_retrospective_corrected/candidate_primary_results.csv")
    usa_ok = [r for r in usa if r["status"] == "ok"]
    audit.equal((len(usa), len(usa_ok)), (62, 62), "U.S. planned/executable")
    usa_alpha = [f(r, "alpha_annualized") for r in usa_ok]
    audit.close(statistics.median(usa_alpha), -0.000522, "U.S. median alpha", 5e-6)
    audit.equal(sum(a > 0 for a in usa_alpha), 30, "U.S. positive estimates")
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "p_value_two_sided") <= 0.05 for r in usa_ok), 6,
                "U.S. nominal positives")
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "holm_p_value") <= 0.05 for r in usa_ok), 1,
                "U.S. Holm positives")
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "max_abs_t_p_value") <= 0.05 for r in usa_ok), 1,
                "U.S. max-|t| positives")
    audit.equal(sum(f(r, "simultaneous_ci_low_annualized") >= 0.02 for r in usa_ok), 0,
                "U.S. material confirmations")

    broad_dir = evidence / "usa_broad_jkp_crossfit"
    broad_manifest = json.loads((broad_dir / "run_manifest.json").read_text())
    audit.equal(broad_manifest["analysis_label"], "post_hoc_exploratory_broad_jkp_crossfit",
                "broad-JKP analysis label")
    audit.close(float(broad_manifest["market_alignment_correlation"]), 0.9993633983234792,
                "broad-JKP market alignment", 1e-12)
    for filename, expected in broad_manifest["output_sha256"].items():
        audit.equal(sha256(broad_dir / filename), expected, f"broad-JKP output SHA: {filename}")
    broad = rows(broad_dir / "broad_jkp_crossfit_results.csv")
    audit.equal(len(broad), 62, "broad-JKP candidate family")
    audit.equal({int(r["n_benchmark_factors"]) for r in broad}, {133},
                "broad-JKP benchmark dimension")
    audit.equal({int(r["n_evaluation_months"]) for r in broad}, {126},
                "broad-JKP evaluation months")
    audit.equal(sum(f(r, "alpha_annualized") > 0 for r in broad), 23,
                "broad-JKP positive estimates")
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "p_value_two_sided") <= 0.05 for r in broad), 1,
                "broad-JKP nominal positives")
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "holm_p_value") <= 0.05 for r in broad), 0,
                "broad-JKP Holm positives")
    audit.equal(sum(f(r, "alpha_annualized") > 0 and f(r, "max_abs_t_p_value") <= 0.05 for r in broad), 0,
                "broad-JKP max-|t| positives")
    audit.equal(sum(f(r, "simultaneous_ci_low_annualized") >= 0.02 for r in broad), 0,
                "broad-JKP material confirmations")
    broad_best = max(broad, key=lambda r: f(r, "alpha_annualized"))
    audit.equal(broad_best["candidate_id"], "repo_alphaagent_decay_resistant_quality",
                "broad-JKP sole nominal candidate")
    audit.close(f(broad_best, "alpha_annualized"), 0.09241089267753816,
                "broad-JKP best alpha", 1e-12)
    audit.close(f(broad_best, "holm_p_value"), 0.15245852200869842,
                "broad-JKP best Holm p", 1e-12)
    audit.close(f(broad_best, "max_abs_t_p_value"), 0.09138172365526895,
                "broad-JKP best max-|t| p", 1e-12)

    diagnostic = rows(evidence / "fixed_calendar_diagnostics/fixed_calendar_country_loo.csv")
    country = [r for r in diagnostic if r["diagnostic"] == "country_fixed_primary_calendar"]
    audit.equal(len(country), 27 * 6, "fixed-calendar country rows")
    country_by_candidate: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in country:
        country_by_candidate[row["candidate_id"]].append(row)
    audit.equal(sum(all(f(r, "alpha_annualized") > 0 for r in group) for group in country_by_candidate.values()), 20,
                "positive in all countries")
    audit.equal(sum(all(f(r, "alpha_annualized") <= 0 for r in group) for group in country_by_candidate.values()), 0,
                "positive in no countries")
    loo = [r for r in diagnostic if r["diagnostic"] == "loo_fixed_primary_calendar"]
    primary_median = statistics.median(alpha)
    loo_medians = []
    for market in sorted({r["excluded_market"] for r in loo}):
        loo_medians.append(statistics.median(f(r, "alpha_annualized") for r in loo if r["excluded_market"] == market))
    audit.close(max(abs(value - primary_median) for value in loo_medians), 0.0307,
                "maximum LOO median shift", 5e-5)
    common = [r for r in diagnostic if r["diagnostic"] == "g7_usa_common_calendar"]
    usa_map = {r["candidate_id"]: r for r in usa_ok}
    common = [r for r in common if r["candidate_id"] in usa_map]
    audit.equal(len(common), 27, "same-window paired paths")
    gx = [f(r, "alpha_annualized") for r in common]
    ux = [f(usa_map[r["candidate_id"]], "alpha_annualized") for r in common]
    audit.close(spearman(ux, gx), 0.413, "same-window Spearman", 5e-4)
    audit.equal(sum((a > 0) == (b > 0) for a, b in zip(ux, gx)), 12, "same-window sign agreement")

    source_path = paper / "icaif2026_submission.tex"
    source = source_path.read_text()
    generated = (paper / "generated_results.tex").read_text()
    submission_generated = (paper / "icaif2026_results.tex").read_text()
    audit.require(re.search(r"\\documentclass\[[^]]*sigconf[^]]*anonymous", source) is not None,
                  "source is not anonymous ACM sigconf")
    audit.require("Anonymous Author(s)" in source, "anonymous author label missing")
    audit.require("\\appendix" not in source.lower(), "appendix is forbidden by the call")
    for token in ["TODO", "TBD", "FIXME", "Sasha Cui", "zc362", "/nfs/", "alpha_evolve"]:
        audit.require(token not in source, f"source contains forbidden/identifying token: {token}")
    expected_macros = {
        "SystemCount": "103", "MethodSystemCount": "67", "ArtifactCountFT": "20",
        "ReachableArtifactCountFT": "18", "LicensedArtifactCountFT": "9",
        "NativeDatedOutputCount": "3", "NativeReturnCount": "0", "ProxyCount": "62",
        "ValidProxyCount": "27", "PathFailureCandidateCount": "35", "PathFailureEventCount": "40",
        "PositiveAlphaCount": "24", "NominalPositiveCount": "21", "HolmPositiveCount": "11",
        "MaxTPositiveCount": "12", "EconomicConfirmedCount": "4", "RegressionMonthCount": "293",
        "PositiveAtTwentyFive": "23", "PositiveAtFifty": "19", "USNominalPositiveCount": "6",
    }
    for name, expected in expected_macros.items():
        audit.require(f"\\newcommand{{\\{name}}}{{{expected}}}" in generated, f"macro {name} mismatch")
    expected_submission_macros = {
        "USRegressionMonthCount": "281", "USMedianAlphaPct": "-0.05\\%",
        "USAlphaIQRPct": "[-1.26\\%, 2.05\\%]", "USPositiveAlphaCount": "30",
        "USNominalCount": "6", "USHolmPositiveCount": "1", "USMaxTPositiveCount": "1",
        "USEconomicConfirmedCount": "0", "USRealityCheckP": "0.0105",
        "USBestAlphaPct": "6.93\\%", "USBestSimultaneousLowerPct": "0.48\\%",
        "USMedianTurnover": "0.90", "USTurnoverIQR": "0.63--1.92",
        "USMedianCostDragPct": "1.17\\%", "USCrossSectionMedianCostShiftPct": "2.20\\%",
        "USPositiveAtZero": "46",
        "USPositiveAtTen": "30", "USPositiveAtTwentyFive": "18",
        "USPositiveAtFifty": "10", "USMedianGrossAlphaPct": "2.15\\%",
        "USHACLagNominalCounts": "5/6/6/6", "USHACLagHolmCounts": "0/1/1/0",
        "BroadEvaluationMonthCount": "126", "BroadPositiveAlphaCount": "23",
        "BroadNominalPositiveCount": "1", "BroadHolmPositiveCount": "0",
        "BroadMaxTPositiveCount": "0", "BroadEconomicConfirmedCount": "0",
        "BroadBestAlphaPct": "9.24\\%", "BroadBestRawP": "0.0025",
        "BroadBestHolmP": "0.152", "BroadBestMaxTP": "0.091",
        "BroadBestSimultaneousLowerPct": "-0.70\\%",
        "BroadMarketAlignmentCorrelation": "0.999",
    }
    for name, expected in expected_submission_macros.items():
        audit.require(
            f"\\newcommand{{\\{name}}}{{{expected}}}" in submission_generated,
            f"submission macro {name} mismatch",
        )
    audit.require("U.S. mechanisms, six factors & 62 / 62 & 30 & 6 & 1 & 1 & 0" in source,
                  "main results table U.S. row mismatch")
    audit.require("U.S. mechanisms, rolling broad JKP & 62 / 62 & 23 & 1 & 0 & 0 & 0" in source,
                  "main results table broad-JKP row mismatch")
    audit.require("direct-code route" in source and "reconstruction route" in source,
                  "two-route alpha-adjudication framing missing")
    for provenance in ["Compustat Global", r"\texttt{ret\_exc\_lead1m}", "converted to U.S. dollars"]:
        audit.require(provenance in source, f"international return provenance missing: {provenance}")
    audit.require("We therefore do not construct a native-agent leaderboard" not in source,
                  "abstract retains limitation-led leaderboard sentence")
    cited = set()
    for match in re.finditer(r"\\cite\{([^}]+)\}", source):
        cited.update(key.strip() for key in match.group(1).split(","))
    bib = (paper / "icaif2026_references.bib").read_text()
    bib_keys = set(re.findall(r"@[A-Za-z]+\{([^,]+),", bib))
    audit.equal(cited - bib_keys, set(), "citation keys missing from bibliography")
    audit.equal(bib_keys - cited, set(), "uncited dedicated bibliography entries")

    audit.require(pdf.is_file(), f"submission PDF missing: {pdf}")
    if pdf.is_file():
        info = command_text(["pdfinfo", str(pdf)])
        pages_match = re.search(r"^Pages:\s+(\d+)", info, flags=re.MULTILINE)
        audit.require(pages_match is not None, "PDF page count unavailable")
        if pages_match:
            count = int(pages_match.group(1))
            audit.require(1 <= count <= 8, f"PDF has {count} pages; ICAIF limit is 8 including references")
        audit.require("Page size:       612 x 792 pts (letter)" in info, "PDF is not US letter")
        text = command_text(["pdftotext", str(pdf), "-"])
        audit.require("Anonymous Author(s)" in text, "PDF does not show anonymous authorship")
        audit.require("Do Financial AI Agents Discover Alpha?" in text, "PDF title missing")
        for token in ["Sasha Cui", "zc362", "/nfs/", "alpha_evolve"]:
            audit.require(token not in text and token not in info, f"PDF identity/path leak: {token}")
        audit.require("References" in text or "REFERENCES" in text, "PDF references missing")
    log = paper / "icaif2026_submission.log"
    if log.is_file():
        log_text = log.read_text(errors="replace")
        for pattern in ["Overfull", "undefined references", "Citation(s) may have changed", "Fatal error"]:
            audit.require(pattern not in log_text, f"LaTeX log contains: {pattern}")

    if audit.failures:
        print(f"ICAIF AUDIT FAILED: {len(audit.failures)} failure(s) across {audit.checks} checks")
        for failure in audit.failures:
            print(f"- {failure}")
        return 1
    print(f"ICAIF AUDIT PASSED: {audit.checks} checks; evidence, anonymity, citations, and PDF verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
