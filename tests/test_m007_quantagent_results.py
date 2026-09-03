from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M007_quantagent"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m007_outputs_reconstruct_fixed_component_result_and_hashes():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract = json.loads((ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json").read_text())
    assert manifest["status"] == "evaluated_partial"
    assert manifest["candidate_id"] == recipe["candidate_id"] == "quantagent_atr14_breakout_literal"
    assert manifest["benchmark_id"] == contract["benchmark_id"]
    assert recipe["monthly_adapter"]["costs"] == "common fixed cost cases with 10 bp primary"
    assert manifest["contract_sha256"] == sha256(ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json")
    assert manifest["recipe_sha256"] == sha256(OUTPUT / "recipe.json")
    assert manifest["prior_jkp_outcomes_seen"] is True
    assert manifest["confirmatory_claim"] is False
    source_manifest_path = ROOT / "paper_runs/fidelity_formula_components/manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text())
    assert manifest["source_component_manifest_sha256"] == sha256(source_manifest_path)
    for name, expected in manifest["source_component_output_sha256"].items():
        assert source_manifest["output_sha256"][name] == expected
        private_source = ROOT / "paper_runs/fidelity_formula_components" / name
        if private_source.is_file():
            assert sha256(private_source) == expected
    for name, expected in manifest["output_sha256"].items():
        assert sha256(OUTPUT / name) == expected
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.month.iloc[0] == "1999-08-31"
    assert path.month.iloc[-1] == "2024-12-31"
    np.testing.assert_allclose(path.net_return,
                               path.gross_return - 0.001 * path.traded_notional,
                               atol=1e-15, rtol=0)
    rebuilt = return_statistics(path.net_return.to_numpy())
    for key, value in rebuilt.items():
        assert manifest["primary_result"][f"full_{key}"] == pytest.approx(value)


def test_m007_diagnostics_and_partial_claim_boundary_are_explicit():
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
    assert "not the paper's self-improving agent" in report
    assert "already mapped and evaluated" in report
    assert "must not be used as evidence that the full agent worked or failed" in report


def test_m007_is_closed_as_a_partial():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M007"]["status"] == "completed_partial"
    assert ledger["progress_summary"]["closed"] >= 7
    assert ledger["progress_summary"]["completed_partial"] >= 1
