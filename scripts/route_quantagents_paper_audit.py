#!/usr/bin/env python3
"""Route the paper-linked QuantAgents static repository into artifact evidence."""
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


SYSTEM_ID = "SYS-QUANT-AGENTS"
SYSTEM_NAME = "QuantAgents"
OWNER_REPO = "QuantAgents/quantagents.github.io"
URL = f"https://github.com/{OWNER_REPO}"
HEAD_SHA = "a1d0d56d04d2b73a5fbc472ec9af865a29be6ef7"
ARCHIVE_SHA256 = "33b11602cc4e1a326b7677f8155d580f0caf38a4a80189bcca45db1b0ded17c3"
OBSERVED_AT = "2026-08-13T02:40:00+00:00"
MANIFEST = ROOT / "paper_runs/paper_replication_audits/quantagents/manifest.json"
RELEASE_AUDIT = ROOT / "paper_runs/paper_replication_audits/quantagents/release_execution_audit.json"
SOURCE_PROVENANCE = ROOT / "paper_runs/paper_replication_audits/quantagents/source_provenance.json"
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
        "archive_bytes": 81_460_192,
        "archive_uncompressed_bytes": 88_003_221,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 41,
        "python_file_count": 0,
        "has_code": False,
        "has_environment": False,
        "has_runner": False,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": [],
        "environment_markers": [],
        "runner_markers": [],
        "support_markers": [
            "index.html",
            "static/images/frameworkhtml.png",
            "static/images/agent1.png",
            "static/images/vis1.mp4",
            "static/images/vis5.png",
        ],
        "tracked_test_files": 0,
        "rendered_algorithms": 4,
        "rendered_agent_profiles": 4,
        "meeting_videos": 3,
        "paper_leaderboard_cells": 90,
        "excluded_template_residue": {
            "records": 6_141,
            "data_file": "visualizer/data/data_public.js",
            "reason": "MathVista/VQA website template, unrelated to QuantAgents",
        },
        "paper_code_released": False,
        "paper_dataset_released": False,
        "paper_result_arrays_released": False,
        "paper_result_credit": False,
    }


def quantagents_row() -> dict[str, Any]:
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
        "check_method": "paper-linked first-party project site plus pinned Git history, tree, archive, media, and full primary-source audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": OWNER_REPO,
        "default_branch": "main",
        "head_sha": HEAD_SHA,
        "observed_license": "MIT",
        "license_source": "LICENSE file and GitHub repository metadata at pinned head",
        "static_observation": observation,
        "errors": [],
    }
    basis = {
        "definition": definitions,
        "evidence": [{
            "url": URL,
            "tier": "R1",
            "basis": "static author documentation, rendered algorithms/profiles, result table, and meeting videos; no system code, environment, runner, dataset, or result arrays",
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
        "static_fidelity_tier": "R1",
        "static_fidelity_basis_json": compact(basis),
        "failure_category": "none",
        "native_execution_attempted": "N",
        "audit_timestamp_utc": OBSERVED_AT,
        "artifact_url_results_json": compact([result]),
        "errors_json": "[]",
    }


def validate_inputs() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {
        "published_numeric_table_cells": 238,
        "quantagents_own_numeric_table_cells": 132,
        "author_site_corroborated_main_table_cells": 90,
        "published_numeric_table_cells_faithfully_regenerated": 0,
        "published_empirical_panels": 14,
        "published_empirical_panels_faithfully_regenerated": 0,
        "public_system_source_files_recovered": 0,
        "project_repository_files": 41,
        "site_unrelated_vqa_records": 6_141,
        "full_end_to_end_pipeline_reproduced": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"QuantAgents manifest mismatch for {key}")
    release = json.loads(RELEASE_AUDIT.read_text(encoding="utf-8"))
    if (
        release["url"] != URL
        or release["head_sha"] != HEAD_SHA
        or release["archive_sha256"] != ARCHIVE_SHA256
        or release["repository_license"] != "MIT"
        or release["native_execution_possible"] is not False
    ):
        raise ValueError("QuantAgents release provenance mismatch")
    provenance = json.loads(SOURCE_PROVENANCE.read_text(encoding="utf-8"))
    if (
        provenance["project_repository"] != URL
        or provenance["project_repository_head"] != HEAD_SHA
        or provenance["project_repository_archive_sha256"] != ARCHIVE_SHA256
    ):
        raise ValueError("QuantAgents primary-source provenance mismatch")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("QuantAgents registry does not route the paper-linked repository")


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
    rows[matches[0]] = quantagents_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)
    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "paper directly links the first-party project repository; it is R1 documentation and media, not released QuantAgents system code or data",
        "corrected_at_utc": OBSERVED_AT,
        "evidence": "paper_runs/paper_replication_audits/quantagents/source_provenance.json",
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
