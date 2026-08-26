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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/mm_arc"
SPEC = importlib.util.spec_from_file_location(
    "audit_mm_arc_paper", ROOT / "scripts/audit_mm_arc_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text())


def test_all_three_official_versions_are_pinned_rebuilt_and_visually_checked() -> None:
    data = manifest()
    assert data["official_versions_audited"] == ["v1", "v2", "v3"]
    assert data["legacy_v1_v2_source_identical"] is True
    assert data["v3_wholesale_replacement"] is True
    assert data["official_pdf_and_source_recovered"] is True
    assert data["official_document_rebuild_completed"] is True
    assert data["official_pages_visually_checked"] == 81
    assert data["rebuilt_pages_visually_checked"] == 78
    revisions = {row["version"]: row for row in rows("version_revision_audit.csv")}
    assert set(revisions) == {"v1", "v2", "v3"}
    assert revisions["v1"]["submitted"] == "2025-09-05"
    assert revisions["v2"]["submitted"] == "2025-09-10"
    assert revisions["v3"]["submitted"] == "2026-07-27"
    assert revisions["v1"]["rebuilt_pages"] == "30"
    assert revisions["v2"]["rebuilt_pages"] == "32"
    assert revisions["v3"]["rebuilt_pages"] == "16"
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["arxiv"]["id"] == "2509.05080"
    assert provenance["arxiv"]["visual_qa"]["unreadable_clipped_or_overlapping_pages"] == 0


def test_version_replacement_is_not_conflated_with_legacy_replication() -> None:
    revisions = {row["version"]: row for row in rows("version_revision_audit.csv")}
    assert revisions["v1"]["title"].startswith("MM-DREX")
    assert revisions["v1"]["authors"] == "9"
    assert revisions["v1"]["method_family"].startswith("Qwen2.5")
    assert revisions["v2"]["version_relationship"].startswith("source-identical")
    assert revisions["v3"]["title"].startswith("MM-ARC")
    assert revisions["v3"]["authors"] == "10"
    assert revisions["v3"]["method_family"].startswith("Qwen3")
    assert revisions["v3"]["version_relationship"] == (
        "wholesale_replacement_not_a_minor_revision"
    )
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["v2_to_v3_method_identity"]["status"] == "wholesale_replacement"
    assert checks["v1_transaction_cost_scope"]["status"] == "explicit_future_work"


def test_every_unique_printed_result_unit_fails_closed() -> None:
    legacy = rows("published_result_ledger_v1_v2.csv")
    current = rows("published_result_ledger_v3.csv")
    assert len(legacy) == 671
    assert len(current) == 651
    assert Counter(row["table_label"] for row in legacy) == audit.V1_RESULT_TABLES
    assert Counter(row["table_label"] for row in current) == audit.V3_RESULT_TABLES
    for result in legacy + current:
        assert result["source_document_recovered"] == "True"
        assert result["author_native_experiment_executed"] == "False"
        assert result["published_result_regenerated"] == "False"
        assert result["paper_result_credit"] == "False"
    data = manifest()
    assert data["legacy_unique_published_numeric_table_units"] == 671
    assert data["current_published_numeric_table_units"] == 651
    assert data["legacy_native_numeric_units_regenerated"] == 0
    assert data["current_native_numeric_units_regenerated"] == 0


def test_official_release_is_substantial_but_not_deployment_complete() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["url"] == "https://anonymous.4open.science/r/MM-ARC-32F7/"
    assert release["archive_files"] == 107
    assert release["archive_sha256"] == "830e4257125e67f4f9c64c9ae2a446b02593f83b94bd81b19aae225f5014f317"
    assert release["previous_archive_sha256"] == "b0e647858678b06aaeeddb3cebcc6ee29af76d44877fc7d611c2a957f281098d"
    assert release["archive_bytes"] == 1_121_831
    assert release["archive_uncompressed_bytes"] == 2_595_188
    assert release["archive_snapshot_count"] == 2
    assert release["archive_refresh_changed_files"] == ["DATA_CARD.md", "MODEL_CARD.md"]
    assert release["archive_refresh_unchanged_code_and_artifact_files"] == 105
    assert release["license"] == "Apache-2.0"
    assert release["registered_artifacts"] == 35
    assert release["registered_artifact_bytes"] == 341_958_665
    assert release["verified_payload_files"] == 26
    assert release["verified_payload_bytes"] == 1_395_457
    assert release["lfs_pointer_files"] == 9
    assert release["lfs_payload_bytes_unavailable"] == 340_563_208
    assert len(release["lfs_pointer_inventory"]) == 9
    assert all(row["observed_bytes"] == 133 for row in release["lfs_pointer_inventory"])
    assert release["unique_lfs_oids"] == 7
    assert release["official_public_lfs_endpoint_file_not_found"] == 9
    assert release["exact_public_payload_unique_oids_recovered"] == 1
    assert release["exact_public_payload_registered_paths_recovered"] == 3
    assert release["exact_public_payload_unique_bytes_recovered"] == 11_422_650
    assert release["exact_public_payload_registered_bytes_recovered"] == 34_267_950
    assert release["verified_payload_files_after_exact_public_recovery"] == 29
    assert release["verified_payload_bytes_after_exact_public_recovery"] == 35_663_407
    assert release["remaining_unavailable_pointer_files"] == 6
    assert release["remaining_unavailable_unique_oids"] == 6
    assert release["remaining_unavailable_registered_bytes"] == 306_295_258
    assert release["global_exact_lfs_code_search_queries"] == 10
    assert release["global_exact_lfs_code_search_hits"] == 0
    assert release["global_remaining_lfs_oids_queried"] == 6
    assert release["tokenizer_recovery_source_attributable_to_mm_arc_authors"] is False
    assert release["base_model_id"] == "Qwen/Qwen3-VL-8B-Instruct"
    assert release["base_model_revision"] == "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b"
    assert release["base_model_registered_bytes"] == 17_545_907_231
    assert release["artifact_verification_passed"] is False


def test_public_refresh_and_exact_tokenizer_recovery_are_fail_closed() -> None:
    snapshots = rows("release_snapshot_history.csv")
    assert len(snapshots) == 2
    assert snapshots[1]["changed_paths"] == "DATA_CARD.md;MODEL_CARD.md"
    assert snapshots[1]["code_or_artifact_paths_changed"] == "False"
    recovery = rows("lfs_payload_recovery_audit.csv")
    assert len(recovery) == 9
    assert len({row["oid_sha256"] for row in recovery}) == 7
    recovered = [row for row in recovery if row["exact_public_payload_recovered"] == "True"]
    assert len(recovered) == 3
    assert {row["oid_sha256"] for row in recovered} == {
        "be75606093db2094d7cd20f3c2f385c212750648bd6ea4fb2bf507a6a4c55506"
    }
    assert all(row["registry_verification_after_hydration"] == "True" for row in recovered)
    assert all(row["declared_runtime_loaded"] == "True" for row in recovered)
    assert all(row["author_attributable_recovery"] == "False" for row in recovered)
    assert all(row["paper_result_credit"] == "False" for row in recovered)
    unavailable = [row for row in recovery if row["exact_public_payload_recovered"] == "False"]
    assert len(unavailable) == 6
    assert sum(int(row["registered_bytes"]) for row in unavailable) == 306_295_258
    assert all(row["official_public_file_endpoint"] == "404_file_not_found_2026-08-14" for row in recovery)
    searches = rows("global_lfs_recovery_search.csv")
    assert len(searches) == 10
    assert Counter(row["query_type"] for row in searches) == {
        "oid_sha256": 6,
        "distinctive_path": 2,
        "distinctive_directory": 2,
    }
    assert {row["total_count"] for row in searches} == {"0"}
    assert {row["incomplete_results"] for row in searches} == {"False"}
    assert {row["public_payload_or_pointer_hit"] for row in searches} == {"False"}
    assert {row["native_model_or_strategy_execution_enabled"] for row in searches} == {"False"}
    assert {row["paper_result_credit"] for row in searches} == {"False"}
    assert {row["checked_at_utc"] for row in searches} == {"2026-08-26T16:52:00Z"}
    data = manifest()
    assert data["global_exact_lfs_code_search_queries"] == 10
    assert data["global_exact_lfs_code_search_hits"] == 0
    assert data["global_remaining_lfs_oids_queried"] == 6
    runtime = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())[
        "tokenizer_runtime_validation"
    ]
    assert runtime["transformers"] == "5.11.0"
    assert runtime["tokenizers"] == "0.22.2"
    assert runtime["protobuf"] == "7.35.0"
    assert runtime["model_forward_executed"] is False
    assert runtime["paper_result_credit"] is False
    assert len(runtime["adapters"]) == 3
    assert all(item["decoded_round_trip_exact"] for item in runtime["adapters"])


def test_native_code_checks_are_credited_only_as_code_contracts() -> None:
    release = json.loads((AUDIT_DIR / "release_execution_audit.json").read_text())
    assert release["test_command"] == "python -m pytest -q"
    assert release["tests_passed"] == 111
    assert release["ruff_clean"] is True
    assert release["bytecode_compilation_passed"] is True
    assert release["direct_pytest_console_script_errors"] == 2
    assert release["tests_download_lfs"] is False
    assert release["tests_use_model_runtime_doubles"] is True
    assert release["full_model_forward_executed_in_audit"] is False
    assert release["paper_decision_cycle_executed_in_audit"] is False
    assert release["published_table_or_figure_regenerated"] is False
    assert release["paper_result_credit"] is False


def test_method_audit_records_every_material_research_boundary() -> None:
    methods = {(row["version"], row["dimension"]): row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 21
    assert methods[("v1_v2", "author_native_runtime")]["status"] == "missing"
    assert methods[("v1_v2", "trading_costs")]["status"] == "absent"
    assert methods[("v3", "official_repository")]["status"] == "substantial_release"
    assert methods[("v3", "official_repository_refresh")]["status"] == "two_document_files_changed"
    assert methods[("v3", "qwen_and_router_artifacts")]["status"] == "tokenizers_recovered_weights_unavailable"
    assert methods[("v3", "full_benchmark_market_data")]["status"] == "missing"
    assert methods[("v3", "training_and_experiment_controller")]["status"] == "missing"
    assert methods[("v3", "five_seed_training")]["status"] == "partial_one_seed_only"
    assert methods[("v3", "result_arrays_and_report_generator")]["status"] == "missing"
    assert methods[("v3", "artifact_integrity")]["status"] == "partial_exact_public_recovery"
    assert methods[("v3", "published_results")]["status"] == "not_regenerated"
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    boundary = provenance["release_boundary"]
    assert boundary["v1_v2_implementation_recovered"] is False
    assert boundary["v3_runtime_source_recovered"] is True
    assert boundary["v3_deployment_payloads_all_recovered"] is False
    assert boundary["v3_exact_generic_tokenizer_oid_recovered"] is True
    assert boundary["v3_remaining_paper_specific_lfs_payloads"] == 6
    assert boundary["v3_complete_research_pipeline_recovered"] is False
    assert boundary["published_result_lineage_recovered"] is False


def test_empirical_figures_are_inventoried_without_native_credit() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 8
    assert sum(int(row["empirical_series_or_panels"]) for row in figures) == 18
    assert all(row["underlying_numeric_array_released"] == "False" for row in figures)
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)
    assert manifest()["native_empirical_figure_series_regenerated"] == 0


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned MM-ARC primary-source scratch is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_mm_arc_paper.py"), "--output", str(tmp_path / "strict"), "--strict"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert json.loads((tmp_path / "strict/manifest.json").read_text())[
        "full_end_to_end_pipeline_reproduced"
    ] is False


def test_manifest_hashes_every_output_and_readme_states_honest_boundary() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    readme = (AUDIT_DIR / "README.md").read_text()
    for marker in (
        "wholesale 17-page replacement", "111 tests", "Git LFS pointers",
        "29/35", "306,295,258", "zero regenerated published", "No proxy",
        "All ten complete searches returned zero indexed files",
        "does not reproduce the legacy",
    ):
        assert marker in readme
