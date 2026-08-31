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
import contextlib
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
import tarfile
import tempfile
import warnings
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
from pypdf import PdfReader


SOURCE_COMMIT = "be814aa47970de9bf2fdd6a1d5a60ae5cf361b46"
SOURCE_ROOT_COMMIT = "85028214b043b38508d07587d01820324503d69a"
HISTORICAL_ARTIFACT_COMMIT = "0b7f499e556668bf49885fd8836efe85ef51558f"
HISTORICAL_DELETION_COMMIT = "45169ea8509c29113c7e7945dc52a6b3e43521eb"
HISTORICAL_NOTEBOOK_PATH = "Visualize-metrics-test/metrics.ipynb"
HISTORICAL_NOTEBOOK_SHA256 = "3096d6a67336270b5b820bd92408733b641abe73edaf04fa9215ec36d3fcf6dc"
HISTORICAL_METRICS_PATH = "Visualize-metrics-test/metrics.py"
HISTORICAL_METRICS_SHA256 = "ffec58d7bdc4b9e94e9bdcf2205c98ab9bef27ce8ddb95e377e154efeae15f21"
HISTORICAL_MAIN_OUTPUT_SHA256 = {
    3: "85f523f7c53c5b949ed981b844b2509ad42326a1c9e48357fe726618ab2cfbe2",
    4: "15f13301c590546bb7d35abba8f7e9f3d15c1d168ea97607f686c3cfdcaf0b2d",
    5: "bdefc696e07efb74cb66a78d6818006ff336b8be9cefb42f09e3298d517822c1",
}
EXPECTED_REACHABLE_COMMITS = 55
EXPECTED_REACHABLE_OBJECTS = 336
EXPECTED_REACHABLE_BLOBS = 171
EXPECTED_REACHABLE_TREES = 110
EXPECTED_HISTORICAL_TREE_FILES = 33
EXPECTED_HISTORICAL_ACTION_CSVS = 18
HISTORICAL_NOTEBOOK_BLOB = "3bd4a5557828c56fb8467617cb56a0c87915ce9f"
PAPER_SHA256 = "acb7527d02871cfad7d2754314b9a803f917b326847a456579df9cf7b0a648b9"
PAPER_URL = "https://arxiv.org/pdf/2311.13743"
SOURCE_URL = "https://github.com/pipiku915/finmem-llm-stocktrading"
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
# GitHub REST reported 192 forks on the census date. GraphQL could enumerate
# 181 accessible fork repositories and all 187 of their branch refs. The
# eleven-repository gap is retained explicitly; deleted, private, or otherwise
# unavailable repositories are not represented as inspected.
PUBLIC_FORK_REST_COUNT = 192
PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT = 181
PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT = 187
PUBLIC_FORK_GRAPHQL_REF_SHA256 = "cdf4678580ceb1e0bb3b3b2757a111ed56ef806a78c021737c8aba09bedb229e"
PUBLIC_FORK_SNAPSHOT_SHA256 = "4cb2de423df779cf6b863de9bc8884c5d10b5df651d51c15b9aae4fa8d12749c"
PUBLIC_FORK_REPRESENTATIVE_REF_COUNT = 20
PUBLIC_FORK_REPRESENTATIVE_REF_SHA256 = "37d1917c35228b8fea949c20adc9943e5d363acdd9db803529ed425eb23bd0ba"
PUBLIC_FORK_UNIQUE_HEAD_SHA256 = "5a9d435698b065bda0b68327a3dd2255e30d6116c9f46899076985140662b324"
PUBLIC_FORK_BASE_REACHABLE_HEAD_COUNT = 9
PUBLIC_FORK_DIVERGENT_HEAD_COUNT = 11
PUBLIC_FORK_DIVERGENT_SURFACE_SHA256 = "eca265fe2031aa49ca7fca7214c9c9eb898245000b9e4889884890ed95feee2d"
PUBLIC_FORK_DIVERGENT_COMMIT_COUNT = 45
PUBLIC_FORK_DIVERGENT_COMMIT_SHA256 = "f70a95b9ae6bc50c1b0b1ee40276d3e3f38fb7156f8f7574449779b5f4189b4f"
PUBLIC_FORK_DIVERGENT_PATH_COUNT = 299
PUBLIC_FORK_DIVERGENT_PATH_SHA256 = "8f00f9a5bf429b24e9bdc6983b41b9eeb08367a4542c6b68807dc055d32670ae"
OFFICIAL_SOURCE_AUTHOR_EMAILS = {
    "54829669+pipiku915@users.noreply.github.com",
    "57229766+Carolyn-Jiang@users.noreply.github.com",
    "hli113@stevens.edu",
}
OFFICIAL_SOURCE_AUTHOR_NAMES = {"Shirley Yu", "Haohang Li", "Yuechen Jiang"}
EXPECTED_DIVERGENT_AUTHOR_EMAILS = {
    "63671735+adamd1985@users.noreply.github.com",
    "adomenech@izertis.com",
    "cjie2399@usc.edu",
    "esiebomaj@gmail.com",
    "fateamjp@yahoo.co.jp",
    "goseng123@gmail.com",
    "gquiroga@dc.uba.ar",
    "irfanilgin@gmail.com",
    "jzljohn18@gmail.com",
    "letiennn41@gmail.com",
}
FORK_MINIRUN_HEAD = "cf3f751faaf103ac871301e0b05d2e9919f5f269"
FORK_CHECKPOINT_HEAD = "d60e7e048849860db8c459c3abb9b578373a9289"
FORK_MINIRUN_CONFIG_SHA256 = "53c5e4de08986fc1bd608aad2d0f176445829cd61ef584e1ff2011715209e107"
FORK_MINIRUN_ACTION_SHA256 = "f5fea23964dd8a3f48eb40f783ff708a1352a543d7fa40797aef90dfd34d789e"
FORK_CHECKPOINT_CONFIG_SHA256 = "642f892206cb5a8c9966a396c093d9dd091b985c28e66afd55f51337d3546889"

# Human review is encoded as a fail-closed classification only after the full
# commit/path surface above is validated. Every entry is post-paper and has no
# public identity match to the authors observed in the official source history.
DIVERGENT_FORK_FINDINGS: Mapping[str, Mapping[str, Any]] = {
    "0236c632e6634b960f02b16646e682e518bb0fbc": {
        "commits": 17,
        "paths": 19,
        "classification": "unattributed_postpaper_data_pipeline_extension",
    },
    "13a00873e78ca0f67ee0a0ac01bea60a5623c133": {
        "commits": 3,
        "paths": 16,
        "classification": "unattributed_postpaper_crypto_adaptation",
    },
    "16f2752d3f86415a1375fb82671c2db38a3dbd36": {
        "commits": 1,
        "paths": 1,
        "classification": "unattributed_postpaper_source_only_change",
    },
    "1dbc0d816789547a5c713caa6c7a40b83a02cb04": {
        "commits": 3,
        "paths": 133,
        "classification": "unattributed_postpaper_modular_rewrite_placeholders_only",
    },
    "21b1a5bd91ac7d0e1fd14e34acdd2dff9b7bc7f9": {
        "commits": 9,
        "paths": 25,
        "classification": "unattributed_postpaper_csv_writer_code_without_output",
    },
    "3b30f241a01db86c4c1c62b361c879d30717d42e": {
        "commits": 2,
        "paths": 2,
        "classification": "unattributed_postpaper_environment_only_change",
    },
    "51428f385640e9ec42b2797a44ae1d6193af42ce": {
        "commits": 4,
        "paths": 8,
        "classification": "unattributed_postpaper_commodity_adaptation",
    },
    "afef9c5c886bafc322483151eaf4aeafe14a48ee": {
        "commits": 2,
        "paths": 2,
        "classification": "unattributed_postpaper_build_only_change",
    },
    FORK_MINIRUN_HEAD: {
        "commits": 2,
        "paths": 73,
        "classification": "unattributed_postpaper_tsla_hold_only_minirun_wrong_model_dates_topk",
    },
    FORK_CHECKPOINT_HEAD: {
        "commits": 2,
        "paths": 154,
        "classification": "unattributed_postpaper_tsla_checkpoint_without_action_or_metric_output",
    },
    "fd352f7e86d28b7427b8f71211c5fcbd910589a0": {
        "commits": 2,
        "paths": 20,
        "classification": "unattributed_postpaper_incomplete_fake_amzn_baseline_input",
    },
}
PAPER_VERSIONS: Mapping[str, Mapping[str, Any]] = {
    "v1": {
        "submitted_at": "2023-11-23T00:24:40Z",
        "pdf_sha256": "a7b67bc4a2c2ffe9d7428ce12c230fb9e8760269488016b560700a474aa4f293",
        "pdf_bytes": 7_573_802,
        "pdf_pages": 22,
        "table_4_pdf_page": 17,
        "source_sha256": "b767e14d10dcccf6881ecfd71346f2f8baff77debce97713ebd3c70421e926f9",
        "source_archive_bytes": 17_012_431,
        "source_entries": 33,
        "source_files": 32,
        "source_uncompressed_bytes": 18_976_429,
    },
    "v2": {
        "submitted_at": "2023-12-03T16:18:55Z",
        "pdf_sha256": PAPER_SHA256,
        "pdf_bytes": 7_799_225,
        "pdf_pages": 22,
        "table_4_pdf_page": 18,
        "source_sha256": "62888b9c2ca94b531bdfff66fb44fe7c361bd46f2154b1d2a7d82f603ffb3ff2",
        "source_archive_bytes": 20_438_499,
        "source_entries": 40,
        "source_files": 39,
        "source_uncompressed_bytes": 22_789_668,
    },
}
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

TABLE_4_STRATEGIES = (
    "buy_and_hold",
    "self_adaptive",
    "risk_seeking",
    "risk_averse",
)
TABLE_4_V1_RAW = {
    "daily_volatility_pct": (0.039527, 0.027419, 0.032722, 0.017744),
    "annualized_volatility_pct": (0.038050, 0.025960, 0.029236, 0.009358),
}
TABLE_4_V2_PERCENT = {metric: tuple(value * 100 for value in values) for metric, values in TABLE_4_V1_RAW.items()}
SEPARATE_TSLA_FULL_DAILY_PERCENT = {
    "buy_and_hold": 3.9527,
    "self_adaptive": 2.7419,
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


def _sha256_lines(lines: Sequence[str]) -> str:
    return hashlib.sha256("".join(f"{line}\n" for line in lines).encode("utf-8")).hexdigest()


def git_object_exists(root: Path, object_spec: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", object_spec],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


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
        raise RuntimeError(f"Action path has {len(actions)} entries for {len(prices)} prices")
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
    object_ids = [
        line.split(" ", 1)[0] for line in git_text(source_root, "rev-list", "--objects", "--all").splitlines()
    ]
    object_types = subprocess.run(
        ["git", "-C", str(source_root), "cat-file", "--batch-check=%(objecttype)"],
        input="\n".join(object_ids) + "\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    object_counts = {kind: object_types.count(kind) for kind in ("blob", "tree", "commit")}
    unreachable = subprocess.run(
        ["git", "-C", str(source_root), "fsck", "--full", "--no-reflogs", "--unreachable"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
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
        "reachable_object_count": len(object_ids) == EXPECTED_REACHABLE_OBJECTS,
        "reachable_blob_count": object_counts["blob"] == EXPECTED_REACHABLE_BLOBS,
        "reachable_tree_count": object_counts["tree"] == EXPECTED_REACHABLE_TREES,
        "reachable_object_commit_count": object_counts["commit"] == EXPECTED_REACHABLE_COMMITS,
        "no_unreachable_objects": not unreachable,
        "root_commit": roots == [SOURCE_ROOT_COMMIT],
        "historical_tree_file_count": len(paths) == EXPECTED_HISTORICAL_TREE_FILES,
        "historical_action_csv_count": len(csv_paths) == EXPECTED_HISTORICAL_ACTION_CSVS,
        "deletion_removed_entire_historical_tree": sorted(deleted) == sorted(paths),
        "notebook_sha256": hashlib.sha256(notebook).hexdigest() == HISTORICAL_NOTEBOOK_SHA256,
        "metrics_sha256": hashlib.sha256(metrics).hexdigest() == HISTORICAL_METRICS_SHA256,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Pinned FinMem Git history changed: {checks}")
    return {
        "is_shallow_repository": shallow == "true",
        "reachable_commits": commit_count,
        "reachable_objects": len(object_ids),
        "reachable_blobs": object_counts["blob"],
        "reachable_trees": object_counts["tree"],
        "unreachable_objects": len(unreachable),
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
        "deletion_authored_at": git_text(source_root, "show", "-s", "--format=%aI", HISTORICAL_DELETION_COMMIT).strip(),
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
    notebook = json.loads(git_blob(source_root, HISTORICAL_ARTIFACT_COMMIT, HISTORICAL_NOTEBOOK_PATH))
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
                    values[(table, scope, strategy, metric)] = value * 100 if metric in PERCENT_METRICS else value
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


def paper_version_audit(
    version_root: Path,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Pin both official arXiv PDFs and their matching TeX source archives."""
    version_rows: List[Dict[str, Any]] = []
    source_rows: List[Dict[str, Any]] = []
    equation = (
        r"\textbf{Annum-Volatility} &= \textbf{Daily Volatility} "
        r"\times \sqrt{252}"
    )
    tex_table_rows = {
        "v1": (
            r"\textbf{Daily Volatility} & 0.039527 & 0.027419 & 0.032722 & \textbf{0.017744} \\ ".rstrip(),
            r"\textbf{Annualized Volatility} & 0.038050 & 0.025960 & 0.029236 & \textbf{0.009358} \\ ".rstrip(),
        ),
        "v2": (
            r"\textbf{Daily Volatility (\%)} & 3.9527 & 2.7419 & 3.2722 & \textbf{1.7744} \\ ".rstrip(),
            r"\textbf{Annualized Volatility (\%)} & 3.8050 & 2.5960 & 2.9236 & \textbf{0.9358} \\ ".rstrip(),
        ),
    }
    pdf_markers = {
        "v1": ("0.039527 0.027419 0.032722 0.017744", "0.038050 0.025960 0.029236 0.009358"),
        "v2": ("3.9527 2.7419 3.2722 1.7744", "3.8050 2.5960 2.9236 0.9358"),
    }
    for version, expected in PAPER_VERSIONS.items():
        pdf_path = version_root / f"paper_{version}.pdf"
        archive_path = version_root / f"source_{version}.tar"
        extracted_root = version_root / f"source_{version}"
        reader = PdfReader(pdf_path)
        table_page = int(expected["table_4_pdf_page"])
        table_text = reader.pages[table_page - 1].extract_text() or ""
        checks = {
            "pdf_sha256": sha256(pdf_path) == expected["pdf_sha256"],
            "pdf_bytes": pdf_path.stat().st_size == expected["pdf_bytes"],
            "pdf_pages": len(reader.pages) == expected["pdf_pages"],
            "table_4_pdf_text": all(marker in table_text for marker in pdf_markers[version]),
            "source_sha256": sha256(archive_path) == expected["source_sha256"],
            "source_archive_bytes": archive_path.stat().st_size == expected["source_archive_bytes"],
        }
        with tarfile.open(archive_path, "r:*") as archive:
            members = archive.getmembers()
            files = [member for member in members if member.isfile()]
            checks.update(
                {
                    "source_entries": len(members) == expected["source_entries"],
                    "source_files": len(files) == expected["source_files"],
                    "source_uncompressed_bytes": sum(member.size for member in files)
                    == expected["source_uncompressed_bytes"],
                }
            )
            for member in sorted(files, key=lambda item: item.name):
                stream = archive.extractfile(member)
                if stream is None:
                    raise RuntimeError(f"Cannot read {version} source member {member.name}")
                payload = stream.read()
                extracted = extracted_root / member.name
                if not extracted.is_file() or extracted.read_bytes() != payload:
                    raise RuntimeError(f"Extracted {version} source differs from archive: {member.name}")
                if member.name == "templateArxiv.tex":
                    role = "paper_primary_tex"
                elif member.name.lower().endswith((".bib", ".bbl")):
                    role = "paper_bibliography"
                elif member.name.lower().endswith((".png", ".jpg", ".jpeg", ".pdf")):
                    role = "paper_figure_asset"
                elif member.name.lower().endswith((".sty", ".cls")):
                    role = "paper_style_asset"
                else:
                    role = "paper_source_support_file"
                source_rows.append(
                    {
                        "version": version,
                        "path": member.name,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "uncompressed_bytes": member.size,
                        "role": role,
                    }
                )
        tex = (extracted_root / "templateArxiv.tex").read_text(encoding="utf-8")
        checks["annualization_equation_in_tex"] = equation in tex
        checks["table_4_values_in_tex"] = all(row in tex for row in tex_table_rows[version])
        if not all(checks.values()):
            raise RuntimeError(f"Pinned FinMem arXiv {version} sources changed: {checks}")
        version_rows.append(
            {
                "version": version,
                "submitted_at": expected["submitted_at"],
                "pdf_sha256": expected["pdf_sha256"],
                "pdf_bytes": expected["pdf_bytes"],
                "pdf_pages": expected["pdf_pages"],
                "source_archive_sha256": expected["source_sha256"],
                "source_archive_bytes": expected["source_archive_bytes"],
                "source_entries": expected["source_entries"],
                "source_files": expected["source_files"],
                "source_uncompressed_bytes": expected["source_uncompressed_bytes"],
                "table_4_pdf_page": table_page,
                "table_4_page_visually_inspected": "yes",
                "table_4_values_verified_in_pdf_text": "yes",
                "table_4_values_verified_in_primary_tex": "yes",
                "annualization_equation_verified_in_primary_tex": "yes",
                "table_4_revision_status": "same_numeric_values_retained_across_v1_and_v2",
            }
        )
    return version_rows, source_rows


def table_4_volatility_forensics(
    source_root: Path,
    author_outputs: Sequence[Mapping[str, Any]],
    action_reproduction: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Trace each disputed Table 4 cell through every reachable source blob."""
    notebook = json.loads(git_blob(source_root, HISTORICAL_ARTIFACT_COMMIT, HISTORICAL_NOTEBOOK_PATH))
    character_text = notebook_text_output(notebook, 18)
    separate_text = notebook_text_output(notebook, 19)
    required_character = (
        "Standard Deviation & 0.038050 & 0.025960 & 0.029236 & 0.009358",
        "Annualized Volatility & 0.604020 & 0.412100 & 0.464112 & 0.148557",
    )
    required_separate = (
        "Standard Deviation & 0.039527 & 0.027419 & 0.031453 & 0.039521 & 0.039521 & 0.039382",
        "Annualized Volatility & 0.627470 & 0.435264 & 0.499305 & 0.627370 & 0.627374 & 0.625173",
        "Cumulative Return & 0.181865 & 0.989811 & 0.103947 & 0.230767 & 0.228670 & 0.701477",
        "Sharpe Ratio & 4.601053 & 36.099395 & 3.304806 & 5.839171 & 5.786047 & 17.812020",
    )
    if not all(fragment in character_text for fragment in required_character):
        raise RuntimeError("Historical character output changed")
    if not all(fragment in separate_text for fragment in required_separate):
        raise RuntimeError("Historical separate TSLA-full output changed")

    notebook_blob = git_text(
        source_root,
        "rev-parse",
        f"{HISTORICAL_ARTIFACT_COMMIT}:{HISTORICAL_NOTEBOOK_PATH}",
    ).strip()
    if notebook_blob != HISTORICAL_NOTEBOOK_BLOB:
        raise RuntimeError(f"Historical notebook blob changed: {notebook_blob}")
    notebook_history = git_text(
        source_root,
        "log",
        "--all",
        "--follow",
        "--format=%H",
        "--",
        HISTORICAL_NOTEBOOK_PATH,
    ).splitlines()
    historical_notebook_blobs = set()
    for commit in notebook_history:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(source_root),
                "ls-tree",
                commit,
                "--",
                HISTORICAL_NOTEBOOK_PATH,
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if result:
            historical_notebook_blobs.add(result.split()[2])
    if historical_notebook_blobs != {HISTORICAL_NOTEBOOK_BLOB}:
        raise RuntimeError(f"Expected one historical notebook blob, found {historical_notebook_blobs}")

    object_lines = git_text(source_root, "rev-list", "--objects", "--all").splitlines()
    object_ids = [line.split(" ", 1)[0] for line in object_lines]
    types = subprocess.run(
        ["git", "-C", str(source_root), "cat-file", "--batch-check=%(objecttype)"],
        input="\n".join(object_ids) + "\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    blob_ids = [oid for oid, kind in zip(object_ids, types) if kind == "blob"]
    if len(blob_ids) != EXPECTED_REACHABLE_BLOBS:
        raise RuntimeError(f"Expected 171 reachable blobs, found {len(blob_ids)}")
    literals = {f"{value:.6f}" for values in TABLE_4_V1_RAW.values() for value in values}
    hits: Dict[str, List[str]] = {literal: [] for literal in literals}
    for blob_id in blob_ids:
        payload = subprocess.run(
            ["git", "-C", str(source_root), "cat-file", "blob", blob_id],
            check=True,
            capture_output=True,
        ).stdout
        for literal in literals:
            if literal.encode() in payload:
                hits[literal].append(blob_id)
    expected_hits = {
        "0.039527": [HISTORICAL_NOTEBOOK_BLOB],
        "0.027419": [HISTORICAL_NOTEBOOK_BLOB],
        "0.032722": [],
        "0.017744": [],
        "0.038050": [HISTORICAL_NOTEBOOK_BLOB],
        "0.025960": [HISTORICAL_NOTEBOOK_BLOB],
        "0.029236": [HISTORICAL_NOTEBOOK_BLOB],
        "0.009358": [HISTORICAL_NOTEBOOK_BLOB],
    }
    if hits != expected_hits:
        raise RuntimeError(f"FinMem Table 4 reachable-blob findings changed: {hits}")

    author_index = {
        (row["strategy_or_configuration"], row["metric"]): row for row in author_outputs if row["paper_table"] == 4
    }
    action_index = {
        (row["strategy_or_configuration"], row["metric"]): row for row in action_reproduction if row["paper_table"] == 4
    }
    rows: List[Dict[str, Any]] = []
    for metric in ("daily_volatility_pct", "annualized_volatility_pct"):
        for index, strategy in enumerate(TABLE_4_STRATEGIES):
            paper_raw = TABLE_4_V1_RAW[metric][index]
            paper_percent = TABLE_4_V2_PERCENT[metric][index]
            native = float(author_index[(strategy, metric)]["historical_notebook_value"])
            native_daily = float(author_index[(strategy, "daily_volatility_pct")]["historical_notebook_value"])
            replay = float(action_index[(strategy, metric)]["recomputed_value"])
            literal = f"{paper_raw:.6f}"
            if metric == "annualized_volatility_pct":
                relation = "paper_annualized_cell_equals_preserved_character_daily_value"
                reason = (
                    "Published annualized value exactly equals the native character-output "
                    "daily volatility; it is not daily volatility multiplied by sqrt(252)."
                )
            elif strategy in SEPARATE_TSLA_FULL_DAILY_PERCENT:
                relation = "paper_daily_cell_matches_separate_tsla_full_output_value"
                reason = (
                    "Published daily value appears in a separate TSLA-full notebook output "
                    "whose return and Sharpe values show it is a different experiment."
                )
            else:
                relation = "paper_only_value_absent_from_all_reachable_source_blobs"
                reason = (
                    "Published daily value is absent from all 171 reachable public source "
                    "blobs; this bounded finding does not exclude unavailable private artifacts."
                )
            rows.append(
                {
                    "strategy_or_configuration": strategy,
                    "metric": metric,
                    "paper_v1_raw_value": paper_raw,
                    "paper_v2_percent_value": paper_percent,
                    "preserved_character_same_metric_value_pct": native,
                    "preserved_character_daily_volatility_pct": native_daily,
                    "historical_action_replay_value_pct": replay,
                    "paper_minus_character_notebook_pct": paper_percent - native,
                    "paper_minus_action_replay_pct": paper_percent - replay,
                    "reachable_blob_literal": literal,
                    "reachable_blob_hit_count": len(hits[literal]),
                    "reachable_blob_hit_ids": ",".join(hits[literal]),
                    "source_relation": relation,
                    "defensible_paper_result_credit": "no",
                    "credit_reason": reason,
                }
            )
    summary = {
        "scope": "all eight disputed daily/annualized volatility cells in FinMem Table 4",
        "official_arxiv_versions_audited": 2,
        "table_4_numeric_values_changed_between_v1_and_v2": False,
        "table_4_pdf_pages_visually_inspected": {"v1": 17, "v2": 18},
        "reachable_commits_scanned": EXPECTED_REACHABLE_COMMITS,
        "reachable_objects_scanned": EXPECTED_REACHABLE_OBJECTS,
        "reachable_blobs_byte_scanned": len(blob_ids),
        "unreachable_objects_in_source_clone": 0,
        "historical_notebook_path_revisions": len(notebook_history),
        "unique_historical_notebook_blobs": len(historical_notebook_blobs),
        "historical_notebook_blob": HISTORICAL_NOTEBOOK_BLOB,
        "annualized_cells_matching_native_daily_values": 4,
        "daily_cells_matching_separate_tsla_full_output": 2,
        "daily_cells_absent_from_all_reachable_source_blobs": 2,
        "cells_receiving_defensible_paper_result_credit": 0,
        "bounded_conclusion": (
            "The public record supports a cross-experiment/mislabeled-table construction "
            "defect, not a faithful native reproduction of the eight displayed cells."
        ),
    }
    return rows, summary


def parse_action_csv(blob: bytes) -> Tuple[List[Tuple[datetime, int]], str]:
    rows = list(csv.DictReader(io.StringIO(blob.decode("utf-8-sig"))))
    if not rows:
        raise RuntimeError("Historical action CSV is empty")
    fields = set(rows[0])
    date_field = next((name for name in ("date", "dates") if name in fields), None)
    action_field = next((name for name in ("direction", "action", "actions") if name in fields), None)
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
                "direction_values": ",".join(str(value) for value in sorted({value for _, value in actions})),
            }
        )
    if len(rows) != EXPECTED_HISTORICAL_ACTION_CSVS:
        raise RuntimeError(f"Expected 18 historical action CSVs, found {len(rows)}")
    return rows


def historical_action_reproduction(source_root: Path, price_root: Path) -> List[Dict[str, Any]]:
    prices, timestamps = load_adjusted_prices(price_root / "TSLA_ablation.json")
    trading_dates = [
        datetime.fromtimestamp(timestamp, timezone.utc).replace(tzinfo=None).date() for timestamp in timestamps
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
                parsed, _ = parse_action_csv(git_blob(source_root, HISTORICAL_ARTIFACT_COMMIT, path))
                filtered = [(date.date(), value) for date, value in parsed if first_date <= date.date() <= last_date]
                action_dates = [date for date, _ in filtered]
                if action_dates != trading_dates:
                    raise RuntimeError(f"Historical action dates do not align to Yahoo trading dates: {path}")
                action_cache[path] = np.asarray([value for _, value in filtered], dtype=float)
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


def historical_native_metric_function_execution(source_root: Path, price_root: Path) -> List[Dict[str, Any]]:
    metrics_blob = git_blob(
        source_root,
        HISTORICAL_ARTIFACT_COMMIT,
        HISTORICAL_METRICS_PATH,
    )
    if hashlib.sha256(metrics_blob).hexdigest() != HISTORICAL_METRICS_SHA256:
        raise RuntimeError("Historical FinMem metric source changed")
    namespace: Dict[str, Any] = {"__name__": "finmem_historical_metrics"}
    exec(
        compile(
            metrics_blob.decode("utf-8"),
            HISTORICAL_METRICS_PATH,
            "exec",
        ),
        namespace,
    )
    calculate_metrics = namespace.get("calculate_metrics")
    main_function = namespace.get("main")
    yfinance_module = namespace.get("yf")
    if (
        not callable(calculate_metrics)
        or not callable(main_function)
        or getattr(yfinance_module, "__version__", "") != "0.2.32"
    ):
        raise RuntimeError("Historical FinMem metric dependency contract changed")

    network_calls = 0

    def blocked_download(*args: Any, **kwargs: Any) -> None:
        nonlocal network_calls
        network_calls += 1
        raise RuntimeError("live yfinance download forbidden in pinned FinMem audit")

    yfinance_module.download = blocked_download
    prices, timestamps = load_adjusted_prices(price_root / "TSLA_ablation.json")
    trading_dates = [
        datetime.fromtimestamp(timestamp, timezone.utc).replace(tzinfo=None).date() for timestamp in timestamps
    ]
    first_date, last_date = min(trading_dates), max(trading_dates)
    targets = [row for row in paper_table_rows() if row["paper_table"] in {3, 4, 5}]
    metric_order = (
        "cumulative_return_pct",
        "sharpe_ratio",
        "daily_volatility_pct",
        "annualized_volatility_pct",
        "max_drawdown_pct",
    )
    rows: List[Dict[str, Any]] = []
    for paper_table, strategy in sorted(
        {(int(row["paper_table"]), str(row["strategy_or_configuration"])) for row in targets}
    ):
        path = HISTORICAL_ABLATION_ACTION_PATHS.get((paper_table, strategy), "")
        if strategy == "buy_and_hold":
            actions = np.ones(len(prices), dtype=float)
            action_evidence = "synthetic_all_ones_buy_and_hold_path"
        else:
            parsed, _ = parse_action_csv(git_blob(source_root, HISTORICAL_ARTIFACT_COMMIT, path))
            filtered = [(date.date(), value) for date, value in parsed if first_date <= date.date() <= last_date]
            if [date for date, _ in filtered] != trading_dates:
                raise RuntimeError(f"Historical action dates do not align for native metric run: {path}")
            actions = np.asarray([value for _, value in filtered], dtype=float)
            action_evidence = f"{HISTORICAL_ARTIFACT_COMMIT}:{path}"
        native_tuple = calculate_metrics(prices.tolist(), actions.tolist())
        native_values = {
            metric: float(value) * (100.0 if index in {0, 2, 3, 4} else 1.0)
            for index, (metric, value) in enumerate(zip(metric_order, native_tuple))
        }
        adapter_values = source_action_metrics(prices, actions)
        adapter_errors = {metric: abs(native_values[metric] - adapter_values[metric]) for metric in metric_order}
        paper_values = {
            str(row["metric"]): float(row["paper_value"])
            for row in targets
            if int(row["paper_table"]) == paper_table and row["strategy_or_configuration"] == strategy
        }
        paper_matches = {
            metric: abs(native_values[metric] - paper_values[metric]) <= DISPLAY_TOLERANCE for metric in metric_order
        }
        rows.append(
            {
                "paper_table": paper_table,
                "strategy_or_configuration": strategy,
                "source_commit": HISTORICAL_ARTIFACT_COMMIT,
                "source_path": HISTORICAL_METRICS_PATH,
                "source_sha256": HISTORICAL_METRICS_SHA256,
                "source_function": "calculate_metrics",
                "yfinance_version_imported": yfinance_module.__version__,
                "live_yfinance_calls": network_calls,
                "price_input": "TSLA_ablation.json",
                "price_input_sha256": PRICE_SHA256["TSLA_ablation.json"],
                "action_evidence": action_evidence,
                **{f"native_{metric}": native_values[metric] for metric in metric_order},
                "maximum_absolute_error_against_audit_adapter": max(adapter_errors.values()),
                "all_five_metrics_match_audit_adapter": all(error <= 1e-12 for error in adapter_errors.values()),
                "paper_cells_matched": sum(paper_matches.values()),
                "paper_cells_conflicted": len(paper_matches) - sum(paper_matches.values()),
                "paper_row_fully_matched": all(paper_matches.values()),
                "native_metric_function_evidence": True,
                "native_agent_result_credit": False,
            }
        )

    def pinned_get_price(start: str, end: str, ticker: str) -> List[float]:
        return prices.tolist()

    namespace["get_price"] = pinned_get_price
    main_row_names = {
        "cumulative_return_pct": "Cumulative Return",
        "sharpe_ratio": "Sharpe Ratio",
        "daily_volatility_pct": "Standard Deviation",
        "annualized_volatility_pct": "Annualized Volatility",
        "max_drawdown_pct": "Max Drawdown",
    }
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_root = Path(temporary_directory)
        for paper_table in (3, 4, 5):
            df_paths: Dict[str, str] = {}
            col_names: Dict[str, List[str]] = {}
            strategies = sorted(
                {
                    str(row["strategy_or_configuration"])
                    for row in targets
                    if int(row["paper_table"]) == paper_table and row["strategy_or_configuration"] != "buy_and_hold"
                }
            )
            for strategy in strategies:
                source_path = HISTORICAL_ABLATION_ACTION_PATHS[(paper_table, strategy)]
                action_blob = git_blob(
                    source_root,
                    HISTORICAL_ARTIFACT_COMMIT,
                    source_path,
                )
                destination = temporary_root / f"{paper_table}_{strategy}.csv"
                destination.write_bytes(action_blob)
                header = next(csv.reader(io.StringIO(action_blob.decode("utf-8-sig"))))
                date_field = next(field for field in ("date", "dates") if field in header)
                action_field = next(field for field in ("direction", "action", "actions") if field in header)
                df_paths[strategy] = str(destination)
                col_names[strategy] = [date_field, action_field]
            output_path = temporary_root / f"table_{paper_table}.csv"
            captured_stdout = io.StringIO()
            with warnings.catch_warnings(record=True) as captured_warnings:
                warnings.simplefilter("always")
                with contextlib.redirect_stdout(captured_stdout):
                    main_function(
                        "TSLA",
                        "2022-06-16",
                        "2022-12-28",
                        df_paths,
                        col_names,
                        str(output_path),
                    )
            output_sha256 = hashlib.sha256(output_path.read_bytes()).hexdigest()
            if output_sha256 != HISTORICAL_MAIN_OUTPUT_SHA256[paper_table]:
                raise RuntimeError(f"FinMem parameterized main output changed: Table {paper_table}")
            output_frame = namespace["pd"].read_csv(output_path, index_col=0)
            for row in rows:
                if int(row["paper_table"]) != paper_table:
                    continue
                strategy = str(row["strategy_or_configuration"])
                column = "Buy & Hold" if strategy == "buy_and_hold" else strategy
                main_errors = []
                for metric in metric_order:
                    main_value = float(output_frame.loc[main_row_names[metric], column])
                    if metric != "sharpe_ratio":
                        main_value *= 100.0
                    main_errors.append(abs(main_value - float(row[f"native_{metric}"])))
                row.update(
                    {
                        "parameterized_main_executed": True,
                        "parameterized_main_output_sha256": output_sha256,
                        "parameterized_main_warning_count": len(captured_warnings),
                        "parameterized_main_stdout_nonempty": bool(captured_stdout.getvalue().strip()),
                        "parameterized_main_maximum_function_error": max(main_errors),
                        "parameterized_main_matches_calculate_metrics": all(error <= 1e-12 for error in main_errors),
                        "parameterized_main_input_adapter": (
                            "get_price_rebound_to_pinned_TSLA_ablation_json;"
                            "author_local_action_paths_rebound_to_exact_git_blobs"
                        ),
                        "source_formula_changed": False,
                        "hardcoded_dunder_main_block_executed": False,
                    }
                )
    if (
        len(rows) != 15
        or network_calls != 0
        or not all(row["all_five_metrics_match_audit_adapter"] for row in rows)
        or not all(row["parameterized_main_executed"] for row in rows)
        or not all(row["parameterized_main_matches_calculate_metrics"] for row in rows)
        or sum(row["paper_cells_matched"] for row in rows) != 67
        or sum(row["paper_row_fully_matched"] for row in rows) != 11
    ):
        raise RuntimeError("FinMem native metric-function execution census changed")
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
                "status": ("rounding_consistent" if error <= 0.001 else "paper_internal_annualization_mismatch"),
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


def public_fork_census(census_root: Path, branch_ref_snapshot: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fail closed over every unique head in the dated accessible-fork census.

    The local evidence store materializes one representative ref for each
    unique head, while the committed GraphQL snapshot retains the complete
    repository/branch mapping. Binary checkpoint files are byte-scanned only;
    no untrusted pickle is deserialized.
    """
    if git_text(census_root, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise RuntimeError("FinMem public-fork census is shallow")
    ref_lines = git_text(
        census_root,
        "for-each-ref",
        "refs/fork-census",
        "--format=%(refname)%09%(objectname)",
    ).splitlines()
    if (
        len(ref_lines) != PUBLIC_FORK_REPRESENTATIVE_REF_COUNT
        or _sha256_lines(ref_lines) != PUBLIC_FORK_REPRESENTATIVE_REF_SHA256
    ):
        raise RuntimeError("FinMem representative public-fork ref census changed")
    refs = [line.split("\t", 1) for line in ref_lines]
    unique_heads = sorted({head for _, head in refs})
    if (
        len(unique_heads) != PUBLIC_FORK_REPRESENTATIVE_REF_COUNT
        or _sha256_lines(unique_heads) != PUBLIC_FORK_UNIQUE_HEAD_SHA256
    ):
        raise RuntimeError("FinMem public-fork unique-head census changed")

    if sha256(branch_ref_snapshot) != PUBLIC_FORK_SNAPSHOT_SHA256:
        raise RuntimeError("FinMem public-fork branch-ref snapshot bytes changed")
    with branch_ref_snapshot.open(newline="", encoding="utf-8") as handle:
        branch_rows = list(csv.DictReader(handle))
    expected_columns = {
        "repository",
        "branch",
        "head_commit",
        "repository_created_at",
        "repository_pushed_at",
        "head_committed_at",
        "head_author_login",
        "head_author_name",
        "head_author_email",
        "head_subject",
    }
    if not branch_rows or set(branch_rows[0]) != expected_columns:
        raise RuntimeError("FinMem public-fork branch-ref snapshot schema changed")
    branch_rows.sort(key=lambda row: (row["repository"].lower(), row["branch"].lower(), row["head_commit"]))
    canonical_branch_refs = [f"{row['repository']}\t{row['branch']}\t{row['head_commit']}" for row in branch_rows]
    if (
        len(branch_rows) != PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT
        or len({row["repository"] for row in branch_rows}) != PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT
        or len({(row["repository"], row["branch"]) for row in branch_rows}) != len(branch_rows)
        or _sha256_lines(canonical_branch_refs) != PUBLIC_FORK_GRAPHQL_REF_SHA256
        or {row["head_commit"] for row in branch_rows} != set(unique_heads)
    ):
        raise RuntimeError("FinMem complete public-fork branch-ref snapshot changed")

    expected_structured_data_paths = {
        FORK_MINIRUN_HEAD: (
            "Fake-Sample-Data/example_input/Fake-News-Data-for-Each-Stock/AMZN_fake.csv",
            "Fake-Sample-Data/example_input/Fake-News-Data-for-Each-Stock/MSFT_fake.csv",
            "Fake-Sample-Data/example_input/Fake-News-Data-for-Each-Stock/NFLX_fake.csv",
            "Fake-Sample-Data/example_input/Fake-News-Data-for-Each-Stock/TSLA_fake.csv",
            "Fake-Sample-Data/example_input/filing_data.parquet",
            "tsla_gpt3.5.csv",
        )
    }
    structured_data_suffixes = (".csv", ".jsonl", ".log", ".npy", ".npz", ".parquet")
    rows: List[Dict[str, Any]] = []
    extra_commits_by_head: Dict[str, List[str]] = {}
    changed_paths_by_head: Dict[str, List[str]] = {}
    divergent_surface: List[str] = []
    extra_author_emails: set[str] = set()
    extra_author_names: set[str] = set()
    all_extra_commits: set[str] = set()
    all_extra_paths: set[str] = set()
    for ref, head in refs:
        extra_commits = sorted(git_text(census_root, "rev-list", head, "--not", SOURCE_COMMIT).splitlines())
        changed_paths: set[str] = set()
        extra_dates: List[str] = []
        for commit in extra_commits:
            changed_paths.update(
                path
                for path in git_text(
                    census_root,
                    "diff-tree",
                    "--root",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    commit,
                ).splitlines()
                if path
            )
            meta = git_text(census_root, "show", "-s", "--format=%aI%x00%an%x00%ae", commit).rstrip("\n").split("\0")
            if len(meta) != 3:
                raise RuntimeError(f"Malformed FinMem fork commit metadata: {commit}")
            extra_dates.append(meta[0])
            extra_author_names.add(meta[1])
            extra_author_emails.add(meta[2])
        ordered_paths = sorted(changed_paths)
        extra_commits_by_head[head] = extra_commits
        changed_paths_by_head[head] = ordered_paths
        if extra_commits:
            divergent_surface.append(f"{head}\t{';'.join(extra_commits)}\t{';'.join(ordered_paths)}")
            all_extra_commits.update(extra_commits)
            all_extra_paths.update(ordered_paths)
            expected = DIVERGENT_FORK_FINDINGS.get(head)
            if expected is None:
                raise RuntimeError(f"Unreviewed divergent FinMem fork head: {head}")
            if (len(extra_commits), len(ordered_paths)) != (
                expected["commits"],
                expected["paths"],
            ):
                raise RuntimeError(f"FinMem fork surface changed for {head}")
            paper_v2_time = datetime.fromisoformat(str(PAPER_VERSIONS["v2"]["submitted_at"]).replace("Z", "+00:00"))
            if any(datetime.fromisoformat(value) <= paper_v2_time for value in extra_dates):
                raise RuntimeError(f"Expected only post-paper divergent commits for {head}")
            classification = str(expected["classification"])
        else:
            classification = "official_public_history_reachable"

        final_structured_data_paths = tuple(
            path
            for path in ordered_paths
            if path.lower().endswith(structured_data_suffixes) and git_object_exists(census_root, f"{head}:{path}")
        )
        if final_structured_data_paths != expected_structured_data_paths.get(head, ()):
            raise RuntimeError(f"FinMem fork structured-data surface changed for {head}: {final_structured_data_paths}")
        head_meta = (
            git_text(census_root, "show", "-s", "--format=%cI%x00%an%x00%ae%x00%s", head).rstrip("\n").split("\0", 3)
        )
        if len(head_meta) != 4:
            raise RuntimeError(f"Malformed FinMem fork-head metadata: {head}")
        matching_branch_rows = [row for row in branch_rows if row["head_commit"] == head]
        rows.append(
            {
                "representative_ref": ref,
                "head_commit": head,
                "head_date": head_meta[0],
                "head_author_name": head_meta[1],
                "head_author_email": head_meta[2],
                "head_subject": head_meta[3],
                "branch_ref_count": len(matching_branch_rows),
                "repository_count": len({row["repository"] for row in matching_branch_rows}),
                "repositories": ";".join(sorted({row["repository"] for row in matching_branch_rows})),
                "extra_commit_count_beyond_official_head": len(extra_commits),
                "extra_changed_path_count": len(ordered_paths),
                "final_changed_structured_data_path_count": len(final_structured_data_paths),
                "final_changed_structured_data_paths": ";".join(final_structured_data_paths),
                "official_source_author_identity_match_in_extra_commits": False,
                "classification": classification,
                "paper_result_credit": False,
            }
        )

    base_reachable = [row for row in rows if not row["extra_commit_count_beyond_official_head"]]
    if len(base_reachable) != PUBLIC_FORK_BASE_REACHABLE_HEAD_COUNT:
        raise RuntimeError("FinMem base-reachable public-fork head count changed")
    if len(rows) - len(base_reachable) != PUBLIC_FORK_DIVERGENT_HEAD_COUNT:
        raise RuntimeError("FinMem divergent public-fork head count changed")
    if set(extra_commits_by_head) != set(unique_heads):
        raise RuntimeError("FinMem unique-head review coverage changed")
    if set(DIVERGENT_FORK_FINDINGS) != {head for head, commits in extra_commits_by_head.items() if commits}:
        raise RuntimeError("FinMem reviewed divergent-head set changed")
    if _sha256_lines(divergent_surface) != PUBLIC_FORK_DIVERGENT_SURFACE_SHA256:
        raise RuntimeError("FinMem divergent fork commit/path surface changed")
    if (
        len(all_extra_commits) != PUBLIC_FORK_DIVERGENT_COMMIT_COUNT
        or _sha256_lines(sorted(all_extra_commits)) != PUBLIC_FORK_DIVERGENT_COMMIT_SHA256
        or len(all_extra_paths) != PUBLIC_FORK_DIVERGENT_PATH_COUNT
        or _sha256_lines(sorted(all_extra_paths)) != PUBLIC_FORK_DIVERGENT_PATH_SHA256
    ):
        raise RuntimeError("FinMem aggregate divergent fork surface changed")
    if extra_author_emails != EXPECTED_DIVERGENT_AUTHOR_EMAILS:
        raise RuntimeError(f"FinMem divergent fork author identities changed: {extra_author_emails}")
    if extra_author_emails & OFFICIAL_SOURCE_AUTHOR_EMAILS:
        raise RuntimeError("FinMem divergent commits now match an official source author email")
    if extra_author_names & OFFICIAL_SOURCE_AUTHOR_NAMES:
        raise RuntimeError("FinMem divergent commits now match an official source author name")

    mini_config = git_blob(census_root, FORK_MINIRUN_HEAD, "config/tsla_gpt_config.toml")
    mini_action = git_blob(census_root, FORK_MINIRUN_HEAD, "tsla_gpt3.5.csv")
    mini_state = git_blob(
        census_root,
        FORK_MINIRUN_HEAD,
        "data/05_train_model_output/agent_1/state_dict.pkl",
    )
    if (
        hashlib.sha256(mini_config).hexdigest() != FORK_MINIRUN_CONFIG_SHA256
        or b'model = "phi3v"' not in mini_config
        or b"top_k = 3" not in mini_config
        or hashlib.sha256(mini_action).hexdigest() != FORK_MINIRUN_ACTION_SHA256
        or b"gpt-3.5-turbo-0125" not in mini_state
    ):
        raise RuntimeError("FinMem post-paper TSLA mini-run evidence changed")
    mini_action_rows = list(csv.DictReader(io.StringIO(mini_action.decode("utf-8"))))
    if (
        len(mini_action_rows) != 19
        or mini_action_rows[0]["date"] != "2016-01-13"
        or mini_action_rows[-1]["date"] != "2016-02-09"
        or {row["symbol"] for row in mini_action_rows} != {"TSLA"}
        or {row["direction"] for row in mini_action_rows} != {"0"}
    ):
        raise RuntimeError("FinMem post-paper TSLA mini-run action path changed")

    checkpoint_config = git_blob(census_root, FORK_CHECKPOINT_HEAD, "config/tsla_gpt_config.toml")
    checkpoint_state = git_blob(
        census_root,
        FORK_CHECKPOINT_HEAD,
        "data/06_train_checkpoint/agent_1/state_dict.pkl",
    )
    checkpoint_result_paths = git_text(
        census_root,
        "ls-tree",
        "-r",
        "--name-only",
        FORK_CHECKPOINT_HEAD,
        "data/09_results",
    ).splitlines()
    if (
        hashlib.sha256(checkpoint_config).hexdigest() != FORK_CHECKPOINT_CONFIG_SHA256
        or b'model = "gpt-3.5-turbo-0125"' not in checkpoint_config
        or b"top_k = 3" not in checkpoint_config
        or b"gpt-3.5-turbo-0125" not in checkpoint_state
        or checkpoint_result_paths != ["data/09_results/.gitkeep"]
    ):
        raise RuntimeError("FinMem post-paper checkpoint evidence changed")
    deleted_author_tree_paths = [
        path
        for path in changed_paths_by_head[FORK_CHECKPOINT_HEAD]
        if path.startswith("FinMem-LLM-trading-main/Visualize-metrics-test/")
    ]
    if (
        len(deleted_author_tree_paths) != 33
        or sum(path.lower().endswith(".csv") for path in deleted_author_tree_paths) != 18
        or sum(path.lower().endswith(".ipynb") for path in deleted_author_tree_paths) != 7
        or any(git_object_exists(census_root, f"{FORK_CHECKPOINT_HEAD}:{path}") for path in deleted_author_tree_paths)
        or git_text(
            census_root,
            "rev-parse",
            "316d5ac5140945f4886faaa9c4437f6aeacf67ed^",
        ).strip()
        != SOURCE_ROOT_COMMIT
    ):
        raise RuntimeError("FinMem fork deletion lineage changed")

    summary: Dict[str, Any] = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "github_rest_reported_forks": PUBLIC_FORK_REST_COUNT,
        "graphql_accessible_forks": PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT,
        "rest_minus_accessible_fork_gap": (PUBLIC_FORK_REST_COUNT - PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT),
        "accessibility_gap_interpretation": ("deleted_private_or_otherwise_unavailable_not_inspected"),
        "graphql_accessible_branch_refs": PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT,
        "graphql_accessible_branch_ref_census_sha256": PUBLIC_FORK_GRAPHQL_REF_SHA256,
        "graphql_accessible_branch_ref_snapshot_file_sha256": sha256(branch_ref_snapshot),
        "representative_unique_head_refs": len(rows),
        "representative_ref_census_sha256": _sha256_lines(ref_lines),
        "unique_heads": len(unique_heads),
        "unique_head_sha256": _sha256_lines(unique_heads),
        "heads_reachable_from_official_history": len(base_reachable),
        "divergent_heads_reviewed": len(rows) - len(base_reachable),
        "divergent_extra_commits_reviewed": len(all_extra_commits),
        "divergent_changed_paths_reviewed": len(all_extra_paths),
        "divergent_heads_matching_official_source_author_identity": 0,
        "postpaper_native_action_paths_discovered": 1,
        "postpaper_native_action_path": "tsla_gpt3.5.csv",
        "postpaper_native_action_rows": len(mini_action_rows),
        "postpaper_native_action_date_range": "2016-01-13/2016-02-09",
        "postpaper_native_action_unique_directions": [0],
        "postpaper_native_action_matches_paper_model_dates_topk_or_trials": False,
        "postpaper_checkpoint_head": FORK_CHECKPOINT_HEAD,
        "postpaper_checkpoint_final_result_paths": checkpoint_result_paths,
        "known_author_history_paths_deleted_not_newly_contributed": len(deleted_author_tree_paths),
        "paper_result_artifacts_discovered_in_divergent_fork_heads": 0,
        "paper_result_credit": False,
        "pickle_execution_policy": "byte_scan_only_no_deserialization",
    }
    return rows, summary


def build_audit(
    source_root: Path,
    paper_path: Path,
    paper_version_root: Path,
    price_root: Path,
    fork_census_root: Path,
    fork_snapshot_path: Path,
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
    native_metric_runs = historical_native_metric_function_execution(source_root, price_root)
    paper_versions, paper_source_files = paper_version_audit(paper_version_root)
    table_4_forensics, table_4_forensic_summary = table_4_volatility_forensics(
        source_root, author_outputs, action_reproduction
    )
    fork_heads, fork_summary = public_fork_census(fork_census_root, fork_snapshot_path)

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
    write_csv(
        output_dir / "historical_native_metric_function_execution.csv",
        native_metric_runs,
        list(native_metric_runs[0]),
    )
    write_csv(
        output_dir / "official_paper_version_inventory.csv",
        paper_versions,
        list(paper_versions[0]),
    )
    write_csv(
        output_dir / "official_paper_source_inventory.csv",
        paper_source_files,
        list(paper_source_files[0]),
    )
    write_csv(
        output_dir / "table_4_volatility_provenance.csv",
        table_4_forensics,
        list(table_4_forensics[0]),
    )
    write_csv(
        output_dir / "public_fork_unique_head_inventory.csv",
        fork_heads,
        list(fork_heads[0]),
    )
    (output_dir / "table_4_volatility_forensics.json").write_text(
        json.dumps(table_4_forensic_summary, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "public_fork_census.json").write_text(json.dumps(fork_summary, indent=2) + "\n", encoding="utf-8")

    matched = sum(row["status"] == "exact_displayed_precision_match" for row in conformance)
    mismatched = sum(row["status"].startswith("mismatch") for row in conformance)
    unverifiable = sum(row["status"].startswith("unverifiable") for row in conformance)
    volatility_mismatches = sum(row["status"] == "paper_internal_annualization_mismatch" for row in volatility)
    row_groups: Dict[Tuple[int, str, str], List[Mapping[str, Any]]] = {}
    for row in conformance:
        key = (row["paper_table"], row["scope"], row["strategy_or_configuration"])
        row_groups.setdefault(key, []).append(row)
    fully_matched_rows = sum(
        all(row["status"] == "exact_displayed_precision_match" for row in rows) for rows in row_groups.values()
    )
    mismatched_rows = sum(any(row["status"].startswith("mismatch") for row in rows) for rows in row_groups.values())
    unverifiable_rows = sum(
        all(row["status"].startswith("unverifiable") for row in rows) for rows in row_groups.values()
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

    author_matched = sum(row["status"] == "author_output_exact_displayed_precision_match" for row in author_outputs)
    author_last_decimal = sum(
        row["status"] == "author_output_one_last_decimal_unit_difference" for row in author_outputs
    )
    author_conflicted = sum(row["status"] == "paper_conflicts_with_preserved_author_output" for row in author_outputs)
    action_matched = sum(
        row["status"] == "historical_action_exact_displayed_precision_match" for row in action_reproduction
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
        path for directory in result_dirs for path in directory.glob("*") if path.is_file() and path.name != ".gitkeep"
    ]
    manifest: Dict[str, Any] = {
        "audit": "FinMem paper claims versus pinned public source history and price inputs",
        "overall_status": "author_outputs_partially_verified_not_end_to_end_reproduced",
        "full_paper_reproduced": False,
        "end_to_end_agent_result_cells_reproduced": 0,
        "paper_url": PAPER_URL,
        "paper_sha256": PAPER_SHA256,
        "official_arxiv_versions_audited": len(paper_versions),
        "official_arxiv_pdf_pages_pinned": sum(int(row["pdf_pages"]) for row in paper_versions),
        "official_table_4_pdf_pages_visually_inspected": len(paper_versions),
        "official_arxiv_source_files_inventoried": len(paper_source_files),
        "official_arxiv_version_inventory": paper_versions,
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
        "historical_native_metric_configurations_executed": len(native_metric_runs),
        "historical_native_metric_cells_executed": len(native_metric_runs) * 5,
        "historical_native_metric_cells_matching_audit_adapter": sum(
            5 for row in native_metric_runs if row["all_five_metrics_match_audit_adapter"]
        ),
        "historical_native_metric_cells_matching_paper": sum(row["paper_cells_matched"] for row in native_metric_runs),
        "historical_native_metric_rows_fully_matching_paper": sum(
            row["paper_row_fully_matched"] for row in native_metric_runs
        ),
        "historical_native_metric_rows_conflicted_with_paper": sum(
            not row["paper_row_fully_matched"] for row in native_metric_runs
        ),
        "historical_native_metric_maximum_adapter_error": max(
            row["maximum_absolute_error_against_audit_adapter"] for row in native_metric_runs
        ),
        "historical_native_metric_yfinance_version": "0.2.32",
        "historical_native_metric_live_yfinance_calls": 0,
        "historical_parameterized_main_tables_executed": 3,
        "historical_parameterized_main_configurations_executed": len(native_metric_runs),
        "historical_parameterized_main_metric_cells_executed": len(native_metric_runs) * 5,
        "historical_parameterized_main_cells_matching_calculate_metrics": sum(
            5 for row in native_metric_runs if row["parameterized_main_matches_calculate_metrics"]
        ),
        "historical_parameterized_main_maximum_function_error": max(
            row["parameterized_main_maximum_function_error"] for row in native_metric_runs
        ),
        "historical_parameterized_main_output_sha256": HISTORICAL_MAIN_OUTPUT_SHA256,
        "historical_parameterized_main_live_yfinance_calls": 0,
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
        "table_4_disputed_volatility_cells_forensically_traced": len(table_4_forensics),
        "table_4_annualized_cells_matching_native_daily_values": 4,
        "table_4_daily_cells_matching_separate_tsla_full_output": 2,
        "table_4_daily_cells_absent_from_all_reachable_source_blobs": 2,
        "table_4_disputed_volatility_cells_receiving_result_credit": 0,
        "current_head_native_action_or_return_files_shipped": len(shipped_result_files),
        "historical_action_csvs_in_public_git_history": len(action_inventory),
        "historical_repository_audit": history,
        "public_fork_census_date": fork_summary["census_date"],
        "github_rest_reported_public_forks": fork_summary["github_rest_reported_forks"],
        "graphql_accessible_public_forks": fork_summary["graphql_accessible_forks"],
        "public_fork_accessibility_gap": fork_summary["rest_minus_accessible_fork_gap"],
        "public_fork_branch_refs_examined": fork_summary["graphql_accessible_branch_refs"],
        "public_fork_unique_heads_examined": fork_summary["unique_heads"],
        "public_fork_divergent_heads_examined": fork_summary["divergent_heads_reviewed"],
        "public_fork_divergent_extra_commits_examined": fork_summary["divergent_extra_commits_reviewed"],
        "public_fork_divergent_changed_paths_examined": fork_summary["divergent_changed_paths_reviewed"],
        "public_fork_author_attributed_divergent_heads": fork_summary[
            "divergent_heads_matching_official_source_author_identity"
        ],
        "public_fork_additional_native_action_paths": fork_summary["postpaper_native_action_paths_discovered"],
        "public_fork_paper_result_artifacts_discovered": fork_summary[
            "paper_result_artifacts_discovered_in_divergent_fork_heads"
        ],
        "public_fork_paper_result_credit": fork_summary["paper_result_credit"],
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
        "source_calculate_metrics_function_operational": True,
        "source_parameterized_metrics_main_operational_with_input_adapter": True,
        "source_parameterized_metrics_main_formulas_changed": False,
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
            "The exact historical parameterized main writes all three ablation tables for "
            "all 15 recovered configurations after only rebinding its author-local action "
            "paths and get_price input to hash-pinned public artifacts. Its formulas are "
            "unchanged, it makes zero live network calls, and all 75 values match the exact "
            "calculate_metrics function within 1e-12. Replaying the ablation actions "
            "against a hash-pinned Yahoo response reproduces 67/75 displayed "
            "Table 3--5 cells. The remaining eight are both Table 4 volatility columns. Both "
            "official arXiv versions and their TeX sources retain them: four annualized cells "
            "exactly equal native daily values, two daily cells match a separate TSLA "
            "experiment, and two daily cells are absent from all 171 reachable source blobs. "
            "None earns result credit. This is strong paper-output lineage but not an end-to-end "
            "FinMem rerun: the original inputs, memories, complete five-trial outputs, and exact "
            "paper configuration remain absent from the current public tree. An exhaustive dated "
            "census of 181 accessible forks and 187 branch refs found 11 divergent unique heads, "
            "but no author-attributed divergent lineage or additional paper-result artifact. The "
            "one new action CSV is an unaffiliated, post-paper, 19-row all-hold TSLA mini-run using "
            "the wrong model, dates, and top-K, so it receives zero paper credit."
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

- Official paper record: https://arxiv.org/abs/2311.13743. Both v1 and v2 PDFs
  and matching TeX source archives are hash-pinned and audited; the current v2 PDF
  is {PAPER_URL} (SHA-256 `{PAPER_SHA256}`).
- Public source: {SOURCE_URL}, commit `{commit}`.
- Historical author-output snapshot: commit `{HISTORICAL_ARTIFACT_COMMIT}`
  (2023-11-30), deleted from the current tree by commit
  `{HISTORICAL_DELETION_COMMIT}` (2024-02-09).
- Public-fork census: GitHub REST reported {fork_summary["github_rest_reported_forks"]}
  forks on {fork_summary["census_date"]}; GraphQL exposed
  {fork_summary["graphql_accessible_forks"]} repositories and
  {fork_summary["graphql_accessible_branch_refs"]} branch refs. The
  {fork_summary["rest_minus_accessible_fork_gap"]} unavailable repositories are
  explicitly not claimed as inspected.

## What is genuinely verified or reproduced

- The hash-pinned executed notebook provides machine-readable author outputs for all
  235 displayed metric cells. It matches {author_matched}/235 cells exactly and four
  more within one unit of the paper's last printed decimal, corroborating 227/235.
  The eight substantive disagreements are exactly the daily- and annualized-volatility
  entries for all four Table 4 rows.
- The official v1 and v2 PDFs each contain 22 pages. Their matching source archives
  contain {len(paper_source_files)} files in total. Table 4 was visually inspected on
  v1 page 17 and v2 page 18, and the printed cells were cross-checked against extracted
  PDF text and primary TeX. The same eight disputed numbers survive the revision.
- Exhaustive byte scanning covers all {history["reachable_blobs"]} blobs in the complete
  {history["reachable_commits"]}-commit source history. The four paper annualized cells
  exactly equal the preserved character output's daily-volatility cells. Buy-and-Hold
  and Self-Adaptive daily values occur in a separate `TSLA-full.csv` notebook output
  whose returns and Sharpe ratios establish that it is a different experiment. The
  Risk-Seeking and Risk-Averse daily values occur in no reachable public source blob.
  This bounded evidence supports a cross-experiment/mislabeled-table construction
  defect; it does not prove what may have existed in unavailable private artifacts.
- The exact pinned `calculate_metrics` function executes all 15 historical action
  configurations with yfinance 0.2.32 imported and live downloads blocked. All 75
  values match the independent adapter within 1e-12 and {action_matched}/75 match
  the paper at display precision. Tables 3 and 5 match completely (55/55); Table 4
  matches cumulative return, Sharpe, and drawdown (12/20) but conflicts on the same
  eight volatility cells.
- The exact historical parameterized `main` function also writes all three ablation
  table CSVs. The audit changes no source formula: it only rebinds `get_price` to the
  hash-pinned `TSLA_ablation.json` response and replaces author-local action paths with
  exact Git blobs. All 75 written values agree with `calculate_metrics` within 1e-12,
  all three output hashes are pinned, and the blocked live-download counter remains zero.
- This is stronger than paper-value transcription: it connects the paper values to
  author-shipped outputs and independently replays the ablation metric path. It is
  still not an end-to-end rerun of FinMem's LLM decisions or five repeated trials.
- The complete accessible-fork snapshot collapses to {fork_summary["unique_heads"]}
  unique heads: {fork_summary["heads_reachable_from_official_history"]} are reachable
  from official history and all {fork_summary["divergent_heads_reviewed"]} divergent
  heads were reviewed across {fork_summary["divergent_extra_commits_reviewed"]} extra
  commits and {fork_summary["divergent_changed_paths_reviewed"]} changed paths. None
  matches an official-source author identity or contributes a paper-result artifact.
  One post-paper fork contains a 19-row, 2016 TSLA action CSV whose directions are all
  hold, while its active config is phi3v/top-K=3 and its checkpoint identifies
  GPT-3.5. A second contains GPT-3.5/top-K=3 TSLA checkpoint state but no action or
  metric result file. These are unaffiliated mini-runs, not the paper's GPT-4-Turbo,
  top-K=5, five-ticker, five-trial lineage, and receive zero paper credit. The second
  branch deletes the 33-file historical author-output tree from the official root;
  those deleted files are already counted once as official history, not fork evidence.

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
- The reusable metric function and its parameterized `main` now execute with the two
  explicit input/path adapters above. The released hard-coded `if __name__ == "__main__"`
  block remains non-operational: it references an undefined lowercase ticker, hard-codes
  author-local result paths, and uses yfinance/pandas without declaring them in either
  locked environment file.
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
  Table 4 volatility entries disagree with both the preserved character output and the
  independent action replay. Version and blob forensics explain six literal lineages
  and bound the other two to the papers. All {len(volatility) - volatility_mismatches} corresponding
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
        "--paper-version-root",
        type=Path,
        default=Path(
            os.environ.get(
                "FINMEM_PAPER_VERSION_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/finmem_paper_versions",
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
        "--fork-census-root",
        type=Path,
        default=Path(
            os.environ.get(
                "FINMEM_FORK_CENSUS_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/finmem_fork_census",
            )
        ),
    )
    parser.add_argument(
        "--fork-snapshot",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/finmem/public_fork_branch_ref_snapshot.csv",
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
        args.paper_version_root.resolve(),
        args.price_root.resolve(),
        args.fork_census_root.resolve(),
        args.fork_snapshot.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and manifest["overall_status"] != "reproduced")


if __name__ == "__main__":
    sys.exit(main())
