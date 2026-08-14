#!/usr/bin/env python3
"""Route the pinned AAPM paper audit into the frozen artifact evidence.

Both official arXiv source versions directly link the public author repository.
This deterministic correction replaces only the AAPM row, preserves earlier
post-freeze corrections, and recomputes the public-artifact summary.
"""
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


SYSTEM_ID = "SYS-EMPIRICAL-ASSET-PRICING-LLM"
URL = "https://github.com/chengjunyan1/AAPM"
OWNER_REPO = "chengjunyan1/AAPM"
HEAD = "cc54e4337fcd4089dc69e4a1173e82a675648475"
ARCHIVE_SHA256 = "50a30166b77a2835852585b1a164e96e11e03d42e4b1b1e6038485480f5e829b"
OBSERVED_AT = "2026-08-11T19:30:00+00:00"
ROW_AUDIT_AT = "2026-08-11T00:00:00+00:00"
PAPER_MANIFEST = ROOT / "paper_runs/paper_replication_audits/aapm/manifest.json"
SOURCE_PROVENANCE = ROOT / "paper_runs/paper_replication_audits/aapm/source_provenance.json"
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
        "archive_bytes": 21_760_000,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 10,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": ["analysis.py", "memdb.py", "model.py", "prompt.py", "utils.py"],
        "environment_markers": ["requirements.txt"],
        "runner_markers": ["analysis.py"],
        "support_markers": ["config.yaml", "data/wsj_metadata.json"],
    }


def aapm_row() -> dict[str, Any]:
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
        "check_method": "paper/source link plus pinned Git history, tree, archive, and full paper-level source audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": OWNER_REPO,
        "default_branch": "main",
        "head_sha": HEAD,
        "observed_license": "MIT",
        "license_source": f"pinned_archive_{ARCHIVE_SHA256}",
        "static_observation": observation,
        "errors": [],
    }
    basis = {
        "definition": definitions,
        "evidence": [{
            "url": URL,
            "tier": "R3",
            "basis": "code+environment+analysis runner+configuration support",
            "markers": observation,
        }],
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "Empirical Asset Pricing with Large Language Model Agents",
        "stratum": "F",
        "main_FT": "Y",
        "artifact_urls": URL,
        "artifact_url_count": 1,
        "artifact_url_types": "github_repository",
        "public_artifact_listed": "Y",
        "reachability_outcome": "reachable_all",
        "github_owner_repos": OWNER_REPO,
        "default_branch_head_shas": f"{OWNER_REPO}@main={HEAD}",
        "observed_licenses": f"{OWNER_REPO}=MIT",
        "static_fidelity_tier": "R3",
        "static_fidelity_basis_json": compact(basis),
        "failure_category": "none",
        "native_execution_attempted": "N",
        "audit_timestamp_utc": ROW_AUDIT_AT,
        "artifact_url_results_json": compact([result]),
        "errors_json": "[]",
    }


def validate_inputs() -> None:
    manifest = json.loads(PAPER_MANIFEST.read_text(encoding="utf-8"))
    expected = {
        "tracked_source_files": 10,
        "released_metadata_records": 65_733,
        "v1_table_result_cells": 114,
        "v2_table_result_cells": 162,
        "author_output_result_cells_available": 0,
        "end_to_end_result_cells_reproduced": 0,
        "public_forks_accessible": 14,
        "public_fork_branch_refs_audited": 14,
        "public_fork_unique_heads_audited": 4,
        "public_fork_divergent_heads_audited": 0,
        "public_fork_native_result_artifacts_found": False,
        "public_fork_paper_result_credit": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"AAPM paper manifest mismatch for {key}")
    provenance = json.loads(SOURCE_PROVENANCE.read_text(encoding="utf-8"))
    if provenance["official_repository"] != URL:
        raise ValueError("AAPM paper audit does not identify the routed repository")
    if provenance["current_head"] != HEAD:
        raise ValueError("AAPM repository head changed from the pinned audit")
    if provenance["current_tree_sha256"] != "fe28d88828b080f86f7493c182d5d7f29d4e4cd92a2d9f4e526cc08dfb7794e3":
        raise ValueError("AAPM current tree changed from the pinned audit")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("AAPM registry route is not the repository linked by both paper versions")


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
    rows[matches[0]] = aapm_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)

    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "both official arXiv source versions directly link the public author repository omitted from the frozen registry",
        "corrected_at_utc": ROW_AUDIT_AT,
        "evidence": "paper_runs/paper_replication_audits/aapm/source_provenance.json",
        "source_head": HEAD,
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
