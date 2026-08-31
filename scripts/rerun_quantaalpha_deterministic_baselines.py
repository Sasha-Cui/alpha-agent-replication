#!/usr/bin/env python3
"""Rerun QuantaAlpha's released deterministic Alpha158/Alpha360 baselines.

The recovered author config hard-codes a private Qlib provider path.  This
driver changes only the provider and output locations in memory, runs each
released baseline twice in fresh Python processes, and emits a normalized
evidence record without machine-specific paths or elapsed-time noise.
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


SOURCE_COMMIT = "8a034319ff925d9dc621077ebf97d48e1890dad2"
DATA_FINGERPRINT = "5b50aa45aaaf925efc9bfdc2dedb6e4211e3ee6297abaeccf3b356ee90609c4e"
AUTHOR_PROVIDER_URI = "/home/tjxy/.qlib/qlib_data/cn_data"
FACTOR_COUNTS = {"alpha158": 158, "alpha360": 360}
PAPER_VALUES = {
    "alpha158": {
        "IC": "0.0131",
        "ICIR": "0.0817",
        "Rank_IC": "0.0334",
        "Rank_ICIR": "0.2119",
        "IR": "0.4099",
        "CR": "0.2620",
        "ARR_pct": "2.66",
        "MDD_pct": "10.15",
    },
    "alpha360": {
        "IC": "0.0105",
        "ICIR": "0.0636",
        "Rank_IC": "0.0306",
        "Rank_ICIR": "0.1889",
        "IR": "0.6009",
        "CR": "0.3550",
        "ARR_pct": "4.09",
        "MDD_pct": "11.52",
    },
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
RUNTIME_PACKAGES = {
    "pyqlib": "pyqlib",
    "numpy": "numpy",
    "pandas": "pandas",
    "joblib": "joblib",
    "lightgbm": "lightgbm",
    "mlflow": "mlflow",
    "scipy": "scipy",
    "scikit_learn": "scikit-learn",
    "tables": "tables",
    "numexpr": "numexpr",
}

SINGLE_RUN_DRIVER = r"""
import json
import os
import sys
from pathlib import Path

source_root = Path(sys.argv[1]).resolve()
config_path = Path(sys.argv[2]).resolve()
provider_root = Path(sys.argv[3]).resolve()
output_dir = Path(sys.argv[4]).resolve()
factor_source = sys.argv[5]
output_name = sys.argv[6]
experiment_name = sys.argv[7]

sys.path.insert(0, str(source_root))
os.chdir(output_dir.parent)
from backtest_v2.backtest_runner import BacktestRunner

runner = BacktestRunner(str(config_path))
runner.config["data"]["provider_uri"] = str(provider_root)
runner.config["experiment"]["output_dir"] = str(output_dir)
metrics = runner.run(
    factor_source=factor_source,
    experiment_name=experiment_name,
    output_name=output_name,
    test_period="default",
    ic_only=False,
)
print("AUDIT_RESULT=" + json.dumps(metrics, sort_keys=True))
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(source_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def normalize_metrics(raw: dict[str, Any]) -> dict[str, float]:
    normalized = {
        canonical: float(raw[source]) * multiplier
        for source, (canonical, multiplier) in RAW_TO_CANONICAL.items()
    }
    if set(normalized) != set(next(iter(PAPER_VALUES.values()))):
        raise RuntimeError("QuantaAlpha deterministic baseline metric schema drifted")
    return normalized


def displayed_match(observed: float, paper_value: str) -> bool:
    decimals = len(paper_value.partition(".")[2])
    return f"{observed:.{decimals}f}" == paper_value


def output_name(factor_source: str, run_index: int) -> str:
    suffix = "" if run_index == 1 else "_repeat"
    return f"{factor_source}_full{suffix}"


def run_one(
    source_root: Path,
    config_path: Path,
    provider_root: Path,
    output_dir: Path,
    factor_source: str,
    run_index: int,
) -> None:
    name = output_name(factor_source, run_index)
    experiment = f"quantaalpha_audit_{name}"
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            SINGLE_RUN_DRIVER,
            str(source_root),
            str(config_path),
            str(provider_root),
            str(output_dir),
            factor_source,
            name,
            experiment,
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=output_dir.parent,
        env={**os.environ, "PYTHONPATH": str(source_root)},
    )
    log_path = output_dir / f"{name}.log"
    log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"{factor_source} run {run_index} failed; see {log_path}")
    if "AUDIT_RESULT=" not in completed.stdout:
        raise RuntimeError(f"{factor_source} run {run_index} emitted no audit result")


def load_run(output_dir: Path, factor_source: str, run_index: int) -> dict[str, Any]:
    name = output_name(factor_source, run_index)
    path = output_dir / f"{name}_backtest_metrics.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("factor_source") != factor_source:
        raise RuntimeError(f"{factor_source} result identity drifted")
    if payload.get("num_factors") != FACTOR_COUNTS[factor_source]:
        raise RuntimeError(f"{factor_source} factor count drifted")
    config = payload.get("config", {})
    expected_config = {
        "data_range": "2016-01-01 ~ 2025-12-26",
        "test_range": "2022-01-01 ~ 2025-12-26",
        "backtest_range": "2022-01-01 ~ 2025-12-26",
        "market": "csi300",
        "benchmark": "SH000300",
    }
    if config != expected_config or payload.get("test_period") != "default":
        raise RuntimeError(f"{factor_source} protocol drifted")
    return {
        "run_index": run_index,
        "native_metrics": normalize_metrics(payload["metrics"]),
    }


def runtime_versions() -> dict[str, str]:
    versions = {"python": ".".join(map(str, sys.version_info[:3]))}
    for label, package in RUNTIME_PACKAGES.items():
        versions[label] = importlib.metadata.version(package)
    return versions


def collect_evidence(
    source_root: Path,
    provider_root: Path,
    config_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    source_commit = run_git(source_root, "rev-parse", "HEAD")
    source_modified = bool(run_git(source_root, "status", "--porcelain"))
    if source_commit != SOURCE_COMMIT:
        raise RuntimeError("QuantaAlpha source commit drifted")
    if source_modified:
        raise RuntimeError("QuantaAlpha author checkout is modified")
    if not provider_root.is_dir():
        raise FileNotFoundError(provider_root)
    source_files = {
        "config.yaml": config_path,
        "backtest_runner.py": source_root / "backtest_v2/backtest_runner.py",
        "factor_loader.py": source_root / "backtest_v2/factor_loader.py",
    }
    evidence: dict[str, Any] = {
        "source_commit": source_commit,
        "author_source_modified": source_modified,
        "source_file_sha256": {name: sha256(path) for name, path in source_files.items()},
        "runtime": runtime_versions(),
        "protocol": {
            "author_config_provider_uri": AUTHOR_PROVIDER_URI,
            "audit_provider_substitution": "local recovered provider identified by data_fingerprint_sha256",
            "data_fingerprint_sha256": DATA_FINGERPRINT,
            "test_range": ["2022-01-01", "2025-12-26"],
            "market": "csi300",
            "benchmark": "SH000300",
            "model": "released LightGBM configuration",
            "portfolio": "TopkDropout top50/drop5",
            "deal_price": "open",
            "open_cost": 0.0005,
            "close_cost": 0.0015,
            "llm_or_market_api_called": False,
        },
        "baselines": {},
    }
    for factor_source in FACTOR_COUNTS:
        runs = [load_run(output_dir, factor_source, index) for index in (1, 2)]
        metrics = tuple(PAPER_VALUES[factor_source])
        repeat_max = max(
            abs(runs[0]["native_metrics"][metric] - runs[1]["native_metrics"][metric])
            for metric in metrics
        )
        first = runs[0]["native_metrics"]
        matches = [
            metric
            for metric, paper_value in PAPER_VALUES[factor_source].items()
            if displayed_match(first[metric], paper_value)
        ]
        evidence["baselines"][factor_source] = {
            "factor_count": FACTOR_COUNTS[factor_source],
            "paper_values": PAPER_VALUES[factor_source],
            "runs": runs,
            "repeat_max_abs_difference": repeat_max,
            "paper_metrics_matching_at_display_precision": matches,
            "paper_metric_cells_matching": len(matches),
            "complete_paper_row_match": len(matches) == len(metrics),
        }
    return evidence


def parse_args() -> argparse.Namespace:
    recovery_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_recovery")
    source_root = recovery_root / "source_8a0343"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=source_root)
    parser.add_argument("--provider-root", type=Path, default=recovery_root / "provider/cn_data")
    parser.add_argument("--config", type=Path, default=source_root / "backtest_v2/config.yaml")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=recovery_root / "reruns/deterministic_baselines",
    )
    parser.add_argument("--evidence-json", type=Path)
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Normalize two existing runs per baseline without rerunning Qlib",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not args.collect_only:
        for factor_source in FACTOR_COUNTS:
            for run_index in (1, 2):
                run_one(
                    args.source_root,
                    args.config,
                    args.provider_root,
                    args.output_dir,
                    factor_source,
                    run_index,
                )
    evidence = collect_evidence(
        args.source_root,
        args.provider_root,
        args.config,
        args.output_dir,
    )
    evidence_path = args.evidence_json or (
        args.output_dir / "quantaalpha_deterministic_baseline_evidence.json"
    )
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(evidence_path)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
