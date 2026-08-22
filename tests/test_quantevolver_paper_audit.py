from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_quantevolver_paper.py"
SPEC = importlib.util.spec_from_file_location("quantevolver_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_numeric_table_denominator_is_complete_and_fail_closed() -> None:
    rows = audit.paper_table_rows()
    assert len(rows) == 75
    assert Counter(row["paper_table"] for row in rows) == {
        "Overall Evaluation": 60,
        "Ablation Results on Dataset B": 15,
    }
    assert Counter(row["method"] for row in rows if row["paper_table"] == "Overall Evaluation") == {
        "AlphaBench": 12,
        "QuantaAlpha": 12,
        "R&D-Agent": 12,
        "Alpha-Jungle": 12,
        "QuantEvolver": 12,
    }
    assert len(
        {
            (row["paper_table"], row["method"], row["benchmark"], row["metric"])
            for row in rows
        }
    ) == 75
    assert {row["paper_result_credit"] for row in rows} == {False}


def test_ablation_and_non_table_claim_censuses_are_explicit() -> None:
    design = audit.ablation_design_rows()
    claims = audit.published_non_table_claims()
    assert len(design) == 15
    assert Counter(row["component"] for row in design) == {"Seed": 5, "Div": 5, "DSL": 5}
    assert {row["native_paper_run_reproduced"] for row in design} == {False}
    assert len(claims) == 42
    assert Counter(row["claim_role"] for row in claims) == {
        "result": 31,
        "configuration": 11,
    }
    assert {row["paper_result_credit"] for row in claims} == {False}


def test_internal_checks_expose_arithmetic_and_metric_conflicts() -> None:
    checks = {row["check"]: row for row in audit.internal_consistency_checks()}
    assert len(checks) == 9
    assert round(checks["Benchmark A improvement claim versus Table Overall"]["recomputed_value"], 2) == 1.20
    assert round(checks["Benchmark B best-RankIC improvement claim versus Table Overall"]["recomputed_value"], 2) == 73.89
    assert checks["Miner/backbone model identity"]["status"] == "paper_internal_configuration_conflict"
    assert checks["published ICIR versus released cross-sectional evaluator"]["status"] == "paper_source_metric_conflict"
    assert checks["Benchmark A IC/RankIC definitions"]["status"] == "paper_metric_definition_incomplete"
    assert checks["profitability return and rounded ending NAV"]["status"] == "compatible_at_display_precision"


def test_committed_audit_is_self_hashing_and_component_gate_is_separate() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/quantevolver"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    table = read_csv(output / "paper_numeric_table_conformance.csv")
    design = read_csv(output / "ablation_design_cells.csv")
    claims = read_csv(output / "published_non_table_claims.csv")
    checks = read_csv(output / "paper_internal_and_source_checks.csv")
    gaps = read_csv(output / "paper_specification_gaps.csv")
    mechanisms = read_csv(output / "source_mechanism_conformance.csv")
    inventory = read_csv(output / "released_source_inventory.csv")
    history = read_csv(output / "released_source_history_inventory.csv")
    fork_branches = read_csv(output / "public_fork_branch_ref_snapshot.csv")
    fork_heads = read_csv(output / "public_fork_unique_head_inventory.csv")
    fork_census = json.loads((output / "public_fork_census.json").read_text(encoding="utf-8"))
    paper_assets = read_csv(output / "paper_source_asset_inventory.csv")
    native = json.loads((output / "native_component_execution.json").read_text(encoding="utf-8"))
    freeze = (output / "reconstructed_environment_freeze.txt").read_text(
        encoding="utf-8"
    )
    component = json.loads((output / "separate_component_gate.json").read_text(encoding="utf-8"))

    assert manifest["overall_status"] == "not_reproduced_substantial_public_framework_zero_paper_results"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_era_source_revision_available"] is True
    assert manifest["source_commit"] == audit.SOURCE_COMMIT
    assert manifest["source_history_commits"] == 2
    assert manifest["source_history_commits_audited"] == 2
    assert manifest["source_history_result_or_data_artifact_paths"] == 0
    assert manifest["source_history_paper_result_literal_hits_outside_bundled_pdf"] == 0
    assert manifest["source_history_paper_result_artifacts_found"] == 0
    assert manifest["public_forks_reported_by_github_rest"] == 4
    assert manifest["public_forks_accessible"] == 4
    assert manifest["public_fork_branch_refs_audited"] == 4
    assert manifest["public_fork_tag_refs_audited"] == 0
    assert manifest["public_fork_unique_heads_audited"] == 1
    assert manifest["public_fork_divergent_heads_audited"] == 0
    assert manifest["public_fork_unique_commits_beyond_official_history"] == 0
    assert manifest["public_fork_unique_blobs_beyond_official_history"] == 0
    assert manifest["public_fork_native_result_artifacts_found"] is False
    assert manifest["public_fork_paper_result_credit"] is False
    assert manifest["paper_numeric_table_cells_total"] == 75
    assert manifest["native_paper_table_result_cells_reproduced"] == 0
    assert manifest["published_non_table_result_claims_total"] == 31
    assert manifest["native_non_table_result_claims_reproduced"] == 0
    assert manifest["paper_specification_gaps_total"] == 35
    assert manifest["numeric_result_figure_panels_total"] == 5
    assert manifest["numeric_result_figure_arrays_shipped"] == 0
    assert manifest["source_mechanism_dimensions_total"] == 67
    assert manifest["source_mechanism_matches_or_analogues"] == 38
    assert manifest["source_mechanism_status_counts"] == {
        "exact_or_direct_match": 33,
        "substantial_analogue": 5,
        "absent": 25,
        "conflict": 2,
        "unverifiable": 2,
    }
    assert manifest["tracked_source_files_total"] == 67
    assert manifest["tracked_source_python_files_total"] == 55
    assert manifest["tracked_source_upstream_test_files_total"] == 3
    assert manifest["native_source_dependency_environment_reproduced"] is True
    assert manifest["native_source_exact_historical_dependency_versions_recovered"] is False
    assert manifest["native_source_modules_imported_with_real_dependencies"] == 52
    assert manifest["native_rft_task_bank_tasks_prepared"] == 9
    assert manifest["native_rft_training_prompt_rows_prepared"] == 16
    assert manifest["native_rft_validation_prompt_rows_prepared"] == 4
    assert manifest["native_rft_verl_dataset_subclass_resolved"] is True
    assert manifest["native_full_gpu_training_environment_reproduced"] is False
    assert manifest["separate_component_gate_counted"] == 3
    assert manifest["separate_component_gate_passed"] is True
    assert manifest["separate_component_gate_grade"] == "B"
    assert manifest["separate_component_gate_paper_result_credit"] is False

    assert len(table) == 75
    assert {row["paper_result_credit"] for row in table} == {"False"}
    assert len(design) == 15
    assert len(claims) == 42
    assert len(checks) == 9
    assert len(gaps) == 35
    assert len(mechanisms) == 67
    assert Counter(row["paper_mechanism_credit"] for row in mechanisms) == {
        "True": 38,
        "False": 29,
    }
    assert len(inventory) == 67
    assert sum(row["python_source"] == "True" for row in inventory) == 55
    assert len(history) == 2
    assert [int(row["tracked_paths"]) for row in history] == [1, 67]
    assert [int(row["python_paths"]) for row in history] == [0, 55]
    assert {row["result_or_data_artifact_paths"] for row in history} == {"0"}
    assert {row["paper_result_literal_hits_outside_bundled_pdf"] for row in history} == {"0"}
    assert {row["paper_result_artifact_found"] for row in history} == {"False"}
    assert len(fork_branches) == 4
    assert {row["repository"] for row in fork_branches} == set(
        audit.PUBLIC_FORK_REPOSITORIES
    )
    assert {row["head_commit"] for row in fork_branches} == {audit.SOURCE_COMMIT}
    assert {row["relation_to_official_head"] for row in fork_branches} == {
        "official_head_exact"
    }
    assert {row["unique_commits_beyond_official_history"] for row in fork_branches} == {
        "0"
    }
    assert {row["unique_blobs_beyond_official_history"] for row in fork_branches} == {
        "0"
    }
    assert {row["native_result_artifact_found"] for row in fork_branches} == {"False"}
    assert {row["paper_result_credit"] for row in fork_branches} == {"False"}
    assert len(fork_heads) == 1
    assert fork_heads[0]["head_commit"] == audit.SOURCE_COMMIT
    assert fork_heads[0]["branch_ref_count"] == "4"
    assert fork_census["census_date"] == "2026-08-14"
    assert fork_census["github_rest_reported_forks"] == 4
    assert fork_census["accessible_branch_refs"] == 4
    assert fork_census["tag_refs"] == 0
    assert fork_census["unique_heads"] == 1
    assert fork_census["official_head_exact_unique_heads"] == 1
    assert fork_census["divergent_unique_heads"] == 0
    assert fork_census["native_result_artifacts_found"] == 0
    assert fork_census["paper_result_credit"] is False
    assert len(paper_assets) == 10
    assert sum(row["asset_role"] == "numeric_result_figure" for row in paper_assets) == 5
    assert {row["underlying_numeric_array_shipped"] for row in paper_assets} == {"False"}

    assert native["tracked_python_files_compiled"] == 55
    assert native["compile_status"] == "passed_in_reconstructed_declared_environment"
    assert native["upstream_tests_status"] == "passed"
    assert native["pip_check"] == "No broken requirements found."
    assert native["dependency_environment_reproduced"] is True
    assert native["declared_all_environment_reconstructed"] is True
    assert native["compatible_verl_environment_reconstructed"] is True
    assert native["exact_historical_dependency_versions_recovered"] is False
    assert native["full_gpu_training_environment_reproduced"] is False
    assert native["dependency_freeze_sha256"] == audit.RECONSTRUCTED_ENV_FREEZE_SHA256
    assert native["dependency_freeze_lines"] == 119
    assert len(freeze.splitlines()) == 119
    assert audit.sha256_bytes(freeze.encode()) == audit.RECONSTRUCTED_ENV_FREEZE_SHA256
    assert native["public_quickstart_component"]["valid_seeds"] == 3
    assert native["public_quickstart_component"]["invalid_seeds"] == 1
    assert native["public_quickstart_component"]["example_task_bank_tasks"] == 9
    assert native["deterministic_released_seed_dsl_components"] is True
    real = native["real_dependency_component"]
    assert real["imported_source_modules"] == 52
    assert real["vllm_installed"] is False
    assert real["verl_dataset_subclass"] is True
    assert real["task_bank_tasks"] == 9
    assert real["train_prompt_rows"] == 16
    assert real["validation_prompt_rows"] == 4
    assert real["advantage_estimator"] == "grpo"
    assert real["rollout_backend"] == "vllm"
    assert real["torch_cuda_available"] is False
    assert real["ray_initialized"] is False
    assert real["network_attempts"] == []
    assert native["paper_result_reproduction"] is False

    assert component["counted_components"] == 3
    assert component["grade_a_or_b"] == 3
    assert component["pass_rate"] == 1.0
    assert component["native_agent_replication"] is False
    assert component["search_or_RFT_replication"] is False
    assert component["paper_result_reproduction"] is False

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_primary_sources_when_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantevolver_source")
    paper_source = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantevolver_paper/source")
    if not source_root.exists() or not paper_source.exists():
        return
    assert str(audit.run_git(source_root, "rev-parse", "HEAD")).strip() == audit.SOURCE_COMMIT
    assert str(audit.run_git(source_root, "ls-tree", "-r", "--name-only", audit.README_ONLY_COMMIT)).splitlines() == [
        "README.md"
    ]
    assert len(audit.source_inventory(source_root)) == 67
    assert len(audit.source_history_inventory(source_root)) == 2
    branches, heads, summary = audit.public_fork_audit(source_root)
    assert len(branches) == 4
    assert len(heads) == 1
    assert summary["native_result_artifacts_found"] == 0
    assert len(audit.paper_source_inventory(paper_source)) == 10
    source_python = Path(audit.DEFAULT_SOURCE_PYTHON)
    if source_python.is_file():
        native = audit.native_component_checks(source_root, source_python)
        assert native["dependency_environment_reproduced"] is True
        assert native["real_dependency_component"]["network_attempts"] == []
