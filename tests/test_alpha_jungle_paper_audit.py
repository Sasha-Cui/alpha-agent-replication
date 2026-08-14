from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_alpha_jungle_paper.py"
SPEC = importlib.util.spec_from_file_location("alpha_jungle_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def output_dir() -> Path:
    return ROOT / "paper_runs/paper_replication_audits/alpha_jungle"


def test_published_and_extended_result_censuses_are_complete_and_uncredited() -> None:
    published = read_csv(output_dir() / "aaai_final_table_result_conformance.csv")
    v1 = read_csv(output_dir() / "v1_extended_table_result_conformance.csv")
    v2 = read_csv(output_dir() / "v2_extended_table_result_conformance.csv")
    v3 = read_csv(output_dir() / "v3_extended_table_result_conformance.csv")
    assert len(published) == 64
    assert {row["paper_table"] for row in published} == {"Table_1_ablation"}
    assert Counter(row["paper_table"] for row in v1) == audit.V1_EXPECTED_TABLE_COUNTS
    assert Counter(row["paper_table"] for row in v2) == audit.V2_EXPECTED_TABLE_COUNTS
    assert Counter(row["paper_table"] for row in v3) == audit.V3_EXPECTED_TABLE_COUNTS
    assert len(v1) == 956
    assert len(v2) == 1184
    assert len(v3) == 1312
    all_rows = published + v1 + v2 + v3
    assert {row["paper_result_credit"] for row in all_rows} == {"False"}
    assert {row["native_alpha_jungle_result_credit"] for row in all_rows} == {"False"}


def test_version_lineage_preserves_semantic_relabel_and_current_metric_conflict() -> None:
    rows = read_csv(output_dir() / "version_lineage_audit.csv")
    assert len(rows) == 932
    assert sum(row["same_numeric_display_value"] == "True" for row in rows) == 925
    relabelled = [row for row in rows if row["AR_to_AER_semantic_relabel"] == "True"]
    assert len(relabelled) == 16
    assert {row["v1_metric"].split("_")[-1] for row in relabelled} == {"AR"}
    assert {row["v3_metric"].split("_")[-1] for row in relabelled} == {"AER"}
    assert {row["same_numeric_display_value"] for row in relabelled} == {"True"}
    assert {row["status"] for row in relabelled} == {
        "v1_AR_relabelled_as_v3_AER_same_numeric_value"
    }
    changed = [row for row in rows if row["same_numeric_display_value"] == "False"]
    assert len(changed) == 7
    assert {row["paper_table"] for row in changed} == {"llm_sensitivity"}
    current_conflicts = [
        row for row in rows
        if row["current_v3_AR_header_conflicts_with_AER_definition"] == "True"
    ]
    assert len(current_conflicts) == 200
    assert {row["native_reproduction_credit"] for row in rows} == {"False"}


def test_adjacent_version_lineage_pins_the_v2_transition_and_v3_additions() -> None:
    v1_v2 = read_csv(output_dir() / "v1_v2_version_lineage_audit.csv")
    v2_v3 = read_csv(output_dir() / "v2_v3_version_lineage_audit.csv")
    assert len(v1_v2) == 932
    assert sum(row["same_numeric_display_value"] == "True" for row in v1_v2) == 925
    assert sum(row["AR_to_AER_semantic_relabel"] == "True" for row in v1_v2) == 16
    v1_v2_changed = [row for row in v1_v2 if row["same_numeric_display_value"] == "False"]
    assert len(v1_v2_changed) == 7
    assert {row["paper_table"] for row in v1_v2_changed} == {"llm_sensitivity"}
    assert len(v2_v3) == 1184
    assert {row["same_numeric_display_value"] for row in v2_v3} == {"True"}
    assert {row["AR_to_AER_semantic_relabel"] for row in v2_v3} == {"False"}
    assert {row["native_reproduction_credit"] for row in v1_v2 + v2_v3} == {"False"}

    figures = read_csv(output_dir() / "figure_version_lineage.csv")
    v2_v3_figures = [row for row in figures if row["version_pair"] == "v2_v3"]
    assert len(v2_v3_figures) == 16
    assert {row["byte_identical"] for row in v2_v3_figures} == {"True"}
    assert {row["native_result_reproduced"] for row in figures} == {"False"}


def test_formula_component_credit_stops_at_the_adaptation_boundary() -> None:
    rows = read_csv(output_dir() / "formula_component_conformance.csv")
    assert len(rows) == 6
    implemented = [row for row in rows if row["local_component_executed"] == "True"]
    missing = [row for row in rows if row["local_component_executed"] == "False"]
    assert {row["paper_formula_number"] for row in implemented} == {"4", "5", "6"}
    assert {row["paper_formula_number"] for row in missing} == {"1", "2", "3"}
    assert {row["local_formula_tree_preserved"] for row in implemented} == {"True"}
    assert {row["local_cadence"] for row in implemented} == {"monthly_JKP"}
    assert {row["paper_cadence"] for row in rows} == {"daily"}
    assert {row["present_in_v2_source"] for row in rows} == {"True"}
    assert {row["paper_model_and_search_reproduced"] for row in rows} == {"False"}
    assert {row["native_alpha_jungle_result_credit"] for row in rows} == {"False"}


def test_cost_reconciliation_is_internal_arithmetic_not_result_reproduction() -> None:
    rows = read_csv(output_dir() / "cost_arithmetic_audit.csv")
    assert len(rows) == 30
    assert {row["match_at_paper_precision"] for row in rows} == {"True"}
    assert {row["evidence_type"] for row in rows} == {
        "paper_internal_arithmetic_not_independent_experiment"
    }
    assert {row["paper_result_credit"] for row in rows} == {"False"}
    fama_total = next(row for row in rows if row["row_index"] == "6" and row["metric"] == "total_cost_usd")
    assert fama_total["paper_value"] == fama_total["recomputed_from_same_table_inputs"] == "27.069"


def test_unaffiliated_candidate_is_pinned_but_broken_and_receives_no_credit() -> None:
    execution = json.loads((output_dir() / "community_execution.json").read_text(encoding="utf-8"))
    inventory = read_csv(output_dir() / "community_source_inventory.csv")
    conformance = read_csv(output_dir() / "community_method_conformance.csv")
    assert len(inventory) == 96
    assert sum(row["is_python"] == "True" for row in inventory) == 40
    assert sum(row["is_nominal_test"] == "True" for row in inventory) == 3
    assert execution["compile_success"] is True
    assert execution["python_files_compiled"] == 40
    assert execution["package_import_success"] is False
    assert execution["package_import_missing_internal_data_module"] is True
    assert execution["pytest_exit_code"] == 2
    assert execution["pytest_collection_errors"] == 3
    assert execution["pytest_tests_passed"] == 0
    assert execution["author_linked"] is False
    assert execution["native_paper_result_credit"] is False
    assert {row["author_source_credit"] for row in conformance} == {"False"}
    assert {row["paper_result_credit"] for row in conformance} == {"False"}


def test_method_and_claim_audits_retain_the_decisive_blockers() -> None:
    methods = read_csv(output_dir() / "method_specification_audit.csv")
    claims = read_csv(output_dir() / "qualitative_claim_audit.csv")
    assert len(methods) == 63
    assert sum(row["severity"] == "blocking" for row in methods) == 26
    assert sum(row["assessment"] == "conflict" for row in methods) == 2
    assert {row["native_alpha_jungle_verified"] for row in methods} == {"False"}
    author_source = next(row for row in methods if row["dimension"] == "author-linked implementation")
    assert (author_source["assessment"], author_source["severity"]) == ("missing", "blocking")
    metric_lineage = next(
        row for row in methods if row["dimension"] == "v1 AR to v2/v3/final AER lineage"
    )
    assert (metric_lineage["assessment"], metric_lineage["severity"]) == ("conflict", "blocking")
    published = next(row for row in claims if row["claim"] == "published Table 1 result reproduction")
    assert published["observed"].startswith("0/64")
    community = next(row for row in claims if row["paper_version"] == "community_candidate")
    assert community["assessment"] == "not_author_source_and_not_operational_replication"


def test_manifest_provenance_prompt_and_output_hashes_are_consistent() -> None:
    manifest = json.loads((output_dir() / "manifest.json").read_text(encoding="utf-8"))
    provenance = json.loads((output_dir() / "source_provenance.json").read_text(encoding="utf-8"))
    native = json.loads((output_dir() / "native_execution.json").read_text(encoding="utf-8"))
    assert manifest["paper_evidence_route"] == (
        "paper_only_underspecified_with_three_adapted_disclosed_formula_components"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["published_final_table_result_cells"] == 64
    assert manifest["v1_extended_table_result_cells"] == 956
    assert manifest["v2_extended_table_result_cells"] == 1184
    assert manifest["v3_extended_table_result_cells"] == 1312
    assert manifest["native_alpha_jungle_result_cells_reproduced"] == 0
    assert manifest["adapted_formula_trees_executed"] == 3
    assert manifest["adapted_formula_trees_with_paper_result_credit"] == 0
    assert manifest["common_v1_v3_same_display_value"] == 925
    assert manifest["common_v1_v2_same_display_value"] == 925
    assert manifest["v1_AR_cells_relabelled_v2_AER"] == 16
    assert manifest["common_v2_v3_result_cells"] == 1184
    assert manifest["common_v2_v3_same_display_value"] == 1184
    assert manifest["v3_result_cells_added_beyond_v2"] == 128
    assert manifest["v1_AR_cells_relabelled_v3_AER"] == 16
    assert manifest["v3_AR_header_cells_conflicting_with_current_AER_definition"] == 228
    assert manifest["paper_source_compilation"]["v1"]["pages"] == 30
    assert manifest["paper_source_compilation"]["v2"]["pages"] == 30
    assert manifest["paper_source_compilation"]["v3"]["pages"] == 31
    assert {
        tuple(result["exit_codes"])
        for result in manifest["paper_source_compilation"].values()
    } == {(0, 0, 0)}
    assert all(
        result["stable_cross_references"]
        for result in manifest["paper_source_compilation"].values()
    )
    assert native["native_alpha_jungle_execution_attempted"] is False
    assert native["official_pdf_table_text_verified"] is True
    assert provenance["official_author_repository_found"] is False
    assert provenance["publication_authority"]["pdf_sha256"] == audit.AAAI_FINAL_PDF_SHA256
    assert provenance["intermediate_arxiv"]["pdf_sha256"] == audit.ARXIV_V2_PDF_SHA256
    assert provenance["community_candidate"]["author_linked"] is False
    for version in ("v1", "v2", "v3"):
        prompt = (output_dir() / f"paper_prompts_{version}.tex.txt").read_text(encoding="utf-8")
        assert prompt.count("Generation Prompt") >= 2
        assert "Alpha Overfitting Risk Assessment Prompt" in prompt
        assert "Alpha Refinement Prompt" in prompt
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output_dir() / filename) == expected


def test_dynamic_pinned_sources_and_parsers_when_available() -> None:
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/alpha_jungle_paper_audit")
    community = paper / "candidate_dtbtc"
    if not paper.exists() or not community.exists():
        return
    validation = audit.validate_inputs(paper, community)
    assert validation["author_linked_repository_found"] is False
    v1 = audit.parse_results(paper, "v1")
    v2 = audit.parse_results(paper, "v2")
    v3 = audit.parse_results(paper, "v3")
    published = audit.published_final_rows(paper, v3)
    lineage = audit.version_lineage(v1, v3)
    v1_v2_lineage = audit.adjacent_version_lineage(v1, v2, "v1", "v2")
    v2_v3_lineage = audit.adjacent_version_lineage(v2, v3, "v2", "v3")
    costs = audit.cost_arithmetic(v3)
    formulas = audit.formula_component_conformance(paper, ROOT)
    assert (
        len(published),
        len(v1),
        len(v2),
        len(v3),
        len(lineage),
        len(v1_v2_lineage),
        len(v2_v3_lineage),
        len(costs),
        len(formulas),
    ) == (
        64,
        956,
        1184,
        1312,
        932,
        932,
        1184,
        30,
        6,
    )
