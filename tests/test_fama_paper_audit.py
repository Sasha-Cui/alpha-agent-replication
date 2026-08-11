"""Contract tests for the fail-closed FAMA paper/source audit."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_fama_paper.py"
SPEC = importlib.util.spec_from_file_location("audit_fama_paper", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)

PAPER = (
    ROOT
    / "literature_review/papers/"
    "10_can_large_language_models_mine_interpretable_financial_factors_more_effectively_a_neural_s.pdf"
)
OUTPUT = ROOT / "paper_runs/paper_replication_audits/fama"


def csv_rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_official_pdf_is_pinned_and_appendix_contradicts_claimed_factor_count() -> None:
    assert audit.sha256(PAPER) == audit.EXPECTED_PDF_SHA256
    text, pages = audit.pdf_text(PAPER)
    audit.validate_pdf(text, pages)
    identifiers = audit.initial_factor_ids(text)
    assert pages == 12
    assert len(identifiers) == len(set(identifiers)) == 71
    assert identifiers[:5] == ["002", "003", "004", "005", "006"]
    assert identifiers[-5:] == ["095", "096", "098", "099", "101"]


def test_all_table_results_are_enumerated_without_native_credit() -> None:
    rows = csv_rows("official_table_result_conformance.csv")
    assert len(rows) == 65
    assert {row["source_unit"] for row in rows} == {"Table 1", "Table 2", "Table 4"}
    assert all(row["paper_result_credit"] == "no" for row in rows)
    assert all(row["display_match"] == "no" for row in rows)
    assert all(row["reproduced_display_value"] == "" for row in rows)
    fama_sr = [
        row for row in rows
        if row["source_unit"] == "Table 2" and row["model"] == "FAMA" and row["metric"] == "SR"
    ]
    assert len(fama_sr) == 1
    assert fama_sr[0]["published_display_value"] == "667.2%"


def test_configuration_and_raster_result_denominators_are_separate() -> None:
    configs = csv_rows("numeric_configuration_audit.csv")
    figures = csv_rows("figure_result_inventory.csv")
    assert len(configs) == 8
    assert all(row["paper_result_credit"] == "no" for row in configs)
    assert sum(int(row["visible_result_markers"]) for row in figures) == 38
    result_figures = [row for row in figures if int(row["visible_result_markers"])]
    assert {row["audit_status"] for row in result_figures} == {
        "raster_only_no_raw_plot_values"
    }


def test_equation_algorithm_split_and_unit_conflicts_are_fail_closed() -> None:
    rows = csv_rows("paper_internal_consistency_audit.csv")
    by_id = {row["issue_id"]: row for row in rows}
    assert len(rows) == 12
    assert sum(row["severity"] == "blocking" for row in rows) == 8
    for identifier in (
        "FAMA-INT-001",
        "FAMA-INT-003",
        "FAMA-INT-004",
        "FAMA-INT-006",
        "FAMA-INT-007",
        "FAMA-INT-008",
    ):
        assert by_id[identifier]["severity"] == "blocking"
        assert by_id[identifier]["replication_effect"] == (
            "prevents_exact_native_reconstruction"
        )
    assert by_id["FAMA-INT-002"]["audit_recomputation"] == "0.106"


def test_method_audit_records_missing_native_pipeline_inputs() -> None:
    rows = csv_rows("method_specification_audit.csv")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["assessment"]] = counts.get(row["assessment"], 0) + 1
    assert len(rows) == 69
    assert counts == {"specified": 24, "missing": 29, "conflict": 7, "partial": 9}
    by_dimension = {row["dimension"]: row for row in rows}
    assert by_dimension["author-linked implementation"]["severity"] == "blocking"
    assert by_dimension["final mined factor expressions"]["assessment"] == "missing"
    assert by_dimension["factor correlation equation"]["assessment"] == "conflict"
    assert by_dimension["local proxy relation"]["assessment"] == "partial"


def test_prompt_is_recovered_but_runtime_definition_is_not() -> None:
    prompt = (OUTPUT / "paper_prompt_template.txt").read_text(encoding="utf-8")
    assert prompt == audit.PROMPT_TEMPLATE
    assert "{function_definition}" in prompt
    assert 'generate_factor_num: 1' in prompt
    assert "rank(correlation(open, volume, 10) / rank(open))" in prompt
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["runtime_prompt_templates_recovered"] == 1
    assert manifest["runtime_prompt_function_definitions_recovered"] == 0


def test_manifest_and_native_execution_state_zero_reproduction_honestly() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((OUTPUT / "native_execution.json").read_text(encoding="utf-8"))
    assert manifest["overall_fidelity"] == (
        "zero_of_65_table_results_and_zero_of_38_figure_markers_reproduced_no_native_pipeline"
    )
    assert manifest["published_table_result_cells_reproduced"] == 0
    assert manifest["visible_figure_result_markers_reproduced"] == 0
    assert manifest["author_linked_code_found"] is False
    assert native["attempted"] is False
    assert native["paper_result_credit"] is False
    assert native["local_proxy_status"] == "M1_example_or_motif_partial_support_only"


def test_source_search_and_existing_proxy_never_become_native_evidence() -> None:
    searches = csv_rows("source_search_inventory.csv")
    assert len(searches) == 3
    assert all(row["total_count"] == "0" for row in searches)
    assert all(row["author_linked_repository_found"] == "no" for row in searches)
    provenance = json.loads((OUTPUT / "source_provenance.json").read_text(encoding="utf-8"))
    assert provenance["official_pdf_sha256"] == audit.EXPECTED_PDF_SHA256
    assert provenance["official_artifact_links"] == [audit.PDF_URL]
    assert provenance["author_linked_code_or_supplement_found"] is False

    with (
        ROOT / "paper_runs/submission_evidence/mapping_audit/mapping_audit.csv"
    ).open(newline="", encoding="utf-8") as stream:
        mapping = next(row for row in csv.DictReader(stream) if row["candidate_id"] == "fama_value_momentum_interpretable")
    assert mapping["mapping_fidelity_tier"] == "M1_example_or_motif_partial_support"
    assert mapping["exact_original_claim_matches_monthly_us_ff_alpha"] == (
        "no explicit match identified"
    )
    assert "not the native system" in mapping["negative_evidence_boundary"]
