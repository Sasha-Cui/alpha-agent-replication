from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M028_treevo"
AUDIT = ROOT / "paper_runs/paper_replication_audits/treevo"


def test_m028_closes_search_without_inventing_a_factor():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250816334"
    assert "TreEvo evolves hierarchical thought trees" in recipe["headline_strategy"]
    assert recipe["paper_configuration"]["population"] == 10
    assert recipe["paper_configuration"]["evaluation_budget"] == 200
    assert recipe["paper_configuration"]["mutation_probabilities"] == {"root": 0.4, "internal": 0.4, "fine": 0.2}
    assert recipe["recovered_component_credit"]["prompt_templates"] == 7
    assert recipe["recovered_component_credit"]["traditional_operator_names"] == 22
    assert recipe["recovered_component_credit"]["generated_factor_expressions"] == 0
    assert len(recipe["missing_headline_objects"]) == 6
    assert len(recipe["rejected_substitutes"]) == 5


def test_m028_matches_prompt_operator_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    assert manifest["attributable_implementation_source_files_recovered"] == 0
    assert manifest["prompt_templates_recovered_v2"] == 7
    assert manifest["actual_runtime_prompt_calls_recovered"] == 0
    assert manifest["conditional_metric_component_executed"] is True
    assert manifest["paper_result_credit_for_metric_component"] is False
    assert manifest["published_result_cells_faithfully_regenerated_v1"] == 0
    assert manifest["published_numeric_result_units_v1"] == 114
    assert manifest["published_result_cells_faithfully_regenerated_v2"] == 0
    assert manifest["published_numeric_result_units_v2"] == 293
    with (AUDIT / "method_specification_audit.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    outputs = next(row for row in rows if row["dimension"] == "factor_outputs")
    converter = next(row for row in rows if row["dimension"] == "code_generation")
    assert outputs["status"] == converter["status"] == "missing"


def test_m028_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m028 = rows["M028"]
    assert m028["status"] == "closed_not_evaluable"
    assert m028["monthly_returns_path"] == m028["metrics_path"] == m028["run_manifest_path"] == ""
    assert m028["recipe_path"] and m028["verdict_path"] and m028["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 28
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 22
