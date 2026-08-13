from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/route_p1gpt_paper_audit.py"
SPEC = importlib.util.spec_from_file_location("route_p1gpt_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_correction_row_routes_attributable_web_client_at_r3() -> None:
    row = route.p1gpt_row()
    assert row["artifact_urls"] == route.ARTIFACT_URL
    assert row["artifact_url_count"] == 1
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R3"
    assert row["native_execution_attempted"] == "Y"
    result = json.loads(row["artifact_url_results_json"])[0]
    assert result["github_owner_repo"] == route.OWNER_REPO
    assert result["head_sha"] == route.HEAD
    assert result["observed_license"] == "MIT"
    observation = result["static_observation"]
    assert observation["file_count"] == 38
    assert observation["python_file_count"] == 22
    assert observation["python_compile_exit"] == 0
    assert observation["has_runner"] is True
    assert observation["has_support"] is True
    assert observation["model_service_source_shipped"] is False
    assert observation["paper_result_generator_shipped"] is False


def test_committed_artifact_audit_and_summary_include_p1gpt() -> None:
    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row == {key: str(value) for key, value in route.p1gpt_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {row["metric"]: row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "35"
    assert ft["artifact_reachable_among_all"]["successes"] == "34"
    assert ft["github_head_resolved_among_all"]["successes"] == "33"
    assert ft["static_R2_or_R3_among_all"]["successes"] == "23"
    assert ft["static_R3_among_all"]["successes"] == "17"
    payload = json.loads((audit_dir / "artifact_audit.json").read_text(encoding="utf-8"))
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
    assert payload["metadata"]["registry_sha256"] == route.sha256(route.REGISTRY)


def test_native_ledger_credits_static_component_but_zero_native_outputs() -> None:
    rows = csv_rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R3"
    assert row["native_dated_signal_or_return_shipped"] == "N"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A2_no_shipped_native_dated_output"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_46_of_72_displayed_cells_verified_zero_of_12_"
        "native_agent_cells_end_to_end_lookahead_counterexample"
    )
    assert row["fidelity_class"] == "F1_static_no_native_output"
    note = row["concise_evidence_note"]
    assert "11/12 P1GPT cells" in note
    assert "35 of another 36 cells" in note
    assert "6.14%, not the printed 6.41%" in note
    assert "0/12 native P1GPT cells" in note
    assert "lookahead" in note


def test_paper_route_prioritizes_component_blocker_over_proxy() -> None:
    rows = csv_rows(
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    row = next(item for item in rows if item["canonical_work_id"] == "CensusArxiv251023032")
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == route.SYSTEM_ID
    assert row["static_fidelity_tiers"] == "R3"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert "0/12 native P1GPT cells" in row["precise_native_or_access_blocker"]
    assert row["proxy_role"] == "secondary_diagnostic_after_native_review"


def test_static_paper_assets_reflect_p1gpt_correction() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text(encoding="utf-8")
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
    assert r"\newcommand{\TargetedAuditCount}{65}" in generated
    system_table = (ROOT / "docs/paper/tables/system_registry.tex").read_text(encoding="utf-8")
    failure_table = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text(encoding="utf-8")
    assert r"P1GPT/web\_demo" in system_table
    assert "P1GPT & reachable" in failure_table
    assert "0/12 native P1GPT cells" in failure_table
    assert "lookahead" in failure_table
