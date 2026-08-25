#!/usr/bin/env python3
"""Audit every AlphaAgent paper version against both official repository roots.

The repository's default ``main`` branch is a July 2026 rewrite, but the same
public repository also retains a disjoint 485-commit ``legacy-main`` history
beginning in April 2024.  That history contains the preprint-era AlphaAgent
workflow, prompts, AST matcher, Qlib configurations, factor-expression artifacts,
and seven extensionless Qlib/MLflow run records.  This audit pins and executes an
intact February 2025 mechanism snapshot, records later preprint-cutoff breakage,
compiles and compares both official arXiv source archives, and inventories the
complete official two-root Git closure.  One native author run record corroborates
five displayed paper cells, but it is not an independent regeneration: the paper's
predictions, portfolios, daily returns, trials, and figure arrays remain unreleased.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import pickletools
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


SOURCE_COMMIT = "b42cb397025510da44355db9dcf278304321f589"
SOURCE_URL = "https://github.com/RndmVariableQ/AlphaAgent"
SOURCE_FIRST_COMMIT = "7debd15ca98309a8df9c1d50aca3831f320687cf"
LEGACY_HEAD_COMMIT = "1da96e94a06a925c3997899f1848899440585efe"
LEGACY_ROOT_COMMIT = "c740262752b585bc59e41e26807d826ec7bebe75"
PAPER_MECHANISM_COMMIT = "95e47882cbed3ba0cafd42e812fe0032a8ae0681"
PAPER_MECHANISM_COMMIT_UTC = "2025-02-12T13:30:56Z"
QLIB_SOURCE_COMMIT = "c9ed050ef034fe6519c14b59f3d207abcb693282"
MATCHING_RUN_ID = "77b227f86e5a47bab48178cac409a98b"
MATCHING_RUN_STARTED_UTC = "2025-01-28T05:53:44.771Z"
RUN_TIME_PUBLIC_HEAD = "0e1747b36a0d5f1b5d3c5ca23bff659f891c69d4"
RUN_TIME_US_FACTOR_PATH = "rdagent/app/qlib_rd_loop/us_factors.csv"
PAPER_ERA_US_FACTOR_PATH = "factor_zoo/us_factors.csv"
QLIB_DATA_DOWNLOADER_SHA256 = (
    "53abbe19beebb29da47806a574d31f393cc963e0acdc5c7e41efac092f8f044c"
)
QLIB_US_VERSIONED_DATA_URL = (
    "https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/"
    "qlib_data_us_1d_0.9.5.zip"
)
QLIB_US_FALLBACK_DATA_URL = (
    "https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/"
    "qlib_data_us_1d_latest.zip"
)
QLIB_US_DATA_ARCHIVE_SHA256 = (
    "20e3283009784843dcfe690488bf3aa739e64159f1da51a9ec33dd3fb647187f"
)
QLIB_US_DATA_ARCHIVE_BYTES = 450_094_816
QLIB_US_DATA_ASSET_LAST_MODIFIED_UTC = "2024-05-22T06:54:13Z"
QLIB_US_DATA_OBSERVED_ON = "2026-08-25"
LATEST_FULL_TREE_PREPRINT_COMMIT = "3cbb7b7e9abe9bc3f3beaa7fcb2102293fbbea4a"
PREPRINT_CUTOFF_COMMIT = "0bc7a34ed9701a0149ae990b6484e7c73b347ea0"
PAPER_RUN_RECORD_TREE = "09339a924f84bd42915e8643fcd39a60ac81e911"
ALPHAAGENT_INTRO_COMMIT = "7f041be0793600188be180e3df2acf5421c1c644"
PAPER_URL = "https://arxiv.org/pdf/2502.16789v2"
PAPER_SHA256 = "cf620c3b33a98edd4124230458b65741e1767fa37a3a180828de1035ded52ab1"
PAPER_V1_URL = "https://arxiv.org/pdf/2502.16789v1"
PAPER_V1_SHA256 = "943b286b40186ce03b8e39fc0dbd2f268807042c6192e9200e68972cb45ab890"
PAPER_VERSIONS: Mapping[str, Mapping[str, Any]] = {
    "v1": {
        "submitted_at": "2025-02-24T02:56:46Z",
        "pdf_url": PAPER_V1_URL,
        "pdf_sha256": PAPER_V1_SHA256,
        "pdf_bytes": 1_188_155,
        "pdf_pages": 10,
        "source_url": "https://export.arxiv.org/e-print/2502.16789v1",
        "source_sha256": "229d28d990237c781b2507b531ffd3cef038b9299eb1c9945e1a950d61938371",
        "source_bytes": 1_735_844,
        "source_files": 26,
        "source_uncompressed_bytes": 2_235_538,
        "source_tree_sha256": "229bb105ce8f188899fe02d9d2497a54a33e09fc53f7ea9d291e5951248de97f",
        "main_tex": "SIGKDD_main.tex",
        "source_commits_at_submission": 438,
        "source_cutoff_commit": PREPRINT_CUTOFF_COMMIT,
        "source_cutoff_date": "2025-02-17T15:07:43+08:00",
        "source_cutoff_tracked_files": 455,
    },
    "v2": {
        "submitted_at": "2025-06-09T01:44:51Z",
        "pdf_url": PAPER_URL,
        "pdf_sha256": PAPER_SHA256,
        "pdf_bytes": 1_924_216,
        "pdf_pages": 10,
        "source_url": "https://export.arxiv.org/e-print/2502.16789v2",
        "source_sha256": "ac8bb821ed1935931a089056778b44e4f864fec85f7101b52e39a1c82246079f",
        "source_bytes": 1_442_257,
        "source_files": 15,
        "source_uncompressed_bytes": 1_867_776,
        "source_tree_sha256": "6a8e4bbba891c4fc78469f0ae387a5d02c7a8b434c6425e533231cf390f1d2d9",
        "main_tex": "SIGKDD_CAMERA-READY_VERSION.tex",
        "source_commits_at_submission": 483,
        "source_cutoff_commit": "d4770f11f0ed1ea3d26cf519ede1560c6bab744d",
        "source_cutoff_date": "2025-06-07T17:32:08+08:00",
        "source_cutoff_tracked_files": 181,
    },
}
OFFICIAL_HEADS = (SOURCE_COMMIT, LEGACY_HEAD_COMMIT)
FORK_DISCOVERY_DATE = "2026-08-14"
FORK_DEFAULT_HEAD_TOTAL = 71
FORK_DATA_REPOSITORY = "vodaza36/AlphaAgent"
FORK_DATA_TIP = "8f16d03d4048647d9eb6ce2e5224bfaff99f7812"
FORK_DATA_ZIP_SHA256 = "ac0ead7c234f1aefa8c2dc0d4e5c2df04285b00cb1e78aba484b1e31f61f0ec5"
FORK_DEFAULT_HEAD_GROUPS: tuple[Mapping[str, Any], ...] = (
    {
        "group_id": "official_legacy_head",
        "repository": "57 fork default branches",
        "repository_count": 57,
        "tip_commit": LEGACY_HEAD_COMMIT,
        "base_commit": LEGACY_HEAD_COMMIT,
        "expected_commits_ahead": 0,
        "expected_changed_paths": 0,
        "expected_added_paths": 0,
        "candidate_paths": "",
        "classification": "unchanged_official_legacy_head",
    },
    {
        "group_id": "official_rewrite_head",
        "repository": "10 fork default branches",
        "repository_count": 10,
        "tip_commit": SOURCE_COMMIT,
        "base_commit": SOURCE_COMMIT,
        "expected_commits_ahead": 0,
        "expected_changed_paths": 0,
        "expected_added_paths": 0,
        "candidate_paths": "",
        "classification": "unchanged_official_rewrite_head",
    },
    {
        "group_id": "hongyi_h_model_substitution",
        "repository": "hongyi-h/AlphaAgent",
        "repository_count": 1,
        "tip_commit": "e3634a100a33d2a21532e8bafcf458765a7aef8b",
        "base_commit": LEGACY_HEAD_COMMIT,
        "expected_commits_ahead": 1,
        "expected_changed_paths": 2,
        "expected_added_paths": 0,
        "candidate_paths": "",
        "classification": "llm_endpoint_and_model_substitution_only",
    },
    {
        "group_id": "hexa_localization",
        "repository": "HexaWarriorW/AlphaAgent",
        "repository_count": 1,
        "tip_commit": "bb6e330f33c2a68917f8ec489d147f9df8027bb2",
        "base_commit": LEGACY_HEAD_COMMIT,
        "expected_commits_ahead": 8,
        "expected_changed_paths": 59,
        "expected_added_paths": 14,
        "candidate_paths": "",
        "classification": "localization_and_runtime_changes_no_paper_outputs",
    },
    {
        "group_id": "vodaza_postpaper_run",
        "repository": FORK_DATA_REPOSITORY,
        "repository_count": 1,
        "tip_commit": FORK_DATA_TIP,
        "base_commit": LEGACY_HEAD_COMMIT,
        "expected_commits_ahead": 19,
        "expected_changed_paths": 43,
        "expected_added_paths": 14,
        "candidate_paths": "data/us_data.zip;hypothesis.md",
        "classification": "unaffiliated_2026_data_bundle_and_new_hypothesis_summary",
    },
    {
        "group_id": "wang_rewrite_extension",
        "repository": "Wangchanghao12/AlphaAgent",
        "repository_count": 1,
        "tip_commit": "e5e58cd6b1e8251436a8e5fbf65f0e82cd48bf3e",
        "base_commit": SOURCE_COMMIT,
        "expected_commits_ahead": 40,
        "expected_changed_paths": 48,
        "expected_added_paths": 14,
        "candidate_paths": "artifacts/factorzoo/stock_1d/mining_delivered_registry.json",
        "classification": "disjoint_rewrite_extension_not_paper_experiment",
    },
)
OFFICIAL_COMMIT_SEQUENCE_SHA256 = (
    "dec34bd1290f543cc8906310682a34e98625fd985b75dfa124251f1bc40cf266"
)
OFFICIAL_OBJECT_SEQUENCE_SHA256 = (
    "a787a51c629a774a5d308468d03e594c280abfb109263ee1bd6d5ea7c895e9f7"
)
OFFICIAL_PATH_SEQUENCE_SHA256 = (
    "7f517ea6d3cce3303ff830fc8824e78a86c577ba52413df0e4a00272c5b9329d"
)
PUBLIC_HEAD_DISCOVERY_SHA256 = (
    "72885e1d64e1109c4009a08372c68142d013665b2edeb5e321320d1e2ec8d731"
)
EMPTY_DISCOVERY_SHA256 = hashlib.sha256(b"").hexdigest()
DEFAULT_SOURCE_PYTHON = (
    "/nfs/roberts/project/pi_btk22/zc362/environments/current/"
    "alphaagent-rewrite/bin/python"
)
DEFAULT_PAPER_HOST_PYTHON = str(
    Path(__file__).resolve().parent / "run_alphaagent_paper_host_python.sh"
)
DEFAULT_PAPER_QLIB_PYTHON = str(
    Path(__file__).resolve().parent / "run_alphaagent_paper_qlib_python.sh"
)
DEFAULT_PAPER_QLIB_SOURCE_ROOT = (
    "/nfs/roberts/scratch/pi_btk22/zc362/qlib_alphaagent_paper_era"
)
DEFAULT_PAPER_QLIB_DATA_ARCHIVE = (
    "/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_qlib_us_095/"
    "20260825115404_qlib_data_us_1d_latest.zip"
)
REWRITE_ENV_FREEZE_SHA256 = (
    "98a93cf29257f73ff3e26d2f4a1fe2ab264c1ea9d1d9eed4fd2d978ff6d99f02"
)
PAPER_HOST_ENV_FREEZE_SHA256 = (
    "040a0414d4bb482cb18ec5bb60f3b3e0b495ac17a41a2ebdd4693f3275ec640c"
)
PAPER_QLIB_ENV_FREEZE_SHA256 = (
    "450be5351acb35eb1d3b6b443226cac7a730bb8cce9101146f3e777c22ece1f2"
)
PAPER_ERA_IMPORT_FAILURE_MODULE = "rdagent.components.coder.factor_coder.test"
PAPER_ERA_IMPORT_FAILURE_PATH = (
    "/home/tangziyi/RD-Agent/rdagent/components/coder/factor_coder/"
    "template_debug.jinjia2"
)
EXPECTED_SYNTHETIC_SHA256 = (
    "e0bd090308b893c6bcf97cc1589538e4fcedc4a896bb90d21a0848e92d7a5dc9"
)

PINNED_SOURCE_SHA256 = {
    "README.md": "b90839541fdb8d2f31ba75d868e614561791f6f4e6f020a3a04ae6d1cf4ca292",
    "pyproject.toml": "7b8c4e7fe00b45d476384cc1c48a368f004624834b7dd152d967c3eb1039e3c7",
    "configs/data.yaml": "f220cd2ffeade57b7de8ec6ffb8ecc4551821d38b9d333100500591272acdd14",
    "docs/data_release.md": "793389162defa295eebdb0c733f72615416a2d89a27168668019ad2a2e17afae",
    "docs/dev_log.md": "3d75eb4528e62a9043dfdb687716fa6d4323430419e47fe04b50738aca60785f",
    "scripts/factor_mining.py": "b0b6a52998a19bb471d7b475aaf82920c8c22387079b34716c4ac40ce4b671c0",
    "alphaagent/factor/mining/config.py": "776ddb5dd26886cabefe7f01796a52e39cdede709ca5ed9977de3cadeba5f660",
    "alphaagent/factor/mining/loop.py": "04f8af1a2f996ef8f7eff4d7f0dbe5309148d0910bc8807463b9f3eaad06a989",
    "alphaagent/factor/mining/prompts.py": "3001f33376935d9ab43e7491a30bd04cc3641fd96981a409b7b6dcc0aeccfbab",
    "alphaagent/factor/zoo/similarity.py": "50139fe8a1d1c9bd01d3e20a5c9bdfda5368d33539047e114fb029ad4552a48c",
    "alphaagent/dsl/core/parser.py": "8edb9dbdb0c1e3a9f64a283d7d48026a60d31a0b3b061b19fc03907c86f4b4f3",
    "artifacts/factorzoo/stock_1d/mining_delivered_registry.json": "4c7e3fad8ed6cc57284642ef827fd1619f5ed94529e555f006431ff9536bacd7",
    "artifacts/factorzoo/stock_1d/mls_fmb_percentiles.json": "a5ebe6b28af119b0ea430106516b694ac790a814656dfdd999c3ae42f646ebf5",
}

PAPER_MECHANISM_SHA256 = {
    "factor_zoo/alpha101.csv": "d08d678a4a9003cf9427faa1f7b0d1a682a652bc51183d9f1b743bd3043524b5",
    "rdagent/app/qlib_rd_loop/conf.py": "d69138aca91dd4709a6c66afd57a241ac88521375d6ae4fa608ac05a6fe21552",
    "rdagent/components/coder/factor_coder/expr_parser_tree.py": "4cd66f0c207080e86e887bfd24f5592ac861966a35c4080ed8d17cfbc49dd777",
    "rdagent/components/coder/factor_coder/prompts_alphaagent.yaml": "699459f9ab9d6d22ccfbadff9fd12f7bd97dd317e9ccbe79b53ebb3a5d309f3b",
    "rdagent/components/workflow/alphaagent_loop.py": "6ed8bcfd34a830cc568f36c091780eff6a777a4abecfd93f19d75258d9a23b75",
    "rdagent/scenarios/qlib/experiment/factor_template/conf_cn_combined.yaml": "a1bbb321adb86ae913a8d46133d7c53c805fa2090de0c2f8604e20cd960f89d2",
    "rdagent/scenarios/qlib/experiment/factor_template/conf_us.yaml": "1e9c967acfd772aae9f206e65e11d7556136e7971ea129f4a6ae90d754edd37b",
    "rdagent/scenarios/qlib/experiment/factor_template/conf_us_combined.yaml": "a9e5ac589020624ac255276c241bc4b8a69930f7220f68f8f14edb04a4fe1a6d",
    "rdagent/scenarios/qlib/proposal/factor_proposal.py": "8b550d509942c63f14b4ffccd50025b7e417a647904f9130f44198f0dc8f5ecd",
    "rdagent/scenarios/qlib/proposal/prompts_alphaagent.yaml": "65f65b096a910a7ec3f018e83b49ba2cf963179aa4b062a77b3a49915fa9f9a9",
}

METRICS = ("IC", "ICIR", "AR_pct", "IR", "MDD_pct")

# method|CSI500 five metrics|S&P500 five metrics
TABLE_2_TEXT = """
LSTM|0.0175|0.1521|4.96|0.6225|-9.68|0.0028|0.0181|-1.51|-0.1671|-26.05
Transformer|0.0131|0.1074|4.11|0.5074|-17.45|0.0013|0.0129|-4.55|-0.4964|-34.96
LightGBM|0.0120|0.1209|-1.18|-0.1588|-18.97|0.0011|0.0116|-2.64|-0.4224|-21.17
TRA|0.0198|0.1794|2.91|0.4261|-12.73|-0.0003|-0.0027|-8.51|-1.1345|-49.55
Stock-Mixer|0.0000|0.0003|-0.35|-0.0496|-16.82|0.0030|0.0312|-2.49|-0.3342|-29.43
AlphaForge|0.0146|0.1299|3.45|0.3270|-17.67|0.0026|0.0240|2.45|0.3369|-10.91
RD-Agent|0.0113|0.0872|0.78|0.0744|-20.85|0.0019|0.0123|1.69|0.1664|-23.18
DeepSeek-R1 best-of-10|0.0132|0.1201|1.58|0.2086|-14.95|0.0048|0.0369|2.75|0.2400|-15.34
OpenAI-o1 best-of-10|0.0159|0.1502|0.46|0.0632|-21.29|0.0028|0.0217|2.29|0.2021|-16.35
AlphaAgent|0.0212|0.1938|11.00|1.488|-9.36|0.0056|0.0552|8.74|1.0545|-9.10
"""

TABLE_2_V1_TEXT = TABLE_2_TEXT.replace(
    "AlphaForge|0.0146|0.1299|3.45|0.3270|-17.67|0.0026|0.0240|2.45|0.3369|-10.91",
    "AlphaForge|0.0146|0.1299|3.45|0.3270|-17.67|0.0017|0.0215|2.10|0.2604|-19.57",
)

DATASET_SPLITS = (
    ("S&P500", "training", "2015-01", "2019-12", 1258),
    ("S&P500", "validation", "2020-01", "2020-12", 253),
    ("S&P500", "testing", "2021-01", "2025-01", 1004),
    ("CSI500", "training", "2015-01", "2019-12", 1219),
    ("CSI500", "validation", "2020-01", "2020-12", 243),
    ("CSI500", "testing", "2021-01", "2025-01", 968),
)

DATASET_SPLITS_V1 = tuple(
    (market, split, start, "2024-12" if split == "testing" else end, days)
    for market, split, start, end, days in DATASET_SPLITS
)

BASE_FACTOR_EXPRESSIONS = {
    "intraday_return": "DIVIDE(SUBTRACT($close, $open), $open)",
    "daily_return": "SUBTRACT(DIVIDE($close, DELAY($close, 1)), 1)",
    "relative_volume_20d": "DIVIDE($volume, TS_MEAN($volume, 20))",
    "normalized_daily_range": "DIVIDE(SUBTRACT($high, $low), DELAY($close, 1))",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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


def git_output(root: Path, *args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=check,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def git_tree_files(root: Path, commit: str) -> list[str]:
    output = git_output(
        root, "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only", commit
    )
    return [line for line in output.splitlines() if line]


def git_commit_record(root: Path, commit: str) -> dict[str, str]:
    commit_hash, date, subject = git_output(
        root, "show", "-s", "--format=%H|%aI|%s", commit
    ).split("|", 2)
    return {"commit": commit_hash, "date": date, "subject": subject}


def extract_git_commit(source_root: Path, commit: str, destination: Path) -> None:
    with tempfile.NamedTemporaryFile(
        prefix=f"alphaagent-{commit[:12]}-", suffix=".tar", dir=destination.parent, delete=False
    ) as handle:
        archive_path = Path(handle.name)
    try:
        subprocess.run(
            [
                "git",
                "-C",
                str(source_root),
                "archive",
                "--format=tar",
                f"--output={archive_path}",
                commit,
            ],
            check=True,
        )
        with tarfile.open(archive_path) as archive:
            try:
                archive.extractall(destination, filter="fully_trusted")
            except TypeError:  # pragma: no cover - Python versions before filter support
                archive.extractall(destination)
    finally:
        archive_path.unlink(missing_ok=True)


def history_audit(source_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    official_heads = (SOURCE_COMMIT, LEGACY_HEAD_COMMIT)
    roots = sorted(
        git_output(source_root, "rev-list", *official_heads, "--max-parents=0").splitlines()
    )
    merge_base = subprocess.run(
        ["git", "-C", str(source_root), "merge-base", SOURCE_COMMIT, LEGACY_HEAD_COMMIT],
        check=False,
        capture_output=True,
        text=True,
    )
    facts: dict[str, Any] = {
        "is_shallow": git_output(source_root, "rev-parse", "--is-shallow-repository") == "true",
        "reachable_commits": int(
            git_output(source_root, "rev-list", *official_heads, "--count")
        ),
        "current_main_commits": int(git_output(source_root, "rev-list", SOURCE_COMMIT, "--count")),
        "legacy_main_commits": int(git_output(source_root, "rev-list", LEGACY_HEAD_COMMIT, "--count")),
        "root_commits": roots,
        "current_and_legacy_have_common_ancestor": merge_base.returncode == 0,
        "paper_mechanism_is_legacy_ancestor": subprocess.run(
            ["git", "-C", str(source_root), "merge-base", "--is-ancestor", PAPER_MECHANISM_COMMIT, LEGACY_HEAD_COMMIT],
            check=False,
        ).returncode
        == 0,
        "preprint_cutoff_is_legacy_ancestor": subprocess.run(
            ["git", "-C", str(source_root), "merge-base", "--is-ancestor", PREPRINT_CUTOFF_COMMIT, LEGACY_HEAD_COMMIT],
            check=False,
        ).returncode
        == 0,
        "paper_mechanism_files": len(git_tree_files(source_root, PAPER_MECHANISM_COMMIT)),
        "paper_mechanism_python_files": sum(
            path.endswith(".py") for path in git_tree_files(source_root, PAPER_MECHANISM_COMMIT)
        ),
        "paper_mechanism_factor_csvs": sum(
            path.startswith("factor_zoo/") and path.endswith(".csv")
            for path in git_tree_files(source_root, PAPER_MECHANISM_COMMIT)
        ),
        "preprint_cutoff_factor_csvs": sum(
            path.startswith("factor_zoo/") and path.endswith(".csv")
            for path in git_tree_files(source_root, PREPRINT_CUTOFF_COMMIT)
        ),
    }
    expected: dict[str, Any] = {
        "is_shallow": False,
        "reachable_commits": 493,
        "current_main_commits": 8,
        "legacy_main_commits": 485,
        "root_commits": sorted([SOURCE_FIRST_COMMIT, LEGACY_ROOT_COMMIT]),
        "current_and_legacy_have_common_ancestor": False,
        "paper_mechanism_is_legacy_ancestor": True,
        "preprint_cutoff_is_legacy_ancestor": True,
        "paper_mechanism_files": 856,
        "paper_mechanism_python_files": 331,
        "paper_mechanism_factor_csvs": 15,
        "preprint_cutoff_factor_csvs": 0,
    }
    if facts != expected:
        raise RuntimeError(f"Pinned two-root Git history changed: {facts!r}")

    timeline = [
        (LEGACY_ROOT_COMMIT, "legacy history begins"),
        (ALPHAAGENT_INTRO_COMMIT, "AlphaAgent workflow first appears"),
        (PAPER_MECHANISM_COMMIT, "mechanism-complete snapshot pinned for component audit"),
        (LATEST_FULL_TREE_PREPRINT_COMMIT, "latest full tree before cleanup; Alpha101 path is regressed"),
        (PREPRINT_CUTOFF_COMMIT, "latest commit before arXiv v1; factor_zoo removed"),
        (LEGACY_HEAD_COMMIT, "public legacy-main head"),
        (SOURCE_FIRST_COMMIT, "disjoint rewritten main begins"),
        (SOURCE_COMMIT, "pinned rewritten main head"),
    ]
    rows = []
    for commit, role in timeline:
        item = git_commit_record(source_root, commit)
        rows.append({**item, "role": role})
    return facts, rows


def git_first_commit(root: Path) -> tuple[str, str]:
    output = subprocess.run(
        ["git", "-C", str(root), "log", "--reverse", "--format=%H|%aI"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    commit, date = output[0].split("|", 1)
    return commit, date


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _source_tree_facts(root: Path) -> tuple[int, int, str]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    records = [
        f"{path.relative_to(root).as_posix()}\t{path.stat().st_size}\t{sha256(path)}\n"
        for path in files
    ]
    return (
        len(files),
        sum(path.stat().st_size for path in files),
        hashlib.sha256("".join(records).encode()).hexdigest(),
    )


def _extract_official_source(archive_path: Path, destination: Path) -> None:
    with tarfile.open(archive_path, "r:*") as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(f"Unsafe paper-source archive member: {member.name}")
            if not (member.isfile() or member.isdir()):
                raise RuntimeError(
                    f"Unsupported paper-source archive member type: {member.name}"
                )
        try:
            archive.extractall(destination, filter="fully_trusted")
        except TypeError:  # pragma: no cover - Python versions before filter support
            archive.extractall(destination)


def _active_latex(source: str) -> str:
    return "\n".join(
        re.split(r"(?<!\\)%", line, maxsplit=1)[0] for line in source.splitlines()
    )


def _paper_table_2_values(main_tex: Path) -> list[float]:
    active = _active_latex(main_tex.read_text(encoding="utf-8", errors="replace"))
    blocks = re.findall(r"\\begin\{table\*\}.*?\\end\{table\*\}", active, re.S)
    performance = [block for block in blocks if r"\label{tab:performance}" in block]
    if len(performance) != 1:
        raise RuntimeError(
            f"Expected one active performance table in {main_tex}, got {len(performance)}"
        )
    body = performance[0].split(r"\midrule", 1)[1].split(r"\bottomrule", 1)[0]
    values: list[float] = []
    for line in body.splitlines():
        if "&" not in line or not line.rstrip().endswith(r"\\"):
            continue
        cells = line.split("&")[1:]
        if len(cells) != 10:
            raise RuntimeError(f"Malformed active performance row in {main_tex}: {line}")
        for cell in cells:
            numbers = re.findall(r"-?\d+(?:\.\d+)?", cell)
            if len(numbers) != 1:
                raise RuntimeError(
                    f"Expected one numeric display value in {main_tex}: {cell!r}"
                )
            values.append(float(numbers[0]))
    if len(values) != 100:
        raise RuntimeError(f"Expected 100 Table 2 result cells in {main_tex}, got {len(values)}")
    return values


def _resolve_casefold_path(root: Path, declared: str) -> Path:
    current = root
    for part in Path(declared).parts:
        exact = current / part
        if exact.exists():
            current = exact
            continue
        matches = [item for item in current.iterdir() if item.name.casefold() == part.casefold()]
        if len(matches) != 1:
            raise RuntimeError(f"Cannot resolve paper figure {declared!r} below {root}")
        current = matches[0]
    return current


def _figure_logical_id(declared: str) -> str:
    stem = Path(declared).stem.casefold()
    if stem == "overview":
        return "workflow_overview"
    if stem == "ast":
        return "ast_originality_example"
    if stem.startswith("ex_return"):
        return "cumulative_excess_returns"
    if stem.startswith("yearly_ic_ric"):
        return "yearly_ic_rankic_csi500"
    if stem.startswith("ic_std"):
        return "five_round_ic_evolution"
    if stem == "hit_ratio_comparison":
        return "hit_ratio_development_token_efficiency"
    if stem == "llm_performance_radar_charts":
        return "base_llm_performance_radar"
    raise RuntimeError(f"Unclassified active AlphaAgent paper figure: {declared}")


def _paper_figure_assets(version: str, source_root: Path, main_tex: Path) -> list[dict[str, Any]]:
    active = _active_latex(main_tex.read_text(encoding="utf-8", errors="replace"))
    includes: list[str] = []
    for block in re.findall(r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}", active, re.S):
        paths = re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", block)
        if len(paths) != 1:
            raise RuntimeError(f"Expected one source asset per active figure in {main_tex}")
        includes.extend(paths)
    rows = []
    for display_index, declared in enumerate(includes, start=1):
        resolved = _resolve_casefold_path(source_root, declared)
        rows.append(
            {
                "paper_version": version,
                "display_index": display_index,
                "logical_figure_id": _figure_logical_id(declared),
                "declared_path": declared,
                "archive_path": resolved.relative_to(source_root).as_posix(),
                "source_asset_sha256": sha256(resolved),
                "source_asset_bytes": resolved.stat().st_size,
                "lineage_status": "",
                "paper_result_credit": False,
            }
        )
    return rows


def _pdf_pages(pdf_path: Path) -> int:
    output = subprocess.run(
        ["pdfinfo", str(pdf_path)], check=True, capture_output=True, text=True
    ).stdout
    match = re.search(r"^Pages:\s+(\d+)$", output, re.M)
    if not match:
        raise RuntimeError(f"pdfinfo did not report a page count for {pdf_path}")
    return int(match.group(1))


def _compile_paper_source(source_root: Path, main_tex: str, latex_command: str) -> dict[str, Any]:
    logs = []
    for pass_number in (1, 2):
        completed = subprocess.run(
            [latex_command, "-interaction=nonstopmode", "-halt-on-error", main_tex],
            cwd=source_root,
            capture_output=True,
            text=True,
        )
        logs.append(completed.stdout + completed.stderr)
        if completed.returncode:
            tail = "\n".join(logs[-1].splitlines()[-30:])
            raise RuntimeError(
                f"Paper-source compilation failed on pass {pass_number} for {main_tex}:\n{tail}"
            )
    compiled_pdf = source_root / f"{Path(main_tex).stem}.pdf"
    return {
        "compile_passes": 2,
        "compiled_pdf_pages": _pdf_pages(compiled_pdf),
        "compiled_pdf_bytes": compiled_pdf.stat().st_size,
        "undefined_reference_warnings_after_pass_2": sum(
            "undefined" in line.casefold() for line in logs[-1].splitlines()
        ),
        "paper_result_credit": False,
    }


def official_paper_version_rows(
    paper_versions_root: Path, source_root: Path, latex_command: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    version_rows: list[dict[str, Any]] = []
    numeric_by_version: dict[str, list[dict[str, Any]]] = {}
    figure_rows: list[dict[str, Any]] = []
    for version, expected in PAPER_VERSIONS.items():
        pdf_path = paper_versions_root / f"paper_{version}.pdf"
        archive_path = paper_versions_root / f"paper_{version}_source.tar.gz"
        if sha256(pdf_path) != expected["pdf_sha256"] or pdf_path.stat().st_size != expected["pdf_bytes"]:
            raise RuntimeError(f"Pinned official {version} PDF changed")
        if (
            sha256(archive_path) != expected["source_sha256"]
            or archive_path.stat().st_size != expected["source_bytes"]
        ):
            raise RuntimeError(f"Pinned official {version} source archive changed")
        if _pdf_pages(pdf_path) != expected["pdf_pages"]:
            raise RuntimeError(f"Pinned official {version} PDF page count changed")
        with tempfile.TemporaryDirectory(prefix=f"alphaagent-paper-{version}-") as temp_dir:
            extracted = Path(temp_dir)
            _extract_official_source(archive_path, extracted)
            file_count, uncompressed_bytes, tree_sha256 = _source_tree_facts(extracted)
            observed_tree = (file_count, uncompressed_bytes, tree_sha256)
            expected_tree = (
                expected["source_files"],
                expected["source_uncompressed_bytes"],
                expected["source_tree_sha256"],
            )
            if observed_tree != expected_tree:
                raise RuntimeError(
                    f"Pinned official {version} source tree changed: {observed_tree!r}"
                )
            expected_numeric = paper_numeric_rows(version)
            parsed_table_2 = _paper_table_2_values(extracted / expected["main_tex"])
            expected_table_2 = [
                row["paper_value"] for row in expected_numeric if row["paper_table"] == 2
            ]
            if parsed_table_2 != expected_table_2:
                raise RuntimeError(f"Official {version} Table 2 parser disagrees with the ledger")
            figures = _paper_figure_assets(
                version, extracted, extracted / expected["main_tex"]
            )
            compilation = _compile_paper_source(
                extracted, expected["main_tex"], latex_command
            )
        cutoff = expected["source_cutoff_commit"]
        observed_commit_count = int(
            git_output(
                source_root,
                "rev-list",
                *OFFICIAL_HEADS,
                f"--before={expected['submitted_at']}",
                "--count",
            )
        )
        observed_cutoff = git_output(
            source_root,
            "rev-list",
            *OFFICIAL_HEADS,
            f"--before={expected['submitted_at']}",
            "-1",
        )
        if (
            observed_commit_count != expected["source_commits_at_submission"]
            or observed_cutoff != cutoff
        ):
            raise RuntimeError(
                f"Official source-at-submission boundary changed for {version}"
            )
        cutoff_files = git_tree_files(source_root, cutoff)
        cutoff_runs = {
            path.split("/", 2)[1]
            for path in cutoff_files
            if path.startswith("saved_mlruns/") and len(path.split("/", 2)) > 1
        }
        cutoff_factor_files = [path for path in cutoff_files if path.startswith("factor_zoo/")]
        if (
            len(cutoff_files) != expected["source_cutoff_tracked_files"]
            or cutoff_runs
            or cutoff_factor_files
        ):
            raise RuntimeError(
                f"Pinned source-at-submission tree changed for {version}"
            )
        version_rows.append(
            {
                "paper_version": version,
                "submitted_at": expected["submitted_at"],
                "pdf_url": expected["pdf_url"],
                "pdf_sha256": expected["pdf_sha256"],
                "pdf_bytes": expected["pdf_bytes"],
                "pdf_pages": expected["pdf_pages"],
                "source_url": expected["source_url"],
                "source_sha256": expected["source_sha256"],
                "source_archive_bytes": expected["source_bytes"],
                "source_files": expected["source_files"],
                "source_uncompressed_bytes": expected["source_uncompressed_bytes"],
                "source_tree_sha256": expected["source_tree_sha256"],
                "main_tex": expected["main_tex"],
                "numeric_table_cells": len(expected_numeric),
                "numeric_result_cells": sum(row["cell_role"] == "result" for row in expected_numeric),
                "numeric_configuration_cells": sum(
                    row["cell_role"] == "configuration" for row in expected_numeric
                ),
                "active_figure_assets": len(figures),
                "compile_passes": compilation["compile_passes"],
                "compiled_pdf_pages": compilation["compiled_pdf_pages"],
                "undefined_reference_warnings_after_pass_2": compilation[
                    "undefined_reference_warnings_after_pass_2"
                ],
                "source_commits_at_submission": expected[
                    "source_commits_at_submission"
                ],
                "source_cutoff_commit": cutoff,
                "source_cutoff_date": expected["source_cutoff_date"],
                "source_cutoff_tracked_files": len(cutoff_files),
                "source_cutoff_native_run_records": len(cutoff_runs),
                "source_cutoff_factor_zoo_files": len(cutoff_factor_files),
                "paper_document_reproduced": (
                    compilation["compiled_pdf_pages"] == expected["pdf_pages"]
                ),
                "paper_experiment_reproduced": False,
            }
        )
        numeric_by_version[version] = expected_numeric
        figure_rows.extend(figures)

    lineage_rows = []
    v1 = {
        (row["paper_table"], row["entity"], row["market"], row["metric"]): row
        for row in numeric_by_version["v1"]
    }
    v2 = {
        (row["paper_table"], row["entity"], row["market"], row["metric"]): row
        for row in numeric_by_version["v2"]
    }
    if set(v1) != set(v2) or len(v1) != 106:
        raise RuntimeError("Official AlphaAgent paper table cell identities changed")
    for key in sorted(v1, key=lambda item: tuple(str(value) for value in item)):
        old, new = v1[key], v2[key]
        if old["paper_value"] != new["paper_value"]:
            status = "numeric_value_revised_in_v2"
        elif old["period"] != new["period"]:
            status = "configuration_label_revised_in_v2"
        else:
            status = "unchanged"
        lineage_rows.append(
            {
                "display_cell_id": "|".join(str(value) for value in key),
                "paper_table": old["paper_table"],
                "cell_role": old["cell_role"],
                "entity": old["entity"],
                "market": old["market"],
                "metric": old["metric"],
                "v1_period": old["period"],
                "v1_value": old["paper_value"],
                "v2_period": new["period"],
                "v2_value": new["paper_value"],
                "status": status,
                "paper_result_credit": False,
            }
        )
    figure_groups: dict[str, list[dict[str, Any]]] = {}
    for row in figure_rows:
        figure_groups.setdefault(row["logical_figure_id"], []).append(row)
    for logical_id, rows in figure_groups.items():
        if len(rows) == 1:
            status = "added_in_v2"
        elif len({row["source_asset_sha256"] for row in rows}) == 1:
            status = "byte_identical"
        else:
            status = "source_asset_revised_in_v2"
        for row in rows:
            row["lineage_status"] = status
    if Counter(row["status"] for row in lineage_rows) != {
        "unchanged": 99,
        "numeric_value_revised_in_v2": 5,
        "configuration_label_revised_in_v2": 2,
    }:
        raise RuntimeError("Official AlphaAgent paper numeric lineage changed")
    if Counter(
        rows[0]["lineage_status"] for rows in figure_groups.values()
    ) != {
        "byte_identical": 3,
        "source_asset_revised_in_v2": 3,
        "added_in_v2": 1,
    }:
        raise RuntimeError("Official AlphaAgent paper figure lineage changed")
    return version_rows, lineage_rows, figure_rows


def _public_history_path_kind(path: str) -> str:
    if path.startswith("saved_mlruns/"):
        if "/metrics/" in path:
            return "paper_era_author_metric_scalar"
        if "/artifacts/" in path:
            return "paper_era_author_serialized_run_artifact"
        if "/params/" in path or "/tags/" in path:
            return "paper_era_author_run_metadata"
        return "paper_era_author_run_record"
    if path.startswith("factor_zoo/"):
        return "paper_era_factor_zoo_artifact"
    if path.startswith("artifacts/factorzoo/"):
        return "post_paper_rewrite_factor_artifact"
    suffix = Path(path).suffix.casefold()
    if suffix == ".py":
        return "python_source"
    if suffix in {".yaml", ".yml", ".toml", ".json", ".ini", ".cfg"}:
        return "configuration_or_metadata"
    if suffix in {".md", ".rst", ".txt"}:
        return "documentation_or_prompt"
    if suffix in {".csv", ".parquet", ".pkl", ".pickle"}:
        return "data_or_serialized_artifact"
    return "other"


def _is_primitive_paper_output_path(path: str) -> bool:
    if not path.startswith("saved_mlruns/"):
        return False
    name = Path(path).name.casefold()
    return name in {
        "pred.pkl",
        "prediction.pkl",
        "positions.pkl",
        "holdings.pkl",
        "portfolio_analysis.pkl",
        "report_normal_1day.pkl",
        "sig_analysis.pkl",
    }


def public_source_history(
    source_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    commit_sequence = git_output(
        source_root, "rev-list", "--topo-order", "--reverse", *OFFICIAL_HEADS
    ).splitlines()
    object_lines = git_output(source_root, "rev-list", "--objects", *OFFICIAL_HEADS).splitlines()
    object_ids = sorted(line.split(" ", 1)[0] for line in object_lines)
    object_types: Counter[str] = Counter()
    for offset in range(0, len(object_ids), 1000):
        batch = "".join(f"{oid}\n" for oid in object_ids[offset : offset + 1000])
        completed = subprocess.run(
            ["git", "-C", str(source_root), "cat-file", "--batch-check=%(objecttype)"],
            input=batch,
            check=True,
            capture_output=True,
            text=True,
        )
        object_types.update(completed.stdout.splitlines())
    path_output = subprocess.run(
        [
            "git",
            "-C",
            str(source_root),
            "-c",
            "core.quotePath=false",
            "log",
            "--format=",
            "--name-only",
            "--no-renames",
            *OFFICIAL_HEADS,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    paths = sorted({line for line in path_output.splitlines() if line})
    run_ids = sorted(
        {
            path.split("/", 2)[1]
            for path in paths
            if path.startswith("saved_mlruns/") and len(path.split("/", 2)) > 1
        }
    )
    path_rows = [
        {
            "path": path,
            "classification": _public_history_path_kind(path),
            "paper_era_author_run_record": path.startswith("saved_mlruns/"),
            "primitive_prediction_return_or_holding_output": _is_primitive_paper_output_path(
                path
            ),
            "paper_result_credit": False,
        }
        for path in paths
    ]
    facts = {
        "official_heads": {
            "legacy-main": LEGACY_HEAD_COMMIT,
            "main": SOURCE_COMMIT,
        },
        "official_tags": [],
        "official_releases": [],
        "public_head_discovery_sha256": PUBLIC_HEAD_DISCOVERY_SHA256,
        "public_tag_discovery_sha256": EMPTY_DISCOVERY_SHA256,
        "public_release_discovery_sha256": EMPTY_DISCOVERY_SHA256,
        "official_reachable_commits": len(commit_sequence),
        "official_commit_sequence_sha256": hashlib.sha256(
            "".join(f"{commit}\n" for commit in commit_sequence).encode()
        ).hexdigest(),
        "official_reachable_objects": len(object_ids),
        "official_object_sequence_sha256": hashlib.sha256(
            "".join(f"{oid}\n" for oid in object_ids).encode()
        ).hexdigest(),
        "official_reachable_object_types": dict(sorted(object_types.items())),
        "official_unique_historical_file_paths": len(paths),
        "official_path_sequence_sha256": hashlib.sha256(
            "".join(f"{path}\n" for path in paths).encode()
        ).hexdigest(),
        "historical_author_run_record_paths": sum(
            path.startswith("saved_mlruns/") for path in paths
        ),
        "historical_author_run_ids": run_ids,
        "primitive_prediction_return_or_holding_paths": sum(
            _is_primitive_paper_output_path(path) for path in paths
        ),
        "paper_result_credit": False,
    }
    expected = {
        "commits": 493,
        "objects": 8312,
        "types": {"blob": 3907, "commit": 493, "tree": 3912},
        "paths": 2499,
        "run_paths": 385,
        "run_ids": 7,
        "primitive_paths": 0,
    }
    observed = {
        "commits": facts["official_reachable_commits"],
        "objects": facts["official_reachable_objects"],
        "types": facts["official_reachable_object_types"],
        "paths": facts["official_unique_historical_file_paths"],
        "run_paths": facts["historical_author_run_record_paths"],
        "run_ids": len(run_ids),
        "primitive_paths": facts["primitive_prediction_return_or_holding_paths"],
    }
    if observed != expected:
        raise RuntimeError(f"Pinned official public history changed: {observed!r}")
    if facts["official_commit_sequence_sha256"] != OFFICIAL_COMMIT_SEQUENCE_SHA256:
        raise RuntimeError("Pinned official commit sequence changed")
    if facts["official_object_sequence_sha256"] != OFFICIAL_OBJECT_SEQUENCE_SHA256:
        raise RuntimeError("Pinned official object sequence changed")
    if facts["official_path_sequence_sha256"] != OFFICIAL_PATH_SEQUENCE_SHA256:
        raise RuntimeError("Pinned official historical path sequence changed")
    return path_rows, facts


def fork_default_head_audit(
    source_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Audit the bounded current fork-default-head census without promoting forks.

    The 2026-08-14 GitHub GraphQL census contained 71 default branches grouped
    into six unique heads. Sixty-seven point exactly at one of the two official
    heads. The four divergent tips are locally object-pinned and checked below.
    """
    rows: list[dict[str, Any]] = []
    for group in FORK_DEFAULT_HEAD_GROUPS:
        tip = str(group["tip_commit"])
        base = str(group["base_commit"])
        if tip == base:
            commits_ahead = changed_paths = added_paths = 0
        else:
            merge_base = git_output(source_root, "merge-base", base, tip)
            if merge_base != base:
                raise RuntimeError(
                    f"Fork tip {tip} no longer descends from pinned base {base}"
                )
            commits_ahead = int(
                git_output(source_root, "rev-list", "--count", f"{base}..{tip}")
            )
            changed_paths = len(
                git_output(source_root, "diff", "--name-only", base, tip).splitlines()
            )
            added_paths = len(
                git_output(
                    source_root,
                    "diff",
                    "--diff-filter=A",
                    "--name-only",
                    base,
                    tip,
                ).splitlines()
            )
        observed = (commits_ahead, changed_paths, added_paths)
        expected = (
            int(group["expected_commits_ahead"]),
            int(group["expected_changed_paths"]),
            int(group["expected_added_paths"]),
        )
        if observed != expected:
            raise RuntimeError(
                f"Pinned fork surface changed for {group['group_id']}: {observed} != {expected}"
            )
        rows.append(
            {
                "discovery_date": FORK_DISCOVERY_DATE,
                "group_id": group["group_id"],
                "repository": group["repository"],
                "repository_count": group["repository_count"],
                "default_head_commit": tip,
                "base_commit": base,
                "commits_ahead_of_base": commits_ahead,
                "changed_paths_from_base": changed_paths,
                "added_paths_from_base": added_paths,
                "candidate_data_or_result_paths": group["candidate_paths"],
                "classification": group["classification"],
                "additional_attributable_author_native_artifact": False,
                "paper_result_units_regenerated": 0,
                "paper_result_credit": False,
            }
        )
    if sum(int(row["repository_count"]) for row in rows) != FORK_DEFAULT_HEAD_TOTAL:
        raise RuntimeError("Pinned fork-default-head denominator changed")
    if sum(row["default_head_commit"] not in OFFICIAL_HEADS for row in rows) != 4:
        raise RuntimeError("Pinned divergent fork-head group count changed")
    return rows, fork_data_bundle_audit(source_root)


def fork_data_bundle_audit(source_root: Path) -> dict[str, Any]:
    """Inspect the sole fork default head that ships a market-data candidate."""
    zip_blob = _git_blob(source_root, FORK_DATA_TIP, "data/us_data.zip")
    observed_zip_sha = hashlib.sha256(zip_blob).hexdigest()
    if observed_zip_sha != FORK_DATA_ZIP_SHA256:
        raise RuntimeError(
            f"Pinned independent fork data ZIP changed: {observed_zip_sha}"
        )
    with zipfile.ZipFile(io.BytesIO(zip_blob)) as archive:
        infos = archive.infolist()
        calendar = archive.read("calendars/day.txt").decode().splitlines()
        sp500_rows = [
            line.split("\t")
            for line in archive.read("instruments/sp500.txt").decode().splitlines()
            if line
        ]
        all_rows = [
            line.split("\t")
            for line in archive.read("instruments/all.txt").decode().splitlines()
            if line
        ]
        feature_symbols = {
            name.split("/", 2)[1]
            for name in archive.namelist()
            if name.startswith("features/") and name.count("/") >= 2
        }
        uncompressed_bytes = sum(info.file_size for info in infos)
    finite_membership_rows = sum(row[2] != "2099-12-31" for row in sp500_rows)
    paper_pdf = _git_blob(source_root, FORK_DATA_TIP, "alphaagent-paper.pdf")
    data_guide = _git_blob(source_root, FORK_DATA_TIP, "DATA.md").decode()
    hypothesis = _git_blob(source_root, FORK_DATA_TIP, "hypothesis.md").decode()
    observed = {
        "zip_entries": len(infos),
        "zip_uncompressed_bytes": uncompressed_bytes,
        "calendar_rows": len(calendar),
        "calendar_start": calendar[0],
        "calendar_end": calendar[-1],
        "feature_symbols": len(feature_symbols),
        "sp500_membership_rows": len(sp500_rows),
        "sp500_rows_with_finite_membership_end": finite_membership_rows,
        "all_instrument_rows": len(all_rows),
    }
    expected = {
        "zip_entries": 3980,
        "zip_uncompressed_bytes": 23945945,
        "calendar_rows": 1533,
        "calendar_start": "2020-01-02",
        "calendar_end": "2026-02-06",
        "feature_symbols": 568,
        "sp500_membership_rows": 568,
        "sp500_rows_with_finite_membership_end": 1,
        "all_instrument_rows": 568,
    }
    if observed != expected:
        raise RuntimeError(f"Pinned independent fork data census changed: {observed!r}")
    for marker in (
        "survivorship-bias-free S&P 500 dataset",
        "approximately 600 symbols",
        "2020-2026",
    ):
        if marker not in data_guide:
            raise RuntimeError(f"Pinned fork data-guide marker changed: {marker}")
    for marker in (
        "Mining Results (step_n=5, run 2026-02-09)",
        "11.0785",
        "spurious (data leak / look-ahead bias)",
    ):
        if marker not in hypothesis:
            raise RuntimeError(f"Pinned fork hypothesis marker changed: {marker}")
    if hashlib.sha256(paper_pdf).hexdigest() != PAPER_SHA256:
        raise RuntimeError("Fork paper copy no longer matches official arXiv v2 PDF")
    return {
        "discovery_date": FORK_DISCOVERY_DATE,
        "repository": FORK_DATA_REPOSITORY,
        "tip_commit": FORK_DATA_TIP,
        "official_repository_artifact": False,
        "attributable_to_paper_authors": False,
        "branched_after_official_legacy_head": True,
        "bundled_paper_copy_sha256": PAPER_SHA256,
        "bundled_paper_copy_matches_official_v2": True,
        "data_zip_sha256": FORK_DATA_ZIP_SHA256,
        "data_zip_bytes": len(zip_blob),
        **observed,
        "data_guide_claims_survivorship_bias_free": True,
        "archive_membership_file_supports_claim": False,
        "paper_training_start_2015_covered": False,
        "paper_exact_yahoo_snapshot_or_transform_lineage_recovered": False,
        "new_hypothesis_summary_date": "2026-02-09",
        "new_hypothesis_summary_flags_1100pct_return_as_lookahead": True,
        "new_hypothesis_raw_prediction_return_or_holding_arrays_shipped": False,
        "paper_result_units_regenerated": 0,
        "paper_result_credit": False,
        "interpretation": (
            "This independent post-paper fork ships a new 2020-2026 Qlib bundle and a "
            "2026 mining summary, not the paper experiment. Its sp500.txt has only one "
            "finite membership end across 568 rows despite the survivorship-bias-free "
            "label, and the calendar omits the paper's 2015-2019 training period."
        ),
    }


def paper_numeric_rows(paper_version: str = "v2") -> list[dict[str, Any]]:
    if paper_version not in PAPER_VERSIONS:
        raise ValueError(f"Unknown AlphaAgent paper version: {paper_version}")
    dataset_splits = DATASET_SPLITS_V1 if paper_version == "v1" else DATASET_SPLITS
    table_2_text = TABLE_2_V1_TEXT if paper_version == "v1" else TABLE_2_TEXT
    rows: list[dict[str, Any]] = []
    for market, split, start, end, days in dataset_splits:
        rows.append(
            {
                "paper_table": 1,
                "entity": split,
                "market": market,
                "period": f"{start} to {end}",
                "metric": "trading_days",
                "paper_value": float(days),
                "cell_role": "configuration",
            }
        )
    for line in table_2_text.strip().splitlines():
        method, *values = line.split("|")
        if len(values) != 10:
            raise RuntimeError(f"Malformed Table 2 row: {line}")
        for market, part in zip(("CSI500", "S&P500"), (values[:5], values[5:])):
            for metric, value in zip(METRICS, part):
                rows.append(
                    {
                        "paper_table": 2,
                        "entity": method,
                        "market": market,
                        "period": "2021-01-01 to 2024-12-31",
                        "metric": metric,
                        "paper_value": float(value),
                        "cell_role": "result",
                    }
                )
    if Counter(row["paper_table"] for row in rows) != {1: 6, 2: 100}:
        raise RuntimeError("Paper numeric-cell denominator changed")
    if Counter(row["cell_role"] for row in rows) != {
        "result": 100,
        "configuration": 6,
    }:
        raise RuntimeError("Paper result/configuration boundary changed")
    return rows


def table_conformance() -> list[dict[str, Any]]:
    rows = []
    for row in paper_numeric_rows():
        if row["cell_role"] == "result":
            status = "unavailable_missing_native_paper_result_path"
            reason = (
                "paper-era source, factor expressions, and seven partial Qlib/MLflow records "
                "survive in Git history, but this cell has no full-period exact author-record "
                "match and no prediction, holding, return, or baseline output survives"
            )
        else:
            status = "paper_configuration_recovered_without_frozen_dataset"
            reason = (
                "preprint-era Qlib configs recover the market/split protocol, but the exact "
                "Baostock/Yahoo panels and their trading-day calendars are not shipped"
            )
        rows.append(
            {
                **row,
                "native_reproduced_value": "",
                "absolute_difference": "",
                "status": status,
                "reason": reason,
            }
        )
    return rows


def _git_blob(source_root: Path, commit: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(source_root), "show", f"{commit}:{relative}"],
        check=True,
        capture_output=True,
    ).stdout


def _mlflow_value(source_root: Path, run_id: str, relative: str) -> str:
    text = _git_blob(
        source_root,
        PAPER_MECHANISM_COMMIT,
        f"saved_mlruns/{run_id}/{relative}",
    ).decode()
    parts = text.split()
    if relative.startswith("metrics/"):
        if len(parts) != 3:
            raise RuntimeError(f"Malformed MLflow metric {run_id}/{relative}: {text!r}")
        return parts[1]
    return text


def _pickle_string_values(blob: bytes) -> list[str]:
    return [
        argument
        for _opcode, argument, _position in pickletools.genops(blob)
        if isinstance(argument, str)
    ]


def paper_era_run_records(source_root: Path) -> list[dict[str, Any]]:
    """Recover and classify the seven extensionless Qlib/MLflow records.

    The author committed the record directories on 2025-02-12 and removed them
    at the preprint-cutoff commit.  They ship metrics, full task/config pickles,
    and fitted LightGBM state, but not prediction, return, position, or input
    data objects.  Consequently they corroborate displayed cells but are not an
    independently regenerated experiment.
    """
    observed_tree = git_output(
        source_root, "rev-parse", f"{PAPER_MECHANISM_COMMIT}:saved_mlruns"
    )
    if observed_tree != PAPER_RUN_RECORD_TREE:
        raise RuntimeError(f"Pinned MLflow record tree changed: {observed_tree}")
    run_ids = git_output(
        source_root, "ls-tree", "--name-only", f"{PAPER_MECHANISM_COMMIT}:saved_mlruns"
    ).splitlines()
    if len(run_ids) != 7:
        raise RuntimeError(f"Expected seven paper-era MLflow runs, found {len(run_ids)}")

    paper = {
        (row["market"], row["metric"]): float(row["paper_value"])
        for row in paper_numeric_rows()
        if row["cell_role"] == "result" and row["entity"] == "AlphaAgent"
    }
    metric_paths = {
        "IC": "metrics/IC",
        "ICIR": "metrics/ICIR",
        "AR_pct": "metrics/1day.excess_return_with_cost.annualized_return",
        "IR": "metrics/1day.excess_return_with_cost.information_ratio",
        "MDD_pct": "metrics/1day.excess_return_with_cost.max_drawdown",
    }
    rows: list[dict[str, Any]] = []
    for run_id in run_ids:
        market_raw = _mlflow_value(
            source_root, run_id, "params/dataset.kwargs.handler.kwargs.instruments"
        )
        market_map = {"SP500": "S&P500", "csi500": "CSI500"}
        if market_raw not in market_map:
            raise RuntimeError(
                f"Unexpected instrument universe in run {run_id}: {market_raw!r}"
            )
        market = market_map[market_raw]
        test_segment = _mlflow_value(
            source_root, run_id, "params/dataset.kwargs.segments.test"
        )
        command = _mlflow_value(source_root, run_id, "params/cmd-sys.argv")
        start_ms = int(
            next(
                line.split(":", 1)[1].strip()
                for line in _mlflow_value(source_root, run_id, "meta.yaml").splitlines()
                if line.startswith("start_time:")
            )
        )
        config_blob = _git_blob(
            source_root, PAPER_MECHANISM_COMMIT, f"saved_mlruns/{run_id}/artifacts/config"
        )
        dataset_blob = _git_blob(
            source_root, PAPER_MECHANISM_COMMIT, f"saved_mlruns/{run_id}/artifacts/dataset"
        )
        task_blob = _git_blob(
            source_root, PAPER_MECHANISM_COMMIT, f"saved_mlruns/{run_id}/artifacts/task"
        )
        strings = _pickle_string_values(config_blob)
        model_states = [value for value in strings if value.startswith("tree\nversion=")]
        if len(model_states) != 1:
            raise RuntimeError(f"Expected one fitted LightGBM state in run {run_id}")
        feature_line = next(
            line for line in model_states[0].splitlines() if line.startswith("feature_names=")
        )
        feature_count = len(feature_line.removeprefix("feature_names=").split())
        expected_full_segments = {
            "S&P500": "[datetime.date(2021, 1, 1), datetime.date(2024, 12, 31)]",
            "CSI500": "[datetime.date(2021, 1, 1), datetime.date(2024, 12, 30)]",
        }
        full_period = test_segment == expected_full_segments[market]
        run_file_count = len(
            git_output(
                source_root,
                "ls-tree",
                "-r",
                "--name-only",
                f"{PAPER_MECHANISM_COMMIT}:saved_mlruns/{run_id}",
            ).splitlines()
        )
        values: dict[str, float] = {}
        matches: dict[str, bool] = {}
        for metric, path in metric_paths.items():
            value = float(_mlflow_value(source_root, run_id, path))
            if metric in {"AR_pct", "MDD_pct"}:
                value *= 100.0
            values[metric] = value
            decimals = {
                "IC": 4,
                "ICIR": 4,
                "AR_pct": 2,
                "IR": 4,
                "MDD_pct": 2,
            }[metric]
            matches[metric] = round(value, decimals) == round(paper[(market, metric)], decimals)
        matched = sum(matches.values()) if full_period else 0
        rows.append(
            {
                "run_id": run_id,
                "run_started_utc_ms": start_ms,
                "market": market,
                "test_segment": test_segment,
                "command": command,
                "tracked_files": run_file_count,
                "input_features": feature_count,
                "generated_factor_features": feature_count - 4,
                "config_sha256": hashlib.sha256(config_blob).hexdigest(),
                "dataset_sha256": hashlib.sha256(dataset_blob).hexdigest(),
                "task_sha256": hashlib.sha256(task_blob).hexdigest(),
                "fitted_lightgbm_state_sha256": hashlib.sha256(
                    model_states[0].encode("utf-8")
                ).hexdigest(),
                "ic": values["IC"],
                "icir": values["ICIR"],
                "annualized_return_pct": values["AR_pct"],
                "information_ratio": values["IR"],
                "max_drawdown_pct": values["MDD_pct"],
                "full_paper_period": full_period,
                "display_cells_matching_alphaagent_row": matched,
                "all_five_display_cells_match": matched == 5,
                "paper_result_cells_corroborated": 5 if matched == 5 else 0,
                "fitted_lightgbm_state_shipped": True,
                "predictions_returns_holdings_shipped": False,
                "paper_result_credit_kind": (
                    "author_history_native_run_artifact_exact_display_match"
                    if matched == 5
                    else "author_history_run_artifact_no_complete_display_match"
                ),
            }
        )
    if Counter(row["market"] for row in rows) != {"S&P500": 4, "CSI500": 3}:
        raise RuntimeError("Pinned MLflow market census changed")
    if sum(int(row["tracked_files"]) for row in rows) != 385:
        raise RuntimeError("Pinned MLflow file census changed")
    if [row["run_id"] for row in rows if row["all_five_display_cells_match"]] != [
        "77b227f86e5a47bab48178cac409a98b"
    ]:
        raise RuntimeError("Pinned AlphaAgent Table 2 MLflow correspondence changed")
    return rows


def paper_era_run_input_audit(
    source_root: Path,
    qlib_source_root: Path,
    qlib_data_archive: Path,
    run_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Test whether the matching author run can be replayed from released inputs.

    This deliberately separates an executable fitted model and matching scalar
    record from a regeneration. It audits both candidate-factor chronology and
    the exact Qlib downloader/data route pinned by the paper-era Dockerfile.
    """
    records = list(run_records or paper_era_run_records(source_root))
    matching = next(row for row in records if row["run_id"] == MATCHING_RUN_ID)
    if (
        int(matching["run_started_utc_ms"]) != 1_738_043_624_771
        or int(matching["generated_factor_features"]) != 5
    ):
        raise RuntimeError("Matching AlphaAgent run identity changed")

    run_head = git_output(
        source_root,
        "rev-list",
        PAPER_MECHANISM_COMMIT,
        f"--before={MATCHING_RUN_STARTED_UTC}",
        "--max-count=1",
    )
    if run_head != RUN_TIME_PUBLIC_HEAD:
        raise RuntimeError(f"Public head at matching-run time changed: {run_head}")

    def factor_rows(commit: str, path: str) -> list[dict[str, str]]:
        payload = _git_blob(source_root, commit, path).decode("utf-8")
        return list(csv.DictReader(io.StringIO(payload)))

    run_time_factors = factor_rows(RUN_TIME_PUBLIC_HEAD, RUN_TIME_US_FACTOR_PATH)
    paper_snapshot_factors = factor_rows(PAPER_MECHANISM_COMMIT, PAPER_ERA_US_FACTOR_PATH)
    if len(run_time_factors) != 4 or len(paper_snapshot_factors) != 6:
        raise RuntimeError("Pinned US factor-candidate chronology changed")
    run_time_expressions = {row["factor_expression"] for row in run_time_factors}
    later_factor_names = [
        row["factor_name"]
        for row in paper_snapshot_factors
        if row["factor_expression"] not in run_time_expressions
    ]
    if later_factor_names != [
        "5D_VolumeSpike_Confirmation6",
        "Stable_MeanReversion_10D",
    ]:
        raise RuntimeError(f"Post-run factor additions changed: {later_factor_names}")
    object_paths = [
        line.split(" ", 1)[1]
        for line in git_output(source_root, "rev-list", "--objects", "--all").splitlines()
        if " " in line
    ]
    combined_paths = [
        path for path in object_paths if path.endswith("combined_factors_df.pkl")
    ]
    if combined_paths:
        raise RuntimeError(f"A combined factor input unexpectedly exists: {combined_paths}")

    downloader_blob = _git_blob(
        qlib_source_root, QLIB_SOURCE_COMMIT, "qlib/tests/data.py"
    )
    if sha256_bytes(downloader_blob) != QLIB_DATA_DOWNLOADER_SHA256:
        raise RuntimeError("Pinned paper-era Qlib downloader changed")
    downloader_text = downloader_blob.decode("utf-8")
    required_downloader_fragments = (
        'REMOTE_URL = "https://github.com/SunsetWolf/qlib_dataset/releases/download"',
        'dataset_version = "v2" if dataset_version is None else dataset_version',
        '_get_file_name_with_version("latest", dataset_version=version)',
    )
    if not all(fragment in downloader_text for fragment in required_downloader_fragments):
        raise RuntimeError("Paper-era Qlib downloader fallback semantics changed")

    if qlib_data_archive.stat().st_size != QLIB_US_DATA_ARCHIVE_BYTES:
        raise RuntimeError("Pinned Qlib US archive size changed")
    if sha256(qlib_data_archive) != QLIB_US_DATA_ARCHIVE_SHA256:
        raise RuntimeError("Pinned Qlib US archive hash changed")
    with zipfile.ZipFile(qlib_data_archive) as archive:
        names = archive.namelist()
        calendars = archive.read("calendars/day.txt").decode().splitlines()
        sp500_rows = archive.read("instruments/sp500.txt").decode().splitlines()
        feature_symbols = {
            name.split("/")[1]
            for name in names
            if name.startswith("features/")
            and name.count("/") >= 2
            and name.split("/")[1]
        }
    if (
        len(names) != 71_959
        or len(calendars) != 5_250
        or calendars[0] != "1999-12-31"
        or calendars[-1] != "2020-11-10"
        or len(sp500_rows) != 755
        or len(feature_symbols) != 8_994
    ):
        raise RuntimeError("Pinned Qlib US archive contents changed")

    return {
        "matching_run_id": MATCHING_RUN_ID,
        "matching_run_started_utc": MATCHING_RUN_STARTED_UTC,
        "matching_run_generated_factor_features": 5,
        "public_head_at_run_time": RUN_TIME_PUBLIC_HEAD,
        "public_head_at_run_time_committed_at": git_output(
            source_root, "show", "-s", "--format=%cI", RUN_TIME_PUBLIC_HEAD
        ),
        "run_time_public_us_factor_candidate_path": RUN_TIME_US_FACTOR_PATH,
        "run_time_public_us_factor_candidate_rows": len(run_time_factors),
        "paper_snapshot_us_factor_candidate_path": PAPER_ERA_US_FACTOR_PATH,
        "paper_snapshot_us_factor_candidate_rows": len(paper_snapshot_factors),
        "factor_candidates_added_after_run": later_factor_names,
        "run_time_candidate_file_matches_model_generated_feature_count": False,
        "combined_factors_df_ever_tracked": False,
        "exact_generated_factor_lineage_recovered": False,
        "qlib_source_commit": QLIB_SOURCE_COMMIT,
        "qlib_data_downloader_path": "qlib/tests/data.py",
        "qlib_data_downloader_sha256": QLIB_DATA_DOWNLOADER_SHA256,
        "qlib_data_versioned_url": QLIB_US_VERSIONED_DATA_URL,
        "qlib_data_versioned_url_available_when_observed": False,
        "qlib_data_fallback_url": QLIB_US_FALLBACK_DATA_URL,
        "qlib_data_fallback_asset_last_modified_utc": QLIB_US_DATA_ASSET_LAST_MODIFIED_UTC,
        "qlib_data_observed_on": QLIB_US_DATA_OBSERVED_ON,
        "qlib_data_archive_bytes": QLIB_US_DATA_ARCHIVE_BYTES,
        "qlib_data_archive_sha256": QLIB_US_DATA_ARCHIVE_SHA256,
        "qlib_data_zip_entries": len(names),
        "qlib_data_calendar_rows": len(calendars),
        "qlib_data_calendar_start": calendars[0],
        "qlib_data_calendar_end": calendars[-1],
        "qlib_data_sp500_membership_rows": len(sp500_rows),
        "qlib_data_feature_symbols": len(feature_symbols),
        "qlib_data_has_spx_feature": "spx" in feature_symbols,
        "qlib_data_has_gspc_feature": "^gspc" in feature_symbols,
        "paper_training_period_covered": True,
        "paper_validation_period_fully_covered": False,
        "paper_test_period_covered": False,
        "matching_run_benchmark_available": False,
        "matching_run_replayable_from_released_inputs": False,
        "native_backtests_reexecuted": 0,
        "paper_result_credit": False,
        "status": "released_downloader_archive_and_factor_history_cannot_replay_matching_run",
    }


def apply_run_record_conformance(
    table_rows: list[dict[str, Any]], run_rows: Sequence[Mapping[str, Any]]
) -> None:
    matching = next(row for row in run_rows if row["all_five_display_cells_match"])
    values = {
        "IC": matching["ic"],
        "ICIR": matching["icir"],
        "AR_pct": matching["annualized_return_pct"],
        "IR": matching["information_ratio"],
        "MDD_pct": matching["max_drawdown_pct"],
    }
    for row in table_rows:
        if row["entity"] == "AlphaAgent" and row["market"] == "S&P500":
            row["native_reproduced_value"] = values[row["metric"]]
            row["absolute_difference"] = abs(
                float(row["paper_value"]) - float(values[row["metric"]])
            )
            row["status"] = "corroborated_by_author_history_native_run_artifact"
            row["reason"] = (
                "the official author's preprint-era Git history ships the exact Qlib/MLflow "
                "metric and executed-config record; all five S&P500 AlphaAgent cells match at "
                "display precision, but missing inputs/predictions/returns prevent regeneration"
            )


def published_non_table_claims() -> list[dict[str, Any]]:
    raw = [
        ("Figure 3/text", "CSI500 cumulative excess return", 45.0, "pct", "approximate", "result"),
        ("Figure 3/text", "S&P500 cumulative excess return", 37.0, "pct", "lower_bound", "result"),
        ("Figure 4", "yearly evaluation periods", 5.0, "years", "exact", "configuration"),
        ("Figure 4 caption", "AlphaAgent factors in decay plot", 15.0, "factors", "exact", "configuration"),
        ("Figure 4/text", "AlphaAgent yearly IC", 0.02, "IC", "approximate", "result"),
        ("Figure 4/text", "AlphaAgent yearly RankIC", 0.025, "RankIC", "approximate", "result"),
        ("Section 4.5", "evolution rounds in ablation", 100.0, "rounds", "exact", "configuration"),
        ("Section 4.5", "rounds per market in ablation", 50.0, "rounds", "exact", "configuration"),
        ("Figure 6", "AlphaAgent hit ratio", 0.29, "ratio", "exact", "result"),
        ("Figure 6", "hit ratio without factor constraints", 0.16, "ratio", "exact", "result"),
        ("Section 4.5", "hit-ratio improvement", 81.0, "pct", "exact", "result"),
        ("Figure 6", "AlphaAgent development success rate", 0.83, "ratio", "exact", "result"),
        ("Figure 6", "development success without symbolic assembly", 0.75, "ratio", "exact", "result"),
        ("Figure 6", "AlphaAgent normalized token efficiency", 1.0, "ratio", "exact", "result"),
        ("Figure 6", "token efficiency without symbolic assembly", 0.81, "ratio", "exact", "result"),
        ("Section 4.5", "token-efficiency improvement", 23.0, "pct", "exact", "result"),
        ("Figure 7/text", "DeepSeek-R1 AlphaAgent ICIR", 0.0615, "ICIR", "exact", "result"),
        ("Figure 7/text", "DeepSeek-R1 AlphaAgent annualized return", 9.19, "pct", "exact", "result"),
        ("Figure 7/text", "DeepSeek-R1 AlphaAgent maximum drawdown", -6.50, "pct", "exact", "result"),
        ("Section 4.5", "GPT-3.5 AlphaAgent-vs-RD-Agent IC p-value", 0.0311, "p_value", "exact", "result"),
        ("Section 4.5", "Qwen-Plus AlphaAgent-vs-RD-Agent IC p-value", 0.0109, "p_value", "exact", "result"),
        ("Section 4.5", "DeepSeek-R1 AlphaAgent-vs-RD-Agent IC p-value", 0.0382, "p_value", "exact", "result"),
        ("Section 4.3", "independent trials for RD-Agent and AlphaAgent", 20.0, "trials", "exact", "configuration"),
        ("Section 4.3", "evolution rounds per trial", 5.0, "rounds", "exact", "configuration"),
        ("Table 2/method", "reasoning-model best-of candidates", 10.0, "candidates", "exact", "configuration"),
        ("Section 4.3", "reasoning-model iterative rounds", 5.0, "rounds", "exact", "configuration"),
    ]
    rows = []
    for location, claim, value, unit, exactness, role in raw:
        rows.append(
            {
                "paper_location": location,
                "claim": claim,
                "paper_value": value,
                "unit": unit,
                "exactness": exactness,
                "claim_role": role,
                "native_reproduced_value": "",
                "status": "unavailable_missing_native_paper_result_path"
                if role == "result"
                else "paper_configuration_recovered_without_complete_trial_inputs",
                "paper_result_credit": False,
            }
        )
    if Counter(row["claim_role"] for row in rows) != {
        "result": 18,
        "configuration": 8,
    }:
        raise RuntimeError("Non-table claim boundary changed")
    return rows


def specification_gaps() -> list[dict[str, Any]]:
    raw = [
        ("regularizer_weights", "alpha_1, alpha_2, alpha_3 are not disclosed", "blocks exact objective"),
        ("er_weights", "beta_1, beta_2, beta_3 are not disclosed", "blocks exact ER score"),
        ("similarity_normalization", "S(f) scaling to [0,1] is not defined", "blocks originality threshold"),
        ("alignment_sign", "C is added to a score said to be better when lower although C is better when higher", "objective sign is ambiguous"),
        ("constraint_thresholds", "no SL, PC, ER acceptance thresholds are disclosed", "blocks factor filter"),
        ("operator_library", "a large paper-era operator library is recovered, but the paper does not pin an exact library revision", "blocks proof of expression equivalence"),
        ("prompts", "paper-era idea/factor/eval prompts are recovered, but prompt/API versions used for every reported trial are not identified", "blocks exact agent replay"),
        ("llm_sampling", "temperature, seeds, API snapshots, and token limits are absent", "blocks stochastic replay"),
        ("seed_hypotheses", "initial research directions and all 20 trial inputs are absent", "blocks search replay"),
        ("factor_outputs", "multiple paper-era factor pools survive, including a 15-row CN candidate file, while MLflow model states expose only feature counts and no lineage proves which exact pool generated a paper panel", "blocks final model-input identity"),
        ("lightgbm", "seven fitted LightGBM states survive, but factor-name mappings, random seeds, and the selected final China lineage are absent", "blocks exact fitted-model/input identity beyond the recovered records"),
        ("universe", "constituent histories, delisting rules, adjustment rules, and filters are absent", "blocks panel identity"),
        ("portfolio", "paper-era Qlib configs plus seven executed metric/config records recover top-k/drop, benchmark, price, limits, account and fees, but predictions, positions, daily returns and complete recorder objects are absent", "blocks end-to-end result regeneration"),
        ("transaction_costs", "paper-era configs recover fees, min costs, deal price and price-limit threshold, but frozen market-state/suspension inputs are absent", "blocks exact net returns"),
        ("trial_aggregation", "the aggregation/selection from 20 trials to Table 2 is not fully specified", "blocks metric target"),
        ("figure_arrays", "underlying daily curves, yearly values, and round distributions are absent", "blocks figure reproduction"),
        ("p_value_samples", "the IC samples used in the three Student t tests are absent", "blocks p-value reproduction"),
    ]
    return [
        {"dimension": dimension, "missing_specification": gap, "consequence": consequence}
        for dimension, gap, consequence in raw
    ]


def current_source_conformance(source_root: Path) -> list[dict[str, Any]]:
    parser_text = (source_root / "alphaagent/dsl/core/parser.py").read_text(encoding="utf-8")
    sim_text = (source_root / "alphaagent/factor/zoo/similarity.py").read_text(encoding="utf-8")
    prompt_text = (source_root / "alphaagent/factor/mining/prompts.py").read_text(encoding="utf-8")
    loop_text = (source_root / "alphaagent/factor/mining/loop.py").read_text(encoding="utf-8")
    config_text = (source_root / "alphaagent/factor/mining/config.py").read_text(encoding="utf-8")
    readme = (source_root / "README.md").read_text(encoding="utf-8")
    dev_log = (source_root / "docs/dev_log.md").read_text(encoding="utf-8")

    checks = [
        ("paper_era_source", "paper implementation released by June 2025", "first commit 2026-07-01", "mismatch_post_paper_rewrite", False),
        ("paper_markets", "CSI500 and S&P500", "CSI1000/A-shares reference dataset", "mismatch", False),
        ("paper_data_sources", "Baostock and Yahoo Finance", "Tushare/open parquet package", "mismatch", False),
        ("paper_input_fields", "OHLCV only", "price, fundamentals, industry, and market-cap fields", "mismatch", False),
        ("paper_test_period", "2021-01 to 2025-01", "default validation 2022-01 to 2024-12", "mismatch", False),
        ("paper_llm", "GPT-3.5-turbo", "gpt-4o-mini dataclass default; CLI requires MODEL", "mismatch", False),
        ("three_specialized_agents", "idea agent, factor agent, eval agent", "one tool-calling trajectory/AgentScope agent", "mismatch", False),
        ("structured_idea_agent", "observation/knowledge/justification/specification", "not implemented as a distinct typed stage", "missing", False),
        ("factor_agent_memory", "successful and failed implementations with failure modes", "delivered-factor registry only", "mismatch", False),
        ("eval_agent", "backtest plus similarity and performance feedback", "train/validation expression evaluation tools", "component_analogue", True),
        ("operator_library", "symbolic operator library", "native DSL operator registry", "component_match", True),
        ("ast_representation", "tree-valued AST T(f)", "pyparsing compiles to Python code strings", "mismatch", False),
        ("largest_common_subtree", "recursive subtree isomorphism size", "not implemented", "missing", False),
        ("alpha101_novelty_zoo", "compare against Alpha101", "no Alpha101 expressions or loader", "missing", False),
        ("similarity_kind", "AST structural similarity", "mean daily cross-sectional Pearson correlation", "mismatch", False),
        ("symbolic_length", "algorithmic SL(f)", "no computation or threshold", "missing", False),
        ("parameter_count", "algorithmic PC(f)", "no computation or threshold", "missing", False),
        ("alignment_c1", "LLM hypothesis-description consistency", "not implemented", "missing", False),
        ("alignment_c2", "LLM description-expression consistency", "not implemented", "missing", False),
        ("alignment_alpha", "alpha=0.5", "no scoring function", "missing", False),
        ("er_score", "beta-weighted novelty/alignment/feature penalty", "no scoring function", "missing", False),
        ("feedback_loop", "metrics guide later iterations", "tool results appended to LLM context", "component_match", True),
        ("multiple_candidates", "multiple expressions per hypothesis", "prompt requests 3--5 parallel train evaluations", "component_analogue", True),
        ("paper_lightgbm", "LightGBM next-day return model, depth 4", "model directory remains TODO", "missing", False),
        ("paper_qlib_backtest", "Qlib top-k dropout strategy", "no portfolio/backtest package", "missing", False),
        ("paper_transaction_fees", "market-specific buy/sell fees", "no paper backtest implementation", "missing", False),
        ("paper_baselines", "nine baselines in Table 2", "no exact baseline runners", "missing", False),
        ("paper_trials", "20 trials x 5 rounds", "no exact runner, seeds, or trajectories", "missing", False),
        ("paper_outputs", "15 factors, curves, predictions, holdings, returns, metrics", "post-paper registry metrics only", "missing", False),
        ("current_registry", "paper final factors", "8 post-paper delivered factors", "provenance_mismatch", False),
        ("current_expressions", "paper factor pool", "13 post-paper DSL expressions", "provenance_mismatch", False),
        ("current_data_release", "paper CSI500/S&P500 frozen panels", "2026 CSI1000 Tushare package", "provenance_mismatch", False),
    ]
    if "parse_multi_line_expression" not in parser_text:
        raise RuntimeError("Pinned parser implementation changed")
    if 'SIMILARITY_KIND = "cross_sectional_pearson_mean"' not in sim_text:
        raise RuntimeError("Pinned similarity implementation changed")
    if "3～5" not in prompt_text or "eval_on_train_set" not in prompt_text:
        raise RuntimeError("Pinned mining prompt changed")
    if "messages.append" not in loop_text or 'model: str = "gpt-4o-mini"' not in config_text:
        raise RuntimeError("Pinned mining loop/config changed")
    if "CSI 1000" not in readme or "Tushare" not in readme:
        raise RuntimeError("Pinned README provenance changed")
    if "model/" not in dev_log or "backtest/" not in dev_log:
        raise RuntimeError("Pinned development-state evidence changed")
    return [
        {
            "dimension": dimension,
            "paper_requirement": paper,
            "released_implementation": released,
            "status": status,
            "paper_mechanism_credit": credit,
        }
        for dimension, paper, released, status, credit in checks
    ]


def paper_era_source_conformance(snapshot_root: Path) -> list[dict[str, Any]]:
    proposal = (snapshot_root / "rdagent/scenarios/qlib/proposal/factor_proposal.py").read_text()
    workflow = (snapshot_root / "rdagent/components/workflow/alphaagent_loop.py").read_text()
    conf = (snapshot_root / "rdagent/app/qlib_rd_loop/conf.py").read_text()
    ast = (snapshot_root / "rdagent/components/coder/factor_coder/expr_parser_tree.py").read_text()
    coder_prompt = (
        snapshot_root / "rdagent/components/coder/factor_coder/prompts_alphaagent.yaml"
    ).read_text()
    cn = (
        snapshot_root
        / "rdagent/scenarios/qlib/experiment/factor_template/conf_cn_combined.yaml"
    ).read_text()
    us = (
        snapshot_root
        / "rdagent/scenarios/qlib/experiment/factor_template/conf_us_combined.yaml"
    ).read_text()
    llm_conf = (snapshot_root / "rdagent/oai/llm_conf.py").read_text()

    required = {
        "structured_hypothesis": "class AlphaAgentHypothesis" in proposal
        and "concise_specification" in proposal,
        "alpha101_loader": 'pd.read_csv("factor_zoo/alpha101.csv"' in proposal,
        "duplicate_filter": "duplicated_subtree_size >= 5" in proposal,
        "trace_feedback": "self.trace.hist.append" in workflow,
        "five_rounds": "evolving_n: int = 5" in conf,
        "largest_subtree": "def find_largest_common_subtree" in ast,
        "factor_alignment_prompt": "factor expression is align with the factor description"
        in coder_prompt,
        "cn_market": "market: &market csi500" in cn,
        "us_market": "market: &market SP500" in us,
        "cn_top50": "topk: 50" in cn and "n_drop: 5" in cn,
        "us_top50": "topk: 50" in us and "n_drop: 5" in us,
        "lightgbm_depth": "max_depth: 4" in cn and "max_depth: 4" in us,
        "default_llm_mismatch": 'chat_model: str = "gpt-4-turbo"' in llm_conf,
    }
    if not all(required.values()):
        raise RuntimeError(f"Pinned paper-era AlphaAgent mechanism changed: {required!r}")

    checks = [
        ("paper_era_source", "paper implementation available before the February 2025 preprint", "public legacy-main snapshot dated 2025-02-12", "recovered_preprint_source", True),
        ("paper_markets", "CSI500 and S&P500", "csi500 and SP500 Qlib configs", "component_match", True),
        ("paper_data_sources", "Baostock and Yahoo Finance", "Baostock URI is explicit; US uses an unversioned local us_data URI with no downloader provenance", "partial_source_match", True),
        ("paper_input_fields", "four OHLCV-derived base features", "the same four feature formulas and next-day label", "component_match", True),
        ("paper_test_period", "2021-01 through 2024-12", "2021-01-01 through 2024-12-30/31", "component_match", True),
        ("paper_llm", "GPT-3.5-turbo", "repository default is gpt-4-turbo; executed model selection is not pinned", "mismatch", False),
        ("three_specialized_agents", "idea, factor, and eval agents", "hypothesis generator, factor constructor/parser, runner/summarizer stages", "component_match", True),
        ("structured_idea_agent", "observation, knowledge, justification, specification", "typed AlphaAgentHypothesis has all four fields", "component_match", True),
        ("factor_agent_memory", "successful and failed implementations with failure modes", "Trace plus CoSTEER successful/failed knowledge stores", "component_match", True),
        ("eval_agent", "execution, stability, backtest and metric feedback", "factor evaluator, Qlib runner and LLM feedback summarizer", "component_match", True),
        ("operator_library", "symbolic operator library", "full function library and prompt semantics", "component_match", True),
        ("ast_representation", "tree-valued AST T(f)", "typed pyparsing Var/Number/Function/Binary/Conditional nodes", "component_match", True),
        ("largest_common_subtree", "recursive subtree isomorphism size", "find_largest_common_subtree executes and counts nodes", "component_match", True),
        ("alpha101_novelty_zoo", "compare against Alpha101", "loader and 101 named Alpha rows exist, but 15 generated rows contaminate the loaded 116-row file", "partial_contaminated_reference_zoo", True),
        ("similarity_kind", "AST structural largest-common-subtree similarity", "same structural operation, including commutative operators", "component_match", True),
        ("symbolic_length", "algorithmic SL(f)", "no SL term or weight is implemented", "missing", False),
        ("parameter_count", "algorithmic PC(f)", "no free-parameter count or weight is implemented", "missing", False),
        ("alignment_c1", "numeric hypothesis-description consistency", "hypothesis conditions factor generation, but no separate numeric c1 evaluator exists", "prompt_only_no_score", False),
        ("alignment_c2", "numeric description-expression consistency", "LLM evaluator checks the same semantic relation but returns prose, not a [0,1] score", "component_analogue", True),
        ("alignment_alpha", "alpha=0.5", "no combined numeric alignment function", "missing", False),
        ("er_score", "beta-weighted novelty/alignment/feature penalty", "no beta-weighted ER function; novelty is a hard retry at subtree size >=5", "mismatch_hard_filter", False),
        ("feedback_loop", "metrics guide later iterations", "runner metrics and feedback are appended to Trace and rendered into the next prompts", "component_match", True),
        ("multiple_candidates", "multiple expressions per hypothesis", "prompt requests 2--4 factors and constructor processes every response entry", "component_match", True),
        ("paper_lightgbm", "LightGBM next-day return model, depth 4", "full LGBModel kwargs and DatasetH segments are recovered", "configuration_match", True),
        ("paper_qlib_backtest", "Qlib top-50/drop-5 strategy", "combined CN/US configs use TopkDropoutStrategy topk=50, n_drop=5 and recorders", "configuration_match", True),
        ("paper_transaction_fees", "CN 5/15 bp and US 0/5 bp buy/sell fees", "matching open/close costs plus deal price, limit threshold and min costs", "configuration_match", True),
        ("paper_baselines", "nine Table 2 baselines", "named GP, o1 and DeepSeek factor-expression CSVs exist, but no exact baseline runners or outputs", "partial_unlinked_artifacts", False),
        ("paper_trials", "20 trials x 5 rounds", "evolving_n=5 is recovered; no 20-trial launcher, seeds or trajectories", "partial_configuration", False),
        ("paper_outputs", "factors, curves, predictions, holdings, returns and metrics", "factor pools plus seven Qlib/MLflow metric/config/model records exist; predictions, curves, positions and returns do not", "partial_native_run_records", False),
        ("current_registry", "paper final factors", "8 entries from the disjoint 2026 rewrite", "provenance_mismatch", False),
        ("current_expressions", "paper factor pool", "13 expressions from the disjoint 2026 DSL", "provenance_mismatch", False),
        ("current_data_release", "paper CSI500/S&P500 frozen panels", "2026 CSI1000 Tushare package", "provenance_mismatch", False),
    ]
    return [
        {
            "dimension": dimension,
            "paper_requirement": paper,
            "released_implementation": released,
            "status": status,
            "paper_mechanism_credit": credit,
        }
        for dimension, paper, released, status, credit in checks
    ]


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    rows = []
    for relative in git_files(source_root):
        path = source_root / relative
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "paper_era_artifact": False,
                "paper_result_credit": False,
            }
        )
    return rows


def paper_era_source_inventory(
    source_root: Path, snapshot_root: Path
) -> list[dict[str, Any]]:
    rows = []
    for relative in git_tree_files(source_root, PAPER_MECHANISM_COMMIT):
        path = snapshot_root / relative
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "paper_era_artifact": True,
                "paper_result_credit": False,
            }
        )
    return rows


def paper_era_factor_rows(snapshot_root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((snapshot_root / "factor_zoo").glob("*.csv")):
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = list(csv.reader(handle))
        if not reader:
            raise RuntimeError(f"Empty paper-era factor file: {path}")
        expression_rows = len(reader) - 1
        alpha101_reference_rows = min(101, expression_rows) if path.name == "alpha101.csv" else 0
        rows.append(
            {
                "path": f"factor_zoo/{path.name}",
                "expression_rows": expression_rows,
                "alpha101_reference_rows": alpha101_reference_rows,
                "other_expression_rows": expression_rows - alpha101_reference_rows,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "directly_referenced_by_alphaagent_code": path.name == "alpha101.csv",
                "paper_result_credit": False,
                "interpretation": (
                    "Alpha101 reference plus 15 appended generated expressions"
                    if path.name == "alpha101.csv"
                    else "author-released preprint-era factor-expression artifact with no result lineage"
                ),
            }
        )
    if len(rows) != 15 or sum(int(row["expression_rows"]) for row in rows) != 268:
        raise RuntimeError("Pinned paper-era factor inventory changed")
    return rows


def _marked_json(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        if line.startswith("@@@"):
            return json.loads(line.removeprefix("@@@"))
    raise RuntimeError(f"Subprocess did not emit a marked JSON summary:\n{stdout}")


def _python_environment_snapshot(
    python: Path, expected_freeze_sha256: str
) -> tuple[dict[str, Any], str]:
    if not python.is_file():
        raise FileNotFoundError(python)
    clean_env = os.environ.copy()
    clean_env.pop("PYTHONPATH", None)
    pip_check = subprocess.run(
        [str(python), "-m", "pip", "check"],
        check=True,
        capture_output=True,
        text=True,
        env=clean_env,
    )
    freeze = subprocess.run(
        [str(python), "-m", "pip", "freeze", "--all"],
        check=True,
        capture_output=True,
        text=True,
        env=clean_env,
    ).stdout
    freeze_sha256 = sha256_bytes(freeze.encode())
    if freeze_sha256 != expected_freeze_sha256:
        raise RuntimeError(
            f"Paper-era environment changed: {freeze_sha256} != "
            f"{expected_freeze_sha256}"
        )
    return (
        {
            "python": str(python),
            "python_version": subprocess.run(
                [str(python), "--version"],
                check=True,
                capture_output=True,
                text=True,
                env=clean_env,
            ).stdout.strip(),
            "pip_check": pip_check.stdout.strip(),
            "dependency_freeze_sha256": freeze_sha256,
            "dependency_freeze_lines": len(freeze.splitlines()),
        },
        freeze,
    )


def _run_paper_era_host_checks(
    snapshot_root: Path, host_python: Path
) -> tuple[dict[str, Any], str]:
    environment, freeze = _python_environment_snapshot(
        host_python, PAPER_HOST_ENV_FREEZE_SHA256
    )
    import_program = r"""
import aiohttp, httpx, importlib, importlib.metadata, json, requests
from pathlib import Path

network_attempts = []
def block_httpx(self, request, *args, **kwargs):
    network_attempts.append(f'httpx:{request.method}:{request.url}')
    raise RuntimeError('network disabled during paper-era AlphaAgent audit')
async def block_httpx_async(self, request, *args, **kwargs):
    network_attempts.append(f'httpx-async:{request.method}:{request.url}')
    raise RuntimeError('network disabled during paper-era AlphaAgent audit')
def block_requests(self, request, *args, **kwargs):
    network_attempts.append(f'requests:{request.method}:{request.url}')
    raise RuntimeError('network disabled during paper-era AlphaAgent audit')
async def block_aiohttp(self, method, url, *args, **kwargs):
    network_attempts.append(f'aiohttp:{method}:{url}')
    raise RuntimeError('network disabled during paper-era AlphaAgent audit')
httpx.Client.send = block_httpx
httpx.AsyncClient.send = block_httpx_async
requests.sessions.Session.send = block_requests
aiohttp.ClientSession._request = block_aiohttp

modules = []
for file in sorted(Path('rdagent').rglob('*.py')):
    fstr = str(file)
    if 'meta_tpl' in fstr or 'template' in fstr or 'tpl' in fstr or 'model_coder' in fstr:
        continue
    if (
        fstr.endswith('rdagent/log/ui/app.py')
        or fstr.endswith('rdagent/app/cli.py')
        or fstr.endswith('rdagent/app/CI/run.py')
    ):
        continue
    modules.append(fstr[fstr.index('rdagent'):-3].replace('/', '.'))

imported = []
failures = []
for name in modules:
    try:
        importlib.import_module(name)
        imported.append(name)
    except Exception as exc:
        failures.append({
            'module': name,
            'exception_type': type(exc).__name__,
            'message': str(exc),
        })

distribution = importlib.metadata.distribution('rdagent')
direct_url_path = Path(distribution._path) / 'direct_url.json'
packages = {
    name: importlib.metadata.version(name)
    for name in (
        'aiohttp', 'docker', 'langchain', 'langchain-community', 'numpy',
        'openai', 'pandas', 'pytest', 'rdagent', 'scikit-learn', 'streamlit'
    )
}
print('@@@' + json.dumps({
    'selected_source_modules': len(modules),
    'imported_source_modules': len(imported),
    'imported_module_names': imported,
    'failures': failures,
    'network_attempts': network_attempts,
    'resolved_packages': packages,
    'rdagent_direct_url': json.loads(direct_url_path.read_text()),
}, sort_keys=True))
"""
    clean_env = os.environ.copy()
    clean_env["PYTHONPATH"] = str(snapshot_root)
    import_outputs = []
    for _ in range(2):
        completed = subprocess.run(
            [str(host_python), "-c", import_program],
            cwd=snapshot_root,
            env=clean_env,
            check=True,
            capture_output=True,
            text=True,
        )
        import_outputs.append(_marked_json(completed.stdout))
    if import_outputs[0] != import_outputs[1]:
        raise RuntimeError("Paper-era RD-Agent module import inventory is nondeterministic")
    imports = import_outputs[0]
    expected_failure = {
        "module": PAPER_ERA_IMPORT_FAILURE_MODULE,
        "exception_type": "FileNotFoundError",
        "message": f"[Errno 2] No such file or directory: '{PAPER_ERA_IMPORT_FAILURE_PATH}'",
    }
    if (
        imports["selected_source_modules"] != 113
        or imports["imported_source_modules"] != 112
        or imports["failures"] != [expected_failure]
        or imports["network_attempts"]
    ):
        raise RuntimeError(f"Paper-era RD-Agent import boundary changed: {imports}")
    direct_url = imports["rdagent_direct_url"]
    if direct_url.get("vcs_info", {}).get("commit_id") != PAPER_MECHANISM_COMMIT:
        raise RuntimeError(f"Wrong RD-Agent environment commit: {direct_url}")

    pytest_program = r"""
import aiohttp, httpx, json, pytest, requests, sys
network_attempts = []
def block_httpx(self, request, *args, **kwargs):
    network_attempts.append(f'httpx:{request.method}:{request.url}')
    raise RuntimeError('network disabled during paper-era AlphaAgent audit')
async def block_httpx_async(self, request, *args, **kwargs):
    network_attempts.append(f'httpx-async:{request.method}:{request.url}')
    raise RuntimeError('network disabled during paper-era AlphaAgent audit')
def block_requests(self, request, *args, **kwargs):
    network_attempts.append(f'requests:{request.method}:{request.url}')
    raise RuntimeError('network disabled during paper-era AlphaAgent audit')
async def block_aiohttp(self, method, url, *args, **kwargs):
    network_attempts.append(f'aiohttp:{method}:{url}')
    raise RuntimeError('network disabled during paper-era AlphaAgent audit')
httpx.Client.send = block_httpx
httpx.AsyncClient.send = block_httpx_async
requests.sessions.Session.send = block_requests
aiohttp.ClientSession._request = block_aiohttp
exit_code = pytest.main(sys.argv[1:])
print('@@@' + json.dumps({'exit_code': exit_code, 'network_attempts': network_attempts}, sort_keys=True))
raise SystemExit(exit_code)
"""
    misc_summaries = []
    for _ in range(2):
        completed = subprocess.run(
            [
                str(host_python),
                "-c",
                pytest_program,
                "test/utils/test_misc.py",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            cwd=snapshot_root,
            env=clean_env,
            check=False,
            capture_output=True,
            text=True,
        )
        summary = _marked_json(completed.stdout)
        combined = completed.stdout + completed.stderr
        if completed.returncode != 0 or summary != {"exit_code": 0, "network_attempts": []}:
            raise RuntimeError(f"Paper-era singleton test failed:\n{combined}")
        if "1 passed" not in combined:
            raise RuntimeError(f"Paper-era singleton test count changed:\n{combined}")
        misc_summaries.append(summary)

    import_test = subprocess.run(
        [
            str(host_python),
            "-c",
            pytest_program,
            "test/utils/test_import.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=snapshot_root,
        env=clean_env,
        check=False,
        capture_output=True,
        text=True,
    )
    import_test_summary = _marked_json(import_test.stdout)
    import_test_combined = import_test.stdout + import_test.stderr
    if (
        import_test.returncode != 1
        or import_test_summary != {"exit_code": 1, "network_attempts": []}
        or "1 failed" not in import_test_combined
        or PAPER_ERA_IMPORT_FAILURE_PATH not in import_test_combined
    ):
        raise RuntimeError(
            "Paper-era upstream import-test failure boundary changed:\n"
            + import_test_combined
        )

    environment.update(
        {
            "dependency_environment_reproduced": True,
            "exact_historical_dependency_versions_recovered": False,
            "dependency_release_cutoff_utc": PAPER_MECHANISM_COMMIT_UTC,
            "source_commit_in_environment": PAPER_MECHANISM_COMMIT,
            "resolved_packages": imports["resolved_packages"],
            "selected_source_modules": imports["selected_source_modules"],
            "imported_source_modules": imports["imported_source_modules"],
            "imported_module_names": imports["imported_module_names"],
            "module_import_failures": imports["failures"],
            "module_import_inventory_deterministic_across_two_runs": True,
            "upstream_offline_tests": {
                "tests_total": 2,
                "tests_passed": 1,
                "tests_failed": 1,
                "passing_test": "test/utils/test_misc.py::MiscTest::test_singleton",
                "passing_test_runs": len(misc_summaries),
                "expected_source_failure_test": (
                    "test/utils/test_import.py::TestRDAgentImports::test_import_modules"
                ),
                "expected_source_failure_module": PAPER_ERA_IMPORT_FAILURE_MODULE,
                "expected_source_failure_path": PAPER_ERA_IMPORT_FAILURE_PATH,
                "failure_is_dependency_error": False,
            },
            "network_attempts": imports["network_attempts"],
            "rdagent_direct_url": direct_url,
            "paper_result_reproduction": False,
        }
    )
    return environment, freeze


def _run_paper_era_qlib_checks(
    snapshot_root: Path, qlib_python: Path
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    environment, freeze = _python_environment_snapshot(
        qlib_python, PAPER_QLIB_ENV_FREEZE_SHA256
    )
    program = r"""
import hashlib, importlib.metadata, json, pickletools
from pathlib import Path
import lightgbm as lgb
import numpy as np
import qlib
import requests

network_attempts = []
def block_requests(self, request, *args, **kwargs):
    network_attempts.append(f'requests:{request.method}:{request.url}')
    raise RuntimeError('network disabled during paper-era AlphaAgent Qlib audit')
requests.sessions.Session.send = block_requests

root = Path('.')
executions = []
for run_dir in sorted((root / 'saved_mlruns').iterdir()):
    blob = (run_dir / 'artifacts/config').read_bytes()
    strings = [
        argument
        for _opcode, argument, _position in pickletools.genops(blob)
        if isinstance(argument, str)
    ]
    model_state = next(value for value in strings if value.startswith('tree\nversion='))
    booster = lgb.Booster(model_str=model_state)
    probe = np.vstack([
        np.zeros(booster.num_feature(), dtype=np.float64),
        np.ones(booster.num_feature(), dtype=np.float64),
    ])
    predictions = booster.predict(probe)
    feature_names = booster.feature_name()
    executions.append({
        'run_id': run_dir.name,
        'model_features': booster.num_feature(),
        'model_trees': booster.num_trees(),
        'model_current_iteration': booster.current_iteration(),
        'model_per_iteration': booster.num_model_per_iteration(),
        'feature_names_sha256': hashlib.sha256('\n'.join(feature_names).encode()).hexdigest(),
        'zero_probe_prediction': float(predictions[0]),
        'one_probe_prediction': float(predictions[1]),
        'probe_predictions_sha256': hashlib.sha256(
            predictions.astype('<f8', copy=False).tobytes()
        ).hexdigest(),
        'split_importance_sum': int(booster.feature_importance('split').sum()),
        'gain_importance_sum': float(booster.feature_importance('gain').sum()),
    })

packages = {
    name: importlib.metadata.version(name)
    for name in ('catboost', 'lightgbm', 'mlflow', 'pyqlib', 'scipy', 'torch', 'xgboost')
}
qlib_distribution = importlib.metadata.distribution('pyqlib')
qlib_direct_url = json.loads(
    (Path(qlib_distribution._path) / 'direct_url.json').read_text()
)
torch_distribution = importlib.metadata.distribution('torch')
torch_direct_url = json.loads(
    (Path(torch_distribution._path) / 'direct_url.json').read_text()
)
print('@@@' + json.dumps({
    'executions': executions,
    'network_attempts': network_attempts,
    'qlib_direct_url': qlib_direct_url,
    'qlib_import_version': qlib.__version__,
    'resolved_packages': packages,
    'torch_direct_url': torch_direct_url,
}, sort_keys=True))
"""
    clean_env = os.environ.copy()
    clean_env.pop("PYTHONPATH", None)
    outputs = []
    for _ in range(2):
        completed = subprocess.run(
            [str(qlib_python), "-c", program],
            cwd=snapshot_root,
            env=clean_env,
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(_marked_json(completed.stdout))
    if outputs[0] != outputs[1]:
        raise RuntimeError("Paper-era fitted LightGBM execution is nondeterministic")
    observed = outputs[0]
    executions = observed["executions"]
    expected_packages = {
        "catboost": "1.2.7",
        "lightgbm": "4.5.0",
        "mlflow": "1.30.0",
        "pyqlib": "0.9.5.99",
        "scipy": "1.11.4",
        "torch": "2.2.1+cpu",
        "xgboost": "2.1.4",
    }
    matching_execution = next(
        row for row in executions if row["run_id"] == "77b227f86e5a47bab48178cac409a98b"
    )
    if (
        len(executions) != 7
        or observed["network_attempts"]
        or observed["resolved_packages"] != expected_packages
        or observed["qlib_direct_url"].get("vcs_info", {}).get("commit_id")
        != QLIB_SOURCE_COMMIT
        or matching_execution["model_features"] != 9
        or matching_execution["model_trees"] != 3
    ):
        raise RuntimeError(f"Paper-era Qlib/model boundary changed: {observed}")
    environment.update(
        {
            "dependency_environment_reproduced": True,
            "exact_historical_dependency_versions_recovered": False,
            "exact_cuda_container_reproduced": False,
            "cpu_compatibility_substitution": True,
            "dependency_release_cutoff_utc": PAPER_MECHANISM_COMMIT_UTC,
            "source_commit_in_environment": QLIB_SOURCE_COMMIT,
            "qlib_import_version": observed["qlib_import_version"],
            "qlib_direct_url": observed["qlib_direct_url"],
            "torch_direct_url": observed["torch_direct_url"],
            "resolved_packages": observed["resolved_packages"],
            "fitted_lightgbm_states_loaded": len(executions),
            "fitted_lightgbm_state_execution_runs": 2,
            "fitted_lightgbm_state_execution_deterministic": True,
            "network_attempts": observed["network_attempts"],
            "native_backtests_reexecuted": 0,
            "paper_result_reproduction": False,
        }
    )
    return environment, freeze, executions


def run_paper_era_component_checks(
    snapshot_root: Path, host_python: Path, qlib_python: Path
) -> dict[str, Any]:
    compile_result = subprocess.run(
        [str(host_python), "-m", "compileall", "-q", str(snapshot_root)],
        check=True,
        capture_output=True,
        text=True,
    )
    if compile_result.stdout or compile_result.stderr:
        raise RuntimeError(
            "Paper-era compile emitted unexpected output:\n"
            + compile_result.stdout
            + compile_result.stderr
        )
    program = r"""
import importlib.util, json, sys
from pathlib import Path
import pandas as pd

root = Path(sys.argv[1])
path = root / 'rdagent/components/coder/factor_coder/expr_parser_tree.py'
spec = importlib.util.spec_from_file_location('alphaagent_paper_era_expr_parser', path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

def score(left, right):
    match = module.compare_expressions(left, right)
    return None if match is None else match.size

factor_df = pd.read_csv(root / 'factor_zoo/alpha101.csv')
probe = str(factor_df.iloc[0, 1])
self_score, subtree, matched = module.match_alphazoo(probe, factor_df)
candidate_df = pd.read_csv(root / 'factor_zoo/cn_factors_test.csv')
candidate_errors = []
for _, row in candidate_df.iterrows():
    try:
        module.parse_expression(str(row['factor_expression']))
    except ValueError:
        candidate_errors.append(str(row['factor_name']))
print(json.dumps({
    'identical_expression_lcs_size': score('RANK(DELTA($open, 1))', 'RANK(DELTA($open, 1))'),
    'commutative_expression_lcs_size': score('$open + $close', '$close + $open'),
    'partial_expression_lcs_size': score('MEAN($close, 10) + STD($volume, 5)', 'MEAN($close, 10) - MAX($open, 2)'),
    'loaded_alpha101_csv_rows': len(factor_df),
    'named_alpha101_reference_rows': int(factor_df['factor_name'].astype(str).str.match(r'^Alpha#\d+$').sum()),
    'alpha101_self_match_lcs_size': self_score,
    'alpha101_self_match_exact': matched == probe,
    'alpha101_self_match_subtree_present': subtree is not None,
    'figure4_candidate_factor_rows': len(candidate_df),
    'figure4_candidate_parseable_rows': len(candidate_df) - len(candidate_errors),
    'figure4_candidate_parse_failures': candidate_errors,
}, sort_keys=True))
"""
    outputs = []
    for _ in range(2):
        completed = subprocess.run(
            [str(host_python), "-c", program, str(snapshot_root)],
            cwd=snapshot_root,
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(json.loads(completed.stdout))
    if outputs[0] != outputs[1]:
        raise RuntimeError("Paper-era AST component is not deterministic")
    expected = {
        "identical_expression_lcs_size": 4,
        "commutative_expression_lcs_size": 3,
        "partial_expression_lcs_size": 3,
        "loaded_alpha101_csv_rows": 116,
        "named_alpha101_reference_rows": 101,
        "alpha101_self_match_lcs_size": 23,
        "alpha101_self_match_exact": True,
        "alpha101_self_match_subtree_present": True,
        "figure4_candidate_factor_rows": 15,
        "figure4_candidate_parseable_rows": 14,
        "figure4_candidate_parse_failures": ["Lagged_Volume_Change_Factor_3D"],
    }
    if outputs[0] != expected:
        raise RuntimeError(f"Pinned paper-era AST behavior changed: {outputs[0]!r}")
    host_environment, host_freeze = _run_paper_era_host_checks(
        snapshot_root, host_python
    )
    qlib_environment, qlib_freeze, model_executions = _run_paper_era_qlib_checks(
        snapshot_root, qlib_python
    )
    return {
        "snapshot_commit": PAPER_MECHANISM_COMMIT,
        "python_files_compiled": 331,
        "compile_passed": True,
        "ast_component_runs": 2,
        "ast_component_deterministic": True,
        **outputs[0],
        "dependency_architecture": (
            "RD-Agent host process plus a separately built Qlib backtest runtime"
        ),
        "dependency_environment_reproduced": True,
        "exact_historical_dependency_versions_recovered": False,
        "exact_cuda_container_reproduced": False,
        "host_environment": host_environment,
        "qlib_environment": qlib_environment,
        "fitted_model_executions": model_executions,
        "_host_dependency_freeze_text": host_freeze,
        "_qlib_dependency_freeze_text": qlib_freeze,
        "network_or_llm_calls": False,
        "paper_result_reproduction": False,
    }


def current_registry_rows(source_root: Path) -> list[dict[str, Any]]:
    registry = json.loads(
        (source_root / "artifacts/factorzoo/stock_1d/mining_delivered_registry.json").read_text(
            encoding="utf-8"
        )
    )
    rows = []
    for factor_id, item in sorted(registry.items()):
        metrics = item.get("ingest_metrics", {})
        config = item.get("ingest_config", {})
        rows.append(
            {
                "factor_id": factor_id,
                "ingested_at": item.get("ingested_at", ""),
                "label_col": config.get("label_col", ""),
                "eval_start": metrics.get("eval_start", ""),
                "eval_end": metrics.get("eval_end", ""),
                "ic": metrics.get("ic", ""),
                "icir": metrics.get("icir", ""),
                "rank_ic": metrics.get("rank_ic", ""),
                "paper_result_credit": False,
                "reason": "post-paper CSI1000/Tushare artifact, not a paper factor/output",
            }
        )
    return rows


def data_release_provenance() -> list[dict[str, Any]]:
    return [
        {
            "artifact": "alphaagent-data-20260703.zip",
            "official_share_url": "https://pan.baidu.com/s/1GsCl6McyoHyws5bl571HqQ?pwd=5qp5",
            "share_file_id": "640389739420941",
            "bytes": 524248466,
            "observed_available": True,
            "observed_on": "2026-08-11",
            "dataset_claim": "CSI1000 union, Tushare, 2015-01 through 2026-06",
            "paper_requirement": "CSI500 Baostock and S&P500 Yahoo Finance through 2025-01",
            "paper_data_credit": False,
            "status": "available_post_paper_data_with_wrong_markets_source_and_vintage",
        }
    ]


def _run_source_tests(source_root: Path, source_python: Path) -> dict[str, Any]:
    program = r"""
import aiohttp, httpx, importlib, importlib.metadata, json, pytest, requests
from pathlib import Path

network_attempts = []
def block_httpx(self, request, *args, **kwargs):
    network_attempts.append(f'httpx:{request.method}:{request.url}')
    raise RuntimeError('network disabled during AlphaAgent source audit')
async def block_httpx_async(self, request, *args, **kwargs):
    network_attempts.append(f'httpx-async:{request.method}:{request.url}')
    raise RuntimeError('network disabled during AlphaAgent source audit')
def block_requests(self, request, *args, **kwargs):
    network_attempts.append(f'requests:{request.method}:{request.url}')
    raise RuntimeError('network disabled during AlphaAgent source audit')
async def block_aiohttp(self, method, url, *args, **kwargs):
    network_attempts.append(f'aiohttp:{method}:{url}')
    raise RuntimeError('network disabled during AlphaAgent source audit')
httpx.Client.send = block_httpx
httpx.AsyncClient.send = block_httpx_async
requests.sessions.Session.send = block_requests
aiohttp.ClientSession._request = block_aiohttp

modules = []
for path in sorted(Path('alphaagent').rglob('*.py')):
    parts = list(path.with_suffix('').parts)
    if parts[-1] == '__init__':
        parts = parts[:-1]
    name = '.'.join(parts)
    if name and name not in modules:
        modules.append(name)
for name in modules:
    importlib.import_module(name)

exit_code = pytest.main(['tests', '-q', '-p', 'no:cacheprovider'])
packages = {
    name: importlib.metadata.version(name)
    for name in (
        'agentscope', 'alphaagent', 'lightgbm', 'numba', 'numpy', 'openai',
        'pandas', 'pyarrow', 'pytest', 'scikit-learn', 'tushare'
    )
}
print(json.dumps({
    'exit_code': exit_code,
    'imported_source_modules': len(modules),
    'imported_module_names': modules,
    'resolved_packages': packages,
    'network_attempts': network_attempts,
}, sort_keys=True))
raise SystemExit(exit_code)
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_root)
    outputs = []
    summaries = []
    for _ in range(2):
        completed = subprocess.run(
            [str(source_python), "-c", program],
            cwd=source_root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        combined = completed.stdout + completed.stderr
        if "80 passed" not in combined:
            raise RuntimeError(f"Pinned source test count changed:\n{combined}")
        outputs.append(json.loads(completed.stdout.splitlines()[-1]))
        summaries.append("80 passed")
    if outputs[0] != outputs[1]:
        raise RuntimeError("AlphaAgent real-dependency source check is nondeterministic")
    observed = outputs[0]
    if (
        observed["exit_code"] != 0
        or observed["imported_source_modules"] != 72
        or observed["network_attempts"]
    ):
        raise RuntimeError(f"AlphaAgent real-dependency source boundary changed: {observed}")
    return {
        "status": "passed_with_real_declared_dependencies",
        "tests_passed": 80,
        "dependency_stubs": [],
        "imported_source_modules": observed["imported_source_modules"],
        "resolved_packages": observed["resolved_packages"],
        "network_attempts": observed["network_attempts"],
        "deterministic_across_two_runs": True,
        "network_or_llm_calls": False,
        "paper_result_reproduction": False,
        "summary_tail": "80 passed",
    }


def _run_base_factor_component(
    source_root: Path, source_python: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    program = r"""
import hashlib, json, sys
import numpy as np
import pandas as pd

from alphaagent.dsl import eval_factor

expressions = json.loads(sys.argv[1])
dates = pd.bdate_range('2020-01-01', periods=40)
assets = [f'S{i:02d}' for i in range(12)]
index = pd.MultiIndex.from_product([dates, assets], names=['datetime', 'instrument'])
t = np.repeat(np.arange(len(dates), dtype=float), len(assets))
a = np.tile(np.arange(len(assets), dtype=float), len(dates))
base = 20.0 + 0.07 * t + 0.03 * a + np.sin((t + a) / 5.0)
panel = pd.DataFrame(index=index)
panel['open'] = base * (1.0 + 0.001 * np.cos(a + t / 3.0))
panel['close'] = base * (1.0 + 0.002 * np.sin(a / 2.0 + t / 4.0))
panel['high'] = np.maximum(panel['open'], panel['close']) * 1.01
panel['low'] = np.minimum(panel['open'], panel['close']) * 0.99
panel['volume'] = 100000.0 + 1000.0 * a + 500.0 * t

rows = []
digest = hashlib.sha256()
for name, expression in sorted(expressions.items()):
    values = eval_factor(expression, panel).to_numpy(dtype=np.float64)
    canonical = np.nan_to_num(values, nan=9.87654321e99, posinf=8.7654321e99, neginf=-8.7654321e99)
    digest.update(name.encode())
    digest.update(canonical.tobytes())
    rows.append({
        'factor': name,
        'expression': expression,
        'rows': int(values.size),
        'finite_values': int(np.isfinite(values).sum()),
        'native_parser_executable': True,
        'paper_metric_reproduced': False,
        'status': 'post_paper_dsl_executes_on_synthetic_data_only',
    })
print(json.dumps({'sha256': digest.hexdigest(), 'rows': rows}, sort_keys=True))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_root)
    outputs = []
    for _ in range(2):
        completed = subprocess.run(
            [str(source_python), "-c", program, json.dumps(BASE_FACTOR_EXPRESSIONS)],
            cwd=source_root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(json.loads(completed.stdout))
    if outputs[0] != outputs[1]:
        raise RuntimeError("Post-paper DSL synthetic component is not deterministic")
    if outputs[0]["sha256"] != EXPECTED_SYNTHETIC_SHA256:
        raise RuntimeError("Pinned post-paper DSL synthetic output changed")
    return (
        {
            "synthetic_runs": 2,
            "deterministic": True,
            "sha256": outputs[0]["sha256"],
            "paper_result_reproduction": False,
        },
        outputs[0]["rows"],
    )


def run_native_component_checks(
    source_root: Path, source_python: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not source_python.is_file():
        raise FileNotFoundError(source_python)
    clean_env = os.environ.copy()
    clean_env.pop("PYTHONPATH", None)
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
    if freeze_sha256 != REWRITE_ENV_FREEZE_SHA256:
        raise RuntimeError(
            "AlphaAgent rewrite environment changed: "
            f"{freeze_sha256} != {REWRITE_ENV_FREEZE_SHA256}"
        )
    tests = _run_source_tests(source_root, source_python)
    synthetic, rows = _run_base_factor_component(source_root, source_python)
    component = {
        "source_python": str(source_python),
        "source_python_version": subprocess.run(
            [str(source_python), "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "dependency_environment_reproduced": True,
        "exact_historical_dependency_versions_recovered": False,
        "dependency_scope": "post-paper 2026 rewrite only; not the 2025 paper-era RD-Agent/Qlib environment",
        "pip_check": pip_check.stdout.strip(),
        "dependency_freeze_sha256": freeze_sha256,
        "dependency_freeze_lines": len(freeze.splitlines()),
        "_dependency_freeze_text": freeze,
        "upstream_tests": tests,
        "synthetic_base_factor_component": synthetic,
        "paper_result_reproduction": False,
    }
    return component, rows


def verify_pins(
    source_root: Path, paper_pdf: Path, paper_v1_pdf: Path
) -> tuple[str, str]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    observed_paper = sha256(paper_pdf)
    if observed_paper != PAPER_SHA256:
        raise RuntimeError(f"Expected paper SHA-256 {PAPER_SHA256}, found {observed_paper}")
    observed_v1 = sha256(paper_v1_pdf)
    if observed_v1 != PAPER_V1_SHA256:
        raise RuntimeError(
            f"Expected original-paper SHA-256 {PAPER_V1_SHA256}, found {observed_v1}"
        )
    for relative, expected in PINNED_SOURCE_SHA256.items():
        observed = sha256(source_root / relative)
        if observed != expected:
            raise RuntimeError(f"Pinned hash changed for {relative}: {observed}")
    first_commit, first_date = git_first_commit(source_root)
    if first_commit != SOURCE_FIRST_COMMIT or not first_date.startswith("2026-07-01"):
        raise RuntimeError(f"Pinned first-commit provenance changed: {first_commit}|{first_date}")
    for relative, expected in PAPER_MECHANISM_SHA256.items():
        observed = git_output(source_root, "show", f"{PAPER_MECHANISM_COMMIT}:{relative}")
        observed_hash = hashlib.sha256(observed.encode()).hexdigest()
        # git show as text strips the final newline; the extracted-tree hashes below are
        # authoritative.  This read only proves every pinned path still exists.
        if not observed or len(observed_hash) != 64:
            raise RuntimeError(f"Paper-era source path disappeared: {relative}")
    return commit, first_date


def build_audit(
    source_root: Path,
    paper_pdf: Path,
    paper_v1_pdf: Path,
    paper_versions_root: Path,
    latex_command: str,
    source_python: Path,
    paper_host_python: Path,
    paper_qlib_python: Path,
    paper_qlib_source_root: Path,
    paper_qlib_data_archive: Path,
    output_dir: Path,
) -> dict[str, Any]:
    commit, first_date = verify_pins(source_root, paper_pdf, paper_v1_pdf)
    history, history_rows = history_audit(source_root)
    history_paths, history_summary = public_source_history(source_root)
    fork_rows, fork_bundle = fork_default_head_audit(source_root)
    paper_versions, paper_lineage, paper_figures = official_paper_version_rows(
        paper_versions_root, source_root, latex_command
    )
    table_rows = table_conformance()
    run_records = paper_era_run_records(source_root)
    apply_run_record_conformance(table_rows, run_records)
    run_input_audit = paper_era_run_input_audit(
        source_root,
        paper_qlib_source_root,
        paper_qlib_data_archive,
        run_records,
    )
    claims = published_non_table_claims()
    gaps = specification_gaps()
    inventory = source_inventory(source_root)
    registry = current_registry_rows(source_root)
    release = data_release_provenance()
    component, base_factors = run_native_component_checks(source_root, source_python)
    rewrite_dependency_freeze = component.pop("_dependency_freeze_text")

    with tempfile.TemporaryDirectory(prefix="alphaagent-paper-era-") as temp_dir:
        paper_era_root = Path(temp_dir)
        extract_git_commit(source_root, PAPER_MECHANISM_COMMIT, paper_era_root)
        for relative, expected in PAPER_MECHANISM_SHA256.items():
            observed = sha256(paper_era_root / relative)
            if observed != expected:
                raise RuntimeError(
                    f"Pinned paper-era hash changed for {relative}: {observed}"
                )
        mechanisms = paper_era_source_conformance(paper_era_root)
        current_mechanisms = current_source_conformance(source_root)
        paper_era_inventory = paper_era_source_inventory(source_root, paper_era_root)
        paper_era_factors = paper_era_factor_rows(paper_era_root)
        paper_era_component = run_paper_era_component_checks(
            paper_era_root, paper_host_python, paper_qlib_python
        )
        paper_host_dependency_freeze = paper_era_component.pop(
            "_host_dependency_freeze_text"
        )
        paper_qlib_dependency_freeze = paper_era_component.pop(
            "_qlib_dependency_freeze_text"
        )
        model_executions = {
            row["run_id"]: row
            for row in paper_era_component["fitted_model_executions"]
        }
        if set(model_executions) != {row["run_id"] for row in run_records}:
            raise RuntimeError("Fitted-model execution/run-record IDs differ")
        for row in run_records:
            execution = model_executions[row["run_id"]]
            row.update(
                {
                    "fitted_lightgbm_state_loaded": True,
                    "model_features_loaded": execution["model_features"],
                    "model_trees_loaded": execution["model_trees"],
                    "model_current_iteration": execution["model_current_iteration"],
                    "model_per_iteration": execution["model_per_iteration"],
                    "feature_names_sha256": execution["feature_names_sha256"],
                    "zero_probe_prediction": execution["zero_probe_prediction"],
                    "one_probe_prediction": execution["one_probe_prediction"],
                    "probe_predictions_sha256": execution[
                        "probe_predictions_sha256"
                    ],
                    "split_importance_sum": execution["split_importance_sum"],
                    "gain_importance_sum": execution["gain_importance_sum"],
                    "fitted_model_execution_paper_result_credit": False,
                }
            )

    if len(inventory) != 141:
        raise RuntimeError(f"Expected 141 tracked source files, got {len(inventory)}")
    if len(registry) != 8:
        raise RuntimeError(f"Expected 8 post-paper registry entries, got {len(registry)}")
    if (
        len(mechanisms) != 32
        or len(current_mechanisms) != 32
        or len(gaps) != 17
        or len(base_factors) != 4
    ):
        raise RuntimeError("Pinned audit dimension counts changed")
    if Counter(row["status"] for row in table_rows) != {
        "corroborated_by_author_history_native_run_artifact": 5,
        "unavailable_missing_native_paper_result_path": 95,
        "paper_configuration_recovered_without_frozen_dataset": 6,
    }:
        raise RuntimeError("Pinned numeric conformance boundary changed")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_1_2_conformance.csv", table_rows)
    write_csv(output_dir / "published_non_table_claims.csv", claims)
    write_csv(output_dir / "source_mechanism_conformance.csv", mechanisms)
    write_csv(output_dir / "current_rewrite_mechanism_conformance.csv", current_mechanisms)
    write_csv(output_dir / "official_history_timeline.csv", history_rows)
    write_csv(output_dir / "official_paper_version_inventory.csv", paper_versions)
    write_csv(output_dir / "official_paper_numeric_lineage.csv", paper_lineage)
    write_csv(output_dir / "official_paper_figure_asset_inventory.csv", paper_figures)
    write_csv(output_dir / "public_source_history_path_inventory.csv", history_paths)
    write_csv(output_dir / "fork_default_head_census.csv", fork_rows)
    write_csv(output_dir / "paper_specification_gaps.csv", gaps)
    write_csv(output_dir / "released_source_inventory.csv", inventory)
    write_csv(output_dir / "paper_era_source_inventory.csv", paper_era_inventory)
    write_csv(output_dir / "paper_era_factor_artifacts.csv", paper_era_factors)
    write_csv(output_dir / "paper_era_mlflow_run_records.csv", run_records)
    write_csv(output_dir / "post_paper_registry_metrics.csv", registry)
    write_csv(output_dir / "data_release_provenance.csv", release)
    write_csv(output_dir / "synthetic_base_factor_component.csv", base_factors)
    (output_dir / "native_component.json").write_text(
        json.dumps(component, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "current_rewrite_environment_freeze.txt").write_text(
        rewrite_dependency_freeze, encoding="utf-8"
    )
    (output_dir / "paper_era_host_environment_freeze.txt").write_text(
        paper_host_dependency_freeze, encoding="utf-8"
    )
    (output_dir / "paper_era_qlib_environment_freeze.txt").write_text(
        paper_qlib_dependency_freeze, encoding="utf-8"
    )
    (output_dir / "paper_era_component.json").write_text(
        json.dumps(paper_era_component, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "public_source_history.json").write_text(
        json.dumps(history_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "fork_data_bundle_audit.json").write_text(
        json.dumps(fork_bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "paper_era_run_input_audit.json").write_text(
        json.dumps(run_input_audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    mechanism_counts = Counter(row["status"] for row in mechanisms)
    manifest: dict[str, Any] = {
        "audit": "all AlphaAgent paper versions versus both roots of the official repository",
        "overall_status": "partially_corroborated_paper_era_native_run_records_recovered",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": "arXiv:2502.16789v2",
        "paper_date": "2025-06-09",
        "paper_sha256": PAPER_SHA256,
        "paper_v1_url": PAPER_V1_URL,
        "paper_v1_sha256": PAPER_V1_SHA256,
        "official_arxiv_versions_audited": len(paper_versions),
        "official_arxiv_source_archives_audited": len(paper_versions),
        "official_paper_versions_compiled_to_published_page_count": sum(
            row["paper_document_reproduced"] for row in paper_versions
        ),
        "official_paper_numeric_cell_identities": len(paper_lineage),
        "official_paper_numeric_values_revised_in_v2": sum(
            row["status"] == "numeric_value_revised_in_v2" for row in paper_lineage
        ),
        "official_paper_configuration_labels_revised_in_v2": sum(
            row["status"] == "configuration_label_revised_in_v2"
            for row in paper_lineage
        ),
        "official_paper_active_figure_assets_v1": sum(
            row["paper_version"] == "v1" for row in paper_figures
        ),
        "official_paper_active_figure_assets_v2": sum(
            row["paper_version"] == "v2" for row in paper_figures
        ),
        "official_paper_logical_figure_assets_revised_in_v2": len(
            {
                row["logical_figure_id"]
                for row in paper_figures
                if row["lineage_status"] == "source_asset_revised_in_v2"
            }
        ),
        "official_paper_logical_figure_assets_added_in_v2": len(
            {
                row["logical_figure_id"]
                for row in paper_figures
                if row["lineage_status"] == "added_in_v2"
            }
        ),
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "source_commit_date": "2026-07-03",
        "source_first_commit": SOURCE_FIRST_COMMIT,
        "source_first_commit_date": first_date,
        "legacy_source_head": LEGACY_HEAD_COMMIT,
        "legacy_source_root": LEGACY_ROOT_COMMIT,
        "paper_mechanism_commit": PAPER_MECHANISM_COMMIT,
        "paper_mechanism_commit_date": "2025-02-12",
        "latest_full_tree_preprint_commit": LATEST_FULL_TREE_PREPRINT_COMMIT,
        "preprint_cutoff_commit": PREPRINT_CUTOFF_COMMIT,
        "paper_era_source_revision_available": True,
        "official_git_history": history,
        "public_source_history": history_summary,
        "public_source_unique_historical_file_paths": history_summary[
            "official_unique_historical_file_paths"
        ],
        "public_source_reachable_blobs": history_summary[
            "official_reachable_object_types"
        ]["blob"],
        "public_source_reachable_trees": history_summary[
            "official_reachable_object_types"
        ]["tree"],
        "public_source_reachable_commit_objects": history_summary[
            "official_reachable_object_types"
        ]["commit"],
        "public_source_historical_author_run_record_paths": history_summary[
            "historical_author_run_record_paths"
        ],
        "public_source_historical_author_run_ids": len(
            history_summary["historical_author_run_ids"]
        ),
        "public_source_primitive_prediction_return_or_holding_paths": history_summary[
            "primitive_prediction_return_or_holding_paths"
        ],
        "fork_discovery_date": FORK_DISCOVERY_DATE,
        "fork_default_heads_total": sum(
            int(row["repository_count"]) for row in fork_rows
        ),
        "fork_unique_default_head_groups": len(fork_rows),
        "forks_at_official_heads": sum(
            int(row["repository_count"])
            for row in fork_rows
            if row["default_head_commit"] in OFFICIAL_HEADS
        ),
        "divergent_fork_default_heads": sum(
            int(row["repository_count"])
            for row in fork_rows
            if row["default_head_commit"] not in OFFICIAL_HEADS
        ),
        "divergent_fork_paper_result_units_regenerated": sum(
            int(row["paper_result_units_regenerated"])
            for row in fork_rows
            if row["default_head_commit"] not in OFFICIAL_HEADS
        ),
        "independent_fork_data_bundle_audited": True,
        "independent_fork_data_bundle_calendar_start": fork_bundle[
            "calendar_start"
        ],
        "independent_fork_data_bundle_sp500_rows": fork_bundle[
            "sp500_membership_rows"
        ],
        "independent_fork_data_bundle_finite_membership_end_rows": fork_bundle[
            "sp500_rows_with_finite_membership_end"
        ],
        "independent_fork_data_bundle_valid_paper_input": False,
        "paper_numeric_tables_audited": [1, 2],
        "paper_numeric_table_cells_total": 106,
        "paper_numeric_result_cells_total": 100,
        "paper_numeric_configuration_cells_total": 6,
        "paper_table_cell_counts": {"1": 6, "2": 100},
        "native_paper_table_result_cells_reproduced": 0,
        "native_paper_table_result_cells_corroborated": 5,
        "paper_table_result_cells_unavailable": 95,
        "published_non_table_claims_total": 26,
        "published_non_table_result_claims_total": 18,
        "native_non_table_result_claims_reproduced": 0,
        "paper_specification_gaps_total": len(gaps),
        "source_mechanism_dimensions_total": len(mechanisms),
        "source_mechanism_status_counts": dict(mechanism_counts),
        "source_mechanism_component_matches_or_analogues": sum(
            bool(row["paper_mechanism_credit"]) for row in mechanisms
        ),
        "source_mechanism_fully_faithful": False,
        "paper_era_tracked_files_total": len(paper_era_inventory),
        "paper_era_python_files_compiled": paper_era_component["python_files_compiled"],
        "paper_era_factor_csv_files": len(paper_era_factors),
        "paper_era_factor_expression_rows": sum(
            int(row["expression_rows"]) for row in paper_era_factors
        ),
        "paper_era_qlib_mlflow_run_records": len(run_records),
        "paper_era_qlib_mlflow_records_with_fitted_models": sum(
            bool(row["fitted_lightgbm_state_shipped"]) for row in run_records
        ),
        "paper_era_fitted_lightgbm_states_loaded": sum(
            bool(row["fitted_lightgbm_state_loaded"]) for row in run_records
        ),
        "paper_era_fitted_lightgbm_state_execution_deterministic": (
            paper_era_component["qlib_environment"][
                "fitted_lightgbm_state_execution_deterministic"
            ]
        ),
        "paper_era_native_backtests_reexecuted": paper_era_component[
            "qlib_environment"
        ]["native_backtests_reexecuted"],
        "paper_era_matching_run_id": run_input_audit["matching_run_id"],
        "paper_era_matching_run_generated_factor_features": run_input_audit[
            "matching_run_generated_factor_features"
        ],
        "paper_era_run_time_public_factor_candidates": run_input_audit[
            "run_time_public_us_factor_candidate_rows"
        ],
        "paper_era_exact_generated_factor_lineage_recovered": run_input_audit[
            "exact_generated_factor_lineage_recovered"
        ],
        "paper_era_qlib_fallback_archive_sha256": run_input_audit[
            "qlib_data_archive_sha256"
        ],
        "paper_era_qlib_fallback_calendar_start": run_input_audit[
            "qlib_data_calendar_start"
        ],
        "paper_era_qlib_fallback_calendar_end": run_input_audit[
            "qlib_data_calendar_end"
        ],
        "paper_era_qlib_fallback_has_spx_benchmark": run_input_audit[
            "qlib_data_has_spx_feature"
        ],
        "paper_era_qlib_fallback_covers_test_period": run_input_audit[
            "paper_test_period_covered"
        ],
        "paper_era_matching_run_replayable_from_released_inputs": run_input_audit[
            "matching_run_replayable_from_released_inputs"
        ],
        "paper_era_qlib_mlflow_full_table_row_matches": sum(
            bool(row["all_five_display_cells_match"]) for row in run_records
        ),
        "paper_era_qlib_mlflow_display_cells_corroborated": sum(
            int(row["paper_result_cells_corroborated"]) for row in run_records
        ),
        "paper_era_named_alpha101_reference_rows": paper_era_component[
            "named_alpha101_reference_rows"
        ],
        "paper_era_loaded_alpha101_csv_rows": paper_era_component[
            "loaded_alpha101_csv_rows"
        ],
        "paper_era_figure4_candidate_factor_rows": paper_era_component[
            "figure4_candidate_factor_rows"
        ],
        "paper_era_figure4_candidate_parseable_rows": paper_era_component[
            "figure4_candidate_parseable_rows"
        ],
        "paper_era_ast_component_executable": True,
        "tracked_source_files_total": len(inventory),
        "post_paper_dsl_expressions_shipped": 13,
        "post_paper_registry_metric_entries": len(registry),
        "post_paper_registry_entries_receiving_paper_credit": 0,
        "current_post_paper_data_release_available": True,
        "current_post_paper_data_release_bytes": 524248466,
        "current_post_paper_data_release_valid_paper_input": False,
        "native_paper_data_snapshot_shipped": False,
        "native_paper_factor_pool_shipped": True,
        "native_paper_factor_pool_result_lineage_proven": False,
        "native_paper_llm_trajectories_shipped": False,
        "native_paper_prompts_shipped": True,
        "native_paper_predictions_or_returns_shipped": False,
        "native_paper_prediction_or_return_series_shipped": False,
        "native_partial_qlib_mlflow_records_shipped": True,
        "native_paper_metric_scalars_shipped": True,
        "native_paper_holdings_or_complete_qlib_recorders_shipped": False,
        "native_paper_baseline_outputs_shipped": False,
        "native_paper_figure_arrays_shipped": False,
        "native_paper_metric_or_figure_arrays_shipped": False,
        "native_source_tests_passed_with_dependency_stubs": 0,
        "native_source_tests_passed_with_real_dependencies": component[
            "upstream_tests"
        ]["tests_passed"],
        "native_source_tests_dependency_faithful": True,
        "current_rewrite_dependency_environment_reproduced": component[
            "dependency_environment_reproduced"
        ],
        "current_rewrite_exact_historical_dependency_versions_recovered": component[
            "exact_historical_dependency_versions_recovered"
        ],
        "current_rewrite_source_modules_imported": component["upstream_tests"][
            "imported_source_modules"
        ],
        "paper_era_dependency_environment_reproduced": paper_era_component[
            "dependency_environment_reproduced"
        ],
        "paper_era_host_dependency_environment_reproduced": paper_era_component[
            "host_environment"
        ]["dependency_environment_reproduced"],
        "paper_era_qlib_dependency_environment_reproduced": paper_era_component[
            "qlib_environment"
        ]["dependency_environment_reproduced"],
        "paper_era_exact_historical_dependency_versions_recovered": (
            paper_era_component["exact_historical_dependency_versions_recovered"]
        ),
        "paper_era_exact_cuda_container_reproduced": paper_era_component[
            "exact_cuda_container_reproduced"
        ],
        "paper_era_dependency_release_cutoff_utc": PAPER_MECHANISM_COMMIT_UTC,
        "paper_era_rdagent_commit_in_environment": paper_era_component[
            "host_environment"
        ]["source_commit_in_environment"],
        "paper_era_qlib_commit_in_environment": paper_era_component[
            "qlib_environment"
        ]["source_commit_in_environment"],
        "paper_era_host_selected_source_modules": paper_era_component[
            "host_environment"
        ]["selected_source_modules"],
        "paper_era_host_source_modules_imported": paper_era_component[
            "host_environment"
        ]["imported_source_modules"],
        "paper_era_host_source_module_failures": len(
            paper_era_component["host_environment"]["module_import_failures"]
        ),
        "paper_era_upstream_offline_tests_passed": paper_era_component[
            "host_environment"
        ]["upstream_offline_tests"]["tests_passed"],
        "paper_era_upstream_offline_tests_failed": paper_era_component[
            "host_environment"
        ]["upstream_offline_tests"]["tests_failed"],
        "native_synthetic_base_factors_executable": 4,
        "native_synthetic_component_deterministic": True,
        "native_synthetic_component_paper_result_reproduction": False,
        "audit_runtime_called_llm_or_market_data_api": False,
        "interpretation": (
            "The official repository has two unrelated roots. Its default main is a July 2026 "
            "CSI1000/Tushare rewrite, but public legacy-main retains a substantial preprint-era "
            "implementation. A pinned February 2025 snapshot contains the multi-stage workflow, "
            "structured hypothesis, prompts, operator library, AST largest-common-subtree matcher, "
            "Alpha101 reference expressions, Qlib/LightGBM configs, feedback loop, and 15 factor CSVs. "
            "The exact RD-Agent commit now resolves in a date-bounded host environment, and a separate "
            "Qlib compatibility environment pins the Dockerfile's exact Qlib commit and declared "
            "PyTorch/SciPy/CatBoost/XGBoost layer. This reproduces the released dependency architecture, "
            "not the exact CUDA image or unknowable versions of requirements the authors left unpinned. "
            "The released implementation is still not the paper's exact objective: SL, PC, numeric "
            "c1/c2, alpha=0.5, beta-weighted ER, GPT-3.5 execution provenance, 20 trial seeds, and exact "
            "factor-to-result lineage are missing or divergent. Seven extensionless Qlib/MLflow run "
            "records were recovered from the same author commit; one S&P500 record matches all five "
            "AlphaAgent Table 2 cells at display precision and ships its executed config plus fitted "
            "LightGBM state. All seven fitted states load natively and deterministically, but without "
            "the input panel they cannot regenerate predictions or metrics. Those 5/100 cells are "
            "author-artifact corroborations, not regenerations: "
            "no predictions, holdings, returns, complete recorder artifacts, baseline outputs, or figure "
            "arrays survive. The exact Qlib downloader falls back to a hash-pinned 450,094,816-byte "
            "US archive whose calendar ends on 2020-11-10 and lacks the configured SPX benchmark, so "
            "it cannot execute the matching run's 2021--2024 test. The public head at the run timestamp "
            "has four US candidate factors while the fitted model requires five generated features; "
            "the later paper snapshot has six after adding two candidates. No combined_factors_df.pkl "
            "exists anywhere in the complete history. Thus neither the exact factor order nor the input "
            "panel can be reconstructed from released artifacts. No paper-result credit is added. "
            "Mechanism faithfulness is substantial, 5/100 Table 2 cells are "
            "corroborated, 0/100 are independently regenerated, and 0/18 additional quantitative result "
            "claims are reproduced. A bounded 2026-08-14 census of all 71 fork default heads found "
            "four divergent tips but zero additional paper results. The sole fork data candidate is an "
            "unaffiliated 2026 bundle whose calendar starts in 2020 and whose S&P500 membership file "
            "has only one finite removal date across 568 rows; it cannot supply the paper's missing "
            "2015 training panel or receive paper credit."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
        "paper_mechanism_file_sha256": PAPER_MECHANISM_SHA256,
    }

    report = f"""# AlphaAgent paper-level conformance audit

Overall verdict: **the paper is not reproduced end to end, but 5/100 Table 2
cells are corroborated by a native author run record and the paper-era
implementation is substantially recovered**. The previous audit looked only at
the rewritten default branch, then missed extensionless MLflow records in the
legacy tree; both omissions made it materially too pessimistic.

## Primary-source pins

- Final paper: {PAPER_URL} (arXiv v2, 2025-06-09; SHA-256 `{PAPER_SHA256}`).
- Original preprint: {PAPER_V1_URL} (10 pages; SHA-256 `{PAPER_V1_SHA256}`).
- Both official PDFs and both matching arXiv source archives are hash-pinned.
  Each source compiles in two passes to the published 10-page count.
- Official repository: {SOURCE_URL}. It has two unrelated Git roots, not one
  continuous history: 8 commits on rewritten `main` and 485 on public
  `legacy-main`, 493 reachable commits in total. The public repository exposes
  only those two heads, with no tags or releases.
- A bounded GitHub GraphQL census on {FORK_DISCOVERY_DATE} covered all 71 fork
  default branches: 57 point at the official legacy head, 10 at the official
  rewrite head, and four are divergent. Each divergent tip is object-pinned and
  audited separately; none receives author-native or paper-result credit.
- Mechanism snapshot: `{PAPER_MECHANISM_COMMIT}` (2025-02-12), before arXiv v1.
  It contains 856 tracked files, including 331 Python modules and 15 factor CSVs.
- The same author commit contains seven Qlib/MLflow run directories (385 files),
  executed on 2025-01-28: four S&P500 and three CSI500 runs. Every directory has
  metrics, parameters, a serialized task/config, and a fitted LightGBM state.
- The paper-era Qlib Dockerfile pins Qlib commit `{QLIB_SOURCE_COMMIT}` and a
  PyTorch 2.2.1/CUDA 12.1 base image, then leaves CatBoost and XGBoost unpinned
  while pinning SciPy 1.11.4. The audit preserves this host/container split.
- The 2025-02-17 preprint-cutoff commit `{PREPRINT_CUTOFF_COMMIT}` removed the
  factor zoo. The audit intentionally pins the earlier mechanism-complete tree
  and records that deletion instead of pretending the cutoff head is runnable.
- Rewritten main: `{commit}` (2026-07-03). Its first commit is
  `{SOURCE_FIRST_COMMIT}` ({first_date}) and has no common ancestor with the
  paper-era branch.

## What genuinely passes

- The all-version lineage contains 106 stable numeric table-cell identities.
  Version 2 revises five S&P500 AlphaForge result values and two test-period
  labels. Three logical figure assets are byte-identical, three are revised,
  and one base-LLM radar figure is added in v2. These are version facts, not
  experimental reproduction credit.
- The complete official two-root closure contains 493 commits, 3,907 blobs,
  3,912 trees, and 2,499 unique historical file paths. All 385 historical
  `saved_mlruns` paths belong to the same seven run IDs already audited; no
  prediction, return series, holding, or portfolio-analysis path is present.
- All 331 Python files in the paper-era snapshot compile under the reconstructed
  Python 3.10 host environment.
- The exact RD-Agent commit is installed with a hard dependency-release cutoff of
  `{PAPER_MECHANISM_COMMIT_UTC}`. Its 153-line freeze passes `pip check`. Of 113
  modules selected by the authors' own import test, 112 import twice with real
  dependencies and zero blocked HTTP attempts. The sole failure is the committed
  developer file `rdagent.components.coder.factor_coder.test`, which opens the
  author's absolute `/home/tangziyi/RD-Agent/.../template_debug.jinjia2` path.
  The authors' singleton test passes twice; their import test therefore remains
  honestly 1/2 rather than being patched or reported green.
- A separate 119-line Qlib compatibility freeze passes `pip check`, installs the
  exact Qlib commit from the Dockerfile, retains SciPy 1.11.4, and resolves
  CatBoost 1.2.7 and XGBoost 2.1.4 using the same historical cutoff. PyTorch
  2.2.1 CPU substitutes for the unavailable CUDA container, so exact-container
  credit remains false.
- All seven shipped LightGBM model strings load twice in that Qlib environment.
  The matching S&P500 artifact is a 9-feature, 3-tree fitted model; deterministic
  zero/one-vector probes and feature-importance summaries are tracked. This proves
  the fitted states are executable, not that their paper inputs or metrics were
  regenerated.
- The exact Qlib downloader and its fallback route are now executed and pinned.
  The 450,094,816-byte US archive has 71,959 entries, 8,994 feature symbols,
  755 S&P500 membership rows, and 5,250 calendar dates from 1999-12-31 through
  2020-11-10. These are primary-source data-provenance facts; because the archive
  has no 2021--2024 observations and no `SPX` feature, they establish a replay
  failure rather than paper-result credit.
- The paper-era AST parser executes twice deterministically. Identical,
  commutative, and partially shared expressions return largest-common-subtree
  sizes 4, 3, and 3. An exact Alpha101 probe matches itself with size 23.
- A historical China candidate file has exactly 15 factors, matching Figure 4's
  caption count, but only 14 parse under the shipped AST grammar and no source
  lineage identifies it as the exact plotted pool. Count agreement is therefore
  candidate evidence, not Figure 4 reproduction.
- The loaded `alpha101.csv` has 116 rows: 101 named Alpha101 references plus 15
  appended generated expressions. That supports the paper's originality path but
  also exposes reference-zoo contamination that must be reported, not hidden.
- The historical source implements the structured hypothesis fields, multi-stage
  proposal/construct/calculate/backtest/feedback loop, factor-expression parser,
  prose description-expression alignment critic, failed/successful implementation
  memory, multi-candidate generation, and metric feedback into later rounds.
- Historical CN/US Qlib configs recover the four OHLCV feature formulas,
  next-day label, train/validation/test segments, full LightGBM kwargs, Qlib
  signal/portfolio records, top-50/drop-5 combined strategies, and stated fees.
- Fifteen historical factor CSVs contain 268 expression rows. Names identify CN,
  US, GP, o1, and DeepSeek candidate pools, but no released lineage proves which
  file or row produced any published metric.
- One full-period S&P500 record, `77b227f86e5a47bab48178cac409a98b`, carries the
  exact paper market/splits, four base factors plus five generated features,
  LightGBM depth 4, top-50/drop-5 strategy, SPX benchmark, open execution and
  5-bp sell cost. Its IC 0.0056356, ICIR 0.0552135, AR 8.7439%, IR 1.0544927,
  and MDD -9.0982% round exactly to all five AlphaAgent S&P500 cells in Table 2.
- Two full-period CSI500 records carry the paper configuration and 8/9 generated
  features, but neither matches the complete five-cell China row. Three other US
  and one China record use a 2020 test start or altered train split and receive
  no paper-cell credit.
- Separately, all 80 tests in the 2026 rewrite pass twice with real AgentScope,
  Tushare, OpenAI, LightGBM, and scikit-learn dependencies; all 72 rewrite
  modules import and no blocked HTTP send is attempted. Its 126-line environment
  freeze is tracked, and four synthetic base factors remain deterministic. This
  closes the rewrite's dependency-test gap, not the paper-era environment or any
  paper result, so these checks receive no paper-result credit.

## Why the paper is still not replicated

- Table 2 has **100 numeric result cells**. **5/100** are corroborated by one
  released native author run artifact; **0/100** have been independently
  regenerated. Eighteen more quantitative result claims in figures/text remain
  0/18. The run export omits predictions, daily returns, holdings/positions and
  complete portfolio-analysis artifacts, so its printed metrics cannot be
  recomputed from primitive outputs.
- The seven run records and factor zoo existed on 2025-02-12 but were removed
  on 2025-02-17. Consequently both the v1 submission cutoff (438 source
  commits) and v2 cutoff (483 commits) contain zero native run directories and
  zero factor-zoo files; recovery depends on earlier public history.
- The exact Baostock CSI500 and Yahoo S&P500 panels, constituent histories, and
  data transformations are absent. The US config points only to unversioned local
  `us_data`; it does not establish frozen panel identity. The paper-era Qlib
  downloader first asks for a versioned 0.9.5 archive, which is unavailable, then
  falls back to the hash-pinned `latest` asset observed on 2026-08-25. That asset
  reports Last-Modified 2024-05-22 but ends on 2020-11-10, lacks the configured
  `SPX` benchmark, does not fully cover validation, and has zero test-period dates.
  It therefore cannot be the missing panel or run the released 2021--2024 task.
- The matching model requires five generated features. At its 2025-01-28 run
  timestamp, the latest public commit contains four US candidate expressions; the
  paper snapshot contains six only after two more were added on 2025-02-12. The
  model stores anonymous `Column_0`--`Column_8` names, and no
  `combined_factors_df.pkl` exists in any reachable Git object. The exact five
  expressions, order, values, and preprocessing lineage are not recoverable.
- RD-Agent's host requirements and the Qlib Dockerfile's CatBoost/XGBoost installs
  were unpinned. A commit-date release cutoff gives a reproducible compatible
  reconstruction, but cannot prove the authors' exact installed wheels. Bouchet's
  CPU environment also does not reproduce the mirrored CUDA 12.1 image digest.
- The code defaults to GPT-4-turbo, while the paper reports GPT-3.5-turbo. The
  executed model/API snapshot, temperature, seeds, token limits, initial research
  directions, and 20 independent trial trajectories are not pinned.
- The paper's displayed regularizer is not faithfully implemented. The source has
  AST largest-subtree matching and a hard retry at duplicated size >=5, but no
  symbolic-length term, free-parameter count, numeric c1/c2 alignment scores,
  alpha=0.5 combination, beta-weighted ER function, normalization, or disclosed
  objective weights/acceptance thresholds.
- The paper says lower ER is better while adding an alignment term described as
  higher-is-better. That sign ambiguity, plus undisclosed alpha/beta weights and
  thresholds, prevents an exact objective even with recovered source.
- Historical run records substantially recover executed model/backtest settings
  and fitted LightGBM states. They expose only anonymous feature columns, however,
  so factor-pool identity, random seeds, predictions, returns, and portfolio paths
  remain missing. Exact metric correspondence is corroboration, not regeneration.
- The only divergent fork with a data candidate is the unaffiliated 2026
  `{FORK_DATA_REPOSITORY}` branch. Its 17,805,441-byte Qlib ZIP has 568 feature
  symbols and a 1,533-day calendar from 2020-01-02 through 2026-02-06, so it omits
  the paper's 2015--2019 training period. More seriously, its `sp500.txt` gives
  only 1/568 rows a finite membership end despite calling the package
  survivorship-bias-free. Its separate 2026 mining summary flags a 1,100% return
  as look-ahead leakage and ships no primitive result arrays. This is useful
  negative evidence, not a paper input or result.

## Honest boundary

The official historical source is much closer to the paper than the rewritten
default branch: this is a **substantial mechanism implementation with one exact
five-cell native output correspondence**, not merely an analogue. It is still not
an end-to-end replication of the published experiments.
The 2026 CSI1000/Tushare data package, DSL expressions, and registry metrics belong
to a disjoint rewrite and receive zero paper credit. The 71-fork census likewise
adds zero paper-result units. Run
`scripts/audit_alphaagent_paper.py` to regenerate the package; `--strict` remains
fail-closed until paper-era inputs, predictions, portfolios, stochastic trial
lineage, and every published result are reproduced.
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
                "ALPHAAGENT_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAAGENT_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_paper.pdf",
            )
        ),
    )
    parser.add_argument(
        "--paper-v1-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAAGENT_PAPER_V1_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_paper_v1.pdf",
            )
        ),
    )
    parser.add_argument(
        "--paper-versions-root",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAAGENT_PAPER_VERSIONS_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_paper_versions",
            )
        ),
    )
    parser.add_argument("--latex-command", default="pdflatex")
    parser.add_argument(
        "--source-python",
        type=Path,
        default=Path(os.environ.get("ALPHAAGENT_SOURCE_PYTHON", DEFAULT_SOURCE_PYTHON)),
    )
    parser.add_argument(
        "--paper-host-python",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAAGENT_PAPER_HOST_PYTHON", DEFAULT_PAPER_HOST_PYTHON
            )
        ),
    )
    parser.add_argument(
        "--paper-qlib-python",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAAGENT_PAPER_QLIB_PYTHON", DEFAULT_PAPER_QLIB_PYTHON
            )
        ),
    )
    parser.add_argument(
        "--paper-qlib-source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAAGENT_PAPER_QLIB_SOURCE_ROOT",
                DEFAULT_PAPER_QLIB_SOURCE_ROOT,
            )
        ),
    )
    parser.add_argument(
        "--paper-qlib-data-archive",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAAGENT_PAPER_QLIB_DATA_ARCHIVE",
                DEFAULT_PAPER_QLIB_DATA_ARCHIVE,
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/alphaagent",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(),
        args.paper_pdf.resolve(),
        args.paper_v1_pdf.resolve(),
        args.paper_versions_root.resolve(),
        args.latex_command,
        args.source_python.resolve(),
        args.paper_host_python.resolve(),
        args.paper_qlib_python.resolve(),
        args.paper_qlib_source_root.resolve(),
        args.paper_qlib_data_archive.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
