from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M004_flag_trader"


def test_m004_closes_the_learned_policy_without_using_baselines():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["headline_strategy"].startswith("Fusion LLM trading agent")
    assert recipe["static_information_recovered"] == {"hyperparameter_settings": 22, "prompt_template": True}
    assert len(recipe["missing_executable_objects"]) == 7
    assert len(recipe["procedure_conflicts"]) == 4
    assert len(recipe["rejected_substitutes"]) == 4
    assert any("baselines" in route["reason"] for route in recipe["rejected_substitutes"])
    assert "No baseline or fabricated" in recipe["result_policy"]


def test_m004_matches_the_existing_source_boundary():
    manifest = json.loads((ROOT / "paper_runs/paper_replication_audits/flag_trader/manifest.json").read_text())
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_table_cells_total"] == 360
    assert manifest["paper_table_cells_reproduced"] == 6
    assert manifest["flag_trader_native_result_cells_reproduced"] == 0
    assert manifest["official_flag_trader_checkpoint_released"] is False
    assert manifest["official_flag_trader_source_released"] is False
    assert manifest["official_flag_trader_trajectory_released"] is False
    assert manifest["paper_hyperparameter_settings"] == 22
    assert manifest["paper_prompt_template_recovered"] is True
    assert manifest["unaffiliated_candidate_paper_credit"] is False


def test_m004_has_no_fabricated_returns():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    m004 = next(row for row in ledger["milestones"] if row["milestone_id"] == "M004")
    assert m004["status"] == "closed_not_evaluable"
    assert m004["monthly_returns_path"] == m004["metrics_path"] == m004["run_manifest_path"] == ""
    assert m004["recipe_path"] and m004["verdict_path"] and m004["closure_reason"]
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 3
