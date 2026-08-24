#!/usr/bin/env python3
"""Exercise the unaffiliated FactorMiner-inspired candidate on a synthetic panel.

This runner supplies component evidence only. It cannot grant native FactorMiner
or paper-result credit because the candidate declares itself paper-inspired,
uses different data/model semantics, and ships no paper result lineage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np


SEED = 20260824


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    sys.path.insert(0, str(checkout))

    from backtest.engine import run_factor_backtest, run_library_backtest
    from data.stock_data import calculate_returns
    from factor_mining.experience_memory import ExperienceMemory
    from factor_mining.expression_engine import ExpressionEngine, validate_expression
    from factor_mining.factor_library import FactorLibrary, FactorRecord, compute_ic, compute_icir
    from test_pipeline import TEST_FACTORS

    attempts: list[str] = []

    def blocked_connect(_socket: socket.socket, address: object) -> None:
        attempts.append(str(address))
        raise RuntimeError("network disabled by independent-candidate audit")

    def run_once() -> dict[str, object]:
        rng = np.random.default_rng(SEED)
        assets, observations = 50, 620
        returns = rng.normal(0.0003, 0.018, (assets, observations))
        close = 100.0 * np.exp(np.cumsum(returns, axis=1))
        spread = np.abs(rng.normal(0.01, 0.003, (assets, observations)))
        high, low = close * (1.0 + spread), close * (1.0 - spread)
        panel = {
            "open": close * (1.0 + rng.normal(0.0, 0.002, (assets, observations))),
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.lognormal(15.0, 0.5, (assets, observations)),
            "vwap": (high + low + close) / 3.0,
            "returns": returns,
            "codes": np.asarray([f"S{index:04d}" for index in range(assets)]),
            "dates": np.arange(observations),
        }
        forward = calculate_returns(panel)
        engine = ExpressionEngine(panel)
        signals: dict[str, np.ndarray] = {}
        ic_values: dict[str, tuple[float, float]] = {}
        for definition in TEST_FACTORS:
            expression = definition["expression"]
            valid, error = validate_expression(expression)
            if not valid:
                raise ValueError(f"candidate expression rejected: {expression}: {error}")
            signal = engine.evaluate(expression)
            if signal.shape != (assets, observations) or np.isfinite(signal).sum() == 0:
                raise ValueError(f"candidate expression produced invalid output: {expression}")
            ic = compute_ic(signal, forward)
            signals[expression] = signal
            ic_values[expression] = (float(np.nanmean(ic)), float(compute_icir(ic)))
        best = max(ic_values, key=lambda value: abs(ic_values[value][0]))
        single = run_factor_backtest(signals[best], forward)
        with tempfile.TemporaryDirectory(prefix="factorminer-independent-") as temporary:
            temporary_path = Path(temporary)
            library = FactorLibrary(path=temporary_path / "library.json")
            for expression, (ic_mean, icir) in list(ic_values.items())[:5]:
                library.admit(
                    FactorRecord(
                        expression=expression,
                        ic_mean=ic_mean,
                        ic_std=0.1,
                        icir=icir,
                        max_correlation=0.0,
                        turnover=0.0,
                        logic_description="synthetic audit",
                        mining_round=1,
                    )
                )
            memory = ExperienceMemory(path=temporary_path / "memory.json")
            memory.update_round(1)
            memory.formation(
                [
                    {
                        "expression": expression,
                        "logic": "synthetic audit",
                        "admitted": True,
                        "reason": "audit",
                        "ic_mean": value[0],
                    }
                    for expression, value in list(ic_values.items())[:5]
                ]
            )
            context = memory.retrieve(library.size)
            if library.size != 5 or not context["mining_state_summary"]:
                raise ValueError("candidate library/memory round-trip failed")
            combined = run_library_backtest(
                {factor.expression: signals[factor.expression] for factor in library.factors},
                forward,
                method="equal",
            )
        fields = ("sharpe", "annual_return", "max_drawdown", "win_ratio", "turnover")
        return {
            "expressions": len(signals),
            "best_expression": best,
            "best_ic": ic_values[best][0],
            "single_backtest": {key: float(single[key]) for key in fields},
            "library_backtest": {key: float(combined[key]) for key in fields},
        }

    with patch("socket.socket.connect", blocked_connect):
        first, second = run_once(), run_once()
    if first != second:
        raise ValueError("independent candidate synthetic executions differ")
    canonical = json.dumps(first, sort_keys=True, separators=(",", ":")).encode()
    print(
        json.dumps(
            {
                "candidate_scope": "unaffiliated_component_only_zero_paper_credit",
                "seed": SEED,
                "repeat_equal": True,
                "network_attempts": attempts,
                "payload_sha256": hashlib.sha256(canonical).hexdigest(),
                "result": first,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
