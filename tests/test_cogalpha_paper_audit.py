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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/cogalpha"
SPEC = importlib.util.spec_from_file_location(
    "audit_cogalpha_paper", ROOT / "scripts/audit_cogalpha_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_two_edition_denominators_keep_native_credit_zero() -> None:
    data = manifest()
    assert data["editions"] == {
        "arxiv_v1": {
            "additional_unique_prose_numeric_units": 8,
            "figure_line_series": 4,
            "native_empirical_units_regenerated": 0,
            "table_cells": 150,
            "total_unique_empirical_units": 150,
            "unique_table_cells_after_declared_repeats": 138,
        },
        "arxiv_v4_acl_final": {
            "additional_unique_prose_numeric_units": 32,
            "figure_line_series": 4,
            "native_empirical_units_regenerated": 0,
            "table_cells": 298,
            "total_unique_empirical_units": 306,
            "unique_table_cells_after_declared_repeats": 270,
        },
    }
    tables = rows("published_table_result_ledger.csv")
    assert Counter((row["edition"], row["table"]) for row in tables) == {
        ("arxiv_v1", "main_baselines"): 120,
        ("arxiv_v1", "ablation"): 30,
        ("arxiv_v4_acl_final", "main_baselines"): 132,
        ("arxiv_v4_acl_final", "ablation"): 30,
        ("arxiv_v4_acl_final", "hyperparameters"): 32,
        ("arxiv_v4_acl_final", "cross_dataset"): 104,
    }
    assert Counter(row["duplicate_kind"] for row in tables) == {
        "none": 408,
        "exact_repeat_of_main_table": 40,
    }
    assert all(row["native_pipeline_executed"] == "False" for row in tables)
    assert all(row["native_result_regenerated"] == "False" for row in tables)
    assert all(row["paper_result_credit"] == "False" for row in tables)


def test_primary_source_lineage_records_v1_defect_and_current_rebuild() -> None:
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    arxiv = provenance["arxiv"]
    assert arxiv["versions"] == 4
    assert arxiv["v1_pages"] == 27
    assert arxiv["v1_unmodified_rebuild"] is False
    assert "numeric main.bbl" in arxiv["v1_build_blocker"]
    assert arxiv["v4_pages"] == arxiv["v4_rebuild_pages"] == 35
    assert arxiv["v4_unmodified_rebuild"] is True
    assert arxiv["v4_rebuild_extracted_token_multiset_jaccard"] > 0.9996
    assert arxiv["acl_final_pages"] == 35
    assert arxiv["v4_to_acl_final_extracted_token_multiset_jaccard"] > 0.994
    assert arxiv["visual_qa"] == {
        "editions_inspected": 3,
        "pages_inspected": 97,
        "unreadable_blank_clipped_or_overlapping_pages": 0,
    }


def test_author_prompt_release_gets_specification_not_runtime_credit() -> None:
    prompts = rows("prompt_release_inventory.csv")
    assert len(prompts) == manifest()["author_prompt_template_count"] == 39
    assert Counter(row["family"] for row in prompts) == {
        "seven_level_agent_hierarchy": 22,
        "shared": 11,
        "multi_agent_quality_checker": 4,
        "thinking_evolution": 2,
    }
    assert all(
        row["release_commit"] == "6294d9ffa9dfc286fb14e82343f8f22a5f928c1c"
        for row in prompts
    )
    assert all(row["postdates_arxiv_v1"] == "True" for row in prompts)
    assert all(row["postdates_arxiv_v4"] == "True" for row in prompts)
    assert all(row["native_prompt_specification_credit"] == "True" for row in prompts)
    assert all(row["runtime_model_call_replayed"] == "False" for row in prompts)
    assert all(row["paper_result_credit"] == "False" for row in prompts)
    release = json.loads((AUDIT_DIR / "source_provenance.json").read_text())[
        "prompt_release"
    ]
    assert release["commit_count"] == 1
    assert release["license"] is None
    assert release["runtime_code_included"] is False
    assert release["datasets_included"] is False
    assert release["experiment_outputs_included"] is False
    assert release["complete_public_history_audited"] is True
    assert release["public_history_commits"] == 1
    assert release["public_history_tracked_paths"] == 47
    assert release["public_history_archive_snapshot_paths_exact"] == 47
    assert release["public_history_result_artifacts_found"] == 0
    assert release["public_forks_accessible"] == 1
    assert release["public_fork_branch_refs_audited"] == 1
    assert release["public_fork_unique_heads_audited"] == 1
    assert release["public_fork_divergent_heads_audited"] == 0
    assert release["public_fork_native_result_artifacts_found"] is False
    assert release["public_fork_paper_result_credit"] is False


def test_complete_prompt_history_and_sole_public_fork_add_no_result_lineage() -> None:
    history = rows("released_source_history_inventory.csv")
    forks = rows("public_fork_branch_ref_snapshot.csv")
    census = json.loads((AUDIT_DIR / "public_fork_census.json").read_text())
    assert len(history) == 1
    assert history[0]["commit"] == audit.PROMPT_COMMIT
    assert history[0]["tracked_paths"] == "47"
    assert history[0]["markdown_paths"] == "45"
    assert history[0]["archive_snapshot_paths_exact"] == "47"
    assert history[0]["structured_result_or_data_payload_paths"] == "0"
    assert history[0]["distinctive_paper_result_literal_hits"] == "0"
    assert history[0]["native_result_artifact_found"] == "False"
    assert history[0]["paper_result_credit"] == "False"
    assert len(forks) == 1
    assert forks[0]["repository"] == audit.PUBLIC_FORK_REPOSITORY
    assert forks[0]["head_commit"] == audit.PROMPT_COMMIT
    assert forks[0]["relation_to_official_head"] == "official_head_exact"
    assert forks[0]["commits_ahead_of_official"] == "0"
    assert forks[0]["commits_behind_official"] == "0"
    assert forks[0]["unique_commits_beyond_official_history"] == "0"
    assert forks[0]["unique_blobs_beyond_official_history"] == "0"
    assert forks[0]["native_result_artifact_found"] == "False"
    assert forks[0]["paper_result_credit"] == "False"
    assert census["census_date"] == "2026-08-14"
    assert census["official_history_commits"] == 1
    assert census["official_history_tracked_paths"] == 47
    assert census["official_history_archive_snapshot_paths_exact"] == 47
    assert census["official_history_result_artifacts_found"] == 0
    assert census["github_rest_reported_forks"] == 1
    assert census["accessible_public_forks"] == 1
    assert census["accessible_branch_refs"] == 1
    assert census["tag_refs"] == 0
    assert census["unique_heads"] == 1
    assert census["official_head_exact_unique_heads"] == 1
    assert census["divergent_unique_heads"] == 0
    assert census["unique_commits_beyond_official_history"] == 0
    assert census["unique_blobs_beyond_official_history"] == 0
    assert census["native_result_artifacts_found"] == 0
    assert census["paper_result_credit"] is False
    data = manifest()
    assert data["repository_history_commits_audited"] == 1
    assert data["repository_history_archive_snapshot_paths_exact"] == 47
    assert data["repository_history_result_artifacts_found"] == 0
    assert data["public_forks_accessible"] == 1
    assert data["public_fork_native_result_artifacts_found"] is False
    assert data["public_fork_paper_result_credit"] is False


def test_components_execute_without_becoming_paper_results() -> None:
    component = json.loads((AUDIT_DIR / "component_execution.json").read_text())
    assert component["published_factor_listings_executed"] == 3
    assert component["computed"] == {
        "factor_dayhigh_impact_per_vol": [0.04, 0.03],
        "factor_price_impact_per_vol_tanh_1d": [
            0.000909090659,
            0.000263157889,
        ],
        "factor_upward_impact_per_vol": [0.01, 0.025],
    }
    prompt = component["prompt_component"]
    assert prompt["family"] == "seven_level_agent_hierarchy/agent_market_cycle"
    assert prompt["assembled_user_prompt_bytes"] > 4000
    assert prompt["unresolved_declared_placeholders"] == []
    assert prompt["model_request_sent"] is False
    assert prompt["model_response_received"] is False
    assert component["paper_input_used"] is False
    assert component["native_experiment_runner_used"] is False
    assert component["paper_result_credit"] is False


def test_author_curve_asset_is_correspondence_not_regeneration() -> None:
    evidence = rows("published_prose_figure_ledger.csv")
    curves = [row for row in evidence if row["metric"] == "line_series"]
    assert len(curves) == 8
    assert {row["result"] for row in curves} == {
        "65-80 Strategy",
        "80-90 Strategy",
        "85-95 Strategy",
        "Benchmark",
    }
    assert all(row["author_output_correspondence"] == "True" for row in curves)
    assert all(row["native_result_regenerated"] == "False" for row in curves)
    assert all(row["paper_result_credit"] == "False" for row in curves)
    assert manifest()["author_output_curve_series_correspondence"] == 4
    assert manifest()["author_output_curve_series_regenerated"] == 0


def test_method_and_claim_checks_fail_closed() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 35
    for dimension in (
        "runtime_source",
        "exact_dependency_lock",
        "point_in_time_data_snapshot",
        "universe_membership",
        "immutable_model_checkpoint",
        "runtime_requests_responses",
        "sampling_parameters",
        "random_seeds",
        "initial_factor_pool",
        "evolved_factor_pool",
        "quality_checker_outputs",
        "predictions",
        "portfolio_returns",
        "raw_result_arrays",
        "full_end_to_end_pipeline",
    ):
        assert methods[dimension]["status"] == "missing"
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["v1_source_rebuild"]["status"] == "fails_unmodified"
    assert checks["v4_source_rebuild"]["status"] == "passes"
    assert checks["v1_all_metric_superiority"]["status"] == "contradicted"
    assert checks["v4_all_metric_superiority"]["status"] == "qualified_in_prose"
    assert checks["significantly_improved_factor"]["status"] == (
        "no_statistical_test"
    )
    assert checks["source_code_release_claim"]["status"] == (
        "prompt_only_release"
    )
    assert checks["single_round_randomness"]["status"] == "not_reproducible"


def test_discovery_boundary_identifies_only_prompt_release() -> None:
    discovery = rows("discovery_evidence.csv")
    assert len(discovery) == 7
    recovered = [
        row
        for row in discovery
        if row["attributable_native_artifact_recovered"] == "True"
    ]
    assert len(recovered) == 1
    assert recovered[0]["route"] == "author_prompt_repository"
    assert recovered[0]["finding"] == "prompt_templates_only"
    assert all("not proof" in row["negative_search_limit"] for row in discovery)


def test_generator_is_deterministic_and_strict_mode_fails_closed(
    tmp_path: Path,
) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned CogAlpha primary-source scratch is only available on Bouchet")
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
            str(ROOT / "scripts/audit_cogalpha_paper.py"),
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


def test_manifest_hashes_outputs_and_readme_states_boundary() -> None:
    data = manifest()
    expected = {
        path.name
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "native CogAlpha experiments are **not reproduced**" in text
    assert "0/150 and 0/306" in text
    assert "39 attributable prompt templates" in text
    assert "complete public Git surface was also exhausted" in text
    assert "all 47 Git paths are" in text
    assert "one accessible fork with one branch" in text
    assert "zero unique commits, zero unique blobs" in text
    assert "4/4" in text
    assert "No local proxy" in text
