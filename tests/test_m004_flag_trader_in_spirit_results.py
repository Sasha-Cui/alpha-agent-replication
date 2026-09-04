from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M004_flag_trader"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m004_manifest_pins_in_spirit_policy_and_all_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M004"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "4b01fb4a9930cffac4d70021ade8a0fa5b2b9396"
    assert manifest["state_feature_count"] == 4
    assert manifest["policy_update_months"] == 305
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m004_policy_history_is_past_only_complete_and_clipped():
    history = pd.read_csv(OUTPUT / "policy_history.csv", parse_dates=["formation_month", "training_start", "training_end"])
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.training_months.eq(60).all()
    assert (history.training_end < history.formation_month).all()
    assert history.clipped_gradient_norm.le(0.5 + 1e-15).all()
    assert history.parameter_delta_norm.le(0.0005 * 0.5 + 1e-15).all()
    assert history.action_memory_weight.eq(0.2).all()
    assert history.finite_current_scores.min() == 828


def test_m004_primary_path_and_fixed_negative_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(-0.0243990218007607)
    assert primary.full_annualized_sharpe == pytest.approx(0.03406998717343323)
    assert primary.full_maximum_drawdown == pytest.approx(-0.8279293838404127)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.029129794437227657)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.0967640732220172)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.272744539088553)
    assert primary.average_traded_notional == pytest.approx(1.684806061784478)


def test_m004_ledger_closes_and_advances_once_to_m005():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M004"]["status"] == "completed_in_spirit"
    assert rows["M004"]["recipe_path"] and rows["M004"]["run_manifest_path"]
    assert rows["M004"]["monthly_returns_path"] and rows["M004"]["metrics_path"]
    assert rows["M004"]["verdict_path"]
    assert rows["M005"]["status"] == "in_progress_in_spirit"
    assert ledger["progress_summary"] == {
        "carried_common_evaluation": 17,
        "completed_in_spirit": 2,
        "discarded_structural_mismatch": 7,
        "in_progress_in_spirit": 1,
        "queued_in_spirit": 42,
    }
