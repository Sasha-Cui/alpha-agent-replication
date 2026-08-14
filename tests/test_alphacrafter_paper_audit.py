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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/alphacrafter"
SPEC = importlib.util.spec_from_file_location(
    "audit_alphacrafter_paper", ROOT / "scripts/audit_alphacrafter_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text())


def test_both_official_versions_are_pinned_and_visually_checked() -> None:
    data = manifest()
    assert data["official_versions_audited"] == ["v1", "v2"]
    assert data["v2_substantial_revision"] is True
    assert data["official_pdf_and_source_recovered"] is True
    assert data["v1_document_rebuild_completed"] is True
    assert data["v2_document_rebuild_completed"] is True
    assert data["v2_rebuild_blocker"] is None
    assert data["v2_build_source_matches_official_archive"] is True
    assert data["v2_rebuilt_manuscript_tokens_match"] is True
    assert data["official_pages_visually_checked"] == 48
    assert data["rebuilt_pages_visually_checked"] == 48
    revisions = {row["version"]: row for row in rows("version_revision_audit.csv")}
    assert revisions["v1"]["submitted"] == "2026-05-07"
    assert revisions["v1"]["official_pages"] == "26"
    assert revisions["v1"]["rebuilt_pages"] == "26"
    assert revisions["v2"]["submitted"] == "2026-07-28"
    assert revisions["v2"]["official_pages"] == "22"
    assert revisions["v2"]["rebuilt_pages"] == "22"
    assert revisions["v2"]["version_relationship"].startswith("substantial")
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["arxiv"]["id"] == "2605.05580"
    assert provenance["arxiv"]["visual_qa"]["unreadable_clipped_or_overlapping_pages"] == 0
    assert "CJK" in provenance["arxiv"]["v2_build_boundary"]
    build = json.loads((AUDIT_DIR / "document_build_verification.json").read_text())
    assert build["official_source_tree_modified_for_build"] is False
    assert build["pdf_latex_passes"] == 4
    assert build["bibtex_passes"] == 1
    assert build["successful_pass_page_counts"] == [19, 22, 22, 22]
    assert build["converged_on_pdf_latex_pass"] == 4
    assert build["official_pages"] == build["rebuilt_pages"] == 22
    assert build["manuscript_token_comparison"][
        "all_manuscript_tokens_match_after_expected_metadata_differences"
    ] is True
    visual = build["visual_comparison"]
    assert visual["pages_compared"] == 22
    assert visual["unreadable_clipped_overlapping_or_missing_elements"] == 0
    assert visual["layout_tables_figures_pagination_match"] is True


def test_every_printed_result_unit_fails_closed() -> None:
    v1 = rows("published_result_ledger_v1.csv")
    v2 = rows("published_result_ledger_v2.csv")
    assert len(v1) == 176
    assert len(v2) == 304
    assert Counter(row["table_label"] for row in v1) == audit.V1_RESULT_TABLES
    assert Counter(row["table_label"] for row in v2) == audit.V2_RESULT_TABLES
    for result in v1 + v2:
        assert result["source_document_recovered"] == "True"
        assert result["author_native_experiment_executed"] == "False"
        assert result["published_result_regenerated"] == "False"
        assert result["paper_result_credit"] == "False"
    data = manifest()
    assert data["v1_native_numeric_units_regenerated"] == 0
    assert data["v2_native_numeric_units_regenerated"] == 0


def test_release_attribution_is_strong_without_claiming_direct_paper_link() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["url"] == "https://github.com/NJU-LINK/AlphaCrafter"
    assert release["head_sha"] == "c6dbc1ba4e0a4ecbc3ea1454c5290dbea4b36b0d"
    assert release["archive_files"] == 79
    assert release["archive_uncompressed_bytes"] == 889_614
    assert release["license"] == "MIT"
    assert release["python_files"] == 48
    assert "not directly linked" in release["attribution"]
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["release_boundary"]["attribution_strength"].endswith(
        "not_direct_paper_link"
    )
    assert provenance["release_boundary"]["full_public_history_audited"] is True
    assert provenance["release_boundary"]["public_history_commits"] == 13
    assert provenance["release_boundary"]["historical_agent_result_or_run_artifacts"] == 0
    assert provenance["release_boundary"]["historical_paper_result_literal_hits_outside_index_inputs"] == 0


def test_complete_public_history_has_no_latent_agent_result_artifact() -> None:
    history = rows("released_source_history_inventory.csv")
    assert len(history) == 13
    assert history[0]["commit"] == audit.REPOSITORY_ROOT
    assert history[-1]["commit"] == audit.REPOSITORY_HEAD
    assert [int(row["tracked_paths"]) for row in history] == [69] + [77] * 7 + [79] * 5
    assert [int(row["python_paths"]) for row in history] == [49] * 8 + [48] * 5
    assert {row["unclassified_structured_paths"] for row in history} == {"0"}
    assert {row["agent_result_or_run_artifact_paths"] for row in history} == {"0"}
    assert {row["paper_result_literal_hits_outside_index_inputs"] for row in history} == {"0"}
    assert {row["paper_result_artifact_found"] for row in history} == {"False"}
    data = manifest()
    assert data["repository_history_commits_audited"] == 13
    assert data["repository_history_unclassified_structured_paths"] == 0
    assert data["repository_history_agent_result_or_run_artifact_paths"] == 0
    assert data["repository_history_paper_result_artifacts_found"] == 0
    assert data["repository_history_paper_result_literal_hits_outside_index_inputs"] == 0


def test_native_components_pass_without_paper_result_credit() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["editable_install_passed"] is True
    assert release["cli_help_passed"] is True
    assert release["bytecode_compilation_passed"] is True
    assert release["tracked_tests"] == 0
    assert release["pytest_outcome"] == "no tests collected (exit 5)"
    assert release["a_share_component_check"]["a_share_buy_success"] is True
    assert release["a_share_component_check"]["a_share_t_plus_one_unlock_success"] is True
    assert release["a_share_component_check"]["a_share_sell_success"] is True
    assert release["us_component_check"]["us_short_success"] is True
    assert release["us_component_check"]["us_cover_success"] is True
    assert release["metric_component_check"]["evaluation_metric_contract_success"] is True
    assert release["component_fixture_uses_synthetic_data"] is True
    assert release["published_table_or_figure_regenerated"] is False
    assert release["paper_result_credit"] is False


def test_full_launcher_and_multimarket_boundaries_fail_closed() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["default_requested_model"] == "gpt-5.3-codex"
    assert release["registered_models"] == ["gpt-5", "gpt-5.2"]
    assert release["full_launcher_reached_model_api"] is False
    methods = {
        (row["version"], row["dimension"]): row
        for row in rows("method_specification_audit.csv")
    }
    assert methods[("v1_v2", "default_model_configuration")]["status"] == "internally_broken"
    assert methods[("v1_v2", "model_backbones")]["status"] == "paper_specified_release_incomplete"
    assert methods[("v1_v2", "end_to_end_market_routing")]["status"] == "incomplete"
    assert methods[("v1_v2", "release_data_payload")]["status"] == "templates_only"
    assert methods[("v1_v2", "baseline_implementations")]["status"] == "missing"
    assert methods[("v1_v2", "live_brokerage")]["status"] == "missing"
    assert methods[("v1_v2", "published_results")]["status"] == "not_regenerated"


def test_internal_conflicts_and_release_mismatches_are_explicit() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["v1_full_model_cross_table"]["status"] == "conflicting_values"
    assert checks["v2_full_model_cross_table"]["status"] == "consistent"
    assert checks["default_model_registry"]["status"] == "runtime_failure"
    assert checks["provider_generality"]["status"] == "paper_release_mismatch"
    assert checks["us_end_to_end_path"]["status"] == "paper_release_mismatch"
    assert checks["released_calendar_coverage"]["status"] == "paper_release_mismatch"
    assert checks["live_execution_claim"]["status"] == "unverifiable_from_release"
    assert checks["v2_source_build"]["status"] == "complete"


def test_empirical_panels_are_inventoried_without_native_credit() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 12
    assert sum(int(row["empirical_series_or_panels"]) for row in figures if row["version"] == "v1") == 16
    assert sum(int(row["empirical_series_or_panels"]) for row in figures if row["version"] == "v2") == 14
    assert all(row["underlying_numeric_array_released"] == "False" for row in figures)
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)
    assert manifest()["native_empirical_panels_regenerated"] == 0


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned AlphaCrafter primary-source scratch is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audit_alphacrafter_paper.py"),
            "--output",
            str(tmp_path / "strict"),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert json.loads((tmp_path / "strict/manifest.json").read_text())[
        "full_end_to_end_pipeline_reproduced"
    ] is False


def test_manifest_hashes_every_output_and_readme_states_honest_boundary() -> None:
    data = manifest()
    expected = {
        path.name
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    readme = (AUDIT_DIR / "README.md").read_text()
    for marker in (
        "strongly attributable",
        "does not directly link",
        "fails before any API call",
        "complete non-shallow repository history has 13 commits",
        "0/176 v1 and 0/304 v2",
        "0/16 v1 and 0/14 v2",
        "not an AlphaCrafter replication",
    ):
        assert marker in readme
