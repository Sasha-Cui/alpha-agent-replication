"""Contracts for the fail-closed, multi-version MACI paper/source audit."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_maci_paper.py"
SPEC = importlib.util.spec_from_file_location("audit_maci_paper", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)

OUTPUT = ROOT / "paper_runs/paper_replication_audits/maci"


def csv_rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_manifest_keeps_both_experiments_and_the_zero_result_boundary() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["full_end_to_end_pipeline_reproduced"] is False
    assert manifest["v1_v2_published_table_units"] == 321
    assert manifest["v1_v2_direct_table_results"] == 318
    assert manifest["v1_v2_unique_direct_measurements"] == 315
    assert manifest["v1_v2_table_units_faithfully_regenerated"] == 0
    assert manifest["v3_published_table_units"] == 442
    assert manifest["v3_direct_table_results"] == 430
    assert manifest["v3_unique_direct_measurements"] == 426
    assert manifest["v3_table_units_faithfully_regenerated"] == 0
    assert manifest["v1_published_plotted_result_units_author_output_verified"] == 21
    assert manifest["v1_published_plotted_result_units_regenerated"] == 0
    assert manifest["v3_plotted_bars_lines_points_regenerated"] == 0
    assert manifest["v3_source_files_recovered"] == 0
    assert manifest["llm_calls_made"] == 0


def test_every_published_table_unit_is_ledgered_without_inflated_credit() -> None:
    v1 = csv_rows("published_result_ledger_v1_v2.csv")
    v3 = csv_rows("published_result_ledger_v3.csv")
    assert len(v1) == 321
    assert len(v3) == 442
    assert Counter(row["table"] for row in v1) == {
        "classification": 36,
        "market_rise_fall": 9,
        "portfolio": 36,
        "llm_asset_pricing": 162,
        "traditional_asset_pricing": 54,
        "ablation": 24,
    }
    assert Counter(row["table"] for row in v3) == {
        "performance": 414,
        "ablation": 28,
    }
    assert sum(row["cell_kind"] == "direct_result" for row in v1) == 318
    assert sum(row["cell_kind"] == "direct_result" for row in v3) == 430
    assert sum(row["native_maci_output"] == "True" for row in v1) == 102
    assert sum(row["native_maci_output"] == "True" for row in v3) == 244
    assert all(row["native_regenerated_value"] == "" for row in v1 + v3)
    assert all(row["paper_result_credit"] == "False" for row in v1 + v3)


def test_author_figure_lineage_is_verified_but_not_called_regeneration() -> None:
    rows = csv_rows("figure_lineage_v1.csv")
    assert len(rows) == 17
    compiled = [row for row in rows if row["compiled_into_v1_pdf"] == "True"]
    assert len(compiled) == 16
    assert sum(int(row["published_plotted_result_units"]) for row in compiled) == 21
    assert Counter(row["author_output_correspondence"] for row in rows) == {
        "byte_identical": 12,
        "render_pixel_identical_metadata_only_difference": 1,
        "all_author_drawing_geometry_preserved_submitted_label_adds_factor": 1,
        "all_five_vector_paths_same_y_and_point_counts_after_horizontal_resize_legend_changed": 3,
    }
    assert all(row["native_result_regenerated"] == "False" for row in rows)
    assert all(row["paper_result_credit"] == "False" for row in rows)


def test_raw_source_execution_fails_closed_and_overlay_remains_labelled() -> None:
    native = json.loads((OUTPUT / "native_execution.json").read_text(encoding="utf-8"))
    assert native["declared_python_requirement"] == ">=3.9.15"
    assert native["python39_compile_passed"] is False
    assert len(native["python39_syntax_errors"]) == 2
    assert native["python311_compile_passed"] is True
    assert native["raw_python311_import_passed"] is False
    assert native["raw_python311_import_exception"] == (
        "ModuleNotFoundError: No module named 'environ.constants'"
    )
    assert native["reconstruction_overlay"]["is_native_unmodified_source"] is False
    assert native["reconstruction_overlay"]["later_constants_still_missing_symbols"] == [
        "AP_LABEL", "LABEL",
    ]
    assert native["paper_runner_executed"] is False
    assert native["paper_runner_first_blocker_after_overlay"] == (
        "FileNotFoundError: data/blockchain/n-unique-addresses.json"
    )
    assert native["deterministic_component_harness_passed"] is True
    assert native["component_execution_is_paper_result_replication"] is False


def test_pinned_manuscripts_rebuild_deterministically_and_pass_visual_qa() -> None:
    rows = json.loads((OUTPUT / "manuscript_provenance.json").read_text(encoding="utf-8"))
    assert [row["version"] for row in rows] == ["v1", "v2", "v3"]
    assert [row["official_pages"] for row in rows] == [14, 14, 10]
    assert [row["rebuild_pages"] for row in rows] == [14, 14, 10]
    assert all(row["rebuild_runs_byte_identical"] for row in rows)
    assert all(row["official_rebuild_text"]["multiset_jaccard"] > 0.997 for row in rows)
    assert all(row["final_latex_log"]["undefined_citations"] == 0 for row in rows)
    assert all(row["final_latex_log"]["undefined_references"] == 0 for row in rows)
    assert all(row["final_latex_log"]["latex_errors"] == 0 for row in rows)
    assert all(
        row["visual_qa"]["status"] == "passed_full_document_contact_sheet_review"
        for row in rows
    )
    assert all(row["paper_result_credit"] is False for row in rows)


def test_method_prompt_and_internal_consistency_gaps_remain_explicit() -> None:
    methods = {
        (row["paper_version"], row["dimension"]): row
        for row in csv_rows("method_specification_audit.csv")
    }
    assert len(methods) == 33
    assert methods[("v1/v2", "raw_inputs")]["status"] == "missing"
    assert methods[("v1/v2", "fine_tuned_model_ids")]["status"] == "incomplete_unverified"
    assert methods[("v3", "system_architecture")]["status"] == "paper_only"
    assert methods[("v3", "risk_free_rate")]["status"] == "hard_result_method_conflict"

    prompts = csv_rows("prompt_inventory.csv")
    assert Counter(row["paper_version"] for row in prompts) == {"v3": 18, "v1/v2": 9}
    assert sum(
        row["paper_version"] == "v3" and row["compiled_into_appendix"] == "True"
        for row in prompts
    ) == 3
    assert all(row["actual_request_released"] == "False" for row in prompts)
    assert all(row["actual_response_released"] == "False" for row in prompts)

    issues = {row["claim_id"]: row for row in csv_rows("internal_consistency_audit.csv")}
    assert len(issues) == 14
    assert issues["python_requirement"]["status"] == "hard_environment_conflict"
    assert "20/23 bear rows" in issues["bear_regime_mdd"]["evidence"]
    assert issues["risk_free_rate"]["status"] == "hard_method_result_conflict"
    assert issues["traceability"]["status"] == "claim_unverifiable"


def test_primary_sources_and_current_author_tree_do_not_fill_v3_gaps() -> None:
    sources = csv_rows("external_primary_source_audit.csv")
    assert len(sources) == 7
    assert {row["subject"] for row in sources} >= {
        "GPT-5 release and snapshot",
        "Claude Sonnet 4.5 release",
        "Claude Sonnet 4.5 training boundary",
        "Fama-French risk-free factor",
    }
    validation = json.loads(
        (OUTPUT / "primary_source_validation.json").read_text(encoding="utf-8")
    )
    assert validation["fama_french_archive_sha256"] == audit.EXPECTED[
        "fama_french_archive"
    ]
    assert min(validation["fama_french_2025_monthly_rf_pct"].values()) == 0.30
    assert max(validation["fama_french_2025_monthly_rf_pct"].values()) == 0.38

    inventory = json.loads(
        (OUTPUT / "author_source_inventory.json").read_text(encoding="utf-8")
    )
    assert inventory["pre_submission_constants_present"] is False
    assert inventory["current_constants_present"] is True
    assert inventory["pre_submission_data_files"] == 0
    assert inventory["pre_submission_processed_data_files"] == 0
    assert all(value == 0 for value in inventory["v3_architecture_capability_term_file_hits"].values())
    assert inventory["v3_implementation_recovered"] is False


def test_manifest_hashes_cover_every_committed_audit_output() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    actual_names = {
        path.name for path in OUTPUT.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(manifest["output_sha256"]) == actual_names
    assert {
        name: sha256(OUTPUT / name)
        for name in sorted(actual_names)
    } == manifest["output_sha256"]

    readme = " ".join((OUTPUT / "README.md").read_text(encoding="utf-8").split())
    assert "not reproduced end to end" in readme
    assert "Zero of 321" in readme
    assert "Zero of 442" in readme
    assert "do not recover any missing experimental data" in readme
