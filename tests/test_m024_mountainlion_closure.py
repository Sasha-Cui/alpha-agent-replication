from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M024_mountainlion"
AUDIT = ROOT / "paper_runs/paper_replication_audits/mountainlion"


def test_m024_closes_forecast_components_without_inventing_portfolio():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250720474"
    assert "Four-agent crypto forecasting" in recipe["headline_strategy"]
    assert len(recipe["paper_configuration"]["tokens"]) == 10
    assert recipe["paper_configuration"]["verbatim_prompt_templates"] == 7
    assert recipe["released_component_credit"]["public_history_commits_scanned"] == 2273
    assert recipe["released_component_credit"]["exact_native_paper_mechanisms"] == 0
    assert len(recipe["missing_headline_objects"]) == 7
    assert len(recipe["rejected_substitutes"]) == 5
    assert "no auditable trading return" in recipe["result_policy"]


def test_m024_matches_product_component_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    assert manifest["attributable_public_repositories"] == 2
    assert manifest["frontend_repeated_build_byte_identical"] is True
    assert manifest["backend_paper_time_core_compiles"] is True
    assert manifest["paper_corresponding_source_component_checks_passed"] == 7
    assert manifest["exact_native_paper_mechanism_dimensions_reproduced"] == 0
    assert manifest["reachable_public_commits_audited"] == 2273
    assert manifest["historical_serialized_result_or_model_artifact_paths_found"] == 0
    assert manifest["native_result_generation_pipeline_found"] is False
    assert manifest["published_performance_result_units_faithfully_regenerated"] == 0
    assert manifest["published_performance_result_units"] == 20
    with (AUDIT / "mechanism_conformance.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    portfolio = next(row for row in rows if row["dimension"] == "portfolio/trading rule")
    returns = next(row for row in rows if row["dimension"] == "return evaluation")
    assert portfolio["status"] == returns["status"] == "missing"


def test_m024_has_no_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m024 = rows["M024"]
    assert m024["status"] == "closed_not_evaluable"
    assert m024["monthly_returns_path"] == m024["metrics_path"] == m024["run_manifest_path"] == ""
    assert m024["recipe_path"] and m024["verdict_path"] and m024["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 24
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 19
