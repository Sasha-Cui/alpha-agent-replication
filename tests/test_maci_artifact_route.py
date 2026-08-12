"""Contracts for routing the pinned MACI author artifact."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/route_maci_paper_audit.py"
SPEC = importlib.util.spec_from_file_location("route_maci_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_pinned_author_row_is_reachable_mit_and_honestly_r2() -> None:
    row = route.maci_row()
    assert row["artifact_urls"] == route.URL
    assert row["default_branch_head_shas"].endswith(route.HEAD)
    assert row["observed_licenses"] == "lyc0603/multi-agent=MIT"
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R2"
    result = json.loads(row["artifact_url_results_json"])[0]
    observation = result["static_observation"]
    assert observation["archive_bytes"] == 316_791_931
    assert observation["file_count"] == 6547
    assert observation["has_runner"] is True
    assert observation["has_support"] is False


def test_committed_audit_preserves_prior_corrections_and_adds_only_maci() -> None:
    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row == {key: str(value) for key, value in route.maci_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {row["metric"]: row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "27"
    assert ft["artifact_reachable_among_all"]["successes"] == "26"
    assert ft["github_head_resolved_among_all"]["successes"] == "26"
    assert ft["static_R2_or_R3_among_all"]["successes"] == "18"
    assert ft["static_R3_among_all"]["successes"] == "12"
    payload = json.loads((audit_dir / "artifact_audit.json").read_text(encoding="utf-8"))
    assert {item["system_id"] for item in payload["metadata"]["post_freeze_evidence_corrections"]} == {
        "SYS-EMPIRICAL-ASSET-PRICING-LLM",
        "SYS-FIN-AGENT",
        "SYS-GPT-SIGNAL",
        "SYS-HEDGE-AGENTS",
        "SYS-MACI",
        "SYS-MOUNTAIN-LION",
        "SYS-P1GPT",
        "SYS-RAPTOR",
    }
    assert payload["metadata"]["registry_sha256"] == route.sha256(route.REGISTRY)


def test_native_and_paper_routes_keep_output_verification_below_reproduction() -> None:
    native = csv_rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in native if item["system_id"] == route.SYSTEM_ID)
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R2"
    assert row["native_dated_signal_or_return_shipped"] == "Y"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A3_wrong_asset_class_crypto"
    assert row["fidelity_class"] == "F2_dated_output_task_incompatible"
    assert "0/321 v1/v2 table units" in row["concise_evidence_note"]
    assert "0/442 v3 table units" in row["concise_evidence_note"]

    routes = csv_rows(
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    paper = next(item for item in routes if item["canonical_work_id"] == "CensusArxiv250100826")
    assert paper["paper_evidence_route"] == "public_code_available"
    assert paper["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert paper["full_prompt_search_training_pipeline_reproduced"] == "no"


def test_static_assets_reflect_maci_once() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\ArtifactCountFT}{27}" in generated
    assert r"\newcommand{\ReachableArtifactCountFT}{26}" in generated
    assert r"\newcommand{\LicensedArtifactCountFT}{15}" in generated
    assert r"\newcommand{\PinnedRepoCountFT}{26}" in generated
    assert r"\newcommand{\ArtifactTierSummaryFT}{\artifacttier{R0}: 41, \artifacttier{R1}: 8, \artifacttier{R2}: 6, \artifacttier{R3}: 12}" in generated
    assert r"\newcommand{\NativeDatedOutputCount}{6}" in generated
    assert r"\newcommand{\TargetedAuditCount}{38}" in generated
