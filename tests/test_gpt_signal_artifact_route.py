from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/route_gpt_signal_paper_audit.py"
SPEC = importlib.util.spec_from_file_location("route_gpt_signal_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_pinned_correction_row_is_recovered_author_source_at_r1() -> None:
    row = route.gpt_signal_row()
    assert row["artifact_urls"] == route.URL
    assert row["default_branch_head_shas"].endswith(route.HEAD)
    assert row["observed_licenses"].endswith("=NOASSERTION")
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R1"
    assert row["failure_category"] == "static_package_insufficient"
    result = json.loads(row["artifact_url_results_json"])[0]
    observation = result["static_observation"]
    assert observation["file_count"] == 13_884
    assert observation["has_code"] is True
    assert observation["has_environment"] is False
    assert observation["has_runner"] is False
    assert observation["archive_sha256"] == route.ARCHIVE_SHA256


def test_committed_artifact_audit_and_summary_include_gpt_signal() -> None:
    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row == {key: str(value) for key, value in route.gpt_signal_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {row["metric"]: row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "36"
    assert ft["artifact_reachable_among_all"]["successes"] == "35"
    assert ft["github_head_resolved_among_all"]["successes"] == "34"
    assert ft["static_R2_or_R3_among_all"]["successes"] == "24"
    payload = json.loads((audit_dir / "artifact_audit.json").read_text(encoding="utf-8"))
    corrections = payload["metadata"]["post_freeze_evidence_corrections"]
    assert {item["system_id"] for item in corrections} == {
        "SYS-JANUS-Q",
        "SYS-FIN-AGENT",
        "SYS-ALPHA-SCHEMA",
        "SYS-ALPHA-CRAFTER",
        "SYS-COG-ALPHA",
        "SYS-EMPIRICAL-ASSET-PRICING-LLM",
        "SYS-GPT-SIGNAL",
        "SYS-HEDGE-AGENTS",
        "SYS-MACI",
        "SYS-MOUNTAIN-LION",
        "SYS-FIN-ANALYST",
        "SYS-P1GPT",
        "SYS-QUANT-AGENTS", "SYS-ATLAS",
        "SYS-RAPTOR",
        "SYS-MM-DREX",
            "SYS-MAD-EVOLVE",
    }
    assert payload["metadata"]["registry_sha256"] == route.sha256(route.REGISTRY)


def test_native_ledger_credits_dated_outputs_but_not_full_reproduction() -> None:
    rows = csv_rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R1"
    assert row["native_dated_signal_or_return_shipped"] == "Y"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A3_US_only_not_six_country"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:partial_1549_of_1554_published_units_author_thesis_source_recovery"
    )
    assert row["fidelity_class"] == "F2_dated_output_task_incompatible"
    note = row["concise_evidence_note"]
    assert "1,549/1,554" in note
    assert "not an end-to-end GPT regeneration" in note
    assert "one-month panels use future-quarter fundamentals" in note
    assert "six-country" in note


def test_paper_route_and_static_assets_reflect_gpt_signal_correction() -> None:
    routes = csv_rows(
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    row = next(item for item in routes if item["canonical_work_id"] == "CensusArxiv241018448")
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == route.SYSTEM_ID
    assert row["static_fidelity_tiers"] == "R1"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\ArtifactCountFT}{36}" in generated
    assert r"\newcommand{\ReachableArtifactCountFT}{35}" in generated
    assert r"\newcommand{\LicensedArtifactCountFT}{20}" in generated
    assert r"\newcommand{\PinnedRepoCountFT}{34}" in generated
    assert r"\newcommand{\ArtifactTierSummaryFT}{\artifacttier{R0}: 32, \artifacttier{R1}: 11, \artifacttier{R2}: 6, \artifacttier{R3}: 18}" in generated
    assert r"\newcommand{\NativeDatedOutputCount}{8}" in generated
    assert r"\newcommand{\TargetedAuditCount}{66}" in generated
    failure_table = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "GPT-Signal & reachable" in failure_table
    assert "1,549/1,554" in failure_table
    assert "future-quarter fundamentals" in failure_table
