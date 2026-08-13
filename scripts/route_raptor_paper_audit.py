#!/usr/bin/env python3
"""Route the pinned RAPTOR paper/source audit into frozen artifact evidence.

The submission-era anonymous 4open snapshot expired after the original census.
The published CEUR PDF directly embeds the lead author's repository URL. This
deterministic correction replaces only the RAPTOR row, preserves other evidence
corrections, and recomputes the public-artifact summary.
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


SYSTEM_ID = "SYS-RAPTOR"
URL = "https://github.com/blakealmon/AI-Hedge-Fund-Driven-By-Multi-Agent-LLM-Based-Architecture"
OWNER_REPO = "blakealmon/AI-Hedge-Fund-Driven-By-Multi-Agent-LLM-Based-Architecture"
HEAD = "1793abf29ecde15597cb2bb4cb345accf655531f"
ARCHIVE_SHA256 = "badb4c27ba34232d6539975f3191dcc7a066a0ee1456c448ec9bb21f5e33d697"
OBSERVED_AT = "2026-08-11T18:47:37.230004+00:00"
ROW_AUDIT_AT = "2026-08-11T00:00:00+00:00"
PAPER_MANIFEST = ROOT / "paper_runs/paper_replication_audits/raptor/manifest.json"
SOURCE_PROVENANCE = ROOT / "paper_runs/paper_replication_audits/raptor/source_provenance.json"
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
        "archive_bytes": 6033284,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 825,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": [
            "cli/main.py",
            "comparisonAlgorithms/run_rules.py",
            "evaluation/eval_range.py",
            "main.py",
        ],
        "environment_markers": ["pyproject.toml", "requirements.txt", "uv.lock"],
        "runner_markers": [
            "mvo_blm_runner.py",
            "testing/mvo_blm_runner.py",
            "testingLoopMultithreaded.py",
        ],
        "support_markers": [
            "config/portfolio.example.json",
            "testing/scripts/visualize.py",
            "testing/2025-01-01/portfolio_snapshot_2025-01-01.json",
        ],
    }


def raptor_row() -> dict[str, Any]:
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
        "check_method": "git ls-remote plus pinned GitHub archive and paper-level source/output audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": OWNER_REPO,
        "default_branch": "main",
        "head_sha": HEAD,
        "observed_license": "Apache-2.0",
        "license_source": f"pinned_archive_{ARCHIVE_SHA256}",
        "static_observation": observation,
        "errors": [],
    }
    basis = {
        "definition": definitions,
        "evidence": [{
            "url": URL,
            "tier": "R3",
            "basis": "code+environment+runner+tests/examples/config",
            "markers": observation,
        }],
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "RAPTOR",
        "stratum": "T",
        "main_FT": "Y",
        "artifact_urls": URL,
        "artifact_url_count": 1,
        "artifact_url_types": "github_repository",
        "public_artifact_listed": "Y",
        "reachability_outcome": "reachable_all",
        "github_owner_repos": OWNER_REPO,
        "default_branch_head_shas": f"{OWNER_REPO}@main={HEAD}",
        "observed_licenses": f"{OWNER_REPO}=Apache-2.0",
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
        "tracked_source_files": 825,
        "author_result_snapshots": 166,
        "displayed_scalar_results": 42,
        "author_output_verified_scalar_results": 16,
        "current_public_response_verified_scalar_results": 3,
        "displayed_scalar_results_verified": 19,
        "end_to_end_result_cells_reproduced": 0,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"RAPTOR paper manifest mismatch for {key}")
    provenance = json.loads(SOURCE_PROVENANCE.read_text(encoding="utf-8"))
    if provenance["author_github_repository"] != URL:
        raise ValueError("RAPTOR paper audit does not identify the routed author repository")
    if provenance["author_repository_head"] != HEAD:
        raise ValueError("RAPTOR author repository head changed from the pinned audit")
    if provenance["author_repository_archive_sha256"] != ARCHIVE_SHA256:
        raise ValueError("RAPTOR author archive hash changed from the pinned audit")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("RAPTOR registry route is not the repository linked by the published PDF")


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
    rows[matches[0]] = raptor_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)

    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "published final PDF directly links the lead author's repository after the anonymous snapshot expired",
        "corrected_at_utc": ROW_AUDIT_AT,
        "evidence": "paper_runs/paper_replication_audits/raptor/source_provenance.json",
        "source_head": HEAD,
    }
    corrections = [
        item
        for item in audit_payload["metadata"].get(
            "post_freeze_evidence_corrections", []
        )
        if item["system_id"] != SYSTEM_ID
    ]
    corrections.append(correction)
    corrections.sort(key=lambda item: item["system_id"])
    for metadata in (audit_payload["metadata"], summary_payload["metadata"]):
        metadata["registry_sha256"] = sha256(REGISTRY)
        metadata["post_freeze_evidence_corrections"] = corrections
    payload_rows = audit_payload["rows"]
    payload_matches = [
        index for index, row in enumerate(payload_rows) if row["system_id"] == SYSTEM_ID
    ]
    if len(payload_rows) != 103 or len(payload_matches) != 1:
        raise ValueError("artifact JSON is not the expected 103-row census")
    payload_rows[payload_matches[0]] = {
        key: str(value) for key, value in raptor_row().items()
    }
    audit_payload["rows"] = payload_rows
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
