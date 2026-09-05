from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M038_p1gpt"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m038_manifest_pins_layered_workflow_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M038"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "7f47c3cb0d876b3c203c5e35d78a3b1b6a2d8296"
    assert manifest["layer_count"] == 5
    assert manifest["agent_count"] == 9
    assert manifest["policy_update_months"] == 305
    assert manifest["aggregate_actions"] == {
        "buy": 119664,
        "hold": 55938,
        "sell": 118659,
    }
    assert manifest["confidence_forced_holds"] == 4755
    assert manifest["mean_confidence"] == pytest.approx(0.6468271222115969)
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m038_workflow_runs_five_layers_nine_agents_and_confidence_holds():
    history = pd.read_csv(OUTPUT / "workflow_history.csv", parse_dates=["formation_month"])
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.layer_count.eq(5).all()
    assert history.agent_count.eq(9).all()
    assert history.domain_agent_count.eq(4).all()
    assert history.supporting_agent_count.eq(4).all()
    assert history.integrated_report_count.eq(7).all()
    assert history.mean_confidence.between(0.0, 1.0).all()
    assert history.conflict_hold_count.sum() == 4755
    assert (history.buy_count + history.hold_count + history.sell_count).eq(
        history.finite_scores
    ).all()
    assert history.finite_scores.min() == 930


def test_m038_primary_path_and_fixed_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(0.0028420141857861125)
    assert primary.full_annualized_sharpe == pytest.approx(0.1106572961405768)
    assert primary.full_maximum_drawdown == pytest.approx(-0.5434383252002097)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.005968796738828408)
    assert primary.jkp_residual_t_hac == pytest.approx(-0.2518221232669956)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.8011785563678478)
    assert primary.average_traded_notional == pytest.approx(1.6636531657261513)


def test_m038_ledger_closes_and_advances_to_m039():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M038"]["status"] == "completed_in_spirit"
    assert rows["M038"]["recipe_path"] and rows["M038"]["run_manifest_path"]
    assert rows["M038"]["monthly_returns_path"] and rows["M038"]["metrics_path"]
    assert rows["M038"]["verdict_path"]
    assert rows["M039"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 26
    assert sum(ledger["progress_summary"].values()) == 69
