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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/stratllm"
SPEC = importlib.util.spec_from_file_location(
    "audit_stratllm_paper", ROOT / "scripts/audit_stratllm_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_official_document_is_pinned_rebuilt_and_visually_checked() -> None:
    data = manifest()
    assert data["official_version_audited"] == "v1"
    assert data["official_pdf_and_source_recovered"] is True
    assert data["official_document_rebuild_completed"] is True
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    arxiv = provenance["arxiv"]
    assert arxiv["submitted_utc"] == "2026-05-07T11:17:23Z"
    assert arxiv["pdf_pages"] == arxiv["rebuild_pages"] == 6
    assert arxiv["source_file_count"] == 6
    assert arxiv["repeated_downloads_byte_identical"] is True
    assert arxiv["rebuild_extracted_token_multiset_jaccard"] > 0.998
    assert arxiv["visual_qa"] == {
        "pages_inspected": 6,
        "unreadable_or_clipped_pages": 0,
    }


def test_complete_table_and_figure_denominators_keep_native_credit_zero() -> None:
    tables = rows("published_result_ledger.csv")
    figures = rows("figure_result_ledger.csv")
    data = manifest()
    assert len(tables) == data["published_numeric_table_cells"] == 195
    assert Counter(row["table"] for row in tables) == {
        "Table 1": 168,
        "Table 2": 27,
    }
    assert Counter(row["duplicate_kind"] for row in tables) == {
        "none": 186,
        "exact_repeat_of_table1": 9,
    }
    assert len(figures) == data["published_figure_numeric_points"] == 6
    assert Counter(row["duplicate_kind"] for row in figures) == {
        "none": 4,
        "exact_repeat_of_table1": 2,
    }
    assert data["published_unique_empirical_numeric_units"] == 190
    assert data["native_empirical_units_regenerated"] == 0
    assert all(row["native_pipeline_executed"] == "False" for row in tables)
    assert all(row["native_result_regenerated"] == "False" for row in tables + figures)
    assert all(row["paper_result_credit"] == "False" for row in tables + figures)


def test_literal_live_forward_claim_fails_public_model_chronology() -> None:
    releases = rows("model_release_chronology.csv")
    assert len(releases) == 10
    assert all(row["literal_live_forward_2025_possible"] == "False" for row in releases)
    assert all(row["defensible_interpretation"] == "post-hoc chronological replay of 2025 data" for row in releases)
    assert sum(row["first_public_date_used_for_audit"].startswith("2026-") for row in releases) == 8
    assert all(row["after_latest_stated_evaluation_date"] == "True" for row in releases[:9])
    assert releases[-1]["model_family"] == "Claude-Sonnet-4.5"
    assert releases[-1]["first_public_date_used_for_audit"] == "2025-09-29"
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["literal_live_forward_2025"]["status"] == (
        "contradicted_by_public_model_chronology"
    )
    assert checks["defensible_temporal_interpretation"]["status"] == (
        "post_hoc_chronological_replay_possible_but_unverified"
    )
    assert manifest()["literal_live_forward_2025_claim_supported"] is False
    assert manifest()["post_hoc_chronological_replay_verified"] is False


def test_method_prompt_strategy_and_metric_ledgers_fail_closed() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 35
    for dimension in (
        "asset_universe",
        "short_window_dates",
        "long_window_dates",
        "price_data",
        "news_data",
        "annual_reports",
        "transaction_costs",
        "exact_prompts",
        "structured_output_schema",
        "model_call_parameters",
        "sampling_configuration",
        "random_seeds",
        "runtime_requests_responses",
        "metric_formulas",
        "actions_orders_fills",
        "cash_holdings_nav_returns",
        "raw_result_arrays",
        "native_source",
    ):
        assert methods[dimension]["status"] == "missing"
    prompts = rows("prompt_inventory.csv")
    assert [row["mode"] for row in prompts] == ["Free", "Guided", "Strict"]
    assert all(row["exact_system_prompt_recovered"] == "False" for row in prompts)
    assert all(row["native_prompt_call_credit"] == "False" for row in prompts)
    strategies = rows("strategy_specification_audit.csv")
    assert len(strategies) == 4
    assert sum(row["has_one_exact_entry_threshold"] == "True" for row in strategies) == 1
    assert all(row["fully_executable_definition_recovered"] == "False" for row in strategies)
    metrics = rows("metric_specification_audit.csv")
    assert len(metrics) == 9
    assert all(row["exact_formula_recovered"] == "False" for row in metrics)
    assert all(row["native_metric_credit"] == "False" for row in metrics)


def test_consistency_checks_separate_arithmetic_from_unsupported_claims() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert len(checks) == 11
    assert checks["gpt_mdd_reduction"]["status"] == "passes_displayed_arithmetic"
    assert checks["best_us_total_return"]["status"] == "passes_table_check"
    assert checks["best_us_alpha"]["status"] == "prose_overstates_joint_best_performance"
    assert checks["highlight_caption"]["status"] == "incomplete_highlighting"
    assert checks["universal_strict_insurance"]["status"] == "under_supported_by_unpaired_rows"
    assert checks["standard_models_require_strict"]["status"] == "overbroad_relative_to_ablation"
    assert checks["disposition_effect"]["status"] == "not_identified_by_released_statistics"
    assert checks["temporal_horizon_significance"]["status"] == "unsupported_without_results_or_test"
    assert checks["metric_naming"]["status"] == "tr_ar_definition_gap"


def test_component_execution_and_discovery_do_not_invent_native_release() -> None:
    component = json.loads((AUDIT_DIR / "procedure_component_execution.json").read_text())
    assert component["computed"] == {
        "action_mapping": {"-1": "sell", "0": "hold", "1": "buy"},
        "maximum_affordable_integer_shares": 9,
        "remaining_cash": 91.0,
    }
    assert component["native_broker_used"] is False
    assert component["paper_input_used"] is False
    assert component["paper_result_credit"] is False
    discovery = rows("discovery_evidence.csv")
    assert len(discovery) == 7
    assert all(row["attributable_native_artifact_recovered"] == "False" for row in discovery)
    assert all("not proof" in row["negative_search_limit"] for row in discovery)
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    boundary = provenance["release_boundary"]
    assert boundary["advertised_project_page_status"] == 404
    assert boundary["attributable_implementation_recovered"] is False
    assert boundary["bounded_negative_search_is_proof_of_nonexistence"] is False


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned Strat-LLM primary-source scratch is only available on Bouchet")
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
            str(ROOT / "scripts/audit_stratllm_paper.py"),
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


def test_manifest_hashes_every_output_and_readme_states_boundary() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "native Strat-LLM experiment is **not reproduced**" in text
    assert "0/186 unique table cells" in text
    assert "0/4 additional" in text
    assert "No local proxy" in text
