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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/agora"
SPEC = importlib.util.spec_from_file_location("audit_agora_paper", ROOT / "scripts/audit_agora_paper.py")
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
    assert provenance["arxiv_id"] == "2606.29194"
    assert provenance["arxiv_version"] == "v1"
    assert provenance["source_files"] == 25
    assert provenance["official_pages"] == 42
    assert provenance["rebuilt_pages"] == 42
    assert provenance["official_pages_visually_checked"] == 42
    assert provenance["rebuilt_pages_visually_checked"] == 42
    assert provenance["visual_defects_observed"] == 0
    assert provenance["official_rebuilt_token_jaccard"] > 0.999
    assert provenance["paper_contains_repository_url"] is False


def test_every_displayed_quantitative_table_cell_fails_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 293
    assert Counter(row["table_label"] for row in results) == {
        "tab:headline": 48,
        "tab:sig_summary": 14,
        "tab:libstate": 40,
        "tab:decomp": 9,
        "tab:cost_sensitivity": 20,
        "tab:multiseed": 8,
        "tab:nw_ci": 31,
        "tab:robustness": 32,
        "tab:rolling": 49,
        "tab:sigtests": 42,
    }
    assert all(row["unit_definition"] == "one populated displayed quantitative table cell" for row in results)
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["raw_result_record_recovered"] == "False" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["published_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)


def test_empirical_vector_assets_do_not_masquerade_as_raw_results() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 5
    assert sum(int(row["empirical_panels"]) for row in figures) == 4
    assert sum(int(row["empirical_series_or_groups"]) for row in figures) == 26
    empirical = [row for row in figures if row["empirical_panels"] == "1"]
    assert len(empirical) == 4
    assert all(len(row["source_asset_sha256"]) == 64 for row in figures)
    assert all(row["underlying_numeric_array_recovered"] == "False" for row in figures)
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)


def test_two_complete_paper_metric_programs_execute_with_narrow_credit() -> None:
    metrics = {row["listing"]: row for row in rows("metric_execution_audit.csv")}
    assert set(metrics) == {"monotonicity_score_v1", "excess_drawdown_penalty_v1"}
    assert all(row["paper_code_executed_verbatim"] == "True" for row in metrics.values())
    assert all(row["ast_parse_passed"] == "True" for row in metrics.values())
    assert all(row["deterministic"] == "True" for row in metrics.values())
    assert all(row["finite_and_bounded"] == "True" for row in metrics.values())
    assert all(row["direction_and_guard_checks_passed"] == "True" for row in metrics.values())
    assert all(row["small_input_value"] == "0" for row in metrics.values())
    assert float(metrics["monotonicity_score_v1"]["positive_order_value"]) > 0.99
    assert float(metrics["monotonicity_score_v1"]["negative_order_value"]) < -0.99
    assert all(row["author_native_pipeline_executed"] == "False" for row in metrics.values())
    assert all(row["published_metric_result_regenerated"] == "False" for row in metrics.values())
    assert all(row["paper_result_credit"] == "False" for row in metrics.values())


def test_method_ledger_preserves_detailed_specification_and_missing_lineage() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 17
    assert methods["official paper and source"]["status"] == "complete"
    assert methods["claimed public release"]["status"] == "claimed_but_unrecovered"
    assert methods["temporal split"]["status"] == "specified"
    assert methods["prediction target"]["status"] == "specified"
    assert methods["promoted metric programs"]["status"] == "complete_component"
    assert methods["alpha programs and pools"]["status"] == "missing"
    assert methods["exact prompts and model calls"]["status"] == "missing"
    assert methods["raw empirical outputs"]["status"] == "missing"


def test_material_paper_internal_conflicts_are_explicit() -> None:
    issues = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    for check in (
        "release_claim_tense",
        "skill_library_count",
        "agora_per_alpha_median",
        "b6_per_alpha_median",
        "positive_baseline_count",
        "holdout_observation_count",
    ):
        assert issues[check]["status"] == "conflict"
    assert issues["same_holdout_ic"]["status"] == "unexplained_difference"
    assert issues["same_holdout_sharpe"]["status"] == "unexplained_difference"
    assert issues["cost_sensitivity"]["status"] == "directional_anomaly"
    assert issues["test_segment_feedback"]["status"] == "explicit_limitation"
    assert issues["full_system_seed"]["status"] == "explicit_limitation"
    assert issues["metric_novelty"]["status"] == "appropriately_bounded"


def test_claimed_release_search_is_bounded_and_rejects_false_domain_match() -> None:
    releases = rows("release_search_audit.csv")
    exact = [row for row in releases if row["observation"].startswith("complete bounded exact")]
    assert len(exact) == 9
    assert all(row["observed_matches"] == "0" for row in exact)
    hf = [row for row in releases if row["surface"].startswith("Hugging Face")]
    assert len(hf) == 2 and all(row["observed_matches"] == "0" for row in hf)
    domain = next(row for row in releases if row["surface"] == "paper-author affiliation domain")
    assert "e-commerce" in domain["observation"]
    candidate = next(row for row in releases if row["surface"] == "GitHub repository affiliation-domain token")
    assert candidate["observed_matches"] == "1"
    assert "47-file" in candidate["observation"]
    assert "unofficial/not affiliated" in candidate["observation"]
    assert all(row["attributable_agora_release_found"] == "False" for row in releases)
    assert all(row["negative_search_boundary"] for row in releases)


def test_manifest_and_readme_state_the_fail_closed_result() -> None:
    manifest = load_json("manifest.json")
    assert manifest["active_quantitative_table_cells"] == 293
    assert manifest["result_tables"] == 10
    assert manifest["author_native_table_cells_regenerated"] == 0
    assert manifest["active_empirical_figure_panels"] == 4
    assert manifest["empirical_figure_series_or_groups"] == 26
    assert manifest["author_native_empirical_panels_regenerated"] == 0
    assert manifest["complete_paper_metric_programs_executed"] == 2
    assert manifest["paper_metric_programs_passing_controlled_checks"] == 2
    assert manifest["attributable_agora_implementation_found"] is False
    assert manifest["raw_result_arrays_recovered"] == 0
    assert manifest["strict_success"] is False
    expected = {path.name for path in AUDIT_DIR.iterdir() if path.is_file() and path.name != "manifest.json"}
    assert set(manifest["generated_file_sha256"]) == expected
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "not reproducible end to end",
        "293 displayed quantitative result cells",
        "Zero of 293 cells and 0/4 panels",
        "Neither the PDF nor TeX contains a repository URL",
        "both programs AST-parse and execute verbatim",
        "paper-derived component executions",
        "eight claimed skill libraries versus nine rows",
        "1.06 versus 2.461",
        "91 versus 60 observations",
        "costs rise from 9 to 45 bps",
        "strict_success` remains false",
    ):
        assert marker in readme


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned Agora audit evidence is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_agora_paper.py"), "--output", str(tmp_path / "strict"), "--strict"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    strict = json.loads((tmp_path / "strict/manifest.json").read_text())
    assert strict["author_native_table_cells_regenerated"] == 0
    assert strict["strict_success"] is False
