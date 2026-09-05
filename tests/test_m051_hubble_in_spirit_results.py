from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from alpha_evolve.headline_backtest import return_statistics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M051_hubble"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m051_manifest_pins_search_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["milestone_id"] == "M051"
    assert manifest["code_commit"] == "360bc8b2dab7e0413474b3ac9c763c4f363fe69f"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["family_count"] == 6 and manifest["mining_rounds"] == 3
    assert manifest["candidate_count"] == 204 and manifest["selection_records"] == 15
    assert len(manifest["selected_candidates"]) == 5
    assert max(manifest["selected_family_counts"].values()) == 2
    assert manifest["confirmatory_claim"] is False and manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m051_search_artifacts_are_complete_and_diverse():
    metrics = pd.read_csv(OUTPUT / "candidate_metrics.csv")
    history = pd.read_csv(OUTPUT / "selection_history.csv")
    assert len(metrics) == 204 and len(history) == 15
    assert set(history["round"]) == {1, 2, 3}
    assert history.groupby(["round", "family"]).size().max() <= 2
    assert history.groupby("round").size().eq(5).all()
    assert metrics.coverage.between(0.0, 1.0).all()


def test_m051_primary_result_is_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    primary = pd.read_csv(OUTPUT / "metrics.csv").query("primary == True").iloc[0]
    assert len(path) == 305 and path.path_status.eq("ok").all()
    np.testing.assert_allclose(path.net_return, path.gross_return - 0.001 * path.traded_notional, rtol=0, atol=1e-15)
    assert primary.full_cagr == pytest.approx(return_statistics(path.net_return.to_numpy())["cagr"])
    assert primary.full_cagr == pytest.approx(0.08614812611062761)
    assert primary.full_annualized_sharpe == pytest.approx(0.4811451533135395)
    assert primary.full_maximum_drawdown == pytest.approx(-0.5408222152551622)
    assert primary.jkp_residual_mean_annualized == pytest.approx(0.007951826780581938)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.6994984446542014)


def test_m051_ledger_closes_and_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M051"]["status"] == "completed_in_spirit"
    assert rows["M051"]["run_manifest_path"] and rows["M051"]["metrics_path"]
    assert rows["M052"]["status"] in {"queued_in_spirit", "in_progress_in_spirit", "completed_in_spirit"}
    assert ledger["progress_summary"]["completed_in_spirit"] >= 34
    assert sum(ledger["progress_summary"].values()) == 69
