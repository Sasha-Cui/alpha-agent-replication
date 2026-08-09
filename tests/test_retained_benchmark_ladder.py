"""Regression tests for the retained-strategy benchmark ladder contract."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_retained_benchmark_ladder.py"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("run_retained_benchmark_ladder", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
OUTPUT = ROOT / "paper_runs/submission_evidence/retained_benchmark_ladder"


def test_implementation_basis_is_explicit_and_noninflationary() -> None:
    assert (
        MODULE.implementation_basis("M2_released_seed_expression")
        == "released_code_component_adaptation"
    )
    assert (
        MODULE.implementation_basis("M1_named_rule_partial_support")
        == "source_grounded_paper_component"
    )
    assert (
        MODULE.implementation_basis("M0_narrative_translation")
        == "in_spirit_reconstruction"
    )


def test_benchmark_ladder_is_nested_without_duplicate_ff_columns() -> None:
    factor_sets = {
        spec["benchmark_id"]: set(spec["factor_columns"])
        for spec in MODULE.MODEL_SPECS
    }
    assert factor_sets["capm"] < factor_sets["ff3"] < factor_sets["ff5_mom"]
    assert len(factor_sets["capm"]) == 1
    assert len(factor_sets["ff3"]) == 3
    assert len(factor_sets["ff5_mom"]) == 6


def test_generated_ladder_covers_all_retained_strategies_and_papers() -> None:
    results = pd.read_csv(OUTPUT / "strategy_benchmark_results.csv")
    comparison = pd.read_csv(OUTPUT / "strategy_benchmark_comparison.csv")
    papers = pd.read_csv(OUTPUT / "paper_benchmark_summary.csv")
    summary = pd.read_csv(OUTPUT / "benchmark_summary.csv")

    assert len(results) == 200
    assert results["candidate_id"].nunique() == 50
    assert results["canonical_work_id"].nunique() == 40
    assert set(results.groupby("candidate_id").size()) == {4}
    assert set(results.groupby("benchmark_id").size()) == {50}
    assert set(results.groupby("benchmark_id")["n_benchmark_returns"].first()) == {
        1,
        3,
        6,
        133,
    }
    assert len(comparison) == comparison["candidate_id"].nunique() == 50
    assert len(papers) == papers["canonical_work_id"].nunique() == 40
    assert len(summary) == 16
    assert results["alpha_annualized"].notna().all()

    route_counts = (
        comparison["implementation_basis"].value_counts().sort_index().to_dict()
    )
    assert route_counts == {
        "in_spirit_reconstruction": 37,
        "released_code_component_adaptation": 1,
        "source_grounded_paper_component": 12,
    }


def test_matched_benchmark_counts_and_broad_results_are_reconciled() -> None:
    results = pd.read_csv(OUTPUT / "strategy_benchmark_results.csv")
    expected = {
        "capm": (44, 28, 6),
        "ff3": (41, 5, 1),
        "ff5_mom": (41, 7, 2),
        "ff5_mom_jkp132": (17, 1, 0),
    }
    for benchmark_id, counts in expected.items():
        group = results[results["benchmark_id"].eq(benchmark_id)]
        actual = (
            int(group["positive_alpha_estimate"].sum()),
            int(group["nominal_positive_5pct"].sum()),
            int(group["holm_positive_5pct"].sum()),
        )
        assert actual == counts
        assert set(group["n_evaluation_months"]) == {126}
        assert set(group["evaluation_start"]) == {"2011-08-31"}
        assert set(group["evaluation_end"]) == {"2022-01-31"}

    broad = results[results["benchmark_id"].eq("ff5_mom_jkp132")].set_index(
        "candidate_id"
    )
    legacy = pd.read_csv(
        ROOT
        / "paper_runs/submission_evidence/usa_broad_jkp_crossfit/"
        "broad_jkp_crossfit_results.csv"
    ).set_index("candidate_id")
    aligned = legacy.loc[broad.index]
    assert np.allclose(
        broad["alpha_annualized"].sort_index(),
        aligned["alpha_annualized"].sort_index(),
        rtol=0,
        atol=1e-14,
    )


def test_factor_correlation_ledger_is_complete() -> None:
    correlations = pd.read_csv(OUTPUT / "strategy_jkp_factor_correlations.csv")
    top = correlations[
        correlations["factor_rank_by_absolute_correlation"].eq(1)
    ]
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert len(correlations) == 50 * 132
    assert len(top) == 50
    assert int((top["absolute_correlation"] >= 0.5).sum()) == 47
    assert top["jkp_factor_id"].nunique() == 21
    assert np.isclose(
        top["absolute_correlation"].median(),
        manifest["factor_correlation_summary"][
            "median_top_absolute_correlation"
        ],
    )
