"""Contracts for the fail-closed QuantAgent self-improving paper audit."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_quantagent_self_improving_paper.py"
SPEC = importlib.util.spec_from_file_location("audit_quantagent_self_improving_paper", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)

PAPER = (
    ROOT
    / "literature_review/papers/"
    "26_2402_03755_quantagent_seeking_holy_grail_in_trading_by_self_improving_large_language_model.pdf"
)
OUTPUT = ROOT / "paper_runs/paper_replication_audits/quantagent_self_improving"


def csv_rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_official_pdf_is_pinned_and_all_15_pages_are_audited() -> None:
    assert audit.sha256(PAPER) == audit.EXPECTED_PDF_SHA256
    text, pages, metadata = audit.pdf_text(PAPER)
    audit.validate_pdf(text, pages)
    assert pages == 15
    assert "QuantAgent" in str(metadata["/Title"])


def test_source_inventory_and_rebuild_are_document_not_result_credit() -> None:
    rows = csv_rows("source_file_inventory.csv")
    assert len(rows) == 44
    by_name = {row["source_member"]: row for row in rows}
    assert by_name["main.tex"]["sha256"] == audit.EXPECTED_MAIN_TEX_SHA256
    assert by_name["tex/appendix/experiment.tex"]["sha256"] == audit.EXPECTED_APPENDIX_TEX_SHA256
    assert sum(row["role"] == "active_result_figure_display_geometry" for row in rows) == 3
    assert all(row["raw_experimental_array_or_table"] == "no" for row in rows)
    assert all(row["native_pipeline_code"] == "no" for row in rows)

    build = json.loads((OUTPUT / "source_build_audit.json").read_text(encoding="utf-8"))
    assert build["source_document_rebuild_succeeded"] is True
    assert build["official_pages"] == build["rebuilt_pages"] == 15
    assert build["token_multiset_jaccard"] > 0.999
    assert build["document_rebuild_credit"] is True
    assert build["experimental_reproduction_credit"] is False


def test_all_four_published_listings_are_checked_exactly_and_fail_closed() -> None:
    rows = csv_rows("published_code_conformance.csv")
    assert len(rows) == 4
    by_class = {row["class_name"]: row for row in rows}
    assert sum(row["compile_status"] == "compiled" for row in rows) == 3
    assert sum(row["runtime_status"] == "executed_with_unreleased_factor_base_stub" for row in rows) == 1
    assert by_class["VolatilityBreakoutSignal"]["component_credit"] == "conditional_literal_formula_only"
    assert "two-bar close lag" in by_class["VolatilityBreakoutSignal"]["material_defect_or_boundary"]
    assert by_class["ThreeSoldierSignal"]["runtime_status"] == "runtime_error_on_deterministic_fixture"
    assert by_class["ImprovedThreeSoldierSignal"]["runtime_status"] == "runtime_error_on_deterministic_fixture"
    assert by_class["ThreeSoldierSignalV3"]["compile_status"] == "compile_error"
    assert "SyntaxError" in by_class["ThreeSoldierSignalV3"]["compile_error"]
    assert all(row["native_agent_credit"] == "no" for row in rows)
    assert all(row["paper_result_credit"] == "no" for row in rows)


def test_every_displayed_result_object_remains_unreproduced() -> None:
    rows = csv_rows("displayed_result_conformance.csv")
    assert len(rows) == 21
    assert sum(row["display_object"] == "line_series" for row in rows) == 17
    matrices = [row for row in rows if row["display_object"] == "10x10_heatmap"]
    assert len(matrices) == 4
    assert sum(int(row["display_elements"]) for row in matrices) == 400
    assert {row["figure"] for row in rows} == {"Figure 3", "Figure 4", "Figure 5"}
    assert all(row["raw_values_released"] == "no" for row in rows)
    assert all(row["exact_values_recovered"] == "no" for row in rows)
    assert all(row["paper_result_credit"] == "no" for row in rows)


def test_prompts_claims_and_internal_conflicts_do_not_inflate_credit() -> None:
    prompts = csv_rows("prompt_inventory.csv")
    claims = csv_rows("claim_audit.csv")
    issues = csv_rows("paper_internal_consistency_audit.csv")
    assert len(prompts) == 9
    assert sum(row["recovery_status"] == "recovered" for row in prompts) == 1
    assert all(row["exact_replay_credit"] == "no" for row in prompts)
    assert len(claims) == 9
    assert all(row["exactly_reproduced"] == "no" for row in claims)
    assert all(row["paper_result_credit"] == "no" for row in claims)
    assert len(issues) == 12
    assert sum(row["severity"] == "blocking" for row in issues) == 6
    by_id = {row["issue_id"]: row for row in issues}
    assert "undefined r" in by_id["QA-INT-001"]["issue"]
    assert "syntactically invalid" in by_id["QA-INT-005"]["issue"]
    assert "sublinear KT" in by_id["QA-INT-010"]["issue"]


def test_method_audit_records_exact_source_gains_and_native_blockers() -> None:
    rows = csv_rows("method_specification_audit.csv")
    assert len(rows) >= 80
    by_dimension = {row["dimension"]: row for row in rows}
    assert by_dimension["authoritative TeX source"]["assessment"] == "specified"
    assert by_dimension["author-linked repository"]["severity"] == "blocking"
    assert by_dimension["idea_factor framework"]["assessment"] == "missing"
    assert by_dimension["termination variable"]["assessment"] == "conflict"
    assert by_dimension["Three Soldiers v3 code"]["assessment"] == "conflict"
    assert by_dimension["Figure 4 raw matrices"]["severity"] == "blocking"
    assert by_dimension["end-to-end sublinear-KT proof"]["assessment"] == "conflict"


def test_public_searches_and_same_name_repository_are_not_native_evidence() -> None:
    searches = csv_rows("source_search_inventory.csv")
    assert len(searches) == 8
    assert all(row["total_count"] == "0" for row in searches)
    assert all(row["incomplete_results"] == "false" for row in searches)
    assert all(row["author_linked_repository_found"] == "no" for row in searches)
    collisions = csv_rows("same_name_nonmatch.csv")
    assert len(collisions) == 1
    assert collisions[0]["repository"] == "Y-Research-SBU/QuantAgent"
    assert collisions[0]["author_overlap"] == "none"
    assert collisions[0]["native_credit_for_2402_03755"] == "no"


def test_manifest_and_native_execution_state_the_honest_boundary() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((OUTPUT / "native_execution.json").read_text(encoding="utf-8"))
    assert manifest["overall_fidelity"] == (
        "source_document_rebuilt_but_zero_of_17_line_series_and_zero_of_400_"
        "heatmap_cells_reproduced_no_native_agent_pipeline"
    )
    assert manifest["published_python_listings"] == 4
    assert manifest["published_python_listings_compiled"] == 3
    assert manifest["published_python_listings_executed_with_stub"] == 1
    assert manifest["mentor_passed_listing_compiles"] is False
    assert manifest["plotted_line_series_reproduced"] == 0
    assert manifest["heatmap_cells_reproduced"] == 0
    assert manifest["author_linked_code_found"] is False
    assert native["attempted"] is False
    assert native["paper_result_credit"] is False


def test_existing_local_candidates_keep_m0_and_conditional_boundaries() -> None:
    conformance = {row["candidate_id"]: row for row in csv_rows("local_mapping_conformance.csv")}
    assert conformance["quantagent_three_soldiers_trend"]["local_tier"] == "M0_narrative_translation"
    assert conformance["quantagent_volatility_breakout"]["local_tier"] == "M0_narrative_translation"
    assert conformance["quantagent_atr14_breakout_literal"]["local_tier"] == "C-conditional"
    assert all(row["paper_result_credit"] == "no" for row in conformance.values())

    with (
        ROOT / "paper_runs/submission_evidence/mapping_audit/mapping_audit.csv"
    ).open(newline="", encoding="utf-8") as stream:
        mapped = [row for row in csv.DictReader(stream) if row["source_name"] == "QuantAgent Holy Grail"]
    assert len(mapped) == 2
    assert {row["candidate_id"] for row in mapped} == {
        "quantagent_three_soldiers_trend",
        "quantagent_volatility_breakout",
    }
    assert {row["mapping_fidelity_tier"] for row in mapped} == {"M0_narrative_translation"}
    assert all(row["source_supports_exact_ingredients"] == "no" for row in mapped)
    assert all(row["source_supports_tested_weighting_rule"] == "no" for row in mapped)
