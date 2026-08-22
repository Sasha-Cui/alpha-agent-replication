#!/usr/bin/env python3
"""Execute baselines from a prepared, pinned FINSABER source snapshot.

Run this from the external FINSABER checkout after placing the hash-pinned price
CSV at its repository path and applying the import-only audit adapter.
"""

from __future__ import annotations

import argparse
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
    args = parser.parse_args()
    if args.training_years is not None and args.training_years <= 0:
        parser.error("--training-years must be positive")

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

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
