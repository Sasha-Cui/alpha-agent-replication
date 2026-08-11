"""Contracts for the fail-closed AAPM paper/source audit."""
from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_aapm_paper.py"
SPEC = importlib.util.spec_from_file_location("audit_aapm_paper", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)

V1_PAPER = ROOT / "literature_review/papers/57_aapm_large_language_model_agent_based_asset_pricing_models_v1.pdf"
V2_PAPER = ROOT / "literature_review/papers/58_empirical_asset_pricing_with_large_language_model_agents_v2.pdf"
OUTPUT = ROOT / "paper_runs/paper_replication_audits/aapm"


def csv_rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_both_official_paper_versions_are_pinned_and_visually_audited() -> None:
    assert audit.sha256(V1_PAPER) == audit.V1_PDF_SHA256
    assert audit.sha256(V2_PAPER) == audit.V2_PDF_SHA256
    _, v1_links = audit.validate_pdf(V1_PAPER, "v1")
    _, v2_links = audit.validate_pdf(V2_PAPER, "v2")
    assert any(row["uri"].rstrip("/") == audit.OFFICIAL_REPOSITORY for row in v1_links)
    assert any(row["uri"].rstrip("/") == audit.OFFICIAL_REPOSITORY for row in v2_links)
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["official_pdf_pages_audited"] == 33
    assert manifest["official_pdf_pages_visually_inspected"] == 33
    assert manifest["source_rebuild_pages_visually_inspected"] == 33


def test_official_source_is_complete_only_as_a_ten_file_component_release() -> None:
    rows = csv_rows("source_file_inventory.csv")
    assert len(rows) == 10
    assert sum(row["compile_status"] == "compiled" for row in rows) == 5
    assert Counter(row["role"] for row in rows) == {
        "implementation_source": 5, "documentation": 1, "license": 1,
        "configuration": 1, "dependency_manifest": 1, "released_metadata_only": 1,
    }
    assert all(row["author_result_output"] == "no" for row in rows)
    assert all(row["end_to_end_result_credit"] == "no" for row in rows)


def test_released_wsj_file_is_metadata_only_and_does_not_cover_v2() -> None:
    rows = {row["check"]: row for row in csv_rows("released_metadata_audit.csv")}
    assert rows["records"]["value"] == "65733"
    assert rows["minimum_date"]["value"] == "2021-10-01"
    assert rows["maximum_date"]["value"] == "2023-11-30"
    assert json.loads(rows["year_counts"]["value"]) == {"2021": 7889, "2022": 32965, "2023": 24879}
    assert rows["article_bodies"]["value"] == "0"
    assert rows["article_bodies"]["assessment"] == "missing"
    assert rows["returns_or_factors"]["value"] == "0"


def test_every_table_cell_is_counted_without_inflating_reproduction_credit() -> None:
    rows = csv_rows("displayed_result_conformance.csv")
    assert len(rows) == 276
    assert Counter(row["version"] for row in rows) == {"v1": 114, "v2": 162}
    assert Counter((row["version"], row["table"]) for row in rows) == {
        ("v1", "table:sr"): 42, ("v1", "table:ape"): 28, ("v1", "table:abl"): 44,
        ("v2", "table:sr"): 42, ("v2", "table:ape"): 28, ("v2", "table:abl"): 44,
        ("v2", "table:abl_fm"): 48,
    }
    assert all(row["author_output_available"] == "no" for row in rows)
    assert all(row["independent_end_to_end_reproduction"] == "no" for row in rows)
    assert all(row["credit_boundary"] == "paper_display_only_no_result_credit" for row in rows)


def test_version_comparison_exposes_changed_tables_and_reused_rasters() -> None:
    comparison = csv_rows("version_result_comparison.csv")
    assert len(comparison) == 114
    assert Counter(row["exact_value_match"] for row in comparison) == {"no": 112, "yes": 2}
    assert all(row["same_experiment_provenance_demonstrated"] == "no" for row in comparison)
    unchanged = {(row["table"], row["row_number"], row["metric"], row["v1_value"]) for row in comparison if row["exact_value_match"] == "yes"}
    assert unchanged == {("table:abl", "8", "avg_abs_t_alpha", "2.49"), ("table:sr", "4", "MDD_VW", "6.31")}

    figures = csv_rows("source_figure_inventory.csv")
    assert len(figures) == 16
    assert Counter(row["relationship"] for row in figures) == {"byte_identical": 15, "changed": 1}
    changed = [row["figure"] for row in figures if row["relationship"] == "changed"]
    assert changed == ["ablation_nk.png"]
    for name in ("deciles.png", "econ_preds.png", "tickers_preds.png"):
        row = next(row for row in figures if row["figure"] == name)
        assert row["relationship"] == "byte_identical"
        assert row["independent_reproduction"] == "no"


def test_every_quantitative_figure_unit_stays_at_raster_only_credit() -> None:
    rows = csv_rows("figure_series_conformance.csv")
    assert len(rows) == 54
    assert Counter(row["figure"] for row in rows) == {
        "ablation_nk.png": 2, "deciles.png": 10, "econ_preds.png": 18, "tickers_preds.png": 24,
    }
    assert Counter(row["unit_kind"] for row in rows) == {"named_series": 40, "title_scalar": 14}
    assert all(row["underlying_array_released"] == "no" for row in rows)
    assert all(row["independent_reproduction"] == "no" for row in rows)


def test_displayed_percentage_arithmetic_is_not_silently_accepted() -> None:
    rows = csv_rows("paper_improvement_claim_audit.csv")
    assert len(rows) == 49
    assert Counter(row["version"] for row in rows) == {"v1": 21, "v2": 28}
    by_key = {(row["version"], row["claim"]): row for row in rows}
    assert by_key[("v1", "GPT-4 MDD gain TP")]["rounded_numeric_match"] == "no"
    assert float(by_key[("v1", "GPT-4 MDD gain TP")]["computed_percent"]) < 0
    assert by_key[("v2", "Ours TP MDD gain")]["rounded_numeric_match"] == "no"
    assert by_key[("v2", "Ours TP MDD gain")]["semantic_issue"] == "wrong comparator"
    assert by_key[("v2", "O1 SR improvement TP")]["rounded_numeric_match"] == "no"
    assert by_key[("v2", "O1 SR improvement VW")]["rounded_numeric_match"] == "no"
    assert by_key[("v2", "Ours VW MDD underperformance")]["semantic_issue"] == "wrong comparator name"
    assert "calls a lower t-value an increase" in by_key[("v2", "Ours t-value reduction")]["semantic_issue"]


def test_method_audit_exposes_missing_hybrid_model_and_execution_defects() -> None:
    rows = {row["dimension"]: row for row in csv_rows("method_specification_audit.csv")}
    assert len(rows) == 28
    assert rows["LLM iterative refinement"]["assessment"] == "present_component"
    assert rows["v1 default LLM"]["assessment"] == "match"
    assert rows["v2 default LLM"]["assessment"] == "different"
    assert rows["manual financial factors"]["assessment"] == "missing"
    assert rows["historical factor pretraining"]["assessment"] == "missing"
    assert rows["macro note update"]["assessment"] == "implementation_bug"
    assert rows["SKIP path"]["assessment"] == "implementation_bug"
    assert rows["training entrypoint"]["assessment"] == "missing"
    assert rows["evaluation mode"]["assessment"] == "implementation_bug"
    assert rows["published outputs"]["assessment"] == "missing"
    assert all(row["end_to_end_credit"] == "no" for row in rows.values())


def test_internal_consistency_audit_names_version_and_provenance_conflicts() -> None:
    rows = csv_rows("paper_internal_consistency_audit.csv")
    assert len(rows) == 16
    by_issue = {(row["version"], row["issue"]): row for row in rows}
    assert ("v2", "split arithmetic") in by_issue
    assert ("v2", "decile test period") in by_issue
    assert ("v2", "figure provenance") in by_issue
    assert ("v2", "O1 SR percentages") in by_issue
    assert ("v1", "GPT-4 TP MDD sign") in by_issue
    assert ("both", "manual-factor model") in by_issue
    assert all(row["result_credit"] == "none" for row in rows)


def test_official_repository_and_search_snapshot_are_pinned() -> None:
    provenance = json.loads((OUTPUT / "source_provenance.json").read_text(encoding="utf-8"))
    assert provenance["paper_era_commit"] == audit.PAPER_ERA_COMMIT
    assert provenance["current_head"] == audit.CURRENT_HEAD
    assert provenance["repository_change_since_paper_era"] == ["README.md"]
    assert provenance["github_snapshot"]["license"] == "MIT"
    assert provenance["github_snapshot"]["captured_commits"] == 9
    assert provenance["github_snapshot"]["captured_forks"] == 14
    searches = csv_rows("source_search_inventory.csv")
    assert len(searches) == 4
    assert all(row["total_count"] == "0" for row in searches)
    assert all(row["incomplete_results"] == "false" for row in searches)
    assert all(row["native_result_found"] == "no" for row in searches)


def test_native_execution_and_manifest_state_the_honest_boundary() -> None:
    execution = {row["component"]: row for row in csv_rows("native_execution.csv")}
    assert execution["source syntax compile"]["status"] == "pass"
    assert execution["analysis.py entrypoint"]["status"] == "blocked_before_component"
    assert "chromadb" in execution["analysis.py entrypoint"]["detail"]
    assert execution["model.py entrypoint"]["status"] == "blocked_before_component"
    assert "wandb" in execution["model.py entrypoint"]["detail"]
    assert execution["model training"]["status"] == "not_reachable_no_entrypoint_and_inputs"
    assert execution["portfolio and pricing evaluation"]["status"] == "not_released"
    assert execution["end-to-end paper experiment"]["attempted"] == "no"

    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["author_output_result_cells_available"] == 0
    assert manifest["end_to_end_result_cells_reproduced"] == 0
    assert manifest["llm_calls_made"] == 0
    assert manifest["paper_result_credit"] == "no_result_credit_component_source_audit_only"
    assert manifest["overall_fidelity"] == "official_papers_sources_code_and_metadata_audited_zero_of_162_v2_result_cells_reproduced"
    readme = " ".join((OUTPUT / "README.md").read_text(encoding="utf-8").split())
    assert "End-to-end AAPM result cells reproduced: 0/162" in readme
    assert "component code, not an executable paper replication" in readme
    assert "adaptation, not a faithful replication" in readme
