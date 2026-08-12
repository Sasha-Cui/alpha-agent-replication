from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_factorminer_audit_routes_to_paper_only_without_artifact_inflation() -> None:
    subprocess.run(
        [sys.executable, "scripts/build_native_fidelity_ledger.py"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, "scripts/build_paper_evidence_routes.py"],
        cwd=ROOT,
        check=True,
    )
    with (ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        native = {row["system_id"]: row for row in csv.DictReader(stream)}
    row = native["SYS-FACTOR-MINER"]
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_110_formula_syntax_components_zero_of_488_table_"
        "cells_zero_of_12100_heatmap_cells_no_author_native_pipeline"
    )
    note = row["concise_evidence_note"]
    assert "488 numeric table-result cells" in note
    assert "12,100 annotations" in note
    assert "all 110 exact strings" in note
    assert "exactly matches just 2/110 printed formulas" in note
    assert "Zero regenerate from an author-native experiment" in note
    assert "10/110 heatmap labels conflict" in note
    assert "only 29/44 columns including ties" in note
    assert "first became public on 2025-12-17" in note

    with (
        ROOT
        / "paper_runs/submission_evidence/replication_scope/"
        "paper_evidence_route_ledger.csv"
    ).open(newline="", encoding="utf-8") as stream:
        routes = {row["canonical_work_id"]: row for row in csv.DictReader(stream)}
    route = routes["CensusArxiv260214670"]
    assert route["paper_evidence_route"] == "paper_only_underspecified"
    assert route["public_artifact_statuses"] == "not_listed"
    assert route["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert route["native_execution_audit_status"] == row["targeted_execution_audit_status"]
    assert route["full_prompt_search_training_pipeline_reproduced"] == "no"
