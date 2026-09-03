from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M012_aapm"
AUDIT = ROOT / "paper_runs/paper_replication_audits/aapm"


def test_m012_closes_hybrid_policy_without_promoting_components():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv240917266"
    assert "hybrid asset-pricing model" in recipe["headline_strategy"]
    assert recipe["paper_configuration"]["temperature"] == 0.2
    assert recipe["paper_configuration"]["portfolio_rules"] == ["TP", "EW", "VW"]
    assert recipe["released_component_credit"]["reconstructed_metadata_rows"] == 65733
    assert len(recipe["missing_headline_objects"]) == 7
    assert len(recipe["material_source_conflicts"]) == 5
    assert len(recipe["rejected_substitutes"]) == 5
    assert "positive performance claims remain unresolved" in recipe["result_policy"]


def test_m012_matches_native_component_and_missing_input_boundary():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    native = json.loads((AUDIT / "native_execution.json").read_text())
    assert manifest["end_to_end_result_cells_reproduced"] == 0
    assert manifest["v2_table_result_cells"] == 162
    assert manifest["paper_era_source_modules_imported"] == 4
    assert manifest["paper_era_memory_component_runs"] == 2
    assert manifest["paper_era_model_forward_component_runs"] == 2
    assert manifest["reconstructed_metadata_index_rows"] == 65733
    assert manifest["paper_era_analysis_reached_missing_private_input"] is True
    probe = native["metadata index analysis probe"]
    assert probe["execution_runs"] == 2
    assert probe["paper_inputs_recovered"] is False
    assert probe["runs"][0]["missing_required_fields"] == ["Tickers", "Topics", "Content"]
    assert probe["runs"][0]["llm_calls_made"] == 0
    with (AUDIT / "method_specification_audit.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    manual = next(row for row in rows if row["dimension"] == "manual financial factors")
    assert manual["assessment"] == "missing"
    assert manual["end_to_end_credit"] == "no"


def test_m012_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m012 = rows["M012"]
    assert m012["status"] == "closed_not_evaluable"
    assert m012["monthly_returns_path"] == m012["metrics_path"] == m012["run_manifest_path"] == ""
    assert m012["recipe_path"] and m012["verdict_path"] and m012["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 12
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 10
