from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M067_raptor"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m067_manifest_pins_orchestration_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M067"
    assert manifest["code_commit"] == "45d20d88c389317b229eae4dbe1e99c20d42099a"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["formation_months"] == 305
    assert manifest["agent_roles_per_security"] == 14
    assert manifest["total_append_only_messages"] == 4_270_000
    assert manifest["final_action_counts"] == {"BUY": 86532, "HOLD": 131550, "SELL": 86918}
    assert manifest["maximum_diagnostic_long_only_weight"] == pytest.approx(
        0.023572486204443154
    )
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m067_monthly_orchestration_is_complete_and_synchronized():
    history = pd.read_csv(OUTPUT / "orchestration_history.csv")
    assert len(history) == 305
    assert history.security_count.eq(1000).all()
    assert history.append_only_message_count.eq(14000).all()
    assert history.finite_score_count.eq(1000).all()
    assert (history.final_BUY + history.final_HOLD + history.final_SELL).eq(1000).all()
    for analyst in ("fundamental", "macro", "market", "news", "social", "valuation"):
        assert (
            history[f"{analyst}_BUY"]
            + history[f"{analyst}_HOLD"]
            + history[f"{analyst}_SELL"]
        ).eq(1000).all()
    np.testing.assert_allclose(history.long_only_weight_sum, 1.0, atol=5e-15)
    assert history.long_only_maximum_weight.le(0.10).all()


def test_m067_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    all_paths = pd.read_csv(OUTPUT / "monthly_returns.csv")
    assert len(path) == 305 and path.path_status.eq("ok").all()
    assert len(all_paths) == 610
    assert len(pd.read_csv(OUTPUT / "metrics.csv")) == 6
    np.testing.assert_allclose(
        path.net_return,
        path.gross_return - 0.001 * path.traded_notional,
        rtol=0,
        atol=1e-15,
    )
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(0.021005433364084558)
    assert primary.full_annualized_sharpe == pytest.approx(0.20860335764389726)
    assert primary.full_maximum_drawdown == pytest.approx(-0.43390090323707475)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.021511668986293808)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.539612929613924)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.12365473191806173)


def test_m067_closes_the_in_spirit_ledger_without_advancing():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M067"]["status"] == "completed_in_spirit"
    assert rows["M067"]["run_manifest_path"] and rows["M067"]["metrics_path"]
    assert ledger["progress_summary"] == {
        "carried_common_evaluation": 17,
        "completed_in_spirit": 45,
        "discarded_structural_mismatch": 7,
        "in_progress_in_spirit": 0,
        "queued_in_spirit": 0,
    }
    assert sum(ledger["progress_summary"].values()) == 69
