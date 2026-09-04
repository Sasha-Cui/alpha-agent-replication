from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M020_mass"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m020_manifest_pins_mass_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M020"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "c2e33607f216fd08a6f405b825daaee91b90a63f"
    assert manifest["investor_type_count"] == 16
    assert manifest["agents_per_type"] == 32
    assert manifest["policy_update_months"] == 305
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m020_simulation_is_past_only_and_runs_the_frozen_agent_population():
    history = pd.read_csv(
        OUTPUT / "simulation_history.csv",
        parse_dates=["formation_month", "annealing_start", "annealing_end"],
    )
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.annealing_history_months.eq(60).all()
    assert history.annealing_iterations.eq(100).all()
    assert (history.annealing_end < history.formation_month).all()
    assert history.total_agent_selections.eq(16 * 32 * 5).all()
    assert history.finite_scores.min() == 1000
    assert history.accepted_proposals.between(0, 100).all()

    weights = history.filter(like="type_weight__")
    np.testing.assert_allclose(weights.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert weights.ge(0).all().all()
    orientations = history.filter(like="orientation__")
    assert set(np.unique(orientations.to_numpy())) <= {-1, 1}


def test_m020_primary_path_and_fixed_negative_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(-0.06553665090487193)
    assert primary.full_annualized_sharpe == pytest.approx(-0.439721356110393)
    assert primary.full_maximum_drawdown == pytest.approx(-0.8729749843312773)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.054128233386003415)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.6109144259983574)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.10719837528906757)
    assert primary.average_traded_notional == pytest.approx(3.1301928914433454)


def test_m020_ledger_closes_skips_carried_m021_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M020"]["status"] == "completed_in_spirit"
    assert rows["M020"]["recipe_path"] and rows["M020"]["run_manifest_path"]
    assert rows["M020"]["monthly_returns_path"] and rows["M020"]["metrics_path"]
    assert rows["M020"]["verdict_path"]
    assert rows["M021"]["status"] == "carried_common_evaluation"
    assert rows["M022"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 14
    assert sum(ledger["progress_summary"].values()) == 69
