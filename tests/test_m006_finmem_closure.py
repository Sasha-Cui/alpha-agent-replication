from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M006_finmem"


def test_m006_closes_the_policy_without_promoting_historical_outputs():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["headline_strategy"].startswith("GPT-4-Turbo stock-trading policy")
    assert recipe["paper_configuration"] == {"model": "GPT-4-Turbo", "temperature": 0.7,
                                               "top_k_memories": 5, "tickers": 5, "trials": 5}
    assert len(recipe["missing_headline_objects"]) == 6
    assert len(recipe["released_conflicts"]) == 4
    assert len(recipe["rejected_substitutes"]) == 5
    assert "No historical action" in recipe["result_policy"]


def test_m006_matches_existing_author_output_and_metric_boundary():
    manifest = json.loads((ROOT / "paper_runs/paper_replication_audits/finmem/manifest.json").read_text())
    assert manifest["full_paper_reproduced"] is False
    assert manifest["end_to_end_agent_result_cells_reproduced"] == 0
    assert manifest["paper_result_cells_total"] == 235
    assert manifest["historical_author_output_cells_corroborated"] == 227
    assert manifest["historical_action_metric_cells_recomputed"] == 75
    assert manifest["historical_action_metric_cells_matched"] == 67
    assert manifest["historical_action_csvs_in_public_git_history"] == 18
    assert manifest["current_head_native_action_or_return_files_shipped"] == 0


def test_m006_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    m006 = next(row for row in ledger["milestones"] if row["milestone_id"] == "M006")
    assert m006["status"] == "closed_not_evaluable"
    assert m006["monthly_returns_path"] == m006["metrics_path"] == m006["run_manifest_path"] == ""
    assert m006["recipe_path"] and m006["verdict_path"] and m006["closure_reason"]
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 5
