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


def test_blindtrade_is_a_targeted_paper_only_audit_with_zero_native_credit() -> None:
    ledger = rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in ledger if item["system_id"] == "SYS-BLIND-TRADE")
    assert row["public_artifact_status"] == "not_listed"
    assert row["static_tier"] == "R0"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A0_no_public_artifact"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_six_of_98_current_passive_benchmark_cells_zero_author_native_"
        "zero_of_9_empirical_panels_four_prompts_zero_valid_json_no_attributable_pipeline"
    )
    assert row["fidelity_class"] == "F0_no_public_artifact"
    note = row["concise_evidence_note"]
    assert "0/98 author-native table cells" in note
    assert "0/9 panels" in note
    assert "6/98 passive benchmark cells" in note
    assert "none of the four" in note
    assert "cross_sectional_score" in note
    assert "selected on the reported holdout" in note
    assert "S&P 100" in note
    assert "M0 proxy remains narrative only" in note


def test_blindtrade_paper_route_exposes_the_precise_blocker() -> None:
    routes = rows(ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv")
    row = next(item for item in routes if item["canonical_work_id"] == "CensusArxiv260317692")
    assert row["paper_evidence_route"] == "paper_only_underspecified"
    assert row["public_artifact_statuses"] == "not_listed"
    assert row["static_fidelity_tiers"] == ""
    assert row["native_pipeline_disposition"] == "paper_only_audit_recorded_no_native_code_pipeline"
    assert row["native_execution_audit_status"].startswith(
        "paper_audit:completed_six_of_98_current_passive_benchmark_cells"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["good_faith_reconstruction"] == "no"
    assert row["mapping_count"] == "0"
    assert row["mapping_fidelity_tiers"] == ""
    assert row["mapping_disposition"] == "availability_only_no_performance_inference"
    assert row["proxy_role"] == "no_proxy"
    assert row["negative_inference_boundary"] == "no_performance_inference"
    blocker = row["precise_native_or_access_blocker"]
    assert "SYS-BLIND-TRADE:A0_no_public_artifact" in blocker
    assert "0/98 author-native table cells" in blocker
    assert "6/98 passive benchmark cells" in blocker
    assert "0/9 panels" in blocker


def test_static_report_and_claim_ledger_count_blindtrade_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\TargetedAuditCount}{67}" in generated
    claims = {row["macro"]: row for row in rows(ROOT / "paper_runs/submission_evidence/claims.csv")}
    assert claims["TargetedAuditCount"]["rendered_value"] == "67"
    assert claims["TargetedAuditCount"]["source_sha256"] == sha256(
        ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
    )
    failures = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "BlindTrade" in failures
    assert "0/98 author-native table cells" in failures
    assert "6/98 passive benchmark cells" in failures
    assert failures.count("BlindTrade &") == 1


def test_manifest_preserves_component_and_no_native_result_boundary() -> None:
    data = json.loads((ROOT / "paper_runs/paper_replication_audits/blindtrade/manifest.json").read_text())
    assert data["published_numeric_table_cells"] == 98
    assert data["author_native_table_cells_regenerated"] == 0
    assert data["current_public_passive_benchmark_cells_replayed"] == 28
    assert data["current_public_passive_benchmark_cells_matching"] == 6
    assert data["empirical_figure_panels"] == 9
    assert data["author_native_empirical_panels_regenerated"] == 0
    assert data["full_system_prompts_recovered"] == 4
    assert data["printed_prompt_schemas_valid_json"] == 0
    assert data["attributable_code_or_data_release_found"] is False
    assert data["strict_success"] is False
