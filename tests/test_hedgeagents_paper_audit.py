from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/hedgeagents"
SPEC = importlib.util.spec_from_file_location(
    "audit_hedgeagents_paper", ROOT / "scripts/audit_hedgeagents_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_all_three_published_tables_are_transcribed_without_credit() -> None:
    site_results = {
        model: tuple(float(value) for value in values)
        for _, model, values in audit.MAIN_RESULTS
        if model not in {"Bitcoin", "FX", "DJIA", "Improvement"}
    }
    ledger = audit.performance_ledger(site_results)
    assert len(ledger) == 236
    assert sum(row["table"] == "main" for row in ledger) == 119
    assert sum(row["table"] == "conference_ablation" for row in ledger) == 63
    assert sum(row["table"] == "llm_backbone" for row in ledger) == 54
    assert sum(bool(row["hedgeagents_system_output"]) for row in ledger) == 126
    assert all(row["paper_result_credit"] is False for row in ledger)
    assert all(row["native_reproduced_value"] == "" for row in ledger)


def test_manifest_fail_closed_result_boundary() -> None:
    data = manifest()
    assert data["overall_status"] == (
        "not_reproduced_no_public_system_source_frozen_inputs_runtime_traces_or_portfolio_path"
    )
    assert data["full_end_to_end_pipeline_reproduced"] is False
    assert data["published_numeric_table_cells"] == 236
    assert data["hedgeagents_own_numeric_table_cells"] == 126
    assert data["author_site_corroborated_main_table_cells"] == 90
    assert data["published_numeric_table_cells_faithfully_regenerated"] == 0
    assert data["hedgeagents_own_cells_faithfully_regenerated"] == 0
    assert data["public_system_source_files_recovered"] == 0
    assert data["llm_calls_made"] == 0


def test_author_site_duplicates_never_become_reproduction_credit() -> None:
    ledger = rows("published_performance_ledger.csv")
    corroborated = [row for row in ledger if row["author_site_corroborated"] == "True"]
    assert len(corroborated) == 90
    assert {row["table"] for row in corroborated} == {"main"}
    assert all(row["status"] == "author_site_duplicate_zero_credit" for row in corroborated)
    assert all(row["paper_result_credit"] == "False" for row in corroborated)
    assert all(row["native_reproduced_value"] == "" for row in corroborated)


def test_arxiv_bundle_is_manuscript_source_not_trading_source() -> None:
    inventory = rows("paper_source_inventory.csv")
    assert len(inventory) == 20
    assert sum(row["role"] == "primary_manuscript_source" for row in inventory) == 1
    assert sum(row["role"] == "published_figure" for row in inventory) == 14
    assert all(row["is_executable_system_source"] == "False" for row in inventory)
    assert all(row["replication_credit"] == "False" for row in inventory)


def test_static_site_and_unrelated_template_residue_are_separated() -> None:
    access = {row["artifact"]: row for row in rows("artifact_access_audit.csv")}
    site = access["author_project_repository"]
    residue = access["author_site_mathvista_residue"]
    assert site["tier"] == "R1 static documentation"
    assert site["system_source_credit"] == "False"
    assert "6,141-record VQA" in residue["availability"]
    assert residue["tier"] == "unrelated template residue"
    assert residue["system_source_credit"] == "False"
    data = manifest()
    assert data["author_site_tree_files"] == 46
    assert data["author_site_hedgeagents_image_assets"] == 15
    assert data["author_site_unrelated_template_image_assets"] == 4
    assert data["author_site_unrelated_vqa_records"] == 6141


def test_profile_screenshots_expose_scope_conflicts_not_an_implementation() -> None:
    permissions = rows("profile_permissions.csv")
    assert len(permissions) == 57
    tools = [row for row in permissions if row["permission_type"] == "tool"]
    actions = [row for row in permissions if row["permission_type"] == "action"]
    assert len(tools) == 25
    assert len(actions) == 22
    assert len({row["name"] for row in tools}) == 23
    assert len({row["name"] for row in actions}) == 10
    assert {(row["agent"], row["agent_named_count"]) for row in tools} == {
        ("Dave", "6"), ("Bob", "7"), ("Emily", "7"), ("Otto", "5")
    }
    assert all(row["implementation_released"] == "False" for row in permissions)
    assert all(row["faithful_replication_credit"] == "False" for row in permissions)


def test_prompt_inventory_does_not_confuse_symbols_or_profiles_with_runtime() -> None:
    prompts = rows("prompt_inventory.csv")
    assert len(prompts) == 9
    assert sum(row["publication_form"] == "verbatim simplified template" for row in prompts) == 1
    assert sum(row["status"] == "missing_exact_prompt" for row in prompts) == 4
    assert sum(row["status"] == "author_profile_image_not_runtime_prompt" for row in prompts) == 4
    assert all(row["runtime_values_released"] == "False" for row in prompts)
    assert all(row["actual_request_released"] == "False" for row in prompts)
    assert all(row["actual_response_released"] == "False" for row in prompts)


def test_method_ledger_records_execution_blockers_explicitly() -> None:
    dimensions = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    for key in (
        "asset_universe",
        "technical_indicators",
        "initial_capital",
        "trade_fill_timing_and_price",
        "transaction_costs",
        "slippage",
        "metric_formulas",
        "baseline_implementations",
        "randomness",
        "runtime_environment",
        "actual_llm_requests",
        "native_actions_orders_fills",
        "native_equity_curves",
    ):
        assert dimensions[key]["status"].startswith("missing")
    assert dimensions["llm_model"]["status"] == "specified_historical_snapshot_now_deprecated"
    assert dimensions["actions"]["status"] == "conflicting_action_contract"


def test_material_internal_conflicts_remain_visible() -> None:
    findings = {row["claim_id"]: row for row in rows("internal_consistency_audit.csv")}
    assert len(findings) == 8
    assert findings["full_system_mdd"]["status"] == "hard_internal_conflict"
    assert "14.21" in findings["full_system_mdd"]["paper_claim"]
    assert "8.68" in findings["full_system_mdd"]["paper_claim"]
    assert findings["main_table_sr_improvement"]["status"] == "not_roundable_from_displayed_values"
    assert "24.8705%" in findings["main_table_sr_improvement"]["recomputed_or_comparison"]
    assert findings["wins_all_metrics"]["status"] == "claim_contradicted_by_own_table"
    assert findings["conference_synergy_sr_percentages"]["status"] == (
        "unsupported_by_displayed_ablation_values"
    )
    assert manifest()["hard_or_material_internal_consistency_findings"] == 7


def test_figures_are_inventoried_but_not_digitized_into_fake_results() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 12
    assert sum(int(row["panels"]) for row in figures) == 25
    assert all(row["exact_dated_underlying_values_released"] == "False" for row in figures)
    assert all(row["figure_digitization_is_replication"] == "False" for row in figures)
    assert all(row["status"] == "published_visual_only_zero_result_credit" for row in figures)


def test_later_author_paper_is_bounded_as_risk_not_direct_measurement() -> None:
    warning = json.loads((AUDIT_DIR / "temporal_leakage_warning.json").read_text(encoding="utf-8"))
    assert warning["same_five_authors"] is True
    assert warning["hedgeagents_named_as_representative_historical_backtest"] is True
    assert warning["hedgeagents_in_pre_post_temporal_decay_experiment"] is False
    assert warning["temporal_decay_experiment_methods"] == [
        "FinMem", "FinAgent", "QuantAgent", "FinCON", "TradingAgents"
    ]
    assert warning["gpt_4_1106_preview_official_knowledge_cutoff"] == "April 2023"
    assert "not direct proof" in warning["interpretation"]


def test_rebuilds_and_static_assets_do_not_count_as_system_execution() -> None:
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text(encoding="utf-8"))
    native = json.loads((AUDIT_DIR / "native_execution.json").read_text(encoding="utf-8"))
    assert provenance["first_deterministic_rebuild_sha256"] != provenance["second_deterministic_rebuild_sha256"]
    assert "trailer ID" in provenance["rebuild_comparison"]
    assert provenance["source_archive_contains_system_code"] is False
    assert native["manuscript_source_rebuilt"] is True
    assert native["manuscript_rebuild_is_system_execution"] is False
    assert native["author_site_static_assets_validated"] is True
    assert native["hedgeagents_pipeline_executed"] is False
    assert native["published_table_cells_faithfully_regenerated"] == 0


def test_negative_search_is_bounded_and_manifest_hashes_all_outputs() -> None:
    discovery = rows("discovery_evidence.csv")
    assert len(discovery) == 10
    assert all(row["system_implementation_recovered"] == "False" for row in discovery)
    assert all(row["negative_search_limit"] for row in discovery)
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())


def test_readme_states_the_honest_replication_boundary() -> None:
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "**Zero of 236**" in text
    assert "R1 static documentation artifact" in text
    assert "unrelated to HedgeAgents" in text
    assert "**not** proof" in text
    assert "does **not** call\n  them byte-identical" in text
