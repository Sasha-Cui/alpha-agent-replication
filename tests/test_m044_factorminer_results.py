from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M044_factorminer"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m044_outputs_reconstruct_the_frozen_partial_and_hashes():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract_path = ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json"
    contract = json.loads(contract_path.read_text())
    assert manifest["status"] == "evaluated_partial"
    assert manifest["milestone_id"] == recipe["milestone_id"] == "M044"
    assert manifest["candidate_id"] == recipe["candidate_id"]
    assert manifest["benchmark_id"] == contract["benchmark_id"]
    assert manifest["contract_sha256"] == sha256(contract_path)
    assert manifest["recipe_sha256"] == sha256(OUTPUT / "recipe.json")
    assert manifest["paper_source_sha256"] == recipe["paper_version"]["source_archive_sha256"]
    assert manifest["formula_ledger_sha256"] == recipe["formula_evidence"]["tracked_ledger_sha256"]
    assert manifest["interpreter_commit"] == recipe["formula_evidence"]["accessible_interpreter_commit"]
    assert manifest["prior_jkp_outcomes_seen"] is True
    assert manifest["confirmatory_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert sha256(OUTPUT / name) == expected


def test_m044_path_preserves_training_cash_and_common_deciles():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    assert len(path) == 305
    assert path.month.iloc[0] == "1999-08-31"
    assert path.month.iloc[-1] == "2024-12-31"
    assert path.path_status.value_counts().to_dict() == {
        "ok": 293,
        "insufficient_formation_coverage": 12,
    }
    warmup = path.path_status.eq("insufficient_formation_coverage")
    active = path.path_status.eq("ok")
    assert path.loc[warmup, ["gross_return", "traded_notional"]].eq(0).all().all()
    assert path.loc[warmup, "gross_exposure"].isna().all()
    assert path.loc[active, "formation_universe"].eq(1000).all()
    assert path.loc[active, "finite_signal_count"].eq(1000).all()
    assert path.loc[active, "n_long"].eq(100).all()
    assert path.loc[active, "n_short"].eq(100).all()
    np.testing.assert_allclose(path.loc[active, "gross_exposure"], 2.0, atol=1e-12, rtol=0)
    np.testing.assert_allclose(
        path.net_return, path.gross_return - 0.001 * path.traded_notional, atol=1e-15, rtol=0
    )
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    rebuilt = return_statistics(path.net_return.to_numpy())
    for key, value in rebuilt.items():
        assert manifest["primary_result"][f"full_{key}"] == pytest.approx(value)


def test_m044_signal_is_flat_before_cost_and_negative_after_turnover_cost():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    gross = metrics.loc[metrics.case.eq("zero_cost_0")].iloc[0]
    adverse = metrics.loc[metrics.case.eq("adverse_100_cost_10")].iloc[0]
    assert gross.full_cagr == pytest.approx(-0.002297485090971718)
    assert gross.jkp_residual_mean_annualized == pytest.approx(0.015840244549637117)
    assert gross.jkp_residual_p_two_sided == pytest.approx(0.5383926272222207)
    assert primary.full_cagr == pytest.approx(-0.03836024431771046)
    assert primary.full_annualized_sharpe == pytest.approx(-0.2782548510501758)
    assert primary.full_maximum_drawdown == pytest.approx(-0.6739652553587584)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.02355797380024334)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.3605655221302867)
    assert primary.average_traded_notional == pytest.approx(3.061326228751711)
    assert primary.annualized_linear_cost_drag == pytest.approx(0.03673591474502053)
    assert adverse.full_cagr == pytest.approx(-0.12152009405386599)
    zero_cases = metrics.loc[metrics.missing_return_policy.eq("zero")].sort_values("cost_bps_one_way")
    assert zero_cases.full_cagr.is_monotonic_decreasing


def test_m044_selection_and_coverage_freeze_all_110_formulas():
    coverage = pd.read_csv(OUTPUT / "feature_coverage.csv", dtype={"factor_id": str})
    selection = pd.read_csv(OUTPUT / "factor_selection.csv", dtype={"factor_id": str})
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert len(coverage) == len(selection) == 110
    assert coverage.factor_id.nunique() == selection.factor_id.nunique() == 110
    assert coverage.finite_fraction.min() > 0.91
    assert selection.selected.sum() == 40
    np.testing.assert_allclose(selection.loc[selection.selected, "weight"].sum(), 1.0)
    assert selection.training_ic_months.value_counts().to_dict() == {12: 109, 6: 1}
    assert manifest["selection"]["selected_ids"] == selection.loc[selection.selected, "factor_id"].tolist()


def test_m044_ledger_records_the_central_partial():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    milestone = rows["M044"]
    assert milestone["status"] == "completed_partial"
    assert milestone["implementation_path"] == "scripts/run_factorminer_top40_milestone.py"
    assert milestone["recipe_path"] and milestone["run_manifest_path"]
    assert milestone["monthly_returns_path"] and milestone["metrics_path"] and milestone["verdict_path"]
    assert milestone["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 44
    assert ledger["progress_summary"]["completed_partial"] >= 9
