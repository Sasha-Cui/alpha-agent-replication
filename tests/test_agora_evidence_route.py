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


def test_agora_is_targeted_with_two_paper_components_but_zero_native_result_credit() -> None:
    ledger = rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in ledger if item["system_id"] == "SYS-AGORA")
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_two_paper_metric_programs_zero_of_293_table_cells_zero_of_4_"
        "empirical_panels_claimed_release_unrecovered_no_attributable_pipeline"
    )
    assert row["fidelity_class"] == "F0_no_public_artifact"
    note = row["concise_evidence_note"]
    assert "42-page arXiv-v1" in note
    assert "293 displayed quantitative result cells" in note
    assert "four empirical vector-PDF panels" in note
    assert "two complete metric programs" in note
    assert "paper-derived component checks" in note
    assert "neither the PDF nor TeX contains a repository URL" in note
    assert "0/293 table cells" in note
    assert "0/4 empirical panels" in note
    assert "eight versus nine skill libraries" in note
    assert "91 versus 60 holdout observations" in note


def test_agora_paper_route_exposes_claimed_but_unrecovered_release() -> None:
    routes = rows(ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv")
    row = next(item for item in routes if item["canonical_work_id"] == "CensusArxiv260629194")
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["public_artifact_statuses"] == "not_listed"
    assert row["static_fidelity_tiers"] == ""
    assert row["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert row["native_execution_audit_status"].startswith("paper_audit:completed_two_paper_metric_programs")
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["good_faith_reconstruction"] == "no"
    assert row["mapping_count"] == "0"
    assert row["mapping_fidelity_tiers"] == ""
    assert row["mapping_disposition"] == "availability_only_no_performance_inference"
    assert row["proxy_role"] == "no_proxy"
    assert row["negative_inference_boundary"] == "no_performance_inference"
    blocker = row["precise_native_or_access_blocker"]
    assert "SYS-AGORA:A0_no_public_artifact" in blocker
    assert "two complete metric programs" in blocker
    assert "0/293 table cells" in blocker
    assert "0/4 empirical panels" in blocker


def test_static_report_and_claim_ledger_count_agora_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\TargetedAuditCount}{66}" in generated
    claims = {row["macro"]: row for row in rows(ROOT / "paper_runs/submission_evidence/claims.csv")}
    assert claims["TargetedAuditCount"]["rendered_value"] == "66"
    assert claims["TargetedAuditCount"]["source_sha256"] == sha256(
        ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
    )
    failures = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "Agora" in failures
    assert "0/293 table cells" in failures
    assert "two complete metric programs" in failures
    assert failures.count("Agora — AI Trading's Alpha Singularity &") == 1


def test_manifest_preserves_component_and_zero_native_result_boundary() -> None:
    data = json.loads((ROOT / "paper_runs/paper_replication_audits/agora/manifest.json").read_text())
    assert data["active_quantitative_table_cells"] == 293
    assert data["author_native_table_cells_regenerated"] == 0
    assert data["active_empirical_figure_panels"] == 4
    assert data["author_native_empirical_panels_regenerated"] == 0
    assert data["complete_paper_metric_programs_executed"] == 2
    assert data["paper_metric_programs_passing_controlled_checks"] == 2
    assert data["attributable_agora_implementation_found"] is False
    assert data["strict_success"] is False
