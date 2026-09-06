from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M053_alphacrafter"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m053_manifest_pins_workflow_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M053"
    assert manifest["code_commit"] == "dc00e22eff081470cd4a7f4101950c46709f71ed"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["miner_count"] == 3 and manifest["candidate_count"] == 48
    assert manifest["policy_update_months"] == 305
    assert manifest["unique_selected_candidates"] == 44
    assert manifest["regime_counts"] == {"uptrend": 261, "downtrend": 44}
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m053_workflow_is_complete_and_diverse():
    history = pd.read_csv(OUTPUT / "workflow_history.csv")
    assert len(history) == 305
    assert history.maintenance_months.eq(60).all()
    assert history.selected_factor_count.eq(5).all()
    assert history.selected_miners.str.split("|").map(len).ge(2).all()
    assert history.finite_scores.eq(1000).all()


def test_m053_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(-0.06489901135559173)
    assert primary.full_annualized_sharpe == pytest.approx(-0.07624693196093849)
    assert primary.full_maximum_drawdown == pytest.approx(-0.9440550595375486)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.07808434604664151)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.05624047998841627)


def test_m053_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M053"]["status"] == "completed_in_spirit"
    assert rows["M053"]["run_manifest_path"] and rows["M053"]["metrics_path"]
    assert rows["M054"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 36
    assert sum(ledger["progress_summary"].values()) == 69
