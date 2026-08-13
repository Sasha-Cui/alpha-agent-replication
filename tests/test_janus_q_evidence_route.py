from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/route_janus_q_paper_audit.py"
SPEC = importlib.util.spec_from_file_location("route_janus_q_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_correction_row_is_reachable_r1_static_output_and_data_not_code() -> None:
    row = route.janus_q_row()
    assert row["artifact_urls"] == f"{route.PROJECT_URL} ; {route.REPOSITORY_URL}"
    assert row["artifact_url_count"] == 2
    assert row["default_branch_head_shas"] == (
        f"{route.OWNER_REPO}@{route.DEFAULT_BRANCH}={route.DEFAULT_HEAD}"
    )
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R1"
    assert row["failure_category"] == "static_package_insufficient"
    results = json.loads(row["artifact_url_results_json"])
    assert len(results) == 2
    repository = next(item for item in results if item["url_type"] == "github_repository")
    assert repository["github_owner_repo"] == route.OWNER_REPO
    assert repository["default_branch"] == route.DEFAULT_BRANCH
    assert repository["head_sha"] == route.DEFAULT_HEAD
    assert repository["static_observation"]["file_count"] == 20
    assert repository["static_observation"]["archive_sha256"] == route.ARCHIVE_SHA256
    assert repository["static_observation"]["historical_branch"] == route.RELEASE_BRANCH
    assert repository["static_observation"]["historical_release_head"] == route.RELEASE_HEAD
    assert repository["static_observation"]["has_code"] is False
    assert repository["static_observation"]["has_environment"] is False
    assert repository["static_observation"]["has_runner"] is False
    project = next(item for item in results if item["url_type"] == "project_page")
    assert any("277,304,208 bytes" in marker for marker in project["static_observation"]["support_markers"])
    assert "currently expired" in project["static_observation"]["support_markers"][-1]


def test_registry_and_committed_artifact_audit_share_author_routes() -> None:
    registry = csv_rows(ROOT / "literature_review/census_v1/system_registry.csv", "|")
    registry_row = next(row for row in registry if row["system_id"] == route.SYSTEM_ID)
    assert registry_row["official_artifact"] == f"{route.PROJECT_URL} ; {route.REPOSITORY_URL}"
    assert "static output site and Drive dataset" in registry_row["lineage_dedup_notes"]
    assert "code archive is expired" in registry_row["lineage_dedup_notes"]

    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row == {key: str(value) for key, value in route.janus_q_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {row["metric"]: row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "35"
    assert ft["artifact_reachable_among_all"]["successes"] == "34"
    assert ft["github_head_resolved_among_all"]["successes"] == "33"
    assert sum(
        item["main_FT"] == "Y" and item["static_fidelity_tier"] == "R1"
        for item in rows
    ) == 11

    payload = json.loads((audit_dir / "artifact_audit.json").read_text(encoding="utf-8"))
    corrections = payload["metadata"]["post_freeze_evidence_corrections"]
    janus = next(item for item in corrections if item["system_id"] == route.SYSTEM_ID)
    assert janus["source_head"] == route.RELEASE_HEAD
    assert "R1 evidence, not system code" in janus["reason"]
    assert payload["metadata"]["registry_sha256"] == route.sha256(route.REGISTRY)


def test_native_ledger_records_dated_china_nav_and_precise_blocker() -> None:
    rows = csv_rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R1"
    assert row["native_dated_signal_or_return_shipped"] == "Y"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A3_CN_only_portfolio_NAV_no_six_country_security_mapping"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:partial_61_of_130_table_cells_85_of_85_released_nav_metrics_"
        "31999_of_31999_data_links_static_outputs_no_native_training_or_backtest"
    )
    assert row["fidelity_class"] == "F2_dated_output_task_incompatible"
    note = row["concise_evidence_note"]
    for marker in (
        "61/130 printed table cells",
        "one CSI-1000 Sharpe cell is directly contradicted",
        "85/85 total-return",
        "0/130 table cells and 0/10 empirical panels",
        "China-only portfolio NAV paths",
    ):
        assert marker in note


def test_paper_route_uses_public_artifact_precedence_without_overclaiming() -> None:
    rows = csv_rows(
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    row = next(item for item in rows if item["canonical_work_id"] == "CensusArxiv260219919")
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == route.SYSTEM_ID
    assert row["public_artifact_statuses"] == "reachable_static_snapshot"
    assert row["static_fidelity_tiers"] == "R1"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["native_execution_audit_status"].startswith("paper_audit:partial_61_of_130")
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["good_faith_reconstruction"] == "yes"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["mapping_disposition"] == "clearly_labeled_motif_proxy"
    assert row["proxy_role"] == "secondary_diagnostic_after_native_review"
    assert "0/130 table cells and 0/10 empirical panels" in row["precise_native_or_access_blocker"]


def test_static_report_counts_and_tables_include_janus_q_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\ArtifactCountFT}{35}" in generated
    assert r"\newcommand{\ReachableArtifactCountFT}{34}" in generated
    assert r"\newcommand{\LicensedArtifactCountFT}{20}" in generated
    assert r"\newcommand{\PinnedRepoCountFT}{33}" in generated
    assert (
        r"\newcommand{\ArtifactTierSummaryFT}{\artifacttier{R0}: 33, "
        r"\artifacttier{R1}: 11, \artifacttier{R2}: 6, \artifacttier{R3}: 17}"
        in generated
    )
    assert r"\newcommand{\NativeDatedOutputCount}{7}" in generated
    assert r"\newcommand{\TargetedAuditCount}{62}" in generated
    claims = {
        row["macro"]: row
        for row in csv_rows(ROOT / "paper_runs/submission_evidence/claims.csv")
    }
    assert claims["ArtifactCountFT"]["rendered_value"] == "35"
    assert claims["NativeDatedOutputCount"]["rendered_value"] == "7"
    assert claims["TargetedAuditCount"]["rendered_value"] == "62"
    system_table = (ROOT / "docs/paper/tables/system_registry.tex").read_text(encoding="utf-8")
    failure_table = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert system_table.count("SYS-\\allowbreak{}JANUS-\\allowbreak{}Q") == 1
    assert "static output site and Drive dataset" in system_table
    assert "Janus-Q & reachable" in failure_table
    assert "61/130 printed table cells" in failure_table


def test_routed_summary_and_standalone_manifest_share_zero_native_credit() -> None:
    manifest = json.loads(
        (ROOT / "paper_runs/paper_replication_audits/janus_q/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["published_numeric_table_cells"] == 130
    assert manifest["author_linked_table_cells_exactly_verified"] == 61
    assert manifest["author_linked_table_cells_contradicted"] == 1
    assert manifest["author_native_table_cells_regenerated"] == 0
    assert manifest["full_end_to_end_pipeline_reproduced"] is False
