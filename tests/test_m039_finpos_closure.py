from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M039_finpos"
AUDIT = ROOT / "paper_runs/paper_replication_audits/finpos"


def test_m039_selects_the_dual_agent_policy_not_future_reward_values():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv251027251"
    config = recipe["paper_configuration"]
    assert config["frequency"] == "daily close decision"
    assert config["position_update"] == "pos_t = pos_(t-1) + d_t*q_t"
    assert config["direction_set"] == [-1, 0, 1]
    assert config["training_reward_horizons_days"] == [1, 7, 30]
    assert config["native_assets"] == ["TSLA", "AAPL", "AMZN", "NFLX", "COIN"]
    assert len(recipe["missing_headline_objects"]) == 10
    assert len(recipe["rejected_substitutes"]) == 5
    assert "future 1/7/30-day prices" in recipe["rejected_substitutes"][0]["reason"]


def test_m039_matches_the_revision_aware_paper_and_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    provenance = json.loads((AUDIT / "source_provenance.json").read_text())
    assert recipe["paper_pdf_sha256"] == provenance["pinned_input_sha256"]["primary/official-v2.pdf"]
    assert recipe["paper_source_sha256"] == provenance["pinned_input_sha256"]["primary/source-v2.tar"]
    assert provenance["official_pages"]["v2"] == 22
    assert manifest["current_empirical_table_cells"] == 294
    assert manifest["v1_empirical_table_cells"] == 225
    assert manifest["author_native_table_cells_regenerated"] == 0
    assert manifest["author_native_empirical_panels_regenerated"] == 0
    assert manifest["attributable_finpos_implementation_found"] is False
    live = recipe["live_release_recheck"]
    assert live["github_repository_search_arxiv"] == 0
    assert live["github_repository_search_title"] == 0
    assert live["updated_homepage_contains_finpos"] is False
    assert live["attributable_implementation_found"] is False


def test_m039_preserves_component_credit_without_action_policy_credit():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    credit = recipe["paper_component_credit"]
    assert credit["paper_derived_mechanics_executed"] == 11
    assert credit["controlled_checks_passed"] == 11
    assert credit["valid_json_output_examples"] == 4
    with (AUDIT / "component_execution_audit.csv").open(newline="") as handle:
        components = list(csv.DictReader(handle))
    assert len(components) == 11
    assert all(row["deterministic_control_passed"] == "True" for row in components)
    assert all(row["author_native_pipeline_executed"] == "False" for row in components)
    assert all(row["paper_result_credit"] == "False" for row in components)
    with (AUDIT / "method_specification_audit.csv").open(newline="") as handle:
        method = {row["dimension"]: row for row in csv.DictReader(handle)}
    assert method["native implementation"]["status"] == "unreleased"
    assert method["position sizing"]["status"] == "equation_underspecified"
    assert method["multi-timescale reward"]["status"] == "equation_partial"
    assert method["raw empirical outputs"]["status"] == "missing"


def test_m039_has_no_return_artifact_and_advances_the_ledger():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m039 = rows["M039"]
    assert m039["status"] == "closed_not_evaluable"
    assert m039["monthly_returns_path"] == m039["metrics_path"] == m039["run_manifest_path"] == ""
    assert m039["recipe_path"] and m039["verdict_path"] and m039["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 39
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 32
