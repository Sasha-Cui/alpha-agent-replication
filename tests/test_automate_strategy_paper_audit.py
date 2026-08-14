from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_automate_strategy_paper.py"
SPEC = importlib.util.spec_from_file_location("automate_strategy_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def test_published_targets_cover_table_2_and_table_4() -> None:
    assert len(audit.PAPER_TABLE_2) == 5
    assert len(audit.PAPER_TABLE_3_SELECTED_INDICES) == 12
    assert len(audit.PAPER_TABLE_4) == 8
    assert len(audit.TABLE_4_METRICS) == 5
    assert audit.PAPER_TABLE_4[0][1][0] == 53.173


def test_table_2_absolute_ic_audit_is_explicit() -> None:
    rows = [
        {"index": 1, "category": "Momentum", "ic": -0.01},
        {"index": 3, "category": "Momentum", "ic": 0.02},
        {"index": 9, "category": "Momentum", "ic": -0.03},
    ]
    rows.extend(
        {"index": index, "category": category, "ic": value}
        for category, index, value in (
            ("Mean Reversion", 10, -0.0187),
            ("Volatility", 20, 0.0258),
            ("Fundamental", 27, -0.0192),
            ("Growth", 33, -0.0217),
        )
    )
    result = audit.table_2_audit(rows)
    momentum = next(
        row
        for row in result
        if row["category"] == "Momentum" and row["metric"] == "mean_ic_of_saf"
    )
    assert momentum["source_absolute_ic_aggregation"] == 0.02
    assert "absolute IC" in momentum["aggregation_note"]


def test_committed_audit_records_partial_component_not_paper_replication() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/automate_strategy_finding"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    with (output / "factor_workbook_inventory.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        inventory = list(csv.DictReader(handle))
    with (output / "table_4_conformance.csv").open(newline="", encoding="utf-8") as handle:
        table_4 = list(csv.DictReader(handle))
    with (output / "released_source_history_inventory.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        history = list(csv.DictReader(handle))
    with (output / "historical_branch_component_inventory.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        branch_components = list(csv.DictReader(handle))
    with (output / "public_fork_ref_inventory.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        fork_refs = list(csv.DictReader(handle))
    assert manifest["overall_status"] == "not_reproduced_missing_integrated_native_output"
    assert manifest["paper_table_2_cells_matched"] == 3
    assert manifest["paper_table_2_cells_total"] == 10
    assert manifest["paper_table_4_cells_verified"] == 0
    assert manifest["paper_table_4_cells_unverifiable"] == 40
    assert manifest["native_integrated_portfolio_return_shipped"] is False
    assert manifest["dnn_hidden_width_matches"] is False
    assert manifest["source_agent_contains_hardcoded_credential"] is True
    assert manifest["source_agent_historical_credential_literal_present_at_pinned_commit"] is True
    assert manifest["source_agent_current_main_credential_redacted"] is True
    assert manifest["public_fork_census_checked_at"] == "2026-08-14"
    assert manifest["public_forks_total"] == 24
    assert manifest["public_fork_branch_refs_total"] == 25
    assert manifest["public_fork_branch_ref_sequence_sha256"] == (
        "61c027bcfab368f1641f2d0f8e5b1901d5c6c89548464d6ef91922403cef8e2f"
    )
    assert manifest["public_fork_branch_refs_reachable_from_official_history"] == 25
    assert manifest["public_divergent_fork_heads_total"] == 0
    assert manifest["public_fork_paper_result_credit_paths_total"] == 0
    assert manifest["new_project_branch_reviewed"] is True
    assert manifest["new_project_branch_component_attempt_is_paper_faithful"] is False
    assert manifest["new_project_branch_paper_result_credit"] is False
    runtime = json.loads(
        (output / "historical_branch_runtime_observation.json").read_text(encoding="utf-8")
    )
    assert runtime["source_commit"] == audit.NEW_PROJECT_HEAD
    assert runtime["reconstructed_package_import"] == "passed"
    assert runtime["multi_agent_synthetic_probe"]["status"] == "passed"
    assert runtime["multi_agent_synthetic_probe"]["paper_result_credit"] is False
    assert runtime["optimizer_short_batch_probe"]["status"] == "failed"
    assert runtime["optimizer_short_batch_probe"]["exception_type"] == "ZeroDivisionError"
    assert runtime["default_constructor_probe"]["status"].startswith("environment_crash")
    assert runtime["default_constructor_probe"]["author_code_failure_inferred"] is False
    source_history = manifest["released_source_history"]
    assert source_history["public_commits_reviewed"] == 7
    assert source_history["public_branches_reviewed"] == 2
    assert source_history["public_tags"] == 0
    assert source_history["public_releases"] == 0
    assert source_history["unreachable_git_objects"] == 0
    assert source_history["historical_unique_paths_reviewed"] == 39
    assert source_history["history_complete_for_pinned_public_refs"] is True
    assert source_history["current_main_diff_from_pinned_commit"] == "credential_redaction_only"
    assert source_history["new_project_default_mlp_architecture_matches_paper"] is False
    assert source_history["new_project_connected_to_released_workbooks"] is False
    assert source_history["new_project_native_run_or_result_shipped"] is False
    assert source_history["new_project_paper_result_credit"] is False
    assert len(history) == 7
    assert history[-1]["commit"] == audit.CURRENT_MAIN_HEAD
    assert history[-1]["evidence_role"] == "credential_redaction_only_no_experiment_evidence"
    assert history[-1]["usable_hardcoded_credential_literal_present"] == "False"
    assert all(row["paper_result_credit"] == "False" for row in history)
    assert len(branch_components) == 6
    assert {row["path"] for row in branch_components} == {
        "README.md",
        "main.py",
        "multi_agent_system.py",
        "requirements.txt",
        "seed_alphas_factory.py",
        "weight_optimization.py",
    }
    assert all(row["connected_to_released_workbooks"] == "False" for row in branch_components)
    assert all(row["paper_configuration_match"] == "False" for row in branch_components)
    assert all(row["paper_result_credit"] == "False" for row in branch_components)
    assert len(fork_refs) == 25
    assert len({row["repository"] for row in fork_refs}) == 24
    assert all(row["reachable_from_pinned_official_history"] == "True" for row in fork_refs)
    assert all(row["additional_commits"] == "0" for row in fork_refs)
    assert all(row["paper_result_credit"] == "False" for row in fork_refs)
    assert len(inventory) == 7
    assert {row["sample_start"] for row in inventory} == {"2022-09-30"}
    assert {row["sample_end"] for row in inventory} == {"2022-12-30"}
    assert all(row["covers_paper_test_window"] == "False" for row in inventory)
    assert all(row["status"].startswith("unverifiable") for row in table_4)
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected
