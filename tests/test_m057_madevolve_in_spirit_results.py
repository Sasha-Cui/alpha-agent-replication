from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M057_madevolve"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m057_manifest_pins_search_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M057"
    assert manifest["code_commit"] == "6f215d929d9e09d147bf750c566bd5a23e414171"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["candidate_library_size"] == 40
    assert manifest["walk_forward_blocks"] == 13
    assert manifest["generation_records"] == 195
    assert manifest["total_proposals"] == 1950
    assert manifest["block_unique_programs"] == 1875
    assert manifest["patch_proposals"] == 1379
    assert manifest["rewrite_proposals"] == 571
    assert manifest["parent_improvements"] == 602
    assert manifest["migration_transfers"] == 195
    assert manifest["distinct_frozen_programs"] == 13
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m057_program_windows_and_generations_are_complete():
    blocks = pd.read_csv(OUTPUT / "program_block_history.csv")
    evolution = pd.read_csv(OUTPUT / "generation_history.csv")
    assert len(blocks) == 13 and blocks.test_months.sum() == 305
    assert blocks.term_count.between(2, 5).all()
    assert blocks.minimum_finite_scores.eq(1000).all()
    assert len(evolution) == 195 and evolution.groupby("block").size().eq(15).all()
    assert (evolution.patch_proposals + evolution.rewrite_proposals).eq(10).all()
    assert evolution.loc[evolution.generation.isin([5, 10, 15]), "migrants"].eq(5).all()


def test_m057_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(0.060480205463400605)
    assert primary.full_annualized_sharpe == pytest.approx(0.40248230952781916)
    assert primary.full_maximum_drawdown == pytest.approx(-0.5048012303819325)
    assert primary.jkp_residual_mean_annualized == pytest.approx(0.05485355900220875)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.16467370286964267)


def test_m057_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M057"]["status"] == "completed_in_spirit"
    assert rows["M057"]["run_manifest_path"] and rows["M057"]["metrics_path"]
    assert rows["M060"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 39
    assert sum(ledger["progress_summary"].values()) == 69
