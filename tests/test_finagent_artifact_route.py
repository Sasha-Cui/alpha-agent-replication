from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/route_finagent_paper_audit.py"
SPEC = importlib.util.spec_from_file_location("route_finagent_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_pinned_correction_row_is_author_linked_reachable_and_r3() -> None:
    row = route.finagent_row()
    assert row["artifact_urls"] == "https://github.com/DVampire/FinAgent"
    assert row["default_branch_head_shas"].endswith(route.HEAD)
    assert row["observed_licenses"] == "DVampire/FinAgent=MIT"
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R3"
    result = json.loads(row["artifact_url_results_json"])[0]
    assert result["static_observation"]["file_count"] == 342
    assert result["static_observation"]["has_runner"] is True


def test_committed_artifact_audit_and_summary_include_correction() -> None:
    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == "SYS-FIN-AGENT")
    assert row == {key: str(value) for key, value in route.finagent_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {(row["metric"]): row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "24"
    assert ft["artifact_reachable_among_all"]["successes"] == "23"
    assert ft["github_head_resolved_among_all"]["successes"] == "23"
    assert ft["static_R3_among_all"]["successes"] == "10"
    payload = json.loads((audit_dir / "artifact_audit.json").read_text(encoding="utf-8"))
    correction = payload["metadata"]["post_freeze_evidence_corrections"]
    assert {item["system_id"] for item in correction} == {
        "SYS-FIN-AGENT",
        "SYS-EMPIRICAL-ASSET-PRICING-LLM",
        "SYS-GPT-SIGNAL",
        "SYS-HEDGE-AGENTS",
        "SYS-RAPTOR",
    }
    assert payload["metadata"]["registry_sha256"] == route.sha256(route.REGISTRY)


def test_native_ledger_does_not_promote_static_source_to_result_reproduction() -> None:
    rows = csv_rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in rows if item["system_id"] == "SYS-FIN-AGENT")
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R3"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["blocking_stage"] == "A2_no_shipped_native_dated_output"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_zero_of_1061_published_result_units_substantial_source_conflicts"
    )
    assert row["fidelity_class"] == "F1_static_no_native_output"
    assert "zero native results reproduced" in row["concise_evidence_note"]


def test_static_paper_assets_and_claim_hashes_reflect_the_correction() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\ArtifactCountFT}{24}" in generated
    assert r"\newcommand{\ArtifactRateFT}{35.8\%}" in generated
    assert r"\newcommand{\ReachableArtifactCountFT}{23}" in generated
    assert r"\newcommand{\LicensedArtifactCountFT}{12}" in generated
    assert r"\newcommand{\PinnedRepoCountFT}{23}" in generated
    assert r"\newcommand{\TargetedAuditCount}{33}" in generated
    system_table = (ROOT / "docs/paper/tables/system_registry.tex").read_text(encoding="utf-8")
    failure_table = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert "DVampire/FinAgent" in system_table
    assert "FinAgent & reachable" in failure_table
    assert "zero native results reproduced" in failure_table
    claims = {row["macro"]: row for row in csv_rows(ROOT / "paper_runs/submission_evidence/claims.csv")}
    assert claims["ArtifactCountFT"]["rendered_value"] == "24"
    assert claims["ArtifactCountFT"]["source_sha256"] == route.sha256(
        ROOT / "paper_runs/submission_evidence/artifact_audit/artifact_audit.csv"
    )
    assert claims["TargetedAuditCount"]["rendered_value"] == "33"
    assert claims["TargetedAuditCount"]["source_sha256"] == route.sha256(
        ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
    )
