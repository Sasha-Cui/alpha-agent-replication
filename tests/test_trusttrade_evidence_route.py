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


def test_trusttrade_is_a_targeted_paper_audit_with_component_but_zero_system_credit() -> None:
    ledger = rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in ledger if item["system_id"] == "SYS-TRUST-TRADE")
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_three_paper_linked_interfaces_183_stock_days_one_of_12_"
        "strict_inactive_baseline_cells_zero_of_26_native_panels_no_attributable_trusttrade_pipeline"
    )
    assert row["fidelity_class"] == "F0_no_public_artifact"
    note = row["concise_evidence_note"]
    assert "0/26 empirical figure panels" in note
    assert "31-repository lab organization" in note
    assert "source maps expose all 847" in note
    assert "183 GPT-4o-mini stock-day records" in note
    assert "1/12 cells" in note
    assert "3/12 or 7/12" in note
    assert "None is a TrustTrade result" in note
    assert "68/183 stock-days" in note
    assert "four open-by-default reports" in note
    assert "No participant outputs" in note


def test_trusttrade_paper_route_exposes_the_precise_blocker() -> None:
    routes = rows(ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv")
    row = next(item for item in routes if item["canonical_work_id"] == "CensusArxiv260322567")
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["public_artifact_statuses"] == "not_listed"
    assert row["static_fidelity_tiers"] == ""
    assert row["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert row["native_execution_audit_status"].startswith(
        "paper_audit:completed_three_paper_linked_interfaces_183_stock_days"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["good_faith_reconstruction"] == "no"
    assert row["mapping_count"] == "0"
    assert row["mapping_fidelity_tiers"] == ""
    assert row["mapping_disposition"] == "availability_only_no_performance_inference"
    assert row["proxy_role"] == "no_proxy"
    assert row["negative_inference_boundary"] == "no_performance_inference"
    blocker = row["precise_native_or_access_blocker"]
    assert "SYS-TRUST-TRADE:A0_no_public_artifact" in blocker
    assert "0/26 empirical figure panels" in blocker
    assert "183 GPT-4o-mini stock-day records" in blocker
    assert "1/12 cells" in blocker
    assert "None is a TrustTrade result" in blocker


def test_static_report_and_claim_ledger_count_trusttrade_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\TargetedAuditCount}{63}" in generated
    claims = {row["macro"]: row for row in rows(ROOT / "paper_runs/submission_evidence/claims.csv")}
    assert claims["TargetedAuditCount"]["rendered_value"] == "63"
    assert claims["TargetedAuditCount"]["source_sha256"] == sha256(
        ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
    )
    failures = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "TrustTrade" in failures
    assert "0/26 empirical figure panels" in failures
    assert "183 GPT-4o-mini stock-day records" in failures
    assert failures.count("TrustTrade &") == 1


def test_manifest_preserves_interface_component_and_no_trusttrade_result_boundary() -> None:
    data = json.loads((ROOT / "paper_runs/paper_replication_audits/trusttrade/manifest.json").read_text())
    assert data["active_empirical_result_panels"] == 26
    assert data["author_native_empirical_panels_regenerated"] == 0
    assert data["inactive_source_table_cells"] == 12
    assert data["strict_literal_inactive_cells_matching"] == 1
    assert data["paper_linked_interfaces_recovered"] == 3
    assert data["paper_linked_stock_days_recovered"] == 183
    assert data["attributable_interface_component_recovered"] is True
    assert data["attributable_trusttrade_pipeline_found"] is False
    assert data["strict_success"] is False
