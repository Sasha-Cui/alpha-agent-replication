from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M023_efs"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m023_outputs_reconstruct_us_component_and_hashes():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    contract_path = ROOT / "paper_runs/us_jkp_headline/benchmark_contract.json"
    contract = json.loads(contract_path.read_text())
    assert manifest["status"] == "evaluated_partial"
    assert manifest["milestone_id"] == recipe["milestone_id"] == "M023"
    assert manifest["candidate_id"] == recipe["candidate_id"] == "efs_skew_gated_breakout"
    assert manifest["benchmark_id"] == contract["benchmark_id"]
    assert manifest["contract_sha256"] == sha256(contract_path)
    assert manifest["recipe_sha256"] == sha256(OUTPUT / "recipe.json")
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
    np.testing.assert_allclose(path.net_return,
                               path.gross_return - 0.001 * path.traded_notional,
                               atol=1e-15, rtol=0)
    rebuilt = return_statistics(path.net_return.to_numpy())
    for key, value in rebuilt.items():
        assert manifest["primary_result"][f"full_{key}"] == pytest.approx(value)


def test_m023_has_complete_diagnostics_and_honest_partial_boundary():
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
    assert "US50 skew-gated breakout" in report
    assert "evolutionary search; LLM generation" in report
    assert "one disclosed formula component" in report


def test_m023_is_closed_as_an_evaluated_partial():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M023"]["status"] == "completed_partial"
    assert ledger["progress_summary"]["closed"] >= 23
    assert ledger["progress_summary"]["completed_partial"] >= 4
