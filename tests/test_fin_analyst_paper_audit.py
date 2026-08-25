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


def test_all_119_empirical_table_cells_separate_output_verification_from_llm_replay() -> None:
    results = rows("published_result_ledger.csv")
    assert len(results) == 119
    assert Counter(row["table_label"] for row in results) == {
        "tab:results": 10,
        "tab:tsla": 42,
        "tab:btc": 35,
        "tab:ablation": 20,
        "tab:error_attribution": 12,
    }
    assert sum(row["official_input_or_result_record_recovered"] == "True" for row in results) == 34
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["author_native_decision_pipeline_reexecuted"] == "False" for row in results)
    verified = [
        row for row in results
        if row["published_result_regenerated_at_display_precision"] == "True"
    ]
    assert len(verified) == 19
    baseline = [row for row in verified if row["official_historical_dataset_replayed"] == "True"]
    assert len(baseline) == 14
    assert {(row["table_label"], row["quantitative_column_index"]) for row in baseline} == {
        *{("tab:tsla", str(index)) for index in range(1, 8)},
        *{("tab:btc", str(index)) for index in range(1, 8)},
    }
    assert {row["paper_protocol_period_match"] for row in baseline} == {"False"}
    live = [row for row in verified if row["official_historical_dataset_replayed"] == "False"]
    assert len(live) == 5
    assert {
        (row["row_label"], row["quantitative_column_index"]) for row in live
    } == {
        ("Acted days / exposure", "1"),
        ("Acted days / exposure", "2"),
        ("Hit rate (acted days)", "1"),
        ("Hit rate (acted days)", "2"),
        ("Max equity drawdown", "2"),
    }
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


def test_complete_public_histories_and_deleted_author_archive_are_audited() -> None:
    history = load_json("release_history_audit.json")
    assert history["author_space"]["commits"] == 5
    assert history["author_space"]["objects"] == 25
    assert history["author_space"]["paths"] == 13
    assert history["author_space"]["deleted_lfs_archive_sha256"] == (
        audit.AUTHOR_ARCHIVE_LFS_SHA256
    )
    assert history["author_space"]["deleted_lfs_archive_bytes"] == 9_356
    assert [row["path"] for row in history["author_space"]["deleted_lfs_archive_members"]] == [
        "app.py", "Dockerfile", "requirements.txt", "README.md"
    ]
    assert history["author_space"]["deleted_lfs_archive_contains_decisions_or_results"] is False

    assert history["dataset"]["commits"] == 103
    assert history["dataset"]["objects"] == 615
    assert history["dataset"]["paths"] == 4
    assert history["dataset"]["lfs_payload_revisions"] == 204
    assert history["dataset"]["lfs_payloads_verified"] == 204
    assert history["dataset"]["fully_covering_declared_period_revisions_per_asset"] == {
        "BTC": 20, "TSLA": 20
    }
    assert history["dataset"]["unique_declared_period_price_paths_among_full_revisions"] == {
        "BTC": 1, "TSLA": 1
    }
    assert history["dataset"]["full_declared_period_revisions_matching_printed_return"] == {
        "BTC": 0, "TSLA": 0
    }
    assert history["dataset"]["historical_action_or_result_paths"] == 0

    assert history["organizer"]["commits"] == 327
    assert history["organizer"]["objects"] == 1807
    assert history["organizer"]["paths"] == 104
    assert history["organizer"]["unique_ref_heads"] == 2
    assert history["organizer"]["historical_primitive_decision_or_result_paths"] == 0
    assert history["organizer"]["sole_data_json_value"] == []


def test_all_historical_dataset_payloads_pin_hidden_two_baseline_rows() -> None:
    revisions = rows("dataset_revision_lineage.csv")
    assert len(revisions) == 204
    assert Counter(row["asset"] for row in revisions) == {"TSLA": 102, "BTC": 102}
    assert {row["payload_verified_against_lfs_pointer"] for row in revisions} == {"True"}
    full = [row for row in revisions if row["fully_covers_declared_period"] == "True"]
    assert Counter(row["asset"] for row in full) == {"TSLA": 20, "BTC": 20}
    assert {row["declared_period_return_matches_printed"] for row in full} == {"False"}
    assert {
        asset: len({row["declared_period_price_sha256"] for row in full if row["asset"] == asset})
        for asset in ("TSLA", "BTC")
    } == {"TSLA": 1, "BTC": 1}
    recovered = {
        row["asset"]: row
        for row in revisions
        if row["recovered_table_baseline_revision"] == "True"
    }
    assert recovered["TSLA"]["commit"] == audit.OFFLINE_BASELINE_REVISIONS["TSLA"]["commit"]
    assert recovered["TSLA"]["dataset_end"] == "2026-05-20"
    assert recovered["TSLA"]["dataset_rows"] == "293"
    assert recovered["BTC"]["commit"] == audit.OFFLINE_BASELINE_REVISIONS["BTC"]["commit"]
    assert recovered["BTC"]["dataset_end"] == "2026-05-21"
    assert recovered["BTC"]["dataset_rows"] == "294"

    baseline = rows("offline_baseline_reproduction.csv")
    assert len(baseline) == 14
    assert Counter(row["asset"] for row in baseline) == {"TSLA": 7, "BTC": 7}
    assert {row["matches_at_display_precision"] for row in baseline} == {"True"}
    assert {row["paper_protocol_period_match"] for row in baseline} == {"False"}
    assert {row["paper_result_credit"] for row in baseline} == {"False"}
    assert {row["dataset_end"] for row in baseline if row["asset"] == "TSLA"} == {"2026-05-20"}
    assert {row["dataset_end"] for row in baseline if row["asset"] == "BTC"} == {"2026-05-21"}


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


def test_error_attribution_replay_recovers_five_full_cells_and_four_partial_components() -> None:
    replay = rows("error_attribution_replay.csv")
    assert len(replay) == 12
    exact = [row for row in replay if row["full_printed_cell_match"] == "True"]
    assert len(exact) == 5
    assert {(row["row_label"], row["asset"]) for row in exact} == {
        ("Acted days / exposure", "TSLA"),
        ("Acted days / exposure", "BTC"),
        ("Hit rate (acted days)", "TSLA"),
        ("Hit rate (acted days)", "BTC"),
        ("Max equity drawdown", "BTC"),
    }
    partial = [row for row in replay if row["verification_class"] == "partial_component_match_not_full_printed_cell"]
    assert len(partial) == 4
    assert {row["row_label"] for row in partial} == {
        "Long days: hit / total PnL", "Short days: hit / total PnL"
    }
    assert {row["matching_components"] for row in partial} == {"1"}
    assert all(row["paper_result_credit"] == "False" for row in replay)


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
    assert checks["live_error_attribution_denominators"]["status"] == (
        "mixed_conventions_exactly_replayed"
    )
    assert checks["declared_offline_period_vs_table_lineage"]["status"] == (
        "major_protocol_conflict"
    )
    assert checks["offline_baseline_mixed_asset_endpoints"]["status"] == (
        "exact_hidden_lineage_recovered"
    )
    assert checks["offline_ntr_semantics"]["status"] == (
        "label_and_protocol_conflict"
    )


def test_manifest_hashes_readme_and_builder_are_deterministic(tmp_path: Path) -> None:
    manifest = load_json("manifest.json")
    assert manifest["active_empirical_table_cells"] == 119
    assert manifest["empirical_figure_panels"] == 2
    assert manifest["paper_window_official_decision_rows_recovered"] == 97
    assert manifest["paper_window_official_rows_replayed_with_organizer_scorer"] == 97
    assert manifest["published_table_cells_regenerated"] == 19
    assert manifest["published_table_cells_verified_from_official_decisions_and_organizer_output"] == 5
    assert manifest["published_baseline_cells_regenerated_from_official_history"] == 14
    assert manifest["published_baseline_cells_regenerated_with_declared_endpoint"] == 0
    assert manifest["published_baseline_cells_regenerated_with_recovered_mixed_endpoints"] == 14
    assert manifest["author_space_history_commits"] == 5
    assert manifest["author_space_deleted_lfs_archive_recovered"] is True
    assert manifest["author_space_deleted_lfs_archive_contains_results"] is False
    assert manifest["official_dataset_history_commits"] == 103
    assert manifest["official_dataset_lfs_payloads_verified"] == 204
    assert manifest["official_dataset_full_declared_period_revisions_per_asset"] == {"BTC": 20, "TSLA": 20}
    assert manifest["official_dataset_full_declared_period_revisions_matching_printed_return"] == {"BTC": 0, "TSLA": 0}
    assert manifest["organizer_history_commits"] == 327
    assert manifest["organizer_historical_primitive_decision_or_result_paths"] == 0
    assert manifest["published_table_cells_reproduced_end_to_end_from_native_llm_pipeline"] == 0
    assert manifest["full_empirical_figure_panels_regenerated"] == 0
    assert manifest["strict_success"] is False
    assert manifest["generated_file_sha256"] == {
        path.name: file_sha256(path)
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "119 displayed empirical table cells", "Nineteen of 119 printed cells",
        "all 14 cells in the two offline Buy-and-Hold rows",
        "May-21 revision ending May 20", "May-22 revision ending May 21",
        "Three BTC HOLD votes become BUY", "99.96% extracted-token overlap",
        "strict_success` is false", "no native agent or ablation result is regenerated",
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
