from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M010_llmfactor"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m010_manifest_pins_sequential_predictor_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M010"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "4512af39a48b5336a06f731eed0bfb9e99c8baad"
    assert manifest["factor_candidate_count"] == 8
    assert manifest["selected_factor_count"] == 5
    assert manifest["policy_update_months"] == 305
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m010_prediction_history_is_past_only_and_complete():
    history = pd.read_csv(OUTPUT / "prediction_history.csv", parse_dates=["formation_month", "training_start", "training_end"])
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.training_months.eq(60).all()
    assert (history.training_end < history.formation_month).all()
    assert history.peer_relation_coverage.min() > 900
    assert history.five_price_history_coverage.min() > 750
    assert history.finite_scores.min() == 620
    assert history.filter(regex=r"^factor_[1-5]$").nunique(axis=1).eq(5).all()


def test_m010_primary_path_and_fixed_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(-0.08130816355518056)
    assert primary.full_annualized_sharpe == pytest.approx(-0.26449910138450544)
    assert primary.full_maximum_drawdown == pytest.approx(-0.9172563679702314)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.055496089199863506)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.710811079024062)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.08711599369838367)
    assert primary.average_traded_notional == pytest.approx(2.8923970853421914)


def test_m010_ledger_closes_and_advances_once_to_m011():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M010"]["status"] == "completed_in_spirit"
    assert rows["M010"]["recipe_path"] and rows["M010"]["run_manifest_path"]
    assert rows["M010"]["monthly_returns_path"] and rows["M010"]["metrics_path"]
    assert rows["M010"]["verdict_path"]
    assert rows["M011"]["status"] == "in_progress_in_spirit"
    assert ledger["progress_summary"] == {
        "carried_common_evaluation": 17,
        "completed_in_spirit": 7,
        "discarded_structural_mismatch": 7,
        "in_progress_in_spirit": 1,
        "queued_in_spirit": 37,
    }
