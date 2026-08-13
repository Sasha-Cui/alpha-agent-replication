#!/usr/bin/env python3
"""Route pinned Janus-Q static-output/data evidence into the artifact audit."""
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


SYSTEM_ID = "SYS-JANUS-Q"
PROJECT_URL = "https://cute-twilight-5f2400.netlify.app"
REPOSITORY_URL = "https://github.com/Jackson906E/Janus-Q-demo"
OWNER_REPO = "Jackson906E/Janus-Q-demo"
DEFAULT_BRANCH = "main"
DEFAULT_HEAD = "526ac4e32d1e6904f5f3e2af25ea18886b61d325"
RELEASE_BRANCH = "gh-page"
RELEASE_HEAD = "4455e10202865d9fe0c167ed0bdea57af266fdc1"
ARCHIVE_SHA256 = "2d167729ced890f32f4151037c9e33a0638eb9b66fe6e74701bb622adcccdb48"
OBSERVED_AT = "2026-08-13T15:00:00+00:00"
ROW_AUDIT_AT = "2026-08-13T00:00:00+00:00"
PAPER_MANIFEST = ROOT / "paper_runs/paper_replication_audits/janus_q/manifest.json"
SOURCE_PROVENANCE = ROOT / "paper_runs/paper_replication_audits/janus_q/source_provenance.json"
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


def definitions() -> dict[str, str]:
    return {
        "R0": "no listed public artifact or no reachable artifact",
        "R1": "reachable landing page, documentation, pseudocode, or statically incomplete repository",
        "R2": "observable source code plus dependency/setup manifest",
        "R3": "R2 plus a runner and tests/examples/configuration support",
    }


def repository_observation() -> dict[str, Any]:
    return {
        "archive_bytes": 3_789_979,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 20,
        "tree_bytes": 4_263_244,
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
            "static/app.js",
            "data/nav_timeseries.json",
            "data/unified_backtest.json",
            "static/backtest_multi_csv_all_results.png",
        ],
        "historical_branch": RELEASE_BRANCH,
        "historical_release_head": RELEASE_HEAD,
        "current_main_state": "one-byte README only",
    }


def project_observation() -> dict[str, Any]:
    return {
        "checked_at_utc": OBSERVED_AT,
        "file_count": 14,
        "tree_bytes": 2_340_384,
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
            "app.js",
            "eight JSON output endpoints",
            "six-file linked Drive dataset (277,304,208 bytes)",
            "paper-linked anonymous code archive currently expired",
        ],
    }


def janus_q_row() -> dict[str, Any]:
    project = project_observation()
    repository = repository_observation()
    project_result = {
        "url": PROJECT_URL,
        "url_type": "project_page",
        "check_method": "paper-source link plus pinned page assets, output JSON, Drive data, and full paper audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": "",
        "default_branch": "",
        "head_sha": "",
        "observed_license": "NOASSERTION",
        "license_source": "no license observed on project page or linked Drive release",
        "static_observation": project,
        "errors": [],
    }
    repository_result = {
        "url": REPOSITORY_URL,
        "url_type": "github_repository",
        "check_method": "first-author identity plus pinned full Git history, gh-page commit, tree, and archive",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": OWNER_REPO,
        "default_branch": DEFAULT_BRANCH,
        "head_sha": DEFAULT_HEAD,
        "observed_license": "NOASSERTION",
        "license_source": "no repository license declaration or license text in pinned tree",
        "static_observation": repository,
        "errors": [],
    }
    basis = {
        "definition": definitions(),
        "evidence": [
            {
                "url": PROJECT_URL,
                "tier": "R1",
                "basis": "static author project page, outputs, figures, and dataset links; no training or backtest implementation",
                "markers": project,
            },
            {
                "url": REPOSITORY_URL,
                "tier": "R1",
                "basis": "first-author historical static site/output tree; no system code, environment, or runner in any commit",
                "markers": repository,
            },
        ],
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "Janus-Q",
        "stratum": "T",
        "main_FT": "Y",
        "artifact_urls": f"{PROJECT_URL} ; {REPOSITORY_URL}",
        "artifact_url_count": 2,
        "artifact_url_types": "project_page;github_repository",
        "public_artifact_listed": "Y",
        "reachability_outcome": "reachable_all",
        "github_owner_repos": OWNER_REPO,
        "default_branch_head_shas": f"{OWNER_REPO}@{DEFAULT_BRANCH}={DEFAULT_HEAD}",
        "observed_licenses": f"project_page=NOASSERTION;{OWNER_REPO}=NOASSERTION",
        "static_fidelity_tier": "R1",
        "static_fidelity_basis_json": compact(basis),
        "failure_category": "static_package_insufficient",
        "native_execution_attempted": "N",
        "audit_timestamp_utc": ROW_AUDIT_AT,
        "artifact_url_results_json": compact([project_result, repository_result]),
        "errors_json": "[]",
    }


def validate_inputs() -> None:
    manifest = json.loads(PAPER_MANIFEST.read_text(encoding="utf-8"))
    expected = {
        "published_numeric_table_cells": 130,
        "author_linked_table_cells_exactly_verified": 61,
        "author_linked_table_cells_contradicted": 1,
        "published_table_cells_without_numeric_backing": 68,
        "author_native_table_cells_regenerated": 0,
        "active_empirical_figure_panels": 10,
        "author_linked_numeric_panels_recovered": 5,
        "author_native_figure_panels_regenerated": 0,
        "released_nav_derived_metrics_verified": 85,
        "released_jsonl_records_exactly_linked": 31_999,
        "first_author_historical_tree_files": 20,
        "first_author_system_source_files": 0,
        "full_end_to_end_pipeline_reproduced": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"Janus-Q paper manifest mismatch for {key}")
    provenance = json.loads(SOURCE_PROVENANCE.read_text(encoding="utf-8"))
    if provenance["author_project_url"] != PROJECT_URL:
        raise ValueError("Janus-Q audit does not identify the routed project page")
    if provenance["author_repository"] != REPOSITORY_URL:
        raise ValueError("Janus-Q audit does not identify the first-author repository")
    if provenance["author_repository_default_branch"] != DEFAULT_BRANCH:
        raise ValueError("Janus-Q repository default branch changed")
    if provenance["author_repository_default_branch_head"] != DEFAULT_HEAD:
        raise ValueError("Janus-Q repository default branch head changed")
    if provenance["author_release_commit"] != RELEASE_HEAD:
        raise ValueError("Janus-Q historical release commit changed")
    if provenance["pins"]["release/author_repo-gh-page.tar.gz"] != ARCHIVE_SHA256:
        raise ValueError("Janus-Q historical release archive changed")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != f"{PROJECT_URL} ; {REPOSITORY_URL}":
        raise ValueError("Janus-Q registry route is not the pinned author release")


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
    rows[matches[0]] = janus_q_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)

    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "source-commented author project, linked Drive data, and first-author static-output history were omitted from the frozen registry; all are R1 evidence, not system code",
        "corrected_at_utc": ROW_AUDIT_AT,
        "evidence": "paper_runs/paper_replication_audits/janus_q/source_provenance.json",
        "source_head": RELEASE_HEAD,
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
