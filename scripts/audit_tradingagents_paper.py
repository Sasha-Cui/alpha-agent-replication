#!/usr/bin/env python3
"""Audit every TradingAgents paper version and the full public source history.

The project site, including the complete result table, predates arXiv v1. The
executable implementation does not: the first public code release arrived about
52 hours after v7. This fail-closed audit pins all seven arXiv PDFs and source
archives, every discovered public branch/tag/release and reachable Git object,
the paper-era site, and the nearest v0.1.0 implementation. It inventories every
Table 1 cell and every plotted result series, checks internal metric identities,
and executes deterministic components plus the real dependency-backed graph
constructor from v0.1.0 without external API calls.
Author-rendered correspondence is never promoted to independent regeneration.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


PAPER_URL = "https://arxiv.org/pdf/2412.20138v7"
PAPER_VERSION = "arXiv:2412.20138v7"
PAPER_DATE = "2025-06-03T05:45:06Z"
PAPER_SHA256 = "431d0c39365b4c46b43162371fa15b3dcf8d142b377d642b3e5925dc81f3487b"
PAPER_SOURCE_SHA256 = "17bc9ebe6c7379ed832ec9915eb147feccda3c8c582a84d93f1f87dfbaf3ed65"
SOURCE_URL = "https://github.com/TauricResearch/TradingAgents"
SOURCE_COMMIT = "cc97cb6d5deb10eac370db0c6678e2796a62eba8"
SOURCE_TAG = "v0.1.0"
SOURCE_COMMIT_DATE = "2025-06-05T03:08:28-07:00"
CURRENT_SOURCE_COMMIT = "a33fd4c0f134485a43553a2c23a63cb14adbd88f"
PRE_RELEASE_COMMIT = "635e91ac75f68e5a48eaf0c07760252f73326118"
PRE_RELEASE_COMMIT_DATE = "2025-02-02T12:53:37-08:00"
PRE_RELEASE_TABLE_PATH = "index_complete.html"
PRE_RELEASE_TABLE_SHA256 = "7f38e893195179f58364ea760ca61440a791acd6205cb1c12ba5c62909c6e9bf"
FIRST_PUBLIC_COMMIT = "c2fa046a9bc169b218c827127f2e44338ebd0890"
FIRST_EXACT_TABLE_COMMIT = "db9f63fa54059ec8ae262ef10557c853b6a011a7"
FIRST_EXACT_TABLE_COMMIT_DATE = "2024-12-28T11:56:38+08:00"
FIRST_EXACT_TABLE_BLOB = "a13337c440f63c955bcceffa09daafad806aae69"
FIRST_EXACT_TABLE_SHA256 = "169868f714b9ef74da76ee2895a004cdb8e758851505409fc91cc12ec3287a4c"
DEFAULT_SOURCE_PYTHON = str(
    Path(__file__).resolve().with_name("run_tradingagents_v010_python.sh")
)
RECONSTRUCTED_ENV_FREEZE_SHA256 = (
    "d35fd4aa1827f0fe4c151f5b0c3e383620c599215a188f23f2d367c78819b826"
)
DEFAULT_YAHOO_DIAGNOSTIC_ROOT = Path(
    "/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_audit/price_diagnostics"
)
YAHOO_DIAGNOSTIC_OBSERVED_ON = "2026-08-25"
YAHOO_DIAGNOSTIC_SHA256 = {
    "AAPL": "636df21618f5ad5108644432648ad4aa30615723bf6ef4d5762be04343af2fe8",
    "GOOGL": "be84e9e6d5662ffcd5603cc1f9181bee66a29ccde7dca0e9dc683c6fc6eae367",
    "AMZN": "5636e487c47d318c2e15daa6ff3b129ec4533eac4432d1dbeaef27c21bcefeb6",
}
YAHOO_DIAGNOSTIC_URLS = {
    ticker: (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        "?period1=1704067200&period2=1711929600&interval=1d&events=history&includeAdjustedClose=true"
    )
    for ticker in ("AAPL", "GOOGL", "AMZN")
}

PAPER_VERSIONS = {
    1: {
        "submitted_at": "2024-12-28T12:54:06Z",
        "pdf_sha256": "ed4729448e5a288ce1ed7b86181448a8f5e1b271b742cf0e39b836bc382667c2",
        "pdf_bytes": 2438241,
        "pdf_pages": 27,
        "source_sha256": "0e94d0b50bc501201d158795d5a991f35390030007bcf74f62ed4d1556bebb42",
        "source_bytes": 1701575,
        "source_files": 25,
        "source_uncompressed_bytes": 2329271,
        "main_path": "aaai25.tex",
        "main_sha256": "c6a4020732cff55be9b28e5242c86d8f0c5e799ee8a39e500e7d36446d4d1018",
        "table_sha256": "a82934597f6ac2a9b77a3c0e023c31cb8d7a875caa1820a2208558f50b0f0eb6",
        "repository_commits_at_submission": 9,
        "latest_public_commit_at_submission": "0ef7b4657943d6a393fb3b135236080f4a116ab3",
        "public_tree_files_at_submission": 2,
        "compare_figure_generation": "original_stockgpt_legend",
    },
    2: {
        "submitted_at": "2025-01-09T16:36:26Z",
        "pdf_sha256": "89a6ec3de2a76f1c2aae530d8dbdffe8bb0caf82ee3561f5998c6489f528cabf",
        "pdf_bytes": 2438273,
        "pdf_pages": 27,
        "source_sha256": "7b58fe12ee4bb9eab117a495cb78ca6f9d986c93ad6ace01ab6fc304618f8f07",
        "source_bytes": 1705530,
        "source_files": 25,
        "source_uncompressed_bytes": 2329881,
        "main_path": "aaai25.tex",
        "main_sha256": "b7fdf8d2a8b4170809c57596fe9b9a4e03b8cbf93d056d2b7d4448739e07f188",
        "table_sha256": "a82934597f6ac2a9b77a3c0e023c31cb8d7a875caa1820a2208558f50b0f0eb6",
        "repository_commits_at_submission": 12,
        "latest_public_commit_at_submission": "413d9ecbcfa960420ebda55f97372a2b638097f4",
        "public_tree_files_at_submission": 3,
        "compare_figure_generation": "original_stockgpt_legend",
    },
    3: {
        "submitted_at": "2025-01-10T20:02:32Z",
        "pdf_sha256": "bab7dccd7a3f9d6d586ba7a6a6266fb137a443ea2042cab9198021afbbc9f9ee",
        "pdf_bytes": 2439443,
        "pdf_pages": 27,
        "source_sha256": "f73e6cf850b6cab841a8c6278ffec316dd96e7404c18890868df9fbf0c1328dd",
        "source_bytes": 1714273,
        "source_files": 25,
        "source_uncompressed_bytes": 2329893,
        "main_path": "aaai25.tex",
        "main_sha256": "dc8d6bdfc9380c0c65a9951eb38d785b4ff956c0b737b2022dede74cd0e65d2c",
        "table_sha256": "a82934597f6ac2a9b77a3c0e023c31cb8d7a875caa1820a2208558f50b0f0eb6",
        "repository_commits_at_submission": 12,
        "latest_public_commit_at_submission": "413d9ecbcfa960420ebda55f97372a2b638097f4",
        "public_tree_files_at_submission": 3,
        "compare_figure_generation": "original_stockgpt_legend",
    },
    4: {
        "submitted_at": "2025-02-23T18:23:52Z",
        "pdf_sha256": "be1d6c91748834330f70433795fd26654a2a6255fac8646bc53b4e9426072744",
        "pdf_bytes": 2457207,
        "pdf_pages": 27,
        "source_sha256": "941690d21485fc138cd8ae0c0628b9191581dd0754a2c2bbfed5db719c6b927c",
        "source_bytes": 1706631,
        "source_files": 25,
        "source_uncompressed_bytes": 2329056,
        "main_path": "aaai25.tex",
        "main_sha256": "64b3e7fb90440758bcf82cedc86dc009bf0359ce842d2ffe89eab6ad1cfbfeb6",
        "table_sha256": "f7107171ff7c27d239743c7d7cccd97e4267ca7be3ed05affd2a7e38d8549711",
        "repository_commits_at_submission": 19,
        "latest_public_commit_at_submission": PRE_RELEASE_COMMIT,
        "public_tree_files_at_submission": 3,
        "compare_figure_generation": "original_stockgpt_legend",
    },
    5: {
        "submitted_at": "2025-03-02T15:57:39Z",
        "pdf_sha256": "e567beba01cb6f1c641c9beef49fd305d32c3efd74f08cc5ce1df11499167973",
        "pdf_bytes": 2456554,
        "pdf_pages": 27,
        "source_sha256": "8d9f88f6761938906fed37bcfe679d3bbe7809ab69a154cd0c209b9a4e7a72ba",
        "source_bytes": 1704734,
        "source_files": 25,
        "source_uncompressed_bytes": 2329045,
        "main_path": "aaai25.tex",
        "main_sha256": "0418f40c37fb41ab3ddba1283f46abf83e034df67cecd2042d97891b8d199dd5",
        "table_sha256": "f7107171ff7c27d239743c7d7cccd97e4267ca7be3ed05affd2a7e38d8549711",
        "repository_commits_at_submission": 19,
        "latest_public_commit_at_submission": PRE_RELEASE_COMMIT,
        "public_tree_files_at_submission": 3,
        "compare_figure_generation": "original_stockgpt_legend",
    },
    6: {
        "submitted_at": "2025-04-15T19:23:27Z",
        "pdf_sha256": "c1b58227ff5dc3a02f0482e57d14ea368cf517ed692c102fb2323aed4abab8ce",
        "pdf_bytes": 2599685,
        "pdf_pages": 27,
        "source_sha256": "90aaa45bc8905d7e2e1f61f01d38692b66a5f87bacaf4ae65845694a794ce656",
        "source_bytes": 1854705,
        "source_files": 26,
        "source_uncompressed_bytes": 2501606,
        "main_path": "aaai25.tex",
        "main_sha256": "fb4d6b69731952123585fe40e3f1b3aab238e65204b15f35dc201eaf70df8a09",
        "table_sha256": "f7107171ff7c27d239743c7d7cccd97e4267ca7be3ed05affd2a7e38d8549711",
        "repository_commits_at_submission": 19,
        "latest_public_commit_at_submission": PRE_RELEASE_COMMIT,
        "public_tree_files_at_submission": 3,
        "compare_figure_generation": "original_stockgpt_legend",
    },
    7: {
        "submitted_at": PAPER_DATE,
        "pdf_sha256": PAPER_SHA256,
        "pdf_bytes": 1903362,
        "pdf_pages": 38,
        "source_sha256": PAPER_SOURCE_SHA256,
        "source_bytes": 1422118,
        "source_files": 26,
        "source_uncompressed_bytes": 1795582,
        "main_path": "main.tex",
        "main_sha256": "9074ffe583f36834d97c0a8676519fb89332ecfc8502963046225291bb43f4d3",
        "table_sha256": "00c777122162fe05520a7f45212ee34d226fb0d5e363fc9347404795c2632ca4",
        "repository_commits_at_submission": 19,
        "latest_public_commit_at_submission": PRE_RELEASE_COMMIT,
        "public_tree_files_at_submission": 3,
        "compare_figure_generation": "reencoded_tradingagents_legend",
    },
}

ORIGINAL_COMPARE_SHA256 = {
    "AAPL": "8fae0c90b23e7b7680575de2b5faefe8742c7c388a7a93826daa1339eca9026f",
    "GOOGL": "3fa5ce1753aaf625d5a34f39346a6622bd47479005d350e26d3ccb82d5058e77",
    "AMZN": "18c687b80ca1d3e4dac64ffc3de4113153a45b14726fbcbfef02edd9a0320e45",
}
PUBLIC_HISTORY_COMMIT_COUNT = 257
PUBLIC_HISTORY_COMMIT_SHA256 = "6f0c8a613b9fa0f19c0a14c0c659b17725914618075fc39b498fcd0f21b27575"
PUBLIC_HISTORY_PATH_COUNT = 189
PUBLIC_HISTORY_PATH_SHA256 = "4bac9550fa14b23de1db1ecb1aacf659dcada3946496e3de2c8f3b6fa616c534"
PUBLIC_HISTORY_OBJECT_COUNTS = {"blob": 1009, "commit": 257, "tag": 7, "tree": 918}
PUBLIC_DISCOVERY_SHA256 = {
    "branches.json": "fdeef154d01c23e4c8c8ed663ba39bc5ad38b7bcf12726d3b961edb0a7e855d1",
    "releases.json": "9e183c10d90535590256f690d019766facff63427086ba2dd984c60a614ba856",
    "tags.json": "9272a23403304eb2c8849262998dbddcd8c6d03f636495059563e7131b9afe9d",
}

PINNED_SOURCE_SHA256 = {
    "README.md": "aed2e950144639d239d9cb20b0c8ccd58ac6cb9aba611b5142de802289b7c236",
    "requirements.txt": "cdae55137676f17d91918e8d3a492b9e2d1c0d716829955e7764245096bfa577",
    "tradingagents/default_config.py": "8c4f20a0fadcb731d0690e98e7efc8c2944247e0d1ecbf7e1f49f145fc449dde",
    "tradingagents/graph/trading_graph.py": "d8a8477f6e16c1fcda3bfa579485e895a44602747a0929fd086284857ded8ee5",
    "tradingagents/graph/setup.py": "7437ae4c52769adad0beaa71d71bd90a98f18037998bbbb405330f27d5e15d93",
    "tradingagents/graph/conditional_logic.py": "8ec347c2b9a4581f6aa9cc9febf0ad6f777ea289cfffee22c6448957012cecec",
    "tradingagents/graph/propagation.py": "f0a2304b19e2ac5de92456795c37b87e9ec34873dfabc3947b6c1c1aea974ae5",
    "tradingagents/graph/reflection.py": "31a94b13591f13f907e58239406fac79aafaeb55e355f6447a0d96877beebfdd",
    "tradingagents/graph/signal_processing.py": "563df40af1bcffb29623f35c36f4d2f5950863ae78809581bcb7d7eef47591c2",
    "tradingagents/dataflows/interface.py": "4bdf5c2105ea82bae87e0021b32adfd61e3e45f45208d5de7d8886cd7eae1a1c",
}

PINNED_PAPER_SOURCE_SHA256 = {
    "main.tex": "9074ffe583f36834d97c0a8676519fb89332ecfc8502963046225291bb43f4d3",
    "tables/results.tex": "00c777122162fe05520a7f45212ee34d226fb0d5e363fc9347404795c2632ca4",
    "sections/3.methodology.tex": "5ded949606f9b9a72107356130403e60b73f06b4af408f77d67f6aa145ba45d9",
    "sections/4.expreiments.tex": "a7c50641d9eda9b80ea5c5492e97b99b370a5581eabd042b87dd7fcec4363801",
    "sections/5.results.tex": "fdc4eff57e031348cc0ae76204fff1623e6f11da8730dca9746f9c4fb0cc8bc2",
    "sections/appendix.tex": "14fe36d8bcf485b0e68714e161d9ba822ca2f78dae2442ede5b7f252766638f2",
    "sections/cases.tex": "5cbbda36e8bd6ce15e4fd7d46d315a438af6cdb254b4865b1aa5347141e60fed",
}

FIGURE_SHA256 = {
    "figures/AAPL/compare.pdf": "253c734192f00311c7ea5d01be0b551d84625bcce3fafee2ce7606cb56e3f9e4",
    "figures/AAPL/details.pdf": "4e7e79165f6f6c0803468e54fe1b446ecc81882106bebd942451defcf55d7607",
    "figures/AMZN/compare.pdf": "d037f3f53461689a8661118edf318e81450e18e87f70e66cfadde540a66b4326",
    "figures/AMZN/details.pdf": "56b380a7103985e142e76ae6d3b0ec1b0ec8394d7677c7bca5b18d0d5476f3c5",
    "figures/GOOGL/compare.pdf": "981423ff58684e6153f393b1ce423e6613223383188482cc616d31adbd333610",
    "figures/GOOGL/details.pdf": "6fabc415d0eaf6c0bcd29ba89534fdb1c6a2acaad047db320dd373941c54025f",
}

COMPARE_SERIES = (
    "BuyAndHoldStrategy",
    "MACDStrategy",
    "KDJRSIStrategy",
    "ZMRStrategy",
    "SMAStrategy",
    "TradingAgents (StockGPTStrategy label in v1-v6)",
)
DETAIL_SERIES = (
    ("broker", "cash"),
    ("broker", "value"),
    ("trade_net_profit_loss", "positive trades"),
    ("trade_net_profit_loss", "negative trades"),
    ("market", "OHLC candlesticks"),
    ("market", "volume bars"),
    ("transactions", "buy markers"),
    ("transactions", "sell markers"),
)
NATIVE_RESULT_EXTENSIONS = {
    ".ckpt",
    ".csv",
    ".h5",
    ".hdf5",
    ".ipynb",
    ".jsonl",
    ".log",
    ".npy",
    ".npz",
    ".parquet",
    ".pickle",
    ".pkl",
    ".pt",
    ".pth",
}

METRICS = ("CR_pct", "AR_pct", "SR", "MDD_pct")
ASSETS = ("AAPL", "GOOGL", "AMZN")
PERFORMANCE: dict[str, dict[str, tuple[float | None, ...]]] = {
    "B&H": {
        "AAPL": (-5.23, -5.09, -1.29, 11.90),
        "GOOGL": (7.78, 8.09, 1.35, 13.04),
        "AMZN": (17.1, 17.6, 3.53, 3.80),
    },
    "MACD": {
        "AAPL": (-1.49, -1.48, -0.81, 4.53),
        "GOOGL": (6.20, 6.26, 2.31, 1.22),
        "AMZN": (None, None, None, None),
    },
    "KDJ&RSI": {
        "AAPL": (2.05, 2.07, 1.64, 1.09),
        "GOOGL": (0.4, 0.4, 0.02, 1.58),
        "AMZN": (-0.77, -0.76, -2.25, 1.08),
    },
    "ZMR": {
        "AAPL": (0.57, 0.57, 0.17, 0.86),
        "GOOGL": (-0.58, 0.58, 2.12, 2.34),
        "AMZN": (-0.77, -0.77, -2.45, 0.82),
    },
    "SMA": {
        "AAPL": (-3.2, -2.97, -1.72, 3.67),
        "GOOGL": (6.23, 6.43, 2.12, 2.34),
        "AMZN": (11.01, 11.6, 2.22, 3.97),
    },
    "TradingAgents": {
        "AAPL": (26.62, 30.5, 8.21, 0.91),
        "GOOGL": (24.36, 27.58, 6.39, 1.69),
        "AMZN": (23.21, 24.90, 5.60, 2.11),
    },
}

IMPROVEMENT = {
    "AAPL": (24.57, 28.43, 6.57, None),
    "GOOGL": (16.58, 19.49, 4.26, None),
    "AMZN": (6.10, 7.30, 2.07, None),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def run_git(source_root: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return result.stdout


def git_blob_at(source_root: Path, commit: str, relative: str) -> bytes:
    return run_git(source_root, "show", f"{commit}:{relative}", binary=True)  # type: ignore[return-value]


def git_blob(source_root: Path, relative: str) -> bytes:
    return git_blob_at(source_root, SOURCE_COMMIT, relative)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_table_rows(author_output_verified: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method, by_asset in PERFORMANCE.items():
        for asset in ASSETS:
            for metric, value in zip(METRICS, by_asset[asset]):
                if value is None:
                    continue
                status = (
                    "unavailable_missing_native_paper_result_path"
                    if method == "TradingAgents"
                    else "unavailable_missing_native_baseline_result_path"
                )
                rows.append(
                    {
                        "paper_table": 1,
                        "cell_kind": "direct_result",
                        "method": method,
                        "asset": asset,
                        "period": "2024-01-01 to 2024-03-29",
                        "metric": metric,
                        "paper_value": value,
                        "author_output_value": value if author_output_verified else "",
                        "author_output_correspondence": author_output_verified,
                        "native_reproduced_value": "",
                        "absolute_difference": "",
                        "status": (
                            "corroborated_by_exact_author_project_site_table_not_regenerated"
                            if author_output_verified
                            else status
                        ),
                        "paper_result_credit": False,
                    }
                )
    for asset in ASSETS:
        for metric, value in zip(METRICS, IMPROVEMENT[asset]):
            if value is None:
                continue
            rows.append(
                {
                    "paper_table": 1,
                    "cell_kind": "derived_improvement",
                    "method": "Improvement(%)",
                    "asset": asset,
                    "period": "2024-01-01 to 2024-03-29",
                    "metric": metric,
                    "paper_value": value,
                    "author_output_value": value if author_output_verified else "",
                    "author_output_correspondence": author_output_verified,
                    "native_reproduced_value": "",
                    "absolute_difference": "",
                    "status": (
                        "corroborated_by_exact_author_project_site_table_not_regenerated"
                        if author_output_verified
                        else "unavailable_missing_native_inputs"
                    ),
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 77 or Counter(row["cell_kind"] for row in rows) != {
        "direct_result": 68,
        "derived_improvement": 9,
    }:
        raise RuntimeError("TradingAgents Table 1 numeric-cell denominator changed")
    return rows


def current_yahoo_buy_hold_diagnostic(root: Path) -> list[dict[str, Any]]:
    """Check the literal B&H window against a pinned current Yahoo response.

    The paper lists Yahoo among several data sources but never identifies the
    provider used for prices, so these rows are adverse current-public
    correspondence rather than paper-time input or result credit.
    """
    inclusive_days = (date(2024, 3, 29) - date(2024, 1, 1)).days + 1
    years = inclusive_days / 365.25
    formulas = {
        "CR_pct": "100 * (last_adjusted_close / first_adjusted_close - 1)",
        "AR_pct": "paper literal: 100 * ((last / first) ** (1 / (89 / 365.25)) - 1)",
        "SR": "zero-risk-free diagnostic: mean(simple daily return) / sample SD * sqrt(252)",
        "MDD_pct": "100 * maximum peak-to-trough drawdown of adjusted close",
    }
    output: list[dict[str, Any]] = []
    for asset in ASSETS:
        path = root / f"{asset}_2024q1_yahoo.json"
        if sha256(path) != YAHOO_DIAGNOSTIC_SHA256[asset]:
            raise RuntimeError(f"Pinned current Yahoo response changed: {asset}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("chart", {}).get("error") is not None:
            raise RuntimeError(f"Pinned current Yahoo response is an error: {asset}")
        results = payload["chart"]["result"]
        if len(results) != 1 or results[0]["meta"]["symbol"] != asset:
            raise RuntimeError(f"Pinned current Yahoo response identity changed: {asset}")
        result = results[0]
        timestamps = result["timestamp"]
        prices = result["indicators"]["adjclose"][0]["adjclose"]
        if len(timestamps) != 61 or len(prices) != 61 or any(value is None for value in prices):
            raise RuntimeError(f"Pinned current Yahoo response row count changed: {asset}")
        dates = [
            datetime.fromtimestamp(value, timezone.utc).date().isoformat()
            for value in timestamps
        ]
        if dates[0] != "2024-01-02" or dates[-1] != "2024-03-28":
            raise RuntimeError(f"Pinned current Yahoo response date range changed: {asset}")
        values = [float(value) for value in prices]
        returns = [values[index] / values[index - 1] - 1 for index in range(1, len(values))]
        mean = sum(returns) / len(returns)
        sample_variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
        sample_sd = sample_variance**0.5
        cumulative_return = values[-1] / values[0] - 1
        annualized_return = (1 + cumulative_return) ** (1 / years) - 1
        peak = values[0]
        maximum_drawdown = 0.0
        for value in values:
            peak = max(peak, value)
            maximum_drawdown = max(maximum_drawdown, (peak - value) / peak)
        diagnostics = {
            "CR_pct": 100 * cumulative_return,
            "AR_pct": 100 * annualized_return,
            "SR": mean / sample_sd * (252**0.5),
            "MDD_pct": 100 * maximum_drawdown,
        }
        paper_values = dict(zip(METRICS, PERFORMANCE["B&H"][asset]))
        for metric in METRICS:
            observed = diagnostics[metric]
            paper_value = float(paper_values[metric])
            difference = observed - paper_value
            output.append(
                {
                    "asset": asset,
                    "metric": metric,
                    "paper_value": paper_value,
                    "current_yahoo_diagnostic_value": observed,
                    "current_minus_paper": difference,
                    "display_precision_match": abs(difference) <= 0.005,
                    "formula": formulas[metric],
                    "formula_fully_specified_by_paper": metric != "SR",
                    "response_rows": len(values),
                    "response_start": dates[0],
                    "response_end": dates[-1],
                    "response_sha256": YAHOO_DIAGNOSTIC_SHA256[asset],
                    "response_url": YAHOO_DIAGNOSTIC_URLS[asset],
                    "observed_on": YAHOO_DIAGNOSTIC_OBSERVED_ON,
                    "paper_price_provider_mapping_recovered": False,
                    "paper_time_input_lineage": False,
                    "native_paper_result_credit": False,
                    "status": "current_public_yahoo_diagnostic_mismatch_no_paper_time_lineage",
                }
            )
    if len(output) != 12 or any(row["display_precision_match"] for row in output):
        raise RuntimeError("Current Yahoo B&H diagnostic boundary changed")
    return output


def expected_table_values() -> list[float]:
    return [
        float(value)
        for method in PERFORMANCE.values()
        for asset in ASSETS
        for value in method[asset]
        if value is not None
    ] + [
        float(value)
        for asset in ASSETS
        for value in IMPROVEMENT[asset]
        if value is not None
    ]


def exact_html_table_values(payload: bytes) -> list[float]:
    if b"TradingAgents" not in payload or b"26.62" not in payload:
        return []
    html = payload.decode("utf-8", errors="replace")
    for table_html in re.findall(r"<table[^>]*>(.*?)</table>", html, re.S):
        cells = [
            re.sub(r"<[^>]+>", "", cell).strip()
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", table_html, re.S)
        ]
        observed = []
        for cell in cells:
            normalized = cell.replace("&amp;", "&").replace("%", "")
            try:
                observed.append(float(normalized))
            except ValueError:
                continue
        if observed == expected_table_values():
            return observed
    return []


def author_output_correspondence(source_root: Path) -> list[dict[str, Any]]:
    payload = git_blob_at(source_root, PRE_RELEASE_COMMIT, PRE_RELEASE_TABLE_PATH)
    observed_hash = sha256_bytes(payload)
    if observed_hash != PRE_RELEASE_TABLE_SHA256:
        raise RuntimeError(f"Pre-release project-site hash changed: {observed_hash}")

    observed = exact_html_table_values(payload)
    if len(observed) != 77:
        raise RuntimeError("Official project-site Table 1 no longer matches all 77 paper values in order")

    return [
        {
            "output": "table_1",
            "source_commit": PRE_RELEASE_COMMIT,
            "source_commit_date": PRE_RELEASE_COMMIT_DATE,
            "repository_path": PRE_RELEASE_TABLE_PATH,
            "repository_sha256": observed_hash,
            "correspondence_kind": "exact_ordered_numeric_html_table_correspondence",
            "published_result_units_corroborated": len(observed),
            "underlying_numeric_arrays_shipped": 0,
            "independently_regenerated": False,
            "paper_result_credit": False,
        }
    ]


def pdf_page_count(path: Path) -> int:
    output = subprocess.run(
        ["pdfinfo", str(path)], check=True, capture_output=True, text=True
    ).stdout
    match = re.search(r"^Pages:\s+(\d+)$", output, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"pdfinfo did not report a page count for {path}")
    return int(match.group(1))


def paper_version_inventory(versions_root: Path, source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for version, expected in PAPER_VERSIONS.items():
        pdf_path = versions_root / f"paper_v{version}.pdf"
        archive_path = versions_root / f"paper_v{version}_source.tar.gz"
        if sha256(pdf_path) != expected["pdf_sha256"] or pdf_path.stat().st_size != expected["pdf_bytes"]:
            raise RuntimeError(f"TradingAgents paper v{version} PDF drift")
        if pdf_page_count(pdf_path) != expected["pdf_pages"]:
            raise RuntimeError(f"TradingAgents paper v{version} page census changed")
        if sha256(archive_path) != expected["source_sha256"] or archive_path.stat().st_size != expected["source_bytes"]:
            raise RuntimeError(f"TradingAgents paper v{version} source archive drift")
        with tarfile.open(archive_path) as archive:
            files = [member for member in archive.getmembers() if member.isfile()]
            if len(files) != expected["source_files"]:
                raise RuntimeError(f"TradingAgents paper v{version} source-file census changed")
            if sum(member.size for member in files) != expected["source_uncompressed_bytes"]:
                raise RuntimeError(f"TradingAgents paper v{version} source byte census changed")

            def archive_bytes(relative: str) -> bytes:
                handle = archive.extractfile(relative)
                if handle is None:
                    raise RuntimeError(f"TradingAgents paper v{version} missing {relative}")
                return handle.read()

            main = archive_bytes(str(expected["main_path"]))
            table = archive_bytes("tables/results.tex")
            compare = {
                asset: archive_bytes(f"figures/{asset}/compare.pdf") for asset in ASSETS
            }
            details = {
                asset: archive_bytes(f"figures/{asset}/details.pdf") for asset in ASSETS
            }
        if sha256_bytes(main) != expected["main_sha256"]:
            raise RuntimeError(f"TradingAgents paper v{version} main TeX drift")
        if sha256_bytes(table) != expected["table_sha256"]:
            raise RuntimeError(f"TradingAgents paper v{version} Table 1 source drift")
        expected_compare = FIGURE_SHA256 if version == 7 else {
            f"figures/{asset}/compare.pdf": ORIGINAL_COMPARE_SHA256[asset] for asset in ASSETS
        }
        for asset in ASSETS:
            if sha256_bytes(compare[asset]) != expected_compare[f"figures/{asset}/compare.pdf"]:
                raise RuntimeError(f"TradingAgents paper v{version} {asset} comparison figure drift")
            if sha256_bytes(details[asset]) != FIGURE_SHA256[f"figures/{asset}/details.pdf"]:
                raise RuntimeError(f"TradingAgents paper v{version} {asset} detail figure drift")

        cutoff = str(expected["submitted_at"])
        commit_count = int(str(run_git(source_root, "rev-list", "--all", f"--before={cutoff}", "--count")).strip())
        latest = str(
            run_git(source_root, "log", "--all", f"--before={cutoff}", "-1", "--format=%H")
        ).strip()
        if commit_count != expected["repository_commits_at_submission"] or latest != expected["latest_public_commit_at_submission"]:
            raise RuntimeError(f"TradingAgents public-source cutoff changed for paper v{version}")
        cutoff_files = git_files_at(source_root, latest)
        if len(cutoff_files) != expected["public_tree_files_at_submission"]:
            raise RuntimeError(f"TradingAgents cutoff tree changed for paper v{version}")
        table_paths = []
        for relative in cutoff_files:
            if not relative.endswith(".html"):
                continue
            if len(exact_html_table_values(git_blob_at(source_root, latest, relative))) == 77:
                table_paths.append(relative)
        if not table_paths or any(relative.endswith(".py") for relative in cutoff_files):
            raise RuntimeError(f"TradingAgents paper-era site/code boundary changed for v{version}")
        rows.append(
            {
                "paper_version": f"v{version}",
                "submitted_at": cutoff,
                "pdf_sha256": expected["pdf_sha256"],
                "pdf_bytes": expected["pdf_bytes"],
                "pdf_pages": expected["pdf_pages"],
                "source_archive_sha256": expected["source_sha256"],
                "source_archive_bytes": expected["source_bytes"],
                "source_files": expected["source_files"],
                "source_uncompressed_bytes": expected["source_uncompressed_bytes"],
                "main_tex_sha256": expected["main_sha256"],
                "table_1_tex_sha256": expected["table_sha256"],
                "displayed_table_numeric_cells": 77,
                "displayed_result_figure_series": 42,
                "table_values_same_as_v7": True,
                "compare_plot_final_series_label": "TradingAgents" if version == 7 else "StockGPTStrategy",
                "compare_plot_pdf_same_as_v1": version <= 6,
                "detail_plot_pdfs_same_as_v1": True,
                "public_repository_commits_at_submission": commit_count,
                "latest_public_commit_at_submission": latest,
                "public_tree_files_at_submission": len(cutoff_files),
                "exact_author_table_paths_at_submission": ";".join(table_paths),
                "executable_source_present_at_submission": False,
                "public_source_state": "exact_author_site_table_only_no_executable_implementation",
                "native_result_reproduced": False,
                "paper_result_credit": False,
            }
        )
    return rows


def paper_figure_series() -> list[dict[str, Any]]:
    rows = []
    for asset in ASSETS:
        compare_path = f"figures/{asset}/compare.pdf"
        for series in COMPARE_SERIES:
            rows.append(
                {
                    "figure": f"{asset} cumulative-return comparison",
                    "source_asset": compare_path,
                    "asset": asset,
                    "panel": "cumulative_return",
                    "series": series,
                    "v7_source_pdf_sha256": FIGURE_SHA256[compare_path],
                    "paper_source_asset_present": True,
                    "underlying_numeric_data_or_plot_code_released": False,
                    "native_exact_series_reproduced": False,
                    "status": "author_vector_figure_only_no_numeric_curve_array",
                    "paper_result_credit": False,
                }
            )
        details_path = f"figures/{asset}/details.pdf"
        for panel, series in DETAIL_SERIES:
            rows.append(
                {
                    "figure": f"{asset} detailed transaction history",
                    "source_asset": details_path,
                    "asset": asset,
                    "panel": panel,
                    "series": series,
                    "v7_source_pdf_sha256": FIGURE_SHA256[details_path],
                    "paper_source_asset_present": True,
                    "underlying_numeric_data_or_plot_code_released": False,
                    "native_exact_series_reproduced": False,
                    "status": "author_vector_figure_only_no_numeric_series_or_event_array",
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 42:
        raise RuntimeError("TradingAgents result-figure series census changed")
    return rows


def current_source_conformance(source_root: Path) -> list[dict[str, Any]]:
    files = git_files_at(source_root, CURRENT_SOURCE_COMMIT)
    python_files = [path for path in files if path.endswith(".py")]
    python_text = "\n".join(
        git_blob_at(source_root, CURRENT_SOURCE_COMMIT, path).decode("utf-8", errors="replace")
        for path in python_files
    )
    setup = git_blob_at(source_root, CURRENT_SOURCE_COMMIT, "tradingagents/graph/setup.py").decode()
    signal = git_blob_at(source_root, CURRENT_SOURCE_COMMIT, "tradingagents/graph/signal_processing.py").decode()
    baseline_implementation = any(
        token in python_text
        for token in ("BuyAndHoldStrategy", "KDJRSIStrategy", "ZMRStrategy", "SMAStrategy")
    )
    metric_implementation = any(
        token in python_text.lower()
        for token in ("max_drawdown", "sharpe_ratio", "cumulative_return")
    )
    execution_implementation = any(
        token in python_text.lower() for token in ("initial_capital", "commission", "slippage")
    )
    backtest_path = any("backtest" in Path(path).name.lower() for path in python_files)
    native_result_path = any(Path(path).suffix.lower() in NATIVE_RESULT_EXTENSIONS for path in files)
    rows = [
        ("separate_portfolio_manager", "separate fund manager", 'workflow.add_node("Portfolio Manager"' in setup, "later_component_match"),
        ("analyst_concurrency", "four analysts concurrently gather data", "# Connect analysts in sequence" not in setup, "still_mismatch_sequential"),
        ("paper_model_assignment", "deep models for analysts/researchers/trader", "create_market_analyst(self.deep_thinking_llm)" in setup, "still_mismatch_quick_models"),
        ("decision_vocabulary", "buy/sell/hold", "5-tier portfolio rating" not in signal, "changed_to_five_tier_rating"),
        ("portfolio_execution_state", "cash, holdings, positions, orders, and fills", execution_implementation, "still_missing"),
        ("paper_backtest_runner", "2024-01-01 through 2024-03-29 replay", backtest_path, "still_missing"),
        ("paper_baseline_implementations", "B&H, MACD, KDJ+RSI, ZMR, SMA", baseline_implementation, "still_missing"),
        ("paper_metric_implementations", "CR, AR, SR, and MDD evaluator", metric_implementation, "still_missing"),
        ("paper_data_and_outputs", "frozen inputs, decisions, fills, NAVs, returns, and plot arrays", native_result_path, "still_missing"),
        (
            "modern_source_quality",
            "tests and dependency lock",
            "54 test modules present; uv.lock absent from current main but present elsewhere in public history",
            "partial_tests_present_current_lock_absent_not_paper_reproduction",
        ),
    ]
    if len(files) != 160 or len(python_files) != 137:
        raise RuntimeError("TradingAgents current source census changed")
    if sum(path.startswith("tests/test_") and path.endswith(".py") for path in files) != 54:
        raise RuntimeError("TradingAgents current test census changed")
    if any((execution_implementation, backtest_path, baseline_implementation, metric_implementation, native_result_path)):
        raise RuntimeError("TradingAgents current source gained a paper reproduction mechanism requiring review")
    return [
        {
            "dimension": dimension,
            "paper_requirement": requirement,
            "observed_in_current_public_source": observed,
            "status": status,
            "paper_result_credit": False,
        }
        for dimension, requirement, observed, status in rows
    ]


def annualization_identity() -> list[dict[str, Any]]:
    inclusive_days = (date(2024, 3, 29) - date(2024, 1, 1)).days + 1
    years = inclusive_days / 365.25
    rows: list[dict[str, Any]] = []
    for method, by_asset in PERFORMANCE.items():
        for asset, values in by_asset.items():
            cr, ar = values[:2]
            if cr is None or ar is None:
                continue
            expected = ((1.0 + cr / 100.0) ** (1.0 / years) - 1.0) * 100.0
            difference = ar - expected
            rows.append(
                {
                    "method": method,
                    "asset": asset,
                    "paper_CR_pct": cr,
                    "paper_AR_pct": ar,
                    "inclusive_calendar_days": inclusive_days,
                    "N_years_literal": years,
                    "AR_pct_from_published_equation": expected,
                    "paper_minus_equation_pct_points": difference,
                    "display_precision_match": abs(difference) <= 0.015,
                    "status": "fails_literal_published_equation_at_display_precision",
                }
            )
    if len(rows) != 17 or any(row["display_precision_match"] for row in rows):
        raise RuntimeError("Published CR/AR identity boundary changed")
    return rows


def improvement_identity() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    baseline_methods = tuple(method for method in PERFORMANCE if method != "TradingAgents")
    for asset in ASSETS:
        for metric_index, metric in enumerate(METRICS[:3]):
            baseline = [
                PERFORMANCE[method][asset][metric_index]
                for method in baseline_methods
                if PERFORMANCE[method][asset][metric_index] is not None
            ]
            best = max(float(value) for value in baseline)
            ours = float(PERFORMANCE["TradingAgents"][asset][metric_index])
            published = float(IMPROVEMENT[asset][metric_index])
            expected = ours - best
            difference = published - expected
            if abs(difference) < 0.005:
                status = "exact_absolute_difference_from_displayed_cells"
            elif asset == "AMZN" and metric == "CR_pct" and abs(difference) <= 0.011:
                status = "not_exact_from_displayed_cells_hidden_precision_could_explain"
            else:
                status = "inconsistent_with_displayed_cells"
            rows.append(
                {
                    "asset": asset,
                    "metric": metric,
                    "best_displayed_baseline": best,
                    "TradingAgents_displayed": ours,
                    "paper_improvement_pct_label": published,
                    "absolute_difference_from_displayed_cells": expected,
                    "relative_improvement_pct": (expected / abs(best)) * 100.0,
                    "paper_minus_absolute_difference": difference,
                    "status": status,
                }
            )
    expected_counts = {
        "exact_absolute_difference_from_displayed_cells": 7,
        "not_exact_from_displayed_cells_hidden_precision_could_explain": 1,
        "inconsistent_with_displayed_cells": 1,
    }
    if Counter(row["status"] for row in rows) != expected_counts:
        raise RuntimeError("Published improvement identity boundary changed")
    return rows


def published_non_table_claims() -> list[dict[str, Any]]:
    raw = [
        ("Section 6.1.1", "minimum TradingAgents cumulative return", 23.21, "pct", "result", "exact"),
        ("Section 6.1.1", "minimum TradingAgents annual return", 24.90, "pct", "result", "exact"),
        ("Section 6.1.1", "margin over best baseline", 6.1, "pct", "result", "exact"),
        ("Section 6.1.1", "AAPL return lower bound", 26.0, "pct", "result", "lower_bound"),
        ("Section 6.1.3", "claimed maximum drawdown upper bound", 2.0, "pct", "result", "upper_bound"),
        ("Section 6.1.2 footnote", "LLM calls per prediction", 11.0, "calls", "configuration", "exact"),
        ("Section 6.1.2 footnote", "tool calls per prediction", 20.0, "calls", "configuration", "lower_bound"),
        ("Figure 6", "AAPL ending broker cash annotation", 246516.57, "currency_units", "result", "exact"),
        ("Figure 6", "AAPL ending broker value annotation", 130501.44, "currency_units", "result", "exact"),
        ("Figure S1", "AMZN ending broker cash annotation", 12315.59, "currency_units", "result", "exact"),
        ("Figure S1", "AMZN ending broker value annotation", 124872.71, "currency_units", "result", "exact"),
        ("Figure S3", "GOOGL ending broker cash annotation", 116445.06, "currency_units", "result", "exact"),
        ("Figure S3", "GOOGL ending broker value annotation", 127586.29, "currency_units", "result", "exact"),
        ("Figure S3", "GOOGL displayed negative trade PnL", -254.11, "currency_units", "result", "exact"),
    ]
    rows = []
    for location, claim, value, unit, role, exactness in raw:
        rows.append(
            {
                "paper_location": location,
                "claim": claim,
                "paper_value": value,
                "unit": unit,
                "claim_role": role,
                "exactness": exactness,
                "native_reproduced_value": "",
                "status": (
                    "unavailable_missing_native_paper_result_path"
                    if role == "result"
                    else "configuration_documented_not_reproduced"
                ),
                "paper_result_credit": False,
            }
        )
    if Counter(row["claim_role"] for row in rows) != {"result": 12, "configuration": 2}:
        raise RuntimeError("Non-table quantitative-claim boundary changed")
    return rows


def paper_internal_inconsistencies() -> list[dict[str, Any]]:
    return [
        {
            "dimension": "experiment_universe",
            "paper_evidence": "setup names Apple, Nvidia, Microsoft, Meta, Google; Table 1 reports AAPL, GOOGL, AMZN",
            "finding": "AMZN is not in the named five and NVDA/MSFT/META have no table results",
            "severity": "blocks_exact_scope",
        },
        {
            "dimension": "annualized_return_formula",
            "paper_evidence": "Appendix defines AR=(Vend/Vstart)^(1/N)-1 with N years; experiment spans 2024-01-01 to 2024-03-29",
            "finding": "all 17 displayed CR/AR pairs fail the literal equation at display precision",
            "severity": "paper_internal_numeric_inconsistency",
        },
        {
            "dimension": "GOOGL_ZMR_return_sign",
            "paper_evidence": "CR=-0.58% and AR=+0.58%",
            "finding": "the two signs cannot both follow the published formulas for positive N",
            "severity": "paper_internal_numeric_inconsistency",
        },
        {
            "dimension": "GOOGL_SR_improvement",
            "paper_evidence": "TradingAgents SR=6.39; best displayed baseline SR=2.31; improvement=4.26",
            "finding": "displayed subtraction is 4.08, not 4.26",
            "severity": "paper_internal_arithmetic_error",
        },
        {
            "dimension": "improvement_units",
            "paper_evidence": "row is labeled Improvement(%)",
            "finding": "seven cells are exact absolute metric-point differences, not relative percentage improvements",
            "severity": "metric_label_ambiguity",
        },
        {
            "dimension": "maximum_drawdown_claim",
            "paper_evidence": "text says maximum drawdown does not exceed 2; AMZN TradingAgents MDD is 2.11%",
            "finding": "the prose upper bound is contradicted by Table 1",
            "severity": "paper_internal_numeric_inconsistency",
        },
        {
            "dimension": "figure_value_metric_alignment",
            "paper_evidence": "broker values are 130501.44, 124872.71, 127586.29; initial capital is undisclosed",
            "finding": "under an inferred 100000 initial balance, implied returns align within 0.03 points of AR, not CR; this is suggestive only",
            "severity": "unresolved_metric_provenance",
        },
    ]


def case_tool_conformance(source_root: Path) -> list[dict[str, Any]]:
    released = git_blob(source_root, "tradingagents/agents/utils/agent_utils.py").decode()
    paper_tools = [
        ("get_EODHD_news", 1),
        ("get_EODHD_sentiment", 1),
        ("get_YFin_data", 1),
        ("get_finnhub_basic_company_financials", 1),
        ("get_finnhub_company_financials_history", 1),
        ("get_finnhub_company_insider_sentiment", 1),
        ("get_finnhub_company_insider_transactions", 1),
        ("get_finnhub_company_profile", 1),
        ("get_finnhub_news", 4),
        ("get_reddit_stock_info", 1),
        ("get_stockstats_indicators_report", 8),
    ]
    rows = []
    for tool, calls in paper_tools:
        exact = f"def {tool}(" in released
        rows.append(
            {
                "paper_case_tool": tool,
                "published_call_count": calls,
                "exact_name_in_v0_1_0": exact,
                "status": "exact_released_tool_name" if exact else "absent_from_nearest_release",
                "case_output_reproduced": False,
            }
        )
    if Counter(row["status"] for row in rows) != {
        "exact_released_tool_name": 6,
        "absent_from_nearest_release": 5,
    }:
        raise RuntimeError("Appendix case-tool boundary changed")
    return rows


def specification_gaps() -> list[dict[str, Any]]:
    raw = [
        ("asset_scope", "prose and Table 1 disagree on the tested assets", "blocks exact experiment set"),
        ("frozen_data", "no paper-era price/news/social/fundamental snapshot is released", "blocks input identity"),
        (
            "point_in_time_data",
            "publication and revision timestamps for every text/fundamental item are absent",
            "blocks look-ahead audit",
        ),
        (
            "data_provider_mapping",
            "provider-to-field and fallback precedence are not disclosed",
            "blocks multimodal reconstruction",
        ),
        (
            "sentiment_model",
            "auxiliary sentiment model, prompt, version, and outputs are absent",
            "blocks sentiment feature",
        ),
        (
            "technical_indicators",
            "the complete 60-indicator names, parameters, and warmups are absent",
            "blocks technical input",
        ),
        ("llm_snapshots", "model families are named without immutable API snapshots", "blocks LLM replay"),
        ("prompts", "exact experiment prompts and tool schemas are not pinned in the paper", "blocks agent replay"),
        (
            "sampling",
            "temperatures, seeds, token limits, retries, and concurrency are incomplete",
            "blocks stochastic replay",
        ),
        (
            "agent_model_assignment",
            "paper prose and nearest source disagree on quick/deep assignment",
            "blocks node equivalence",
        ),
        ("debate_rounds", "n and facilitator stopping behavior are not reported", "blocks debate trajectory"),
        ("trials", "number of trials and aggregation/selection rule are absent", "blocks table estimator"),
        ("initial_capital", "starting cash is not stated", "blocks portfolio values"),
        ("position_sizing", "size, limits, leverage, and cash constraints are absent", "blocks holdings"),
        ("execution_timing", "signal time, order time, execution price, and latency are absent", "blocks returns"),
        ("shorting", "short/borrow/margin semantics behind figure captions are absent", "blocks short positions"),
        ("costs", "commissions, bid-ask spread, slippage, and borrow costs are absent", "blocks net returns"),
        ("corporate_actions", "dividend and split treatment is not specified", "blocks value path"),
        (
            "multi_asset_portfolio",
            "cross-asset capital allocation and rebalance semantics are absent",
            "blocks portfolio interpretation",
        ),
        (
            "baseline_parameters",
            "lookbacks, thresholds, sizing, and execution rules for five baselines are absent",
            "blocks baselines",
        ),
        ("ZMR_definition", "zero reference line and signal rule are not mathematically specified", "blocks ZMR"),
        ("risk_free_rate", "Sharpe risk-free series/value is not reported", "blocks SR"),
        ("return_frequency", "Sharpe return frequency and annualization convention are absent", "blocks SR"),
        ("annualization_N", "N convention conflicts with the displayed AR values", "blocks AR target"),
        (
            "metric_arrays",
            "daily NAVs, returns, holdings, and exact plot arrays are absent",
            "blocks figures and metrics",
        ),
        (
            "backtest_outputs",
            "actions, orders, fills, reflections, and baseline outputs are absent",
            "blocks result verification",
        ),
        (
            "cost_accounting",
            "paper reports calls per prediction but no token/API cost ledger",
            "blocks cost reproduction",
        ),
    ]
    return [
        {"dimension": dimension, "missing_or_ambiguous_specification": gap, "consequence": consequence}
        for dimension, gap, consequence in raw
    ]


def source_conformance(source_root: Path) -> list[dict[str, Any]]:
    config = git_blob(source_root, "tradingagents/default_config.py").decode()
    graph = git_blob(source_root, "tradingagents/graph/trading_graph.py").decode()
    setup = git_blob(source_root, "tradingagents/graph/setup.py").decode()
    logic = git_blob(source_root, "tradingagents/graph/conditional_logic.py").decode()
    interface = git_blob(source_root, "tradingagents/dataflows/interface.py").decode()
    readme = git_blob(source_root, "README.md").decode()
    requirements = git_blob(source_root, "requirements.txt").decode()
    files = set(git_files(source_root))

    checks = [
        (
            "public_revision_timing",
            "paper-era implementation by 2025-06-03",
            "first code release 2025-06-05; predecessor has only three site files",
            "nearest_post_paper_release",
            False,
        ),
        (
            "four_analyst_roles",
            "fundamental, sentiment/social, news, technical/market",
            "four corresponding analyst nodes",
            "component_match",
            True,
        ),
        (
            "analyst_concurrency",
            "four analysts concurrently gather information",
            "analysts execute sequentially in selected_analysts order",
            "mismatch",
            False,
        ),
        (
            "structured_global_state",
            "structured reports in shared state",
            "typed AgentState report fields and message clearing",
            "component_match",
            True,
        ),
        (
            "bull_bear_debate",
            "bull and bear researchers",
            "Bull Researcher and Bear Researcher routing",
            "component_match",
            True,
        ),
        (
            "research_facilitator",
            "facilitator selects prevailing view",
            "Research Manager node",
            "component_match",
            True,
        ),
        ("trader", "trader synthesizes reports/debate", "Trader node and investment plan", "component_match", True),
        (
            "risk_perspectives",
            "risk-seeking, neutral, conservative debate",
            "Risky, Neutral, Safe nodes",
            "component_match",
            True,
        ),
        (
            "fund_manager",
            "separate fund manager approves and executes",
            "Risk Judge ends graph; no order execution node",
            "mismatch_conflated",
            False,
        ),
        ("action_vocabulary", "buy, sell, hold", "signal processor extracts BUY/SELL/HOLD", "component_match", True),
        (
            "react_tool_use",
            "ReAct-style reasoning and acting",
            "tool-calling analyst loops",
            "component_analogue",
            True,
        ),
        (
            "reflection_memory",
            "reflective agent improves decisions",
            "five Chroma memories plus manual reflect_and_remember",
            "component_analogue",
            True,
        ),
        (
            "automatic_reflection",
            "reflection integrated in sequential backtest",
            "caller must inject realized return; example call is commented",
            "missing",
            False,
        ),
        (
            "experiment_model_families",
            "gpt-4o/o1-preview family split",
            "README states o1-preview and gpt-4o experiments",
            "documentation_match_no_frozen_config",
            True,
        ),
        (
            "executable_experiment_model_config",
            "paper experiment configuration",
            "defaults are o4-mini/gpt-4o-mini; example uses gpt-4.1-nano",
            "mismatch",
            False,
        ),
        (
            "node_model_assignment",
            "analysts, researchers, traders use deep models",
            "all those nodes use quick model; only two managers use deep model",
            "mismatch",
            False,
        ),
        (
            "sampling_configuration",
            "exact paper sampling",
            "quick temperature=0.1, auxiliary temperature=1, deep unspecified",
            "incomplete",
            False,
        ),
        (
            "debate_round_control",
            "n rounds determined by facilitator",
            "hardcoded ConditionalLogic default 1; config value not passed",
            "mismatch",
            False,
        ),
        (
            "risk_round_control",
            "n rounds guided by facilitator",
            "hardcoded ConditionalLogic default 1; config value not passed",
            "mismatch",
            False,
        ),
        (
            "recursion_control",
            "experiment recursion configuration",
            "Propagator default 100; config max_recur_limit not passed",
            "mismatch",
            False,
        ),
        (
            "multimodal_categories",
            "prices, news, social, insiders, statements, indicators",
            "broad corresponding tool categories",
            "component_analogue",
            True,
        ),
        (
            "data_providers",
            "Bloomberg, Yahoo, EODHD, FinnHub, Reddit, X/Twitter, SEDI",
            "Yahoo, Google, FinnHub, Reddit, SimFin, OpenAI web search",
            "mismatch",
            False,
        ),
        ("technical_indicator_count", "60 indicators per asset", "13 selectable indicator keys", "mismatch", False),
        (
            "paper_case_tools",
            "11 unique named tools in appendix transcript",
            "6 exact names present; 5 absent",
            "partial_component_analogue",
            True,
        ),
        (
            "paper_case_output",
            "AAPL 2024-11-19 published transcript and BUY",
            "no frozen prompt inputs, trace, or deterministic replay",
            "missing",
            False,
        ),
        (
            "offline_data_snapshot",
            "paper multimodal panel",
            "author-local /Users/yluo/.../FR1-data path; files absent",
            "missing",
            False,
        ),
        (
            "point_in_time_guarantee",
            "only data available by each trade day",
            "mutable online search and no released timestamped snapshot",
            "unverifiable",
            False,
        ),
        (
            "single_ticker_interface",
            "multi-asset simulation",
            "propagate(company_name, trade_date) has no portfolio input",
            "mismatch",
            False,
        ),
        (
            "portfolio_state",
            "portfolio/fund state across days",
            "no holdings, cash, orders, or portfolio state",
            "missing",
            False,
        ),
        ("position_sizing", "timing and size of trades", "final output is categorical action only", "missing", False),
        (
            "execution_engine",
            "approved order executed in simulated exchange",
            "no exchange/broker execution path",
            "missing",
            False,
        ),
        (
            "long_short_semantics",
            "figure captions show long/short positions",
            "BUY/SELL/HOLD extraction without borrow or position semantics",
            "missing",
            False,
        ),
        (
            "transaction_costs",
            "realistic net trading",
            "no commission/slippage/borrow implementation",
            "missing",
            False,
        ),
        (
            "baseline_implementations",
            "B&H, MACD, KDJ+RSI, ZMR, SMA",
            "no baseline strategy source files",
            "missing",
            False,
        ),
        ("metric_implementations", "CR, AR, SR, MDD", "no metric calculator", "missing", False),
        ("paper_backtest_runner", "2024-01-01 through 2024-03-29", "one-day propagate example only", "missing", False),
        (
            "paper_experiment_config",
            "exact assets/models/data/rounds",
            "no paper config or reproduction script",
            "missing",
            False,
        ),
        (
            "trials_and_seeds",
            "published estimator provenance",
            "no trial count, seeds, or aggregation path",
            "missing",
            False,
        ),
        (
            "paper_outputs",
            "actions, fills, NAVs, returns, metrics, plots",
            "paper-era site preserves rendered Table 1, but no dated actions, fills, NAVs, returns, or arrays",
            "missing",
            False,
        ),
        (
            "runtime_state_logging",
            "explainable structured decision trace",
            "writes full_states_log.json when run",
            "component_match",
            True,
        ),
        (
            "source_prompts",
            "role-specific prompts",
            "role prompt functions are shipped",
            "component_match_unverified_experiment_version",
            True,
        ),
        ("upstream_tests", "validated source release", "v0.1.0 ships no tests or CI", "missing", False),
        (
            "dependency_lock",
            "reconstructible environment",
            "unversioned requirements and no lockfile",
            "missing",
            False,
        ),
        (
            "auxiliary_web_prompt",
            "ticker-specific social retrieval",
            "prompt says '{ticker} on TSLA', contaminating non-TSLA requests",
            "source_bug",
            False,
        ),
        (
            "published_numeric_results",
            "77 Table 1 numeric cells plus quantitative figure/text claims",
            "77 Table 1 cells exactly corroborated by author site; no independent native result path",
            "missing",
            False,
        ),
    ]

    assertions = [
        ('"data_dir": "/Users/yluo/Documents/Code/ScAI/FR1-data"' in config, "local data path"),
        ('"deep_think_llm": "o4-mini"' in config, "default deep model"),
        ("create_market_analyst(\n                self.quick_thinking_llm" in setup, "quick analyst allocation"),
        ("create_trader(self.quick_thinking_llm" in setup, "quick trader allocation"),
        ("ConditionalLogic()" in graph and "Propagator()" in graph, "ignored round/recursion config"),
        ("max_debate_rounds=1" in logic and "max_risk_discuss_rounds=1" in logic, "hardcoded rounds"),
        ("Can you search Social Media for {ticker} on TSLA" in interface, "auxiliary prompt bug"),
        (readme.count("o1-preview") >= 1 and readme.count("gpt-4o") >= 1, "README model claim"),
        ("pytest" not in requirements.lower(), "no declared test runner"),
        (not any(path.startswith("tests/") for path in files), "no source tests"),
    ]
    failed = [name for passed, name in assertions if not passed]
    if failed:
        raise RuntimeError(f"Pinned source evidence changed: {failed}")
    if len(checks) != 45:
        raise RuntimeError(f"Expected 45 source dimensions, got {len(checks)}")
    return [
        {
            "dimension": dimension,
            "paper_requirement": paper,
            "v0_1_0_evidence": released,
            "status": status,
            "paper_mechanism_credit": credit,
        }
        for dimension, paper, released, status, credit in checks
    ]


def git_files(source_root: Path) -> list[str]:
    output = run_git(source_root, "ls-tree", "-r", "--name-only", SOURCE_COMMIT)
    assert isinstance(output, str)
    return [line for line in output.splitlines() if line]


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for relative in git_files(source_root):
        payload = git_blob(source_root, relative)
        rows.append(
            {
                "path": relative,
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "python_source": relative.endswith(".py"),
                "paper_result_artifact": False,
            }
        )
    if len(rows) != 56 or sum(bool(row["python_source"]) for row in rows) != 39:
        raise RuntimeError("Pinned v0.1.0 source inventory changed")
    return rows


def paper_source_inventory(paper_source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(paper_source_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(paper_source_root).as_posix()
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "asset_role": (
                    "numeric_result_figure" if relative in FIGURE_SHA256 else "paper_source_or_architecture_asset"
                ),
                "underlying_numeric_array_shipped": False,
            }
        )
    if len(rows) != 26:
        raise RuntimeError(f"Expected 26 arXiv source assets, got {len(rows)}")
    return rows


COMPONENT_DRIVER = r"""
import importlib.util
import json
import sys
import types
from pathlib import Path

root = Path(sys.argv[1])

def package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    sys.modules[name] = module
    return module

def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, root / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

for name in ["tradingagents", "tradingagents.agents", "tradingagents.agents.utils", "tradingagents.graph"]:
    package(name)

states = types.ModuleType("tradingagents.agents.utils.agent_states")
states.AgentState = dict
states.InvestDebateState = lambda value: dict(value)
states.RiskDebateState = lambda value: dict(value)
sys.modules[states.__name__] = states

lc = types.ModuleType("langchain_openai")
lc.ChatOpenAI = type("ChatOpenAI", (), {})
sys.modules[lc.__name__] = lc

class CaptureGraph:
    def __init__(self, state):
        self.nodes = []
        self.edges = []
        self.conditionals = []
    def add_node(self, name, node): self.nodes.append(name)
    def add_edge(self, left, right): self.edges.append([left, right])
    def add_conditional_edges(self, name, router, mapping): self.conditionals.append(name)
    def compile(self): return self

langgraph = package("langgraph")
lg_graph = types.ModuleType("langgraph.graph")
lg_graph.END = "__end__"
lg_graph.START = "__start__"
lg_graph.StateGraph = CaptureGraph
sys.modules[lg_graph.__name__] = lg_graph
lg_prebuilt = types.ModuleType("langgraph.prebuilt")
lg_prebuilt.ToolNode = type("ToolNode", (), {})
sys.modules[lg_prebuilt.__name__] = lg_prebuilt

agent_names = [
    "create_market_analyst", "create_social_media_analyst", "create_news_analyst",
    "create_fundamentals_analyst", "create_msg_delete", "create_bull_researcher",
    "create_bear_researcher", "create_research_manager", "create_trader",
    "create_risky_debator", "create_neutral_debator", "create_safe_debator",
    "create_risk_manager",
]
agents = sys.modules["tradingagents.agents"]
agents.__all__ = agent_names
def factory(name):
    def create(*args, **kwargs): return name
    return create
for name in agent_names:
    setattr(agents, name, factory(name))

agent_utils = types.ModuleType("tradingagents.agents.utils.agent_utils")
agent_utils.Toolkit = type("Toolkit", (), {})
sys.modules[agent_utils.__name__] = agent_utils

conditional = load("tradingagents.graph.conditional_logic", "tradingagents/graph/conditional_logic.py")
setup = load("tradingagents.graph.setup", "tradingagents/graph/setup.py")
propagation = load("tradingagents.graph.propagation", "tradingagents/graph/propagation.py")
signal = load("tradingagents.graph.signal_processing", "tradingagents/graph/signal_processing.py")

logic = conditional.ConditionalLogic(max_debate_rounds=1, max_risk_discuss_rounds=1)
graph = setup.GraphSetup(
    object(), object(), object(),
    {name: f"tools_{name}" for name in ["market", "social", "news", "fundamentals"]},
    object(), object(), object(), object(), object(), logic,
).setup_graph(["market", "social", "news", "fundamentals"])

debate_route = [
    logic.should_continue_debate({"investment_debate_state": {"count": 0, "current_response": ""}}),
    logic.should_continue_debate({"investment_debate_state": {"count": 1, "current_response": "Bull: case"}}),
    logic.should_continue_debate({"investment_debate_state": {"count": 2, "current_response": "Bear: case"}}),
]
risk_route = [
    logic.should_continue_risk_analysis({"risk_debate_state": {"count": 1, "latest_speaker": "Risky Analyst"}}),
    logic.should_continue_risk_analysis({"risk_debate_state": {"count": 2, "latest_speaker": "Safe Analyst"}}),
    logic.should_continue_risk_analysis({"risk_debate_state": {"count": 3, "latest_speaker": "Neutral Analyst"}}),
]

prop = propagation.Propagator()
initial = prop.create_initial_state("AAPL", "2024-01-02")

class Reply:
    content = "BUY"
class FakeLLM:
    def invoke(self, messages):
        assert "SELL, BUY, or HOLD" in messages[0][1]
        return Reply()
decision = signal.SignalProcessor(FakeLLM()).process_signal("FINAL TRANSACTION PROPOSAL: **BUY**")

result = {
    "topology_nodes": graph.nodes,
    "topology_node_count": len(graph.nodes),
    "unconditional_edges": graph.edges,
    "unconditional_edge_count": len(graph.edges),
    "conditional_router_nodes": graph.conditionals,
    "conditional_router_count": len(graph.conditionals),
    "debate_route": debate_route,
    "risk_route": risk_route,
    "initial_state_keys": sorted(initial),
    "recursion_limit": prop.get_graph_args()["config"]["recursion_limit"],
    "signal_extraction": decision,
}
print(json.dumps(result, sort_keys=True))
"""


REAL_COMPONENT_DRIVER = r"""
import importlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path

import httpx
import requests

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
os.environ["OPENAI_API_KEY"] = "sk-audit-placeholder-never-sent"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

network_attempts = []

def block_sync_httpx(self, request, *args, **kwargs):
    network_attempts.append(f"httpx:{request.method}:{request.url}")
    raise RuntimeError("network disabled during dependency-backed component audit")

async def block_async_httpx(self, request, *args, **kwargs):
    network_attempts.append(f"httpx-async:{request.method}:{request.url}")
    raise RuntimeError("network disabled during dependency-backed component audit")

def block_requests(self, request, *args, **kwargs):
    network_attempts.append(f"requests:{request.method}:{request.url}")
    raise RuntimeError("network disabled during dependency-backed component audit")

httpx.Client.send = block_sync_httpx
httpx.AsyncClient.send = block_async_httpx
requests.sessions.Session.send = block_requests

module_names = []
for path in sorted((root / "tradingagents").rglob("*.py")):
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    name = ".".join(parts)
    if name and name not in module_names:
        module_names.append(name)
for name in module_names:
    importlib.import_module(name)

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

config = dict(DEFAULT_CONFIG)
config["project_dir"] = str(root)
graph = TradingAgentsGraph(config=config)
compiled = graph.graph
view = compiled.get_graph()
edges = [
    {
        "source": edge.source,
        "target": edge.target,
        "conditional": bool(edge.conditional),
    }
    for edge in view.edges
]
edges.sort(key=lambda edge: (edge["source"], edge["target"], edge["conditional"]))
initial = graph.propagator.create_initial_state("AAPL", "2024-01-02")

package_names = [
    "akshare", "backtrader", "chainlit", "chromadb", "eodhd", "feedparser",
    "finnhub-python", "langchain-experimental", "langchain-openai", "langgraph",
    "numpy", "openai", "pandas", "parsel", "praw", "pytz", "questionary",
    "redis", "requests", "rich", "stockstats", "tqdm", "tushare", "yfinance",
]
packages = {name: importlib.metadata.version(name) for name in package_names}

result = {
    "python": sys.version,
    "imported_source_modules": len(module_names),
    "imported_module_names": module_names,
    "compiled_graph_type": f"{type(compiled).__module__}.{type(compiled).__name__}",
    "graph_nodes": sorted(view.nodes),
    "graph_node_count_including_start_end": len(view.nodes),
    "graph_edges": edges,
    "graph_edge_count": len(edges),
    "conditional_edge_count": sum(edge["conditional"] for edge in edges),
    "tool_names_by_group": {
        group: sorted(node.tools_by_name) for group, node in graph.tool_nodes.items()
    },
    "tool_count": sum(len(node.tools_by_name) for node in graph.tool_nodes.values()),
    "initial_state_keys": sorted(initial),
    "recursion_limit": graph.propagator.get_graph_args()["config"]["recursion_limit"],
    "resolved_packages": packages,
    "network_attempts": network_attempts,
}
print(json.dumps(result, sort_keys=True))
"""


def run_native_component_checks(source_root: Path, source_python: Path) -> dict[str, Any]:
    if not source_python.is_file():
        raise FileNotFoundError(source_python)
    clean_env = os.environ.copy()
    clean_env.pop("PYTHONPATH", None)
    clean_env.update(
        {
            "OPENAI_API_KEY": "sk-audit-placeholder-never-sent",
            "ANONYMIZED_TELEMETRY": "False",
        }
    )
    pip_check = subprocess.run(
        [str(source_python), "-m", "pip", "check"],
        check=True,
        capture_output=True,
        text=True,
        env=clean_env,
    )
    freeze = subprocess.run(
        [str(source_python), "-m", "pip", "freeze", "--all"],
        check=True,
        capture_output=True,
        text=True,
        env=clean_env,
    ).stdout
    freeze_sha256 = sha256_bytes(freeze.encode())
    if freeze_sha256 != RECONSTRUCTED_ENV_FREEZE_SHA256:
        raise RuntimeError(
            "TradingAgents reconstructed environment changed: "
            f"{freeze_sha256} != {RECONSTRUCTED_ENV_FREEZE_SHA256}"
        )

    archive = run_git(source_root, "archive", "--format=tar", SOURCE_COMMIT, binary=True)
    assert isinstance(archive, bytes)
    with tempfile.TemporaryDirectory(prefix="tradingagents-v010-") as temporary:
        root = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
            bundle.extractall(root, filter="data")
        declared_requirements = [
            line.strip()
            for line in (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if len(declared_requirements) != 24:
            raise RuntimeError(
                f"Pinned source requirement count changed: {len(declared_requirements)}"
            )
        compile_run = subprocess.run(
            [str(source_python), "-m", "compileall", "-q", str(root)],
            capture_output=True,
            text=True,
            env=clean_env,
        )
        if compile_run.returncode:
            raise RuntimeError(f"Pinned source compile failed: {compile_run.stderr}")
        driver = root / "_audit_component_driver.py"
        driver.write_text(COMPONENT_DRIVER, encoding="utf-8")
        outputs = []
        for _ in range(2):
            run = subprocess.run(
                [str(source_python), str(driver), str(root)],
                check=True,
                capture_output=True,
                text=True,
                env=clean_env,
            )
            outputs.append(json.loads(run.stdout))
        if outputs[0] != outputs[1]:
            raise RuntimeError("Dependency-isolated source topology check is nondeterministic")
        real_driver = root / "_audit_real_dependency_driver.py"
        real_driver.write_text(REAL_COMPONENT_DRIVER, encoding="utf-8")
        real_outputs = []
        for _ in range(2):
            run = subprocess.run(
                [str(source_python), str(real_driver), str(root)],
                capture_output=True,
                text=True,
                cwd=root,
                env=clean_env,
            )
            if run.returncode:
                raise RuntimeError(
                    "Dependency-backed source graph check failed:\n"
                    f"stdout:\n{run.stdout}\nstderr:\n{run.stderr}"
                )
            real_outputs.append(json.loads(run.stdout))
        if real_outputs[0] != real_outputs[1]:
            raise RuntimeError("Dependency-backed source graph check is nondeterministic")
    observed = outputs[0]
    expected = {
        "topology_node_count": 20,
        "unconditional_edge_count": 12,
        "conditional_router_count": 9,
        "debate_route": ["Bull Researcher", "Bear Researcher", "Research Manager"],
        "risk_route": ["Safe Analyst", "Neutral Analyst", "Risk Judge"],
        "recursion_limit": 100,
        "signal_extraction": "BUY",
    }
    for key, value in expected.items():
        if observed[key] != value:
            raise RuntimeError(f"Pinned source component changed for {key}: {observed[key]!r}")
    real_observed = real_outputs[0]
    real_expected = {
        "imported_source_modules": 33,
        "compiled_graph_type": "langgraph.graph.state.CompiledStateGraph",
        "graph_node_count_including_start_end": 22,
        "graph_edge_count": 30,
        "conditional_edge_count": 18,
        "tool_count": 16,
        "recursion_limit": 100,
        "network_attempts": [],
    }
    for key, value in real_expected.items():
        if real_observed[key] != value:
            raise RuntimeError(
                f"Pinned dependency-backed source component changed for {key}: "
                f"{real_observed[key]!r}"
            )
    normalized = json.dumps(observed, sort_keys=True, separators=(",", ":")).encode()
    real_normalized = json.dumps(
        real_observed, sort_keys=True, separators=(",", ":")
    ).encode()
    return {
        "source_commit": SOURCE_COMMIT,
        "source_python": str(source_python),
        "tracked_python_files_compiled": 39,
        "compile_status": "passed_in_reconstructed_declared_dependency_environment",
        "upstream_tests_shipped": 0,
        "dependency_environment_reproduced": True,
        "release_declared_requirements": len(declared_requirements),
        "dependency_environment_scope": "all 24 release-declared unpinned requirements resolved in clean Python 3.10; exact 2025 package versions remain unrecoverable",
        "exact_historical_dependency_versions_recovered": False,
        "pip_check": pip_check.stdout.strip(),
        "dependency_freeze_sha256": freeze_sha256,
        "dependency_freeze_lines": len(freeze.splitlines()),
        "_dependency_freeze_text": freeze,
        "network_boundary": "httpx sync/async and requests sends blocked; constructor completed with zero attempts",
        "dependency_isolation": "none for imports, OpenAI clients, Chroma memories, LangGraph, ToolNode, source factories, or graph compilation",
        "semantic_component": observed,
        "semantic_component_sha256": sha256_bytes(normalized),
        "real_dependency_component": real_observed,
        "real_dependency_component_sha256": sha256_bytes(real_normalized),
        "deterministic_across_two_runs": True,
        "paper_result_reproduction": False,
    }


def verify_pins(
    source_root: Path,
    paper_pdf: Path,
    paper_source_archive: Path,
    paper_source_root: Path,
) -> None:
    if sha256(paper_pdf) != PAPER_SHA256:
        raise RuntimeError(f"Paper PDF hash changed: {sha256(paper_pdf)}")
    if sha256(paper_source_archive) != PAPER_SOURCE_SHA256:
        raise RuntimeError(f"Paper source archive hash changed: {sha256(paper_source_archive)}")
    tag_commit = str(run_git(source_root, "rev-parse", f"{SOURCE_TAG}^{{}}")).strip()
    if tag_commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected {SOURCE_TAG} at {SOURCE_COMMIT}, found {tag_commit}")
    parent = str(run_git(source_root, "rev-parse", f"{SOURCE_COMMIT}^")).strip()
    if parent != PRE_RELEASE_COMMIT:
        raise RuntimeError(f"Expected pre-release parent {PRE_RELEASE_COMMIT}, found {parent}")
    prior_files = git_files_at(source_root, PRE_RELEASE_COMMIT)
    if prior_files != ["README.md", "index.html", "index_complete.html"]:
        raise RuntimeError(f"Pre-release tree changed: {prior_files}")
    pre_release_table_hash = sha256_bytes(git_blob_at(source_root, PRE_RELEASE_COMMIT, PRE_RELEASE_TABLE_PATH))
    if pre_release_table_hash != PRE_RELEASE_TABLE_SHA256:
        raise RuntimeError(f"Pre-release project-site hash changed: {pre_release_table_hash}")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        observed = sha256_bytes(git_blob(source_root, relative))
        if observed != expected:
            raise RuntimeError(f"Pinned source hash changed for {relative}: {observed}")
    for relative, expected in {**PINNED_PAPER_SOURCE_SHA256, **FIGURE_SHA256}.items():
        observed = sha256(paper_source_root / relative)
        if observed != expected:
            raise RuntimeError(f"Pinned paper-source hash changed for {relative}: {observed}")


def git_files_at(source_root: Path, commit: str) -> list[str]:
    output = run_git(source_root, "ls-tree", "-r", "--name-only", commit)
    assert isinstance(output, str)
    return sorted(line for line in output.splitlines() if line)


def public_source_history(
    source_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    discovery_root = source_root / "release-discovery"
    for name, expected in PUBLIC_DISCOVERY_SHA256.items():
        if sha256(discovery_root / name) != expected:
            raise RuntimeError(f"TradingAgents public discovery drift: {name}")
    branches = json.loads((discovery_root / "branches.json").read_text(encoding="utf-8"))
    tags = json.loads((discovery_root / "tags.json").read_text(encoding="utf-8"))
    releases = json.loads((discovery_root / "releases.json").read_text(encoding="utf-8"))
    branch_pairs = [(row["name"], row["commit"]["sha"]) for row in branches]
    tag_pairs = [(row["name"], row["commit"]["sha"]) for row in tags]
    release_rows = [
        (row["tag_name"], row["target_commitish"], row["published_at"], len(row["assets"]))
        for row in releases
    ]
    if branch_pairs != [
        ("main", CURRENT_SOURCE_COMMIT),
        ("v0.2.0", "b4b133eb2d4e1eae16b0018826259c628f0fd0e6"),
    ]:
        raise RuntimeError("TradingAgents public branch discovery changed")
    if tag_pairs != [
        ("v0.3.1", "01477f9afb7a47b849ed4c9259d3a9a4738d9fda"),
        ("v0.3.0", "85946c2f60768ab2dae23a5a36cd927662feef94"),
        ("v0.2.5", "a5cb7cbd61d217fb0bc43f017392a861257afe6a"),
        ("v0.2.4", "7c37249f808f9c169ad2198dc384166e7ca7adf9"),
        ("v0.2.3", "4641c03340c70e0e75e74234c998325164c72b36"),
        ("v0.2.2", "589b351f2ab55a8a37d846848479cebc810a5a36"),
        ("v0.2.1", "551fd7f074fab8e1080d4ca30efaa4b6b4cd7517"),
        ("v0.2.0", "e9470b69c457acbecd62d0707a2f7c045d7f53c9"),
        ("v0.1.1", "47176ba8a25cbbf8feb24417765eb189c61885da"),
        ("v0.1.0", SOURCE_COMMIT),
    ]:
        raise RuntimeError("TradingAgents public tag discovery changed")
    if release_rows != [
        ("v0.3.1", "main", "2026-07-05T14:32:25Z", 0),
        ("v0.3.0", "main", "2026-06-22T02:05:10Z", 0),
        ("v0.2.5", "main", "2026-05-11T09:27:40Z", 0),
        ("v0.2.4", "main", "2026-04-25T22:33:19Z", 0),
        ("v0.2.3", "main", "2026-03-29T19:50:48Z", 0),
        ("v0.2.2", "main", "2026-03-22T23:51:27Z", 0),
        ("v0.2.1", "main", "2026-03-15T23:35:26Z", 0),
        ("v0.2.0", "main", "2026-02-04T07:35:20Z", 0),
    ]:
        raise RuntimeError("TradingAgents public release discovery changed")
    if str(run_git(source_root, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise RuntimeError("TradingAgents source checkout is shallow")

    commits_raw = str(run_git(source_root, "rev-list", "--reverse", "--all"))
    commits = commits_raw.splitlines()
    if len(commits) != PUBLIC_HISTORY_COMMIT_COUNT:
        raise RuntimeError("TradingAgents public commit census changed")
    if hashlib.sha256(commits_raw.encode("utf-8")).hexdigest() != PUBLIC_HISTORY_COMMIT_SHA256:
        raise RuntimeError("TradingAgents public commit sequence changed")
    path_lines = str(run_git(source_root, "log", "--all", "--pretty=format:", "--name-only")).splitlines()
    historical_paths = sorted({line for line in path_lines if line})
    path_payload = ("\n".join(historical_paths) + "\n").encode("utf-8")
    if len(historical_paths) != PUBLIC_HISTORY_PATH_COUNT:
        raise RuntimeError("TradingAgents public historical path census changed")
    if hashlib.sha256(path_payload).hexdigest() != PUBLIC_HISTORY_PATH_SHA256:
        raise RuntimeError("TradingAgents public historical path inventory changed")

    object_lines = str(run_git(source_root, "rev-list", "--objects", "--all")).splitlines()
    object_ids = [line.split(" ", 1)[0] for line in object_lines]
    object_proc = subprocess.run(
        ["git", "-C", str(source_root), "cat-file", "--batch-check=%(objecttype)"],
        input="\n".join(object_ids) + "\n",
        check=True,
        capture_output=True,
        text=True,
    )
    object_types = object_proc.stdout.splitlines()
    object_counts = dict(Counter(object_types))
    if object_counts != PUBLIC_HISTORY_OBJECT_COUNTS:
        raise RuntimeError("TradingAgents reachable-object census changed")
    fsck = subprocess.run(
        ["git", "-C", str(source_root), "fsck", "--full", "--no-reflogs", "--unreachable"],
        check=True,
        capture_output=True,
        text=True,
    )
    if fsck.stdout.strip():
        raise RuntimeError("TradingAgents has unreachable objects requiring review")

    blob_sha256: dict[str, str] = {}
    exact_table_blobs: set[str] = set()
    for object_id, object_type in zip(object_ids, object_types):
        if object_type != "blob":
            continue
        raw = run_git(source_root, "cat-file", "-p", object_id, binary=True)
        assert isinstance(raw, bytes)
        blob_sha256[object_id] = sha256_bytes(raw)
        if len(exact_html_table_values(raw)) == 77:
            exact_table_blobs.add(object_id)
    if len(exact_table_blobs) != 15:
        raise RuntimeError("TradingAgents exact author-table blob census changed")
    if blob_sha256.get(FIRST_EXACT_TABLE_BLOB) != FIRST_EXACT_TABLE_SHA256:
        raise RuntimeError("TradingAgents first author result table changed")

    commit_rows: list[dict[str, Any]] = []
    path_blobs: dict[str, set[str]] = {path: set() for path in historical_paths}
    path_first: dict[str, tuple[str, str]] = {}
    path_last: dict[str, tuple[str, str]] = {}
    exact_table_paths_all: set[str] = set()
    for commit in commits:
        metadata = str(run_git(source_root, "show", "-s", "--format=%H%x1f%cI%x1f%s", commit)).rstrip("\n")
        commit_id, committed_at, subject = metadata.split("\x1f", 2)
        paths = []
        native_result_paths = []
        exact_table_paths = []
        python_files = 0
        for line in str(run_git(source_root, "ls-tree", "-r", commit)).splitlines():
            object_meta, path = line.split("\t", 1)
            _mode, object_type, object_id = object_meta.split()
            if object_type != "blob":
                continue
            paths.append(path)
            path_blobs[path].add(object_id)
            path_first.setdefault(path, (commit_id, committed_at))
            path_last[path] = (commit_id, committed_at)
            suffix = Path(path).suffix.lower()
            if suffix == ".py":
                python_files += 1
            if suffix in NATIVE_RESULT_EXTENSIONS:
                native_result_paths.append(path)
            if object_id in exact_table_blobs:
                exact_table_paths.append(path)
                exact_table_paths_all.add(path)
        commit_rows.append(
            {
                "commit": commit_id,
                "committed_at": committed_at,
                "subject": subject,
                "tracked_files": len(paths),
                "python_files": python_files,
                "executable_source_present": python_files > 0,
                "exact_author_table_paths": ";".join(exact_table_paths),
                "exact_author_table_cells": 77 if exact_table_paths else 0,
                "native_structured_result_paths": len(native_result_paths),
                "native_structured_result_path_names": ";".join(native_result_paths),
                "independently_regenerated_paper_results": 0,
                "paper_result_credit": False,
            }
        )

    path_rows: list[dict[str, Any]] = []
    for path in historical_paths:
        blob_ids = path_blobs[path]
        suffix = Path(path).suffix.lower()
        exact_table = bool(blob_ids & exact_table_blobs)
        if exact_table:
            classification = "author_rendered_exact_table_correspondence"
        elif suffix == ".png":
            classification = "documentation_screenshot_or_architecture_media"
        else:
            classification = "source_test_configuration_or_documentation"
        path_rows.append(
            {
                "path": path,
                "extension": suffix,
                "historical_blob_versions": len(blob_ids),
                "first_reachable_commit": path_first[path][0],
                "first_reachable_committed_at": path_first[path][1],
                "last_reachable_commit": path_last[path][0],
                "last_reachable_committed_at": path_last[path][1],
                "native_structured_result_path": suffix in NATIVE_RESULT_EXTENSIONS,
                "contains_exact_author_table_in_history": exact_table,
                "classification": classification,
                "paper_result_credit": False,
            }
        )
    native_paths = [row for row in path_rows if row["native_structured_result_path"]]
    if native_paths:
        raise RuntimeError("TradingAgents public history gained a native result path")
    if exact_table_paths_all != {"index.html", "index_complete.html"}:
        raise RuntimeError("TradingAgents author-table path lineage changed")

    extension_counts = Counter(row["extension"] or "[none]" for row in path_rows)
    summary = {
        "discovered_public_branches": [{"name": name, "head": commit} for name, commit in branch_pairs],
        "discovered_public_tags": [{"name": name, "target_commit": commit} for name, commit in tag_pairs],
        "discovered_public_releases": [
            {"tag": tag, "target": target, "published_at": published, "assets": assets}
            for tag, target, published, assets in release_rows
        ],
        "reachable_commits": len(commits),
        "unique_historical_paths": len(historical_paths),
        "historical_path_extension_counts": dict(sorted(extension_counts.items())),
        "reachable_object_counts": object_counts,
        "unreachable_objects": 0,
        "native_structured_result_paths": 0,
        "raw_numeric_curve_or_event_array_paths": 0,
        "exact_author_table_blob_versions": len(exact_table_blobs),
        "exact_author_table_paths": sorted(exact_table_paths_all),
        "first_exact_author_table_commit": FIRST_EXACT_TABLE_COMMIT,
        "first_exact_author_table_commit_date": FIRST_EXACT_TABLE_COMMIT_DATE,
        "first_exact_author_table_sha256": FIRST_EXACT_TABLE_SHA256,
        "current_source_commit": CURRENT_SOURCE_COMMIT,
        "current_tracked_files": len(git_files_at(source_root, CURRENT_SOURCE_COMMIT)),
        "independently_regenerated_paper_results": 0,
        "paper_result_credit": False,
    }
    return commit_rows, path_rows, summary


def build_audit(
    source_root: Path,
    paper_pdf: Path,
    paper_source_archive: Path,
    paper_source_root: Path,
    paper_versions_root: Path,
    source_python: Path,
    yahoo_diagnostic_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    verify_pins(source_root, paper_pdf, paper_source_archive, paper_source_root)
    paper_versions = paper_version_inventory(paper_versions_root, source_root)
    figure_series = paper_figure_series()
    history_commits, history_paths, history_summary = public_source_history(source_root)
    author_outputs = author_output_correspondence(source_root)
    table = paper_table_rows(author_output_verified=True)
    yahoo_diagnostic = current_yahoo_buy_hold_diagnostic(yahoo_diagnostic_root)
    annualization = annualization_identity()
    improvement = improvement_identity()
    claims = published_non_table_claims()
    inconsistencies = paper_internal_inconsistencies()
    tools = case_tool_conformance(source_root)
    mechanisms = source_conformance(source_root)
    gaps = specification_gaps()
    inventory = source_inventory(source_root)
    paper_assets = paper_source_inventory(paper_source_root)
    current_source = current_source_conformance(source_root)
    component = run_native_component_checks(source_root, source_python)
    dependency_freeze = component.pop("_dependency_freeze_text")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "table_1_conformance.csv", table)
    write_csv(output_dir / "current_yahoo_buy_hold_diagnostic.csv", yahoo_diagnostic)
    write_csv(output_dir / "author_output_correspondence.csv", author_outputs)
    write_csv(output_dir / "annualized_return_identity_audit.csv", annualization)
    write_csv(output_dir / "improvement_identity_audit.csv", improvement)
    write_csv(output_dir / "published_non_table_claims.csv", claims)
    write_csv(output_dir / "paper_internal_inconsistencies.csv", inconsistencies)
    write_csv(output_dir / "appendix_case_tool_conformance.csv", tools)
    write_csv(output_dir / "source_mechanism_conformance.csv", mechanisms)
    write_csv(output_dir / "paper_specification_gaps.csv", gaps)
    write_csv(output_dir / "released_source_inventory.csv", inventory)
    write_csv(output_dir / "paper_source_asset_inventory.csv", paper_assets)
    write_csv(output_dir / "official_paper_version_inventory.csv", paper_versions)
    write_csv(output_dir / "paper_figure_series_inventory.csv", figure_series)
    write_csv(output_dir / "public_source_history_commit_inventory.csv", history_commits)
    write_csv(output_dir / "public_source_history_path_inventory.csv", history_paths)
    write_csv(output_dir / "current_source_conformance.csv", current_source)
    (output_dir / "public_source_history.json").write_text(
        json.dumps(history_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "native_component.json").write_text(json.dumps(component, indent=2) + "\n", encoding="utf-8")
    (output_dir / "reconstructed_environment_freeze.txt").write_text(
        dependency_freeze, encoding="utf-8"
    )

    mechanism_counts = Counter(row["status"] for row in mechanisms)
    credit = sum(bool(row["paper_mechanism_credit"]) for row in mechanisms)
    manifest: dict[str, Any] = {
        "audit": "TradingAgents all official paper versions versus full public source history",
        "overall_status": "not_reproduced_nearest_release_architecture_components_only",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": PAPER_VERSION,
        "paper_date": PAPER_DATE,
        "paper_sha256": PAPER_SHA256,
        "paper_source_sha256": PAPER_SOURCE_SHA256,
        "official_paper_versions_audited": len(paper_versions),
        "paper_versions_with_identical_table_values": 7,
        "paper_versions_with_executable_source_at_submission": 0,
        "paper_versions_with_exact_author_site_table_at_submission": 7,
        "paper_v1_through_v6_comparison_plot_final_label": "StockGPTStrategy",
        "paper_v7_comparison_plot_final_label": "TradingAgents",
        "source_url": SOURCE_URL,
        "source_tag": SOURCE_TAG,
        "source_commit": SOURCE_COMMIT,
        "source_commit_date": SOURCE_COMMIT_DATE,
        "pre_release_commit": PRE_RELEASE_COMMIT,
        "pre_release_tree_files": 3,
        "first_public_repository_commit": FIRST_PUBLIC_COMMIT,
        "first_exact_author_table_commit": FIRST_EXACT_TABLE_COMMIT,
        "first_exact_author_table_commit_date": FIRST_EXACT_TABLE_COMMIT_DATE,
        "first_exact_author_table_sha256": FIRST_EXACT_TABLE_SHA256,
        "paper_era_source_revision_available": False,
        "paper_era_author_project_site_available": True,
        "paper_era_author_project_site_commit": PRE_RELEASE_COMMIT,
        "paper_era_author_project_site_commit_date": PRE_RELEASE_COMMIT_DATE,
        "paper_era_author_project_site_table_sha256": PRE_RELEASE_TABLE_SHA256,
        "nearest_source_release_after_paper_hours": 52.3894,
        "paper_numeric_tables_audited": [1],
        "paper_numeric_table_cells_total": len(table),
        "paper_direct_result_cells_total": 68,
        "paper_derived_improvement_cells_total": 9,
        "native_paper_table_result_cells_reproduced": 0,
        "author_output_table_cells_corroborated": 77,
        "author_output_table_cells_independently_regenerated": 0,
        "current_public_yahoo_buy_hold_cells_checked": len(yahoo_diagnostic),
        "current_public_yahoo_buy_hold_cells_matching": sum(
            row["display_precision_match"] for row in yahoo_diagnostic
        ),
        "current_public_yahoo_observed_on": YAHOO_DIAGNOSTIC_OBSERVED_ON,
        "current_public_yahoo_has_paper_time_input_lineage": False,
        "current_public_yahoo_paper_price_provider_mapping_recovered": False,
        "published_non_table_quantitative_claims_total": len(claims),
        "published_non_table_result_claims_total": 12,
        "native_non_table_result_claims_reproduced": 0,
        "paper_result_figure_series_total": len(figure_series),
        "native_exact_result_figure_series_reproduced": 0,
        "paper_presented_empirical_units_total": len(table) + 12 + len(figure_series),
        "native_presented_empirical_units_reproduced": 0,
        "annualized_return_pairs_checked": len(annualization),
        "annualized_return_pairs_matching_published_equation": 0,
        "improvement_cells_checked": len(improvement),
        "improvement_cells_exact_absolute_differences": 7,
        "improvement_cells_inconsistent_with_displayed_values": 1,
        "paper_internal_inconsistencies_total": len(inconsistencies),
        "paper_specification_gaps_total": len(gaps),
        "appendix_unique_tools_total": len(tools),
        "appendix_tools_exactly_present_in_nearest_release": 6,
        "appendix_case_output_reproduced": False,
        "source_mechanism_dimensions_total": len(mechanisms),
        "source_mechanism_status_counts": dict(mechanism_counts),
        "source_mechanism_matches_or_analogues": credit,
        "source_mechanism_fully_faithful": False,
        "tracked_source_files_total": len(inventory),
        "tracked_source_python_files_total": 39,
        "paper_source_assets_total": len(paper_assets),
        "numeric_result_figures_total": 6,
        "numeric_result_figure_arrays_shipped": 0,
        "current_public_source_commit": CURRENT_SOURCE_COMMIT,
        "current_public_source_tracked_files": history_summary["current_tracked_files"],
        "current_public_source_python_files": 137,
        "current_public_source_test_files": 54,
        "current_public_source_conformance_dimensions": len(current_source),
        "public_source_reachable_commits_total": history_summary["reachable_commits"],
        "public_source_unique_historical_paths_total": history_summary["unique_historical_paths"],
        "public_source_reachable_blobs_total": history_summary["reachable_object_counts"]["blob"],
        "public_source_reachable_trees_total": history_summary["reachable_object_counts"]["tree"],
        "public_source_reachable_commit_objects_total": history_summary["reachable_object_counts"]["commit"],
        "public_source_reachable_tag_objects_total": history_summary["reachable_object_counts"]["tag"],
        "public_source_unreachable_objects_total": history_summary["unreachable_objects"],
        "public_source_native_structured_result_paths": history_summary["native_structured_result_paths"],
        "public_source_raw_numeric_curve_or_event_array_paths": history_summary[
            "raw_numeric_curve_or_event_array_paths"
        ],
        "public_source_exact_author_table_blob_versions": history_summary[
            "exact_author_table_blob_versions"
        ],
        "public_source_discovered_branches_total": len(history_summary["discovered_public_branches"]),
        "public_source_discovered_tags_total": len(history_summary["discovered_public_tags"]),
        "public_source_discovered_releases_total": len(history_summary["discovered_public_releases"]),
        "native_source_python_files_compiled": component["tracked_python_files_compiled"],
        "native_source_upstream_tests_shipped": 0,
        "native_source_dependency_environment_reproduced": component[
            "dependency_environment_reproduced"
        ],
        "native_source_exact_historical_dependency_versions_recovered": component[
            "exact_historical_dependency_versions_recovered"
        ],
        "native_source_modules_imported_with_real_dependencies": component[
            "real_dependency_component"
        ]["imported_source_modules"],
        "native_source_real_graph_nodes_including_start_end": component[
            "real_dependency_component"
        ]["graph_node_count_including_start_end"],
        "native_source_real_graph_edges": component[
            "real_dependency_component"
        ]["graph_edge_count"],
        "native_source_real_tool_count": component[
            "real_dependency_component"
        ]["tool_count"],
        "native_topology_component_deterministic": True,
        "native_topology_component_paper_result_reproduction": False,
        "native_paper_data_snapshot_shipped": False,
        "native_paper_backtest_runner_shipped": False,
        "native_paper_baseline_implementations_shipped": False,
        "native_paper_metric_implementation_shipped": False,
        "native_paper_actions_orders_fills_shipped": False,
        "native_paper_nav_returns_holdings_shipped": False,
        "paper_era_author_rendered_table_shipped": True,
        "paper_era_author_raw_result_arrays_shipped": False,
        "native_paper_llm_trajectories_shipped": False,
        "native_paper_cost_or_seed_ledger_shipped": False,
        "audit_runtime_called_llm_or_market_data_api": False,
        "interpretation": (
            "All seven official paper versions retain the same 77 Table 1 values and 42 plotted "
            "result series. The exact rendered table existed on the official project site before "
            "arXiv v1, but every paper-version cutoff contains only two or three site files and no "
            "executable implementation. The nearest official code is a substantial multi-agent "
            "architecture release, but it arrived about 52 hours after v7. It implements several "
            "paper roles, structured state, debates, memories, "
            "tool loops, prompts, and runtime logging. A clean Python 3.10 environment resolves all "
            "24 release-declared requirements, imports all 33 source modules, and constructs the "
            "real 22-node, 30-edge graph with 16 tools without an external request; the unpinned "
            "requirements cannot recover exact 2025 package versions. Its pre-release official project site also "
            "contains all 77 Table 1 values in the same order as the paper. This corroborates the "
            "published author output but is not an independent regeneration. A hash-pinned current "
            "Yahoo adjusted-close diagnostic checks all 12 Buy-and-Hold cells under the paper's literal "
            "window and finds zero display-precision matches. Because the paper lists several providers "
            "without mapping prices and no paper-time response survives, this is adverse current-public "
            "correspondence with zero paper-result credit. It does not ship the paper data, experiment "
            "configuration, portfolio/execution engine, baseline or metric code, backtest runner, "
            "actions, fills, NAVs, returns, plots, seeds, or costs. Its analysts are sequential, its "
            "model assignment conflicts with the paper, only 6/11 appendix tool names remain, and "
            "several advertised config values are not wired into the graph. The full discovered "
            "public history has 257 commits, 189 historical paths, 2,191 reachable objects, no "
            "unreachable objects, and no native result-data or curve/event-array path. Later source "
            "adds a separate Portfolio Manager and tests, and the wider history includes a lockfile, "
            "but current main still has no lock and the project still has no paper "
            "backtester, baselines, metrics, frozen data, or result outputs. Therefore 77/77 Table 1 "
            "cells have exact author-output correspondence, while 0/77 Table 1 numeric cells, 0/42 "
            "plotted series, and 0/12 additional quantitative result claims are independently "
            "reproduced. The paper "
            "also contains internal numeric inconsistencies: all 17 CR/AR pairs fail its literal "
            "annualization equation, GOOGL Sharpe improvement is arithmetically wrong, and the prose "
            "MDD bound contradicts AMZN."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
        "paper_source_file_sha256": PINNED_PAPER_SOURCE_SHA256,
        "paper_result_figure_sha256": FIGURE_SHA256,
    }

    report = f"""# TradingAgents paper-level conformance audit

Overall verdict: **not reproduced**. All seven official revisions and every
reachable public source object were audited. The nearest release implements a
meaningful architecture subset, but not the experiment that produced the paper.

## Primary-source pins

- Official paper record: all seven revisions of arXiv:2412.20138. The current
  revision is {PAPER_URL} ({PAPER_VERSION}, {PAPER_DATE}; PDF SHA-256
  `{PAPER_SHA256}`; source archive SHA-256 `{PAPER_SOURCE_SHA256}`).
- The seven pinned PDFs contain 27, 27, 27, 27, 27, 27, and 38 pages. Their
  source archives contain 25--26 files. All preserve the same 77 Table 1 values
  and 42 plotted result series. The comparison plots call the final series
  `StockGPTStrategy` in v1--v6 and `TradingAgents` in v7; the raw comparison
  PDFs were re-encoded for v7, while all three detail PDFs are byte-identical.
- Official source: {SOURCE_URL}, tag `{SOURCE_TAG}`, commit `{SOURCE_COMMIT}`
  ({SOURCE_COMMIT_DATE}). It is the first public code release, about 52.4 hours
  after v7. Its parent `{PRE_RELEASE_COMMIT}` contains only the README and two
  project-site HTML files. The pinned `{PRE_RELEASE_TABLE_PATH}` (SHA-256
  `{PRE_RELEASE_TABLE_SHA256}`) contains all 77 Table 1 values in paper order,
  but no paper-date implementation is present in history.

## What genuinely passes

- All 39 tagged Python files compile in a clean Python 3.10 environment resolving
  all 24 release-declared requirements. All 33 source modules import, and the
  actual OpenAI clients, Chroma memories, LangGraph, ToolNodes, source factories,
  and graph compiler deterministically construct a 22-node, 30-edge graph with
  16 tools. HTTP sends are blocked and the constructor makes zero attempts. The
  release did not pin package versions, so this reconstructs a compatible
  declared-dependency environment, not the exact historical environment, LLM
  calls, data, backtest, or paper results. A narrower route/state/signal check
  also remains deterministic with inert audit inputs.
- `reconstructed_environment_freeze.txt` records all 247 resolved package lines;
  its SHA-256 is checked before every dependency-backed audit execution.
- The release contains four analyst roles, structured shared reports, bull/bear
  debate, a research manager, trader, three risk perspectives, role prompts,
  memories/reflection hooks, categorical BUY/SELL/HOLD extraction, and runtime
  state logging. These are substantive mechanism matches or analogues.
- Six of the eleven unique tool names in the published AAPL appendix transcript
  exist exactly in v0.1.0. The arXiv source also ships six vector performance
  figures, whose hashes and visible annotations are inventoried.
- All 77 Table 1 values are present in the official pre-release project-site HTML
  in exactly the paper's order. This corroborates an author-rendered output; it
  does not independently regenerate any cell or expose the underlying arrays.
- The exact 77-value table first appears at `{FIRST_EXACT_TABLE_COMMIT}`
  ({FIRST_EXACT_TABLE_COMMIT_DATE}), before v1. It persists through 15 distinct
  HTML blobs on `index.html` and `index_complete.html`.

## Why the paper is not replicated

- Table 1 has **77 numeric cells**: 68 direct method results and nine derived
  improvements. **77/77** have exact author-output correspondence, but **0/77**
  independently regenerate through the released pipeline. The six result PDFs
  contain **42 plotted series/event groups**; **0/42** regenerate from native
  numeric arrays. Twelve additional quantitative result claims in prose/figures
  also have zero reproductions. Thus all **131 presentation-level empirical
  audit units** have zero independent native reproductions.
- A hash-pinned current Yahoo adjusted-close response provides 61 sessions from
  2024-01-02 through 2024-03-28 for each table asset. Under the paper's literal
  January 1--March 29 window, all **12/12 Buy-and-Hold cells mismatch** at display
  precision. Current cumulative returns are -7.51% AAPL, +9.24% GOOGL, and
  +20.31% AMZN, versus -5.23%, +7.78%, and +17.10% in the paper. The paper does
  not identify which listed provider supplied prices, and this 2026 observation
  has no paper-time lineage, so it is adverse diagnostic evidence only.
- No frozen multimodal dataset, 60-indicator definition, experiment config,
  backtest runner, baseline implementation, metric code, portfolio state,
  position sizing, execution engine, commission/slippage rules, action history,
  order/fill log, NAV/return path, plot array, trial seed, or API-cost ledger is
  released. Offline mode points to an author-local directory that is not shipped.
- The source executes analysts sequentially although the paper says concurrently;
  assigns the quick model to analysts/researchers/trader although the paper says
  deep; conflates the fund manager with the terminal risk judge; outputs only a
  categorical action; and does not wire configured debate/risk/recursion limits
  into the corresponding routing objects.
- Five of eleven appendix tool names are absent from the nearest release. The
  exact AAPL 2024-11-19 transcript and BUY cannot be replayed without its frozen
  inputs, model snapshots, prompts/tool schemas, and trace.
- Full public-history exhaustion found 257 commits, 189 historical paths, 1,009
  blobs, 918 trees, 257 commit objects, seven annotated-tag objects, and no
  unreachable objects. The discovered two branches, ten tags, and eight GitHub
  releases contain no CSV/Parquet/NumPy/notebook/checkpoint/log result path and
  no numeric curve/event arrays. Later source adds tests and a separate Portfolio
  Manager, and another public ref contains a lockfile, but current main has no
  dependency lock and the project still has no paper backtester, baselines,
  metrics, frozen paper data, portfolio execution ledger, or paper outputs.

## Paper-internal barriers

- All 17 displayed CR/AR pairs fail the paper's literal annualized-return formula
  for the stated 89-day period; for example, AAPL TradingAgents CR=26.62% implies
  about 163.43% annualized, not the reported 30.5%.
- GOOGL TradingAgents SR 6.39 minus the best displayed baseline 2.31 is 4.08,
  not the reported 4.26. The improvement row is otherwise mostly absolute metric
  differences despite its percent label.
- GOOGL ZMR has negative CR but positive AR, impossible under the two published
  return formulas for positive N. The prose says MDD never exceeds 2%, while
  Table 1 reports 2.11% for AMZN.
- The setup names AAPL/NVDA/MSFT/META/GOOGL, while the result table reports
  AAPL/GOOGL/AMZN. The exact experiment universe is therefore internally unclear.

## Honest boundary

The architecture and the historical rendered table are real and useful, but a
current one-day run would use mutable data, substantially later source, and
changed model endpoints and would not reproduce the 2024 paper. The vector
figures expose curves, events, and annotations, not their daily numeric arrays.
Run
`scripts/audit_tradingagents_paper.py` to regenerate this package; `--strict`
fails until the native paper data, exact experiment source/configuration, models,
traces, portfolio/execution rules, baselines, daily outputs, and published values
are reproduced.
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
            os.environ.get("TRADINGAGENTS_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_source")
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "TRADINGAGENTS_PAPER_PDF",
                project_root
                / "literature_review/papers/23_tradingagents_multi_agents_llm_financial_trading_framework.pdf",
            )
        ),
    )
    parser.add_argument(
        "--paper-source-archive",
        type=Path,
        default=Path(
            os.environ.get(
                "TRADINGAGENTS_PAPER_SOURCE_ARCHIVE",
                "/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_paper_v7/tradingagents_paper_v7_source.tar",
            )
        ),
    )
    parser.add_argument(
        "--paper-source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "TRADINGAGENTS_PAPER_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_paper_v7/source"
            )
        ),
    )
    parser.add_argument(
        "--paper-versions-root",
        type=Path,
        default=Path(
            os.environ.get(
                "TRADINGAGENTS_PAPER_VERSIONS_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_paper_versions",
            )
        ),
    )
    parser.add_argument(
        "--source-python",
        type=Path,
        default=Path(os.environ.get("TRADINGAGENTS_SOURCE_PYTHON", DEFAULT_SOURCE_PYTHON)),
    )
    parser.add_argument(
        "--yahoo-diagnostic-root",
        type=Path,
        default=Path(
            os.environ.get(
                "TRADINGAGENTS_YAHOO_DIAGNOSTIC_ROOT", DEFAULT_YAHOO_DIAGNOSTIC_ROOT
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/tradingagents",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root,
        args.paper_pdf,
        args.paper_source_archive,
        args.paper_source_root,
        args.paper_versions_root,
        args.source_python,
        args.yahoo_diagnostic_root,
        args.output_dir,
    )
    print(json.dumps(manifest, indent=2))
    return 1 if args.strict and not manifest["full_paper_reproduced"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
