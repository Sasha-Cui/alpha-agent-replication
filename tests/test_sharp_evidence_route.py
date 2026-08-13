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


def test_sharp_is_targeted_with_seven_paper_mechanics_but_zero_native_result_credit() -> None:
    ledger = rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in ledger if item["system_id"] == "SYS-SHARP")
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_seven_paper_derived_mechanics_zero_of_210_table_cells_zero_of_1_"
        "empirical_panel_cited_dataset_404_no_attributable_pipeline"
    )
    assert row["fidelity_class"] == "F0_no_public_artifact"
    note = row["concise_evidence_note"]
    assert "18-page arXiv-v1" in note
    assert "210 displayed quantitative result cells" in note
    assert "six plotted series" in note
    assert "Seven independently implemented paper-derived mechanics" in note
    assert "specification checks, not author code" in note
    assert "currently return HTTP 404" in note
    assert "0/210 table cells" in note
    assert "0/1 empirical panel" in note
    assert "six versus seven initial shared rules" in note


def test_sharp_paper_route_exposes_dead_cited_dataset_and_missing_pipeline() -> None:
    routes = rows(ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv")
    row = next(item for item in routes if item["canonical_work_id"] == "CensusArxiv260506822")
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["public_artifact_statuses"] == "not_listed"
    assert row["static_fidelity_tiers"] == ""
    assert row["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert row["native_execution_audit_status"].startswith("paper_audit:completed_seven_paper_derived_mechanics")
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["good_faith_reconstruction"] == "no"
    assert row["mapping_count"] == "0"
    assert row["mapping_fidelity_tiers"] == ""
    assert row["mapping_disposition"] == "availability_only_no_performance_inference"
    assert row["proxy_role"] == "no_proxy"
    assert row["negative_inference_boundary"] == "no_performance_inference"
    blocker = row["precise_native_or_access_blocker"]
    assert "SYS-SHARP:A0_no_public_artifact" in blocker
    assert "Seven independently implemented paper-derived mechanics" in blocker
    assert "0/210 table cells" in blocker
    assert "0/1 empirical panel" in blocker


def test_static_report_and_claim_ledger_count_sharp_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\TargetedAuditCount}{66}" in generated
    claims = {row["macro"]: row for row in rows(ROOT / "paper_runs/submission_evidence/claims.csv")}
    assert claims["TargetedAuditCount"]["rendered_value"] == "66"
    assert claims["TargetedAuditCount"]["source_sha256"] == sha256(
        ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
    )
    failures = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "0/210 table cells" in failures
    assert "Seven independently implemented paper-derived mechanics" in failures
    assert failures.count("SHARP &") == 1


def test_manifest_preserves_component_and_zero_native_result_boundary() -> None:
    data = json.loads((ROOT / "paper_runs/paper_replication_audits/sharp/manifest.json").read_text())
    assert data["active_quantitative_table_cells"] == 210
    assert data["author_native_table_cells_regenerated"] == 0
    assert data["active_empirical_figure_panels"] == 1
    assert data["author_native_empirical_panels_regenerated"] == 0
    assert data["paper_derived_components_executed"] == 7
    assert data["paper_derived_components_passing_controlled_checks"] == 7
    assert data["attributable_sharp_implementation_found"] is False
    assert data["strict_success"] is False
