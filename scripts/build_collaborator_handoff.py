#!/usr/bin/env python3
"""Build a compact, redistributable collaborator result index.

The index joins frozen aggregate outputs. It does not read or export
security-level observations, monthly strategy returns, or a factor panel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


DEFAULT_OUTPUT = Path("paper_runs/handoff")
INPUTS = {
    "mapping_audit": Path("paper_runs/submission_evidence/mapping_audit/mapping_audit.csv"),
    "benchmark_comparison": Path(
        "paper_runs/submission_evidence/retained_benchmark_ladder/"
        "strategy_benchmark_comparison.csv"
    ),
    "top_factor_diagnostics": Path(
        "paper_runs/submission_evidence/retained_benchmark_ladder/"
        "strategy_top_jkp_factors.csv"
    ),
}

AUDIT_COLUMNS = [
    "candidate_id",
    "replication_scope",
    "source_evidence_status",
    "mapping_support_note",
    "central_omitted_components",
    "benefit_of_doubt_implementation",
    "negative_evidence_boundary",
    "mapping_frozen_before_us_returns_inspected",
    "independent_second_coder",
]
TOP_FACTOR_COLUMNS = {
    "candidate_id": "candidate_id",
    "jkp_factor_id": "closest_factor_id",
    "jkp_factor_column": "closest_factor_column",
    "correlation": "closest_factor_correlation",
    "absolute_correlation": "closest_factor_absolute_correlation",
    "n_common_months": "closest_factor_common_months",
    "common_start": "closest_factor_common_start",
    "common_end": "closest_factor_common_end",
}
BENCHMARK_COLUMNS = [
    f"{prefix}_{suffix}"
    for prefix in ("capm", "ff3", "ff5_mom", "ff5_mom_jkp132")
    for suffix in (
        "alpha_annualized",
        "alpha_t_hac",
        "p_value_two_sided",
        "holm_p_value",
        "positive",
        "nominal_positive",
        "holm_positive",
    )
]
OUTPUT_COLUMNS = [
    "canonical_work_id",
    "bibtex_key",
    "title",
    "year",
    "source_name",
    "candidate_id",
    "paper_ref",
    "proxy_formula",
    "mapping_fidelity_tier",
    "implementation_basis",
    *AUDIT_COLUMNS[1:],
    *BENCHMARK_COLUMNS,
    "strongest_benchmark_positive",
    "strongest_benchmark_nominal_positive",
    "strongest_benchmark_holm_positive",
    "alpha_attenuation_ff3_to_jkp132",
    "alpha_attenuation_ff5_mom_to_jkp132",
    *[column for column in TOP_FACTOR_COLUMNS.values() if column != "candidate_id"],
]
EXPECTED_IMPLEMENTATION_COUNTS = {
    "in_spirit_reconstruction": 37,
    "released_code_component_adaptation": 1,
    "source_grounded_paper_component": 12,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def build_handoff(root: Path, output_dir: Path) -> tuple[Path, Path]:
    """Build and validate the strategy index and deterministic manifest."""
    root = root.resolve()
    output_dir = resolve(root, output_dir)
    input_paths = {name: resolve(root, path) for name, path in INPUTS.items()}

    comparison = pd.read_csv(input_paths["benchmark_comparison"])
    audit = pd.read_csv(input_paths["mapping_audit"])
    factors = pd.read_csv(input_paths["top_factor_diagnostics"])
    factors = factors[factors["factor_rank_by_absolute_correlation"].eq(1)].copy()

    for label, frame in (
        ("benchmark comparison", comparison),
        ("mapping audit", audit),
        ("top-factor diagnostics", factors),
    ):
        if frame["candidate_id"].duplicated().any():
            raise ValueError(f"{label} candidate identifiers are not unique")

    joined = comparison.merge(
        audit[AUDIT_COLUMNS], on="candidate_id", how="left", validate="one_to_one"
    ).merge(
        factors[list(TOP_FACTOR_COLUMNS)].rename(columns=TOP_FACTOR_COLUMNS),
        on="candidate_id",
        how="left",
        validate="one_to_one",
    )
    joined[AUDIT_COLUMNS[1:]] = joined[AUDIT_COLUMNS[1:]].fillna(
        "not_recorded"
    )
    joined = joined[OUTPUT_COLUMNS].sort_values(
        ["canonical_work_id", "candidate_id"], kind="stable"
    )

    if len(joined) != 50 or joined["candidate_id"].nunique() != 50:
        raise ValueError("Handoff index must contain exactly 50 unique strategies")
    if joined["canonical_work_id"].nunique() != 40:
        raise ValueError("Handoff index must cover exactly 40 unique papers")
    counts = joined["implementation_basis"].value_counts().to_dict()
    if counts != EXPECTED_IMPLEMENTATION_COUNTS:
        raise ValueError(f"Unexpected implementation partition: {counts}")
    if joined.isna().any().any():
        missing = joined.columns[joined.isna().any()].tolist()
        raise ValueError(f"Handoff index contains missing values: {missing}")

    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "strategy_result_index.csv"
    joined.to_csv(index_path, index=False, float_format="%.12g", lineterminator="\n")

    manifest = {
        "schema_version": 1,
        "purpose": "Compact collaborator index of frozen, already-derived results",
        "claim_boundary": {
            "native_agent_replications": 0,
            "released_code_component_adaptations": 1,
            "source_grounded_paper_components": 12,
            "in_spirit_reconstructions": 37,
            "interpretation": (
                "The 50 rows are implemented common-task mappings, not 50 native "
                "agent replications or independent confirmations of paper claims."
            ),
        },
        "coverage": {
            "strategies": 50,
            "papers": 40,
            "benchmark_specifications_per_strategy": 4,
        },
        "excluded_data": {
            "security_level_data_included": False,
            "monthly_strategy_returns_included": False,
            "jkp_factor_panel_included": False,
            "external_repository_contents_included": False,
        },
        "inputs": {
            name: {"path": path.relative_to(root).as_posix(), "sha256": sha256(path)}
            for name, path in sorted(input_paths.items())
        },
        "outputs": {
            "strategy_result_index": {
                "path": (
                    index_path.relative_to(root).as_posix()
                    if index_path.is_relative_to(root)
                    else index_path.as_posix()
                ),
                "rows": len(joined),
                "columns": len(joined.columns),
                "sha256": sha256(index_path),
            }
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return index_path, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    index_path, manifest_path = build_handoff(args.root, args.output_dir)
    print(index_path)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
