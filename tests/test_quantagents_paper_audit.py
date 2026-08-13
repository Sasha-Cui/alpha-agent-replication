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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/quantagents"
SPEC = importlib.util.spec_from_file_location(
    "audit_quantagents_paper", ROOT / "scripts/audit_quantagents_paper.py"
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
    assert data["official_pdf_pages"] == 27
    assert data["rebuilt_pdf_pages"] == 27
    assert data["official_pages_visually_checked"] == 27
    assert data["rebuilt_pages_visually_checked"] == 27
    assert data["arxiv_source_files"] == 16
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["official_pdf_sha256"] == audit.PINS["primary/arxiv.pdf"]
    assert provenance["paper_license"] == "CC BY 4.0"
    assert provenance["visual_qa"][
        "unreadable_clipped_overlapping_blank_or_missing_research_content"
    ] == 0
    assert len(provenance["visual_qa"]["contact_sheet_sha256"]) == 11


def test_source_bundle_is_manuscript_not_system_code() -> None:
    source = rows("paper_source_inventory.csv")
    assert len(source) == 16
    assert Counter(row["role"] for row in source) == {
        "bibliography_or_typesetting_support": 5,
        "primary_manuscript_source": 1,
        "published_figure": 10,
    }
    assert all(row["is_executable_system_source"] == "False" for row in source)
    assert all(row["replication_credit"] == "False" for row in source)


def test_every_published_numeric_cell_fails_closed() -> None:
    performance = rows("published_performance_ledger.csv")
    assert len(performance) == 238
    assert Counter(row["table"] for row in performance) == {
        "main": 115,
        "meeting_ablation": 63,
        "llm_backbone": 54,
        "live_trading": 6,
    }
    assert sum(row["quantagents_system_output"] == "True" for row in performance) == 132
    assert sum(row["author_site_corroborated"] == "True" for row in performance) == 90
    assert all(row["arxiv_source_verified"] == "True" for row in performance)
    assert all(row["native_reproduced_value"] == "" for row in performance)
    assert all(row["paper_result_credit"] == "False" for row in performance)
    assert manifest()["published_numeric_table_cells_faithfully_regenerated"] == 0


def test_empirical_figures_are_inventoried_without_plot_credit() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 10
    assert sum(int(row["panels"]) for row in figures) == 16
    assert sum(int(row["empirical_panels"]) for row in figures) == 14
    assert all(row["rendered_author_asset_recovered"] == "True" for row in figures)
    assert all(row["underlying_numeric_array_released"] == "False" for row in figures)
    assert all(row["native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)


def test_direct_project_route_is_pinned_r1_documentation() -> None:
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert provenance["project_site"] == "https://quantagents.github.io/"
    assert provenance["project_repository"] == audit.REPOSITORY_URL
    assert provenance["project_repository_head"] == audit.REPOSITORY_HEAD
    assert "directly link" in provenance["attribution"]
    assert release["url"] == audit.REPOSITORY_URL
    assert release["head_sha"] == audit.REPOSITORY_HEAD
    assert release["archive_files"] == 41
    assert release["archive_uncompressed_bytes"] == 88_003_221
    assert release["repository_license"] == "MIT"
    assert release["license_text_file_present"] is True


def test_site_has_documentation_and_videos_but_no_runnable_system() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["python_files"] == 0
    assert release["package_or_environment_manifests"] == 0
    assert release["system_runner_files"] == 0
    assert release["author_test_files"] == 0
    assert release["meeting_videos"] == 3
    assert release["rendered_algorithms"] == 4
    assert release["rendered_profiles"] == 4
    assert release["paper_code_released"] is False
    assert release["paper_dataset_released"] is False
    assert release["native_execution_possible"] is False
    documentation = rows("site_documentation_inventory.csv")
    assert len(documentation) == 11
    assert sum(bool(row["shown_date"]) for row in documentation) == 3
    assert all(row["runnable"] == "False" for row in documentation)
    assert all(row["raw_trace"] == "False" for row in documentation)


def test_unrelated_mathvista_template_is_excluded() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["unrelated_mathvista_vqa_records"] == 6_141
    access = {row["artifact"]: row for row in rows("artifact_access_audit.csv")}
    residue = access["MathVista template data"]
    assert "6,141 unrelated" in residue["status"]
    assert residue["tier"] == "unrelated template residue"
    assert residue["system_source_credit"] == "False"


def test_prompt_templates_are_static_examples_without_runtime_lineage() -> None:
    prompts = rows("prompt_inventory.csv")
    assert len(prompts) == 8
    assert all(row["paper_template_or_symbol_recovered"] == "True" for row in prompts)
    for field in (
        "runtime_fill_released",
        "actual_request_released",
        "actual_response_released",
        "executable_prompt_path_released",
    ):
        assert all(row[field] == "False" for row in prompts)
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["prompts"]["status"] == "example_templates_only"
    assert methods["meetings"]["status"] == "pseudocode_and_video_only"
    assert methods["strategy_pool"]["status"] == "underspecified"
    assert methods["backtest_execution"]["status"] == "missing"


def test_internal_conflicts_and_unfulfilled_release_are_explicit() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["full_system_volatility"]["status"] == "hard_internal_conflict"
    assert "1.43%" in checks["full_system_volatility"]["detail"]
    assert "1.23%" in checks["full_system_volatility"]["detail"]
    assert checks["action_count"]["status"] == "hard_internal_conflict"
    assert checks["author_site_dataset"]["status"] == "author_source_scope_conflict"
    assert checks["live_period"]["status"] == "hard_internal_conflict"
    assert checks["annual_return_equation"]["status"] == "mathematical_specification_error"
    assert checks["author_site_code_dataset_controls"]["status"] == "unfulfilled_release"
    assert checks["result_improvements"]["status"] == "consistent"


def test_model_deprecation_and_temporal_risk_are_bounded_not_overclaimed() -> None:
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    model = provenance["model_dependency"]
    assert model["snapshot"] == "gpt-4o-2024-05-13"
    assert model["current_status"] == "deprecated"
    assert model["official_pretraining_horizon"] == "October 2023"
    assert "not proof" in model["interpretation"]
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["model_temporal_boundary"]["status"] == "material_contamination_risk"
    assert "not proof" in checks["model_temporal_boundary"]["detail"]


def test_no_native_runtime_or_result_lineage_is_claimed() -> None:
    native = json.loads((AUDIT_DIR / "native_execution.json").read_text())
    assert native["manuscript_source_rebuilt"] is True
    assert native["manuscript_rebuild_is_system_execution"] is False
    assert native["public_quantagents_system_source_found"] is False
    assert native["quantagents_pipeline_executed"] is False
    assert native["llm_calls_made"] == 0
    assert native["native_agent_actions_loaded"] == 0
    assert native["native_orders_or_fills_loaded"] == 0
    assert native["native_portfolio_trajectories_loaded"] == 0
    assert native["published_table_cells_faithfully_regenerated"] == 0
    assert native["published_empirical_panels_faithfully_regenerated"] == 0
    assert manifest()["full_end_to_end_pipeline_reproduced"] is False
    assert manifest()["strict_success"] is False


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned QuantAgents source/site scratch is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_quantagents_paper.py"),
         "--output", str(tmp_path / "strict"), "--strict"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert json.loads((tmp_path / "strict/manifest.json").read_text())["strict_success"] is False


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
        "not reproduced",
        "R1 author documentation",
        "Zero of 238 cells",
        "zero of 14 empirical panels",
        "6,141-record MathVista/VQA",
        "material contamination risk",
        "no QuantAgents mechanism or",
        "result credit",
    ):
        assert marker in readme
