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
    component = json.loads((output / "native_component.json").read_text(encoding="utf-8"))
    author_outputs = read_csv(output / "author_output_correspondence.csv")

    assert manifest["overall_status"] == ("not_reproduced_nearest_release_architecture_components_only")
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_era_source_revision_available"] is False
    assert manifest["paper_era_author_project_site_available"] is True
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
