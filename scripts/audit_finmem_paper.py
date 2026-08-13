#!/usr/bin/env python3
"""Audit FinMem's paper tables against pinned public source and price inputs.

The current source tree omits the paper outputs, but the repository's public
history preserves an executed metrics notebook and dated action CSVs. This
audit distinguishes author-output verification, independent metric replay from
those actions, and an end-to-end agent rerun. It never loads untrusted pickle
files, calls an LLM/embedding endpoint, or treats fake sample data as paper data.
"""

from __future__ import annotations

import argparse
import ast
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np


SOURCE_COMMIT = "be814aa47970de9bf2fdd6a1d5a60ae5cf361b46"
SOURCE_ROOT_COMMIT = "85028214b043b38508d07587d01820324503d69a"
HISTORICAL_ARTIFACT_COMMIT = "0b7f499e556668bf49885fd8836efe85ef51558f"
HISTORICAL_DELETION_COMMIT = "45169ea8509c29113c7e7945dc52a6b3e43521eb"
HISTORICAL_NOTEBOOK_PATH = "Visualize-metrics-test/metrics.ipynb"
HISTORICAL_NOTEBOOK_SHA256 = "3096d6a67336270b5b820bd92408733b641abe73edaf04fa9215ec36d3fcf6dc"
HISTORICAL_METRICS_PATH = "Visualize-metrics-test/metrics.py"
HISTORICAL_METRICS_SHA256 = "ffec58d7bdc4b9e94e9bdcf2205c98ab9bef27ce8ddb95e377e154efeae15f21"
EXPECTED_REACHABLE_COMMITS = 55
EXPECTED_HISTORICAL_TREE_FILES = 33
EXPECTED_HISTORICAL_ACTION_CSVS = 18
PAPER_SHA256 = "acb7527d02871cfad7d2754314b9a803f917b326847a456579df9cf7b0a648b9"
PAPER_URL = "https://arxiv.org/pdf/2311.13743"
SOURCE_URL = "https://github.com/pipiku915/finmem-llm-stocktrading"
DISPLAY_TOLERANCE = 0.00005 + 1e-12
METRICS = (
    "cumulative_return_pct",
    "sharpe_ratio",
    "daily_volatility_pct",
    "annualized_volatility_pct",
    "max_drawdown_pct",
)
PRICE_SHA256 = {
    "AMZN.json": "8c7a964f6220b745cafb1c55672cebd8735eee7282ad162fa095e4bf13b886be",
    "COIN.json": "94ca049b0c9f58eb457b32b4dcaa4eaa113df342370548e088dce6cff96658b5",
    "MSFT.json": "cb9ea811b22d69997947e4f416f9a9ed815db906bce64e56025b83aba3f3c6b3",
    "NFLX.json": "4bb40883ba169119eac1093d4826099e7124dfeb2432d1429c6e7da8b365ab8c",
    "TSLA.json": "9671c00a781703776f339316c03207f7503429bdd636bca800ccfcfa956c34b0",
    "TSLA_ablation.json": "f360ce8c19140b159daaf50c4561a228eb46a05d6b3f26e0e0182f79ca75ec87",
}

NOTEBOOK_TABLE_CELLS = {2: 15, 3: 17, 4: 18, 5: 16}
NOTEBOOK_MODEL_NAMES = {
    2: {
        "BuyHold": "buy_and_hold",
        "FinMe": "finmem",
        "Park": "generative_agents",
        "FinGPT": "fingpt",
        "A2C": "a2c",
        "PPO": "ppo",
        "DQN": "dqn",
    },
    3: {
        "BuyHold": "buy_and_hold",
        "ChatGPT3.5-Turbo": "gpt_3_5_turbo",
        "ChatGPT4": "gpt_4",
        "ChatGPT4-Turbo": "gpt_4_turbo",
        "davinci-003": "davinci_003",
        "Llama-70b-chat": "llama2_70b_chat",
    },
    4: {
        "BuyHold": "buy_and_hold",
        "Self Adaptive": "self_adaptive",
        "Risk Seeking": "risk_seeking",
        "Risk Averse": "risk_averse",
    },
    5: {
        "BuyHold": "buy_and_hold",
        "Top 1": "top_1",
        "Top 3": "top_3",
        "Top 5": "top_5",
        "Top 10": "top_10",
    },
}
NOTEBOOK_METRIC_NAMES = {
    "Cumulative Return": "cumulative_return_pct",
    "Sharpe Ratio": "sharpe_ratio",
    "Standard Deviation": "daily_volatility_pct",
    "Annualized Volatility": "annualized_volatility_pct",
    "Max Drawdown": "max_drawdown_pct",
}
PERCENT_METRICS = {
    "cumulative_return_pct",
    "daily_volatility_pct",
    "annualized_volatility_pct",
    "max_drawdown_pct",
}

# Each ablation action path survives in the public Git history at the pinned
# artifact commit. Buy-and-Hold is generated as an all-ones direction path.
HISTORICAL_ABLATION_ACTION_PATHS = {
    (3, "gpt_3_5_turbo"): "Visualize-metrics-test/LLM/dat_df_GPT3.5_turbo.csv",
    (3, "gpt_4"): "Visualize-metrics-test/LLM/TSLA_GPT4.csv",
    (3, "gpt_4_turbo"): "Visualize-metrics-test/LLM/Tsla_GPT4_turbo.csv",
    (3, "davinci_003"): "Visualize-metrics-test/LLM/dat_df_davicin003.csv",
    (3, "llama2_70b_chat"): "Visualize-metrics-test/LLM/dat_df_llama.csv",
    (4, "self_adaptive"): "Visualize-metrics-test/character/TSLA_Bi.csv",
    (4, "risk_seeking"): "Visualize-metrics-test/character/TSLA_seeking_V8.csv",
    (4, "risk_averse"): "Visualize-metrics-test/character/TSLA_averse_V6.csv",
    (5, "top_1"): "Visualize-metrics-test/Topk/TSLA_top1.csv",
    (5, "top_3"): "Visualize-metrics-test/Topk/TSLA_top3.csv",
    (5, "top_5"): "Visualize-metrics-test/Topk/TSLA_top5.csv",
    (5, "top_10"): "Visualize-metrics-test/Topk/TSLA_top10.csv",
}


# Transcribed from Tables 2--5 of the pinned official PDF. Rows contain:
# table|scope|strategy/configuration|cumulative return|Sharpe|daily volatility|
# annualized volatility|max drawdown.
PAPER_ROWS_TEXT = """
2|TSLA|buy_and_hold|-18.6312|-0.5410|4.4084|69.9818|55.3208
2|TSLA|finmem|61.7758|2.6789|2.9522|46.8649|10.7996
2|TSLA|generative_agents|13.4636|0.5990|2.8774|45.6774|24.3177
2|TSLA|fingpt|-7.4554|-0.2795|3.4145|54.2027|42.3993
2|TSLA|a2c|13.7067|0.3979|4.4096|70.0009|52.3308
2|TSLA|ppo|1.2877|0.0374|4.4110|70.0232|54.3264
2|TSLA|dqn|33.3393|0.9694|4.4027|69.8900|52.0033
2|NFLX|buy_and_hold|35.5111|1.4109|3.1964|50.7410|20.9263
2|NFLX|finmem|36.4485|2.0168|2.2951|36.4342|15.8495
2|NFLX|generative_agents|32.0058|1.5965|2.5460|40.4168|16.9893
2|NFLX|fingpt|9.0090|0.4266|2.6819|42.5732|28.2705
2|NFLX|a2c|14.6155|0.5788|3.2071|50.9112|25.0184
2|NFLX|ppo|8.4121|0.3330|3.2086|50.9344|25.0184
2|NFLX|dqn|-12.2067|-0.4833|3.2078|50.9217|28.7017
2|AMZN|buy_and_hold|-10.7739|-0.4980|2.7697|43.9674|33.6828
2|AMZN|finmem|4.8850|0.2327|2.6872|42.6576|22.9294
2|AMZN|generative_agents|-13.9271|-0.9981|1.7864|28.3576|27.7334
2|AMZN|fingpt|-29.6781|-2.1756|1.7464|27.7225|28.4838
2|AMZN|a2c|-6.3591|-0.2938|2.7706|43.9819|26.1275
2|AMZN|ppo|-8.4194|-0.3891|2.7702|43.9761|33.6828
2|AMZN|dqn|-29.9820|-1.3906|2.7603|43.8177|38.3740
2|MSFT|buy_and_hold|14.6949|0.8359|2.2326|35.4411|15.0097
2|MSFT|finmem|23.2613|1.4402|2.0512|32.5617|14.9889
2|MSFT|generative_agents|-18.1031|-1.6057|1.4318|22.7285|24.2074
2|MSFT|fingpt|5.7356|0.4430|1.6442|26.1008|12.8459
2|MSFT|a2c|0.4598|0.0261|2.2357|35.4913|23.6781
2|MSFT|ppo|12.8067|0.7282|2.2333|35.4532|19.5355
2|MSFT|dqn|14.7397|0.8385|2.2326|35.4408|25.1845
2|COIN|buy_and_hold|-30.0071|-0.5150|6.7517|107.1795|60.5084
2|COIN|finmem|34.9832|0.7170|5.6538|89.7515|35.7526
2|COIN|generative_agents|3.4627|0.0896|4.4783|71.0908|32.0957
2|COIN|fingpt|-88.7805|-1.9507|5.2736|83.7153|73.5774
3|TSLA_ablation|buy_and_hold|-66.9497|-2.0845|3.8050|60.4020|67.3269
3|TSLA_ablation|gpt_3_5_turbo|16.1501|2.1589|0.8862|14.0683|1.1073
3|TSLA_ablation|gpt_4|62.6180|2.2251|3.3339|52.9237|17.4012
3|TSLA_ablation|gpt_4_turbo|54.6958|2.4960|2.5960|41.2100|12.5734
3|TSLA_ablation|davinci_003|1.6308|0.8515|0.2269|3.6018|0.8408
3|TSLA_ablation|llama2_70b_chat|-52.7233|-2.8532|2.1891|34.7503|44.7168
4|TSLA_ablation|buy_and_hold|-66.9497|-2.0845|3.9527|3.8050|67.3269
4|TSLA_ablation|self_adaptive|54.6958|2.4960|2.7419|2.5960|12.5734
4|TSLA_ablation|risk_seeking|-19.4132|-0.7866|3.2722|2.9236|45.0001
4|TSLA_ablation|risk_averse|-12.4679|-1.5783|1.7744|0.9358|15.9882
5|TSLA_ablation|buy_and_hold|-66.9497|-2.0845|3.8050|60.4020|67.3269
5|TSLA_ablation|top_1|52.0936|1.8642|3.3105|52.5529|25.2355
5|TSLA_ablation|top_3|29.4430|1.1214|3.1105|49.3779|27.0972
5|TSLA_ablation|top_5|54.6958|2.4960|2.5960|41.2100|12.5734
5|TSLA_ablation|top_10|79.4448|2.7469|3.4262|54.3891|17.1360
"""


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


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def git_blob(root: Path, commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{path}"],
        check=True,
        capture_output=True,
    ).stdout


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_table_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in PAPER_ROWS_TEXT.strip().splitlines():
        values = line.split("|")
        if len(values) != 8:
            raise ValueError(f"Malformed paper result row: {line}")
        table, scope, strategy = values[:3]
        for metric, value in zip(METRICS, values[3:]):
            rows.append(
                {
                    "paper_table": int(table),
                    "scope": scope,
                    "strategy_or_configuration": strategy,
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    return rows


def load_adjusted_prices(path: Path) -> Tuple[np.ndarray, List[int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    adjusted = result["indicators"]["adjclose"][0]["adjclose"]
    paired = [(timestamp, price) for timestamp, price in zip(timestamps, adjusted) if price is not None]
    return (
        np.asarray([float(price) for _, price in paired], dtype=float),
        [int(timestamp) for timestamp, _ in paired],
    )


def source_buy_hold_metrics(prices: np.ndarray) -> Dict[str, float]:
    """Reproduce data-pipeline/07-metrics.py with all actions fixed to +1."""
    return source_action_metrics(prices, np.ones(len(prices), dtype=float))


def source_action_metrics(prices: np.ndarray, actions: np.ndarray) -> Dict[str, float]:
    """Reproduce the released signed-log-return metric path."""
    if len(actions) < len(prices) - 1:
        raise RuntimeError(
            f"Action path has {len(actions)} entries for {len(prices)} prices"
        )
    daily = np.diff(np.log(prices)) * actions[: len(prices) - 1]
    daily_std = float(np.std(daily, ddof=1))
    cumulative = float(np.sum(daily))
    annualized = daily_std * math.sqrt(252)
    sharpe = (cumulative / (len(prices) / 252)) / annualized

    # Preserve the released implementation: it compounds log returns as if they
    # were simple returns for the max-drawdown calculation.
    cumulative_path = np.cumprod(np.concatenate((np.asarray([1.0]), 1 + daily)))
    peaks = np.maximum.accumulate(cumulative_path)
    max_drawdown = float(np.max((peaks - cumulative_path) / peaks))
    return {
        "cumulative_return_pct": cumulative * 100,
        "sharpe_ratio": sharpe,
        "daily_volatility_pct": daily_std * 100,
        "annualized_volatility_pct": annualized * 100,
        "max_drawdown_pct": max_drawdown * 100,
    }


def historical_repository_audit(source_root: Path) -> Dict[str, Any]:
    shallow = git_text(source_root, "rev-parse", "--is-shallow-repository").strip()
    commit_count = int(git_text(source_root, "rev-list", "--all", "--count").strip())
    roots = git_text(source_root, "rev-list", "--max-parents=0", "--all").splitlines()
    paths = git_text(
        source_root,
        "ls-tree",
        "-r",
        "--name-only",
        HISTORICAL_ARTIFACT_COMMIT,
        "Visualize-metrics-test",
    ).splitlines()
    csv_paths = [path for path in paths if path.endswith(".csv")]
    deleted = [
        line.split("\t", 1)[1]
        for line in git_text(
            source_root,
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            HISTORICAL_DELETION_COMMIT,
            "--",
            "Visualize-metrics-test",
        ).splitlines()
        if line.startswith("D\t")
    ]
    notebook = git_blob(source_root, HISTORICAL_ARTIFACT_COMMIT, HISTORICAL_NOTEBOOK_PATH)
    metrics = git_blob(source_root, HISTORICAL_ARTIFACT_COMMIT, HISTORICAL_METRICS_PATH)
    checks = {
        "full_non_shallow_clone": shallow == "false",
        "reachable_commit_count": commit_count == EXPECTED_REACHABLE_COMMITS,
        "root_commit": roots == [SOURCE_ROOT_COMMIT],
        "historical_tree_file_count": len(paths) == EXPECTED_HISTORICAL_TREE_FILES,
        "historical_action_csv_count": len(csv_paths) == EXPECTED_HISTORICAL_ACTION_CSVS,
        "deletion_removed_entire_historical_tree": sorted(deleted) == sorted(paths),
        "notebook_sha256": hashlib.sha256(notebook).hexdigest()
        == HISTORICAL_NOTEBOOK_SHA256,
        "metrics_sha256": hashlib.sha256(metrics).hexdigest() == HISTORICAL_METRICS_SHA256,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Pinned FinMem Git history changed: {checks}")
    return {
        "is_shallow_repository": shallow == "true",
        "reachable_commits": commit_count,
        "root_commit": roots[0],
        "historical_artifact_commit": HISTORICAL_ARTIFACT_COMMIT,
        "historical_artifact_authored_at": git_text(
            source_root, "show", "-s", "--format=%aI", HISTORICAL_ARTIFACT_COMMIT
        ).strip(),
        "historical_tree_files": len(paths),
        "historical_action_csvs": len(csv_paths),
        "historical_notebook_path": HISTORICAL_NOTEBOOK_PATH,
        "historical_notebook_sha256": HISTORICAL_NOTEBOOK_SHA256,
        "historical_metrics_path": HISTORICAL_METRICS_PATH,
        "historical_metrics_sha256": HISTORICAL_METRICS_SHA256,
        "deletion_commit": HISTORICAL_DELETION_COMMIT,
        "deletion_authored_at": git_text(
            source_root, "show", "-s", "--format=%aI", HISTORICAL_DELETION_COMMIT
        ).strip(),
        "deleted_tree_files": len(deleted),
    }


def notebook_text_output(notebook: Mapping[str, Any], cell_index: int) -> str:
    outputs = notebook["cells"][cell_index].get("outputs", [])
    values = []
    for output in outputs:
        text = output.get("data", {}).get("text/plain", output.get("text", ""))
        if isinstance(text, list):
            text = "".join(text)
        if text:
            values.append(str(text))
    if len(values) != 1:
        raise RuntimeError(f"Expected one text output in notebook cell {cell_index}")
    value = values[0]
    if value.startswith(("'", '"')):
        value = ast.literal_eval(value)
    return value


def parse_notebook_author_outputs(source_root: Path) -> List[Dict[str, Any]]:
    notebook = json.loads(
        git_blob(source_root, HISTORICAL_ARTIFACT_COMMIT, HISTORICAL_NOTEBOOK_PATH)
    )
    values: Dict[Tuple[int, str, str, str], float] = {}
    for table, cell_index in NOTEBOOK_TABLE_CELLS.items():
        text = notebook_text_output(notebook, cell_index).replace("Buy & Hold", "BuyHold")
        lines = [line.strip() for line in text.splitlines()]
        if table == 2:
            for line in lines:
                parts = [part.strip().rstrip("\\") for part in line.split(" & ")]
                if len(parts) != 7 or parts[0] not in {"TSLA", "NFLX", "AMZN", "MSFT", "COIN"}:
                    continue
                scope, model = parts[:2]
                strategy = NOTEBOOK_MODEL_NAMES[table][model]
                for metric, raw in zip(METRICS, parts[2:]):
                    value = float(raw)
                    values[(table, scope, strategy, metric)] = (
                        value * 100 if metric in PERCENT_METRICS else value
                    )
        else:
            header = next(line for line in lines if line.startswith("Unnamed: 0 & "))
            models = [part.strip().rstrip("\\").strip() for part in header.split(" & ")[1:]]
            for line in lines:
                parts = [part.strip().rstrip("\\") for part in line.split(" & ")]
                if not parts or parts[0] not in NOTEBOOK_METRIC_NAMES:
                    continue
                metric = NOTEBOOK_METRIC_NAMES[parts[0]]
                for model, raw in zip(models, parts[1:]):
                    strategy = NOTEBOOK_MODEL_NAMES[table][model]
                    value = float(raw)
                    values[(table, "TSLA_ablation", strategy, metric)] = (
                        value * 100 if metric in PERCENT_METRICS else value
                    )

    targets = paper_table_rows()
    if len(values) != len(targets) or set(values) != {
        (
            row["paper_table"],
            row["scope"],
            row["strategy_or_configuration"],
            row["metric"],
        )
        for row in targets
    }:
        raise RuntimeError("Historical notebook does not cover every paper table cell")
    rows = []
    for target in targets:
        key = (
            target["paper_table"],
            target["scope"],
            target["strategy_or_configuration"],
            target["metric"],
        )
        notebook_value = values[key]
        error = abs(target["paper_value"] - notebook_value)
        if error <= DISPLAY_TOLERANCE:
            status = "author_output_exact_displayed_precision_match"
        elif error <= 0.0001001:
            status = "author_output_one_last_decimal_unit_difference"
        else:
            status = "paper_conflicts_with_preserved_author_output"
        rows.append(
            {
                **target,
                "historical_notebook_value": notebook_value,
                "absolute_error": error,
                "display_tolerance": DISPLAY_TOLERANCE,
                "status": status,
                "evidence_commit": HISTORICAL_ARTIFACT_COMMIT,
                "evidence_path": HISTORICAL_NOTEBOOK_PATH,
            }
        )
    return rows


def parse_action_csv(blob: bytes) -> Tuple[List[Tuple[datetime, int]], str]:
    rows = list(csv.DictReader(io.StringIO(blob.decode("utf-8-sig"))))
    if not rows:
        raise RuntimeError("Historical action CSV is empty")
    fields = set(rows[0])
    date_field = next((name for name in ("date", "dates") if name in fields), None)
    action_field = next(
        (name for name in ("direction", "action", "actions") if name in fields), None
    )
    if not date_field or not action_field:
        raise RuntimeError(f"Unknown historical action schema: {sorted(fields)}")
    parsed = []
    for row in rows:
        raw_date = row.get(date_field, "").strip()
        raw_action = row.get(action_field, "").strip()
        if not raw_date or not raw_action:
            continue
        parsed.append((datetime.strptime(raw_date, "%m/%d/%y"), int(float(raw_action))))
    return parsed, f"{date_field}+{action_field}"


def historical_action_inventory(source_root: Path) -> List[Dict[str, Any]]:
    paths = sorted(
        path
        for path in git_text(
            source_root,
            "ls-tree",
            "-r",
            "--name-only",
            HISTORICAL_ARTIFACT_COMMIT,
            "Visualize-metrics-test",
        ).splitlines()
        if path.endswith(".csv")
    )
    rows = []
    for path in paths:
        blob = git_blob(source_root, HISTORICAL_ARTIFACT_COMMIT, path)
        actions, schema = parse_action_csv(blob)
        rows.append(
            {
                "commit": HISTORICAL_ARTIFACT_COMMIT,
                "path": path,
                "sha256": hashlib.sha256(blob).hexdigest(),
                "parsed_action_rows": len(actions),
                "first_action_date": min(date for date, _ in actions).date().isoformat(),
                "last_action_date": max(date for date, _ in actions).date().isoformat(),
                "schema": schema,
                "direction_values": ",".join(
                    str(value) for value in sorted({value for _, value in actions})
                ),
            }
        )
    if len(rows) != EXPECTED_HISTORICAL_ACTION_CSVS:
        raise RuntimeError(f"Expected 18 historical action CSVs, found {len(rows)}")
    return rows


def historical_action_reproduction(
    source_root: Path, price_root: Path
) -> List[Dict[str, Any]]:
    prices, timestamps = load_adjusted_prices(price_root / "TSLA_ablation.json")
    trading_dates = [
        datetime.fromtimestamp(timestamp, timezone.utc).replace(tzinfo=None).date()
        for timestamp in timestamps
    ]
    first_date, last_date = min(trading_dates), max(trading_dates)
    action_cache: Dict[str, np.ndarray] = {}
    targets = [row for row in paper_table_rows() if row["paper_table"] in {3, 4, 5}]
    rows = []
    for target in targets:
        strategy = target["strategy_or_configuration"]
        path = HISTORICAL_ABLATION_ACTION_PATHS.get((target["paper_table"], strategy), "")
        if strategy == "buy_and_hold":
            actions = np.ones(len(prices), dtype=float)
            evidence = "synthetic_all_ones_buy_and_hold_path"
        else:
            if path not in action_cache:
                parsed, _ = parse_action_csv(
                    git_blob(source_root, HISTORICAL_ARTIFACT_COMMIT, path)
                )
                filtered = [
                    (date.date(), value)
                    for date, value in parsed
                    if first_date <= date.date() <= last_date
                ]
                action_dates = [date for date, _ in filtered]
                if action_dates != trading_dates:
                    raise RuntimeError(
                        f"Historical action dates do not align to Yahoo trading dates: {path}"
                    )
                action_cache[path] = np.asarray(
                    [value for _, value in filtered], dtype=float
                )
            actions = action_cache[path]
            evidence = f"{HISTORICAL_ARTIFACT_COMMIT}:{path}"
        computed = source_action_metrics(prices, actions)[target["metric"]]
        error = abs(target["paper_value"] - computed)
        rows.append(
            {
                **target,
                "recomputed_value": computed,
                "absolute_error": error,
                "display_tolerance": DISPLAY_TOLERANCE,
                "status": (
                    "historical_action_exact_displayed_precision_match"
                    if error <= DISPLAY_TOLERANCE
                    else "paper_conflicts_with_historical_action_replay"
                ),
                "evidence": evidence,
                "price_input": "TSLA_ablation.json",
                "price_input_sha256": PRICE_SHA256["TSLA_ablation.json"],
            }
        )
    return rows


def price_input_inventory(price_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, float]]]:
    inventory = []
    metrics: Dict[str, Dict[str, float]] = {}
    for filename, expected_hash in PRICE_SHA256.items():
        path = price_root / filename
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(f"Pinned Yahoo input hash mismatch for {filename}: {actual_hash}")
        prices, timestamps = load_adjusted_prices(path)
        scope = filename.removesuffix(".json")
        metrics[scope] = source_buy_hold_metrics(prices)
        inventory.append(
            {
                "scope": scope,
                "source": "Yahoo Finance chart API adjusted close",
                "query_period_start": "2022-06-16" if scope == "TSLA_ablation" else "2022-10-06",
                "query_period_end_exclusive": "2022-12-28" if scope == "TSLA_ablation" else "2023-04-10",
                "observations": len(prices),
                "first_unix_timestamp": min(timestamps),
                "last_unix_timestamp": max(timestamps),
                "first_adjusted_close": prices[0],
                "last_adjusted_close": prices[-1],
                "input_sha256": actual_hash,
                "retrieval_date": "2026-08-11",
                "interpretation": "current historical retrieval; not the unshipped original paper snapshot",
            }
        )
    return inventory, metrics


def table_conformance(price_metrics: Mapping[str, Mapping[str, float]]) -> List[Dict[str, Any]]:
    rows = []
    for target in paper_table_rows():
        source_value: Any = ""
        absolute_error: Any = ""
        if target["strategy_or_configuration"] == "buy_and_hold":
            source_value = price_metrics[target["scope"]][target["metric"]]
            absolute_error = abs(float(target["paper_value"]) - source_value)
            status = (
                "exact_displayed_precision_match"
                if absolute_error <= DISPLAY_TOLERANCE
                else "mismatch_against_pinned_2026_yahoo_retrieval"
            )
            evidence = "released_metric_formula_adapter_plus_pinned_current_yahoo_adjusted_close"
        else:
            status = "unverifiable_missing_native_action_series"
            evidence = "paper_value_only_no_shipped_checkpoint_action_path_or_trial_output"
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
    return rows


def volatility_identity_audit() -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[int, str, str], Dict[str, float]] = {}
    for row in paper_table_rows():
        key = (row["paper_table"], row["scope"], row["strategy_or_configuration"])
        grouped.setdefault(key, {})[row["metric"]] = row["paper_value"]
    output = []
    for (table, scope, strategy), values in grouped.items():
        implied = values["daily_volatility_pct"] * math.sqrt(252)
        error = abs(implied - values["annualized_volatility_pct"])
        output.append(
            {
                "paper_table": table,
                "scope": scope,
                "strategy_or_configuration": strategy,
                "paper_daily_volatility_pct": values["daily_volatility_pct"],
                "paper_annualized_volatility_pct": values["annualized_volatility_pct"],
                "daily_times_sqrt_252_pct": implied,
                "absolute_error": error,
                "status": (
                    "rounding_consistent"
                    if error <= 0.001
                    else "paper_internal_annualization_mismatch"
                ),
            }
        )
    return output


def archive_inventory(source_root: Path) -> List[Dict[str, Any]]:
    archive_path = source_root / "data-pipeline/Fake-Sample-Data.zip"
    rows = []
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            if info.is_dir() or info.filename.startswith("__MACOSX/") or info.filename.endswith(".DS_Store"):
                continue
            lowered = info.filename.lower()
            if "fake-news" in lowered:
                role = "synthetic_news_input_not_paper_data"
            elif lowered.endswith("filing_data.parquet"):
                role = "sample_filing_input_not_paper_data"
            elif lowered.endswith(("env_data.pkl", "filing_q.pkl", "filing_k.pkl", "news_fake.pkl", "price.pkl")):
                role = "sample_pipeline_output_not_agent_action_or_paper_result"
            else:
                role = "other_sample_artifact"
            rows.append(
                {
                    "archive": "data-pipeline/Fake-Sample-Data.zip",
                    "entry": info.filename,
                    "uncompressed_bytes": info.file_size,
                    "role": role,
                    "safe_inspection": "ZIP directory only; pickle payloads not executed",
                }
            )
    return rows


def source_config_audit(source_root: Path) -> List[Dict[str, Any]]:
    config = (source_root / "config/tsla_gpt_config.toml").read_text(encoding="utf-8")
    shell = (source_root / "run_opeai.sh").read_text(encoding="utf-8")
    chat = (source_root / "puppy/chat.py").read_text(encoding="utf-8")
    metrics = (source_root / "data-pipeline/07-metrics.py").read_text(encoding="utf-8")
    pyproject = (source_root / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (source_root / ".devcontainer/requirements.txt").read_text(encoding="utf-8")
    rows = (
        {
            "dimension": "main_backbone",
            "paper": "GPT-4-Turbo",
            "released": "gpt-3.5-turbo-0125",
            "status": "mismatch",
        },
        {
            "dimension": "main_top_k_per_layer",
            "paper": "5",
            "released": "3",
            "status": "mismatch",
        },
        {
            "dimension": "gpt_temperature",
            "paper": "0.7",
            "released": "omitted from GPT request payload",
            "status": "mismatch",
        },
        {
            "dimension": "main_ticker_configs",
            "paper": "TSLA,NFLX,AMZN,MSFT,COIN",
            "released": "TSLA only",
            "status": "incomplete",
        },
        {
            "dimension": "main_training_period",
            "paper": "2021-08-17 through 2022-10-05",
            "released": "commented example 2022-07-14 through 2022-07-20",
            "status": "mismatch",
        },
        {
            "dimension": "main_testing_period",
            "paper": "2022-10-06 through 2023-04-10",
            "released": "active example 2022-07-20 through 2022-08-01",
            "status": "mismatch",
        },
        {
            "dimension": "five_repeated_trials",
            "paper": "average of five trials",
            "released": "no trial driver, trial seeds, or trial outputs",
            "status": "missing",
        },
        {
            "dimension": "paper_input_snapshot",
            "paper": "Yahoo OHLCV, Alpaca/Benzinga news, SEC filings",
            "released": "fake Kaggle news sample and sample pipeline artifacts",
            "status": "missing_original_inputs",
        },
        {
            "dimension": "native_result_paths",
            "paper": "Tables 2--5 action paths and metrics",
            "released": "only .gitkeep placeholders in result/checkpoint directories",
            "status": "missing",
        },
        {
            "dimension": "metrics_entrypoint",
            "paper": "paper metric computation",
            "released": "undefined lowercase ticker, author-local paths, missing declared yfinance/pandas dependencies",
            "status": "not_operational_without_repair",
        },
        {
            "dimension": "risk_profile_selection",
            "paper": "report profile with highest test-period cumulative return",
            "released": "no three-profile evaluation driver or outputs",
            "status": "missing_and_test_selected",
        },
    )
    checks = {
        "config_model": 'model = "gpt-3.5-turbo-0125"' in config,
        "config_top_k": "top_k = 3" in config,
        "shell_test_start": "-st 2022-07-20" in shell,
        "shell_test_end": "-et 2022-08-01" in shell,
        "gpt_temperature_absent": '"temperature"' not in chat.split("else:")[-1],
        "metrics_ticker_bug": "yf.download(ticker," in metrics,
        "metrics_local_paths": "/Users/yuechenjiang/" in metrics,
        "yfinance_undeclared": "yfinance" not in pyproject and "yfinance" not in requirements,
        "pandas_undeclared": re.search(r"(^|\n)pandas([=<>]|\s)", requirements) is None
        and re.search(r"(^|\n)pandas\s*=", pyproject) is None,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Pinned FinMem source findings changed: {checks}")
    return list(rows)


def build_audit(
    source_root: Path,
    paper_path: Path,
    price_root: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    if sha256(paper_path) != PAPER_SHA256:
        raise RuntimeError("Official paper PDF hash does not match the pinned primary source")

    inventory, price_metrics = price_input_inventory(price_root)
    conformance = table_conformance(price_metrics)
    volatility = volatility_identity_audit()
    archive = archive_inventory(source_root)
    config = source_config_audit(source_root)
    history = historical_repository_audit(source_root)
    author_outputs = parse_notebook_author_outputs(source_root)
    action_inventory = historical_action_inventory(source_root)
    action_reproduction = historical_action_reproduction(source_root, price_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_2_5_conformance.csv", conformance, list(conformance[0]))
    write_csv(output_dir / "yahoo_buy_hold_input_inventory.csv", inventory, list(inventory[0]))
    write_csv(output_dir / "paper_volatility_identity_audit.csv", volatility, list(volatility[0]))
    write_csv(output_dir / "released_archive_inventory.csv", archive, list(archive[0]))
    write_csv(output_dir / "source_config_conformance.csv", config, list(config[0]))
    write_csv(
        output_dir / "historical_author_output_conformance.csv",
        author_outputs,
        list(author_outputs[0]),
    )
    write_csv(
        output_dir / "historical_action_inventory.csv",
        action_inventory,
        list(action_inventory[0]),
    )
    write_csv(
        output_dir / "historical_action_metric_reproduction.csv",
        action_reproduction,
        list(action_reproduction[0]),
    )

    matched = sum(row["status"] == "exact_displayed_precision_match" for row in conformance)
    mismatched = sum(row["status"].startswith("mismatch") for row in conformance)
    unverifiable = sum(row["status"].startswith("unverifiable") for row in conformance)
    volatility_mismatches = sum(
        row["status"] == "paper_internal_annualization_mismatch" for row in volatility
    )
    row_groups: Dict[Tuple[int, str, str], List[Mapping[str, Any]]] = {}
    for row in conformance:
        key = (row["paper_table"], row["scope"], row["strategy_or_configuration"])
        row_groups.setdefault(key, []).append(row)
    fully_matched_rows = sum(
        all(row["status"] == "exact_displayed_precision_match" for row in rows)
        for rows in row_groups.values()
    )
    mismatched_rows = sum(any(row["status"].startswith("mismatch") for row in rows) for rows in row_groups.values())
    unverifiable_rows = sum(
        all(row["status"].startswith("unverifiable") for row in rows)
        for rows in row_groups.values()
    )
    if (matched, mismatched, unverifiable) != (16, 24, 195):
        raise RuntimeError(
            "Pinned FinMem conformance counts changed: "
            f"matched={matched}, mismatched={mismatched}, unverifiable={unverifiable}"
        )
    if (fully_matched_rows, mismatched_rows, unverifiable_rows) != (2, 6, 39):
        raise RuntimeError("Pinned FinMem row-level conformance counts changed")
    if volatility_mismatches != 4:
        raise RuntimeError(f"Expected four Table 4 annualization mismatches, got {volatility_mismatches}")

    author_matched = sum(
        row["status"] == "author_output_exact_displayed_precision_match"
        for row in author_outputs
    )
    author_last_decimal = sum(
        row["status"] == "author_output_one_last_decimal_unit_difference"
        for row in author_outputs
    )
    author_conflicted = sum(
        row["status"] == "paper_conflicts_with_preserved_author_output"
        for row in author_outputs
    )
    action_matched = sum(
        row["status"] == "historical_action_exact_displayed_precision_match"
        for row in action_reproduction
    )
    action_conflicted = len(action_reproduction) - action_matched
    if (author_matched, author_last_decimal, author_conflicted) != (223, 4, 8):
        raise RuntimeError(
            "Pinned FinMem historical author-output counts changed: "
            f"matched={author_matched}, last_decimal={author_last_decimal}, "
            f"conflicted={author_conflicted}"
        )
    if (action_matched, action_conflicted) != (67, 8):
        raise RuntimeError(
            "Pinned FinMem historical action-replay counts changed: "
            f"matched={action_matched}, conflicted={action_conflicted}"
        )
    conflict_keys = {
        (row["paper_table"], row["strategy_or_configuration"], row["metric"])
        for row in author_outputs
        if row["status"] == "paper_conflicts_with_preserved_author_output"
    }
    if conflict_keys != {
        (4, strategy, metric)
        for strategy in ("buy_and_hold", "self_adaptive", "risk_seeking", "risk_averse")
        for metric in ("daily_volatility_pct", "annualized_volatility_pct")
    }:
        raise RuntimeError(f"Unexpected FinMem author-output conflicts: {conflict_keys}")

    result_dirs = [
        source_root / f"data/{index:02d}_{name}"
        for index, name in (
            (4, "model_output_log"),
            (5, "train_model_output"),
            (6, "train_checkpoint"),
            (7, "test_model_output"),
            (8, "test_checkpoint"),
            (9, "results"),
        )
    ]
    shipped_result_files = [
        path
        for directory in result_dirs
        for path in directory.glob("*")
        if path.is_file() and path.name != ".gitkeep"
    ]
    manifest: Dict[str, Any] = {
        "audit": "FinMem paper claims versus pinned public source history and price inputs",
        "overall_status": "author_outputs_partially_verified_not_end_to_end_reproduced",
        "full_paper_reproduced": False,
        "end_to_end_agent_result_cells_reproduced": 0,
        "paper_url": PAPER_URL,
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "paper_numeric_tables_audited": [2, 3, 4, 5],
        "paper_result_rows_total": len(row_groups),
        "paper_result_cells_total": len(conformance),
        "historical_author_output_cells_exact": author_matched,
        "historical_author_output_cells_one_last_decimal_unit_difference": author_last_decimal,
        "historical_author_output_cells_corroborated": author_matched + author_last_decimal,
        "historical_author_output_cells_conflicted_with_paper": author_conflicted,
        "historical_author_output_rows_all_cells_exact": 40,
        "historical_author_output_rows_corroborated": 43,
        "historical_author_output_rows_conflicted_with_paper": 4,
        "historical_action_metric_cells_recomputed": len(action_reproduction),
        "historical_action_metric_cells_matched": action_matched,
        "historical_action_metric_cells_conflicted_with_paper": action_conflicted,
        "historical_action_metric_rows_fully_matched": 11,
        "historical_action_metric_rows_conflicted_with_paper": 4,
        "buy_hold_cells_recomputed": matched + mismatched,
        "buy_hold_cells_matched": matched,
        "buy_hold_cells_mismatched_against_current_yahoo": mismatched,
        "current_head_non_buy_hold_cells_without_native_outputs": unverifiable,
        "non_buy_hold_cells_exact_in_historical_author_output": 185,
        "non_buy_hold_cells_corroborated_by_historical_author_output": 189,
        "paper_result_rows_fully_matched": fully_matched_rows,
        "paper_result_rows_mismatched_against_current_yahoo": mismatched_rows,
        "paper_result_rows_unverifiable": unverifiable_rows,
        "ablation_buy_hold_rows_fully_matched": 2,
        "main_table_buy_hold_rows_fully_matched": 0,
        "paper_table_4_annualization_identity_mismatches": volatility_mismatches,
        "paper_other_table_annualization_identity_mismatches": 0,
        "current_head_native_action_or_return_files_shipped": len(shipped_result_files),
        "historical_action_csvs_in_public_git_history": len(action_inventory),
        "historical_repository_audit": history,
        "native_training_checkpoints_shipped": False,
        "native_testing_checkpoints_shipped": False,
        "original_paper_news_filings_snapshot_shipped": False,
        "fake_sample_archive_is_paper_input": False,
        "paper_main_backbone": "GPT-4-Turbo",
        "source_only_gpt_config_model": "gpt-3.5-turbo-0125",
        "paper_main_top_k": 5,
        "source_only_gpt_config_top_k": 3,
        "paper_gpt_temperature": 0.7,
        "source_gpt_temperature": "omitted",
        "paper_repeated_trials": 5,
        "source_trial_seeds_shipped": False,
        "paper_selects_best_risk_profile_on_test_outcome": True,
        "source_metrics_entrypoint_operational_as_released": False,
        "paper_metric_is_self_financing_portfolio_return": False,
        "paper_metric_interpretation": (
            "sum of next-day log returns multiplied by daily buy/sell/hold direction; "
            "no transaction costs and no cash/NAV accounting"
        ),
        "interpretation": (
            "The full public Git history preserves an executed notebook that corroborates "
            "227/235 displayed paper cells (223 exact and four differing by one last-decimal "
            "unit) and 18 dated action CSVs. "
            "Replaying the ablation actions "
            "against a hash-pinned Yahoo response independently reproduces 67/75 displayed "
            "Table 3--5 cells. The remaining eight are both Table 4 volatility columns: they "
            "conflict with the preserved author output, the replayed metrics, and the paper's "
            "annualization identity. This is strong paper-output lineage but not an end-to-end "
            "FinMem rerun: the original inputs, memories, complete five-trial outputs, and exact "
            "paper configuration remain absent from the current public tree."
        ),
        "source_file_sha256": {
            name: sha256(source_root / name)
            for name in (
                "README.md",
                "config/tsla_gpt_config.toml",
                "data-pipeline/07-metrics.py",
                "data-pipeline/Fake-Sample-Data.zip",
                "poetry.lock",
                "puppy/agent.py",
                "puppy/chat.py",
                "puppy/portfolio.py",
                "run.py",
                "run_opeai.sh",
            )
        },
        "external_price_input_sha256": PRICE_SHA256,
    }

    report = f"""# FinMem paper-level conformance audit

Overall verdict: **strong author-output verification, not an end-to-end reproduction**.
The current tree omits the paper outputs, but its full public Git history preserves an
executed metrics notebook and 18 dated action CSVs. The original five-stock inputs,
trained memories, complete five-trial paths, and exact paper configuration remain absent.

## Primary sources

- Official paper: {PAPER_URL} (SHA-256 `{PAPER_SHA256}`).
- Public source: {SOURCE_URL}, commit `{commit}`.
- Historical author-output snapshot: commit `{HISTORICAL_ARTIFACT_COMMIT}`
  (2023-11-30), deleted from the current tree by commit
  `{HISTORICAL_DELETION_COMMIT}` (2024-02-09).

## What is genuinely verified or reproduced

- The hash-pinned executed notebook provides machine-readable author outputs for all
  235 displayed metric cells. It matches {author_matched}/235 cells exactly and four
  more within one unit of the paper's last printed decimal, corroborating 227/235.
  The eight substantive disagreements are exactly the daily- and annualized-volatility
  entries for all four Table 4 rows.
- Independently applying the released metric code to the historical dated action CSVs
  and a hash-pinned Yahoo response reproduces {action_matched}/75 displayed cells in
  Tables 3--5. Tables 3 and 5 match completely (55/55); Table 4 matches cumulative
  return, Sharpe, and drawdown (12/20) but conflicts on the same eight volatility cells.
- This is stronger than paper-value transcription: it connects the paper values to
  author-shipped outputs and independently replays the ablation metric path. It is
  still not an end-to-end rerun of FinMem's LLM decisions or five repeated trials.

- The released metric formulas and a hash-pinned Yahoo adjusted-close retrieval
  reproduce the full five-metric TSLA Buy-and-Hold row exactly at four decimals for
  the ablation period (2022-06-16 to 2022-12-28) in both Tables 3 and 5.
- Across all repeated Buy-and-Hold cells in Tables 2--5, {matched}/40 match and
  {mismatched}/40 differ. The five main Table 2 rows use the paper's stated dates,
  but none fully matches the 2026 Yahoo retrieval; these are input-snapshot
  mismatches, not proof that the authors' unavailable historical snapshot was wrong.
- The exact ablation match establishes fidelity of the adapter to the released
  signed-log-return, volatility, Sharpe, and drawdown implementation. It does not
  establish an LLM-agent result.

## Why this is not a complete FinMem rerun

- The current result/checkpoint directories contain only placeholders. Public history
  supplies action paths and outputs, but does not identify five complete trial paths,
  their seeds, or the averaging lineage claimed by the paper.
- The paper's main configuration is GPT-4-Turbo, temperature 0.7, top-K=5, and five
  tickers. The only released GPT config is TSLA with GPT-3.5-Turbo-0125, omitted GPT
  temperature, and top-K=3. No configs exist for NFLX, AMZN, MSFT, or COIN.
- The paper trains from 2021-08-17 to 2022-10-05 and tests from 2022-10-06 to
  2023-04-10. The active shell example tests 2022-07-20 to 2022-08-01, and its
  required TSLA input/checkpoint files are absent.
- The paper's Alpaca/Benzinga news, SEC filings, and exact Yahoo snapshot are not
  released. `Fake-Sample-Data.zip` explicitly contains Kaggle-derived fake news and
  sample pipeline objects, not paper inputs or agent outputs; pickle payloads were
  inventoried without execution.
- The metrics script is not directly operational: it references an undefined
  lowercase ticker, hard-codes author-local result paths, and uses yfinance/pandas
  without declaring them in either locked environment file.
- The paper averages five repeated trials but provides no seeds or trial paths. It
  also reports whichever of three risk profiles has the highest cumulative return
  on the test period, an outcome-selected figure rather than a prespecified profile.

## Metric and paper consistency boundary

- The paper's "Cumulative Return" is the sum of daily log returns multiplied by
  each day's direction (-1/0/+1). It has no transaction costs, cash balance, or
  self-financing NAV, so it should be interpreted as a signed-return score rather
  than conventional cumulative portfolio return.
- Table 4's four annualized-volatility cells fail the paper's own identity,
  annualized volatility = daily volatility times sqrt(252). More decisively, all eight
  Table 4 volatility entries disagree with both the preserved author notebook and the
  independent action replay. All {len(volatility) - volatility_mismatches} corresponding
  rows in Tables 2, 3, and 5 are rounding-consistent.

Run `scripts/audit_finmem_paper.py` to regenerate this package. Use `--strict` when
a CI failure is desired until native paper action paths and original inputs exist.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "FINMEM_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/finmem_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "FINMEM_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/finmem_paper.pdf",
            )
        ),
    )
    parser.add_argument(
        "--price-root",
        type=Path,
        default=Path(
            os.environ.get(
                "FINMEM_YAHOO_PRICE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/finmem_yahoo_prices",
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/finmem",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(),
        args.paper_pdf.resolve(),
        args.price_root.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and manifest["overall_status"] != "reproduced")


if __name__ == "__main__":
    sys.exit(main())
