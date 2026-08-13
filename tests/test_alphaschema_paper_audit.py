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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/alphaschema"
SPEC = importlib.util.spec_from_file_location(
    "audit_alphaschema_paper", ROOT / "scripts/audit_alphaschema_paper.py"
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
    assert data["official_pages_visually_checked"] == 18
    assert data["rebuilt_pages_visually_checked"] == 18
    version = rows("version_audit.csv")[0]
    assert version["submitted"] == "2026-07-29"
    assert version["official_pages"] == "18"
    assert version["source_files"] == "23"
    assert version["rebuilt_pages"] == "18"
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["arxiv"]["id"] == "2607.26642"
    assert provenance["arxiv"]["visual_qa"]["unreadable_clipped_or_overlapping_pages"] == 0


def test_every_printed_numeric_table_unit_fails_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 212
    assert Counter(row["table_label"] for row in results) == audit.RESULT_TABLES
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["published_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    assert manifest()["native_numeric_units_regenerated"] == 0


def test_repository_is_directly_attributable_without_inventing_license() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["url"] == "https://github.com/JingyangYi/AlphaSchema"
    assert release["head_sha"] == "1206a094abfaad7cc53e6dff39f8fae43e851acb"
    assert release["archive_files"] == 32
    assert release["archive_uncompressed_bytes"] == 1_945_533
    assert release["license"] == "not_declared"
    assert "first author" in release["attribution"]
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["release_boundary"]["attribution_strength"] == (
        "direct_manuscript_link_and_first_author_owner"
    )
    assert provenance["release_boundary"]["full_public_history_audited"] is True
    assert provenance["release_boundary"]["public_history_commits"] == 2
    assert provenance["release_boundary"]["historical_unclassified_result_artifact_paths"] == 0


def test_complete_public_history_has_no_latent_result_artifact() -> None:
    history = rows("released_source_history_inventory.csv")
    assert len(history) == 2
    assert history[0]["commit"] == audit.REPOSITORY_ROOT
    assert history[-1]["commit"] == audit.REPOSITORY_HEAD
    assert [int(row["tracked_paths"]) for row in history] == [29, 32]
    assert [int(row["python_paths"]) for row in history] == [16, 16]
    assert {row["schema_or_config_json_paths"] for row in history} == {"6"}
    assert {row["unclassified_result_artifact_paths"] for row in history} == {"0"}
    assert {row["paper_result_artifact_found"] for row in history} == {"False"}
    data = manifest()
    assert data["repository_history_commits_audited"] == 2
    assert data["repository_history_unclassified_result_artifact_paths"] == 0
    assert data["repository_history_paper_result_artifacts_found"] == 0


def test_author_tests_demo_and_appendix_component_have_no_result_credit() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["editable_install_passed"] is True
    assert release["cli_help_passed"] is True
    assert release["bytecode_compilation_passed"] is True
    assert release["author_tests"] == "9 passed"
    assert release["native_demo_rounds"] == 3
    assert release["native_demo_plans"] == 48
    assert release["native_demo_uses_mock_evaluator"] is True
    component = release["paper_appendix_factor_component"]
    assert component["paper_appendix_example_executed"] is True
    assert component["symbols"] == 25
    assert component["periods"] == [20, 100]
    assert component["factor_outputs"] == 2
    assert component["leakage_issues"] == []
    assert component["finite_reward"] is True
    assert component["published_result_credit"] is False
    assert release["published_table_or_figure_regenerated"] is False
    assert release["paper_result_credit"] is False


def test_paper_release_mismatches_are_explicit() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    for dimension in (
        "mutation_ranking", "exploration_schedule", "schema_set_identity", "main_forward_label"
    ):
        assert methods[dimension]["status"] == "paper_release_mismatch"
    assert methods["price_volume_schema"]["status"] == "released_but_revision_diverges"
    assert methods["fundamental_schema"]["status"] == "missing"
    assert methods["final_factor_pool_selection"]["status"] == "missing"
    assert methods["downstream_combiner"]["status"] == "missing"
    assert methods["portfolio_backtest"]["status"] == "missing"
    assert methods["baselines"]["status"] == "missing"
    assert methods["default_launcher"]["status"] == "data_blocked"
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["main_forward_label"]["status"] == "paper_release_mismatch"
    assert checks["schema_inventory"]["status"] == "paper_release_mismatch"
    assert checks["quality_canonicalization"]["status"] == "paper_release_mismatch"
    assert checks["repository_license"]["status"] == "not_declared"


def test_research_payload_and_end_to_end_result_path_are_absent() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    for field in (
        "paper_market_data_released",
        "paper_fundamental_schema_and_data_released",
        "paper_factor_pools_released",
        "paper_baseline_implementations_released",
        "paper_trial_outputs_released",
        "paper_downstream_combiner_released",
        "paper_portfolio_engine_released",
        "default_launcher_operational_as_released",
    ):
        assert release[field] is False
    data = manifest()
    assert data["full_launcher_operational_as_released"] is False
    assert data["full_end_to_end_pipeline_reproduced"] is False
    assert data["strict_success"] is False


def test_empirical_panels_are_inventoried_without_native_credit() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 8
    assert sum(int(row["empirical_series_or_panels"]) for row in figures) == 9
    assert all(row["underlying_numeric_array_released"] == "False" for row in figures)
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)
    assert manifest()["native_empirical_panels_regenerated"] == 0


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned AlphaSchema source/release scratch is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_alphaschema_paper.py"),
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
        "direct rather than inferred",
        "passes all 9 author tests",
        "complete non-shallow public history has only two commits",
        "0/212 published numeric table units",
        "0/9 empirical panels regenerated",
        "not a true reproduction",
    ):
        assert marker in readme
