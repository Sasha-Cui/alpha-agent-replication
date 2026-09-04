from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M018_hedgeagents"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m018_manifest_pins_conference_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M018"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "dec1209e830c1d071cd46393c0e75da335d886b7"
    assert manifest["specialist_count"] == 3
    assert manifest["policy_update_months"] == 305
    assert manifest["extreme_conference_months"] == 127
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m018_conference_is_past_only_allocated_and_defensive_when_extreme():
    history = pd.read_csv(OUTPUT / "conference_history.csv", parse_dates=["formation_month", "conference_start", "conference_end"])
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.conference_months.eq(60).all()
    assert (history.conference_end < history.formation_month).all()
    allocations = history.filter(like="allocation__")
    np.testing.assert_allclose(allocations.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert allocations.ge(0.1 / 3 - 1e-14).all().all()
    assert history.loc[history.extreme_conference, "allocation__defensive"].ge(0.5).all()
    assert history.finite_scores.min() == 994


def test_m018_primary_path_and_fixed_positive_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(0.04738755373265002)
    assert primary.full_annualized_sharpe == pytest.approx(0.32319800034659846)
    assert primary.full_maximum_drawdown == pytest.approx(-0.5317525713337165)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.0014476422356601475)
    assert primary.jkp_residual_t_hac == pytest.approx(-0.07660736103706818)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.9389359029043314)
    assert primary.average_traded_notional == pytest.approx(1.298592443485702)


def test_m018_ledger_closes_skips_carried_m019_and_activates_m020():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M018"]["status"] == "completed_in_spirit"
    assert rows["M018"]["recipe_path"] and rows["M018"]["run_manifest_path"]
    assert rows["M018"]["monthly_returns_path"] and rows["M018"]["metrics_path"]
    assert rows["M018"]["verdict_path"]
    assert rows["M019"]["status"] == "carried_common_evaluation"
    assert rows["M020"]["status"] == "in_progress_in_spirit"
    assert ledger["progress_summary"] == {
        "carried_common_evaluation": 17,
        "completed_in_spirit": 13,
        "discarded_structural_mismatch": 7,
        "in_progress_in_spirit": 1,
        "queued_in_spirit": 31,
    }
