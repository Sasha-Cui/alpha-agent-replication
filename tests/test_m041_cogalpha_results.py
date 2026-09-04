from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M041_cogalpha"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m041_outputs_reconstruct_complete_result_and_hashes():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract_path = ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json"
    component_path = ROOT / "paper_runs/paper_replication_audits/cogalpha/component_execution.json"
    contract = json.loads(contract_path.read_text())
    assert manifest["status"] == "evaluated_partial"
    assert manifest["milestone_id"] == recipe["milestone_id"] == "M041"
    assert manifest["candidate_id"] == recipe["candidate_id"]
    assert manifest["benchmark_id"] == contract["benchmark_id"]
    assert manifest["contract_sha256"] == sha256(contract_path)
    assert manifest["recipe_sha256"] == sha256(OUTPUT / "recipe.json")
    assert manifest["component_execution_sha256"] == sha256(component_path)
    assert manifest["prior_jkp_outcomes_seen"] is True
    assert manifest["confirmatory_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert sha256(OUTPUT / name) == expected
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    assert len(path) == 305
    assert path.month.iloc[0] == "1999-08-31"
    assert path.month.iloc[-1] == "2024-12-31"
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    assert path.finite_signal_count.min() >= 992
    assert path.n_long.min() >= 99
    assert path.n_short.min() >= 99
    np.testing.assert_allclose(path.gross_exposure, 2.0, atol=1e-12, rtol=0)
    np.testing.assert_allclose(
        path.net_return,
        path.gross_return - 0.001 * path.traded_notional,
        atol=1e-15,
        rtol=0,
    )
    rebuilt = return_statistics(path.net_return.to_numpy())
    for key, value in rebuilt.items():
        assert manifest["primary_result"][f"full_{key}"] == pytest.approx(value)


def test_m041_negative_primary_and_adverse_results_are_frozen_without_tuning():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    assert len(metrics) == 6
    assert metrics.primary.astype(str).str.lower().eq("true").sum() == 1
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    gross = metrics.loc[metrics.case.eq("zero_cost_0")].iloc[0]
    adverse = metrics.loc[metrics.case.eq("adverse_100_cost_10")].iloc[0]
    assert primary.cost_bps_one_way == 10
    assert primary.full_cagr == pytest.approx(-0.0402902459885383)
    assert primary.full_annualized_sharpe == pytest.approx(-0.2807967376845891)
    assert primary.full_maximum_drawdown == pytest.approx(-0.6874126927683348)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.0156393475572962)
    assert primary.jkp_residual_t_hac == pytest.approx(-0.894721111087728)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.370936190549776)
    assert primary.exploratory_bonferroni69_p == 1.0
    assert gross.full_cagr == pytest.approx(-0.0212677058311894)
    assert gross.jkp_residual_p_two_sided == pytest.approx(0.7362624026887558)
    assert adverse.full_cagr == pytest.approx(-0.2462701915721104)
    assert adverse.full_maximum_drawdown == pytest.approx(-0.9992427624400682)
    zero_cases = metrics.loc[metrics.missing_return_policy.eq("zero")].sort_values("cost_bps_one_way")
    assert zero_cases.full_cagr.is_monotonic_decreasing


def test_m041_attribution_coverage_and_partial_claim_boundary_are_explicit():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert primary.evaluation_months == 185
    assert primary.evaluation_start == "2009-08-31"
    assert primary.evaluation_end == "2024-12-31"
    assert primary.hac_lags == 4
    assert primary.average_traded_notional == pytest.approx(1.629916064239653)
    assert primary.annualized_linear_cost_drag == pytest.approx(0.019558992770875836)
    assert primary.maximum_missing_forward_gross_weight < 0.132
    residuals = pd.read_csv(OUTPUT / "attribution_residuals.csv")
    assert len(residuals) == 6 * 185
    assert residuals.groupby("case").size().eq(185).all()
    assert np.isfinite(residuals[["net_return", "factor_replication_return", "residual"]]).all().all()
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_for_execution"
    assert len(recipe["full_system_not_reproduced"]) == 7
    verdict = (OUTPUT / "verdict.md").read_text()
    assert "central partial adaptation" in verdict
    assert "option **B**" in verdict


def test_m041_ledger_records_partial_evaluation():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m041 = rows["M041"]
    assert m041["status"] == "completed_partial"
    assert m041["implementation_path"] == "scripts/run_cogalpha_evolved_factor_milestone.py"
    assert m041["monthly_returns_path"] and m041["metrics_path"] and m041["run_manifest_path"]
    assert m041["recipe_path"] and m041["verdict_path"] and m041["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 41
    assert ledger["progress_summary"]["completed_partial"] >= 7
