#!/usr/bin/env python3
"""Fail closed on the major revision's central factual and framing claims."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def pdf_text(path: Path) -> str:
    """Extract PDF text with the system utility or the project environment fallback."""
    if shutil.which("pdftotext"):
        return subprocess.run(
            ["pdftotext", str(path), "-"], check=True, text=True, capture_output=True
        ).stdout
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def holm_positive_count(group) -> int:
    ordered = sorted(
        enumerate(float(row["p_value_two_sided"]) if float(row["alpha_annualized"]) > 0 else 1.0
                  for row in group),
        key=lambda item: item[1],
    )
    rejected = set()
    for rank, (index, value) in enumerate(ordered):
        if value <= .05 / (len(group) - rank):
            rejected.add(index)
        else:
            break
    return sum(index in rejected and float(row["alpha_annualized"]) > 0
               for index, row in enumerate(group))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pdf", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    evidence = root / "paper_runs/submission_evidence"

    mapping_manifest = json.loads((evidence / "mapping_audit/manifest.json").read_text())
    for name, expected in mapping_manifest["output_sha256"].items():
        require(sha256(evidence / "mapping_audit" / name) == expected, f"mapping hash: {name}")
    mapping = rows(evidence / "mapping_audit/mapping_audit.csv")
    require(len(mapping) == 62, "mapping family is not 62")
    tiers = {}
    for row in mapping:
        tiers[row["mapping_fidelity_tier"]] = tiers.get(row["mapping_fidelity_tier"], 0) + 1
    require(tiers == {"M0_narrative_translation": 49, "M1_example_or_motif_partial_support": 6,
                      "M1_named_rule_partial_support": 6, "M2_released_seed_expression": 1},
            f"mapping tiers changed: {tiers}")
    require(not mapping_manifest["mapping_outcome_blind"], "mapping unexpectedly marked outcome blind")
    require(not mapping_manifest["independent_second_coder"], "mapping unexpectedly marked double coded")
    require(mapping_manifest["exact_common_task_claims_identified"] == 0, "exact common-task count changed")
    require(mapping_manifest["good_faith_reconstruction"]["source_grounded_component_tests"] == 13,
            "source-grounded component count changed")
    require(mapping_manifest["good_faith_reconstruction"]["exploratory_favorable_stress_tests"] == 49,
            "narrative stress-test count changed")
    require(mapping_manifest["good_faith_reconstruction"]["source_level_negative_claims_permitted"] == 0,
            "source-level negative inference was improperly enabled")
    require(sum(row["anti_strawman_status"] == "eligible_for_component_level_interpretation_only"
                for row in mapping) == 13, "component-level anti-strawman roles changed")
    require(sum(row["anti_strawman_status"] == "exploratory_only_no_negative_inference"
                for row in mapping) == 49, "narrative anti-strawman roles changed")
    grounded_summary = {row["benchmark"]: row for row in rows(
        evidence / "mapping_audit/source_grounded_subset_summary.csv")}
    six_grounded = grounded_summary["six_factor_primary"]
    broad_grounded = grounded_summary["broad_jkp_post_hoc"]
    require(int(six_grounded["candidate_count"]) == 13, "six-factor grounded denominator changed")
    require(int(six_grounded["nominal_positive_5pct"]) == 1, "six-factor grounded nominal count changed")
    require(int(six_grounded["holm_positive_5pct_within_subset"]) == 0,
            "six-factor grounded Holm count changed")
    require(abs(float(six_grounded["median_alpha_annualized"]) - 0.0088150683489442) < 1e-12,
            "six-factor grounded median changed")
    require(int(broad_grounded["nominal_positive_5pct"]) == 0 and
            int(broad_grounded["holm_positive_5pct_within_subset"]) == 0,
            "broad grounded discoveries changed")

    census_scope = rows(evidence / "replication_scope/system_census_bibliography.csv")
    direct_scope = rows(evidence / "replication_scope/direct_code_attempt_inventory.csv")
    grounded_scope = rows(evidence / "replication_scope/source_grounded_component_inventory.csv")
    require(len(census_scope) == 67, "system-lineage census bibliography is not complete")
    require(len(direct_scope) == 14, "direct-code attempt inventory is not 14")
    require(sum(row["in_67_system_census"] == "yes" for row in direct_scope) == 8,
            "direct attempts inside the 67-system census changed")
    require(len(grounded_scope) == 13, "source-grounded component inventory is not 13")
    require(len({row["source_index"] for row in grounded_scope}) == 5,
            "source-grounded paper count is not five")

    direct = rows(root / "paper_runs/repository_ff5mom_metrics_summary.csv")
    require(len(direct) == 14, "direct audit denominator changed")
    testable = [row for row in direct if row["metric_status"] == "computed_jkp_only"]
    require(len(testable) == 1, "direct testable denominator changed")
    require(not any(row["beats_ff5mom_at_5pct"] == "True" for row in direct), "direct beater found")

    primary = [row for row in rows(evidence / "usa_retrospective_corrected/candidate_primary_results.csv")
               if row["status"] == "ok"]
    require(len(primary) == 62, "U.S. family is not fully executable")
    require(sum(float(row["alpha_annualized"]) > 0 and float(row["holm_p_value"]) <= .05
                for row in primary) == 1, "U.S. Holm count changed")
    require(sum(float(row["simultaneous_ci_low_annualized"]) >= .02 for row in primary) == 0,
            "U.S. material count changed")
    hac = rows(evidence / "usa_retrospective_corrected/hac_lag_sensitivity.csv")
    holm_by_lag = []
    for lag in (0, 3, 6, 12):
        group = [row for row in hac if int(row["fixed_hac_lags"]) == lag]
        holm_by_lag.append(holm_positive_count(group))
    require(holm_by_lag == [0, 1, 1, 0], f"HAC sensitivity changed: {holm_by_lag}")

    broad = rows(evidence / "usa_broad_jkp_crossfit/broad_jkp_crossfit_results.csv")
    require(len(broad) == 62 and {int(float(row["n_benchmark_factors"])) for row in broad} == {133},
            "broad factor family changed")
    require(sum(float(row["alpha_annualized"]) > 0 and float(row["holm_p_value"]) <= .05
                for row in broad) == 0, "broad Holm discovery found")

    forensic_manifest = json.loads((evidence / "international_failure_forensics/manifest.json").read_text())
    for name, expected in forensic_manifest["output_sha256"].items():
        require(sha256(evidence / "international_failure_forensics" / name) == expected,
                f"forensic hash: {name}")
    require(forensic_manifest["failure_events"] == 40, "failure event count changed")
    require(forensic_manifest["failure_candidates"] == 35, "failure candidate count changed")
    require(forensic_manifest["single_extreme_short_position_dominates"] == 40,
            "not all events have the documented dominant short return")

    tex = (root / "docs/paper/icaif2026_submission.tex").read_text(encoding="utf-8")
    for required in ["Does Public Evidence Support Financial-Agent Alpha Claims?",
                     "one yields a testable code-backed adaptation", "not outcome-blind",
                     "does \\emph{not} rerun rolling estimation", "excluded from headline performance inference",
                     "benefit of the doubt", "failure cannot count as evidence against the source",
                     "13 source-grounded component tests", "The 14 targeted implementation attempts",
                     "The five papers underlying the 13 source-grounded component tests"]:
        require(required in tex, f"required disclosure absent: {required}")
    for forbidden in ["Do Financial AI Agents Discover Alpha?", "AlphaAgent survivor", "Robust result"]:
        require(forbidden not in tex, f"forbidden overclaim present: {forbidden}")
    bibliography_text = "\n".join([
        (root / "docs/paper/icaif2026_references.bib").read_text(encoding="utf-8"),
        (root / "docs/paper/references.bib").read_text(encoding="utf-8"),
        tex,
    ])
    for forbidden in ["López de Prado", "LopezDePrado", "BaileyEtAl2017PBO",
                      "BaileyLopezDePrado2014DSR", "bailey2014deflated"]:
        require(forbidden not in bibliography_text, f"prohibited citation remains: {forbidden}")

    if args.pdf:
        text = pdf_text(args.pdf)
        require("Does Public Evidence Support Financial-Agent Alpha Claims?" in text, "wrong PDF title")
        require("producing 40 events" in text, "international forensic disclosure absent")
        require("13 source-grounded component tests" in text, "good-faith subset disclosure absent")
        require("cannot count as evidence against the source" in text,
                "anti-strawman source-protection disclosure absent")
        require("The 14 targeted implementation attempts" in text, "direct-code inventory absent")
        require("The five papers underlying the 13 source-grounded component tests" in text,
                "source-grounded paper inventory absent")
        require("López de Prado" not in text and "Lopez de Prado" not in text,
                "prohibited author remains in PDF")
        require("AlphaAgent survivor" not in text, "forbidden PDF phrase")
    print("major-revision validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
