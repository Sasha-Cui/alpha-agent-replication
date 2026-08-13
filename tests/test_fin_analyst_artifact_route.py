from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/route_fin_analyst_paper_audit.py"
SPEC = importlib.util.spec_from_file_location("route_fin_analyst_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_pinned_author_space_is_reachable_r3_without_license_overclaim() -> None:
    row = route.fin_analyst_row()
    assert row["artifact_urls"] == route.URL
    assert row["default_branch_head_shas"].endswith(route.HEAD)
    assert row["observed_licenses"] == "Mohotarema/Fin_Analyst=NOASSERTION"
    assert row["public_artifact_listed"] == "Y"
    assert row["reachability_outcome"] == "reachable_all"
    assert row["static_fidelity_tier"] == "R3"
    assert row["native_execution_attempted"] == "Y"
    result = json.loads(row["artifact_url_results_json"])[0]
    assert result["url_type"] == "huggingface_space"
    assert result["head_sha"] == route.HEAD
    assert result["observed_license"] == "NOASSERTION"
    assert result["static_observation"]["file_count"] == 13
    assert result["static_observation"]["archive_sha256"] == route.ARCHIVE_SHA256


def test_committed_artifact_evidence_contains_fin_analyst_correction() -> None:
    audit_dir = ROOT / "paper_runs/submission_evidence/artifact_audit"
    rows = csv_rows(audit_dir / "artifact_audit.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row == {key: str(value) for key, value in route.fin_analyst_row().items()}
    summary = csv_rows(audit_dir / "artifact_audit_summary.csv")
    ft = {row["metric"]: row for row in summary if row["group"] == "F+T"}
    assert ft["public_artifact_listed"]["successes"] == "36"
    assert ft["artifact_reachable_among_all"]["successes"] == "35"
    assert ft["github_head_resolved_among_all"]["successes"] == "34"
    assert ft["static_R3_among_all"]["successes"] == "18"
    payload = json.loads((audit_dir / "artifact_audit.json").read_text())
    correction = next(
        item for item in payload["metadata"]["post_freeze_evidence_corrections"]
        if item["system_id"] == route.SYSTEM_ID
    )
    assert correction["source_head"] == route.HEAD
    assert payload["metadata"]["registry_sha256"] == route.sha256(route.REGISTRY)


def test_native_ledger_credits_dated_outputs_but_not_common_task_or_paper_results() -> None:
    rows = csv_rows(ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv")
    row = next(item for item in rows if item["system_id"] == route.SYSTEM_ID)
    assert row["public_artifact_status"] == "reachable_static_snapshot"
    assert row["static_tier"] == "R3"
    assert row["native_dated_signal_or_return_shipped"] == "Y"
    assert row["prespecified_G7_monthly_common_task_compatible"] == "N"
    assert row["blocking_stage"] == "A3_wrong_asset_scope_TSLA_BTC_not_six_country_security_panel"
    assert row["fidelity_class"] == "F2_dated_output_task_incompatible"
    assert row["targeted_execution_audit_status"] == (
        "paper_audit:completed_pre_live_R3_native_controlled_paths_97_official_decisions_"
        "replayed_zero_of_119_table_cells_zero_of_2_full_empirical_panels_major_table_"
        "figure_source_conflicts"
    )
    note = row["concise_evidence_note"]
    for marker in (
        "97 paper-window decisions", "0/119 printed table cells",
        "TSLA +4.79%", "BTC replays -0.10%", "three HOLD votes to BUY",
        "cannot supply the six-country security-level common task",
    ):
        assert marker in note


def test_paper_route_prioritizes_public_native_evidence_without_overclaiming() -> None:
    rows = csv_rows(
        ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    row = next(item for item in rows if item["canonical_work_id"] == "CensusArxiv260712233")
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == route.SYSTEM_ID
    assert row["static_fidelity_tiers"] == "R3"
    assert row["native_pipeline_disposition"] == "targeted_execution_recorded"
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert row["mapping_disposition"] == "availability_only_no_performance_inference"
    assert row["proxy_role"] == "no_proxy"
    assert "0/119 printed table cells" in row["precise_native_or_access_blocker"]


def test_static_assets_reflect_evidence_derived_counts() -> None:
    generated = (ROOT / "docs/paper/generated_results.tex").read_text()
    for macro in (
        r"\newcommand{\ArtifactCountFT}{36}",
        r"\newcommand{\ReachableArtifactCountFT}{35}",
        r"\newcommand{\PinnedRepoCountFT}{34}",
        r"\newcommand{\ArtifactTierSummaryFT}{\artifacttier{R0}: 32, \artifacttier{R1}: 11, \artifacttier{R2}: 6, \artifacttier{R3}: 18}",
        r"\newcommand{\NativeDatedOutputCount}{11}",
        r"\newcommand{\TargetedAuditCount}{67}",
    ):
        assert macro in generated
    routes = (ROOT / "docs/paper/generated_evidence_routes.tex").read_text()
    assert r"\newcommand{\PublicCodeRouteWorkCount}{35\xspace}" in routes
    assert r"\newcommand{\PaperOnlyUnderspecifiedWorkCount}{34\xspace}" in routes
    failure = (ROOT / "docs/paper/tables/artifact_failures.tex").read_text()
    assert "Fin-Analyst at FinMMEval Task 3 & reachable" in failure
    assert "0/119 printed table cells" in failure
