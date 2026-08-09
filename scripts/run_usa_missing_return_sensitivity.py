#!/usr/bin/env python3
"""Build the referee-requested U.S. missing-return sensitivity.

The frozen primary evaluator assigns zero to a held security whose next-month
excess return is missing. The existing monthly output also records the fraction
of gross portfolio weight exposed to those missing returns and total gross
exposure. This script applies the evaluator's already-defined position-adverse
unit-move policy exactly at the frozen weights:

    adverse return = zero-policy return - missing gross-weight share * gross exposure

The policy assigns -100% to a missing long return and +100% to a missing short
return. It is an intentionally severe stress, not an estimate of expected
delisting returns. Portfolio formation, turnover, factor returns, calendars,
and all 62 mappings remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_submission_evidence as runner


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def apply_position_adverse_unit_move(monthly: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with the exact frozen-weight adverse missing contribution."""
    required = {
        "gross_return",
        "gross_exposure",
        "missing_excess_return_gross_weight",
    }
    missing = required - set(monthly.columns)
    if missing:
        raise ValueError(f"monthly return file lacks required fields: {sorted(missing)}")
    result = monthly.copy()
    exposure = result["missing_excess_return_gross_weight"].fillna(0.0).astype(float)
    gross = result["gross_exposure"].fillna(0.0).astype(float)
    result["missing_return_adverse_contribution"] = -(exposure * gross)
    result["gross_return"] = (
        result["gross_return"].astype(float)
        + result["missing_return_adverse_contribution"]
    )
    return result


def positive_counts(frame: pd.DataFrame) -> dict[str, int | float]:
    ok = frame.loc[frame["status"] == "ok"].copy()
    return {
        "n_estimable": len(ok),
        "median_alpha_annualized": float(ok["alpha_annualized"].median()),
        "q25_alpha_annualized": float(ok["alpha_annualized"].quantile(0.25)),
        "q75_alpha_annualized": float(ok["alpha_annualized"].quantile(0.75)),
        "positive_alpha_count": int((ok["alpha_annualized"] > 0).sum()),
        "nominal_positive_5pct": int(
            ((ok["alpha_annualized"] > 0) & (ok["p_value_two_sided"] <= 0.05)).sum()
        ),
        "holm_positive_5pct": int(
            ((ok["alpha_annualized"] > 0) & (ok["holm_p_value"] <= 0.05)).sum()
        ),
        "max_t_positive_5pct": int(
            ((ok["alpha_annualized"] > 0) & (ok["max_abs_t_p_value"] <= 0.05)).sum()
        ),
        "simultaneous_lower_bound_above_2pp": int(
            (ok["simultaneous_ci_low_annualized"] >= 0.02).sum()
        ),
    }


def scope_summary(
    policy: str,
    primary: pd.DataFrame,
    mapping: pd.DataFrame,
) -> list[dict[str, int | float | str]]:
    role = mapping[["candidate_id", "good_faith_empirical_role"]].drop_duplicates()
    if len(role) != 62:
        raise RuntimeError("mapping ledger does not assign one role to each of 62 candidates")
    joined = primary.merge(role, on="candidate_id", how="left", validate="one_to_one")
    rows: list[dict[str, int | float | str]] = []
    scopes = {
        "all_mappings": joined,
        "source_grounded_components": joined.loc[
            joined["good_faith_empirical_role"] == "source_grounded_component_test"
        ],
        "narrative_stress_tests": joined.loc[
            joined["good_faith_empirical_role"] == "exploratory_favorable_stress_test"
        ],
    }
    for scope, frame in scopes.items():
        ok = frame.loc[frame["status"] == "ok"].copy()
        p_map = {
            str(row.candidate_id): (
                float(row.p_value_two_sided)
                if float(row.alpha_annualized) > 0 and np.isfinite(row.p_value_two_sided)
                else 1.0
            )
            for row in ok.itertuples()
        }
        holm = runner.multiplicity_adjustments(p_map, planned_m=len(frame))
        holm_positive = int(
            holm.merge(ok[["candidate_id", "alpha_annualized"]], on="candidate_id")
            .eval("alpha_annualized > 0 and holm_p_value <= 0.05")
            .sum()
        )
        rows.append(
            {
                "policy": policy,
                "scope": scope,
                "n_estimable": len(ok),
                "median_alpha_annualized": float(ok["alpha_annualized"].median()),
                "positive_alpha_count": int((ok["alpha_annualized"] > 0).sum()),
                "nominal_positive_5pct": int(
                    ((ok["alpha_annualized"] > 0) & (ok["p_value_two_sided"] <= 0.05)).sum()
                ),
                "holm_positive_5pct_within_scope": holm_positive,
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Defaults to paper_runs/submission_evidence/usa_missing_return_sensitivity.",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    base = root / "paper_runs/submission_evidence/usa_retrospective_corrected"
    mapping_path = root / "paper_runs/submission_evidence/mapping_audit/mapping_audit.csv"
    out_dir = (
        args.out_dir.resolve()
        if args.out_dir
        else root / "paper_runs/submission_evidence/usa_missing_return_sensitivity"
    )
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite nonempty output directory: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    candidate_path = base / "candidate_monthly_country_equal.csv"
    factor_path = base / "factor_monthly_country_equal.csv"
    metadata_path = base / "candidate_metadata.csv"
    zero_primary_path = base / "candidate_primary_results.csv"
    candidates = pd.read_csv(candidate_path, parse_dates=["month"])
    factors = pd.read_csv(factor_path, parse_dates=["month"])
    metadata = pd.read_csv(metadata_path)
    mapping = pd.read_csv(mapping_path)
    zero_primary = pd.read_csv(zero_primary_path)

    adverse_candidates = apply_position_adverse_unit_move(candidates)
    _, adverse_primary, _, bootstrap_meta = runner.run_pooled_analysis(
        adverse_candidates,
        factors,
        metadata,
        n_bootstrap=args.bootstrap,
    )

    missing_by_candidate = candidates.groupby("candidate_id").agg(
        mean_missing_return_gross_weight=("missing_excess_return_gross_weight", "mean"),
        max_missing_return_gross_weight=("missing_excess_return_gross_weight", "max"),
        months_with_missing_return_exposure=(
            "missing_excess_return_gross_weight",
            lambda values: int((values.fillna(0.0) > 0).sum()),
        ),
    ).reset_index()

    policy_rows = []
    for policy, frame in (
        ("zero_primary", zero_primary),
        ("position_adverse_100", adverse_primary),
    ):
        row: dict[str, int | float | str] = {"policy": policy}
        row.update(positive_counts(frame))
        row.update(
            {
                "median_candidate_mean_missing_return_gross_weight": float(
                    missing_by_candidate["mean_missing_return_gross_weight"].median()
                ),
                "max_candidate_mean_missing_return_gross_weight": float(
                    missing_by_candidate["mean_missing_return_gross_weight"].max()
                ),
                "maximum_monthly_missing_return_gross_weight": float(
                    missing_by_candidate["max_missing_return_gross_weight"].max()
                ),
            }
        )
        policy_rows.append(row)

    outputs = {
        "candidate_primary_results.csv": adverse_primary,
        "missing_exposure_by_candidate.csv": missing_by_candidate,
        "policy_summary.csv": pd.DataFrame(policy_rows),
        "scope_summary.csv": pd.DataFrame(
            scope_summary("zero_primary", zero_primary, mapping)
            + scope_summary("position_adverse_100", adverse_primary, mapping)
        ),
    }
    for name, frame in outputs.items():
        frame.to_csv(out_dir / name, index=False)

    manifest = {
        "analysis_label": "post_hoc_referee_requested_missing_return_sensitivity",
        "policy": (
            "At frozen weights, assign -100% to a missing long return and +100% "
            "to a missing short return; formation, turnover, factors, and mappings unchanged."
        ),
        "interpretation": (
            "Intentionally severe stress, not an expected-return or delisting-return estimate."
        ),
        "bootstrap": bootstrap_meta,
        "input_sha256": {
            str(path.relative_to(root)): sha256(path)
            for path in (
                candidate_path,
                factor_path,
                metadata_path,
                zero_primary_path,
                mapping_path,
            )
        },
        "output_sha256": {name: sha256(out_dir / name) for name in outputs},
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"out_dir": str(out_dir), "policy_summary": policy_rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
