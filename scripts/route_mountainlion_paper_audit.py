#!/usr/bin/env python3
"""Route recovered MountainLion source into the frozen artifact evidence.

The frozen census listed no artifact. A primary-source paper audit recovered an
attributable product frontend and an attributable GenAI platform repository.
Both are real, runnable component packages; neither contains the experiment or
result lineage behind the paper. This deterministic correction replaces only
MountainLion, preserves all earlier corrections, and recomputes the summary.
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


SYSTEM_ID = "SYS-MOUNTAIN-LION"
BACKEND_URL = "https://github.com/MountainLionAi/GenAI-Platform"
FRONTEND_URL = "https://github.com/MountainLionAi/MountainLion"
ARTIFACT_URLS = f"{BACKEND_URL} ; {FRONTEND_URL}"
BACKEND_OWNER_REPO = "MountainLionAi/GenAI-Platform"
FRONTEND_OWNER_REPO = "MountainLionAi/MountainLion"
BACKEND_HEAD = "3f76de1fe4d8d423f7d4e46e45f19f5bd43992ec"
BACKEND_PAPER_TIME_HEAD = "98b98d31dec6d29a5c518943d980300612030a40"
FRONTEND_HEAD = "f7819f3537808d398f6c3da37e43b51ecebdbd42"
BACKEND_ARCHIVE_SHA256 = "1524ffc672b40b0f8185b328caf63609ff09e234bb98eab6ed492ab771c31af9"
BACKEND_PAPER_TIME_ARCHIVE_SHA256 = "66aa61c5ae03a6d587e94a1252421cae1f66579eeb3cec29875d09061e6efb88"
FRONTEND_ARCHIVE_SHA256 = "e336674987252aa8e1df3ccbc1f7a8609f242ef57b4ee9c21c06006608774478"
OBSERVED_AT = "2026-08-12T16:38:40+00:00"
ROW_AUDIT_AT = "2026-08-12T00:00:00+00:00"
PAPER_MANIFEST = ROOT / "paper_runs/paper_replication_audits/mountainlion/manifest.json"
SOURCE_SUMMARY = (
    ROOT
    / "paper_runs/paper_replication_audits/mountainlion/"
    "public_source_snapshot_summary.csv"
)
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


def backend_observation() -> dict[str, Any]:
    return {
        "archive_bytes": 14_161_920,
        "archive_sha256": BACKEND_ARCHIVE_SHA256,
        "paper_time_head": BACKEND_PAPER_TIME_HEAD,
        "paper_time_archive_sha256": BACKEND_PAPER_TIME_ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 220,
        "paper_time_file_count": 199,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": [
            "genaipf/agent/autogen/auto_agent.py",
            "genaipf/dispatcher/api.py",
            "genaipf/services/gpt_service.py",
            "genaipf/tools/search/perplexity/perplexity_search_agent.py",
        ],
        "environment_markers": ["requirements.txt", "setup.py", ".env.example"],
        "runner_markers": ["app.py"],
        "support_markers": ["examples/multi_agent_t001.py", "examples/test_agent.py"],
    }


def frontend_observation() -> dict[str, Any]:
    return {
        "archive_bytes": 2_426_880,
        "archive_sha256": FRONTEND_ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 153,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": ["src/api/api.js", "src/App.vue", "src/page/Crypto.vue"],
        "environment_markers": ["package.json", "package-lock.json"],
        "runner_markers": ["package.json#scripts.build", "package.json#scripts.dev"],
        "support_markers": ["vite.config.js"],
    }


def artifact_result(
    *,
    url: str,
    owner_repo: str,
    head: str,
    license_name: str,
    observation: dict[str, Any],
    execution_note: str,
) -> dict[str, Any]:
    return {
        "url": url,
        "url_type": "github_repository",
        "check_method": (
            "git ls-remote plus pinned archive, paper-level source audit, and "
            f"component execution ({execution_note})"
        ),
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": owner_repo,
        "default_branch": "main",
        "head_sha": head,
        "observed_license": license_name,
        "license_source": f"pinned_archive_{observation['archive_sha256']}",
        "static_observation": observation,
        "errors": [],
    }


def mountainlion_row() -> dict[str, Any]:
    backend = backend_observation()
    frontend = frontend_observation()
    definitions = {
        "R0": "no listed public artifact or no reachable artifact",
        "R1": "reachable landing page, documentation, pseudocode, or statically incomplete repository",
        "R2": "observable source code plus dependency/setup manifest",
        "R3": "R2 plus a runner and tests/examples/configuration support",
    }
    results = [
        artifact_result(
            url=BACKEND_URL,
            owner_repo=BACKEND_OWNER_REPO,
            head=BACKEND_HEAD,
            license_name="Apache-2.0",
            observation=backend,
            execution_note="paper-time core compile",
        ),
        artifact_result(
            url=FRONTEND_URL,
            owner_repo=FRONTEND_OWNER_REPO,
            head=FRONTEND_HEAD,
            license_name="MIT",
            observation=frontend,
            execution_note="locked install and repeated deterministic build",
        ),
    ]
    basis = {
        "definition": definitions,
        "evidence": [
            {
                "url": BACKEND_URL,
                "tier": "R3",
                "basis": "code+environment+runner+examples/configuration support",
                "markers": backend,
            },
            {
                "url": FRONTEND_URL,
                "tier": "R3",
                "basis": "code+locked environment+build runner+Vite configuration",
                "markers": frontend,
            },
        ],
        "paper_fidelity_boundary": (
            "R3 is static package completeness, not paper-result reproduction; "
            "0/20 forecasting performance cells regenerate"
        ),
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "MountainLion",
        "stratum": "T",
        "main_FT": "Y",
        "artifact_urls": ARTIFACT_URLS,
        "artifact_url_count": 2,
        "artifact_url_types": "github_repository;github_repository",
        "public_artifact_listed": "Y",
        "reachability_outcome": "reachable_all",
        "github_owner_repos": f"{BACKEND_OWNER_REPO};{FRONTEND_OWNER_REPO}",
        "default_branch_head_shas": (
            f"{BACKEND_OWNER_REPO}@main={BACKEND_HEAD};"
            f"{FRONTEND_OWNER_REPO}@main={FRONTEND_HEAD}"
        ),
        "observed_licenses": (
            f"{BACKEND_OWNER_REPO}=Apache-2.0;{FRONTEND_OWNER_REPO}=MIT"
        ),
        "static_fidelity_tier": "R3",
        "static_fidelity_basis_json": compact(basis),
        "failure_category": "none",
        "native_execution_attempted": "Y",
        "audit_timestamp_utc": ROW_AUDIT_AT,
        "artifact_url_results_json": compact(results),
        "errors_json": "[]",
    }


def validate_inputs() -> None:
    manifest = json.loads(PAPER_MANIFEST.read_text(encoding="utf-8"))
    expected = {
        "published_performance_result_units": 20,
        "published_performance_result_units_faithfully_regenerated": 0,
        "verbatim_prompt_templates": 7,
        "runtime_prompt_requests_replayed": 0,
        "attributable_public_repositories": 2,
        "paper_relevant_public_source_files": 352,
        "frontend_dist_files": 67,
        "backend_public_test_functions": 0,
        "native_result_generation_pipeline_found": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"MountainLion paper manifest mismatch for {key}")

    with SOURCE_SUMMARY.open(newline="", encoding="utf-8") as handle:
        source_rows = {row["source_id"]: row for row in csv.DictReader(handle)}
    source_expected = {
        "frontend": (FRONTEND_HEAD, FRONTEND_ARCHIVE_SHA256),
        "backend_paper_time": (
            BACKEND_PAPER_TIME_HEAD,
            BACKEND_PAPER_TIME_ARCHIVE_SHA256,
        ),
        "backend_current": (BACKEND_HEAD, BACKEND_ARCHIVE_SHA256),
    }
    for source_id, (commit, archive_hash) in source_expected.items():
        if source_rows[source_id]["commit"] != commit:
            raise ValueError(f"MountainLion {source_id} commit changed")
        if source_rows[source_id]["archive_sha256"] != archive_hash:
            raise ValueError(f"MountainLion {source_id} archive changed")

    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != ARTIFACT_URLS:
        raise ValueError("MountainLion registry route is not the two recovered repositories")


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
    rows[matches[0]] = mountainlion_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)

    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": (
            "paper/source audit recovered an attributable product frontend and "
            "GenAI platform; both are runnable components but neither ships the "
            "paper experiment or result lineage"
        ),
        "corrected_at_utc": ROW_AUDIT_AT,
        "evidence": "paper_runs/paper_replication_audits/mountainlion/manifest.json",
        "source_heads": [BACKEND_HEAD, FRONTEND_HEAD],
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
