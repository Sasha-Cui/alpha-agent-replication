from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M013_finvision"
AUDIT = ROOT / "paper_runs/paper_replication_audits/finvision"


def test_m013_closes_agent_without_promoting_prompt_templates():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv241108899"
    assert "LangGraph multi-agent" in recipe["headline_strategy"]
    assert recipe["paper_configuration"]["chart_lookback_days"] == 60
    assert recipe["paper_configuration"]["reflection_signal_window_days"] == 30
    assert recipe["recovered_component_credit"] == {
        "prompt_templates": 5,
        "actual_llm_requests": 0,
        "actual_llm_responses": 0,
        "public_system_source_files": 0,
    }
    assert len(recipe["missing_headline_objects"]) == 7
    assert len(recipe["rejected_substitutes"]) == 5
    assert "positive paper results remain unresolved" in recipe["result_policy"]


def test_m013_matches_prompt_system_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    native = json.loads((AUDIT / "native_execution.json").read_text())
    assert manifest["prompt_templates_recovered"] == 5
    assert manifest["actual_llm_requests_recovered"] == 0
    assert manifest["actual_llm_responses_recovered"] == 0
    assert manifest["public_system_source_files_recovered"] == 0
    assert manifest["finvision_own_cells_faithfully_regenerated"] == 0
    assert manifest["finvision_own_performance_cells"] == 18
    assert manifest["published_performance_cells_faithfully_regenerated"] == 0
    assert manifest["published_performance_cells"] == 72
    assert manifest["current_yahoo_diagnostic_display_matches"] == 3
    assert manifest["current_yahoo_diagnostic_faithful_credit"] == 0
    assert native["finvision_pipeline_executed"] is False
    with (AUDIT / "prompt_inventory.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 5
    assert all(row["actual_request_released"] == row["actual_response_released"] == "False" for row in rows)


def test_m013_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m013 = rows["M013"]
    assert m013["status"] == "closed_not_evaluable"
    assert m013["monthly_returns_path"] == m013["metrics_path"] == m013["run_manifest_path"] == ""
    assert m013["recipe_path"] and m013["verdict_path"] and m013["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 13
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 11
