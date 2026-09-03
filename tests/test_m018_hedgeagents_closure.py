from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M018_hedgeagents"
AUDIT = ROOT / "paper_runs/paper_replication_audits/hedgeagents"


def test_m018_closes_static_site_without_promoting_profiles_or_risk_proxy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250213165"
    assert "Four-agent cross-asset" in recipe["headline_strategy"]
    assert recipe["paper_configuration"]["budget_cycle_days"] == 30
    assert recipe["paper_configuration"]["memory_top_k"] == 5
    assert recipe["recovered_component_credit"]["unique_tool_names"] == 23
    assert recipe["recovered_component_credit"]["unique_action_names"] == 10
    assert recipe["recovered_component_credit"]["system_source_files"] == 0
    assert len(recipe["missing_headline_objects"]) == 7
    assert len(recipe["rejected_substitutes"]) == 5


def test_m018_matches_static_artifact_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    native = json.loads((AUDIT / "native_execution.json").read_text())
    assert manifest["public_system_source_files_recovered"] == 0
    assert manifest["author_site_corroborated_main_table_cells"] == 90
    assert manifest["unique_profile_tool_names"] == 23
    assert manifest["unique_profile_action_names"] == 10
    assert manifest["hedgeagents_own_cells_faithfully_regenerated"] == 0
    assert manifest["hedgeagents_own_numeric_table_cells"] == 126
    assert manifest["published_numeric_table_cells_faithfully_regenerated"] == 0
    assert manifest["published_numeric_table_cells"] == 236
    assert manifest["published_figure_panels"] == 25
    assert manifest["published_figures_with_exact_dated_underlying_values"] == 0
    assert native["hedgeagents_pipeline_executed"] is False
    with (AUDIT / "internal_consistency_audit.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    risk = next(row for row in rows if row["claim_id"] == "risk_equation_symbols_and_cvar")
    assert risk["status"] == "mathematical_specification_ambiguous"


def test_m018_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m018 = rows["M018"]
    assert m018["status"] == "closed_not_evaluable"
    assert m018["monthly_returns_path"] == m018["metrics_path"] == m018["run_manifest_path"] == ""
    assert m018["recipe_path"] and m018["verdict_path"] and m018["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 18
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 16
