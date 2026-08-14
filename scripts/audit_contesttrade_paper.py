#!/usr/bin/env python3
"""Audit every ContestTrade paper version against the full public source history.

The audit is deliberately fail closed. It inventories every numeric result in
paper Tables 1--3 and both result figures, statically traces the public CLI,
checks the two isolated contest components, compares the ZI reward equations,
and exhausts all official refs, accessible public forks, and paper source archives. It never
imports the upstream package, unpickles joblib files, or calls an external API.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


SOURCE_COMMIT = "22432f9bbba5f1d6862d3b6b5508d4d882b40b94"
SOURCE_URL = "https://github.com/FinStep-AI/ContestTrade"
PAPER_URL = "https://arxiv.org/pdf/2508.00554v4"
PAPER_SHA256 = "a2fd14e7e9074c535ab238a4a9028365c860169743e06223bd20302de549a15c"
PAPER_VERSIONS = {
    1: {
        "submitted_at": "2025-08-01T11:48:13Z",
        "pdf_sha256": "323cae5cc50ab6c7a2fa4acbce4d1f27582ad57ad6a1ec5f4ac1f8df92701c88",
        "pdf_bytes": 3971025,
        "pdf_pages": 9,
        "source_sha256": "c6eed2c73639448e91e2957828fb78b67ff27730df6db8d04002be6b2a07dc59",
        "source_bytes": 3240263,
        "source_files": 12,
        "source_uncompressed_bytes": 3866542,
        "main_tex_sha256": "afd09dba622cef1b51f0d92d39233a9d05691cc3a2a784c3779a026299582c53",
        "repository_commits_at_submission": 0,
        "latest_public_commit_at_submission": "",
        "public_source_state": "repository_not_yet_created",
    },
    2: {
        "submitted_at": "2025-08-13T13:17:06Z",
        "pdf_sha256": "63b5845e6db4bff28d2f742bb0e14e8c5b58e8c13e17b422dc63a5fd38bcec77",
        "pdf_bytes": 4015275,
        "pdf_pages": 9,
        "source_sha256": "587ae77726956e0ede5674b0632e8bf082916957a06013f729a3937e3f5f9d2a",
        "source_bytes": 3274447,
        "source_files": 12,
        "source_uncompressed_bytes": 3910578,
        "main_tex_sha256": "115ed7e294848efb76c41ffd343b3bc3123a29f94aa9d1a6d6f90b751855026f",
        "repository_commits_at_submission": 36,
        "latest_public_commit_at_submission": "13eaf2acb87c348ff695d54a8d861ab3a486c099",
        "public_source_state": "generic_agents_and_legacy_judger_no_data_or_research_contest",
    },
    3: {
        "submitted_at": "2025-08-18T06:13:10Z",
        "pdf_sha256": "5d4f7f2bb89c871c2c9508391afee7aa3795108aa00d8acc82378978d46b2070",
        "pdf_bytes": 3966023,
        "pdf_pages": 9,
        "source_sha256": "e792beb2c64d8b5f6e45b71278d835fb2eabf4e1580b846d8a966855b3b00e7f",
        "source_bytes": 3246448,
        "source_files": 12,
        "source_uncompressed_bytes": 3862059,
        "main_tex_sha256": "b7ea1a1d4ffe3193bfd454c95fd01338f11b5caecd9c1da7ce38ab308c4317fd",
        "repository_commits_at_submission": 53,
        "latest_public_commit_at_submission": "750251a1cfc96470879ede7e513098466d9c27aa",
        "public_source_state": "generic_agents_and_legacy_judger_no_data_or_research_contest",
    },
    4: {
        "submitted_at": "2026-07-08T07:16:24Z",
        "pdf_sha256": PAPER_SHA256,
        "pdf_bytes": 3966727,
        "pdf_pages": 8,
        "source_sha256": "0394d207779d165a36fb203eb26683d735d51477df8ddeecbc9482ad96a4bac9",
        "source_bytes": 3237611,
        "source_files": 11,
        "source_uncompressed_bytes": 3825318,
        "main_tex_sha256": "6cd9686c58273c298d50ec32c8947a5618fd71fc52a790d1c07d53c97ccfdb83",
        "repository_commits_at_submission": 130,
        "latest_public_commit_at_submission": SOURCE_COMMIT,
        "public_source_state": "isolated_contests_present_but_not_reachable_from_public_entrypoint",
    },
}
ORIGINAL_MAIN_RESULT_RASTER_SHA256 = (
    "d8af1c91d75a193d2a76359f6999f3f9998f3b5fb7dcf6a4e2f1c3e67a93f75e"
)
REVISED_MAIN_RESULT_RASTER_SHA256 = (
    "eb9076ab2fd42c764f7a0f4a3bbdd7c2fd76a7bcc5c1a6f5caf7f908d8ef74d3"
)
ABLATION_RESULT_RASTER_SHA256 = (
    "89b27648998bf7fc792f02ed1b2f4fac250acc64b31b657a5ce4fee82dcce38d"
)
PUBLIC_HISTORY_COMMIT_COUNT = 130
PUBLIC_HISTORY_COMMIT_SHA256 = "2aa60512c4cdf45ff0827c1aa03619feefec2e26b1e9c8f7de465790b7bd7562"
PUBLIC_HISTORY_PATH_COUNT = 132
PUBLIC_HISTORY_PATH_SHA256 = "2143e79946a72bfa4cd40fbfc98153d993b2212579c34e2385bb9e44b33f3c47"
PUBLIC_HISTORY_OBJECT_COUNTS = {"blob": 322, "commit": 130, "tag": 1, "tree": 267}
OFFICIAL_HISTORY_TIPS = (
    "refs/remotes/origin/main",
    "refs/remotes/origin/dev",
    "refs/tags/v2.0",
    "refs/tags/v1.1",
    "refs/tags/v1.0",
)
PUBLIC_DISCOVERY_SHA256 = {
    "branches.json": "9cab115b6d33e4361761c608c6653d453ecb4768fd78495f255e4aeacccae889",
    "releases.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "tags.json": "594f4ddc47631fe6b14ce70ca09bb5b823d1cb7e3d28f59ed952268b5a121b8d",
}
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_SNAPSHOT_SHA256 = (
    "087e935650f0782b76d279b9b17a430aebea574bcc79b80a8c8c8b25d5273aa5"
)
PUBLIC_FORK_REPOSITORY_LISTINGS = 157
PUBLIC_FORK_ACCESSIBLE_REPOSITORIES = 153
PUBLIC_FORK_BRANCH_REFS = 186
PUBLIC_FORK_TAG_REFS = 26
PUBLIC_FORK_REF_SEQUENCE_SHA256 = (
    "70905bdd119c37e86d22baa8485b434ddd1b79592e0c6a8785fd3b5ca2f181c6"
)
PUBLIC_FORK_UNIQUE_HEADS = 52
PUBLIC_FORK_DIVERGENT_HEADS = 21
PUBLIC_FORK_DIVERGENT_COMMITS = 88
PUBLIC_FORK_DIVERGENT_COMMIT_SHA256 = (
    "86a9148c54e782e2a7ed0f5228993d36aa29e8ab03d84d9bb807c58126d07e82"
)
PUBLIC_FORK_DIVERGENT_PATHS = 200
PUBLIC_FORK_DIVERGENT_PATH_SHA256 = (
    "0c02a8f2c27b053b24d3b735e848e2f787a74e981143a9bc097f5f37f766d862"
)
PUBLIC_FORK_NEW_OBJECT_COUNTS = {"blob": 381, "commit": 88, "tree": 292}
PUBLIC_FORK_NEW_OBJECT_SHA256 = (
    "77f4692e336746cedbd602d7c2607da952723fd60de33a445a3cc2b3c303a7bd"
)
PUBLIC_FORK_INACCESSIBLE_REPOSITORIES = {
    "b08240/ContestTrade",
    "forgottenAc1/ContestTrade",
    "litom914295/ContestTrade",
    "zhenhaip/ContestTrade",
}
PUBLIC_FORK_STRUCTURED_CHANGED_PATHS = {
    ".claude/settings.local.json",
    "2508.00554v3.pdf",
    "agents_workspace/portfolio.json",
    "cli/static/welcome.txt",
    "contest_trade/config/belief_list.json",
    "contest_trade/config/etf_pool.txt",
    "contest_trade/utils/cache/market_manager/csi1000_components_cache.json",
    "contest_trade/utils/cache/market_manager/csi300_components_cache.json",
    "contest_trade/utils/cache/market_manager/csi500_components_cache.json",
    "contest_trade/utils/cache/market_manager/namechange_data.json",
    "contest_trade/utils/cache/market_manager/stock_basic_cache.json",
    "contest_trade/utils/cache/market_manager/trade_calendar.json",
    "contest_trade/utils/cache/market_manager/us_stock_basic_cache.json",
    "contest_trade/utils/cache/tencent_code_cache.json",
    "crash_report.txt",
    "debug_log.txt",
    "polygon_news.json",
    "requirements.txt",
    "run_output.txt",
    "seekingalpha_news.json",
}
PUBLIC_FORK_PORTFOLIO_BLOBS = {
    "614ce068753a48f36f9f5d93ad7e7921fc9b328b",
    "c1ffddd4b5b7950d671b33cbfa0e3aca17691011",
}
FIRST_PUBLIC_REPOSITORY_COMMIT = "e42d8db87b0f54ce4013e47244c1196d612a95f5"
FIRST_PUBLIC_CODE_COMMIT = "f8aa2364a3c2926111ec0d3fc4ed245d521ac7d8"
FIRST_DATA_CONTEST_COMMIT = "01ce65b53015513af4f2d5e2f2bfda72dd4d4c5b"
DATA_CONTEST_MODEL_COMMIT = "86a80065261782f34bdc79b90912f4870c2f8eee"
FIRST_RESEARCH_CONTEST_COMMIT = "2ad4f371396ae21abd58ea5e9129f05dac8fb7cf"

PINNED_SOURCE_SHA256 = {
    "README.md": "fb77bb27b3ba888c015d0fa9cbdc82bb083aa0be79d72081b030eff1ac771830",
    "README_en.md": "ed99cc6175beb76bf81e846e4ed9d6b26cc1d6f778d23ecdea6511ede255820f",
    "config.yaml": "1f5835d06f46ccf528c1861802e37bab90cac52fcd596c3001682a8e3af1f1f7",
    "uv.lock": "5563509e7ae60e3c8e833ed54cc86d13fc1f9e503d074baf251a60fe861c1cb7",
    "contest_trade/main.py": "6b25ceda52272a10876f398d1c230999e5392f128a6ef022b8df3dd36c959880",
    "contest_trade/contest/data_analyst/data_contest.py": "e59b7c66ceb718a55d22fe7d4e1397abe72fc12881e6c3136986324bcb0cf720",
    "contest_trade/contest/data_analyst/evaluator.py": "948bd379e55a7d75a20990ae966d4f1f5e7241935a891cad8384bc193ce56716",
    "contest_trade/contest/data_analyst/predictor.py": "e5b8c20b2f4308d073a8b5b50cfd89c692d6fcd75d87dc35412491749230a106",
    "contest_trade/contest/data_analyst/lightgbm_predictor/lgbm_mean_model.joblib": "b465f26e4493e77de35b9821038f95ee87074044cff92099d69fdf5478f7036e",
    "contest_trade/contest/data_analyst/lightgbm_predictor/lgbm_std_model.joblib": "418a45f8848aef18f1b1f1de17b26b9d3873e1d11f7da4e378be3e37d6769fbf",
    "contest_trade/contest/researcher/research_contest.py": "80004deb52f673d28e7c2ffbfef3f3da68be0794d2445903ad95e584b7f916af",
    "contest_trade/contest/researcher/research_predictor.py": "36742c53b7abf10d2599642fae05e87f8cd2e9052232d16d2468b6e3e461f0cc",
    "contest_trade/contest/researcher/research_weight_optimizer.py": "509725dc372c401f79158f5dd174c81a9a8da39f8a35c70ad53f462a0fa6296a",
    "contest_trade/contest/researcher/research_signal_judger.py": "768699811c13e2c5e480337884a0ec78c3f69b9cf5b1e652c1530ded03aa4e38",
    "contest_trade/utils/market_manager.py": "9ee554492cc6ea582ddf70ebf799a0a3fa5952ab722f28a7c63a243b627a040b",
    "contest_trade/agents/data_analysis_agent.py": "d71027810fd287438132a2ac87baf79fc416ba750e72909cc190f120161dbe83",
    "cli/main.py": "cab8909e0f4fe7e0adb9778b84cd9dac3bba8eb3192e768d919e32811cc0376f",
    "requirements.txt": "bb4d9ae6afd058639137e0f37b2a7f8487957d7431728c88ef3e59b801943945",
    "pyproject.toml": "f74bad584b3d452aa9c5cabcb5983e5335db17f52ef19a0cd4e9fa1f51a9a90e",
}

# method|cumulative return %|Sharpe ratio|max drawdown %
TABLE_1_TEXT = """
CSI All Share|4.42|0.46|13.75
MACD|2.69|0.10|10.65
RSI&KDJ|8.19|0.47|8.30
LGBM|-25.94|-1.30|34.17
LSTM|8.34|0.51|29.56
A2C|7.89|0.69|18.84
PPO|15.07|1.33|17.11
MASS|-19.12|-1.76|24.55
ContestTrade|52.80|3.12|12.41
"""

# team|setting|rank IC|ICIR
TABLE_2_TEXT = """
Data Analyst|Contest|0.054|0.13
Researcher|Contest|0.079|0.18
"""

# configuration|cumulative return %|Sharpe ratio|max drawdown %
TABLE_3_TEXT = """
Full|52.80|3.12|12.41
w/o LLM Judge|50.55|2.57|13.48
w/o Contest Researcher|32.83|1.78|16.70
w/o Contest Data Analyst|42.85|2.01|13.47
w/o Deep Research|43.75|2.08|20.55
w/o All|3.01|0.07|26.63
"""

METRICS = ("cumulative_return_pct", "sharpe_ratio", "max_drawdown_pct")
MODEL_FEATURES = (
    "reward_mean_1d",
    "reward_mean_3d",
    "reward_std_3d",
    "reward_mean_5d",
    "reward_std_5d",
)
MAIN_RESULT_SERIES = (
    "MACD",
    "RSI&KDJ",
    "LGBM (LightGBM label in v1)",
    "LSTM",
    "PPO",
    "A2C",
    "MASS",
    "CSI All Share",
    "ContestTrade",
)
ABLATION_RESULT_SERIES = (
    "w/o LLM Judge",
    "w/o Deep Research",
    "w/o Contest - Researcher",
    "w/o Contest - Data Analyst",
    "w/o All",
    "ContestTrade (Full Model)",
)
NATIVE_RESULT_EXTENSIONS = {
    ".ckpt",
    ".csv",
    ".h5",
    ".hdf5",
    ".ipynb",
    ".jsonl",
    ".npy",
    ".npz",
    ".parquet",
    ".pickle",
    ".pkl",
    ".pt",
    ".pth",
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


def git_files(root: Path) -> list[str]:
    output = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in output.splitlines() if line]


def git_output(root: Path, *args: str, binary: bool = False) -> Any:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    ).stdout


def git_zpaths(root: Path, *args: str) -> list[str]:
    raw = git_output(root, *args, binary=True)
    return [item.decode("utf-8") for item in raw.split(b"\0") if item]


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paper_result_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in TABLE_1_TEXT.strip().splitlines():
        method, *values = line.split("|")
        for metric, value in zip(METRICS, values):
            rows.append(
                {
                    "paper_table": 1,
                    "entity": method,
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    for line in TABLE_2_TEXT.strip().splitlines():
        team, setting, rank_ic, icir = line.split("|")
        for metric, value in (("rank_ic", rank_ic), ("icir", icir)):
            rows.append(
                {
                    "paper_table": 2,
                    "entity": f"{team} {setting}",
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    for line in TABLE_3_TEXT.strip().splitlines():
        configuration, *values = line.split("|")
        for metric, value in zip(METRICS, values):
            rows.append(
                {
                    "paper_table": 3,
                    "entity": configuration,
                    "metric": metric,
                    "paper_value": float(value),
                }
            )
    if Counter(row["paper_table"] for row in rows) != {1: 27, 2: 4, 3: 18}:
        raise RuntimeError("Paper result denominator changed")
    return rows


def result_conformance() -> list[dict[str, Any]]:
    reason_by_table = {
        1: "no released native return path, baseline runner, backtester, or metric evaluator",
        2: "no released native contest-score path, evaluation panel, or RankIC/ICIR evaluator",
        3: "no released ablation runner, return path, or metric evaluator",
    }
    return [
        {
            **row,
            "native_reproduced_value": "",
            "absolute_difference": "",
            "status": "unavailable_missing_native_result_path",
            "reason": reason_by_table[row["paper_table"]],
        }
        for row in paper_result_rows()
    ]


def paper_internal_consistency() -> list[dict[str, Any]]:
    table_1_ours = {
        row["metric"]: row["paper_value"]
        for row in paper_result_rows()
        if row["paper_table"] == 1 and row["entity"] == "ContestTrade"
    }
    table_3_full = {
        row["metric"]: row["paper_value"]
        for row in paper_result_rows()
        if row["paper_table"] == 3 and row["entity"] == "Full"
    }
    return [
        {
            "metric": metric,
            "table_1_contesttrade": table_1_ours[metric],
            "table_3_full": table_3_full[metric],
            "absolute_difference": abs(table_1_ours[metric] - table_3_full[metric]),
            "status": "paper_internal_identity_match_not_independent_reproduction",
        }
        for metric in METRICS
    ]


def expected_result_value_sequences() -> list[tuple[str, ...]]:
    sequences = []
    for block, label_columns in (
        (TABLE_1_TEXT, 1),
        (TABLE_2_TEXT, 2),
        (TABLE_3_TEXT, 1),
    ):
        for line in block.strip().splitlines():
            sequences.append(tuple(line.split("|")[label_columns:]))
    return list(dict.fromkeys(sequences))


def sequence_present(text: str, values: Sequence[str]) -> bool:
    pattern = r"&\s*" + r"\s*&\s*".join(re.escape(value) for value in values)
    return re.search(pattern, text, flags=re.DOTALL) is not None


def paper_figure_rows() -> list[dict[str, Any]]:
    rows = []
    for figure, digest, series in (
        ("main performance raster", REVISED_MAIN_RESULT_RASTER_SHA256, MAIN_RESULT_SERIES),
        ("ablation raster", ABLATION_RESULT_RASTER_SHA256, ABLATION_RESULT_SERIES),
    ):
        for label in series:
            rows.append(
                {
                    "figure": figure,
                    "series": label,
                    "current_paper_raster_sha256": digest,
                    "numeric_curve_array_released": False,
                    "native_numeric_series_reproduced": False,
                    "public_repository_exact_original_v1_raster": figure
                    == "main performance raster",
                    "status": (
                        "author_raster_correspondence_without_numeric_curve_data"
                        if figure == "main performance raster"
                        else "official_paper_raster_only"
                    ),
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 15:
        raise RuntimeError("ContestTrade result-figure series census changed")
    return rows


def pdf_page_count(path: Path) -> int:
    output = subprocess.run(
        ["pdfinfo", str(path)], check=True, capture_output=True, text=True
    ).stdout
    match = re.search(r"^Pages:\s+(\d+)$", output, flags=re.MULTILINE)
    if not match:
        raise RuntimeError("pdfinfo did not report a page count for %s" % path)
    return int(match.group(1))


def paper_version_inventory(
    versions_root: Path, source_root: Path
) -> list[dict[str, Any]]:
    sequences = expected_result_value_sequences()
    rows = []
    for version, expected in PAPER_VERSIONS.items():
        pdf_path = versions_root / f"paper_v{version}.pdf"
        archive_path = versions_root / f"source_v{version}.tar"
        if sha256(pdf_path) != expected["pdf_sha256"] or pdf_path.stat().st_size != expected["pdf_bytes"]:
            raise RuntimeError("ContestTrade paper v%d PDF drift" % version)
        if sha256(archive_path) != expected["source_sha256"] or archive_path.stat().st_size != expected["source_bytes"]:
            raise RuntimeError("ContestTrade paper v%d source drift" % version)
        if pdf_page_count(pdf_path) != expected["pdf_pages"]:
            raise RuntimeError("ContestTrade paper v%d page census changed" % version)
        with tarfile.open(archive_path) as archive:
            files = [member for member in archive.getmembers() if member.isfile()]
            if len(files) != expected["source_files"]:
                raise RuntimeError("ContestTrade paper v%d source-file census changed" % version)
            if sum(member.size for member in files) != expected["source_uncompressed_bytes"]:
                raise RuntimeError("ContestTrade paper v%d source byte census changed" % version)
            tex_handle = archive.extractfile("main.tex")
            main_figure_handle = archive.extractfile("figures/main_result.jpg")
            ablation_figure_handle = archive.extractfile("figures/ablation_study.jpg")
            if tex_handle is None or main_figure_handle is None or ablation_figure_handle is None:
                raise RuntimeError("ContestTrade paper v%d primary source assets missing" % version)
            tex_bytes = tex_handle.read()
            main_figure_bytes = main_figure_handle.read()
            ablation_figure_bytes = ablation_figure_handle.read()
        if hashlib.sha256(tex_bytes).hexdigest() != expected["main_tex_sha256"]:
            raise RuntimeError("ContestTrade paper v%d main.tex drift" % version)
        tex = tex_bytes.decode("utf-8")
        normalized_tex = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", tex)
        verified_sequences = sum(sequence_present(normalized_tex, sequence) for sequence in sequences)
        if verified_sequences != len(sequences):
            raise RuntimeError("ContestTrade paper v%d result table values changed" % version)
        main_digest = hashlib.sha256(main_figure_bytes).hexdigest()
        expected_main_digest = (
            ORIGINAL_MAIN_RESULT_RASTER_SHA256
            if version == 1
            else REVISED_MAIN_RESULT_RASTER_SHA256
        )
        if main_digest != expected_main_digest:
            raise RuntimeError("ContestTrade paper v%d main result raster changed" % version)
        if hashlib.sha256(ablation_figure_bytes).hexdigest() != ABLATION_RESULT_RASTER_SHA256:
            raise RuntimeError("ContestTrade paper v%d ablation raster changed" % version)

        cutoff = expected["submitted_at"]
        commits_at_submission = int(
            str(
                git_output(
                    source_root,
                    "rev-list",
                    *OFFICIAL_HISTORY_TIPS,
                    f"--before={cutoff}",
                    "--count",
                )
            ).strip()
        )
        latest = str(
            git_output(
                source_root,
                "log",
                *OFFICIAL_HISTORY_TIPS,
                f"--before={cutoff}",
                "-1",
                "--format=%H",
            )
        ).strip()
        if commits_at_submission != expected["repository_commits_at_submission"]:
            raise RuntimeError("ContestTrade repository cutoff changed for paper v%d" % version)
        if latest != expected["latest_public_commit_at_submission"]:
            raise RuntimeError("ContestTrade latest public cutoff commit changed for paper v%d" % version)
        cutoff_paths = (
            set(str(git_output(source_root, "ls-tree", "-r", "--name-only", latest)).splitlines())
            if latest
            else set()
        )
        data_contest_present = (
            "contest_trade/contest/data_analyst/data_contest.py" in cutoff_paths
        )
        research_contest_present = (
            "contest_trade/contest/researcher/research_contest.py" in cutoff_paths
        )
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
                "main_tex_sha256": expected["main_tex_sha256"],
                "distinct_result_row_value_sequences_verified": verified_sequences,
                "displayed_table_cells": 49,
                "displayed_figure_series": 15,
                "result_values_same_as_v4": True,
                "main_result_raster_sha256": main_digest,
                "ablation_result_raster_sha256": ABLATION_RESULT_RASTER_SHA256,
                "public_repository_commits_at_submission": commits_at_submission,
                "latest_public_commit_at_submission": latest,
                "data_contest_source_present_at_submission": data_contest_present,
                "research_contest_source_present_at_submission": research_contest_present,
                "public_source_state": expected["public_source_state"],
                "native_result_reproduced": False,
                "paper_result_credit": False,
            }
        )
    return rows


def source_milestone_rows(source_root: Path) -> list[dict[str, Any]]:
    milestones = (
        ("public repository created", FIRST_PUBLIC_REPOSITORY_COMMIT),
        ("first public code tree", FIRST_PUBLIC_CODE_COMMIT),
        ("Data Contest source introduced", FIRST_DATA_CONTEST_COMMIT),
        ("Data Contest fixed models introduced", DATA_CONTEST_MODEL_COMMIT),
        ("Research Contest source introduced", FIRST_RESEARCH_CONTEST_COMMIT),
        ("current public source", SOURCE_COMMIT),
    )
    rows = []
    for milestone, commit in milestones:
        metadata = str(
            git_output(source_root, "show", "-s", "--format=%H%x1f%cI%x1f%s", commit)
        ).rstrip("\n")
        commit_id, committed_at, subject = metadata.split("\x1f", 2)
        rows.append(
            {
                "milestone": milestone,
                "commit": commit_id,
                "committed_at": committed_at,
                "subject": subject,
                "after_paper_v1": committed_at > PAPER_VERSIONS[1]["submitted_at"],
                "after_paper_v2": committed_at > PAPER_VERSIONS[2]["submitted_at"],
                "after_paper_v3": committed_at > PAPER_VERSIONS[3]["submitted_at"],
                "paper_result_artifact_created": False,
                "paper_result_credit": False,
            }
        )
    return rows


def public_source_history(
    source_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    discovery_root = source_root / "release-discovery"
    for name, expected in PUBLIC_DISCOVERY_SHA256.items():
        if sha256(discovery_root / name) != expected:
            raise RuntimeError("ContestTrade public discovery drift: %s" % name)
    branches = json.loads((discovery_root / "branches.json").read_text(encoding="utf-8"))
    tags = json.loads((discovery_root / "tags.json").read_text(encoding="utf-8"))
    releases = json.loads((discovery_root / "releases.json").read_text(encoding="utf-8"))
    branch_pairs = [(row["name"], row["commit"]["sha"]) for row in branches]
    tag_pairs = [(row["name"], row["commit"]["sha"]) for row in tags]
    if branch_pairs != [
        ("dev", "b017ffaa23eee5043163b4a11b5803b6da58fd0e"),
        ("main", SOURCE_COMMIT),
    ]:
        raise RuntimeError("ContestTrade public branch discovery changed")
    if tag_pairs != [
        ("v2.0", "7e960d01f7bba90c4e076fc8da59326838a861a5"),
        ("v1.1", "3025a7150ca539d43617437c0253fe6caf0c0cba"),
        ("v1.0", "750251a1cfc96470879ede7e513098466d9c27aa"),
    ]:
        raise RuntimeError("ContestTrade public tag discovery changed")
    if releases:
        raise RuntimeError("ContestTrade gained a public release requiring review")
    if str(git_output(source_root, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise RuntimeError("ContestTrade source checkout is shallow")

    commits_raw = str(
        git_output(source_root, "rev-list", "--reverse", *OFFICIAL_HISTORY_TIPS)
    )
    commits = commits_raw.splitlines()
    if len(commits) != PUBLIC_HISTORY_COMMIT_COUNT:
        raise RuntimeError("ContestTrade public commit census changed")
    if hashlib.sha256(commits_raw.encode("utf-8")).hexdigest() != PUBLIC_HISTORY_COMMIT_SHA256:
        raise RuntimeError("ContestTrade public commit sequence changed")
    path_lines = str(
        git_output(
            source_root,
            "log",
            *OFFICIAL_HISTORY_TIPS,
            "--pretty=format:",
            "--name-only",
        )
    ).splitlines()
    historical_paths = sorted({line for line in path_lines if line})
    path_payload = ("\n".join(historical_paths) + "\n").encode("utf-8")
    if len(historical_paths) != PUBLIC_HISTORY_PATH_COUNT:
        raise RuntimeError("ContestTrade public historical path census changed")
    if hashlib.sha256(path_payload).hexdigest() != PUBLIC_HISTORY_PATH_SHA256:
        raise RuntimeError("ContestTrade public historical path inventory changed")

    object_lines = str(
        git_output(source_root, "rev-list", "--objects", *OFFICIAL_HISTORY_TIPS)
    ).splitlines()
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
        raise RuntimeError("ContestTrade reachable-object census changed")
    fsck = subprocess.run(
        ["git", "-C", str(source_root), "fsck", "--full", "--no-reflogs", "--unreachable"],
        check=True,
        capture_output=True,
        text=True,
    )
    if fsck.stdout.strip():
        raise RuntimeError("ContestTrade has unreachable objects requiring review")

    sequences = expected_result_value_sequences()
    blob_sha256: dict[str, str] = {}
    text_row_hit_blobs: list[str] = []
    for object_id, object_type in zip(object_ids, object_types):
        if object_type != "blob":
            continue
        raw = git_output(source_root, "cat-file", "-p", object_id, binary=True)
        blob_sha256[object_id] = hashlib.sha256(raw).hexdigest()
        if b"\x00" in raw[:8192]:
            continue
        text = raw.decode("utf-8", errors="replace")
        if any(sequence_present(text, sequence) for sequence in sequences):
            text_row_hit_blobs.append(object_id)
    if text_row_hit_blobs:
        raise RuntimeError("ContestTrade public history now contains a complete paper result row")

    commit_rows: list[dict[str, Any]] = []
    path_blobs: dict[str, set[str]] = {path: set() for path in historical_paths}
    path_first: dict[str, tuple[str, str]] = {}
    path_last: dict[str, tuple[str, str]] = {}
    for commit in commits:
        metadata = str(
            git_output(source_root, "show", "-s", "--format=%H%x1f%cI%x1f%s", commit)
        ).rstrip("\n")
        commit_id, committed_at, subject = metadata.split("\x1f", 2)
        paths = []
        native_result_paths = []
        exact_original_raster_paths = []
        for line in str(git_output(source_root, "ls-tree", "-r", commit)).splitlines():
            object_meta, path = line.split("\t", 1)
            _mode, object_type, object_id = object_meta.split()
            if object_type != "blob":
                continue
            paths.append(path)
            path_blobs[path].add(object_id)
            path_first.setdefault(path, (commit, committed_at))
            path_last[path] = (commit, committed_at)
            if Path(path).suffix.lower() in NATIVE_RESULT_EXTENSIONS:
                native_result_paths.append(path)
            if blob_sha256[object_id] == ORIGINAL_MAIN_RESULT_RASTER_SHA256:
                exact_original_raster_paths.append(path)
        data_contest_present = (
            "contest_trade/contest/data_analyst/data_contest.py" in paths
        )
        research_contest_present = (
            "contest_trade/contest/researcher/research_contest.py" in paths
        )
        commit_rows.append(
            {
                "commit": commit_id,
                "committed_at": committed_at,
                "subject": subject,
                "tracked_files": len(paths),
                "data_contest_source_present": data_contest_present,
                "research_contest_source_present": research_contest_present,
                "native_structured_result_paths": len(native_result_paths),
                "native_structured_result_path_names": ";".join(native_result_paths),
                "exact_original_v1_result_raster_paths": ";".join(
                    exact_original_raster_paths
                ),
                "independently_regenerated_paper_results": 0,
                "paper_result_credit": False,
            }
        )

    path_rows: list[dict[str, Any]] = []
    for path in historical_paths:
        digests = {blob_sha256[object_id] for object_id in path_blobs[path]}
        suffix = Path(path).suffix.lower()
        exact_original_raster = ORIGINAL_MAIN_RESULT_RASTER_SHA256 in digests
        if exact_original_raster:
            classification = "author_original_v1_result_raster_correspondence"
        elif suffix == ".joblib":
            classification = "fixed_component_model_without_training_provenance"
        elif suffix == ".json" and "/cache/" in path:
            classification = "market_metadata_cache_not_paper_input_or_output"
        else:
            classification = "source_documentation_or_nonresult_media"
        path_rows.append(
            {
                "path": path,
                "extension": suffix,
                "historical_blob_versions": len(path_blobs[path]),
                "first_reachable_commit": path_first[path][0],
                "first_reachable_committed_at": path_first[path][1],
                "last_reachable_commit": path_last[path][0],
                "last_reachable_committed_at": path_last[path][1],
                "native_structured_result_path": suffix in NATIVE_RESULT_EXTENSIONS,
                "exact_original_v1_result_raster": exact_original_raster,
                "classification": classification,
                "paper_result_credit": False,
            }
        )
    native_paths = [row for row in path_rows if row["native_structured_result_path"]]
    exact_raster_paths = [row["path"] for row in path_rows if row["exact_original_v1_result_raster"]]
    if native_paths:
        raise RuntimeError("ContestTrade public history gained a native result path")
    if exact_raster_paths != ["assets/performance_comparison.jpg"]:
        raise RuntimeError("ContestTrade original raster lineage changed")
    revised_raster_blobs = sum(
        digest == REVISED_MAIN_RESULT_RASTER_SHA256 for digest in blob_sha256.values()
    )
    ablation_raster_blobs = sum(
        digest == ABLATION_RESULT_RASTER_SHA256 for digest in blob_sha256.values()
    )
    if revised_raster_blobs or ablation_raster_blobs:
        raise RuntimeError("ContestTrade history gained another official result raster")

    summary = {
        "discovered_public_branches": [
            {"name": name, "head": commit} for name, commit in branch_pairs
        ],
        "discovered_public_tags": [
            {"name": name, "target_commit": commit} for name, commit in tag_pairs
        ],
        "discovered_public_releases": [],
        "reachable_commits": len(commits),
        "unique_historical_paths": len(historical_paths),
        "reachable_object_counts": object_counts,
        "unreachable_objects": 0,
        "native_structured_result_paths": len(native_paths),
        "text_blobs_with_complete_paper_result_row": len(text_row_hit_blobs),
        "exact_original_v1_main_result_raster_paths": exact_raster_paths,
        "exact_revised_main_result_raster_blobs": revised_raster_blobs,
        "exact_ablation_result_raster_blobs": ablation_raster_blobs,
        "raw_numeric_curve_files": 0,
        "independently_regenerated_paper_results": 0,
        "paper_result_credit": False,
    }
    return commit_rows, path_rows, summary


def _git_show_text(source_root: Path, commit: str, path: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(source_root), "show", f"{commit}:{path}"],
        capture_output=True,
    )
    return proc.stdout.decode("utf-8", errors="replace") if proc.returncode == 0 else ""


def _loose_result_sequence_present(text: str, values: Sequence[str]) -> bool:
    bounded_gap = r"[\s\S]{0,240}?"
    tokens = [rf"(?<![\d.]){re.escape(value)}(?![\d.])" for value in values]
    return re.search(bounded_gap.join(tokens), text) is not None


def _fork_path_classification(path: str) -> str:
    if path == "agents_workspace/portfolio.json":
        return "postpaper_personal_mixed_manual_and_ai_trade_ledger_not_paper_experiment"
    if path in {"crash_report.txt", "debug_log.txt", "run_output.txt"}:
        return "postpaper_runtime_failure_diagnostic_not_result"
    if path == "2508.00554v3.pdf":
        return "exact_official_paper_v3_pdf_copy_not_result"
    if path in {"polygon_news.json", "seekingalpha_news.json"}:
        return "us_market_news_input_snapshot_not_paper_panel"
    if "/cache/" in path or path.endswith("_cache.json"):
        return "market_metadata_cache_not_paper_experiment_input_or_output"
    if path == "contest_trade/contest/researcher/lightgbm_predictor/train_model.py":
        return "research_training_scaffold_still_missing_models_and_called_method"
    if path in {
        ".claude/settings.local.json",
        "cli/static/welcome.txt",
        "contest_trade/config/belief_list.json",
        "contest_trade/config/etf_pool.txt",
        "requirements.txt",
    }:
        return "configuration_dependency_or_static_input_not_paper_result"
    return "implementation_documentation_or_nonresult_media"


def public_fork_audit(
    source_root: Path,
    snapshot_path: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    """Exhaust every accessible public fork ref without widening official history."""
    if sha256(snapshot_path) != PUBLIC_FORK_SNAPSHOT_SHA256:
        raise RuntimeError("ContestTrade public-fork snapshot changed")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if len(snapshot) != PUBLIC_FORK_REPOSITORY_LISTINGS:
        raise RuntimeError("ContestTrade public-fork REST listing count changed")

    repository_rows: list[dict[str, Any]] = []
    ref_rows: list[dict[str, Any]] = []
    refs_by_head: dict[str, list[tuple[str, str, str]]] = {}
    inaccessible: set[str] = set()
    for item in snapshot:
        repository = item["full_name"]
        has_error = bool(item.get("ref_error"))
        if has_error:
            inaccessible.add(repository)
            if item["branches"] or item["tags"]:
                raise RuntimeError("Inaccessible ContestTrade fork unexpectedly has refs")
        repository_rows.append(
            {
                "repository": repository,
                "url": item["clone_url"].removesuffix(".git"),
                "default_branch": item["default_branch"],
                "accessible_via_git": not has_error,
                "branch_refs": len(item["branches"]),
                "tag_refs": len(item["tags"]),
                "access_classification": (
                    "accessible_refs_exhausted"
                    if not has_error
                    else "stale_rest_listing_repository_now_404_or_inaccessible"
                ),
            }
        )
        for kind, refs in (("branch", item["branches"]), ("tag", item["tags"])):
            for name, head in refs.items():
                refs_by_head.setdefault(head, []).append((repository, kind, name))
                ref_rows.append(
                    {
                        "repository": repository,
                        "url": item["clone_url"].removesuffix(".git"),
                        "ref_kind": kind,
                        "ref_name": name,
                        "head_commit": head,
                    }
                )
    repository_rows.sort(key=lambda row: str(row["repository"]).casefold())
    ref_rows.sort(
        key=lambda row: (
            str(row["repository"]).casefold(),
            str(row["ref_kind"]),
            str(row["ref_name"]),
        )
    )
    if inaccessible != PUBLIC_FORK_INACCESSIBLE_REPOSITORIES:
        raise RuntimeError("ContestTrade inaccessible public-fork set changed")
    if len(repository_rows) - len(inaccessible) != PUBLIC_FORK_ACCESSIBLE_REPOSITORIES:
        raise RuntimeError("ContestTrade accessible public-fork count changed")
    if Counter(row["ref_kind"] for row in ref_rows) != {
        "branch": PUBLIC_FORK_BRANCH_REFS,
        "tag": PUBLIC_FORK_TAG_REFS,
    }:
        raise RuntimeError("ContestTrade public-fork ref counts changed")
    ref_payload = (
        "\n".join(
            "\t".join(
                (
                    str(row["repository"]),
                    str(row["ref_kind"]),
                    str(row["ref_name"]),
                    str(row["head_commit"]),
                )
            )
            for row in ref_rows
        )
        + "\n"
    ).encode("utf-8")
    if hashlib.sha256(ref_payload).hexdigest() != PUBLIC_FORK_REF_SEQUENCE_SHA256:
        raise RuntimeError("ContestTrade public-fork ref sequence changed")

    official_commits = set(
        str(git_output(source_root, "rev-list", *OFFICIAL_HISTORY_TIPS)).splitlines()
    )
    if len(official_commits) != PUBLIC_HISTORY_COMMIT_COUNT:
        raise RuntimeError("ContestTrade explicit official history changed")
    for head in refs_by_head:
        present = subprocess.run(
            ["git", "-C", str(source_root), "cat-file", "-e", f"{head}^{{commit}}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        if present:
            raise RuntimeError(f"ContestTrade public-fork object missing: {head}")
    if len(refs_by_head) != PUBLIC_FORK_UNIQUE_HEADS:
        raise RuntimeError("ContestTrade public-fork unique-head count changed")
    divergent_heads = sorted(set(refs_by_head) - official_commits)
    if len(divergent_heads) != PUBLIC_FORK_DIVERGENT_HEADS:
        raise RuntimeError("ContestTrade divergent public-fork head count changed")

    divergent_commits_raw = str(
        git_output(
            source_root,
            "rev-list",
            "--reverse",
            *divergent_heads,
            "--not",
            *OFFICIAL_HISTORY_TIPS,
        )
    )
    divergent_commits = divergent_commits_raw.splitlines()
    if len(divergent_commits) != PUBLIC_FORK_DIVERGENT_COMMITS:
        raise RuntimeError("ContestTrade divergent public-fork commit count changed")
    if (
        hashlib.sha256(divergent_commits_raw.encode("utf-8")).hexdigest()
        != PUBLIC_FORK_DIVERGENT_COMMIT_SHA256
    ):
        raise RuntimeError("ContestTrade divergent public-fork commit sequence changed")
    commit_paths: dict[str, list[str]] = {}
    changed_paths: set[str] = set()
    for commit in divergent_commits:
        paths = sorted(
            set(
                git_zpaths(
                    source_root,
                    "diff-tree",
                    "--root",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    "-z",
                    commit,
                )
            )
        )
        commit_paths[commit] = paths
        changed_paths.update(paths)
    changed_path_payload = ("\n".join(sorted(changed_paths)) + "\n").encode("utf-8")
    if len(changed_paths) != PUBLIC_FORK_DIVERGENT_PATHS:
        raise RuntimeError("ContestTrade divergent public-fork path count changed")
    if (
        hashlib.sha256(changed_path_payload).hexdigest()
        != PUBLIC_FORK_DIVERGENT_PATH_SHA256
    ):
        raise RuntimeError("ContestTrade divergent public-fork path inventory changed")
    structured_suffixes = {
        ".ckpt",
        ".csv",
        ".h5",
        ".hdf5",
        ".ipynb",
        ".json",
        ".jsonl",
        ".npy",
        ".npz",
        ".parquet",
        ".pdf",
        ".pickle",
        ".pkl",
        ".pt",
        ".pth",
        ".txt",
    }
    structured_changed_paths = {
        path for path in changed_paths if Path(path).suffix.casefold() in structured_suffixes
    }
    if structured_changed_paths != PUBLIC_FORK_STRUCTURED_CHANGED_PATHS:
        raise RuntimeError("ContestTrade fork structured-path surface changed")

    official_object_ids = {
        line.split(" ", 1)[0]
        for line in str(
            git_output(source_root, "rev-list", "--objects", *OFFICIAL_HISTORY_TIPS)
        ).splitlines()
    }
    fork_object_lines = str(
        git_output(source_root, "rev-list", "--objects", *divergent_heads)
    ).splitlines()
    new_object_ids = sorted(
        {line.split(" ", 1)[0] for line in fork_object_lines} - official_object_ids
    )
    new_object_payload = ("\n".join(new_object_ids) + "\n").encode("utf-8")
    if hashlib.sha256(new_object_payload).hexdigest() != PUBLIC_FORK_NEW_OBJECT_SHA256:
        raise RuntimeError("ContestTrade fork unique-object inventory changed")
    object_proc = subprocess.run(
        ["git", "-C", str(source_root), "cat-file", "--batch-check=%(objecttype)"],
        input="\n".join(new_object_ids) + "\n",
        check=True,
        capture_output=True,
        text=True,
    )
    object_types = object_proc.stdout.splitlines()
    new_object_counts = dict(Counter(object_types))
    if new_object_counts != PUBLIC_FORK_NEW_OBJECT_COUNTS:
        raise RuntimeError("ContestTrade fork unique-object type census changed")
    new_blob_ids = {
        object_id
        for object_id, object_type in zip(new_object_ids, object_types)
        if object_type == "blob"
    }

    path_new_blobs: dict[str, set[str]] = {path: set() for path in changed_paths}
    for commit in divergent_commits:
        raw_tree = git_output(source_root, "ls-tree", "-r", "-z", commit, binary=True)
        for raw_line in raw_tree.split(b"\0"):
            if not raw_line:
                continue
            object_meta, raw_path = raw_line.split(b"\t", 1)
            _mode, object_type, object_id = object_meta.decode("ascii").split()
            path = raw_path.decode("utf-8")
            if object_type == "blob" and object_id in new_blob_ids and path in path_new_blobs:
                path_new_blobs[path].add(object_id)

    paper_row_hit_blobs: list[str] = []
    paper_identifier_blobs: list[str] = []
    empirical_keyword_blobs: list[str] = []
    backtest_function_blobs: list[str] = []
    blob_sha256: dict[str, str] = {}
    sequences = expected_result_value_sequences()
    empirical_pattern = re.compile(
        r"\bsharpe\b|cumulative[ _-]*return|max(?:imum)?[ _-]*drawdown|\bbacktest(?:ing)?\b",
        re.IGNORECASE,
    )
    for blob_id in sorted(new_blob_ids):
        raw = git_output(source_root, "cat-file", "-p", blob_id, binary=True)
        blob_sha256[blob_id] = hashlib.sha256(raw).hexdigest()
        if b"\x00" in raw[:8192]:
            continue
        text = raw.decode("utf-8", errors="replace")
        if any(_loose_result_sequence_present(text, sequence) for sequence in sequences):
            paper_row_hit_blobs.append(blob_id)
        if "2508.00554" in text:
            paper_identifier_blobs.append(blob_id)
        if empirical_pattern.search(text):
            empirical_keyword_blobs.append(blob_id)
        if "def backtest" in text:
            tree = ast.parse(text)
            functions = [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "backtest"
            ]
            if functions:
                body = ast.get_source_segment(text, functions[0]) or ""
                required = (
                    "SimpleTradeCompany",
                    "run_company(trigger_time)",
                    'final_state.get("research_signals", [])',
                )
                if not all(marker in body for marker in required):
                    raise RuntimeError("ContestTrade fork backtest body changed")
                if any(
                    marker in body.casefold()
                    for marker in ("datacontest", "researchcontest", "sharpe", "drawdown", "portfolio")
                ):
                    raise RuntimeError("ContestTrade fork backtest gained an unreviewed result path")
                backtest_function_blobs.append(blob_id)
    if paper_row_hit_blobs:
        raise RuntimeError("ContestTrade public fork contains a complete paper result row")
    if len(paper_identifier_blobs) != 8 or len(empirical_keyword_blobs) != 4:
        raise RuntimeError("ContestTrade fork paper/empirical text surface changed")
    if len(backtest_function_blobs) != 1:
        raise RuntimeError("ContestTrade fork backtest implementation census changed")

    if path_new_blobs["agents_workspace/portfolio.json"] != PUBLIC_FORK_PORTFOLIO_BLOBS:
        raise RuntimeError("ContestTrade personal portfolio ledger lineage changed")
    portfolio_stats = []
    for blob_id in sorted(PUBLIC_FORK_PORTFOLIO_BLOBS):
        payload = json.loads(
            git_output(source_root, "cat-file", "-p", blob_id, binary=True)
        )
        history = payload.get("history", [])
        daily_stats = payload.get("daily_stats", [])
        portfolio_stats.append(
            {
                "blob": blob_id,
                "history_records": len(history),
                "manual_records": sum("MANUAL" in row.get("type", "") for row in history),
                "ai_records": sum("MANUAL" not in row.get("type", "") for row in history),
                "daily_stat_records": len(daily_stats),
                "first_date": min(row["date"] for row in daily_stats),
                "last_date": max(row["date"] for row in daily_stats),
            }
        )
    if {
        (
            row["history_records"],
            row["manual_records"],
            row["ai_records"],
            row["daily_stat_records"],
            row["first_date"],
            row["last_date"],
        )
        for row in portfolio_stats
    } != {
        (16, 9, 7, 21, "2026-02-02", "2026-02-03"),
        (16, 9, 7, 25, "2026-02-02", "2026-02-04"),
    }:
        raise RuntimeError("ContestTrade personal portfolio ledger semantics changed")
    paper_v3_blobs = {
        blob_id
        for blob_id in path_new_blobs["2508.00554v3.pdf"]
        if blob_sha256[blob_id] == PAPER_VERSIONS[3]["pdf_sha256"]
    }
    if len(paper_v3_blobs) != 1:
        raise RuntimeError("ContestTrade fork paper-v3 PDF copy changed")
    diagnostics = {
        "crash_report.txt": ("GraphRecursionError", "NameError: name 'traceback' is not defined"),
        "debug_log.txt": ("Import/Init error",),
        "run_output.txt": (),
    }
    for path, markers in diagnostics.items():
        if not path_new_blobs[path]:
            raise RuntimeError(f"ContestTrade fork diagnostic disappeared: {path}")
        if markers:
            texts = [
                git_output(source_root, "cat-file", "-p", blob, binary=True).decode(
                    "utf-8", errors="replace"
                )
                for blob in path_new_blobs[path]
            ]
            if not all(any(marker in text for text in texts) for marker in markers):
                raise RuntimeError(f"ContestTrade fork diagnostic changed: {path}")

    unique_commits_by_head = {
        head: str(
            git_output(
                source_root,
                "rev-list",
                head,
                "--not",
                *OFFICIAL_HISTORY_TIPS,
            )
        ).splitlines()
        for head in refs_by_head
    }
    head_rows: list[dict[str, Any]] = []
    for head in sorted(refs_by_head):
        paths = git_zpaths(source_root, "ls-tree", "-r", "--name-only", "-z", head)
        main_text = _git_show_text(source_root, head, "contest_trade/main.py")
        predictor_text = _git_show_text(
            source_root,
            head,
            "contest_trade/contest/researcher/research_predictor.py",
        )
        data_contest_text = _git_show_text(
            source_root,
            head,
            "contest_trade/contest/data_analyst/data_contest.py",
        )
        cli_text = _git_show_text(source_root, head, "cli/main.py")
        research_models = [
            path
            for path in paths
            if "contest/researcher/lightgbm_predictor/" in path
            and path.endswith(".joblib")
        ]
        data_integrated = "DataContest(" in main_text
        research_integrated = "ResearchContest(" in main_text
        predict_method = "def predict_signal_scores" in predictor_text
        facility_allocator = (
            "facility_location" in data_contest_text.casefold()
            or "lazy_greedy" in data_contest_text.casefold()
        )
        backtest_present = "def backtest" in cli_text
        portfolio_present = "agents_workspace/portfolio.json" in paths
        behind, ahead = map(
            int,
            str(
                git_output(
                    source_root,
                    "rev-list",
                    "--left-right",
                    "--count",
                    f"{SOURCE_COMMIT}...{head}",
                )
            ).split(),
        )
        merge_proc = subprocess.run(
            ["git", "-C", str(source_root), "merge-base", SOURCE_COMMIT, head],
            capture_output=True,
            text=True,
        )
        merge_base = merge_proc.stdout.strip() if merge_proc.returncode == 0 else ""
        relation = (
            "official_head_exact"
            if head == SOURCE_COMMIT
            else "official_history_reachable"
            if head in official_commits
            else "divergent"
        )
        refs = sorted(refs_by_head[head])
        head_rows.append(
            {
                "head_commit": head,
                "repositories_and_refs": ";".join(
                    f"{repository}:{kind}:{name}" for repository, kind, name in refs
                ),
                "ref_count": len(refs),
                "relation_to_official_history": relation,
                "merge_base_with_official_head": merge_base,
                "commits_ahead_of_official_head": ahead,
                "commits_behind_official_head": behind,
                "unique_commits_beyond_official_history": len(unique_commits_by_head[head]),
                "tracked_paths": len(paths),
                "data_contest_called_from_main": data_integrated,
                "research_contest_called_from_main": research_integrated,
                "research_model_files": len(research_models),
                "research_predict_signal_scores_method": predict_method,
                "facility_location_allocator_present": facility_allocator,
                "date_loop_backtest_command_present": backtest_present,
                "native_nonpaper_personal_portfolio_ledger_present": portfolio_present,
                "native_paper_result_artifact_present": False,
                "paper_result_credit": False,
            }
        )
    if any(
        row["data_contest_called_from_main"]
        or row["research_contest_called_from_main"]
        or row["research_model_files"]
        or row["research_predict_signal_scores_method"]
        or row["facility_location_allocator_present"]
        for row in head_rows
    ):
        raise RuntimeError("ContestTrade fork gained an unreviewed native-contest path")
    if sum(row["date_loop_backtest_command_present"] for row in head_rows) != 2:
        raise RuntimeError("ContestTrade fork backtest-head count changed")
    if sum(row["native_nonpaper_personal_portfolio_ledger_present"] for row in head_rows) != 1:
        raise RuntimeError("ContestTrade fork portfolio-head count changed")

    for row in ref_rows:
        head = str(row["head_commit"])
        row["relation_to_official_history"] = (
            "official_history_reachable" if head in official_commits else "divergent"
        )
        row["unique_commits_beyond_official_history"] = len(unique_commits_by_head[head])
        row["paper_result_credit"] = False

    commit_rows: list[dict[str, Any]] = []
    result_shaped_paths = {
        "agents_workspace/portfolio.json",
        "crash_report.txt",
        "debug_log.txt",
        "run_output.txt",
    }
    for sequence, commit in enumerate(divergent_commits, start=1):
        metadata = str(
            git_output(
                source_root,
                "show",
                "-s",
                "--format=%aI%x1f%an%x1f%ae%x1f%s",
                commit,
            )
        ).rstrip("\n").split("\x1f", 3)
        if len(metadata) != 4:
            raise RuntimeError("ContestTrade fork commit metadata parse changed")
        paths = commit_paths[commit]
        special = sorted(set(paths) & PUBLIC_FORK_STRUCTURED_CHANGED_PATHS)
        nonpaper_outputs = sorted(set(paths) & result_shaped_paths)
        classifications = sorted({_fork_path_classification(path) for path in paths})
        commit_rows.append(
            {
                "sequence": sequence,
                "commit": commit,
                "authored_at": metadata[0],
                "author_name": metadata[1],
                "author_email": metadata[2],
                "subject": metadata[3],
                "changed_paths": len(paths),
                "structured_or_paper_paths": ";".join(special),
                "nonpaper_result_shaped_paths": ";".join(nonpaper_outputs),
                "path_classifications": ";".join(classifications),
                "complete_paper_result_row_hits": 0,
                "native_paper_result_artifact_present": False,
                "paper_result_credit": False,
            }
        )

    path_rows: list[dict[str, Any]] = []
    backtest_blob_set = set(backtest_function_blobs)
    for path in sorted(changed_paths):
        blobs = path_new_blobs[path]
        classification = _fork_path_classification(path)
        path_rows.append(
            {
                "path": path,
                "extension": Path(path).suffix.casefold(),
                "new_blob_versions": len(blobs),
                "classification": classification,
                "exact_official_paper_v3_pdf_copy": path == "2508.00554v3.pdf",
                "date_loop_backtest_source": bool(blobs & backtest_blob_set),
                "native_nonpaper_personal_portfolio_ledger": (
                    path == "agents_workspace/portfolio.json"
                ),
                "runtime_failure_diagnostic": path in diagnostics,
                "native_paper_result_artifact": False,
                "paper_result_credit": False,
            }
        )

    official_ref_count = sum(
        str(row["head_commit"]) in official_commits for row in ref_rows
    )
    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "snapshot_sha256": PUBLIC_FORK_SNAPSHOT_SHA256,
        "github_rest_repository_listings": len(repository_rows),
        "accessible_public_forks": len(repository_rows) - len(inaccessible),
        "stale_or_inaccessible_rest_listings": len(inaccessible),
        "stale_or_inaccessible_repositories": sorted(inaccessible),
        "accessible_branch_refs": sum(row["ref_kind"] == "branch" for row in ref_rows),
        "tag_refs": sum(row["ref_kind"] == "tag" for row in ref_rows),
        "all_refs_audited": len(ref_rows),
        "unique_heads": len(head_rows),
        "official_history_reachable_unique_heads": len(head_rows) - len(divergent_heads),
        "divergent_unique_heads": len(divergent_heads),
        "refs_reachable_from_official_history": official_ref_count,
        "refs_beyond_official_history": len(ref_rows) - official_ref_count,
        "divergent_unique_commits": len(divergent_commits),
        "divergent_changed_paths": len(changed_paths),
        "divergent_new_object_counts": new_object_counts,
        "structured_or_paper_changed_paths": len(structured_changed_paths),
        "new_text_blobs_with_paper_identifier": len(paper_identifier_blobs),
        "new_text_blobs_with_empirical_keywords": len(empirical_keyword_blobs),
        "new_text_blobs_with_complete_paper_result_row": len(paper_row_hit_blobs),
        "exact_official_paper_v3_pdf_copies": len(paper_v3_blobs),
        "date_loop_backtest_function_blobs": len(backtest_function_blobs),
        "date_loop_backtest_heads": sum(
            row["date_loop_backtest_command_present"] for row in head_rows
        ),
        "date_loop_backtest_constructs_paper_portfolio_or_metrics": False,
        "native_nonpaper_personal_portfolio_paths": 1,
        "native_nonpaper_personal_portfolio_blob_versions": len(portfolio_stats),
        "native_nonpaper_personal_portfolio_semantics": portfolio_stats,
        "runtime_failure_diagnostic_paths": len(diagnostics),
        "name_bearing_paper_coauthor_account_divergent_refs": sum(
            row["repository"] == "stepfun-sunrui/ContestTrade"
            and row["relation_to_official_history"] == "divergent"
            for row in ref_rows
        ),
        "name_bearing_account_identity_independently_verified": False,
        "heads_integrating_data_contest": 0,
        "heads_integrating_research_contest": 0,
        "heads_with_required_research_models": 0,
        "heads_with_research_predict_signal_scores_method": 0,
        "heads_with_facility_location_allocator": 0,
        "native_paper_result_artifacts_found": 0,
        "independently_regenerated_paper_results": 0,
        "paper_result_credit": False,
        "interpretation": (
            "all 153 git-accessible forks and 212 branch/tag refs were exhausted; 21 "
            "divergent heads add community engineering, a signal-count-only date-loop "
            "command, one mixed manual/AI personal portfolio ledger dated February 2026, "
            "and failure diagnostics, but no head integrates either paper contest, ships "
            "the required research models or called method, implements facility-location "
            "allocation, or exposes the paper panel, trajectories, portfolio, numeric "
            "curves, table rows, baselines, ablations, seeds, or metrics"
        ),
    }
    return repository_rows, ref_rows, head_rows, commit_rows, path_rows, summary


def ast_class_methods(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
    raise RuntimeError(f"Class {class_name} not found in {path}")


def ast_string_calls(path: Path, attribute: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == attribute and node.args and isinstance(node.args[0], ast.Constant):
            if isinstance(node.args[0].value, str):
                values.append(node.args[0].value)
    return values


def entrypoint_reachability(source_root: Path) -> list[dict[str, Any]]:
    main_path = source_root / "contest_trade/main.py"
    cli_path = source_root / "cli/main.py"
    research_contest_path = source_root / "contest_trade/contest/researcher/research_contest.py"
    research_predictor_path = source_root / "contest_trade/contest/researcher/research_predictor.py"
    main_text = main_path.read_text(encoding="utf-8")
    cli_text = cli_path.read_text(encoding="utf-8")
    research_text = research_contest_path.read_text(encoding="utf-8")
    predictor_methods = ast_class_methods(research_predictor_path, "ResearchPredictor")
    nodes = ast_string_calls(main_path, "add_node")
    model_dir = research_predictor_path.parent / "lightgbm_predictor"
    return [
        {
            "check": "public_cli_import",
            "paper_requirement": "runnable system entrypoint",
            "released_evidence": "cli/main.py imports and constructs SimpleTradeCompany",
            "observed": str("from contest_trade.main import SimpleTradeCompany" in cli_text),
            "status": "component_present",
        },
        {
            "check": "active_workflow_nodes",
            "paper_requirement": "data agents -> Data Contest -> researchers -> Research Contest -> portfolio",
            "released_evidence": ",".join(nodes),
            "observed": str(nodes),
            "status": "mismatch_contests_and_portfolio_absent",
        },
        {
            "check": "data_contest_reachable",
            "paper_requirement": "Data Contest scores and allocates factor context",
            "released_evidence": "no DataContest reference/import/call in contest_trade/main.py",
            "observed": str("DataContest" in main_text),
            "status": "not_reachable_from_public_entrypoint",
        },
        {
            "check": "research_contest_reachable",
            "paper_requirement": "Research Contest predicts and weights signals",
            "released_evidence": "no ResearchContest reference/import/call in contest_trade/main.py",
            "observed": str("ResearchContest" in main_text),
            "status": "not_reachable_from_public_entrypoint",
        },
        {
            "check": "portfolio_construction",
            "paper_requirement": "positive-Sharpe weighted portfolio",
            "released_evidence": "finalize assigns best_signals = research_signals without allocation",
            "observed": str("best_signals = research_signals" in main_text),
            "status": "mismatch_no_active_allocation",
        },
        {
            "check": "research_model_files",
            "paper_requirement": "runnable Research Contest predictor",
            "released_evidence": "ResearchPredictor raises FileNotFoundError when two joblibs are absent",
            "observed": str((model_dir / "lgbm_mean_model.joblib").exists() or (model_dir / "lgbm_std_model.joblib").exists()),
            "status": "missing_both_required_models",
        },
        {
            "check": "research_predict_signal_scores_method",
            "paper_requirement": "Research Contest callable prediction method",
            "released_evidence": "research_contest.py calls predict_signal_scores",
            "observed": str("predict_signal_scores" in predictor_methods),
            "status": "missing_called_method" if "predict_signal_scores" in research_text else "changed_call_path",
        },
    ]


def paper_zi_reward(pairs: Sequence[tuple[float, float]]) -> float:
    """Paper Algorithm 1: signed rating times percent price change, summed."""
    return sum(rating * price_change_pct for rating, price_change_pct in pairs)


def released_zi_reward(pairs: Sequence[tuple[float, float]]) -> float:
    """Exact released evaluator behavior for valid price changes, without importing it."""
    if not pairs:
        return 0.0
    total = 0.0
    for rating, price_change_pct in pairs:
        clipped = max(-20.0, min(20.0, price_change_pct))
        if rating > 0:
            total += rating * clipped
    return total / len(pairs)


def zi_semantics_rows() -> list[dict[str, Any]]:
    cases = {
        "symmetric_bullish_and_correct_bearish": [(2.0, 5.0), (-2.0, -5.0)],
        "bearish_but_price_rises": [(-2.0, 5.0)],
        "single_bullish": [(2.0, 5.0)],
        "clipping_changes_large_move": [(1.0, 25.0)],
    }
    return [
        {
            "case": name,
            "rating_price_change_pct_pairs": json.dumps(pairs),
            "paper_signed_sum": paper_zi_reward(pairs),
            "released_positive_only_clipped_average": released_zi_reward(pairs),
            "absolute_difference": abs(paper_zi_reward(pairs) - released_zi_reward(pairs)),
            "status": "match" if paper_zi_reward(pairs) == released_zi_reward(pairs) else "semantic_mismatch",
        }
        for name, pairs in cases.items()
    ]


def safe_model_inventory(source_root: Path) -> list[dict[str, Any]]:
    """Inspect serialized model bytes as text; never execute joblib/pickle payloads."""
    model_dir = source_root / "contest_trade/contest/data_analyst/lightgbm_predictor"
    rows = []
    for name in ("lgbm_mean_model.joblib", "lgbm_std_model.joblib"):
        path = model_dir / name
        raw = path.read_bytes()
        text = raw.decode("latin1", errors="ignore")
        feature_match = re.search(r"feature_names=([^\r\n]+)", text)
        features = feature_match.group(1).strip().split() if feature_match else []
        rows.append(
            {
                "file": path.relative_to(source_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "safe_inspection_only": True,
                "model_class_string_present": "LGBMRegressor" in text,
                "objective_regression_l1_present": "objective=regression_l1" in text,
                "feature_names": " ".join(features),
                "feature_count": len(features),
                "expected_five_feature_set": features == list(MODEL_FEATURES),
                "training_dates_split_seed_provenance_present": False,
                "status": "shipped_component_without_training_provenance",
            }
        )
    return rows


def cache_inventory(source_root: Path) -> list[dict[str, Any]]:
    cache_dir = source_root / "contest_trade/utils/cache/market_manager"
    rows = []
    for path in sorted(cache_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if path.name == "trade_calendar.json":
            records = len(data["trade_dates"])
            start = data["trade_dates"][0]
            end = data["trade_dates"][-1]
            snapshot = data.get("last_updated", "")
        elif isinstance(data, list):
            records = len(data)
            trade_dates = sorted({str(row.get("trade_date", "")) for row in data if isinstance(row, dict) and row.get("trade_date")})
            start = trade_dates[0] if trade_dates else ""
            end = trade_dates[-1] if trade_dates else ""
            snapshot = trade_dates[-1] if trade_dates else ""
        else:
            records = len(data)
            start = ""
            end = ""
            snapshot = ""
        rows.append(
            {
                "file": path.relative_to(source_root).as_posix(),
                "sha256": sha256(path),
                "record_count": records,
                "date_start": start,
                "date_end": end,
                "snapshot_or_update_date": snapshot,
                "paper_native_input_or_output": False,
                "status": "released_market_metadata_cache_not_paper_experiment_panel",
            }
        )
    return rows


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for relative in git_files(source_root):
        path = source_root / relative
        rows.append(
            {
                "file": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "paper_result_artifact": False,
            }
        )
    return rows


def source_conformance(source_root: Path) -> list[dict[str, Any]]:
    data_contest = (source_root / "contest_trade/contest/data_analyst/data_contest.py").read_text(encoding="utf-8")
    evaluator = (source_root / "contest_trade/contest/data_analyst/evaluator.py").read_text(encoding="utf-8")
    predictor = (source_root / "contest_trade/contest/data_analyst/predictor.py").read_text(encoding="utf-8")
    research_predictor = (source_root / "contest_trade/contest/researcher/research_predictor.py").read_text(encoding="utf-8")
    optimizer = (source_root / "contest_trade/contest/researcher/research_weight_optimizer.py").read_text(encoding="utf-8")
    config = (source_root / "config.yaml").read_text(encoding="utf-8")
    data_agent = (source_root / "contest_trade/agents/data_analysis_agent.py").read_text(encoding="utf-8")
    market = (source_root / "contest_trade/utils/market_manager.py").read_text(encoding="utf-8")
    rows = [
        ("paper_test_period", "2025-01-01 through 2025-06-30", "no experiment date driver/config", "missing"),
        ("paper_training_validation_period", "2024-07 through 2024-12 or earlier", "no training dataset/split driver", "missing"),
        ("daily_a_share_universe", "China A-share daily", "market utilities exist; experiment universe snapshot absent", "partial"),
        ("transaction_cost", "0.001", "CN utility uses multiple commission/stamp/transfer/slippage fields", "mismatch"),
        ("t_plus_one_and_price_limits", "enforced", "market utility code exists; no released backtester", "partial_unverified"),
        ("data_history_window_m", "m=5", "Data predictor constructs 1d/3d/5d reward summaries", "component_match"),
        ("research_prediction_window_n", "n=5", "ResearchPredictor default prediction_window_days=3", "mismatch"),
        ("factor_model_features", "mean, volatility, trend, drawdown", "shipped models expose mean/std only", "mismatch"),
        ("rolling_daily_training", "retrain only on labels realized before decision t", "two fixed joblibs; no data-contest trainer or training provenance", "missing"),
        ("data_allocation", "token-budgeted facility-location lazy greedy; L0=32k L*=16k", "sort predicted scores and select top_k=3", "mismatch"),
        ("data_similarity", "embedding cosine similarity", "no facility-location/cosine path in DataContest", "missing"),
        ("research_allocation", "max(0, Sharpe) normalized", "optimizer clips negative Sharpe and normalizes positive total", "component_match"),
        ("zi_rating_scale", "integer -2,-1,0,1,2", "LLM rating prompt requests -2 through 2", "component_match"),
        ("zi_reward_aggregation", "signed rating*price-change sum", "positive ratings only; +/-20 clip; average over valid observations", "mismatch"),
        ("paper_agent_tool_count", "8 tools", "research config lists 7 tool names", "mismatch"),
        ("factor_context_budget", "about 4k tokens per factor", "default final_target_tokens=4000; at least one check uses string length", "partial"),
        ("data_contest_switch", "Data Contest active", "isolated code exists but active public workflow never calls it", "not_implemented_in_active_path"),
        ("research_contest_switch", "Research Contest active", "config contest_mode false and active workflow never calls it", "not_implemented_in_active_path"),
        ("deepseek_models", "DeepSeek-V3 and DeepSeek-R1", "aliases deepseek-chat and deepseek-reasoner; exact snapshots absent", "partial_unpinned"),
        ("llm_temperature", "paper provides no complete numeric run configuration", "mutable source values such as 0.7 and 0.1", "paper_underspecified"),
        ("temporal_search_filter", "records no later than formation date", "search request bounds prior 30 days; original returned record snapshot absent", "component_partial"),
        ("paper_input_snapshot", "exact news/financial/price data", "only market metadata caches shipped", "missing"),
        ("paper_output_snapshot", "contest scores, actions, holdings, returns", "no tracked native experiment outputs", "missing"),
        ("backtest_evaluator", "CR, Sharpe, MDD and constraints", "no released experiment backtester/metric evaluator", "missing"),
        ("baseline_implementations", "8 paper baselines", "no released native paper baseline runner", "missing"),
        ("ablation_runner", "five ablations plus full", "no released ablation experiment driver", "missing"),
        ("random_seeds", "exact stochastic controls", "no paper-run seeds", "missing"),
        ("cost_or_api_snapshot", "exact external services and responses", "keys/services required; no immutable response snapshot", "missing"),
        ("csi_component_cache_time", "point-in-time universe at each decision", "CSI utility paths load cache snapshot trade_date 20250630", "current_release_path_risk"),
    ]
    # Source-pinned assertions supporting the human-readable observations above.
    assert "top_k" in data_contest and "sorted" in data_contest
    assert "rating > 0" in evaluator and "total_reward / valid_count" in evaluator
    assert all(feature in predictor for feature in MODEL_FEATURES)
    assert "prediction_window_days: int = 3" in research_predictor
    assert "if sharpe_ratio > 0" in optimizer and "/ total_sharpe" in optimizer
    assert "contest_mode: False" in config
    assert "final_target_tokens" in data_agent
    assert "20250630" in market
    return [
        {
            "dimension": dimension,
            "paper_requirement": requirement,
            "released_evidence": evidence,
            "status": status,
        }
        for dimension, requirement, evidence, status in rows
    ]


def verify_pins(source_root: Path, paper_pdf: Path) -> str:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    if sha256(paper_pdf) != PAPER_SHA256:
        raise RuntimeError(f"Expected paper SHA-256 {PAPER_SHA256}, found {sha256(paper_pdf)}")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        path = source_root / relative
        observed = sha256(path)
        if observed != expected:
            raise RuntimeError(f"Pinned hash changed for {relative}: {observed}")
    return commit


def build_audit(
    source_root: Path,
    paper_pdf: Path,
    paper_versions_root: Path,
    fork_snapshot_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    commit = verify_pins(source_root, paper_pdf)
    conformance = result_conformance()
    identities = paper_internal_consistency()
    figures = paper_figure_rows()
    paper_versions = paper_version_inventory(paper_versions_root, source_root)
    milestones = source_milestone_rows(source_root)
    history_commits, history_paths, history_summary = public_source_history(source_root)
    (
        fork_repositories,
        fork_refs,
        fork_heads,
        fork_commits,
        fork_paths,
        fork_summary,
    ) = public_fork_audit(source_root, fork_snapshot_path)
    reachability = entrypoint_reachability(source_root)
    zi_rows = zi_semantics_rows()
    models = safe_model_inventory(source_root)
    caches = cache_inventory(source_root)
    source = source_inventory(source_root)
    config = source_conformance(source_root)

    if len(conformance) != 49 or {row["status"] for row in conformance} != {"unavailable_missing_native_result_path"}:
        raise RuntimeError("Pinned result-cell boundary changed")
    if len(figures) != 15 or len(paper_versions) != 4:
        raise RuntimeError("ContestTrade paper version/figure census changed")
    if len(history_commits) != 130 or len(history_paths) != 132:
        raise RuntimeError("ContestTrade full-history census changed")
    if (
        len(fork_repositories) != PUBLIC_FORK_REPOSITORY_LISTINGS
        or len(fork_refs) != PUBLIC_FORK_BRANCH_REFS + PUBLIC_FORK_TAG_REFS
        or len(fork_heads) != PUBLIC_FORK_UNIQUE_HEADS
        or len(fork_commits) != PUBLIC_FORK_DIVERGENT_COMMITS
        or len(fork_paths) != PUBLIC_FORK_DIVERGENT_PATHS
    ):
        raise RuntimeError("ContestTrade full public-fork census changed")
    if len(source) != 117:
        raise RuntimeError(f"Expected 117 tracked source files, got {len(source)}")
    if len(caches) != 7 or len(models) != 2:
        raise RuntimeError("Pinned release artifact inventory changed")
    if len([row for row in zi_rows if row["status"] == "semantic_mismatch"]) != 3:
        raise RuntimeError("Pinned ZI semantic diagnostic changed")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_1_3_conformance.csv", conformance)
    write_csv(output_dir / "paper_internal_consistency.csv", identities)
    write_csv(output_dir / "paper_figure_series_inventory.csv", figures)
    write_csv(output_dir / "official_paper_version_inventory.csv", paper_versions)
    write_csv(output_dir / "public_source_milestone_inventory.csv", milestones)
    write_csv(output_dir / "public_source_history_commit_inventory.csv", history_commits)
    write_csv(output_dir / "public_source_history_path_inventory.csv", history_paths)
    write_csv(output_dir / "public_fork_repository_access_inventory.csv", fork_repositories)
    write_csv(output_dir / "public_fork_ref_snapshot.csv", fork_refs)
    write_csv(output_dir / "public_fork_unique_head_inventory.csv", fork_heads)
    write_csv(output_dir / "public_fork_divergent_commit_inventory.csv", fork_commits)
    write_csv(output_dir / "public_fork_divergent_path_inventory.csv", fork_paths)
    write_csv(output_dir / "source_entrypoint_reachability.csv", reachability)
    write_csv(output_dir / "zi_reward_semantics_audit.csv", zi_rows)
    write_csv(output_dir / "shipped_lightgbm_model_inventory.csv", models)
    write_csv(output_dir / "released_cache_inventory.csv", caches)
    write_csv(output_dir / "source_config_conformance.csv", config)
    write_csv(output_dir / "released_source_inventory.csv", source)
    (output_dir / "public_source_history.json").write_text(
        json.dumps(history_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "public_fork_census.json").write_text(
        json.dumps(fork_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest: dict[str, Any] = {
        "audit": "ContestTrade arXiv v1--v4 results versus complete official history and accessible public-fork surface",
        "overall_status": "not_reproduced_public_entrypoint_omits_contests",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": "arXiv:2508.00554v4",
        "paper_sha256": PAPER_SHA256,
        "official_paper_versions_audited": len(paper_versions),
        "official_paper_pdf_pages_total": sum(row["pdf_pages"] for row in paper_versions),
        "official_paper_source_files_total": sum(row["source_files"] for row in paper_versions),
        "paper_result_values_stable_across_all_versions": all(
            row["result_values_same_as_v4"] for row in paper_versions
        ),
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "source_commit_date": "2025-12-22",
        "paper_numeric_tables_audited": [1, 2, 3],
        "paper_numeric_result_cells_total": 49,
        "paper_numeric_figure_series_total": len(figures),
        "paper_result_display_units_total": 49 + len(figures),
        "paper_table_cell_counts": {"1": 27, "2": 4, "3": 18},
        "native_paper_result_cells_reproduced": 0,
        "paper_numeric_result_cells_unavailable": 49,
        "native_numeric_figure_series_reproduced": 0,
        "native_paper_result_display_units_reproduced": 0,
        "public_repository_author_raster_series_correspondences": len(
            MAIN_RESULT_SERIES
        ),
        "public_repository_exact_original_v1_result_raster": True,
        "public_repository_raw_numeric_curve_files": history_summary[
            "raw_numeric_curve_files"
        ],
        "paper_internal_repeated_cells_consistent": 3,
        "paper_internal_repeated_cells_independent_reproductions": 0,
        "tracked_source_files_total": len(source),
        "public_source_reachable_commits_total": history_summary["reachable_commits"],
        "public_source_unique_historical_paths_total": history_summary[
            "unique_historical_paths"
        ],
        "public_source_reachable_blobs_total": history_summary[
            "reachable_object_counts"
        ]["blob"],
        "public_source_reachable_trees_total": history_summary[
            "reachable_object_counts"
        ]["tree"],
        "public_source_reachable_commit_objects_total": history_summary[
            "reachable_object_counts"
        ]["commit"],
        "public_source_reachable_tag_objects_total": history_summary[
            "reachable_object_counts"
        ]["tag"],
        "public_source_unreachable_objects_total": history_summary[
            "unreachable_objects"
        ],
        "public_source_native_structured_result_paths": history_summary[
            "native_structured_result_paths"
        ],
        "public_source_text_blobs_with_complete_paper_result_row": history_summary[
            "text_blobs_with_complete_paper_result_row"
        ],
        "public_fork_census_date": fork_summary["census_date"],
        "public_fork_rest_repository_listings": fork_summary[
            "github_rest_repository_listings"
        ],
        "public_forks_accessible": fork_summary["accessible_public_forks"],
        "public_fork_stale_or_inaccessible_rest_listings": fork_summary[
            "stale_or_inaccessible_rest_listings"
        ],
        "public_fork_branch_refs_audited": fork_summary["accessible_branch_refs"],
        "public_fork_tag_refs_audited": fork_summary["tag_refs"],
        "public_fork_unique_heads_audited": fork_summary["unique_heads"],
        "public_fork_divergent_heads_audited": fork_summary["divergent_unique_heads"],
        "public_fork_divergent_commits_audited": fork_summary[
            "divergent_unique_commits"
        ],
        "public_fork_divergent_paths_audited": fork_summary["divergent_changed_paths"],
        "public_fork_new_blobs_audited": fork_summary["divergent_new_object_counts"][
            "blob"
        ],
        "public_fork_new_text_blobs_with_complete_paper_result_row": fork_summary[
            "new_text_blobs_with_complete_paper_result_row"
        ],
        "public_fork_exact_official_paper_v3_pdf_copies": fork_summary[
            "exact_official_paper_v3_pdf_copies"
        ],
        "public_fork_date_loop_backtest_heads": fork_summary[
            "date_loop_backtest_heads"
        ],
        "public_fork_date_loop_backtest_constructs_paper_portfolio_or_metrics": (
            fork_summary["date_loop_backtest_constructs_paper_portfolio_or_metrics"]
        ),
        "public_fork_native_nonpaper_personal_portfolio_paths": fork_summary[
            "native_nonpaper_personal_portfolio_paths"
        ],
        "public_fork_runtime_failure_diagnostic_paths": fork_summary[
            "runtime_failure_diagnostic_paths"
        ],
        "public_fork_heads_integrating_data_contest": fork_summary[
            "heads_integrating_data_contest"
        ],
        "public_fork_heads_integrating_research_contest": fork_summary[
            "heads_integrating_research_contest"
        ],
        "public_fork_heads_with_required_research_models": fork_summary[
            "heads_with_required_research_models"
        ],
        "public_fork_heads_with_research_predict_signal_scores_method": fork_summary[
            "heads_with_research_predict_signal_scores_method"
        ],
        "public_fork_heads_with_facility_location_allocator": fork_summary[
            "heads_with_facility_location_allocator"
        ],
        "public_fork_native_paper_result_artifacts_found": fork_summary[
            "native_paper_result_artifacts_found"
        ],
        "public_fork_paper_result_credit": False,
        "paper_v1_public_repository_commits_at_submission": 0,
        "paper_v2_public_repository_commits_at_submission": 36,
        "paper_v3_public_repository_commits_at_submission": 53,
        "paper_v1_predates_public_repository": True,
        "paper_v2_data_and_research_contest_source_present_at_submission": False,
        "paper_v3_data_and_research_contest_source_present_at_submission": False,
        "data_contest_first_public_after_paper_v3": True,
        "research_contest_first_public_after_paper_v3": True,
        "active_public_workflow_nodes": ["run_data_agents", "run_research_agents", "finalize"],
        "data_contest_reachable_from_public_entrypoint": False,
        "research_contest_reachable_from_public_entrypoint": False,
        "active_portfolio_constructor_present": False,
        "isolated_data_contest_code_present": True,
        "data_contest_shipped_model_files": 2,
        "data_contest_model_training_provenance_present": False,
        "data_contest_facility_location_allocator_present": False,
        "research_contest_required_model_files_present": False,
        "research_predict_signal_scores_method_present": False,
        "research_positive_sharpe_weight_component_present": True,
        "zi_semantic_diagnostic_cases": len(zi_rows),
        "zi_semantic_mismatch_cases": sum(row["status"] == "semantic_mismatch" for row in zi_rows),
        "native_experiment_input_snapshot_shipped": False,
        "native_contest_scores_actions_holdings_or_returns_shipped": False,
        "native_backtest_metric_evaluator_shipped": False,
        "native_baseline_runner_shipped": False,
        "native_ablation_runner_shipped": False,
        "exact_paper_run_seeds_shipped": False,
        "audit_imported_upstream_package": False,
        "audit_unpickled_shipped_models": False,
        "audit_called_llm_or_external_api": False,
        "paper_v4_postdates_pinned_source_commit": True,
        "interpretation": (
            "All four official paper versions retain the same 49 table cells and 15 result-figure "
            "series. Paper v1 predates the public repository, and v2/v3 predate the first public "
            "Data and Research Contest implementations. The repository later shipped the exact "
            "original v1 main-result raster, corroborating nine author-rendered curves but no "
            "numeric series. The complete 130-commit public history contains no native structured "
            "result path or complete paper result row. A dated census also exhausts all 153 "
            "git-accessible public forks and their 212 refs: 21 divergent heads and 88 extra "
            "commits add genuine community engineering, a signal-count-only date loop, one "
            "mixed manual/AI February-2026 personal portfolio ledger, and failure diagnostics, "
            "but no paper experiment result or missing native-contest lineage. The current release contains agent utilities "
            "and inspectable pieces of both contests, "
            "but the CLI runs SimpleTradeCompany, whose graph has only data agents, research "
            "agents, and finalize. It never calls DataContest or ResearchContest and finalize "
            "passes through all research signals without the paper's allocation. The isolated "
            "ResearchContest is not runnable as pinned because its two required model files and "
            "a called prediction method are absent. The isolated DataContest ships two fixed "
            "models but no rolling-training provenance, uses top-3 score sorting instead of the "
            "paper's token-budgeted facility-location allocator, and changes the signed ZI reward "
            "into a clipped positive-only average. With no paper data/output snapshot, experiment "
            "driver, baselines, backtester, ablations, or seeds, 0/64 paper result display units "
            "can be counted as native reproductions."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
    }

    report = f"""# ContestTrade paper-level conformance audit

Overall verdict: **not reproduced**. All four official arXiv versions and all
discovered public source refs have now been audited. The release provides useful
component and author-output evidence, but no public revision executes the claimed
system end to end or regenerates a paper result.

## Primary sources and chronology

- Official paper record: https://arxiv.org/abs/2508.00554. The v1--v4 PDFs and
  TeX source archives are hash-pinned ({sum(row['pdf_pages'] for row in paper_versions)}
  PDF pages and {sum(row['source_files'] for row in paper_versions)} source files).
  Every version retains the same 49 table cells and 15 result-figure series.
- Public source: {SOURCE_URL}, current commit `{commit}`. Discovery covers main and
  dev, tags v1.0/v1.1/v2.0, no GitHub releases, {history_summary['reachable_commits']}
  reachable commits, {history_summary['unique_historical_paths']} historical paths,
  {sum(history_summary['reachable_object_counts'].values())} objects, and no
  unreachable objects.
- Public forks: the {fork_summary['census_date']} REST snapshot listed
  {fork_summary['github_rest_repository_listings']} repositories. Four stale listings
  returned 404/inaccessible Git endpoints; all {fork_summary['accessible_public_forks']}
  git-accessible forks were exhausted across {fork_summary['accessible_branch_refs']}
  branch refs and {fork_summary['tag_refs']} tag refs. Their
  {fork_summary['unique_heads']} unique heads include
  {fork_summary['divergent_unique_heads']} divergent heads, collectively adding
  {fork_summary['divergent_unique_commits']} commits,
  {fork_summary['divergent_changed_paths']} changed paths, and
  {fork_summary['divergent_new_object_counts']['blob']} genuinely new blobs beyond
  the explicit official-history boundary.
- Paper v1 was submitted on 2025-08-01, before the public repository's first commit
  on 2025-08-08 and before its first code tree on 2025-08-11. At v2 and v3 submission,
  the public tree still contained neither the Data Contest nor Research Contest.
  Those first appeared on 2025-08-26 and 2025-08-27, respectively.
- Paper v4 (2026-07-08) postdates the current source head (2025-12-22), but the later
  paper date cannot turn absent execution paths, inputs, or results into a replication.

## What the release genuinely preserves

- `assets/performance_comparison.jpg` is byte-for-byte identical to the original v1
  paper's main-result raster. This corroborates the authorship and lineage of all nine
  visible curves, but the repository has no underlying dates/values and the revised
  v2--v4 raster and six-series ablation raster occur only in paper source archives.
- The isolated Data Contest contains five-day reward features and two serialized
  LightGBM models. This audit reads their bytes only (never unpickles them) and confirms
  the five feature names and L1-regression metadata. No training dates, split, daily
  rolling trainer, seed, or dataset accompanies them.
- The isolated Research weight optimizer implements positive-Sharpe normalization.
  This is a component match, not an executed paper portfolio.
- The paper's repeated Full/Ours table cells are internally identical across all
  versions. Repetition and author-rendered rasters are not independent reproductions.

## Why the claimed system is not replicated

- Exhaustive scanning of all 322 reachable blobs finds no CSV, Parquet, NumPy,
  checkpoint, notebook, JSONL, or other native structured result path and no text blob
  containing a complete paper result row. There are no raw numeric curves, contest
  scores, selected factors, actions, holdings, daily returns, or run logs.
- The fork-only blob scan likewise finds zero complete paper result rows. One fork adds
  a date-loop command called `backtest`, but its function only invokes
  `SimpleTradeCompany`, prints research-signal counts, and never calls either contest,
  constructs holdings/returns, or calculates Sharpe/drawdown. No fork head repairs the
  missing Research models/method or adds the facility-location allocator.
- One later personal fork commits two versions of `agents_workspace/portfolio.json`.
  They contain 16 mixed manual/AI trade records (nine manual, seven AI) and 21/25
  intraday snapshots from 2026-02-02 through 2026-02-04. They are useful evidence that
  a community auto-trading adaptation ran, but they are not the paper experiment panel,
  are manually intervened, contain no paper metrics, and receive zero paper credit.
- Three other fork paths are runtime failure diagnostics; the longest terminates in a
  LangGraph recursion error followed by a missing-`traceback` `NameError`. An exact
  paper-v3 PDF copy and U.S.-market news inputs are provenance/input evidence only.
- Static tracing of the actual CLI reaches `run_data_agents -> run_research_agents ->
  finalize`. Neither `DataContest` nor `ResearchContest` is called, and `finalize`
  exposes all research signals without constructing the paper portfolio.
- The isolated Research Contest requires two absent model files and calls
  `predict_signal_scores`, which `ResearchPredictor` does not define. Its default
  prediction horizon is three days, while paper v4 specifies five.
- The Data Contest sorts predicted scores and retains top three. No public revision
  implements the paper's 32k-to-16k token-budgeted facility-location/lazy-greedy
  allocator or embedding-cosine diversity objective.
- Paper Algorithm 1 sums signed rating x price change. The released evaluator ignores
  non-positive ratings, clips price changes to +/-20%, and averages observations. The
  synthetic diagnostic gives paper reward 20 versus released reward 5 for one correct
  bullish and one correct bearish observation.
- The release lacks the immutable experiment panel, backtester/metric evaluator,
  baseline and ablation runners, complete model/API snapshot, and run seeds. Its seven
  JSON caches are market metadata, not paper inputs or outputs.

## Honest denominator

The paper has **64 result display units**: 49 numeric table cells (27 main performance,
4 contest-score, 18 ablation) plus 15 raster-only return series (9 main, 6 ablation).
**0/64** are independently reproduced. The exact v1 raster is recorded separately as
an author-output correspondence for nine series and receives no result credit. All 49
table cells and all 15 numeric curves remain unavailable from native result paths.

Run `scripts/audit_contesttrade_paper.py` to regenerate this package. Use `--strict`
to fail until the released system executes both contests and reproduces the pinned
paper inputs, configurations, trajectories, portfolio, curves, and all 49 table cells.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
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
                "CONTESTTRADE_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/contesttrade_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "CONTESTTRADE_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/contesttrade_paper.pdf",
            )
        ),
    )
    parser.add_argument(
        "--paper-versions-root",
        type=Path,
        default=Path(
            os.environ.get(
                "CONTESTTRADE_PAPER_VERSIONS_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/contesttrade_paper_versions",
            )
        ),
    )
    parser.add_argument(
        "--fork-snapshot",
        type=Path,
        default=Path(
            os.environ.get(
                "CONTESTTRADE_FORK_SNAPSHOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/contesttrade_paper_versions/public_fork_snapshot.json",
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/contesttrade",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(),
        args.paper_pdf.resolve(),
        args.paper_versions_root.resolve(),
        args.fork_snapshot.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
