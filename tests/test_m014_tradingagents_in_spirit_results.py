from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M014_tradingagents"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m014_manifest_pins_debate_graph_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M014"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "8fe3eceb0ff1de373bfd4dc078a05cee4be9d161"
    assert manifest["analyst_count"] == 4
    assert manifest["policy_update_months"] == 305
    assert sum(manifest["risk_choice_counts"].values()) == 305
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m014_debate_history_is_past_only_normalized_and_complete():
    history = pd.read_csv(OUTPUT / "debate_history.csv", parse_dates=["formation_month", "reflection_start", "reflection_end"])
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.reflection_months.eq(60).all()
    assert (history.reflection_end < history.formation_month).all()
    reliability = history.filter(like="reliability_weight__")
    np.testing.assert_allclose(reliability.sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert set(history.risk_choice) == {"risk_seeking", "neutral", "conservative"}
    assert history.mean_bull_case.ge(0).all()
    assert history.mean_bear_case.le(0).all()
    assert history.finite_scores.min() == 974


def test_m014_primary_path_and_fixed_positive_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(0.03800534820079782)
    assert primary.full_annualized_sharpe == pytest.approx(0.2788137942805858)
    assert primary.full_maximum_drawdown == pytest.approx(-0.6699573617204759)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.0210015129236583)
    assert primary.jkp_residual_t_hac == pytest.approx(-0.7106975406614159)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.4772716839983714)
    assert primary.average_traded_notional == pytest.approx(2.3127578152746384)


def test_m014_ledger_closes_and_remains_closed_as_the_study_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M014"]["status"] == "completed_in_spirit"
    assert rows["M014"]["recipe_path"] and rows["M014"]["run_manifest_path"]
    assert rows["M014"]["monthly_returns_path"] and rows["M014"]["metrics_path"]
    assert rows["M014"]["verdict_path"]
    assert rows["M015"]["status"] == "discarded_structural_mismatch"
    assert rows["M016"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 11
    assert sum(ledger["progress_summary"].values()) == 69
