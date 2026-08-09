#!/usr/bin/env python3
"""Fail closed on the major revision's central factual and framing claims."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


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
    pretrim_scope = rows(evidence / "replication_scope/pretrim_primary_record_inventory.csv")
    waterfall = rows(evidence / "replication_scope/work_level_evidence_waterfall.csv")
    citation_metadata = rows(root / "literature_review/census_v1/primary_record_metadata.csv")
    search_log = rows(root / "literature_review/census_v1/search_log.csv")
    search_protocol = (root / "literature_review/census_v1/search_protocol.md").read_text(
        encoding="utf-8"
    )
    require(len(search_log) == 22, "search route log does not contain all planned routes")
    for query in ("Q1", "Q2", "Q3"):
        require(sum(row["query_family"] == query for row in search_log) == 5,
                f"search route coverage changed for {query}")
    require(all(row["completed_by_utc"] == "2026-08-02T23:59:59Z" for row in search_log),
            "search cutoff changed")
    require(all(row["raw_hit_count_preserved"] == "no" for row in search_log),
            "search log incorrectly claims preserved raw hit counts")
    for required in ("cutoff-bounded systematic screen", "result pages, rankings, and hit counts",
                     "Crossref and OpenAlex", "Borderline records"):
        require(required in search_protocol, f"search-protocol disclosure absent: {required}")
    require(len(census_scope) == 67, "system-lineage census bibliography is not complete")
    require(len(direct_scope) == 14, "direct-code attempt inventory is not 14")
    require(sum(row["in_67_system_census"] == "yes" for row in direct_scope) == 8,
            "direct attempts inside the 67-system census changed")
    require(len(grounded_scope) == 13, "source-grounded component inventory is not 13")
    require(len({row["source_index"] for row in grounded_scope}) == 5,
            "source-grounded paper count is not five")
    require(len(pretrim_scope) == len(citation_metadata) == 104,
            "pre-trim primary-record inventory is not 104")
    require(len({row["canonical_work_id"] for row in citation_metadata}) == 98,
            "pre-trim canonical work count is not 98")
    require(sum(row["main_ft"] == "yes" for row in citation_metadata) == 71,
            "retained primary-record link count is not 71")
    retained_works = {row["canonical_work_id"] for row in citation_metadata
                      if row["main_ft"] == "yes"}
    require(len(retained_works) == 69, "retained canonical work count is not 69")
    preferred = [row for row in citation_metadata if row["preferred_citation"] == "yes"]
    require(len(preferred) == 98, "preferred citation count is not 98")
    require(len(waterfall) == len({row["canonical_work_id"] for row in waterfall}) == 98,
            "work-level evidence waterfall is not a 98-work partition")
    require(sum(row["screen_decision"] == "retained_formula_or_trading" for row in waterfall) == 69
            and sum(row["screen_decision"] == "screened_out" for row in waterfall) == 29,
            "98-to-69 screen waterfall changed")
    require(sum(row["good_faith_reconstruction"] == "yes" for row in waterfall) == 40
            and sum(row["reconstruction_fidelity"] == "availability_only" for row in waterfall) == 29,
            "69-to-40 reconstruction waterfall changed")
    require(sum(int(row["mapping_count"]) for row in waterfall) == 50,
            "retained works no longer produce 50 mappings")
    require(sum(row["reconstruction_fidelity"] == "source_grounded_component_test"
                for row in waterfall) == 5,
            "source-grounded work count changed")
    require(sum(row["reconstruction_fidelity"] == "narrative_favorable_stress_test"
                for row in waterfall) == 35,
            "narrative reconstructed-work count changed")
    require(sum(row["direct_code_route"] == "retained_code_attempt" for row in waterfall) == 8
            and sum(row["direct_code_route"] == "diagnostic_code_attempt" for row in waterfall) == 6,
            "retained/diagnostic code-attempt split changed")
    require(sum(row["native_agent_replication"] == "yes" for row in waterfall) == 0
            and sum(row["code_backed_adaptation"] == "yes_released_seed_expression"
                    for row in waterfall) == 1,
            "native/code-backed replication outcome changed")
    census_bib = (root / "docs/paper/census_primary_records.bib").read_text(encoding="utf-8")
    bib_keys = set(re.findall(r"^@\w+\{([^,]+),", census_bib, flags=re.MULTILINE))
    require(bib_keys == {row["bibtex_key"] for row in preferred},
            "generated corpus bibliography does not cover every canonical work")
    citation_macros = (root / "docs/paper/generated_corpus_citations.tex").read_text(encoding="utf-8")
    cited_corpus_keys = {
        key.strip()
        for body in re.findall(r"\\cite\{([^}]+)\}", citation_macros)
        for key in body.split(",")
        if key.strip()
    }
    require(cited_corpus_keys == {row["bibtex_key"] for row in preferred},
            "manuscript macros do not cite all 98 screened works")

    direct = rows(root / "paper_runs/repository_ff5mom_metrics_summary.csv")
    require(len(direct) == 14, "direct audit denominator changed")
    testable = [row for row in direct if row["metric_status"] == "computed_jkp_only"]
    require(len(testable) == 1, "direct testable denominator changed")
    require(not any(row["beats_ff5mom_at_5pct"] == "True" for row in direct), "direct beater found")
    require(abs(float(testable[0]["candidate_standalone_oos_sharpe"]) - 0.3159540989730854) < 1e-12,
            "direct seed-adaptation Sharpe changed")

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

    missing_dir = evidence / "usa_missing_return_sensitivity"
    missing_manifest = json.loads((missing_dir / "manifest.json").read_text())
    require(missing_manifest["analysis_label"] ==
            "post_hoc_referee_requested_missing_return_sensitivity",
            "missing-return sensitivity has wrong analysis label")
    for name, expected in missing_manifest["output_sha256"].items():
        require(sha256(missing_dir / name) == expected, f"missing-return hash: {name}")
    missing_summary = {row["policy"]: row for row in rows(missing_dir / "policy_summary.csv")}
    require(set(missing_summary) == {"zero_primary", "position_adverse_100"},
            "missing-return policy set changed")
    adverse = missing_summary["position_adverse_100"]
    require(int(adverse["n_estimable"]) == 62, "adverse missing-return family is not 62")
    require(abs(float(adverse["median_alpha_annualized"]) - (-0.048404310807554085)) < 1e-12,
            "adverse missing-return median changed")
    require(int(adverse["positive_alpha_count"]) == 4 and
            int(adverse["nominal_positive_5pct"]) == 0 and
            int(adverse["holm_positive_5pct"]) == 0,
            "adverse missing-return positive counts changed")

    costs = rows(evidence / "usa_retrospective_corrected/candidate_cost_alpha_results.csv")
    cost_holm = []
    for cost in (0, 5, 10, 25, 50):
        group = [row for row in costs if row["status"] == "ok" and
                 int(float(row["cost_bps_one_way"])) == cost]
        cost_holm.append(holm_positive_count(group))
    require(cost_holm == [1, 1, 1, 0, 0], f"cost-grid Holm counts changed: {cost_holm}")

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
    for required in ["Can Public Artifacts Substantiate Financial-Agent Alpha?",
                     "yields a testable code-backed adaptation", "not outcome-blind",
                     "does \\emph{not} rerun rolling estimation", "excluded from headline performance inference",
                     "benefit of the doubt", "failure cannot count as evidence against the source",
                     "13 source-grounded component tests", "The 14 targeted implementation attempts",
                     "The five papers underlying the 13 source-grounded component tests",
                     "103 candidate lineages backed by 98 distinct cited works",
                     "All 98 works are cited", "\\ReconstructedWorkCount retained works",
                     "\\RetainedMappingCount mappings",
                     "29 remain availability-only", "covers eight retained works",
                     "cutoff-bounded systematic screen rather than a complete universe",
                     "these statistics are descriptive conditional diagnostics",
                     "The position-adverse unit-move stress",
                     "supplies numerical anchors behind Figure",
                     "not an independent out-of-sample discovery test",
                     "\\USGrossPositiveBreakEvenMedianBps",
                     "Reproducibility and Audit Trail", "generated_corpus_citations.tex",
                     "census_primary_records"]:
        require(required in tex, f"required disclosure absent: {required}")
    for forbidden in ["Do Financial AI Agents Discover Alpha?",
                      "Does Public Evidence Support Financial-Agent Alpha Claims?",
                      "AlphaAgent survivor", "Robust result",
                      "Anonymous Empirical Artifact"]:
        require(forbidden not in tex, f"forbidden overclaim present: {forbidden}")
    require("supplement" not in tex.casefold(), "paper improperly depends on a supplement")
    bibliography_text = "\n".join([
        (root / "docs/paper/icaif2026_references.bib").read_text(encoding="utf-8"),
        (root / "docs/paper/references.bib").read_text(encoding="utf-8"),
        census_bib,
        (root / "literature_review/census_v1/primary_record_metadata.csv").read_text(encoding="utf-8"),
        tex,
    ])
    for forbidden in ["López de Prado", "LopezDePrado", "BaileyEtAl2017PBO",
                      "BaileyLopezDePrado2014DSR", "bailey2014deflated"]:
        require(forbidden not in bibliography_text, f"prohibited citation remains: {forbidden}")

    if args.pdf:
        text = pdf_text(args.pdf)
        normalized_text = re.sub(r"\s+", " ", text)
        folded_text = normalized_text.casefold()
        require("Can Public Artifacts Substantiate Financial-Agent Alpha?" in normalized_text,
                "wrong PDF title")
        require("producing 40 events" in normalized_text, "international forensic disclosure absent")
        require("13 source-grounded component tests" in text, "good-faith subset disclosure absent")
        require("cannot count as evidence against the source" in text,
                "anti-strawman source-protection disclosure absent")
        require("The 14 targeted implementation attempts" in text, "direct-code inventory absent")
        require("The five papers underlying the 13 source-grounded component tests" in text,
                "source-grounded paper inventory absent")
        require("103 candidate lineages" in normalized_text and "98 distinct cited works" in normalized_text,
                "pre-trim breadth disclosure absent")
        require("69 works" in normalized_text, "retained bibliography breadth disclosure absent")
        require("All 98 works are cited" in normalized_text,
                "complete screened-corpus citation disclosure absent")
        require("40 retained works" in normalized_text and "50 mappings" in normalized_text,
                "retained reconstruction waterfall absent")
        require("29 remain availability-only" in normalized_text,
                "availability-only retained-work disclosure absent")
        require("covers eight retained works" in normalized_text,
                "retained code-route disclosure absent")
        require("cutoff-bounded systematic screen" in folded_text,
                "systematic-search limitation absent")
        require(all(token in folded_text for token in
                    ("descriptive", "conditional", "not confirmatory")),
                "conditional-inference boundary absent")
        require(all(token in folded_text for token in
                    ("position-adverse", "unit-move stress", "missing")),
                "missing-return sensitivity absent")
        require("reproducibility and audit trail" in folded_text,
                "self-contained audit section absent")
        require("Numerical anchors for Figure" in text and
                all(token in normalized_text for token in ("0.316", "6.93%", "4.46%")),
                "alpha/t-stat/Sharpe anchor table absent")
        require("supplement" not in folded_text, "PDF improperly depends on a supplement")
        from pypdf import PdfReader
        require(len(PdfReader(args.pdf).pages) <= 8, "PDF exceeds ICAIF's eight-page total limit")
        bbl = (root / "docs/paper/icaif2026_submission.bbl").read_text(encoding="utf-8")
        require(len(re.findall(r"^\\bibitem", bbl, flags=re.MULTILINE)) >= 110,
                "compiled bibliography does not contain all 98 corpus works plus methods")
        require("López de Prado" not in text and "Lopez de Prado" not in text,
                "prohibited author remains in PDF")
        require("AlphaAgent survivor" not in text, "forbidden PDF phrase")
    print("major-revision validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
