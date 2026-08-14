from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_agentic_ai_audit_routes_to_paper_only_without_artifact_inflation() -> None:
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
    row = native["SYS-AGENTIC-AI-SCREENING"]
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_v1_zero_of_953_v2_zero_of_1344_one_linked_input_"
        "one_date_prompt_no_author_native_pipeline"
    )
    note = row["concise_evidence_note"]
    assert "953 v1" in note
    assert "1,344 v2" in note
    assert "0/2,297" in note
    assert "4,589 rows" in note
    assert "December 2023" in note
    assert "full annual prompt histories" in note.lower()
    assert "`01092`" in note
    assert "September 2021" in note
    assert "October 2023" in note
    assert "exact author model snapshots" in note
    assert "inactive" in note
    assert "passes 114 tests" in note
    assert "receives no native or paper-result credit" in note

    with (ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        routes = {row["canonical_work_id"]: row for row in csv.DictReader(stream)}
    route = routes["CensusArxiv260323300"]
    assert route["paper_evidence_route"] == "paper_only_underspecified"
    assert route["public_artifact_statuses"] == "not_listed"
    assert route["native_pipeline_disposition"] == ("paper_only_audit_recorded_no_native_code_pipeline")
    assert route["native_execution_audit_status"] == row["targeted_execution_audit_status"]
    assert route["full_prompt_search_training_pipeline_reproduced"] == "no"
