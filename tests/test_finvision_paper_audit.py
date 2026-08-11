from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/finvision"
SPEC = importlib.util.spec_from_file_location(
    "audit_finvision_paper", ROOT / "scripts/audit_finvision_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_paper_table_contract_is_72_cells_with_18_finvision_cells() -> None:
    ledger = audit.performance_ledger(True, audit.FINAGENT_PRECISE)
    assert len(ledger) == 72
    assert sum(row["method"].startswith("FinVision") for row in ledger) == 18
    assert {row["ticker"] for row in ledger} == {"AAPL", "MSFT", "AMZN"}
    assert {row["metric"] for row in ledger} == {"ARR_pct", "SR", "MDD_pct"}


def test_manifest_fail_closed_result_boundary() -> None:
    data = manifest()
    assert data["overall_status"] == "not_reproduced_no_public_system_source_frozen_inputs_or_trajectories"
    assert data["full_end_to_end_pipeline_reproduced"] is False
    assert data["published_performance_cells"] == 72
    assert data["finvision_own_performance_cells"] == 18
    assert data["published_performance_cells_faithfully_regenerated"] == 0
    assert data["finvision_own_cells_faithfully_regenerated"] == 0
    assert data["llm_calls_made"] == 0
    assert data["public_system_source_files_recovered"] == 0


def test_corroboration_and_lineage_never_become_reproduction_credit() -> None:
    ledger = rows("published_performance_ledger.csv")
    assert len(ledger) == 72
    assert all(row["arxiv_source_verified"] == "True" for row in ledger)
    assert all(row["author_thesis_corroborated"] == "True" for row in ledger)
    assert all(row["paper_result_credit"] == "False" for row in ledger)
    assert all(row["native_reproduced_value"] == "" for row in ledger)
    finagent = [row for row in ledger if row["method"] == "FinAgent"]
    assert len(finagent) == 9
    assert sum(row["external_lineage_status"] == "two_decimal_rounding_match" for row in finagent) == 8
    assert sum("truncation" in row["external_lineage_status"] for row in finagent) == 1


def test_current_yahoo_diagnostic_is_separate_and_zero_credit() -> None:
    diagnostic = rows("market_baseline_diagnostic.csv")
    assert len(diagnostic) == 9
    assert sum(row["display_match"] == "True" for row in diagnostic) == 3
    assert all(row["faithful_replication_credit"] == "False" for row in diagnostic)
    assert all("current_input_diagnostic" in row["status"] for row in diagnostic)


def test_paper_day_counts_and_news_inputs_remain_unreproduced() -> None:
    stats = rows("dataset_statistics_audit.csv")
    trading = [row for row in stats if row["dimension"] == "trading_days"]
    news = [row for row in stats if row["dimension"] == "news_articles"]
    assert len(trading) == len(news) == 6
    assert {(row["paper_value"], row["pinned_current_value"]) for row in trading} == {
        ("42", "41"),
        ("145", "147"),
    }
    assert all(row["status"] == "not_reproduced_original_query_and_snapshot_unreleased" for row in news)
    assert all(row["faithful_replication_credit"] == "False" for row in stats)


def test_prompt_templates_do_not_stand_in_for_runtime_traces() -> None:
    prompts = rows("prompt_inventory.csv")
    assert len(prompts) == 5
    assert {row["prompt"] for row in prompts} == {
        "news_summarizer",
        "chart_analyst",
        "reflection_short_medium",
        "trading_signal_chart_reflection",
        "prediction",
    }
    assert all(row["template_printed_in_appendix"] == "True" for row in prompts)
    assert all(row["runtime_values_released"] == "False" for row in prompts)
    assert all(row["actual_request_released"] == "False" for row in prompts)
    assert all(row["actual_response_released"] == "False" for row in prompts)


def test_method_ledger_records_material_missing_execution_choices() -> None:
    dimensions = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    for key in (
        "initial_capital",
        "price_field_and_adjustment",
        "trade_fill_timing_and_price",
        "transaction_costs",
        "slippage",
        "reward_equation",
        "sharpe_convention",
        "ppo_dqn_hyperparameters",
        "actual_llm_requests",
        "native_actions_equity_curves",
    ):
        assert dimensions[key]["status"].startswith("missing")
    assert dimensions["finagent_caption_citation"]["status"] == "citation_lineage_error"
    assert dimensions["public_system_implementation"]["status"] == "not_publicly_recovered_not_proof_of_nonexistence"


def test_arxiv_bundle_is_manuscript_source_not_system_source() -> None:
    inventory = rows("paper_source_inventory.csv")
    assert len(inventory) == 22
    assert sum(row["role"] == "primary_manuscript_source" for row in inventory) == 1
    used = [row for row in inventory if row["role"] == "published_figure_used_by_active_manuscript"]
    assert [row["path"] for row in used] == ["framework.png"]
    assert all(row["is_executable_system_source"] == "False" for row in inventory)


def test_two_clean_manuscript_builds_are_honestly_characterized() -> None:
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text(encoding="utf-8"))
    native = json.loads((AUDIT_DIR / "native_execution.json").read_text(encoding="utf-8"))
    assert provenance["first_clean_rebuild_sha256"] != provenance["second_clean_rebuild_sha256"]
    assert "trailer ID" in provenance["clean_rebuild_comparison"]
    assert native["manuscript_rebuild_repeated_byte_identical"] is False
    assert native["manuscript_rebuild_text_identical"] is True
    assert native["manuscript_rebuild_is_system_execution"] is False
    assert native["finvision_pipeline_executed"] is False


def test_negative_public_search_is_bounded_not_overclaimed() -> None:
    discovery = rows("discovery_evidence.csv")
    access = rows("artifact_access_audit.csv")
    assert len(discovery) >= 30
    assert all("not proof" in row["negative_search_limit"] or row["negative_search_limit"] == "not a system implementation" for row in discovery)
    assert all(row["system_source_credit"] == "False" for row in access)
    author = next(row for row in access if row["artifact"] == "author_github_current")
    assert author["availability"] == "27 public repos inspected"


def test_manifest_hashes_every_nonmanifest_output() -> None:
    data = manifest()
    expected = {path.name for path in AUDIT_DIR.iterdir() if path.is_file() and path.name != "manifest.json"}
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())


def test_readme_states_zero_credit_and_correct_period_interpretation() -> None:
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "zero of 72" in text.lower()
    assert "seven months is the **testing** window" in text
    assert "not proof that private or deleted artifacts never existed" in text
    assert "does **not** call them byte-identical" in text
