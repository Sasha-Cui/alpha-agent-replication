from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M039_finpos"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m039_manifest_pins_position_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M039"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "e1384e7b8f0a950352b2dfe72f111aaa714122cd"
    assert manifest["memory_layer_count"] == 3
    assert manifest["decision_agent_count"] == 2
    assert manifest["policy_update_months"] == 305
    assert manifest["aggregate_directions"] == {
        "buy": 102341,
        "hold": 101305,
        "sell": 101354,
    }
    assert manifest["mean_absolute_position"] == pytest.approx(0.27549913406880455)
    assert manifest["mean_trade_quantity"] == pytest.approx(0.02318596797697346)
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m039_positions_are_carried_purged_and_cvar_bounded():
    history = pd.read_csv(
        OUTPUT / "position_history.csv",
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
    reliability = history.filter(like="memory_reliability__")
    np.testing.assert_allclose(reliability.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert history.minimum_cvar_position_cap.ge(0.25).all()
    assert history.mean_cvar_position_cap.le(1.0).all()
    assert history.mean_trade_quantity.between(0.0, 0.25).all()
    assert (
        history.position_increase_count
        + history.position_decrease_count
        + history.position_unchanged_count
    ).eq(1000).all()
    assert history.stale_position_resets.sum() == 5989
    assert history.finite_scores.eq(1000).all()


def test_m039_primary_path_and_fixed_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(-0.003292138565471836)
    assert primary.full_annualized_sharpe == pytest.approx(0.02471979566581508)
    assert primary.full_maximum_drawdown == pytest.approx(-0.5226146907996824)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.011559437727184058)
    assert primary.jkp_residual_t_hac == pytest.approx(-0.6533588080301207)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.5135249880189648)
    assert primary.average_traded_notional == pytest.approx(0.39237860767347277)


def test_m039_ledger_closes_and_advances_to_m040():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M039"]["status"] == "completed_in_spirit"
    assert rows["M039"]["recipe_path"] and rows["M039"]["run_manifest_path"]
    assert rows["M039"]["monthly_returns_path"] and rows["M039"]["metrics_path"]
    assert rows["M039"]["verdict_path"]
    assert rows["M040"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 27
    assert sum(ledger["progress_summary"].values()) == 69
