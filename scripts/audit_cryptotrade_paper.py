#!/usr/bin/env python3
"""Audit CryptoTrade's paper tables against its pinned public code and data.

The audit executes only the deterministic trading environment and traditional
signal strategies. It never imports the module containing the released API
credential, calls an LLM endpoint, or treats the README's one-day example as a
full-period paper result.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
from argparse import Namespace
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd


SOURCE_COMMIT = "210da73af5f17992be425e61305524a5c24dae40"
PAPER_SHA256 = "376606b05f5398c9200b0a560690693ea0a023a97631175ae02528e4dffec5cf"
PAPER_URL = "https://aclanthology.org/2024.emnlp-main.63.pdf"
SOURCE_URL = "https://github.com/Xtra-Computing/CryptoTrade"
DISPLAY_TOLERANCE = 0.005 + 1e-12
METRICS = (
    "total_return_pct",
    "daily_return_mean_pct",
    "daily_return_std_pct",
    "sharpe_ratio",
)
REGIMES = ("bull", "sideways", "bear")
TRADITIONAL_STRATEGIES = {
    "buy_and_hold",
    "sma",
    "slma",
    "macd",
    "bollinger_bands",
}
TIME_SERIES_STRATEGIES = {"lstm", "informer", "autoformer", "timesnet", "patchtst"}
LLM_STRATEGIES = {"gpt_3_5_turbo", "gpt_4", "gpt_4o"}
SMA_PERIODS = (5, 10, 15, 20, 30)


# Transcribed from Tables 2--4 of the pinned official PDF. Each row is:
# asset|strategy|three total returns|three daily means|three daily stds|three Sharpes,
# with values ordered bull, sideways, bear within each metric block.
PAPER_ROWS_TEXT = """
btc|buy_and_hold|39.66|-0.83|-15.61|0.56|0.00|-0.24|2.23|1.74|2.07|0.25|0.00|-0.11
btc|sma|22.58|3.65|-21.74|0.35|0.06|-0.36|1.89|1.21|1.25|0.18|0.05|-0.29
btc|slma|38.53|-3.14|-7.68|0.55|-0.04|-0.11|2.21|0.83|1.23|0.25|-0.05|-0.09
btc|macd|13.57|-6.71|-9.51|0.22|-0.09|-0.14|1.45|1.01|1.56|0.15|-0.09|-0.09
btc|bollinger_bands|2.97|-3.19|-1.17|0.05|-0.04|-0.02|0.32|0.87|0.51|0.15|-0.05|-0.03
btc|lstm|31.67|-4.13|-17.20|0.47|-0.05|-0.28|2.11|1.62|1.27|0.22|-0.03|-0.22
btc|informer|0.34|-2.33|-13.38|0.01|-0.03|-0.21|0.82|0.54|1.02|0.01|-0.06|-0.21
btc|autoformer|14.73|-4.90|-12.72|0.24|-0.07|-0.20|1.65|1.15|1.13|0.14|-0.06|-0.18
btc|timesnet|2.84|-5.12|-13.64|0.05|-0.07|-0.22|1.06|1.10|1.04|0.05|-0.06|-0.21
btc|patchtst|1.79|-5.02|-21.94|0.03|-0.07|-0.37|0.71|0.57|1.05|0.04|-0.13|-0.35
btc|gpt_3_5_turbo|18.84|0.33|-9.12|0.30|0.01|-0.14|1.69|1.19|1.52|0.18|0.01|-0.09
btc|gpt_4|26.35|-4.07|-11.72|0.40|-0.05|-0.18|1.76|1.43|1.67|0.23|-0.04|-0.11
btc|gpt_4o|28.47|-5.08|-13.71|0.43|-0.07|-0.21|1.89|1.14|1.71|0.23|-0.06|-0.12
eth|buy_and_hold|22.59|-1.91|-12.24|0.36|-0.01|-0.17|2.62|1.94|2.39|0.14|-0.00|-0.07
eth|sma|10.17|-5.45|-10.12|0.18|-0.15|-0.15|2.29|1.64|1.64|0.08|-0.07|-0.09
eth|slma|5.20|-2.62|-15.90|0.11|-0.03|-0.24|2.37|1.08|1.86|0.05|-0.03|-0.13
eth|macd|7.72|0.77|-12.15|0.13|0.02|-0.18|1.22|1.43|1.56|0.10|0.01|-0.12
eth|bollinger_bands|2.59|4.47|-0.41|0.04|0.07|0.00|0.40|1.02|0.58|0.11|0.06|-0.01
eth|lstm|22.12|1.27|-13.22|0.36|0.02|-0.19|2.59|1.11|2.36|0.14|0.15|-0.08
eth|informer|14.55|-4.74|-11.49|0.23|-0.06|-0.17|1.54|1.45|1.65|0.15|-0.04|-0.10
eth|autoformer|7.77|-10.06|-19.44|0.13|-0.14|-0.31|1.81|1.33|1.61|0.08|-0.10|-0.20
eth|timesnet|13.31|-8.08|-10.64|0.21|-0.11|-0.16|1.50|1.08|1.04|0.14|-0.10|-0.16
eth|patchtst|8.95|-9.64|-13.76|0.15|-0.13|-0.21|1.37|1.66|1.39|0.11|-0.11|-0.15
eth|gpt_3_5_turbo|18.91|-5.02|-14.40|0.30|-0.06|-0.22|2.01|1.56|2.08|0.15|-0.04|-0.10
eth|gpt_4|25.72|0.72|-13.72|0.41|0.03|-0.21|2.45|1.67|2.02|0.17|0.02|-0.10
eth|gpt_4o|25.47|-6.59|-15.35|0.40|-0.07|-0.23|2.25|1.81|2.16|0.18|-0.04|-0.11
sol|buy_and_hold|176.72|-3.23|-36.08|1.83|0.01|-0.61|6.00|3.92|3.45|0.30|0.00|-0.18
sol|sma|119.37|-0.62|1.04|1.43|0.03|0.02|5.67|3.06|0.10|0.25|0.01|0.16
sol|slma|169.98|6.22|-8.11|1.78|0.16|-0.11|5.93|3.23|1.88|0.30|0.05|-0.06
sol|macd|23.25|-9.78|-21.07|0.35|-0.16|-0.33|1.76|2.38|2.44|0.20|-0.07|-0.13
sol|bollinger_bands|2.92|-0.46|-21.69|0.05|0.00|-0.35|0.35|1.23|1.75|0.13|-0.00|-0.20
sol|lstm|144.69|-3.56|-36.75|1.61|0.01|-0.63|5.69|3.90|3.43|0.28|0.00|-0.18
sol|informer|41.85|-6.55|-26.13|0.58|-0.10|-0.43|1.90|2.00|2.36|0.31|-0.05|-0.18
sol|autoformer|35.86|-6.17|-23.56|0.51|-0.10|-0.38|1.97|1.90|2.35|0.26|-0.05|-0.16
sol|timesnet|45.28|-10.63|-21.60|0.64|-0.18|-0.35|2.66|2.01|1.75|0.24|-0.09|-0.20
sol|patchtst|18.45|-7.10|-27.86|0.29|-0.11|-0.46|1.57|1.98|2.49|0.18|-0.06|-0.19
sol|gpt_3_5_turbo|102.45|-13.05|-24.08|1.26|-0.23|-0.39|4.54|2.42|2.60|0.28|-0.15|-0.10
sol|gpt_4|99.84|-2.16|-19.55|1.24|0.01|-0.31|4.53|3.33|2.35|0.27|0.00|-0.13
sol|gpt_4o|115.18|3.09|-16.32|1.38|0.11|-0.25|4.98|3.31|2.35|0.28|0.03|-0.10
"""


PAPER_SPLITS: Mapping[str, Mapping[str, Tuple[str, str, float, float, float]]] = {
    "btc": {
        "validation": ("2023-01-19", "2023-03-13", 20977.48, 20628.03, -1.67),
        "bear": ("2023-04-12", "2023-06-16", 30462.48, 25575.28, -15.61),
        "sideways": ("2023-06-17", "2023-08-25", 26328.68, 26163.68, -0.83),
        "bull": ("2023-10-01", "2023-12-01", 26967.40, 37718.01, 39.66),
    },
    "eth": {
        "validation": ("2023-01-13", "2023-03-12", 1417.13, 1429.60, 0.88),
        "bear": ("2023-04-12", "2023-06-16", 1892.94, 1664.98, -12.24),
        "sideways": ("2023-06-20", "2023-08-31", 1734.79, 1705.11, -1.91),
        "bull": ("2023-10-01", "2023-12-01", 1671.00, 2051.76, 22.59),
    },
    "sol": {
        "validation": ("2023-01-14", "2023-03-12", 18.29, 18.24, -0.27),
        "bear": ("2023-04-12", "2023-06-16", 23.02, 14.76, -36.08),
        "sideways": ("2023-07-08", "2023-08-31", 21.49, 20.83, -3.23),
        "bull": ("2023-10-01", "2023-12-01", 21.39, 59.25, 176.72),
    },
}


PAPER_ABLATION = {
    "full": (28.47, 0.23),
    "without_reflection": (17.14, 0.06),
    "without_news": (19.69, 0.06),
    "without_transaction_statistics": (12.70, 0.05),
    "without_technical": (17.27, 0.05),
    "base": (8.40, 0.03),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_result_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in PAPER_ROWS_TEXT.strip().splitlines():
        values = line.split("|")
        if len(values) != 14:
            raise ValueError(f"Malformed paper result row: {line}")
        asset, strategy = values[:2]
        numbers = [float(value) for value in values[2:]]
        totals, means, stds, sharpes = (
            numbers[0:3],
            numbers[3:6],
            numbers[6:9],
            numbers[9:12],
        )
        for index, regime in enumerate(REGIMES):
            metrics = (totals[index], means[index], stds[index], sharpes[index])
            for metric, paper_value in zip(METRICS, metrics):
                rows.append(
                    {
                        "asset": asset,
                        "strategy": strategy,
                        "regime": regime,
                        "metric": metric,
                        "paper_value": paper_value,
                    }
                )
    return rows


def load_environment(source_root: Path) -> Any:
    module_path = source_root / "eth_env.py"
    spec = importlib.util.spec_from_file_location("cryptotrade_pinned_eth_env", module_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def source_simulation(
    environment_module: Any,
    source_root: Path,
    asset: str,
    start: str,
    end: str,
    strategy: str,
    parameter: Any = None,
) -> Dict[str, float]:
    old_cwd = Path.cwd()
    os.chdir(source_root)
    try:
        environment = environment_module.ETHTradingEnv(Namespace(dataset=asset, starting_date=start, ending_date=end))
        state, _, _, _ = environment.reset()
        start_net_worth = float(state["net_worth"])
        previous_net_worth = start_net_worth
        daily_returns: List[float] = []
        for _, row in environment.data.reset_index(drop=True).iterrows():
            net_worth = float(state["net_worth"])
            daily_returns.append(net_worth / previous_net_worth - 1)
            previous_net_worth = net_worth
            if environment.done:
                break

            cash = float(state["cash"])
            held = float(state["eth_held"])
            action = 0.0
            if strategy == "buy_and_hold":
                action = 1.0 if cash > 0 else 0.0
            elif strategy == "sma":
                period = int(parameter)
                buy = float(state["open"]) > float(row[f"SMA_{period}"])
                action = 0.5 if buy and cash > 0 else -0.5 if not buy and held > 0 else 0.0
            elif strategy == "slma":
                short, long = parameter
                buy = float(row[f"SMA_{short}"]) > float(row[f"SMA_{long}"])
                action = 0.5 if buy else -0.5 if held > 0 else 0.0
            elif strategy == "macd":
                # This intentionally preserves the released runner's signal direction.
                buy = float(row["MACD"]) < float(row["Signal_Line"])
                action = 0.5 if buy and cash > 0 else -0.5 if not buy and held > 0 else 0.0
            elif strategy == "bollinger_bands":
                lower = float(row["SMA_20"]) - 2 * float(row["STD_20"])
                upper = float(row["SMA_20"]) + 2 * float(row["STD_20"])
                price = float(state["open"])
                action = 0.5 if price < lower and cash > 0 else -0.5 if price > upper and held > 0 else 0.0
            else:
                raise ValueError(f"Unsupported deterministic source strategy: {strategy}")
            state, _, _, _ = environment.step(action)
    finally:
        os.chdir(old_cwd)

    daily = np.asarray(daily_returns, dtype=float) * 100
    mean = float(np.mean(daily))
    std = float(np.std(daily))
    return {
        "total_return_pct": (float(state["net_worth"]) / start_net_worth - 1) * 100,
        "daily_return_mean_pct": mean,
        "daily_return_std_pct": std,
        "sharpe_ratio": mean / std,
        "start_open": float(environment.starting_price),
        "end_open": float(state["open"]),
        "observations": int(environment.total_steps),
    }


def fixed_parameter(strategy: str) -> Any:
    if strategy == "sma":
        return 15
    if strategy == "slma":
        return (15, 30)
    return None


def result_conformance(
    environment_module: Any, source_root: Path
) -> Tuple[List[Dict[str, Any]], Dict[Tuple[str, str, str], Dict[str, float]]]:
    reproduced: Dict[Tuple[str, str, str], Dict[str, float]] = {}
    for asset in PAPER_SPLITS:
        for regime in REGIMES:
            start, end, *_ = PAPER_SPLITS[asset][regime]
            for strategy in sorted(TRADITIONAL_STRATEGIES):
                reproduced[(asset, strategy, regime)] = source_simulation(
                    environment_module,
                    source_root,
                    asset,
                    start,
                    end,
                    strategy,
                    fixed_parameter(strategy),
                )

    rows = []
    for target in paper_result_rows():
        strategy = target["strategy"]
        key = (target["asset"], strategy, target["regime"])
        source_value: Any = ""
        absolute_error: Any = ""
        if strategy in TRADITIONAL_STRATEGIES:
            source_value = reproduced[key][target["metric"]]
            absolute_error = abs(source_value - target["paper_value"])
            status = "exact_displayed_precision_match" if absolute_error <= DISPLAY_TOLERANCE else "mismatch"
            evidence = "pinned_native_environment_with_released_traditional_strategy_logic"
        elif strategy in TIME_SERIES_STRATEGIES:
            status = "unverifiable_no_shipped_full_period_output"
            evidence = "partial_lstm_code_only" if strategy == "lstm" else "implementation_not_released"
        elif strategy in LLM_STRATEGIES:
            status = "unverifiable_no_shipped_full_period_output"
            evidence = "api_runner_and_one_day_readme_example_only"
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        rows.append(
            {
                **target,
                "source_recomputed_value": source_value,
                "absolute_error": absolute_error,
                "display_tolerance": DISPLAY_TOLERANCE,
                "status": status,
                "evidence": evidence,
            }
        )
    return rows, reproduced


def split_conformance(
    environment_module: Any,
    source_root: Path,
    reproduced: Mapping[Tuple[str, str, str], Mapping[str, float]],
) -> List[Dict[str, Any]]:
    rows = []
    for asset, splits in PAPER_SPLITS.items():
        for split, (start, end, paper_open, paper_close, paper_trend) in splits.items():
            if split == "validation":
                actual = source_simulation(
                    environment_module,
                    source_root,
                    asset,
                    start,
                    end,
                    "buy_and_hold",
                )
            else:
                actual = reproduced[(asset, "buy_and_hold", split)]
            rows.append(
                {
                    "asset": asset,
                    "split": split,
                    "start": start,
                    "end": end,
                    "paper_open": paper_open,
                    "source_open": actual["start_open"],
                    "open_status": (
                        "exact_displayed_precision_match"
                        if abs(paper_open - actual["start_open"]) <= DISPLAY_TOLERANCE
                        else "mismatch"
                    ),
                    "paper_close": paper_close,
                    "source_end_open": actual["end_open"],
                    "close_status": (
                        "exact_displayed_precision_match"
                        if abs(paper_close - actual["end_open"]) <= DISPLAY_TOLERANCE
                        else "mismatch"
                    ),
                    "paper_trend_pct": paper_trend,
                    "source_costed_buy_hold_return_pct": actual["total_return_pct"],
                    "trend_status": (
                        "exact_displayed_precision_match"
                        if abs(paper_trend - actual["total_return_pct"]) <= DISPLAY_TOLERANCE
                        else "mismatch"
                    ),
                    "source_observations_including_end_price": actual["observations"],
                }
            )
    return rows


def parameter_selection_audit(
    environment_module: Any,
    source_root: Path,
    conformance: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    rows = []
    for asset, splits in PAPER_SPLITS.items():
        validation_start, validation_end, *_ = splits["validation"]
        candidates: Mapping[str, Iterable[Any]] = {
            "sma": SMA_PERIODS,
            "slma": tuple(combinations(SMA_PERIODS, 2)),
        }
        for strategy, parameters in candidates.items():
            results = [
                (
                    parameter,
                    source_simulation(
                        environment_module,
                        source_root,
                        asset,
                        validation_start,
                        validation_end,
                        strategy,
                        parameter,
                    )["total_return_pct"],
                )
                for parameter in parameters
            ]
            best_parameter, best_return = max(results, key=lambda item: item[1])
            released_fixed = fixed_parameter(strategy)
            relevant = [
                row
                for row in conformance
                if row["asset"] == asset
                and row["strategy"] == strategy
                and row["status"] in {"exact_displayed_precision_match", "mismatch"}
            ]
            rows.append(
                {
                    "asset": asset,
                    "strategy": strategy,
                    "paper_rule": "select best validation performance",
                    "released_runner_fixed_parameter": str(released_fixed),
                    "released_data_validation_argmax": str(best_parameter),
                    "released_data_validation_argmax_return_pct": best_return,
                    "fixed_parameter_equals_validation_argmax": released_fixed == best_parameter,
                    "paper_test_metric_cells_matching_with_fixed_parameter": sum(
                        row["status"] == "exact_displayed_precision_match" for row in relevant
                    ),
                    "paper_test_metric_cells_total": len(relevant),
                    "status": (
                        "selection_rule_match" if released_fixed == best_parameter else "selection_rule_mismatch"
                    ),
                }
            )
    return rows


def _date_bounds(path: Path, column: str, date_format: str) -> Tuple[str, str, int]:
    frame = pd.read_csv(path)
    dates = pd.to_datetime(frame[column], format=date_format, errors="raise")
    return dates.min().date().isoformat(), dates.max().date().isoformat(), len(frame)


def data_inventory(source_root: Path) -> List[Dict[str, Any]]:
    specifications = (
        ("data/eth_daily.csv", "price", "snapped_at", "%Y-%m-%d %H:%M:%S UTC"),
        ("data/bitcoin_daily_price.csv", "price", "timeOpen", "%Y-%m-%dT%H:%M:%S.%fZ"),
        ("data/solana_daily_price.csv", "price", "timeOpen", "%Y-%m-%dT%H:%M:%S.%fZ"),
        (
            "data/eth_more_transaction_statistics.csv",
            "on_chain",
            "day",
            "%d/%m/%y %H:%M",
        ),
        (
            "data/bitcoin_transaction_statistics.csv",
            "on_chain",
            "day",
            "%Y-%m-%d %H:%M:%S.%f UTC",
        ),
        (
            "data/solana_transaction_statistics.csv",
            "on_chain",
            "day",
            "%Y-%m-%d %H:%M:%S.%f UTC",
        ),
    )
    rows = []
    for relative, role, column, date_format in specifications:
        path = source_root / relative
        start, end, count = _date_bounds(path, column, date_format)
        rows.append(
            {
                "path": relative,
                "role": role,
                "rows_or_files": count,
                "date_start": start,
                "date_end": end,
                "sha256": sha256(path),
            }
        )
    for relative in (
        "data/gnews",
        "data/selected_bitcoin_202301_202401",
        "data/selected_solana_202301_202401",
    ):
        paths = sorted((source_root / relative).glob("*.json"))
        rows.append(
            {
                "path": relative,
                "role": "off_chain_news",
                "rows_or_files": len(paths),
                "date_start": paths[0].stem,
                "date_end": paths[-1].stem,
                "sha256": "directory_inventory_not_single_file",
            }
        )
    return rows


def source_execution_gaps(source_root: Path) -> List[Dict[str, str]]:
    runner = (source_root / "run_agent.sh").read_text(encoding="utf-8")
    baseline = (source_root / "run_baseline.py").read_text(encoding="utf-8")
    prompts = (source_root / "env_history.py").read_text(encoding="utf-8")
    utils = (source_root / "utils.py").read_text(encoding="utf-8")
    executable = bool((source_root / "run_agent.sh").stat().st_mode & stat.S_IXUSR)
    logs_dir = (source_root / "logs").is_dir()
    active_commands = [
        line.strip() for line in runner.splitlines() if line.strip().startswith("python -u run_agent.py")
    ]
    period_mismatches = sum(
        any(literal in command for literal in ("eth --starting_date 2023-06-17", "sol --starting_date 2023-06-17"))
        for command in active_commands
    )
    gaps = (
        (
            "readme_run_command",
            "fails_before_agent_execution",
            f"run_agent.sh executable={executable}; required logs directory present={logs_dir}",
        ),
        (
            "active_gpt4o_periods",
            "two_of_nine_commands_mismatch_paper_splits",
            f"active_commands={len(active_commands)}; mismatched_eth_sol_sideways={period_mismatches}",
        ),
        (
            "baseline_entrypoint",
            "fails_without_source_edits_and_dependencies",
            "README omits required packages; run_baseline constructs Namespace without dataset",
        ),
        (
            "asset_specific_prompts",
            "mismatch_for_btc_and_sol",
            "released prompt templates hard-code ETH instead of interpolating the dataset",
        ),
        (
            "llm_result_evidence",
            "full_period_outputs_absent",
            "README contains one first-step ETH example; no paper-period result logs are tracked",
        ),
        (
            "time_series_baselines",
            "incomplete_release",
            "LSTM is embedded in a monolithic ETH runner; Informer/AutoFormer/TimesNet/PatchTST implementations and outputs are absent",
        ),
        (
            "model_identity",
            "paper_to_runner_mismatch",
            "paper reports GPT-4 while released shell commands use gpt-4-turbo",
        ),
        (
            "transaction_cost_specification",
            "paper_underspecified",
            "paper states a proportional fee but not its rate; source fixes EX_RATE=0.004 plus a fixed gas charge",
        ),
        (
            "credential_hygiene",
            "environment_variable_used",
            "released utility reads OPENAI_API_KEY; the audit never imports or uses the API module",
        ),
    )
    if "Namespace(starting_date=sargs['starting_date'], ending_date=sargs['ending_date'])" not in baseline:
        raise RuntimeError("Pinned baseline runner no longer has the audited missing-dataset call")
    if "You are an ETH cryptocurrency" not in prompts:
        raise RuntimeError("Pinned prompt templates no longer have the audited asset literal")
    utility_tree = ast.parse(utils)
    api_key_assignments = [
        node
        for node in ast.walk(utility_tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "api_key" for target in node.targets)
    ]
    if len(api_key_assignments) != 1 or not isinstance(api_key_assignments[0].value, ast.Call):
        raise RuntimeError("Pinned API-key loading pattern changed; re-audit it explicitly")
    return [{"component": component, "status": status, "evidence": evidence} for component, status, evidence in gaps]


def build_audit(source_root: Path, paper_path: Path, output_dir: Path) -> Dict[str, Any]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    if sha256(paper_path) != PAPER_SHA256:
        raise RuntimeError("Official paper PDF hash does not match the pinned primary source")

    environment_module = load_environment(source_root)
    conformance, reproduced = result_conformance(environment_module, source_root)
    splits = split_conformance(environment_module, source_root, reproduced)
    selection = parameter_selection_audit(environment_module, source_root, conformance)
    inventory = data_inventory(source_root)
    gaps = source_execution_gaps(source_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_2_4_conformance.csv", conformance, list(conformance[0]))
    write_csv(output_dir / "dataset_split_conformance.csv", splits, list(splits[0]))
    write_csv(output_dir / "parameter_selection_audit.csv", selection, list(selection[0]))
    write_csv(output_dir / "data_inventory.csv", inventory, list(inventory[0]))
    write_csv(output_dir / "source_execution_gaps.csv", gaps, list(gaps[0]))
    paper_inconsistencies = (
        {
            "claim": "Table 5 ablation market/asset label",
            "paper_value_a": "ETH bullish (caption/prose)",
            "paper_value_b": "Full=28.47% return, 0.23 Sharpe",
            "status": "paper_internal_mismatch",
            "evidence": (
                "The Full values equal BTC-bull GPT-4o in Table 2, while ETH-bull GPT-4o in Table 3 is 25.47% and 0.18."
            ),
        },
    )
    write_csv(
        output_dir / "paper_internal_inconsistencies.csv",
        paper_inconsistencies,
        list(paper_inconsistencies[0]),
    )

    matched = sum(row["status"] == "exact_displayed_precision_match" for row in conformance)
    mismatched = sum(row["status"] == "mismatch" for row in conformance)
    unverifiable = sum(row["status"].startswith("unverifiable") for row in conformance)
    deterministic = matched + mismatched
    grouped: Dict[Tuple[str, str, str], List[Mapping[str, Any]]] = {}
    for row in conformance:
        grouped.setdefault((row["asset"], row["strategy"], row["regime"]), []).append(row)
    fully_matched_rows = sum(
        all(row["status"] == "exact_displayed_precision_match" for row in rows) for rows in grouped.values()
    )
    mismatched_rows = sum(any(row["status"] == "mismatch" for row in rows) for rows in grouped.values())
    unverifiable_rows = sum(all(row["status"].startswith("unverifiable") for row in rows) for rows in grouped.values())
    split_price_matches = sum(
        row[metric] == "exact_displayed_precision_match" for row in splits for metric in ("open_status", "close_status")
    )
    split_trend_matches = sum(row["trend_status"] == "exact_displayed_precision_match" for row in splits)
    manifest: Dict[str, Any] = {
        "audit": "CryptoTrade paper claims versus pinned public code and data",
        "overall_status": "partial_reproduction_traditional_baselines_only",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "paper_result_metric_cells_total": len(conformance),
        "native_deterministic_metric_cells_recomputed": deterministic,
        "native_deterministic_metric_cells_matched": matched,
        "native_deterministic_metric_cells_mismatched": mismatched,
        "paper_result_metric_cells_unverifiable": unverifiable,
        "paper_strategy_regime_rows_total": len(grouped),
        "paper_strategy_regime_rows_fully_matched": fully_matched_rows,
        "paper_strategy_regime_rows_mismatched": mismatched_rows,
        "paper_strategy_regime_rows_unverifiable": unverifiable_rows,
        "traditional_strategy_rows_total": 45,
        "traditional_strategy_rows_fully_matched": 43,
        "traditional_strategy_cells_matched": 174,
        "traditional_strategy_cells_total": 180,
        "traditional_mismatches": (
            "ETH sideways SMA: daily mean and standard deviation; SOL bear SMA: all four displayed metrics"
        ),
        "dataset_split_price_cells_matched": split_price_matches,
        "dataset_split_price_cells_total": len(splits) * 2,
        "dataset_split_costed_trend_cells_matched": split_trend_matches,
        "dataset_split_costed_trend_cells_total": len(splits),
        "paper_described_validation_selections_matching_released_data_argmax": sum(
            row["status"] == "selection_rule_match" for row in selection
        ),
        "paper_described_validation_selections_total": len(selection),
        "paper_ablation_rows": len(PAPER_ABLATION),
        "paper_ablation_full_values_duplicate_btc_bull_gpt4o": (PAPER_ABLATION["full"] == (28.47, 0.23)),
        "full_period_llm_result_logs_shipped": False,
        "full_period_time_series_result_logs_shipped": False,
        "all_time_series_implementations_shipped": False,
        "readme_example_is_full_period_result": False,
        "readme_run_agent_shell_executable": bool((source_root / "run_agent.sh").stat().st_mode & stat.S_IXUSR),
        "run_agent_log_directory_shipped": (source_root / "logs").is_dir(),
        "dependency_lock_or_environment_manifest_shipped": any(
            (source_root / name).is_file()
            for name in ("requirements.txt", "pyproject.toml", "environment.yml", "Dockerfile")
        ),
        "source_prompts_asset_generic": False,
        "paper_gpt4_label_matches_released_gpt4_turbo_literal": False,
        "paper_transaction_fee_rate_disclosed": False,
        "source_exchange_fee_rate": float(environment_module.EX_RATE),
        "source_fixed_gas_fee_asset_units": float(environment_module.GAS_FEE),
        "source_contains_hardcoded_credential_literal": False,
        "audit_imported_or_used_credential_module": False,
        "interpretation": (
            "The released market data, native environment, costs, and traditional-signal logic "
            "reproduce 174/180 displayed traditional-baseline metric cells. This is strong "
            "component evidence, not a full CryptoTrade replication: 288 LLM/time-series cells "
            "lack shipped full-period outputs, two traditional rows contain mismatches, validation "
            "selection is not implemented as described, and the documented entrypoints are not "
            "operational without repair."
        ),
        "source_file_sha256": {
            name: sha256(source_root / name)
            for name in (
                "README.md",
                "env_history.py",
                "eth_env.py",
                "eth_trial.py",
                "run_agent.py",
                "run_agent.sh",
                "run_baseline.py",
                "utils.py",
            )
        },
    }
    if (matched, mismatched, unverifiable) != (174, 6, 288):
        raise RuntimeError(
            "Pinned CryptoTrade conformance counts changed: "
            f"matched={matched}, mismatched={mismatched}, unverifiable={unverifiable}"
        )
    if (fully_matched_rows, mismatched_rows, unverifiable_rows) != (43, 2, 72):
        raise RuntimeError("Pinned CryptoTrade row-level conformance counts changed")

    report = f"""# CryptoTrade paper-level conformance audit

Overall verdict: **partial reproduction, not a full paper replication**. The pinned
public data and native trading environment strongly reproduce deterministic
traditional baselines, but the released artifacts do not reproduce CryptoTrade's
full-period LLM results or the five time-series baselines.

## Primary sources

- Official paper: {PAPER_URL} (SHA-256 `{PAPER_SHA256}`).
- Public source: {SOURCE_URL}, commit `{commit}`.

## What reproduces

- A safe adapter over the released environment, 0.4% exchange cost, fixed gas cost,
  and traditional-signal logic matches {matched}/{deterministic} displayed cells
  across Buy-and-Hold, SMA, SLMA, MACD, and Bollinger Bands.
- {fully_matched_rows}/45 traditional strategy/asset/regime rows match all four
  displayed metrics (total return, daily mean, daily standard deviation, and
  Sharpe ratio). This includes every Buy-and-Hold, SLMA, MACD, and Bollinger row.
- ETH-sideways SMA matches the paper's -5.45% total return and -0.07 Sharpe, but
  the released path produces -0.07+/-1.00 daily return rather than -0.15+/-1.64.
  The paper's daily cell exactly duplicates its ETH-bear SMA daily cell.
- SOL-bear SMA is the larger mismatch: the paper reports +1.04% return,
  0.02+/-0.10 daily return, and 0.16 Sharpe, while every released SMA window loses
  between 17.77% and 22.19%; the runner's fixed 15-day window produces -17.77%,
  -0.28+/-2.00, and -0.14.

## Why this is not a full reproduction

- {unverifiable}/{len(conformance)} paper result cells are unverifiable: no complete
  GPT-3.5-turbo, GPT-4, or GPT-4o result paths are shipped, and the README contains
  only the first ETH-bull GPT-4 step rather than the paper's full-period result.
- Informer, AutoFormer, TimesNet, and PatchTST implementations are absent. The
  included LSTM is embedded in an ETH-only monolithic runner, has no seed, trains
  on the full requested interval, and ships no result path.
- The paper says SMA/SLMA parameters are selected on validation performance. The
  source prints candidate validation results and then hard-codes SMA=15 and
  SLMA=15/30. Only {manifest["paper_described_validation_selections_matching_released_data_argmax"]}/6
  fixed choices equal the released-data validation argmax.
- The paper does not disclose the transaction-fee rate. The source uses 0.4% of
  traded value plus a fixed gas charge, which is necessary to match the tables.
- `run_agent.sh` is tracked as non-executable and redirects into an absent `logs/`
  directory. Its active GPT-4o ETH/SOL sideways commands use dates that differ
  from Table 1. `run_baseline.py` omits `dataset` when constructing the environment
  and depends on packages absent from the README requirement list.
- Prompt templates hard-code ETH even for BTC and SOL. The paper's GPT-4 label is
  implemented as `gpt-4-turbo`; no immutable endpoint snapshot or complete API
  response log is available, so a present-day paid rerun would not prove the
  published result.
- The released utility reads `OPENAI_API_KEY` from the environment. This audit does
  not import the API utility or call an endpoint.

## Paper/source inconsistencies retained as evidence

- Table 5 calls the ablation ETH-bull, but its Full values (28.47%, 0.23) exactly
  duplicate BTC-bull GPT-4o in Table 2; ETH-bull GPT-4o is 25.47%, 0.18 in Table 3.
- The released test-period data usually match Table 1 and exactly drive the
  traditional results, but validation prices diverge and the BTC-bear start and
  SOL-bull end prices also differ. See `dataset_split_conformance.csv`.

Run `scripts/audit_cryptotrade_paper.py` to regenerate this package. Use `--strict`
when a CI failure is desired until a defensible full-paper result exists.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "CRYPTOTRADE_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/cryptotrade_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "CRYPTOTRADE_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/cryptotrade_paper.pdf",
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/cryptotrade",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(args.source_root.resolve(), args.paper_pdf.resolve(), args.output_dir.resolve())
    print(json.dumps(manifest, indent=2))
    return int(args.strict and manifest["overall_status"] != "reproduced")


if __name__ == "__main__":
    sys.exit(main())
