from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/route_cogalpha_paper_audit.py"
SPEC = importlib.util.spec_from_file_location("route_cogalpha_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_correction_row_is_reachable_r1_prompt_specification_not_runtime() -> None:
    row = route.cogalpha_row()
    assert row["artifact_urls"] == route.URL
    assert row["default_branch_head_shas"].endswith(route.HEAD)
    assert row["observed_licenses"] == "uwFengyuan/CogAlpha_Prompt=NOASSERTION"
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R1"
    result = json.loads(row["artifact_url_results_json"])[0]
    observation = result["static_observation"]
    assert observation["archive_sha256"] == route.ARCHIVE_SHA256
    assert observation["file_count"] == 47
    assert observation["prompt_template_count"] == 39
    assert observation["has_code"] is False
    assert observation["has_environment"] is False
    assert observation["has_runner"] is False
    assert observation["explicit_nonrunnable"] is True
    assert "experiment outputs" in observation["excluded_runtime_materials"]


def test_registry_artifact_audit_and_post_freeze_correction_agree() -> None:
    registry = csv_rows(ROOT / "literature_review/census_v1/system_registry.csv", "|")
    registry_row = next(row for row in registry if row["system_id"] == route.SYSTEM_ID)
    assert registry_row["official_artifact"] == route.URL
    assert "prompt-only repository" in registry_row["lineage_dedup_notes"]

    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row == {key: str(value) for key, value in route.cogalpha_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {row["metric"]: row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "35"
    assert ft["artifact_reachable_among_all"]["successes"] == "34"
    assert ft["github_head_resolved_among_all"]["successes"] == "33"
    assert sum(
        item["main_FT"] == "Y" and item["static_fidelity_tier"] == "R1"
        for item in rows
    ) == 11

    payload = json.loads((audit_dir / "artifact_audit.json").read_text())
    corrections = payload["metadata"]["post_freeze_evidence_corrections"]
    assert {item["system_id"] for item in corrections} == {
        "SYS-JANUS-Q",
        "SYS-ALPHA-SCHEMA",
        "SYS-ALPHA-CRAFTER",
        "SYS-COG-ALPHA",
        "SYS-EMPIRICAL-ASSET-PRICING-LLM",
        "SYS-FIN-AGENT",
        "SYS-GPT-SIGNAL",
        "SYS-HEDGE-AGENTS",
        "SYS-MACI",
        "SYS-MOUNTAIN-LION",
        "SYS-P1GPT",
        "SYS-QUANT-AGENTS", "SYS-ATLAS",
        "SYS-RAPTOR",
        "SYS-MM-DREX",
            "SYS-MAD-EVOLVE",
    }
    correction = next(item for item in corrections if item["system_id"] == route.SYSTEM_ID)
    assert correction["source_head"] == route.HEAD
    assert "not CogAlpha runtime code" in correction["reason"]
    assert payload["metadata"]["registry_sha256"] == route.sha256(route.REGISTRY)


def test_native_ledger_records_specification_credit_and_zero_results() -> None:
    rows = csv_rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R1"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A2_no_shipped_native_dated_output"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_v1_zero_of_150_current_zero_of_306_39_prompt_"
        "templates_four_author_curve_series_zero_regenerated"
    )
    assert row["fidelity_class"] == "F1_static_no_native_output"
    note = row["concise_evidence_note"]
    assert "0/306 current empirical units reproduce" in note
    assert "39 prompt templates" in note
    assert "author-output correspondence but no raw dated array" in note
    assert "R1 prompt specification" in note
    assert "local M0 narrative translation remains secondary" in note


def test_paper_route_prioritizes_prompt_artifact_without_calling_it_code() -> None:
    rows = csv_rows(
        ROOT
        / "paper_runs/submission_evidence/replication_scope/"
        "paper_evidence_route_ledger.csv"
    )
    row = next(
        item for item in rows if item["canonical_work_id"] == "CensusArxiv251118850"
    )
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == route.SYSTEM_ID
    assert row["public_artifact_statuses"] == "reachable_static_snapshot"
    assert row["static_fidelity_tiers"] == "R1"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["good_faith_reconstruction"] == "yes"
    assert row["mapping_fidelity_tiers"] == "M0_narrative_translation"
    assert row["mapping_disposition"] == "clearly_labeled_motif_proxy"
    assert row["proxy_role"] == "secondary_diagnostic_after_native_review"
    blocker = row["precise_native_or_access_blocker"]
    assert "not model calls, alpha mining, backtesting" in blocker
    assert "0/306 current empirical units reproduce" in blocker


def test_static_report_counts_and_tables_include_cogalpha_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text()
    assert r"\newcommand{\ArtifactCountFT}{35}" in generated
    assert r"\newcommand{\ArtifactRateFT}{52.2\%}" in generated
    assert r"\newcommand{\ReachableArtifactCountFT}{34}" in generated
    assert r"\newcommand{\LicensedArtifactCountFT}{20}" in generated
    assert r"\newcommand{\PinnedRepoCountFT}{33}" in generated
    assert (
        r"\newcommand{\ArtifactTierSummaryFT}{\artifacttier{R0}: 33, "
        r"\artifacttier{R1}: 11, \artifacttier{R2}: 6, \artifacttier{R3}: 17}"
        in generated
    )
    assert r"\newcommand{\TargetedAuditCount}{62}" in generated
    claims = {
        row["macro"]: row
        for row in csv_rows(ROOT / "paper_runs/submission_evidence/claims.csv")
    }
    assert claims["ArtifactCountFT"]["rendered_value"] == "35"
    assert claims["TargetedAuditCount"]["rendered_value"] == "62"
    system_table = (ROOT / "docs/paper/tables/system_registry.tex").read_text()
    failure_table = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text()
    assert r"uwFengyuan/CogAlpha\_Prompt" in system_table
    assert "CogAlpha & reachable" in failure_table
    assert "R1 prompt specification" in failure_table
    assert "0/306 current empirical units reproduce" in failure_table


def test_standalone_manifest_preserves_zero_native_credit_boundary() -> None:
    manifest = json.loads(
        (
            ROOT / "paper_runs/paper_replication_audits/cogalpha/manifest.json"
        ).read_text()
    )
    assert manifest["editions"]["arxiv_v1"]["total_unique_empirical_units"] == 150
    assert (
        manifest["editions"]["arxiv_v4_acl_final"]["total_unique_empirical_units"]
        == 306
    )
    assert manifest["author_prompt_template_count"] == 39
    assert manifest["native_empirical_units_regenerated"] == 0
    assert manifest["full_end_to_end_pipeline_reproduced"] is False
