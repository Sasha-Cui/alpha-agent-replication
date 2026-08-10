#!/usr/bin/env python3
"""Fail closed on the major revision's central factual and framing claims."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
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


def holm_count(p_values) -> int:
    """Return the number of sequential Holm rejections at familywise 5%."""
    ordered = sorted(float(value) for value in p_values)
    rejected = 0
    for rank, value in enumerate(ordered):
        if value <= .05 / (len(ordered) - rank):
            rejected += 1
        else:
            break
    return rejected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pdf", type=Path)
    parser.add_argument(
        "--bbl",
        type=Path,
        help="Explicit compiled bibliography for release-build validation",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    evidence = root / "paper_runs/submission_evidence"

    mapping_manifest = json.loads((evidence / "mapping_audit/manifest.json").read_text())
    for name, expected in mapping_manifest["output_sha256"].items():
        require(sha256(evidence / "mapping_audit" / name) == expected, f"mapping hash: {name}")
    mapping = rows(evidence / "mapping_audit/mapping_audit.csv")
    anchor_packet = rows(evidence / "mapping_audit/source_anchor_review_packet.csv")
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
    require(len(anchor_packet) == 13 and
            len({row["source_index"] for row in anchor_packet}) == 5,
            "source-anchor review packet scope changed")
    require(all(row["source_locator"] and row["researcher_supplied_changes"]
                for row in anchor_packet), "source-anchor packet is not inspectable")
    require(all(row["exact_original_claim_match"] == "no" and
                row["mapping_frozen_before_returns"] == "no" and
                row["independent_outcome_blind_review"] == "no"
                for row in anchor_packet), "source-anchor packet overstates fidelity")
    require(all(row["audit_status"] ==
                "post_hoc_source_anchor_audit; independent review pending"
                for row in anchor_packet), "source-anchor review status changed")
    quant_anchor = next(row for row in anchor_packet if row["candidate_id"] ==
                        "repo_quantevolver_return_sharpe_proxy")
    require("60-bar" in quant_anchor["source_supported_content"] and
            "12-month" in quant_anchor["researcher_supplied_changes"] and
            "not the literal released expression" in quant_anchor["researcher_supplied_changes"],
            "QuantEvolver horizon adaptation is not explicit")
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
    require({int(float(row["hac_lags"])) for row in primary} == {5},
            "primary HAC lag is not five")
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
    threshold_counts = []
    for cost in (0, 5, 10, 25, 50):
        group = [row for row in costs if row["status"] == "ok" and
                 int(float(row["cost_bps_one_way"])) == cost]
        cost_holm.append(holm_positive_count(group))
        material_p = [
            .5 * math.erfc(
                ((float(row["alpha_annualized"]) - .02) /
                 (12. * float(row["alpha_se_monthly"]))) / math.sqrt(2.)
            )
            for row in group
        ]
        threshold_counts.append((
            cost,
            sum(float(row["alpha_annualized"]) > 0 for row in group),
            sum(float(row["alpha_annualized"]) > 0 and
                float(row["p_value_two_sided"]) <= .05 for row in group),
            holm_positive_count(group),
            sum(float(row["alpha_annualized"]) >= .02 for row in group),
            sum(value <= .05 for value in material_p),
            holm_count(material_p),
        ))
    require(cost_holm == [1, 1, 1, 0, 0], f"cost-grid Holm counts changed: {cost_holm}")
    require(threshold_counts == [
        (0, 46, 7, 1, 33, 3, 0),
        (5, 42, 7, 1, 21, 1, 0),
        (10, 30, 6, 1, 16, 1, 0),
        (25, 18, 1, 0, 10, 1, 0),
        (50, 10, 0, 0, 1, 0, 0),
    ], f"gross-to-net threshold counts changed: {threshold_counts}")

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
    for required in [
        "Do Financial LLM Agents Discover New Alpha?",
        "all 50 retained reconstructions",
        "market plus 132 JKP",
        "\\LadderMedianFFFiveMomToJKPAttenuationPct",
        "\\input{tables/top_jkp_factor_matches.tex}",
        "descriptive spanning diagnostics, not confirmatory tests",
        "The other 29 retained works remain availability-only",
        "not the unavailable native agent",
        "47 of 50",
        "median nearest-factor correlation is 0.81",
        "none reports factor-adjusted alpha or uses JKP132",
        "proprietary pretraining corpora",
        "does not attribute any strategy to memorization, retrieval, or rediscovery",
        "The secondary repository audit targets 14 implementations",
        "It reproduces zero native agents",
        "All 98 works are cited",
        "\\ReconstructedWorkCount retained works",
        "\\RetainedMappingCount mappings",
        "cutoff-bounded systematic screen rather than a complete universe",
        "Reproducibility and Secondary Code Audit",
        "generated_corpus_citations.tex",
        "census_primary_records",
        "Public-prompt replay",
        "What changes when the LLM is actually prompted?",
        "\\input{tables/guruagents_prompt_replay_attribution.tex}",
        "\\PromptReplayBABMedianAlphaPct",
        "does not fully absorb the strongest replay result",
        "unrestricted JKP132 OLS",
    ]:
        require(required in tex, f"required disclosure absent: {required}")
    for forbidden in [
        "Can Public Artifacts Substantiate Financial-Agent Alpha?",
        "Does Public Evidence Support Financial-Agent Alpha Claims?",
        "AlphaAgent survivor",
        "Robust result",
        "Anonymous Empirical Artifact",
    ]:
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
        require("Do Financial LLM Agents Discover New Alpha?" in normalized_text,
                "wrong PDF title")
        require("50 retained strategy reconstructions" in normalized_text and
                "40 papers" in normalized_text,
                "headline strategy and paper denominators absent")
        require("47 of 50" in normalized_text and "0.81" in normalized_text,
                "nearest-factor evidence absent")
        require("median becomes -1.69%" in normalized_text and
                "none survives Holm" in normalized_text,
                "JKP absorption result absent")
        require("Most frequent JKP132 analogues" in normalized_text,
                "top-factor table absent")
        require("The five papers underlying the 13 source-grounded component tests" in normalized_text,
                "source-grounded paper inventory absent")
        require("All 98 works are cited" in normalized_text,
                "complete screened-corpus citation disclosure absent")
        require("40 retained works" in normalized_text and "50 mappings" in normalized_text,
                "retained reconstruction waterfall absent")
        require("29 retained works remain availability-only" in normalized_text,
                "availability-only retained-work disclosure absent")
        require("cutoff" in folded_text and "systematic screen" in folded_text,
                "systematic-search limitation absent")
        require("secondary repository audit targets 14 implementations" in folded_text and
                "zero native agents" in folded_text,
                "secondary code-audit boundary absent")
        require(all(token in folded_text for token in
                    ("descriptive", "not confirmatory", "post-hoc")),
                "conditional-inference boundary absent")
        require("proprietary pretraining" in folded_text and
                "does not attribute any strategy" in folded_text,
                "mechanism caveat absent")
        require("reproducibility and secondary code audit" in folded_text,
                "self-contained audit section absent")
        require("public-prompt replay" in folded_text and
                "what changes when the llm is actually prompted?" in folded_text,
                "prompt-replay methods or results section absent")
        require("5.80%" in normalized_text and "2.59%" in normalized_text and
                "11 of 12" in normalized_text,
                "prompt-replay BAB attribution absent")
        require("one archived-final buffett replay remains holm-positive" in folded_text and
                "unrestricted jkp132 ols" in folded_text,
                "prompt-replay identification boundary absent")
        require("supplement" not in folded_text, "PDF improperly depends on a supplement")
        from pypdf import PdfReader
        require(len(PdfReader(args.pdf).pages) <= 8, "PDF exceeds ICAIF's eight-page total limit")
        require("López de Prado" not in text and "Lopez de Prado" not in text,
                "prohibited author remains in PDF")
        require("AlphaAgent survivor" not in text, "forbidden PDF phrase")
    if args.bbl is not None:
        bbl_path = args.bbl.resolve()
        require(
            bbl_path.is_file(),
            f"explicit compiled bibliography is missing: {bbl_path}",
        )
        if bbl_path.is_file():
            bbl = bbl_path.read_text(encoding="utf-8")
            require(
                len(re.findall(r"^\\bibitem", bbl, flags=re.MULTILINE)) >= 100,
                "compiled bibliography does not contain all 98 corpus works plus methods",
            )
    print("major-revision validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
