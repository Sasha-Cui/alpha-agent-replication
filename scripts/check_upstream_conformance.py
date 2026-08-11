#!/usr/bin/env python3
"""Outcome-blind conformance check against the pinned QuantEvolver source.

The checked-in files under tests/upstream_snapshots/quantevolver are exact,
hash-verified copies of the two upstream implementation files used by the
primary component study. This script executes those files on a deterministic
synthetic OHLCV panel and compares their scores and long-short paths with the
study's independently vectorized monthly implementation. No empirical return
outcome is read by this check.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import types
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_faithful_component_replications import (  # noqa: E402
    PRIMARY_COMPONENTS,
    SOURCE_COMMIT,
    evaluate_released_seeds,
    released_cross_sectional_path,
)


SNAPSHOT_ROOT = ROOT / "tests/upstream_snapshots/quantevolver"
SNAPSHOT_HASHES = {
    "LICENSE": "f8e25686c7e519aa7edac74d4f826d0f52ea711c0a8a3aafd0773b81ff7e6561",
    "examples/seed_candidates.yaml": (
        "c8a20de0850156b8c831547a58239bb88b5d6486da50d6f9ecbaa2df0d13d718"
    ),
    "quant_evolver/dsl/evaluator.py": (
        "8c6e8201b8794bb2166a118cb753231bca1379c8aff115c6d29799ce8400516c"
    ),
    "quant_evolver/evaluation/cross_sectional_rankic.py": (
        "b38066082453d58295e45467fad662b33c1a1ef97232d3575348e2cfade56295"
    ),
}
FIXTURE_ID = "deterministic_12_symbol_275_bar_ohlcv_v1"
SCORE_ATOL = 5e-12
PATH_ATOL = 5e-13


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load reference module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _StubDataConfig:
    @classmethod
    def from_dict(cls, _value: object) -> "_StubDataConfig":
        return cls()


class _StubDataStore:
    def __init__(self, _config: object = None) -> None:
        pass

    def available_symbols(self) -> list[str]:
        return []


def load_pinned_modules() -> tuple[types.ModuleType, types.ModuleType]:
    """Load exact source snapshots while stubbing only unused data/compiler I/O."""
    evaluator = _load_module(
        "_pinned_quantevolver_evaluator",
        SNAPSHOT_ROOT / "quant_evolver/dsl/evaluator.py",
    )

    package_names = (
        "quant_evolver",
        "quant_evolver.dsl",
        "quant_evolver.dsl.compiler",
        "quant_evolver.dsl.evaluator",
        "quant_evolver.evaluation",
        "quant_evolver.evaluation.data",
    )
    saved = {name: sys.modules.get(name) for name in package_names}
    try:
        quant_evolver = types.ModuleType("quant_evolver")
        dsl = types.ModuleType("quant_evolver.dsl")
        compiler = types.ModuleType("quant_evolver.dsl.compiler")
        evaluator_bridge = types.ModuleType("quant_evolver.dsl.evaluator")
        evaluation = types.ModuleType("quant_evolver.evaluation")
        data = types.ModuleType("quant_evolver.evaluation.data")
        compiler.compile_expr = lambda expr, warmup_param: expr  # type: ignore[attr-defined]
        evaluator_bridge.evaluate_expr_series = evaluator.evaluate_expr_series  # type: ignore[attr-defined]
        data.LocalDataConfig = _StubDataConfig  # type: ignore[attr-defined]
        data.LocalDataStore = _StubDataStore  # type: ignore[attr-defined]
        replacements = {
            "quant_evolver": quant_evolver,
            "quant_evolver.dsl": dsl,
            "quant_evolver.dsl.compiler": compiler,
            "quant_evolver.dsl.evaluator": evaluator_bridge,
            "quant_evolver.evaluation": evaluation,
            "quant_evolver.evaluation.data": data,
        }
        sys.modules.update(replacements)
        cross_sectional = _load_module(
            "_pinned_quantevolver_cross_sectional",
            SNAPSHOT_ROOT / "quant_evolver/evaluation/cross_sectional_rankic.py",
        )
    finally:
        for name, prior in saved.items():
            if prior is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = prior
    return evaluator, cross_sectional


def deterministic_fixture() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    months = pd.date_range("2000-01-31", periods=275, freq="ME")
    step = np.arange(len(months), dtype=float)
    bars_by_symbol: dict[str, pd.DataFrame] = {}
    panel_rows: list[pd.DataFrame] = []
    for symbol_number in range(12):
        symbol = f"S{symbol_number:02d}"
        phase = 0.37 * symbol_number
        close = (
            30.0
            + 1.7 * symbol_number
            + (0.025 + 0.002 * symbol_number) * step
            + (0.7 + 0.03 * symbol_number) * np.sin(step / 8.0 + phase)
            + 0.15 * np.cos(step / 19.0 + 2.0 * phase)
        )
        volume = (
            1000.0
            + 23.0 * symbol_number
            + (2.5 + 0.1 * symbol_number) * step
            + 35.0 * np.cos(step / 13.0 + phase)
        )
        bars = pd.DataFrame(
            {
                "open": close * (1.0 - 0.001),
                "high": close * (1.0 + 0.004),
                "low": close * (1.0 - 0.004),
                "close": close,
                "volume": volume,
            },
            index=months,
        )
        bars_by_symbol[symbol] = bars
        panel_rows.append(
            pd.DataFrame(
                {
                    "permno": 10000 + symbol_number,
                    "month": months,
                    "prc": close,
                    "tvol": volume,
                    "me": 1_000_000.0 - 1000.0 * symbol_number,
                }
            )
        )
    return bars_by_symbol, pd.concat(panel_rows, ignore_index=True)


def _snapshot_failures() -> list[str]:
    failures = []
    for relative, expected in SNAPSHOT_HASHES.items():
        path = SNAPSHOT_ROOT / relative
        if not path.is_file():
            failures.append(f"missing pinned source snapshot: {relative}")
        elif sha256(path) != expected:
            failures.append(f"pinned source snapshot hash mismatch: {relative}")
    return failures


@lru_cache(maxsize=1)
def conformance_report() -> tuple[dict[str, Any], list[str]]:
    """Run the reference and vectorized implementations on synthetic inputs."""
    failures = _snapshot_failures()
    report: dict[str, Any] = {
        "source_commit": SOURCE_COMMIT,
        "fixture_id": FIXTURE_ID,
        "uses_empirical_outcomes": False,
        "snapshot_sha256": SNAPSHOT_HASHES,
        "score_absolute_tolerance": SCORE_ATOL,
        "path_absolute_tolerance": PATH_ATOL,
        "candidate_results": {},
    }
    if failures:
        report["passed"] = False
        report["failures"] = failures
        return report, failures

    evaluator, cross_sectional = load_pinned_modules()
    bars_by_symbol, panel = deterministic_fixture()
    scored = evaluate_released_seeds(panel)
    symbols = list(bars_by_symbol)
    permno_by_symbol = {
        symbol: 10000 + position for position, symbol in enumerate(symbols)
    }
    cross_sectional._bars_for_symbol = (  # type: ignore[attr-defined]
        lambda symbol, _cfg: bars_by_symbol[symbol].copy()
    )

    for candidate_id, metadata in PRIMARY_COMPONENTS.items():
        max_score_difference = 0.0
        compared_score_count = 0
        for symbol in symbols:
            reference_score = evaluator.evaluate_expr_series(
                metadata["expression"], bars_by_symbol[symbol], warmup_bars=240
            )
            implemented_score = (
                scored.loc[scored["permno"] == permno_by_symbol[symbol]]
                .set_index("month")[candidate_id]
                .dropna()
            )
            if not reference_score.index.equals(implemented_score.index):
                failures.append(f"score index mismatch for {candidate_id}/{symbol}")
                continue
            difference = np.abs(
                reference_score.to_numpy() - implemented_score.to_numpy()
            )
            if len(difference):
                max_score_difference = max(
                    max_score_difference, float(difference.max())
                )
            compared_score_count += len(difference)
            if not np.allclose(
                reference_score.to_numpy(),
                implemented_score.to_numpy(),
                rtol=0.0,
                atol=SCORE_ATOL,
            ):
                failures.append(f"score value mismatch for {candidate_id}/{symbol}")

        first_month = bars_by_symbol[symbols[0]].index[239]
        last_month = bars_by_symbol[symbols[0]].index[-1]
        config = cross_sectional.CrossSectionalConfig(
            symbols=symbols,
            start_date=first_month.strftime("%Y-%m-%d"),
            end_date=last_month.strftime("%Y-%m-%d"),
            bar_minutes=5,
            horizon_bars=1,
            min_symbols_per_time=8,
            min_times=20,
        )
        reference_path = cross_sectional.evaluate_cross_sectional_expr(
            metadata["expression"], config
        )
        if reference_path.profile is None:
            failures.append(
                f"reference evaluator produced no profile for {candidate_id}"
            )
            reference_dates = pd.DatetimeIndex([])
            reference_returns = np.asarray([], dtype=float)
        else:
            reference_dates = pd.to_datetime(reference_path.profile["ts"])
            reference_returns = np.asarray(
                reference_path.profile["ls_return"], dtype=float
            )

        implemented_path, _ = released_cross_sectional_path(
            scored, candidate_id, min_symbols=8
        )
        implemented_dates = pd.DatetimeIndex(
            implemented_path["formation_month"]
        )
        implemented_returns = implemented_path["gross_excess_return"].to_numpy()
        if not reference_dates.equals(implemented_dates):
            failures.append(f"portfolio timestamp mismatch for {candidate_id}")
        if len(reference_returns) != len(implemented_returns):
            failures.append(f"portfolio length mismatch for {candidate_id}")
            max_path_difference = float("inf")
        else:
            path_difference = np.abs(reference_returns - implemented_returns)
            max_path_difference = (
                float(path_difference.max()) if len(path_difference) else 0.0
            )
            if not np.allclose(
                reference_returns,
                implemented_returns,
                rtol=0.0,
                atol=PATH_ATOL,
            ):
                failures.append(f"portfolio return mismatch for {candidate_id}")

        report["candidate_results"][candidate_id] = {
            "expression": metadata["expression"],
            "score_values_compared": compared_score_count,
            "portfolio_times_compared": len(reference_returns),
            "max_abs_score_difference": max_score_difference,
            "max_abs_portfolio_return_difference": max_path_difference,
        }

    report["passed"] = not failures
    report["failures"] = failures
    return report, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-report",
        type=Path,
        help="also write the deterministic conformance report to this path",
    )
    args = parser.parse_args()
    report, failures = conformance_report()
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(rendered + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
