from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M050_agentic_screening"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m050_manifest_and_outputs_are_pinned():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M050"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "3836a8d0043881729531206b1dff397034560957"
    assert manifest["screening_agent_count"] == 2
    assert manifest["formation_history_months"] == 180
    assert manifest["policy_update_months"] == 305
    assert manifest["aggregate_actions"] == {"buy": 16862, "hold": 226879, "sell": 61259}
    assert manifest["buy_union_fallback_months"] == 44
    assert manifest["sell_union_fallback_months"] == 0
    assert manifest["conflict_stock_months"] == 0
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m050_screening_path_is_complete():
    history = pd.read_csv(OUTPUT / "screening_history.csv")
    assert len(history) == 305
    assert (history.final_buy_count + history.final_hold_count + history.final_sell_count).eq(1000).all()
    assert history.finite_scores.eq(1000).all()
    assert history.finite_precision_count.min() == 523
    assert history.buy_union_fallback.sum() == 44
    assert history.sell_union_fallback.sum() == 0


def test_m050_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(-0.020619239265633138)
    assert primary.full_annualized_sharpe == pytest.approx(-0.1286807983451857)
    assert primary.full_maximum_drawdown == pytest.approx(-0.5431141034138103)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.025648355733468346)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.10268706324865189)


def test_m050_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M050"]["status"] == "completed_in_spirit"
    assert rows["M050"]["run_manifest_path"] and rows["M050"]["metrics_path"]
    assert rows["M051"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 33
    assert sum(ledger["progress_summary"].values()) == 69
