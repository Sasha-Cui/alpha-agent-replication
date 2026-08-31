from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_alphaagent_paper.py"
SPEC = importlib.util.spec_from_file_location("alphaagent_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_targets_cover_all_numeric_table_cells() -> None:
    rows = audit.paper_numeric_rows()
    assert len(rows) == 106
    assert Counter(row["paper_table"] for row in rows) == {1: 6, 2: 100}
    assert Counter(row["cell_role"] for row in rows) == {
        "result": 100,
        "configuration": 6,
    }
    assert (
        len(
            {
                (
                    row["paper_table"],
                    row["entity"],
                    row["market"],
                    row["period"],
                    row["metric"],
                )
                for row in rows
            }
        )
        == 106
    )
    v1 = {
        (row["paper_table"], row["entity"], row["market"], row["metric"]): row for row in audit.paper_numeric_rows("v1")
    }
    v2 = {(row["paper_table"], row["entity"], row["market"], row["metric"]): row for row in rows}
    assert set(v1) == set(v2)
    assert sum(v1[key]["paper_value"] != v2[key]["paper_value"] for key in v1) == 5
    assert sum(v1[key]["period"] != v2[key]["period"] for key in v1) == 2


def test_non_table_claims_preserve_result_boundary() -> None:
    rows = audit.published_non_table_claims()
    assert len(rows) == 26
    assert Counter(row["claim_role"] for row in rows) == {
        "result": 18,
        "configuration": 8,
    }
    assert {row["paper_result_credit"] for row in rows} == {False}


def test_committed_audit_is_fail_closed() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/alphaagent"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    table = read_csv(output / "tables_1_2_conformance.csv")
    claims = read_csv(output / "published_non_table_claims.csv")
    mechanisms = read_csv(output / "source_mechanism_conformance.csv")
    current_mechanisms = read_csv(output / "current_rewrite_mechanism_conformance.csv")
    history = read_csv(output / "official_history_timeline.csv")
    paper_versions = read_csv(output / "official_paper_version_inventory.csv")
    paper_lineage = read_csv(output / "official_paper_numeric_lineage.csv")
    paper_figures = read_csv(output / "official_paper_figure_asset_inventory.csv")
    history_paths = read_csv(output / "public_source_history_path_inventory.csv")
    history_summary = json.loads((output / "public_source_history.json").read_text(encoding="utf-8"))
    fork_heads = read_csv(output / "fork_default_head_census.csv")
    fork_bundle = json.loads((output / "fork_data_bundle_audit.json").read_text(encoding="utf-8"))
    run_inputs = json.loads((output / "paper_era_run_input_audit.json").read_text(encoding="utf-8"))
    fork_wang_registry = read_csv(output / "fork_wang_postpaper_registry_metrics.csv")
    gaps = read_csv(output / "paper_specification_gaps.csv")
    inventory = read_csv(output / "released_source_inventory.csv")
    paper_era_inventory = read_csv(output / "paper_era_source_inventory.csv")
    paper_era_factors = read_csv(output / "paper_era_factor_artifacts.csv")
    paper_era_runs = read_csv(output / "paper_era_mlflow_run_records.csv")
    native_recorders = read_csv(
        output / "paper_era_native_qlib_recorder_execution.csv"
    )
    paper_era_aggregations = read_csv(output / "paper_era_mlflow_aggregation_forensics.csv")
    registry = read_csv(output / "post_paper_registry_metrics.csv")
    data_release = read_csv(output / "data_release_provenance.csv")
    factors = read_csv(output / "synthetic_base_factor_component.csv")
    component = json.loads((output / "native_component.json").read_text(encoding="utf-8"))
    rewrite_freeze = (output / "current_rewrite_environment_freeze.txt").read_text(encoding="utf-8")
    paper_host_freeze = (output / "paper_era_host_environment_freeze.txt").read_text(encoding="utf-8")
    paper_qlib_freeze = (output / "paper_era_qlib_environment_freeze.txt").read_text(encoding="utf-8")
    paper_era_component = json.loads((output / "paper_era_component.json").read_text(encoding="utf-8"))

    assert manifest["overall_status"] == ("partially_corroborated_paper_era_native_run_records_recovered")
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_era_source_revision_available"] is True
    assert manifest["paper_v1_sha256"] == audit.PAPER_V1_SHA256
    assert manifest["paper_mechanism_commit"] == audit.PAPER_MECHANISM_COMMIT
    assert manifest["official_arxiv_versions_audited"] == 2
    assert manifest["official_arxiv_source_archives_audited"] == 2
    assert manifest["official_paper_versions_compiled_to_published_page_count"] == 2
    assert manifest["official_paper_numeric_cell_identities"] == 106
    assert manifest["official_paper_numeric_values_revised_in_v2"] == 5
    assert manifest["official_paper_configuration_labels_revised_in_v2"] == 2
    assert manifest["official_paper_active_figure_assets_v1"] == 6
    assert manifest["official_paper_active_figure_assets_v2"] == 7
    assert manifest["official_paper_logical_figure_assets_revised_in_v2"] == 3
    assert manifest["official_paper_logical_figure_assets_added_in_v2"] == 1
    assert manifest["official_git_history"] == {
        "is_shallow": False,
        "reachable_commits": 493,
        "current_main_commits": 8,
        "legacy_main_commits": 485,
        "root_commits": sorted([audit.SOURCE_FIRST_COMMIT, audit.LEGACY_ROOT_COMMIT]),
        "current_and_legacy_have_common_ancestor": False,
        "paper_mechanism_is_legacy_ancestor": True,
        "preprint_cutoff_is_legacy_ancestor": True,
        "paper_mechanism_files": 856,
        "paper_mechanism_python_files": 331,
        "paper_mechanism_factor_csvs": 15,
        "preprint_cutoff_factor_csvs": 0,
    }
    assert manifest["paper_numeric_table_cells_total"] == 106
    assert manifest["paper_numeric_result_cells_total"] == 100
    assert manifest["native_paper_table_result_cells_reproduced"] == 0
    assert manifest["native_paper_table_result_cells_corroborated"] == 5
    assert manifest["paper_table_result_cells_unavailable"] == 95
    assert manifest["published_non_table_result_claims_total"] == 18
    assert manifest["native_non_table_result_claims_reproduced"] == 0
    assert manifest["paper_specification_gaps_total"] == 17
    assert manifest["source_mechanism_dimensions_total"] == 32
    assert manifest["source_mechanism_component_matches_or_analogues"] == 20
    assert manifest["source_mechanism_fully_faithful"] is False
    assert manifest["paper_era_tracked_files_total"] == 856
    assert manifest["paper_era_python_files_compiled"] == 331
    assert manifest["paper_era_factor_csv_files"] == 15
    assert manifest["paper_era_factor_expression_rows"] == 268
    assert manifest["paper_era_qlib_mlflow_run_records"] == 7
    assert manifest["paper_era_mlflow_multi_record_aggregation_candidates"] == 30
    assert manifest["paper_era_mlflow_full_period_aggregation_candidates"] == 2
    assert manifest["paper_era_mlflow_aggregation_candidates_with_numeric_coincidence"] == 13
    assert manifest["paper_era_mlflow_aggregation_valid_period_display_cells_matching"] == 0
    assert manifest["paper_era_mlflow_aggregation_full_table_row_matches"] == 0
    assert manifest["paper_era_mlflow_aggregation_max_display_cells_matching"] == 2

    assert manifest["paper_era_qlib_mlflow_records_with_fitted_models"] == 7
    assert manifest["paper_era_fitted_lightgbm_states_loaded"] == 7
    assert manifest["paper_era_fitted_lightgbm_state_execution_deterministic"] is True
    assert manifest["paper_era_qlib_mlflow_records_loaded_via_native_recorder"] == 7
    assert manifest["paper_era_native_recorder_execution_runs"] == 2
    assert manifest["paper_era_native_recorder_execution_deterministic"] is True
    assert manifest["paper_era_native_recorder_metrics_loaded"] == 133
    assert manifest["paper_era_native_recorder_params_loaded"] == 189
    assert manifest["paper_era_native_recorder_tags_loaded"] == 35
    assert manifest["paper_era_native_recorder_artifacts_resolved"] == 21
    assert (
        manifest["paper_era_native_recorder_artifacts_loaded_as_raw_bytes"]
        == 21
    )
    assert manifest["paper_era_native_recorder_artifacts_unpickled"] is False
    assert manifest["paper_era_native_recorder_records_matching_manual_metrics"] == 7
    assert manifest["paper_era_native_recorder_raw_artifact_hashes_matching"] == 7
    assert manifest["paper_era_native_recorder_maximum_metric_parser_error"] < 1e-15
    assert manifest["paper_era_native_recorder_paper_result_reproductions"] == 0
    assert manifest["paper_era_native_backtests_reexecuted"] == 0
    assert manifest["paper_era_qlib_mlflow_full_table_row_matches"] == 1
    assert manifest["paper_era_qlib_mlflow_display_cells_corroborated"] == 5
    assert manifest["paper_era_native_recorder_display_cells_corroborated"] == 5
    assert manifest["paper_era_named_alpha101_reference_rows"] == 101
    assert manifest["paper_era_loaded_alpha101_csv_rows"] == 116
    assert manifest["paper_era_figure4_candidate_factor_rows"] == 15
    assert manifest["paper_era_figure4_candidate_parseable_rows"] == 14
    assert manifest["paper_era_ast_component_executable"] is True
    assert manifest["post_paper_dsl_expressions_shipped"] == 13
    assert manifest["post_paper_registry_metric_entries"] == 8
    assert manifest["post_paper_registry_entries_receiving_paper_credit"] == 0
    assert manifest["current_post_paper_data_release_available"] is True
    assert manifest["current_post_paper_data_release_bytes"] == 524248466
    assert manifest["current_post_paper_data_release_valid_paper_input"] is False
    assert manifest["native_paper_factor_pool_shipped"] is True
    assert manifest["native_paper_factor_pool_result_lineage_proven"] is False
    assert manifest["native_paper_prompts_shipped"] is True
    assert manifest["native_partial_qlib_mlflow_records_shipped"] is True
    assert manifest["native_paper_metric_scalars_shipped"] is True
    assert manifest["native_paper_prediction_or_return_series_shipped"] is False
    assert manifest["native_paper_holdings_or_complete_qlib_recorders_shipped"] is False
    assert manifest["native_paper_figure_arrays_shipped"] is False
    assert manifest["native_source_tests_passed_with_dependency_stubs"] == 0
    assert manifest["native_source_tests_passed_with_real_dependencies"] == 80
    assert manifest["native_source_tests_dependency_faithful"] is True
    assert manifest["current_rewrite_dependency_environment_reproduced"] is True
    assert manifest["current_rewrite_exact_historical_dependency_versions_recovered"] is False
    assert manifest["current_rewrite_source_modules_imported"] == 72
    assert manifest["paper_era_dependency_environment_reproduced"] is True
    assert manifest["paper_era_host_dependency_environment_reproduced"] is True
    assert manifest["paper_era_qlib_dependency_environment_reproduced"] is True
    assert manifest["paper_era_exact_historical_dependency_versions_recovered"] is False
    assert manifest["paper_era_exact_cuda_container_reproduced"] is False
    assert manifest["paper_era_dependency_release_cutoff_utc"] == (audit.PAPER_MECHANISM_COMMIT_UTC)
    assert manifest["paper_era_rdagent_commit_in_environment"] == (audit.PAPER_MECHANISM_COMMIT)
    assert manifest["paper_era_qlib_commit_in_environment"] == audit.QLIB_SOURCE_COMMIT
    assert manifest["paper_era_host_selected_source_modules"] == 113
    assert manifest["paper_era_host_source_modules_imported"] == 112
    assert manifest["paper_era_host_source_module_failures"] == 1
    assert manifest["paper_era_upstream_offline_tests_passed"] == 1
    assert manifest["paper_era_upstream_offline_tests_failed"] == 1
    assert manifest["native_synthetic_base_factors_executable"] == 4
    assert manifest["native_synthetic_component_paper_result_reproduction"] is False
    assert manifest["public_source_unique_historical_file_paths"] == 2499
    assert manifest["public_source_reachable_blobs"] == 3907
    assert manifest["public_source_reachable_trees"] == 3912
    assert manifest["public_source_reachable_commit_objects"] == 493
    assert manifest["public_source_historical_author_run_record_paths"] == 385
    assert manifest["public_source_historical_author_run_ids"] == 7
    assert manifest["public_source_primitive_prediction_return_or_holding_paths"] == 0
    assert manifest["fork_discovery_date"] == "2026-08-30"
    assert manifest["fork_default_heads_total"] == 73
    assert manifest["fork_unique_default_head_groups"] == 6
    assert manifest["forks_at_official_heads"] == 69
    assert manifest["divergent_fork_default_heads"] == 4
    assert manifest["divergent_fork_paper_result_units_regenerated"] == 0
    assert manifest["independent_fork_data_bundle_audited"] is True
    assert manifest["independent_fork_data_bundle_calendar_start"] == "2020-01-02"
    assert manifest["independent_fork_data_bundle_sp500_rows"] == 568
    assert manifest["independent_fork_data_bundle_finite_membership_end_rows"] == 1
    assert manifest["independent_fork_data_bundle_valid_paper_input"] is False
    assert manifest["wang_fork_tip_commit"] == audit.FORK_WANG_TIP
    assert manifest["wang_fork_commits_ahead_of_rewrite"] == 51
    assert manifest["wang_fork_changed_paths_from_rewrite"] == 130
    assert manifest["wang_fork_postpaper_registry_metric_entries"] == 26
    assert manifest["wang_fork_postpaper_registry_entries_attributable_to_paper_run"] == 0
    assert manifest["wang_fork_postpaper_registry_entries_receiving_paper_credit"] == 0
    assert manifest["paper_era_matching_run_id"] == audit.MATCHING_RUN_ID
    assert manifest["paper_era_matching_run_generated_factor_features"] == 5
    assert manifest["paper_era_run_time_public_factor_candidates"] == 4
    assert manifest["paper_era_exact_generated_factor_lineage_recovered"] is False
    assert manifest["paper_era_qlib_fallback_archive_sha256"] == (audit.QLIB_US_DATA_ARCHIVE_SHA256)
    assert manifest["paper_era_qlib_fallback_calendar_start"] == "1999-12-31"
    assert manifest["paper_era_qlib_fallback_calendar_end"] == "2020-11-10"
    assert manifest["paper_era_qlib_fallback_has_spx_benchmark"] is False
    assert manifest["paper_era_qlib_fallback_covers_test_period"] is False
    assert manifest["paper_era_matching_run_replayable_from_released_inputs"] is False

    assert Counter(row["status"] for row in table) == {
        "corroborated_by_author_history_native_qlib_recorder": 5,
        "unavailable_missing_native_paper_result_path": 95,
        "paper_configuration_recovered_without_frozen_dataset": 6,
    }
    assert Counter(row["claim_role"] for row in claims) == {
        "result": 18,
        "configuration": 8,
    }
    assert len(mechanisms) == 32
    assert Counter(row["paper_mechanism_credit"] for row in mechanisms) == {
        "False": 12,
        "True": 20,
    }
    assert len(current_mechanisms) == 32
    assert Counter(row["paper_mechanism_credit"] for row in current_mechanisms) == {
        "False": 28,
        "True": 4,
    }
    assert len(history) == 8
    assert len(paper_versions) == 2
    assert {row["paper_version"] for row in paper_versions} == {"v1", "v2"}
    assert {row["compiled_pdf_pages"] for row in paper_versions} == {"10"}
    assert {row["source_cutoff_native_run_records"] for row in paper_versions} == {"0"}
    assert {row["source_cutoff_factor_zoo_files"] for row in paper_versions} == {"0"}
    assert len(paper_lineage) == 106
    assert Counter(row["status"] for row in paper_lineage) == {
        "unchanged": 99,
        "numeric_value_revised_in_v2": 5,
        "configuration_label_revised_in_v2": 2,
    }
    assert len(paper_figures) == 13
    assert Counter(row["paper_version"] for row in paper_figures) == {"v2": 7, "v1": 6}
    figure_status = {row["logical_figure_id"]: row["lineage_status"] for row in paper_figures}
    assert Counter(figure_status.values()) == {
        "byte_identical": 3,
        "source_asset_revised_in_v2": 3,
        "added_in_v2": 1,
    }
    assert len(history_paths) == 2499
    assert sum(row["paper_era_author_run_record"] == "True" for row in history_paths) == 385
    assert {row["primitive_prediction_return_or_holding_output"] for row in history_paths} == {"False"}
    assert history_summary["official_reachable_object_types"] == {
        "blob": 3907,
        "commit": 493,
        "tree": 3912,
    }
    assert history_summary["historical_author_run_ids"] == sorted(row["run_id"] for row in paper_era_runs)
    assert len(fork_heads) == 6
    assert sum(int(row["repository_count"]) for row in fork_heads) == 73
    assert Counter(row["default_head_commit"] for row in fork_heads) == {
        audit.LEGACY_HEAD_COMMIT: 1,
        audit.SOURCE_COMMIT: 1,
        "e3634a100a33d2a21532e8bafcf458765a7aef8b": 1,
        "bb6e330f33c2a68917f8ec489d147f9df8027bb2": 1,
        audit.FORK_DATA_TIP: 1,
        audit.FORK_WANG_TIP: 1,
    }
    assert {row["paper_result_credit"] for row in fork_heads} == {"False"}
    assert {row["additional_attributable_author_native_artifact"] for row in fork_heads} == {"False"}
    assert sum(int(row["paper_result_units_regenerated"]) for row in fork_heads) == 0
    assert fork_bundle["repository"] == "vodaza36/AlphaAgent"
    assert fork_bundle["tip_commit"] == audit.FORK_DATA_TIP
    assert fork_bundle["data_zip_sha256"] == audit.FORK_DATA_ZIP_SHA256
    assert fork_bundle["data_zip_bytes"] == 17805441
    assert fork_bundle["zip_entries"] == 3980
    assert fork_bundle["calendar_rows"] == 1533
    assert fork_bundle["calendar_start"] == "2020-01-02"
    assert fork_bundle["calendar_end"] == "2026-02-06"
    assert fork_bundle["feature_symbols"] == 568
    assert fork_bundle["sp500_membership_rows"] == 568
    assert fork_bundle["sp500_rows_with_finite_membership_end"] == 1
    assert fork_bundle["archive_membership_file_supports_claim"] is False
    assert fork_bundle["paper_training_start_2015_covered"] is False
    assert fork_bundle["paper_result_units_regenerated"] == 0
    assert fork_bundle["paper_result_credit"] is False
    assert len(fork_wang_registry) == 26
    assert {row["tip_commit"] for row in fork_wang_registry} == {audit.FORK_WANG_TIP}
    assert {row["ingest_status"] for row in fork_wang_registry} == {"stored"}
    assert {row["source"] for row in fork_wang_registry} == {"submit"}
    assert {row["postpaper_disjoint_rewrite_artifact"] for row in fork_wang_registry} == {"True"}
    assert {row["attributable_to_paper_run"] for row in fork_wang_registry} == {"False"}
    assert {row["paper_result_credit"] for row in fork_wang_registry} == {"False"}
    assert len({row["factor_id"] for row in fork_wang_registry}) == 26
    assert run_inputs["matching_run_id"] == audit.MATCHING_RUN_ID
    assert run_inputs["matching_run_started_utc"] == audit.MATCHING_RUN_STARTED_UTC
    assert run_inputs["public_head_at_run_time"] == audit.RUN_TIME_PUBLIC_HEAD
    assert run_inputs["matching_run_generated_factor_features"] == 5
    assert run_inputs["run_time_public_us_factor_candidate_rows"] == 4
    assert run_inputs["paper_snapshot_us_factor_candidate_rows"] == 6
    assert run_inputs["factor_candidates_added_after_run"] == [
        "5D_VolumeSpike_Confirmation6",
        "Stable_MeanReversion_10D",
    ]
    assert run_inputs["combined_factors_df_ever_tracked"] is False
    assert run_inputs["exact_generated_factor_lineage_recovered"] is False
    assert run_inputs["qlib_data_downloader_sha256"] == (audit.QLIB_DATA_DOWNLOADER_SHA256)
    assert run_inputs["qlib_data_archive_sha256"] == audit.QLIB_US_DATA_ARCHIVE_SHA256
    assert run_inputs["qlib_data_archive_bytes"] == 450_094_816
    assert run_inputs["qlib_data_zip_entries"] == 71_959
    assert run_inputs["qlib_data_calendar_rows"] == 5_250
    assert run_inputs["qlib_data_calendar_start"] == "1999-12-31"
    assert run_inputs["qlib_data_calendar_end"] == "2020-11-10"
    assert run_inputs["qlib_data_sp500_membership_rows"] == 755
    assert run_inputs["qlib_data_feature_symbols"] == 8_994
    assert run_inputs["qlib_data_has_spx_feature"] is False
    assert run_inputs["qlib_data_has_gspc_feature"] is True
    assert run_inputs["paper_test_period_covered"] is False
    assert run_inputs["matching_run_replayable_from_released_inputs"] is False
    assert run_inputs["native_backtests_reexecuted"] == 0
    assert run_inputs["paper_result_credit"] is False
    assert len(gaps) == 17
    assert len(inventory) == 141
    assert len(paper_era_inventory) == 856
    assert {row["paper_era_artifact"] for row in paper_era_inventory} == {"True"}
    assert {row["paper_result_credit"] for row in paper_era_inventory} == {"False"}
    assert len(paper_era_factors) == 15
    assert sum(int(row["expression_rows"]) for row in paper_era_factors) == 268
    alpha101 = next(row for row in paper_era_factors if row["path"] == "factor_zoo/alpha101.csv")
    assert int(alpha101["expression_rows"]) == 116
    assert int(alpha101["alpha101_reference_rows"]) == 101
    assert int(alpha101["other_expression_rows"]) == 15
    assert len(paper_era_runs) == 7
    assert sum(int(row["tracked_files"]) for row in paper_era_runs) == 385
    for hash_field in (
        "config_sha256",
        "dataset_sha256",
        "task_sha256",
        "fitted_lightgbm_state_sha256",
    ):
        assert all(len(row[hash_field]) == 64 for row in paper_era_runs)
    exact_runs = [row for row in paper_era_runs if row["all_five_display_cells_match"] == "True"]
    assert [row["run_id"] for row in exact_runs] == ["77b227f86e5a47bab48178cac409a98b"]
    assert exact_runs[0]["market"] == "S&P500"
    assert int(exact_runs[0]["display_cells_matching_alphaagent_row"]) == 5
    assert int(exact_runs[0]["paper_result_cells_corroborated"]) == 5
    assert int(exact_runs[0]["generated_factor_features"]) == 5
    assert int(exact_runs[0]["model_features_loaded"]) == 9
    assert int(exact_runs[0]["model_trees_loaded"]) == 3
    assert {row["fitted_lightgbm_state_loaded"] for row in paper_era_runs} == {"True"}
    assert {row["fitted_model_execution_paper_result_credit"] for row in paper_era_runs} == {"False"}
    assert all(len(row["feature_names_sha256"]) == 64 for row in paper_era_runs)
    assert all(len(row["probe_predictions_sha256"]) == 64 for row in paper_era_runs)
    assert {row["predictions_returns_holdings_shipped"] for row in paper_era_runs} == {"False"}
    assert {row["native_qlib_recorder_loaded"] for row in paper_era_runs} == {"True"}
    assert {row["native_recorder_status"] for row in paper_era_runs} == {"FINISHED"}
    assert {row["native_recorder_metric_count"] for row in paper_era_runs} == {"19"}
    assert {row["native_recorder_param_count"] for row in paper_era_runs} == {"27"}
    assert {row["native_recorder_tag_count"] for row in paper_era_runs} == {"5"}
    assert {row["native_recorder_artifacts"] for row in paper_era_runs} == {
        "config;dataset;task"
    }
    assert {
        row["native_recorder_raw_artifact_hashes_match"]
        for row in paper_era_runs
    } == {"True"}
    assert {
        row["native_recorder_metrics_match_parsed_values"]
        for row in paper_era_runs
    } == {"True"}
    assert max(
        float(row["native_recorder_maximum_metric_parser_error"])
        for row in paper_era_runs
    ) < 1e-15
    assert {row["native_recorder_artifacts_unpickled"] for row in paper_era_runs} == {
        "False"
    }
    assert {
        row["native_recorder_paper_result_reproduction"]
        for row in paper_era_runs
    } == {"False"}
    assert len(native_recorders) == 7
    assert {row["status"] for row in native_recorders} == {"FINISHED"}
    assert sum(int(row["metrics_loaded"]) for row in native_recorders) == 133
    assert sum(int(row["params_loaded"]) for row in native_recorders) == 189
    assert sum(int(row["tags_loaded"]) for row in native_recorders) == 35
    assert sum(int(row["artifacts_resolved"]) for row in native_recorders) == 21
    assert sum(
        int(row["raw_artifacts_loaded_without_unpickling"])
        for row in native_recorders
    ) == 21
    assert {row["metric_values_match_manual_parser"] for row in native_recorders} == {
        "True"
    }
    assert {row["raw_artifact_hashes_match"] for row in native_recorders} == {
        "True"
    }
    assert {
        row["native_recorder_paper_result_reproduction"]
        for row in native_recorders
    } == {"False"}
    assert sum(
        int(row["paper_result_cells_corroborated"])
        for row in native_recorders
    ) == 5
    assert len(paper_era_aggregations) == 30
    assert Counter(row["market"] for row in paper_era_aggregations) == {
        "CSI500": 8,
        "S&P500": 22,
    }
    assert Counter(row["aggregation"] for row in paper_era_aggregations) == {
        "mean": 15,
        "median": 15,
    }
    assert sum(
        row["all_runs_cover_full_paper_period"] == "True"
        for row in paper_era_aggregations
    ) == 2
    assert sum(
        int(row["display_cells_matching"]) > 0
        for row in paper_era_aggregations
    ) == 13
    assert {
        row["valid_period_display_cells_matching"] for row in paper_era_aggregations
    } == {"0"}
    assert {row["all_five_display_cells_match"] for row in paper_era_aggregations} == {
        "False"
    }
    assert {row["paper_result_credit"] for row in paper_era_aggregations} == {"False"}
    csi_aggregation_matches = [
        row
        for row in paper_era_aggregations
        if row["market"] == "CSI500" and int(row["display_cells_matching"])
    ]
    assert len(csi_aggregation_matches) == 1
    assert csi_aggregation_matches[0]["aggregation"] == "mean"
    assert csi_aggregation_matches[0]["run_count"] == "3"
    assert csi_aggregation_matches[0]["display_metrics_matching"] == "IC"
    assert csi_aggregation_matches[0]["all_runs_cover_full_paper_period"] == "False"

    assert len(registry) == 8
    assert {row["paper_result_credit"] for row in registry} == {"False"}
    assert len(data_release) == 1
    assert data_release[0]["paper_data_credit"] == "False"
    assert int(data_release[0]["bytes"]) == 524248466
    assert len(factors) == 4
    assert {row["native_parser_executable"] for row in factors} == {"True"}
    assert {row["paper_metric_reproduced"] for row in factors} == {"False"}
    assert component["upstream_tests"]["tests_passed"] == 80
    assert component["upstream_tests"]["status"] == "passed_with_real_declared_dependencies"
    assert component["upstream_tests"]["dependency_stubs"] == []
    assert component["upstream_tests"]["imported_source_modules"] == 72
    assert component["upstream_tests"]["network_attempts"] == []
    assert component["upstream_tests"]["deterministic_across_two_runs"] is True
    assert component["dependency_environment_reproduced"] is True
    assert component["exact_historical_dependency_versions_recovered"] is False
    assert component["pip_check"] == "No broken requirements found."
    assert component["dependency_freeze_sha256"] == audit.REWRITE_ENV_FREEZE_SHA256
    assert component["dependency_freeze_lines"] == 126
    assert len(rewrite_freeze.splitlines()) == 126
    assert audit.sha256_bytes(rewrite_freeze.encode()) == audit.REWRITE_ENV_FREEZE_SHA256
    assert component["synthetic_base_factor_component"]["deterministic"] is True
    assert component["synthetic_base_factor_component"]["sha256"] == (
        "e0bd090308b893c6bcf97cc1589538e4fcedc4a896bb90d21a0848e92d7a5dc9"
    )
    assert component["paper_result_reproduction"] is False
    assert paper_era_component["compile_passed"] is True
    assert paper_era_component["python_files_compiled"] == 331
    assert paper_era_component["ast_component_deterministic"] is True
    assert paper_era_component["identical_expression_lcs_size"] == 4
    assert paper_era_component["commutative_expression_lcs_size"] == 3
    assert paper_era_component["partial_expression_lcs_size"] == 3
    assert paper_era_component["named_alpha101_reference_rows"] == 101
    assert paper_era_component["loaded_alpha101_csv_rows"] == 116
    assert paper_era_component["alpha101_self_match_exact"] is True
    assert paper_era_component["figure4_candidate_factor_rows"] == 15
    assert paper_era_component["figure4_candidate_parseable_rows"] == 14
    assert paper_era_component["figure4_candidate_parse_failures"] == ["Lagged_Volume_Change_Factor_3D"]
    assert paper_era_component["dependency_environment_reproduced"] is True
    assert paper_era_component["exact_historical_dependency_versions_recovered"] is False
    assert paper_era_component["exact_cuda_container_reproduced"] is False
    host_environment = paper_era_component["host_environment"]
    assert host_environment["dependency_freeze_sha256"] == (audit.PAPER_HOST_ENV_FREEZE_SHA256)
    assert host_environment["dependency_freeze_lines"] == 153
    assert host_environment["pip_check"] == "No broken requirements found."
    assert host_environment["source_commit_in_environment"] == audit.PAPER_MECHANISM_COMMIT
    assert host_environment["selected_source_modules"] == 113
    assert host_environment["imported_source_modules"] == 112
    assert host_environment["network_attempts"] == []
    assert host_environment["module_import_failures"] == [
        {
            "module": audit.PAPER_ERA_IMPORT_FAILURE_MODULE,
            "exception_type": "FileNotFoundError",
            "message": (f"[Errno 2] No such file or directory: '{audit.PAPER_ERA_IMPORT_FAILURE_PATH}'"),
        }
    ]
    assert host_environment["upstream_offline_tests"]["tests_passed"] == 1
    assert host_environment["upstream_offline_tests"]["tests_failed"] == 1
    assert host_environment["upstream_offline_tests"]["failure_is_dependency_error"] is False
    qlib_environment = paper_era_component["qlib_environment"]
    assert qlib_environment["dependency_freeze_sha256"] == (audit.PAPER_QLIB_ENV_FREEZE_SHA256)
    assert qlib_environment["dependency_freeze_lines"] == 119
    assert qlib_environment["pip_check"] == "No broken requirements found."
    assert qlib_environment["source_commit_in_environment"] == audit.QLIB_SOURCE_COMMIT
    assert qlib_environment["resolved_packages"] == {
        "catboost": "1.2.7",
        "lightgbm": "4.5.0",
        "mlflow": "1.30.0",
        "pyqlib": "0.9.5.99",
        "scipy": "1.11.4",
        "torch": "2.2.1+cpu",
        "xgboost": "2.1.4",
    }
    assert qlib_environment["fitted_lightgbm_states_loaded"] == 7
    assert qlib_environment["native_mlflow_recorders_loaded"] == 7
    assert qlib_environment["native_mlflow_recorder_execution_runs"] == 2
    assert qlib_environment["native_mlflow_recorder_execution_deterministic"] is True
    assert qlib_environment["native_mlflow_metrics_loaded"] == 133
    assert qlib_environment["native_mlflow_params_loaded"] == 189
    assert qlib_environment["native_mlflow_tags_loaded"] == 35
    assert qlib_environment["native_mlflow_artifacts_resolved"] == 21
    assert qlib_environment["native_mlflow_artifacts_loaded_as_raw_bytes"] == 21
    assert qlib_environment["native_mlflow_artifacts_unpickled"] is False
    assert qlib_environment["native_backtests_reexecuted"] == 0
    assert qlib_environment["network_attempts"] == []
    assert len(paper_era_component["fitted_model_executions"]) == 7
    matching_model = next(
        row
        for row in paper_era_component["fitted_model_executions"]
        if row["run_id"] == "77b227f86e5a47bab48178cac409a98b"
    )
    assert matching_model["model_features"] == 9
    assert matching_model["model_trees"] == 3
    assert matching_model["native_recorder_status"] == "FINISHED"
    assert matching_model["native_recorder_metric_count"] == 19
    assert matching_model["native_recorder_relevant_metrics"] == {
        "IC": 0.005635554500180115,
        "ICIR": 0.055213454925421054,
        "1day.excess_return_with_cost.annualized_return": 0.08743898075444394,
        "1day.excess_return_with_cost.information_ratio": 1.0544926514004396,
        "1day.excess_return_with_cost.max_drawdown": -0.09098193314326458,
    }
    assert matching_model["native_recorder_artifacts"] == [
        "config",
        "dataset",
        "task",
    ]
    assert matching_model["native_recorder_artifacts_unpickled"] is False
    assert len(paper_host_freeze.splitlines()) == 153
    assert audit.sha256_bytes(paper_host_freeze.encode()) == (audit.PAPER_HOST_ENV_FREEZE_SHA256)
    assert len(paper_qlib_freeze.splitlines()) == 119
    assert audit.sha256_bytes(paper_qlib_freeze.encode()) == (audit.PAPER_QLIB_ENV_FREEZE_SHA256)
    assert paper_era_component["paper_result_reproduction"] is False

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_global_evidence_route_preserves_run_input_replay_failure() -> None:
    ledger = read_csv(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in ledger if item["system_id"] == "SYS-ALPHA-AGENT")
    note = row["concise_evidence_note"]
    assert "30 candidates in total" in note
    assert "Only two consist entirely of full-paper-period records" in note
    assert "both match zero displayed cells" in note
    assert "13 off-period candidates" in note
    assert "450,094,816-byte US archive" in note
    assert "calendar ends on 2020-11-10" in note
    assert "four US candidate expressions" in note
    assert "requires five generated features" in note
    assert "No combined_factors_df.pkl exists" in note
    assert "adds no paper-result credit" in note

    failure_table = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text()
    assert "30 candidates in total" in failure_table
    assert "13 off-period candidates" in failure_table
    assert "450,094,816-byte" in failure_table
    assert "2020-11-10" in failure_table
    assert r"combined\_factors\_df.pkl" in failure_table


def test_pinned_source_static_checks_when_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_source")
    if not source_root.exists():
        return
    assert audit.git_head(source_root) == audit.SOURCE_COMMIT
    first_commit, first_date = audit.git_first_commit(source_root)
    assert first_commit == audit.SOURCE_FIRST_COMMIT
    assert first_date.startswith("2026-07-01")
    history, timeline = audit.history_audit(source_root)
    assert history["legacy_main_commits"] == 485
    assert history["current_and_legacy_have_common_ancestor"] is False
    assert history["paper_mechanism_files"] == 856
    assert history["preprint_cutoff_factor_csvs"] == 0
    assert len(timeline) == 8
    history_paths, history_summary = audit.public_source_history(source_root)
    assert len(history_paths) == 2499
    assert history_summary["official_reachable_commits"] == 493
    assert history_summary["official_reachable_objects"] == 8312
    assert history_summary["historical_author_run_record_paths"] == 385
    assert history_summary["primitive_prediction_return_or_holding_paths"] == 0
    fork_heads, fork_bundle = audit.fork_default_head_audit(source_root)
    assert len(fork_heads) == 6
    assert sum(int(row["repository_count"]) for row in fork_heads) == 73
    assert sum(int(row["paper_result_units_regenerated"]) for row in fork_heads) == 0
    assert fork_bundle["data_zip_bytes"] == 17805441
    assert fork_bundle["calendar_start"] == "2020-01-02"
    assert fork_bundle["sp500_rows_with_finite_membership_end"] == 1
    assert fork_bundle["paper_training_start_2015_covered"] is False
    fork_wang_registry = audit.fork_wang_registry_rows(source_root)
    assert len(fork_wang_registry) == 26
    assert {row["tip_commit"] for row in fork_wang_registry} == {audit.FORK_WANG_TIP}
    assert {row["paper_result_credit"] for row in fork_wang_registry} == {False}

    qlib_source = Path(audit.DEFAULT_PAPER_QLIB_SOURCE_ROOT)
    qlib_archive = Path(audit.DEFAULT_PAPER_QLIB_DATA_ARCHIVE)
    if qlib_source.exists() and qlib_archive.exists():
        run_inputs = audit.paper_era_run_input_audit(source_root, qlib_source, qlib_archive)
        assert run_inputs["matching_run_id"] == audit.MATCHING_RUN_ID
        assert run_inputs["run_time_public_us_factor_candidate_rows"] == 4
        assert run_inputs["paper_snapshot_us_factor_candidate_rows"] == 6
        assert run_inputs["qlib_data_archive_sha256"] == (audit.QLIB_US_DATA_ARCHIVE_SHA256)
        assert run_inputs["paper_test_period_covered"] is False
        assert run_inputs["matching_run_replayable_from_released_inputs"] is False

    current = {row["dimension"]: row for row in audit.current_source_conformance(source_root)}
    assert current["paper_era_source"]["status"] == "mismatch_post_paper_rewrite"
    assert current["largest_common_subtree"]["status"] == "missing"

    with tempfile.TemporaryDirectory() as temp_dir:
        snapshot = Path(temp_dir)
        audit.extract_git_commit(source_root, audit.PAPER_MECHANISM_COMMIT, snapshot)
        mechanisms = {row["dimension"]: row for row in audit.paper_era_source_conformance(snapshot)}
    assert mechanisms["paper_era_source"]["status"] == "recovered_preprint_source"
    assert mechanisms["ast_representation"]["status"] == "component_match"
    assert mechanisms["largest_common_subtree"]["status"] == "component_match"
    assert mechanisms["similarity_kind"]["status"] == "component_match"
    assert mechanisms["paper_lightgbm"]["status"] == "configuration_match"
    assert mechanisms["symbolic_length"]["status"] == "missing"
    assert mechanisms["er_score"]["status"] == "mismatch_hard_filter"

    source_python = Path(audit.DEFAULT_SOURCE_PYTHON)
    if source_python.is_file():
        component, _ = audit.run_native_component_checks(source_root, source_python)
        assert component["upstream_tests"]["dependency_stubs"] == []
        assert component["upstream_tests"]["network_attempts"] == []


def test_pinned_official_paper_sources_when_available() -> None:
    versions_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_paper_versions")
    if not versions_root.exists():
        return
    for version, expected in audit.PAPER_VERSIONS.items():
        pdf = versions_root / f"paper_{version}.pdf"
        archive = versions_root / f"paper_{version}_source.tar.gz"
        assert audit.sha256(pdf) == expected["pdf_sha256"]
        assert audit.sha256(archive) == expected["source_sha256"]
        assert audit._pdf_pages(pdf) == 10
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            audit._extract_official_source(archive, source)
            assert audit._source_tree_facts(source) == (
                expected["source_files"],
                expected["source_uncompressed_bytes"],
                expected["source_tree_sha256"],
            )
            parsed = audit._paper_table_2_values(source / expected["main_tex"])
            ledger = [row["paper_value"] for row in audit.paper_numeric_rows(version) if row["paper_table"] == 2]
            assert parsed == ledger
            figures = audit._paper_figure_assets(version, source, source / expected["main_tex"])
            assert len(figures) == (6 if version == "v1" else 7)
