from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hubble_audit_routes_to_paper_only_without_artifact_inflation() -> None:
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
    row = native["SYS-HUBBLE"]
    assert row["public_artifact_status"] == "not_listed"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_v1_zero_of_47_unique_cells_v2_zero_of_102_unique_"
        "cells_zero_of_50_figure_series_formulas_intentionally_withheld"
    )
    note = row["concise_evidence_note"]
    assert "50 v1 numeric table cells (47 unique)" in note
    assert "108 v2 cells (102 unique)" in note
    assert "Zero regenerate from the native system" in note
    assert "explicitly withholds exact formulas" in note
    assert "both named backends first became public on 2026-03-11" in note
    assert "No unaffiliated implementation" in note

    with (
        ROOT
        / "paper_runs/submission_evidence/replication_scope/"
        "paper_evidence_route_ledger.csv"
    ).open(
        newline="", encoding="utf-8"
    ) as stream:
        routes = {row["canonical_work_id"]: row for row in csv.DictReader(stream)}
    route = routes["CensusArxiv260409601"]
    assert route["paper_evidence_route"] == "paper_only_underspecified"
    assert route["public_artifact_statuses"] == "not_listed"
    assert route["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert route["native_execution_audit_status"] == row["targeted_execution_audit_status"]
    assert route["full_prompt_search_training_pipeline_reproduced"] == "no"
