from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M046_factorengine"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m046_outputs_reconstruct_the_frozen_partial_and_hashes():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract_path = ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json"
    assert manifest["status"] == "evaluated_partial"
    assert manifest["milestone_id"] == recipe["milestone_id"] == "M046"
    assert manifest["candidate_id"] == recipe["candidate_id"]
    assert manifest["contract_sha256"] == sha256(contract_path)
    assert manifest["recipe_sha256"] == sha256(OUTPUT / "recipe.json")
    assert manifest["prior_jkp_outcomes_seen"] is True
    assert manifest["confirmatory_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert sha256(OUTPUT / name) == expected


def test_m046_path_preserves_complete_decile_accounting():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    assert path.finite_signal_count.min() == 928
    assert path.n_long.min() == path.n_short.min() == 92
    np.testing.assert_allclose(path.gross_exposure, 2.0, atol=1e-12, rtol=0)
    np.testing.assert_allclose(
        path.net_return, path.gross_return - 0.001 * path.traded_notional, atol=1e-15, rtol=0
    )
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    for key, value in return_statistics(path.net_return.to_numpy()).items():
        assert manifest["primary_result"][f"full_{key}"] == pytest.approx(value)


def test_m046_weak_zero_cost_signal_and_negative_net_result_are_frozen():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    gross = metrics.loc[metrics.case.eq("zero_cost_0")].iloc[0]
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    adverse = metrics.loc[metrics.case.eq("adverse_100_cost_10")].iloc[0]
    assert gross.full_cagr == pytest.approx(-0.009105465960881576)
    assert gross.full_arithmetic_annualized_return == pytest.approx(0.0037292274479997257)
    assert gross.jkp_residual_p_two_sided == pytest.approx(0.6176481623462802)
    assert primary.full_cagr == pytest.approx(-0.0366979371580024)
    assert primary.full_annualized_sharpe == pytest.approx(-0.1550999972482473)
    assert primary.full_maximum_drawdown == pytest.approx(-0.695714373735833)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.016683578004524996)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.48202816723307274)
    assert primary.average_traded_notional == pytest.approx(2.346326322303297)
    assert primary.annualized_linear_cost_drag == pytest.approx(0.028155915867639564)
    assert adverse.full_cagr == pytest.approx(-0.1409567160995494)
    zero_cases = metrics.loc[metrics.missing_return_policy.eq("zero")].sort_values("cost_bps_one_way")
    assert zero_cases.full_cagr.is_monotonic_decreasing


def test_m046_ledger_records_the_repaired_central_partial():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M046"]
    assert milestone["status"] == "completed_partial"
    assert milestone["implementation_path"] == "scripts/run_factorengine_evolved_factor_milestone.py"
    assert milestone["recipe_path"] and milestone["run_manifest_path"]
    assert milestone["monthly_returns_path"] and milestone["metrics_path"] and milestone["verdict_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 46
    assert ledger["progress_summary"]["completed_partial"] >= 10
