from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M036_factfin"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m036_manifest_pins_counterfactual_search_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M036"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "db3077c70f95989eaf093d7629ff99c805af8e55"
    assert manifest["component_count"] == 4
    assert manifest["mcts_evaluations"] == 100
    summary = manifest["search_summary"]
    assert summary["selected_weights"] == pytest.approx(
        [0.140740740741, 0.74074074074, 0.118518518519]
    )
    assert summary["selected_training_mean_rankic"] == pytest.approx(0.021862564821770413)
    assert summary["validation_rankic"] == pytest.approx(0.023690139315984942)
    assert summary["prediction_consistency"] == pytest.approx(0.7105517443353025)
    assert summary["confidence_invariance"] == pytest.approx(0.8185305232062801)
    assert summary["input_dependency_score"] == pytest.approx(0.28093553464655313)
    assert summary["counterfactual_objective"] == pytest.approx(0.011208671987034648)
    assert summary["distinct_programs"] == 94
    assert summary["counterfactual_finalists"] == 10
    assert summary["counterfactual_scenarios"] == 50
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m036_mcts_and_counterfactual_selection_are_complete():
    history = pd.read_csv(OUTPUT / "search_history.csv")
    assert len(history) == 100
    assert history.iteration.tolist() == list(range(1, 101))
    assert history.depth.max() <= 10
    assert history.node_id.nunique() == 100
    assert history.counterfactual_finalist.sum() == 10
    assert history.selected_final.sum() == 1
    selected = history.loc[history.selected_final].iloc[0]
    assert selected.node_id == 87
    assert selected.depth == 3
    assert selected.counterfactual_objective == pytest.approx(0.011208671987034648)
    assert np.isfinite(
        history.loc[
            history.counterfactual_finalist,
            [
                "validation_rankic",
                "prediction_consistency",
                "confidence_invariance",
                "input_dependency_score",
                "counterfactual_objective",
            ],
        ].to_numpy(dtype=float)
    ).all()


def test_m036_primary_path_and_fixed_positive_raw_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(0.044425160567125976)
    assert primary.full_annualized_sharpe == pytest.approx(0.35002938856010823)
    assert primary.full_maximum_drawdown == pytest.approx(-0.39255806590653775)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.003168739273127275)
    assert primary.jkp_residual_t_hac == pytest.approx(-0.17990685570746057)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.8572256929456843)
    assert primary.average_traded_notional == pytest.approx(1.1933828107253335)


def test_m036_ledger_closes_and_advances_to_m037():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M036"]["status"] == "completed_in_spirit"
    assert rows["M036"]["recipe_path"] and rows["M036"]["run_manifest_path"]
    assert rows["M036"]["monthly_returns_path"] and rows["M036"]["metrics_path"]
    assert rows["M036"]["verdict_path"]
    assert rows["M037"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 24
    assert sum(ledger["progress_summary"].values()) == 69
