from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M030_mm_arc"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m030_manifest_pins_rabo_router_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M030"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "54831c02206134d1bd684299767d57bab634a827"
    assert manifest["expert_count"] == 4
    assert manifest["single_market_pool_count"] == 12
    assert manifest["policy_update_months"] == 305
    assert manifest["regime_counts"] == {"bear": 25, "bull": 217, "sideways": 63}
    assert manifest["regime_sparse_fallback_months"] == 19
    assert manifest["mean_router_weights"] == pytest.approx(
        {
            "trend": 0.2661488805209934,
            "reversal": 0.2597979139394125,
            "breakout": 0.19426220937810207,
            "exposure_control": 0.279790996161492,
        }
    )
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m030_routing_is_past_only_pool_bounded_and_simplex_valued():
    history = pd.read_csv(
        OUTPUT / "routing_history.csv",
        parse_dates=["formation_month", "audit_start", "audit_end"],
    )
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.audit_history_months.eq(120).all()
    assert (history.audit_end < history.formation_month).all()
    assert history.regime_audit_months.ge(12).all()
    assert history.single_market_pool_count.eq(12).all()
    assert history.admitted_pool_members.eq(20).all()
    for expert in ["trend", "reversal", "breakout", "exposure_control"]:
        assert history[f"selected__{expert}"].str.count("\\|").eq(4).all()
    weights = history.filter(like="router_weight__")
    np.testing.assert_allclose(weights.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert weights.ge(0).all().all()
    assert history.finite_scores.min() == 866


def test_m030_primary_path_and_fixed_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(
        path.net_return,
        path.gross_return - 0.001 * path.traded_notional,
        rtol=0,
        atol=1e-15,
    )
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(0.035957241335884405)
    assert primary.full_annualized_sharpe == pytest.approx(0.26555775795619707)
    assert primary.full_maximum_drawdown == pytest.approx(-0.5643440262489331)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.004247762419389844)
    assert primary.jkp_residual_t_hac == pytest.approx(-0.12394462519819414)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.9013591195391863)
    assert primary.average_traded_notional == pytest.approx(2.1059927996327334)


def test_m030_ledger_closes_skips_discarded_m031_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M030"]["status"] == "completed_in_spirit"
    assert rows["M030"]["recipe_path"] and rows["M030"]["run_manifest_path"]
    assert rows["M030"]["monthly_returns_path"] and rows["M030"]["metrics_path"]
    assert rows["M030"]["verdict_path"]
    assert rows["M031"]["status"] == "discarded_structural_mismatch"
    assert rows["M032"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 21
    assert sum(ledger["progress_summary"].values()) == 69
