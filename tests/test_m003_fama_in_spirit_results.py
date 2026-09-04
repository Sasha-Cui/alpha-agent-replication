from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M003_fama"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m003_in_spirit_manifest_pins_frozen_inputs_code_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract_path = ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json"
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == recipe["milestone_id"] == "M003"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["contract_sha256"] == digest(contract_path)
    assert manifest["code_commit"] == "f92fdc71e36098e3c896d6389f85b6a893ce7907"
    assert manifest["candidate_count"] == 51
    assert manifest["selection_months"] == 305
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m003_in_spirit_selection_is_strictly_past_trained_and_complete():
    selection = pd.read_csv(OUTPUT / "selection_history.csv", parse_dates=["formation_month", "training_start", "training_end"])
    assert len(selection) == 305
    assert selection.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert selection.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert selection.training_months.eq(60).all()
    assert selection.cluster_count.eq(7).all()
    assert selection.eligible_candidates.eq(51).all()
    assert selection.selected_1.ne(selection.selected_2).all()
    assert (selection.training_end < selection.formation_month).all()


def test_m003_in_spirit_primary_path_and_negative_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    assert path.finite_signal_count.min() == 847
    np.testing.assert_allclose(path.gross_exposure, 2.0, rtol=0, atol=1e-12)
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(-0.005918125080627057)
    assert primary.full_annualized_sharpe == pytest.approx(0.04742447675645922)
    assert primary.full_maximum_drawdown == pytest.approx(-0.6341363848441941)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.0035677963018997515)
    assert primary.jkp_residual_t_hac == pytest.approx(-0.09946671750324519)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.9207677124062403)
    assert primary.average_traded_notional == pytest.approx(2.90907164809134)


def test_m003_in_spirit_ledger_closes_result_and_advances_once():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M003"]["status"] == "completed_in_spirit"
    assert rows["M003"]["recipe_path"] and rows["M003"]["run_manifest_path"]
    assert rows["M003"]["monthly_returns_path"] and rows["M003"]["metrics_path"]
    assert rows["M003"]["verdict_path"]
    assert rows["M004"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 1
    assert sum(ledger["progress_summary"].values()) == 69
