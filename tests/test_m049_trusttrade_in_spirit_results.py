from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M049_trusttrade"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m049_manifest_pins_policy_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M049"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "f3adb3be2e8c39b73fce83318c45c173acccab46"
    assert manifest["domain_count"] == 4 and manifest["report_count"] == 12
    assert manifest["policy_update_months"] == 305
    assert manifest["aggregate_actions"] == {"buy": 94454, "hold": 120847, "sell": 89699}
    assert manifest["mean_absolute_position"] == pytest.approx(0.315170735857379)
    assert manifest["mean_risk_cap"] == pytest.approx(0.5)
    assert manifest["confirmatory_claim"] is False and manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m049_reflection_is_purged_and_complete():
    history = pd.read_csv(OUTPUT / "reflection_history.csv", parse_dates=["formation_month", "reflection_cutoff", "long_reflection_start", "long_reflection_end"])
    assert len(history) == 305
    assert history.long_reflection_months.eq(60).all()
    assert history.short_reflection_months.eq(12).all()
    assert (history.long_reflection_end <= history.reflection_cutoff).all()
    assert (history.reflection_cutoff < history.formation_month).all()
    assert (history.buy_count + history.hold_count + history.sell_count).eq(1000).all()
    np.testing.assert_allclose(history.filter(like="reliability__").sum(axis=1), 1.0, rtol=0, atol=1e-14)
    assert history.finite_scores.eq(1000).all()


def test_m049_primary_path_and_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(-0.04561229347500695)
    assert primary.full_annualized_sharpe == pytest.approx(-0.14496580849856763)
    assert primary.full_maximum_drawdown == pytest.approx(-0.8130979885985082)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.013646665112148265)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.5731873770904777)


def test_m049_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M049"]["status"] == "completed_in_spirit"
    assert rows["M049"]["run_manifest_path"] and rows["M049"]["metrics_path"]
    assert rows["M050"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 32
    assert sum(ledger["progress_summary"].values()) == 69
