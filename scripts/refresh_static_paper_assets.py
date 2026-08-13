#!/usr/bin/env python3
"""Refresh paper assets affected only by static artifact-evidence corrections.

The full paper builder additionally requires large candidate-monthly files that
are intentionally absent from the compact repository.  This strict partial
builder recomputes only census/artifact/native-ledger values and their direct
tables, figures, claim hashes, and macros while preserving all unrelated
validated results.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_paper_assets as paper  # noqa: E402


REGISTRY = ROOT / "literature_review/census_v1/system_registry.csv"
AUDIT = ROOT / "paper_runs/submission_evidence/artifact_audit/artifact_audit.csv"
SUMMARY = ROOT / "paper_runs/submission_evidence/artifact_audit/artifact_audit_summary.csv"
NATIVE = ROOT / "paper_runs/submission_evidence/native_fidelity_ledger.csv"
CLAIMS = ROOT / "paper_runs/submission_evidence/claims.csv"
PAPER = ROOT / "docs/paper"


def computed_macros(
    registry: pd.DataFrame,
    audit: pd.DataFrame,
    native: pd.DataFrame,
) -> dict[str, str]:
    ft = audit[audit["main_FT"].eq("Y")].copy()
    method_count = int(registry["main_FT"].eq("Y").sum())
    listed = int(ft["public_artifact_listed"].eq("Y").sum())
    reachable = int(ft["reachability_outcome"].eq("reachable_all").sum())
    licenses = ft["observed_licenses"].fillna("").astype(str).str.strip()
    licensed = int((licenses.ne("") & ~licenses.str.contains("NOASSERTION", case=False)).sum())
    pinned = int(ft["default_branch_head_shas"].fillna("").astype(str).str.strip().ne("").sum())
    tiers = ft["static_fidelity_tier"].value_counts().reindex(["R0", "R1", "R2", "R3"], fill_value=0)
    tier_text = ", ".join(rf"\artifacttier{{{tier}}}: {int(tiers[tier])}" for tier in tiers.index)
    native_dated = int(native["native_dated_signal_or_return_shipped"].eq("Y").sum())
    native_compatible = int(native["prespecified_G7_monthly_common_task_compatible"].eq("Y").sum())
    targeted = int(native["targeted_execution_audit_status"].astype(str).ne("not_targeted_in_legacy_execution_audit").sum())
    translatable = int(
        native["targeted_execution_audit_status"]
        .astype(str)
        .str.contains("seed_idea_proxy|component_gate_separate", regex=True)
        .sum()
    )
    low, high = paper.wilson_interval(listed, method_count)
    values = {
        "SystemCount": str(len(registry)),
        "MethodSystemCount": str(method_count),
        "ArtifactCountFT": str(listed),
        "ArtifactRateFT": paper.fmt_percent(listed / method_count, 1),
        "ArtifactWilsonFT": paper.fmt_interval(low, high),
        "ReachableArtifactCountFT": str(reachable),
        "LicensedArtifactCountFT": str(licensed),
        "PinnedRepoCountFT": str(pinned),
        "ArtifactTierSummaryFT": tier_text,
        "NativeDatedOutputCount": str(native_dated),
        "NativeReturnCount": str(native_compatible),
        "NativeUnavailableCount": str(method_count - native_compatible),
        "TargetedAuditCount": str(targeted),
        "TranslatableSeedCount": str(translatable),
    }
    expected = {
        "SystemCount": "103",
        "MethodSystemCount": "67",
        "ArtifactCountFT": "29",
        "ReachableArtifactCountFT": "28",
        "LicensedArtifactCountFT": "16",
        "PinnedRepoCountFT": "27",
        "ArtifactTierSummaryFT": r"\artifacttier{R0}: 39, \artifacttier{R1}: 9, \artifacttier{R2}: 6, \artifacttier{R3}: 13",
        "TargetedAuditCount": "46",
        "TranslatableSeedCount": "1",
    }
    for key, value in expected.items():
        if values[key] != value:
            raise ValueError(f"corrected static macro mismatch for {key}: {values[key]}")
    return values


def update_generated_results(values: dict[str, str]) -> None:
    path = PAPER / "generated_results.tex"
    text = path.read_text(encoding="utf-8")
    for name, value in values.items():
        pattern = re.compile(rf"^\\newcommand\{{\\{name}\}}\{{.*\}}$", re.MULTILINE)
        text, count = pattern.subn(lambda _match, n=name, v=value: rf"\newcommand{{\{n}}}{{{v}}}", text)
        if count != 1:
            raise ValueError(f"generated macro occurrence mismatch: {name}={count}")
    paper.write_text(path, text)


def update_claims(values: dict[str, str]) -> list[paper.Claim]:
    with CLAIMS.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    registry_hash = paper.sha256_file(REGISTRY)
    audit_hash = paper.sha256_file(AUDIT)
    native_hash = paper.sha256_file(NATIVE)
    for row in rows:
        macro = row["macro"]
        if macro in ("SystemCount", "MethodSystemCount"):
            row["source_sha256"] = registry_hash
        if macro in {
            "ArtifactCountFT", "ArtifactRateFT", "ArtifactWilsonFT",
            "ReachableArtifactCountFT", "LicensedArtifactCountFT",
            "PinnedRepoCountFT", "ArtifactTierSummaryFT",
        }:
            row["source_sha256"] = audit_hash
        if macro in {
            "NativeDatedOutputCount", "NativeReturnCount", "NativeUnavailableCount",
            "TargetedAuditCount", "TranslatableSeedCount",
        }:
            row["source_sha256"] = native_hash
        if macro in values:
            row["rendered_value"] = values[macro]
        if macro == "TargetedAuditCount":
            row["claim"] = "Systems examined in a targeted paper-level or execution audit."
        if macro == "TranslatableSeedCount":
            row["source_filter"] = (
                "targeted_execution_audit_status contains seed_idea_proxy or component_gate_separate"
            )
    fields = list(paper.Claim.__dataclass_fields__)
    with CLAIMS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return [paper.Claim(**row) for row in rows]


def main() -> None:
    registry, audit, _summary, native = paper.load_static_inputs(REGISTRY, AUDIT, SUMMARY, NATIVE)
    values = computed_macros(registry, audit, native)
    update_generated_results(values)
    claims = update_claims(values)
    paper.build_artifact_summary_table(audit, native, PAPER / "tables/artifact_summary.tex")
    paper.build_system_registry_table(registry, PAPER / "tables/system_registry.tex")
    paper.build_artifact_failure_table(native, registry, PAPER / "tables/artifact_failures.tex")
    paper.build_claim_map_table(claims, PAPER / "tables/claim_map.tex")
    paper.configure_plotting()
    paper.build_census_funnel_figure(registry, audit, native, PAPER / "figures/census_funnel.pdf")
    paper.build_artifact_attrition_figure(audit, PAPER / "figures/artifact_attrition.pdf")
    print(values)


if __name__ == "__main__":
    main()
