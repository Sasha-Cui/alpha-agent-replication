from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK_ID = "CensusArxiv250817565"


def test_paper_route_records_completed_audit_without_inventing_code() -> None:
    route = ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    with route.open(newline="", encoding="utf-8") as stream:
        selected = [
            row for row in csv.DictReader(stream)
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
        "paper_audit:completed_152_of_156_source_adjacent_baseline_cells_"
        "120_of_120_deterministic_32_of_36_model_cells_24_coin_guard_cells_recovered_"
        "4_xgboost_coin_cells_conflict_"
        "zero_of_120_unique_native_table_cells_zero_of_15_native_curves"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    blocker = row["precise_native_or_access_blocker"]
    assert "152/156" in blocker and "two-year" in blocker
    assert "120/120 deterministic cells" in blocker
    assert "24 COIN cells" in blocker
    assert "16/20 XGBoost cells" in blocker
    assert "matches 0/4 COIN cells" in blocker
    assert "0/120" in blocker and "0/15" in blocker
    assert "Qwen3-Trader" in blocker and "FINSABER" in blocker
    assert row["proxy_role"] == "no_proxy"
