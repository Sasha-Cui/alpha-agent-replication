#!/usr/bin/env python3
"""Execute baselines from a prepared, pinned FINSABER source snapshot.

Run this from the external FINSABER checkout after placing the hash-pinned price
CSV at its repository path and applying the import-only audit adapter.
"""

from __future__ import annotations

import argparse
import inspect
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(Path.cwd()))

from backtest.finsaber_bt import FINSABERBt
from backtest.strategy.timing import (
    ARIMAPredictorStrategy,
    ATRBandStrategy,
    BollingerBandsStrategy,
    BuyAndHoldStrategy,
    SMACrossStrategy,
    TurnOfTheMonthStrategy,
    WMAStrategy,
    XGBoostPredictorStrategy,
)


STRATEGIES = {
    cls.__name__: cls
    for cls in (
        BuyAndHoldStrategy,
        SMACrossStrategy,
        WMAStrategy,
        ATRBandStrategy,
        BollingerBandsStrategy,
        TurnOfTheMonthStrategy,
        ARIMAPredictorStrategy,
        XGBoostPredictorStrategy,
    )
}
DETERMINISTIC_STRATEGIES = {
    "BuyAndHoldStrategy",
    "SMACrossStrategy",
    "WMAStrategy",
    "ATRBandStrategy",
    "BollingerBandsStrategy",
    "TurnOfTheMonthStrategy",
}
PREPARED_RUNNER_SHA256 = "c26cc01268fcc88d69fde8f6f69fc22ad0982d0db378e6e4fe5fce1a99b29777"
XGBOOST_AVAILABLE_HISTORY_RUNNER_SHA256 = (
    "138044d73ca97e5dc42aefa037bf61cd07fa476b854c2c5493447d3f095050fd"
)
METRIC_KEYS = (
    "total_return",
    "annual_return",
    "annual_volatility",
    "sharpe_ratio",
    "sortino_ratio",
    "max_drawdown",
    "total_commission",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", action="append", required=True,
                        choices=sorted(STRATEGIES))
    parser.add_argument("--training-years", type=int, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--bypass-unused-prior-guard",
        action="store_true",
    )
    parser.add_argument(
        "--allow-incomplete-model-history-adapter",
        action="store_true",
    )
    args = parser.parse_args()
    if args.training_years is not None and args.training_years <= 0:
        parser.error("--training-years must be positive")

    runner_path = Path("backtest/finsaber_bt.py")
    runner_sha256_before = sha256(runner_path)
    if args.bypass_unused_prior_guard and args.allow_incomplete_model_history_adapter:
        parser.error("guard adapters are mutually exclusive")
    if args.allow_incomplete_model_history_adapter:
        if args.strategy != ["XGBoostPredictorStrategy"]:
            parser.error(
                "--allow-incomplete-model-history-adapter requires exactly "
                "XGBoostPredictorStrategy"
            )
        if args.training_years != 2:
            parser.error("--allow-incomplete-model-history-adapter requires --training-years 2")
        if runner_sha256_before != XGBOOST_AVAILABLE_HISTORY_RUNNER_SHA256:
            raise RuntimeError("XGBoost available-history runner patch drifted")
    elif runner_sha256_before != PREPARED_RUNNER_SHA256:
        raise RuntimeError("prepared FINSABER runner snapshot drifted")
    if args.bypass_unused_prior_guard:
        requested = set(args.strategy)
        unsupported = requested - DETERMINISTIC_STRATEGIES
        if unsupported:
            parser.error(
                "--bypass-unused-prior-guard is restricted to deterministic "
                f"strategies; unsupported: {sorted(unsupported)}"
            )
        for name in sorted(requested):
            strategy = STRATEGIES[name]
            if "prior_period" not in vars(strategy.params):
                raise RuntimeError(f"{name} prior-period boundary drifted")
            source = inspect.getsource(strategy)
            if source.count("prior_period") != 1:
                raise RuntimeError(f"{name} consumes prior_period outside its declaration")
            delattr(strategy.params, "prior_period")

    price_path = Path("data/price/all_sp500_prices_2000_2024_delisted_include.csv")
    config = {
        "tickers": ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"],
        "date_from": "2022-10-06",
        "date_to": "2023-04-10",
        "silence": True,
        "setup_name": "cherry_pick_both_finmem",
        "save_results": False,
        "training_years": args.training_years,
    }
    report = {
        "adapter": {
            "unused_prior_period_guard_bypassed": args.bypass_unused_prior_guard,
            "incomplete_model_history_guard_bypassed": (
                args.allow_incomplete_model_history_adapter
            ),
            "scope": (
                "xgboost_available_pretest_history_only"
                if args.allow_incomplete_model_history_adapter
                else "deterministic_strategies_only"
                if args.bypass_unused_prior_guard
                else "none"
            ),
            "strategy_formula_changed": False,
            "prepared_runner_sha256": runner_sha256_before,
            "prepared_source_snapshot_modified_during_run": False,
        },
        "execution": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {
                name: package_version(name)
                for name in (
                    "backtrader", "matplotlib", "numpy", "pandas",
                    "python-dotenv", "statsmodels", "xgboost",
                )
            },
        },
        "inputs": {
            "price_csv_bytes": price_path.stat().st_size,
            "price_csv_sha256": sha256(price_path),
            "config": config,
        },
        "results": {},
    }

    for name in args.strategy:
        operator = FINSABERBt(dict(config))
        raw = operator.run_iterative_tickers(STRATEGIES[name])
        report["results"][name] = {
            ticker: {
                key: float(metrics[key])
                for key in METRIC_KEYS
                if key in metrics
            }
            for ticker, metrics in raw.items()
        }

    if sha256(runner_path) != runner_sha256_before:
        report["adapter"]["prepared_source_snapshot_modified_during_run"] = True
        raise RuntimeError("prepared FINSABER source changed during execution")
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
