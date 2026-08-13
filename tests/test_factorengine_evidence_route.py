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


def test_factorengine_is_a_targeted_paper_only_audit_with_zero_native_credit() -> None:
    ledger = rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in ledger if item["system_id"] == "SYS-FACTOR-ENGINE")
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_zero_of_276_table_units_zero_of_8_empirical_panels_"
        "one_of_two_printed_factor_programs_executes_one_unattributable_candidate"
    )
    assert row["fidelity_class"] == "F0_no_public_artifact"
    note = row["concise_evidence_note"]
    assert "0/276 table units" in note
    assert "0/8 empirical panels" in note
    assert "two evolution prompt templates" in note
    assert "daily_range_expr is undefined" in note
    assert "26-evaluation synthetic" in note
    assert "no native or result credit" in note
    assert "M0 proxy remains narrative only" in note


def test_factorengine_paper_route_exposes_the_precise_blocker() -> None:
    routes = rows(ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv")
    row = next(item for item in routes if item["canonical_work_id"] == "CensusArxiv260316365")
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["public_artifact_statuses"] == "not_listed"
    assert row["static_fidelity_tiers"] == ""
    assert row["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert row["native_execution_audit_status"].startswith("paper_audit:completed_zero_of_276_table_units")
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["good_faith_reconstruction"] == "yes"
    assert row["mapping_count"] == "1"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["proxy_role"] == "clearly_labeled_favorable_motif_proxy"
    assert row["negative_inference_boundary"] == "no_negative_inference_about_source"
    blocker = row["precise_native_or_access_blocker"]
    assert "SYS-FACTOR-ENGINE:A0_no_public_artifact" in blocker
    assert "0/276 table units" in blocker
    assert "0/8 empirical panels" in blocker
    assert "daily_range_expr is undefined" in blocker


def test_static_report_and_claim_ledger_count_factorengine_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\TargetedAuditCount}{56}" in generated
    claims = {row["macro"]: row for row in rows(ROOT / "paper_runs/submission_evidence/claims.csv")}
    assert claims["TargetedAuditCount"]["rendered_value"] == "56"
    assert claims["TargetedAuditCount"]["source_sha256"] == sha256(
        ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
    )
    failures = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "FactorEngine" in failures
    assert "0/276 table units" in failures
    assert failures.count("FactorEngine &") == 1


def test_manifest_preserves_source_and_no_native_result_boundary() -> None:
    data = json.loads((ROOT / "paper_runs/paper_replication_audits/factorengine/manifest.json").read_text())
    assert data["paper_versions_audited"] == 2
    assert data["official_pages_visually_checked"] == 52
    assert data["rebuilt_pages_visually_checked"] == 52
    assert data["published_numeric_table_units"] == 276
    assert data["native_table_units_regenerated"] == 0
    assert data["empirical_panels"] == 8
    assert data["native_empirical_panels_regenerated"] == 0
    assert data["evolution_prompt_templates"] == 2
    assert data["printed_factor_programs"] == 2
    assert data["verbatim_factor_programs_executing"] == 1
    assert data["attributable_code_release_found"] is False
    assert data["strict_success"] is False
