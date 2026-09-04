from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M008_alpha_gpt_2_0"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m008_manifest_pins_three_stage_pipeline_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M008"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "b58e769c7c82560485e47f6245205786af3711e7"
    assert manifest["candidate_count"] == 51
    assert manifest["selected_factor_count"] == 5
    assert manifest["policy_update_months"] == 305
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m008_pipeline_is_past_only_complete_and_runs_risk_analysis():
    history = pd.read_csv(OUTPUT / "pipeline_history.csv", parse_dates=["formation_month", "training_start", "training_end"])
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.training_months.eq(60).all()
    assert (history.training_end < history.formation_month).all()
    assert history.eligible_candidates.eq(51).all()
    assert history.selected_factors.eq(5).all()
    assert history.finite_scores.min() == 822
    assert history.high_risk_count.between(100, 210).all()


def test_m008_primary_path_and_significant_negative_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(-0.05576587927126486)
    assert primary.full_annualized_sharpe == pytest.approx(-0.23548725597190912)
    assert primary.full_maximum_drawdown == pytest.approx(-0.88446522073232)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.12063358807768912)
    assert primary.jkp_residual_t_hac == pytest.approx(-3.646942738486641)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.0002653790337575107)
    assert primary.exploratory_bonferroni69_p == pytest.approx(0.01831115332926824)


def test_m008_ledger_closes_and_advances_once_to_m009():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M008"]["status"] == "completed_in_spirit"
    assert rows["M008"]["recipe_path"] and rows["M008"]["run_manifest_path"]
    assert rows["M008"]["monthly_returns_path"] and rows["M008"]["metrics_path"]
    assert rows["M008"]["verdict_path"]
    assert rows["M009"]["status"] == "in_progress_in_spirit"
    assert ledger["progress_summary"] == {
        "carried_common_evaluation": 17,
        "completed_in_spirit": 5,
        "discarded_structural_mismatch": 7,
        "in_progress_in_spirit": 1,
        "queued_in_spirit": 39,
    }
