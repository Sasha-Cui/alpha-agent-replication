"""Contracts for the fail-closed LLMFactor paper/source audit."""
from __future__ import annotations

import csv
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_llmfactor_paper.py"
SPEC = importlib.util.spec_from_file_location("audit_llmfactor_paper", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)

PAPER = ROOT / "literature_review/papers/19_llmfactor_extracting_profitable_factors_through_prompts_for_explainable_stock_movement_pre.pdf"
OUTPUT = ROOT / "paper_runs/paper_replication_audits/llmfactor"


def csv_rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_original_paper_is_pinned_and_all_authoritative_pages_were_audited() -> None:
    assert audit.sha256(PAPER) == audit.EXPECTED_ARXIV_PDF_SHA256
    text, pages, _ = audit.pdf_text(PAPER)
    assert pages == 12
    normalized = " ".join(text.split())
    assert "Sequential Knowledge-Guided Prompting" in normalized
    assert "repro- ducibility of results cannot be guaranteed" in normalized
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["official_pdf_pages_audited"] == 24
    assert manifest["official_pdf_pages_visually_inspected"] == 24


def test_official_source_is_document_only_and_rebuilds_without_native_credit() -> None:
    source = csv_rows("source_file_inventory.csv")
    assert len(source) == 9
    main = next(row for row in source if row["source_member"] == "acl_latex.tex")
    assert main["sha256"] == audit.EXPECTED_SOURCE_MAIN_SHA256
    assert all(row["native_pipeline_code"] == "no" for row in source)
    assert all(row["raw_experiment_data_or_result_array"] == "no" for row in source)
    assert all(row["paper_result_credit"] == "no" for row in source)

    builds = {row["comparison_id"]: row for row in csv_rows("source_build_audit.csv")}
    assert set(builds) == {"arxiv_v1_source_rebuild", "arxiv_v1_source_to_acl_final"}
    assert float(builds["arxiv_v1_source_rebuild"]["token_multiset_jaccard"]) > .999
    assert float(builds["arxiv_v1_source_to_acl_final"]["token_multiset_jaccard"]) > .948
    assert all(row["compatibility_patch"] == "none" for row in builds.values())
    assert all(row["native_system_or_result_credit"] == "no" for row in builds.values())


def test_every_displayed_result_cell_is_counted_and_fails_closed() -> None:
    rows = csv_rows("displayed_result_conformance.csv")
    assert len(rows) == 206
    assert Counter(row["table"] for row in rows) == {"Table 2": 148, "Table 3": 22, "Table 7": 18, "Table 8": 18}
    assert Counter(row["scope"] for row in rows) == {"baseline": 124, "native_llmfactor": 82}
    assert all(row["raw_values_released"] == "no" for row in rows)
    assert all(row["native_reproduced"] == "no" for row in rows)
    assert all(row["paper_result_credit"] == "no" for row in rows)
    edt = [row for row in rows if row["table"] == "Table 2" and row["dataset"] == "EDT" and row["metric"] == "ACC"]
    assert max(float(row["displayed_value"]) for row in edt if row["scope"] == "baseline") == 75.67
    assert max(float(row["displayed_value"]) for row in edt if row["scope"] == "native_llmfactor") == 60.83


def test_prompt_renderer_executes_only_the_disclosed_skeleton() -> None:
    rendered = audit.render_english_skgp(
        "NVDA", "AMD", "news", "demand", "competitor",
        ["d1", "d2", "d3", "d4", "d5"], [1, 0, 1, 0, 1], "d6",
    )
    assert rendered["relation_prompt"] == "Please fill in the blank and return a complete sentence: NVDA and AMD are most likely in a ___ relationship."
    assert rendered["factor_prompt"].endswith("following news.\nnews")
    assert "On d1, the stock price of NVDA rose." in rendered["price_prompt"]
    assert "On d2, the stock price of NVDA fell." in rendered["price_prompt"]
    assert rendered["price_prompt"].endswith("On d6, the stock price of NVDA will ___.")
    prompts = csv_rows("prompt_component_execution.csv")
    assert len(prompts) == 3
    assert all(row["conditional_component_credit"] == "yes" for row in prompts)
    assert all(row["llm_invoked"] == "no" for row in prompts)
    assert all(row["native_pipeline_credit"] == "no" for row in prompts)
    assert all(row["paper_result_credit"] == "no" for row in prompts)
    templates = csv_rows("prompt_template_conformance.csv")
    assert len(templates) == 12
    assert all(row["exact_replay_credit"] == "no" for row in templates)


def test_published_metric_equations_pass_a_deterministic_fixture_only() -> None:
    acc, mcc = audit.accuracy_mcc(12, 3, 2, 8)
    assert acc == .8
    assert math.isclose(mcc, 90 / math.sqrt(23100))
    rows = {row["metric"]: row for row in csv_rows("metric_component_execution.csv")}
    assert set(rows) == {"ACC", "MCC"}
    assert all(row["status"] == "pass" for row in rows.values())
    assert all(row["conditional_component_credit"] == "yes" for row in rows.values())
    assert all(row["paper_result_credit"] == "no" for row in rows.values())


def test_method_and_internal_consistency_audits_expose_material_boundaries() -> None:
    methods = {row["dimension"]: row for row in csv_rows("method_specification_audit.csv")}
    assert len(methods) == 53
    assert methods["model aliases"]["assessment"] == "exact"
    assert methods["message roles"]["assessment"] == "missing"
    assert methods["stock_match expression"]["assessment"] == "conflict"
    assert methods["raw result arrays"]["severity"] == "blocking"
    assert methods["author code"]["assessment"] == "missing"

    issues = csv_rows("paper_internal_consistency_audit.csv")
    assert len(issues) == 16
    assert sum("not the rounded mean" in row["issue"] for row in issues) == 4
    assert any("EDT accuracy" in row["issue"] and "75.67" in row["evidence"] for row in issues)
    assert any("English final-template" in row["issue"] for row in issues)
    assert any("Chinese initial-template" in row["issue"] for row in issues)
    assert all(row["paper_result_credit"] == "no" for row in issues)


def test_claims_and_local_mapping_do_not_inflate_fidelity() -> None:
    claims = csv_rows("claim_audit.csv")
    assert len(claims) == 15
    assert all(row["exactly_reproduced"] == "no" for row in claims)
    assert all(row["native_paper_result_reproduced"] == "no" for row in claims)
    mappings = csv_rows("local_mapping_conformance.csv")
    assert len(mappings) == 1
    row = mappings[0]
    assert row["candidate_id"] == "paper_llmfactor_explainable_price_news"
    assert row["local_tier"] == "M0_narrative_translation"
    assert row["paper_inputs_present"] == "no"
    assert row["paper_prompt_pipeline_present"] == "no"
    assert row["paper_result_credit"] == "no"


def test_public_search_and_later_community_sources_have_zero_native_credit() -> None:
    searches = csv_rows("source_search_inventory.csv")
    assert len(searches) == 6
    assert int(searches[0]["total_count"]) == 30
    assert all(row["total_count"] == "0" for row in searches[1:])
    assert all(row["incomplete_results"] == "false" for row in searches)
    assert all(row["author_linked_repository_found"] == "no" for row in searches)

    sources = csv_rows("community_source_inventory.csv")
    assert len(sources) == 1959
    assert Counter(row["repository"] for row in sources) == {"tasoo-oos/LLMFactor": 269, "Kuon12138/SKGP": 1690}
    tasoo_py = [row for row in sources if row["repository"] == "tasoo-oos/LLMFactor" and row["path"].endswith(".py")]
    kuon_py = [row for row in sources if row["repository"] == "Kuon12138/SKGP" and row["path"].endswith(".py")]
    assert len(tasoo_py) == 39 and all(row["compile_status"] == "compiled" for row in tasoo_py)
    assert len(kuon_py) == 15
    assert Counter(row["compile_status"].split(":")[0] for row in kuon_py) == {"compiled": 14, "SyntaxError": 1}
    assert all(row["native_author_source"] == "no" for row in sources)
    assert all(row["native_paper_result_output"] == "no" for row in sources)


def test_community_data_and_method_divergences_are_explicit() -> None:
    data = {row["repository"]: row for row in csv_rows("community_data_inventory.csv")}
    tasoo = data["tasoo-oos/LLMFactor"]
    assert tasoo["tracked_csv_files"] == "220"
    assert tasoo["exact_ticker_intersection"] == "105"
    assert tasoo["scheduled_entries_t5_exact_names"] == "80655"
    assert "DDpA" in tasoo["ticker_name_mismatches"]
    assert "CTA-PB" in tasoo["ticker_name_mismatches"]
    assert all(row["native_credit"] == "no" for row in data.values())

    methods = csv_rows("community_method_conformance.csv")
    assert len(methods) == 28
    by_key = {(row["repository"], row["dimension"]): row for row in methods}
    assert by_key[("tasoo-oos/LLMFactor", "relation stage")]["assessment"] == "missing"
    assert by_key[("Kuon12138/SKGP", "window")]["assessment"] == "different"
    assert by_key[("Kuon12138/SKGP", "saved AAPL result")]["assessment"] == "target_leakage"
    assert by_key[("Kuon12138/SKGP", "saved AAPL prediction")]["assessment"] == "failed"
    assert all(row["native_credit"] == "no" for row in methods)
    assert all(row["paper_result_credit"] == "no" for row in methods)


def test_complete_community_histories_are_pinned_integral_and_fail_closed() -> None:
    summary = json.loads((OUTPUT / "community_source_history_summary.json").read_text(encoding="utf-8"))
    assert summary["total_commits"] == 20
    assert summary["total_reachable_objects"] == 452325
    assert summary["total_unique_historical_paths_by_repository"] == 474337
    assert summary["author_linked_code_or_data_found"] is False
    assert summary["native_credit"] is False
    assert summary["paper_result_credit"] is False

    histories = {row["repository"].split("github.com/")[-1]: row for row in summary["repositories"]}
    tasoo = histories["tasoo-oos/LLMFactor"]
    kuon = histories["Kuon12138/SKGP"]
    assert tasoo["root"] == audit.EXPECTED_TASOO_ROOT
    assert tasoo["head"] == audit.EXPECTED_TASOO_HEAD
    assert tasoo["commits"] == 13
    assert tasoo["reachable_object_types"] == {"blob": 100427, "commit": 13, "tree": 184}
    assert tasoo["unique_historical_paths"] == 103013
    assert tasoo["unique_historical_path_object_pairs"] == 103062
    assert kuon["root"] == audit.EXPECTED_KUON_ROOT
    assert kuon["head"] == audit.EXPECTED_KUON_HEAD
    assert kuon["commits"] == 7
    assert kuon["reachable_object_types"] == {"blob": 351214, "commit": 7, "tree": 480}
    assert kuon["unique_historical_paths"] == 371324
    assert kuon["unique_historical_path_object_pairs"] == 371725
    for row in histories.values():
        assert row["complete_non_partial_clone"] is True
        assert row["fsck_full_returncode"] == 0
        assert row["fsck_unreachable_or_dangling_findings"] == 0
        assert row["tags"] == []
        assert row["paper_author_overlap"] is False
        assert row["native_credit"] is False
        assert row["paper_result_credit"] is False

    commits = csv_rows("community_source_history_commit_inventory.csv")
    assert len(commits) == 20
    assert Counter(row["repository"] for row in commits) == {"tasoo-oos/LLMFactor": 13, "Kuon12138/SKGP": 7}
    tasoo_paths = [int(row["tracked_paths"]) for row in commits if row["repository"] == "tasoo-oos/LLMFactor"]
    kuon_paths = [int(row["tracked_paths"]) for row in commits if row["repository"] == "Kuon12138/SKGP"]
    assert tasoo_paths == [9, 12, 13, 12, 102519, 102528, 241, 241, 245, 246, 248, 263, 269]
    assert kuon_paths == [369979, 1672, 1671, 1680, 1687, 1696, 1690]
    assert all(row["native_author_source"] == "no" for row in commits)
    assert all(row["paper_result_credit"] == "no" for row in commits)


def test_historical_community_data_and_outputs_do_not_gain_paper_credit() -> None:
    data = csv_rows("community_historical_data_inventory.csv")
    assert len(data) == 4
    daily = {(row["repository"], row["dataset"]): row for row in data if row["scope"] == "historical_daily_preprocessed_news"}
    assert daily[("tasoo-oos/LLMFactor", "CMIN-US")]["path_count"] == "102175"
    assert daily[("tasoo-oos/LLMFactor", "CMIN-US")]["unique_blob_ids"] == "99994"
    assert daily[("Kuon12138/SKGP", "CMIN-US")]["path_count"] == "102175"
    assert daily[("Kuon12138/SKGP", "CMIN-CN")]["path_count"] == "266551"
    assert daily[("Kuon12138/SKGP", "CMIN-CN")]["ticker_count"] == "300"
    lineage = next(row for row in data if row["scope"] == "cross_repository_historical_dataset_lineage")
    assert lineage["path_count"] == "102505"
    assert lineage["identical_path_object_pairs"] == "102504"
    assert lineage["remaining_path_case_difference"] == "price/raw/SNAP.csv <-> price/raw/snap.csv"
    assert all(row["native_credit"] == "no" for row in data)
    assert all(row["paper_result_credit"] == "no" for row in data)

    results = csv_rows("community_historical_result_inventory.csv")
    assert len(results) == 30
    assert len({row["path"] for row in results}) == 18
    assert Counter(row["json_shape"] for row in results) == {"dict": 24, "not_json": 6}
    assert sum(row["contains_error_marker"] == "true" for row in results) == 8
    assert all(row["content_emitted"] == "no_metadata_only" for row in results)
    assert all(row["native_author_output"] == "no" for row in results)
    assert all(row["paper_result_credit"] == "no" for row in results)


def test_manifest_and_native_execution_state_the_honest_boundary() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((OUTPUT / "native_execution.json").read_text(encoding="utf-8"))
    assert manifest["overall_fidelity"] == "official_documents_and_prompt_metric_components_audited_zero_of_82_native_and_zero_of_206_total_result_cells_reproduced"
    assert manifest["displayed_result_cells"] == 206
    assert manifest["displayed_result_cells_reproduced"] == 0
    assert manifest["native_llmfactor_result_cells"] == 82
    assert manifest["native_llmfactor_result_cells_reproduced"] == 0
    assert manifest["baseline_result_cells"] == 124
    assert manifest["method_dimensions"] == 53
    assert manifest["internal_consistency_issues"] == 16
    assert manifest["author_linked_code_found"] is False
    assert manifest["paper_result_credit"] is False
    assert native["native_execution_attempted"] is False
    assert native["llm_calls_made"] == 0
    assert native["paper_result_credit"] is False

    readme = " ".join((OUTPUT / "README.md").read_text(encoding="utf-8").split())
    assert "0/82 displayed native result cells" in readme
    assert "0/206 cells" in readme
    assert "does not reproduce an LLMFactor result" in readme
