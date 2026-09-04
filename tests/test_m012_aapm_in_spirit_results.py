from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M012_aapm"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m012_manifest_pins_hybrid_model_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M012"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "36361aa8dc9222fa38d95f9284e9cb6aa8ecd4a1"
    assert manifest["hybrid_feature_count"] == 23
    assert manifest["policy_update_months"] == 305
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m012_pretraining_is_past_only_complete_and_hybrid():
    history = pd.read_csv(OUTPUT / "pretraining_history.csv", parse_dates=["formation_month", "pretraining_start", "pretraining_end"])
    catalog = pd.read_csv(OUTPUT / "hybrid_feature_catalog.csv")
    assert len(history) == 305
    assert len(catalog) == 23
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.pretraining_months.eq(120).all()
    assert (history.pretraining_end < history.formation_month).all()
    assert history.hybrid_feature_count.eq(23).all()
    assert history.stock_report_coverage.min() > 850
    assert history.finite_scores.min() == 653


def test_m012_primary_path_and_fixed_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(-0.0538584092126444)
    assert primary.full_annualized_sharpe == pytest.approx(-0.14438199735713614)
    assert primary.full_maximum_drawdown == pytest.approx(-0.9024956776709772)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.06372643633246797)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.6686300684402307)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.09519071604968848)
    assert primary.average_traded_notional == pytest.approx(2.077845381223535)


def test_m012_ledger_closes_and_advances_once_to_m013():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M012"]["status"] == "completed_in_spirit"
    assert rows["M012"]["recipe_path"] and rows["M012"]["run_manifest_path"]
    assert rows["M012"]["monthly_returns_path"] and rows["M012"]["metrics_path"]
    assert rows["M012"]["verdict_path"]
    assert rows["M013"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 9
    assert sum(ledger["progress_summary"].values()) == 69
