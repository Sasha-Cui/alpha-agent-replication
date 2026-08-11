"""Contract tests for the fail-closed AlphaAgents paper/source audit."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_alphaagents_paper.py"
SPEC = importlib.util.spec_from_file_location("audit_alphaagents_paper", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)

PAPER = (
    ROOT
    / "literature_review/papers/"
    "36_alphaagents_large_language_model_based_multi_agents_for_equity_portfolio_constructions.pdf"
)
OUTPUT = ROOT / "paper_runs/paper_replication_audits/alphaagents"


def csv_rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_official_pdf_is_pinned_and_all_nine_pages_are_audited() -> None:
    assert audit.sha256(PAPER) == audit.EXPECTED_PDF_SHA256
    text, pages, metadata = audit.pdf_text(PAPER)
    audit.validate_pdf(text, pages)
    assert pages == 9
    assert "AlphaAgents" in str(metadata["/Title"])


def test_official_source_inventory_and_document_rebuild_are_separate_from_results() -> None:
    rows = csv_rows("source_file_inventory.csv")
    assert len(rows) == 17
    by_name = {row["source_member"]: row for row in rows}
    assert by_name["sample-authordraft.tex"]["sha256"] == audit.EXPECTED_TEX_SHA256
    assert by_name["sample-authordraft.tex"]["role"] == "paper_source"
    assert sum(row["role"] == "raster_figure_or_screenshot" for row in rows) == 13
    assert all(row["contains_machine_readable_experimental_values"] == "no" for row in rows)

    build = json.loads((OUTPUT / "source_build_audit.json").read_text(encoding="utf-8"))
    assert build["source_document_rebuild_succeeded"] is True
    assert build["official_pages"] == build["rebuilt_pages"] == 9
    assert build["token_multiset_jaccard"] > 0.997
    assert build["active_duplicate_labels"] == {
        "fig:enter-label": 3,
        "fig:risk-neutral-sharpe": 2,
    }
    assert build["document_rebuild_credit"] is True
    assert build["experimental_reproduction_credit"] is False


def test_seven_source_only_portfolios_recover_77_memberships_without_native_credit() -> None:
    rows = csv_rows("source_only_portfolio_inventory.csv")
    assert len(rows) == 7
    assert sum(int(row["ticker_count"]) for row in rows) == 77
    by_key = {(row["risk_profile"], row["portfolio"]): row for row in rows}
    assert by_key[("all", "benchmark")]["tickers_in_source_order"].split("|") == list(audit.BENCHMARK)
    assert by_key[("risk-neutral", "fundamental")]["ticker_count"] == "14"
    assert "SNOW" not in by_key[("risk-neutral", "fundamental")]["tickers_in_source_order"].split("|")
    assert by_key[("risk-averse", "fundamental")]["tickers_in_source_order"] == "CDNS|NOW|ADBE|ADSK"
    assert all(row["specification_credit"] == "source_only" for row in rows)
    assert all(row["native_agent_output_credit"] == "no" for row in rows)
    assert all(row["performance_result_credit"] == "no" for row in rows)


def test_all_20_plotted_performance_series_remain_unreproduced() -> None:
    rows = csv_rows("plotted_result_series_conformance.csv")
    assert len(rows) == 20
    assert {row["figure"] for row in rows} == {"Figure 6", "Figure 7", "Figure 8"}
    assert sum(row["metric"] == "cumulative return" for row in rows) == 13
    assert sum(row["metric"] == "rolling Sharpe" for row in rows) == 7
    assert all(row["raw_values_released"] == "no" for row in rows)
    assert all(row["native_reproduction_status"] == "not_reproduced_raster_line_only" for row in rows)
    assert all(row["paper_result_credit"] == "no" for row in rows)


def test_prompt_claim_and_consistency_audits_fail_closed() -> None:
    prompts = csv_rows("prompt_inventory.csv")
    claims = csv_rows("quantitative_and_qualitative_claim_audit.csv")
    issues = csv_rows("paper_internal_consistency_audit.csv")

    assert len(prompts) == 10
    assert sum(row["recovery_status"] == "recovered" for row in prompts) == 7
    assert sum(row["recovery_status"] == "missing" for row in prompts) == 3
    assert all(row["native_runtime_message_recovered"] == "no" for row in prompts)
    assert len(claims) == 10
    assert all(row["paper_result_credit"] == "no" for row in claims)

    by_id = {row["issue_id"]: row for row in issues}
    assert len(issues) == 9
    assert sum(row["severity"] == "blocking" for row in issues) == 5
    for identifier in (
        "ALPHAAGENTS-INT-001",
        "ALPHAAGENTS-INT-002",
        "ALPHAAGENTS-INT-003",
        "ALPHAAGENTS-INT-004",
        "ALPHAAGENTS-INT-005",
    ):
        assert by_id[identifier]["replication_effect"] == "prevents_exact_native_reconstruction"


def test_method_audit_records_source_improvements_and_native_blockers() -> None:
    rows = csv_rows("method_specification_audit.csv")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["assessment"]] = counts.get(row["assessment"], 0) + 1
    assert len(rows) == 89
    assert counts == {"specified": 30, "missing": 40, "partial": 17, "conflict": 2}
    by_dimension = {row["dimension"]: row for row in rows}
    assert by_dimension["authoritative TeX source"]["assessment"] == "specified"
    assert by_dimension["stock identities"]["assessment"] == "specified"
    assert by_dimension["risk-neutral prompt"]["severity"] == "blocking"
    assert by_dimension["rolling window length"]["assessment"] == "missing"
    assert by_dimension["performance plot values"]["severity"] == "blocking"
    assert by_dimension["local proxy relation"]["assessment"] == "partial"


def test_five_unaffiliated_reimplementations_never_become_native_evidence() -> None:
    rows = csv_rows("community_reimplementation_inventory.csv")
    assert len(rows) == 5
    assert {row["repository"] for row in rows} == audit.EXPECTED_COMMUNITY_REPOSITORIES
    assert all(row["author_linked"] == "no" for row in rows)
    assert all(row["native_paper_pipeline"] == "no" for row in rows)
    assert all(row["paper_result_series_reproduced"] == "0" for row in rows)
    assert all(row["paper_result_credit"] == "no" for row in rows)

    searches = csv_rows("source_search_inventory.csv")
    assert len(searches) == 7
    assert all(row["incomplete_results"] == "false" for row in searches)
    assert all(row["author_linked_repository_found"] == "no" for row in searches)


def test_manifest_and_native_execution_state_the_exact_evidence_boundary() -> None:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((OUTPUT / "native_execution.json").read_text(encoding="utf-8"))
    assert manifest["overall_fidelity"] == (
        "source_document_rebuilt_and_7_portfolios_recovered_but_zero_of_20_"
        "plotted_performance_series_reproduced_no_native_agent_pipeline"
    )
    assert manifest["source_document_rebuild_succeeded"] is True
    assert manifest["source_only_portfolios_recovered"] == 7
    assert manifest["source_only_ticker_memberships_recovered"] == 77
    assert manifest["plotted_performance_series_reproduced"] == 0
    assert manifest["author_linked_code_found"] is False
    assert native["attempted"] is False
    assert native["paper_result_credit"] is False
    assert native["local_proxy_status"] == "M0_narrative_translation_only"


def test_existing_local_candidates_remain_m0_narrative_translations() -> None:
    with (
        ROOT / "paper_runs/submission_evidence/mapping_audit/mapping_audit.csv"
    ).open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row["source_name"] == "AlphaAgents"]
    assert len(rows) == 2
    assert {row["mapping_fidelity_tier"] for row in rows} == {"M0_narrative_translation"}
    assert all(row["source_supports_exact_ingredients"] == "no" for row in rows)
    assert all(row["source_supports_tested_weighting_rule"] == "no" for row in rows)
    assert all(row["exact_original_claim_matches_monthly_us_ff_alpha"] == "no explicit match identified" for row in rows)
