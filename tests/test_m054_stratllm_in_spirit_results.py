from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M054_stratllm"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m054_manifest_pins_alignment_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M054"
    assert manifest["code_commit"] == "0f89c5feee6fd2a534a2ea49267c024290ba518f"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["source_count"] == 3 and manifest["strategy_count"] == 4
    assert manifest["policy_update_months"] == 305
    assert manifest["mode_counts"] == {"free": 217, "strict": 48, "guided": 40}
    assert manifest["aggregate_actions"] == {"buy": 119550, "hold": 62444, "sell": 123006}
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m054_alignment_is_complete_and_stratified():
    history = pd.read_csv(OUTPUT / "alignment_history.csv")
    assert len(history) == 305
    assert history.reliability_months.eq(60).all()
    assert set(history.selected_mode) == {"free", "guided", "strict"}
    assert (history.buy_count + history.hold_count + history.sell_count).eq(1000).all()
    np.testing.assert_allclose(history.filter(like="source_reliability__").sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert history.finite_scores.eq(1000).all()


def test_m054_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(0.0339032251443423)
    assert primary.full_annualized_sharpe == pytest.approx(0.26223703712260626)
    assert primary.full_maximum_drawdown == pytest.approx(-0.5714377867839882)
    assert primary.jkp_residual_mean_annualized == pytest.approx(0.013979398084406756)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.6368176029984085)


def test_m054_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M054"]["status"] == "completed_in_spirit"
    assert rows["M054"]["run_manifest_path"] and rows["M054"]["metrics_path"]
    assert rows["M055"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 37
    assert sum(ledger["progress_summary"].values()) == 69
