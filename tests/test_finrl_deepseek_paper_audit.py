from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_finrl_deepseek_paper.py"
SPEC = importlib.util.spec_from_file_location("finrl_deepseek_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_complete_table_and_unique_measurement_census_is_fail_closed() -> None:
    rows = audit.paper_table_rows()
    unique = audit.unique_measurement_rows(rows)
    assert len(rows) == 36
    assert Counter(row["paper_table"] for row in rows) == {
        "Table 1 main 100-epoch comparison": 12,
        "Table 2 PPO infusion": 12,
        "Table 3 CPPO infusion": 12,
    }
    assert len(unique) == 24
    assert {row["paper_result_credit"] for row in rows + unique} == {False}


def test_stored_notebook_outputs_are_incomplete_mismatches_and_stale() -> None:
    rows = audit.notebook_conformance_rows()
    stale = audit.notebook_stale_output_rows()
    assert len(rows) == 36
    assert Counter(row["status"] for row in rows) == {
        "stored_output_mismatch": 27,
        "missing_stored_output": 9,
    }
    assert len(stale) == 6
    assert {row["status"] for row in stale} == {"same_series_different_stored_output"}


def test_postpaper_community_checkpoint_rerun_is_adverse_not_promoted() -> None:
    rows = audit.community_notebook_conformance_rows()
    assert len(rows) == 36
    assert Counter(row["status"] for row in rows) == {
        "postpaper_community_stored_output_mismatch": 30,
        "missing_postpaper_community_stored_output": 6,
    }
    assert sum(bool(row["community_stored_value"]) for row in rows) == 30
    assert {row["paper_result_credit"] for row in rows} == {False}


def test_raster_results_and_mechanism_boundary_are_explicit() -> None:
    figures = audit.figure_rows()
    labels = audit.figure_metric_rows()
    mechanisms = audit.mechanism_conformance()
    configs = audit.config_conformance()
    assert len(figures) == 32
    assert Counter(row["figure"] for row in figures) == {
        "Figure 1 / download4.png": 5,
        "Figure 2 / download10.png": 7,
        "Figure 3 / download15.png": 5,
        "Figure 4 / download13.png": 5,
        "Figure 5 / download17.png": 5,
        "Figure 6 / download18.png": 5,
    }
    assert len(labels) == 4
    assert {row["paper_result_credit"] for row in figures + labels} == {False}
    assert len(mechanisms) == 26
    assert sum(row["paper_mechanism_credit"] for row in mechanisms) == 7
    assert len(configs) == 20
    assert len(audit.specification_gaps()) == 20


def test_committed_audit_records_native_execution_without_promoting_it() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/finrl_deepseek"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((output / "native_released_agent_execution.json").read_text(encoding="utf-8"))
    history = json.loads((output / "public_source_history.json").read_text(encoding="utf-8"))
    table = read_csv(output / "paper_numeric_table_conformance.csv")
    notebook = read_csv(output / "released_notebook_metric_conformance.csv")
    rerun_conformance = read_csv(output / "native_current_rerun_conformance.csv")
    alignment = read_csv(output / "notebook_benchmark_alignment_audit.csv")
    benchmark = json.loads((output / "yahoo_ndx_20190101_20231231.json").read_text(encoding="utf-8"))
    current_runs = {
        name: json.loads((output / name).read_text(encoding="utf-8"))
        for name in (
            "native_current_seed0.json",
            "native_current_seed42.json",
            "native_current_mean.json",
        )
    }
    historical_notebooks = read_csv(output / "historical_notebook_inventory.csv")
    historical_logs = read_csv(output / "historical_training_log_inventory.csv")
    fork_repositories = read_csv(output / "public_fork_repository_access_inventory.csv")
    fork_refs = read_csv(output / "public_fork_ref_snapshot.csv")
    fork_heads = read_csv(output / "public_fork_unique_head_inventory.csv")
    fork_commits = read_csv(output / "public_fork_divergent_commit_inventory.csv")
    fork_paths = read_csv(output / "public_fork_divergent_path_inventory.csv")
    fork_notebooks = read_csv(output / "public_fork_notebook_inventory.csv")
    fork_table = read_csv(output / "public_fork_notebook_table_conformance.csv")
    fork_summary = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))
    assert manifest["overall_status"] == ("released_data_checkpoints_and_code_execute_but_paper_results_not_reproduced")
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_table_cells_total"] == 36
    assert manifest["paper_unique_numeric_measurements_total"] == 24
    assert manifest["native_table_cells_display_precision_matches"] == 0
    assert manifest["native_table_cells_with_paper_result_credit"] == 0
    assert manifest["stored_notebook_table_cells_present"] == 27
    assert manifest["stored_notebook_table_cells_missing"] == 9
    assert manifest["stored_notebook_table_cells_matching_paper"] == 0
    assert manifest["paper_figure_series_total"] == 32
    assert manifest["native_exact_figure_series_reproduced"] == 0
    assert manifest["paper_relevant_released_checkpoints_executed"] == 8
    assert manifest["native_evaluation_protocols_executed"] == 3
    assert manifest["native_current_rerun_configurations_total"] == 24
    assert manifest["native_current_rerun_configurations_exact"] == 17
    assert manifest["native_current_rerun_exact_by_file"] == {
        "native_current_mean.json": 7,
        "native_current_seed0.json": 4,
        "native_current_seed42.json": 6,
    }
    assert manifest["native_current_rerun_protocols_all_configurations_exact"] == 0
    assert manifest["native_current_rerun_maximum_final_asset_relative_difference"] > 0.316
    assert manifest["native_current_information_ratio_measurements"] == 24
    assert manifest["native_current_information_ratio_display_precision_matches"] == 0
    assert manifest["native_current_information_ratio_paper_result_credit"] == 0
    assert manifest["pinned_ndx_benchmark_artifact_sha256"] == audit.NDX_BENCHMARK_ARTIFACT_SHA256
    assert manifest["pinned_ndx_benchmark_canonical_close_sha256"] == audit.NDX_BENCHMARK_CANONICAL_CLOSE_SHA256
    assert manifest["pinned_ndx_benchmark_timestamps_total"] == 979
    assert manifest["pinned_ndx_benchmark_all_ohlcv_null_timestamps"] == 42
    assert manifest["pinned_ndx_benchmark_valid_close_observations"] == 937
    assert manifest["pinned_ndx_benchmark_first_valid_date"] == "2020-02-11"
    assert manifest["pinned_ndx_benchmark_last_valid_date"] == "2023-12-29"
    assert manifest["released_notebook_exact_benchmark_alignment_operational"] is False
    assert manifest["released_notebook_trade_dates"] == 1257
    assert manifest["released_notebook_sliced_asset_values"] == 1256
    assert manifest["native_repaired_benchmark_common_dates"] == 936
    assert manifest["native_repaired_benchmark_aligned_returns"] == 935
    assert manifest["native_repaired_benchmark_is_paper_time_snapshot"] is False
    assert manifest["released_dataset_files_total"] == 12
    assert manifest["released_checkpoint_files_total"] == 15
    assert manifest["current_tracked_source_files_total"] == 47
    assert manifest["pre_submission_python_files_compiled"] == 25
    assert manifest["pre_submission_python_files_total"] == 25
    assert manifest["current_python_files_compiled"] == 26
    assert manifest["current_python_files_total"] == 27
    assert manifest["public_source_reachable_commits_total"] == 36
    assert manifest["public_source_unique_historical_paths_total"] == 48
    assert manifest["public_source_reachable_blobs_total"] == 73
    assert manifest["public_source_reachable_trees_total"] == 36
    assert manifest["public_source_reachable_commit_objects_total"] == 36
    assert manifest["public_source_unreachable_objects_total"] == 0
    assert manifest["historical_notebook_blobs_total"] == 9
    assert manifest["historical_notebook_valid_json_blobs"] == 7
    assert manifest["historical_notebook_malformed_json_blobs"] == 2
    assert manifest["historical_notebook_distinct_metric_output_signatures"] == 1
    assert manifest["historical_notebook_blobs_with_paper_numeric_match"] == 0
    assert manifest["historical_training_log_blobs_total"] == 15
    assert manifest["historical_training_logs_with_evaluation_metrics"] == 0
    assert manifest["historical_logs_with_exact_released_checkpoint_name"] == 10
    assert manifest["paper_relevant_checkpoints_with_exact_training_log_name"] == 5
    assert manifest["public_fork_rest_repository_listings"] == 81
    assert manifest["public_forks_accessible"] == 80
    assert manifest["public_fork_stale_or_inaccessible_rest_listings"] == 1
    assert manifest["public_fork_branch_refs_audited"] == 82
    assert manifest["public_fork_tag_refs_audited"] == 0
    assert manifest["public_fork_unique_heads_audited"] == 10
    assert manifest["public_fork_divergent_heads_audited"] == 5
    assert manifest["public_fork_divergent_commits_audited"] == 69
    assert manifest["public_fork_divergent_paths_audited"] == 84
    assert manifest["public_fork_new_blobs_audited"] == 159
    assert manifest["public_fork_notebook_blob_versions_audited"] == 2
    assert manifest["public_fork_community_stored_metric_entries"] == 33
    assert manifest["public_fork_community_table_cells_corresponded"] == 30
    assert manifest["public_fork_community_table_cells_matching_paper"] == 0
    assert manifest["public_fork_community_table_cells_mismatching_paper"] == 30
    assert manifest["public_fork_community_table_cells_missing"] == 6
    assert manifest["public_fork_postpaper_adaptation_python_files_compiled"] == 82
    assert manifest["public_fork_new_checkpoint_paths"] == 0
    assert manifest["public_fork_new_dataset_paths"] == 0
    assert manifest["public_fork_new_training_log_paths"] == 0
    assert manifest["public_fork_native_paper_result_artifacts_found"] == 0
    assert manifest["public_fork_paper_result_credit"] is False
    assert len(table) == 36 and len(notebook) == 36
    assert sum(bool(row["native_seed0_value"]) for row in table) == 36
    assert Counter(row["status"] for row in table if row["metric"] == "Information Ratio") == {
        "native_current_benchmark_alignment_repair_mismatch_no_credit": 12
    }
    assert len(rerun_conformance) == 24
    assert Counter(
        row["current_rerun_file"]
        for row in rerun_conformance
        if row["all_three_stored_metrics_exact_on_current_rerun"] == "True"
    ) == {
        "native_current_mean.json": 7,
        "native_current_seed0.json": 4,
        "native_current_seed42.json": 6,
    }
    assert {row["information_ratio_display_precision_match"] for row in rerun_conformance} == {"False"}
    assert {row["paper_result_credit"] for row in rerun_conformance} == {"False"}
    assert len(alignment) == 1
    assert alignment[0]["released_notebook_exact_series_construction_operational"] == "False"
    assert alignment[0]["released_trade_unique_dates"] == "1257"
    assert alignment[0]["released_notebook_asset_values_after_assets_1_slice"] == "1256"
    assert alignment[0]["paper_time_benchmark_snapshot"] == "False"
    assert alignment[0]["paper_result_credit"] == "False"
    assert benchmark["canonical_close_sha256"] == (audit.NDX_BENCHMARK_CANONICAL_CLOSE_SHA256)
    assert benchmark["valid_close_observations"] == 937
    assert benchmark["raw_responses_byte_identical"] is False
    assert len(benchmark["raw_response_sha256"]) == 2
    assert len(historical_notebooks) == 9
    assert {row["stored_metric_entries"] for row in historical_notebooks} == {"24"}
    assert {row["normalized_metric_output_sha256"] for row in historical_notebooks} == {
        audit.HISTORICAL_NOTEBOOK_OUTPUT_SIGNATURE_SHA256
    }
    assert {row["paper_numeric_tokens_matched"] for row in historical_notebooks} == {"0"}
    assert len(historical_logs) == 15
    assert sum(bool(row["exact_released_checkpoint_basenames"]) for row in historical_logs) == 10
    assert sum(bool(row["exact_paper_relevant_checkpoint_basenames"]) for row in historical_logs) == 5
    assert {row["contains_paper_evaluation_metric_labels"] for row in historical_logs} == {"False"}
    assert len(fork_repositories) == 81
    assert sum(row["accessible_via_git"] == "True" for row in fork_repositories) == 80
    assert len(fork_refs) == 82
    assert len(fork_heads) == 10
    assert sum(row["relation_to_official_history"] == "divergent" for row in fork_heads) == 5
    assert sum(row["new_metric_output_notebook_blobs"] == "1" for row in fork_heads) == 1
    assert len(fork_commits) == 69
    assert sum(row["introduced_community_metric_notebook_blob"] == "True" for row in fork_commits) == 1
    assert len(fork_paths) == 84
    assert sum(row["community_metric_output_notebook"] == "True" for row in fork_paths) == 1
    assert len(fork_notebooks) == 2
    assert {row["stored_metric_entries"] for row in fork_notebooks} == {"0", "33"}
    assert len(fork_table) == 36
    assert sum(row["status"] == "postpaper_community_stored_output_mismatch" for row in fork_table) == 30
    assert fork_summary["postpaper_adaptation_changes_native_objective_or_protocol"] is True
    assert fork_summary["postpaper_adaptation_requires_unreleased_local_pkg_or_runtime_services"] is True
    assert fork_summary["postpaper_adaptation_committed_result_or_checkpoint_artifacts"] == 0
    assert fork_summary["paper_result_credit"] is False
    assert history["reachable_commits"] == 36
    assert history["reachable_object_counts"] == {"blob": 73, "commit": 36, "tree": 36}
    assert history["official_history_tips"] == [audit.CURRENT_COMMIT]
    assert history["fork_refs_excluded_from_official_history"] is True
    assert history["paper_result_credit"] is False
    assert {row["paper_result_credit"] for row in table} == {"False"}
    assert native["source_revision"] == audit.CURRENT_COMMIT
    assert set(native["runs"]) == {
        "native_seed0.json",
        "native_seed42.json",
        "native_mean.json",
    }
    assert all(len(run["results"]) == 8 for run in native["runs"].values())
    assert native["current_rerun_conformance"]["configurations_total"] == 24
    assert native["current_rerun_conformance"]["configurations_exact"] == 17
    assert native["current_rerun_conformance"]["information_ratio_display_precision_matches"] == 0
    assert native["paper_result_credit"] is False
    assert set(current_runs) == {
        "native_current_seed0.json",
        "native_current_seed42.json",
        "native_current_mean.json",
    }
    expected_runtime = {
        "numpy": "2.3.5",
        "pandas": "2.2.3",
        "platform_machine": "x86_64",
        "python": "3.12.8",
        "torch": "2.10.0+cu128",
        "torch_num_threads": 8,
    }
    assert {tuple(run["runtime"].items()) for run in current_runs.values()} == {tuple(expected_runtime.items())}
    assert {run["benchmark"]["canonical_close_sha256"] for run in current_runs.values()} == {
        audit.NDX_BENCHMARK_CANONICAL_CLOSE_SHA256
    }
    assert all(len(run["results"]) == 8 for run in current_runs.values())
    assert {
        result["benchmark_common_dates"] for run in current_runs.values() for result in run["results"].values()
    } == {936}
    assert {
        result["benchmark_aligned_returns"] for run in current_runs.values() for result in run["results"].values()
    } == {935}
    assert {
        result["released_notebook_alignment_reused"]
        for run in current_runs.values()
        for result in run["results"].values()
    } == {False}
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_primary_sources_when_available() -> None:
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_source")
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_paper")
    artifacts = Path("/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_artifacts")
    fork_snapshot = paper / "public_fork_snapshot.json"
    if not source.exists() or not paper.exists() or not artifacts.exists() or not fork_snapshot.exists():
        return
    assert str(audit.run_git(source, "rev-parse", "HEAD")).strip() == audit.CURRENT_COMMIT
    assert audit.sha256(paper / "paper.pdf") == audit.PAPER_PDF_SHA256
    assert audit.sha256(paper / "source.tar") == audit.PAPER_SOURCE_SHA256
    assert audit.sha256(paper / "arxiv_api.xml") == audit.ARXIV_API_SHA256
    assert len(audit.source_inventory(source)) == 47
    commits, notebooks, logs, history = audit.public_source_history(source, paper)
    assert len(commits) == 36
    assert len(notebooks) == 9
    assert len(logs) == 15
    assert history["independently_regenerated_paper_results"] == 0
    assert history["paper_result_credit"] is False
    forks = audit.public_fork_audit(source, fork_snapshot)
    assert len(forks["repositories"]) == 81
    assert len(forks["refs"]) == 82
    assert len(forks["heads"]) == 10
    assert len(forks["commits"]) == 69
    assert len(forks["paths"]) == 84
    assert len(forks["notebooks"]) == 2
    assert len(forks["community_table_conformance"]) == 36
    assert forks["summary"]["native_paper_result_artifacts_found"] == 0
    native = audit.validate_native_inputs(artifacts)
    assert len(native["input_artifacts"]) == 11
    reruns = audit.validate_current_native_reruns(
        native,
        artifacts,
        ROOT / "paper_runs/paper_replication_audits/finrl_deepseek",
    )
    assert reruns["configurations_total"] == 24
    assert reruns["configurations_exact"] == 17
    assert reruns["protocols_all_configurations_exact"] == 0
    assert reruns["information_ratio_display_precision_matches"] == 0
    assert reruns["paper_result_credit"] is False
