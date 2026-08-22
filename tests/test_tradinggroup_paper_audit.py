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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/tradinggroup"
SPEC = importlib.util.spec_from_file_location(
    "audit_tradinggroup_paper", ROOT / "scripts/audit_tradinggroup_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_official_document_and_source_are_pinned_and_rebuilt() -> None:
    data = manifest()
    assert data["official_version_audited"] == "v1"
    assert data["official_pdf_and_source_recovered"] is True
    assert data["official_document_rebuild_completed"] is True
    provenance = json.loads(
        (AUDIT_DIR / "source_provenance.json").read_text(encoding="utf-8")
    )
    arxiv = provenance["arxiv"]
    assert arxiv["pdf_pages"] == 9
    assert arxiv["source_file_count"] == 6
    assert arxiv["repeated_downloads_byte_identical"] is True
    assert arxiv["source_rebuild_completed"] is True
    assert arxiv["rebuild_extracted_token_multiset_jaccard"] > 0.997
    assert arxiv["visual_qa"] == {
        "pages_inspected": 9,
        "unreadable_or_clipped_pages": 0,
    }


def test_complete_result_denominator_separates_native_and_baseline_credit() -> None:
    ledger = rows("published_result_ledger.csv")
    data = manifest()
    assert len(ledger) == data["published_numeric_table_cells"] == 360
    assert Counter(row["table"] for row in ledger) == {
        "Table 1": 240,
        "Table 2": 40,
        "Table 3": 80,
    }
    assert data["published_table1_slots"] == 320
    assert data["published_table1_dash_cells"] == 80
    assert sum(row["native_tradinggroup_result"] == "True" for row in ledger) == 140
    assert sum(row["duplicate_kind"] != "none" for row in ledger) == 20
    assert data["published_unique_numeric_table_cells"] == 340
    assert data["unique_native_tradinggroup_table_cells"] == 120
    assert data["native_tradinggroup_table_cells_regenerated"] == 0
    assert all(row["native_pipeline_executed"] == "False" for row in ledger)
    assert all(row["native_result_regenerated"] == "False" for row in ledger)
    credited = [row for row in ledger if row["paper_result_credit"] == "True"]
    assert len(credited) == 128
    assert all(row["credit_class"] == "source_adjacent_baseline_execution" for row in credited)
    assert all(row["native_tradinggroup_result"] == "False" for row in credited)


def test_exact_finsaber_execution_recovers_all_eligible_baselines_not_native_system() -> None:
    ledger = rows("finsaber_execution_ledger.csv")
    assert len(ledger) == manifest()["source_adjacent_baseline_cells_executed"] == 128
    assert Counter(row["strategy"] for row in ledger) == {
        "Buy and Hold": 16,
        "SMA Cross": 16,
        "WMA Cross": 16,
        "ATR Band": 16,
        "Bollinger Bands": 16,
        "Turn of The Month": 16,
        "ARIMA": 16,
        "XGBoost": 16,
    }
    matches = [row for row in ledger if row["fresh_execution_matches_paper"] == "True"]
    assert len(matches) == manifest()["source_adjacent_baseline_cells_matching_paper"] == 128
    assert Counter(row["strategy"] for row in matches) == {
        "Buy and Hold": 16,
        "SMA Cross": 16,
        "WMA Cross": 16,
        "ATR Band": 16,
        "Bollinger Bands": 16,
        "Turn of The Month": 16,
        "ARIMA": 16,
        "XGBoost": 16,
    }
    model_rows = [row for row in ledger if row["strategy"] in {"ARIMA", "XGBoost"}]
    assert all(
        row["execution_configuration"] == "historical_two_year_model_window"
        for row in model_rows
    )
    assert all(row["fresh_execution_matches_paper"] == "True" for row in model_rows)
    assert all(
        row["pinned_default_execution_matches_paper"] == "False"
        for row in model_rows
    )
    assert manifest()["source_adjacent_baseline_cells_matching_pinned_default"] == 96
    assert manifest()["model_baseline_training_years_recovered"] == 2
    assert manifest()["model_baseline_cells_matching_paper"] == 32
    assert all(row["ticker"] != "COIN" for row in ledger)
    assert all(row["native_tradinggroup_credit"] == "False" for row in ledger)
    source = rows("finsaber_source_output_comparison.csv")
    assert len(source) == 172
    assert Counter(row["status"] for row in source) == {
        "differs_from_paper": 109,
        "matches_paper_at_display_precision": 59,
        "paper_dash_or_no_numeric_cell": 4,
    }


def test_pinned_data_exactly_confirms_paper_test_set_claims() -> None:
    dataset = {row["ticker"]: row for row in rows("test_dataset_audit.csv")}
    assert set(dataset) == {"TSLA", "NFLX", "AMZN", "MSFT", "COIN"}
    assert all(row["matches_paper_claims"] == "True" for row in dataset.values())
    assert all(row["restricted_unpickler_only_allows_datetime_date"] == "True" for row in dataset.values())
    assert {ticker: int(row["price_date_count"]) for ticker, row in dataset.items()} == {
        ticker: 127 for ticker in dataset
    }
    assert {ticker: int(row["news_date_count"]) for ticker, row in dataset.items()} == {
        "TSLA": 127, "NFLX": 0, "AMZN": 22, "MSFT": 127, "COIN": 0,
    }
    assert int(dataset["MSFT"]["annual_filing_date_count"]) == 0
    assert int(dataset["MSFT"]["quarterly_filing_date_count"]) == 1
    assert all(row["native_agent_result_credit"] == "False" for row in dataset.values())


def test_formulas_prompts_and_figures_have_explicit_component_boundaries() -> None:
    formulas = rows("formula_inventory.csv")
    execution = json.loads(
        (AUDIT_DIR / "formula_component_execution.json").read_text(encoding="utf-8")
    )
    prompts = rows("prompt_inventory.csv")
    figures = rows("figure_inventory.csv")
    assert len(formulas) == manifest()["printed_formula_units_conditionally_executed"] == 13
    assert all(row["synthetic_component_executed"] == "True" for row in formulas)
    assert all(row["paper_result_credit"] == "False" for row in formulas)
    assert execution["formula_count"] == 13
    assert execution["native_tradinggroup_evaluator_used"] is False
    assert execution["paper_result_credit"] is False
    assert len(prompts) == 5
    assert all(row["figure2_runtime_shaped_example"] == "True" for row in prompts)
    assert all(row["exact_full_template_recovered"] == "False" for row in prompts)
    assert all(row["native_prompt_call_credit"] == "False" for row in prompts)
    assert Counter(row["figure"] for row in figures) == {
        "Figure 1": 1, "Figure 2": 1, "Figure 3": 1,
    }
    figure3 = next(row for row in figures if row["figure"] == "Figure 3")
    assert int(figure3["panels"]) == 5
    assert int(figure3["plotted_series"]) == 25
    assert int(figure3["native_tradinggroup_series"]) == 15
    assert figure3["underlying_array_released"] == "False"
    assert figure3["regenerated"] == "False"


def test_displayed_arithmetic_and_framework_conflicts_are_audited() -> None:
    annotations = rows("table3_annotation_audit.csv")
    assert len(annotations) == 60
    assert Counter(row["status"] for row in annotations) == {
        "passes_displayed_arithmetic": 58,
        "annotation_rounding_mismatch": 2,
    }
    mismatches = {
        (row["ticker"], row["configuration"], row["metric"]): row
        for row in annotations if row["status"] == "annotation_rounding_mismatch"
    }
    assert set(mismatches) == {
        ("TSLA", "RM+PC", "SPR"), ("TSLA", "RM+PC", "CR")
    }
    checks = {row["claim_id"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["dataset_claims"]["status"] == "passes_recovered_data_check"
    assert checks["deterministic_baselines"]["status"] == "substantial_fresh_reproduction"
    assert checks["model_baselines"]["status"] == "exact_historical_configuration_reproduction"
    assert checks["finsaber_coin_execution"]["status"] == "advertised_runner_conflict"
    assert checks["global_optimum"]["status"] == "overbroad_ambiguous_claim"
    assert checks["native_results"]["status"] == "unverifiable_without_release"


def test_method_and_discovery_ledgers_do_not_invent_native_release() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 31
    assert methods["test_data"]["status"] == "recovered"
    assert methods["baseline_framework"]["status"] == "recovered"
    assert methods["baseline_model_training_window"]["status"] == "recovered_but_paper_omitted"
    for dimension in (
        "peft_hyperparameters", "checkpoint", "full_prompts",
        "runtime_model_requests", "chain_of_thought", "style_multipliers",
        "random_seeds", "native_source", "daily_actions_fills_nav",
        "raw_table_arrays", "figure_curve_arrays",
    ):
        assert methods[dimension]["status"] == "missing"
    discovery = rows("discovery_evidence.csv")
    assert len(discovery) == 7
    assert all(row["attributable_tradinggroup_system_recovered"] == "False" for row in discovery)
    assert all("not proof" in row["negative_search_limit"] for row in discovery)
    provenance = json.loads(
        (AUDIT_DIR / "source_provenance.json").read_text(encoding="utf-8")
    )
    boundary = provenance["release_boundary"]
    assert boundary["attributable_tradinggroup_implementation_recovered"] is False
    assert boundary["qwen3_trader_checkpoint_recovered"] is False
    assert boundary["finsaber_is_source_adjacent_baseline_framework_not_tradinggroup_source"] is True
    finsaber = provenance["finsaber"]
    assert finsaber["paper_lineage_execution_config"]["training_years"] == 2
    assert "all 32" in finsaber["model_training_window_finding"]


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned TradingGroup primary-source scratch is only available on Bouchet")
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
            str(ROOT / "scripts/audit_tradinggroup_paper.py"),
            "--output", str(tmp_path / "strict"), "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    strict_manifest = json.loads(
        (tmp_path / "strict/manifest.json").read_text(encoding="utf-8")
    )
    assert strict_manifest["full_end_to_end_pipeline_reproduced"] is False


def test_manifest_hashes_outputs_and_readme_states_honest_boundary() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "native TradingGroup experiment not\nreproduced" in text
    assert "**0/120 unique native table cells**" in text
    assert "**128/128**" in text
    assert "16/16 XGBoost" in text
    assert "FINSABER is the cited baseline" in text
    assert "bounded public search" in text
