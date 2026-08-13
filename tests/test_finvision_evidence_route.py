from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_finvision_is_a_targeted_paper_only_audit_with_zero_native_credit() -> None:
    ledger = rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in ledger if item["system_id"] == "SYS-FIN-VISION")
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_zero_of_72_performance_cells_no_public_system_source"
    )
    assert row["fidelity_class"] == "F0_no_public_artifact"
    note = row["concise_evidence_note"]
    assert "0/72 cells reproduce" in note
    assert "five printed prompt templates" in note
    assert "3/9 Market cells" in note
    assert "42/145" in note and "41/147" in note
    assert "not proof" in note


def test_finvision_paper_route_exposes_the_precise_blocker() -> None:
    routes = rows(
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    row = next(item for item in routes if item["canonical_work_id"] == "CensusArxiv241108899")
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["public_artifact_statuses"] == "not_listed"
    assert row["static_fidelity_tiers"] == ""
    assert row["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_zero_of_72_performance_cells_no_public_system_source"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert "SYS-FIN-VISION:A0_no_public_artifact" in row["precise_native_or_access_blocker"]
    assert "0/72 cells reproduce" in row["precise_native_or_access_blocker"]


def test_static_report_and_claim_ledger_count_finvision_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\TargetedAuditCount}{46}" in generated
    claims = {row["macro"]: row for row in rows(ROOT / "paper_runs/submission_evidence/claims.csv")}
    assert claims["TargetedAuditCount"]["rendered_value"] == "46"
    assert claims["TargetedAuditCount"]["source_sha256"] == sha256(
        ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
    )
    failures = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "FinVision" in failures
    assert "0/72 cells reproduce" in failures


def test_paper_manifest_and_routed_summary_share_the_same_zero_credit_boundary() -> None:
    manifest = json.loads(
        (ROOT / "paper_runs/paper_replication_audits/finvision/manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["published_performance_cells"] == 72
    assert manifest["published_performance_cells_faithfully_regenerated"] == 0
    assert manifest["current_yahoo_diagnostic_display_matches"] == 3
    assert manifest["current_yahoo_diagnostic_faithful_credit"] == 0
    assert manifest["full_end_to_end_pipeline_reproduced"] is False
