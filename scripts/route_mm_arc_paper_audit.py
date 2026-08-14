#!/usr/bin/env python3
"""Route the v3 paper-linked MM-ARC archive into frozen artifact evidence."""
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


SYSTEM_ID = "SYS-MM-DREX"
URL = "https://anonymous.4open.science/r/MM-ARC-32F7/"
ARCHIVE_SHA256 = "830e4257125e67f4f9c64c9ae2a446b02593f83b94bd81b19aae225f5014f317"
PREVIOUS_ARCHIVE_SHA256 = "b0e647858678b06aaeeddb3cebcc6ee29af76d44877fc7d611c2a957f281098d"
OBSERVED_AT = "2026-08-14T21:45:30+00:00"
MANIFEST = ROOT / "paper_runs/paper_replication_audits/mm_arc/manifest.json"
RELEASE_AUDIT = ROOT / "paper_runs/paper_replication_audits/mm_arc/release_execution_audit.json"
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
        "archive_bytes": 1_121_831,
        "archive_uncompressed_bytes": 2_595_188,
        "archive_sha256": ARCHIVE_SHA256,
        "previous_archive_sha256": PREVIOUS_ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "snapshot_count": 2,
        "refresh_changed_paths": ["DATA_CARD.md", "MODEL_CARD.md"],
        "refresh_unchanged_code_and_artifact_files": 105,
        "file_count": 107,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": [
            "mmarc_pipeline/runtime.py", "mmarc_pipeline/pools.py",
            "mmarc_pipeline/multimodal.py", "mmarc_pipeline/portfolio.py",
        ],
        "environment_markers": ["pyproject.toml", "Dockerfile", "constraints.production.txt"],
        "runner_markers": ["mmarc_pipeline/cli.py", "mmarc_pipeline/service.py"],
        "support_markers": [
            "tests/test_runtime_acceptance.py", "config/production.example.yaml",
            "artifacts/registry.json", "DATA_CARD.md", "MODEL_CARD.md",
        ],
        "git_lfs_pointer_files": 9,
        "registered_payload_bytes_missing_from_official_endpoint": 340_563_208,
        "exact_public_payload_unique_oids_recovered": 1,
        "exact_public_payload_registered_paths_recovered": 3,
        "registered_payload_bytes_unavailable_after_exact_public_recovery": 306_295_258,
        "registered_artifact_files_verified_after_exact_public_recovery": 29,
    }


def mm_arc_row() -> dict[str, Any]:
    observation = static_observation()
    definitions = {
        "R0": "no listed public artifact or no reachable artifact",
        "R1": "reachable landing page, documentation, pseudocode, or statically incomplete repository",
        "R2": "observable source code plus dependency/setup manifest",
        "R3": "R2 plus a runner and tests/examples/configuration support",
    }
    result = {
        "url": URL,
        "url_type": "anonymous_4open_repository",
        "check_method": "paper-linked anonymous 4open archive plus pinned paper/source/release audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": "",
        "default_branch": "",
        "head_sha": "",
        "observed_license": "Apache-2.0",
        "license_source": f"pinned_archive_{ARCHIVE_SHA256}",
        "static_observation": observation,
        "errors": [
            "latest bulk archive contains 9 Git LFS pointers; official single-file endpoints return file_not_found",
            "one generic tokenizer OID is independently byte-recoverable, but 6 paper-specific payloads remain unavailable",
        ],
    }
    basis = {
        "definition": definitions,
        "evidence": [{
            "url": URL,
            "tier": "R3",
            "basis": "code+environment+runner+tests/examples/config; LFS boundary is tracked separately",
            "markers": observation,
        }],
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "MM-DREX",
        "stratum": "T",
        "main_FT": "Y",
        "artifact_urls": URL,
        "artifact_url_count": 1,
        "artifact_url_types": "anonymous_4open_repository",
        "public_artifact_listed": "Y",
        "reachability_outcome": "reachable_all",
        "github_owner_repos": "",
        "default_branch_head_shas": "",
        "observed_licenses": "MM-ARC-32F7=Apache-2.0",
        "static_fidelity_tier": "R3",
        "static_fidelity_basis_json": compact(basis),
        "failure_category": "none",
        "native_execution_attempted": "Y",
        "audit_timestamp_utc": OBSERVED_AT,
        "artifact_url_results_json": compact([result]),
        "errors_json": compact(result["errors"]),
    }


def validate_inputs() -> None:
    manifest = json.loads(MANIFEST.read_text())
    expected = {
        "legacy_unique_published_numeric_table_units": 671,
        "current_published_numeric_table_units": 651,
        "legacy_native_numeric_units_regenerated": 0,
        "current_native_numeric_units_regenerated": 0,
        "official_repository_files": 107,
        "official_repository_tests_passed": 111,
        "official_repository_lfs_pointer_files": 9,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"MM-ARC manifest mismatch for {key}")
    release = json.loads(RELEASE_AUDIT.read_text())
    if release["url"] != URL or release["archive_sha256"] != ARCHIVE_SHA256:
        raise ValueError("MM-ARC release provenance mismatch")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("MM-ARC registry does not route the paper-linked repository")


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
    rows[matches[0]] = mm_arc_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)
    audit_payload = json.loads(json_path.read_text())
    summary_payload = json.loads(summary_json_path.read_text())
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "current v3 PDF directly links a substantial anonymous 4open release",
        "corrected_at_utc": OBSERVED_AT,
        "evidence": "paper_runs/paper_replication_audits/mm_arc/source_provenance.json",
        "source_archive_sha256": ARCHIVE_SHA256,
    }
    corrections = [
        item for item in audit_payload["metadata"].get("post_freeze_evidence_corrections", [])
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
