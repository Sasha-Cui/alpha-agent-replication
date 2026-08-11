#!/usr/bin/env python3
"""Route the pinned HedgeAgents paper audit into artifact evidence.

The original census missed the authors' project repository.  The repository is
reachable and revision-pinned, but it is an R1 static documentation site rather
than released HedgeAgents code.  This deterministic correction replaces only
the HedgeAgents row, preserves prior post-freeze corrections, and recomputes
the public-artifact summary.
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


SYSTEM_ID = "SYS-HEDGE-AGENTS"
URL = "https://github.com/hedgeagents/hedgeagents.github.io"
OWNER_REPO = "hedgeagents/hedgeagents.github.io"
HEAD = "329c5cc8613d91e517de4fbdb0dbc8476a356db5"
ARCHIVE_SHA256 = "f86c9d0562a31864ec4bc3d449af803b6048c2393a1130a351a2c657d3943ad2"
OBSERVED_AT = "2026-08-11T21:30:00+00:00"
ROW_AUDIT_AT = "2026-08-11T00:00:00+00:00"
PAPER_MANIFEST = ROOT / "paper_runs/paper_replication_audits/hedgeagents/manifest.json"
SOURCE_PROVENANCE = ROOT / "paper_runs/paper_replication_audits/hedgeagents/source_provenance.json"
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
        "archive_bytes": 15_079_735,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 46,
        "tree_bytes": 21_503_635,
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
            "static/images/ALLCR.png",
        ],
        "excluded_template_residue": {
            "records": 6_141,
            "data_file": "visualizer/data/data_public.js",
            "reason": "MathVista/VQA website template, unrelated to HedgeAgents",
        },
    }


def hedgeagents_row() -> dict[str, Any]:
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
        "check_method": "paper project link plus pinned Git history, tree, archive, and full primary-source audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": OWNER_REPO,
        "default_branch": "main",
        "head_sha": HEAD,
        "observed_license": "NOASSERTION",
        "license_source": "no license file or repository license declaration in pinned tree",
        "static_observation": observation,
        "errors": [],
    }
    basis = {
        "definition": definitions,
        "evidence": [{
            "url": URL,
            "tier": "R1",
            "basis": "static author documentation and result images; no system code, environment, or runner",
            "markers": observation,
        }],
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "HedgeAgents",
        "stratum": "T",
        "main_FT": "Y",
        "artifact_urls": URL,
        "artifact_url_count": 1,
        "artifact_url_types": "github_repository",
        "public_artifact_listed": "Y",
        "reachability_outcome": "reachable_all",
        "github_owner_repos": OWNER_REPO,
        "default_branch_head_shas": f"{OWNER_REPO}@main={HEAD}",
        "observed_licenses": f"{OWNER_REPO}=NOASSERTION",
        "static_fidelity_tier": "R1",
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
        "published_numeric_table_cells": 236,
        "hedgeagents_own_numeric_table_cells": 126,
        "author_site_corroborated_main_table_cells": 90,
        "published_numeric_table_cells_faithfully_regenerated": 0,
        "public_system_source_files_recovered": 0,
        "author_site_tree_files": 46,
        "author_site_unrelated_vqa_records": 6_141,
        "full_end_to_end_pipeline_reproduced": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"HedgeAgents paper manifest mismatch for {key}")
    provenance = json.loads(SOURCE_PROVENANCE.read_text(encoding="utf-8"))
    if provenance["author_repository"] != URL:
        raise ValueError("HedgeAgents audit does not identify the routed repository")
    if provenance["author_repository_head"] != HEAD:
        raise ValueError("HedgeAgents repository head changed from the pinned audit")
    if provenance["author_repository_archive_sha256"] != ARCHIVE_SHA256:
        raise ValueError("HedgeAgents repository archive changed from the pinned audit")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("HedgeAgents registry route is not the author project repository")


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
    rows[matches[0]] = hedgeagents_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)

    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "author project repository linked by the paper was omitted from the frozen registry; repository is R1 documentation, not system code",
        "corrected_at_utc": ROW_AUDIT_AT,
        "evidence": "paper_runs/paper_replication_audits/hedgeagents/source_provenance.json",
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
