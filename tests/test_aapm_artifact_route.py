from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/route_aapm_paper_audit.py"
SPEC = importlib.util.spec_from_file_location("route_aapm_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_pinned_correction_row_is_paper_linked_reachable_and_r3() -> None:
    row = route.aapm_row()
    assert row["artifact_urls"] == route.URL
    assert row["default_branch_head_shas"].endswith(route.HEAD)
    assert row["observed_licenses"] == "chengjunyan1/AAPM=MIT"
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R3"
    result = json.loads(row["artifact_url_results_json"])[0]
    assert result["static_observation"]["file_count"] == 10
    assert result["static_observation"]["has_runner"] is True
    assert result["static_observation"]["archive_sha256"] == route.ARCHIVE_SHA256


def test_committed_artifact_audit_and_summary_include_aapm() -> None:
    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row == {key: str(value) for key, value in route.aapm_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {row["metric"]: row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "36"
    assert ft["artifact_reachable_among_all"]["successes"] == "35"
    assert ft["github_head_resolved_among_all"]["successes"] == "34"
    assert ft["static_R3_among_all"]["successes"] == "18"
    payload = json.loads((audit_dir / "artifact_audit.json").read_text(encoding="utf-8"))
    corrections = payload["metadata"]["post_freeze_evidence_corrections"]
    assert {item["system_id"] for item in corrections} == {
        "SYS-JANUS-Q",
        "SYS-ALPHA-SCHEMA",
        "SYS-ALPHA-CRAFTER",
        "SYS-COG-ALPHA",
        "SYS-EMPIRICAL-ASSET-PRICING-LLM", "SYS-FIN-AGENT", "SYS-GPT-SIGNAL",
        "SYS-HEDGE-AGENTS", "SYS-MACI", "SYS-MOUNTAIN-LION", "SYS-FIN-ANALYST", "SYS-P1GPT",
        "SYS-RAPTOR",
        "SYS-MM-DREX",
            "SYS-MAD-EVOLVE",
        "SYS-QUANT-AGENTS", "SYS-ATLAS",
    }
    assert payload["metadata"]["registry_sha256"] == route.sha256(route.REGISTRY)


def test_native_ledger_keeps_static_components_at_zero_result_credit() -> None:
    rows = csv_rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R3"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A2_no_shipped_native_dated_output"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_zero_of_162_v2_table_results_missing_hybrid_pipeline_"
        "and_v2_lineage"
    )
    assert row["fidelity_class"] == "F1_static_no_native_output"
    note = row["concise_evidence_note"]
    assert "zero native paper results reproduced" in note
    assert "never ingests the paper's central manual-factor input" in note
    assert "112/114 common table cells change while 15/16 rasters are reused" in note


def test_paper_route_and_static_assets_reflect_aapm_without_overclaiming() -> None:
    rows = csv_rows(
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    row = next(item for item in rows if item["canonical_work_id"] == "CensusArxiv240917266")
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == route.SYSTEM_ID
    assert row["static_fidelity_tiers"] == "R3"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_disposition"] == "availability_only_no_performance_inference"
    assert row["proxy_role"] == "no_proxy"
    assert "zero native paper results reproduced" in row["precise_native_or_access_blocker"]

    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\ArtifactCountFT}{36}" in generated
    assert r"\newcommand{\ReachableArtifactCountFT}{35}" in generated
    assert r"\newcommand{\LicensedArtifactCountFT}{20}" in generated
    assert r"\newcommand{\PinnedRepoCountFT}{34}" in generated
    assert r"\newcommand{\ArtifactTierSummaryFT}{\artifacttier{R0}: 32, \artifacttier{R1}: 11, \artifacttier{R2}: 6, \artifacttier{R3}: 18}" in generated
    assert r"\newcommand{\NativeDatedOutputCount}{11}" in generated
    assert r"\newcommand{\TargetedAuditCount}{67}" in generated
    system_table = (ROOT / "docs/paper/tables/system_registry.tex").read_text(encoding="utf-8")
    failure_table = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "chengjunyan1/AAPM" in system_table
    assert "Empirical Asset Pricing with Large Language Model Agents & reachable" in failure_table
    assert "zero native paper results reproduced" in failure_table
