#!/usr/bin/env python3
"""Route the attributable AlphaCrafter repository into frozen artifact evidence."""
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


SYSTEM_ID = "SYS-ALPHA-CRAFTER"
URL = "https://github.com/NJU-LINK/AlphaCrafter"
HEAD_SHA = "c6dbc1ba4e0a4ecbc3ea1454c5290dbea4b36b0d"
ARCHIVE_SHA256 = "41b7b55892cd43ec8594b7a6070ae2a70ebdf4da38b3b52ee06e99d54e0660b1"
OBSERVED_AT = "2026-08-12T00:00:00+00:00"
MANIFEST = ROOT / "paper_runs/paper_replication_audits/alphacrafter/manifest.json"
RELEASE_AUDIT = ROOT / "paper_runs/paper_replication_audits/alphacrafter/release_execution_audit.json"
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
        "archive_bytes": 297_049,
        "archive_uncompressed_bytes": 889_614,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 79,
        "python_file_count": 48,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": [
            "alphacrafter/main.py", "alphacrafter/sim/exchange_a.py",
            "alphacrafter/sim/exchange_us.py", "alphacrafter/agent/openai/agent.py",
        ],
        "environment_markers": ["Dockerfile", "docker-compose.yml", "setup.py"],
        "runner_markers": ["alphacrafter/main.py"],
        "support_markers": [
            "README.md", "alphacrafter/config.yaml",
            "alphacrafter/sandbox/template_a", "alphacrafter/sandbox/template_us",
        ],
        "tracked_tests": 0,
        "default_model_registry_mismatch": True,
        "research_data_payload_released": False,
    }


def alphacrafter_row() -> dict[str, Any]:
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
        "check_method": "pinned GitHub archive plus paper/source/release attribution audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": "NJU-LINK/AlphaCrafter",
        "default_branch": "main",
        "head_sha": HEAD_SHA,
        "observed_license": "MIT",
        "license_source": f"pinned_archive_{ARCHIVE_SHA256}",
        "static_observation": observation,
        "errors": [],
    }
    basis = {
        "definition": definitions,
        "evidence": [
            {
                "url": URL,
                "tier": "R3",
                "basis": "code+environment+runner+examples/config; runtime and research-data boundaries are tracked separately",
                "markers": observation,
            }
        ],
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "AlphaCrafter",
        "stratum": "F",
        "main_FT": "Y",
        "artifact_urls": URL,
        "artifact_url_count": 1,
        "artifact_url_types": "github_repository",
        "public_artifact_listed": "Y",
        "reachability_outcome": "reachable_all",
        "github_owner_repos": "NJU-LINK/AlphaCrafter",
        "default_branch_head_shas": f"NJU-LINK/AlphaCrafter@{HEAD_SHA}",
        "observed_licenses": "NJU-LINK/AlphaCrafter=MIT",
        "static_fidelity_tier": "R3",
        "static_fidelity_basis_json": compact(basis),
        "failure_category": "none",
        "native_execution_attempted": "Y",
        "audit_timestamp_utc": OBSERVED_AT,
        "artifact_url_results_json": compact([result]),
        "errors_json": "[]",
    }


def validate_inputs() -> None:
    manifest = json.loads(MANIFEST.read_text())
    expected = {
        "v1_published_numeric_result_units": 176,
        "v2_published_numeric_result_units": 304,
        "v1_native_numeric_units_regenerated": 0,
        "v2_native_numeric_units_regenerated": 0,
        "v1_empirical_panels": 16,
        "v2_empirical_panels": 14,
        "repository_files": 79,
        "native_component_checks_passed": 6,
        "public_forks_accessible": 6,
        "public_fork_branch_refs_audited": 6,
        "public_fork_unique_heads_audited": 4,
        "public_fork_divergent_commits_audited": 17,
        "public_fork_native_result_artifacts_found": False,
        "public_fork_paper_result_credit": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"AlphaCrafter manifest mismatch for {key}")
    release = json.loads(RELEASE_AUDIT.read_text())
    if (
        release["url"] != URL
        or release["head_sha"] != HEAD_SHA
        or release["archive_sha256"] != ARCHIVE_SHA256
    ):
        raise ValueError("AlphaCrafter release provenance mismatch")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("AlphaCrafter registry does not route the attributable repository")


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
    rows[matches[0]] = alphacrafter_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)
    audit_payload = json.loads(json_path.read_text())
    summary_payload = json.loads(summary_json_path.read_text())
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "author-organization repository cites exact paper/authors and matches the released architecture; paper does not directly link it",
        "corrected_at_utc": OBSERVED_AT,
        "evidence": "paper_runs/paper_replication_audits/alphacrafter/source_provenance.json",
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
