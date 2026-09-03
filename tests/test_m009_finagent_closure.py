from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M009_finagent"
AUDIT = ROOT / "paper_runs/paper_replication_audits/finagent"


def test_m009_closes_the_agent_without_promoting_runnable_components():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["source_commit"] == "08fb217d374b6c923b0ab3e6dbd8213e1d0fcf1c"
    assert "multimodal" in recipe["headline_strategy"].lower()
    assert recipe["paper_configuration"]["retrieval_horizons_days"] == [1, 7, 14]
    assert recipe["paper_configuration"]["top_k_memories"] == 5
    assert len(recipe["missing_headline_objects"]) == 7
    assert len(recipe["material_source_conflicts"]) == 5
    assert len(recipe["rejected_substitutes"]) == 5
    assert "false failure claim" in recipe["result_policy"]


def test_m009_matches_native_audit_and_baseline_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    native = json.loads((AUDIT / "native_execution.json").read_text())
    assert manifest["released_python_files"] == 142
    assert manifest["paper_era_core_modules_imported"] == 65
    assert manifest["released_source_mechanisms_verified"] == 13
    assert manifest["paper_mechanisms_audited"] == 31
    assert manifest["published_result_display_units_reproduced"] == 0
    assert manifest["published_result_display_units_total"] == 1061
    assert manifest["released_strategy_record_appendix_comparisons"] == 288
    assert manifest["released_strategy_record_appendix_display_matches"] == 0
    assert manifest["buy_hold_current_response_unique_cells_matching"] == 13
    assert manifest["buy_hold_current_response_unique_cells_checked"] == 36
    assert native["full_native_system_execution_attempted"] is False
    assert native["dependency_environment"]["future_state_exposure_observed"] is True
    with (AUDIT / "paper_mechanism_conformance.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    future_chart = next(row for row in rows if row["claim"] == "chart_uses_only_information_available_by_decision_time")
    assert future_chart["status"] == "conflict_future_14_days_rendered"


def test_m009_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m009 = rows["M009"]
    assert m009["status"] == "closed_not_evaluable"
    assert m009["monthly_returns_path"] == m009["metrics_path"] == m009["run_manifest_path"] == ""
    assert m009["recipe_path"] and m009["verdict_path"] and m009["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 9
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 7
