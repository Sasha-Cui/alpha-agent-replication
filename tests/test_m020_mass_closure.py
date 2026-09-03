from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M020_mass"
AUDIT = ROOT / "paper_runs/paper_replication_audits/mass"


def test_m020_closes_distribution_state_without_inventing_agent_decisions():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250510278"
    assert recipe["paper_configuration"]["investor_types"] == 16
    assert recipe["paper_configuration"]["agents_per_type"] == 32
    assert recipe["paper_configuration"]["candidate_pool_size"] == 20
    assert recipe["paper_configuration"]["stocks_selected_per_agent"] == 5
    assert recipe["paper_configuration"]["round_trip_cost"] == 0.001
    assert recipe["recovered_component_credit"]["native_signal_nonidentifiability_proved"] is True
    assert len(recipe["missing_headline_objects"]) == 6
    assert len(recipe["source_conflicts"]) == 5
    assert len(recipe["rejected_substitutes"]) == 5


def test_m020_matches_distribution_and_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    proof = json.loads((AUDIT / "native_signal_nonidentifiability.json").read_text())
    assert manifest["native_dated_distribution_snapshot_shipped"] is True
    assert manifest["native_signal_aggregation_source_shipped"] is True
    assert manifest["native_agent_decision_cache_shipped"] is False
    assert manifest["native_dated_signal_output_shipped"] is False
    assert manifest["native_portfolio_or_return_path_shipped"] is False
    assert manifest["native_signal_nonidentifiability_proved"] is True
    assert manifest["paper_numeric_result_cells_reproduced"] == 0
    assert manifest["paper_numeric_result_cells_total"] == 766
    assert manifest["paper_empirical_figures_reproduced"] == 0
    assert manifest["paper_empirical_figures_audited"] == 5
    assert proof["same_released_distribution_in_both_scenarios"] is True
    assert proof["released_state_identifies_unique_signal"] is False
    assert proof["changed_signal_stock_count"] == 10


def test_m020_has_no_return_artifact_and_closes_batch_of_twenty():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m020 = rows["M020"]
    assert m020["status"] == "closed_not_evaluable"
    assert m020["monthly_returns_path"] == m020["metrics_path"] == m020["run_manifest_path"] == ""
    assert m020["recipe_path"] and m020["verdict_path"] and m020["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 20
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 17
