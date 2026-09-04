from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M016_marketsenseai"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m016_manifest_pins_signal_agent_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M016"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "c9a1caa23d5eb52a7537981b506748f8fb674bb7"
    assert manifest["specialist_count"] == 4
    assert manifest["policy_update_months"] == 305
    assert sum(manifest["diagnostic_action_counts"].values()) == 279742
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m016_signal_history_is_past_only_normalized_and_complete():
    history = pd.read_csv(OUTPUT / "signal_history.csv", parse_dates=["formation_month", "reliability_start", "reliability_end"])
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.reliability_months.eq(60).all()
    assert (history.reliability_end < history.formation_month).all()
    reliability = history.filter(like="reliability_weight__")
    np.testing.assert_allclose(reliability.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert history.finite_scores.min() == 748
    assert (history.buy_count + history.sell_count + history.hold_count).eq(history.finite_scores).all()


def test_m016_primary_path_and_fixed_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(-0.01262637903386521)
    assert primary.full_annualized_sharpe == pytest.approx(0.05526838292058979)
    assert primary.full_maximum_drawdown == pytest.approx(-0.815269092700901)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.03353029745397254)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.2412272744017607)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.214521801911838)
    assert primary.average_traded_notional == pytest.approx(2.0672851448778644)


def test_m016_ledger_closes_skips_discarded_m017_and_activates_m018():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M016"]["status"] == "completed_in_spirit"
    assert rows["M016"]["recipe_path"] and rows["M016"]["run_manifest_path"]
    assert rows["M016"]["monthly_returns_path"] and rows["M016"]["metrics_path"]
    assert rows["M016"]["verdict_path"]
    assert rows["M017"]["status"] == "discarded_structural_mismatch"
    assert rows["M018"]["status"] == "in_progress_in_spirit"
    assert ledger["progress_summary"] == {
        "carried_common_evaluation": 17,
        "completed_in_spirit": 12,
        "discarded_structural_mismatch": 7,
        "in_progress_in_spirit": 1,
        "queued_in_spirit": 32,
    }
