#!/usr/bin/env python3
"""Audit original-paper benchmarks and join them to the matched ladder.

The paper-level coding distinguishes a market or method comparator from an
asset-pricing spanning regression. Negative coding requires a verified full
PDF or full HTML text; inaccessible or partially indexed papers remain
unresolved. The resulting heterogeneity tables are descriptive because the
return mappings and source-benchmark coding were not outcome blind.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_AUDIT = Path(
    "paper_runs/submission_evidence/source_benchmark_audit/"
    "source_benchmark_audit.csv"
)
DEFAULT_LADDER = Path(
    "paper_runs/submission_evidence/retained_benchmark_ladder/"
    "strategy_benchmark_comparison.csv"
)
DEFAULT_PAPERS = Path(
    "paper_runs/submission_evidence/retained_benchmark_ladder/"
    "paper_benchmark_summary.csv"
)
DEFAULT_OUTPUT = Path(
    "paper_runs/submission_evidence/source_benchmark_audit"
)

BENCHMARK_IDS = ("capm", "ff3", "ff5_mom", "ff5_mom_jkp132")
FULL_TEXT_STATUSES = {"pdf_full_text", "html_full_text"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_audit(audit: pd.DataFrame, papers: pd.DataFrame) -> None:
    if len(audit) != audit["canonical_work_id"].nunique() or len(audit) != 40:
        raise ValueError("Source benchmark audit must contain 40 unique papers")
    expected = set(papers["canonical_work_id"])
    observed = set(audit["canonical_work_id"])
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise ValueError(f"Source audit mismatch; missing={missing}, extra={extra}")

    verified = audit["full_text_status"].isin(FULL_TEXT_STATUSES)
    negative_columns = (
        "asset_pricing_factor_regression",
        "factor_adjusted_intercept_reported",
        "jkp132_used",
    )
    if audit.loc[~verified, negative_columns].ne("unresolved").any().any():
        raise ValueError("Partial records cannot be coded as negative evidence")
    if audit.loc[verified, negative_columns].eq("unresolved").any().any():
        raise ValueError("Verified full texts must have complete benchmark coding")

    factor_models = audit.loc[verified, "asset_pricing_factor_regression"]
    expected_factor_models = {"none_identified": 37, "carhart4_and_ff5_loadings": 1}
    if factor_models.value_counts().to_dict() != expected_factor_models:
        raise ValueError("Verified source-benchmark counts changed")
    if audit.loc[verified, "factor_adjusted_intercept_reported"].ne("no").any():
        raise ValueError("A verified paper now reports a factor-adjusted intercept")
    if audit.loc[verified, "jkp132_used"].ne("no").any():
        raise ValueError("A verified paper now uses JKP132")


def summarize_audit(audit: pd.DataFrame) -> pd.DataFrame:
    verified = audit["full_text_status"].isin(FULL_TEXT_STATUSES)
    metrics = (
        ("mapped_papers", len(audit)),
        ("verified_full_text_papers", int(verified.sum())),
        ("unresolved_papers", int((~verified).sum())),
        (
            "verified_without_asset_pricing_regression",
            int(
                audit.loc[verified, "asset_pricing_factor_regression"]
                .eq("none_identified")
                .sum()
            ),
        ),
        (
            "verified_with_multifactor_loadings_only",
            int(
                audit.loc[verified, "asset_pricing_factor_regression"]
                .eq("carhart4_and_ff5_loadings")
                .sum()
            ),
        ),
        (
            "verified_reporting_factor_adjusted_intercept",
            int(
                audit.loc[verified, "factor_adjusted_intercept_reported"]
                .eq("yes")
                .sum()
            ),
        ),
        (
            "verified_using_jkp132",
            int(audit.loc[verified, "jkp132_used"].eq("yes").sum()),
        ),
    )
    return pd.DataFrame(metrics, columns=["metric", "value"])


def heterogeneity(joined: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    grouping_columns = (
        "asset_pricing_factor_regression",
        "original_benchmark_class",
        "implementation_basis",
    )
    for grouping in grouping_columns:
        for group_value, group in joined.groupby(grouping, dropna=False):
            for benchmark_id in BENCHMARK_IDS:
                alpha = group[f"{benchmark_id}_alpha_annualized"]
                records.append(
                    {
                        "grouping": grouping,
                        "group_value": group_value,
                        "benchmark_id": benchmark_id,
                        "paper_count": group["canonical_work_id"].nunique(),
                        "strategy_count": len(group),
                        "median_alpha_annualized": alpha.median(),
                        "positive_strategy_count": int(
                            group[f"{benchmark_id}_positive"].sum()
                        ),
                        "nominal_positive_strategy_count": int(
                            group[f"{benchmark_id}_nominal_positive"].sum()
                        ),
                        "holm_positive_strategy_count": int(
                            group[f"{benchmark_id}_holm_positive"].sum()
                        ),
                    }
                )
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--ladder", type=Path, default=DEFAULT_LADDER)
    parser.add_argument("--papers", type=Path, default=DEFAULT_PAPERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    root = args.root.resolve()
    audit_path = root / args.audit
    ladder_path = root / args.ladder
    papers_path = root / args.papers
    output = root / args.output
    output.mkdir(parents=True, exist_ok=True)

    audit = pd.read_csv(audit_path, keep_default_na=False)
    ladder = pd.read_csv(ladder_path)
    papers = pd.read_csv(papers_path)
    validate_audit(audit, papers)

    joined = ladder.merge(
        audit,
        on="canonical_work_id",
        how="left",
        validate="many_to_one",
    )
    if len(joined) != 50 or joined["canonical_work_id"].nunique() != 40:
        raise ValueError("Joined source-benchmark ledger changed denominator")

    summary = summarize_audit(audit)
    hetero = heterogeneity(joined)
    joined_path = output / "strategy_source_benchmark_results.csv"
    summary_path = output / "source_benchmark_summary.csv"
    hetero_path = output / "source_benchmark_heterogeneity.csv"
    joined.to_csv(joined_path, index=False)
    summary.to_csv(summary_path, index=False)
    hetero.to_csv(hetero_path, index=False)

    manifest = {
        "analysis_label": "source_paper_benchmark_audit_and_heterogeneity",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "interpretation": (
            "descriptive source-paper benchmark coding; negative coding requires "
            "verified full text; not outcome-blind"
        ),
        "paper_count": 40,
        "strategy_count": 50,
        "verified_full_text_papers": 38,
        "unresolved_papers": 2,
        "verified_without_asset_pricing_regression": 37,
        "verified_with_multifactor_loadings_only": 1,
        "verified_reporting_factor_adjusted_intercept": 0,
        "verified_using_jkp132": 0,
        "input_sha256": {
            str(audit_path.relative_to(root)): sha256(audit_path),
            str(ladder_path.relative_to(root)): sha256(ladder_path),
            str(papers_path.relative_to(root)): sha256(papers_path),
        },
        "output_sha256": {
            joined_path.name: sha256(joined_path),
            summary_path.name: sha256(summary_path),
            hetero_path.name: sha256(hetero_path),
        },
    }
    (output / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
