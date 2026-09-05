from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M048_alphalogics"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m048_manifest_pins_logic_evolution_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M048"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "ec521e344a8a638b5344d628dd327036ca7e2504"
    assert manifest["initial_logic_count"] == 6
    assert manifest["outer_rounds"] == 5
    assert manifest["logic_round_evaluations"] == 30
    assert manifest["candidates_evaluated"] == 108
    assert manifest["early_stops"] == 24
    assert len(manifest["selected_expressions"]) == 6
    assert manifest["selected_expressions"]["trend_persistence"] == "pair_product__ret_6_1__turnover_126d"
    assert set(manifest["selected_orientations"].values()).issubset({-1, 1})
    assert manifest["calibration_observations"] == 125306
    assert manifest["final_ridge_penalty"] == pytest.approx(408.7298425908121)
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m048_search_runs_five_persistent_logic_rounds():
    history = pd.read_csv(OUTPUT / "search_history.csv")
    assert len(history) == 30
    assert set(history.outer_round) == {1, 2, 3, 4, 5}
    assert history.market_logic.nunique() == 6
    assert history.candidates_evaluated.sum() == 108
    assert history.stopped_early.astype(bool).sum() == 24
    assert history.incumbent_orientation.isin([-1, 1]).all()
    assert history.incumbent_validation_icir.ge(0.0).all()


def test_m048_primary_path_and_fixed_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(0.029910126480622523)
    assert primary.full_annualized_sharpe == pytest.approx(0.2500414995060964)
    assert primary.full_maximum_drawdown == pytest.approx(-0.529497453644288)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.03810942412927554)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.6495445005099956)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.09903613432435619)
    assert primary.average_traded_notional == pytest.approx(2.753811452773477)


def test_m048_ledger_closes_and_advances_to_m049():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M048"]["status"] == "completed_in_spirit"
    assert rows["M048"]["recipe_path"] and rows["M048"]["run_manifest_path"]
    assert rows["M048"]["monthly_returns_path"] and rows["M048"]["metrics_path"]
    assert rows["M048"]["verdict_path"]
    assert rows["M049"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 31
    assert sum(ledger["progress_summary"].values()) == 69
