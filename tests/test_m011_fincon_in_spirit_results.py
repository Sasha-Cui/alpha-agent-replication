from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M011_fincon"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m011_manifest_pins_hierarchy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M011"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "2b2d3640ea57e17b0de6af239620a14babe85dcb"
    assert manifest["analyst_count"] == 4
    assert manifest["policy_update_months"] == 305
    assert sum(manifest["final_belief_weights"].values()) == pytest.approx(1.0)
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m011_belief_history_is_past_only_normalized_and_risk_aware():
    history = pd.read_csv(OUTPUT / "belief_history.csv", parse_dates=["formation_month", "procedural_start", "procedural_end"])
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.procedural_months.eq(60).all()
    assert (history.procedural_end < history.formation_month).all()
    beliefs = history.filter(like="belief_weight__")
    np.testing.assert_allclose(beliefs.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert beliefs.gt(0).all().all()
    assert history.cvar_coverage.min() > 600
    assert history.finite_scores.min() == 534


def test_m011_primary_path_and_fixed_positive_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(0.025886336798734977)
    assert primary.full_annualized_sharpe == pytest.approx(0.2296298678337495)
    assert primary.full_maximum_drawdown == pytest.approx(-0.6465708373690175)
    assert primary.jkp_residual_mean_annualized == pytest.approx(0.003185532086962724)
    assert primary.jkp_residual_t_hac == pytest.approx(0.13971233192702417)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.8888872825079729)
    assert primary.average_traded_notional == pytest.approx(1.2477212290531863)


def test_m011_ledger_closes_and_advances_once_to_m012():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M011"]["status"] == "completed_in_spirit"
    assert rows["M011"]["recipe_path"] and rows["M011"]["run_manifest_path"]
    assert rows["M011"]["monthly_returns_path"] and rows["M011"]["metrics_path"]
    assert rows["M011"]["verdict_path"]
    assert rows["M012"]["status"] == "in_progress_in_spirit"
    assert ledger["progress_summary"] == {
        "carried_common_evaluation": 17,
        "completed_in_spirit": 8,
        "discarded_structural_mismatch": 7,
        "in_progress_in_spirit": 1,
        "queued_in_spirit": 36,
    }
