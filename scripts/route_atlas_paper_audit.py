#!/usr/bin/env python3
"""Route the paper-cited same-author StockSim component into artifact evidence."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_artifact_audit as artifact  # noqa: E402


SYSTEM_ID = "SYS-ATLAS"
SYSTEM_NAME = "ATLAS"
OWNER_REPO = "harrypapadakis/StockSim"
URL = f"https://github.com/{OWNER_REPO}"
HEAD_SHA = "c1a25c195df4c93b2db4a748f80ceae0f1c9fe50"
ARCHIVE_SHA256 = "824b8b041ff5bf8733d2f755015432eefdc94fdb65fd53b1d1f22a2d99696db7"
OBSERVED_AT = "2026-08-13T00:15:00+00:00"
MANIFEST = ROOT / "paper_runs/paper_replication_audits/atlas/manifest.json"
RELEASE_AUDIT = ROOT / "paper_runs/paper_replication_audits/atlas/release_execution_audit.json"
REGISTRY = ROOT / "literature_review/census_v1/system_registry.csv"
AUDIT_DIR = ROOT / "paper_runs/submission_evidence/artifact_audit"

AUDIT_FIELDS = [
    "system_id", "system_name", "stratum", "main_FT", "artifact_urls",
    "artifact_url_count", "artifact_url_types", "public_artifact_listed",
    "reachability_outcome", "github_owner_repos", "default_branch_head_shas",
    "observed_licenses", "static_fidelity_tier", "static_fidelity_basis_json",
    "failure_category", "native_execution_attempted", "audit_timestamp_utc",
    "artifact_url_results_json", "errors_json",
]
SUMMARY_FIELDS = [
    "group", "metric", "successes", "denominator", "proportion",
    "wilson_95_lower", "wilson_95_upper", "z",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def static_observation() -> dict[str, Any]:
    return {
        "archive_bytes": 2_234_151,
        "archive_uncompressed_bytes": 31_949_454,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 81,
        "python_file_count": 43,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": [
            "agents/llm_agent.py", "exchanges/exchange_agent.py",
            "utils/metrics.py", "utils/orders.py",
        ],
        "environment_markers": ["requirements.txt", "Dockerfile", "docker-compose.yml"],
        "runner_markers": ["main_launcher.py"],
        "support_markers": [
            "README.md", "configs/demo_config.yaml",
            "configs/demo_multi_provider_config.yaml",
            "configs/orderbook_historical_test.yaml",
        ],
        "tracked_test_files": 0,
        "as_declared_asyncio_import_passed": False,
        "asyncio_import_after_audit_adjustment_passed": True,
        "bytecode_compilation_after_adjustment_passed": True,
        "modules_imported_after_adjustment": 43,
        "modules_failed_import_after_adjustment": 0,
        "stock_sim_component_checks_passed": 4,
        "atlas_specific_code_released": False,
        "adaptive_opro_implementation_released": False,
        "atlas_sample_config_released": False,
        "paper_data_snapshot_released": False,
        "paper_runtime_prompts_and_trajectories_released": False,
        "paper_result_arrays_released": False,
        "paper_result_credit": False,
    }


def atlas_row() -> dict[str, Any]:
    observation = static_observation()
    definitions = {
        "R0": "no listed public artifact or no reachable artifact",
        "R1": "reachable landing page, documentation, pseudocode, or statically incomplete repository",
        "R2": "observable source code plus dependency/setup manifest",
        "R3": "R2 plus a runner and tests/examples/configuration support",
    }
    result = {
        "url": URL,
        "url_type": "github_repository",
        "check_method": "paper citation plus pinned same-author precursor repository and native component audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": OWNER_REPO,
        "default_branch": "main",
        "head_sha": HEAD_SHA,
        "observed_license": "MIT",
        "license_source": "README declaration only; repository has no license-text file and GitHub detects no license",
        "static_observation": observation,
        "errors": [],
    }
    basis = {
        "definition": definitions,
        "evidence": [{
            "url": URL,
            "tier": "R3",
            "basis": "cited same-author precursor framework has code+environment+runner+configuration support; ATLAS and Adaptive-OPRO research payload are absent",
            "markers": observation,
        }],
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": SYSTEM_NAME,
        "stratum": "T",
        "main_FT": "Y",
        "artifact_urls": URL,
        "artifact_url_count": 1,
        "artifact_url_types": "github_repository",
        "public_artifact_listed": "Y",
        "reachability_outcome": "reachable_all",
        "github_owner_repos": OWNER_REPO,
        "default_branch_head_shas": f"{OWNER_REPO}@main={HEAD_SHA}",
        "observed_licenses": f"{OWNER_REPO}=MIT",
        "static_fidelity_tier": "R3",
        "static_fidelity_basis_json": compact(basis),
        "failure_category": "none",
        "native_execution_attempted": "Y",
        "audit_timestamp_utc": OBSERVED_AT,
        "artifact_url_results_json": compact([result]),
        "errors_json": "[]",
    }


def validate_inputs() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {
        "official_pages_visually_checked": 209,
        "rebuilt_pages_visually_checked": 209,
        "published_numeric_result_units": 1_784,
        "native_numeric_units_regenerated": 0,
        "empirical_panels": 5,
        "native_empirical_panels_regenerated": 0,
        "repository_files": 81,
        "author_tests_passed": 0,
        "native_component_checks_passed": 4,
        "modules_imported_after_audit_adjustment": 43,
        "modules_failed_import_after_audit_adjustment": 0,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"ATLAS manifest mismatch for {key}")
    release = json.loads(RELEASE_AUDIT.read_text(encoding="utf-8"))
    if (
        release["url"] != URL
        or release["head_sha"] != HEAD_SHA
        or release["archive_sha256"] != ARCHIVE_SHA256
        or release["license_declaration"] != "MIT"
        or release["license_text_file_present"] is not False
        or release["atlas_specific_code_released"] is not False
    ):
        raise ValueError("ATLAS/StockSim release provenance mismatch")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("ATLAS registry does not route the cited StockSim component")


def route() -> None:
    validate_inputs()
    csv_path = AUDIT_DIR / "artifact_audit.csv"
    json_path = AUDIT_DIR / "artifact_audit.json"
    summary_csv_path = AUDIT_DIR / "artifact_audit_summary.csv"
    summary_json_path = AUDIT_DIR / "artifact_audit_summary.json"
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    matches = [index for index, row in enumerate(rows) if row["system_id"] == SYSTEM_ID]
    if len(rows) != 103 or len(matches) != 1:
        raise ValueError("artifact audit is not the expected 103-row census")
    rows[matches[0]] = atlas_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)
    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "paper cites a same-author StockSim precursor repository; it is a real framework component but contains no ATLAS/Adaptive-OPRO research payload",
        "corrected_at_utc": OBSERVED_AT,
        "evidence": "paper_runs/paper_replication_audits/atlas/source_provenance.json",
        "source_archive_sha256": ARCHIVE_SHA256,
    }
    corrections = [
        item
        for item in audit_payload["metadata"].get("post_freeze_evidence_corrections", [])
        if item["system_id"] != SYSTEM_ID
    ]
    corrections.append(correction)
    corrections.sort(key=lambda item: item["system_id"])
    for metadata in (audit_payload["metadata"], summary_payload["metadata"]):
        metadata["registry_sha256"] = sha256(REGISTRY)
        metadata["post_freeze_evidence_corrections"] = corrections
    audit_payload["rows"] = rows
    summary_payload["groups"] = grouped_summary
    artifact.atomic_csv(csv_path, rows, AUDIT_FIELDS)
    artifact.atomic_json(json_path, audit_payload)
    artifact.atomic_csv(summary_csv_path, long_summary, SUMMARY_FIELDS)
    artifact.atomic_json(summary_json_path, summary_payload)


def main() -> None:
    route()
    print(AUDIT_DIR / "artifact_audit.csv")


if __name__ == "__main__":
    main()
