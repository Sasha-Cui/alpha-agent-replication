from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_alphamemo_paper.py"
SPEC = importlib.util.spec_from_file_location("alphamemo_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)

REAL_DRIVER = ROOT / "scripts/run_alphamemo_real_data_probe.py"
REAL_SPEC = importlib.util.spec_from_file_location("alphamemo_real_data_probe", REAL_DRIVER)
assert REAL_SPEC and REAL_SPEC.loader
real_probe = importlib.util.module_from_spec(REAL_SPEC)
sys.modules[REAL_SPEC.name] = real_probe
REAL_SPEC.loader.exec_module(real_probe)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_targets_cover_all_numeric_experimental_cells() -> None:
    rows = audit.paper_numeric_rows()
    assert len(rows) == 484
    assert Counter(row["paper_table"] for row in rows) == {
        2: 140,
        3: 48,
        4: 6,
        5: 182,
        6: 80,
        7: 8,
        8: 5,
        9: 15,
    }
    assert Counter(row["cell_role"] for row in rows) == {
        "result": 474,
        "configuration": 10,
    }
    assert len(
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
    ) == 484


def test_cross_table_identities_are_only_internal_checks() -> None:
    rows = audit.paper_internal_identities()
    assert len(rows) == 69
    assert {row["absolute_difference"] for row in rows} == {0.0}
    assert {row["status"] for row in rows} == {
        "paper_internal_identity_match_not_independent_reproduction"
    }
    assert Counter((row["left_table"], row["right_table"]) for row in rows) == {
        (2, 3): 16,
        (2, 5): 28,
        (3, 5): 24,
        (7, 8): 1,
    }


def test_committed_audit_preserves_the_native_result_boundary() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/alphamemo"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "tables_2_9_conformance.csv")
    identities = read_csv(output / "paper_internal_identities.csv")
    source = read_csv(output / "source_mechanism_conformance.csv")
    formulas = read_csv(output / "representative_factor_parser_audit.csv")
    inventory = read_csv(output / "released_source_inventory.csv")
    component = json.loads((output / "native_synthetic_component.json").read_text(encoding="utf-8"))
    history = json.loads((output / "official_source_history.json").read_text(encoding="utf-8"))
    fork_branches = read_csv(output / "public_fork_branch_ref_snapshot.csv")
    fork_heads = read_csv(output / "public_fork_unique_head_inventory.csv")
    fork_census = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))
    current_data = read_csv(output / "alphamemo_current_data_snapshot.csv")
    paper_environment = read_csv(output / "alphamemo_paper_environment.csv")
    real_metrics = read_csv(output / "alphamemo_real_data_metrics.csv")
    native_stages = read_csv(output / "alphamemo_native_stage_audit.csv")
    real = json.loads((output / "alphamemo_real_data_probe.json").read_text(encoding="utf-8"))

    assert manifest["overall_status"] == (
        "not_reproduced_native_current_data_pipeline_component_only"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_table_cells_total"] == 484
    assert manifest["paper_numeric_result_cells_total"] == 474
    assert manifest["native_paper_result_cells_reproduced"] == 0
    assert manifest["paper_result_cells_unavailable"] == 474
    assert manifest["active_official_runner_configuration_cells_matched"] == 4
    assert manifest["paper_pairwise_internal_identity_matches"] == 69
    assert manifest["native_source_tests_passed"] == 1
    assert manifest["paper_declared_python_environment_reproduced"] is True
    assert manifest["paper_declared_python_version"] == "3.11.11"
    assert manifest["paper_declared_environment_package_count"] == 202
    assert manifest["native_current_data_builder_snapshot_replayed"] is True
    assert manifest["native_current_data_trading_days"] == 2511
    assert manifest["native_current_data_market_assets"] == 14
    assert manifest["native_current_data_benchmark_series"] == 1
    assert manifest["native_current_data_raw_search_completed"] is True
    assert manifest["native_current_data_raw_export_failed_template_root"] is True
    assert manifest["native_current_data_raw_qrun_failed_nonexecutable"] is True
    assert manifest["native_current_data_compatible_end_to_end_runs"] == 2
    assert manifest["native_current_data_search_byte_identical"] is True
    assert manifest["native_current_data_valid_factor_evaluations"] == 12
    assert manifest["native_current_data_admitted_factors"] == 0
    assert manifest["native_current_data_selected_backtest_factors"] == 12
    assert manifest["native_current_data_exported_metric_values"] == 19
    assert manifest["native_current_data_metrics_repeat_atol_1e_12"] is True
    assert manifest["native_current_data_max_reported_repeat_difference"] == 0.0
    assert manifest["native_current_data_replay_llm_calls"] == 0
    assert manifest["native_current_data_replay_network_attempts"] == 0
    assert manifest["native_current_data_probe_paper_configuration"] is False
    assert manifest["native_current_data_probe_paper_result_credit"] is False
    assert manifest["source_history_reachable_commits"] == 2
    assert manifest["source_history_root_commits"] == 1
    assert manifest["source_history_local_branches"] == 1
    assert manifest["source_history_remote_tracking_branches"] == 1
    assert manifest["source_history_tags"] == 0
    assert manifest["source_history_root_to_head_only_readme_changed"] is True
    assert manifest["source_history_native_result_artifacts_found"] is False
    assert manifest["public_fork_census_date"] == "2026-08-14"
    assert manifest["public_forks_reported_by_github_rest"] == 1
    assert manifest["public_forks_accessible_via_graphql"] == 1
    assert manifest["public_fork_branch_refs_audited"] == 1
    assert manifest["public_fork_unique_heads_audited"] == 1
    assert manifest["public_fork_divergent_heads_audited"] == 1
    assert manifest["public_fork_paper_coauthor_heads_audited"] == 1
    assert manifest["public_fork_coauthor_provenance_corroborated"] is True
    assert manifest["public_fork_native_result_artifacts_found"] is False
    assert manifest["public_fork_paper_result_credit"] is False
    assert manifest["root_readme_configuration_recovered"] is True
    assert manifest["root_readme_stable_data_snapshot_warning_recovered"] is True
    assert manifest["native_synthetic_smoke_deterministic"] is True
    assert manifest["native_synthetic_smoke_memory_policy_branch_exercised"] is False
    assert manifest["native_synthetic_smoke_paper_result_reproduction"] is False
    assert manifest["native_released_strategies_diagnosed"] == 7
    assert manifest["native_active_strategy_diagnostic_runs"] == 14
    assert manifest["native_active_strategy_diagnostics_deterministic"] is True
    assert manifest["native_active_memory_branches_exercised"] is True
    assert manifest["native_active_strategy_diagnostics_paper_configuration"] is False
    assert manifest["native_active_strategy_diagnostics_paper_result_reproduction"] is False
    assert manifest["released_structured_and_graph_are_aliases"] is True
    assert manifest["published_representative_formulas_native_parser_executable"] == 5
    assert manifest["published_representative_formula_metrics_reproduced"] == 0
    assert manifest["paper_ast_diff_mechanism_implemented_faithfully"] is False
    assert manifest["paper_parent_context_implemented_faithfully"] is False
    assert manifest["audit_used_external_yahoo_api_to_acquire_frozen_current_snapshot"] is True
    assert manifest["real_data_replay_called_llm_or_external_data_api"] is False
    assert manifest["audit_called_llm_or_external_data_api"] is True

    assert Counter(row["status"] for row in conformance) == {
        "unavailable_missing_native_result_path": 474,
        "configuration_match_active_official_runner": 4,
        "configuration_not_reproduced_by_released_diagnostic_runner": 6,
    }
    assert len(identities) == 69
    assert len(source) == 39
    assert len(formulas) == 5
    assert {row["native_parser_executable"] for row in formulas} == {"True"}
    assert {row["paper_metric_reproduced"] for row in formulas} == {"False"}
    assert len(inventory) == 49
    assert len(fork_branches) == 1
    assert fork_branches[0]["repository"] == audit.PUBLIC_FORK_REPOSITORY
    assert fork_branches[0]["head_commit"] == audit.PUBLIC_FORK_HEAD
    assert fork_branches[0]["head_author_name"] == "Fengxiang He"
    assert len(fork_heads) == 1
    assert fork_heads[0]["extra_commit_count_beyond_official_head"] == "1"
    assert fork_heads[0]["extra_changed_paths"] == "README.md"
    assert fork_heads[0]["paper_author_identity_match"] == "True"
    assert fork_heads[0]["classification"] == "paper_coauthor_provenance_only_readme_change"
    assert fork_heads[0]["paper_result_credit"] == "False"
    assert fork_census["paper_coauthor_authored_divergent_heads"] == 1
    assert fork_census["coauthor_identity"] == "Fengxiang He"
    assert fork_census["coauthor_is_named_paper_author"] is True
    assert fork_census["coauthor_fork_only_replaces_placeholder_bibtex_author_metadata"] is True
    assert fork_census[
        "native_input_trajectory_factor_pool_prediction_return_or_metric_paths_discovered"
    ] == 0
    assert fork_census["exact_paper_result_table_or_figure_paths_discovered"] == 0
    assert fork_census["paper_result_credit"] is False

    assert component["upstream_tests_passed"] == 1
    assert component["synthetic_smoke_runs"] == 2
    assert component["synthetic_smoke_deterministic"] is True
    assert component["synthetic_smoke_sha256"] == (
        "82b09f8e2dbc77be1553295fad848b17354027b40fcd2e70c964be767f3955c1"
    )
    assert component["synthetic_smoke_summary"]["n_effective"] == 5
    assert component["synthetic_smoke_configured_warmup"] == 30
    assert component["synthetic_smoke_max_batch_start_step"] == 8
    assert component["synthetic_smoke_memory_policy_branch_exercised"] is False
    active = component["active_strategy_diagnostic"]
    assert active["strategies"] == [
        "alphamemo",
        "sspm",
        "veto",
        "structured",
        "graph",
        "gp",
        "random",
    ]
    assert active["runs_per_strategy"] == 2
    assert active["all_deterministic"] is True
    assert active["memory_branch_counts"] == {
        "alphamemo": {"motif_prior": 20, "random_or_warmup": 12},
        "sspm": {"lambda_positive": 28, "lambda_zero": 4},
        "veto": {"apv_resample": 24, "warmup": 8},
    }
    assert active["structured_and_graph_alias_trajectory_equal"] is True
    assert len(active["rows"]) == 7
    assert {row["deterministic"] for row in active["rows"]} == {True}
    assert {row["paper_result_reproduction"] for row in active["rows"]} == {False}
    assert active["paper_configuration"] is False
    assert active["paper_result_reproduction"] is False
    assert component["paper_result_reproduction"] is False

    assert len(current_data) == 93
    assert sum(int(row["size_bytes"]) for row in current_data) == 920_339
    assert len(paper_environment) == 202
    environment = {row["package"]: row["version"] for row in paper_environment}
    assert {key: environment[key] for key in real_probe.EXPECTED_DIRECT_PACKAGES} == (
        real_probe.EXPECTED_DIRECT_PACKAGES
    )
    assert len(real_metrics) == 19
    assert max(float(row["absolute_difference"]) for row in real_metrics) <= 1e-12
    assert {row["paper_result_credit"] for row in real_metrics} == {"False"}
    assert len(native_stages) == 6
    assert {row["paper_result_credit"] for row in native_stages} == {"False"}

    assert real["source_commit"] == audit.SOURCE_COMMIT
    assert real["source_unmodified"] is True
    assert real["environment"]["python"] == "3.11.11"
    assert real["environment"]["package_count"] == 202
    assert real["frozen_current_data"]["provider_file_count"] == 93
    assert real["frozen_current_data"]["provider_total_bytes"] == 920_339
    assert real["frozen_current_data"]["paper_time_snapshot"] is False
    assert real["frozen_current_data"]["point_in_time_2025_membership"] is False
    assert real["raw_execution"]["returncode"] != 0
    assert real["raw_execution"]["search_completed"] is True
    assert real["raw_execution"]["paper_result_credit"] is False
    compatible = real["compatible_execution"]
    assert compatible["runs"] == 2
    assert compatible["search_byte_identical"] is True
    assert compatible["selected_formulas_byte_identical"] is True
    assert compatible["search_summary"]["n_ok"] == 12
    assert compatible["search_summary"]["n_effective"] == 0
    assert compatible["n_selected_factors"] == 12
    assert compatible["metric_count"] == 19
    assert compatible["metric_reporting_decimal_places"] == 12
    assert compatible["expected_metrics_atol_1e_12"] is True
    assert compatible["metrics_repeat_atol_1e_12"] is True
    assert compatible["max_reported_repeat_difference"] == 0.0
    assert compatible["network_attempts"] == []
    assert compatible["llm_calls"] == 0
    assert compatible["paper_configuration"] is False
    assert compatible["paper_result_credit"] is False
    assert real["paper_result_cells_reproduced"] == 0

    assert history["is_shallow_repository"] is False
    assert history["reachable_commit_count"] == 2
    assert history["root_commit_count"] == 1
    assert history["local_branch_count"] == 1
    assert history["remote_tracking_branch_count"] == 1
    assert history["tag_count"] == 0
    assert history["unreachable_object_output_empty"] is True
    assert [item["commit"] for item in history["commits"]] == [
        audit.SOURCE_ROOT_COMMIT,
        audit.SOURCE_COMMIT,
    ]
    assert history["root_to_head_changed_paths"] == ["M\tREADME.md"]
    assert history["root_tree_file_count"] == 49
    assert history["head_tree_file_count"] == 49
    assert history["root_readme_sha256"] == audit.SOURCE_ROOT_README_SHA256
    assert history["root_readme_recovered_configuration"] == {
        "train": "2016-01-01 to 2020-12-31",
        "validation": "2021-01-01 to 2021-12-31",
        "test_and_backtest": "2022-01-01 to 2025-12-26",
        "strategy": "alphamemo",
        "budget": 500,
        "batch_size": 10,
        "label_days": 20,
        "warmup": 200,
        "memory_weight": 0.05,
        "motif_sample_size": 4,
        "random_motif_prob": 0.35,
        "max_factors": 50,
    }
    assert history["historical_native_result_artifacts_found"] is False
    assert history["paper_result_reproduction"] is False

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_source_static_checks_when_source_is_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_source")
    if not source_root.exists():
        return
    rows = audit.source_conformance(source_root)
    findings = {row["dimension"]: row for row in rows}
    assert audit.git_head(source_root) == audit.SOURCE_COMMIT
    history = audit.source_history_audit(source_root)
    assert history["reachable_commit_count"] == 2
    assert history["root_to_head_changed_paths"] == ["M\tREADME.md"]
    assert history["root_readme_recovered_configuration"]["budget"] == 500
    assert findings["paper_split"]["status"] == "configuration_match"
    assert findings["admission_quality_threshold"]["status"] == "mismatch_active_runner"
    assert findings["ast_diff_motif"]["status"] == "mismatch"
    assert findings["parent_context"]["status"] == "mismatch"
    assert findings["native_output_snapshot"]["status"] == "missing"
    assert findings["qlib_template_resolution"]["status"] == "broken_active_path"
    assert findings["qlib_backtest_entrypoint_mode"]["status"] == "broken_active_path"
    assert findings["factor_admission_to_backtest"]["status"] == "mismatch_active_runner"
    assert findings["released_strategy_aliases"]["status"] == "aliases_not_distinct_methods"
    assert findings["released_smoke_memory_branch"]["status"] == "pre_memory_component_only"


def test_public_fork_provenance_when_bouchet_clone_is_available() -> None:
    fork_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_fork")
    if not fork_root.exists():
        return
    branches, heads, summary = audit.public_fork_audit(fork_root)
    assert len(branches) == len(heads) == 1
    assert summary["paper_coauthor_authored_divergent_heads"] == 1
    assert summary["exact_paper_result_table_or_figure_paths_discovered"] == 0
    assert summary["paper_result_credit"] is False


def test_real_data_probe_inputs_when_bouchet_assets_are_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_source")
    source_python = Path(audit.DEFAULT_PAPER_SOURCE_PYTHON)
    provider = Path(audit.DEFAULT_REAL_DATA_PROVIDER)
    qlib_source = Path(audit.DEFAULT_QLIB_SOURCE)
    if not all(path.exists() for path in (source_root, source_python, provider, qlib_source)):
        return
    provider_rows, env_rows, summary = real_probe.validate_inputs(
        source_root, source_python, provider, qlib_source
    )
    assert len(provider_rows) == real_probe.PROVIDER_FILE_COUNT
    assert len(env_rows) == real_probe.ENVIRONMENT_PACKAGE_COUNT
    assert summary["manifest_sha256"] == real_probe.ENVIRONMENT_MANIFEST_SHA256
