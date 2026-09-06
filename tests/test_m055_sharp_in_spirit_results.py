from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M055_sharp"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m055_manifest_pins_evolution_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M055"
    assert manifest["code_commit"] == "51ce6bfa9fddbd4c0fc2d28743afe111f783b49f"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["initial_rule_count"] == 6
    assert manifest["walk_forward_blocks"] == 13
    assert manifest["evolution_rounds"] == 65
    assert manifest["accepted_mutation_rounds"] == 17
    assert manifest["best_update_rounds"] == 7
    assert manifest["distinct_frozen_rubrics"] == 4
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m055_rubric_windows_and_mutations_are_complete():
    blocks = pd.read_csv(OUTPUT / "rubric_block_history.csv")
    evolution = pd.read_csv(OUTPUT / "rubric_evolution_history.csv")
    assert len(blocks) == 13 and blocks.test_months.sum() == 305
    assert blocks.rule_count.eq(6).all()
    assert blocks.minimum_finite_scores.eq(1000).all()
    assert len(evolution) == 65 and evolution.groupby("block").size().eq(5).all()
    assert evolution.worst_month_count.eq(20).all()
    assert evolution.proposed_mutation_count.between(0, 3).all()


def test_m055_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(0.029607549930612764)
    assert primary.full_annualized_sharpe == pytest.approx(0.25326119228266397)
    assert primary.full_maximum_drawdown == pytest.approx(-0.50709995829169)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.010243094462884262)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.6814929688190757)


def test_m055_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M055"]["status"] == "completed_in_spirit"
    assert rows["M055"]["run_manifest_path"] and rows["M055"]["metrics_path"]
    assert rows["M057"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 38
    assert sum(ledger["progress_summary"].values()) == 69
