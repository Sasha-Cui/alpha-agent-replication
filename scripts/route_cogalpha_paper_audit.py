#!/usr/bin/env python3
"""Route the pinned CogAlpha paper/prompt audit into artifact evidence.

The frozen census predated the authors' prompt-template repository.  The
repository is reachable and revision-pinned, but intentionally contains no
runtime, data, model endpoints, or outputs.  This deterministic correction
therefore records an R1 prompt specification—not CogAlpha source code—and
recomputes the public-artifact summary without granting result credit.
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


SYSTEM_ID = "SYS-COG-ALPHA"
URL = "https://github.com/uwFengyuan/CogAlpha_Prompt"
OWNER_REPO = "uwFengyuan/CogAlpha_Prompt"
HEAD = "6294d9ffa9dfc286fb14e82343f8f22a5f928c1c"
ARCHIVE_SHA256 = "fd51d57bb161a6efa2130ea2630f6dc9742c65dd423ca8ab349d54ab45266f0e"
OBSERVED_AT = "2026-08-12T15:00:00+00:00"
ROW_AUDIT_AT = "2026-08-12T00:00:00+00:00"
PAPER_MANIFEST = ROOT / "paper_runs/paper_replication_audits/cogalpha/manifest.json"
SOURCE_PROVENANCE = ROOT / "paper_runs/paper_replication_audits/cogalpha/source_provenance.json"
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
        "archive_bytes": 447_452,
        "archive_sha256": ARCHIVE_SHA256,
        "checked_at_utc": OBSERVED_AT,
        "file_count": 47,
        "tree_bytes": 563_111,
        "prompt_template_count": 39,
        "has_code": False,
        "has_environment": False,
        "has_runner": False,
        "has_support": True,
        "explicit_nonrunnable": True,
        "code_markers": [],
        "environment_markers": [],
        "runner_markers": [],
        "support_markers": [
            "README.md",
            "prompts/seven_level_agent_hierarchy/base_agent.md",
            "prompts/multi_agent_quality_checker/judge_agent.md",
            "prompts/thinking_evolution/mutation_agent.md",
        ],
        "excluded_runtime_materials": [
            "runtime code", "datasets", "experiment outputs", "model endpoints",
            "API keys", "local paths",
        ],
    }


def cogalpha_row() -> dict[str, Any]:
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
        "check_method": "author repository plus pinned Git history, tree, archive, and full primary-source audit",
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
            "basis": "39 author prompt templates; README explicitly excludes runtime code, data, model endpoints, and outputs",
            "markers": observation,
        }],
    }
    return {
        "system_id": SYSTEM_ID,
        "system_name": "CogAlpha",
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
        "failure_category": "none",
        "native_execution_attempted": "N",
        "audit_timestamp_utc": ROW_AUDIT_AT,
        "artifact_url_results_json": compact([result]),
        "errors_json": "[]",
    }


def validate_inputs() -> None:
    manifest = json.loads(PAPER_MANIFEST.read_text(encoding="utf-8"))
    expected = {
        "author_prompt_repository_recovered": True,
        "author_prompt_template_count": 39,
        "author_prompt_model_calls_replayed": 0,
        "author_output_curve_series_correspondence": 4,
        "author_output_curve_series_regenerated": 0,
        "native_empirical_units_regenerated": 0,
        "full_end_to_end_pipeline_reproduced": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"CogAlpha paper manifest mismatch for {key}")
    if manifest["editions"]["arxiv_v1"]["total_unique_empirical_units"] != 150:
        raise ValueError("CogAlpha v1 empirical denominator changed")
    if manifest["editions"]["arxiv_v4_acl_final"]["total_unique_empirical_units"] != 306:
        raise ValueError("CogAlpha current empirical denominator changed")
    provenance = json.loads(SOURCE_PROVENANCE.read_text(encoding="utf-8"))
    release = provenance["prompt_release"]
    if release["repository"] != URL or release["commit"] != HEAD:
        raise ValueError("CogAlpha prompt release changed from the pinned audit")
    if release["runtime_code_included"] or release["experiment_outputs_included"]:
        raise ValueError("CogAlpha release boundary changed")
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="|"))
    row = next(item for item in rows if item["system_id"] == SYSTEM_ID)
    if row["official_artifact"] != URL:
        raise ValueError("CogAlpha registry route is not the author prompt repository")


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
    rows[matches[0]] = cogalpha_row()
    long_summary, grouped_summary = artifact.summary_rows(rows)

    audit_payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    correction = {
        "system_id": SYSTEM_ID,
        "reason": "author prompt repository published after the frozen census; repository is R1 specification evidence, not CogAlpha runtime code",
        "corrected_at_utc": ROW_AUDIT_AT,
        "evidence": "paper_runs/paper_replication_audits/cogalpha/source_provenance.json",
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
