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
    assert manifest["v3_table_units_author_output_verified"] == 394
    assert manifest["v3_table_units_author_output_different"] == 48
    assert manifest["v1_published_plotted_result_units_author_output_verified"] == 21
    assert manifest["v1_published_plotted_result_units_regenerated"] == 0
    assert manifest["v3_plotted_bars_lines_points_regenerated"] == 0
    assert manifest["v3_plotted_bars_lines_points_author_output_verified"] == 136
    assert manifest["v3_source_files_recovered"] == 42
    assert manifest["v3_python_source_files_recovered"] == 24
    assert manifest["v1_v2_public_history_commits_audited"] == 164
    assert manifest["v3_public_history_commits_audited"] == 20
    assert manifest["v1_v2_deleted_fine_tuning_message_records_recovered"] == 962
    assert manifest["v3_non_rag_architecture_component_paths_passed"] == 9
    assert manifest["v3_non_rag_architecture_component_paths_denominator"] == 9
    assert manifest["v3_rag_architecture_paths_blocked_by_missing_source_module"] == 3
    assert manifest["v3_runner_dry_run_with_labelled_data_overlay_passed"] is True
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
    assert sum(row["author_output_verified"] == "True" for row in v3) == 394
    assert all(row["author_output_value"] != "" for row in v3)
    mismatches = [row for row in v3 if row["author_output_verified"] == "False"]
    assert Counter(row["strategy_or_variant"] for row in mismatches) == {
        "LSTM": 17,
        "Informer": 18,
        "Autoformer": 13,
    }


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


def test_v3_author_figures_preserve_136_units_but_zero_regeneration() -> None:
    rows = csv_rows("figure_lineage_v3.csv")
    assert len(rows) == 5
    assert sum(int(row["published_plotted_result_units"]) for row in rows) == 142
    assert sum(int(row["author_output_verified_units"]) for row in rows) == 136
    assert Counter(row["author_output_correspondence"] for row in rows) == {
        "byte_identical": 3,
        "20_of_23_paper_paths_share_author_vector_geometry_three_final_baselines_changed": 1,
        "20_of_23_paper_points_have_matching_author_table_coordinates_three_final_baselines_changed": 1,
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
    assert native["raw_python311_import_exception"] == ("ModuleNotFoundError: No module named 'environ.constants'")
    assert native["reconstruction_overlay"]["is_native_unmodified_source"] is False
    assert native["reconstruction_overlay"]["later_constants_still_missing_symbols"] == [
        "AP_LABEL",
        "LABEL",
    ]
    assert native["paper_runner_executed"] is False
    assert native["paper_runner_first_blocker_after_overlay"] == (
        "FileNotFoundError: data/blockchain/n-unique-addresses.json"
    )
    assert native["deterministic_component_harness_passed"] is True
    assert native["component_execution_is_paper_result_replication"] is False


def test_v3_source_components_execute_but_raw_runner_and_rag_fail_closed() -> None:
    native = json.loads((OUTPUT / "native_execution_v3.json").read_text(encoding="utf-8"))
    assert native["head"] == audit.EXPECTED["author_v3_commit"]
    assert native["compile"] == {
        "python_file_count": 24,
        "all_passed": True,
        "failures": [],
    }
    assert native["raw_runner_import"]["passed"] is False
    assert native["raw_runner_import"]["stderr_last_line"] == ("ModuleNotFoundError: No module named 'environ.data'")
    components = native["architecture_component_execution"]
    assert components["unmodified_non_rag_passed"] == 9
    assert components["unmodified_non_rag_denominator"] == 9
    assert components["unmodified_rag_failures"] == 3
    assert components["overlay_rag_passed"] == 3
    assert native["runner_dry_run_with_missing_data_overlay"]["passed"] is True
    aliases = native["single_agent_capability_contract"]
    assert aliases["runner_capability_to_agent_capability"] == {
        "zero_shot": "zero_shot",
        "chain_of_thought": "chain_of_thought",
        "rag": "zero_shot",
        "skill": "zero_shot",
    }
    assert aliases["rag_is_distinct_in_single_agent_wrapper"] is False
    assert aliases["skill_is_distinct_in_single_agent_wrapper"] is False
    assert native["llm_calls_made"] == 0
    assert native["paper_results_regenerated"] == 0
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
    assert all(row["visual_qa"]["status"] == "passed_full_document_contact_sheet_review" for row in rows)
    assert all(row["paper_result_credit"] is False for row in rows)


def test_method_prompt_and_internal_consistency_gaps_remain_explicit() -> None:
    methods = {(row["paper_version"], row["dimension"]): row for row in csv_rows("method_specification_audit.csv")}
    assert len(methods) == 35
    assert methods[("v1/v2", "raw_inputs")]["status"] == "missing"
    assert methods[("v1/v2", "fine_tuned_model_ids")]["status"] == "incomplete_unverified"
    assert methods[("v3", "system_architecture")]["status"] == ("source_present_component_verified")
    assert methods[("v3", "react_loop")]["status"] == "paper_source_conflict"
    assert methods[("v3", "single_agent_capabilities")]["status"] == ("hard_source_result_conflict")
    assert methods[("v3", "risk_free_rate")]["status"] == "hard_result_method_conflict"

    prompts = csv_rows("prompt_inventory.csv")
    assert Counter(row["paper_version"] for row in prompts) == {"v3": 18, "v1/v2": 9}
    assert sum(row["paper_version"] == "v3" and row["compiled_into_appendix"] == "True" for row in prompts) == 3
    assert all(row["actual_request_released"] == "False" for row in prompts)
    assert all(row["actual_response_released"] == "False" for row in prompts)

    issues = {row["claim_id"]: row for row in csv_rows("internal_consistency_audit.csv")}
    assert len(issues) == 14
    assert issues["python_requirement"]["status"] == "hard_environment_conflict"
    assert "20/23 bear rows" in issues["bear_regime_mdd"]["evidence"]
    assert issues["risk_free_rate"]["status"] == "hard_method_result_conflict"
    assert issues["traceability"]["status"] == "claim_unverifiable"
    assert issues["code_lineage"]["status"] == "v3_source_recovered_incomplete"


def test_primary_sources_and_both_author_repositories_preserve_v3_boundaries() -> None:
    sources = csv_rows("external_primary_source_audit.csv")
    assert len(sources) == 7
    assert {row["subject"] for row in sources} >= {
        "GPT-5 release and snapshot",
        "Claude Sonnet 4.5 release",
        "Claude Sonnet 4.5 training boundary",
        "Fama-French risk-free factor",
    }
    validation = json.loads((OUTPUT / "primary_source_validation.json").read_text(encoding="utf-8"))
    assert validation["fama_french_archive_sha256"] == audit.EXPECTED["fama_french_archive"]
    assert min(validation["fama_french_2025_monthly_rf_pct"].values()) == 0.30
    assert max(validation["fama_french_2025_monthly_rf_pct"].values()) == 0.38

    inventory = json.loads((OUTPUT / "author_source_inventory.json").read_text(encoding="utf-8"))
    assert inventory["pre_submission_constants_present"] is False
    assert inventory["current_constants_present"] is True
    assert inventory["pre_submission_data_files"] == 0
    assert inventory["pre_submission_processed_data_files"] == 0
    assert all(value == 0 for value in inventory["v1_v2_repository_v3_architecture_capability_term_file_hits"].values())
    assert inventory["v1_v2_repository_contains_v3_implementation"] is False
    assert inventory["v3_author_commit"] == audit.EXPECTED["author_v3_commit"]
    assert inventory["v3_tracked_files"] == 42
    assert inventory["v3_python_files"] == 24
    assert inventory["v3_data_package_present"] is False
    assert inventory["v3_implementation_recovered"] is True

    source_rows = csv_rows("v3_source_inventory.csv")
    assert len(source_rows) == 42
    assert sum(row["path"].endswith(".py") for row in source_rows) == 24
    assert all(row["paper_result_credit"] == "False" for row in source_rows)


def test_complete_public_histories_recover_training_records_not_results() -> None:
    history = json.loads((OUTPUT / "repository_history.json").read_text(encoding="utf-8"))
    v1 = history["v1_v2_repository_history"]
    v3 = history["v3_repository_history"]
    assert (v1["commit_count"], v1["reachable_object_count"]) == (164, 7997)
    assert (v3["commit_count"], v3["reachable_object_count"]) == (20, 209)
    assert v1["shallow"] is False and v3["shallow"] is False
    training = history["v1_v2_deleted_training_records"]
    assert training["total_records"] == 962
    assert [row["records"] for row in training["files"]] == [930, 31, 1]
    assert training["files"][0]["image_week_min"] == "2023-W22"
    assert training["files"][0]["image_week_max"] == "2023-W52"
    assert all(row["paper_result_credit"] is False for row in training["files"])
    assert history["v3_missing_module_paths_present_in_any_commit"] == {
        "environ/data/coingecko.py": False,
        "environ/data/cointelegraph.py": False,
        "environ/data/rag_store.py": False,
    }
    assert history["result_regeneration_credit"] is False


def test_manifest_hashes_cover_every_committed_audit_output() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    actual_names = {path.name for path in OUTPUT.iterdir() if path.is_file() and path.name != "manifest.json"}
    assert set(manifest["output_sha256"]) == actual_names
    assert {name: sha256(OUTPUT / name) for name in sorted(actual_names)} == manifest["output_sha256"]

    readme = " ".join((OUTPUT / "README.md").read_text(encoding="utf-8").split())
    assert "not reproduced end to end" in readme
    assert "Zero of 321" in readme
    assert "Zero of 442" in readme
    assert "do not fill any missing experimental data" in readme
