from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M019_alphaagent"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m019_outputs_reconstruct_partial_result_and_hashes():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract_path = ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json"
    contract = json.loads(contract_path.read_text())
    assert manifest["status"] == "evaluated_partial"
    assert manifest["milestone_id"] == recipe["milestone_id"] == "M019"
    assert manifest["benchmark_id"] == contract["benchmark_id"]
    assert manifest["contract_sha256"] == sha256(contract_path)
    assert manifest["recipe_sha256"] == sha256(OUTPUT / "recipe.json")
    assert manifest["source_factor_file_sha256"] == recipe["source_factor_file_sha256"]
    assert manifest["prior_jkp_outcomes_seen"] is True
    assert manifest["confirmatory_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert sha256(OUTPUT / name) == expected
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    assert len(path) == 305
    assert path.path_status.eq("insufficient_formation_coverage").sum() == 24
    assert path.path_status.eq("ok").sum() == 281
    assert path.loc[path.path_status.eq("insufficient_formation_coverage"), "gross_return"].eq(0).all()
    np.testing.assert_allclose(path.net_return,
                               path.gross_return - 0.001 * path.traded_notional,
                               atol=1e-15, rtol=0)
    rebuilt = return_statistics(path.net_return.to_numpy())
    for key, value in rebuilt.items():
        assert manifest["primary_result"][f"full_{key}"] == pytest.approx(value)


def test_m019_attribution_model_and_claim_boundary_are_explicit():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    assert len(metrics) == 6
    assert metrics.primary.astype(str).str.lower().eq("true").sum() == 1
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert primary.missing_return_policy == "zero"
    assert primary.cost_bps_one_way == 10
    assert primary.cash_warmup_months == 24
    assert primary.scored_months == 281
    assert primary.evaluation_months == 185
    assert primary.exploratory_bonferroni69_p == min(1, 69 * primary.jkp_residual_p_two_sided)
    residuals = pd.read_csv(OUTPUT / "attribution_residuals.csv")
    selected = residuals.loc[residuals.case == primary["case"]]
    assert len(selected) == 185
    np.testing.assert_allclose(selected.net_return - selected.factor_replication_return,
                               selected.residual, atol=1e-15, rtol=0)
    assert 12 * selected.residual.mean() == pytest.approx(primary.jkp_residual_mean_annualized)
    coefficients = pd.read_csv(OUTPUT / "rolling_model_coefficients.csv")
    assert len(coefficients) == 281
    assert coefficients.training_months.between(24, 120).all()
    report = (OUTPUT / "verdict.md").read_text()
    assert "not the AlphaAgent mining loop or native fitted run" in report
    assert "without selecting on their new JKP performance" in report
    assert "does not reproduce" in report


def test_m019_is_closed_as_an_evaluated_partial():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M019"]["status"] == "completed_partial"
    assert ledger["progress_summary"]["closed"] >= 19
    assert ledger["progress_summary"]["completed_partial"] >= 2
