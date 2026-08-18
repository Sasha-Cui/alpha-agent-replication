#!/usr/bin/env python3
"""Recompute and rerun the complete released QuantaAlpha/GPT factor pool.

The public factor JSON contains 150 custom expressions.  Two expressions call
``TS_SUM(MEAN(...))`` and fail in the released operator library because ``MEAN``
collapses the security index.  Their prose and formulas require a per-date
cross-sectional mean broadcast to each security before the rolling time-series
sum.  This driver applies only that documented compatibility interpretation,
leaves the pinned author checkout untouched, and then runs the released Qlib
training and TopkDropout backtest with all 150 custom factors plus Alpha158(20).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


TARGET_FACTORS = {
    "ResidualMom_AbsorpGate_20D",
    "ResidualMom_VolumeConfirm_20D",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package(name: str) -> None:
    module = types.ModuleType(name)
    module.__path__ = []
    sys.modules[name] = module


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def broadcast_cross_sectional_mean(value: pd.Series | pd.DataFrame):
    """Broadcast each date's cross-sectional mean to the original row index."""
    if "datetime" not in value.index.names:
        raise ValueError("QuantaAlpha MEAN compatibility requires a datetime index level")
    return value.groupby(level="datetime").transform("mean")


def install_author_factor_modules(source_root: Path) -> tuple[Any, Any]:
    """Load only the author's parser/operator modules without importing its agent stack."""
    source_root = source_root.resolve()
    sys.path.insert(0, str(source_root))
    for name in (
        "alphaagent",
        "alphaagent.components",
        "alphaagent.components.coder",
        "alphaagent.components.coder.factor_coder",
    ):
        _package(name)
    factor_code = source_root / "alphaagent/components/coder/factor_coder"
    function_lib = _load(
        "alphaagent.components.coder.factor_coder.function_lib",
        factor_code / "function_lib.py",
    )
    _load(
        "alphaagent.components.coder.factor_coder.expr_parser",
        factor_code / "expr_parser.py",
    )
    calculator = _load(
        "quantaalpha_audit_custom_factor_calculator",
        source_root / "backtest_v2/custom_factor_calculator.py",
    )
    function_lib.MEAN = broadcast_cross_sectional_mean
    return function_lib, calculator


def load_all_public_factors(_loader: Any, file_path: Path, quality_filter: str | None = None):
    """Load public expressions even though their author-local cache paths are unavailable."""
    payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
    rows = []
    for factor_id, item in payload.get("factors", {}).items():
        if quality_filter and item.get("quality") != quality_filter:
            continue
        expression = item.get("factor_expression", "")
        if expression:
            rows.append(
                {
                    "factor_id": factor_id,
                    "factor_name": item.get("factor_name", factor_id),
                    "factor_expression": expression,
                    "factor_description": item.get("factor_description", ""),
                }
            )
    if len(rows) != 150:
        raise RuntimeError(f"expected 150 public custom factors, found {len(rows)}")
    print(f"AUDIT_RECOVERY loaded {len(rows)} public expressions without author-local caches")
    return rows


def seed_cache(base_cache: Path | None, complete_cache: Path) -> int:
    """Hard-link reusable expression caches, with a copy fallback across filesystems."""
    complete_cache.mkdir(parents=True, exist_ok=True)
    if base_cache is None:
        return 0
    copied = 0
    for source in sorted(base_cache.glob("*.pkl")):
        target = complete_cache / source.name
        if target.exists():
            continue
        try:
            os.link(source, target)
        except OSError:
            shutil.copy2(source, target)
        copied += 1
    return copied


def recover_target_factors(
    source_root: Path,
    provider_root: Path,
    factor_json: Path,
    config_path: Path,
    complete_cache: Path,
    calculator_module: Any,
) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["data"]["provider_uri"] = str(provider_root)
    data = calculator_module.get_qlib_stock_data(config)
    payload = json.loads(factor_json.read_text(encoding="utf-8"))
    factors = [
        item for item in payload["factors"].values() if item.get("factor_name") in TARGET_FACTORS
    ]
    if {item["factor_name"] for item in factors} != TARGET_FACTORS:
        raise RuntimeError("the two compatibility-target factor identities drifted")
    calculator = calculator_module.CustomFactorCalculator(
        data, cache_dir=complete_cache, auto_extract_cache=False
    )
    rows = []
    for item in factors:
        name, expression, result, source = calculator._process_single_factor(item, use_cache=False)
        if source != "computed" or result is None or result.isna().all():
            raise RuntimeError(f"failed to recompute {name}: {source}")
        calculator._save_to_cache(expression, result)
        cache_path = complete_cache / f"{hashlib.md5(expression.encode()).hexdigest()}.pkl"
        rows.append(
            {
                "factor_name": name,
                "expression_sha256": hashlib.sha256(expression.encode()).hexdigest(),
                "cache_sha256": sha256(cache_path),
                "rows": int(result.shape[0]),
                "finite_rows": int(result.notna().sum()),
                "mean": float(result.mean()),
                "std": float(result.std()),
                "minimum": float(result.min()),
                "maximum": float(result.max()),
            }
        )
    commit = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return {
        "author_source_commit": commit,
        "author_source_modified": bool(
            subprocess.run(
                ["git", "-C", str(source_root), "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        ),
        "compatibility_change": (
            "MEAN uses groupby(level='datetime').transform('mean') to preserve the "
            "security index required by TS_SUM"
        ),
        "data_rows": int(data.shape[0]),
        "factor_json_sha256": sha256(factor_json),
        "factors": sorted(rows, key=lambda row: row["factor_name"]),
    }


def run_complete_pool(
    source_root: Path,
    provider_root: Path,
    factor_json: Path,
    config_path: Path,
    complete_cache: Path,
    output_dir: Path,
) -> dict[str, Any]:
    from backtest_v2.backtest_runner import BacktestRunner
    from backtest_v2.factor_loader import FactorLoader

    FactorLoader._parse_all_factors_from_json = load_all_public_factors
    output_dir.mkdir(parents=True, exist_ok=True)
    runner = BacktestRunner(str(config_path))
    runner.config["data"]["provider_uri"] = str(provider_root)
    runner.config["llm"]["cache_dir"] = str(complete_cache)
    runner.config["llm"]["auto_extract_cache"] = False
    # Single-process calculation preserves the documented in-memory operator repair
    # if a non-target cache is absent. Existing caches are simply loaded.
    runner.config.setdefault("factor_calculation", {})["n_jobs"] = 1
    runner.config["experiment"]["output_dir"] = str(output_dir)
    return runner.run(
        factor_source="combined",
        factor_json=[str(factor_json)],
        experiment_name="quantaalpha_recovered_qa_gpt_complete_170_full",
        output_name="qa_gpt_complete_170_recovered_full",
        test_period="default",
        ic_only=False,
    )


def parse_args() -> argparse.Namespace:
    root = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_recovery")
    source = root / "source_8a0343"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=source)
    parser.add_argument("--provider-root", type=Path, default=root / "provider/cn_data")
    parser.add_argument(
        "--factor-json",
        type=Path,
        default=source / "factor_library/RANKIC_desc_150_QA_round11_best_gpt_123_csi300.json",
    )
    parser.add_argument("--config", type=Path, default=source / "backtest_v2/config.yaml")
    parser.add_argument("--base-cache-dir", type=Path, default=root / "factor_cache_gpt")
    parser.add_argument("--complete-cache-dir", type=Path, default=root / "factor_cache_gpt_complete")
    parser.add_argument(
        "--output-dir", type=Path, default=root / "reruns/qa_gpt_complete_170_driver_actual"
    )
    parser.add_argument(
        "--evidence-json", type=Path, default=root / "complete_pool_factor_recovery.json"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in (args.source_root, args.provider_root, args.factor_json, args.config):
        if not path.exists():
            raise FileNotFoundError(path)
    seeded = seed_cache(args.base_cache_dir, args.complete_cache_dir)
    _function_lib, calculator = install_author_factor_modules(args.source_root)
    evidence = recover_target_factors(
        args.source_root,
        args.provider_root,
        args.factor_json,
        args.config,
        args.complete_cache_dir,
        calculator,
    )
    evidence["base_cache_files_seeded"] = seeded
    metrics = run_complete_pool(
        args.source_root,
        args.provider_root,
        args.factor_json,
        args.config,
        args.complete_cache_dir,
        args.output_dir,
    )
    evidence["complete_pool_factor_count"] = 170
    evidence["complete_pool_metrics"] = {key: float(value) for key, value in metrics.items()}
    evidence["llm_or_market_api_called"] = False
    args.evidence_json.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_json.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(args.evidence_json)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
