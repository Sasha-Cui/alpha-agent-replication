#!/usr/bin/env python3
"""Build the licensed-data collaborator bundle outside the public Git tree.

The bundle contains aggregate monthly strategy paths and factor returns, not
security-level records. Running this script requires an affirmative data-use
acknowledgement; that acknowledgement does not grant redistribution rights.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from run_broad_jkp_crossfit import BASE_FACTOR_COLUMNS


PRIMARY_FACTOR_COLUMNS = [
    "jkp_topn_mkt",
    "char__be_me",
    "char__market_equity",
    "char__at_gr1",
    "char__ope_be",
    "char__ret_12_1",
]
CANDIDATE_COLUMNS = [
    "market",
    "formation_month",
    "realization_month",
    "candidate_id",
    "gross_return",
    "traded_notional",
    "net_return_10bps",
    "analysis_eligible",
    "path_failure_event",
    "path_status",
    "failure_month",
    "failure_total_return",
    "missing_excess_return_gross_weight",
    "missing_total_return_gross_weight",
]
RECONSTRUCTION_FILES = {
    "benchmark_residuals.csv": "monthly_benchmark_residuals.csv",
    "benchmark_fitted_values.csv": "monthly_benchmark_fitted_values.csv",
    "benchmark_selected_lambdas.csv": "monthly_benchmark_selected_lambdas.csv",
    "benchmark_factor_loadings.parquet": (
        "monthly_benchmark_factor_loadings.parquet"
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def parse_bool(series: pd.Series) -> pd.Series:
    normalized = series.astype(str).str.strip().str.lower()
    valid = normalized.isin({"true", "false", "1", "0", "yes", "no"})
    if not valid.all():
        values = sorted(series[~valid].astype(str).unique())
        raise ValueError(f"Unrecognized boolean values: {values}")
    return normalized.isin({"true", "1", "yes"})


def retained_candidate_ids(strategy_index: pd.DataFrame) -> list[str]:
    if "candidate_id" not in strategy_index:
        raise ValueError("Strategy index has no candidate_id column")
    candidate_ids = sorted(strategy_index["candidate_id"].astype(str).tolist())
    if len(candidate_ids) != 50 or len(set(candidate_ids)) != 50:
        raise ValueError("Strategy index must contain exactly 50 unique candidates")
    return candidate_ids


def prepare_candidate_paths(
    source: pd.DataFrame,
    candidate_ids: list[str],
    cost_bps: float,
) -> pd.DataFrame:
    required = {
        "market",
        "formation_month",
        "month",
        "candidate_id",
        "gross_return",
        "traded_notional",
        "analysis_eligible",
        "path_failure_event",
        "path_status",
        "failure_month",
        "failure_total_return",
        "missing_excess_return_gross_weight",
        "missing_total_return_gross_weight",
    }
    missing = sorted(required - set(source))
    if missing:
        raise ValueError(f"Candidate matrix is missing columns: {missing}")

    frame = source[source["candidate_id"].isin(candidate_ids)].copy()
    present = set(frame["candidate_id"].astype(str).unique())
    absent = sorted(set(candidate_ids) - present)
    if absent:
        raise ValueError(f"Candidate matrix is missing retained IDs: {absent}")
    frame["formation_month"] = pd.to_datetime(
        frame["formation_month"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    frame["realization_month"] = pd.to_datetime(
        frame.pop("month"), errors="raise"
    ).dt.strftime("%Y-%m-%d")
    frame["analysis_eligible"] = parse_bool(frame["analysis_eligible"])
    frame["path_failure_event"] = parse_bool(frame["path_failure_event"])
    frame["net_return_10bps"] = (
        pd.to_numeric(frame["gross_return"], errors="raise")
        - (cost_bps / 10000.0)
        * pd.to_numeric(frame["traded_notional"], errors="raise")
    )
    frame = frame[CANDIDATE_COLUMNS].sort_values(
        ["realization_month", "candidate_id"], kind="stable"
    )
    if frame.duplicated(["realization_month", "candidate_id"]).any():
        raise ValueError("Candidate matrix has duplicate candidate-month rows")
    if frame["candidate_id"].nunique() != 50:
        raise ValueError("Prepared candidate matrix does not contain 50 candidates")
    return frame.reset_index(drop=True)


def prepare_primary_factors(source: pd.DataFrame) -> pd.DataFrame:
    required = {"market", "formation_month", "month", *PRIMARY_FACTOR_COLUMNS}
    missing = sorted(required - set(source))
    if missing:
        raise ValueError(f"Primary factor matrix is missing columns: {missing}")
    frame = source[
        ["market", "formation_month", "month", *PRIMARY_FACTOR_COLUMNS]
    ].copy()
    frame["formation_month"] = pd.to_datetime(
        frame["formation_month"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    frame["realization_month"] = pd.to_datetime(
        frame.pop("month"), errors="raise"
    ).dt.strftime("%Y-%m-%d")
    frame = frame[
        ["market", "formation_month", "realization_month", *PRIMARY_FACTOR_COLUMNS]
    ].sort_values("realization_month", kind="stable")
    if frame["realization_month"].duplicated().any():
        raise ValueError("Primary factor matrix has duplicate realization months")
    return frame.reset_index(drop=True)


def prepare_broad_factors(
    source: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    if "month" not in source or "capm_top1000_mkt" not in source:
        raise ValueError("Broad factor panel lacks month or capm_top1000_mkt")
    characteristic_columns = [
        column for column in source if column.startswith("char__")
    ]
    factor_order = [
        *BASE_FACTOR_COLUMNS,
        *[
            column
            for column in characteristic_columns
            if column not in BASE_FACTOR_COLUMNS
        ],
    ]
    if len(characteristic_columns) != 132 or len(factor_order) != 133:
        raise ValueError(
            "Broad factor panel must contain market plus 132 JKP returns; "
            f"found {len(factor_order)} total factors"
        )
    formation = pd.to_datetime(source["month"], errors="raise")
    frame = source[["month", *factor_order]].copy()
    frame = frame.rename(columns={"month": "formation_month"})
    frame["formation_month"] = formation.dt.strftime("%Y-%m-%d")
    frame.insert(
        1,
        "realization_month",
        (formation + pd.offsets.MonthEnd(1)).dt.strftime("%Y-%m-%d"),
    )
    frame = frame.sort_values("formation_month", kind="stable")
    if frame["formation_month"].duplicated().any():
        raise ValueError("Broad factor panel has duplicate formation months")
    return frame.reset_index(drop=True), factor_order


def wide_candidate_matrix(
    paths: pd.DataFrame,
    value_column: str,
    candidate_ids: list[str],
) -> pd.DataFrame:
    matrix = paths.pivot(
        index=["formation_month", "realization_month"],
        columns="candidate_id",
        values=value_column,
    ).reindex(columns=candidate_ids)
    if matrix.columns.tolist() != candidate_ids or matrix.isna().all().any():
        raise ValueError(f"Incomplete wide candidate matrix for {value_column}")
    return matrix.reset_index().rename_axis(columns=None)


def normalize_reconstruction_csv(
    source_path: Path,
    candidate_ids: list[str],
) -> pd.DataFrame:
    frame = pd.read_csv(source_path)
    if "month" in frame and "realization_month" not in frame:
        frame = frame.rename(columns={"month": "realization_month"})
    required = {"benchmark_id", "realization_month", *candidate_ids}
    missing = sorted(required - set(frame))
    if missing:
        raise ValueError(f"{source_path.name} is missing columns: {missing}")
    frame = frame[["benchmark_id", "realization_month", *candidate_ids]].copy()
    frame["realization_month"] = pd.to_datetime(
        frame["realization_month"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    if frame.duplicated(["benchmark_id", "realization_month"]).any():
        raise ValueError(f"{source_path.name} has duplicate benchmark-month rows")
    if frame["benchmark_id"].nunique() != 4:
        raise ValueError(f"{source_path.name} does not contain four benchmarks")
    return frame.sort_values(
        ["benchmark_id", "realization_month"], kind="stable"
    ).reset_index(drop=True)


def validate_loadings(
    source_path: Path,
    candidate_ids: list[str],
    factor_order_by_benchmark: dict[str, list[str]],
) -> pd.DataFrame:
    frame = pd.read_parquet(source_path)
    required = {
        "benchmark_id",
        "realization_month",
        "factor_column",
        "candidate_id",
        "loading",
    }
    missing = sorted(required - set(frame))
    if missing:
        raise ValueError(f"Loading matrix is missing columns: {missing}")
    if set(frame["candidate_id"]) != set(candidate_ids):
        raise ValueError("Loading matrix candidate IDs differ from the retained set")
    expected_factors = {
        benchmark: set(factors)
        for benchmark, factors in factor_order_by_benchmark.items()
    }
    for benchmark, group in frame.groupby("benchmark_id"):
        if benchmark not in expected_factors:
            raise ValueError(f"Unexpected loading benchmark: {benchmark}")
        if set(group["factor_column"]) != expected_factors[benchmark]:
            raise ValueError(f"Loading factor order is incomplete for {benchmark}")
    frame["realization_month"] = pd.to_datetime(
        frame["realization_month"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    return frame.sort_values(
        ["benchmark_id", "realization_month", "factor_column", "candidate_id"],
        kind="stable",
    ).reset_index(drop=True)


def file_record(path: Path) -> dict[str, object]:
    if path.suffix == ".csv":
        frame = pd.read_csv(path)
        rows = len(frame)
        columns = frame.columns.tolist()
    elif path.suffix == ".parquet":
        frame = pd.read_parquet(path)
        rows = len(frame)
        columns = frame.columns.tolist()
    else:
        rows = None
        columns = None
    return {
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "rows": rows,
        "columns": columns,
    }


def create_archive(output_dir: Path) -> Path:
    archive_path = output_dir.with_suffix(".tar.gz")
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(output_dir, arcname=output_dir.name, recursive=True)
    return archive_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-monthly", type=Path, required=True)
    parser.add_argument("--primary-factor-monthly", type=Path, required=True)
    parser.add_argument("--broad-factor-panel", type=Path, required=True)
    parser.add_argument("--reconstruction-dir", type=Path, required=True)
    parser.add_argument(
        "--strategy-index",
        type=Path,
        default=Path("paper_runs/handoff/strategy_result_index.csv"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cost-bps", type=float, default=10.0)
    parser.add_argument(
        "--authorized-data-use-acknowledged",
        action="store_true",
        help=(
            "Confirm that the builder and intended recipients are authorized "
            "to use every supplied input under its applicable terms"
        ),
    )
    args = parser.parse_args()

    if not args.authorized_data_use_acknowledged:
        parser.error(
            "Refusing to build without --authorized-data-use-acknowledged"
        )
    if args.cost_bps != 10.0:
        parser.error("This handoff specification requires a 10-bp one-way cost")

    output_dir = args.output_dir.resolve()
    archive_path = output_dir.with_suffix(".tar.gz")
    archive_hash_path = output_dir.with_suffix(".tar.gz.sha256")
    if output_dir.exists() or archive_path.exists() or archive_hash_path.exists():
        parser.error("Output directory or archive already exists; choose a new path")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir()

    strategy_index = pd.read_csv(args.strategy_index)
    candidate_ids = retained_candidate_ids(strategy_index)
    candidate_paths = prepare_candidate_paths(
        pd.read_csv(args.candidate_monthly), candidate_ids, args.cost_bps
    )
    primary_factors = prepare_primary_factors(
        pd.read_csv(args.primary_factor_monthly)
    )
    broad_factors, broad_factor_order = prepare_broad_factors(
        pd.read_csv(args.broad_factor_panel)
    )

    benchmark_manifest_path = args.reconstruction_dir / "run_manifest.json"
    with benchmark_manifest_path.open(encoding="utf-8") as stream:
        benchmark_manifest = json.load(stream)
    factor_order_by_benchmark = {
        benchmark: details["factor_order"]
        for benchmark, details in benchmark_manifest["model_results"].items()
    }
    if factor_order_by_benchmark.get("ff5_mom_jkp132") != broad_factor_order:
        raise ValueError("Broad factor order differs from the reconstruction run")
    if float(benchmark_manifest["cost_bps_one_way"]) != args.cost_bps:
        raise ValueError("Reconstruction cost differs from the requested bundle cost")

    strategy_index.to_csv(output_dir / "strategy_result_index.csv", index=False)
    candidate_paths.to_csv(output_dir / "monthly_candidate_paths.csv", index=False)
    for value_column, filename in (
        ("gross_return", "monthly_candidate_gross_returns.csv"),
        ("traded_notional", "monthly_candidate_traded_notional.csv"),
        ("net_return_10bps", "monthly_candidate_net_returns_10bps.csv"),
        ("analysis_eligible", "monthly_candidate_eligibility.csv"),
        ("path_failure_event", "monthly_candidate_failure_events.csv"),
    ):
        wide_candidate_matrix(
            candidate_paths, value_column, candidate_ids
        ).to_csv(output_dir / filename, index=False)
    primary_factors.to_csv(
        output_dir / "monthly_primary_factor_returns.csv", index=False
    )
    broad_factors.to_csv(
        output_dir / "monthly_broad_jkp_factor_returns.csv", index=False
    )

    for source_name, destination_name in RECONSTRUCTION_FILES.items():
        source_path = args.reconstruction_dir / source_name
        destination_path = output_dir / destination_name
        if source_path.suffix == ".csv":
            normalize_reconstruction_csv(source_path, candidate_ids).to_csv(
                destination_path, index=False
            )
        else:
            validate_loadings(
                source_path, candidate_ids, factor_order_by_benchmark
            ).to_parquet(destination_path, index=False, compression="zstd")
    shutil.copy2(benchmark_manifest_path, output_dir / "benchmark_run_manifest.json")

    readme = """# Authorized collaborator data bundle

This bundle supports inspection and rerunning of the 50 retained U.S. strategy
reconstructions and the matched four-rung benchmark ladder. It contains
aggregate strategy and factor-return paths, not security-level observations.

`formation_month` is the portfolio/factor formation key. `realization_month`
is the month in which the corresponding return is realized. The external
broad factor source keys a next-month return by formation month, so the runner
and this bundle define `realization_month = formation_month + one month-end`.

Net strategy return is `gross_return - 0.001 * traded_notional`, corresponding
to a 10-basis-point one-way cost. Rolling benchmark fits use a 120-month
training window, a final 24-month validation block, and then evaluate the next
month. Fitted values and loadings exclude the training-period intercept by
design; the residual estimand retains persistent out-of-sample abnormal return.

Access to this bundle does not grant any right to redistribute its inputs or
derived matrices. Each recipient must already be authorized under all
applicable JKP, market-data, institutional, and third-party terms. Consult
`MANIFEST.json` for hashes, factor order, dates, windows, versions, and the
full file inventory.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    input_paths = {
        "candidate_monthly": args.candidate_monthly.resolve(),
        "primary_factor_monthly": args.primary_factor_monthly.resolve(),
        "broad_factor_panel": args.broad_factor_panel.resolve(),
        "strategy_index": args.strategy_index.resolve(),
        "benchmark_run_manifest": benchmark_manifest_path.resolve(),
    }
    generated_files = sorted(
        path for path in output_dir.iterdir() if path.name != "MANIFEST.json"
    )
    manifest = {
        "bundle_schema": "alpha-agent-authorized-collaborator-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "authorization_acknowledged": True,
        "licensing_terms": {
            "scope": (
                "aggregate strategy and factor-return paths; no security-level "
                "observations"
            ),
            "recipient_requirement": (
                "each recipient must be independently authorized for every input"
            ),
            "redistribution": (
                "not granted by this repository; underlying third-party terms apply"
            ),
            "code_license": "Apache-2.0; see repository LICENSES/CODE_LICENSE.txt",
            "documentation_license": (
                "CC-BY-4.0; see repository LICENSES/DOCUMENTATION_LICENSE.txt"
            ),
        },
        "strategy_count": 50,
        "candidate_ids": candidate_ids,
        "cost_bps_one_way": args.cost_bps,
        "return_formula": "gross_return - 0.001 * traded_notional",
        "date_labels": {
            "formation_month": "information/portfolio formation month-end",
            "realization_month": "month-end of the realized next-month return",
            "broad_panel_shift": "formation_month + one month-end",
        },
        "sample_dates": {
            "candidate_formation_start": candidate_paths["formation_month"].min(),
            "candidate_formation_end": candidate_paths["formation_month"].max(),
            "candidate_realization_start": candidate_paths[
                "realization_month"
            ].min(),
            "candidate_realization_end": candidate_paths[
                "realization_month"
            ].max(),
            "primary_factor_realization_start": primary_factors[
                "realization_month"
            ].min(),
            "primary_factor_realization_end": primary_factors[
                "realization_month"
            ].max(),
            "broad_factor_formation_start": broad_factors["formation_month"].min(),
            "broad_factor_formation_end": broad_factors["formation_month"].max(),
            "benchmark_evaluation_start": benchmark_manifest[
                "evaluation_start"
            ],
            "benchmark_evaluation_end": benchmark_manifest["evaluation_end"],
        },
        "training_and_validation": {
            "training_months": benchmark_manifest["train_months"],
            "validation_months": benchmark_manifest["validation_months"],
            "evaluation_months": benchmark_manifest["evaluation_months"],
            "ridge_lambdas_by_benchmark": {
                benchmark: details["ridge_lambdas"]
                for benchmark, details in benchmark_manifest[
                    "model_results"
                ].items()
            },
        },
        "factor_order": {
            "same_universe_primary_six": PRIMARY_FACTOR_COLUMNS,
            "broad_market_plus_jkp132": broad_factor_order,
            "by_benchmark": factor_order_by_benchmark,
        },
        "software_versions": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "pyarrow": package_version("pyarrow"),
        },
        "source_inputs": {
            label: {
                "path": str(path),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for label, path in input_paths.items()
        },
        "files": {
            path.name: file_record(path)
            for path in generated_files
        },
    }
    manifest_path = output_dir / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    archive_path = create_archive(output_dir)
    archive_digest = sha256(archive_path)
    archive_hash_path.write_text(
        f"{archive_digest}  {archive_path.name}\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "archive": str(archive_path),
                "archive_sha256": archive_digest,
                "strategy_count": len(candidate_ids),
                "candidate_rows": len(candidate_paths),
                "broad_factor_count": len(broad_factor_order),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
