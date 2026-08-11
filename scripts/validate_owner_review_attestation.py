#!/usr/bin/env python3
"""Validate the separate human owner-review attestation without inventing it."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd


EXPECTED_REVIEWER = "Sasha Cui"
REVIEW_FIELDS = (
    "source_expression_match",
    "dsl_semantics_match",
    "input_mapping_acceptable",
    "evaluator_rule_match",
    "mechanical_changes_only",
)
REQUIRED_COLUMNS = (
    "candidate_id",
    "source_seed_id",
    "reviewer",
    "review_date",
    *REVIEW_FIELDS,
    "grade",
    "review_status",
    "notes",
)


def review_summary(
    attestation_path: Path,
    expected_candidates: dict[str, dict[str, str]],
) -> tuple[dict[str, object], list[str]]:
    failures: list[str] = []
    if not attestation_path.is_file():
        return (
            {"status": "missing", "completed_rows": 0, "required_rows": len(expected_candidates)},
            ["missing owner review attestation"],
        )

    frame = pd.read_csv(attestation_path, dtype=str, keep_default_na=False)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame]
    if missing_columns:
        return (
            {"status": "invalid", "completed_rows": 0, "required_rows": len(expected_candidates)},
            [f"owner review attestation is missing columns: {missing_columns}"],
        )

    if len(frame) != len(expected_candidates):
        failures.append("owner review attestation row count differs from the candidate census")
    if frame["candidate_id"].duplicated().any():
        failures.append("owner review attestation contains duplicate candidate rows")
    if set(frame["candidate_id"]) != set(expected_candidates):
        failures.append("owner review attestation candidate set differs from the census")

    statuses = frame["review_status"].str.strip().str.casefold()
    if not statuses.isin(["pending", "complete"]).all():
        failures.append("owner review status must be pending or complete")

    completed_rows = 0
    for row in frame.itertuples(index=False):
        candidate_id = row.candidate_id
        metadata = expected_candidates.get(candidate_id)
        if metadata is None:
            continue
        if row.source_seed_id != metadata["seed_id"]:
            failures.append(f"owner review source seed mismatch for {candidate_id}")
        status = row.review_status.strip().casefold()
        answers = {
            field: str(getattr(row, field)).strip().casefold()
            for field in REVIEW_FIELDS
        }
        if status == "pending":
            if any(answers.values()) or row.grade.strip() or row.reviewer.strip() or row.review_date.strip():
                failures.append(
                    f"pending owner review row contains completion fields for {candidate_id}"
                )
            continue

        completed_rows += 1
        if row.reviewer.strip() != EXPECTED_REVIEWER:
            failures.append(f"completed owner review has the wrong reviewer for {candidate_id}")
        try:
            date.fromisoformat(row.review_date.strip())
        except ValueError:
            failures.append(f"completed owner review has an invalid date for {candidate_id}")
        if set(answers.values()) != {"yes"}:
            failures.append(f"completed owner review does not affirm every check for {candidate_id}")
        if row.grade.strip() not in {"A", "B"}:
            failures.append(f"completed owner review is not strict grade A or B for {candidate_id}")

    if failures:
        status = "invalid"
    elif completed_rows == len(expected_candidates):
        status = "complete"
    else:
        status = "pending"
    return (
        {
            "status": status,
            "completed_rows": completed_rows,
            "required_rows": len(expected_candidates),
            "reviewer_required": EXPECTED_REVIEWER,
        },
        failures,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attestation", type=Path)
    args = parser.parse_args()

    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from run_faithful_component_replications import PRIMARY_COMPONENTS

    summary, failures = review_summary(args.attestation, PRIMARY_COMPONENTS)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "owner review "
        f"{summary['status']}: {summary['completed_rows']}/{summary['required_rows']} "
        "candidate attestations complete"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
