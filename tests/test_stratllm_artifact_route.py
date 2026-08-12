from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK_ID = "CensusArxiv260506024"


def test_stratllm_route_preserves_zero_native_result_boundary() -> None:
    route = (
        ROOT
        / "paper_runs/submission_evidence/replication_scope/"
        "paper_evidence_route_ledger.csv"
    )
    with route.open(newline="", encoding="utf-8") as stream:
        selected = [
            row
            for row in csv.DictReader(stream)
            if row["canonical_work_id"] == WORK_ID
        ]
    assert len(selected) == 1
    row = selected[0]
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["reachable_public_code_system_ids"] == ""
    assert row["native_pipeline_disposition"] == (
        "paper_only_audit_recorded_no_native_code_pipeline"
    )
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_zero_of_190_unique_empirical_units_"
        "live_forward_chronology_contradicted"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["proxy_role"] == "no_proxy"

    blocker = row["precise_native_or_access_blocker"]
    assert "190 unique empirical units" in blocker
    assert "Zero reproduce from the native system" in blocker
    assert "HTTP 404" in blocker
    assert "live-forward interpretation" in blocker
    assert "eight in 2026" in blocker
    assert "chronological replay" in blocker
    assert "complete strategy rules" in blocker
    assert "immutable model requests" in blocker
    assert "No local proxy is credited" in blocker
