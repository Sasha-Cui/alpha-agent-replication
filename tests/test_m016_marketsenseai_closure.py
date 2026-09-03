from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M016_marketsenseai"
AUDIT = ROOT / "paper_runs/paper_replication_audits/marketsenseai"


def test_m016_closes_missing_signal_not_monthly_portfolio_shell():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250200415"
    assert "Five-agent GPT-4o" in recipe["headline_strategy"]
    assert recipe["paper_configuration"]["agent_count"] == 5
    assert recipe["paper_configuration"]["signal_frequency"] == "monthly"
    assert recipe["paper_configuration"]["portfolio_rules"] == [
        "equal-weight buy signals", "capitalization-weight buy signals"
    ]
    assert recipe["paper_configuration"]["transaction_cost_bps_per_trade"] == 10
    assert len(recipe["missing_headline_objects"]) == 7
    assert len(recipe["rejected_substitutes"]) == 5
    assert "positive monthly portfolio claims remain unresolved" in recipe["result_policy"]


def test_m016_matches_operational_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    assert manifest["operational_system_source_found"] is False
    assert manifest["native_signal_or_portfolio_outputs_found"] is False
    assert manifest["native_mechanism_dimensions_reproduced"] == 0
    assert manifest["paper_mechanism_dimensions"] == 38
    assert manifest["paper_2025_result_table_units_faithfully_regenerated"] == 0
    assert manifest["paper_2025_result_table_units"] == 157
    assert manifest["paper_2025_empirical_figure_assets_faithfully_regenerated"] == 0
    assert manifest["paper_2025_empirical_figure_assets"] == 6
    with (AUDIT / "paper_mechanism_conformance.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    target = [row for row in rows if row["canonical_work_id"] == "CensusArxiv250200415"]
    signal = next(row for row in target if row["dimension"] == "signal timing")
    portfolio = next(row for row in target if row["dimension"] == "portfolio rule")
    output = next(row for row in target if row["dimension"] == "native result outputs")
    assert signal["primary_source_evidence"].startswith("monthly stated")
    assert portfolio["primary_source_evidence"].startswith("equal/cap weighting stated")
    assert output["status"] == "missing"


def test_m016_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m016 = rows["M016"]
    assert m016["status"] == "closed_not_evaluable"
    assert m016["monthly_returns_path"] == m016["metrics_path"] == m016["run_manifest_path"] == ""
    assert m016["recipe_path"] and m016["verdict_path"] and m016["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 16
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 14
