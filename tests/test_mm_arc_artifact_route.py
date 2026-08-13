from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "route_mm_arc_paper_audit", ROOT / "scripts/route_mm_arc_paper_audit.py"
)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_pinned_artifact_row_is_paper_linked_reachable_and_r3() -> None:
    row = route.mm_arc_row()
    assert row["artifact_urls"] == route.URL
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R3"
    assert row["native_execution_attempted"] == "Y"
    assert row["default_branch_head_shas"] == ""
    result = json.loads(row["artifact_url_results_json"])[0]
    observation = result["static_observation"]
    assert observation["file_count"] == 107
    assert observation["has_runner"] is True
    assert observation["archive_sha256"] == route.ARCHIVE_SHA256
    assert observation["git_lfs_pointer_files"] == 9
    assert observation["registered_payload_bytes_unavailable"] == 340_563_208


def test_committed_artifact_audit_and_summary_include_mm_arc() -> None:
    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row == {key: str(value) for key, value in route.mm_arc_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {row["metric"]: row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "35"
    assert ft["artifact_reachable_among_all"]["successes"] == "34"
    assert ft["github_head_resolved_among_all"]["successes"] == "33"
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
        "paper_audit:completed_v1_v2_zero_of_671_v3_zero_of_651_substantial_"
        "v3_release_111_tests_missing_lfs_and_research_lineage"
    )
    note = row["concise_evidence_note"]
    for marker in (
        "671 legacy", "651 current", "111 tests", "9 Git LFS pointers",
        "0/671 legacy", "0/651 current", "0/18 empirical figure series",
    ):
        assert marker in note


def test_paper_evidence_route_moves_mm_arc_to_public_code_with_blocker() -> None:
    rows = csv_rows(
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    row = next(item for item in rows if item["canonical_work_id"] == "CensusArxiv250905080")
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == route.SYSTEM_ID
    assert row["static_fidelity_tiers"] == "R3"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["proxy_role"] == "secondary_diagnostic_after_native_review"
    assert "A2_no_shipped_native_dated_output" in row["precise_native_or_access_blocker"]


def test_static_paper_assets_reflect_mm_arc_correction() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text()
    assert r"\newcommand{\ArtifactCountFT}{35}" in generated
    assert r"\newcommand{\ReachableArtifactCountFT}{34}" in generated
    assert r"\newcommand{\LicensedArtifactCountFT}{20}" in generated
    assert r"\newcommand{\PinnedRepoCountFT}{33}" in generated
    assert (
        r"\newcommand{\ArtifactTierSummaryFT}{\artifacttier{R0}: 33, "
        r"\artifacttier{R1}: 11, \artifacttier{R2}: 6, \artifacttier{R3}: 17}"
    ) in generated
    assert r"\newcommand{\TargetedAuditCount}{64}" in generated
    routes = (ROOT / "docs/paper/generated_evidence_routes.tex").read_text()
    assert r"\newcommand{\PublicCodeRouteWorkCount}{34\xspace}" in routes
    assert r"\newcommand{\PaperOnlyUnderspecifiedWorkCount}{35\xspace}" in routes
    failure_table = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text()
    assert "MM-DREX & reachable" in failure_table
    assert "0/671 legacy" in failure_table
    assert "0/651 current" in failure_table


def test_registries_preserve_legacy_identity_and_current_release() -> None:
    census = csv_rows(ROOT / "literature_review/census_v1/system_registry.csv", "|")
    row = next(item for item in census if item["system_id"] == route.SYSTEM_ID)
    assert row["system_name"] == "MM-DREX"
    assert row["official_artifact"] == route.URL
    assert "wholesale MM-ARC replacement" in row["lineage_dedup_notes"]
    registry = csv_rows(ROOT / "paper_runs/registry.csv")
    paper = next(item for item in registry if item["ref_index"] == "32")
    assert paper["code_status"] == "official_v3_anonymous_release"
    assert paper["code_url"] == route.URL
    assert paper["execution_state"] == "audited_component_execution_only"
    assert paper["verdict"] == (
        "zero_of_671_legacy_and_zero_of_651_current_numeric_result_units_regenerated"
    )
