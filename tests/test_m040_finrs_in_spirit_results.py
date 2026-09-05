from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M040_finrs"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m040_manifest_pins_risk_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M040"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "800927a235a1d340ee352ffdc338cbae32717731"
    assert manifest["memory_layer_count"] == 3
    assert manifest["decision_agent_count"] == 2
    assert manifest["policy_update_months"] == 305
    assert manifest["mean_base_absolute_position"] == pytest.approx(0.27549913406880455)
    assert manifest["mean_final_absolute_exposure"] == pytest.approx(0.04371209106664782)
    assert manifest["mean_scaled_kelly"] == pytest.approx(0.10268935212287524)
    assert manifest["mean_volatility_adjustment"] == pytest.approx(0.49541126413803627)
    assert manifest["total_risk_shrunk"] == 256775
    assert manifest["total_risk_zeroed"] == 93887
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m040_risk_controls_are_purged_bounded_and_shrinking():
    history = pd.read_csv(
        OUTPUT / "risk_history.csv",
        parse_dates=[
            "formation_month",
            "label_cutoff",
            "reward_history_start",
            "reward_history_end",
        ],
    )
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.reward_history_months.eq(60).all()
    assert (history.reward_history_end <= history.label_cutoff).all()
    assert (history.label_cutoff < history.formation_month).all()
    assert history.mean_win_probability.between(0.5, 0.75).all()
    assert history.mean_payoff_odds.between(0.5, 2.0).all()
    assert history.mean_scaled_kelly.ge(0.0).all()
    assert history.mean_volatility_adjustment.between(0.0, 1.0).all()
    assert history.mean_cvar_cap.between(0.0, 0.75).all()
    assert history.mean_final_absolute_exposure.le(history.mean_base_absolute_position).all()
    assert history.risk_shrunk_count.gt(0).all()
    assert history.risk_shrunk_count.sum() == 256775
    assert history.risk_zeroed_count.sum() == 93887
    assert history.finite_scores.eq(1000).all()


def test_m040_primary_path_and_fixed_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(
        path.net_return,
        path.gross_return - 0.001 * path.traded_notional,
        rtol=0,
        atol=1e-15,
    )
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(-0.009323071061867694)
    assert primary.full_annualized_sharpe == pytest.approx(-0.04230528895442908)
    assert primary.full_maximum_drawdown == pytest.approx(-0.4860185153069079)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.013118221603206647)
    assert primary.jkp_residual_t_hac == pytest.approx(-0.7784760116167114)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.4362884430859195)
    assert primary.average_traded_notional == pytest.approx(0.5880928015371659)


def test_m040_ledger_closes_and_advances_to_m042():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M040"]["status"] == "completed_in_spirit"
    assert rows["M040"]["recipe_path"] and rows["M040"]["run_manifest_path"]
    assert rows["M040"]["monthly_returns_path"] and rows["M040"]["metrics_path"]
    assert rows["M040"]["verdict_path"]
    assert rows["M042"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 28
    assert sum(ledger["progress_summary"].values()) == 69
