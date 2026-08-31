from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_tradingagents_paper.py"
SPEC = importlib.util.spec_from_file_location("tradingagents_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_table_denominator_covers_every_numeric_cell() -> None:
    rows = audit.paper_table_rows()
    assert len(rows) == 77
    assert Counter(row["cell_kind"] for row in rows) == {
        "direct_result": 68,
        "derived_improvement": 9,
    }
    assert Counter(row["method"] for row in rows) == {
        "B&H": 12,
        "MACD": 8,
        "KDJ&RSI": 12,
        "ZMR": 12,
        "SMA": 12,
        "TradingAgents": 12,
        "Improvement(%)": 9,
    }
    assert len({(row["paper_table"], row["method"], row["asset"], row["metric"]) for row in rows}) == 77
    assert {row["paper_result_credit"] for row in rows} == {False}
    assert {row["author_output_correspondence"] for row in rows} == {False}


def test_paper_internal_metric_checks_fail_closed() -> None:
    annualization = audit.annualization_identity()
    improvements = audit.improvement_identity()
    inconsistencies = audit.paper_internal_inconsistencies()

    assert len(annualization) == 17
    assert {row["display_precision_match"] for row in annualization} == {False}
    aapl = next(row for row in annualization if row["method"] == "TradingAgents" and row["asset"] == "AAPL")
    assert round(aapl["AR_pct_from_published_equation"], 2) == 163.43
    assert Counter(row["status"] for row in improvements) == {
        "exact_absolute_difference_from_displayed_cells": 7,
        "not_exact_from_displayed_cells_hidden_precision_could_explain": 1,
        "inconsistent_with_displayed_cells": 1,
    }
    googl_sr = next(row for row in improvements if row["asset"] == "GOOGL" and row["metric"] == "SR")
    assert googl_sr["absolute_difference_from_displayed_cells"] == 4.08
    assert googl_sr["paper_improvement_pct_label"] == 4.26
    assert len(inconsistencies) == 7


def test_result_figure_denominator_is_explicit_and_fail_closed() -> None:
    rows = audit.paper_figure_series()
    assert len(rows) == 42
    assert Counter(row["panel"] for row in rows) == {
        "cumulative_return": 18,
        "broker": 6,
        "trade_net_profit_loss": 6,
        "market": 6,
        "transactions": 6,
    }
    assert {row["native_exact_series_reproduced"] for row in rows} == {False}
    assert {row["paper_result_credit"] for row in rows} == {False}


def test_committed_audit_is_fail_closed_and_self_hashing() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/tradingagents"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    table = read_csv(output / "table_1_conformance.csv")
    annualization = read_csv(output / "annualized_return_identity_audit.csv")
    improvements = read_csv(output / "improvement_identity_audit.csv")
    claims = read_csv(output / "published_non_table_claims.csv")
    inconsistencies = read_csv(output / "paper_internal_inconsistencies.csv")
    tools = read_csv(output / "appendix_case_tool_conformance.csv")
    mechanisms = read_csv(output / "source_mechanism_conformance.csv")
    gaps = read_csv(output / "paper_specification_gaps.csv")
    inventory = read_csv(output / "released_source_inventory.csv")
    paper_assets = read_csv(output / "paper_source_asset_inventory.csv")
    paper_versions = read_csv(output / "official_paper_version_inventory.csv")
    figure_series = read_csv(output / "paper_figure_series_inventory.csv")
    vector_endpoints = read_csv(output / "paper_vector_curve_endpoint_conformance.csv")
    yahoo = read_csv(output / "current_yahoo_buy_hold_diagnostic.csv")
    history_commits = read_csv(output / "public_source_history_commit_inventory.csv")
    history_paths = read_csv(output / "public_source_history_path_inventory.csv")
    history = json.loads((output / "public_source_history.json").read_text(encoding="utf-8"))
    current_source = read_csv(output / "current_source_conformance.csv")
    component = json.loads((output / "native_component.json").read_text(encoding="utf-8"))
    freeze = (output / "reconstructed_environment_freeze.txt").read_text(encoding="utf-8")
    author_outputs = read_csv(output / "author_output_correspondence.csv")
    fork_branches = read_csv(output / "public_fork_branch_ref_snapshot.csv")
    fork_heads = read_csv(output / "public_fork_unique_head_inventory.csv")
    fork_commits = read_csv(output / "public_fork_divergent_commit_inventory.csv")
    fork_tiers = read_csv(output / "public_fork_artifact_tier_summary.csv")
    fork_site = read_csv(output / "public_fork_author_site_commit_inventory.csv")
    fork_rasters = read_csv(output / "public_fork_author_raster_correspondence.csv")
    fork_notable = read_csv(output / "public_fork_notable_artifact_inventory.csv")
    fork_census = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))

    assert manifest["overall_status"] == "not_reproduced_author_output_rasters_and_architecture_components_only"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_era_source_revision_available"] is False
    assert manifest["paper_era_author_project_site_available"] is True
    assert manifest["official_paper_versions_audited"] == 7
    assert manifest["paper_versions_with_executable_source_at_submission"] == 0
    assert manifest["paper_versions_with_exact_author_site_table_at_submission"] == 7
    assert manifest["paper_v1_through_v6_comparison_plot_final_label"] == "StockGPTStrategy"
    assert manifest["paper_v7_comparison_plot_final_label"] == "TradingAgents"
    assert manifest["source_commit"] == audit.SOURCE_COMMIT
    assert manifest["pre_release_tree_files"] == 3
    assert manifest["paper_numeric_table_cells_total"] == 77
    assert manifest["paper_direct_result_cells_total"] == 68
    assert manifest["paper_derived_improvement_cells_total"] == 9
    assert manifest["native_paper_table_result_cells_reproduced"] == 0
    assert manifest["author_output_table_cells_corroborated"] == 77
    assert manifest["author_output_table_cells_independently_regenerated"] == 0
    assert manifest["published_non_table_result_claims_total"] == 12
    assert manifest["native_non_table_result_claims_reproduced"] == 0
    assert manifest["paper_result_figure_series_total"] == 42
    assert manifest["native_exact_result_figure_series_reproduced"] == 0
    assert manifest["paper_presented_empirical_units_total"] == 131
    assert manifest["native_presented_empirical_units_reproduced"] == 0
    assert manifest["paper_vector_curve_endpoints_total"] == 17
    assert manifest["paper_vector_curve_endpoints_matching_table"] == 1
    assert manifest["paper_vector_curve_endpoints_conflicting_with_table"] == 16
    assert manifest["paper_vector_curve_endpoints_with_native_result_credit"] == 0
    assert manifest["annualized_return_pairs_checked"] == 17
    assert manifest["current_public_yahoo_buy_hold_cells_checked"] == 12
    assert manifest["current_public_yahoo_buy_hold_cells_matching"] == 0
    assert manifest["current_public_yahoo_observed_on"] == "2026-08-25"
    assert manifest["current_public_yahoo_has_paper_time_input_lineage"] is False
    assert manifest["current_public_yahoo_paper_price_provider_mapping_recovered"] is False
    assert manifest["annualized_return_pairs_matching_published_equation"] == 0
    assert manifest["paper_internal_inconsistencies_total"] == 7
    assert manifest["paper_specification_gaps_total"] == 27
    assert manifest["appendix_unique_tools_total"] == 11
    assert manifest["appendix_tools_exactly_present_in_nearest_release"] == 6
    assert manifest["appendix_case_output_reproduced"] is False
    assert manifest["source_mechanism_dimensions_total"] == 45
    assert manifest["source_mechanism_matches_or_analogues"] == 14
    assert manifest["source_mechanism_fully_faithful"] is False
    assert manifest["tracked_source_files_total"] == 56
    assert manifest["tracked_source_python_files_total"] == 39
    assert manifest["paper_source_assets_total"] == 26
    assert manifest["numeric_result_figure_arrays_shipped"] == 0
    assert manifest["native_source_upstream_tests_shipped"] == 0
    assert manifest["native_source_dependency_environment_reproduced"] is True
    assert manifest["native_source_exact_historical_dependency_versions_recovered"] is False
    assert manifest["native_source_modules_imported_with_real_dependencies"] == 33
    assert manifest["native_source_real_graph_nodes_including_start_end"] == 22
    assert manifest["native_source_real_graph_edges"] == 30
    assert manifest["native_source_real_tool_count"] == 16
    assert manifest["audit_runtime_called_llm_or_market_data_api"] is False
    assert manifest["paper_era_author_rendered_table_shipped"] is True
    assert manifest["paper_era_author_raw_result_arrays_shipped"] is False
    assert manifest["public_source_reachable_commits_total"] == 257
    assert manifest["public_source_unique_historical_paths_total"] == 189
    assert manifest["public_source_reachable_blobs_total"] == 1009
    assert manifest["public_source_reachable_trees_total"] == 918
    assert manifest["public_source_reachable_commit_objects_total"] == 257
    assert manifest["public_source_reachable_tag_objects_total"] == 7
    assert manifest["public_source_unreachable_objects_in_official_ref_scope"] == 0
    assert manifest["public_source_native_structured_result_paths"] == 0
    assert manifest["public_source_raw_numeric_curve_or_event_array_paths"] == 0
    assert manifest["public_source_exact_author_table_blob_versions"] == 15
    assert manifest["public_source_discovered_branches_total"] == 2
    assert manifest["public_source_discovered_tags_total"] == 10
    assert manifest["public_source_discovered_releases_total"] == 8
    assert manifest["current_public_source_tracked_files"] == 160
    assert manifest["current_public_source_python_files"] == 137
    assert manifest["current_public_source_test_files"] == 54
    assert manifest["github_rest_reported_public_forks"] == 19586
    assert manifest["graphql_accessible_public_forks"] == 19445
    assert manifest["public_fork_accessibility_gap"] == 141
    assert manifest["public_fork_branch_refs_examined"] == 24584
    assert manifest["public_fork_unique_heads_examined"] == 4234
    assert manifest["public_fork_heads_reachable_from_official_history"] == 115
    assert manifest["public_fork_divergent_heads_examined"] == 4119
    assert manifest["public_fork_connected_divergent_heads"] == 4083
    assert manifest["public_fork_disconnected_divergent_heads"] == 36
    assert manifest["public_fork_extra_commits_examined"] == 37020
    assert manifest["public_fork_changed_paths_examined"] == 326583
    assert manifest["public_fork_changed_new_blobs_inventoried"] == 340214
    assert manifest["public_fork_unique_selected_artifact_blobs_reviewed"] == 54583
    assert manifest["public_fork_unique_selected_artifact_bytes_reviewed"] == 6257226176
    assert manifest["public_fork_extra_commits_with_exact_official_author_identity"] == 1172
    assert manifest["public_fork_author_site_commits_recovered"] == 20
    assert manifest["public_fork_author_site_preserving_repositories"] == 48
    assert manifest["author_output_figure_series_cross_format_correspondence"] == 14
    assert manifest["paper_table_cells_independently_regenerated_from_public_forks"] == 0
    assert manifest["paper_figure_series_independently_regenerated_from_public_forks"] == 0

    assert len(table) == 77
    assert len(fork_branches) == 24584
    assert len({row["repository"] for row in fork_branches}) == 19445
    assert len(fork_heads) == 4234
    assert Counter(row["status"] for row in fork_heads) == {
        "official_history_reachable": 115,
        "connected_divergent": 4083,
        "disconnected_divergent": 36,
    }
    assert len(fork_commits) == 37020
    assert [int(row["selected_blobs"]) for row in fork_tiers] == [10910, 39823, 1931, 1922]
    assert len(fork_site) == 20
    assert len(fork_rasters) == 2
    assert sum(int(row["series_corresponding"]) for row in fork_rasters) == 14
    assert {row["cross_format_raster_correspondence"] for row in fork_rasters} == {"True"}
    assert {row["underlying_numeric_array_recovered"] for row in fork_rasters} == {"False"}
    assert {row["native_series_regenerated"] for row in fork_rasters} == {"False"}
    assert {row["paper_result_credit"] for row in fork_rasters} == {"False"}
    assert {row["artifact_role"] for row in fork_notable} == {"paper_quote_only", "unaffiliated_aapl_baseline"}
    assert {row["raw_result_lineage_shipped"] for row in fork_notable} == {"False"}
    assert fork_census["attributable_paper_run_artifacts"] == 0
    assert fork_census["paper_table_cells_independently_regenerated_from_forks"] == 0
    assert {row["paper_result_credit"] for row in table} == {"False"}
    assert {row["author_output_correspondence"] for row in table} == {"True"}
    assert {row["author_output_value"] for row in table} == {row["paper_value"] for row in table}
    assert {row["status"] for row in table} == {"corroborated_by_exact_author_project_site_table_not_regenerated"}
    assert len(author_outputs) == 1
    assert author_outputs[0]["published_result_units_corroborated"] == "77"
    assert author_outputs[0]["independently_regenerated"] == "False"
    assert author_outputs[0]["paper_result_credit"] == "False"
    assert len(annualization) == 17
    assert len(vector_endpoints) == 17
    assert Counter(row["status"] for row in vector_endpoints) == {
        "author_figure_endpoint_conflicts_with_table": 16,
        "exact_author_figure_table_endpoint_correspondence": 1,
    }
    exact_vector = next(row for row in vector_endpoints if row["display_precision_match"] == "True")
    assert (exact_vector["asset"], exact_vector["method"]) == ("AMZN", "KDJ&RSI")
    assert {row["native_paper_result_credit"] for row in vector_endpoints} == {"False"}

    assert {row["display_precision_match"] for row in annualization} == {"False"}
    assert len(improvements) == 9
    assert len(yahoo) == 12
    assert Counter(row["asset"] for row in yahoo) == {"AAPL": 4, "GOOGL": 4, "AMZN": 4}
    assert {row["display_precision_match"] for row in yahoo} == {"False"}
    assert {row["paper_time_input_lineage"] for row in yahoo} == {"False"}
    assert {row["native_paper_result_credit"] for row in yahoo} == {"False"}
    assert Counter(row["formula_fully_specified_by_paper"] for row in yahoo) == {
        "True": 9,
        "False": 3,
    }
    cumulative = {
        row["asset"]: float(row["current_yahoo_diagnostic_value"]) for row in yahoo if row["metric"] == "CR_pct"
    }
    assert math.isclose(cumulative["AAPL"], -7.509797567549237)
    assert math.isclose(cumulative["GOOGL"], 9.235007082040148)
    assert math.isclose(cumulative["AMZN"], 20.30948689024379)
    assert {row["response_rows"] for row in yahoo} == {"61"}
    assert {row["response_start"] for row in yahoo} == {"2024-01-02"}
    assert {row["response_end"] for row in yahoo} == {"2024-03-28"}
    assert len(claims) == 14
    assert Counter(row["claim_role"] for row in claims) == {
        "result": 12,
        "configuration": 2,
    }
    assert len(inconsistencies) == 7
    assert Counter(row["status"] for row in tools) == {
        "exact_released_tool_name": 6,
        "absent_from_nearest_release": 5,
    }
    assert len(mechanisms) == 45
    assert Counter(row["paper_mechanism_credit"] for row in mechanisms) == {
        "True": 14,
        "False": 31,
    }
    assert len(gaps) == 27
    assert len(inventory) == 56
    assert sum(row["python_source"] == "True" for row in inventory) == 39
    assert len(paper_assets) == 26
    assert sum(row["asset_role"] == "numeric_result_figure" for row in paper_assets) == 6
    assert {row["underlying_numeric_array_shipped"] for row in paper_assets} == {"False"}
    assert len(paper_versions) == 7
    assert {row["displayed_table_numeric_cells"] for row in paper_versions} == {"77"}
    assert {row["displayed_result_figure_series"] for row in paper_versions} == {"42"}
    assert {row["executable_source_present_at_submission"] for row in paper_versions} == {"False"}
    assert {row["native_result_reproduced"] for row in paper_versions} == {"False"}
    assert [row["compare_plot_final_series_label"] for row in paper_versions] == [
        "StockGPTStrategy",
        "StockGPTStrategy",
        "StockGPTStrategy",
        "StockGPTStrategy",
        "StockGPTStrategy",
        "StockGPTStrategy",
        "TradingAgents",
    ]
    assert len(figure_series) == 42
    assert {row["native_exact_series_reproduced"] for row in figure_series} == {"False"}
    assert len(history_commits) == 257
    assert len(history_paths) == 189
    assert sum(row["contains_exact_author_table_in_history"] == "True" for row in history_paths) == 2
    assert {row["native_structured_result_path"] for row in history_paths} == {"False"}
    assert history["reachable_object_counts"] == {"blob": 1009, "commit": 257, "tag": 7, "tree": 918}
    assert history["unreachable_objects_in_official_ref_scope"] == 0
    assert history["exact_author_table_paths"] == ["index.html", "index_complete.html"]
    assert len(current_source) == 10
    assert {row["paper_result_credit"] for row in current_source} == {"False"}

    assert component["tracked_python_files_compiled"] == 39
    assert component["compile_status"] == "passed_in_reconstructed_declared_dependency_environment"
    assert component["upstream_tests_shipped"] == 0
    assert component["dependency_environment_reproduced"] is True
    assert component["release_declared_requirements"] == 24
    assert component["exact_historical_dependency_versions_recovered"] is False
    assert component["pip_check"] == "No broken requirements found."
    assert component["dependency_freeze_sha256"] == audit.RECONSTRUCTED_ENV_FREEZE_SHA256
    assert component["dependency_freeze_lines"] == 247
    assert len(freeze.splitlines()) == 247
    assert audit.sha256_bytes(freeze.encode()) == audit.RECONSTRUCTED_ENV_FREEZE_SHA256
    assert component["deterministic_across_two_runs"] is True
    assert component["semantic_component"]["topology_node_count"] == 20
    assert component["semantic_component"]["unconditional_edge_count"] == 12
    assert component["semantic_component"]["conditional_router_count"] == 9
    real = component["real_dependency_component"]
    assert real["imported_source_modules"] == 33
    assert real["compiled_graph_type"] == "langgraph.graph.state.CompiledStateGraph"
    assert real["graph_node_count_including_start_end"] == 22
    assert real["graph_edge_count"] == 30
    assert real["conditional_edge_count"] == 18
    assert real["tool_count"] == 16
    assert real["network_attempts"] == []
    assert component["paper_result_reproduction"] is False

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_global_evidence_route_preserves_current_yahoo_boundary() -> None:
    ledger = read_csv(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in ledger if item["system_id"] == "SYS-TRADING-AGENTS")
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_77_of_77_author_table_cells_corroborated_16_of_17_"
        "vector_endpoints_conflict_14_of_42_"
        "author_raster_series_cross_format_12_current_yahoo_cells_zero_matches_19445_"
        "forks_24584_refs_4234_heads_exhausted_zero_native_regenerated"
    )
    note = row["concise_evidence_note"]
    assert "current Yahoo adjusted-close diagnostic" in note
    assert "all 12 Buy-and-Hold cells" in note
    assert "matches 0/12 at display precision" in note
    assert "no paper-time lineage" in note
    assert "19,445 accessible public forks" in note
    assert "14/42 paper series" in note
    assert "No fork provides a native paper run" in note
    assert "17 cumulative-return vector endpoints" in note
    assert "other 16" in note

    route = read_csv(ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv")
    route_row = next(item for item in route if item["canonical_work_id"] == "CensusArxiv241220138")
    assert "matches 0/12 at display precision" in route_row["precise_native_or_access_blocker"]
    failures = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text()
    assert "matches 0/12 at display precision" in failures


def test_pinned_primary_sources_when_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_source")
    paper_source = Path("/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_paper_v7/source")
    fork_snapshot = paper_source.parent / "public_fork_branch_ref_snapshot_2026-08-30.csv"
    if not source_root.exists() or not paper_source.exists() or not fork_snapshot.exists():
        return

    assert str(audit.run_git(source_root, "rev-parse", "v0.1.0^{}")).strip() == (audit.SOURCE_COMMIT)
    assert audit.git_files_at(source_root, audit.PRE_RELEASE_COMMIT) == [
        "README.md",
        "index.html",
        "index_complete.html",
    ]
    author_outputs = audit.author_output_correspondence(source_root)
    assert author_outputs[0]["published_result_units_corroborated"] == 77
    assert audit.paper_table_rows(author_output_verified=True)[0]["author_output_correspondence"] is True
    assert len(audit.source_inventory(source_root)) == 56
    assert len(audit.paper_source_inventory(paper_source)) == 26
    assert Counter(row["status"] for row in audit.case_tool_conformance(source_root)) == {
        "exact_released_tool_name": 6,
        "absent_from_nearest_release": 5,
    }
    vector_endpoints = audit.paper_vector_curve_endpoint_rows(paper_source)
    assert len(vector_endpoints) == 17
    assert sum(row["display_precision_match"] for row in vector_endpoints) == 1
    assert {row["native_paper_result_credit"] for row in vector_endpoints} == {False}
    diagnostic_root = audit.DEFAULT_YAHOO_DIAGNOSTIC_ROOT
    if diagnostic_root.is_dir():
        diagnostic = audit.current_yahoo_buy_hold_diagnostic(diagnostic_root)
        assert len(diagnostic) == 12
        assert {row["display_precision_match"] for row in diagnostic} == {False}
        assert {row["paper_time_input_lineage"] for row in diagnostic} == {False}
        assert {row["native_paper_result_credit"] for row in diagnostic} == {False}
    source_python = Path(audit.DEFAULT_SOURCE_PYTHON)
    if source_python.is_file():
        component = audit.run_native_component_checks(source_root, source_python)
        assert component["dependency_environment_reproduced"] is True
        assert component["real_dependency_component"]["network_attempts"] == []
    fork = audit.audit_public_forks(source_root, paper_source, fork_snapshot, deep_scan=False)
    branch_rows, head_rows, commit_rows, tier_rows, site_rows, _, notable_rows, census = fork
    assert [len(branch_rows), len(head_rows), len(commit_rows)] == [24584, 4234, 37020]
    assert [int(row["selected_blobs"]) for row in tier_rows] == [10910, 39823, 1931, 1922]
    assert len(site_rows) == 20
    assert len(notable_rows) == 2
