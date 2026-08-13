#!/usr/bin/env python3
"""Route the recovered GPT-Signal author source into frozen artifact evidence.

The repository promised by the paper is now 404 and its surviving 2024 Wayback
capture contains only a README.  A separate author-owned pre-publication thesis
repository contains the exact data, GPT outputs, figures, and analysis code.
This deterministic correction routes that recovered source at R1, preserves all
other evidence corrections, and recomputes the public-artifact summary.
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


SYSTEM_ID = "SYS-GPT-SIGNAL"
URL = "https://github.com/Yiningww/Thesis"
OWNER_REPO = "Yiningww/Thesis"
HEAD = "434230ca9123048a4d79e2cc1390b23b050ef68e"
ARCHIVE_SHA256 = "451d7334bf4a6de94dcbc6cf2e29d9f5c30f228a58457fdd278d5ba9772992fd"
OBSERVED_AT = "2026-08-11T20:17:58+00:00"
ROW_AUDIT_AT = "2026-08-11T00:00:00+00:00"
PAPER_MANIFEST = ROOT / "paper_runs/paper_replication_audits/gpt_signal/manifest.json"
SOURCE_PROVENANCE = ROOT / "paper_runs/paper_replication_audits/gpt_signal/source_provenance.json"
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
        "archive_bytes": 181_698_560,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 13_884,
        "has_code": True,
        "has_environment": False,
        "has_runner": False,
        "has_support": True,
        "explicit_nonrunnable": False,
        "code_markers": [
            "Code/Data/data.py",
            "Code/Data/plot.py",
            "Code/langchain/prompt.py",
        ],
        "environment_markers": [],
        "runner_markers": [],
        "support_markers": [
            "Code/Data/Information Technology/DEC start/AAPL.xlsx",
            "Code/Data/historical_return/AAPL2015-12-31-2020-12-31.csv",
            "Code/langchain/output/gpt-4-1106-preview/zero_shot_cot/out_gpt-4-1106-preview_zero_shot_cot_20240207-154023.csv",
        ],
    }


def gpt_signal_row() -> dict[str, Any]:
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
        "check_method": "git ls-remote plus pinned GitHub archive and paper-level source/data/output audit",
        "checked_at_utc": OBSERVED_AT,
        "reachable": True,
        "github_owner_repo": OWNER_REPO,
        "default_branch": "main",
        "head_sha": HEAD,
        "observed_license": "NOASSERTION",
        "license_source": "no_license_file_or_GitHub_license_detected_in_pinned_archive",
        "static_observation": observation,
        "errors": [],
    }
    basis = {
        "definition": definitions,
        "evidence": [{
            "url": URL,
            "tier": "R1",
            "basis": "author source/data/outputs are observable, but no dependency manifest or reliable end-to-end runner is shipped",
            "markers": observation,
        }],
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "GPT-Signal",
        "stratum": "F",
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
        "failure_category": "static_package_insufficient",
        "native_execution_attempted": "N",
        "audit_timestamp_utc": ROW_AUDIT_AT,
        "artifact_url_results_json": compact([result]),
        "errors_json": "[]",
    }


def validate_inputs() -> None:
    manifest = json.loads(PAPER_MANIFEST.read_text(encoding="utf-8"))
    expected = {
        "author_source_files": 13_884,
        "published_result_units": 1_554,
        "published_result_units_reproduced": 1_549,
        "published_correlation_cells_reproduced": 1_309,
        "published_boxplot_statistics_reproduced": 240,
        "reachable_unique_out_or_txt_blobs_scanned": 230,
        "historical_twenty_value_windows_scanned": 1_356,
        "historical_matching_all_sector_evc_windows": 0,
        "alternate_author_evc_formula_reproduces_plot": False,
        "all_sector_evc_plot_only_uniform_translation": True,
        "paper_result_credit_for_plot_translation": False,
        "llm_calls_made": 0,
        "full_end_to_end_pipeline_reproduced": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"GPT-Signal paper manifest mismatch for {key}")
    provenance = json.loads(SOURCE_PROVENANCE.read_text(encoding="utf-8"))
    if provenance["author_repository"] != URL:
        raise ValueError("GPT-Signal paper audit does not identify the routed author repository")
    if provenance["head"] != HEAD:
        raise ValueError("GPT-Signal author repository head changed from the pinned audit")
    if provenance["archive_sha256"] != ARCHIVE_SHA256:
        raise ValueError("GPT-Signal author archive hash changed from the pinned audit")
    if provenance["license"] != "none_observed" or provenance["dependency_manifest"] != "none_observed":
        raise ValueError("GPT-Signal R1 license/environment basis changed")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("GPT-Signal registry route is not the recovered author repository")


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
    rows[matches[0]] = gpt_signal_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)

    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "author-owned pre-publication thesis repository recovers the exact GPT-Signal source, data, and outputs; the paper-listed repository is deleted and its surviving capture is only a placeholder",
        "corrected_at_utc": ROW_AUDIT_AT,
        "evidence": "paper_runs/paper_replication_audits/gpt_signal/source_provenance.json",
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
