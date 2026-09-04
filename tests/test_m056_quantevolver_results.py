from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M056_quantevolver"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m056_outputs_pin_the_frozen_partial_and_hashes():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract_path = ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json"
    contract = json.loads(contract_path.read_text())
    assert manifest["status"] == "evaluated_partial"
    assert manifest["milestone_id"] == recipe["milestone_id"] == "M056"
    assert manifest["candidate_id"] == recipe["candidate_id"]
    assert manifest["benchmark_id"] == contract["benchmark_id"]
    assert manifest["contract_sha256"] == sha256(contract_path)
    assert manifest["recipe_sha256"] == sha256(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "605f4f0d4c9ced8114e69a781a3afbb73dd7c1bd"
    assert manifest["prior_jkp_outcomes_seen"] is True
    assert manifest["confirmatory_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert sha256(OUTPUT / name) == expected


def test_m056_primary_path_uses_complete_common_calendar_and_accounting():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    assert len(path) == 305
    assert path.month.iloc[0] == "1999-08-31"
    assert path.month.iloc[-1] == "2024-12-31"
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    assert path.finite_signal_count.min() == 653
    np.testing.assert_allclose(path.gross_exposure, 2.0, rtol=0, atol=1e-12)
    np.testing.assert_array_equal(path.n_long, path.n_short)
    np.testing.assert_allclose(
        path.net_return,
        path.gross_return - 0.001 * path.traded_notional,
        rtol=0,
        atol=1e-15,
    )
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    rebuilt = return_statistics(path.net_return.to_numpy())
    for key, value in rebuilt.items():
        assert manifest["primary_result"][f"full_{key}"] == pytest.approx(value)


def test_m056_first_seed_is_weak_and_not_distinct_from_jkp():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    assert len(metrics) == 6
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    adverse = metrics.loc[metrics.case.eq("adverse_100_cost_10")].iloc[0]
    assert primary.full_cagr == pytest.approx(-0.007967440857434949)
    assert primary.full_annualized_sharpe == pytest.approx(0.05617618707998742)
    assert primary.full_maximum_drawdown == pytest.approx(-0.7378985961144163)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.006994800095552825)
    assert primary.jkp_residual_t_hac == pytest.approx(-0.22695750359984498)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.8204567871047782)
    assert primary.exploratory_bonferroni69_p == 1.0
    assert primary.average_traded_notional == pytest.approx(0.7781383123077067)
    assert adverse.full_cagr == pytest.approx(-0.04577890380605232)
    zero_cases = metrics.loc[metrics.missing_return_policy.eq("zero")].sort_values("cost_bps_one_way")
    assert zero_cases.full_cagr.is_monotonic_decreasing


def test_m056_ledger_records_the_evaluated_central_partial():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M056"]
    assert milestone["status"] == "completed_partial"
    assert milestone["implementation_path"] == "scripts/run_quantevolver_headline.py"
    assert milestone["recipe_path"] and milestone["run_manifest_path"]
    assert milestone["monthly_returns_path"] and milestone["metrics_path"]
    assert milestone["verdict_path"] and milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 56
    assert ledger["progress_summary"]["completed_partial"] >= 11
