from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M025_contesttrade"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m025_manifest_pins_both_contests_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M025"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "7a5d5df7274a1db147b0241c7f7998330e710d29"
    assert manifest["data_agent_count"] == 16
    assert manifest["research_agent_count"] == 5
    assert manifest["policy_update_months"] == 305
    assert manifest["mean_data_selected_count"] == pytest.approx(7.475409836065574)
    assert manifest["data_no_positive_fallback_months"] == 0
    assert manifest["research_no_positive_fallback_months"] == 8
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m025_contests_are_past_only_budgeted_and_positive_weighted():
    history = pd.read_csv(
        OUTPUT / "contest_history.csv",
        parse_dates=[
            "formation_month",
            "data_history_start",
            "data_history_end",
            "research_history_start",
            "research_history_end",
        ],
    )
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.data_history_months.eq(24).all()
    assert history.research_history_months.eq(24).all()
    assert (history.data_history_end < history.formation_month).all()
    assert (history.research_history_end < history.formation_month).all()
    assert history.data_candidate_count.eq(16).all()
    assert history.data_selected_count.between(1, 8).all()
    assert history.research_agent_count.eq(5).all()
    allocations = history.filter(like="allocation__")
    np.testing.assert_allclose(allocations.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert allocations.ge(0).all().all()
    assert history.finite_scores.min() == 844


def test_m025_primary_path_and_fixed_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(0.0016654946993603925)
    assert primary.full_annualized_sharpe == pytest.approx(0.12790454077467645)
    assert primary.full_maximum_drawdown == pytest.approx(-0.7725939793161626)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.06957121812707431)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.6582362336637955)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.09726979399014792)
    assert primary.average_traded_notional == pytest.approx(2.1830766095318936)


def test_m025_ledger_closes_skips_carried_m026_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M025"]["status"] == "completed_in_spirit"
    assert rows["M025"]["recipe_path"] and rows["M025"]["run_manifest_path"]
    assert rows["M025"]["monthly_returns_path"] and rows["M025"]["metrics_path"]
    assert rows["M025"]["verdict_path"]
    assert rows["M026"]["status"] == "carried_common_evaluation"
    assert rows["M027"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 17
    assert sum(ledger["progress_summary"].values()) == 69
