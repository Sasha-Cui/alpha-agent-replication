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
from collections import Counter
from pathlib import Path

from validate_faithful_component_replications import validation_failures


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

    strict_dir = evidence / "strict_proxy_fidelity_audit"
    strict_manifest = json.loads((strict_dir / "manifest.json").read_text())
    for name, expected in strict_manifest["output_sha256"].items():
        require(sha256(strict_dir / name) == expected, f"strict-audit hash: {name}")
    strict_rows = rows(strict_dir / "legacy_50_proxy_fidelity_audit.csv")
    require(len(strict_rows) == 50, "strict proxy-fidelity audit is not 50 rows")
    strict_counts = Counter(row["grade"] for row in strict_rows)
    require(
        {grade: strict_counts.get(grade, 0) for grade in ("A", "B", "C", "D", "U")}
        == {"A": 0, "B": 0, "C": 15, "D": 33, "U": 2},
        f"strict proxy-fidelity grades changed: {strict_counts}",
    )
    require(
        all(row["native_agent_output_reproduced"] == "no" for row in strict_rows),
        "legacy proxy audit improperly claims a native-agent output",
    )
    require(
        strict_manifest["jkp_characteristic_composites"] == 46
        and strict_manifest["common_monthly_portfolio_rule"] == 47,
        "legacy proxy construction counts changed",
    )
    require(
        strict_manifest["native_agent_outputs_reproduced"] == 0
        and "construction diagnostics" in strict_manifest["allowed_empirical_use"],
        "strict audit does not enforce the construction-only evidence boundary",
    )

    faithful_dir = root / "paper_runs/faithful_component_replications"
    failures = validation_failures(faithful_dir)
    require(
        not failures,
        "primary faithful-component gate failed: " + "; ".join(failures),
    )
    faithful_manifest = json.loads((faithful_dir / "manifest.json").read_text())
    require(
        faithful_manifest["n_counted_components"] == 3
        and faithful_manifest["n_grade_a_or_b"] == 3
        and faithful_manifest["faithfulness_pass_rate"] == 1.0
        and faithful_manifest["n_return_rows"] == 915
        and faithful_manifest["n_holding_rows"] == 184596
        and faithful_manifest["n_nonconsecutive_forward_holding_rows"] == 6,
        "primary faithful-component census or 100% gate changed",
    )
    faithful_ledger = rows(faithful_dir / "faithfulness_ledger.csv")
    require(
        len(faithful_ledger) == 3
        and Counter(row["grade"] for row in faithful_ledger) == {"B": 3}
        and all(row["counted_primary"].casefold() == "true" for row in faithful_ledger),
        "primary ledger is not exactly three counted strict-B rows",
    )
    faithful_attribution_manifest = json.loads(
        (faithful_dir / "attribution_manifest.json").read_text()
    )
    for name, expected in faithful_attribution_manifest["output_sha256"].items():
        require(
            sha256(faithful_dir / name) == expected,
            f"primary formula attribution hash: {name}",
        )
    require(
        faithful_attribution_manifest["n_candidates"] == 3
        and faithful_attribution_manifest["n_common_months"] == 270
        and faithful_attribution_manifest["n_evaluation_months"] == 150,
        "primary formula attribution sample changed",
    )
    require(
        faithful_attribution_manifest["multiplicity"]
        == "Holm across 3 formula components within each benchmark; not across benchmark specifications",
        "primary formula multiplicity family changed",
    )
    faithful_results = rows(faithful_dir / "attribution_results.csv")
    require(
        len(faithful_results) == 12
        and {int(row["n_months"]) for row in faithful_results} == {150}
        and {int(row["hac_lags"]) for row in faithful_results} == {4},
        "primary formula attribution result dimensions changed",
    )
    faithful_summary = {
        row["benchmark_id"]: row
        for row in rows(faithful_dir / "attribution_summary.csv")
    }
    expected_faithful_summary = {
        "capm": (0.012249689311478715, 3, 0),
        "ff3": (0.002548814243069449, 2, 1),
        "ff5_mom": (-0.004008847614354719, 1, 0),
        "ff5_mom_jkp132": (0.006713086230964472, 2, 0),
    }
    require(
        set(faithful_summary) == set(expected_faithful_summary),
        "primary formula benchmarks changed",
    )
    for benchmark, (median, positive, holm) in expected_faithful_summary.items():
        row = faithful_summary[benchmark]
        require(
            math.isclose(float(row["median_alpha_annualized"]), median, abs_tol=1e-12)
            and int(row["positive_alpha_count"]) == positive
            and int(row["holm_positive_count"]) == holm,
            f"primary formula summary changed: {benchmark}",
        )
    faithful_holm = [
        row
        for row in faithful_results
        if row["holm_positive_5pct"].casefold() == "true"
    ]
    require(
        len(faithful_holm) == 1
        and faithful_holm[0]["candidate_id"] == "quantevolver_price_zscore_reversal_120"
        and faithful_holm[0]["benchmark_id"] == "ff3"
        and math.isclose(float(faithful_holm[0]["alpha_annualized"]), 0.06950820555606094, abs_tol=1e-12)
        and math.isclose(float(faithful_holm[0]["alpha_t_hac"]), 2.600934010610762, abs_tol=1e-12)
        and math.isclose(float(faithful_holm[0]["holm_p_within_benchmark"]), 0.027891100679990045, abs_tol=1e-12),
        "primary formula Holm-positive row changed",
    )

    formula_dir = root / "paper_runs/fidelity_formula_components"
    formula_manifest = json.loads((formula_dir / "manifest.json").read_text())
    formula_access_gated = {"formation_holdings.csv", "monthly_return_paths.csv"}
    for name, expected in formula_manifest["output_sha256"].items():
        path = formula_dir / name
        if name in formula_access_gated and not path.is_file():
            continue
        require(
            path.is_file() and sha256(path) == expected,
            f"formula hash: {name}",
        )
    require(
        formula_manifest["n_candidates"] == 12
        and formula_manifest["n_return_rows"] == 3660,
        "formula component row counts changed",
    )
    require(
        formula_manifest["n_complete_case_candidate_months"] == 2620
        and formula_manifest["n_imputed_candidate_months"] == 1040
        and formula_manifest["n_imputed_holdings"] == 1782,
        "formula complete-case and imputed-month counts changed",
    )
    require(
        math.isclose(
            formula_manifest["total_imputed_target_weight"],
            46.45656780476914,
            abs_tol=1e-12,
        ),
        "formula missing-target-weight diagnostic changed",
    )
    realization = formula_manifest["realization_diagnostics_by_candidate"]
    require(
        len(realization) == 12
        and all(item["n_path_months"] == 305 for item in realization.values())
        and all(item["n_omitted_no_calendar_horizon"] == 1 for item in realization.values())
        and all(
            item["n_omitted_no_observed_required_leg"] == 0
            for item in realization.values()
        ),
        "formula path or terminal-horizon diagnostics changed",
    )
    formula_ledger = rows(formula_dir / "formula_fidelity_ledger.csv")
    formula_grades = Counter(row["grade"] for row in formula_ledger)
    require(
        len(formula_ledger) == 12
        and formula_grades == {"B": 3, "B-conditional": 5, "C-conditional": 4},
        f"formula fidelity grades changed: {formula_grades}",
    )
    require(
        all(row["native_agent_replication"].casefold() == "false" for row in formula_ledger)
        and all(
            "without reranking, substitution, or weight changes"
            in row["realized_return_handling"]
            for row in formula_ledger
        ),
        "formula ledger overclaims replication or obscures missing-return handling",
    )

    attribution_manifest = json.loads(
        (formula_dir / "attribution_manifest.json").read_text()
    )
    for name, expected in attribution_manifest["output_sha256"].items():
        artifact_path = root / name if name.startswith("docs/") else formula_dir / name
        require(sha256(artifact_path) == expected, f"formula attribution hash: {name}")
    require(
        attribution_manifest["n_candidates"] == 12
        and attribution_manifest["n_common_months"] == 270
        and attribution_manifest["n_evaluation_months"] == 150,
        "formula attribution sample changed",
    )
    require(
        attribution_manifest["multiplicity"]
        == "Holm across 12 formula components within each benchmark; not across benchmark specifications",
        "formula multiplicity family changed",
    )
    formula_results = rows(formula_dir / "attribution_results.csv")
    require(
        len(formula_results) == 48
        and {int(row["n_months"]) for row in formula_results} == {150}
        and {int(row["hac_lags"]) for row in formula_results} == {4},
        "formula attribution result dimensions changed",
    )
    formula_summary = {
        row["benchmark_id"]: row
        for row in rows(formula_dir / "attribution_summary.csv")
    }
    expected_formula_summary = {
        "capm": (0.00878256811808894, 7, 1),
        "ff3": (-0.011258696287808682, 4, 0),
        "ff5_mom": (-0.005931704336225034, 5, 0),
        "ff5_mom_jkp132": (0.009776930797485038, 9, 0),
    }
    require(set(formula_summary) == set(expected_formula_summary), "formula benchmarks changed")
    for benchmark, (median, positive, holm) in expected_formula_summary.items():
        row = formula_summary[benchmark]
        require(
            math.isclose(float(row["median_alpha_annualized"]), median, abs_tol=1e-12)
            and int(row["positive_alpha_count"]) == positive
            and int(row["holm_positive_count"]) == holm,
            f"formula summary changed: {benchmark}",
        )
    formula_holm = [
        row for row in formula_results if row["holm_positive_5pct"].casefold() == "true"
    ]
    require(
        len(formula_holm) == 1
        and formula_holm[0]["candidate_id"] == "efs_regime_switched_return_volatility"
        and formula_holm[0]["benchmark_id"] == "capm"
        and math.isclose(float(formula_holm[0]["alpha_annualized"]), 0.074401710985317, abs_tol=1e-12)
        and math.isclose(float(formula_holm[0]["alpha_t_hac"]), 2.902815021543435, abs_tol=1e-12)
        and math.isclose(
            float(formula_holm[0]["holm_p_within_benchmark"]), 0.0443790006248571, abs_tol=1e-12
        ),
        "formula Holm-positive row changed",
    )
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
        "A Fidelity Audit, Disclosed-Formula Study, and Prompt-Decision Replay",
        "A0/B0/C15/D33/U2",
        "46 of the 50 strategies",
        "47 use essentially the same monthly",
        "cannot adjudicate native-agent performance",
        "primary formula sample instead exhaustively includes the three evaluator-valid seeds",
        "3/3 strict grade B components (100\\%)",
        "Only grade-B mechanical adaptations are made",
        "There is no missing-return imputation",
        "184,596 formation holdings",
        "Six holdings use a nonconsecutive next available bar",
        "median annualized out-of-window residual is $+1.2250\\%$ under CAPM",
        "$+0.2549\\%$ under FF3",
        "$-0.4009\\%$ under FF5 plus momentum",
        "$+0.6713\\%$ under FF5 plus momentum plus JKP132",
        "$6.9508\\%$",
        "Holm $p=0.0279$",
        "five B-conditional and four C-conditional rows are excluded",
        "completed the D07 three-row owner attestation",
        "\\input{tables/faithful_component_census.tex}",
        "Holm adjustment is across the three faithful components",
        "\\input{tables/guruagents_prompt_replay_attribution.tex}",
        "current 2026 OpenRouter-served",
        "original provider or model snapshot",
        "Holm adjustment is across the 12 replay paths",
        "not across benchmark specifications",
        "unrestricted JKP132 OLS",
        "figures/guruagents_paired_attribution.pdf",
        "This is attenuation, not universal absorption",
        "Construction Diagnostic: Legacy JKP-Built Proxies",
        "not a replication result for the cited papers",
        "do not use the 50-strategy ladder to estimate an agent-alpha prevalence rate",
        "This does not prove either universal novelty or universal absorption",
        "census_primary_records",
    ]:
        require(required in tex, f"required disclosure absent: {required}")
    for forbidden in [
        "Can Public Artifacts Substantiate Financial-Agent Alpha?",
        "Does Public Evidence Support Financial-Agent Alpha Claims?",
        "AlphaAgent survivor",
        "Robust result",
        "Anonymous Empirical Artifact",
        "FORMULA_RESULTS_PLACEHOLDER",
        "paper's main result",
        "\\input{tables/top_jkp_factor_matches.tex}",
        "all 12 are faithful",
        "\\input{tables/disclosed_formula_components.tex}",
        "306 net-return months per component",
        "3,672 candidate-month",
        "-0.7199\\% under CAPM",
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
        require("A Fidelity Audit" in normalized_text, "revised PDF subtitle absent")
        require(
            all(token in normalized_text for token in
                ("A0/B0/C15/D33/U2", "46 of the 50 strategies",
                 "47 use essentially the same monthly")),
            "strict proxy-fidelity audit facts absent",
        )
        require(
            all(
                token in normalized_text
                for token in (
                    "3/3 strict grade B",
                    "100%",
                    "305 return observations",
                    "184,596 formation holdings",
                    "Six holdings use a nonconsecutive",
                    "1.2250%",
                    "0.2549%",
                    "0.4009%",
                    "0.6713%",
                    "6.9508%",
                    "0.0279",
                )
            )
            and "exhaustive set of evaluator-valid example seeds" in folded_text
            and "no missing-return imputation" in folded_text
            and "five b-conditional and four c-conditional rows are excluded" in folded_text
            and "completed the d07 three-row owner attestation" in folded_text,
            "primary faithful-component scope, results, or limitations absent",
        )
        require(
            "current 2026 openrouter-served" in folded_text
            and "original provider or model snapshot" in folded_text,
            "current-endpoint replay limitation absent",
        )
        require(
            "5.80%" in normalized_text
            and "2.59%" in normalized_text
            and "11 of 12" in normalized_text,
            "prompt-replay BAB attribution absent",
        )
        require(
            "one archived-final buffett path remains holm-positive" in folded_text
            and "unrestricted jkp132 ols" in folded_text,
            "prompt-replay identification boundary absent",
        )
        require(
            "construction diagnostic: legacy jkp-built proxies" in folded_text
            and "not a replication result for the cited papers" in folded_text,
            "legacy proxy layer is not visibly quarantined",
        )
        require(
            "this does not prove either universal novelty or universal absorption"
            in folded_text,
            "bounded conclusion absent",
        )
        require("most frequent jkp132 analogues" not in folded_text,
                "legacy nearest-factor table remains in the PDF")
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
                len(re.findall(r"^\\bibitem", bbl, flags=re.MULTILINE)) >= 10,
                "compiled bibliography is missing cited methods or source anchors",
            )
    print("major-revision validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
