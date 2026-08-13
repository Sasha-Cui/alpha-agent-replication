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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/sharp"
SPEC = importlib.util.spec_from_file_location("audit_sharp_paper", ROOT / "scripts/audit_sharp_paper.py")
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_json(name: str) -> dict:
    return json.loads((AUDIT_DIR / name).read_text())


def test_original_source_rebuild_and_visual_audit_are_pinned() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["arxiv_id"] == "2605.06822"
    assert provenance["arxiv_version"] == "v1"
    assert provenance["source_files"] == 14
    assert provenance["official_pages"] == 18
    assert provenance["rebuilt_pages"] == 18
    assert provenance["official_pages_visually_checked"] == 18
    assert provenance["rebuilt_pages_visually_checked"] == 18
    assert provenance["visual_defects_observed"] == 0
    assert provenance["official_rebuilt_token_jaccard"] > 0.999
    assert provenance["paper_contains_native_implementation_url"] is False
    assert provenance["paper_contains_dataset_url"] is True
    assert provenance["paper_cited_dataset_url_current_status"] == 404


def test_every_displayed_quantitative_table_cell_fails_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 210
    assert Counter(row["table_label"] for row in results) == {
        "tab:summary": 132,
        "tab:ablation": 16,
        "tab:opensource": 14,
        "tab:static_full": 48,
    }
    assert all(row["unit_definition"] == "one populated displayed quantitative table cell" for row in results)
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["raw_result_record_recovered"] == "False" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["published_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)


def test_empirical_asset_does_not_masquerade_as_raw_result() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 7
    assert sum(int(row["empirical_panels"]) for row in figures) == 1
    assert sum(int(row["empirical_series_or_groups"]) for row in figures) == 6
    empirical = [row for row in figures if row["empirical_panels"] == "1"]
    assert len(empirical) == 1 and empirical[0]["figure"] == "fig:cumret"
    assert all(len(row["source_asset_sha256"]) == 64 for row in figures)
    assert all(row["underlying_numeric_array_or_run_log_recovered"] == "False" for row in figures)
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)


def test_seven_paper_derived_mechanics_execute_with_narrow_credit() -> None:
    components = {row["component"]: row for row in rows("component_execution_audit.csv")}
    assert set(components) == {
        "composite_signal",
        "cross_sectional_2L2S_control",
        "next_open_o2o_return",
        "entry_cost_and_portfolio_return",
        "reported_metrics",
        "validation_gate",
        "rubric_bounds",
    }
    assert all(row["deterministic_control_passed"] == "True" for row in components.values())
    assert all(row["paper_derived_not_author_code"] == "True" for row in components.values())
    assert all(row["author_native_pipeline_executed"] == "False" for row in components.values())
    assert all(row["published_result_regenerated"] == "False" for row in components.values())
    assert all(row["paper_result_credit"] == "False" for row in components.values())
    assert all("not the author implementation" in row["boundary"] for row in components.values())


def test_method_ledger_preserves_specification_and_missing_lineage() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 18
    assert methods["official paper and source"]["status"] == "complete"
    assert methods["native implementation"]["status"] == "claimed_but_unrecovered"
    assert methods["cited LongShort-data"]["status"] == "dead_or_inaccessible"
    assert methods["stock universes"]["status"] == "specified"
    assert methods["walk-forward splits"]["status"] == "partial"
    assert methods["agent prompts and outputs"]["status"] == "missing"
    assert methods["randomness and run lineage"]["status"] == "missing"
    assert methods["raw empirical outputs"]["status"] == "missing"


def test_price_only_baseline_recovery_attempt_does_not_tune_conventions() -> None:
    recovery = {row["target"]: row for row in rows("baseline_recovery_audit.csv")}
    assert len(recovery) == 6
    assert recovery["Yahoo chart endpoint"]["observed_state"] == "HTTP 429"
    assert recovery["all three exact walk-forward calendars"]["observed_state"] == "missing"
    assert recovery["Random L/S seed and draws"]["observed_state"] == "missing"
    final = recovery["price-only published baseline cells"]
    assert final["observed_state"] == "not_defensibly_regenerated"
    assert final["published_result_regenerated"] == "False"
    assert "no tuning to printed cells" in final["boundary"]


def test_material_internal_boundaries_and_consistency_are_explicit() -> None:
    issues = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert issues["shared_initial_rule_count"]["status"] == "conflict"
    assert issues["sector_rule_release"]["status"] == "unverifiable_release_claim"
    assert issues["test_calendar"]["status"] == "underspecified"
    assert issues["transaction_cost_semantics"]["status"] == "ambiguous"
    assert issues["arithmetic_proprietary_averages"]["status"] == "consistent"
    assert issues["arithmetic_open_source_lifts"]["status"] == "consistent"
    assert issues["random_null_interpretation"]["status"] == "appropriately_bounded"
    assert issues["news_safety_gap"]["status"] == "internally_consistent"
    assert issues["production_limits"]["status"] == "explicit_limitation"


def test_release_search_is_bounded_and_cited_repository_is_404() -> None:
    releases = rows("release_search_audit.csv")
    exact = [row for row in releases if row["observation"].startswith("complete bounded exact")]
    assert len(exact) == 9
    assert all(row["observed_matches"] == "0" for row in exact)
    endpoints = [row for row in releases if "API returned 404" in row["observation"]]
    assert len(endpoints) == 2
    hf = [row for row in releases if row["surface"].startswith("Hugging Face")]
    assert len(hf) == 2 and all(row["observed_matches"] == "0" for row in hf)
    assert all(row["attributable_sharp_release_found"] == "False" for row in releases)
    assert all(row["negative_search_boundary"] for row in releases)


def test_manifest_and_readme_state_the_fail_closed_result() -> None:
    manifest = load_json("manifest.json")
    assert manifest["active_quantitative_table_cells"] == 210
    assert manifest["result_tables"] == 4
    assert manifest["author_native_table_cells_regenerated"] == 0
    assert manifest["active_empirical_figure_panels"] == 1
    assert manifest["empirical_figure_series_or_groups"] == 6
    assert manifest["author_native_empirical_panels_regenerated"] == 0
    assert manifest["paper_derived_components_executed"] == 7
    assert manifest["paper_derived_components_passing_controlled_checks"] == 7
    assert manifest["attributable_sharp_implementation_found"] is False
    assert manifest["raw_result_arrays_recovered"] == 0
    assert manifest["strict_success"] is False
    expected = {path.name for path in AUDIT_DIR.iterdir() if path.is_file() and path.name != "manifest.json"}
    assert set(manifest["generated_file_sha256"]) == expected
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "not reproducible end to end",
        "210 displayed quantitative result cells",
        "Zero of 210 cells and 0/1 empirical panels",
        "currently return 404",
        "specification checks, not author code or empirical results",
        "does not tune conventions",
        "six rules",
        "seven rules",
        "strict_success` remains false",
    ):
        assert marker in readme


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned SHARP audit evidence is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_sharp_paper.py"), "--output", str(tmp_path / "strict"), "--strict"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    strict = json.loads((tmp_path / "strict/manifest.json").read_text())
    assert strict["author_native_table_cells_regenerated"] == 0
    assert strict["strict_success"] is False
