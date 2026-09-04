from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M013_finvision"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m013_manifest_pins_consensus_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M013"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "cdba88c6d04c07ebcffc091cfe535e24eb2a022a"
    assert manifest["upstream_agent_count"] == 4
    assert manifest["policy_update_months"] == 305
    assert sum(manifest["diagnostic_action_counts"].values()) == 298768
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m013_agent_history_is_past_only_normalized_and_complete():
    history = pd.read_csv(OUTPUT / "agent_history.csv", parse_dates=["formation_month", "reliability_start", "reliability_end"])
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.reliability_months.eq(60).all()
    assert (history.reliability_end < history.formation_month).all()
    reliability = history.filter(like="reliability_weight__")
    np.testing.assert_allclose(reliability.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert history.finite_scores.min() == 923
    assert (history.buy_count + history.sell_count + history.hold_count).eq(history.finite_scores).all()


def test_m013_primary_path_and_fixed_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(-0.006528437473736326)
    assert primary.full_annualized_sharpe == pytest.approx(0.12253451926157426)
    assert primary.full_maximum_drawdown == pytest.approx(-0.8754511825410425)
    assert primary.jkp_residual_mean_annualized == pytest.approx(0.014797306473683823)
    assert primary.jkp_residual_t_hac == pytest.approx(0.5431825803044341)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.5870040990950542)
    assert primary.average_traded_notional == pytest.approx(2.1034914116837706)


def test_m013_closes_ten_result_batch_without_activating_next_paper():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M013"]["status"] == "completed_in_spirit"
    assert rows["M013"]["recipe_path"] and rows["M013"]["run_manifest_path"]
    assert rows["M013"]["monthly_returns_path"] and rows["M013"]["metrics_path"]
    assert rows["M013"]["verdict_path"]
    assert rows["M014"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 10
    assert sum(ledger["progress_summary"].values()) == 69
