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


def test_xalpha_is_targeted_with_paper_components_but_zero_native_result_credit() -> None:
    ledger = rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in ledger if item["system_id"] == "SYS-XALPHA")
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_three_paper_factor_programs_one_contract_pass_zero_of_138_"
        "numeric_units_zero_of_3_empirical_panels_no_attributable_pipeline"
    )
    assert row["fidelity_class"] == "F0_no_public_artifact"
    note = row["concise_evidence_note"]
    assert "61-page arXiv-v2" in note
    assert "20 named agent/utility prompt frameworks" in note
    assert "Three printed factor programs execute verbatim" in note
    assert "only the main-text program satisfies" in note
    assert "HTTP 404" in note
    assert "27 public repositories" in note
    assert "0/138 published numeric units" in note
    assert "0/3 empirical panels" in note
    assert "No exact Qlib snapshot" in note


def test_xalpha_paper_route_exposes_the_precise_blocker() -> None:
    routes = rows(ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv")
    row = next(item for item in routes if item["canonical_work_id"] == "CensusArxiv260708332")
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["public_artifact_statuses"] == "not_listed"
    assert row["static_fidelity_tiers"] == ""
    assert row["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert row["native_execution_audit_status"].startswith("paper_audit:completed_three_paper_factor_programs")
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["good_faith_reconstruction"] == "no"
    assert row["mapping_count"] == "0"
    assert row["mapping_fidelity_tiers"] == ""
    assert row["mapping_disposition"] == "availability_only_no_performance_inference"
    assert row["proxy_role"] == "no_proxy"
    assert row["negative_inference_boundary"] == "no_performance_inference"
    blocker = row["precise_native_or_access_blocker"]
    assert "SYS-XALPHA:A0_no_public_artifact" in blocker
    assert "Three printed factor programs execute verbatim" in blocker
    assert "0/138 published numeric units" in blocker
    assert "0/3 empirical panels" in blocker


def test_static_report_and_claim_ledger_count_xalpha_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\TargetedAuditCount}{62}" in generated
    claims = {row["macro"]: row for row in rows(ROOT / "paper_runs/submission_evidence/claims.csv")}
    assert claims["TargetedAuditCount"]["rendered_value"] == "62"
    assert claims["TargetedAuditCount"]["source_sha256"] == sha256(
        ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
    )
    failures = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "XALPHA" in failures
    assert "0/138 published numeric units" in failures
    assert "Three printed factor programs" in failures
    assert failures.count("XALPHA &") == 1


def test_manifest_preserves_component_and_zero_native_result_boundary() -> None:
    data = json.loads((ROOT / "paper_runs/paper_replication_audits/xalpha/manifest.json").read_text())
    assert data["active_numeric_result_units"] == 138
    assert data["author_native_numeric_result_units_regenerated"] == 0
    assert data["active_empirical_figure_panels"] == 3
    assert data["author_native_empirical_panels_regenerated"] == 0
    assert data["paper_factor_programs_executed"] == 3
    assert data["paper_factor_programs_passing_output_name_contract"] == 1
    assert data["attributable_xalpha_implementation_found"] is False
    assert data["strict_success"] is False
