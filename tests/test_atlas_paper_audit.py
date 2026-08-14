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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/atlas"
SPEC = importlib.util.spec_from_file_location(
    "audit_atlas_paper", ROOT / "scripts/audit_atlas_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text())


def test_all_five_official_sources_are_pinned_rebuilt_and_visually_checked() -> None:
    data = manifest()
    assert data["official_versions_audited"] == ["v1", "v2", "v3", "v4", "v5"]
    assert data["official_pdf_and_source_recovered"] is True
    assert data["document_rebuild_completed"] is True
    assert data["official_pages_visually_checked"] == 209
    assert data["rebuilt_pages_visually_checked"] == 209
    versions = rows("version_audit.csv")
    assert [row["official_pages"] for row in versions] == ["37", "43", "43", "43", "43"]
    assert [row["rebuilt_pages"] for row in versions] == ["37", "43", "43", "43", "43"]
    assert [row["source_files"] for row in versions] == ["9", "8", "8", "8", "6"]
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["arxiv"]["id"] == "2510.15949"
    visual = provenance["arxiv"]["visual_qa"]
    assert visual["unreadable_clipped_overlapping_blank_or_missing_pages"] == 0
    assert len(visual["contact_sheet_sha256"]) == 25


def test_source_inventory_is_complete_and_never_misclassified_as_system_code() -> None:
    inventory = rows("source_inventory.csv")
    assert len(inventory) == 39
    assert Counter(row["version"] for row in inventory) == {
        "v1": 9, "v2": 8, "v3": 8, "v4": 8, "v5": 6,
    }
    assert all(row["role"] == "official_manuscript_source" for row in inventory)
    assert all(row["paper_system_implementation"] == "False" for row in inventory)


def test_every_current_empirical_table_scalar_fails_closed() -> None:
    results = rows("published_result_ledger.csv")
    expected = {label: count for label, (_, count) in audit.RESULT_TABLES.items()}
    assert len(results) == 1_784
    assert Counter(row["table_label"] for row in results) == expected
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["published_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    assert manifest()["native_numeric_units_regenerated"] == 0


def test_figure_inventory_distinguishes_author_coordinates_from_native_results() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 10
    assert sum(int(row["panels"]) for row in figures) == 12
    assert sum(int(row["empirical_panels"]) for row in figures) == 5
    empirical = [row for row in figures if int(row["empirical_panels"])]
    assert all(row["author_latex_plot_coordinates_recovered"] == "True" for row in empirical)
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)
    assert manifest()["native_empirical_panels_regenerated"] == 0


def test_paper_prompt_templates_are_not_counted_as_runtime_trajectories() -> None:
    prompts = rows("prompt_artifact_inventory.csv")
    assert len(prompts) == 10
    assert all(row["paper_template_recovered"] == "True" for row in prompts)
    for field in (
        "exact_runtime_payload_recovered", "model_request_response_recovered",
        "trajectory_recovered", "native_replayed", "paper_result_credit",
    ):
        assert all(row[field] == "False" for row in prompts)
    data = manifest()
    assert data["paper_prompt_templates_recovered"] == 10
    assert data["runtime_prompt_trajectories_recovered"] == 0


def test_stock_sim_route_is_cited_same_author_but_precedes_atlas() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["url"] == "https://github.com/harrypapadakis/StockSim"
    assert release["head_sha"] == "c1a25c195df4c93b2db4a748f80ceae0f1c9fe50"
    assert release["head_commit_date"] == "2025-07-15T13:12:01+03:00"
    assert release["archive_files"] == 81
    assert release["archive_uncompressed_bytes"] == 31_949_454
    assert "first author" in release["attribution"]
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["release_boundary"]["attribution_strength"] == (
        "paper_cited_same_author_precursor_framework"
    )
    assert provenance["release_boundary"]["atlas_specific_source_recovered"] is False


def test_complete_stocksim_history_recovers_precursor_output_without_paper_credit() -> None:
    history = rows("released_source_history_inventory.csv")
    assert len(history) == 20
    assert [row["commit"] for row in history] == list(audit.STOCKSIM_HISTORY_COMMITS)
    assert all(row["python_source_paths"] == "43" for row in history)
    assert all(
        row["paper_specific_system_source_found"] == "False" for row in history
    )
    artifacts = rows("historical_precursor_artifact_inventory.csv")
    assert len(artifacts) == 4
    xom = next(row for row in artifacts if row["path"] == "charts/XOM.html")
    assert xom["artifact_role"] == "stocksim_precursor_agent_output"
    assert xom["dated_agent_order_events"] == "20"
    assert xom["dated_portfolio_points"] == "43"
    assert xom["attributable_atlas_paper_run"] == "False"
    assert xom["published_result_regenerated"] == "False"
    assert xom["paper_result_credit"] == "False"
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    full = release["full_public_history_audit"]
    assert full["public_commits_reviewed"] == 20
    assert full["public_branches_reviewed"] == 2
    assert full["public_tags"] == 0
    assert full["public_releases"] == 0
    assert full["unreachable_objects"] == 0
    assert full["historical_unique_paths_reviewed"] == 107
    assert full["historical_xom_initial_cash_roi_percent"] == 5.01564
    assert full["historical_xom_matches_published_atlas_xom_roi_mean"] is False
    assert full["historical_lob_asset"] == "AAPL"
    assert full["historical_lob_order_records"] == 191_015


def test_all_public_stocksim_forks_are_exhausted_without_atlas_result_credit() -> None:
    branches = rows("public_fork_branch_ref_snapshot.csv")
    commits = rows("public_fork_unique_commit_inventory.csv")
    census = json.loads((AUDIT_DIR / "public_fork_census.json").read_text())
    assert len(branches) == 11
    assert len({row["repository"] for row in branches}) == 5
    assert len({row["head_commit"] for row in branches}) == 8
    assert Counter(row["relation_to_official_head"] for row in branches) == {
        "exact_official_main": 4,
        "descendant_of_official_main": 7,
    }
    assert all(row["commits_behind_official_main"] == "0" for row in branches)
    assert all(row["public_tag_refs"] == "0" for row in branches)
    assert all(row["native_atlas_result_payload_found"] == "False" for row in branches)
    assert all(row["paper_result_credit"] == "False" for row in branches)
    assert len(commits) == 12
    assert all(row["authored_after_atlas_v5_submission"] == "True" for row in commits)
    assert all(row["atlas_identifier_paths_at_commit"] == "0" for row in commits)
    assert all(row["changed_result_payload_paths"] == "0" for row in commits)
    assert all(row["exact_atlas_author_display_name_match"] == "False" for row in commits)
    assert all(row["native_atlas_result_payload_found"] == "False" for row in commits)
    assert all(row["paper_result_credit"] == "False" for row in commits)
    assert census == json.loads(
        (AUDIT_DIR / "release_execution_audit.json").read_text()
    )["public_fork_census"]
    assert census["census_date"] == "2026-08-14"
    assert census["github_rest_reported_forks"] == 5
    assert census["accessible_public_forks"] == 5
    assert census["accessible_branch_refs"] == 11
    assert census["unique_heads"] == 8
    assert census["official_head_exact_refs"] == 4
    assert census["divergent_unique_heads"] == 7
    assert census["unique_commits_beyond_official_history"] == 12
    assert census["unique_trees_beyond_official_history"] == 26
    assert census["unique_blobs_beyond_official_history"] == 22
    assert census["unique_changed_paths"] == 13
    assert census["atlas_identifier_paths"] == 0
    assert census["changed_result_payload_paths"] == 0
    assert census["native_atlas_result_payloads_found"] == 0
    assert census["paper_result_credit"] is False
    data = manifest()
    assert data["public_forks_audited"] == 5
    assert data["public_fork_branch_refs_audited"] == 11
    assert data["public_fork_unique_heads_audited"] == 8
    assert data["public_fork_unique_commits_beyond_official_history_audited"] == 12
    assert data["public_fork_unique_changed_paths_audited"] == 13
    assert data["public_fork_native_atlas_result_payloads_recovered"] == 0


def test_demo_config_receives_partial_method_evidence_not_complete_atlas_credit() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    for field in (
        "demo_config_matches_atlas_xom_asset",
        "demo_config_matches_atlas_date_window",
        "demo_config_matches_atlas_daily_cadence",
        "demo_config_matches_atlas_initial_cash",
        "demo_config_matches_atlas_three_analyst_roles",
    ):
        assert release[field] is True
    assert release["demo_config_is_complete_atlas_experiment_config"] is False
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["precursor_xom_configuration"]["status"] == "partially_recovered"
    assert methods["assets_and_period"]["status"] == (
        "partially_recovered_not_frozen"
    )
    assert methods["market_data"]["status"] == "precursor_chart_only"
    assert methods["precursor_native_output"]["status"] == (
        "recovered_not_paper_attributable"
    )


def test_license_boundary_distinguishes_readme_declaration_from_license_text() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["license_declaration"] == "MIT"
    assert release["license_text_file_present"] is False
    assert release["github_detected_license"] is None
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["repository_license"]["status"] == "readme_declaration_only"


def test_as_declared_dependency_failure_and_bounded_adjustment_are_explicit() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["as_declared_dependency_install_passed"] is True
    assert release["as_declared_asyncio_import_passed"] is False
    assert "tasks.async" in release["as_declared_failure"]
    assert release["audit_adjustment"] == (
        "removed obsolete asyncio backport so stdlib asyncio is used"
    )
    assert release["dependency_check_after_adjustment_passed"] is True
    assert release["bytecode_compilation_after_adjustment_passed"] is True
    assert release["modules_imported_after_adjustment"] == 43
    assert release["modules_failed_import_after_adjustment"] == 0
    assert release["tracked_test_files"] == 0
    assert release["author_tests"] == "absent"


def test_precursor_component_checks_receive_no_atlas_result_credit() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    checks = release["native_component_fixture"]
    assert checks["config"]["errors"] == []
    assert checks["config"]["instrument"] == ["XOM"]
    assert checks["metrics"]["ROI"] == 0.05
    assert checks["order_match"]["trades"] == 1
    assert checks["candle_triggers"]["market_up"] == 100
    assert checks["atlas_specific_component"] is False
    assert checks["atlas_result_credit"] is False
    assert release["native_component_checks_passed"] == 4
    assert release["published_table_or_figure_regenerated"] is False
    assert release["paper_result_credit"] is False


def test_atlas_payload_and_full_pipeline_are_absent() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    for field in (
        "atlas_specific_code_released", "adaptive_opro_implementation_released",
        "atlas_sample_config_released", "paper_data_snapshot_released",
        "paper_news_and_fundamental_inputs_released",
        "paper_model_requests_responses_released",
        "paper_runtime_prompts_and_trajectories_released", "paper_seeds_released",
        "paper_run_artifacts_released", "paper_result_arrays_released",
        "full_launcher_operational_without_external_services",
    ):
        assert release[field] is False
    assert release["full_launcher_blockers"] == [
        "RabbitMQ host", "log directory", "Polygon or Alpha Vantage API key",
    ]
    data = manifest()
    assert data["atlas_specific_code_recovered"] is False
    assert data["full_end_to_end_pipeline_reproduced"] is False
    assert data["strict_success"] is False


def test_method_inventory_preserves_paper_release_boundaries() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["paper_specific_release"]["status"] == "missing"
    assert methods["assets_and_period"]["status"] == "partially_recovered_not_frozen"
    assert methods["market_data"]["status"] == "precursor_chart_only"
    assert methods["agent_architecture"]["status"] == "precursor_components_execute"
    assert methods["adaptive_opro"]["status"] == "paper_specification_only"
    assert methods["replications"]["status"] == "specified_not_released"
    assert methods["published_results"]["status"] == "not_regenerated"
    assert methods["search_for_release"]["status"] == "no_public_atlas_implementation_found"


def test_published_correlation_claims_recompute_from_rounded_table_values() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert "r=0.644310" in checks["adaptive_absolute_correlation"]["detail"]
    assert "r=0.047462" in checks["adaptive_gain_correlation"]["detail"]
    assert "beta=0.059769" in checks["adaptive_gain_correlation"]["detail"]
    assert "r=-0.777240" in checks["reflection_gain_correlation"]["detail"]
    assert "beta=-0.614329" in checks["reflection_gain_correlation"]["detail"]
    assert checks["code_release_language"]["status"] == "not_fulfilled_in_pinned_evidence"


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned ATLAS paper/StockSim scratch is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_atlas_paper.py"),
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
        "all five official revisions", "209 official and all 209 rebuilt pages",
        "1,784 printed empirical scalar units", "43/43 modules import",
        "four controlled checks", "no ATLAS identifier",
        "20 commits across `main` and", "20 dated, explained orders",
        "+5.01564%", "191,015 AAPL orders", "all five public forks",
        "11 branch refs", "eight unique heads", "12 commits",
        "supplies no", "attributable ATLAS experiment or result evidence",
        "0/1,784 empirical numeric table units", "0/5 empirical panels regenerated",
        "not currently a true experimental replication", "package.",
    ):
        assert marker in readme
