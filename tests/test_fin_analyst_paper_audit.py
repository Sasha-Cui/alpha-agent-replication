from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/fin_analyst"
SPEC = importlib.util.spec_from_file_location(
    "audit_fin_analyst_paper", ROOT / "scripts/audit_fin_analyst_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_json(name: str) -> dict:
    return json.loads((AUDIT_DIR / name).read_text())


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_original_source_rebuild_and_public_lineage_are_pinned() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["arxiv_id"] == "2607.12233"
    assert provenance["paper_version"].startswith("v1")
    assert provenance["source_files"] == 9
    assert provenance["official_pages"] == provenance["rebuilt_pages"] == 13
    assert provenance["official_rebuilt_token_jaccard"] > 0.999
    assert provenance["all_official_and_rebuilt_pages_visually_checked"] is True
    assert provenance["author_space"] == {
        "url": audit.AUTHOR_SPACE,
        "commit": audit.AUTHOR_COMMIT,
        "tracked_files": 13,
        "license": "NOASSERTION",
    }
    assert provenance["dataset"]["pre_live_commit"] == audit.DATASET_COMMIT
    assert provenance["organizer"]["source_commit"] == audit.ARENA_COMMIT


def test_all_119_empirical_table_cells_fail_closed() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 119
    assert Counter(row["table_label"] for row in results) == {
        "tab:results": 10,
        "tab:tsla": 42,
        "tab:btc": 35,
        "tab:ablation": 20,
        "tab:error_attribution": 12,
    }
    assert sum(row["official_input_or_result_record_recovered"] == "True" for row in results) == 8
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["author_native_decision_pipeline_reexecuted"] == "False" for row in results)
    assert all(row["published_result_regenerated_at_display_precision"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)


def test_native_prompts_and_corpora_are_recovered_with_boundaries() -> None:
    prompts = rows("prompt_correspondence.csv")
    assert len(prompts) == 9
    assert {row["agent"] for row in prompts} == {
        "News", "Event", "Earnings", "Strategy", "Fundamentals", "Analyst",
        "Technical", "Social", "Meta agent",
    }
    assert all(len(row["native_system_prompt_sha256"]) == 64 for row in prompts)
    assert all(row["paper_labels_prompts_full"] == "True" for row in prompts)
    assert all(row["paper_row_is_byte_identical_to_native_prompt"] == "False" for row in prompts)
    corpora = rows("native_corpus_inventory.csv")
    assert len(corpora) == 7
    assert sum(int(row["records"]) for row in corpora if row["file"].endswith("jsonl")) == 5781
    assert next(row for row in corpora if row["file"] == "TSLA_TA_2025.csv")["maximum_date"] == "2025-12-30"
    assert next(row for row in corpora if row["file"] == "TSLA_wsb_2025.jsonl")["maximum_date"] == "2026-04-12"


def test_pinned_pre_live_dataset_matches_scope_but_not_offline_buy_hold() -> None:
    dataset = {row["asset"]: row for row in rows("offline_dataset_audit.csv")}
    assert set(dataset) == {"TSLA", "BTC"}
    assert dataset["TSLA"]["calendar_rows"] == dataset["BTC"]["calendar_rows"] == "283"
    assert dataset["TSLA"]["distinct_price_observations_including_initial"] == "194"
    assert dataset["BTC"]["distinct_price_observations_including_initial"] == "283"
    assert float(dataset["TSLA"]["raw_start_to_end_return_pct"]) == pytest.approx(41.5424773460)
    assert float(dataset["BTC"]["raw_start_to_end_return_pct"]) == pytest.approx(-27.5170826425)
    assert all(row["paper_buy_hold_matches_raw_dataset"] == "False" for row in dataset.values())


def test_official_live_decisions_replay_but_contradict_table() -> None:
    replay = {row["asset"]: row for row in rows("live_result_replay.csv")}
    assert replay["TSLA"]["decision_rows"] == "47"
    assert replay["BTC"]["decision_rows"] == "50"
    assert float(replay["TSLA"]["organizer_replay_return_pct"]) == pytest.approx(4.79098262915)
    assert float(replay["TSLA"]["organizer_replay_sharpe"]) == pytest.approx(1.57807325215)
    assert replay["TSLA"]["organizer_replay_win_rate_pct"] == "45"
    assert float(replay["BTC"]["organizer_replay_return_pct"]) == pytest.approx(-0.09755191591)
    assert replay["BTC"]["organizer_replay_win_rate_pct"] == "40"
    assert all(row["all_printed_live_metrics_match"] == "False" for row in replay.values())


def test_native_controlled_run_exposes_btc_vote_defects_without_external_calls() -> None:
    execution = load_json("native_execution.json")
    assert execution["pip_check_passed"] is True
    assert execution["app_py_compiles"] is True
    assert execution["paid_or_external_model_calls"] == 0
    assert execution["external_fear_greed_calls"] == 0
    assert execution["author_native_paper_actions_regenerated"] == 0
    controlled = execution["controlled_execution"]
    assert controlled["tsla_endpoint"]["response"] == {"recommended_action": "SELL"}
    assert controlled["tsla_endpoint"]["llm_call_seams_exercised"] == 8
    assert controlled["btc_three_hold_case"][0] == "BUY"
    assert "H=3" in controlled["btc_three_hold_case"][1]
    assert controlled["btc_missing_fear_greed_case"][0] == "SELL"
    assert "S=2" in controlled["btc_missing_fear_greed_case"][1]


def test_figure_and_internal_conflicts_are_not_silently_reconciled() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 3
    empirical = [row for row in figures if row["empirical"] == "True"]
    assert len(empirical) == 2
    assert all(row["buy_hold_endpoint_matches_rounding"] == "True" for row in empirical)
    assert all(row["agent_endpoint_matches"] == "False" for row in empirical)
    assert all(row["full_panel_regenerated"] == "False" for row in empirical)
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["btc_live_table_vs_figure"]["status"] == "major_numeric_conflict"
    assert checks["tsla_live_table_vs_official_replay"]["status"] == "major_numeric_conflict"
    assert checks["btc_all_hold_majority"]["status"] == "source_method_conflict"
    assert checks["btc_missing_fear_greed"]["status"] == "source_method_conflict"
    assert checks["full_prompts_claim"]["status"] == "specification_conflict"


def test_manifest_hashes_readme_and_builder_are_deterministic(tmp_path: Path) -> None:
    manifest = load_json("manifest.json")
    assert manifest["active_empirical_table_cells"] == 119
    assert manifest["empirical_figure_panels"] == 2
    assert manifest["paper_window_official_decision_rows_recovered"] == 97
    assert manifest["paper_window_official_rows_replayed_with_organizer_scorer"] == 97
    assert manifest["published_table_cells_regenerated"] == 0
    assert manifest["full_empirical_figure_panels_regenerated"] == 0
    assert manifest["strict_success"] is False
    assert manifest["generated_file_sha256"] == {
        path.name: file_sha256(path)
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "119 displayed empirical table cells", "Zero of 119 printed table cells",
        "Three BTC HOLD votes become BUY", "99.96% extracted-token overlap",
        "strict_success` is false", "far from 100% paper-result faithfulness",
    ):
        assert marker in readme
    if not audit.DEFAULT_SCRATCH.is_dir() or not audit.NATIVE_ENV.is_dir():
        pytest.skip("pinned evidence and native environment are only available on Bouchet")
    first, second = tmp_path / "first", tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
