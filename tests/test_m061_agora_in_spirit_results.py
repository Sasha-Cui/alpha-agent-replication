from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M061_agora"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m061_manifest_pins_sealed_search_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M061"
    assert manifest["code_commit"] == "06b5e55e38af62bbfad4d2e7c16143fadf807ee4"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["candidate_library_size"] == 145
    assert manifest["outer_rounds"] == 100
    assert manifest["alpha_registry_size"] == 94
    assert manifest["selected_top_alpha_count"] == 30
    assert len(manifest["selected_top_alphas"]) == 30
    assert manifest["final_accepted_metrics"] == ["excess_drawdown_penalty_v1"]
    assert manifest["metric_action_counts"] == {"none": 97, "promote": 2, "demote": 1}
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m061_registry_and_round_history_are_complete():
    registry = pd.read_csv(OUTPUT / "alpha_registry.csv")
    rounds = pd.read_csv(OUTPUT / "round_history.csv")
    assert len(registry) == 94 and registry.alpha.nunique() == 94
    assert registry.selected_top30.sum() == 30
    assert len(rounds) == 100 and rounds.registry_size.iloc[-1] == 94
    assert rounds.channel_b_brief_records.eq(2).all()
    assert rounds.channel_c_wiki_commit.all()
    assert set(rounds.loc[rounds.metric_action.eq("promote"), "metric_proposal"]) == {
        "monotonicity_score_v1",
        "excess_drawdown_penalty_v1",
    }


def test_m061_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(0.09051063986326757)
    assert primary.full_annualized_sharpe == pytest.approx(0.46313519870532005)
    assert primary.full_maximum_drawdown == pytest.approx(-0.5170321169738938)
    assert primary.jkp_residual_mean_annualized == pytest.approx(0.004376232407465525)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.8506543793091623)


def test_m061_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M061"]["status"] == "completed_in_spirit"
    assert rows["M061"]["run_manifest_path"] and rows["M061"]["metrics_path"]
    assert rows["M063"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 41
    assert sum(ledger["progress_summary"].values()) == 69
