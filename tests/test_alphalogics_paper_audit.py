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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/alphalogics"
SPEC = importlib.util.spec_from_file_location(
    "audit_alphalogics_paper", ROOT / "scripts/audit_alphalogics_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text())


def test_original_source_rebuild_and_visual_qa_are_pinned() -> None:
    data = manifest()
    assert data["official_pdf_recovered"] is True
    assert data["official_source_recovered"] is True
    assert data["unmodified_source_rebuild_completed"] is True
    assert data["official_pages_visually_checked"] == 19
    assert data["rebuilt_pages_visually_checked"] == 19
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    arxiv = provenance["arxiv"]
    assert arxiv["identifier"] == "2603.20247"
    assert arxiv["version"] == "v1"
    assert arxiv["source_files"] == 10
    assert arxiv["official_pdf_sha256"] == audit.PINS["discovery/tracked.pdf"]
    rebuild = provenance["rebuild"]
    assert rebuild["text_comparison"]["multiset_jaccard"] > 0.999
    assert rebuild["visual_qa"][
        "unreadable_clipped_overlapping_blank_or_missing_research_pages"
    ] == 0
    assert len(rebuild["visual_qa"]["contact_sheet_sha256"]) == 6


def test_all_exact_table_units_fail_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 158
    assert Counter(row["table"] for row in results) == audit.TABLE_EXPECTED
    assert all(row["source_tex_recovered"] == "True" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["published_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    values = {(row["table"], row["row"], row["metric"]): row["printed_value"] for row in results}
    assert values[("main_results", "AlphaLogics", "csi500_ir")] == "1.5266"
    assert values[("main_results", "AlphaLogics", "sp500_ir")] == "1.2658"
    assert values[("hypothesis_accuracy", "Alpha191", "mathematical_explanation")] == "94.9"
    assert manifest()["native_numeric_table_units_regenerated"] == 0


def test_all_empirical_figure_markers_fail_closed() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 5
    assert sum(int(row["display_panels"]) for row in figures) == 20
    assert sum(int(row["empirical_panels"]) for row in figures) == 18
    assert sum(int(row["displayed_result_markers"]) for row in figures) == 204
    assert all(row["underlying_numeric_array_recovered"] == "False" for row in figures)
    markers = rows("figure_marker_ledger.csv")
    assert len(markers) == 204
    assert Counter(row["figure"] for row in markers) == {
        "figure_3_constraint_ablation": 60,
        "figure_4_logic_evolution": 120,
        "figure_5_library_size": 24,
    }
    assert all(row["exact_numeric_value_printed"] == "False" for row in markers)
    assert all(row["published_marker_regenerated"] == "False" for row in markers)
    assert all(row["paper_result_credit"] == "False" for row in markers)


def test_prompt_and_dsl_specification_is_recovered_without_runtime_credit() -> None:
    prompts = rows("prompt_template_ledger.csv")
    assert len(prompts) == 8
    assert [row["agent"] for row in prompts] == [
        "FormulaStructureAgent",
        "FinancialSemanticsMappingAgent",
        "MarketLogicAbstractionAgent",
        "LogicToFinanceConstraintAgent",
        "FactorExpressionGeneratorAgent",
        "FactorPerformanceFeedbackAgent",
        "MarketLogicGeneratorAgent",
        "MarketLogicRefinementDirectionAgent",
    ]
    assert all(row["valid_json"] == "True" for row in prompts)
    assert all(row["filled_runtime_request_recovered"] == "False" for row in prompts)
    assert all(row["filled_runtime_response_recovered"] == "False" for row in prompts)
    operations = rows("dsl_operation_ledger.csv")
    assert len(operations) == 59
    assert len({row["printed_signature"] for row in operations}) == 59
    assert all(row["source_specification_recovered"] == "True" for row in operations)
    assert all(row["author_native_implementation_recovered"] == "False" for row in operations)


def test_paper_derived_algorithm_checks_expose_control_flow_boundaries() -> None:
    algorithms = json.loads((AUDIT_DIR / "algorithm_conformance.json").read_text())
    assert algorithms["source_algorithms"] == ["inner-loop", "outer-loop"]
    assert algorithms["paper_derived_not_author_native"] is True
    inner = algorithms["inner_loop_scripted_check"]
    assert inner["best"] == 1.2
    assert inner["iterations"] == 6
    assert inner["trace"][-1]["no_improvement"] == 3
    assert inner["trace"][-1]["feedback_called"] is False
    outer = algorithms["outer_loop_scripted_check"]
    assert outer["attempts"] == 5
    assert len(outer["generated"]) == 6
    assert len(outer["evaluated"]) == 5
    assert outer["unevaluated_generated_logics"] == ["logic_5"]
    assert algorithms["published_result_credit"] is False


def test_material_specification_ambiguities_and_conflicts_are_explicit() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["agent_prompts"]["status"] == "template_complete_runtime_missing"
    assert methods["logic_schema"]["status"] == "example_only"
    assert methods["objective"]["status"] == "underspecified"
    assert methods["portfolio"]["status"] == "misdescribed_and_incomplete"
    assert methods["published_tables"]["status"] == "not_regenerated"
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["math_consistency_prose"]["status"] == "literal_contradiction"
    assert "94.9" in checks["math_consistency_prose"]["detail"]
    assert checks["mdd_sign"]["status"] == "definition_table_conflict"
    assert checks["portfolio_term"]["status"] == "qlib_semantics_conflict"
    assert checks["outer_loop_final_generation"]["status"] == "unevaluated_candidate"
    assert checks["dsl_aliases"]["status"] == "undefined_aliases"


def test_all_post_paper_candidates_are_independent_components_only() -> None:
    release = json.loads((AUDIT_DIR / "candidate_release_audit.json").read_text())
    assert release["native_paper_credit"] is False
    assert release["paper_author_identity_matches"] == 0
    candidates = {item["repository"]: item for item in release["candidates"]}
    assert set(candidates) == {
        "sjkncs/alphalogics-reproduction",
        "kaihenglin/ai-factor-mining",
        "sn0wfree/QuantNodes",
    }
    assert "Gaussian" in candidates["sjkncs/alphalogics-reproduction"]["paper_mismatch"]
    assert "two syntax errors" in candidates["kaihenglin/ai-factor-mining"]["execution"]
    assert "52 focused tests passed" in candidates["sn0wfree/QuantNodes"]["execution"]
    assert "IR is copied into best_ic" in candidates["sn0wfree/QuantNodes"]["paper_mismatch"]
    assert all(item["native_paper_credit"] is False for item in candidates.values())
    assert "private, deleted" in release["bounded_negative_inference"]


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned AlphaLogics audit evidence is only available on Bouchet")
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
            str(ROOT / "scripts/audit_alphalogics_paper.py"),
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
    assert strict["full_end_to_end_pipeline_reproduced"] is False
    assert strict["strict_success"] is False


def test_manifest_hashes_every_output_and_readme_is_honest() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    assert data["attributable_alphalogics_code_recovered"] is False
    assert data["independent_candidates_with_native_credit"] == 0
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "All 19 official and all 19 rebuilt pages",
        "eight active JSON agent templates",
        "59 explicit DSL operation signatures",
        "0/158 table units",
        "0/204 figure markers",
        "0/18 empirical panels",
        "52 focused tests",
        "zero native-paper and zero published-result credit",
        "not a true empirical replication",
    ):
        assert marker in readme
