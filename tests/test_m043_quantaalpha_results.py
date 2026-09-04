from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M043_quantaalpha"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m043_outputs_reconstruct_the_frozen_partial_and_hashes():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract_path = ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json"
    contract = json.loads(contract_path.read_text())
    assert manifest["status"] == "evaluated_partial"
    assert manifest["milestone_id"] == recipe["milestone_id"] == "M043"
    assert manifest["candidate_id"] == recipe["candidate_id"]
    assert manifest["benchmark_id"] == contract["benchmark_id"]
    assert manifest["contract_sha256"] == sha256(contract_path)
    assert manifest["recipe_sha256"] == sha256(OUTPUT / "recipe.json")
    assert manifest["source_factor_sha256"] == recipe["release_evidence"]["prepublication_factor_sha256"]
    assert manifest["source_commit"] == recipe["release_evidence"]["prepublication_results_commit"]
    assert manifest["code_commit"] == "6b2f046eeb1b6a47db78e171c96631023baa4cb3"
    assert manifest["prior_jkp_outcomes_seen"] is True
    assert manifest["confirmatory_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert sha256(OUTPUT / name) == expected


def test_m043_path_preserves_cash_warmup_and_topk_dropout_accounting():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    assert len(path) == 305
    assert path.month.iloc[0] == "1999-08-31"
    assert path.month.iloc[-1] == "2024-12-31"
    assert path.path_status.value_counts().to_dict() == {
        "ok": 233,
        "training_or_validation_cash": 72,
    }
    warmup = path.path_status.eq("training_or_validation_cash")
    active = path.path_status.eq("ok")
    assert path.loc[warmup, ["gross_return", "traded_notional", "gross_exposure"]].eq(0).all().all()
    assert path.loc[active, "formation_universe"].eq(1000).all()
    assert path.loc[active, "finite_signal_count"].eq(1000).all()
    assert path.loc[active, "n_holdings"].eq(50).all()
    np.testing.assert_allclose(path.loc[active, "gross_exposure"], 1.0, atol=1e-12, rtol=0)
    np.testing.assert_allclose(
        path.net_return,
        path.gross_return - 0.001 * path.traded_notional,
        atol=1e-15,
        rtol=0,
    )
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    rebuilt = return_statistics(path.net_return.to_numpy())
    for key, value in rebuilt.items():
        assert manifest["primary_result"][f"full_{key}"] == pytest.approx(value)


def test_m043_primary_result_is_positive_but_not_distinct_from_jkp():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    assert len(metrics) == 6
    assert metrics.primary.astype(str).str.lower().eq("true").sum() == 1
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    adverse = metrics.loc[metrics.case.eq("adverse_100_cost_10")].iloc[0]
    assert primary.full_cagr == pytest.approx(0.013847350860724417)
    assert primary.full_annualized_sharpe == pytest.approx(0.18552522717149025)
    assert primary.full_maximum_drawdown == pytest.approx(-0.37343240982704284)
    assert primary.jkp_residual_mean_annualized == pytest.approx(0.01796864870004371)
    assert primary.jkp_residual_t_hac == pytest.approx(0.8466701962569573)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.39717897537501157)
    assert primary.exploratory_bonferroni69_p == 1.0
    assert primary.cash_warmup_months == 72
    assert primary.scored_months == 233
    assert primary.average_traded_notional == pytest.approx(0.14011440264827105)
    assert adverse.full_cagr == pytest.approx(-0.013822473486112652)
    zero_cases = metrics.loc[metrics.missing_return_policy.eq("zero")].sort_values("cost_bps_one_way")
    assert zero_cases.full_cagr.is_monotonic_decreasing


def test_m043_feature_and_model_evidence_cover_the_whole_source_profile():
    coverage = pd.read_csv(OUTPUT / "feature_coverage.csv")
    model = json.loads((OUTPUT / "model_training.json").read_text())
    assert len(coverage) == 170
    assert coverage.factor_name.nunique() == 170
    assert coverage.factor_id.str.startswith("alpha158_20::").sum() == 20
    assert coverage.finite_fraction.min() > 0.54
    assert model["feature_count"] == 170
    assert model["train_months"] == 60
    assert model["validation_months"] == 12
    assert model["test_months"] == 233
    assert model["best_iteration"] == 25
    assert model["test_start"] == "2005-07-31"


def test_m043_ledger_records_the_central_partial():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M043"]
    assert milestone["status"] == "completed_partial"
    assert milestone["implementation_path"] == "scripts/run_quantaalpha_factor_pool_milestone.py"
    assert milestone["recipe_path"] and milestone["run_manifest_path"]
    assert milestone["monthly_returns_path"] and milestone["metrics_path"] and milestone["verdict_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 43
    assert ledger["progress_summary"]["completed_partial"] >= 8
