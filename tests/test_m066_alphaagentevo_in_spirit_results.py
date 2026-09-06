from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M066_alphaagentevo"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m066_manifest_pins_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M066"
    assert manifest["code_commit"] == "b7f9bb032ef83d01dc94bf3f12e55948c94a076c"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["candidate_library_size"] == 210
    assert manifest["training_steps"] == 150
    assert manifest["tool_call_count"] == 600
    assert manifest["elite_pool_size"] == 20
    assert manifest["selected_alpha"] == "pair_mean__ret_12_1__z_score"
    assert manifest["selected_alpha_reward"] == pytest.approx(0.8472531228359442)
    assert manifest["operator_call_counts"] == {
        "pair_product": 439,
        "pair_difference": 93,
        "pair_mean": 58,
        "identity": 10,
    }
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m066_elites_tools_and_policy_history_are_complete():
    elites = pd.read_csv(OUTPUT / "elite_pool.csv")
    tools = pd.read_csv(OUTPUT / "tool_history.csv")
    policy = pd.read_csv(OUTPUT / "policy_history.csv")
    assert len(elites) == 20 and elites.selected_final.sum() == 1
    assert len(tools) == 600 and tools.groupby("step").size().eq(4).all()
    assert len(policy) == 150 and policy.elite_pool_size.iloc[-1] == 20
    np.testing.assert_allclose(tools.groupby("step").group_relative_advantage.sum(), 0.0, atol=1e-12)


def test_m066_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(0.03987682253690927)
    assert primary.full_annualized_sharpe == pytest.approx(0.2806943563512485)
    assert primary.full_maximum_drawdown == pytest.approx(-0.6297928362215597)
    assert primary.jkp_residual_mean_annualized == pytest.approx(0.0008239470307585622)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.971076629465303)


def test_m066_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M066"]["status"] == "completed_in_spirit"
    assert rows["M066"]["run_manifest_path"] and rows["M066"]["metrics_path"]
    assert rows["M067"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 44
    assert sum(ledger["progress_summary"].values()) == 69
