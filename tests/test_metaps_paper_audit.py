from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/metaps"
SPEC = importlib.util.spec_from_file_location(
    "audit_metaps_paper", ROOT / "scripts/audit_metaps_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_json(name: str) -> dict:
    return json.loads((AUDIT_DIR / name).read_text())


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_original_source_rebuild_visual_audit_and_release_boundary_are_pinned() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["arxiv_id"] == "2606.22385"
    assert provenance["arxiv_version"] == "v1"
    assert provenance["source_files"] == 31
    assert provenance["official_pages"] == provenance["rebuilt_pages"] == 25
    assert provenance["official_pages_visually_checked"] == 25
    assert provenance["rebuilt_pages_visually_checked"] == 25
    assert provenance["visual_defects_observed"] == 0
    assert provenance["official_rebuilt_token_jaccard"] > 0.999
    assert provenance["paper_contains_native_implementation_url"] is False
    assert provenance["paper_contains_dataset_or_checkpoint_url"] is False
    assert provenance["attributable_metaps_implementation_found"] is False
    assert provenance["observed_license"] == "NOASSERTION"


def test_every_displayed_quantitative_table_cell_fails_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 492
    assert Counter(row["table_label"] for row in results) == {
        "tab:main_results": 72,
        "tab:input_target_ablation": 24,
        "tab:econswitch_9b_objectives": 20,
        "tab:rolling_4b_full_metrics": 90,
        "tab:direct_action_full": 14,
        "tab:main_scale_training_full_metrics": 168,
        "tab:strategy_behavior_best": 20,
        "tab:training_action_distribution": 12,
        "tab:controlled_sandbox_app": 72,
    }
    assert all(
        row["unit_definition"] == "one populated displayed quantitative table cell"
        for row in results
    )
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["raw_result_record_recovered"] == "False" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["published_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)


def test_rendered_figures_do_not_masquerade_as_raw_results() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 19
    assert sum(int(row["empirical_panels"]) for row in figures) == 20
    assert [row["figure"] for row in figures if row["empirical_panels"] == "0"] == [
        "fig:metaps_framework"
    ]
    assert all(len(row["source_asset_sha256"]) == 64 for row in figures)
    assert all(
        row["underlying_numeric_array_or_run_log_recovered"] == "False"
        for row in figures
    )
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)


def test_twelve_paper_derived_mechanics_execute_with_zero_native_credit() -> None:
    components = {row["component"]: row for row in rows("component_execution_audit.csv")}
    assert set(components) == {
        "news_impulse",
        "momentum_follow",
        "risk_reset",
        "liquidity_rebate",
        "volatility_breakout_literal",
        "size_bucket_rule",
        "ranking_score",
        "v1_target",
        "v2_score",
        "v3_score",
        "stock_return_identity",
        "sandbox_implied_initial",
    }
    assert all(row["deterministic_control_passed"] == "True" for row in components.values())
    assert all(row["paper_derived_not_author_code"] == "True" for row in components.values())
    assert all(row["author_native_pipeline_executed"] == "False" for row in components.values())
    assert all(row["published_result_regenerated"] == "False" for row in components.values())
    assert all(row["paper_result_credit"] == "False" for row in components.values())
    assert all("not author code" in row["boundary"] for row in components.values())


def test_method_ledger_preserves_specification_and_missing_lineage() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 26
    assert methods["official paper and source"]["status"] == "complete"
    assert methods["native implementation"]["status"] == "unreleased"
    assert methods["stock strategy roster"]["status"] == "names_and_compact_listings"
    assert methods["candidate ranking"]["status"] == "equation_underspecified"
    assert methods["V2 labels"]["status"] == "formula_underspecified"
    assert methods["fine tuning"]["status"] == "missing"
    assert methods["stock backtest"]["status"] == "missing"
    assert methods["sandbox environment"]["status"] == "narrative_only"
    assert methods["randomness and run lineage"]["status"] == "missing"
    assert methods["raw empirical outputs"]["status"] == "missing"


def test_material_internal_conflicts_and_consistency_are_explicit() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["volatility_breakout_listing"]["status"] == "mathematically_unreachable"
    assert checks["risk_reset_action_space"]["status"] == "conflict"
    assert checks["raw_size_modes_to_runtime_buckets"]["status"] == "missing_mapping"
    assert checks["compact_listing_helpers"]["status"] == "unreleased_dependencies"
    assert checks["small_cap_breakout_window"]["status"] == "ambiguous"
    assert checks["stock_return_final_value"]["status"] == "rounding_consistent"
    assert checks["sandbox_return_final_equity"]["status"] == (
        "internally_consistent_undisclosed_initial"
    )
    assert checks["decision_count"]["status"] == "consistent"
    assert checks["SFT_action_totals"]["status"] == "consistent"
    assert checks["empirical_asset_lineage"]["status"] == "static_only"


def test_release_search_is_bounded_and_finds_no_attributable_release() -> None:
    releases = rows("release_search_audit.csv")
    zero = [row for row in releases if row["observation"].startswith("complete bounded exact")]
    assert len(zero) == 6 and all(row["observed_matches"] == "0" for row in zero)
    hf = [row for row in releases if row["surface"].startswith("Hugging Face")]
    assert len(hf) == 2 and all(row["observed_matches"] == "0" for row in hf)
    assert all(row["attributable_metaps_release_found"] == "False" for row in releases)
    assert all(row["negative_search_boundary"] for row in releases)


def test_manifest_hashes_and_readme_state_the_fail_closed_result() -> None:
    manifest = load_json("manifest.json")
    assert manifest["active_quantitative_table_cells"] == 492
    assert manifest["result_tables"] == 9
    assert manifest["author_native_table_cells_regenerated"] == 0
    assert manifest["active_empirical_figure_panels"] == 20
    assert manifest["author_native_empirical_panels_regenerated"] == 0
    assert manifest["paper_derived_components_executed"] == 12
    assert manifest["paper_derived_components_passing_controlled_checks"] == 12
    assert manifest["attributable_metaps_implementation_found"] is False
    assert manifest["raw_result_arrays_recovered"] == 0
    assert manifest["full_end_to_end_pipeline_reproduced"] is False
    assert manifest["strict_success"] is False
    expected = {
        path.name: file_sha256(path)
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert manifest["generated_file_sha256"] == expected
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "paper-derived component replication, not an end-to-end MetaPS replication",
        "492 displayed result cells across nine empirical tables",
        "Zero of 492 cells and 0/20 empirical panels",
        "Twelve controlled paper-derived mechanics execute",
        "mathematically unreachable",
        "undisclosed initial equity near 8654.47",
        "strict_success` remains false",
    ):
        assert marker in readme


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned MetaPS audit evidence is only available on Bouchet")
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
            str(ROOT / "scripts/audit_metaps_paper.py"),
            "--output",
            str(tmp_path / "strict"),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    strict = json.loads((tmp_path / "strict/manifest.json").read_text())
    assert strict["author_native_table_cells_regenerated"] == 0
    assert strict["strict_success"] is False
