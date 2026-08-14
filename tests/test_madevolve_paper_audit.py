from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/madevolve_trading"
SPEC = importlib.util.spec_from_file_location(
    "audit_madevolve_paper", ROOT / "scripts/audit_madevolve_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text())


def test_official_source_is_pinned_rebuilt_and_visually_checked() -> None:
    data = manifest()
    assert data["official_versions_audited"] == ["v1"]
    assert data["official_pdf_and_source_recovered"] is True
    assert data["document_rebuild_completed"] is True
    assert data["official_pages_visually_checked"] == 46
    assert data["rebuilt_pages_visually_checked"] == 46
    version = rows("version_audit.csv")[0]
    assert version["submitted"] == "2026-05-21"
    assert version["official_pages"] == "46"
    assert version["source_files"] == "19"
    assert version["rebuilt_pages"] == "46"
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["arxiv"]["id"] == "2605.23007"
    assert provenance["arxiv"]["visual_qa"][
        "unreadable_clipped_overlapping_blank_or_missing_pages"
    ] == 0
    assert len(provenance["arxiv"]["visual_qa"]["contact_sheet_sha256"]) == 8


def test_every_empirical_numeric_table_unit_fails_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 214
    assert Counter(row["table_label"] for row in results) == audit.RESULT_TABLES
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["published_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    assert manifest()["native_numeric_units_regenerated"] == 0


def test_repository_route_is_direct_and_coauthor_owned() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["url"] == "https://github.com/tianyi-stack/MadEvolve"
    assert release["head_sha"] == "8b881d3a45d8f68050c28c8d64c2bb653001103a"
    assert release["archive_files"] == 69
    assert release["archive_uncompressed_bytes"] == 413_976
    assert "coauthor Tianyi Li" in release["attribution"]
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["framework_site"]["direct_repository_link"] == release["url"]
    assert provenance["release_boundary"]["attribution_strength"] == (
        "direct_manuscript_site_to_coauthor_repository"
    )


def test_full_public_history_contains_no_latent_paper_payload() -> None:
    history = rows("released_source_history_inventory.csv")
    assert [row["commit"] for row in history] == list(audit.REPOSITORY_COMMITS)
    assert len(history) == 6
    assert {row["tracked_paths"] for row in history} == {"69"}
    assert {row["python_paths"] for row in history} == {"66"}
    assert {row["structured_result_or_data_payload_paths"] for row in history} == {"0"}
    assert {row["paper_domain_literal_hits_outside_readme"] for row in history} == {"0"}
    assert {row["paper_result_artifact_found"] for row in history} == {"False"}
    data = manifest()
    assert data["repository_history_commits_audited"] == 6
    assert data["repository_history_structured_result_or_data_payload_paths"] == 0
    assert data["repository_history_paper_result_artifacts_found"] == 0
    boundary = json.loads((AUDIT_DIR / "source_provenance.json").read_text())[
        "release_boundary"
    ]
    assert boundary["full_public_history_audited"] is True
    assert (boundary["public_branches"], boundary["public_tags"], boundary["public_releases"]) == (
        1, 0, 0
    )
    assert boundary["unreachable_git_objects"] == 0


def test_every_public_fork_ref_stays_inside_audited_official_history() -> None:
    branches = rows("public_fork_branch_ref_snapshot.csv")
    heads = rows("public_fork_unique_head_inventory.csv")
    census = json.loads((AUDIT_DIR / "public_fork_census.json").read_text())
    assert len(branches) == 2
    assert {row["repository"] for row in branches} == set(audit.PUBLIC_FORK_REPOSITORIES)
    assert {row["head_commit"] for row in branches} == {
        audit.REPOSITORY_HEAD,
        audit.REPOSITORY_COMMITS[0],
    }
    assert {row["relation_to_official_head"] for row in branches} == {
        "official_head_exact",
        "official_history_ancestor",
    }
    assert {row["commits_ahead_of_official"] for row in branches} == {"0"}
    assert {row["unique_commits_beyond_official_history"] for row in branches} == {"0"}
    assert {row["unique_blobs_beyond_official_history"] for row in branches} == {"0"}
    assert {row["native_result_artifact_found"] for row in branches} == {"False"}
    assert {row["paper_result_credit"] for row in branches} == {"False"}
    assert len(heads) == 2
    assert {row["relation_to_official_history"] for row in heads} == {
        "official_head_exact",
        "official_history_ancestor",
    }
    assert census["census_date"] == "2026-08-14"
    assert census["github_rest_reported_forks"] == 2
    assert census["accessible_public_forks"] == 2
    assert census["accessible_branch_refs"] == 2
    assert census["tag_refs"] == 0
    assert census["unique_heads"] == 2
    assert census["official_head_exact_unique_heads"] == 1
    assert census["official_history_ancestor_unique_heads"] == 1
    assert census["divergent_unique_heads"] == 0
    assert census["unique_commits_beyond_official_history"] == 0
    assert census["unique_blobs_beyond_official_history"] == 0
    assert census["native_result_artifacts_found"] == 0
    assert census["paper_result_credit"] is False
    data = manifest()
    assert data["public_forks_accessible"] == 2
    assert data["public_fork_branch_refs_audited"] == 2
    assert data["public_fork_unique_heads_audited"] == 2
    assert data["public_fork_divergent_heads_audited"] == 0
    assert data["public_fork_native_result_artifacts_found"] is False
    assert data["public_fork_paper_result_credit"] is False


def test_license_boundary_distinguishes_declaration_from_license_text() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["license_declaration"] == "MIT"
    assert release["license_text_file_present"] is False
    assert release["github_detected_license"] is None
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["repository_license"]["status"] == "metadata_only"


def test_as_declared_runtime_failures_and_audit_adaptation_are_explicit() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["editable_install_passed"] is True
    assert release["cli_help_as_declared_passed"] is False
    assert release["cli_failure_missing_dependency"] == "python-dotenv"
    assert release["cli_help_after_audit_dependency_passed"] is True
    assert release["bytecode_compilation_passed"] is False
    assert "insight.py:123" in release["compile_failure"]
    assert release["modules_imported_after_audit_dependency"] == 64
    assert release["modules_failed_import_after_audit_dependency"] == 2
    assert release["tracked_test_files"] == 0
    assert release["author_tests"] == "absent"


def test_general_framework_components_pass_without_trading_or_result_credit() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    component = release["native_component_fixture"]
    assert component["differential_patch"]["success"] is True
    assert component["partition_grid"]["insertions"] == [True, True, True]
    assert component["islands"]["total_members"] == 5
    assert component["elite_vault"]["top"] == ["p1", "p2"]
    assert component["artifact_store"]["lineage"] == ["p0", "p1"]
    assert component["paper_trading_component"] is False
    assert component["paper_result_credit"] is False
    assert release["published_table_or_figure_regenerated"] is False
    assert release["paper_result_credit"] is False


def test_trading_research_payload_and_end_to_end_path_are_absent() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    for field in (
        "paper_trading_code_released",
        "paper_market_data_released",
        "paper_configs_and_seeds_released",
        "paper_model_call_traces_released",
        "paper_candidate_programs_released",
        "paper_best_evolved_programs_released",
        "paper_backtester_released",
        "paper_optuna_studies_released",
        "paper_claude_code_search_artifacts_released",
        "paper_run_reports_released",
        "paper_result_arrays_released",
        "full_launcher_operational_as_released",
    ):
        assert release[field] is False
    data = manifest()
    assert data["full_launcher_operational_as_released"] is False
    assert data["full_end_to_end_pipeline_reproduced"] is False
    assert data["strict_success"] is False


def test_method_inventory_preserves_paper_release_boundaries() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["framework_release"]["status"] == "substantial_general_framework"
    assert methods["trading_adapter"]["status"] == "missing"
    assert methods["baseline_forecaster"]["status"] == "pseudocode_only"
    assert methods["baseline_strategy"]["status"] == "pseudocode_only"
    assert methods["paper_islands"]["status"] == "configuration_missing"
    assert methods["paper_migration"]["status"] == "framework_default_matches"
    assert methods["five_madevolve_runs"]["status"] == "missing"
    assert methods["optuna_sweeps"]["status"] == "specified_not_released"
    assert methods["cli_as_declared"]["status"] == "fails_missing_dependency"
    assert methods["bytecode_compilation"]["status"] == "fails_release_syntax_error"


def test_empirical_panels_are_inventoried_without_source_figure_credit() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 13
    assert sum(int(row["empirical_series_or_panels"]) for row in figures) == 21
    assert all(row["rendered_author_figure_recovered"] == "True" for row in figures)
    assert all(row["underlying_numeric_array_released"] == "False" for row in figures)
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)
    assert manifest()["native_empirical_panels_regenerated"] == 0


def test_paper_internal_counts_are_recorded_consistently() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["paper_program_total"]["status"] == "consistent"
    assert checks["five_run_candidate_total"]["status"] == "consistent"
    assert checks["run5_count"]["status"] == "consistent"
    assert checks["paper_island_count"]["status"] == "configuration_missing"
    assert checks["research_payload"]["status"] == "unreleased"
    assert checks["live_trading_claim"]["status"] == "paper_disclaims_transfer"


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned MadEvolve source/release scratch is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_madevolve_paper.py"),
         "--output", str(tmp_path / "strict"), "--strict"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert json.loads((tmp_path / "strict/manifest.json").read_text())[
        "full_end_to_end_pipeline_reproduced"
    ] is False


def test_manifest_hashes_every_output_and_readme_states_honest_boundary() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    readme = (AUDIT_DIR / "README.md").read_text()
    for marker in (
        "direct paper-to-framework-site-to-coauthor-repository route",
        "64/66 modules import",
        "full public Git history",
        "six commits on one branch",
        "public fork surface was exhausted",
        "two branch refs and no tag refs",
        "zero unique commits, zero unique",
        "no trading-specific implementation",
        "0/214 empirical numeric table units",
        "0/21 empirical panels regenerated",
        "not a true replication package",
    ):
        assert marker in readme
