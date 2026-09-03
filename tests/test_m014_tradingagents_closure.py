from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M014_tradingagents"
AUDIT = ROOT / "paper_runs/paper_replication_audits/tradingagents"


def test_m014_closes_full_strategy_without_promoting_graph_topology():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv241220138"
    assert "Multi-agent LLM workflow" in recipe["headline_strategy"]
    assert recipe["nearest_source_commit"] == "cc97cb6d5deb10eac370db0c6678e2796a62eba8"
    assert recipe["released_component_credit"]["graph_nodes_including_start_end"] == 22
    assert recipe["released_component_credit"]["graph_edges"] == 30
    assert recipe["released_component_credit"]["released_tools"] == 16
    assert len(recipe["missing_headline_objects"]) == 7
    assert len(recipe["nearest_release_conflicts"]) == 5
    assert len(recipe["rejected_substitutes"]) == 5
    assert "positive paper results remain unresolved" in recipe["result_policy"]


def test_m014_matches_native_component_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    component = json.loads((AUDIT / "native_component.json").read_text())
    assert manifest["nearest_source_release_after_paper_hours"] == 52.3894
    assert manifest["native_source_modules_imported_with_real_dependencies"] == 33
    assert manifest["native_source_real_graph_nodes_including_start_end"] == 22
    assert manifest["native_source_real_graph_edges"] == 30
    assert manifest["native_source_real_tool_count"] == 16
    assert manifest["native_paper_backtest_runner_shipped"] is False
    assert manifest["native_paper_nav_returns_holdings_shipped"] is False
    assert manifest["native_paper_table_result_cells_reproduced"] == 0
    assert manifest["paper_numeric_table_cells_total"] == 77
    assert manifest["native_exact_result_figure_series_reproduced"] == 0
    assert manifest["paper_result_figure_series_total"] == 42
    assert component["paper_result_reproduction"] is False
    with (AUDIT / "source_mechanism_conformance.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    portfolio = next(row for row in rows if row["dimension"] == "portfolio_state")
    assert portfolio["status"] == "missing"
    assert portfolio["paper_mechanism_credit"] == "False"


def test_m014_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m014 = rows["M014"]
    assert m014["status"] == "closed_not_evaluable"
    assert m014["monthly_returns_path"] == m014["metrics_path"] == m014["run_manifest_path"] == ""
    assert m014["recipe_path"] and m014["verdict_path"] and m014["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 14
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 12
