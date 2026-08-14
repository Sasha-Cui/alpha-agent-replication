from __future__ import annotations

import csv
import importlib.util
import json
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
    history_commits = read_csv(output / "public_source_history_commit_inventory.csv")
    history_paths = read_csv(output / "public_source_history_path_inventory.csv")
    history = json.loads((output / "public_source_history.json").read_text(encoding="utf-8"))
    current_source = read_csv(output / "current_source_conformance.csv")
    component = json.loads((output / "native_component.json").read_text(encoding="utf-8"))
    author_outputs = read_csv(output / "author_output_correspondence.csv")

    assert manifest["overall_status"] == ("not_reproduced_nearest_release_architecture_components_only")
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
    assert manifest["annualized_return_pairs_checked"] == 17
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
    assert manifest["native_source_dependency_environment_reproduced"] is False
    assert manifest["audit_runtime_called_llm_or_market_data_api"] is False
    assert manifest["paper_era_author_rendered_table_shipped"] is True
    assert manifest["paper_era_author_raw_result_arrays_shipped"] is False
    assert manifest["public_source_reachable_commits_total"] == 257
    assert manifest["public_source_unique_historical_paths_total"] == 189
    assert manifest["public_source_reachable_blobs_total"] == 1009
    assert manifest["public_source_reachable_trees_total"] == 918
    assert manifest["public_source_reachable_commit_objects_total"] == 257
    assert manifest["public_source_reachable_tag_objects_total"] == 7
    assert manifest["public_source_unreachable_objects_total"] == 0
    assert manifest["public_source_native_structured_result_paths"] == 0
    assert manifest["public_source_raw_numeric_curve_or_event_array_paths"] == 0
    assert manifest["public_source_exact_author_table_blob_versions"] == 15
    assert manifest["public_source_discovered_branches_total"] == 2
    assert manifest["public_source_discovered_tags_total"] == 10
    assert manifest["public_source_discovered_releases_total"] == 8
    assert manifest["current_public_source_tracked_files"] == 160
    assert manifest["current_public_source_python_files"] == 137
    assert manifest["current_public_source_test_files"] == 54

    assert len(table) == 77
    assert {row["paper_result_credit"] for row in table} == {"False"}
    assert {row["author_output_correspondence"] for row in table} == {"True"}
    assert {row["author_output_value"] for row in table} == {row["paper_value"] for row in table}
    assert {row["status"] for row in table} == {
        "corroborated_by_exact_author_project_site_table_not_regenerated"
    }
    assert len(author_outputs) == 1
    assert author_outputs[0]["published_result_units_corroborated"] == "77"
    assert author_outputs[0]["independently_regenerated"] == "False"
    assert author_outputs[0]["paper_result_credit"] == "False"
    assert len(annualization) == 17
    assert {row["display_precision_match"] for row in annualization} == {"False"}
    assert len(improvements) == 9
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
    assert history["unreachable_objects"] == 0
    assert history["exact_author_table_paths"] == ["index.html", "index_complete.html"]
    assert len(current_source) == 10
    assert {row["paper_result_credit"] for row in current_source} == {"False"}

    assert component["tracked_python_files_compiled"] == 39
    assert component["compile_status"] == "passed_without_importing_declared_dependencies"
    assert component["upstream_tests_shipped"] == 0
    assert component["dependency_environment_reproduced"] is False
    assert component["deterministic_across_two_runs"] is True
    assert component["semantic_component"]["topology_node_count"] == 20
    assert component["semantic_component"]["unconditional_edge_count"] == 12
    assert component["semantic_component"]["conditional_router_count"] == 9
    assert component["paper_result_reproduction"] is False

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_primary_sources_when_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_source")
    paper_source = Path("/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_paper_v7/source")
    if not source_root.exists() or not paper_source.exists():
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
