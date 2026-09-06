from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M060_metaps"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m060_manifest_pins_router_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M060"
    assert manifest["code_commit"] == "559eef76d4e22a4028383122af78430d7827e924"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["strategy_count"] == 10
    assert manifest["router_update_months"] == 305
    assert manifest["counterfactual_rollout_months"] == 437
    assert manifest["selected_strategy_counts"] == {
        "macro_rotation": 72,
        "mean_revert_fade": 47,
        "momentum_follow": 46,
        "risk_reset": 43,
        "cross_asset_hedge": 39,
        "small_cap_breakout": 30,
        "news_impulse": 11,
        "liquidity_rebate": 11,
        "earnings_drift": 4,
        "volatility_breakout": 2,
    }
    assert manifest["exposure_bucket_counts"] == {"small": 267, "medium": 35, "large": 3}
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m060_router_history_and_rollouts_are_complete():
    history = pd.read_csv(OUTPUT / "router_history.csv")
    rollouts = pd.read_csv(OUTPUT / "counterfactual_rollouts.csv")
    assert len(history) == 305 and len(rollouts) == 437
    assert history.training_examples.eq(120).all()
    assert history.finite_scores.eq(1000).all()
    assert set(history.selected_strategy) == set(rollouts.columns) - {"formation_month"}
    assert history.filter(like="v3_label_count__").sum(axis=1).eq(120).all()
    np.testing.assert_allclose(history.filter(like="router_probability__").sum(axis=1), 1.0, atol=1e-14)


def test_m060_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(-0.050194165265137536)
    assert primary.full_annualized_sharpe == pytest.approx(-0.05531287010738562)
    assert primary.full_maximum_drawdown == pytest.approx(-0.9137785045637139)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.06403485577456887)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.22268144013390623)


def test_m060_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M060"]["status"] == "completed_in_spirit"
    assert rows["M060"]["run_manifest_path"] and rows["M060"]["metrics_path"]
    assert rows["M061"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 40
    assert sum(ledger["progress_summary"].values()) == 69
