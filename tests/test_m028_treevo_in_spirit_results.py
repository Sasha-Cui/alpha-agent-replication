from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import return_statistics


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M028_treevo"
SELECTED = "mean(mean(product(ret_6_1,rvol_21d),ret_1_0),difference(ret_6_1,ret_12_1))"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m028_manifest_pins_hierarchical_search_and_outputs():
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["status"] == "evaluated_in_spirit"
    assert manifest["fidelity_label"] == "in_spirit_reconstruction"
    assert manifest["milestone_id"] == "M028"
    assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
    assert manifest["code_commit"] == "326eaad4172d22865fbdfbb429fe8ea06ed5d270"
    assert manifest["population_size"] == 10
    assert manifest["evaluation_budget"] == 200
    assert manifest["invalid_candidate_evaluations"] == 2
    summary = manifest["search_summary"]
    assert summary["selected_evaluation"] == 180
    assert summary["selected_expression"] == SELECTED
    assert summary["selected_node_count"] == 9
    assert summary["selected_training_direction"] == -1
    assert summary["selected_training_mean_rankic"] == pytest.approx(-0.0557788587361305)
    assert summary["selected_validation_mean_oriented_rankic"] == pytest.approx(0.06359362663572933)
    assert manifest["confirmatory_claim"] is False
    assert manifest["native_paper_result_claim"] is False
    for name, expected in manifest["output_sha256"].items():
        assert digest(OUTPUT / name) == expected


def test_m028_search_uses_exact_budget_operators_and_pre_common_selection():
    history = pd.read_csv(OUTPUT / "search_history.csv")
    assert len(history) == 200
    assert history.evaluation.tolist() == list(range(1, 201))
    assert history.operator.value_counts().to_dict() == {
        "crossover": 70,
        "mutation": 60,
        "pruning": 60,
        "initialization": 10,
    }
    assert history.valid_candidate.sum() == 198
    assert history.survives_final_population.sum() == 10
    assert history.selected_final.sum() == 1
    selected = history.loc[history.selected_final].iloc[0]
    assert selected.expression == SELECTED
    assert selected.training_rankic_months == 96
    assert selected.validation_rankic_months == 24
    assert selected.valid_candidate


def test_m028_primary_path_and_fixed_result_are_exact():
    path = pd.read_csv(OUTPUT / "primary_monthly_returns.csv")
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    primary = metrics.loc[metrics.primary.astype(str).str.lower().eq("true")].iloc[0]
    assert len(path) == 305
    assert path.path_status.eq("ok").all()
    assert path.formation_universe.eq(1000).all()
    np.testing.assert_allclose(
        path.net_return,
        path.gross_return - 0.001 * path.traded_notional,
        rtol=0,
        atol=1e-15,
    )
    rebuilt = return_statistics(path.net_return.to_numpy())
    assert primary.full_cagr == pytest.approx(rebuilt["cagr"])
    assert primary.full_cagr == pytest.approx(0.006510794385248708)
    assert primary.full_annualized_sharpe == pytest.approx(0.12386006186968512)
    assert primary.full_maximum_drawdown == pytest.approx(-0.6622420547909008)
    assert primary.jkp_residual_mean_annualized == pytest.approx(-0.04044032828807209)
    assert primary.jkp_residual_t_hac == pytest.approx(-1.2182660178233338)
    assert primary.jkp_residual_p_two_sided == pytest.approx(0.22312289924790418)
    assert primary.average_traded_notional == pytest.approx(2.7327481768676773)


def test_m028_ledger_closes_and_advances_to_m029():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M028"]["status"] == "completed_in_spirit"
    assert rows["M028"]["recipe_path"] and rows["M028"]["run_manifest_path"]
    assert rows["M028"]["monthly_returns_path"] and rows["M028"]["metrics_path"]
    assert rows["M028"]["verdict_path"]
    assert rows["M029"]["status"] in {
        "queued_in_spirit",
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert ledger["progress_summary"]["completed_in_spirit"] >= 19
    assert sum(ledger["progress_summary"].values()) == 69
