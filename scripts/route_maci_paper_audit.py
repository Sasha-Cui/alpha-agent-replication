#!/usr/bin/env python3
"""Route the pinned MACI paper/source audit into the frozen artifact evidence.

The generic artifact crawler cannot inspect the 316 MB author archive under
its 50 MB safety limit. This deterministic correction replaces only MACI,
preserves prior post-freeze corrections, and recomputes the public-artifact
summary from the pinned multi-version paper/source audit.
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


SYSTEM_ID = "SYS-MACI"
URL = "https://github.com/lyc0603/multi-agent"
OWNER_REPO = "lyc0603/multi-agent"
HEAD = "2326185cc2d1eff02724cfeb88116ebb13f904e7"
OBSERVED_AT = "2026-08-12T00:07:52+00:00"
ROW_AUDIT_AT = "2026-08-12T00:00:00+00:00"
ARCHIVE_BYTES = 316_791_931
PAPER_MANIFEST = ROOT / "paper_runs/paper_replication_audits/maci/manifest.json"
SOURCE_INVENTORY = ROOT / "paper_runs/paper_replication_audits/maci/author_source_inventory.json"
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
        "archive_bytes": ARCHIVE_BYTES,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 6547,
        "has_code": True,
        "has_environment": True,
        "has_runner": True,
        "has_support": False,
        "explicit_nonrunnable": False,
        "code_markers": [
            "environ/agent.py",
            "environ/constants.py",
            "environ/data_loader.py",
            "environ/env.py",
            "environ/env_datahander.py",
            "environ/env_portfolio.py",
            "environ/evaluator.py",
            "environ/exhibits.py",
            "environ/explanation.py",
            "environ/fetch/cryptocompare.py",
            "environ/instructions.py",
            "environ/prompt_generator.py",
            "environ/prompts.py",
            "environ/settings.py",
            "environ/utils.py",
            "scripts/ap.py",
            "scripts/benchmark.py",
            "scripts/cmkt.py",
            "scripts/fetch/coingecko.py",
            "scripts/fetch/cointelegraph.py",
        ],
        "environment_markers": ["pyproject.toml"],
        "runner_markers": [
            "scripts/ap.py",
            "scripts/benchmark.py",
            "scripts/cmkt.py",
            "scripts/fetch/coingecko.py",
            "scripts/fetch/cointelegraph.py",
            "scripts/fetch/rf.py",
            "scripts/fetch/stablecoin.py",
            "scripts/fine_tuning.py",
            "scripts/nasdaq.py",
            "scripts/plot/colorbar.py",
            "scripts/plot/portfolio.py",
            "scripts/process/env_data.py",
            "scripts/process/paper.py",
            "scripts/process/signal/capm.py",
            "scripts/process/signal/cmkt.py",
            "scripts/process/signal/common_factors.py",
            "scripts/process/signal/crypto_daily.py",
            "scripts/process/signal/crypto_weekly.py",
            "scripts/process/signal/gecko_all.py",
            "scripts/process/signal/market_factors.py",
        ],
        "support_markers": [],
    }


def maci_row() -> dict[str, Any]:
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
        "check_method": "git ls-remote plus bounded 316 MB archive inspection and full multi-version paper/source audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": OWNER_REPO,
        "default_branch": "main",
        "head_sha": HEAD,
        "observed_license": "MIT",
        "license_source": "github_api_and_pinned_author_archive",
        "static_observation": observation,
        "errors": [],
    }
    basis = {
        "definition": definitions,
        "evidence": [{
            "url": URL,
            "tier": "R2",
            "basis": "code+environment manifest; runners present but no qualifying test/example/config support package",
            "markers": observation,
        }],
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "MACI — LLM-Powered Multi-Agent System for Automated Crypto Portfolio Management",
        "stratum": "T",
        "main_FT": "Y",
        "artifact_urls": URL,
        "artifact_url_count": 1,
        "artifact_url_types": "github_repository",
        "public_artifact_listed": "Y",
        "reachability_outcome": "reachable_all",
        "github_owner_repos": OWNER_REPO,
        "default_branch_head_shas": f"{OWNER_REPO}@main={HEAD}",
        "observed_licenses": f"{OWNER_REPO}=MIT",
        "static_fidelity_tier": "R2",
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
        "v1_v2_published_table_units": 321,
        "v1_v2_table_units_faithfully_regenerated": 0,
        "v1_published_plotted_result_units_author_output_verified": 21,
        "v1_published_plotted_result_units_regenerated": 0,
        "v3_published_table_units": 442,
        "v3_table_units_faithfully_regenerated": 0,
        "v3_source_files_recovered": 0,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"MACI paper manifest mismatch for {key}")
    inventory = json.loads(SOURCE_INVENTORY.read_text(encoding="utf-8"))
    if inventory["current_commit"] != HEAD:
        raise ValueError("MACI current author head changed from the pinned audit")
    if inventory["v3_implementation_recovered"] is not False:
        raise ValueError("MACI audit unexpectedly reports a v3 implementation")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("MACI registry route is not the first-author repository")


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
    rows[matches[0]] = maci_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)

    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "the first-author v1/v2 source repository was recovered after the frozen registry; the rewritten v3 implementation remains unreleased",
        "corrected_at_utc": ROW_AUDIT_AT,
        "evidence": "paper_runs/paper_replication_audits/maci/manifest.json",
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
