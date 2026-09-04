from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M029_tradinggroup"
AUDIT = ROOT / "paper_runs/paper_replication_audits/tradinggroup"


def test_m029_preserves_baseline_success_without_promoting_it():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250817565"
    assert "Five-agent daily trading system" in recipe["headline_strategy"]
    assert recipe["paper_configuration"]["training_trajectories"] == 1080
    assert recipe["paper_configuration"]["peft_base"] == "Qwen3-8B"
    assert recipe["recovered_baseline_credit"]["source_adjacent_baseline_cells"] == "156/156"
    assert recipe["recovered_baseline_credit"]["native_tradinggroup_credit"] == 0
    assert len(recipe["missing_headline_objects"]) == 6
    assert len(recipe["rejected_substitutes"]) == 5
    assert "remain credited as baseline results" in recipe["result_policy"]


def test_m029_matches_data_baseline_and_native_result_boundaries():
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    assert manifest["test_ticker_data_claims_reproduced"] == manifest["test_ticker_data_claims_total"] == 5
    assert manifest["deterministic_baseline_cells_matching_paper"] == 120
    assert manifest["model_baseline_cells_matching_paper"] == 36
    assert manifest["source_adjacent_baseline_cells_matching_paper"] == 156
    assert manifest["paper_result_credit_for_finsaber_baselines_is_native_credit"] is False
    assert manifest["qwen3_trader_checkpoint_recovered"] is False
    assert manifest["native_tradinggroup_table_cells_regenerated"] == 0
    assert manifest["unique_native_tradinggroup_table_cells"] == 120
    assert manifest["native_tradinggroup_figure_series_regenerated"] == 0
    assert manifest["native_tradinggroup_figure_series"] == 15
    with (AUDIT / "test_dataset_audit.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 5
    assert all(row["matches_paper_claims"] == "True" for row in rows)
    assert all(row["native_agent_result_credit"] == "False" for row in rows)


def test_m029_has_no_native_return_artifact():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m029 = rows["M029"]
    assert m029["status"] == "closed_not_evaluable"
    assert m029["monthly_returns_path"] == m029["metrics_path"] == m029["run_manifest_path"] == ""
    assert m029["recipe_path"] and m029["verdict_path"] and m029["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 29
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 23
