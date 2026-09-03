from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M001_gpt_signal"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m001_public_outputs_reconstruct_primary_result_and_hashes():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    contract = json.loads((ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert manifest["status"] == "evaluated"
    assert manifest["benchmark_id"] == contract["benchmark_id"] == recipe["benchmark_id"]
    assert manifest["contract_sha256"] == sha256(ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json")
    assert manifest["recipe_sha256"] == sha256(OUTPUT / "recipe.json")
    assert manifest["new_strategy_recipe_selection_used_jkp_results"] is False
    for name, expected in manifest["output_sha256"].items():
        assert sha256(OUTPUT / name) == expected
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.month.iloc[0] == "1999-08-31"
    assert path.month.iloc[-1] == "2024-12-31"
    assert path.formation_universe.eq(1000).all()
    expected_net = path.gross_return - 0.001 * path.traded_notional
    np.testing.assert_allclose(path.net_return, expected_net, atol=1e-15, rtol=0)
    rebuilt = return_statistics(path.net_return.to_numpy())
    primary = manifest["primary_result"]
    for key, value in rebuilt.items():
        assert primary[f"full_{key}"] == pytest.approx(value)


def test_m001_metrics_have_one_primary_and_fixed_diagnostics():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    assert len(metrics) == 6
    assert metrics.primary.astype(str).str.lower().eq("true").sum() == 1
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert primary.missing_return_policy == "zero"
    assert primary.cost_bps_one_way == 10
    assert primary.evaluation_months == 185
    assert primary.minimum_finite_signal_count >= 20
    assert 0 <= primary.jkp_alpha_p_two_sided <= 1
    assert primary.interim_bonferroni69_p == min(1, 69 * primary.jkp_alpha_p_two_sided)
    assert primary.jkp_alpha_ci_low_annualized < primary.jkp_alpha_annualized < primary.jkp_alpha_ci_high_annualized
    residuals = pd.read_csv(OUTPUT / "attribution_residuals.csv")
    selected = residuals.loc[residuals.case == primary["case"]]
    assert len(selected) == 185
    np.testing.assert_allclose(selected.net_return - selected.factor_replication_return,
                               selected.residual, atol=1e-15, rtol=0)
    assert 12 * selected.residual.mean() == pytest.approx(primary.jkp_alpha_annualized)


def test_m001_closure_is_counted_separately_from_original_paper_reproduction():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    counts = pd.Series(row["status"] for row in ledger["milestones"]).value_counts().to_dict()
    summary = ledger["progress_summary"]
    assert summary == {"closed": 1, "completed_adapted": 1, "completed_partial": 0,
                       "closed_not_evaluable": 0, "in_progress": 0, "queued": 68}
    assert counts == {"queued": 68, "completed_adapted": 1}
    report = (OUTPUT / "verdict.md").read_text()
    assert "not an original-paper or fresh-LLM reproduction" in report
    assert "No sign, factor formula or hyperparameter was changed after viewing the result" in report
