from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M047_blindtrade"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m047_manifest_pins_graph_intent_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M047"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "e196e1acbf50a0929c3a9313c707fbd79bf4addb"
    assert manifest["agent_count"] == 4
    assert manifest["semantic_graph_layers"] == 2
    assert manifest["policy_update_months"] == 305
    assert manifest["intent_counts"] == {"defensive": 163, "neutral": 33, "aggressive": 109}
    assert sum(manifest["intent_counts"].values()) == 305
    assert manifest["mean_semantic_neighbors"] == pytest.approx(9.999898360655738)
    assert manifest["zero_semantic_neighbors"] == 0
    assert manifest["mean_absolute_proposed_score"] == pytest.approx(0.3754477194374795)
    assert manifest["mean_absolute_inertial_score"] == pytest.approx(0.2684342432416211)
    assert manifest["stale_score_resets"] == 5989
    assert sum(manifest["mean_agent_reliability"].values()) == pytest.approx(1.0)
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m047_policy_is_purged_graph_based_and_inertial():
    history = pd.read_csv(
        OUTPUT / "policy_history.csv",
        parse_dates=[
            "formation_month",
            "agent_ic_cutoff",
            "agent_ic_history_start",
            "agent_ic_history_end",
            "intent_reward_cutoff",
            "intent_reward_history_start",
            "intent_reward_history_end",
        ],
    )
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.agent_ic_history_months.eq(60).all()
    assert history.intent_reward_history_months.eq(60).all()
    assert (history.agent_ic_history_end <= history.agent_ic_cutoff).all()
    assert (history.intent_reward_history_end <= history.intent_reward_cutoff).all()
    assert (history.agent_ic_cutoff < history.formation_month).all()
    assert (history.intent_reward_cutoff < history.formation_month).all()
    assert set(history.selected_intent) == {"defensive", "neutral", "aggressive"}
    reliability = history.filter(like="agent_reliability__")
    np.testing.assert_allclose(reliability.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert history.mean_semantic_neighbors.between(0.0, 10.0).all()
    assert history.zero_neighbor_count.eq(0).all()
    assert history.mean_absolute_inertial_score.le(1.0).all()
    assert history.finite_scores.eq(1000).all()


def test_m047_primary_path_and_fixed_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(-0.08025653151810008)
    assert primary.full_annualized_sharpe == pytest.approx(-0.1744884291097868)
    assert primary.full_maximum_drawdown == pytest.approx(-0.8807306259666909)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.007710066699191015)
    assert primary.jkp_residual_t_hac == pytest.approx(-0.25740366999893255)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.7968671700668672)
    assert primary.average_traded_notional == pytest.approx(0.8107942438823907)


def test_m047_ledger_closes_and_advances_to_m048():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M047"]["status"] == "completed_in_spirit"
    assert rows["M047"]["recipe_path"] and rows["M047"]["run_manifest_path"]
    assert rows["M047"]["monthly_returns_path"] and rows["M047"]["metrics_path"]
    assert rows["M047"]["verdict_path"]
    assert rows["M048"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 30
    assert sum(ledger["progress_summary"].values()) == 69
