from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_finagent_paper.py"
SPEC = importlib.util.spec_from_file_location("finagent_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_committed_result_census_is_complete_and_fail_closed() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/finagent"
    table = read_csv(output / "paper_numeric_table_conformance.csv")
    figures = read_csv(output / "paper_figure_display_inventory.csv")
    assert len(table) == 959
    assert Counter(row["paper_table"] for row in table) == {
        "Table 4 main comparison": 242,
        "Appendix Table 7 panel 1": 335,
        "Appendix Table 7 panel 2": 334,
        "Table 5 ablation": 48,
    }
    assert len(figures) == 102
    assert Counter(row["paper_figure"] for row in figures) == {
        "Figure 4 cumulative return": 66,
        "Figure 5 component ablation": 4,
        "Figure 5 retrieval/diversification": 3,
        "Appendix qualitative/performance cases": 29,
    }
    assert {row["paper_result_credit"] for row in table + figures} == {"False"}
    versions = read_csv(output / "official_paper_version_inventory.csv")
    lineage = read_csv(output / "official_paper_result_lineage.csv")
    assert len(versions) == 3
    assert [row["numeric_table_cells"] for row in versions] == ["768", "768", "959"]
    assert [row["pdf_pages"] for row in versions] == ["46", "46", "43"]
    assert {row["figure_display_units"] for row in versions} == {"102"}
    assert {row["result_figure_assets_byte_identical_to_v3"] for row in versions} == {"True"}
    assert [row["public_source_available_at_submission"] for row in versions] == [
        "False",
        "False",
        "True",
    ]
    assert len(lineage) == 966
    assert Counter(row["status"] for row in lineage) == {
        "unchanged_v1_through_v3": 679,
        "display_precision_only_change_in_v3": 55,
        "numeric_value_revised_in_v3": 27,
        "added_in_v3": 198,
        "removed_in_v3": 7,
    }
    assert {row["paper_result_credit"] for row in lineage} == {"False"}


def test_committed_manifest_keeps_document_and_experiment_credit_separate() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/finagent"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((output / "native_execution.json").read_text(encoding="utf-8"))
    freeze = (output / "paper_era_environment_freeze.txt").read_text(
        encoding="utf-8"
    )
    assert manifest["overall_status"] == (
        "substantial_author_linked_source_but_zero_of_1061_published_result_units_reproduced"
    )
    assert manifest["replication_tier"] == (
        "R3_runnable_component_environment_no_paper_result_reproduction"
    )
    assert manifest["paper_document_reproduced"] is True
    assert manifest["full_paper_reproduced"] is False
    assert manifest["published_result_display_units_total"] == 1061
    assert manifest["published_result_display_units_reproduced"] == 0
    assert manifest["paper_result_credit"] is False
    assert manifest["official_arxiv_versions_audited"] == 3
    assert manifest["arxiv_v1_numeric_table_cells"] == 768
    assert manifest["arxiv_v2_numeric_table_cells"] == 768
    assert manifest["arxiv_v3_numeric_table_cells"] == 959
    assert manifest["official_version_unique_table_cell_ids"] == 966
    assert manifest["official_version_numeric_value_revisions_in_v3"] == 27
    assert manifest["official_version_display_precision_only_changes_in_v3"] == 55
    assert manifest["official_version_cell_ids_added_in_v3"] == 198
    assert manifest["official_version_cell_ids_removed_in_v3"] == 7
    assert manifest["official_versions_result_figure_assets_byte_identical"] is True
    assert manifest["official_versions_with_public_source_at_submission"] == 1
    assert manifest["public_fork_census_date"] == "2026-08-14"
    assert manifest["github_rest_reported_public_forks"] == 26
    assert manifest["graphql_accessible_public_forks"] == 26
    assert manifest["public_fork_accessibility_gap"] == 0
    assert manifest["public_fork_branch_refs_examined"] == 30
    assert manifest["public_fork_unique_heads_examined"] == 7
    assert manifest["public_fork_divergent_heads_examined"] == 5
    assert manifest["public_fork_divergent_extra_commits_examined"] == 27
    assert manifest["public_fork_divergent_changed_paths_examined"] == 93
    assert manifest["public_fork_author_attributed_divergent_heads"] == 0
    assert manifest["public_fork_new_final_unique_blobs_examined"] == 24
    assert manifest["public_fork_native_agent_result_paths_discovered"] == 0
    assert manifest["public_fork_exact_paper_result_paths_discovered"] == 0
    assert manifest["public_fork_paper_result_credit"] is False
    assert native["paper_source_compilation"]["exit_code"] == 0
    assert native["paper_source_compilation"]["compiled_pages"] == 43
    assert native["paper_source_compilation"]["paper_result_credit"] is False
    assert native["full_native_system_execution_attempted"] is False
    assert manifest["paper_era_dependency_environment_reproduced"] is True
    assert manifest["paper_era_exact_historical_dependency_versions_recovered"] is False
    assert manifest["paper_era_entrypoint_help_passed"] is True
    assert manifest["paper_era_core_modules_imported"] == 65
    assert manifest["paper_era_controlled_native_component_runs"] == 2
    assert manifest["paper_era_future_state_exposure_observed"] is True
    assert manifest["paper_era_released_metric_functions_executed"] == 7
    assert native["entrypoint_help_probe"]["exit_code"] == 0
    assert native["entrypoint_help_probe"]["passed"] is True
    environment = native["dependency_environment"]
    assert environment["dependency_environment_reproduced"] is True
    assert environment["exact_historical_dependency_versions_recovered"] is False
    assert environment["dependency_release_cutoff_utc"] == audit.SOURCE_CURRENT_DATE_UTC
    assert environment["author_requirements_commit"] == audit.SOURCE_CURRENT_COMMIT
    assert environment["author_requirements_sha256"] == audit.SOURCE_REQUIREMENTS_SHA256
    assert environment["author_requirements_only_postpaper_change"] is True
    assert environment["pip_check"] == "No broken requirements found."
    assert environment["dependency_freeze_sha256"] == audit.PAPER_ENV_FREEZE_SHA256
    assert environment["dependency_freeze_lines"] == 148
    assert environment["entrypoint_help_runs"] == 2
    assert environment["selected_core_modules"] == 65
    assert environment["imported_core_modules"] == 65
    assert environment["module_import_failures"] == []
    assert environment["network_attempts"] == []
    assert environment["pandas_ta_historical_version"] == "0.3.14b0"
    assert environment["pandas_ta_unaffiliated_mirror_commit"] == (
        audit.PANDAS_TA_MIRROR_COMMIT
    )
    assert environment["pandas_ta_original_pypi_distribution_available"] is False
    assert environment["source_tests_shipped"] == 0
    assert environment["controlled_native_component_runs"] == 2
    assert environment["controlled_native_component_deterministic"] is True
    assert environment["future_state_exposure_observed"] is True
    assert environment["long_only_trading_path_executed"] is True
    assert environment["transaction_cost_path_executed"] is True
    assert environment["released_metric_functions_executed"] == 7
    controlled = environment["controlled_native_component"]
    assert controlled["environment"][0]["info"]["date"] == "2024-01-03"
    assert controlled["environment"][0]["state_max"] == "2024-01-05"
    assert controlled["environment"][1]["info"]["position"] == 9
    assert controlled["environment"][3]["info"]["position"] == 0
    assert abs(controlled["metrics"]["MDD"] - 0.02) < 1e-12
    assert len(freeze.splitlines()) == 148
    assert hashlib.sha256(freeze.encode()).hexdigest() == audit.PAPER_ENV_FREEZE_SHA256
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_committed_source_diagnostics_capture_material_conflicts() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/finagent"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    mechanisms = read_csv(output / "paper_mechanism_conformance.csv")
    references = read_csv(output / "released_missing_reference_diagnostics.csv")
    routes = read_csv(output / "released_processor_route_diagnostics.csv")
    metrics = read_csv(output / "paper_source_metric_formula_diagnostics.csv")
    strategies = read_csv(output / "released_strategy_record_inventory.csv")
    strategy_conformance = read_csv(output / "released_strategy_record_paper_conformance.csv")
    history = read_csv(output / "released_source_history_inventory.csv")
    history_paths = read_csv(output / "public_source_history_path_inventory.csv")
    history_summary = json.loads((output / "public_source_history.json").read_text(encoding="utf-8"))
    fork_refs = read_csv(output / "public_fork_branch_ref_snapshot.csv")
    fork_heads = read_csv(output / "public_fork_unique_head_inventory.csv")
    fork_summary = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))
    configs = read_csv(output / "released_config_conformance.csv")
    static = read_csv(output / "released_python_static_compilation.csv")
    artifacts = read_csv(output / "released_data_artifact_inventory.csv")
    assert len(mechanisms) == manifest["paper_mechanisms_audited"] == 31
    assert sum(row["released_source_conformance_credit"] == "True" for row in mechanisms) == 13
    statuses = {row["status"] for row in mechanisms}
    assert "conflict_future_14_days_rendered" in statuses
    assert "conflict_release_is_long_only" in statuses
    assert "conflict_signal_overwritten_by_default_parameters" in statuses
    assert Counter(row["issue"] for row in references) == {
        "nonexistent_stock_list_directory": 21,
        "missing_training_prompt_template": 60,
    }
    assert sum(row["matching_downloader_tag"] == "False" for row in routes) == 3
    assert len(metrics) == 3
    assert {row["matches_paper_formula"] for row in metrics} == {"False"}
    assert len(strategies) == 90
    assert sum(row["record_kind"] == "best_params" and row["nonempty"] == "True" for row in strategies) == 24
    assert len(strategy_conformance) == 288
    assert {row["display_precision_match"] for row in strategy_conformance} == {"False"}
    assert {row["paper_result_credit"] for row in strategy_conformance} == {"False"}
    assert Counter(row["variant"] for row in strategy_conformance) == {"default": 144, "trained": 144}
    assert len(history) == 7
    assert {row["agent_output_paths"] for row in history} == {"0"}
    assert {row["paper_result_credit"] for row in history} == {"False"}
    assert manifest["released_strategy_record_appendix_comparisons"] == 288
    assert manifest["released_strategy_record_appendix_display_matches"] == 0
    assert manifest["reachable_source_history_commits"] == 7
    assert manifest["reachable_source_history_commits_with_agent_output_paths"] == 0
    assert manifest["public_source_unique_historical_paths"] == 1955
    assert manifest["public_source_reachable_blobs"] == 1902
    assert manifest["public_source_reachable_trees"] == 327
    assert manifest["public_source_reachable_commit_objects"] == 7
    assert manifest["public_source_unreachable_objects"] == 0
    assert manifest["public_source_native_agent_result_paths"] == 0
    assert manifest["public_source_historical_strategy_record_paths"] == 90
    assert manifest["public_source_discovered_branches"] == 1
    assert manifest["public_source_discovered_tags"] == 0
    assert manifest["public_source_discovered_releases"] == 0
    assert len(history_paths) == 1955
    assert sum(row["strategy_record_path"] == "True" for row in history_paths) == 90
    assert {row["native_agent_result_path"] for row in history_paths} == {"False"}
    assert history_summary["reachable_object_counts"] == {"blob": 1902, "commit": 7, "tree": 327}
    assert history_summary["unreachable_objects"] == 0
    assert len(fork_refs) == 30
    assert len({row["repository"] for row in fork_refs}) == 26
    assert len({row["head_commit"] for row in fork_refs}) == 7
    assert len(fork_heads) == 7
    assert Counter(row["classification"] for row in fork_heads)[
        "official_public_history_reachable"
    ] == 2
    divergent = [
        row for row in fork_heads
        if row["classification"] != "official_public_history_reachable"
    ]
    assert len(divergent) == 5
    assert sum(int(row["extra_commit_count_beyond_official_head"]) for row in divergent) == 41
    assert all(row["new_final_native_agent_output_path_count"] == "0" for row in fork_heads)
    assert all(
        row["official_source_author_identity_match_in_extra_commits"] == "False"
        for row in divergent
    )
    assert all(row["paper_result_credit"] == "False" for row in fork_heads)
    assert fork_summary["github_rest_reported_forks"] == 26
    assert fork_summary["graphql_accessible_forks"] == 26
    assert fork_summary["rest_minus_accessible_fork_gap"] == 0
    assert fork_summary["graphql_accessible_branch_refs"] == 30
    assert fork_summary["unique_heads"] == 7
    assert fork_summary["heads_reachable_from_official_history"] == 2
    assert fork_summary["divergent_heads_reviewed"] == 5
    assert fork_summary["divergent_extra_commits_reviewed"] == 27
    assert fork_summary["divergent_changed_paths_reviewed"] == 93
    assert fork_summary["divergent_heads_matching_official_source_author_identity"] == 0
    assert fork_summary["new_final_blob_references_reviewed"] == 35
    assert fork_summary["new_final_unique_blobs_reviewed"] == 24
    assert fork_summary["new_final_paths_reviewed"] == 18
    assert fork_summary["native_agent_result_paths_discovered"] == 0
    assert fork_summary["exact_paper_result_table_or_figure_paths_discovered"] == 0
    assert fork_summary["paper_result_credit"] is False
    assert len(configs) == 42
    assert all(row["all_reported_core_fields_match"] == "True" for row in configs)
    assert Counter(row["reflection_model"] for row in configs) == {"True": 36, "False": 6}
    assert {row["valid_environment_declared_mode"] for row in configs} == {"train"}
    assert len(static) == 142
    assert {row["status"] for row in static} == {"compiled"}
    assert all(row["released_count"] == "0" for row in artifacts)


def test_pinned_primary_sources_and_dynamic_parsers_when_available() -> None:
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/finagent_source")
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/finagent_paper")
    if not source.exists() or not paper.exists():
        return
    audit.validate_primary_inputs(source, paper)
    tables = audit.paper_table_rows(paper / "source_v3")
    figures = audit.paper_figure_rows(paper / "source_v3")
    assert len(tables) == 959
    assert len(figures) == 102
    assert len(audit.source_inventory(source)) == 341
    assert len(audit.strategy_record_rows(source)) == 90
    assert len(audit.strategy_record_paper_conformance_rows(source, tables)) == 288
    assert len(audit.source_history_rows(source)) == 7
    assert len(audit.config_conformance_rows(source)) == 42
    assert len(audit.source_reference_diagnostics(source)) == 81
    assert len(audit.static_python_rows(source)) == 142

    census = Path("/nfs/roberts/scratch/pi_btk22/zc362/finagent_fork_census")
    snapshot = ROOT / "paper_runs/paper_replication_audits/finagent/public_fork_branch_ref_snapshot.csv"
    if census.exists() and snapshot.exists():
        heads, summary = audit.public_fork_census(census, snapshot)
        assert len(heads) == 7
        assert summary["divergent_heads_reviewed"] == 5

    versions_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/finagent_paper_versions")
    if versions_root.exists():
        versions, lineage = audit.paper_version_rows(versions_root, source)
        assert [len(audit.paper_table_rows(versions_root / f"source_v{version}", version)) for version in (1, 2, 3)] == [
            768,
            768,
            959,
        ]
        assert len(versions) == 3
        assert len(lineage) == 966
