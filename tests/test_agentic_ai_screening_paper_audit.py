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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/agentic_ai_screening"
SPEC = importlib.util.spec_from_file_location(
    "audit_agentic_ai_screening_paper",
    ROOT / "scripts/audit_agentic_ai_screening_paper.py",
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_official_v1_source_is_pinned_rebuilt_and_visually_checked() -> None:
    data = manifest()
    assert data["official_versions_audited"] == ["v1"]
    assert data["official_pdf_and_source_recovered"] is True
    assert data["official_document_rebuild_completed"] is True
    assert data["official_pages_visually_checked"] == 67
    assert data["rebuilt_pages_visually_checked"] == 67
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    arxiv = provenance["arxiv"]
    assert arxiv["id"] == "2603.23300"
    assert arxiv["version"] == "v1"
    assert arxiv["submitted"] == "2026-03-24"
    assert arxiv["pages"] == 67
    assert arxiv["source_files"] == 5
    assert arxiv["rebuild_extracted_token_multiset_jaccard"] > 0.993
    assert arxiv["visual_qa"] == {
        "official_pages_inspected": 67,
        "rebuilt_pages_inspected": 67,
        "unreadable_clipped_or_overlapping_pages": 0,
    }


def test_all_printed_result_cells_are_inventoried_with_zero_native_credit() -> None:
    data = manifest()
    assert data["published_result_tables"] == 22
    assert data["published_numeric_table_cells"] == 953
    assert data["native_numeric_table_cells_regenerated"] == 0
    results = rows("published_result_ledger.csv")
    assert len(results) == 953
    assert Counter(row["table_label"] for row in results)["tab:long short"] == 8
    assert all(
        count == 45
        for label, count in Counter(row["table_label"] for row in results).items()
        if label != "tab:long short"
    )
    assert all(row["author_native_pipeline_executed"] == "False" for row in results)
    assert all(row["native_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    tables = rows("table_inventory.csv")
    assert len(tables) == 22
    assert sum(int(row["printed_numeric_cells"]) for row in tables) == 953
    assert all(row["native_cells_regenerated"] == "0" for row in tables)


def test_sharpe_arithmetic_preserves_two_source_mismatches() -> None:
    arithmetic = rows("sharpe_arithmetic_audit.csv")
    assert len(arithmetic) == 315
    failures = [row for row in arithmetic if row["within_0_002_tolerance"] == "False"]
    assert {
        (row["table_label"], row["method"], row["objective"])
        for row in failures
    } == {
        ("tab:llm 10", "NLS", "MSR"),
        ("tab:finbert+llm 10", "POET", "MV"),
    }
    malformed = next(
        row
        for row in failures
        if row["table_label"] == "tab:finbert+llm 10"
    )
    assert malformed["reported_annual_return"] == "1092.0"
    llm = next(row for row in failures if row["table_label"] == "tab:llm 10")
    assert float(llm["implied_return_over_sqrt_variance"]) == pytest.approx(
        0.46070387670987084
    )
    assert manifest()["sharpe_arithmetic_mismatches"] == 2


def test_printed_claim_checks_separate_internal_consistency_from_replication() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert len(checks) == 16
    assert checks["printed_sharpe_identity"]["status"] == "two_mismatches"
    assert checks["agentic_10y_poet_mv_return"]["status"] == (
        "missing_decimal_typographical_error"
    )
    assert checks["llm_10y_nls_msr"]["status"] == "printed_triple_conflict"
    assert checks["agentic_5y_comparisons"]["status"] == (
        "claim_matches_printed_tables"
    )
    assert "14/15 versus baseline" in checks["agentic_5y_comparisons"]["detail"]
    assert checks["subsequent_return_leakage_check"]["status"] == (
        "asserted_without_released_statistic"
    )
    assert checks["intersection_attribution"]["status"] == (
        "asserted_without_released_lineage"
    )
    assert checks["screen_label_direction"]["status"] == (
        "methodological_interpretation_boundary"
    )
    assert checks["causal_masking"]["status"] == (
        "prompt_instruction_not_model_control"
    )
    assert checks["theory_to_empirics"]["status"] == (
        "conditional_not_empirically_verified"
    )


def test_linked_news_revision_is_an_exact_input_component_not_results() -> None:
    news = json.loads((AUDIT_DIR / "linked_news_dataset_audit.json").read_text())
    assert news["revision"] == "d3e37035640bc90830ee8741dfa52815b719a26a"
    assert news["rows"] == news["unique_ids"] == 4589
    assert news["unique_symbols"] == 469
    assert news["minimum_publish_date"] == "2006-12-04"
    assert news["maximum_publish_date"] == "2024-04-20"
    assert news["rows_2015_through_2024_04"] == 3768
    assert news["rows_2020_through_2024_04"] == 2621
    assert sum(news["rows_by_year"].values()) == 4589
    assert news["exact_linked_input_recovered"] is True
    assert news["finbert_model_identifier_recovered"] is False
    assert news["paper_sentiment_scores_or_signals_recovered"] is False
    assert news["paper_result_credit"] is False


def test_prompt_and_model_chronology_boundaries_fail_closed() -> None:
    prompts = rows("prompt_component_inventory.csv")
    assert len(prompts) == 3
    assert all(row["exact_text_printed"] == "True" for row in prompts)
    assert all(row["all_evaluation_dates_recovered"] == "False" for row in prompts)
    assert all(row["input_cross_section_recovered"] == "False" for row in prompts)
    assert all(row["tool_implementations_recovered"] == "False" for row in prompts)
    assert all(row["author_model_request_replayable"] == "False" for row in prompts)
    assert all(row["paper_result_credit"] == "False" for row in prompts)
    chronology = json.loads((AUDIT_DIR / "model_release_chronology.json").read_text())
    assert chronology["gemini_2_0_flash_first_public_date"] == "2024-12-11"
    assert chronology["documented_knowledge_cutoff"] == "2024-08"
    assert chronology["knowledge_cutoff_after_test_window_end"] is True
    assert chronology["literal_model_available_during_test_windows"] is False
    assert chronology["retrospective_data_layer_holdout_possible"] is True
    assert chronology["retrospective_model_knowledge_holdout_established"] is False
    assert chronology["timestamped_requests_and_exact_model_revision_recovered"] is False


def test_method_audit_names_every_material_missing_layer() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 29
    assert methods["official_document_source"]["status"] == "complete_document_only"
    assert methods["linked_news_dataset"]["status"] == "exact_link_recovered"
    assert methods["llm_s_prompt"]["status"] == "partial_one_date"
    assert methods["annual_llm_rules"]["status"] == "one_of_required_years"
    assert methods["finbert_model"]["status"] == "missing_identifier"
    assert methods["deep_learning_estimator"]["status"] == "underspecified"
    for dimension in (
        "author_native_runtime",
        "llm_s_generation_parameters",
        "ensemble_signal_ledger",
        "random_seeds",
        "runtime_environment",
        "raw_results",
        "published_result_lineage",
    ):
        assert methods[dimension]["status"] == "missing"


def test_later_independent_implementation_is_tested_but_not_promoted() -> None:
    independent = json.loads(
        (AUDIT_DIR / "independent_implementation_audit.json").read_text()
    )
    assert independent["repository"] == "alanhsieh2000/agentic_portfolio"
    assert independent["repository_created"] == "2026-08-05"
    assert independent["paper_submitted"] == "2026-03-24"
    assert independent["classification"] == "unaffiliated_post_paper_interpretation"
    assert independent["author_attribution_evidence_recovered"] is False
    assert independent["isolated_test_suite"] == "114 passed"
    assert independent["internal_component_execution_credit"] is True
    assert independent["author_native_execution_credit"] is False
    assert independent["paper_result_credit"] is False
    assert independent["published_result_cells_regenerated"] == 0
    assert len(independent["material_divergences"]) == 7
    discovery = rows("discovery_evidence.csv")
    assert len(discovery) == 6
    assert all(
        row["attributable_native_implementation_recovered"] == "False"
        for row in discovery
    )


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned Agentic AI primary-source scratch is only available on Bouchet")
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
            str(ROOT / "scripts/audit_agentic_ai_screening_paper.py"),
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


def test_manifest_hashes_every_output_and_readme_states_honest_boundary() -> None:
    data = manifest()
    expected = {
        path.name
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    assert data["full_end_to_end_pipeline_reproduced"] is False
    assert data["attributable_native_implementation_recovered"] is False
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "953 printed numeric result cells" in text
    assert "0/953 native result credit" in text
    assert "4,589 rows" in text
    assert "one date" in text
    assert "313/315" in text
    assert "114 tests" in text
    assert "zero end-to-end empirical replication" in text
    assert "impossible without author data/runtime/output lineage" in text
