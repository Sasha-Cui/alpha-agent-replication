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


def test_alphalogics_is_a_targeted_paper_only_audit_with_zero_native_credit() -> None:
    ledger = rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in ledger if item["system_id"] == "SYS-ALPHA-LOGICS")
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_zero_of_158_table_units_zero_of_204_figure_markers_"
        "zero_of_18_empirical_panels_two_paper_derived_algorithm_checks_three_"
        "unattributable_candidates"
    )
    assert row["fidelity_class"] == "F0_no_public_artifact"
    note = row["concise_evidence_note"]
    assert "0/158 exact table units" in note
    assert "0/204 displayed figure markers" in note
    assert "0/18 empirical panels" in note
    assert "eight active valid-JSON agent templates" in note
    assert "59 DSL operation signatures" in note
    assert "52 focused tests pass" in note
    assert "no native credit" in note
    assert "favorable narrative motif proxy" in note


def test_alphalogics_paper_route_exposes_the_precise_blocker() -> None:
    routes = rows(
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    row = next(item for item in routes if item["canonical_work_id"] == "CensusArxiv260320247")
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["public_artifact_statuses"] == "not_listed"
    assert row["static_fidelity_tiers"] == ""
    assert row["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert row["native_execution_audit_status"].startswith(
        "paper_audit:completed_zero_of_158_table_units"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["good_faith_reconstruction"] == "yes"
    assert row["mapping_count"] == "1"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["proxy_role"] == "clearly_labeled_favorable_motif_proxy"
    assert row["negative_inference_boundary"] == "no_negative_inference_about_source"
    blocker = row["precise_native_or_access_blocker"]
    assert "SYS-ALPHA-LOGICS:A0_no_public_artifact" in blocker
    assert "0/158 exact table units" in blocker
    assert "0/204 displayed figure markers" in blocker
    assert "0/18 empirical panels" in blocker


def test_static_report_and_claim_ledger_count_alphalogics_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\TargetedAuditCount}{67}" in generated
    claims = {row["macro"]: row for row in rows(ROOT / "paper_runs/submission_evidence/claims.csv")}
    assert claims["TargetedAuditCount"]["rendered_value"] == "67"
    assert claims["TargetedAuditCount"]["source_sha256"] == sha256(
        ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
    )
    failures = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "AlphaLogics" in failures
    assert "0/158 exact table units" in failures
    assert failures.count("AlphaLogics &") == 1


def test_manifest_preserves_source_and_no_native_result_boundary() -> None:
    data = json.loads(
        (ROOT / "paper_runs/paper_replication_audits/alphalogics/manifest.json").read_text()
    )
    assert data["official_pdf_recovered"] is True
    assert data["official_source_recovered"] is True
    assert data["unmodified_source_rebuild_completed"] is True
    assert data["active_agent_prompt_templates"] == 8
    assert data["valid_json_prompt_templates"] == 8
    assert data["dsl_operations_specified"] == 59
    assert data["paper_derived_algorithm_checks_passed"] == 2
    assert data["attributable_alphalogics_code_recovered"] is False
    assert data["published_numeric_table_units"] == 158
    assert data["native_numeric_table_units_regenerated"] == 0
    assert data["empirical_panels"] == 18
    assert data["native_empirical_panels_regenerated"] == 0
    assert data["displayed_figure_result_markers"] == 204
    assert data["native_figure_result_markers_regenerated"] == 0
    assert data["independent_candidates_with_native_credit"] == 0
    assert data["full_end_to_end_pipeline_reproduced"] is False
    assert data["strict_success"] is False
