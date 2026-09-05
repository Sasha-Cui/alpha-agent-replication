from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M032_trading_r1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m032_manifest_pins_reward_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M032"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "a335f1f4ec09641d20e10f4af36d99e2f94031e6"
    assert manifest["reasoning_stage_count"] == 3
    assert manifest["action_count"] == 5
    assert manifest["policy_update_months"] == 305
    assert manifest["aggregate_action_counts"] == {
        "STRONG SELL": 0,
        "SELL": 0,
        "HOLD": 322,
        "BUY": 304678,
        "STRONG BUY": 0,
    }
    assert manifest["mean_group_relative_advantage"] == pytest.approx(0.5356756086869524)
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m032_policy_uses_purged_past_labels_and_records_action_collapse():
    history = pd.read_csv(
        OUTPUT / "policy_history.csv",
        parse_dates=["formation_month", "label_cutoff", "training_start", "training_end"],
    )
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.policy_training_months.eq(60).all()
    assert (history.training_end <= history.label_cutoff).all()
    assert (history.label_cutoff < history.formation_month).all()
    assert history.training_rows.min() == 37592
    assert history.mean_group_relative_advantage.gt(0).all()
    action_counts = history.filter(like="action_count__")
    assert action_counts.sum(axis=1).eq(1000).all()
    assert action_counts.action_count__buy.sum() == 304678
    assert action_counts.action_count__hold.sum() == 322
    assert history.finite_scores.eq(1000).all()


def test_m032_primary_path_and_fixed_negative_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(-0.06822913241767925)
    assert primary.full_annualized_sharpe == pytest.approx(-0.34128406816033324)
    assert primary.full_maximum_drawdown == pytest.approx(-0.9212693952952586)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.08315495578610808)
    assert primary.jkp_residual_t_hac == pytest.approx(-2.4843305804957585)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.012979525310416894)
    assert primary.average_traded_notional == pytest.approx(2.5686064055467397)


def test_m032_ledger_closes_skips_carried_m033_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M032"]["status"] == "completed_in_spirit"
    assert rows["M032"]["recipe_path"] and rows["M032"]["run_manifest_path"]
    assert rows["M032"]["monthly_returns_path"] and rows["M032"]["metrics_path"]
    assert rows["M032"]["verdict_path"]
    assert rows["M033"]["status"] == "carried_common_evaluation"
    assert rows["M034"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 22
    assert sum(ledger["progress_summary"].values()) == 69
