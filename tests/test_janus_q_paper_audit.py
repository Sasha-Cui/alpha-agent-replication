from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_janus_q_paper.py"
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/janus_q"
SPEC = importlib.util.spec_from_file_location("audit_janus_q_paper", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def csv_rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_manifest_preserves_static_release_boundary() -> None:
    manifest = json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))
    expected = {
        "work_id": "CensusArxiv260219919",
        "system_id": "SYS-JANUS-Q",
        "arxiv_id": "2602.19919",
        "published_numeric_table_cells": 130,
        "author_linked_table_cells_exactly_verified": 61,
        "author_linked_table_cells_contradicted": 1,
        "published_table_cells_without_numeric_backing": 68,
        "author_native_table_cells_regenerated": 0,
        "active_empirical_figure_panels": 10,
        "author_linked_numeric_panels_recovered": 5,
        "author_native_figure_panels_regenerated": 0,
        "released_nav_derived_metrics_verified": 85,
        "released_data_files": 6,
        "released_data_bytes": 277_304_208,
        "released_event_stock_rows": 64_326,
        "released_unique_news_ids": 62_265,
        "released_jsonl_records": 31_999,
        "released_jsonl_records_exactly_linked": 31_999,
        "paper_linked_code_archive_expired": True,
        "first_author_historical_tree_files": 20,
        "first_author_system_source_files": 0,
        "first_author_public_history_commits_audited": 10,
        "first_author_public_branches_audited": 2,
        "historical_native_system_source_paths": 0,
        "historical_supplementary_output_revisions_checked": 5,
        "latest_supplementary_output_metrics_matching_array": 1,
        "author_native_training_executed": False,
        "author_native_backtest_executed": False,
        "full_end_to_end_pipeline_reproduced": False,
        "strict_success": False,
    }
    for key, value in expected.items():
        assert manifest[key] == value


def test_cell_ledger_distinguishes_corroboration_contradiction_and_absence() -> None:
    rows = csv_rows("published_result_ledger.csv")
    assert len(rows) == 130
    assert Counter(row["verification_status"] for row in rows) == {
        "verified_author_linked_output": 61,
        "contradicted_by_author_linked_output": 1,
        "no_released_numeric_backing": 68,
    }
    contradiction = next(row for row in rows if row["verification_status"] == "contradicted_by_author_linked_output")
    assert contradiction["table_label"] == "tab:model_comparison"
    assert contradiction["row_label"] == "CSI 1000"
    assert contradiction["metric"] == "SR"
    assert contradiction["printed_value"] == "-0.1036"
    assert contradiction["released_value"] == "-1.036000"
    assert all(row["author_native_experiment_executed"] == "False" for row in rows)
    assert all(row["published_result_regenerated"] == "False" for row in rows)
    assert all(row["paper_result_credit"] == "False" for row in rows)


def test_all_released_nav_metrics_are_independently_verified_without_result_credit() -> None:
    rows = csv_rows("released_nav_metric_verification.csv")
    assert len(rows) == 85
    assert len({row["model"] for row in rows}) == 17
    assert {row["metric"] for row in rows} == {"totalReturn", "mdd", "sr", "arr", "cr"}
    assert all(row["verification_passed"] == "True" for row in rows)
    csi1000 = next(row for row in rows if row["model"] == "CSI 1000" and row["metric"] == "sr")
    assert float(csi1000["author_release_value"]) == pytest.approx(-1.036)
    assert "does not reproduce predictions" in csi1000["boundary"]


def test_released_data_integrity_is_complete_but_explicitly_bounded() -> None:
    rows = {row["check"]: row for row in csv_rows("released_dataset_integrity.csv")}
    assert len(rows) == 11
    assert rows["news_car_row_alignment"]["denominator"] == "64326"
    assert rows["post_car_definition"]["denominator"] == "62462"
    assert rows["jsonl_raw_record_linkage"]["denominator"] == "31999"
    assert rows["jsonl_strength_labels"]["evidence"] == "ground_truth strength equals abs(post_car)>0.0015"
    assert rows["test_assistant_outputs_empty"]["denominator"] == "5999"
    assert all(row["passed"] == "True" for row in rows.values())
    assert all("not proof of annotation quality" in row["boundary"] for row in rows.values())

    inventory = {row["file"]: row for row in csv_rows("released_dataset_inventory.csv")}
    assert set(inventory) == {
        "news_with_label.csv",
        "stock_CAR_series.csv",
        "stock_industry_profile.csv",
        "train.jsonl",
        "val.jsonl",
        "test.jsonl",
    }
    assert inventory["train.jsonl"]["records"] == "20000"
    assert inventory["val.jsonl"]["records"] == "6000"
    assert inventory["test.jsonl"]["records"] == "5999"
    assert sum(int(row["bytes"]) for row in inventory.values()) == 277_304_208


def test_prompt_statistics_reconcile_partially_not_by_assumption() -> None:
    rows = csv_rows("historical_prompt_stat_reconciliation.csv")
    assert len(rows) == 10
    mismatches = {row["event_type"] for row in rows if row["both_values_match"] == "False"}
    assert mismatches == {"行业", "违法违规", "风险警示与消除"}
    assert all(row["simple_cutoff"] == "released rows strictly before 2023-10-25 with finite post_car" for row in rows)


def test_figure_and_method_ledgers_do_not_upgrade_static_backing_to_regeneration() -> None:
    figures = csv_rows("figure_inventory.csv")
    assert sum(int(row["active_empirical_panels"]) for row in figures) == 10
    assert sum(
        int(row["active_empirical_panels"])
        for row in figures
        if row["author_linked_numeric_backing_recovered"] == "True"
    ) == 5
    assert all(row["author_native_figure_pipeline_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)

    methods = {row["dimension"]: row for row in csv_rows("method_specification_audit.csv")}
    assert methods["native implementation"]["status"] == "not_released"
    assert methods["base model"]["status"] == "missing"
    assert methods["GRPO setup"]["status"] == "grid_only"
    assert methods["costs/execution"]["status"] == "missing_for_backtest"
    assert methods["published output arrays"]["status"] == "substantial_but_incomplete"


def test_release_provenance_recovers_first_author_static_history_not_code() -> None:
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text(encoding="utf-8"))
    assert provenance["official_pages"] == provenance["rebuilt_pages"] == 16
    assert provenance["official_pages_visually_checked"] == 16
    assert provenance["rebuilt_pages_visually_checked"] == 16
    assert provenance["visual_defects_observed"] == 0
    assert provenance["official_rebuilt_token_jaccard"] > 0.998
    assert provenance["author_repository"] == "https://github.com/Jackson906E/Janus-Q-demo"
    assert provenance["author_repository_default_branch"] == "main"
    assert provenance["author_repository_default_branch_head"] == (
        "526ac4e32d1e6904f5f3e2af25ea18886b61d325"
    )
    assert provenance["author_release_commit"] == "4455e10202865d9fe0c167ed0bdea57af266fdc1"
    assert provenance["author_release_commit_tree_files"] == 20
    assert provenance["author_release_contains_system_code"] is False
    assert provenance["full_public_repository_history_audited"] is True
    assert provenance["public_repository_commits"] == 10
    assert provenance["public_repository_branches"] == 2
    assert provenance["public_repository_tags"] == provenance["public_repository_releases"] == 0
    assert provenance["unreachable_git_objects"] == 0
    assert provenance["historical_native_system_source_paths"] == 0
    assert provenance["paper_linked_code_archive_observed_state"] == "expired"
    assert provenance["observed_license"] == "NOASSERTION"

    releases = {row["surface"]: row for row in csv_rows("release_search_audit.csv")}
    assert releases["first-author GitHub history"]["native_system_code_found"] == "False"
    assert releases["paper-linked code archive"]["reachable_or_found"] == "False"
    assert releases["paper-linked Drive dataset"]["reachable_or_found"] == "True"
    assert "private, renamed, deleted or later artifacts" in releases["bounded exact public searches"]["negative_search_boundary"]


def test_complete_history_and_supplementary_output_edit_are_fail_closed() -> None:
    history = csv_rows("released_source_history_inventory.csv")
    assert [row["commit"] for row in history] == list(audit.AUTHOR_HISTORY_COMMITS)
    assert len(history) == 10
    assert {row["native_system_source_paths"] for row in history} == {"0"}
    assert {row["native_system_source_found"] for row in history} == {"False"}
    assert sum(int(row["structured_output_payload_paths"]) > 0 for row in history) == 5
    outputs = csv_rows("historical_output_revision_consistency.csv")
    assert len(outputs) == 5
    assert [int(row["matching_metrics"]) for row in outputs] == [5, 5, 1, 1, 1]
    assert outputs[0]["nav_terminal_value"].startswith("1.52612387067")
    assert outputs[-1]["nav_terminal_value"].startswith("1.42612387067")
    assert float(outputs[-1]["reported_total_return"]) == pytest.approx(
        float(outputs[-1]["derived_total_return"]), abs=5e-7
    )
    assert outputs[-1]["mismatching_metrics"] == "arr;sr;mdd;cr"
    assert outputs[-1]["reported_cr"] == "48.203"
    assert float(outputs[-1]["derived_cr"]) == pytest.approx(33.022293, rel=1e-6)
    assert {row["paper_result_credit"] for row in outputs} == {"False"}


def test_internal_contradictions_and_readme_verdict_are_preserved() -> None:
    consistency = {row["check"]: row for row in csv_rows("internal_consistency_audit.csv")}
    assert consistency["dataset_headline"]["status"] == "conflict"
    assert consistency["csi1000_sharpe"]["status"] == "direct_contradiction"
    assert consistency["event_specific_history_edit"]["status"] == "direct_internal_conflict"
    assert consistency["reward_strength_gate"]["status"] == "method_conflict"
    assert consistency["sharpe_improvement_claim"]["status"] == "rounding_overstatement"

    readme = " ".join((AUDIT_DIR / "README.md").read_text(encoding="utf-8").split())
    for marker in (
        "strong author-linked data and published-output recovery, but not an end-to-end replication",
        "61/130 cells",
        "directly contradicts **1/130**",
        "no numeric backing for **68/130**",
        "0/130 cells were produced through the author-native experiment pipeline",
        "**85/85 matching output metrics**",
        "all 31,999 JSONL records",
        "complete public history has 10 revisions",
        "only total return matches the revised array (1/5)",
        "strict_success` remains false",
    ):
        assert marker in readme


def test_generated_hash_manifest_is_complete() -> None:
    manifest = json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))
    expected = {
        path.name: sha256(path)
        for path in AUDIT_DIR.iterdir()
        if path.name != "manifest.json"
    }
    assert manifest["generated_file_sha256"] == expected


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned Janus-Q audit evidence is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(tmp_path / "strict"), "--strict"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    strict = json.loads((tmp_path / "strict/manifest.json").read_text(encoding="utf-8"))
    assert strict["author_native_table_cells_regenerated"] == 0
    assert strict["strict_success"] is False
