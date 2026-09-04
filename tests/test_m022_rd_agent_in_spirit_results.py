from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M022_rd_agent"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m022_manifest_pins_search_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M022"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "3c5e531e6fc232c7352a7ed5db2862682f5d2cfa"
    assert manifest["branch_count"] == 6
    assert manifest["candidate_count"] == 24
    assert manifest["policy_update_months"] == 305
    assert manifest["merged_solution_months"] == 48
    assert sum(manifest["selected_solution_counts"].values()) == 305
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m022_search_is_past_only_parallel_and_aggregated():
    history = pd.read_csv(
        OUTPUT / "search_history.csv",
        parse_dates=[
            "formation_month",
            "research_start",
            "research_end",
            "validation_start",
            "validation_end",
        ],
    )
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.research_months.eq(96).all()
    assert history.validation_months.eq(24).all()
    assert (history.research_end < history.validation_start).all()
    assert (history.validation_end < history.formation_month).all()
    assert history.explored_candidate_count.eq(24).all()
    assert history.branch_winner_count.eq(6).all()
    assert history.finalist_count.eq(8).all()
    assert history.selected_solution_size.isin([1, 3, 6]).all()
    assert history.finite_scores.min() == 774


def test_m022_primary_path_and_fixed_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(0.00030539359404357924)
    assert primary.full_annualized_sharpe == pytest.approx(0.13018138443210897)
    assert primary.full_maximum_drawdown == pytest.approx(-0.7724010763784126)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.05095180432715563)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.3365844472267028)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.18135831851535067)
    assert primary.average_traded_notional == pytest.approx(1.86593483725564)


def test_m022_ledger_closes_skips_carried_m023_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M022"]["status"] == "completed_in_spirit"
    assert rows["M022"]["recipe_path"] and rows["M022"]["run_manifest_path"]
    assert rows["M022"]["monthly_returns_path"] and rows["M022"]["metrics_path"]
    assert rows["M022"]["verdict_path"]
    assert rows["M023"]["status"] == "carried_common_evaluation"
    assert rows["M024"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 15
    assert sum(ledger["progress_summary"].values()) == 69
