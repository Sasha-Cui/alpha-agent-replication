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


def test_both_official_sources_are_pinned_rebuilt_and_visually_checked() -> None:
    data = manifest()
    assert data["official_versions_audited"] == ["v1", "v2"]
    assert data["current_official_version"] == "v2"
    assert data["official_pdf_and_source_recovered"] is True
    assert data["official_document_rebuild_completed"] is True
    assert data["official_pages_visually_checked"] == 149
    assert data["rebuilt_pages_visually_checked"] == 149
    assert data["official_pages_visually_checked_by_version"] == {"v1": 67, "v2": 82}
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["arxiv_id"] == "2603.23300"
    assert provenance["current_version"] == "v2"
    versions = {row["version"]: row for row in provenance["versions"]}
    assert versions["v1"]["submitted"] == "2026-03-24"
    assert versions["v1"]["pages"] == 67
    assert versions["v1"]["source_files"] == 5
    assert versions["v1"]["rebuild_extracted_token_multiset_jaccard"] > 0.993
    assert versions["v1"]["visual_qa"] == {
        "official_pages_inspected": 67,
        "rebuilt_pages_inspected": 67,
        "unreadable_clipped_or_overlapping_pages": 0,
    }
    assert versions["v2"]["submitted"] == "2026-08-11"
    assert versions["v2"]["pages"] == 82
    assert versions["v2"]["source_files"] == 4
    assert versions["v2"]["rebuild_extracted_token_multiset_jaccard"] > 0.994
    assert versions["v2"]["visual_qa"]["official_pages_inspected"] == 82
    assert versions["v2"]["visual_qa"]["rebuilt_pages_inspected"] == 82
    assert versions["v2"]["visual_qa"]["unreadable_clipped_or_overlapping_pages"] == 0
    assert versions["v2"]["visual_qa"]["maximum_different_pixel_fraction_at_72_dpi"] < 0.006


def test_all_printed_result_cells_are_inventoried_with_zero_native_credit() -> None:
    data = manifest()
    assert data["published_result_tables"] == 48
    assert data["published_result_tables_by_version"] == {"v1": 22, "v2": 26}
    assert data["published_numeric_table_cells"] == 2297
    assert data["published_numeric_table_cells_by_version"] == {
        "v1": 953,
        "v2": 1344,
    }
    assert data["native_numeric_table_cells_regenerated"] == 0
    results = rows("published_result_ledger.csv")
    assert len(results) == 2297
    by_version = Counter(row["paper_version"] for row in results)
    assert by_version == {"v1": 953, "v2": 1344}
    v1 = [row for row in results if row["paper_version"] == "v1"]
    v2 = [row for row in results if row["paper_version"] == "v2"]
    assert Counter(row["table_label"] for row in v1)["tab:long short"] == 8
    assert all(
        count == 45 for label, count in Counter(row["table_label"] for row in v1).items() if label != "tab:long short"
    )
    v2_counts = Counter(row["table_label"] for row in v2)
    assert v2_counts["tab:medium additional metrics baseline"] == 60
    assert v2_counts["tab:medium additional metrics agentic_ai"] == 60
    assert "tab:baseline 10" not in v2_counts
    assert "tab:long short" not in v2_counts
    assert sum(v2_counts.values()) == 1344
    assert all(row["author_native_pipeline_executed"] == "False" for row in results)
    assert all(row["native_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    tables = rows("table_inventory.csv")
    assert len(tables) == 48
    assert Counter(row["paper_version"] for row in tables) == {"v1": 22, "v2": 26}
    assert sum(int(row["printed_numeric_cells"]) for row in tables) == 2297
    assert all(row["native_cells_regenerated"] == "0" for row in tables)


def test_sharpe_arithmetic_preserves_four_version_specific_source_mismatches() -> None:
    arithmetic = rows("sharpe_arithmetic_audit.csv")
    assert len(arithmetic) == 723
    assert Counter(row["paper_version"] for row in arithmetic) == {"v1": 315, "v2": 408}
    failures = [row for row in arithmetic if row["rounding_interval_consistent"] == "False"]
    assert {(row["paper_version"], row["table_label"], row["method"], row["objective"]) for row in failures} == {
        ("v1", "tab:llm 10", "NLS", "MSR"),
        ("v1", "tab:finbert+llm 10", "POET", "MV"),
        ("v2", "tab2", "NW", "MV"),
        ("v2", "tab2", "NW", "MSR"),
    }
    malformed = next(
        row for row in failures if row["paper_version"] == "v1" and row["table_label"] == "tab:finbert+llm 10"
    )
    assert malformed["reported_annual_return"] == "1092.0"
    llm = next(row for row in failures if row["paper_version"] == "v1" and row["table_label"] == "tab:llm 10")
    assert float(llm["implied_return_over_sqrt_variance"]) == pytest.approx(0.46070387670987084)
    short_mv = next(row for row in failures if row["paper_version"] == "v2" and row["objective"] == "MV")
    assert float(short_mv["implied_return_over_sqrt_variance"]) == pytest.approx(0.530671010713532)
    assert manifest()["sharpe_arithmetic_mismatches"] == 4
    assert manifest()["sharpe_arithmetic_mismatches_by_version"] == {
        "v1": 2,
        "v2": 2,
    }


def test_printed_claim_checks_separate_internal_consistency_from_replication() -> None:
    all_checks = rows("internal_consistency_audit.csv")
    assert len(all_checks) == 48
    checks = {(row["paper_version"], row["check"]): row for row in all_checks}
    assert checks[("v1", "printed_sharpe_identity")]["status"] == "two_mismatches"
    assert checks[("v1", "agentic_10y_poet_mv_return")]["status"] == ("missing_decimal_typographical_error")
    assert checks[("v1", "llm_10y_nls_msr")]["status"] == ("printed_triple_conflict")
    assert checks[("v1", "agentic_5y_comparisons")]["status"] == ("claim_matches_printed_tables")
    assert "14/15 versus baseline" in checks[("v1", "agentic_5y_comparisons")]["detail"]
    assert checks[("v1", "subsequent_return_leakage_check")]["status"] == ("asserted_without_released_statistic")
    assert checks[("v1", "intersection_attribution")]["status"] == ("asserted_without_released_lineage")
    assert checks[("v1", "screen_label_direction")]["status"] == ("methodological_interpretation_boundary")
    assert checks[("v1", "causal_masking")]["status"] == ("prompt_instruction_not_model_control")
    assert checks[("v1", "theory_to_empirics")]["status"] == ("conditional_not_empirically_verified")
    assert checks[("v2", "visible_table_denominator")]["status"] == ("inactive_source_tables_excluded")
    assert checks[("v2", "medium_llm_table_maximum")]["status"] == ("claim_conflicts_with_printed_table")
    assert checks[("v2", "medium_llm_vs_baseline")]["status"] == ("claim_count_conflict")
    assert checks[("v2", "short_finbert_percentage")]["status"] == ("printed_percentage_conflict")
    assert "114.8%" in checks[("v2", "short_finbert_percentage")]["detail"]
    assert checks[("v2", "short_hybrid_vs_humans")]["status"] == ("claim_count_conflict")
    assert checks[("v2", "model_cutoff_boundary")]["status"] == ("family_cutoffs_corroborated_execution_unverified")


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
    assert len(prompts) == 6
    assert Counter(row["paper_version"] for row in prompts) == {"v1": 3, "v2": 3}
    assert all(row["exact_text_printed"] == "True" for row in prompts)
    assert all(row["all_evaluation_dates_recovered"] == "False" for row in prompts)
    assert all(row["input_cross_section_recovered"] == "False" for row in prompts)
    assert all(row["tool_implementations_recovered"] == "False" for row in prompts)
    assert all(row["author_model_request_replayable"] == "False" for row in prompts)
    assert all(row["paper_result_credit"] == "False" for row in prompts)
    comparison = json.loads((AUDIT_DIR / "prompt_version_comparison.json").read_text())
    assert comparison["all_three_bodies_verbatim_equal_across_versions"] is True
    assert comparison["v1_normalized_sha256"] == comparison["v2_normalized_sha256"]
    assert len(comparison["v1_normalized_sha256"]) == 3
    chronology = json.loads((AUDIT_DIR / "model_release_chronology.json").read_text())
    assert chronology["v1"]["first_public_date"] == "2024-12-11"
    assert chronology["v1"]["documented_knowledge_cutoff"] == "2024-08"
    assert chronology["v1"]["knowledge_cutoff_after_test_window_end"] is True
    assert chronology["v1"]["literal_model_available_during_test_windows"] is False
    assert chronology["v1"]["retrospective_data_layer_holdout_possible"] is True
    assert chronology["v1"]["retrospective_model_knowledge_holdout_established"] is False
    assert chronology["v2"]["medium"]["official_family_cutoff"] == "2021-09-01"
    assert chronology["v2"]["short"]["official_family_pretraining_data_through"] == "2023-10"
    assert chronology["v2"]["medium"]["family_cutoff_claim_corroborated"] is True
    assert chronology["v2"]["short"]["family_cutoff_claim_corroborated"] is True
    assert chronology["v2"]["exact_author_model_ids_or_snapshots_recovered"] is False
    assert chronology["v2"]["timestamped_author_requests_recovered"] is False
    assert chronology["v2"]["retrospective_model_knowledge_holdout_established"] is False


def test_method_audit_names_every_material_missing_layer() -> None:
    all_methods = rows("method_specification_audit.csv")
    assert Counter(row["paper_version"] for row in all_methods) == {"v1": 29, "v2": 35}
    methods = {(row["paper_version"], row["dimension"]): row for row in all_methods}
    assert methods[("v1", "official_document_source")]["status"] == ("complete_document_only")
    assert methods[("v2", "official_document_source")]["status"] == ("complete_document_only")
    assert methods[("v2", "linked_news_dataset")]["status"] == "exact_link_recovered"
    assert methods[("v2", "llm_s_prompt")]["status"] == "partial_one_date"
    assert methods[("v2", "llm_s_models")]["status"] == "family_cutoffs_only"
    assert methods[("v2", "annual_llm_rules")]["status"] == "one_date_only"
    assert methods[("v2", "finbert_model")]["status"] == "missing_identifier"
    assert methods[("v2", "deep_learning_estimator")]["status"] == "underspecified"
    assert methods[("v2", "additional_portfolio_metrics")]["status"] == ("definitions_only")
    assert methods[("v2", "paired_sharpe_tests")]["status"] == ("printed_p_values_only")
    for dimension in (
        "author_native_runtime",
        "llm_s_generation_parameters",
        "ensemble_signal_ledger",
        "random_seeds",
        "runtime_environment",
        "raw_results",
        "published_result_lineage",
    ):
        assert methods[("v2", dimension)]["status"] == "missing"


def test_later_independent_implementation_is_tested_but_not_promoted() -> None:
    independent = json.loads((AUDIT_DIR / "independent_implementation_audit.json").read_text())
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
    assert len(discovery) == 9
    assert {row["route"] for row in discovery} >= {
        "arxiv_v1_source",
        "arxiv_v2_source",
        "github_repository_arxiv_id_2026-08-14",
        "github_repository_exact_title_2026-08-14",
    }
    assert all(row["attributable_native_implementation_recovered"] == "False" for row in discovery)


def test_version_revision_and_figure_ledgers_capture_material_v2_changes() -> None:
    revisions = {row["dimension"]: row for row in rows("version_revision_audit.csv")}
    assert len(revisions) == 16
    assert revisions["rendered_result_tables"]["v1"] == "22"
    assert revisions["rendered_result_tables"]["v2"] == "26"
    assert "iffalse" in revisions["rendered_result_tables"]["assessment"]
    assert revisions["rendered_numeric_cells"]["v1"] == "953"
    assert revisions["rendered_numeric_cells"]["v2"] == "1344"
    assert revisions["llm_s_family"]["v1"] == "Gemini 2.0 Flash"
    assert "GPT-4o" in revisions["llm_s_family"]["v2"]
    assert revisions["author_native_experiment_release"]["v2"] == "not recovered"

    figures = rows("figure_inventory.csv")
    assert Counter(row["paper_version"] for row in figures) == {"v1": 1, "v2": 6}
    v2 = [row for row in figures if row["paper_version"] == "v2"]
    assert sum(row["source_kind"] == "embedded_tikz" for row in v2) == 5
    assert sum(row["source_kind"] == "released_png" for row in v2) == 1
    assert all(row["empirical_result_figure"] == "False" for row in figures)
    assert all(row["official_and_rebuilt_visually_checked"] == "True" for row in figures)


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
    expected = {path.name for path in AUDIT_DIR.iterdir() if path.is_file() and path.name != "manifest.json"}
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    assert data["full_end_to_end_pipeline_reproduced"] is False
    assert data["attributable_native_implementation_recovered"] is False
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "953 v1 numeric cells" in text
    assert "1,344 v2 numeric cells" in text
    assert "0/2,297 cells" in text
    assert "4,589 rows" in text
    assert "one date" in text
    assert "\\iffalse" in text
    assert "two new conflicts" in text
    assert "114.8%" in text
    assert "114 tests" in text
    normalized = " ".join(text.replace("**", "").split())
    assert "zero end-to-end empirical replication" in normalized
    assert "impossible" in text
    assert "author data/runtime/output lineage" in text
