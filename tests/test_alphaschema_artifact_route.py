from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "route_alphaschema_paper_audit",
    ROOT / "scripts/route_alphaschema_paper_audit.py",
)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_pinned_artifact_row_is_direct_reachable_unlicensed_and_r3() -> None:
    row = route.alphaschema_row()
    assert row["artifact_urls"] == route.URL
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R3"
    assert row["native_execution_attempted"] == "Y"
    assert row["default_branch_head_shas"].endswith(route.HEAD_SHA)
    assert row["observed_licenses"].endswith("NOASSERTION")
    result = json.loads(row["artifact_url_results_json"])[0]
    observation = result["static_observation"]
    assert result["observed_license"] == "NOASSERTION"
    assert observation["file_count"] == 32
    assert observation["python_file_count"] == 16
    assert observation["has_runner"] is True
    assert observation["archive_sha256"] == route.ARCHIVE_SHA256
    assert observation["tracked_test_files"] == 1
    assert observation["author_tests_passed"] == 9
    assert observation["native_demo_plans"] == 48
    assert observation["native_demo_uses_mock_evaluator"] is True
    assert observation["paper_result_credit"] is False


def test_committed_artifact_audit_and_summary_include_alphaschema() -> None:
    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row == {key: str(value) for key, value in route.alphaschema_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {row["metric"]: row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "34"
    assert ft["artifact_reachable_among_all"]["successes"] == "33"
    assert ft["github_head_resolved_among_all"]["successes"] == "32"
    assert ft["static_R3_among_all"]["successes"] == "17"
    payload = json.loads((audit_dir / "artifact_audit.json").read_text())
    corrections = payload["metadata"]["post_freeze_evidence_corrections"]
    assert route.SYSTEM_ID in {item["system_id"] for item in corrections}
    assert payload["metadata"]["registry_sha256"] == route.sha256(route.REGISTRY)


def test_native_ledger_routes_components_without_output_or_result_credit() -> None:
    rows = csv_rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R3"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A2_no_shipped_native_dated_output"
    assert row["fidelity_class"] == "F1_static_no_native_output"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_zero_of_212_numeric_units_zero_of_9_empirical_"
        "panels_direct_author_release_nine_tests_appendix_component_missing_research_lineage"
    )
    note = row["concise_evidence_note"]
    for marker in (
        "212", "9 empirical panels", "9 author tests", "48 plans",
        "mock evaluator", "Appendix factor", "0/212", "0/9",
    ):
        assert marker in note


def test_paper_evidence_route_moves_alphaschema_to_public_code_with_blocker() -> None:
    rows = csv_rows(
        ROOT
        / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    row = next(
        item for item in rows if item["canonical_work_id"] == "CensusArxiv260726642"
    )
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == route.SYSTEM_ID
    assert row["static_fidelity_tiers"] == "R3"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["proxy_role"] == "no_proxy"
    assert "A2_no_shipped_native_dated_output" in row["precise_native_or_access_blocker"]


def test_static_paper_assets_reflect_alphaschema_correction() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text()
    assert r"\newcommand{\ArtifactCountFT}{34}" in generated
    assert r"\newcommand{\ReachableArtifactCountFT}{33}" in generated
    assert r"\newcommand{\LicensedArtifactCountFT}{20}" in generated
    assert r"\newcommand{\PinnedRepoCountFT}{32}" in generated
    assert (
        r"\newcommand{\ArtifactTierSummaryFT}{\artifacttier{R0}: 34, "
        r"\artifacttier{R1}: 10, \artifacttier{R2}: 6, \artifacttier{R3}: 17}"
    ) in generated
    assert r"\newcommand{\TargetedAuditCount}{57}" in generated
    routes = (ROOT / "docs/paper/generated_evidence_routes.tex").read_text()
    assert r"\newcommand{\PublicCodeRouteWorkCount}{33\xspace}" in routes
    assert r"\newcommand{\PaperOnlyUnderspecifiedWorkCount}{36\xspace}" in routes
    failure_table = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text()
    assert "AlphaSchema & reachable" in failure_table
    assert "0/212" in failure_table
    assert "0/9" in failure_table


def test_census_routes_direct_release_and_records_no_license() -> None:
    census = csv_rows(ROOT / "literature_review/census_v1/system_registry.csv", "|")
    row = next(item for item in census if item["system_id"] == route.SYSTEM_ID)
    assert row["official_artifact"] == route.URL
    assert "directly links" in row["lineage_dedup_notes"]
    assert "no license" in row["lineage_dedup_notes"]
