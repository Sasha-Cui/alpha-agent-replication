from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M065_factormad"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m065_manifest_pins_debate_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M065"
    assert manifest["code_commit"] == "793f3e8c86600c2fa70a96fc44dcf47a9ec4b053"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["candidate_library_size"] == 210
    assert manifest["debate_episodes"] == 100
    assert manifest["accepted_factor_count"] == 100
    assert manifest["debate_record_count"] == 1100
    assert manifest["corrected_factor_count"] == 0
    assert manifest["seed_source_counts"] == {"generated_factor": 51, "existing_factor": 49}
    assert manifest["complexity_counts"] == {"1": 5, "2": 95}
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m065_accepted_factors_and_debate_are_complete():
    registry = pd.read_csv(OUTPUT / "accepted_factors.csv")
    debate = pd.read_csv(OUTPUT / "debate_history.csv")
    assert len(registry) == 100 and registry.factor.nunique() == 100
    assert np.abs(registry.linear_model_weight).sum() == pytest.approx(1.0)
    assert registry.maximum_prior_rankic_correlation.le(0.98).all()
    assert len(debate) == 1100 and debate.groupby("episode").size().eq(11).all()
    assert debate.proposer.value_counts().to_dict() == {
        "agent_a_quality": 500,
        "agent_b_diversity": 500,
        "validator_corrector": 100,
    }


def test_m065_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(0.07149558844522264)
    assert primary.full_annualized_sharpe == pytest.approx(0.4460789395812816)
    assert primary.full_maximum_drawdown == pytest.approx(-0.473911004470854)
    assert primary.jkp_residual_mean_annualized == pytest.approx(0.03856676465556083)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.12649900484916374)


def test_m065_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M065"]["status"] == "completed_in_spirit"
    assert rows["M065"]["run_manifest_path"] and rows["M065"]["metrics_path"]
    assert rows["M066"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 43
    assert sum(ledger["progress_summary"].values()) == 69
