from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/route_quantagents_paper_audit.py"
SPEC = importlib.util.spec_from_file_location("route_quantagents_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_correction_is_reachable_r1_documentation_not_code() -> None:
    row = route.quantagents_row()
    assert row["artifact_urls"] == route.URL
    assert row["default_branch_head_shas"].endswith(route.HEAD_SHA)
    assert row["observed_licenses"] == "QuantAgents/quantagents.github.io=MIT"
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R1"
    assert row["native_execution_attempted"] == "N"
    result = json.loads(row["artifact_url_results_json"])[0]
    observation = result["static_observation"]
    assert observation["file_count"] == 41
    assert observation["archive_sha256"] == route.ARCHIVE_SHA256
    assert observation["has_code"] is False
    assert observation["has_environment"] is False
    assert observation["has_runner"] is False
    assert observation["meeting_videos"] == 3
    assert observation["excluded_template_residue"]["records"] == 6141


def test_registry_artifact_audit_and_summary_share_the_author_route() -> None:
    registry = csv_rows(ROOT / "literature_review/census_v1/system_registry.csv", "|")
    registry_row = next(row for row in registry if row["system_id"] == route.SYSTEM_ID)
    assert registry_row["official_artifact"] == route.URL
    assert "R1 static documentation site" in registry_row["lineage_dedup_notes"]

    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row == {key: str(value) for key, value in route.quantagents_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {row["metric"]: row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "34"
    assert ft["artifact_reachable_among_all"]["successes"] == "33"
    assert ft["github_head_resolved_among_all"]["successes"] == "32"
    assert sum(
        item["main_FT"] == "Y" and item["static_fidelity_tier"] == "R1"
        for item in rows
    ) == 10
    payload = json.loads((audit_dir / "artifact_audit.json").read_text(encoding="utf-8"))
    correction = next(
        item
        for item in payload["metadata"]["post_freeze_evidence_corrections"]
        if item["system_id"] == route.SYSTEM_ID
    )
    assert correction["source_archive_sha256"] == route.ARCHIVE_SHA256
    assert payload["metadata"]["registry_sha256"] == route.sha256(route.REGISTRY)


def test_native_ledger_records_zero_result_credit_and_precise_blocker() -> None:
    rows = csv_rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R1"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["blocking_stage"] == "A2_no_shipped_native_dated_output"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_zero_of_238_numeric_cells_zero_of_14_empirical_panels_"
        "r1_static_site_no_system_source"
    )
    assert row["fidelity_class"] == "F1_static_no_native_output"
    note = row["concise_evidence_note"]
    assert "0/238 cells and 0/14 empirical panels reproduce" in note
    assert "R1 static site, not a trading implementation" in note
    assert "6,141-record MathVista/VQA template" in note
    assert "material contamination risk, not proof" in note


def test_paper_route_uses_public_artifact_precedence_without_overclaiming() -> None:
    rows = csv_rows(
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    row = next(item for item in rows if item["canonical_work_id"] == "CensusArxiv251004643")
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == route.SYSTEM_ID
    assert row["public_artifact_statuses"] == "reachable_static_snapshot"
    assert row["static_fidelity_tiers"] == "R1"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["good_faith_reconstruction"] == "yes"
    assert row["proxy_role"] == "secondary_diagnostic_after_native_review"
    assert "0/238 cells and 0/14 empirical panels reproduce" in row[
        "precise_native_or_access_blocker"
    ]


def test_static_report_counts_and_tables_include_quantagents_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\ArtifactCountFT}{34}" in generated
    assert r"\newcommand{\ReachableArtifactCountFT}{33}" in generated
    assert r"\newcommand{\LicensedArtifactCountFT}{20}" in generated
    assert r"\newcommand{\PinnedRepoCountFT}{32}" in generated
    assert (
        r"\newcommand{\ArtifactTierSummaryFT}{\artifacttier{R0}: 34, "
        r"\artifacttier{R1}: 10, \artifacttier{R2}: 6, \artifacttier{R3}: 17}"
        in generated
    )
    assert r"\newcommand{\TargetedAuditCount}{57}" in generated
    routes = (ROOT / "docs/paper/generated_evidence_routes.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\PublicCodeRouteWorkCount}{33\xspace}" in routes
    assert r"\newcommand{\PaperOnlyUnderspecifiedWorkCount}{36\xspace}" in routes
    system_table = (ROOT / "docs/paper/tables/system_registry.tex").read_text(encoding="utf-8")
    failure_table = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "QuantAgents/quantagents.github.io" in system_table
    assert "QuantAgents & reachable" in failure_table
    assert "0/238 cells and 0/14 empirical panels reproduce" in failure_table


def test_standalone_manifest_preserves_zero_credit_boundary() -> None:
    manifest = json.loads(route.MANIFEST.read_text(encoding="utf-8"))
    assert manifest["published_numeric_table_cells"] == 238
    assert manifest["quantagents_own_numeric_table_cells"] == 132
    assert manifest["published_numeric_table_cells_faithfully_regenerated"] == 0
    assert manifest["published_empirical_panels"] == 14
    assert manifest["published_empirical_panels_faithfully_regenerated"] == 0
    assert manifest["full_end_to_end_pipeline_reproduced"] is False
