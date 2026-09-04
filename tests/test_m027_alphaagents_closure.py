from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M027_alphaagents"
AUDIT = ROOT / "paper_runs/paper_replication_audits/alphaagents"


def test_m027_preserves_exact_portfolio_without_future_backcast():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250811152"
    portfolio = recipe["headline_portfolio"]
    assert portfolio["risk_profile"] == "risk-neutral"
    assert portfolio["method"] == "multi-agent"
    assert portfolio["decision_date"] == "2024-02-01"
    assert portfolio["equal_weighted"] is True
    assert len(portfolio["source_only_tickers"]) == 13
    assert len(recipe["missing_headline_objects"]) == 6
    assert len(recipe["rejected_substitutes"]) == 5
    assert "Backcasting it would be lookahead" in recipe["result_policy"]


def test_m027_matches_source_membership_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    assert manifest["source_only_portfolios_recovered"] == 7
    assert manifest["source_only_ticker_memberships_recovered"] == 77
    assert manifest["author_linked_code_found"] is False
    assert manifest["plotted_performance_series_reproduced"] == 0
    assert manifest["plotted_performance_series"] == 20
    with (AUDIT / "source_only_portfolio_inventory.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    target = next(row for row in rows if row["risk_profile"] == "risk-neutral" and row["portfolio"] == "multi-agent")
    assert int(target["ticker_count"]) == 13
    assert target["tickers_in_source_order"].split("|") == json.loads((OUTPUT / "recipe.json").read_text())[
        "headline_portfolio"
    ]["source_only_tickers"]
    assert target["native_agent_output_credit"] == target["performance_result_credit"] == "no"


def test_m027_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m027 = rows["M027"]
    assert m027["status"] == "closed_not_evaluable"
    assert m027["monthly_returns_path"] == m027["metrics_path"] == m027["run_manifest_path"] == ""
    assert m027["recipe_path"] and m027["verdict_path"] and m027["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 27
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 21
