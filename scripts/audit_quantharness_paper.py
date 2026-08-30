#!/usr/bin/env python3
"""Audit every QuantHarness paper revision and its full public source history.

This fail-closed audit pins all four arXiv PDFs and source archives, enumerates
every version-specific numeric result cell, walks both public Git branches and
every reachable commit/path/blob, checks the released 1-hour and 4-hour segment
corpus, and reconstructs the paper's linear-regression accuracy baseline.  It
never calls an LLM or treats an author-rendered table, inferred alignment, or
internal arithmetic identity as a native system reproduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import struct
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd


SOURCE_COMMIT = "00a88cbbc3b946cbdf506038545d6b5c2df6a344"
SOURCE_URL = "https://github.com/Y-Research-SBU/QuantHarness"
SOURCE_LEGACY_URL = "https://github.com/Y-Research-SBU/QuantAgent"
PAPER_URL = "https://arxiv.org/abs/2509.09995"
PAPER_API_SHA256 = "338887e5c299807fcf431fb274b9241b00b2f660618196e07fb88d5aac20f718"
PAPER_ABS_SHA256 = "e8148b824b789559d8ce6bb729e6242378a8e6cb9cf7553fcb66cd92dba70fa2"
PAPER_VERSIONS: Dict[str, Dict[str, Any]] = {
    "v1": {
        "submission_date": "2025-09-12T06:35:40Z",
        "pdf_sha256": "b96e189d0c602fc8ac7dbd6b0510298183b335a95ba922d3b031e04447456d1e",
        "pdf_pages": 30,
        "source_archive_sha256": "03acd99b96e156e0513f0c0d525dd1e7de1ae475e21988bf050632610d64b76e",
        "source_files": 26,
        "main_tex_sha256": "bc2c64e71978eadb21d6464a2cab6e5dc559d88737067a7b2e91a12a10a1e3c5",
        "numeric_result_cells": 88,
        "table_family": "original_random_baseline_and_our_4h_table",
        "author_rendered_correspondence_cells": 88,
        "line_chart_pdf_sha256": "",
    },
    "v2": {
        "submission_date": "2025-09-15T17:08:33Z",
        "pdf_sha256": "4556c01ab0321a772bce7eda82cfc5be24ea1c5a79886b0e933032863d814a32",
        "pdf_pages": 30,
        "source_archive_sha256": "74f1b14a69b4fc6d9c6c717aa1a6b44c76191c85d8f87f7e4db9f5f380b67314",
        "source_files": 26,
        "main_tex_sha256": "52a0951a9e105807c56e3caae59be50b4385063d73e0159e49d13846974ba080",
        "numeric_result_cells": 88,
        "table_family": "original_random_baseline_and_our_4h_table",
        "author_rendered_correspondence_cells": 88,
        "line_chart_pdf_sha256": "",
    },
    "v3": {
        "submission_date": "2025-09-27T00:22:39Z",
        "pdf_sha256": "05652d9dd2887c86bf470fdb424c49e5bb12ca1e839510968eb43fb6a4b55760",
        "pdf_pages": 30,
        "source_archive_sha256": "87ad00c83c44c7ec0dd4c19d48c135c5f2246cd6127e8e0902d57a299fdcf278",
        "source_files": 28,
        "main_tex_sha256": "8e447369a7812f168101374abcb74b410fc8de5c65071d84629904ca34d7bcc9",
        "numeric_result_cells": 152,
        "table_family": "expanded_random_lr_xgboost_and_our_4h_table",
        "author_rendered_correspondence_cells": 152,
        "line_chart_pdf_sha256": "c32553f49ca7caf4ebc80637ee9531c8ee9a43fb2accaf4bf3c1eadc7cd12484",
    },
    "v4": {
        "submission_date": "2026-07-27T02:15:11Z",
        "pdf_sha256": "751e6e7274bbf1fd5179153a28d2d29817c704b5d9b714b04ba57bd739cafda2",
        "pdf_pages": 32,
        "source_archive_sha256": "fde8052adb8199923382c9b1a997107c76aa908f7cf1f1b97934a97359131085",
        "source_files": 12,
        "main_tex_sha256": "e9ecc6ca1f61e221361c8f01aa513a4992f1344442d3bf2967d3b3d16ddc6b15",
        "numeric_result_cells": 272,
        "table_family": "v3_4h_table_plus_portfolio_performance_table",
        "author_rendered_correspondence_cells": 152,
        "line_chart_pdf_sha256": "d1f9304372516c26b76839267c32fc3619d745491516da1aa5ba2dc568a40baf",
    },
}
PAPER_SHA256 = PAPER_VERSIONS["v4"]["pdf_sha256"]
PAPER_ERA_PUBLIC_BRANCH_HEADS = {
    "gh-pages": "c6383f1d821b1def48d4f3f5d857fbdf5df405d4",
    "main": SOURCE_COMMIT,
}
PUBLIC_BRANCH_HEADS = {
    "gh-pages": "aa6c669d0eb1a156bec04c70508980f525157141",
    "main": "2e64c7befa75a88d254a426f5f29fa61b0b56732",
}
PUBLIC_REMOTE_REF_SHA256 = "3e9c1b81db0b1036c9e022fef59750e8fc13c4bb42c0bf3f6b71eaef5e95c4fe"
PUBLIC_HISTORY_COMMIT_COUNT = 204
PUBLIC_HISTORY_COMMIT_SHA256 = "da4997e1d5d4e904b9ee2a3d375116d0daff153ab3b026bf2bf61f22b30f6e61"
PUBLIC_HISTORY_PATH_COUNT = 1870
PUBLIC_HISTORY_PATH_SHA256 = "6be757876c08518cc096a8114edc25d9d74728e069c95276d43b20294394a6b7"
PUBLIC_HISTORY_OBJECT_COUNTS = {"commit": 204, "tree": 291, "blob": 2244}
POSTPAPER_OFFICIAL_COMMIT_COUNT = 9
POSTPAPER_OFFICIAL_COMMIT_SHA256 = "cf01c6673da89a08fbea6dd4e6f793ab68681836a0cacd62722a804be2aad688"
POSTPAPER_OFFICIAL_CHANGED_PATH_COUNT = 6
POSTPAPER_OFFICIAL_CHANGED_PATH_SHA256 = "aac87d0fa7d5f39984645c53697fad9174245e6f03ab2f55efab3382d7444344"
PUBLIC_FORK_CENSUS_DATE = "2026-08-30"
PUBLIC_FORK_REST_COUNT = 613
PUBLIC_FORK_ACCESSIBLE_COUNT = 608
PUBLIC_FORK_BRANCH_REF_COUNT = 700
PUBLIC_FORK_BRANCH_REF_SHA256 = "0eafedc7296f1975d1b9ab816724cfa2cfc483d86a58ed3371b6cb3b2b298bd0"
PUBLIC_FORK_SNAPSHOT_SHA256 = "787c9e03726313ce301ba8ca1a46bd215787b921cac979717d044ef6dd3fa630"
PUBLIC_FORK_UNIQUE_HEAD_COUNT = 112
PUBLIC_FORK_UNIQUE_HEAD_SHA256 = "5f5b053d155719ac4ecddea6dce7703f3e5d38db61506a3eeb4c2dd3a4bad13c"
PUBLIC_FORK_DIVERGENT_HEAD_COUNT = 70
PUBLIC_FORK_DIVERGENT_HEAD_SHA256 = "6720c06df6080dac87ee92c71e77c1ce364cc5137328488c8107dfe293b6ac1d"
PUBLIC_FORK_EXTRA_COMMIT_COUNT = 595
PUBLIC_FORK_EXTRA_COMMIT_SHA256 = "340f9c53b253b28cf88526cb83124f7de670d2082e43308db9e19f0b5a53de74"
PUBLIC_FORK_CHANGED_PATH_COUNT = 4845
PUBLIC_FORK_CHANGED_PATH_SHA256 = "3a29ef34c2911d4bef6aef92ec9b3da35fe14d1b5e6a265a3a331cc4afa4b3be"
PUBLIC_FORK_NEW_OBJECT_COUNTS = {"commit": 595, "tree": 1117, "blob": 2072}
PUBLIC_FORK_NEW_OBJECT_SHA256 = "11310e5d8da57d067cb374aa1d58f4e6994a003a45bc0a12bdbf52e556ff3d6c"
PUBLIC_FORK_NEW_BLOB_SHA256 = "d34b46d0332c0ef2d1ce6c711a47c04496e96bddf237f675f4a753bffab0ac1b"
PUBLIC_FORK_NEW_BLOB_BYTES = 887238813
PUBLIC_FORK_TEXT_BLOBS_SCANNED = 1739
PUBLIC_FORK_TRADING_DB_BLOBS = 42
PUBLIC_FORK_TRADING_DB_HISTORY_ROWS = 2228
PUBLIC_FORK_BUILD_DB_BLOBS = 2
PUBLIC_FORK_TASS_MAIN_HEAD = "bbaddd441de4f7bed6f8b9f694da1fda991eb29e"
PUBLIC_FORK_TASS_TEST_HEAD = "94bf2a5c6b1fced7c8a30c2435b87518145102b8"
PUBLIC_FORK_TASS_MINIRUN_COMMIT = "fda501ef0bb48eedc47e133429ae9158f1908cb2"
NATIVE_RESULT_SUFFIXES = (
    ".feather",
    ".h5",
    ".hdf5",
    ".jsonl",
    ".log",
    ".npy",
    ".npz",
    ".parquet",
    ".pickle",
    ".pkl",
    ".pt",
    ".pth",
    ".ckpt",
)
HISTORICAL_RESULT_PATHS = {"assets/1hour.png", "assets/table.png", "assets/table1.png"}
HISTORICAL_RESULT_IMAGES: Dict[str, Dict[str, Any]] = {
    "369deaf966fb19bd5cd9cc8bbcbd846d713f3afe": {
        "sha256": "98a7feda2777c674fa7ded15e8d165f1058a4f063cf5caa314e63c906f6122eb",
        "dimensions": "1545x952",
        "paths": ("assets/table.png",),
        "role": "v1_v2_88_cell_table_render",
        "paper_versions": "v1;v2",
        "canonical_correspondence": True,
        "distinct_table_cells_corresponded": 88,
        "version_specific_table_cells_corresponded": 176,
        "correspondence_kind": "complete_manual_visual_table_correspondence",
    },
    "f23353962f74a7965d07ac049c36e36759b15feb": {
        "sha256": "ea6ec79730540977a845b7b9598a29ab88ba0ac2353064b085a28095598620d5",
        "dimensions": "907x1039",
        "paths": ("assets/table.png",),
        "role": "v3_v4_152_cell_table_alternate_render",
        "paper_versions": "v3;v4",
        "canonical_correspondence": False,
        "distinct_table_cells_corresponded": 0,
        "version_specific_table_cells_corresponded": 0,
        "correspondence_kind": "alternate_complete_manual_visual_table_correspondence",
    },
    "aea3a4a0de14dfd0a49b0bd49cef2ff6d7bf9602": {
        "sha256": "43038180e85b5df4d7cd69e1a4fb77beb829f8274a872cb3d47c79201f9793f1",
        "dimensions": "907x1038",
        "paths": ("assets/table.png", "assets/table1.png"),
        "role": "v3_v4_152_cell_table_alternate_render",
        "paper_versions": "v3;v4",
        "canonical_correspondence": False,
        "distinct_table_cells_corresponded": 0,
        "version_specific_table_cells_corresponded": 0,
        "correspondence_kind": "alternate_complete_manual_visual_table_correspondence",
    },
    "8cb62e42e92b73da79bade2c1b19bac4e1af0a8a": {
        "sha256": "f833dc2927f039dfe36c5c711c6e44f024df9478d0260d8e3834570867bfdce3",
        "dimensions": "966x1032",
        "paths": ("assets/table1.png",),
        "role": "v3_v4_152_cell_table_current_render",
        "paper_versions": "v3;v4",
        "canonical_correspondence": True,
        "distinct_table_cells_corresponded": 152,
        "version_specific_table_cells_corresponded": 304,
        "correspondence_kind": "complete_manual_visual_table_correspondence",
    },
    "7ba02eabeaac6d14135f20eb244edf88d5ed3519": {
        "sha256": "7df9c68daeecd7e3afa16a992b1b02aeebcf4d648e9ea2f9d84966188e9a330d",
        "dimensions": "5607x2302",
        "paths": ("assets/1hour.png",),
        "role": "one_hour_result_chart_intermediate_render",
        "paper_versions": "",
        "canonical_correspondence": False,
        "distinct_table_cells_corresponded": 0,
        "version_specific_table_cells_corresponded": 0,
        "correspondence_kind": "historical_intermediate_raster_not_an_official_paper_figure",
    },
    "c2a0f78125d1e6204e1b62b0125a67a76440158e": {
        "sha256": "d9b8c7aadb8ee32402e20b5a2e7902721277c9f4dfd01297f73431fc8f169e12",
        "dimensions": "5605x2302",
        "paths": ("assets/1hour.png",),
        "role": "one_hour_result_chart_historical_render",
        "paper_versions": "v3",
        "canonical_correspondence": False,
        "distinct_table_cells_corresponded": 0,
        "version_specific_table_cells_corresponded": 0,
        "correspondence_kind": "complete_manual_visual_correspondence_to_v3_line_chart_pdf",
    },
    "a599314dbe06bacaabf6233f5b4ebd364dcd544f": {
        "sha256": "51b36c075015c5558d59e9cb0141aa7902e284599bfa0076f647577bbff9d9be",
        "dimensions": "5605x2311",
        "paths": ("assets/1hour.png",),
        "role": "one_hour_result_chart_current_render",
        "paper_versions": "v4",
        "canonical_correspondence": False,
        "distinct_table_cells_corresponded": 0,
        "version_specific_table_cells_corresponded": 0,
        "correspondence_kind": "complete_manual_visual_correspondence_to_v4_line_chart_pdf",
    },
}
BENCHMARK_TREE_SHA256 = "dfee104e3df70179e87037c2ba8620a2d952e0be337eb01741593f8918d306cc"
ACCURACY_DISPLAY_TOLERANCE = 0.05 + 1e-12
PERCENT_DISPLAY_TOLERANCE = 0.005 + 1e-12
RETURN_DISPLAY_TOLERANCE = 0.0005 + 1e-12
ASSETS_4H = ("BTC", "CL", "DJI", "ES", "VIX", "NQ", "QQQ", "SPX")

PINNED_SOURCE_SHA256 = {
    "README.md": "c1d9fe4d1f46302dddf0c9b7db76678a8cab73d1c186b8a1b3e74608b3fc4417",
    "default_config.py": "5de87cf7a1e5bf7dbab70a2cb72dfec2162dd70ef790a475b72f525f10e8bb0c",
    "web_interface.py": "ca5f88b8abe8d133a8d8b0bfb4183c4934dabd8d3f89b55030671bb43a113641",
    "decision_agent.py": "e55446b9edf2c273992987ca6b3fc5d55e366a7afbff23a564b0c5b6abeb3212",
    "indicator_agent.py": "318a5b5e3aa2611852d3a7ddd088ed986102d96462b3e96b927247af6be1b0cd",
    "pattern_agent.py": "0c581d97249b4c60a004f37f18204dd618fe16b0637c5bb0c1ee677375261dd7",
    "trend_agent.py": "951edc675531ceec9579c5c82d26141c93fb5908ee18b90a34ba6b5ffa778bad",
    "trading_graph.py": "280f1dfad1b9d6d73e3d57d7dc4497c2353e6fb19169c1a28d7d9332ab91f1da",
    "static_util.py": "6f6e2f30a587bd306274f1a532e8a389d16805bcf1a5b43de8d974288d096e05",
    "graph_util.py": "5d0b64dea20f9ece985b2cb3d395dd45a80b119d947db5bd5870f7e171120bf1",
    "requirements.txt": "e7ae5c5ba744bdb13317d3bf093d2f69bca4da2403c7abc860db32cd868d06bc",
}


# table|asset|method|Sharpe|Sortino|Cumulative Return %|Max Drawdown %
TABLE_1_TEXT = """
1|AAPL|LR|0.044|0.068|10.21|-29.59
1|AAPL|XGBoost|-0.241|-0.372|-5.35|-8.23
1|AAPL|TradingAgent|-0.189|-0.245|-13.69|15.25
1|AAPL|Our|-0.155|-0.264|-22.51|-25.44
1|AMZN|LR|0.298|0.709|153.29|-13.60
1|AMZN|XGBoost|-0.248|-0.324|-6.82|-10.31
1|AMZN|TradingAgent|0.199|0.482|20.53|4.85
1|AMZN|Our|0.236|0.502|44.85|-17.31
1|DJI|LR|0.332|0.779|41.46|-3.12
1|DJI|XGBoost|0.320|0.751|3.87|-2.61
1|DJI|TradingAgent|0.194|0.332|5.82|2.34
1|DJI|Our|0.271|0.590|15.50|-3.12
1|ES|LR|0.430|0.953|74.50|-5.90
1|ES|XGBoost|0.596|0.807|9.41|-1.88
1|ES|TradingAgent|0.017|0.030|1.25|8.55
1|ES|Our|0.339|0.661|25.43|-4.72
1|QQQ|LR|0.250|0.415|59.16|-10.74
1|QQQ|XGBoost|0.684|1.604|15.54|-2.01
1|QQQ|TradingAgent|0.067|0.112|3.82|3.66
1|QQQ|Our|0.516|0.000|1.44|-0.27
1|SPX|LR|0.467|1.017|77.78|-5.12
1|SPX|XGBoost|1.266|6.048|15.34|-0.37
1|SPX|TradingAgent|-0.158|-0.226|-6.11|7.68
1|SPX|Our|0.179|0.301|12.52|-8.24
1|NQ|LR|0.246|0.399|59.11|-11.53
1|NQ|XGBoost|-0.072|-0.108|-2.00|-5.10
1|NQ|TradingAgent|-0.092|-0.114|-5.04|9.26
1|NQ|Our|0.190|0.289|19.76|-5.46
1|VIX|TradingAgent|-0.129|-0.189|-30.40|32.28
1|VIX|Our|-0.141|-0.460|-38.70|-41.14
"""
TABLE_1_METRICS = ("sharpe", "sortino", "cumulative_return_pct", "max_drawdown_pct")


# asset|method|accuracy %|delta accuracy % (blank for baseline)|Rcc|Rmax|Rmin
TABLE_2_TEXT = """
BTC|Baseline|45.0||-0.009|1.220|-1.245
BTC|LR|46.0|2.2|-0.066|1.245|-1.210
BTC|XGBoost|45.3|0.7|-0.050|1.218|-1.331
BTC|Our|50.7|12.7|0.089|1.232|-1.212
CL|Baseline|41.0||-0.373|0.970|-1.348
CL|LR|54.3|32.4|-0.114|1.178|-1.141
CL|XGBoost|40.0|-2.4|-0.056|0.958|-1.151
CL|Our|55.0|34.1|-0.008|1.200|-1.119
DJI|Baseline|47.0||0.048|0.755|-0.793
DJI|LR|52.0|10.6|0.149|0.790|-0.725
DJI|XGBoost|47.3|0.6|-0.020|0.874|-0.660
DJI|Our|52.3|11.3|0.163|0.891|-0.649
ES|Baseline|51.0||-0.048|0.538|-0.552
ES|LR|43.0|-15.7|0.032|0.553|-0.546
ES|XGBoost|52.0|2.0|-0.182|0.440|-0.644
ES|Our|55.0|7.8|0.179|0.613|-0.485
VIX|Baseline|46.3||0.059|3.259|-3.157
VIX|LR|48.7|5.2|-0.140|3.407|-3.099
VIX|XGBoost|53.3|15.1|0.161|3.325|-3.110
VIX|Our|54.7|18.1|0.458|3.872|-2.851
NQ|Baseline|43.7||-0.140|0.646|-0.793
NQ|LR|48.7|11.4|0.147|0.782|-0.670
NQ|XGBoost|47.3|8.2|-0.007|0.706|-0.753
NQ|Our|55.3|26.5|0.216|0.814|-0.639
QQQ|Baseline|47.3||-0.048|0.930|-1.017
QQQ|LR|56.0|18.4|0.175|1.113|-0.849
QQQ|XGBoost|52.7|11.4|0.210|1.206|-0.973
QQQ|Our|59.7|26.2|0.211|1.052|-0.881
SPX|Baseline|47.3||-0.162|0.719|-0.862
SPX|LR|59.7|26.2|0.377|0.960|-0.648
SPX|XGBoost|60.0|26.8|0.050|0.782|-0.712
SPX|Our|63.7|34.6|0.341|0.965|-0.641
"""
TABLE_2_METRICS = ("accuracy_pct", "delta_accuracy_pct", "rcc", "rmax", "rmin")


# v1/v2 asset|method|accuracy %|delta accuracy % (blank for baseline)|Rcc|Rmax|Rmin|Rsim
V1_V2_TABLE_TEXT = """
BTC|Baseline|44.3||-0.259|1.115|-1.366|-0.277
BTC|Our|50.7|14.5|0.081|1.232|-1.249|0.004
CL|Baseline|49.0||-0.312|0.999|-1.384|-0.255
CL|Our|57.7|17.8|-0.195|1.181|-1.202|-0.133
DJI|Baseline|49.0||-0.096|0.770|-0.792|-0.131
DJI|Our|51.0|4.1|0.159|0.804|-0.758|0.121
ES|Baseline|41.3||0.006|0.560|-0.539|0.006
ES|Our|55.0|33.2|0.179|0.613|-0.485|0.179
GC|Baseline|47.7||0.018|0.502|-0.449|0.018
GC|Our|51.3|8.4|0.727|0.517|-0.434|0.027
NQ|Baseline|41.3||-0.033|0.717|-0.736|-0.033
NQ|Our|53.3|29.1|0.078|0.747|-0.705|0.078
QQQ|Baseline|39.7||-0.265|0.966|-1.038|-0.252
QQQ|Our|59.7|50.4|0.189|1.052|-0.952|0.193
SPX|Baseline|39.0||-0.108|0.789|-0.846|-0.090
SPX|Our|62.0|59.0|0.207|0.917|-0.717|0.197
"""
V1_V2_TABLE_METRICS = (
    "accuracy_pct",
    "delta_accuracy_pct",
    "rcc",
    "rmax",
    "rmin",
    "rsim",
)


BENCHMARK_PROPERTIES = {
    ("4h", "BTC"): ("2023-04-01", "2025-06-23", 5000),
    ("4h", "CL"): ("2022-04-25", "2025-06-19", 5000),
    ("4h", "DJI"): ("2015-08-26", "2025-05-16", 5000),
    ("4h", "ES"): ("2022-04-19", "2025-06-19", 5000),
    ("4h", "NQ"): ("2022-04-19", "2025-06-19", 5000),
    ("4h", "QQQ"): ("2015-08-24", "2025-05-16", 5000),
    ("4h", "SPX"): ("2015-08-25", "2025-05-16", 5000),
    ("4h", "VIX"): ("2020-10-20", "2025-08-27", 5000),
    ("1h", "BTC"): ("2025-02-21", "2025-09-13", 5000),
    ("1h", "CL"): ("2024-11-12", "2025-09-10", 5000),
    ("1h", "DJI"): ("2022-11-14", "2025-09-02", 5000),
    ("1h", "ES"): ("2024-11-11", "2025-09-10", 5000),
    ("1h", "NQ"): ("2024-11-11", "2025-09-10", 5000),
    ("1h", "QQQ"): ("2022-11-14", "2025-09-02", 5000),
    ("1h", "SPX"): ("2022-11-14", "2025-09-02", 5000),
    ("1h", "DAX"): ("2024-10-21", "2025-09-22", 5000),
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


def git_files(root: Path) -> List[str]:
    output = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in output.splitlines() if line]


def run_git(root: Path, *args: str, binary: bool = False) -> Any:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    ).stdout


def sha256_lines(lines: Sequence[str]) -> str:
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def historical_paths(source_root: Path, heads: Sequence[str]) -> List[str]:
    payload = subprocess.run(
        [
            "git",
            "-C",
            str(source_root),
            "-c",
            "core.quotePath=false",
            "log",
            *heads,
            "--pretty=format:",
            "--name-only",
            "-z",
        ],
        check=True,
        capture_output=True,
    ).stdout
    return sorted({part.decode("utf-8") for part in payload.split(b"\0") if part})


def png_dimensions(payload: bytes) -> str:
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("Expected a PNG historical result image")
    return f"{struct.unpack('>I', payload[16:20])[0]}x{struct.unpack('>I', payload[20:24])[0]}"


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_result_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in TABLE_1_TEXT.strip().splitlines():
        table, asset, method, *values = line.split("|")
        if len(values) != 4:
            raise ValueError(f"Malformed Table 1 row: {line}")
        for metric, value in zip(TABLE_1_METRICS, values):
            rows.append(
                {
                    "paper_table": int(table),
                    "asset": asset,
                    "method": method,
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    for line in TABLE_2_TEXT.strip().splitlines():
        asset, method, *values = line.split("|")
        if len(values) != 5:
            raise ValueError(f"Malformed Table 2 row: {line}")
        for metric, value in zip(TABLE_2_METRICS, values):
            if not value:
                continue
            rows.append(
                {
                    "paper_table": 2,
                    "asset": asset,
                    "method": method,
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    return rows


def v1_v2_paper_result_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in V1_V2_TABLE_TEXT.strip().splitlines():
        asset, method, *values = line.split("|")
        if len(values) != 6:
            raise ValueError(f"Malformed v1/v2 result row: {line}")
        for metric, value in zip(V1_V2_TABLE_METRICS, values):
            if not value:
                continue
            rows.append(
                {
                    "paper_table": "4h_performance_v1_v2",
                    "asset": asset,
                    "method": method,
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    if len(rows) != 88:
        raise RuntimeError(f"Expected 88 v1/v2 table cells, found {len(rows)}")
    return rows


def tex_table_numeric_tokens(main_tex: Path, label: str) -> List[Decimal]:
    """Extract data-area numerics while excluding TeX layout dimensions/rules."""
    text = main_tex.read_text(encoding="utf-8")
    marker = rf"\label{{{label}}}"
    label_position = text.index(marker)
    start = text.rfind(r"\begin{table}", 0, label_position)
    end = text.index(r"\end{table}", label_position) + len(r"\end{table}")
    if start < 0:
        raise RuntimeError(f"Could not find table containing {label} in {main_tex}")
    table = text[start:end]
    table = table[table.index(r"\midrule") + len(r"\midrule") : table.index(r"\bottomrule")]
    data_lines = []
    for line in table.splitlines():
        line = re.sub(r"(?<!\\)%.*$", "", line)
        if not line.strip() or r"\cmidrule" in line:
            continue
        line = re.sub(
            r"\\multirow\{[^}]+\}\{[^}]+\}\{([^}]+)\}",
            r"\1",
            line,
        )
        data_lines.append(line)
    return [
        Decimal(value.lstrip("+")) for value in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", "\n".join(data_lines))
    ]


def _row_values(rows: Sequence[Mapping[str, Any]]) -> List[Decimal]:
    return [Decimal(str(row["paper_value"])) for row in rows]


def paper_version_result_rows(paper_versions_root: Path) -> List[Dict[str, Any]]:
    """Enumerate every numeric result-table cell in every official revision."""
    old_rows = v1_v2_paper_result_rows()
    current_rows = paper_result_rows()
    portfolio_rows = [row for row in current_rows if row["paper_table"] == 1]
    expanded_4h_rows = [row for row in current_rows if row["paper_table"] == 2]
    expected = {
        ("v1", "tab:performance_comparison"): old_rows,
        ("v2", "tab:performance_comparison"): old_rows,
        ("v3", "tab:4hour_comparison"): expanded_4h_rows,
        ("v4", "tab:4hour_comparison"): expanded_4h_rows,
        ("v4", "tab:performance_metrics"): portfolio_rows,
    }
    for (version, label), rows in expected.items():
        observed = tex_table_numeric_tokens(paper_versions_root / f"source_{version}" / "main.tex", label)
        if observed != _row_values(rows):
            raise RuntimeError(
                f"Official {version} table {label} changed: observed {len(observed)} cells, expected {len(rows)}"
            )

    output: List[Dict[str, Any]] = []

    def append_rows(
        version: str,
        family: str,
        rows: Sequence[Mapping[str, Any]],
        author_image_sha256: str,
    ) -> None:
        for row in rows:
            rendered = bool(author_image_sha256)
            output.append(
                {
                    "paper_version": version,
                    "table_family": family,
                    "paper_table": row["paper_table"],
                    "asset": row["asset"],
                    "method": row["method"],
                    "metric": row["metric"],
                    "paper_value": row["paper_value"],
                    "official_tex_value_verified": True,
                    "author_rendered_correspondence": rendered,
                    "author_rendered_evidence_sha256": author_image_sha256,
                    "author_correspondence_status": (
                        "complete_manual_visual_correspondence_to_pinned_author_raster"
                        if rendered
                        else "no_author_rendered_table_correspondence_found"
                    ),
                    "independently_regenerated_from_native_result_path": False,
                    "paper_result_credit": False,
                }
            )

    old_image = HISTORICAL_RESULT_IMAGES["369deaf966fb19bd5cd9cc8bbcbd846d713f3afe"]["sha256"]
    expanded_image = HISTORICAL_RESULT_IMAGES["8cb62e42e92b73da79bade2c1b19bac4e1af0a8a"]["sha256"]
    append_rows("v1", "original_4h", old_rows, old_image)
    append_rows("v2", "original_4h", old_rows, old_image)
    append_rows("v3", "expanded_4h", expanded_4h_rows, expanded_image)
    append_rows("v4", "portfolio_performance", portfolio_rows, "")
    append_rows("v4", "expanded_4h", expanded_4h_rows, expanded_image)
    if len(output) != 600:
        raise RuntimeError(f"Expected 600 version-specific result cells, found {len(output)}")
    return output


def pdf_page_count(path: Path) -> int:
    output = subprocess.run(["pdfinfo", str(path)], check=True, capture_output=True, text=True).stdout
    match = re.search(r"^Pages:\s+(\d+)$", output, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"Could not read PDF page count: {path}")
    return int(match.group(1))


def paper_version_inventory(paper_versions_root: Path) -> List[Dict[str, Any]]:
    if sha256(paper_versions_root / "arxiv_api.xml") != PAPER_API_SHA256:
        raise RuntimeError("Pinned arXiv API version record changed")
    if sha256(paper_versions_root / "abs.html") != PAPER_ABS_SHA256:
        raise RuntimeError("Pinned arXiv abstract/version page changed")
    rows = []
    for version, expected in PAPER_VERSIONS.items():
        pdf = paper_versions_root / f"paper_{version}.pdf"
        archive = paper_versions_root / f"source_{version}.tar"
        source_dir = paper_versions_root / f"source_{version}"
        main_tex = source_dir / "main.tex"
        observed = {
            "pdf_sha256": sha256(pdf),
            "pdf_pages": pdf_page_count(pdf),
            "source_archive_sha256": sha256(archive),
            "source_files": sum(path.is_file() for path in source_dir.rglob("*")),
            "main_tex_sha256": sha256(main_tex),
            "line_chart_pdf_sha256": (
                sha256(source_dir / "assets/line_chart.pdf") if (source_dir / "assets/line_chart.pdf").is_file() else ""
            ),
        }
        with tarfile.open(archive, "r:*") as handle:
            archive_files = sum(member.isfile() for member in handle.getmembers())
        observed["source_archive_files"] = archive_files
        for key in (
            "pdf_sha256",
            "pdf_pages",
            "source_archive_sha256",
            "source_files",
            "main_tex_sha256",
            "line_chart_pdf_sha256",
        ):
            if observed[key] != expected[key]:
                raise RuntimeError(f"Official paper {version} {key} changed: {observed[key]}")
        if archive_files != expected["source_files"]:
            raise RuntimeError(f"Official paper {version} archive/extracted file counts differ")
        rows.append(
            {
                "paper_version": version,
                "submission_date": expected["submission_date"],
                "pdf_url": f"https://arxiv.org/pdf/2509.09995{version}",
                **observed,
                "table_family": expected["table_family"],
                "numeric_result_cells": expected["numeric_result_cells"],
                "author_rendered_correspondence_cells": expected["author_rendered_correspondence_cells"],
                "native_result_cells_independently_regenerated": 0,
            }
        )
    return rows


def table_2_records() -> List[Dict[str, Any]]:
    records = []
    for line in TABLE_2_TEXT.strip().splitlines():
        asset, method, accuracy, delta, rcc, rmax, rmin = line.split("|")
        records.append(
            {
                "asset": asset,
                "method": method,
                "accuracy_pct": float(accuracy),
                "delta_accuracy_pct": None if not delta else float(delta),
                "rcc": float(rcc),
                "rmax": float(rmax),
                "rmin": float(rmin),
            }
        )
    return records


def natural_csv_files(directory: Path) -> List[Path]:
    files = list(directory.glob("*.csv"))

    def number(path: Path) -> int:
        match = re.search(r"_(\d+)\.csv$", path.name)
        if not match:
            raise ValueError(f"Unexpected benchmark filename: {path}")
        return int(match.group(1))

    return sorted(files, key=number)


def benchmark_directory(source_root: Path, horizon: str, asset: str) -> Path:
    base = source_root / "benchmark"
    return base / "1h" / asset.lower() if horizon == "1h" else base / asset.lower()


def benchmark_tree_hash(source_root: Path) -> str:
    digest = hashlib.sha256()
    for relative in sorted(path for path in git_files(source_root) if path.startswith("benchmark/")):
        digest.update(f"{sha256(source_root / relative)}  {relative}\n".encode())
    return digest.hexdigest()


def load_4h_arrays(source_root: Path) -> Dict[str, np.ndarray]:
    arrays: Dict[str, np.ndarray] = {}
    for asset in ASSETS_4H:
        files = natural_csv_files(benchmark_directory(source_root, "4h", asset))
        values = [pd.read_csv(path)[["Close", "High", "Low"]].to_numpy(dtype=float) for path in files]
        array = np.stack(values)
        if array.shape != (100, 100, 3):
            raise RuntimeError(f"Unexpected {asset} benchmark shape: {array.shape}")
        arrays[asset] = array
    return arrays


def linear_regression_directions(close: np.ndarray, window_end: int) -> np.ndarray:
    """Return slope>0 using an OLS line over 40 closes ending before window_end."""
    values = close[:, window_end - 40 : window_end]
    x = np.arange(40, dtype=float)
    centered_x = x - x.mean()
    slopes = ((values - values.mean(axis=1, keepdims=True)) * centered_x).sum(axis=1)
    return slopes > 0


def directional_accuracy(
    close: np.ndarray, directions_long: np.ndarray, reference_index: int = 96
) -> Tuple[int, float]:
    future = close[:, 97:100]
    correct = np.where(
        directions_long[:, None],
        future > close[:, reference_index, None],
        future < close[:, reference_index, None],
    )
    hits = int(correct.sum())
    return hits, 100.0 * hits / 300.0


def extrema_returns(values: np.ndarray, directions_long: np.ndarray, reference_index: int = 96) -> Tuple[float, float]:
    close = values[:, :, 0]
    high = values[:, :, 1]
    low = values[:, :, 2]
    current = close[:, reference_index]
    best = np.where(
        directions_long,
        (high[:, 97:100].max(axis=1) / current - 1.0) * 100.0,
        (1.0 - low[:, 97:100].min(axis=1) / current) * 100.0,
    )
    worst = np.where(
        directions_long,
        (low[:, 97:100].min(axis=1) / current - 1.0) * 100.0,
        (1.0 - high[:, 97:100].max(axis=1) / current) * 100.0,
    )
    return float(best.mean()), float(worst.mean())


def lr_alignment_audit(arrays: Mapping[str, np.ndarray]) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int]]]:
    records = table_2_records()
    published = {row["asset"]: row["accuracy_pct"] for row in records if row["method"] == "LR"}
    rows = []
    for asset in ASSETS_4H:
        close = arrays[asset][:, :, 0]
        described = linear_regression_directions(close, 97)
        inferred = linear_regression_directions(close, 94)
        described_hits, described_value = directional_accuracy(close, described)
        inferred_hits, inferred_value = directional_accuracy(close, inferred)
        published_value = published[asset]
        rows.append(
            {
                "asset": asset,
                "published_accuracy_pct": published_value,
                "paper_described_feature_rows_zero_based": "57:97",
                "paper_described_reference_close_index": 96,
                "paper_described_correct_hits_of_300": described_hits,
                "paper_described_accuracy_pct": described_value,
                "paper_described_absolute_error": abs(published_value - described_value),
                "paper_described_status": (
                    "display_match"
                    if abs(published_value - described_value) <= ACCURACY_DISPLAY_TOLERANCE
                    else "mismatch"
                ),
                "inferred_feature_rows_zero_based": "54:94",
                "inferred_reference_close_index": 96,
                "undocumented_feature_gap_rows": "94:97",
                "inferred_correct_hits_of_300": inferred_hits,
                "inferred_accuracy_pct": inferred_value,
                "inferred_absolute_error": abs(published_value - inferred_value),
                "inferred_status": (
                    "display_match_only_with_undocumented_three_bar_gap"
                    if abs(published_value - inferred_value) <= ACCURACY_DISPLAY_TOLERANCE
                    else "mismatch"
                ),
            }
        )

    # Exhaust every 40-close window ending no later than the current close and
    # every possible reference close before the three outcomes. Compare at the
    # paper's one-decimal precision.
    published_vector = np.asarray([published[asset] for asset in ASSETS_4H])
    direction_cache = {
        end: {asset: linear_regression_directions(arrays[asset][:, :, 0], end) for asset in ASSETS_4H}
        for end in range(40, 98)
    }
    exact_alignments: List[Tuple[int, int]] = []
    for end in range(40, 98):
        for reference in range(97):
            values = []
            for asset in ASSETS_4H:
                _, value = directional_accuracy(arrays[asset][:, :, 0], direction_cache[end][asset], reference)
                values.append(round(value, 1))
            if np.array_equal(np.asarray(values), published_vector):
                exact_alignments.append((end, reference))
    return rows, exact_alignments


def benchmark_inventory(source_root: Path) -> List[Dict[str, Any]]:
    rows = []
    expected_columns = ("Datetime", "Close", "High", "Low", "Open", "Volume")
    for (horizon, asset), (paper_start, paper_end, paper_bars) in BENCHMARK_PROPERTIES.items():
        directory = benchmark_directory(source_root, horizon, asset)
        files = natural_csv_files(directory)
        frames = []
        hashes = []
        numbers = []
        monotonic = True
        unique_within_file = True
        columns_match = True
        row_counts = []
        for path in files:
            frame = pd.read_csv(path)
            timestamps = pd.to_datetime(frame["Datetime"])
            frames.append(frame)
            hashes.append(sha256(path))
            numbers.append(int(re.search(r"_(\d+)\.csv$", path.name).group(1)))
            row_counts.append(len(frame))
            monotonic = monotonic and timestamps.is_monotonic_increasing
            unique_within_file = unique_within_file and not timestamps.duplicated().any()
            columns_match = columns_match and tuple(frame.columns) == expected_columns
        combined = pd.concat(frames, ignore_index=True)
        timestamps = pd.to_datetime(combined["Datetime"])
        observed_start = timestamps.min().date().isoformat()
        observed_end = timestamps.max().date().isoformat()
        sample_digest = hashlib.sha256()
        for path, file_hash in zip(files, hashes):
            relative = path.relative_to(source_root).as_posix()
            sample_digest.update(f"{file_hash}  {relative}\n".encode())
        rows.append(
            {
                "horizon": horizon,
                "asset": asset,
                "paper_full_panel_start_date": paper_start,
                "released_segment_union_start_date": observed_start,
                "start_date_match": observed_start == paper_start,
                "paper_full_panel_end_date": paper_end,
                "released_segment_union_end_date": observed_end,
                "end_date_match": observed_end == paper_end,
                "paper_full_panel_bars": paper_bars,
                "released_segment_files": len(files),
                "released_rows_total_with_overlap": sum(row_counts),
                "released_distinct_timestamps": int(timestamps.nunique()),
                "minimum_rows_per_segment": min(row_counts),
                "maximum_rows_per_segment": max(row_counts),
                "file_numbers_1_through_100_complete": numbers == list(range(1, 101)),
                "all_segments_monotonic": monotonic,
                "all_timestamps_unique_within_segment": unique_within_file,
                "columns_match_ohlcv_schema": columns_match,
                "duplicate_file_payloads": len(hashes) - len(set(hashes)),
                "sampled_segment_tree_sha256": sample_digest.hexdigest(),
                "status": (
                    "released_sampled_segments_complete_endpoints_match_full_panel_absent"
                    if observed_start == paper_start
                    and observed_end == paper_end
                    and len(files) == 100
                    and min(row_counts) == max(row_counts) == 100
                    else "released_benchmark_mismatch"
                ),
            }
        )
    return sorted(rows, key=lambda row: (row["horizon"], row["asset"]))


def source_inventory(source_root: Path) -> List[Dict[str, Any]]:
    rows = []
    for relative in git_files(source_root):
        if relative.startswith("benchmark/"):
            continue
        path = source_root / relative
        if relative.startswith("assets/") or relative.startswith("templates/assets/"):
            role = "static_illustration_or_web_asset_not_numeric_result_path"
        elif relative.startswith("tests/"):
            role = "provider_integration_test_not_paper_benchmark_test"
        elif relative.endswith((".py", ".html")):
            role = "framework_or_web_interface_source"
        else:
            role = "documentation_configuration_or_license"
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "role": role,
            }
        )
    return rows


def history_path_role(path: str) -> str:
    lower = path.lower()
    if lower.startswith("benchmark/") and lower.endswith(".csv"):
        return "released_sampled_benchmark_segment"
    if path in HISTORICAL_RESULT_PATHS:
        return "author_rendered_result_output_no_underlying_array"
    if lower in {
        "assets/benchmark.png",
        "assets/benchmark_1h.png",
        "assets/benchmark_4h.png",
    }:
        return "author_rendered_benchmark_coverage_figure"
    if (lower.endswith(".csv") and not lower.startswith("benchmark/")) or lower.endswith(NATIVE_RESULT_SUFFIXES):
        return "native_result_artifact_candidate"
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".mp4")):
        return "documentation_demo_or_qualitative_paper_asset"
    if lower.endswith((".py", ".html")):
        return "framework_or_web_interface_source"
    return "documentation_configuration_or_license"


def public_source_history(
    source_root: Path,
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    Dict[str, Any],
]:
    """Exhaust the pinned public branch surface, including deleted history."""
    shallow = str(run_git(source_root, "rev-parse", "--is-shallow-repository")).strip()
    if shallow != "false":
        raise RuntimeError("QuantAgent source checkout is shallow")

    remote_lines = sorted(
        line
        for line in str(
            run_git(
                source_root,
                "for-each-ref",
                "--format=%(refname) %(objectname)",
                "refs/remotes/origin",
            )
        ).splitlines()
        if not line.startswith("refs/remotes/origin/HEAD ")
    )
    if sha256_lines(remote_lines) != PUBLIC_REMOTE_REF_SHA256:
        raise RuntimeError(f"Pinned public remote-ref snapshot changed: {remote_lines}")
    discovered_heads = {
        ref.removeprefix("refs/remotes/origin/"): commit
        for ref, commit in (line.split(" ", 1) for line in remote_lines)
    }
    if discovered_heads != PUBLIC_BRANCH_HEADS:
        raise RuntimeError(f"Pinned public branch heads changed: {discovered_heads}")
    tags = str(run_git(source_root, "for-each-ref", "--format=%(refname)", "refs/tags")).splitlines()
    if tags:
        raise RuntimeError(f"Unexpected public tag refs require review: {tags}")

    heads = list(PUBLIC_BRANCH_HEADS.values())
    commits = str(run_git(source_root, "rev-list", "--reverse", *heads)).splitlines()
    if len(commits) != PUBLIC_HISTORY_COMMIT_COUNT or sha256_lines(commits) != PUBLIC_HISTORY_COMMIT_SHA256:
        raise RuntimeError("Pinned QuantAgent reachable commit history changed")
    paths = historical_paths(source_root, heads)
    if len(paths) != PUBLIC_HISTORY_PATH_COUNT or sha256_lines(paths) != PUBLIC_HISTORY_PATH_SHA256:
        raise RuntimeError("Pinned QuantAgent reachable path history changed")

    object_lines = str(run_git(source_root, "rev-list", "--objects", *heads)).splitlines()
    object_ids = [line.split(" ", 1)[0] for line in object_lines]
    object_types = subprocess.run(
        ["git", "-C", str(source_root), "cat-file", "--batch-check=%(objecttype)"],
        input="\n".join(object_ids) + "\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    object_counts = dict(Counter(object_types))
    if object_counts != PUBLIC_HISTORY_OBJECT_COUNTS:
        raise RuntimeError(f"Pinned QuantAgent object census changed: {object_counts}")
    fsck = str(run_git(source_root, "fsck", "--full", "--no-reflogs", "--unreachable")).strip()
    if fsck:
        raise RuntimeError(f"Unreachable QuantAgent Git objects require review: {fsck}")

    branch_commit_sets = {
        branch: set(str(run_git(source_root, "rev-list", head)).splitlines())
        for branch, head in PUBLIC_BRANCH_HEADS.items()
    }
    commit_trees: Dict[str, Dict[str, str]] = {}
    commit_meta: Dict[str, Tuple[str, str]] = {}
    commit_rows: List[Dict[str, Any]] = []
    result_blob_commits: Dict[str, set[str]] = {}
    result_blob_paths: Dict[str, set[str]] = {}
    for commit in commits:
        entries: Dict[str, str] = {}
        for line in str(
            run_git(
                source_root,
                "-c",
                "core.quotePath=false",
                "ls-tree",
                "-r",
                commit,
            )
        ).splitlines():
            left, path = line.split("\t", 1)
            _, object_type, object_id = left.split()
            if object_type == "blob":
                entries[path] = object_id
                if path in HISTORICAL_RESULT_PATHS:
                    result_blob_commits.setdefault(object_id, set()).add(commit)
                    result_blob_paths.setdefault(object_id, set()).add(path)
        commit_trees[commit] = entries
        commit_date, subject = (
            str(run_git(source_root, "show", "-s", "--format=%cI%x00%s", commit)).rstrip("\n").split("\0", 1)
        )
        commit_meta[commit] = (commit_date, subject)
        memberships = sorted(branch for branch, members in branch_commit_sets.items() if commit in members)
        native_candidates = sorted(
            path for path in entries if history_path_role(path) == "native_result_artifact_candidate"
        )
        commit_rows.append(
            {
                "commit": commit,
                "commit_date": commit_date,
                "subject": subject,
                "public_branch_membership": ";".join(memberships),
                "tree_path_count": len(entries),
                "benchmark_csv_path_count": sum(
                    path.startswith("benchmark/") and path.endswith(".csv") for path in entries
                ),
                "author_rendered_result_path_count": sum(path in HISTORICAL_RESULT_PATHS for path in entries),
                "native_result_artifact_candidate_count": len(native_candidates),
                "native_result_artifact_candidate_paths": ";".join(native_candidates),
                "paper_result_credit": False,
            }
        )

    present_counts = Counter(path for tree in commit_trees.values() for path in tree)
    head_trees = {branch: commit_trees[head] for branch, head in PUBLIC_BRANCH_HEADS.items()}
    path_rows = []
    for path in paths:
        role = history_path_role(path)
        path_rows.append(
            {
                "relative_path": path,
                "suffix": Path(path).suffix.lower(),
                "history_role": role,
                "commits_present": present_counts[path],
                "public_branch_heads_present": ";".join(branch for branch, tree in head_trees.items() if path in tree),
                "native_result_artifact_candidate": role == "native_result_artifact_candidate",
                "author_rendered_result_output": path in HISTORICAL_RESULT_PATHS,
                "paper_result_credit": False,
            }
        )
    native_candidates = [row for row in path_rows if row["native_result_artifact_candidate"]]
    if native_candidates:
        raise RuntimeError(f"Historical native result candidates require manual review: {native_candidates}")

    if set(result_blob_commits) != set(HISTORICAL_RESULT_IMAGES):
        raise RuntimeError(f"Pinned historical result-image blob set changed: {sorted(result_blob_commits)}")
    commit_order = {commit: index for index, commit in enumerate(commits)}
    image_rows = []
    for object_id, expected in HISTORICAL_RESULT_IMAGES.items():
        payload = run_git(source_root, "cat-file", "blob", object_id, binary=True)
        paths_for_blob = tuple(sorted(result_blob_paths[object_id]))
        observed_sha256 = hashlib.sha256(payload).hexdigest()
        observed_dimensions = png_dimensions(payload)
        if (
            observed_sha256 != expected["sha256"]
            or observed_dimensions != expected["dimensions"]
            or paths_for_blob != expected["paths"]
        ):
            raise RuntimeError(f"Historical result image changed: {object_id}")
        blob_commits = sorted(result_blob_commits[object_id], key=commit_order.__getitem__)
        first_commit = blob_commits[0]
        last_commit = blob_commits[-1]
        image_rows.append(
            {
                "git_blob": object_id,
                "sha256": observed_sha256,
                "bytes": len(payload),
                "dimensions": observed_dimensions,
                "historical_paths": ";".join(paths_for_blob),
                "role": expected["role"],
                "paper_versions_corresponded": expected["paper_versions"],
                "commits_present": len(blob_commits),
                "first_seen_commit": first_commit,
                "first_seen_date": commit_meta[first_commit][0],
                "last_seen_commit": last_commit,
                "last_seen_date": commit_meta[last_commit][0],
                "reachable_from_public_branches": ";".join(
                    branch
                    for branch, members in branch_commit_sets.items()
                    if any(commit in members for commit in blob_commits)
                ),
                "canonical_correspondence": expected["canonical_correspondence"],
                "distinct_table_cells_corresponded": expected["distinct_table_cells_corresponded"],
                "version_specific_table_cells_corresponded": expected["version_specific_table_cells_corresponded"],
                "correspondence_kind": expected["correspondence_kind"],
                "underlying_numeric_result_array_shipped": False,
                "independently_regenerated": False,
                "paper_result_credit": False,
            }
        )

    summary: Dict[str, Any] = {
        "audit_date": "2026-08-30",
        "repository_shallow": False,
        "public_branch_heads": PUBLIC_BRANCH_HEADS,
        "public_branches_total": len(PUBLIC_BRANCH_HEADS),
        "public_tags_total": 0,
        "reachable_commits_total": len(commits),
        "reachable_commit_list_sha256": sha256_lines(commits),
        "unique_historical_paths_total": len(paths),
        "historical_path_list_sha256": sha256_lines(paths),
        "reachable_object_counts": object_counts,
        "unreachable_objects_total": 0,
        "historical_benchmark_csv_paths_total": sum(
            row["history_role"] == "released_sampled_benchmark_segment" for row in path_rows
        ),
        "historical_benchmark_asset_horizon_sets_total": 18,
        "historical_native_result_artifact_candidates_total": 0,
        "historical_author_rendered_result_paths_total": len(HISTORICAL_RESULT_PATHS),
        "historical_unique_result_image_blobs_total": len(image_rows),
        "historical_unique_table_image_blobs_total": sum("table" in row["role"] for row in image_rows),
        "historical_unique_one_hour_result_chart_blobs_total": sum("one_hour" in row["role"] for row in image_rows),
        "official_one_hour_figure_author_raster_correspondences_total": sum(
            "one_hour" in row["role"] and bool(row["paper_versions_corresponded"]) for row in image_rows
        ),
        "intermediate_nonpaper_one_hour_result_rasters_total": sum(
            "one_hour" in row["role"] and not row["paper_versions_corresponded"] for row in image_rows
        ),
        "distinct_table_cells_author_rendered_correspondence": sum(
            int(row["distinct_table_cells_corresponded"]) for row in image_rows
        ),
        "version_specific_table_cells_author_rendered_correspondence": sum(
            int(row["version_specific_table_cells_corresponded"]) for row in image_rows
        ),
        "historical_native_predictions_evaluators_returns_or_portfolio_paths": False,
        "paper_result_credit_from_author_rendered_images": False,
    }
    if summary["historical_benchmark_csv_paths_total"] != 1800:
        raise RuntimeError("Historical benchmark CSV census changed")
    if summary["distinct_table_cells_author_rendered_correspondence"] != 240:
        raise RuntimeError("Historical table correspondence census changed")
    if summary["version_specific_table_cells_author_rendered_correspondence"] != 480:
        raise RuntimeError("Version-specific table correspondence census changed")
    return commit_rows, path_rows, image_rows, summary


def postpaper_official_source_audit(
    source_root: Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Inventory official changes after the v4 paper-era source snapshot."""
    current_heads = list(PUBLIC_BRANCH_HEADS.values())
    paper_heads = list(PAPER_ERA_PUBLIC_BRANCH_HEADS.values())
    commits = str(run_git(source_root, "rev-list", "--reverse", *current_heads, "--not", *paper_heads)).splitlines()
    if len(commits) != POSTPAPER_OFFICIAL_COMMIT_COUNT or sha256_lines(commits) != POSTPAPER_OFFICIAL_COMMIT_SHA256:
        raise RuntimeError("QuantHarness post-paper official commit surface changed")
    changed_paths: set[str] = set()
    rows: List[Dict[str, Any]] = []
    for commit in commits:
        paths = sorted(
            path
            for path in str(
                run_git(
                    source_root,
                    "diff-tree",
                    "--root",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    commit,
                )
            ).splitlines()
            if path
        )
        changed_paths.update(paths)
        commit_date, author_name, author_email, subject = (
            str(run_git(source_root, "show", "-s", "--format=%cI%x00%an%x00%ae%x00%s", commit))
            .rstrip("\n")
            .split("\0", 3)
        )
        native_result_paths = [path for path in paths if history_path_role(path) == "native_result_artifact_candidate"]
        if native_result_paths:
            raise RuntimeError(f"Post-paper official native result paths require review: {native_result_paths}")
        rows.append(
            {
                "commit": commit,
                "commit_date": commit_date,
                "author_name": author_name,
                "author_email": author_email,
                "subject": subject,
                "changed_path_count": len(paths),
                "changed_paths": ";".join(paths),
                "native_result_artifact_path_count": 0,
                "classification": "postpaper_provider_documentation_or_interface_change",
                "paper_result_credit": False,
            }
        )
    ordered_paths = sorted(changed_paths)
    if (
        len(ordered_paths) != POSTPAPER_OFFICIAL_CHANGED_PATH_COUNT
        or sha256_lines(ordered_paths) != POSTPAPER_OFFICIAL_CHANGED_PATH_SHA256
    ):
        raise RuntimeError("QuantHarness post-paper official path surface changed")
    return rows, {
        "paper_era_branch_heads": PAPER_ERA_PUBLIC_BRANCH_HEADS,
        "current_branch_heads": PUBLIC_BRANCH_HEADS,
        "postpaper_commits": len(commits),
        "postpaper_commit_sha256": sha256_lines(commits),
        "postpaper_changed_paths": len(ordered_paths),
        "postpaper_changed_path_sha256": sha256_lines(ordered_paths),
        "native_result_artifacts_added": 0,
        "paper_result_credit": False,
    }


def _object_ids(source_root: Path, heads: Sequence[str]) -> set[str]:
    return {line.split(" ", 1)[0] for line in str(run_git(source_root, "rev-list", "--objects", *heads)).splitlines()}


def _git_csv(source_root: Path, commit: str, path: str) -> Tuple[bytes, List[Dict[str, str]]]:
    payload = run_git(source_root, "show", f"{commit}:{path}", binary=True)
    return payload, list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))


def public_fork_audit(
    source_root: Path, branch_ref_snapshot: Path
) -> Tuple[
    List[Dict[str, str]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    Dict[str, Any],
]:
    """Fail closed over every accessible public-fork branch and unique head."""
    if sha256(branch_ref_snapshot) != PUBLIC_FORK_SNAPSHOT_SHA256:
        raise RuntimeError("QuantHarness public-fork branch snapshot hash changed")
    with branch_ref_snapshot.open(newline="", encoding="utf-8") as handle:
        branch_rows = list(csv.DictReader(handle))
    expected_columns = {
        "repository",
        "branch",
        "head_commit",
        "repository_created_at",
        "repository_pushed_at",
        "repository_archived",
        "repository_disabled",
        "head_committed_at",
        "head_author_login",
        "head_author_name",
        "head_author_email",
        "head_subject",
    }
    if not branch_rows or set(branch_rows[0]) != expected_columns:
        raise RuntimeError("QuantHarness public-fork branch snapshot schema changed")
    branch_rows.sort(key=lambda row: (row["repository"].lower(), row["branch"].lower(), row["head_commit"]))
    canonical_refs = [f"{row['repository']}\t{row['branch']}\t{row['head_commit']}" for row in branch_rows]
    repositories = {row["repository"] for row in branch_rows}
    unique_heads = sorted({row["head_commit"] for row in branch_rows})
    if (
        len(branch_rows) != PUBLIC_FORK_BRANCH_REF_COUNT
        or len(repositories) != PUBLIC_FORK_ACCESSIBLE_COUNT
        or len({(row["repository"], row["branch"]) for row in branch_rows}) != len(branch_rows)
        or sha256_lines(canonical_refs) != PUBLIC_FORK_BRANCH_REF_SHA256
        or len(unique_heads) != PUBLIC_FORK_UNIQUE_HEAD_COUNT
        or sha256_lines(unique_heads) != PUBLIC_FORK_UNIQUE_HEAD_SHA256
    ):
        raise RuntimeError("QuantHarness complete public-fork branch surface changed")
    for head in unique_heads:
        subprocess.run(
            ["git", "-C", str(source_root), "cat-file", "-e", f"{head}^{{commit}}"],
            check=True,
            capture_output=True,
        )

    refs_by_head: Dict[str, List[Dict[str, str]]] = {}
    for row in branch_rows:
        refs_by_head.setdefault(row["head_commit"], []).append(row)
    base_heads = list(PUBLIC_BRANCH_HEADS.values())
    extra_commits_by_head: Dict[str, List[str]] = {}
    changed_paths_by_head: Dict[str, List[str]] = {}
    path_heads: Dict[str, set[str]] = {}
    head_rows: List[Dict[str, Any]] = []
    for head in unique_heads:
        extra_commits = sorted(str(run_git(source_root, "rev-list", head, "--not", *base_heads)).splitlines())
        paths: set[str] = set()
        for commit in extra_commits:
            paths.update(
                path
                for path in str(
                    run_git(
                        source_root,
                        "diff-tree",
                        "--root",
                        "--no-commit-id",
                        "--name-only",
                        "-r",
                        commit,
                    )
                ).splitlines()
                if path
            )
        ordered_paths = sorted(paths)
        for path in ordered_paths:
            path_heads.setdefault(path, set()).add(head)
        extra_commits_by_head[head] = extra_commits
        changed_paths_by_head[head] = ordered_paths
        refs = refs_by_head[head]
        repositories_for_head = sorted({row["repository"] for row in refs})
        branches_for_head = sorted({row["branch"] for row in refs})
        if not extra_commits:
            classification = (
                "author_personal_fork_official_history_snapshot"
                if "wyattz23/QA" in repositories_for_head
                else "official_history_reachable"
            )
        elif head in {PUBLIC_FORK_TASS_MAIN_HEAD, PUBLIC_FORK_TASS_TEST_HEAD}:
            classification = "unaffiliated_method_adaptation_with_nonpaper_backtest_outputs"
        else:
            classification = "unaffiliated_code_data_or_interface_extension"
        head_date, author_name, author_email, subject = (
            str(run_git(source_root, "show", "-s", "--format=%cI%x00%an%x00%ae%x00%s", head))
            .rstrip("\n")
            .split("\0", 3)
        )
        head_rows.append(
            {
                "head_commit": head,
                "head_date": head_date,
                "head_author_name": author_name,
                "head_author_email": author_email,
                "head_subject": subject,
                "repository_count": len(repositories_for_head),
                "repositories": ";".join(repositories_for_head),
                "branch_count": len(refs),
                "branches": ";".join(branches_for_head),
                "extra_commit_count_beyond_current_official_history": len(extra_commits),
                "extra_changed_path_count": len(ordered_paths),
                "classification": classification,
                "author_attributed_paper_lineage": "wyattz23/QA" in repositories_for_head,
                "paper_result_credit": False,
            }
        )

    divergent_heads = sorted(head for head in unique_heads if extra_commits_by_head[head])
    all_extra_commits = sorted({commit for commits in extra_commits_by_head.values() for commit in commits})
    all_changed_paths = sorted(path_heads)
    if (
        len(divergent_heads) != PUBLIC_FORK_DIVERGENT_HEAD_COUNT
        or sha256_lines(divergent_heads) != PUBLIC_FORK_DIVERGENT_HEAD_SHA256
        or len(all_extra_commits) != PUBLIC_FORK_EXTRA_COMMIT_COUNT
        or sha256_lines(all_extra_commits) != PUBLIC_FORK_EXTRA_COMMIT_SHA256
        or len(all_changed_paths) != PUBLIC_FORK_CHANGED_PATH_COUNT
        or sha256_lines(all_changed_paths) != PUBLIC_FORK_CHANGED_PATH_SHA256
    ):
        raise RuntimeError("QuantHarness divergent public-fork surface changed")

    commit_heads: Dict[str, set[str]] = {}
    for head, commits in extra_commits_by_head.items():
        for commit in commits:
            commit_heads.setdefault(commit, set()).add(head)
    commit_rows: List[Dict[str, Any]] = []
    for commit in all_extra_commits:
        commit_date, author_name, author_email, subject = (
            str(run_git(source_root, "show", "-s", "--format=%cI%x00%an%x00%ae%x00%s", commit))
            .rstrip("\n")
            .split("\0", 3)
        )
        paths = sorted(
            path
            for path in str(
                run_git(
                    source_root,
                    "diff-tree",
                    "--root",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    commit,
                )
            ).splitlines()
            if path
        )
        result_like = [
            path
            for path in paths
            if any(
                token in path.lower()
                for token in (
                    "result",
                    "backtest",
                    "performance",
                    "metric",
                    "equity",
                    "portfolio",
                    "prediction",
                    "signal",
                    "trade",
                    "return",
                    "history",
                )
            )
        ]
        commit_rows.append(
            {
                "commit": commit,
                "commit_date": commit_date,
                "author_name": author_name,
                "author_email": author_email,
                "subject": subject,
                "reachable_divergent_head_count": len(commit_heads[commit]),
                "changed_path_count": len(paths),
                "result_like_changed_path_count": len(result_like),
                "result_like_changed_paths": ";".join(result_like),
                "paper_result_credit": False,
            }
        )

    path_rows: List[Dict[str, Any]] = []
    for path in all_changed_paths:
        lower = path.lower()
        if lower == "trading_data.db":
            role = "community_live_analysis_database"
        elif lower.startswith(("strategy_results/", "backtest_results", "docs/backtest_findings")):
            role = "unaffiliated_backtest_output_or_supporting_path"
        elif any(
            token in lower
            for token in (
                "result",
                "backtest",
                "performance",
                "metric",
                "equity",
                "portfolio",
                "prediction",
                "signal",
                "trade",
                "return",
                "history",
            )
        ):
            role = "result_like_community_path_manual_boundary"
        else:
            role = "community_code_configuration_documentation_or_build_path"
        path_rows.append(
            {
                "relative_path": path,
                "suffix": Path(path).suffix.lower(),
                "divergent_head_count": len(path_heads[path]),
                "role": role,
                "attributable_paper_result_artifact": False,
                "paper_result_credit": False,
            }
        )

    base_objects = _object_ids(source_root, base_heads)
    fork_object_lines = str(run_git(source_root, "rev-list", "--objects", *unique_heads)).splitlines()
    fork_objects = {line.split(" ", 1)[0] for line in fork_object_lines}
    object_path: Dict[str, str] = {}
    for line in fork_object_lines:
        object_id, *rest = line.split(" ", 1)
        if rest:
            object_path.setdefault(object_id, rest[0])
    new_objects = sorted(fork_objects - base_objects)
    if (
        len(new_objects) != sum(PUBLIC_FORK_NEW_OBJECT_COUNTS.values())
        or sha256_lines(new_objects) != PUBLIC_FORK_NEW_OBJECT_SHA256
    ):
        raise RuntimeError("QuantHarness public-fork new-object surface changed")
    metadata = subprocess.run(
        [
            "git",
            "-C",
            str(source_root),
            "cat-file",
            "--batch-check=%(objectname) %(objecttype) %(objectsize)",
        ],
        input="\n".join(new_objects) + "\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    object_counts: Counter[str] = Counter()
    new_blobs: List[str] = []
    blob_sizes: Dict[str, int] = {}
    for line in metadata:
        object_id, object_type, object_size = line.split()
        object_counts[object_type] += 1
        if object_type == "blob":
            new_blobs.append(object_id)
            blob_sizes[object_id] = int(object_size)
    new_blobs.sort()
    if (
        dict(object_counts) != PUBLIC_FORK_NEW_OBJECT_COUNTS
        or sha256_lines(new_blobs) != PUBLIC_FORK_NEW_BLOB_SHA256
        or sum(blob_sizes.values()) != PUBLIC_FORK_NEW_BLOB_BYTES
    ):
        raise RuntimeError("QuantHarness public-fork blob census changed")

    paper_groups: Dict[Tuple[int, str, str], List[float]] = {}
    for row in paper_result_rows():
        key = (int(row["paper_table"]), str(row["asset"]), str(row["method"]))
        paper_groups.setdefault(key, []).append(float(row["paper_value"]))
    number_pattern = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
    text_blobs_scanned = 0
    complete_paper_row_matches: List[Tuple[str, int, str, str]] = []
    db_blobs: List[str] = []
    for blob in new_blobs:
        path = object_path.get(blob, "")
        if path.lower().endswith(".db"):
            db_blobs.append(blob)
        if blob_sizes[blob] > 5_000_000:
            continue
        payload = run_git(source_root, "cat-file", "blob", blob, binary=True)
        if b"\x00" in payload[:8192]:
            continue
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            continue
        text_blobs_scanned += 1
        lower = text.lower()
        numbers = [float(value) for value in number_pattern.findall(text)]
        for (table, asset, method), values in paper_groups.items():
            if asset.lower() not in lower or method.lower() not in lower:
                continue
            if all(any(abs(observed - target) < 1e-9 for observed in numbers) for target in values):
                complete_paper_row_matches.append((blob, table, asset, method))
    if text_blobs_scanned != PUBLIC_FORK_TEXT_BLOBS_SCANNED or complete_paper_row_matches:
        raise RuntimeError(
            f"QuantHarness public-fork text result scan changed: {text_blobs_scanned}, {complete_paper_row_matches[:5]}"
        )

    trading_db_blobs = 0
    build_db_blobs = 0
    history_rows = 0
    db_paper_row_matches: List[Tuple[str, str, str]] = []
    asset_counts: Counter[str] = Counter()
    timeframe_counts: Counter[str] = Counter()
    start_dates: List[str] = []
    end_dates: List[str] = []
    for blob in sorted(db_blobs):
        payload = run_git(source_root, "cat-file", "blob", blob, binary=True)
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
            handle.write(payload)
            temporary_path = Path(handle.name)
        try:
            connection = sqlite3.connect(f"file:{temporary_path}?mode=ro", uri=True)
            tables = {row[0] for row in connection.execute("select name from sqlite_master where type='table'")}
            if "analysis_history" not in tables:
                build_db_blobs += 1
                connection.close()
                continue
            trading_db_blobs += 1
            columns = {row[1] for row in connection.execute('pragma table_info("analysis_history")')}
            required = {
                "asset",
                "timeframe",
                "start_date",
                "end_date",
                "result_summary",
                "result_details",
            }
            if not required <= columns:
                raise RuntimeError("Community trading database schema changed")
            records = connection.execute(
                "select asset,timeframe,start_date,end_date,result_summary,result_details from analysis_history"
            )
            for asset, timeframe, start_date, end_date, result_summary, result_details in records:
                history_rows += 1
                asset_text = str(asset)
                asset_counts[asset_text] += 1
                timeframe_counts[str(timeframe)] += 1
                if start_date:
                    start_dates.append(str(start_date))
                if end_date:
                    end_dates.append(str(end_date))
                text = f"{result_summary or ''}\n{result_details or ''}"
                lower = text.lower()
                numbers = [float(value) for value in number_pattern.findall(text)]
                for (_, paper_asset, method), values in paper_groups.items():
                    if paper_asset.lower() != asset_text.lower() or method.lower() not in lower:
                        continue
                    if all(any(abs(observed - target) < 1e-9 for observed in numbers) for target in values):
                        db_paper_row_matches.append((blob, asset_text, method))
            connection.close()
        finally:
            temporary_path.unlink(missing_ok=True)
    if (
        trading_db_blobs != PUBLIC_FORK_TRADING_DB_BLOBS
        or build_db_blobs != PUBLIC_FORK_BUILD_DB_BLOBS
        or history_rows != PUBLIC_FORK_TRADING_DB_HISTORY_ROWS
        or db_paper_row_matches
        or min(start_dates) != "2024-01-01"
        or max(end_dates) != "2026-07-08"
        or timeframe_counts != {"1d": 2170, "4h": 36, "1h": 22}
    ):
        raise RuntimeError("QuantHarness public-fork database evidence changed")

    tass_main_payload, tass_main_rows = _git_csv(
        source_root,
        PUBLIC_FORK_TASS_MAIN_HEAD,
        "docs/backtest_findings_20260606/summary.csv",
    )
    tass_mini_payload, tass_mini_rows = _git_csv(
        source_root,
        PUBLIC_FORK_TASS_MINIRUN_COMMIT,
        "backtest_results_quant/summary.csv",
    )
    tass_strategy_payload, tass_strategy_rows = _git_csv(
        source_root,
        PUBLIC_FORK_TASS_TEST_HEAD,
        "strategy_results/aggregate.csv",
    )
    if (
        len(tass_main_rows) != 3
        or hashlib.sha256(tass_main_payload).hexdigest()
        != "70b025242754c1513bcbea57565617c6fa0495741cb6d393fdf3dd20a5fc4b1e"
        or len(tass_mini_rows) != 2
        or hashlib.sha256(tass_mini_payload).hexdigest()
        != "0698ee76d47710dbd05e1b3639d6485875d0707f331f38d0ecd45dcd6e9ec3af"
        or len(tass_strategy_rows) != 24
        or hashlib.sha256(tass_strategy_payload).hexdigest()
        != "a098bfa08a2b82d6e0ace39876772ecd05b873e04e74884a806e86cb9d4656c8"
    ):
        raise RuntimeError("QuantHarness noteworthy fork result payload changed")
    mini_aapl = next(row for row in tass_mini_rows if row["symbol"] == "AAPL")
    mini_matches = sum(
        (
            abs(float(mini_aapl["agent_total_return"]) * 100.0 - (-22.51)) < 0.005,
            abs(float(mini_aapl["sharpe_annual"]) - (-0.155)) < 0.0005,
            abs(float(mini_aapl["max_drawdown"]) * 100.0 - 25.44) < 0.005,
        )
    )
    if mini_matches:
        raise RuntimeError("Unaffiliated AAPL mini-run now matches a paper metric")
    result_artifact_rows = [
        {
            "source_head_or_commit": PUBLIC_FORK_TASS_MINIRUN_COMMIT,
            "repository": "TasS-RV/QuantAgent-Build",
            "artifact": "historical_deleted_backtest_results_quant/summary.csv",
            "rows": len(tass_mini_rows),
            "assets": ";".join(sorted(row["symbol"] for row in tass_mini_rows)),
            "window_or_protocol": "2024-10-20_to_2025-02-27_daily_tiny_3_or_5_trade_run",
            "method_relation": "unaffiliated_adaptation_with_AAPL_overlap",
            "comparable_paper_cells": 3,
            "matching_paper_cells": mini_matches,
            "paper_result_credit": False,
        },
        {
            "source_head_or_commit": PUBLIC_FORK_TASS_MAIN_HEAD,
            "repository": "TasS-RV/QuantAgent-Build",
            "artifact": "docs/backtest_findings_20260606/summary.csv",
            "rows": len(tass_main_rows),
            "assets": ";".join(sorted(row["symbol"] for row in tass_main_rows)),
            "window_or_protocol": "2025-06-01_to_2026-06-06_weekly_gemini_2_5_flash_lite_with_overlays",
            "method_relation": "unaffiliated_materially_modified_LLM_backtest",
            "comparable_paper_cells": 0,
            "matching_paper_cells": 0,
            "paper_result_credit": False,
        },
        {
            "source_head_or_commit": PUBLIC_FORK_TASS_TEST_HEAD,
            "repository": "TasS-RV/QuantAgent-Build",
            "artifact": "strategy_results/aggregate.csv",
            "rows": len(tass_strategy_rows),
            "assets": "GOOGL;JNJ;XOM",
            "window_or_protocol": "2015_to_2026_daily_classic_strategy_grid",
            "method_relation": "unaffiliated_non_LLM_classic_strategy_lab",
            "comparable_paper_cells": 0,
            "matching_paper_cells": 0,
            "paper_result_credit": False,
        },
    ]

    summary: Dict[str, Any] = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "github_rest_reported_forks": PUBLIC_FORK_REST_COUNT,
        "graphql_accessible_forks": len(repositories),
        "rest_minus_accessible_fork_gap": PUBLIC_FORK_REST_COUNT - len(repositories),
        "accessibility_gap_interpretation": "deleted_private_or_otherwise_unavailable_not_inspected",
        "graphql_accessible_branch_refs": len(branch_rows),
        "graphql_accessible_branch_ref_census_sha256": sha256_lines(canonical_refs),
        "branch_ref_snapshot_file_sha256": sha256(branch_ref_snapshot),
        "unique_heads": len(unique_heads),
        "unique_head_sha256": sha256_lines(unique_heads),
        "heads_reachable_from_current_official_history": len(unique_heads) - len(divergent_heads),
        "divergent_heads_reviewed": len(divergent_heads),
        "divergent_extra_commits_reviewed": len(all_extra_commits),
        "divergent_changed_paths_reviewed": len(all_changed_paths),
        "new_object_counts": dict(object_counts),
        "new_blob_bytes": sum(blob_sizes.values()),
        "new_text_blobs_scanned": text_blobs_scanned,
        "new_text_blobs_with_complete_paper_result_row": 0,
        "new_database_blobs": len(db_blobs),
        "community_trading_database_blobs": trading_db_blobs,
        "community_trading_database_history_rows_across_versions": history_rows,
        "community_trading_database_distinct_assets": len(asset_counts),
        "community_trading_database_top_assets": dict(asset_counts.most_common(10)),
        "community_trading_database_timeframes": dict(timeframe_counts),
        "community_trading_database_min_start_date": min(start_dates),
        "community_trading_database_max_end_date": max(end_dates),
        "database_history_rows_with_complete_paper_result_row": 0,
        "author_personal_fork_heads_with_extra_commits": 0,
        "unaffiliated_backtest_artifact_families_reviewed": len(result_artifact_rows),
        "unaffiliated_AAPL_mini_run_comparable_cells": 3,
        "unaffiliated_AAPL_mini_run_matching_cells": mini_matches,
        "native_paper_result_artifacts_found": False,
        "paper_result_credit": False,
    }
    return branch_rows, head_rows, commit_rows, path_rows, result_artifact_rows, summary


def historical_benchmark_set_inventory(
    history_paths: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Mapping[str, Any]]] = {}
    for row in history_paths:
        path = str(row["relative_path"])
        if not path.startswith("benchmark/") or not path.endswith(".csv"):
            continue
        parts = path.split("/")
        group = "/".join(parts[:3] if parts[1] == "1h" else parts[:2])
        groups.setdefault(group, []).append(row)
    rows = []
    for group, members in sorted(groups.items()):
        parts = group.split("/")
        horizon = "1h" if parts[1] == "1h" else "4h"
        asset = parts[-1].upper()
        rows.append(
            {
                "historical_directory": group,
                "horizon": horizon,
                "asset": asset,
                "unique_historical_segment_paths": len(members),
                "paths_present_at_main_head": sum(
                    "main" in str(row["public_branch_heads_present"]).split(";") for row in members
                ),
                "paths_present_at_gh_pages_head": sum(
                    "gh-pages" in str(row["public_branch_heads_present"]).split(";") for row in members
                ),
                "original_5000_bar_panel_present": False,
                "native_predictions_or_results_present": False,
            }
        )
    if len(rows) != 18 or {row["unique_historical_segment_paths"] for row in rows} != {100}:
        raise RuntimeError(f"Historical benchmark-set census changed: {rows}")
    return rows


def source_config_audit(source_root: Path) -> List[Dict[str, Any]]:
    config = (source_root / "default_config.py").read_text(encoding="utf-8")
    web = (source_root / "web_interface.py").read_text(encoding="utf-8")
    decision = (source_root / "decision_agent.py").read_text(encoding="utf-8")
    readme = (source_root / "README.md").read_text(encoding="utf-8")
    requirements = (source_root / "requirements.txt").read_text(encoding="utf-8")
    tracked = set(git_files(source_root))
    checks = {
        "agent_model": '"agent_llm_model": "gpt-4o-mini"' in config,
        "graph_model": '"graph_llm_model": "gpt-4o"' in config,
        "temperatures": config.count('"agent_llm_temperature": 0.1') == 1
        and config.count('"graph_llm_temperature": 0.1') == 1,
        "active_tail45": "            df_slice = df.tail(45)" in web,
        "commented_holdout": "#     df_slice = df.tail(49).iloc[:-3]" in web,
        "long_short": '"decision": "<LONG or SHORT>"' in decision,
        "risk_ratio": "between **1.2 and 1.8**" in decision,
        "no_risk_agent": "risk_agent.py" not in tracked,
        "no_eval_source": not any(
            re.search(r"(^|/)(eval|evaluate|benchmark|backtest|experiment)(_|\.|/)", path)
            for path in tracked
            if path.endswith(".py") and not path.startswith("benchmark/")
        ),
        "requirements_unpinned": all(
            not any(token in line for token in ("==", "~=", ">=", "<="))
            for line in requirements.splitlines()
            if line.strip()
        ),
        "readme_decision_agent": "### Decision Agent" in readme,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Pinned QuantHarness source findings changed: {checks}")

    return [
        {
            "dimension": "agent_architecture",
            "paper": "IndicatorAgent, PatternAgent, TrendAgent, RiskAgent",
            "released": "indicator_agent.py, pattern_agent.py, trend_agent.py, decision_agent.py; no risk_agent.py",
            "status": "mismatch",
            "implication": "paper/source fourth-agent role and name are not the same",
        },
        {
            "dimension": "direction_and_risk_ratio_output",
            "paper": "LONG/SHORT plus risk-reward ratio in [1.2,1.8]",
            "released": "DecisionAgent prompt requires LONG/SHORT and ratio 1.2--1.8",
            "status": "match",
            "implication": "prompt-level component only",
        },
        {
            "dimension": "agent_llm_model",
            "paper": "not disclosed for the trading experiment",
            "released": "gpt-4o-mini",
            "status": "paper_underspecified",
            "implication": "paper result cannot be recreated from paper alone",
        },
        {
            "dimension": "decision_graph_llm_model",
            "paper": "not disclosed for the trading experiment",
            "released": "gpt-4o",
            "status": "paper_underspecified",
            "implication": "source default may not identify the paper run",
        },
        {
            "dimension": "llm_temperatures",
            "paper": "not disclosed",
            "released": "agent=0.1; graph=0.1",
            "status": "paper_underspecified",
            "implication": "stochastic protocol and reproducibility are not specified",
        },
        {
            "dimension": "benchmark_segment_release",
            "paper": "100 segments x 100 rows for every asset/horizon",
            "released": "all 1,600 CSVs with 100 rows each",
            "status": "match",
            "implication": "released sampled input component is substantial",
        },
        {
            "dimension": "original_5000_bar_panels",
            "paper": "5,000 source bars per asset/horizon",
            "released": "overlapping sampled segments only; 4,082 or 4,440 distinct timestamps",
            "status": "missing",
            "implication": "sampling cannot be independently rerun",
        },
        {
            "dimension": "held_out_last_three_bars",
            "paper": "last 3 of each 100-row segment withheld from inference",
            "released": "active run_analysis uses df.tail(45); a holdout slice is commented out",
            "status": "not_implemented_in_active_public_path",
            "implication": "passing a released 100-row segment to the active path would expose the outcomes",
        },
        {
            "dimension": "paper_experiment_entrypoint",
            "paper": "run 100 segments x assets x methods and score Tables 1--2/Figure 5",
            "released": "interactive web analysis only; no experiment/evaluation runner",
            "status": "missing",
            "implication": "native benchmark cannot be replayed",
        },
        {
            "dimension": "linear_regression_baseline",
            "paper": "OLS slope over recent 40 closes",
            "released": "no LR baseline/evaluator source",
            "status": "missing",
            "implication": "audit reconstructs from prose, not released evaluator code",
        },
        {
            "dimension": "xgboost_baseline",
            "paper": "TA-Lib features; random 50/50 CSV split; majority vote; HOLD discarded",
            "released": "no training/evaluation source, split, model, actions, or seed",
            "status": "missing",
            "implication": "XGBoost result is not reproducible",
        },
        {
            "dimension": "random_baseline",
            "paper": "random LONG/SHORT and ratio uniform in [1.2,1.8]",
            "released": "no baseline source, draws, or seed",
            "status": "missing",
            "implication": "random result is not reproducible",
        },
        {
            "dimension": "accuracy_evaluator",
            "paper": "three close comparisons per segment",
            "released": "no scoring implementation or prediction files",
            "status": "missing",
            "implication": "only prose-based baseline reconstruction is possible",
        },
        {
            "dimension": "rcc_rmax_rmin_evaluator",
            "paper": "risk-aware returns over three held-out candles",
            "released": "no evaluator, risk-ratio paths, exit-order convention, or result series",
            "status": "missing",
            "implication": "Rcc is not reconstructible and extrema are diagnostic only",
        },
        {
            "dimension": "agent_predictions_and_outputs",
            "paper": "segment-level directions, ratios, rationales, and aggregate results",
            "released": "no generated action, ratio, rationale, or return series",
            "status": "missing",
            "implication": "QuantHarness result cells are unverifiable",
        },
        {
            "dimension": "table_1_portfolio_paths",
            "paper": "Sharpe, Sortino, cumulative return, max drawdown",
            "released": "no portfolio/equity/return series or metric implementation",
            "status": "missing",
            "implication": "all 120 Table 1 numeric cells are unverifiable",
        },
        {
            "dimension": "table_1_aapl_amzn_inputs",
            "paper": "AAPL and AMZN rows",
            "released": "no AAPL or AMZN benchmark directory",
            "status": "missing",
            "implication": "two Table 1 asset inputs are absent",
        },
        {
            "dimension": "one_hour_result_paths",
            "paper": "Figure 5 comparisons across eight assets",
            "released": "1-hour inputs and a static figure image, but no numeric paths/predictions",
            "status": "missing",
            "implication": "Figure 5 cannot be numerically checked",
        },
        {
            "dimension": "case_study_paths",
            "paper": "SPX 8/10 case and agent-reasoning cases",
            "released": "static images; no selected segment IDs or ten prediction records",
            "status": "missing",
            "implication": "case-study claims cannot be replayed",
        },
        {
            "dimension": "dependency_lock",
            "paper": "operational implementation",
            "released": "requirements.txt has names only and no versions",
            "status": "missing",
            "implication": "environment is not reproducibly pinned",
        },
        {
            "dimension": "benchmark_tests",
            "paper": "paper experiment conformance",
            "released": "tests cover MiniMax provider integration only",
            "status": "missing",
            "implication": "no test asserts paper benchmark behavior",
        },
        {
            "dimension": "latency_and_cost_evidence",
            "paper": "HFT/real-time framing",
            "released": "no latency, token, API-cost, or throughput logs",
            "status": "missing",
            "implication": "operational HFT feasibility is not demonstrated by release artifacts",
        },
    ]


def internal_accuracy_identity() -> List[Dict[str, Any]]:
    records = table_2_records()
    baseline = {row["asset"]: row["accuracy_pct"] for row in records if row["method"] == "Baseline"}
    rows = []
    for record in records:
        if record["delta_accuracy_pct"] is None:
            continue
        implied = (record["accuracy_pct"] - baseline[record["asset"]]) / baseline[record["asset"]] * 100.0
        error = abs(record["delta_accuracy_pct"] - implied)
        rows.append(
            {
                "asset": record["asset"],
                "method": record["method"],
                "published_accuracy_pct": record["accuracy_pct"],
                "published_baseline_accuracy_pct": baseline[record["asset"]],
                "published_delta_accuracy_pct": record["delta_accuracy_pct"],
                "implied_delta_accuracy_pct": implied,
                "absolute_error": error,
                "status": (
                    "rounding_consistent_internal_identity"
                    if error <= ACCURACY_DISPLAY_TOLERANCE
                    else "paper_internal_mismatch"
                ),
            }
        )
    return rows


def paper_anomalies() -> List[Dict[str, Any]]:
    rows = []
    for line in TABLE_1_TEXT.strip().splitlines():
        _, asset, method, _, _, _, drawdown = line.split("|")
        if method == "TradingAgent" and float(drawdown) > 0:
            rows.append(
                {
                    "paper_table": 1,
                    "asset": asset,
                    "method": method,
                    "metric": "max_drawdown_pct",
                    "paper_value": float(drawdown),
                    "finding": "positive_value_under_a_lower_is_better_max_drawdown_column",
                    "interpretation": (
                        "all eight TradingAgent drawdowns are positive while every other numeric "
                        "drawdown in Table 1 is non-positive; evaluator/sign convention is unavailable"
                    ),
                }
            )
    rows.append(
        {
            "paper_table": 2,
            "asset": "SPX",
            "method": "Our",
            "metric": "delta_accuracy_pct",
            "paper_value": 34.6,
            "finding": "displayed_accuracy_cells_imply_34_7_pct_not_34_6_pct",
            "interpretation": (
                "hidden unrounded values could explain the difference, but the displayed "
                "63.7 and 47.3 accuracy cells imply 34.6723%, which rounds to 34.7%"
            ),
        }
    )
    return rows


def table_conformance(
    arrays: Mapping[str, np.ndarray], alignment_rows: Sequence[Mapping[str, Any]]
) -> List[Dict[str, Any]]:
    alignment = {row["asset"]: row for row in alignment_rows}
    records = table_2_records()
    baseline = {row["asset"]: row["accuracy_pct"] for row in records if row["method"] == "Baseline"}
    inferred_extrema: Dict[Tuple[str, str], float] = {}
    for asset in ASSETS_4H:
        direction = linear_regression_directions(arrays[asset][:, :, 0], 94)
        rmax, rmin = extrema_returns(arrays[asset], direction)
        inferred_extrema[(asset, "rmax")] = rmax
        inferred_extrema[(asset, "rmin")] = rmin

    rows = []
    for target in paper_result_rows():
        audit_value: Any = ""
        absolute_error: Any = ""
        tolerance: Any = ""
        if target["paper_table"] == 1:
            status = "unverifiable_missing_native_portfolio_or_metric_path"
            evidence = "paper_value_only_no_shipped_returns_equity_curve_or_table_1_evaluator"
        elif target["metric"] == "delta_accuracy_pct":
            record = next(
                row for row in records if row["asset"] == target["asset"] and row["method"] == target["method"]
            )
            audit_value = (record["accuracy_pct"] - baseline[target["asset"]]) / baseline[target["asset"]] * 100.0
            absolute_error = abs(target["paper_value"] - audit_value)
            tolerance = ACCURACY_DISPLAY_TOLERANCE
            status = (
                "paper_internal_identity_match_not_independent_reproduction"
                if absolute_error <= tolerance
                else "paper_internal_identity_mismatch"
            )
            evidence = "derived_only_from_other_printed_table_2_accuracy_cells"
        elif target["method"] == "LR" and target["metric"] == "accuracy_pct":
            audit_value = alignment[target["asset"]]["paper_described_accuracy_pct"]
            absolute_error = abs(target["paper_value"] - audit_value)
            tolerance = ACCURACY_DISPLAY_TOLERANCE
            status = (
                "paper_described_recent_40_window_display_match"
                if absolute_error <= tolerance
                else "mismatch_paper_described_recent_40_window"
            )
            evidence = "released_4h_segments_plus_prose_specification_rows_57_to_96"
        elif target["method"] == "LR" and target["metric"] in {"rmax", "rmin"}:
            audit_value = inferred_extrema[(target["asset"], target["metric"])]
            absolute_error = abs(target["paper_value"] - audit_value)
            tolerance = RETURN_DISPLAY_TOLERANCE
            status = (
                "diagnostic_inferred_gap_display_match_not_native_reproduction"
                if absolute_error <= tolerance
                else "diagnostic_inferred_gap_mismatch"
            )
            evidence = (
                "released_4h_segments_plus_paper_extrema_formula_using_LR_directions_that_"
                "match_accuracy_only_with_undocumented_rows_94_to_96_gap"
            )
        else:
            status = "unverifiable_missing_native_result_or_evaluator"
            if target["method"] == "Our":
                evidence = "no_shipped_agent_predictions_risk_ratios_or_result_series"
            elif target["method"] == "XGBoost":
                evidence = "no_shipped_xgboost_code_model_split_seed_or_predictions"
            elif target["method"] == "Baseline":
                evidence = "no_shipped_random_draws_seed_risk_ratios_or_evaluator"
            else:
                evidence = "LR_Rcc_requires_unshipped_risk_ratio_and_exit_evaluator"
        rows.append(
            {
                **target,
                "audit_value": audit_value,
                "absolute_error": absolute_error,
                "display_tolerance": tolerance,
                "status": status,
                "evidence": evidence,
            }
        )
    return rows


def build_audit(
    source_root: Path,
    paper_versions_root: Path,
    branch_ref_snapshot: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    paper_path = paper_versions_root / "paper_v4.pdf"
    if sha256(paper_path) != PAPER_SHA256:
        raise RuntimeError("Official arXiv v4 PDF hash does not match the pinned primary source")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        actual = sha256(source_root / relative)
        if actual != expected:
            raise RuntimeError(f"Pinned source hash mismatch for {relative}: {actual}")
    tree_hash = benchmark_tree_hash(source_root)
    if tree_hash != BENCHMARK_TREE_SHA256:
        raise RuntimeError(f"Pinned benchmark tree hash mismatch: {tree_hash}")

    paper_versions = paper_version_inventory(paper_versions_root)
    versioned_results = paper_version_result_rows(paper_versions_root)
    (
        history_commits,
        history_paths,
        history_images,
        history_summary,
    ) = public_source_history(source_root)
    postpaper_rows, postpaper_summary = postpaper_official_source_audit(source_root)
    (
        fork_branches,
        fork_heads,
        fork_commits,
        fork_paths,
        fork_results,
        fork_summary,
    ) = public_fork_audit(source_root, branch_ref_snapshot)
    history_benchmark_sets = historical_benchmark_set_inventory(history_paths)
    arrays = load_4h_arrays(source_root)
    alignments, exact_alignment_pairs = lr_alignment_audit(arrays)
    if exact_alignment_pairs != [(94, 96)]:
        raise RuntimeError(f"Pinned LR alignment finding changed: {exact_alignment_pairs}")
    inventory = benchmark_inventory(source_root)
    source_files = source_inventory(source_root)
    config = source_config_audit(source_root)
    identities = internal_accuracy_identity()
    anomalies = paper_anomalies()
    conformance = table_conformance(arrays, alignments)

    status_counts = Counter(row["status"] for row in conformance)
    expected_counts = {
        "unverifiable_missing_native_portfolio_or_metric_path": 120,
        "paper_internal_identity_match_not_independent_reproduction": 23,
        "paper_internal_identity_mismatch": 1,
        "mismatch_paper_described_recent_40_window": 8,
        "diagnostic_inferred_gap_display_match_not_native_reproduction": 7,
        "diagnostic_inferred_gap_mismatch": 9,
        "unverifiable_missing_native_result_or_evaluator": 104,
    }
    if dict(status_counts) != expected_counts:
        raise RuntimeError(f"Pinned result conformance counts changed: {status_counts}")
    if len(conformance) != 272:
        raise RuntimeError(f"Expected 272 numeric paper result cells, got {len(conformance)}")
    if len(inventory) != 16 or not all(row["status"].startswith("released_sampled") for row in inventory):
        raise RuntimeError("Released benchmark inventory changed")
    if Counter(int(row["released_distinct_timestamps"]) for row in inventory) != Counter({4082: 15, 4440: 1}):
        raise RuntimeError("Released benchmark overlap counts changed")
    identity_mismatches = [row for row in identities if row["status"] == "paper_internal_mismatch"]
    if [(row["asset"], row["method"]) for row in identity_mismatches] != [("SPX", "Our")]:
        raise RuntimeError(f"Published delta-accuracy identity findings changed: {identity_mismatches}")
    if Counter(row["paper_version"] for row in versioned_results) != {
        "v1": 88,
        "v2": 88,
        "v3": 152,
        "v4": 272,
    }:
        raise RuntimeError("Version-specific paper result census changed")
    if sum(row["author_rendered_correspondence"] for row in versioned_results) != 480:
        raise RuntimeError("Version-specific author-rendered correspondence changed")
    if any(row["independently_regenerated_from_native_result_path"] for row in versioned_results):
        raise RuntimeError("Native version-specific result credit requires manual review")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_1_2_conformance.csv", conformance, list(conformance[0]))
    write_csv(output_dir / "linear_regression_alignment_audit.csv", alignments, list(alignments[0]))
    write_csv(output_dir / "table_2_delta_accuracy_identity.csv", identities, list(identities[0]))
    write_csv(output_dir / "released_benchmark_inventory.csv", inventory, list(inventory[0]))
    write_csv(output_dir / "source_config_conformance.csv", config, list(config[0]))
    write_csv(output_dir / "released_source_inventory.csv", source_files, list(source_files[0]))
    write_csv(output_dir / "paper_internal_anomalies.csv", anomalies, list(anomalies[0]))
    write_csv(
        output_dir / "official_paper_version_inventory.csv",
        paper_versions,
        list(paper_versions[0]),
    )
    write_csv(
        output_dir / "paper_version_result_conformance.csv",
        versioned_results,
        list(versioned_results[0]),
    )
    write_csv(
        output_dir / "public_source_history_commit_inventory.csv",
        history_commits,
        list(history_commits[0]),
    )
    write_csv(
        output_dir / "public_source_history_path_inventory.csv",
        history_paths,
        list(history_paths[0]),
    )
    write_csv(
        output_dir / "public_source_history_benchmark_set_inventory.csv",
        history_benchmark_sets,
        list(history_benchmark_sets[0]),
    )
    write_csv(
        output_dir / "historical_result_image_inventory.csv",
        history_images,
        list(history_images[0]),
    )
    (output_dir / "public_source_history.json").write_text(
        json.dumps(history_summary, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    write_csv(
        output_dir / "postpaper_official_source_changes.csv",
        postpaper_rows,
        list(postpaper_rows[0]),
    )
    write_csv(
        output_dir / "public_fork_branch_ref_snapshot.csv",
        fork_branches,
        list(fork_branches[0]),
    )
    write_csv(
        output_dir / "public_fork_unique_head_inventory.csv",
        fork_heads,
        list(fork_heads[0]),
    )
    write_csv(
        output_dir / "public_fork_divergent_commit_inventory.csv",
        fork_commits,
        list(fork_commits[0]),
    )
    write_csv(
        output_dir / "public_fork_divergent_path_inventory.csv",
        fork_paths,
        list(fork_paths[0]),
    )
    write_csv(
        output_dir / "public_fork_result_artifact_audit.csv",
        fork_results,
        list(fork_results[0]),
    )
    (output_dir / "public_fork_census.json").write_text(
        json.dumps(fork_summary, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    manifest: Dict[str, Any] = {
        "audit": "QuantHarness official paper versions, official history, and accessible public-fork network",
        "audit_date": "2026-08-30",
        "overall_status": "not_reproduced_full_history_and_608_forks_exhausted_author_table_rasters_only",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_versions": PAPER_VERSIONS,
        "paper_versions_audited": len(paper_versions),
        "paper_version": "arXiv:2509.09995v4",
        "paper_sha256": PAPER_SHA256,
        "version_specific_paper_numeric_result_cells_total": len(versioned_results),
        "version_specific_paper_numeric_result_cells_by_version": dict(
            Counter(row["paper_version"] for row in versioned_results)
        ),
        "distinct_numeric_result_table_cells_across_versions": 360,
        "version_specific_author_rendered_table_cells_corresponded": sum(
            row["author_rendered_correspondence"] for row in versioned_results
        ),
        "distinct_author_rendered_table_cells_corresponded": 240,
        "version_specific_native_result_cells_independently_regenerated": 0,
        "version_specific_result_cells_without_author_rendered_correspondence": 120,
        "source_url": SOURCE_URL,
        "source_legacy_url": SOURCE_LEGACY_URL,
        "source_commit": commit,
        "source_commit_date": "2026-07-23",
        "paper_era_public_source_branch_heads": PAPER_ERA_PUBLIC_BRANCH_HEADS,
        "public_source_branch_heads": PUBLIC_BRANCH_HEADS,
        "postpaper_official_commits_audited": postpaper_summary["postpaper_commits"],
        "postpaper_official_changed_paths_audited": postpaper_summary["postpaper_changed_paths"],
        "postpaper_official_native_result_artifacts_added": postpaper_summary["native_result_artifacts_added"],
        "public_source_branches_total": history_summary["public_branches_total"],
        "public_source_tags_total": history_summary["public_tags_total"],
        "public_source_reachable_commits_total": history_summary["reachable_commits_total"],
        "public_source_unique_historical_paths_total": history_summary["unique_historical_paths_total"],
        "public_source_reachable_object_counts": history_summary["reachable_object_counts"],
        "public_source_unreachable_objects_total": history_summary["unreachable_objects_total"],
        "public_source_historical_benchmark_csv_paths_total": history_summary["historical_benchmark_csv_paths_total"],
        "public_source_historical_benchmark_asset_horizon_sets_total": history_summary[
            "historical_benchmark_asset_horizon_sets_total"
        ],
        "public_source_historical_native_result_artifact_candidates_total": history_summary[
            "historical_native_result_artifact_candidates_total"
        ],
        "public_source_historical_unique_result_image_blobs_total": history_summary[
            "historical_unique_result_image_blobs_total"
        ],
        "public_source_historical_unique_table_image_blobs_total": history_summary[
            "historical_unique_table_image_blobs_total"
        ],
        "public_source_historical_unique_one_hour_result_chart_blobs_total": history_summary[
            "historical_unique_one_hour_result_chart_blobs_total"
        ],
        "official_one_hour_figure_author_raster_correspondences_total": history_summary[
            "official_one_hour_figure_author_raster_correspondences_total"
        ],
        "intermediate_nonpaper_one_hour_result_rasters_total": history_summary[
            "intermediate_nonpaper_one_hour_result_rasters_total"
        ],
        "public_fork_census_date": fork_summary["census_date"],
        "github_rest_reported_public_forks": fork_summary["github_rest_reported_forks"],
        "graphql_accessible_public_forks": fork_summary["graphql_accessible_forks"],
        "public_fork_accessibility_gap": fork_summary["rest_minus_accessible_fork_gap"],
        "public_fork_branch_refs_examined": fork_summary["graphql_accessible_branch_refs"],
        "public_fork_unique_heads_examined": fork_summary["unique_heads"],
        "public_fork_heads_reachable_from_official_history": fork_summary[
            "heads_reachable_from_current_official_history"
        ],
        "public_fork_divergent_heads_examined": fork_summary["divergent_heads_reviewed"],
        "public_fork_divergent_extra_commits_examined": fork_summary["divergent_extra_commits_reviewed"],
        "public_fork_divergent_changed_paths_examined": fork_summary["divergent_changed_paths_reviewed"],
        "public_fork_new_object_counts": fork_summary["new_object_counts"],
        "public_fork_new_blob_bytes_examined": fork_summary["new_blob_bytes"],
        "public_fork_new_text_blobs_scanned": fork_summary["new_text_blobs_scanned"],
        "public_fork_complete_paper_result_rows_found_in_new_text_blobs": 0,
        "public_fork_community_trading_database_blobs_examined": fork_summary["community_trading_database_blobs"],
        "public_fork_community_trading_database_history_rows_examined": fork_summary[
            "community_trading_database_history_rows_across_versions"
        ],
        "public_fork_database_history_rows_with_complete_paper_result_row": 0,
        "public_fork_unaffiliated_backtest_artifact_families_reviewed": fork_summary[
            "unaffiliated_backtest_artifact_families_reviewed"
        ],
        "public_fork_unaffiliated_AAPL_mini_run_comparable_cells": 3,
        "public_fork_unaffiliated_AAPL_mini_run_matching_cells": 0,
        "public_fork_native_paper_result_artifacts_found": False,
        "public_fork_paper_result_credit": False,
        "one_hour_figure_numeric_points_or_arrays_shipped": False,
        "historical_native_predictions_evaluators_returns_or_portfolio_paths": False,
        "paper_numeric_tables_audited": [1, 2],
        "paper_numeric_result_cells_total": len(conformance),
        "paper_table_cell_counts": {"1": 120, "2": 152},
        "native_paper_result_cells_reproduced": 0,
        "paper_internal_delta_identity_cells_consistent": 23,
        "paper_internal_delta_identity_cells_inconsistent": 1,
        "paper_described_lr_accuracy_cells_recomputed": 8,
        "paper_described_lr_accuracy_cells_matched": 0,
        "paper_described_lr_accuracy_cells_mismatched": 8,
        "published_lr_accuracy_cells_exact_only_with_undocumented_three_bar_feature_gap": 8,
        "lr_alignment_search_exact_pairs": [
            {"feature_window_end_exclusive": end, "reference_close_index": reference}
            for end, reference in exact_alignment_pairs
        ],
        "inferred_gap_lr_extrema_cells_recomputed": 16,
        "inferred_gap_lr_extrema_cells_display_matched": 7,
        "inferred_gap_lr_extrema_cells_mismatched": 9,
        "numeric_result_cells_unverifiable": 224,
        "table_1_numeric_cells_unverifiable": 120,
        "table_2_numeric_cells_unverifiable": 104,
        "released_benchmark_csv_files": 1600,
        "released_benchmark_rows_with_overlap": 160000,
        "released_benchmark_asset_horizon_sets": 16,
        "released_sets_with_100_segments_of_100_rows": 16,
        "released_sets_whose_union_matches_paper_date_endpoints": 16,
        "released_distinct_timestamps_by_set": Counter(int(row["released_distinct_timestamps"]) for row in inventory),
        "original_5000_bar_panels_shipped": False,
        "benchmark_tree_sha256": tree_hash,
        "tracked_source_files_total": len(git_files(source_root)),
        "tracked_non_benchmark_files_total": len(source_files),
        "native_agent_predictions_or_return_series_shipped": False,
        "native_table_1_portfolio_paths_shipped": False,
        "native_experiment_evaluator_shipped": False,
        "native_lr_baseline_implementation_shipped": False,
        "native_xgboost_baseline_implementation_shipped": False,
        "native_random_baseline_implementation_shipped": False,
        "one_hour_numeric_result_paths_shipped": False,
        "paper_llm_models_disclosed": False,
        "paper_llm_temperatures_disclosed": False,
        "source_dependency_versions_pinned": False,
        "active_public_web_path_enforces_three_bar_holdout": False,
        "audit_called_llm_or_paid_external_api": False,
        "paper_table_1_positive_tradingagent_drawdown_anomalies": 8,
        "paper_internal_anomalies_total": len(anomalies),
        "interpretation": (
            "All four official paper revisions, the complete two-branch 204-commit official "
            "history, and all 608 accessible public forks are exhausted. The papers contain "
            "600 version-specific result cells (360 distinct); 480 author-rendered table-cell "
            "correspondences remain static corroboration, and 0/600 cells are independently "
            "regenerated. Nine post-paper official commits modify six provider, interface, "
            "test, or documentation paths and add no result artifact. The fork census covers "
            "700 branch refs, 112 unique heads, 70 divergent heads, 595 extra commits, 4,845 "
            "changed paths, and 2,072 genuinely new blobs. Scans of 1,739 text blobs and 2,228 "
            "analysis-history rows across 42 community trading-database versions find zero "
            "complete published result rows. Three unaffiliated backtest families materially "
            "change the model, universe, window, frequency, overlays, or strategy; the sole "
            "AAPL overlap matches 0/3 comparable cells. No fork supplies the paper evaluator, "
            "benchmark predictions, risk ratios, portfolio path, or exact result lineage."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
    }

    report = f"""# QuantHarness paper-level conformance audit

Overall verdict: **not reproduced after auditing every official paper revision, the
complete official history, and every accessible public-fork branch**. The release
provides substantial sampled inputs, an inspectable multi-agent web framework, and
author-rendered result images, but not the experiment runner or native data paths
needed to regenerate a published result.

## Primary-source boundary

- All four official revisions of [{PAPER_URL}]({PAPER_URL}) are pinned by PDF,
  source-archive, and `main.tex` SHA-256. v1/v2 have 30 pages, v3 has 30, and
  current v4 has 32. The v3/v4 `line_chart.pdf` assets are pinned separately;
  the exact submission dates and hashes are recorded in
  `official_paper_version_inventory.csv`.
- The paper-era official [{SOURCE_URL}]({SOURCE_URL}) source (renamed from the
  `Y-Research-SBU/QuantAgent` legacy URL) is pinned at `main` commit `{commit}`.
  The current public surface is separately pinned through
  `{PUBLIC_BRANCH_HEADS["main"]}` and contains both branch heads,
  **{history_summary["reachable_commits_total"]} reachable commits**,
  **{history_summary["unique_historical_paths_total"]} unique historical paths**,
  **{history_summary["reachable_object_counts"]["blob"]} blobs**, no tags, and no
  unreachable objects. Deleted paths and `gh-pages` are included.
- Nine post-paper official commits touch only six provider, interface, test, or
  documentation paths. They add Gemini support, update MiniMax, and refresh the star
  chart; they add no evaluator, prediction, risk-ratio, return, or result artifact.

## Complete public-fork boundary

- GitHub REST reported **{fork_summary["github_rest_reported_forks"]} forks** on
  {fork_summary["census_date"]}. GraphQL exposed all branches for
  **{fork_summary["graphql_accessible_forks"]} repositories** and
  **{fork_summary["graphql_accessible_branch_refs"]} branch refs**; the remaining
  {fork_summary["rest_minus_accessible_fork_gap"]} deleted, private, or otherwise
  unavailable forks are not claimed as inspected.
- The accessible surface collapses to **{fork_summary["unique_heads"]} unique heads**.
  Of these, {fork_summary["heads_reachable_from_current_official_history"]} are
  reachable from current official history and **{fork_summary["divergent_heads_reviewed"]}**
  diverge. The divergent surface contains **{fork_summary["divergent_extra_commits_reviewed"]}
  extra commits**, **{fork_summary["divergent_changed_paths_reviewed"]} changed paths**,
  and **{fork_summary["new_object_counts"]["blob"]} genuinely new blobs** totaling
  {fork_summary["new_blob_bytes"]:,} bytes.
- A content scan covers {fork_summary["new_text_blobs_scanned"]} new text blobs and all
  {fork_summary["community_trading_database_history_rows_across_versions"]}
  `analysis_history` rows across {fork_summary["community_trading_database_blobs"]}
  distinct community `trading_data.db` versions. It finds zero complete published
  result rows. The databases contain live/community analyses from 2024--2026 rather
  than the paper's fixed 100-segment benchmark, and their result tables are empty.
- One unaffiliated fork contributes three real but non-paper backtest families: a tiny
  AAPL/BTC run, a weekly Gemini-2.5-Flash-Lite GOOGL/XOM/JNJ run with added overlays,
  and a daily classic-strategy grid. The AAPL overlap matches 0/3 comparable paper
  cells; the other families use the wrong universe, model, window, frequency, or
  strategy. They receive no paper-result credit. The only identifiable coauthor-owned
  fork is an unchanged official-history snapshot.

## Paper-version evolution and rendered evidence

- v1 and v2 each contain the same **88-cell** random-baseline/Our 4-hour table.
  v3 replaces it with a **152-cell** Baseline/LR/XGBoost/Our table. v4 retains that
  table and adds a **120-cell** portfolio-performance table, for **272** v4 cells.
  The audit therefore enumerates **600 version-specific cells**, representing
  **360 distinct cells** after identical revision tables are deduplicated.
- A historical 1,545x952 author raster completely corresponds to the v1/v2 table.
  Three later author renderings contain the v3/v4 152-cell table; the current
  966x1032 raster is the canonical correspondence. That establishes rendered
  correspondence for **480/600 version-specific cells** and **240 distinct cells**.
  It independently regenerates **0/600**. The v4-only 120-cell table has no source
  raster correspondence.
- History also contains three distinct 1-hour result-chart blobs. Visual inspection
  establishes complete author-raster correspondence between one QuantAgent/DAX chart
  and the official v3 `line_chart.pdf`, and between the current QuantHarness/DAX chart
  and v4. The earlier VIX chart is an intermediate historical output, not an official
  paper figure. None ships plotted arrays, segment predictions, or exact point-level
  values, so all three receive zero numeric reproduction credit.

## Complete source-history finding

- The 1,870 historical paths include **1,800 benchmark CSVs** across 18 historical
  asset/horizon directories. Every directory contains 100 sampled 100-row segment
  paths. The current release retains 1,600 CSVs across 16 sets; historical GC/DXY
  directories do not supply the original 5,000-bar panels or result outputs.
- Across all commits there is no non-benchmark CSV, JSONL, NumPy array, Parquet/HDF,
  pickle, checkpoint, model, log, prediction, risk-ratio, return, equity, portfolio,
  split, or seed artifact attributable to a paper run. Four table-image blobs and
  three one-hour chart blobs are exhaustively pinned in
  `historical_result_image_inventory.csv`; none contains an underlying native path.

## What is genuinely established

- The repository ships all 1,600 advertised sampled CSVs: 16 asset/horizon sets,
  100 files per set, and 100 OHLCV rows per file. Every sampled union reaches the
  exact start and end dates printed in Tables 3--4. The overlapping samples expose
  4,082 distinct timestamps in 15 sets and 4,440 for 1-hour DAX, not the original
  5,000-bar panels, so segment sampling itself cannot be rerun.
- Reconstructing the stated LR baseline with the most recent 40 closes available
  after withholding rows 97--99 gives **0/8** Table 2 accuracy matches. A bounded
  exhaustive search finds one and only one alignment that matches all eight printed
  accuracies: feature rows 54--93, reference close row 96, outcomes rows 97--99.
  That leaves rows 94--96 as an undocumented three-bar feature gap.
- Using those inferred LR directions and the paper's best/worst OHLC formulas gives
  7/16 Rmax/Rmin display matches. The natural paper-described directions give 0/16.
  These are forensic diagnostics, not a native evaluator reproduction.
- 23/24 printed delta-accuracy cells are rounding-consistent with percentage change
  from the printed random-baseline accuracy. SPX "Our" reports +34.6%, while its
  displayed 63.7% and 47.3% accuracies imply +34.7%. Hidden unrounded values could
  explain this; either way, these are identities, not independently reproduced data.

## Why current v4 is not reproduced

- Every one of the 120 numeric Table 1 cells lacks a released return/equity path and
  metric evaluator. Table 1 includes AAPL and AMZN, for which no benchmark directory
  is released. The eight TradingAgent max-drawdown values are positive while every
  other numeric drawdown is non-positive; without the evaluator, the sign convention
  cannot be resolved.
- Of Table 2's 152 numeric cells, 104 have no reconstructible native result path.
  The public tree has no random or XGBoost evaluator, 50/50 split, model, predictions,
  random seed, LR code, Rcc implementation, agent predictions, or risk-ratio records.
  The remaining checked cells are either prose reconstructions, an inferred alignment,
  or identities among already printed values.
- The paper names Indicator, Pattern, Trend, and Risk agents. The source has Indicator,
  Pattern, Trend, and Decision modules and no `risk_agent.py`. Its Decision prompt does
  preserve LONG/SHORT and the 1.2--1.8 risk-ratio range.
- The paper does not disclose the trading-run LLM models or temperatures. Source defaults
  are GPT-4o-mini for agents, GPT-4o for graph/decision, and temperature 0.1 for both,
  but there is no evidence tying those mutable defaults to the published outputs.
- The active public `run_analysis` path uses `df.tail(45)`; the only slice excluding
  the final three rows is commented out. If a released 100-row benchmark segment is
  passed to that active path, the held-out outcome rows are exposed. The paper experiment
  path is absent, so this is a release-path leakage risk, not proof of how authors ran it.
- Figure 5 and the 8/10 SPX case study are released only as static images, without
  numeric predictions or selected segment identifiers. Dependencies are unpinned and
  the shipped tests cover provider integration rather than paper-benchmark behavior.

## Honest denominator

Across revisions, **0/600** version-specific result cells are independently regenerated.
The 480 author-rendered correspondences are tracked separately and never promoted to
native credit. Within current v4's **272** cells, there are 23 internally consistent
derived identities and one displayed mismatch, 8 LR accuracy mismatches under the
stated window, 16 inferred-gap extrema diagnostics (7 display matches), and 224
unavailable cells. No proxy, inferred alignment, author raster, or static figure is
promoted to a faithful end-to-end result.

Run `scripts/audit_quantharness_paper.py` to regenerate this package. Use `--strict`
when CI should fail until native predictions, evaluator paths, exact configuration,
seeds/splits, portfolio series, and numeric 1-hour outputs reproduce the paper.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "QUANTHARNESS_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/quantagent_hft_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-versions-root",
        type=Path,
        default=Path(
            os.environ.get(
                "QUANTHARNESS_PAPER_VERSIONS_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/quantagent_hft_paper",
            )
        ),
    )
    parser.add_argument(
        "--fork-snapshot",
        type=Path,
        default=Path(
            os.environ.get(
                "QUANTHARNESS_FORK_SNAPSHOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/quantagent_hft_paper/public_fork_branch_ref_snapshot_2026-08-30.csv",
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/quantharness",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(),
        args.paper_versions_root.resolve(),
        args.fork_snapshot.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
