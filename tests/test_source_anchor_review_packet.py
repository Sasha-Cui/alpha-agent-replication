from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_source_anchor_review_packet_is_complete_and_cautious() -> None:
    path = ROOT / "paper_runs/submission_evidence/mapping_audit/source_anchor_review_packet.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 13
    assert len({row["source_index"] for row in rows}) == 5
    assert {row["exact_original_claim_match"] for row in rows} == {"no"}
    assert {row["mapping_frozen_before_returns"] for row in rows} == {"no"}
    assert {row["independent_outcome_blind_review"] for row in rows} == {"no"}
    assert {row["audit_status"] for row in rows} == {
        "post_hoc_source_anchor_audit; independent review pending"
    }
    assert all(row["source_locator"] and row["researcher_supplied_changes"] for row in rows)


def test_quantevolver_row_discloses_horizon_adaptation() -> None:
    path = ROOT / "paper_runs/submission_evidence/mapping_audit/source_anchor_review_packet.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        row = next(
            row for row in csv.DictReader(stream)
            if row["candidate_id"] == "repo_quantevolver_return_sharpe_proxy"
        )

    assert "60-bar" in row["source_supported_content"]
    assert "12-month" in row["researcher_supplied_changes"]
    assert "not the literal released expression" in row["researcher_supplied_changes"]
