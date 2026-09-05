from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M029_tradinggroup"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m029_manifest_pins_reflection_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M029"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "84e14e14086f4cfd46fabb5b95a4e6967071b9fd"
    assert manifest["agent_count"] == 5
    assert manifest["policy_update_months"] == 305
    assert manifest["style_selection_counts"] == {
        "aggressive": 96,
        "balanced": 26,
        "conservative": 183,
    }
    assert manifest["risk_intercepted_recommendations"] == 18755
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m029_reflection_is_past_only_and_style_risk_is_active():
    history = pd.read_csv(
        OUTPUT / "reflection_history.csv",
        parse_dates=[
            "formation_month",
            "forecast_reflection_start",
            "forecast_reflection_end",
            "style_reflection_start",
            "style_reflection_end",
        ],
    )
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.forecast_reflection_months.eq(60).all()
    assert history.style_reflection_months.eq(20).all()
    assert (history.forecast_reflection_end < history.formation_month).all()
    assert (history.style_reflection_end < history.formation_month).all()
    assert set(history.selected_style) == {"aggressive", "balanced", "conservative"}
    reliability = history.filter(like="agent_reliability__")
    np.testing.assert_allclose(reliability.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert reliability.ge(0).all().all()
    assert history.risk_intercept_count.sum() == 18755
    assert history.finite_scores.min() == 677


def test_m029_primary_path_and_fixed_negative_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(-0.021763480542315805)
    assert primary.full_annualized_sharpe == pytest.approx(0.03385859111894459)
    assert primary.full_maximum_drawdown == pytest.approx(-0.7982800063431935)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.04652338084276211)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.9456570504652828)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.05169594906344197)
    assert primary.average_traded_notional == pytest.approx(1.9367863850241767)


def test_m029_ledger_closes_and_advances_to_m030():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M029"]["status"] == "completed_in_spirit"
    assert rows["M029"]["recipe_path"] and rows["M029"]["run_manifest_path"]
    assert rows["M029"]["monthly_returns_path"] and rows["M029"]["metrics_path"]
    assert rows["M029"]["verdict_path"]
    assert rows["M030"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 20
    assert sum(ledger["progress_summary"].values()) == 69
