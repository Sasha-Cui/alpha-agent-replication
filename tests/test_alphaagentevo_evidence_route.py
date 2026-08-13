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


def test_alphaagentevo_is_a_targeted_paper_only_audit_with_zero_native_credit() -> None:
    ledger = rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in ledger if item["system_id"] == "SYS-ALPHA-AGENT-EVO")
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_zero_of_147_table_units_zero_of_21_empirical_panels_"
        "zero_of_40_figure_annotations_listed_unrecovered_supplement_no_attributable_pipeline"
    )
    assert row["fidelity_class"] == "F0_no_public_artifact"
    note = row["concise_evidence_note"]
    assert "0/147 table units" in note
    assert "0/21 empirical panels" in note
    assert "0/40 exact figure annotations" in note
    assert "listed but not inspected or presumed absent" in note
    assert "Vietnam-market prompts" in note
    assert "step 90/150" in note
    assert "no native credit" in note
    assert "favorable narrative motif proxy" in note


def test_alphaagentevo_paper_route_exposes_the_precise_blocker() -> None:
    routes = rows(
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    row = next(item for item in routes if item["canonical_work_id"] == "CensusORlNmZrawUMu")
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["public_artifact_statuses"] == "not_listed"
    assert row["static_fidelity_tiers"] == ""
    assert row["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert row["native_execution_audit_status"].startswith(
        "paper_audit:completed_zero_of_147_table_units"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["good_faith_reconstruction"] == "yes"
    assert row["mapping_count"] == "1"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["proxy_role"] == "clearly_labeled_favorable_motif_proxy"
    assert row["negative_inference_boundary"] == "no_negative_inference_about_source"
    blocker = row["precise_native_or_access_blocker"]
    assert "SYS-ALPHA-AGENT-EVO:A0_no_public_artifact" in blocker
    assert "0/147 table units" in blocker
    assert "0/21 empirical panels" in blocker


def test_static_report_and_claim_ledger_count_alphaagentevo_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\TargetedAuditCount}{56}" in generated
    claims = {row["macro"]: row for row in rows(ROOT / "paper_runs/submission_evidence/claims.csv")}
    assert claims["TargetedAuditCount"]["rendered_value"] == "56"
    assert claims["TargetedAuditCount"]["source_sha256"] == sha256(
        ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
    )
    failures = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "AlphaAgentEvo" in failures
    assert "0/147 table units" in failures
    assert failures.count("AlphaAgentEvo &") == 1


def test_manifest_preserves_the_listed_but_unrecovered_boundary() -> None:
    manifest = json.loads(
        (ROOT / "paper_runs/paper_replication_audits/alphaagentevo/manifest.json").read_text()
    )
    assert manifest["official_pdf_recovered"] is True
    assert manifest["official_pages_visually_checked"] == 18
    assert manifest["official_supplement_listed"] is True
    assert manifest["official_supplement_recovered"] is False
    assert manifest["attributable_alphaagentevo_code_recovered"] is False
    assert manifest["published_numeric_result_units"] == 147
    assert manifest["native_numeric_units_regenerated"] == 0
    assert manifest["empirical_panels"] == 21
    assert manifest["native_empirical_panels_regenerated"] == 0
    assert manifest["printed_figure_numeric_annotations"] == 40
    assert manifest["native_figure_numeric_annotations_regenerated"] == 0
    assert manifest["third_party_candidates_with_native_credit"] == 0
    assert manifest["full_end_to_end_pipeline_reproduced"] is False
    assert manifest["strict_success"] is False
