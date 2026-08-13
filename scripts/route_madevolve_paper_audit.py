#!/usr/bin/env python3
"""Route the paper-linked MadEvolve framework into artifact evidence."""
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


SYSTEM_ID = "SYS-MAD-EVOLVE"
SYSTEM_NAME = "MadEvolve"
OWNER_REPO = "tianyi-stack/MadEvolve"
URL = f"https://github.com/{OWNER_REPO}"
HEAD_SHA = "8b881d3a45d8f68050c28c8d64c2bb653001103a"
ARCHIVE_SHA256 = "79a2bad2ac108a66d1c5c6737778ebe05c3021f165f63527b552c4eb52e39f11"
OBSERVED_AT = "2026-08-12T22:00:00+00:00"
MANIFEST = ROOT / "paper_runs/paper_replication_audits/madevolve_trading/manifest.json"
RELEASE_AUDIT = ROOT / "paper_runs/paper_replication_audits/madevolve_trading/release_execution_audit.json"
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
        "archive_bytes": 97_517,
        "archive_uncompressed_bytes": 413_976,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 69,
        "python_file_count": 66,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": [
            "madevolve/engine/orchestrator.py",
            "madevolve/provider/gateway.py",
            "madevolve/repository/topology/partitions.py",
            "madevolve/repository/storage/artifact_store.py",
        ],
        "environment_markers": ["pyproject.toml"],
        "runner_markers": ["madevolve/__main__.py", "madevolve/engine/orchestrator.py"],
        "support_markers": ["README.md"],
        "tracked_test_files": 0,
        "cli_as_declared_passed": False,
        "cli_after_audit_dependency_passed": True,
        "bytecode_compilation_passed": False,
        "general_framework_component_checks_passed": 5,
        "paper_trading_code_released": False,
        "paper_market_data_released": False,
        "paper_result_arrays_released": False,
        "paper_result_credit": False,
    }


def madevolve_row() -> dict[str, Any]:
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
        "check_method": "paper-linked first-party site plus pinned coauthor repository and native execution audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": OWNER_REPO,
        "default_branch": "main",
        "head_sha": HEAD_SHA,
        "observed_license": "MIT",
        "license_source": "pyproject license declaration and classifier; repository has no license-text file and GitHub detects no license",
        "static_observation": observation,
        "errors": [],
    }
    basis = {
        "definition": definitions,
        "evidence": [{
            "url": URL,
            "tier": "R3",
            "basis": "general framework code+environment+CLI/orchestrator+README configuration support; paper trading adapter and research lineage are absent",
            "markers": observation,
        }],
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": SYSTEM_NAME,
        "stratum": "F",
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
        "published_numeric_result_units": 214,
        "native_numeric_units_regenerated": 0,
        "empirical_panels": 21,
        "native_empirical_panels_regenerated": 0,
        "repository_files": 69,
        "author_tests_passed": 0,
        "native_component_checks_passed": 5,
        "modules_imported_after_audit_dependency": 64,
        "modules_failed_import_after_audit_dependency": 2,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"MadEvolve manifest mismatch for {key}")
    release = json.loads(RELEASE_AUDIT.read_text(encoding="utf-8"))
    if (
        release["url"] != URL
        or release["head_sha"] != HEAD_SHA
        or release["archive_sha256"] != ARCHIVE_SHA256
        or release["license_declaration"] != "MIT"
        or release["license_text_file_present"] is not False
    ):
        raise ValueError("MadEvolve release provenance mismatch")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("MadEvolve registry does not route the paper-linked repository")


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
    rows[matches[0]] = madevolve_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)
    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "paper links first-party framework site, which directly links a coauthor-owned general framework repository; trading research payload remains absent",
        "corrected_at_utc": OBSERVED_AT,
        "evidence": "paper_runs/paper_replication_audits/madevolve_trading/source_provenance.json",
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
