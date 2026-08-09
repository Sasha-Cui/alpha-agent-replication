from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/analyze_source_benchmarks.py"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("analyze_source_benchmarks", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
OUTPUT = ROOT / "paper_runs/submission_evidence/source_benchmark_audit"


def test_audit_covers_exactly_the_40_mapped_papers() -> None:
    audit = pd.read_csv(OUTPUT / "source_benchmark_audit.csv", keep_default_na=False)
    papers = pd.read_csv(
        ROOT
        / "paper_runs/submission_evidence/retained_benchmark_ladder/"
        "paper_benchmark_summary.csv"
    )
    MODULE.validate_audit(audit, papers)
    assert len(audit) == audit["canonical_work_id"].nunique() == 40
    assert set(audit["canonical_work_id"]) == set(papers["canonical_work_id"])


def test_negative_source_coding_requires_verified_full_text() -> None:
    audit = pd.read_csv(OUTPUT / "source_benchmark_audit.csv", keep_default_na=False)
    verified = audit["full_text_status"].isin(MODULE.FULL_TEXT_STATUSES)
    assert int(verified.sum()) == 38
    assert int((~verified).sum()) == 2
    for column in (
        "asset_pricing_factor_regression",
        "factor_adjusted_intercept_reported",
        "jkp132_used",
    ):
        assert audit.loc[~verified, column].eq("unresolved").all()


def test_source_benchmark_counts_match_the_coded_ledger() -> None:
    summary = pd.read_csv(OUTPUT / "source_benchmark_summary.csv")
    values = dict(zip(summary["metric"], summary["value"]))
    assert values == {
        "mapped_papers": 40,
        "verified_full_text_papers": 38,
        "unresolved_papers": 2,
        "verified_without_asset_pricing_regression": 37,
        "verified_with_multifactor_loadings_only": 1,
        "verified_reporting_factor_adjusted_intercept": 0,
        "verified_using_jkp132": 0,
    }


def test_heterogeneity_join_preserves_strategy_denominator() -> None:
    joined = pd.read_csv(OUTPUT / "strategy_source_benchmark_results.csv")
    hetero = pd.read_csv(OUTPUT / "source_benchmark_heterogeneity.csv")
    assert len(joined) == joined["candidate_id"].nunique() == 50
    assert joined["canonical_work_id"].nunique() == 40
    factor_groups = hetero[
        hetero["grouping"].eq("asset_pricing_factor_regression")
    ]
    for benchmark_id in MODULE.BENCHMARK_IDS:
        group = factor_groups[factor_groups["benchmark_id"].eq(benchmark_id)]
        assert int(group["strategy_count"].sum()) == 50
        assert int(group["paper_count"].sum()) == 40
    manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
    assert manifest["paper_count"] == 40
    assert manifest["strategy_count"] == 50
