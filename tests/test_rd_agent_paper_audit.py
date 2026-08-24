from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_rd_agent_paper.py"
SPEC = importlib.util.spec_from_file_location("rd_agent_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_committed_table_census_is_complete_and_fail_closed() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/rd_agent"
    rows = read_csv(output / "paper_numeric_table_conformance.csv")
    unique = read_csv(output / "paper_unique_measurement_conformance.csv")
    assert len(rows) == 534
    assert Counter(row["paper_table"] for row in rows) == {
        "Table 2 main MLE-Bench": 108,
        "Table 3 research ablation": 30,
        "Table 4 RAG": 8,
        "Table 5 runtime and GPU": 13,
        "Table 6 closed-source comparison": 27,
        "Table 7 raw main runs": 36,
        "Table 8 GPT-5 costs": 12,
        "Table 9 per-competition medals": 300,
    }
    assert len(unique) == 526
    assert Counter(int(row["display_occurrences"]) for row in unique) == {
        1: 521,
        2: 3,
        3: 1,
        4: 1,
    }
    assert {row["paper_result_credit"] for row in rows + unique} == {"False"}


def test_v1_is_not_silently_merged_with_rewritten_v2_protocol() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/rd_agent"
    v1 = read_csv(output / "paper_v1_result_inventory.csv")
    summary = read_csv(output / "paper_version_summary.csv")
    assert len(v1) == 32
    assert {row["v2_disposition"] for row in v1} == {
        "superseded_noncomparable_protocol_24h_to_12h_models_metrics_and_seeds_changed"
    }
    assert summary[0]["runtime_hours"] == "24"
    assert summary[0]["reported_error"] == "standard deviation"
    assert summary[1]["runtime_hours"] == "12"
    assert summary[1]["reported_error"] == "SEM"
    assert summary[1]["result_authority"] == "True"


def test_source_components_are_not_promoted_to_reported_run_credit() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/rd_agent"
    mechanisms = read_csv(output / "released_source_mechanism_conformance.csv")
    configs = read_csv(output / "released_source_config_conformance.csv")
    figures = read_csv(output / "paper_figure_series_inventory.csv")
    assert len(mechanisms) == 21
    assert {row["required_source_tokens_found"] for row in mechanisms} == {"True"}
    assert {row["reported_run_configuration_or_trace_released"] for row in mechanisms} == {"False"}
    assert {row["paper_mechanism_execution_credit"] for row in mechanisms} == {"False"}
    assert len(configs) == 30
    assert {row["verified_for_reported_run"] for row in configs} == {"False"}
    assert len(figures) == 24
    assert {row["paper_result_credit"] for row in figures} == {"False"}
    assert {row["figure"].split(" / ")[0] for row in figures} == {
        "Figure 1", "Figure 3", "Figure 4", "Figure 5"
    }


def test_committed_native_record_is_component_only() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/rd_agent"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((output / "native_execution.json").read_text(encoding="utf-8"))
    freeze = (output / "paper_era_environment_freeze.txt").read_text(
        encoding="utf-8"
    )
    assert manifest["overall_status"] == (
        "paper_specification_source_and_full_history_audited_zero_native_results_"
        "missing_attributable_run_artifacts"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_table_cells_total"] == 534
    assert manifest["paper_unique_numeric_measurements_total"] == 526
    assert manifest["paper_numeric_table_cells_with_paper_result_credit"] == 0
    assert manifest["paper_mechanisms_with_source_implementation"] == 21
    assert manifest["paper_mechanisms_verified_as_executed_in_reported_run"] == 0
    assert manifest["paper_configurations_verified_for_reported_run"] == 0
    assert manifest["public_source_history_remote_refs"] == 231
    assert manifest["public_source_history_reachable_commits"] == 3384
    assert manifest["public_source_history_unique_changed_paths"] == 3188
    assert manifest["public_source_history_keyword_paths"] == 329
    assert manifest["public_source_history_artifact_candidates_inspected"] == 15
    assert manifest["public_source_history_attributable_paper_run_artifacts"] == 0
    assert manifest["paper_result_cells_reproduced_from_public_history"] == 0
    assert manifest["paper_era_data_science_and_kaggle_python_files_compiled"] == 233
    assert manifest["paper_era_scheduler_component_executed"] is True
    assert manifest["paper_era_interaction_kernel_executed"] is True
    assert manifest["paper_era_dependency_environment_reproduced"] is True
    assert manifest["paper_era_exact_historical_dependency_versions_recovered"] is False
    assert manifest["paper_era_source_modules_imported"] == 192
    assert manifest["paper_era_upstream_offline_tests_passed"] == 2
    assert manifest["paper_era_mle_bench_container_reproduced"] is False
    assert native["full_native_paper_execution_attempted"] is False
    assert native["paper_source_compilation"]["exit_codes"] == [0, 0]
    assert native["paper_source_compilation"]["produced_pdf_pages"] == 33
    assert native["released_source_component_execution"]["paper_result_credit"] is False
    interaction = native["released_source_component_execution"]["native_interaction_kernel_execution"]
    assert interaction["passed"] is True
    assert interaction["best_history"] == "history_high"
    assert interaction["paper_result_credit"] is False
    environment = native["released_source_component_execution"][
        "dependency_environment"
    ]
    assert environment["dependency_environment_reproduced"] is True
    assert environment["exact_historical_dependency_versions_recovered"] is False
    assert environment["dependency_release_cutoff_utc"] == audit.SOURCE_V2_COMMIT_UTC
    assert environment["dependency_freeze_sha256"] == audit.PAPER_ENV_FREEZE_SHA256
    assert environment["dependency_freeze_lines"] == 243
    assert environment["pip_check"] == "No broken requirements found."
    assert environment["selected_source_modules"] == 192
    assert environment["imported_source_modules"] == 192
    assert environment["module_import_failures"] == []
    assert environment["upstream_offline_tests_passed"] == 2
    assert environment["upstream_offline_test_runs"] == 2
    assert environment["litellm_local_model_cost_map"] is True
    assert environment["network_attempts"] == []
    assert environment["torch_optional_extra_installed"] is True
    assert environment["torch_version"] == "2.4.0+cpu"
    assert environment["mle_bench_container_reproduced"] is False
    assert environment["mle_bench_dockerfile_uses_unpinned_live_clone"] is True
    assert environment["rdagent_direct_url"]["vcs_info"]["commit_id"] == (
        audit.SOURCE_V2_COMMIT
    )
    assert len(freeze.splitlines()) == 243
    assert hashlib.sha256(freeze.encode()).hexdigest() == (
        audit.PAPER_ENV_FREEZE_SHA256
    )
    assert native["paper_result_credit"] is False
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_complete_public_history_bounds_developmental_outputs_without_credit() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/rd_agent"
    history = json.loads((output / "public_source_history.json").read_text(encoding="utf-8"))
    paths = read_csv(output / "public_source_history_path_inventory.csv")
    artifacts = read_csv(output / "public_source_history_artifact_candidates.csv")
    assert history["remote_refs"] == 231
    assert history["reachable_commits"] == 3384
    assert history["unique_historical_changed_paths"] == 3188
    assert history["keyword_paths"] == 329
    assert history["bounded_artifact_candidates_inspected"] == 15
    assert history["attributable_published_run_artifacts"] == 0
    assert all(history["checks"].values())
    assert len(paths) == 3188
    assert sum(
        row[
            "contains_result_output_log_trace_checkpoint_submission_or_score_keyword"
        ]
        == "True"
        for row in paths
    ) == 329
    assert sum(row["selected_artifact_candidate"] == "True" for row in paths) == 15
    assert len(artifacts) == 15
    assert Counter(row["artifact_role"] for row in artifacts) == {
        "post_v2_single_competition_command_without_output": 1,
        "pre_v1_three_competition_researcher_diagnostic": 3,
        "pre_v1_automated_evaluation_metadata": 1,
        "post_v2_unrelated_RL_benchmark": 1,
        "between_v1_v2_39_competition_runner_ratio_diagnostic": 5,
        "between_v1_v2_debug_LLM_pickle_not_deserialized": 2,
        "pre_v1_single_example_solution_artifact": 2,
    }
    assert {
        row["attributable_to_published_75_competition_three_seed_run"]
        for row in artifacts
    } == {"False"}
    assert {row["paper_result_credit"] for row in artifacts + paths} == {"False"}


def test_broken_trace_links_and_scope_boundary_are_explicit() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/rd_agent"
    links = read_csv(output / "released_result_link_status.csv")
    checks = read_csv(output / "paper_internal_and_source_checks.csv")
    assert len(links) == 2
    assert {row["status"] for row in links} == {
        "broken_redirect_to_generic_bing_no_trace_artifact"
    }
    assert all("bing.com" in row["resolved_url"] for row in links)
    assert any(row["check"] == "quant mapping boundary" and row["status"] == "correct_scope_boundary" for row in checks)
    assert Counter(row["status"] for row in checks)["contradiction"] >= 4


def test_pinned_primary_sources_when_available() -> None:
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/rd_agent_source")
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/rd_agent_paper")
    if not source.exists() or not paper.exists():
        return
    audit.validate_inputs(source, paper)
    rows = audit.paper_table_rows(paper)
    assert len(rows) == 534
    assert len(audit.unique_measurement_rows(rows)) == 526
    assert len(audit.parse_baseline_medal_rows(paper)) == 75
    mechanisms = audit.mechanism_rows(source)
    assert len(mechanisms) == 21
    assert all(row["required_source_tokens_found"] for row in mechanisms)
    snapshots = audit.source_snapshot_rows(source)
    assert [row["tracked_files"] for row in snapshots] == [536, 609, 907]
    history, paths, artifacts = audit.public_source_history(source)
    assert history["reachable_commits"] == 3384
    assert len(paths) == 3188
    assert len(artifacts) == 15
