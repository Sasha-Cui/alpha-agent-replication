from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M005_alphaquanter"


def test_m005_closes_the_policy_without_trading_on_future_labels():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["headline_strategy"].startswith("Tool-augmented LLM trading policy")
    assert recipe["released_components"]["dated_prompt_reward_rows"] == 2615
    assert recipe["released_components"]["numeric_reward_labels_recovered"] == 2615
    assert recipe["released_components"]["paper_result_credit"] == 0
    assert len(recipe["missing_headline_objects"]) == 6
    assert len(recipe["procedure_conflicts"]) == 4
    assert len(recipe["rejected_substitutes"]) == 4
    assert "direct lookahead" in recipe["rejected_substitutes"][0]["reason"]


def test_m005_matches_existing_released_component_boundary():
    manifest = json.loads((ROOT / "paper_runs/paper_replication_audits/alphaquanter/manifest.json").read_text())
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_result_cells_total"] == 790
    assert manifest["non_buy_hold_cells_unverifiable"] == 756
    assert manifest["released_prompt_label_rows"] == 2615
    assert manifest["paper_test_prompt_rows_shipped"] == 0
    assert manifest["paper_test_action_rows_shipped"] == 0
    assert manifest["reward_label_lineage_exact_numeric_matches"] == 2615
    assert manifest["reward_label_lineage_paper_result_credit"] == 0
    assert manifest["native_training_checkpoints_shipped"] is False
    assert manifest["released_complete_verl_runtime"] is False


def test_m005_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    m005 = next(row for row in ledger["milestones"] if row["milestone_id"] == "M005")
    assert m005["status"] == "closed_not_evaluable"
    assert m005["monthly_returns_path"] == m005["metrics_path"] == m005["run_manifest_path"] == ""
    assert m005["recipe_path"] and m005["verdict_path"] and m005["closure_reason"]
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 4
