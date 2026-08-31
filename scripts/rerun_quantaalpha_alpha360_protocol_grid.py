#!/usr/bin/env python3
"""Run a bounded QuantaAlpha Alpha360 source-protocol grid.

The paper names Alpha360 as a classical Qlib baseline but does not disclose
whether it used the recovered QuantaAlpha backtest profile or Qlib's official
0.9.7 Alpha360/LightGBM workflow. This driver evaluates both coherent primary-
source profiles and two model/preprocessing hybrids. Hybrids are diagnostics
only and can never receive paper-result credit.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


AUTHOR_SOURCE_COMMIT = "8a034319ff925d9dc621077ebf97d48e1890dad2"
QLIB_SOURCE_COMMIT = "da920b7f954f48ab1bb64117c976710de198373e"
DATA_FINGERPRINT = "5b50aa45aaaf925efc9bfdc2dedb6e4211e3ee6297abaeccf3b356ee90609c4e"
QLIB_FILE_SHA256 = {
    "examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha360.yaml": (
        "84cf98f54703ae9bc5257e2a0c07ff6307712ec40266c83ee45cbc28149b6a08"
    ),
    "qlib/contrib/data/handler.py": (
        "b621481c6009c39066c67c71390fd2bea635f56daf9f2c4e38817eff268e3232"
    ),
    "qlib/contrib/data/loader.py": (
        "814b7f7ab3d418ae3c87ce352220080b239eba2670eac9e38376b794be4075cb"
    ),
}
PAPER_VALUES = {
    "IC": "0.0105",
    "ICIR": "0.0636",
    "Rank_IC": "0.0306",
    "Rank_ICIR": "0.1889",
    "IR": "0.6009",
    "CR": "0.3550",
    "ARR_pct": "4.09",
    "MDD_pct": "11.52",
}
RAW_TO_CANONICAL = {
    "IC": ("IC", 1.0),
    "ICIR": ("ICIR", 1.0),
    "Rank IC": ("Rank_IC", 1.0),
    "Rank ICIR": ("Rank_ICIR", 1.0),
    "information_ratio": ("IR", 1.0),
    "calmar_ratio": ("CR", 1.0),
    "annualized_return": ("ARR_pct", 100.0),
    "max_drawdown": ("MDD_pct", -100.0),
}
PROFILE_SPECS = {
    "qlib_v097": {
        "classification": "coherent_primary_source_candidate",
        "model_profile": "qlib_v0.9.7_official_lightgbm",
        "processor_profile": "qlib_v0.9.7_official_alpha360",
        "deal_price": "close",
        "ic_only": False,
        "runs": 2,
    },
    "official_model_author_processors": {
        "classification": "diagnostic_hybrid_no_result_credit",
        "model_profile": "qlib_v0.9.7_official_lightgbm",
        "processor_profile": "quantaalpha_released",
        "deal_price": "open",
        "ic_only": True,
        "runs": 1,
    },
    "author_model_official_processors": {
        "classification": "diagnostic_hybrid_no_result_credit",
        "model_profile": "quantaalpha_released",
        "processor_profile": "qlib_v0.9.7_official_alpha360",
        "deal_price": "open",
        "ic_only": True,
        "runs": 1,
    },
}
PROFILE_DIRS = {
    "qlib_v097": "official_v097_full",
    "official_model_author_processors": "official_model_author_processors",
    "author_model_official_processors": "author_model_official_processors",
}
OUTPUT_NAMES = {
    ("qlib_v097", 1): "alpha360_official_v097_full",
    ("qlib_v097", 2): "alpha360_official_v097_full_repeat",
    ("official_model_author_processors", 1): "alpha360_official_model_author_processors",
    ("author_model_official_processors", 1): "alpha360_author_model_official_processors",
}
RUNTIME_PACKAGES = {
    "pyqlib": "pyqlib",
    "numpy": "numpy",
    "pandas": "pandas",
    "lightgbm": "lightgbm",
    "mlflow": "mlflow",
    "scikit_learn": "scikit-learn",
}

SINGLE_RUN_DRIVER = r"""
import json
import sys
from pathlib import Path

source_root = Path(sys.argv[1]).resolve()
config_path = Path(sys.argv[2]).resolve()
provider_root = Path(sys.argv[3]).resolve()
output_dir = Path(sys.argv[4]).resolve()
profile = json.loads(sys.argv[5])
output_name = sys.argv[6]
experiment_name = sys.argv[7]

sys.path.insert(0, str(source_root))
from backtest_v2.backtest_runner import BacktestRunner

runner = BacktestRunner(str(config_path))
runner.config["data"]["provider_uri"] = str(provider_root)
runner.config["experiment"]["output_dir"] = str(output_dir)
if profile["processor_profile"] == "qlib_v0.9.7_official_alpha360":
    runner.config["dataset"]["infer_processors"] = []
    runner.config["dataset"]["learn_processors"] = [
        {"class": "DropnaLabel"},
        {"class": "CSRankNorm", "kwargs": {"fields_group": "label"}},
    ]
if profile["model_profile"] == "qlib_v0.9.7_official_lightgbm":
    runner.config["model"]["params"] = {
        "loss": "mse",
        "colsample_bytree": 0.8879,
        "learning_rate": 0.0421,
        "subsample": 0.8789,
        "lambda_l1": 205.6999,
        "lambda_l2": 580.9768,
        "max_depth": 8,
        "num_leaves": 210,
        "num_threads": 20,
    }
runner.config["backtest"]["backtest"]["deal_price"] = profile["deal_price"]
metrics = runner.run(
    factor_source="alpha360",
    experiment_name=experiment_name,
    output_name=output_name,
    test_period="default",
    ic_only=profile["ic_only"],
)
print("AUDIT_RESULT=" + json.dumps(metrics, sort_keys=True))
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def displayed_match(observed: float, paper_value: str) -> bool:
    decimals = len(paper_value.partition(".")[2])
    return f"{observed:.{decimals}f}" == paper_value


def normalize_raw_metrics(raw: dict[str, Any]) -> dict[str, float]:
    return {
        canonical: float(raw[source]) * multiplier
        for source, (canonical, multiplier) in RAW_TO_CANONICAL.items()
        if source in raw
    }


def runtime_versions() -> dict[str, str]:
    versions = {"python": ".".join(map(str, sys.version_info[:3]))}
    for label, package in RUNTIME_PACKAGES.items():
        versions[label] = importlib.metadata.version(package)
    return versions


def verify_inputs(
    author_source: Path,
    qlib_source: Path,
    provider_root: Path,
    author_evidence: Path,
) -> dict[str, Any]:
    if run_git(author_source, "rev-parse", "HEAD") != AUTHOR_SOURCE_COMMIT:
        raise RuntimeError("QuantaAlpha author source commit drifted")
    if run_git(author_source, "status", "--porcelain"):
        raise RuntimeError("QuantaAlpha author source is modified")
    if run_git(qlib_source, "rev-parse", "HEAD") != QLIB_SOURCE_COMMIT:
        raise RuntimeError("Qlib v0.9.7 source commit drifted")
    if run_git(qlib_source, "status", "--porcelain"):
        raise RuntimeError("Qlib v0.9.7 source is modified")
    observed_qlib_hashes = {
        relative: sha256(qlib_source / relative) for relative in QLIB_FILE_SHA256
    }
    if observed_qlib_hashes != QLIB_FILE_SHA256:
        raise RuntimeError("Qlib Alpha360 primary-source files drifted")
    if not provider_root.is_dir():
        raise FileNotFoundError(provider_root)
    author_payload = json.loads(author_evidence.read_text(encoding="utf-8"))
    if author_payload["source_commit"] != AUTHOR_SOURCE_COMMIT:
        raise RuntimeError("committed author-run evidence drifted")
    return {
        "author_source_commit": AUTHOR_SOURCE_COMMIT,
        "author_source_file_sha256": author_payload["source_file_sha256"],
        "qlib_source_tag": "v0.9.7",
        "qlib_source_commit": QLIB_SOURCE_COMMIT,
        "qlib_source_file_sha256": observed_qlib_hashes,
        "provider_cross_artifact_matrix_sha256": DATA_FINGERPRINT,
    }


def run_one(
    author_source: Path,
    provider_root: Path,
    output_root: Path,
    profile_name: str,
    run_index: int,
) -> None:
    profile = PROFILE_SPECS[profile_name]
    output_name = OUTPUT_NAMES[(profile_name, run_index)]
    output_dir = output_root / PROFILE_DIRS[profile_name]
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir = output_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            SINGLE_RUN_DRIVER,
            str(author_source),
            str(author_source / "backtest_v2/config.yaml"),
            str(provider_root),
            str(output_dir),
            json.dumps(profile, sort_keys=True),
            output_name,
            f"quantaalpha_audit_{output_name}",
        ],
        cwd=output_root,
        env={
            **os.environ,
            "MLFLOW_TRACKING_URI": (output_root / "mlruns").resolve().as_uri(),
            "PYTHONPATH": str(author_source),
        },
        check=False,
        capture_output=True,
        text=True,
    )
    (log_dir / f"{output_name}.log").write_text(
        completed.stdout + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode:
        raise RuntimeError(f"{profile_name} run {run_index} failed")
    if "AUDIT_RESULT=" not in completed.stdout:
        raise RuntimeError(f"{profile_name} run {run_index} emitted no result")


def load_profile_runs(
    output_root: Path,
    profile_name: str,
) -> list[dict[str, Any]]:
    runs = []
    for run_index in range(1, int(PROFILE_SPECS[profile_name]["runs"]) + 1):
        output_name = OUTPUT_NAMES[(profile_name, run_index)]
        path = (
            output_root
            / PROFILE_DIRS[profile_name]
            / f"{output_name}_backtest_metrics.json"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["factor_source"] != "alpha360" or payload["num_factors"] != 360:
            raise RuntimeError(f"{profile_name} output identity drifted")
        runs.append(
            {
                "run_index": run_index,
                "native_metrics": normalize_raw_metrics(payload["metrics"]),
            }
        )
    return runs


def profile_evidence(
    name: str,
    classification: str,
    spec: dict[str, Any],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    metrics = tuple(runs[0]["native_metrics"])
    if any(tuple(run["native_metrics"]) != metrics for run in runs):
        raise RuntimeError(f"{name} metric schema differs across runs")
    repeat_max = max(
        (
            abs(runs[0]["native_metrics"][metric] - run["native_metrics"][metric])
            for run in runs[1:]
            for metric in metrics
        ),
        default=0.0,
    )
    matches = [
        metric
        for metric in metrics
        if displayed_match(runs[0]["native_metrics"][metric], PAPER_VALUES[metric])
    ]
    coherent = classification != "diagnostic_hybrid_no_result_credit"
    return {
        "classification": classification,
        "model_profile": spec["model_profile"],
        "processor_profile": spec["processor_profile"],
        "deal_price": spec["deal_price"],
        "metrics_checked": len(metrics),
        "runs": runs,
        "repeat_max_abs_difference": repeat_max,
        "paper_metrics_matching_at_display_precision": matches,
        "paper_metric_cells_matching": len(matches),
        "complete_paper_row_match": coherent and len(matches) == len(PAPER_VALUES),
        "paper_result_credit": coherent and len(matches) == len(PAPER_VALUES),
    }


def collect_evidence(
    author_source: Path,
    qlib_source: Path,
    provider_root: Path,
    output_root: Path,
    author_evidence: Path,
) -> dict[str, Any]:
    pins = verify_inputs(author_source, qlib_source, provider_root, author_evidence)
    author_payload = json.loads(author_evidence.read_text(encoding="utf-8"))
    author_runs = author_payload["baselines"]["alpha360"]["runs"]
    profiles = {
        "quantaalpha_release": profile_evidence(
            "quantaalpha_release",
            "coherent_primary_source_candidate",
            {
                "model_profile": "quantaalpha_released",
                "processor_profile": "quantaalpha_released",
                "deal_price": "open",
            },
            author_runs,
        )
    }
    for profile_name, spec in PROFILE_SPECS.items():
        profiles[profile_name] = profile_evidence(
            profile_name,
            str(spec["classification"]),
            spec,
            load_profile_runs(output_root, profile_name),
        )
    coherent = [
        profile
        for profile in profiles.values()
        if profile["classification"] == "coherent_primary_source_candidate"
    ]
    diagnostics = [
        profile
        for profile in profiles.values()
        if profile["classification"] == "diagnostic_hybrid_no_result_credit"
    ]
    summary = {
        "coherent_profiles_checked": len(coherent),
        "coherent_metric_cells_checked": sum(
            int(profile["metrics_checked"]) for profile in coherent
        ),
        "coherent_metric_cells_matching": sum(
            int(profile["paper_metric_cells_matching"]) for profile in coherent
        ),
        "coherent_complete_rows_matching": sum(
            bool(profile["complete_paper_row_match"]) for profile in coherent
        ),
        "diagnostic_hybrid_profiles_checked": len(diagnostics),
        "diagnostic_predictive_cells_checked": sum(
            int(profile["metrics_checked"]) for profile in diagnostics
        ),
        "diagnostic_predictive_cells_matching": sum(
            int(profile["paper_metric_cells_matching"]) for profile in diagnostics
        ),
        "paper_result_cells_added": 0,
    }
    expected = {
        "coherent_profiles_checked": 2,
        "coherent_metric_cells_checked": 16,
        "coherent_metric_cells_matching": 0,
        "coherent_complete_rows_matching": 0,
        "diagnostic_hybrid_profiles_checked": 2,
        "diagnostic_predictive_cells_checked": 8,
        "diagnostic_predictive_cells_matching": 0,
        "paper_result_cells_added": 0,
    }
    if summary != expected:
        raise RuntimeError(f"Alpha360 protocol-grid boundary changed: {summary}")
    return {
        "audit": "QuantaAlpha Alpha360 primary-source protocol grid",
        "source_pins": pins,
        "runtime": runtime_versions(),
        "paper_values": PAPER_VALUES,
        "protocol": {
            "factor_source": "alpha360",
            "factor_count": 360,
            "train": ["2016-01-01", "2020-12-31"],
            "valid": ["2021-01-01", "2021-12-31"],
            "test": ["2022-01-01", "2025-12-26"],
            "market": "csi300",
            "benchmark": "SH000300",
            "portfolio": "TopkDropout top50/drop5",
            "open_cost": 0.0005,
            "close_cost": 0.0015,
            "llm_or_market_api_called": False,
        },
        "profiles": profiles,
        "summary": summary,
        "interpretation": (
            "Neither coherent primary-source profile reproduces any Alpha360 paper "
            "cell. The two hybrids isolate model-versus-preprocessing sensitivity but "
            "are diagnostic only and also reproduce no predictive cell."
        ),
    }


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    recovery_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_recovery")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--author-source",
        type=Path,
        default=recovery_root / "source_8a0343",
    )
    parser.add_argument(
        "--qlib-source",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/qlib_v097"),
    )
    parser.add_argument(
        "--provider-root",
        type=Path,
        default=recovery_root / "provider/cn_data",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=recovery_root / "reruns/alpha360_protocol_grid",
    )
    parser.add_argument(
        "--author-evidence",
        type=Path,
        default=(
            project_root
            / "paper_runs/paper_replication_audits/quantaalpha/"
            "deterministic_baseline_native_evidence.json"
        ),
    )
    parser.add_argument(
        "--evidence-json",
        type=Path,
        default=(
            project_root
            / "paper_runs/paper_replication_audits/quantaalpha/"
            "alpha360_protocol_grid_evidence.json"
        ),
    )
    parser.add_argument("--collect-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    if not args.collect_only:
        for profile_name, spec in PROFILE_SPECS.items():
            for run_index in range(1, int(spec["runs"]) + 1):
                run_one(
                    args.author_source,
                    args.provider_root,
                    args.output_root,
                    profile_name,
                    run_index,
                )
    evidence = collect_evidence(
        args.author_source,
        args.qlib_source,
        args.provider_root,
        args.output_root,
        args.author_evidence,
    )
    args.evidence_json.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_json.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.evidence_json)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
