from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M009_finagent"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m009_manifest_pins_multimodal_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M009"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "7613e2c7eec826ed80b23b971a9a103843d2984e"
    assert manifest["memory_query_count"] == 3
    assert manifest["policy_update_months"] == 305
    assert sum(manifest["selected_tool_counts"].values()) == 305
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m009_reflection_history_is_past_only_and_complete():
    history = pd.read_csv(OUTPUT / "reflection_history.csv", parse_dates=["formation_month", "training_start", "training_end"])
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.training_months.eq(60).all()
    assert (history.training_end < history.formation_month).all()
    assert history.selected_tool.isin(["medium_term_momentum", "short_term_reversal", "price_breakout"]).all()
    assert history.finite_scores.min() == 813
    for query in ("short", "medium", "long"):
        assert history[f"{query}_memory_coverage"].min() > 750
        assert history[f"{query}_mean_retrieved"].between(0, 5).all()


def test_m009_primary_path_and_fixed_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(-0.05857522412771943)
    assert primary.full_annualized_sharpe == pytest.approx(-0.1431162751879432)
    assert primary.full_maximum_drawdown == pytest.approx(-0.8453626790806159)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.04463804480445786)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.2495852755214794)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.2114510846982629)
    assert primary.average_traded_notional == pytest.approx(2.8878151989241325)


def test_m009_ledger_closes_and_advances_once_to_m010():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M009"]["status"] == "completed_in_spirit"
    assert rows["M009"]["recipe_path"] and rows["M009"]["run_manifest_path"]
    assert rows["M009"]["monthly_returns_path"] and rows["M009"]["metrics_path"]
    assert rows["M009"]["verdict_path"]
    assert rows["M010"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 6
    assert sum(ledger["progress_summary"].values()) == 69
