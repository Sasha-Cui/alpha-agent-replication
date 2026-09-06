from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M063_fin_analyst"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m063_manifest_pins_hierarchy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M063"
    assert manifest["code_commit"] == "83fd39d85eb68d8e3235b91dd696d2c887cc715c"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["specialist_count"] == 8 and manifest["policy_months"] == 305
    assert manifest["resolution_counts"] == {
        "news_override": 31393,
        "majority_buy": 57662,
        "majority_sell": 58403,
        "weighted": 157542,
    }
    assert manifest["meta_action_counts"] == {"buy": 106549, "hold": 88535, "sell": 109916}
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m063_specialist_history_is_complete():
    history = pd.read_csv(OUTPUT / "specialist_history.csv")
    assert len(history) == 305
    assert history.finite_scores.eq(1000).all()
    assert (
        (
            history.news_override_count
            + history.majority_buy_count
            + history.majority_sell_count
            + history.weighted_resolution_count
        )
        .eq(1000)
        .all()
    )
    assert (history.meta_buy_count + history.meta_hold_count + history.meta_sell_count).eq(1000).all()


def test_m063_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(0.0004706611821692075)
    assert primary.full_annualized_sharpe == pytest.approx(0.081591847429827)
    assert primary.full_maximum_drawdown == pytest.approx(-0.6308029577092948)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.01412932513400109)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.511452331553097)


def test_m063_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M063"]["status"] == "completed_in_spirit"
    assert rows["M063"]["run_manifest_path"] and rows["M063"]["metrics_path"]
    assert rows["M065"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 42
    assert sum(ledger["progress_summary"].values()) == 69
