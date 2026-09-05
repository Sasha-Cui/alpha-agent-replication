from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M042_alpha_r1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m042_manifest_pins_contextual_gate_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M042"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "bc6262ba89690d4420e2d130e8257061dde3e94c"
    assert manifest["factor_zoo_count"] == 40
    assert manifest["active_factor_count"] == 10
    assert manifest["policy_update_months"] == 305
    assert manifest["unique_selected_factors"] == 40
    assert sum(manifest["selection_frequency"].values()) == 3050
    assert sum(manifest["family_selection_frequency"].values()) == 3050
    assert manifest["selection_frequency"]["rmax1_21d"] == 120
    assert manifest["mean_selected_gate_score"] == pytest.approx(0.5378772593526692)
    assert manifest["mean_absolute_selected_beta"] == pytest.approx(0.002749246808170758)
    assert manifest["unavailable_selected_values"] == 100354
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m042_gate_is_sparse_purged_and_context_conditioned():
    history = pd.read_csv(
        OUTPUT / "gate_history.csv",
        parse_dates=[
            "formation_month",
            "factor_profile_cutoff",
            "factor_profile_history_start",
            "factor_profile_history_end",
            "linear_beta_cutoff",
            "linear_beta_history_start",
            "linear_beta_history_end",
        ],
    )
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.factor_profile_history_months.eq(60).all()
    assert history.linear_beta_history_months.eq(48).all()
    assert (history.factor_profile_history_end <= history.factor_profile_cutoff).all()
    assert (history.linear_beta_history_end <= history.linear_beta_cutoff).all()
    assert (history.factor_profile_cutoff < history.formation_month).all()
    assert (history.linear_beta_cutoff < history.formation_month).all()
    assert history.selected_factor_count.eq(10).all()
    assert history.selected_factors.str.split("|").map(len).eq(10).all()
    assert history.mean_selected_gate_score.between(-1.0, 1.0).all()
    assert history.minimum_selected_gate_score.between(-1.0, 1.0).all()
    assert history.filter(like="state__").apply(np.isfinite).all().all()
    assert history.finite_scores.eq(1000).all()


def test_m042_primary_path_and_fixed_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(-0.04710129448130462)
    assert primary.full_annualized_sharpe == pytest.approx(-0.13807729940680147)
    assert primary.full_maximum_drawdown == pytest.approx(-0.874732475434963)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.09315942666920068)
    assert primary.jkp_residual_t_hac == pytest.approx(-2.412415845142251)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.015847195347949407)
    assert primary.average_traded_notional == pytest.approx(2.7679384493165937)


def test_m042_ledger_closes_and_advances_to_m047():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M042"]["status"] == "completed_in_spirit"
    assert rows["M042"]["recipe_path"] and rows["M042"]["run_manifest_path"]
    assert rows["M042"]["monthly_returns_path"] and rows["M042"]["metrics_path"]
    assert rows["M042"]["verdict_path"]
    assert rows["M047"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 29
    assert sum(ledger["progress_summary"].values()) == 69
