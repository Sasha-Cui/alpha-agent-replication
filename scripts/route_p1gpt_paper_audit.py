#!/usr/bin/env python3
"""Route the attributable P1GPT web client into frozen artifact evidence.

The original census listed no artifact.  A bounded paper-level search recovered
`P1GPT/web_demo`, owned by the P1GPT organization and committed by Neurowatt
developers before the paper.  It is a runnable web-client package, but its
private model service, agents, database, backtest, and paper results are absent.
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


SYSTEM_ID = "SYS-P1GPT"
ARTIFACT_URL = "https://github.com/P1GPT/web_demo"
OWNER_REPO = "P1GPT/web_demo"
HEAD = "a88a3a7c731063d0d1ca7ac15946eb600753f358"
ARCHIVE_SHA256 = "81f201afa31f8a7f277e17d51622ece94bf907a8cc7e0f4a73248a28c5d50e0f"
OBSERVED_AT = "2026-08-12T18:00:00+00:00"
ROW_AUDIT_AT = "2026-08-12T00:00:00+00:00"
PAPER_MANIFEST = ROOT / "paper_runs/paper_replication_audits/p1gpt/manifest.json"
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
        "archive_bytes": 22_970,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 38,
        "python_file_count": 22,
        "python_compile_exit": 0,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": [
            "p1gpt/state/gpt.py", "p1gpt/components/chat.py", "p1gpt/db_model.py"
        ],
        "environment_markers": ["requirements.txt"],
        "runner_markers": ["Dockerfile", "compose.yaml", "deployment.yaml"],
        "support_markers": ["rxconfig.py", "service.yaml", "nginx.conf"],
        "private_model_endpoint": "http://main-llm:8090/invoke/",
        "model_service_source_shipped": False,
        "paper_result_generator_shipped": False,
    }


def p1gpt_row() -> dict[str, Any]:
    observation = static_observation()
    definitions = {
        "R0": "no listed public artifact or no reachable artifact",
        "R1": "reachable landing page, documentation, pseudocode, or statically incomplete repository",
        "R2": "observable source code plus dependency/setup manifest",
        "R3": "R2 plus a runner and tests/examples/configuration support",
    }
    result = {
        "url": ARTIFACT_URL,
        "url_type": "github_repository",
        "check_method": (
            "GitHub API plus pinned repeated archive, paper-level source audit, "
            "and compileall of every Python file"
        ),
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
        "evidence": [
            {
                "url": ARTIFACT_URL,
                "tier": "R3",
                "basis": "code+environment+Docker/Compose/Kubernetes runners+configuration",
                "markers": observation,
            }
        ],
        "paper_fidelity_boundary": (
            "R3 is static client-package completeness, not paper-result reproduction; "
            "0/12 native P1GPT cells regenerate end to end"
        ),
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "P1GPT",
        "stratum": "T",
        "main_FT": "Y",
        "artifact_urls": ARTIFACT_URL,
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
        "native_execution_attempted": "Y",
        "audit_timestamp_utc": ROW_AUDIT_AT,
        "artifact_url_results_json": compact([result]),
        "errors_json": "[]",
    }


def validate_inputs() -> None:
    manifest = json.loads(PAPER_MANIFEST.read_text(encoding="utf-8"))
    expected = {
        "published_table_result_cells": 72,
        "displayed_table_cells_exactly_verified": 46,
        "p1gpt_cells_verified_from_author_plot_outputs": 11,
        "native_p1gpt_result_cells_faithfully_regenerated_end_to_end": 0,
        "attributable_public_repositories": 1,
        "paper_relevant_public_source_files": 38,
        "public_python_files_compiled": 22,
        "native_result_generation_pipeline_found": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"P1GPT paper manifest mismatch for {key}")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != ARTIFACT_URL:
        raise ValueError("P1GPT registry route is not the recovered repository")


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
    rows[matches[0]] = p1gpt_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)

    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": (
            "paper-level search recovered an attributable P1GPT/Neurowatt web "
            "client; the private model service and paper experiment remain absent"
        ),
        "corrected_at_utc": ROW_AUDIT_AT,
        "evidence": "paper_runs/paper_replication_audits/p1gpt/manifest.json",
        "source_heads": [HEAD],
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
