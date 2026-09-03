from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M003_fama"


def test_m003_closes_the_factor_miner_without_promoting_a_motif():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["headline_strategy"].startswith("FAMA neural-symbolic agent")
    assert len(recipe["missing_executable_objects"]) == 6
    assert len(recipe["method_conflicts"]) == 4
    assert len(recipe["rejected_substitutes"]) == 4
    assert any("motif" in route["route"] for route in recipe["rejected_substitutes"])
    assert "No synthetic strategy or zero return" in recipe["result_policy"]


def test_m003_matches_the_existing_fail_closed_source_record():
    manifest = json.loads((ROOT / "paper_runs/paper_replication_audits/fama/manifest.json").read_text())
    assert manifest["author_linked_code_found"] is False
    assert manifest["final_mined_factor_expressions_released"] == 0
    assert manifest["initial_factor_count_claimed"] == 38
    assert manifest["initial_factor_identifiers_listed"] == 71
    assert manifest["runtime_prompt_templates_recovered"] == 1
    assert manifest["runtime_prompt_function_definitions_recovered"] == 0
    assert manifest["published_table_result_cells_reproduced"] == 0
    assert manifest["visible_figure_result_markers_reproduced"] == 0


def test_m003_has_no_fabricated_returns():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    m003 = next(row for row in ledger["milestones"] if row["milestone_id"] == "M003")
    assert m003["status"] == "closed_not_evaluable"
    assert m003["monthly_returns_path"] == m003["metrics_path"] == m003["run_manifest_path"] == ""
    assert m003["recipe_path"] and m003["verdict_path"] and m003["closure_reason"]
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 2
