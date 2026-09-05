from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M024_mountainlion"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m024_manifest_pins_four_agent_fusion_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M024"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "e52a0e33327ae4ede4926321c2fc71e887fb1787"
    assert manifest["agent_count"] == 4
    assert manifest["modality_count"] == 4
    assert manifest["policy_update_months"] == 305
    assert manifest["average_llm_alpha"] == pytest.approx(0.5598919794468936)
    assert manifest["minimum_llm_alpha"] == pytest.approx(0.30571880563241827)
    assert manifest["maximum_llm_alpha"] == pytest.approx(0.7621134717438401)
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m024_fusion_is_past_only_and_adaptive():
    history = pd.read_csv(
        OUTPUT / "fusion_history.csv",
        parse_dates=[
            "formation_month",
            "ml_training_start",
            "ml_training_end",
            "fusion_start",
            "fusion_end",
        ],
    )
    assert len(history) == 305
    assert history.formation_month.iloc[0] == pd.Timestamp("1999-07-31")
    assert history.formation_month.iloc[-1] == pd.Timestamp("2024-11-30")
    assert history.ml_training_months.eq(60).all()
    assert history.fusion_history_months.eq(24).all()
    assert (history.ml_training_end < history.formation_month).all()
    assert (history.fusion_end < history.formation_month).all()
    assert history.agent_count.eq(4).all()
    assert history.modality_count.eq(4).all()
    assert history.llm_alpha.between(0.1, 0.9).all()
    assert history.llm_alpha.nunique() > 100
    assert history.modality_disagreement_rate.between(0.0, 1.0).all()
    assert history.finite_scores.min() == 645


def test_m024_primary_path_and_fixed_negative_result_are_exact():
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
    assert primary.full_cagr == pytest.approx(-0.02762801532339909)
    assert primary.full_annualized_sharpe == pytest.approx(0.015264711672772107)
    assert primary.full_maximum_drawdown == pytest.approx(-0.7830811068261868)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.03018366465258184)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.0130080333523044)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.3110563238094115)
    assert primary.average_traded_notional == pytest.approx(2.3434175167689286)


def test_m024_ledger_closes_and_advances_to_m025():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M024"]["status"] == "completed_in_spirit"
    assert rows["M024"]["recipe_path"] and rows["M024"]["run_manifest_path"]
    assert rows["M024"]["monthly_returns_path"] and rows["M024"]["metrics_path"]
    assert rows["M024"]["verdict_path"]
    assert rows["M025"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 16
    assert sum(ledger["progress_summary"].values()) == 69
