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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/xalpha"
SPEC = importlib.util.spec_from_file_location("audit_xalpha_paper", ROOT / "scripts/audit_xalpha_paper.py")
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
    assert provenance["arxiv_id"] == "2607.08332"
    assert provenance["arxiv_version"] == "v2"
    assert provenance["source_files"] == 22
    assert provenance["official_pages"] == 61
    assert provenance["rebuilt_pages"] == 61
    assert provenance["official_pages_visually_checked"] == 61
    assert provenance["rebuilt_pages_visually_checked"] == 61
    assert provenance["visual_defects_observed"] == 0
    assert provenance["official_rebuilt_token_jaccard"] > 0.999


def test_all_published_numeric_units_fail_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 138
    assert Counter(row["result_family"] for row in results) == {
        "main_comparison_table": 119,
        "representative_factor": 9,
        "heatmap_summary": 6,
        "runtime_claim": 4,
    }
    assert all(row["source_asset_recovered"] == "True" for row in results)
    assert all(row["raw_result_value_recovered"] == "False" for row in results)
    assert all(row["author_native_pipeline_executed"] == "False" for row in results)
    assert all(row["author_native_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    xalpha = [row for row in results if row["result_family"] == "main_comparison_table" and row["method_or_panel"] == "XAlpha"]
    assert len(xalpha) == 7
    assert all(row["rank_within_column"] == "1" for row in xalpha)


def test_empirical_figure_assets_are_rasters_without_raw_arrays() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 5
    assert sum(int(row["active_panels"]) for row in figures) == 5
    assert sum(int(row["empirical_panels"]) for row in figures) == 3
    assert all(len(row["source_asset_sha256"]) == 64 for row in figures)
    empirical = [row for row in figures if row["empirical_panels"] == "1"]
    assert len(empirical) == 3
    assert all(row["raw_result_array_recovered"] == "False" for row in empirical)
    assert all(row["author_native_regeneration"] == "False" for row in empirical)
    assert all(row["paper_result_credit"] == "False" for row in empirical)


def test_prompt_inventory_preserves_selected_excerpt_boundary() -> None:
    prompts = rows("prompt_inventory.csv")
    assert len(prompts) == 22
    assert Counter(row["category"] for row in prompts) == {
        "shared_block": 2,
        "macro_agent": 6,
        "micro_agent": 9,
        "cross_agent": 4,
        "utility": 1,
    }
    assert sum(row["category"] != "shared_block" for row in prompts) == 20
    assert all(row["paper_framework_recovered"] == "True" for row in prompts)
    assert all(row["full_runtime_template_recovered"] == "False" for row in prompts)
    assert all(row["filled_runtime_prompt_recovered"] == "False" for row in prompts)
    assert all(row["author_model_response_recovered"] == "False" for row in prompts)
    assert all("selected prompt excerpts" in row["boundary"] for row in prompts)


def test_three_paper_factor_programs_execute_with_exact_contract_boundary() -> None:
    checks = {row["check"]: row for row in rows("factor_execution_audit.csv")}
    assert set(checks) == {
        "main_overshoot_listing",
        "appendix_overshoot_listing",
        "appendix_dynamic_range_listing",
        "main_appendix_overshoot_value_equivalence",
    }
    listings = [row for key, row in checks.items() if key.endswith("listing")]
    assert all(row["paper_code_executed_verbatim"] == "True" for row in listings)
    assert all(row["output_is_series"] == "True" for row in listings)
    assert all(row["output_length"] == "240" for row in listings)
    assert all(row["index_aligned"] == "True" for row in listings)
    assert all(row["finite_output_count"] == "240" for row in listings)
    assert all(row["prefix_causality_check"] == "True" for row in listings)
    assert checks["main_overshoot_listing"]["output_name_contract_passed"] == "True"
    assert checks["appendix_overshoot_listing"]["output_name_contract_passed"] == "False"
    assert checks["appendix_dynamic_range_listing"]["output_name_contract_passed"] == "False"
    assert checks["main_appendix_overshoot_value_equivalence"]["output_name_contract_passed"] == "True"
    assert all(row["author_native_pipeline_executed"] == "False" for row in checks.values())
    assert all(row["published_metric_regenerated"] == "False" for row in checks.values())
    assert all(row["paper_result_credit"] == "False" for row in checks.values())


def test_method_ledger_separates_specified_details_from_rerun_blockers() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 15
    assert methods["prediction target"]["specification_level"] == "sufficient"
    for dimension in (
        "data universe and snapshot",
        "preprocessing",
        "LLM backend",
        "prompt programs",
        "cycle routing",
        "factor evolution",
        "selection and scoring",
        "portfolio backtest",
        "hardware and runtime",
    ):
        assert methods[dimension]["specification_level"] == "partial"
    for dimension in (
        "report-grounded memory input",
        "factor library",
        "baselines",
        "randomness and run lineage",
        "raw empirical outputs",
    ):
        assert methods[dimension]["specification_level"] == "insufficient"


def test_internal_consistency_and_release_boundaries_are_explicit() -> None:
    issues = {row["issue"]: row for row in rows("internal_consistency_audit.csv")}
    assert issues["main_table_best_claim"]["status"] == "consistent"
    assert issues["cited_prompt_repository"]["status"] == "unresolved"
    assert issues["appendix_overshoot_output_contract"]["status"] == "conflict"
    assert issues["appendix_dynamic_output_contract"]["status"] == "conflict"
    assert issues["huggingface_xalpha_ablation"]["status"] == "not_attributable_empty"
    releases = rows("release_search_audit.csv")
    cited = next(row for row in releases if row["surface"] == "cited GitHub repository")
    assert cited["observed_matches"] == "0"
    assert "status=404" in cited["observation"]
    inventory = next(row for row in releases if row["surface"] == "first-author GitHub inventory")
    assert inventory["observed_matches"] == "27"
    arxiv = next(row for row in releases if row["surface"] == "github code arxiv id")
    assert arxiv["observed_matches"] == "105"
    hf = next(row for row in releases if row["surface"] == "Hugging Face datasets")
    assert hf["observed_matches"] == "1"
    assert ".gitattributes-only" in hf["observation"]
    assert all(row["attributable_xalpha_release_found"] == "False" for row in releases)


def test_manifest_and_readme_state_the_fail_closed_result() -> None:
    manifest = load_json("manifest.json")
    assert manifest["active_numeric_result_units"] == 138
    assert manifest["main_table_result_cells"] == 119
    assert manifest["author_native_numeric_result_units_regenerated"] == 0
    assert manifest["active_empirical_figure_panels"] == 3
    assert manifest["author_native_empirical_panels_regenerated"] == 0
    assert manifest["named_agent_utility_prompt_frameworks_recovered"] == 20
    assert manifest["shared_prompt_blocks_recovered"] == 2
    assert manifest["paper_factor_programs_executed"] == 3
    assert manifest["paper_factor_programs_passing_output_name_contract"] == 1
    assert manifest["attributable_xalpha_implementation_found"] is False
    assert manifest["raw_result_arrays_recovered"] == 0
    assert manifest["strict_success"] is False
    expected = {path.name for path in AUDIT_DIR.iterdir() if path.is_file() and path.name != "manifest.json"}
    assert set(manifest["generated_file_sha256"]) == expected
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "not reproducible end to end",
        "Zero of 138 numeric units and 0/3 panels",
        "HTTP 404",
        "27 public repositories",
        "Three listings execute verbatim",
        "wrong Series name",
        "paper-derived component checks",
        "The three empirical assets are rasters only",
        "strict_success` remains false",
    ):
        assert marker in readme


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned XALPHA audit evidence is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_xalpha_paper.py"), "--output", str(tmp_path / "strict"), "--strict"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    strict = json.loads((tmp_path / "strict/manifest.json").read_text())
    assert strict["author_native_numeric_result_units_regenerated"] == 0
    assert strict["strict_success"] is False
