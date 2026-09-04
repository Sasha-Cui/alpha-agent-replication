from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M006_finmem"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m006_manifest_pins_layered_memory_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M006"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "961c1ae41c1455a316469381b35133a9ae97f283"
    assert manifest["memory_layer_count"] == 3
    assert manifest["policy_update_months"] == 305
    assert sum(manifest["risk_character_counts"].values()) == 305
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m006_memory_history_covers_layers_and_both_characters():
    history = pd.read_csv(OUTPUT / "memory_history.csv", parse_dates=["formation_month"])
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert set(history.risk_character) == {"risk_seeking", "risk_averse"}
    assert history.finite_scores.min() == 904
    for layer in ("shallow", "intermediate", "deep"):
        assert history[f"{layer}_memory_coverage"].min() > 600
        assert history[f"{layer}_mean_retrieved"].between(0, 5).all()


def test_m006_primary_path_and_fixed_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(-0.026300363275978733)
    assert primary.full_annualized_sharpe == pytest.approx(0.02426120724337329)
    assert primary.full_maximum_drawdown == pytest.approx(-0.9181272120154705)
    assert primary.jkp_residual_mean_annualized == pytest.approx(0.0138711339268664)
    assert primary.jkp_residual_t_hac == pytest.approx(0.39734872639278923)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.6911103201279492)
    assert primary.average_traded_notional == pytest.approx(2.778029059243961)


def test_m006_ledger_closes_and_skips_carried_m007_to_activate_m008():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M006"]["status"] == "completed_in_spirit"
    assert rows["M006"]["recipe_path"] and rows["M006"]["run_manifest_path"]
    assert rows["M006"]["monthly_returns_path"] and rows["M006"]["metrics_path"]
    assert rows["M006"]["verdict_path"]
    assert rows["M007"]["status"] == "carried_common_evaluation"
    assert rows["M008"]["status"] == "in_progress_in_spirit"
    assert ledger["progress_summary"] == {
        "carried_common_evaluation": 17,
        "completed_in_spirit": 4,
        "discarded_structural_mismatch": 7,
        "in_progress_in_spirit": 1,
        "queued_in_spirit": 40,
    }
