"""Contracts for the fail-closed Alpha-GPT paper/source lineage audit."""
from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_alpha_gpt_lineage.py"
SPEC = importlib.util.spec_from_file_location("audit_alpha_gpt_lineage", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)

ACL_FINAL = (
    ROOT
    / "literature_review/papers/"
    "11_alpha_gpt_human_ai_interactive_alpha_mining_for_quantitative_investment_acl_anthology.pdf"
)
ALPHA_GPT2 = (
    ROOT
    / "literature_review/papers/"
    "12_alpha_gpt_2_0_human_in_the_loop_ai_for_quantitative_investment.pdf"
)
OUTPUT = ROOT / "paper_runs/paper_replication_audits/alpha_gpt_lineage"


def csv_rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_tracked_original_papers_are_pinned_and_all_pages_were_audited() -> None:
    assert audit.sha256(ACL_FINAL) == audit.EXPECTED_ACL_FINAL_PDF_SHA256
    assert audit.sha256(ALPHA_GPT2) == audit.EXPECTED_ALPHA_GPT2_PDF_SHA256
    acl_text, acl_pages, _ = audit.pdf_text(ACL_FINAL)
    alpha_gpt2_text, alpha_gpt2_pages, _ = audit.pdf_text(ALPHA_GPT2)
    assert acl_pages == 11
    assert alpha_gpt2_pages == 4
    assert "Alpha-GPT" in acl_text
    assert "Draft. Work in progress" in " ".join(alpha_gpt2_text.split())


def test_all_official_source_members_are_inventoried_without_native_credit() -> None:
    rows = csv_rows("source_file_inventory.csv")
    assert len(rows) == 108
    assert Counter(row["archive_id"] for row in rows) == {
        "alpha_gpt_v1": 59,
        "alpha_gpt_v2": 25,
        "alpha_gpt2_v1": 24,
    }
    active_main = {
        row["archive_id"]: row
        for row in rows
        if row["source_member"] == "main.tex"
    }
    assert active_main["alpha_gpt_v1"]["sha256"] == audit.EXPECTED_ALPHA_GPT_V1_MAIN_SHA256
    assert active_main["alpha_gpt_v2"]["sha256"] == audit.EXPECTED_ALPHA_GPT_V2_MAIN_SHA256
    assert active_main["alpha_gpt2_v1"]["sha256"] == audit.EXPECTED_ALPHA_GPT2_MAIN_SHA256
    assert all(row["native_pipeline_code"] == "no" for row in rows)
    assert all(row["raw_experiment_data_or_result_array"] == "no" for row in rows)
    assert all(row["paper_result_credit"] == "no" for row in rows)


def test_source_rebuilds_are_document_evidence_not_experiment_evidence() -> None:
    rows = {row["comparison_id"]: row for row in csv_rows("source_build_audit.csv")}
    assert set(rows) == {
        "alpha_gpt_v1",
        "alpha_gpt_v2_arxiv",
        "alpha_gpt_v2_to_acl_final",
        "alpha_gpt2_v1",
    }
    assert all(row["official_pages"] == row["rebuilt_pages"] for row in rows.values())
    assert float(rows["alpha_gpt_v1"]["token_multiset_jaccard"]) > 0.999
    assert float(rows["alpha_gpt_v2_arxiv"]["token_multiset_jaccard"]) > 0.96
    assert float(rows["alpha_gpt_v2_to_acl_final"]["token_multiset_jaccard"]) > 0.91
    assert float(rows["alpha_gpt2_v1"]["token_multiset_jaccard"]) > 0.997
    assert all(row["document_credit"] == "yes" for row in rows.values())
    assert all(row["native_system_or_result_credit"] == "no" for row in rows.values())


def test_version_lineage_keeps_the_three_empirical_denominators_distinct() -> None:
    rows = {row["version"]: row for row in csv_rows("version_lineage_audit.csv")}
    assert len(rows) == 4
    assert rows["Alpha-GPT arXiv v1"]["displayed_numeric_result_cells"] == "20"
    assert rows["Alpha-GPT arXiv v1"]["plotted_result_series"] == "3"
    assert rows["Alpha-GPT arXiv v2"]["displayed_numeric_result_cells"] == "47"
    assert rows["Alpha-GPT arXiv v2"]["plotted_result_series"] == "2"
    assert rows["Alpha-GPT EMNLP 2025 final"]["displayed_numeric_result_cells"] == "47"
    assert rows["Alpha-GPT 2.0 arXiv v1"]["displayed_numeric_result_cells"] == "0"
    assert rows["Alpha-GPT 2.0 arXiv v1"]["plotted_result_series"] == "0"
    assert "Draft" in rows["Alpha-GPT 2.0 arXiv v1"]["empirical_scope"]


def test_every_displayed_result_object_is_counted_and_fails_closed() -> None:
    rows = csv_rows("displayed_result_conformance.csv")
    assert len(rows) == 78
    assert Counter(row["display_object"] for row in rows) == {
        "numeric_table_cell": 51,
        "numeric_figure_cell": 16,
        "line_series": 5,
        "qualitative_plot_panel": 6,
    }
    assert sum(row["version"] == "Alpha-GPT arXiv v1" for row in rows) == 26
    assert sum(row["version"] == "Alpha-GPT arXiv v2 / ACL final" for row in rows) == 52
    assert all(row["raw_values_released"] == "no" for row in rows)
    assert all(row["native_reproduced"] == "no" for row in rows)
    assert all(row["paper_result_credit"] == "no" for row in rows)


def test_published_formula_checks_expose_the_invalid_showcase_expression() -> None:
    rows = {row["formula_id"]: row for row in csv_rows("published_formula_conformance.csv")}
    assert len(rows) == 4
    flow = rows["AGPT-FORM-01"]
    assert flow["parse_status"] == "parsed"
    assert flow["arity_status"] == "invalid"
    assert "div expects 2 arguments but received 1" in flow["arity_errors"]
    assert "cwise_mul expects 2 arguments but received 3" in flow["arity_errors"]
    valid = [row for row in rows.values() if row["arity_status"] == "valid"]
    assert len(valid) == 3
    assert all(int(row["finite_values_on_deterministic_fixture"]) > 0 for row in valid)
    assert all(row["native_pipeline_credit"] == "no" for row in rows.values())
    assert all(row["paper_result_credit"] == "no" for row in rows.values())


def test_prompts_claims_methods_and_internal_conflicts_do_not_inflate_credit() -> None:
    prompts = csv_rows("prompt_inventory.csv")
    claims = csv_rows("claim_audit.csv")
    issues = csv_rows("paper_internal_consistency_audit.csv")
    methods = csv_rows("method_specification_audit.csv")
    assert len(prompts) == 14
    assert all(row["exact_replay_credit"] == "no" for row in prompts)
    assert len(claims) == 13
    assert all(row["exactly_reproduced"] == "no" for row in claims)
    assert all(row["native_paper_result_reproduced"] == "no" for row in claims)
    assert len(issues) == 18
    assert sum(row["severity"] == "blocking" for row in issues) == 9
    by_issue = {row["issue_id"]: row for row in issues}
    assert "one argument" in by_issue["AGPT-INT-002"]["issue"]
    assert "no experiment or result" in by_issue["AGPT-INT-013"]["issue"]
    assert len(methods) == 123
    by_dimension = {row["dimension"]: row for row in methods}
    assert by_dimension["published Flow of Funds formula arity"]["assessment"] == "conflict"
    assert by_dimension["raw result arrays"]["severity"] == "blocking"
    assert by_dimension["source-to-paper experimental scope"]["assessment"] == "conflict"


def test_public_search_and_unaffiliated_community_code_are_not_native_evidence() -> None:
    searches = csv_rows("source_search_inventory.csv")
    assert len(searches) == 10
    assert searches[0]["query"] == "Alpha-GPT in:name,description,readme"
    assert int(searches[0]["total_count"]) > 0
    assert all(row["total_count"] == "0" for row in searches[1:])
    assert all(row["incomplete_results"] == "false" for row in searches)
    assert all(row["author_linked_repository_found"] == "no" for row in searches)

    sources = csv_rows("community_source_inventory.csv")
    assert len(sources) == 41
    python_sources = [row for row in sources if row["path"].endswith(".py")]
    assert len(python_sources) == 29
    assert all(row["compile_status"] == "compiled" for row in python_sources)
    assert all(row["native_author_source"] == "no" for row in sources)
    assert all(row["native_paper_result_output"] == "no" for row in sources)
    methods = {row["dimension"]: row for row in csv_rows("community_method_conformance.csv")}
    assert methods["author linkage"]["assessment"] == "nonmatch"
    assert methods["genetic programming"]["assessment"] == "missing"
    assert methods["published results"]["assessment"] == "missing"
    assert all(row["native_credit"] == "no" for row in methods.values())


def test_local_candidates_remain_m0_researcher_translations() -> None:
    rows = {row["candidate_id"]: row for row in csv_rows("local_mapping_conformance.csv")}
    assert set(rows) == {
        "paper_alpha_gpt_interactive_formula",
        "paper_alpha_gpt2_full_pipeline",
    }
    assert {row["local_tier"] for row in rows.values()} == {"M0_narrative_translation"}
    assert all(row["paper_result_credit"] == "no" for row in rows.values())

    with (
        ROOT / "paper_runs/submission_evidence/mapping_audit/mapping_audit.csv"
    ).open(newline="", encoding="utf-8") as stream:
        mapped = [
            row
            for row in csv.DictReader(stream)
            if row["candidate_id"] in rows
        ]
    assert len(mapped) == 2
    assert {row["mapping_fidelity_tier"] for row in mapped} == {"M0_narrative_translation"}
    assert all(row["source_supports_exact_ingredients"] == "no" for row in mapped)
    assert all(row["source_supports_tested_weighting_rule"] == "no" for row in mapped)


def test_manifest_and_native_execution_state_the_honest_boundary() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((OUTPUT / "native_execution.json").read_text(encoding="utf-8"))
    assert manifest["overall_fidelity"] == (
        "three_official_documents_rebuilt_and_lineage_audited_zero_native_"
        "alpha_gpt_results_alpha_gpt2_is_unevaluated_draft"
    )
    assert manifest["official_pdf_pages_audited"] == 35
    assert manifest["official_pdf_pages_visually_inspected"] == 35
    assert manifest["official_source_members"] == 108
    assert manifest["method_dimensions"] == 123
    assert manifest["internal_consistency_issues"] == 18
    assert manifest["blocking_internal_consistency_issues"] == 9
    assert manifest["published_formula_examples_arity_valid"] == 3
    assert manifest["alpha_gpt_v1_numeric_result_cells_reproduced"] == 0
    assert manifest["alpha_gpt_final_numeric_result_cells_reproduced"] == 0
    assert manifest["alpha_gpt2_empirical_result_units"] == 0
    assert manifest["community_repository_head"] == audit.EXPECTED_COMMUNITY_HEAD
    assert manifest["author_linked_code_found"] is False
    assert manifest["paper_result_credit"] is False
    assert native["attempted"] is False
    assert native["paper_result_credit"] is False

    readme = " ".join((OUTPUT / "README.md").read_text(encoding="utf-8").split())
    assert "0/20 displayed numeric cells" in readme
    assert "0/47 displayed numeric cells" in readme
    assert "Alpha-GPT 2.0 has no empirical result denominator" in readme
    assert "do not count as native Alpha-GPT executions" in readme
