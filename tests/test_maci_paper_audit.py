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
    assert manifest["v1_v2_public_forks_accessible"] == 2
    assert manifest["v1_v2_public_fork_branch_refs_audited"] == 2
    assert manifest["v1_v2_public_fork_unique_heads_audited"] == 2
    assert manifest["v1_v2_public_fork_divergent_heads_audited"] == 0
    assert manifest["v1_v2_public_fork_unique_commits_beyond_official_history"] == 0
    assert manifest["v1_v2_public_fork_native_result_artifacts_found"] == 0
    assert manifest["v3_public_history_commits_audited"] == 20
    assert manifest["v1_v2_deleted_fine_tuning_message_records_recovered"] == 962
    assert manifest["v1_v2_fine_tuning_record_payloads_recovered"] == 962
    assert manifest["v1_v2_fine_tuning_image_references"] == 931
    assert manifest["v1_v2_fine_tuning_unique_image_payloads_recovered"] == 930
    assert manifest["v1_v2_fine_tuning_image_payload_bytes"] == 53_574_400
    assert manifest["v1_v2_fine_tuning_images_identical_at_current_head"] == 930
    assert (
        manifest["v1_v2_fine_tuning_image_manifest_sha256"]
        == audit.TRAINING_IMAGE_MANIFEST_SHA256
    )
    assert manifest["v1_v2_historical_fine_tuning_payload_complete"] is True
    assert manifest["v1_v2_historical_fine_tuning_files_added_after_paper_v2"] is True
    assert manifest["v1_v2_actual_fine_tuning_upload_job_checkpoint_recovered"] is False
    assert manifest["v1_v2_fine_tuning_payload_paper_result_credit"] is False
    assert manifest["v1_v2_reconstructed_single_0510_records"] == 961
    assert manifest["v1_v2_reconstructed_single_0510_bytes"] == 2_455_569
    assert (
        manifest["v1_v2_reconstructed_single_0510_sha256"]
        == audit.RECONSTRUCTED_SINGLE_0510_SHA256
    )
    assert manifest["v1_v2_reconstructed_single_0510_image_examples"] == 930
    assert manifest["v1_v2_reconstructed_single_0510_text_only_examples"] == 31
    assert manifest["v1_v2_openai_vision_fine_tuning_static_contract_passed"] is True
    assert manifest["v1_v2_native_fine_tuning_contract_network_attempts"] == 0
    assert manifest["v1_v2_native_fine_tuning_contract_file_create_calls"] == 1
    assert manifest["v1_v2_native_fine_tuning_contract_job_create_calls"] == 1
    assert manifest["v1_v2_native_fine_tuning_remote_job_created"] is False
    assert manifest["v1_v2_native_fine_tuning_procedure_paper_result_credit"] is False
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
    fine_tuning = native["fine_tuning_procedure_reconstruction"]
    assert fine_tuning["source_method"] == "FTAgent.fine_tuning"
    assert fine_tuning["network_attempts"] == []
    assert fine_tuning["openai_client_initializations"] == 3
    assert fine_tuning["file_create_calls"] == [
        {
            "purpose": "fine-tune",
            "bytes": 2_455_569,
            "sha256": audit.RECONSTRUCTED_SINGLE_0510_SHA256,
        }
    ]
    assert fine_tuning["fine_tuning_job_create_calls"] == [
        {"training_file": "file-audit", "model": "gpt-4o-2024-08-06"}
    ]
    assert fine_tuning["fine_tuning_job_retrieve_calls"] == [
        {"job_id": "job-audit"}
    ]
    assert fine_tuning["remote_file_uploaded"] is False
    assert fine_tuning["remote_fine_tuning_job_created"] is False
    assert fine_tuning["paper_result_credit"] is False


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
    assert len(methods) == 36
    assert methods[("v1/v2", "raw_inputs")]["status"] == (
        "market_inputs_missing_training_images_recovered"
    )
    assert methods[("v1/v2", "processed_inputs")]["status"] == (
        "market_inputs_missing_historical_training_payload_complete"
    )
    assert methods[("v1/v2", "prompt_templates")]["status"] == (
        "templates_plus_complete_historical_training_payload"
    )
    assert methods[("v1/v2", "fine_tuning_procedure")]["status"] == (
        "native_contract_reconstructed_remote_job_missing"
    )
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
    assert len(sources) == 8
    assert {row["subject"] for row in sources} >= {
        "GPT-4o vision fine-tuning contract",
        "GPT-5 release and snapshot",
        "Claude Sonnet 4.5 release",
        "Claude Sonnet 4.5 training boundary",
        "Fama-French risk-free factor",
    }
    validation = json.loads((OUTPUT / "primary_source_validation.json").read_text(encoding="utf-8"))
    assert validation["fama_french_archive_sha256"] == audit.EXPECTED["fama_french_archive"]
    assert min(validation["fama_french_2025_monthly_rf_pct"].values()) == 0.30
    assert max(validation["fama_french_2025_monthly_rf_pct"].values()) == 0.38
    assert validation["provider_source_count"] == 7

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
    lineage = csv_rows("v1_v2_finetuning_record_lineage.csv")
    payload = json.loads(
        (OUTPUT / "v1_v2_finetuning_payload_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(lineage) == 962
    assert Counter(row["dataset_path"] for row in lineage) == {
        "test/single_cs_0510.jsonl": 930,
        "test/single_mkt_0510.jsonl": 31,
        "test/test.jsonl": 1,
    }
    assert Counter(row["assistant_label"] for row in lineage) == {
        "Fall": 496,
        "Rise": 466,
    }
    image_rows = [row for row in lineage if row["image_reference_present"] == "True"]
    assert len(image_rows) == 931
    assert len({row["image_url"] for row in image_rows}) == 930
    assert len({row["image_path"] for row in image_rows}) == 930
    assert len({row["image_dataset_blob_oid"] for row in image_rows}) == 930
    assert {row["image_width"] for row in image_rows} == {"1000"}
    assert {row["image_height"] for row in image_rows} == {"800"}
    assert {row["image_mode"] for row in image_rows} == {"RGBA"}
    assert {row["image_format"] for row in image_rows} == {"PNG"}
    assert all(
        row["image_dataset_blob_oid"] == row["image_current_blob_oid"]
        for row in image_rows
    )
    assert all(row["complete_record_payload_recovered"] == "True" for row in lineage)
    assert all(row["paper_run_use_verified"] == "False" for row in lineage)
    assert all(row["paper_result_credit"] == "False" for row in lineage)
    assert payload["fine_tuning_format_records"] == 962
    assert payload["image_references"] == 931
    assert payload["unique_image_paths"] == 930
    assert payload["unique_image_git_blobs"] == 930
    assert payload["image_payloads_recovered"] == 930
    assert payload["image_payloads_identical_at_current_head"] == 930
    assert payload["image_payload_bytes"] == 53_574_400
    assert payload["image_dimensions"] == [1000, 800]
    assert payload["image_manifest_sha256"] == audit.TRAINING_IMAGE_MANIFEST_SHA256
    assert payload["all_referenced_image_payloads_recovered"] is True
    assert payload["dataset_added_after_paper_v2"] is True
    assert payload["actual_uploaded_file_identity_recovered"] is False
    assert payload["fine_tuning_job_and_selected_checkpoint_recovered"] is False
    assert payload["paper_run_use_verified"] is False
    assert payload["paper_result_credit"] is False

    procedure = json.loads(
        (OUTPUT / "v1_v2_finetuning_procedure.json").read_text(encoding="utf-8")
    )
    procedure_rows = csv_rows("v1_v2_finetuning_procedure_conformance.csv")
    reconstructed = OUTPUT / "v1_v2_reconstructed_single_0510.jsonl"
    assert reconstructed.stat().st_size == 2_455_569
    assert sha256(reconstructed) == audit.RECONSTRUCTED_SINGLE_0510_SHA256
    with reconstructed.open(encoding="utf-8") as stream:
        reconstructed_rows = [json.loads(line) for line in stream]
    assert len(reconstructed_rows) == 961
    assert procedure["source_contract"]["base_model"] == "gpt-4o-2024-08-06"
    assert procedure["source_contract"]["active_fine_tuning_calls"] == 1
    assert procedure["source_contract"]["component_dataset_paths"] == [
        "test/single_cs_0510.jsonl",
        "test/single_mkt_0510.jsonl",
    ]
    assert procedure["source_contract"]["checkpoint_names"] == [
        "cs_vision_0510.pkl",
        "mkt_news_0510.pkl",
    ]
    assert procedure["source_contract"][
        "same_agent_object_saved_to_both_checkpoint_names"
    ] is True
    assert procedure["source_contract"]["multi_agent_fine_tuning_blocks_active"] is False
    schema = procedure["reconstructed_dataset"]
    assert schema["records"] == 961
    assert schema["image_examples"] == 930
    assert schema["text_only_examples"] == 31
    assert schema["maximum_images_per_example"] == 1
    assert schema["maximum_image_bytes"] == 71_085
    assert schema["image_formats"] == ["PNG"]
    assert schema["image_modes"] == ["RGBA"]
    assert schema["image_detail_values"] == ["high"]
    assert schema["assistant_image_outputs"] == 0
    assert schema["official_openai_static_vision_fine_tuning_contract_passed"] is True
    assert schema["official_openai_documentation"] == audit.OPENAI_VISION_FINE_TUNING_DOC
    assert procedure["actual_uploaded_file_identity_recovered"] is False
    assert procedure["actual_job_id_recovered"] is False
    assert procedure["actual_selected_checkpoint_recovered"] is False
    assert procedure["paper_run_use_verified"] is False
    assert procedure["paper_result_credit"] is False
    assert len(procedure_rows) == 5
    assert {row["paper_result_credit"] for row in procedure_rows} == {"False"}
    assert history["v3_missing_module_paths_present_in_any_commit"] == {
        "environ/data/coingecko.py": False,
        "environ/data/cointelegraph.py": False,
        "environ/data/rag_store.py": False,
    }
    assert history["result_regeneration_credit"] is False


def test_all_public_v1_v2_forks_remain_inside_the_audited_official_history() -> None:
    rows = csv_rows("public_fork_branch_ref_snapshot.csv")
    assert len(rows) == 2
    assert {
        (row["repository"], row["relation_to_official_head"], row["commits_behind_official"])
        for row in rows
    } == {
        ("gelove/multi-agent", "official_head_exact", "0"),
        ("jemxgw/multi-agent", "official_history_ancestor", "3"),
    }
    assert all(row["unique_commits_beyond_official_history"] == "0" for row in rows)
    assert all(row["unique_blobs_beyond_official_history"] == "0" for row in rows)
    assert all(row["native_result_artifact_found"] == "False" for row in rows)
    assert all(row["paper_result_credit"] == "False" for row in rows)

    census = json.loads((OUTPUT / "public_fork_census.json").read_text(encoding="utf-8"))
    assert census["census_date"] == audit.PUBLIC_FORK_CENSUS_DATE
    assert census["official_history_commits"] == 164
    assert census["github_rest_reported_forks"] == 2
    assert census["accessible_public_forks"] == 2
    assert census["accessible_branch_refs"] == 2
    assert census["unique_heads"] == 2
    assert census["official_head_exact_unique_heads"] == 1
    assert census["official_history_ancestor_unique_heads"] == 1
    assert census["divergent_unique_heads"] == 0
    assert census["native_result_artifacts_found"] == 0
    assert census["paper_result_credit"] is False


def test_manifest_hashes_cover_every_committed_audit_output() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    actual_names = {path.name for path in OUTPUT.iterdir() if path.is_file() and path.name != "manifest.json"}
    assert set(manifest["output_sha256"]) == actual_names
    assert {name: sha256(OUTPUT / name) for name in sorted(actual_names)} == manifest["output_sha256"]

    readme = " ".join((OUTPUT / "README.md").read_text(encoding="utf-8").split())
    assert "not reproduced end to end" in readme
    assert "Zero of 321" in readme
    assert "Zero of 442" in readme
    assert "all referenced images are therefore recoverable" in readme
    assert "does not prove they were the uploaded paper training set" in readme
    assert "Replaying its commented construction deterministically concatenates" in readme
    assert "one `purpose=\"fine-tune\"` file call" in readme
    assert "same agent object under both" in readme
    assert "reconstructs the local procedure, not the paper's remote job" in readme
    assert "do not fill any missing experimental data" in readme
