from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M037_atlas"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m037_manifest_pins_adaptive_opro_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M037"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "52a8cbd0b542a7be4529340a40ef93b9b4a1194d"
    assert manifest["analyst_count"] == 3
    assert manifest["optimization_windows"] == 61
    assert manifest["prompt_updates"] == 60
    assert manifest["mean_feedback_score"] == pytest.approx(51.44606526089644)
    assert manifest["final_used_prompt"] == pytest.approx(
        {
            "market_weight": 0.011533150790569222,
            "news_weight": 0.01349964230933486,
            "fundamental_weight": 0.974967206900096,
            "hold_threshold": 0.4,
        }
    )
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m037_optimization_is_windowed_forward_only_and_template_bounded():
    history = pd.read_csv(
        OUTPUT / "optimization_history.csv",
        parse_dates=["window_start", "window_end"],
    )
    assert len(history) == 61
    assert history.prompt_version.tolist() == list(range(61))
    assert history.window_decisions.eq(5).all()
    assert history.update_applied.iloc[:-1].all()
    assert not history.update_applied.iloc[-1]
    np.testing.assert_allclose(
        history.feedback_score,
        np.clip(50.0 + 250.0 * history.window_roi, 0.0, 100.0),
        rtol=0,
        atol=1e-12,
    )
    current = history[[
        "analyst_weight__market",
        "analyst_weight__news",
        "analyst_weight__fundamental",
    ]]
    following = history[[
        "next_analyst_weight__market",
        "next_analyst_weight__news",
        "next_analyst_weight__fundamental",
    ]]
    np.testing.assert_allclose(current.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    np.testing.assert_allclose(following.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert history.hold_threshold.between(0.0, 0.4).all()
    assert history.finite_scores.eq(5000).all()
    assert (history.buy_count + history.hold_count + history.sell_count).eq(5000).all()


def test_m037_primary_path_and_fixed_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(0.013320026914594774)
    assert primary.full_annualized_sharpe == pytest.approx(0.1635627327880511)
    assert primary.full_maximum_drawdown == pytest.approx(-0.4777995484641163)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.041105585264564336)
    assert primary.jkp_residual_t_hac == pytest.approx(-2.2881336688247433)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.02212973806338985)
    assert primary.average_traded_notional == pytest.approx(0.7926671082364681)


def test_m037_ledger_closes_and_advances_to_m038():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M037"]["status"] == "completed_in_spirit"
    assert rows["M037"]["recipe_path"] and rows["M037"]["run_manifest_path"]
    assert rows["M037"]["monthly_returns_path"] and rows["M037"]["metrics_path"]
    assert rows["M037"]["verdict_path"]
    assert rows["M038"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 25
    assert sum(ledger["progress_summary"].values()) == 69
