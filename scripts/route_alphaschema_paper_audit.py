#!/usr/bin/env python3
"""Route the directly linked AlphaSchema repository into artifact evidence."""
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


SYSTEM_ID = "SYS-ALPHA-SCHEMA"
SYSTEM_NAME = "AlphaSchema"
OWNER_REPO = "JingyangYi/AlphaSchema"
URL = f"https://github.com/{OWNER_REPO}"
HEAD_SHA = "1206a094abfaad7cc53e6dff39f8fae43e851acb"
ARCHIVE_SHA256 = "fa4a31a9b664f70e4d83a7474492603d03b9e801f15140bbcb4294d175550e49"
OBSERVED_AT = "2026-08-12T00:00:00+00:00"
MANIFEST = ROOT / "paper_runs/paper_replication_audits/alphaschema/manifest.json"
RELEASE_AUDIT = ROOT / "paper_runs/paper_replication_audits/alphaschema/release_execution_audit.json"
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
        "archive_bytes": 1_573_612,
        "archive_uncompressed_bytes": 1_945_533,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 32,
        "python_file_count": 16,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": [
            "alphaschema/pipeline.py", "alphaschema/schema_space.py",
            "alphaschema/backend.py", "alphaschema/reward_model.py",
        ],
        "environment_markers": ["pyproject.toml"],
        "runner_markers": ["alphaschema/cli.py", "examples/run_demo.py"],
        "support_markers": [
            "README.md", "configs/default_stock_search.json",
            "schemas/stock_alpha/event.json", "tests/test_core.py",
        ],
        "tracked_test_files": 1,
        "author_tests_passed": 9,
        "native_demo_plans": 48,
        "native_demo_uses_mock_evaluator": True,
        "paper_market_data_released": False,
        "paper_trial_outputs_released": False,
        "paper_result_credit": False,
    }


def alphaschema_row() -> dict[str, Any]:
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
        "check_method": "manuscript-linked repository plus pinned archive and native execution audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": OWNER_REPO,
        "default_branch": "main",
        "head_sha": HEAD_SHA,
        "observed_license": "NOASSERTION",
        "license_source": "no license file or repository license declaration in pinned tree",
        "static_observation": observation,
        "errors": [],
    }
    basis = {
        "definition": definitions,
        "evidence": [{
            "url": URL,
            "tier": "R3",
            "basis": "code+environment+CLI/demo+tests/config/schema support; research data and result lineage are absent",
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
        "observed_licenses": f"{OWNER_REPO}=NOASSERTION",
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
        "published_numeric_result_units": 212,
        "native_numeric_units_regenerated": 0,
        "empirical_panels": 9,
        "native_empirical_panels_regenerated": 0,
        "repository_files": 32,
        "author_tests_passed": 9,
        "native_demo_plans": 48,
        "native_component_checks_passed": 3,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"AlphaSchema manifest mismatch for {key}")
    release = json.loads(RELEASE_AUDIT.read_text(encoding="utf-8"))
    if (
        release["url"] != URL
        or release["head_sha"] != HEAD_SHA
        or release["archive_sha256"] != ARCHIVE_SHA256
        or release["license"] != "not_declared"
    ):
        raise ValueError("AlphaSchema release provenance mismatch")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("AlphaSchema registry does not route the manuscript-linked repository")


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
    rows[matches[0]] = alphaschema_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)
    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "manuscript directly links first-author-owned repository; pinned audit records no declared license or released research-result lineage",
        "corrected_at_utc": OBSERVED_AT,
        "evidence": "paper_runs/paper_replication_audits/alphaschema/source_provenance.json",
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
