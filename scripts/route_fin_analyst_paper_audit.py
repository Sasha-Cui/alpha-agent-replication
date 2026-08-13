#!/usr/bin/env python3
"""Route the recovered Fin-Analyst deployment into frozen artifact evidence."""

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


SYSTEM_ID = "SYS-FIN-ANALYST"
URL = "https://huggingface.co/spaces/Mohotarema/Fin_Analyst"
OWNER_REPO = "Mohotarema/Fin_Analyst"
HEAD = "85ab4781e74ed3deb9a7ef49bca3fa23b1ed9738"
ARCHIVE_SHA256 = "39b640608a3df4616dc8f907e95a28a4128f34d3c0a8789c4f3048b3e8e38ad7"
OBSERVED_AT = "2026-08-13T13:35:00+00:00"
ROW_AUDIT_AT = "2026-08-13T00:00:00+00:00"
PAPER_MANIFEST = ROOT / "paper_runs/paper_replication_audits/fin_analyst/manifest.json"
SOURCE_PROVENANCE = ROOT / "paper_runs/paper_replication_audits/fin_analyst/source_provenance.json"
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


def fin_analyst_row() -> dict[str, Any]:
    observation = {
        "archive_bytes": 4_464_640,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 13,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": ["app.py"],
        "environment_markers": ["requirements.txt", "Dockerfile"],
        "runner_markers": ["app.py", "Dockerfile#CMD"],
        "support_markers": ["README.md", "seven bundled data corpora"],
    }
    definitions = {
        "R0": "no listed public artifact or no reachable artifact",
        "R1": "reachable landing page, documentation, pseudocode, or statically incomplete repository",
        "R2": "observable source code plus dependency/setup manifest",
        "R3": "R2 plus a runner and tests/examples/configuration support",
    }
    result = {
        "url": URL,
        "url_type": "huggingface_space",
        "check_method": "Hugging Face API plus pinned Git history/tree/archive and native controlled execution",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": "",
        "huggingface_owner_repo": OWNER_REPO,
        "default_branch": "main",
        "head_sha": HEAD,
        "observed_license": "NOASSERTION",
        "license_source": "no license file or card metadata declaration observed",
        "static_observation": observation,
        "errors": [],
    }
    basis = {
        "definition": definitions,
        "evidence": [{
            "url": URL, "tier": "R3",
            "basis": "code+requirements+Docker/FastAPI runner+README and seven data corpora",
            "markers": observation,
        }],
        "paper_fidelity_boundary": (
            "R3 is static package completeness; controlled native paths run, but "
            "0/119 published table cells and 0/2 full empirical panels regenerate"
        ),
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "Fin-Analyst at FinMMEval Task 3",
        "stratum": "T",
        "main_FT": "Y",
        "artifact_urls": URL,
        "artifact_url_count": 1,
        "artifact_url_types": "huggingface_space",
        "public_artifact_listed": "Y",
        "reachability_outcome": "reachable_all",
        "github_owner_repos": "",
        "default_branch_head_shas": f"{OWNER_REPO}@main={HEAD}",
        "observed_licenses": f"{OWNER_REPO}=NOASSERTION",
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
        "active_empirical_table_cells": 119,
        "empirical_figure_panels": 2,
        "attributable_pre_live_native_implementation_found": True,
        "native_controlled_execution_passed": True,
        "paper_window_official_decision_rows_recovered": 97,
        "published_table_cells_regenerated": 0,
        "full_empirical_figure_panels_regenerated": 0,
        "strict_success": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"Fin-Analyst paper manifest mismatch for {key}")
    provenance = json.loads(SOURCE_PROVENANCE.read_text(encoding="utf-8"))
    if provenance["author_space"]["url"] != URL or provenance["author_space"]["commit"] != HEAD:
        raise ValueError("Fin-Analyst author Space provenance changed")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"].strip():
        raise ValueError("frozen registry unexpectedly contains a Fin-Analyst artifact")


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
    rows[matches[0]] = fin_analyst_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)
    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "first-author pre-live Hugging Face deployment recovered after the frozen registry audit",
        "corrected_at_utc": ROW_AUDIT_AT,
        "evidence": "paper_runs/paper_replication_audits/fin_analyst/source_provenance.json",
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
