from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M034_quantagents"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m034_manifest_pins_meeting_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M034"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "606d680daea72712cb58d6da55543f92a098c296"
    assert manifest["agent_count"] == 4
    assert manifest["memory_type_count"] == 3
    assert manifest["policy_update_months"] == 305
    assert manifest["risk_alert_months"] == 57
    assert manifest["mean_simulated_reward_weight"] == pytest.approx(0.4184118545960414)
    assert sum(manifest["strategy_proposal_counts"].values()) == 305 * 3
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m034_meetings_use_past_memory_dual_rewards_and_trigger_risk():
    history = pd.read_csv(
        OUTPUT / "meeting_history.csv",
        parse_dates=["formation_month", "memory_start", "memory_end"],
    )
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.memory_history_months.eq(120).all()
    assert (history.memory_end < history.formation_month).all()
    assert history.memory_type_count.eq(3).all()
    assert history.retrieved_similar_cases.eq(10).all()
    assert history.strategy_pool_size.eq(10).all()
    assert history.proposed_strategy_members.str.count("\\|").eq(2).all()
    np.testing.assert_allclose(
        history.simulated_reward_weight + history.real_reward_weight,
        1.0,
        rtol=0,
        atol=1e-15,
    )
    assert history.risk_alert_triggered.sum() == 57
    assert history.risk_score.between(0.0, 1.0).all()
    assert history.finite_scores.min() == 645


def test_m034_primary_path_and_fixed_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(0.006413463297187061)
    assert primary.full_annualized_sharpe == pytest.approx(0.13170664028668982)
    assert primary.full_maximum_drawdown == pytest.approx(-0.5382614973416144)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.05966291168306681)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.5594217696766839)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.11889658709159767)
    assert primary.average_traded_notional == pytest.approx(2.208296994111927)


def test_m034_ledger_closes_skips_discarded_m035_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M034"]["status"] == "completed_in_spirit"
    assert rows["M034"]["recipe_path"] and rows["M034"]["run_manifest_path"]
    assert rows["M034"]["monthly_returns_path"] and rows["M034"]["metrics_path"]
    assert rows["M034"]["verdict_path"]
    assert rows["M035"]["status"] == "discarded_structural_mismatch"
    assert rows["M036"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 23
    assert sum(ledger["progress_summary"].values()) == 69
