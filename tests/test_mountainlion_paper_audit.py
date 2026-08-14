from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/mountainlion"
SPEC = importlib.util.spec_from_file_location(
    "audit_mountainlion_paper", ROOT / "scripts/audit_mountainlion_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_table_denominator_is_exhaustive_and_fail_closed() -> None:
    ledger = audit.published_table_ledger()
    assert len(ledger) == 30
    assert Counter(row["cell_kind"] for row in ledger) == {
        "configuration": 10,
        "direct_result": 20,
    }
    assert {row["token"] for row in ledger} == {
        "ADA",
        "BTC",
        "ARB",
        "SOL",
        "XRP",
        "DOGE",
        "TRX",
        "ETH",
        "MATIC",
        "BNB",
    }
    assert all(row["native_reproduced_value"] == "" for row in ledger)
    assert all(row["paper_result_credit"] is False for row in ledger)


def test_manifest_separates_documents_components_and_results() -> None:
    data = manifest()
    assert data["full_paper_reproduced"] is False
    assert data["manuscripts_rebuilt_deterministically"] == 3
    assert data["published_numeric_table_units"] == 30
    assert data["published_configuration_units"] == 10
    assert data["published_performance_result_units"] == 20
    assert data["published_performance_result_units_faithfully_regenerated"] == 0
    assert data["manuscript_rebuilds_receive_result_credit"] is False
    assert data["native_result_generation_pipeline_found"] is False
    assert data["reachable_public_commits_audited"] == 2_273
    assert data["historical_text_blob_revisions_scanned"] == 2_185
    assert data["historical_serialized_result_or_model_artifact_paths_found"] == 0


def test_primary_source_bundles_are_manuscript_only() -> None:
    inventory = rows("paper_source_inventory.csv")
    assert Counter(row["paper_version"] for row in inventory) == {
        "2507.20474v1": 11,
        "2507.20474v2": 10,
        "2507.20474v3": 10,
    }
    assert all(row["operational_system_code"] == "False" for row in inventory)
    assert all(row["raw_numeric_result_array"] == "False" for row in inventory)
    assert all(row["runtime_request_or_response"] == "False" for row in inventory)


def test_figure_assets_are_output_correspondence_not_result_replay() -> None:
    figures = rows("author_figure_inventory.csv")
    assert len(figures) == 18
    assert len({row["sha256"] for row in figures}) == 6
    case_outputs = [
        row for row in figures if row["author_rendered_output_correspondence"] == "True"
    ]
    assert len(case_outputs) == 3
    assert {row["source_path"] for row in case_outputs} == {"fig/comp.pdf"}
    assert all(row["faithfully_regenerated_from_native_pipeline"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)


def test_seven_templates_have_no_runtime_request_or_response_credit() -> None:
    prompts = rows("prompt_inventory.csv")
    assert len(prompts) == 7
    assert all(row["verbatim_template_shipped"] == "True" for row in prompts)
    assert all(row["immutable_request_shipped"] == "False" for row in prompts)
    assert all(row["immutable_response_shipped"] == "False" for row in prompts)
    assert all(row["prompt_execution_reproduced"] == "False" for row in prompts)


def test_attributable_source_inventory_is_pinned_but_contains_no_result_generator() -> None:
    summaries = rows("public_source_snapshot_summary.csv")
    assert {row["source_id"] for row in summaries} == {
        "frontend",
        "backend_paper_time",
        "backend_current",
    }
    assert {row["file_count"] for row in summaries} == {"153", "199", "220"}
    assert all(row["paper_result_generation_source_found"] == "False" for row in summaries)
    files = rows("public_source_file_inventory.csv")
    assert Counter(row["source_id"] for row in files) == {
        "frontend": 153,
        "backend_paper_time": 199,
    }
    assert all(row["paper_table_result_generator"] == "False" for row in files)
    assert all(row["paper_result_array"] == "False" for row in files)


def test_component_execution_credits_real_builds_without_promoting_results() -> None:
    execution = json.loads(
        (AUDIT_DIR / "source_component_execution.json").read_text(encoding="utf-8")
    )
    assert execution["frontend"]["repeated_outputs_byte_identical"] is True
    assert execution["frontend"]["dist_file_count"] == 67
    assert execution["backend_paper_time"]["core_compile_exit"] == 0
    assert execution["backend_paper_time"]["repository_compile_exit"] == 1
    assert execution["backend_paper_time"]["public_test_function_count"] == 0
    assert execution["backend_paper_time"]["full_service_started"] is False
    assert execution["frontend"]["paper_result_credit"] is False
    assert execution["backend_paper_time"]["paper_result_credit"] is False


def test_source_semantics_match_product_components_and_fail_closed_on_results() -> None:
    checks = {row["check_id"]: row for row in rows("source_component_checks.csv")}
    assert checks["frontend_appendix_endpoints"]["status"] == "pass"
    assert checks["paper_table_token_menu_match"]["status"] == "pass"
    assert checks["prediction_database_reader"]["status"] == "pass"
    assert checks["backend_private_module_boundary"]["status"] == "blocked"
    assert checks["backend_public_tests"]["status"] == "missing"
    assert checks["result_generation_assets"]["status"] == "missing"
    observed = checks["result_generation_assets"]["observed"]
    assert "2273 reachable commits" in observed
    assert "2288 path/object revisions" in observed
    assert "2185 scanned text blob revisions" in observed
    assert all(row["exact_native_paper_mechanism_credit"] == "False" for row in checks.values())
    assert all(row["paper_result_credit"] == "False" for row in checks.values())


def test_consistency_audit_records_material_ambiguities() -> None:
    checks = {row["check_id"]: row for row in rows("internal_consistency.csv")}
    assert checks["raw_mse_cross_token_ranking"]["status"] == "invalid_cross_scale_inference"
    assert checks["table_alpha_semantics"]["status"] == "ambiguous_configuration"
    assert checks["return_claim_without_return_result"]["status"] == "unsupported_outcome_claim"
    assert checks["ablation_claim_without_ablation"]["status"] == "unsupported_experiment_claim"
    assert checks["policy_gradient_label"]["status"] == "algorithm_label_conflicts_with_equation"
    assert len(checks) == 15


def test_paper_equation_demos_are_synthetic_components_only() -> None:
    checks = rows("paper_formula_component_checks.csv")
    assert len(checks) == 5
    assert all(row["paper_specification_component_credit"] == "True" for row in checks)
    assert all(row["native_source_implementation_executed"] == "False" for row in checks)
    assert all(row["paper_result_credit"] == "False" for row in checks)
    negative = next(row for row in checks if row["check_id"] == "negative_accuracy_boundary")
    assert negative["synthetic_output"] == "-1"


def test_three_manuscript_rebuilds_are_deterministic_document_evidence_only() -> None:
    rebuilds = json.loads((AUDIT_DIR / "manuscript_rebuilds.json").read_text(encoding="utf-8"))
    assert len(rebuilds) == 3
    assert all(row["same_hash_across_independent_build_directories"] is True for row in rebuilds)
    assert all(row["page_count"] == 17 for row in rebuilds)
    assert all(row["normalized_extracted_word_set_jaccard"] > 0.998 for row in rebuilds)
    assert all("passed_all_17_pages" in row["full_contact_sheet_visual_qa"] for row in rebuilds)
    assert all(row["paper_result_reproduction"] is False for row in rebuilds)


def test_current_arxiv_v3_is_explicitly_pinned_and_matches_repository_pdf() -> None:
    versions = {row["paper_version"]: row for row in rows("paper_version_summary.csv")}
    assert set(versions) == {"2507.20474v1", "2507.20474v2", "2507.20474v3"}
    assert versions["2507.20474v3"]["submitted_at_utc"] == "2025-09-19T02:22:53Z"
    assert versions["2507.20474v3"]["repository_pdf_byte_identical"] == "True"
    assert versions["2507.20474v1"]["repository_pdf_byte_identical"] == "False"
    assert versions["2507.20474v2"]["repository_pdf_byte_identical"] == "False"


def test_complete_public_histories_are_exhaustive_and_receive_no_result_credit() -> None:
    summaries = {
        row["source_id"]: row
        for row in json.loads(
            (AUDIT_DIR / "public_source_history_summary.json").read_text(
                encoding="utf-8"
            )
        )
    }
    assert summaries["frontend"]["commits"] == 6
    assert summaries["backend"]["commits"] == 2_267
    assert summaries["frontend"]["remote_branches"] == 1
    assert summaries["backend"]["remote_branches"] == 98
    assert summaries["backend"]["tags"] == 2
    assert summaries["backend"]["deleted_paths"] == [
        "1.txt",
        "README_en.md",
        "examples/utils/onchain_t001.py",
        "genaipf/test/pics/btc1.png",
        "genaipf/test/response.txt",
        "genaipf/test/test_by_request_client.py",
        "genaipf/tools/search/1.txt",
        "genaipf/tools/search/bing/1.txt",
    ]
    assert all(row["complete_nonshallow_clone"] is True for row in summaries.values())
    assert all(row["object_database_fsck_clean"] is True for row in summaries.values())
    assert all(
        row["native_training_panel_model_prediction_result_or_table_runner_found"]
        is False
        for row in summaries.values()
    )
    assert all(row["paper_result_credit"] is False for row in summaries.values())

    refs = rows("public_source_ref_inventory.csv")
    assert len(refs) == 101
    assert Counter(row["ref_kind"] for row in refs) == {
        "remote_branch": 99,
        "tag": 2,
    }
    commits = rows("public_source_commit_inventory.csv")
    assert Counter(row["source_id"] for row in commits) == {
        "frontend": 6,
        "backend": 2_267,
    }
    paths = rows("public_source_historical_path_inventory.csv")
    assert Counter(row["source_id"] for row in paths) == {
        "frontend": 153,
        "backend": 291,
    }
    assert sum(int(row["path_object_revisions"]) for row in paths) == 2_288
    assert all(
        row["serialized_result_or_model_artifact_path"] == "False" for row in paths
    )
    assert all(row["paper_result_credit"] == "False" for row in commits + paths + refs)


def test_history_content_matches_are_component_correspondence_not_training() -> None:
    scans = {
        (row["source_id"], row["scan_id"]): row
        for row in rows("public_source_history_content_scan.csv")
    }
    assert scans[("backend", "paper_title")]["text_blob_revision_hits"] == "0"
    assert scans[("backend", "table_value")]["text_blob_revision_hits"] == "0"
    assert scans[("backend", "mse")]["text_blob_revision_hits"] == "0"
    assert scans[("backend", "cross_validation")]["text_blob_revision_hits"] == "0"
    assert scans[("backend", "model_fit")]["text_blob_revision_hits"] == "2"
    assert "Bridge(" in scans[("backend", "model_fit")]["interpretation"]
    assert scans[("backend", "kline_predictd")]["text_blob_revision_hits"] == "28"
    assert (
        scans[("backend", "exact_ten_token_product_menu")][
            "text_blob_revision_hits"
        ]
        == "2"
    )
    assert all(row["native_paper_result_pipeline_found"] == "False" for row in scans.values())
    assert all(row["paper_result_credit"] == "False" for row in scans.values())


def test_manifest_hashes_every_nonmanifest_output_and_readme_is_honest() -> None:
    data = manifest()
    expected = {
        path.name
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "not faithfully reproduced" in text
    assert "0/20" in text
    assert "Installing more packages cannot recover" in text
    assert "does not prove" in text


def test_paper_routes_through_public_component_audit_not_proxy_credit() -> None:
    route_path = (
        ROOT
        / "paper_runs/submission_evidence/replication_scope/"
        "paper_evidence_route_ledger.csv"
    )
    with route_path.open(newline="", encoding="utf-8") as stream:
        routed = [row for row in csv.DictReader(stream) if row["canonical_work_id"] == audit.WORK_ID]
    assert len(routed) == 1
    row = routed[0]
    assert row["paper_evidence_route"] == "public_code_available"
    assert row["reachable_public_code_system_ids"] == audit.SYSTEM_ID
    assert row["static_fidelity_tiers"] == "R3"
    assert row["native_execution_audit_status"] == (
        "paper_audit:completed_zero_of_20_performance_cells_public_components_only"
    )
    assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
    assert "0/20" in row["precise_native_or_access_blocker"]
