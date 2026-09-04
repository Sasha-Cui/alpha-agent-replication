from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M033_guruagents_buffett"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m033_outputs_reconstruct_the_complete_long_only_result_and_hashes():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract_path = ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json"
    audit_path = ROOT / "paper_runs/paper_replication_audits/guruagents/source_prompt_conformance.csv"
    contract = json.loads(contract_path.read_text())
    assert manifest["status"] == "evaluated_partial"
    assert manifest["milestone_id"] == recipe["milestone_id"] == "M033"
    assert manifest["candidate_id"] == recipe["candidate_id"]
    assert manifest["benchmark_id"] == contract["benchmark_id"]
    assert manifest["contract_sha256"] == sha256(contract_path)
    assert manifest["recipe_sha256"] == sha256(OUTPUT / "recipe.json")
    assert manifest["source_prompt_conformance_sha256"] == sha256(audit_path)
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
    assert path.finite_signal_count.eq(1000).all()
    assert path.n_short.eq(0).all()
    assert path.n_long.min() >= 900
    np.testing.assert_allclose(path.gross_exposure, 1.0, atol=1e-12, rtol=0)
    np.testing.assert_allclose(
        path.net_return,
        path.gross_return - 0.001 * path.traded_notional,
        atol=1e-15,
        rtol=0,
    )
    rebuilt = return_statistics(path.net_return.to_numpy())
    for key, value in rebuilt.items():
        assert manifest["primary_result"][f"full_{key}"] == pytest.approx(value)


def test_m033_common_cost_result_and_adverse_missing_sensitivity_are_explicit():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    assert len(metrics) == 7
    assert metrics.primary.astype(str).str.lower().eq("true").sum() == 1
    assert metrics.paper_cost.astype(str).str.lower().eq("true").sum() == 1
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    paper_cost = metrics.loc[metrics.paper_cost.astype(str).str.lower().eq("true")].iloc[0]
    adverse = metrics.loc[metrics.case.eq("adverse_100_cost_10")].iloc[0]
    assert primary.missing_return_policy == "zero"
    assert primary.cost_bps_one_way == 10
    assert primary.full_cagr == pytest.approx(0.07931531391034419)
    assert primary.full_annualized_sharpe == pytest.approx(0.5321978023358448)
    assert primary.full_maximum_drawdown == pytest.approx(-0.5134746630857945)
    assert primary.jkp_residual_mean_annualized == pytest.approx(0.006475457836175428)
    assert primary.jkp_residual_t_hac == pytest.approx(1.3643731887906898)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.17245014175915052)
    assert primary.exploratory_bonferroni69_p == 1.0
    assert paper_cost.cost_bps_one_way == 1
    assert paper_cost.full_cagr > primary.full_cagr
    assert adverse.full_cagr == pytest.approx(0.0222305655085168)
    assert adverse.jkp_residual_mean_annualized == pytest.approx(-0.0423257414625334)
    zero_cases = metrics.loc[metrics.missing_return_policy.eq("zero")].sort_values("cost_bps_one_way")
    assert zero_cases.full_cagr.is_monotonic_decreasing


def test_m033_rolling_attribution_and_claim_boundary_are_complete():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert primary.evaluation_months == 185
    assert primary.evaluation_start == "2009-08-31"
    assert primary.evaluation_end == "2024-12-31"
    assert primary.hac_lags == 4
    assert primary.minimum_finite_signal_count == 1000
    assert primary.maximum_missing_forward_gross_weight < 0.021
    residuals = pd.read_csv(OUTPUT / "attribution_residuals.csv")
    assert len(residuals) == 7 * 185
    assert residuals.groupby("case").size().eq(185).all()
    assert np.isfinite(residuals[["net_return", "factor_replication_return", "residual"]]).all().all()
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_for_execution"
    assert len(recipe["excluded_source_behaviors"]) == 6
    verdict = (OUTPUT / "verdict.md").read_text()
    assert "not a full-paper replication" in verdict
    assert "option **B**" in verdict


def test_m033_ledger_records_a_partial_evaluation_not_a_native_replication():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m033 = rows["M033"]
    assert m033["status"] == "completed_partial"
    assert m033["implementation_path"] == "scripts/run_guruagents_buffett_milestone.py"
    assert m033["monthly_returns_path"] and m033["metrics_path"] and m033["run_manifest_path"]
    assert m033["recipe_path"] and m033["verdict_path"] and m033["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 33
    assert ledger["progress_summary"]["completed_partial"] >= 6
