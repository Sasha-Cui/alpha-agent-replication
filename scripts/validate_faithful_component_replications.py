#!/usr/bin/env python3
"""Fail-closed PR-style validation of the counted replication sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_faithful_component_replications import (  # noqa: E402
    DEFAULT_OUT,
    PRIMARY_COMPONENTS,
    SOURCE_COMMIT,
    SOURCE_FILES,
    SOURCE_REPOSITORY,
    verify_upstream_source,
)
from check_upstream_conformance import conformance_report  # noqa: E402
from validate_owner_review_attestation import review_summary  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_bool(series: pd.Series) -> pd.Series:
    return series.map(
        lambda value: value
        if isinstance(value, bool)
        else str(value).strip().casefold() == "true"
    )


def validation_failures(
    component_dir: Path, *, require_full_evidence: bool = False
) -> list[str]:
    failures: list[str] = []
    required_files = {
        "manifest.json",
        "faithfulness_ledger.csv",
        "upstream_conformance.json",
        "owner_review_attestation.csv",
    }
    access_gated_files = {"monthly_return_paths.csv", "formation_holdings.csv"}
    if require_full_evidence:
        required_files |= access_gated_files
    missing_files = sorted(
        name for name in required_files if not (component_dir / name).is_file()
    )
    if missing_files:
        return [f"missing required artifact: {name}" for name in missing_files]

    manifest = json.loads((component_dir / "manifest.json").read_text(encoding="utf-8"))
    ledger = pd.read_csv(component_dir / "faithfulness_ledger.csv")
    full_evidence_available = all(
        (component_dir / name).is_file() for name in access_gated_files
    )
    paths = pd.read_csv(component_dir / "monthly_return_paths.csv") if full_evidence_available else None
    holdings = pd.read_csv(component_dir / "formation_holdings.csv") if full_evidence_available else None
    expected_candidates = set(PRIMARY_COMPONENTS)

    stored_conformance = json.loads(
        (component_dir / "upstream_conformance.json").read_text(encoding="utf-8")
    )
    _, reference_failures = conformance_report()
    failures.extend(
        f"upstream reference conformance: {failure}"
        for failure in reference_failures
    )
    if stored_conformance.get("passed") is not True:
        failures.append("tracked upstream conformance report is not passing")
    if set(stored_conformance.get("candidate_results", {})) != expected_candidates:
        failures.append("upstream conformance report does not cover the candidate census")
    _owner_review, owner_review_failures = review_summary(
        component_dir / "owner_review_attestation.csv", PRIMARY_COMPONENTS
    )
    failures.extend(owner_review_failures)

    if manifest.get("study_role") != "primary_counted_faithful_disclosed_components":
        failures.append("manifest study_role does not identify the primary counted sample")
    if manifest.get("source_repository") != SOURCE_REPOSITORY:
        failures.append("source repository is not the pinned QuantEvolver repository")
    if manifest.get("source_commit") != SOURCE_COMMIT:
        failures.append("source commit differs from the audited pin")
    if manifest.get("source_file_sha256") != SOURCE_FILES:
        failures.append("source file hashes differ from audited pins")
    if manifest.get("technical_reference_conformance_passed") is not True:
        failures.append("manifest does not record passing technical conformance")

    if set(ledger.get("candidate_id", [])) != expected_candidates:
        failures.append("ledger is not the exhaustive three-valid-seed census")
    if len(ledger) != len(expected_candidates):
        failures.append("ledger has duplicate or extra counted rows")
    if "counted_primary" not in ledger or not as_bool(ledger["counted_primary"]).all():
        failures.append("every ledger row must be explicitly counted_primary")
    if "grade" not in ledger or not ledger["grade"].isin(["A", "B"]).all():
        failures.append("every counted row must have strict grade A or B")
    if "grade" in ledger and ledger["grade"].astype(str).str.contains(
        "conditional", case=False
    ).any():
        failures.append("conditional grades are forbidden in the counted sample")

    exact_columns = [
        "source_expression_exact",
        "source_operator_semantics_exact",
        "source_evaluator_rule_exact",
        "source_return_definition_exact",
        "formula_census_outcome_independent",
        "only_permitted_mechanical_changes",
    ]
    for column in exact_columns:
        if column not in ledger or not as_bool(ledger[column]).all():
            failures.append(f"counted rows do not all satisfy {column}")
    for column in [
        "native_agent_replication",
        "full_search_or_training_pipeline_reproduced",
    ]:
        if column not in ledger or as_bool(ledger[column]).any():
            failures.append(f"component scope is misstated in {column}")
    if "source_commit" not in ledger or set(ledger["source_commit"]) != {SOURCE_COMMIT}:
        failures.append("ledger source commits are not pinned consistently")
    if "independent_second_coder_status" not in ledger or set(
        ledger["independent_second_coder_status"]
    ) != {"tracked_in_owner_review_attestation"}:
        failures.append("ledger misstates the separate owner-review record")
    for candidate_id, metadata in PRIMARY_COMPONENTS.items():
        rows = ledger[ledger.get("candidate_id") == candidate_id]
        if len(rows) != 1:
            continue
        row = rows.iloc[0]
        if row.get("source_seed_id") != metadata["seed_id"]:
            failures.append(f"wrong source seed id for {candidate_id}")
        if row.get("exact_source_expression") != metadata["expression"]:
            failures.append(f"source expression drift for {candidate_id}")

    expected_count = len(expected_candidates)
    if manifest.get("n_counted_components") != expected_count:
        failures.append("manifest counted-component total is wrong")
    if manifest.get("n_grade_a_or_b") != expected_count:
        failures.append("manifest strict-pass count is wrong")
    if manifest.get("faithfulness_pass_rate") != 1.0:
        failures.append("manifest faithfulness pass rate is not 100%")
    if not full_evidence_available:
        for name, expected_hash in manifest.get("output_sha256", {}).items():
            if name in access_gated_files:
                continue
            path = component_dir / name
            if not path.is_file() or sha256(path) != expected_hash:
                failures.append(f"tracked output hash mismatch: {name}")
        return failures

    assert paths is not None and holdings is not None
    if set(paths.get("candidate_id", [])) != expected_candidates:
        failures.append("return paths do not cover exactly the counted candidates")
    if paths.duplicated(["candidate_id", "formation_month"]).any():
        failures.append("duplicate candidate/formation-month return rows")
    if "portfolio_rule_id" not in paths or set(paths["portfolio_rule_id"]) != {
        "released_pair_dropna_top_bottom_quintile_equal_mean"
    }:
        failures.append("return paths do not use the released pair/dropna quintile rule")
    if "return_definition" not in paths or set(paths["return_definition"]) != {
        "released_next_bar_close_return_long_mean_minus_short_mean"
    }:
        failures.append("return paths do not use the released forward-return definition")
    if "cost_bps_one_way" not in paths or not np.allclose(
        paths["cost_bps_one_way"], 0.0
    ):
        failures.append("counted returns must not add researcher-specified costs")
    if "source_spearman_rank_ic" not in paths or not np.isfinite(
        paths["source_spearman_rank_ic"]
    ).all():
        failures.append("paths do not preserve the source finite-rank-IC eligibility rule")
    if "gross_excess_return" not in paths or "net_excess_return" not in paths or not np.allclose(
        paths["gross_excess_return"], paths["net_excess_return"], equal_nan=False
    ):
        failures.append("counted gross and net columns must equal the released evaluator return")
    if {"n_eligible_source_pairs", "n_long", "n_short"}.issubset(paths):
        expected_side = np.maximum(1, (paths["n_eligible_source_pairs"] * 0.2).astype(int))
        if not (paths["n_long"].to_numpy() == expected_side).all():
            failures.append("long leg size differs from source floor-20% rule")
        if not (paths["n_short"].to_numpy() == expected_side).all():
            failures.append("short leg size differs from source floor-20% rule")
    else:
        failures.append("path leg-size evidence is incomplete")
    if paths.groupby("candidate_id").size().min() < 20:
        failures.append("a counted component has fewer than 20 source-evaluator times")

    required_holding_columns = {
        "candidate_id",
        "formation_month",
        "side",
        "source_forward_return",
        "source_evaluator_weight",
    }
    if not required_holding_columns.issubset(holdings):
        failures.append("holding evidence is incomplete")
    else:
        reconstructed = (
            holdings.assign(
                weighted_return=(
                    holdings["source_forward_return"]
                    * holdings["source_evaluator_weight"]
                )
            )
            .groupby(["candidate_id", "formation_month"], as_index=False)[
                "weighted_return"
            ]
            .sum()
        )
        compared = paths.merge(
            reconstructed, on=["candidate_id", "formation_month"], how="left", validate="one_to_one"
        )
        if compared["weighted_return"].isna().any() or not np.allclose(
            compared["gross_excess_return"], compared["weighted_return"], atol=1e-14
        ):
            failures.append("return paths do not reconstruct exactly from source-evaluator holdings")

    for name, expected_hash in manifest.get("output_sha256", {}).items():
        path = component_dir / name
        if not path.is_file() or sha256(path) != expected_hash:
            failures.append(f"tracked output hash mismatch: {name}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--verify-upstream", action="store_true")
    parser.add_argument(
        "--require-full-evidence",
        action="store_true",
        help="require access-gated return paths and holdings and reconstruct every return",
    )
    args = parser.parse_args()
    if args.verify_upstream:
        verify_upstream_source()
    failures = validation_failures(
        args.component_dir, require_full_evidence=args.require_full_evidence
    )
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    owner_review, _ = review_summary(
        args.component_dir / "owner_review_attestation.csv", PRIMARY_COMPONENTS
    )
    print("technical faithfulness passed: 3/3 counted components (100%) are strict grade B")
    print(
        f"independent owner review {owner_review['status']}: "
        f"{owner_review['completed_rows']}/{owner_review['required_rows']} rows complete"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
