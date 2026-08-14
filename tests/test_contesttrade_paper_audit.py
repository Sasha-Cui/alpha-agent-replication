from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_contesttrade_paper.py"
SPEC = importlib.util.spec_from_file_location("contesttrade_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_targets_cover_all_numeric_cells_in_tables_1_through_3() -> None:
    rows = audit.paper_result_rows()
    assert len(rows) == 49
    assert Counter(row["paper_table"] for row in rows) == {1: 27, 2: 4, 3: 18}
    assert len({(row["paper_table"], row["entity"], row["metric"]) for row in rows}) == 49
    figures = audit.paper_figure_rows()
    assert Counter(row["figure"] for row in figures) == {
        "main performance raster": 9,
        "ablation raster": 6,
    }
    assert {row["paper_result_credit"] for row in figures} == {False}


def test_zi_reward_semantics_expose_the_released_divergence() -> None:
    pairs = [(2.0, 5.0), (-2.0, -5.0)]
    assert audit.paper_zi_reward(pairs) == 20.0
    assert audit.released_zi_reward(pairs) == 5.0
    assert audit.paper_zi_reward([(-2.0, 5.0)]) == -10.0
    assert audit.released_zi_reward([(-2.0, 5.0)]) == 0.0
    assert audit.paper_zi_reward([(2.0, 5.0)]) == audit.released_zi_reward([(2.0, 5.0)])
    assert audit.paper_zi_reward([(1.0, 25.0)]) == 25.0
    assert audit.released_zi_reward([(1.0, 25.0)]) == 20.0


def test_committed_audit_preserves_the_native_result_boundary() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/contesttrade"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "tables_1_3_conformance.csv")
    identities = read_csv(output / "paper_internal_consistency.csv")
    figures = read_csv(output / "paper_figure_series_inventory.csv")
    paper_versions = read_csv(output / "official_paper_version_inventory.csv")
    milestones = read_csv(output / "public_source_milestone_inventory.csv")
    history_commits = read_csv(output / "public_source_history_commit_inventory.csv")
    history_paths = read_csv(output / "public_source_history_path_inventory.csv")
    history = json.loads((output / "public_source_history.json").read_text(encoding="utf-8"))
    fork_repositories = read_csv(output / "public_fork_repository_access_inventory.csv")
    fork_refs = read_csv(output / "public_fork_ref_snapshot.csv")
    fork_heads = read_csv(output / "public_fork_unique_head_inventory.csv")
    fork_commits = read_csv(output / "public_fork_divergent_commit_inventory.csv")
    fork_paths = read_csv(output / "public_fork_divergent_path_inventory.csv")
    fork_census = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))
    reachability = read_csv(output / "source_entrypoint_reachability.csv")
    zi_rows = read_csv(output / "zi_reward_semantics_audit.csv")
    models = read_csv(output / "shipped_lightgbm_model_inventory.csv")
    caches = read_csv(output / "released_cache_inventory.csv")
    config = read_csv(output / "source_config_conformance.csv")
    source = read_csv(output / "released_source_inventory.csv")

    assert manifest["overall_status"] == "not_reproduced_public_entrypoint_omits_contests"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_result_cells_total"] == 49
    assert manifest["paper_numeric_figure_series_total"] == 15
    assert manifest["paper_result_display_units_total"] == 64
    assert manifest["native_paper_result_cells_reproduced"] == 0
    assert manifest["native_numeric_figure_series_reproduced"] == 0
    assert manifest["native_paper_result_display_units_reproduced"] == 0
    assert manifest["paper_numeric_result_cells_unavailable"] == 49
    assert manifest["paper_internal_repeated_cells_consistent"] == 3
    assert manifest["data_contest_reachable_from_public_entrypoint"] is False
    assert manifest["research_contest_reachable_from_public_entrypoint"] is False
    assert manifest["active_portfolio_constructor_present"] is False
    assert manifest["research_contest_required_model_files_present"] is False
    assert manifest["research_predict_signal_scores_method_present"] is False
    assert manifest["audit_unpickled_shipped_models"] is False
    assert manifest["audit_called_llm_or_external_api"] is False
    assert manifest["official_paper_versions_audited"] == 4
    assert manifest["official_paper_pdf_pages_total"] == 35
    assert manifest["official_paper_source_files_total"] == 47
    assert manifest["paper_result_values_stable_across_all_versions"] is True
    assert manifest["public_source_reachable_commits_total"] == 130
    assert manifest["public_source_unique_historical_paths_total"] == 132
    assert manifest["public_source_reachable_blobs_total"] == 322
    assert manifest["public_source_reachable_trees_total"] == 267
    assert manifest["public_source_reachable_commit_objects_total"] == 130
    assert manifest["public_source_reachable_tag_objects_total"] == 1
    assert manifest["public_source_unreachable_objects_total"] == 0
    assert manifest["public_source_native_structured_result_paths"] == 0
    assert manifest["public_source_text_blobs_with_complete_paper_result_row"] == 0
    assert manifest["public_fork_rest_repository_listings"] == 157
    assert manifest["public_forks_accessible"] == 153
    assert manifest["public_fork_stale_or_inaccessible_rest_listings"] == 4
    assert manifest["public_fork_branch_refs_audited"] == 186
    assert manifest["public_fork_tag_refs_audited"] == 26
    assert manifest["public_fork_unique_heads_audited"] == 52
    assert manifest["public_fork_divergent_heads_audited"] == 21
    assert manifest["public_fork_divergent_commits_audited"] == 88
    assert manifest["public_fork_divergent_paths_audited"] == 200
    assert manifest["public_fork_new_blobs_audited"] == 381
    assert manifest["public_fork_new_text_blobs_with_complete_paper_result_row"] == 0
    assert manifest["public_fork_exact_official_paper_v3_pdf_copies"] == 1
    assert manifest["public_fork_date_loop_backtest_heads"] == 2
    assert manifest["public_fork_date_loop_backtest_constructs_paper_portfolio_or_metrics"] is False
    assert manifest["public_fork_native_nonpaper_personal_portfolio_paths"] == 1
    assert manifest["public_fork_runtime_failure_diagnostic_paths"] == 3
    assert manifest["public_fork_heads_integrating_data_contest"] == 0
    assert manifest["public_fork_heads_integrating_research_contest"] == 0
    assert manifest["public_fork_heads_with_required_research_models"] == 0
    assert manifest["public_fork_heads_with_research_predict_signal_scores_method"] == 0
    assert manifest["public_fork_heads_with_facility_location_allocator"] == 0
    assert manifest["public_fork_native_paper_result_artifacts_found"] == 0
    assert manifest["public_fork_paper_result_credit"] is False
    assert manifest["public_repository_exact_original_v1_result_raster"] is True
    assert manifest["public_repository_author_raster_series_correspondences"] == 9
    assert manifest["public_repository_raw_numeric_curve_files"] == 0
    assert manifest["paper_v1_predates_public_repository"] is True
    assert manifest["paper_v2_data_and_research_contest_source_present_at_submission"] is False
    assert manifest["paper_v3_data_and_research_contest_source_present_at_submission"] is False

    assert len(conformance) == 49
    assert {row["status"] for row in conformance} == {"unavailable_missing_native_result_path"}
    assert len(identities) == 3
    assert {row["status"] for row in identities} == {
        "paper_internal_identity_match_not_independent_reproduction"
    }
    assert Counter(row["status"] for row in zi_rows) == {"semantic_mismatch": 3, "match": 1}
    assert len(models) == 2
    assert {row["expected_five_feature_set"] for row in models} == {"True"}
    assert {row["safe_inspection_only"] for row in models} == {"True"}
    assert len(caches) == 7
    assert len(source) == 117
    assert len(config) == 29
    assert len(figures) == 15
    assert {row["paper_result_credit"] for row in figures} == {"False"}
    assert len(paper_versions) == 4
    assert {row["displayed_table_cells"] for row in paper_versions} == {"49"}
    assert {row["displayed_figure_series"] for row in paper_versions} == {"15"}
    assert {row["result_values_same_as_v4"] for row in paper_versions} == {"True"}
    assert [row["public_repository_commits_at_submission"] for row in paper_versions] == [
        "0",
        "36",
        "53",
        "130",
    ]
    assert len(milestones) == 6
    assert len(history_commits) == 130
    assert len(history_paths) == 132
    assert sum(row["exact_original_v1_result_raster"] == "True" for row in history_paths) == 1
    assert {row["native_structured_result_path"] for row in history_paths} == {"False"}
    assert history["reachable_object_counts"] == {
        "blob": 322,
        "commit": 130,
        "tag": 1,
        "tree": 267,
    }
    assert history["paper_result_credit"] is False

    assert len(fork_repositories) == 157
    assert Counter(row["accessible_via_git"] for row in fork_repositories) == {
        "True": 153,
        "False": 4,
    }
    assert {
        row["repository"]
        for row in fork_repositories
        if row["accessible_via_git"] == "False"
    } == audit.PUBLIC_FORK_INACCESSIBLE_REPOSITORIES
    assert Counter(row["ref_kind"] for row in fork_refs) == {"branch": 186, "tag": 26}
    assert Counter(row["relation_to_official_history"] for row in fork_refs) == {
        "official_history_reachable": 191,
        "divergent": 21,
    }
    assert len(fork_heads) == 52
    assert Counter(row["relation_to_official_history"] for row in fork_heads) == {
        "official_head_exact": 1,
        "official_history_reachable": 30,
        "divergent": 21,
    }
    assert sum(row["date_loop_backtest_command_present"] == "True" for row in fork_heads) == 2
    assert sum(
        row["native_nonpaper_personal_portfolio_ledger_present"] == "True"
        for row in fork_heads
    ) == 1
    assert {row["data_contest_called_from_main"] for row in fork_heads} == {"False"}
    assert {row["research_contest_called_from_main"] for row in fork_heads} == {"False"}
    assert {row["research_model_files"] for row in fork_heads} == {"0"}
    assert {row["research_predict_signal_scores_method"] for row in fork_heads} == {"False"}
    assert {row["facility_location_allocator_present"] for row in fork_heads} == {"False"}
    assert {row["native_paper_result_artifact_present"] for row in fork_heads} == {"False"}
    assert len(fork_commits) == 88
    assert {row["complete_paper_result_row_hits"] for row in fork_commits} == {"0"}
    assert {row["native_paper_result_artifact_present"] for row in fork_commits} == {"False"}
    assert len(fork_paths) == 200
    paths_by_name = {row["path"]: row for row in fork_paths}
    assert paths_by_name["2508.00554v3.pdf"]["exact_official_paper_v3_pdf_copy"] == "True"
    assert paths_by_name["cli/main.py"]["date_loop_backtest_source"] == "True"
    assert (
        paths_by_name["agents_workspace/portfolio.json"][
            "native_nonpaper_personal_portfolio_ledger"
        ]
        == "True"
    )
    assert sum(row["runtime_failure_diagnostic"] == "True" for row in fork_paths) == 3
    assert {row["native_paper_result_artifact"] for row in fork_paths} == {"False"}
    assert fork_census["divergent_new_object_counts"] == {
        "blob": 381,
        "commit": 88,
        "tree": 292,
    }
    assert fork_census["new_text_blobs_with_complete_paper_result_row"] == 0
    assert fork_census["native_nonpaper_personal_portfolio_semantics"] == [
        {
            "ai_records": 7,
            "blob": "614ce068753a48f36f9f5d93ad7e7921fc9b328b",
            "daily_stat_records": 21,
            "first_date": "2026-02-02",
            "history_records": 16,
            "last_date": "2026-02-03",
            "manual_records": 9,
        },
        {
            "ai_records": 7,
            "blob": "c1ffddd4b5b7950d671b33cbfa0e3aca17691011",
            "daily_stat_records": 25,
            "first_date": "2026-02-02",
            "history_records": 16,
            "last_date": "2026-02-04",
            "manual_records": 9,
        },
    ]

    reach = {row["check"]: row for row in reachability}
    assert reach["active_workflow_nodes"]["status"] == "mismatch_contests_and_portfolio_absent"
    assert reach["data_contest_reachable"]["observed"] == "False"
    assert reach["research_contest_reachable"]["observed"] == "False"
    assert reach["research_model_files"]["status"] == "missing_both_required_models"
    assert reach["research_predict_signal_scores_method"]["status"] == "missing_called_method"

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_source_static_checks_when_source_is_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/contesttrade_source")
    versions_root = Path(
        "/nfs/roberts/scratch/pi_btk22/zc362/contesttrade_paper_versions"
    )
    if not source_root.exists() or not versions_root.exists():
        return
    rows = audit.entrypoint_reachability(source_root)
    checks = {row["check"]: row for row in rows}
    assert checks["public_cli_import"]["observed"] == "True"
    assert checks["active_workflow_nodes"]["observed"] == (
        "['run_data_agents', 'run_research_agents', 'finalize']"
    )
    assert audit.git_head(source_root) == audit.SOURCE_COMMIT
    versions = audit.paper_version_inventory(versions_root, source_root)
    commits, paths, history = audit.public_source_history(source_root)
    assert len(versions) == 4
    assert len(commits) == 130
    assert len(paths) == 132
    assert history["native_structured_result_paths"] == 0
    assert history["independently_regenerated_paper_results"] == 0
    snapshot = versions_root / "public_fork_snapshot.json"
    if snapshot.exists():
        repositories, refs, heads, fork_commits, fork_paths, fork_summary = (
            audit.public_fork_audit(source_root, snapshot)
        )
        assert len(repositories) == 157
        assert len(refs) == 212
        assert len(heads) == 52
        assert len(fork_commits) == 88
        assert len(fork_paths) == 200
        assert fork_summary["native_paper_result_artifacts_found"] == 0


def test_contesttrade_fork_audit_is_routed_to_the_frozen_ledgers() -> None:
    native_rows = read_csv(
        ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
    )
    native = next(row for row in native_rows if row["system_id"] == "SYS-CONTEST-TRADE")
    expected_status = (
        "paper_audit:completed_zero_of_64_result_display_units_153_accessible_forks_"
        "212_refs_52_unique_heads_21_divergent_heads_exhausted"
    )
    assert native["targeted_execution_audit_status"] == expected_status
    assert "All 21 divergent heads, 88 extra commits, 200 changed paths" in native[
        "concise_evidence_note"
    ]
    assert "381 new blobs" in native["concise_evidence_note"]
    assert "mixed manual/AI personal portfolio ledger" in native[
        "concise_evidence_note"
    ]

    route_rows = read_csv(
        ROOT
        / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv"
    )
    route = next(row for row in route_rows if row["system_ids"] == "SYS-CONTEST-TRADE")
    assert route["native_execution_audit_status"] == expected_status
    assert route["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert route["good_faith_reconstruction"] == "yes"
    assert route["proxy_role"] == "secondary_diagnostic_after_native_review"
