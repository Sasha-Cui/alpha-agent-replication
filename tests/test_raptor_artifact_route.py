from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/route_raptor_paper_audit.py"
SPEC = importlib.util.spec_from_file_location("route_raptor_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_pinned_correction_row_is_paper_linked_reachable_and_r3() -> None:
    row = route.raptor_row()
    assert row["artifact_urls"] == route.URL
    assert row["default_branch_head_shas"].endswith(route.HEAD)
    assert row["observed_licenses"].endswith("=Apache-2.0")
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R3"
    result = json.loads(row["artifact_url_results_json"])[0]
    assert result["static_observation"]["file_count"] == 825
    assert result["static_observation"]["has_runner"] is True
    assert result["static_observation"]["archive_sha256"] == route.ARCHIVE_SHA256


def test_committed_artifact_audit_and_summary_include_raptor() -> None:
    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row == {key: str(value) for key, value in route.raptor_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {row["metric"]: row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "32"
    assert ft["artifact_reachable_among_all"]["successes"] == "31"
    assert ft["github_head_resolved_among_all"]["successes"] == "30"
    assert ft["static_R3_among_all"]["successes"] == "16"
    payload = json.loads((audit_dir / "artifact_audit.json").read_text(encoding="utf-8"))
    corrections = payload["metadata"]["post_freeze_evidence_corrections"]
    assert {item["system_id"] for item in corrections} == {
        "SYS-FIN-AGENT",
        "SYS-ALPHA-SCHEMA",
        "SYS-ALPHA-CRAFTER",
        "SYS-COG-ALPHA",
        "SYS-EMPIRICAL-ASSET-PRICING-LLM",
        "SYS-GPT-SIGNAL",
        "SYS-HEDGE-AGENTS",
        "SYS-MACI",
        "SYS-MOUNTAIN-LION",
        "SYS-P1GPT",
        "SYS-RAPTOR",
        "SYS-MM-DREX",
            "SYS-MAD-EVOLVE",
    }
    assert payload["metadata"]["registry_sha256"] == route.sha256(route.REGISTRY)


def test_native_ledger_credits_outputs_but_not_end_to_end_reproduction() -> None:
    rows = csv_rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R3"
    assert row["native_dated_signal_or_return_shipped"] == "Y"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A3_US_only_not_six_country"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_16_of_42_author_output_scalar_units_zero_"
        "end_to_end_result_cells"
    )
    assert row["fidelity_class"] == "F2_dated_output_task_incompatible"
    note = row["concise_evidence_note"]
    assert "recover 16/42 scalar units" in note
    assert "0/42 result units" in note
    assert "author-output verification, not experiment reproduction" in note


def test_static_paper_assets_reflect_raptor_correction() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\ArtifactCountFT}{32}" in generated
    assert r"\newcommand{\ReachableArtifactCountFT}{31}" in generated
    assert r"\newcommand{\LicensedArtifactCountFT}{18}" in generated
    assert r"\newcommand{\PinnedRepoCountFT}{30}" in generated
    assert r"\newcommand{\ArtifactTierSummaryFT}{\artifacttier{R0}: 36, \artifacttier{R1}: 9, \artifacttier{R2}: 6, \artifacttier{R3}: 16}" in generated
    assert r"\newcommand{\NativeDatedOutputCount}{6}" in generated
    assert r"\newcommand{\TargetedAuditCount}{49}" in generated
    system_table = (ROOT / "docs/paper/tables/system_registry.tex").read_text(encoding="utf-8")
    failure_table = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert route.OWNER_REPO.replace("_", r"\_") in system_table
    assert "RAPTOR & reachable" in failure_table
    assert "recover 16/42 scalar units" in failure_table
    assert "0/42 result units" in failure_table
