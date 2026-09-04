from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M026_chain_of_alpha"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m026_outputs_reconstruct_formula_result_and_hashes():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract_path = ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json"
    inventory_path = ROOT / "paper_runs/paper_replication_audits/chain_of_alpha/published_factor_inventory.csv"
    contract = json.loads(contract_path.read_text())
    assert manifest["status"] == "evaluated_partial"
    assert manifest["milestone_id"] == recipe["milestone_id"] == "M026"
    assert manifest["candidate_id"] == "chain_of_alpha_volume_adjusted_mean_corr"
    assert manifest["benchmark_id"] == contract["benchmark_id"]
    assert manifest["contract_sha256"] == sha256(contract_path)
    assert manifest["recipe_sha256"] == sha256(OUTPUT / "recipe.json")
    assert manifest["published_factor_inventory_sha256"] == sha256(inventory_path)
    assert manifest["prior_jkp_outcomes_seen"] is True
    assert manifest["confirmatory_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert sha256(OUTPUT / name) == expected
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.finite_signal_count.min() >= 20
    np.testing.assert_allclose(path.net_return,
                               path.gross_return - 0.001 * path.traded_notional,
                               atol=1e-15, rtol=0)
    rebuilt = return_statistics(path.net_return.to_numpy())
    for key, value in rebuilt.items():
        assert manifest["primary_result"][f"full_{key}"] == pytest.approx(value)


def test_m026_attribution_and_partial_claim_boundary_are_explicit():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    assert len(metrics) == 6
    assert metrics.primary.astype(str).str.lower().eq("true").sum() == 1
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert primary.missing_return_policy == "zero"
    assert primary.cost_bps_one_way == 10
    assert primary.evaluation_months == 185
    assert primary.exploratory_bonferroni69_p == min(1, 69 * primary.jkp_residual_p_two_sided)
    residuals = pd.read_csv(OUTPUT / "attribution_residuals.csv")
    selected = residuals.loc[residuals.case == primary["case"]]
    assert len(selected) == 185
    np.testing.assert_allclose(selected.net_return - selected.factor_replication_return,
                               selected.residual, atol=1e-15, rtol=0)
    assert 12 * selected.residual.mean() == pytest.approx(primary.jkp_residual_mean_annualized)
    report = (OUTPUT / "verdict.md").read_text()
    assert "not either LLM chain or the native factor portfolio" in report
    assert "selected because it alone avoids unavailable VWAP" in report
    assert "does not reproduce" in report


def test_m026_is_closed_as_an_evaluated_partial():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M026"]["status"] == "completed_partial"
    assert ledger["progress_summary"]["closed"] >= 26
    assert ledger["progress_summary"]["completed_partial"] >= 5
