from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from alpha_evolve import factormad_paper_components as component


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/factormad"
SPEC = importlib.util.spec_from_file_location(
    "audit_factormad_paper", ROOT / "scripts/audit_factormad_paper.py"
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


def test_original_acm_paper_and_author_lineage_are_pinned() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["doi"] == "10.1145/3768292.3770377"
    assert provenance["official_pdf_pages"] == 9
    assert provenance["official_pages_visually_checked"] == 9
    assert provenance["document_layout_defects_observed"] == 0
    assert provenance["paper_source_archive_found"] is False
    assert provenance["paper_contains_native_implementation_url"] is False
    assert provenance["paper_contains_reproducibility_statement"] is False
    assert provenance["attributable_implementation_found"] is False
    assert provenance["official_first_author_dissertation_summary_recovered"] is True
    assert provenance["official_first_author_dissertation_full_text_recovered"] is False


def test_all_30_table_cells_and_eight_empirical_panels_fail_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 30
    assert {row["method"] for row in results} == {
        "GP", "DSO", "AlphaGen", "CoE", "FactorMAD"
    }
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["raw_result_record_recovered"] == "False" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    figures = rows("figure_inventory.csv")
    assert len(figures) == 6
    assert sum(int(row["empirical_panels"]) for row in figures) == 8
    assert all(row["underlying_numeric_array_or_run_log_recovered"] == "False" for row in figures)


def test_six_mechanics_and_seven_underspecified_operations() -> None:
    checks = {row["component"]: row for row in rows("component_execution_audit.csv")}
    assert len(checks) == 13
    assert all(row["deterministic_control_passed"] == "True" for row in checks.values())
    assert all(row["paper_derived_not_author_code"] == "True" for row in checks.values())
    assert all(row["author_native_pipeline_executed"] == "False" for row in checks.values())
    for name in (
        "agent_initialization",
        "factor_code_validation",
        "factor_code_correction",
        "prediction_model_training",
        "overlapping_topk_portfolios",
        "investment_metrics",
        "llm_request",
    ):
        assert "not author code" in checks[name]["boundary"]


def test_printed_mechanics_and_fail_closed_boundaries() -> None:
    assert component.future_vwap_return([100, 110, 121], time_index=0, horizon=1) == pytest.approx(0.1)
    assert [component.proposing_agent_index(index) for index in range(4)] == [0, 1, 0, 1]
    assert component.equal_weight_top_k([1, 3, 2], 2) == [0.0, 0.5, 0.5]
    with pytest.raises(component.UnderspecifiedPaperMechanic):
        component.equal_weight_top_k([1, 2, 2], 1)
    with pytest.raises(component.UnderspecifiedPaperMechanic):
        component.initialize_agents()
    with pytest.raises(component.UnderspecifiedPaperMechanic):
        component.validate_factor_code()
    with pytest.raises(component.UnderspecifiedPaperMechanic):
        component.combine_overlapping_top_k_portfolios()
    with pytest.raises(component.UnderspecifiedPaperMechanic):
        component.reproduce_llm_request({})


def test_missing_public_artifacts_and_method_boundaries_are_explicit() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 32
    assert methods["native implementation"]["status"] == "unreleased"
    assert methods["initial factor library"]["status"] == "missing"
    assert methods["factor and seed prompts"]["status"] == "missing"
    assert methods["code validator"]["status"] == "prose_only"
    assert methods["prediction models"]["status"] == "partial"
    assert methods["overlapping holdings"]["status"] == "missing"
    assert methods["raw empirical outputs"]["status"] == "missing"
    releases = rows("release_search_audit.csv")
    assert len(releases) == 8
    assert all(row["attributable_release_found"] == "False" for row in releases)
    assert all(row["negative_search_boundary"] for row in releases)


def test_claim_conflicts_and_local_proxy_boundary_are_not_hidden() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["highest_performance_claim"]["status"] == "direct_numeric_conflict"
    assert "1.860" in checks["highest_performance_claim"]["evidence"]
    assert "1.341" in checks["highest_performance_claim"]["evidence"]
    assert checks["rank_normalization_auc_labels"]["status"] == "definition_conflict"
    assert checks["annual_return_definition"]["status"] == "metric_conflict"
    assert checks["daily_topk_ten_day_hold"]["status"] == "algorithm_underspecified"
    proxy = rows("local_proxy_boundary.csv")[0]
    assert proxy["local_candidate"] == "paper_factormad_debate_interpretable"
    assert proxy["paper_method_present"] == "False"
    assert proxy["paper_result_credit"] == "False"
    assert proxy["classification"] == "M0_narrative_translation_in_spirit_only"


def test_manifest_hashes_readme_and_strict_mode_fail_closed(tmp_path: Path) -> None:
    manifest = load_json("manifest.json")
    assert manifest["active_empirical_table_cells"] == 30
    assert manifest["author_native_table_cells_regenerated"] == 0
    assert manifest["empirical_figure_panels"] == 8
    assert manifest["author_native_empirical_panels_regenerated"] == 0
    assert manifest["paper_derived_components_executed"] == 13
    assert manifest["fail_closed_underspecified_core_operations"] == 7
    assert manifest["local_m0_proxy_receives_paper_credit"] is False
    assert manifest["strict_success"] is False
    assert manifest["generated_file_sha256"] == {
        path.name: file_sha256(path)
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "not an end-to-end replication",
        "30 displayed empirical table cells",
        "eight empirical panels",
        "Zero of 30 cells and zero of eight panels",
        "5,255 Shanghai/Shenzhen A-share stocks",
        "1.860 versus FactorMAD's 1.341",
        "M0 in-spirit narrative translation",
        "strict_success` is false",
    ):
        assert marker in readme

    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned evidence is only available on Bouchet")
    first, second = tmp_path / "first", tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_factormad_paper.py"),
         "--output", str(tmp_path / "strict"), "--strict"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 1
