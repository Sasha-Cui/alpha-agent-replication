#!/usr/bin/env python3
"""Route the pinned FinAgent paper audit into the frozen artifact evidence.

The original census missed an author-linked repository that predates the
cutoff.  This deterministic correction replaces only the FinAgent row, keeps
the original 103-system audit untouched otherwise, and recomputes the public
artifact summary from the corrected rows.
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


SYSTEM_ID = "SYS-FIN-AGENT"
URL = "https://github.com/DVampire/FinAgent"
HEAD = "17248a0b8b729ee3e093e30bb7bea7f52181f363"
OBSERVED_AT = "2026-08-11T13:22:39.083413+00:00"
ROW_AUDIT_AT = "2026-08-11T00:00:00+00:00"
PAPER_MANIFEST = ROOT / "paper_runs/paper_replication_audits/finagent/manifest.json"
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
        "archive_bytes": 189389,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 342,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": [
            "finagent/environment/trading.py",
            "finagent/memory/basic_memory.py",
            "finagent/prompt/helper.py",
            "finagent/provider/openai.py",
        ],
        "environment_markers": ["requirements.txt"],
        "runner_markers": ["tools/main.py"],
        "support_markers": [
            "configs/exp/trading/AAPL.py",
            "configs/exp/trading/ETHUSD.py",
            "res/prompts/template/valid/trading/decision.html",
        ],
    }


def finagent_row() -> dict[str, Any]:
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
        "check_method": "git ls-remote --symref plus bounded GitHub archive inspection",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": "DVampire/FinAgent",
        "default_branch": "main",
        "head_sha": HEAD,
        "observed_license": "MIT",
        "license_source": "github_api_and_RELEASE_LICENSE_sha256_62cbdb19bdc50f23545e787f8c244400907163bc4f16e0149ce4e876abc4ca07",
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
        "system_name": "FinAgent",
        "stratum": "T",
        "main_FT": "Y",
        "artifact_urls": URL,
        "artifact_url_count": 1,
        "artifact_url_types": "github_repository",
        "public_artifact_listed": "Y",
        "reachability_outcome": "reachable_all",
        "github_owner_repos": "DVampire/FinAgent",
        "default_branch_head_shas": f"DVampire/FinAgent@main={HEAD}",
        "observed_licenses": "DVampire/FinAgent=MIT",
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
        "source_current_commit": HEAD,
        "source_provenance": "repository_linked_from_lead_author_homepage",
        "published_result_display_units_total": 1061,
        "published_result_display_units_reproduced": 0,
        "paper_result_credit": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"FinAgent paper manifest mismatch for {key}")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("FinAgent registry route is not the author-linked repository")


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
    rows[matches[0]] = finagent_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)

    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "author-linked pre-cutoff repository omitted from original registry",
        "corrected_at_utc": ROW_AUDIT_AT,
        "evidence": "paper_runs/paper_replication_audits/finagent/manifest.json",
        "source_head": HEAD,
    }
    for metadata in (audit_payload["metadata"], summary_payload["metadata"]):
        metadata["registry_sha256"] = sha256(REGISTRY)
        metadata["post_freeze_evidence_corrections"] = [correction]
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
