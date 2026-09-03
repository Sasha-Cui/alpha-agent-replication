from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M010_llmfactor"
AUDIT = ROOT / "paper_runs/paper_replication_audits/llmfactor"


def test_m010_closes_the_prediction_pipeline_without_promoting_components():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv240610811"
    assert "Three-stage LLMFactor pipeline" in recipe["headline_strategy"]
    assert recipe["paper_configuration"]["lookback_periods"] == 5
    assert recipe["paper_configuration"]["factor_count"] == 5
    assert recipe["conditionally_verified_components"] == {
        "english_prompt_skeletons_rendered": 3,
        "metric_formulas_executed": 2,
        "llm_calls_made": 0,
    }
    assert len(recipe["missing_headline_objects"]) == 7
    assert len(recipe["rejected_substitutes"]) == 5
    assert "remain unresolved" in recipe["result_policy"]


def test_m010_matches_native_and_community_audit_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    native = json.loads((AUDIT / "native_execution.json").read_text())
    provenance = json.loads((AUDIT / "source_provenance.json").read_text())
    assert manifest["native_llmfactor_result_cells"] == 82
    assert manifest["native_llmfactor_result_cells_reproduced"] == 0
    assert manifest["displayed_result_cells"] == 206
    assert manifest["displayed_result_cells_reproduced"] == 0
    assert manifest["author_linked_code_found"] is False
    assert native["llm_calls_made"] == 0
    assert native["community_repository_native_credit"] is False
    assert provenance["official_source_contains_native_code"] is False
    assert provenance["official_source_contains_raw_results"] is False
    with (AUDIT / "community_method_conformance.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    leaked = next(row for row in rows if row["repository"] == "Kuon12138/SKGP" and row["dimension"] == "saved AAPL result")
    assert leaked["assessment"] == "target_leakage"
    assert leaked["native_credit"] == leaked["paper_result_credit"] == "no"


def test_m010_has_no_return_artifact_and_closes_batch_of_ten():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m010 = rows["M010"]
    assert m010["status"] == "closed_not_evaluable"
    assert m010["monthly_returns_path"] == m010["metrics_path"] == m010["run_manifest_path"] == ""
    assert m010["recipe_path"] and m010["verdict_path"] and m010["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 10
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 8
