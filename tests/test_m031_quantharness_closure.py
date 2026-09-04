from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M031_quantharness"
AUDIT = ROOT / "paper_runs/paper_replication_audits/quantharness"


def test_m031_selects_the_multi_agent_method_and_rejects_proxies():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv250909995"
    config = recipe["paper_configuration"]
    assert config["native_bar_frequencies"] == ["1-hour", "4-hour"]
    assert config["released_analysis_window_bars"] == 45
    assert config["pattern_chart_window_bars"] == 40
    assert config["forecast_horizon_bars"] == 3
    assert config["decision_set"] == ["LONG", "SHORT"]
    assert config["hold_allowed"] is False
    assert len(recipe["required_formation_inputs"]) == 5
    assert len(recipe["rejected_substitutes"]) == 5
    assert "prior rank(ret_1_0)" in recipe["rejected_substitutes"][0]["route"]


def test_m031_matches_the_pinned_paper_and_source_execution_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    assert recipe["paper_pdf_sha256"] == manifest["paper_sha256"]
    assert recipe["source_commit"] == manifest["source_commit"]
    assert manifest["released_benchmark_csv_files"] == 1600
    assert manifest["paper_numeric_result_cells_total"] == 272
    assert manifest["version_specific_paper_numeric_result_cells_total"] == 600
    assert manifest["native_paper_result_cells_reproduced"] == 0
    assert manifest["historical_native_predictions_evaluators_returns_or_portfolio_paths"] is False
    with (AUDIT / "source_config_conformance.csv").open(newline="") as handle:
        rows = {row["dimension"]: row for row in csv.DictReader(handle)}
    assert rows["agent_architecture"]["status"] == "mismatch"
    assert rows["held_out_last_three_bars"]["status"] == "not_implemented_in_active_public_path"
    assert rows["paper_experiment_entrypoint"]["status"] == "missing"
    assert rows["agent_predictions_and_outputs"]["status"] == "missing"


def test_m031_records_the_monthly_jkp_input_gap_without_private_data_dependency():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract = json.loads((ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json").read_text())
    schema = recipe["common_task_schema_evidence"]
    assert schema["jkp_columns"] == contract["data"]["observed_schema_columns"] == 444
    assert contract["starting_settings_retained_from_corrected_us_study"]["rebalance_frequency"] == "monthly"
    assert schema["exact_required_ohlc_fields_absent"] == [
        "Open", "High", "Low", "Close", "open", "high", "low", "close"
    ]
    assert "prc" in schema["exact_source_fields_present"]
    assert all(name not in contract["factor_columns"] for name in ["char__open", "char__high", "char__low", "char__close"])


def test_m031_has_no_return_artifact_and_advances_the_ledger():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m031 = rows["M031"]
    assert m031["status"] == "closed_not_evaluable"
    assert m031["monthly_returns_path"] == m031["metrics_path"] == m031["run_manifest_path"] == ""
    assert m031["recipe_path"] and m031["verdict_path"] and m031["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 31
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 25
