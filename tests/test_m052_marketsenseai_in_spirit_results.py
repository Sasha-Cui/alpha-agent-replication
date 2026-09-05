from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M052_marketsenseai"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m052_manifest_pins_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M052"
    assert manifest["code_commit"] == "976685c0f9e8a297773809b275c3cafad4d10fcc"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["specialist_count"] == 4 and manifest["policy_update_months"] == 305
    assert manifest["diagnostic_action_counts"] == {
        "strong_sell": 5431,
        "sell": 8407,
        "hold": 246263,
        "buy": 23773,
        "strong_buy": 21126,
    }
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m052_classes_are_complete_and_strongbuy_is_rare():
    history = pd.read_csv(OUTPUT / "signal_history.csv")
    assert len(history) == 305
    classes = history[["strong_sell_count", "sell_count", "hold_count", "buy_count", "strong_buy_count"]]
    assert classes.sum(axis=1).eq(1000).all()
    assert history.strong_buy_count.between(0, 75).all()
    assert history.finite_scores.eq(1000).all()
    np.testing.assert_allclose(history.filter(like="reliability_weight__").sum(axis=1), 1.0, rtol=0, atol=1e-14)


def test_m052_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(-0.007867100347754286)
    assert primary.full_annualized_sharpe == pytest.approx(0.07264697522070097)
    assert primary.full_maximum_drawdown == pytest.approx(-0.7668631650819634)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.03536259252092923)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.17452457617864303)


def test_m052_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M052"]["status"] == "completed_in_spirit"
    assert rows["M052"]["run_manifest_path"] and rows["M052"]["metrics_path"]
    assert rows["M053"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 35
    assert sum(ledger["progress_summary"].values()) == 69
