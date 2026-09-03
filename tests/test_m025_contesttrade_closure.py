from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M025_contesttrade"
AUDIT = ROOT / "paper_runs/paper_replication_audits/contesttrade"


def test_m025_closes_disconnected_contests_without_promoting_components():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250800554"
    assert "Data Contest" in recipe["headline_strategy"]
    assert recipe["paper_configuration"]["data_history_days"] == 5
    assert recipe["paper_configuration"]["research_prediction_days"] == 5
    assert recipe["paper_configuration"]["transaction_cost"] == 0.001
    assert recipe["released_component_credit"]["data_contest_models"] == 2
    assert recipe["released_component_credit"]["active_contests_reached"] == 0
    assert len(recipe["missing_or_conflicting_headline_objects"]) == 7
    assert len(recipe["rejected_substitutes"]) == 5


def test_m025_matches_entrypoint_component_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    assert manifest["data_contest_reachable_from_public_entrypoint"] is False
    assert manifest["research_contest_reachable_from_public_entrypoint"] is False
    assert manifest["active_portfolio_constructor_present"] is False
    assert manifest["data_contest_shipped_model_files"] == 2
    assert manifest["data_contest_model_training_provenance_present"] is False
    assert manifest["research_contest_required_model_files_present"] is False
    assert manifest["research_predict_signal_scores_method_present"] is False
    assert manifest["native_paper_result_display_units_reproduced"] == 0
    assert manifest["paper_result_display_units_total"] == 64
    with (AUDIT / "source_entrypoint_reachability.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    active = next(row for row in rows if row["check"] == "active_workflow_nodes")
    assert active["status"] == "mismatch_contests_and_portfolio_absent"


def test_m025_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m025 = rows["M025"]
    assert m025["status"] == "closed_not_evaluable"
    assert m025["monthly_returns_path"] == m025["metrics_path"] == m025["run_manifest_path"] == ""
    assert m025["recipe_path"] and m025["verdict_path"] and m025["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 25
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 20
