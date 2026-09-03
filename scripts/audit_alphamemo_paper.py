#!/usr/bin/env python3
"""Audit AlphaMemo paper v1 against its pinned official source release.

The audit enumerates all numeric experimental cells in Tables 2--9, separates
result cells from configuration cells, checks repeated-paper identities, traces
the complete reachable official history and active runner, and executes bounded
deterministic synthetic diagnostics across every released strategy, and replays
the real-data path twice on a frozen current-input probe. It does not call an LLM
during replay or count synthetic/current-input outputs, repeated cells,
source-code presence, or diagnostic strategy runs as paper-result reproduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


SOURCE_COMMIT = "412fee13d905bf5a25f0958aa572b7c668ccb925"
SOURCE_ROOT_COMMIT = "cf3b3d18474b77a61b97d7a72e7fe7b20d1a898f"
SOURCE_URL = "https://github.com/jarrettyu/AlphaMemo"
PAPER_URL = "https://arxiv.org/pdf/2606.20625v1"
PAPER_SHA256 = "64dbd4558ec63a88bbf8fc8245b7eb43443878969531a9661e15c31f6fcedcd0"
SOURCE_ROOT_README_SHA256 = "d87aee04c794447755eb5f861834ea0b39bbd01476b08cbb7130be163b83ec79"
DEFAULT_SOURCE_PYTHON = "/nfs/roberts/project/pi_btk22/zc362/environments/bin/kt-python"
DEFAULT_PAPER_SOURCE_PYTHON = (
    "/nfs/roberts/project/pi_btk22/zc362/environments/current/alphamemo-paper/bin/python"
)
DEFAULT_REAL_DATA_PROVIDER = (
    "/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_us_probe_20"
)
DEFAULT_QLIB_SOURCE = (
    "/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_qlib_source/us_data"
)
DEFAULT_REAL_PROBE_WORK_ROOT = (
    "/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_real_probe_work"
)
REAL_DATA_DRIVER = Path(__file__).with_name("run_alphamemo_real_data_probe.py")
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_REST_COUNT = 1
PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT = 1
PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT = 1
PUBLIC_FORK_GRAPHQL_REF_SHA256 = "8f9540d43255af78fd5687e00df5b0964b8908a85557902b7dbf613f857c0e90"
PUBLIC_FORK_REPOSITORY = "FengxiangHe/alphamemo"
PUBLIC_FORK_URL = "https://github.com/FengxiangHe/alphamemo"
PUBLIC_FORK_HEAD = "36f584514b53fa88ddbb8837e7ae28cbf3f8973c"
PUBLIC_FORK_HEAD_DATE = "2026-05-26T16:04:07Z"
PUBLIC_FORK_AUTHOR_LOGIN = "FengxiangHe"
PUBLIC_FORK_AUTHOR_NAME = "Fengxiang He"
PUBLIC_FORK_AUTHOR_EMAIL = "47729453+FengxiangHe@users.noreply.github.com"
PUBLIC_FORK_README_SHA256 = "54153f288ae31d286a448ad579f241fa280da66c7ea1451cfb27f6853775ce55"
PUBLIC_FORK_DIFF_SHA256 = "523946b952ef7e556daf78f99d0c0dca14e905e7f1649771039ff9ae0e7f9ab1"
PAPER_AUTHORS = (
    "Hang Yu",
    "Zifan Zheng",
    "Jeff Z. Pan",
    "Tongliang Liu",
    "Zhiyong Wang",
    "Fengxiang He",
)

RELEASED_STRATEGIES = ("alphamemo", "sspm", "veto", "structured", "graph", "gp", "random")
ACTIVE_DIAGNOSTIC_SHA256 = {
    "alphamemo": "70b820b215c4fba55edb9381998f64b67f06d67bfb9a429c774083c9a0b92359",
    "sspm": "174ab3ecfdbb133db4934f9a86b154e9f1f0e226cc89f61e126f040242f8df9d",
    "veto": "75609ed4627a63422a0fb1cfee4153d11be85bdc0fc86e097981c1b817a2eeba",
    "structured": "a50916c457ea9e6b8458fadb9384663c00f418e315760bbb22a5512778d98aef",
    "graph": "c279a28ef0644f41f132c7bf2684a58297d57e9b13f709287522e297d93ba2fa",
    "gp": "4595b65e90893f69d5eec424a54cd5695a2657fd74d2c29452e699b5cbf64655",
    "random": "21dd2a7738a2e8c8f8f45d0caceadecdd83b35bb183530a53968a469d9a94be2",
}
ACTIVE_DIAGNOSTIC_BRANCH_COUNTS = {
    "alphamemo": {"motif_prior": 20, "random_or_warmup": 12},
    "sspm": {"lambda_positive": 28, "lambda_zero": 4},
    "veto": {"apv_resample": 24, "warmup": 8},
}

PINNED_SOURCE_SHA256 = {
    "README.md": "2df79fa9f1e5112669110bb4b8df4c94f9a90bc94f0623542b0c48fb4c04d74d",
    "pyproject.toml": "8f554cb584ff999d6504801b0c51ad8c464403676373113113e197d9451c24c1",
    "requirements.txt": "60052cd488ab7fa3e5130a594c1b1f1c90ed96f8fbb3573a8ff804eb685f7e23",
    "environment.yml": "2151faddf34a46f8d3255ee5f22a11a45367eb26b2c49027b297b4cb8a16c6b7",
    "configs/demo.json": "88ef9da7f9badfa565ece811e00ec710fb12349121ab891f09ae9f92d4652f9c",
    "scripts/run_main.sh": "77257d925cdf882f15816db88411cb0d12bcc8821c63c734142f438ee100b636",
    "scripts/collect_results.py": "f6b64c62f9a44ac1856e18f0f5df3279006708d878a77cacf2d3fab2427ed454",
    "scripts/alpha_decay.py": "d7e1f88ab5372207c445e9cdb033d7ac1fb5cbb34cbb3baed1b7dd6060988f1f",
    "scripts/qrun_alphamemo.sh": "763585181461fa76eb948d0d21643d5bd3b5508f5a88915a6ea0b1a5761f944b",
    "sspm/cli.py": "57393f8e07eb42c53b81a566984e7057455ea2f5f86c8f7fb99faee509d1bbf9",
    "sspm/runner.py": "d791034f19d3c720218c62c5b76e7451454cdeeb3238754051f28256ac493cdf",
    "sspm/core/dag.py": "e9445a7184ddce311332314acd3d2d7767369c421a5403c53585943863424a03",
    "sspm/core/motifs.py": "d55ef9e25a49cb231635123209a70c24fdc4920295ff9333a64974633df7da6c",
    "sspm/core/types.py": "58fda3c6c1229cb005e34cc801eeecb3673ce3bc6fbf4354c7b9f62c4fba58ca",
    "sspm/generation/heuristic.py": "64a175a49c37c06ff7af71c21a0935ed2786ff6334effb8087c724c0cb9b1b5f",
    "sspm/generation/openai_compatible.py": "a8dffb012ad4fc3e5d4094babec83fb8604abcb561c45dfd554be5eebd41b594",
    "sspm/memory/residual.py": "c2e8ea489c94aba35e157e92bc811894bd73a0d095b759b796960a18ebbecbe5",
    "sspm/strategies/graph_memory.py": "20c90744382be3a3326ef3c3b4f9352f08ca2db207585609975a0d4da788e356",
    "sspm/strategies/sspm.py": "b77f9330ef16b431ad55969acdcc789c8915b879d75a7c79e129173f0c523a05",
    "sspm/strategies/veto_memory.py": "ac427f4313441a57247a396dd66d2a8a73d0979deef2a860eb4ded502496606f",
    "sspm/evaluation/formula_eval.py": "81d77caa5251f3df4158297d0a8536d9805f142e84b3fe301207a50fcc5b5683",
    "sspm/evaluation/qlib_export.py": "c7ced10d1a1b018ffbd162801044a15b6a15a871f14f744445b1fd95f2d2b80c",
    "templates/qlib_factor_template/conf_cn_combined_kdd_ver.yaml": "251d90128426316a754bcb051388aeab653f0a59071a1943fca547f9779defe8",
    "templates/qlib_factor_template/conf_us_combined_kdd_ver.yaml": "70cb8bcadf8f818bf846632ab556ecddcf100c4b027f61459287daf14e4ad659",
    "tests/test_smoke.py": "20f7d652028256ce7203789f177c800a7c9921e4e398f8523b06d6270dc1772c",
}

METRICS_7 = ("IC", "ICIR", "RankIC", "RankICIR", "AR_pct", "MDD_pct", "Sharpe")
METRICS_4 = ("ICIR", "RankICIR", "AR_pct", "Sharpe")

# entity|CSI500 seven metrics|S&P500 seven metrics
TABLE_2_TEXT = """
Alpha158|0.0053|0.0634|0.0115|0.1188|7.70|-24.34|0.4055|0.0155|0.1300|0.0081|0.0611|14.36|-21.86|0.6186
GP|0.0226|0.2404|0.0326|0.3403|6.75|-30.28|0.3197|0.0062|0.0494|-0.0013|-0.0096|14.10|-24.58|0.6534
LightGBM|0.0095|0.1124|-0.0115|-0.1085|8.85|-33.83|0.4028|0.0133|0.1009|0.0046|0.0377|15.46|-26.67|0.6040
LSTM|0.0222|0.2384|0.0096|0.0939|9.95|-40.23|0.4047|0.0138|0.0853|0.0068|0.0412|16.36|-28.84|0.5792
AlphaGen|0.0311|0.2988|0.0436|0.4156|8.03|-30.99|0.4040|0.0348|0.3569|0.0101|0.1153|19.44|-24.22|0.9471
AlphaGPT|0.0077|0.0909|0.0011|0.0118|8.08|-30.39|0.3903|0.0163|0.1202|0.0005|0.0038|17.36|-26.14|0.7501
AlphaSAGE|0.0031|0.0335|0.0190|0.2341|5.49|-37.12|0.2541|0.0256|0.2187|0.0079|0.0745|14.26|-29.96|0.6040
AlphaAgent|0.0102|0.1150|-0.0156|-0.1437|4.27|-40.16|0.1818|0.0306|0.2569|0.0133|0.1023|19.40|-24.77|0.8077
AlphaMemo (residual)|0.0101|0.1104|0.0165|0.1808|6.97|-26.08|0.3511|0.0410|0.3434|0.0228|0.1984|23.65|-23.62|1.0672
AlphaMemo (balanced)|0.0401|0.3462|0.0496|0.4597|11.63|-23.43|0.6109|0.0288|0.2406|0.0144|0.1207|17.07|-22.54|0.7743
"""

# entity|CSI500 four metrics|S&P500 four metrics
TABLE_3_TEXT = """
Search-ledger only|0.2313|0.3707|7.00|0.3536|0.1414|0.0044|13.80|0.6282
AlphaMemo (balanced)|0.3462|0.4597|11.63|0.6109|0.2406|0.1207|17.07|0.7743
Weaker memory|0.1455|0.2886|5.80|0.3011|0.1001|-0.0299|17.09|0.7393
Stronger memory|0.2208|0.3454|11.57|0.5646|0.1579|0.0402|16.20|0.7105
APV-only memory|0.2405|0.3993|7.72|0.3875|0.1718|0.0243|15.99|0.6493
AlphaMemo (residual)|0.1104|0.1808|6.97|0.3511|0.3434|0.1984|23.65|1.0672
"""

# entity|CSI500 seven metrics|S&P500 seven metrics
TABLE_5_TEXT = """
Search-ledger only|0.0218|0.2313|0.0347|0.3707|7.00|-30.63|0.3536|0.0173|0.1414|0.0006|0.0044|13.80|-26.83|0.6282
AlphaMemo (balanced)|0.0401|0.3462|0.0496|0.4597|11.63|-23.43|0.6109|0.0288|0.2406|0.0144|0.1207|17.07|-22.54|0.7743
AlphaMemo (residual)|0.0101|0.1104|0.0165|0.1808|6.97|-26.08|0.3511|0.0410|0.3434|0.0228|0.1984|23.65|-23.62|1.0672
Weaker memory|0.0138|0.1455|0.0295|0.2886|5.80|-29.10|0.3011|0.0130|0.1001|-0.0039|-0.0299|17.09|-22.64|0.7393
Stronger memory|0.0205|0.2208|0.0283|0.3454|11.57|-26.27|0.5646|0.0196|0.1579|0.0048|0.0402|16.20|-25.19|0.7105
Late weak memory|0.0181|0.2231|0.0137|0.1708|8.57|-32.39|0.3917|0.0109|0.0847|-0.0008|-0.0061|15.60|-23.58|0.6814
Late weak memory, seed 2|0.0285|0.2681|0.0195|0.2329|10.39|-28.80|0.4806|0.0223|0.1736|-0.0010|-0.0076|17.15|-25.66|0.7794
APV-only memory|0.0220|0.2405|0.0363|0.3993|7.72|-30.79|0.3875|0.0242|0.1718|0.0035|0.0243|15.99|-26.06|0.6493
Warmup 180, weak memory|0.0339|0.3291|0.0490|0.5074|10.88|-30.82|0.4850|0.0294|0.2266|0.0048|0.0384|19.37|-24.82|0.8605
Warmup 220, weak memory|0.0155|0.2043|0.0089|0.1039|7.94|-29.77|0.3863|0.0308|0.2322|0.0102|0.0778|19.34|-27.28|0.8623
Warmup 240|0.0150|0.1828|0.0213|0.2341|8.78|-24.59|0.4504|0.0210|0.1609|0.0026|0.0192|17.10|-24.57|0.7607
Weak memory, seed 1|0.0041|0.0402|-0.0024|-0.0224|2.50|-45.00|0.1104|0.0330|0.2410|0.0050|0.0374|22.10|-26.82|0.9340
Balanced, seed 3|0.0291|0.3541|0.0350|0.4462|4.08|-38.90|0.1798|0.0246|0.1910|0.0023|0.0179|18.61|-27.98|0.8042
"""

# entity|market|2022 IC/RankIC|...|2025 IC/RankIC
TABLE_6_TEXT = """
AlphaMemo (balanced)|CSI500|0.0030|0.0048|-0.0090|0.0004|0.0087|0.0209|0.0354|0.0289
AlphaMemo (balanced)|S&P500|0.0186|0.0134|-0.0007|0.0016|0.0036|-0.0131|0.0195|0.0157
Weaker memory|CSI500|0.0152|0.0328|-0.0250|-0.0149|0.0293|0.0399|0.0209|0.0251
Weaker memory|S&P500|0.0201|0.0182|0.0010|0.0000|0.0110|-0.0027|0.0191|0.0125
Stronger memory|CSI500|0.0076|0.0149|-0.0099|-0.0087|0.0275|0.0343|0.0221|0.0245
Stronger memory|S&P500|0.0126|0.0089|0.0041|0.0062|0.0078|-0.0079|0.0172|0.0111
APV-only memory|CSI500|0.0219|0.0385|0.0031|0.0273|0.0320|0.0452|0.0407|0.0596
APV-only memory|S&P500|0.0172|0.0175|0.0083|0.0117|0.0024|-0.0093|0.0164|0.0129
AlphaMemo (residual)|CSI500|0.0066|0.0047|-0.0106|0.0011|0.0111|0.0205|0.0223|0.0181
AlphaMemo (residual)|S&P500|-0.0164|0.0229|0.0651|0.0009|0.0658|0.0335|0.0547|0.0478
"""

TABLE_7_TEXT = """
Random search|5|10.4
Result-level memory|2|34.5
Search-Ledger Agent|5|52.4
AlphaMemo|5|76.0
"""

TABLE_8_TEXT = """
AlphaMemo|76.0
NoGate|34.6
AbsOLM|55.6
ManualMut|33.4
NoAPV|70.8
"""

PAPER_FACTORS = {
    "SSPM_000": (
        "CsRank(TsMin(Div(TsSum(Where(Greater($close,Delay($close,5)),Delta(Log(Add($volume,1.0)),5),0.0),10),"
        "TsStd(TsSum(Where(Greater($close,Delay($close,5)),Delta(Log(Add($volume,1.0)),5),0.0),10),60)),20))",
        (0.0325, 0.4461, 0.5237),
    ),
    "SSPM_017": (
        "TsRank(Where(Greater($close,Delay($close,5)),TsMean(Log(Add($volume,1.0)),5),0.0),20)",
        (0.0268, 0.2877, 0.1979),
    ),
    "SSPM_033": (
        "CsRank(Add(Where(Greater($close,Delay($close,5)),Delta(Log(Add($volume,1.0)),5),0.0),"
        "Where(Less($close,Delay($close,5)),Neg(Delta(Log(Add($volume,1.0)),5)),0.0)))",
        (0.0159, 0.2310, 0.3745),
    ),
    "SSPM_038": (
        "CsRank(Add(CsRank(Where(Greater($close,Delay($close,5)),Delta(Log(Add($volume,1.0)),5),"
        "Neg(Delta(Log(Add($volume,1.0)),5)))),CsRank(Mul(Delta(Log(Add($volume,1.0)),5),Delta($close,5)))))",
        (0.0173, 0.2243, 0.3743),
    ),
    "SSPM_036": (
        "CsRank(Add(CsRank(Where(Greater($close,Delay($close,10)),Delta(Log(Add($volume,1.0)),10),0.0)),"
        "CsRank(Mul(Delta(Log(Add($volume,1.0)),5),Delta($close,5)))))",
        (0.0191, 0.2299, 0.3881),
    ),
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


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    ).stdout


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def source_history_audit(source_root: Path) -> dict[str, Any]:
    commits = []
    for line in git_text(
        source_root,
        "log",
        "--reverse",
        "--format=%H%x1f%aI%x1f%cI%x1f%an%x1f%s",
        "--all",
    ).splitlines():
        commit, authored, committed, author, subject = line.split("\x1f")
        commits.append(
            {
                "commit": commit,
                "authored_at": authored,
                "committed_at": committed,
                "author": author,
                "subject": subject,
            }
        )

    roots = git_text(source_root, "rev-list", "--max-parents=0", "--all").splitlines()
    tags = git_text(source_root, "tag", "--list").splitlines()
    refs = [
        line
        for line in git_text(
            source_root,
            "for-each-ref",
            "--format=%(refname)|%(objectname)",
            "refs/heads",
            "refs/remotes",
        ).splitlines()
        if line
    ]
    local_branches = [line for line in refs if line.startswith("refs/heads/")]
    remote_branches = [
        line
        for line in refs
        if line.startswith("refs/remotes/") and not line.startswith("refs/remotes/origin/HEAD|")
    ]
    changed_paths = [
        line
        for line in git_text(
            source_root,
            "diff",
            "--name-status",
            SOURCE_ROOT_COMMIT,
            SOURCE_COMMIT,
        ).splitlines()
        if line
    ]
    root_readme = subprocess.run(
        ["git", "-C", str(source_root), "show", f"{SOURCE_ROOT_COMMIT}:README.md"],
        check=True,
        capture_output=True,
    ).stdout
    root_readme_text = root_readme.decode("utf-8")
    fsck = subprocess.run(
        ["git", "-C", str(source_root), "fsck", "--no-reflogs", "--unreachable"],
        check=True,
        capture_output=True,
        text=True,
    )
    root_files = git_text(source_root, "ls-tree", "-r", "--name-only", SOURCE_ROOT_COMMIT).splitlines()
    head_files = git_text(source_root, "ls-tree", "-r", "--name-only", SOURCE_COMMIT).splitlines()
    remote_url = git_text(source_root, "remote", "get-url", "origin").strip()
    is_shallow = git_text(source_root, "rev-parse", "--is-shallow-repository").strip() == "true"

    expected_commits = [SOURCE_ROOT_COMMIT, SOURCE_COMMIT]
    if [item["commit"] for item in commits] != expected_commits:
        raise RuntimeError(f"Expected two-commit official history {expected_commits}, found {commits}")
    if roots != [SOURCE_ROOT_COMMIT] or tags or changed_paths != ["M\tREADME.md"]:
        raise RuntimeError("Pinned official source topology changed")
    expected_main_ref = f"refs/heads/main|{SOURCE_COMMIT}"
    expected_origin_main_ref = f"refs/remotes/origin/main|{SOURCE_COMMIT}"
    if local_branches != [expected_main_ref] or remote_branches != [expected_origin_main_ref]:
        raise RuntimeError("Pinned official source branch set changed")
    if is_shallow or remote_url not in {SOURCE_URL, f"{SOURCE_URL}.git"}:
        raise RuntimeError("Pinned official source clone provenance changed")
    if len(root_files) != 49 or len(head_files) != 49:
        raise RuntimeError("Pinned official source tree size changed")
    if sha256_bytes(root_readme) != SOURCE_ROOT_README_SHA256:
        raise RuntimeError("Pinned root-commit README changed")
    expected_readme_fragments = (
        "train: 2016-01-01 to 2020-12-31",
        "validation: 2021-01-01 to 2021-12-31",
        "test/backtest: 2022-01-01 to 2025-12-26",
        "budget=500",
        "batch_size=10",
        "warmup=200",
        "memory_weight=0.05",
        "motif_sample_size=4",
        "random_motif_prob=0.35",
        "max_factors=50",
        "build approximate Qlib-format OHLCV data from Yahoo Finance",
        "For final paper numbers, use a stable data snapshot",
    )
    if not all(fragment in root_readme_text for fragment in expected_readme_fragments):
        raise RuntimeError("Pinned root-commit README evidence changed")
    if fsck.stdout.strip() or fsck.stderr.strip():
        raise RuntimeError("Unexpected unreachable or corrupt objects in pinned clone")

    return {
        "scope": "all locally reachable official-clone refs",
        "remote_url": remote_url,
        "is_shallow_repository": is_shallow,
        "reachable_commit_count": len(commits),
        "root_commit_count": len(roots),
        "branch_and_remote_refs": refs,
        "local_branch_count": len(local_branches),
        "remote_tracking_branch_count": len(remote_branches),
        "tag_count": len(tags),
        "unreachable_object_output_empty": True,
        "commits": commits,
        "root_to_head_changed_paths": changed_paths,
        "root_tree_file_count": len(root_files),
        "head_tree_file_count": len(head_files),
        "root_readme_sha256": SOURCE_ROOT_README_SHA256,
        "root_readme_recovered_configuration": {
            "train": "2016-01-01 to 2020-12-31",
            "validation": "2021-01-01 to 2021-12-31",
            "test_and_backtest": "2022-01-01 to 2025-12-26",
            "strategy": "alphamemo",
            "budget": 500,
            "batch_size": 10,
            "label_days": 20,
            "warmup": 200,
            "memory_weight": 0.05,
            "motif_sample_size": 4,
            "random_motif_prob": 0.35,
            "max_factors": 50,
        },
        "root_readme_data_warning": (
            "Yahoo builders are approximate; final paper numbers require a stable data snapshot "
            "with exact provider paths and coverage."
        ),
        "historical_native_result_artifacts_found": False,
        "paper_result_reproduction": False,
    }


def public_fork_audit(
    fork_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Audit the complete dated public-fork surface without result inflation."""
    head = git_head(fork_root)
    remote_url = git_text(fork_root, "remote", "get-url", "origin").strip()
    is_shallow = git_text(fork_root, "rev-parse", "--is-shallow-repository").strip() == "true"
    refs = [
        line
        for line in git_text(
            fork_root,
            "for-each-ref",
            "--format=%(refname)|%(objectname)",
            "refs/heads",
            "refs/remotes",
            "refs/tags",
        ).splitlines()
        if line
    ]
    expected_refs = {
        f"refs/heads/main|{PUBLIC_FORK_HEAD}",
        f"refs/remotes/origin/HEAD|{PUBLIC_FORK_HEAD}",
        f"refs/remotes/origin/main|{PUBLIC_FORK_HEAD}",
    }
    if head != PUBLIC_FORK_HEAD or set(refs) != expected_refs:
        raise RuntimeError("Pinned AlphaMemo public-fork head or refs changed")
    if is_shallow or remote_url not in {PUBLIC_FORK_URL, f"{PUBLIC_FORK_URL}.git"}:
        raise RuntimeError("Pinned AlphaMemo public-fork clone provenance changed")

    extra_commits = [
        line
        for line in git_text(
            fork_root, "rev-list", PUBLIC_FORK_HEAD, "--not", SOURCE_COMMIT
        ).splitlines()
        if line
    ]
    changed_paths = [
        line
        for line in git_text(
            fork_root,
            "diff",
            "--name-status",
            SOURCE_COMMIT,
            PUBLIC_FORK_HEAD,
        ).splitlines()
        if line
    ]
    metadata = git_text(
        fork_root,
        "show",
        "-s",
        "--format=%aI%x1f%an%x1f%ae%x1f%s",
        PUBLIC_FORK_HEAD,
    ).strip().split("\x1f")
    readme = git_bytes(fork_root, "show", f"{PUBLIC_FORK_HEAD}:README.md")
    diff = git_bytes(
        fork_root,
        "diff",
        SOURCE_COMMIT,
        PUBLIC_FORK_HEAD,
        "--",
        "README.md",
    )
    tree_paths = git_text(
        fork_root, "ls-tree", "-r", "--name-only", PUBLIC_FORK_HEAD
    ).splitlines()
    if extra_commits != [PUBLIC_FORK_HEAD] or changed_paths != ["M\tREADME.md"]:
        raise RuntimeError("AlphaMemo public-fork commit/path surface changed")
    if metadata != [
        "2026-05-26T17:04:07+01:00",
        PUBLIC_FORK_AUTHOR_NAME,
        PUBLIC_FORK_AUTHOR_EMAIL,
        "Update README.md",
    ]:
        raise RuntimeError(f"AlphaMemo public-fork commit metadata changed: {metadata}")
    if len(tree_paths) != 49:
        raise RuntimeError("AlphaMemo public-fork tree size changed")
    if sha256_bytes(readme) != PUBLIC_FORK_README_SHA256:
        raise RuntimeError("AlphaMemo coauthor-fork README bytes changed")
    if sha256_bytes(diff) != PUBLIC_FORK_DIFF_SHA256:
        raise RuntimeError("AlphaMemo coauthor-fork README diff changed")
    readme_text = readme.decode("utf-8")
    expected_author_line = (
        "author={Yu, Hang and Zheng, Zifan and Pan, Jeff Z. and Liu, Tongliang "
        "and Wang, Zhiyong and He, Fengxiang}"
    )
    if expected_author_line not in readme_text or "author={...}" in readme_text:
        raise RuntimeError("AlphaMemo coauthor-fork author metadata changed")
    if PUBLIC_FORK_AUTHOR_NAME not in PAPER_AUTHORS:
        raise RuntimeError("AlphaMemo public-fork author no longer matches the paper author list")

    branch_rows = [
        {
            "repository": PUBLIC_FORK_REPOSITORY,
            "branch": "main",
            "head_commit": PUBLIC_FORK_HEAD,
            "repository_created_at": "2026-05-26T16:02:20Z",
            "repository_pushed_at": "2026-05-26T16:04:08Z",
            "head_committed_at": PUBLIC_FORK_HEAD_DATE,
            "head_author_login": PUBLIC_FORK_AUTHOR_LOGIN,
            "head_author_name": PUBLIC_FORK_AUTHOR_NAME,
            "head_author_email": PUBLIC_FORK_AUTHOR_EMAIL,
            "head_subject": "Update README.md",
        }
    ]
    canonical_refs = [
        f'{row["repository"]}\t{row["branch"]}\t{row["head_commit"]}' for row in branch_rows
    ]
    canonical_sha256 = sha256_bytes(
        "".join(f"{line}\n" for line in canonical_refs).encode("utf-8")
    )
    if canonical_sha256 != PUBLIC_FORK_GRAPHQL_REF_SHA256:
        raise RuntimeError("AlphaMemo public-fork branch-ref census changed")

    unique_heads = [
        {
            "head_commit": PUBLIC_FORK_HEAD,
            "repository": PUBLIC_FORK_REPOSITORY,
            "branch": "main",
            "extra_commit_count_beyond_official_head": 1,
            "extra_changed_path_count": 1,
            "extra_changed_paths": "README.md",
            "paper_author_identity_match": True,
            "paper_author_identity": PUBLIC_FORK_AUTHOR_NAME,
            "placeholder_bibtex_authors_replaced_with_paper_authors": True,
            "native_input_trajectory_factor_pool_prediction_return_or_metric_added": False,
            "classification": "paper_coauthor_provenance_only_readme_change",
            "paper_result_credit": False,
        }
    ]
    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "github_rest_reported_forks": PUBLIC_FORK_REST_COUNT,
        "graphql_accessible_forks": PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT,
        "graphql_accessible_branch_refs": PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT,
        "graphql_accessible_branch_ref_census_sha256": canonical_sha256,
        "unique_heads": 1,
        "divergent_heads_reviewed": 1,
        "divergent_extra_commits_reviewed": 1,
        "divergent_changed_paths_reviewed": 1,
        "paper_coauthor_authored_divergent_heads": 1,
        "coauthor_identity": PUBLIC_FORK_AUTHOR_NAME,
        "coauthor_is_named_paper_author": True,
        "coauthor_fork_only_replaces_placeholder_bibtex_author_metadata": True,
        "coauthor_fork_readme_sha256": PUBLIC_FORK_README_SHA256,
        "coauthor_fork_diff_sha256": PUBLIC_FORK_DIFF_SHA256,
        "native_input_trajectory_factor_pool_prediction_return_or_metric_paths_discovered": 0,
        "exact_paper_result_table_or_figure_paths_discovered": 0,
        "paper_result_credit": False,
    }
    return branch_rows, unique_heads, summary


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _two_market_rows(table: int, text: str, metrics: Sequence[str]) -> list[dict[str, Any]]:
    rows = []
    for line in text.strip().splitlines():
        entity, *values = line.split("|")
        if len(values) != 2 * len(metrics):
            raise RuntimeError(f"Malformed Table {table} row: {line}")
        for market, part in zip(("CSI500", "S&P500"), (values[: len(metrics)], values[len(metrics) :])):
            for metric, value in zip(metrics, part):
                rows.append(
                    {
                        "paper_table": table,
                        "entity": entity,
                        "market": market,
                        "period": "aggregate",
                        "metric": metric,
                        "paper_value": float(value),
                        "cell_role": "result",
                    }
                )
    return rows


def paper_numeric_rows() -> list[dict[str, Any]]:
    rows = []
    rows.extend(_two_market_rows(2, TABLE_2_TEXT, METRICS_7))
    rows.extend(_two_market_rows(3, TABLE_3_TEXT, METRICS_4))
    rows.extend(
        [
            {"paper_table": 4, "entity": "Balanced", "market": "", "period": "", "metric": "warmup", "paper_value": 200.0, "cell_role": "configuration"},
            {"paper_table": 4, "entity": "Balanced", "market": "", "period": "", "metric": "memory_weight", "paper_value": 0.05, "cell_role": "configuration"},
            {"paper_table": 4, "entity": "Balanced", "market": "", "period": "", "metric": "motif_sample_size", "paper_value": 4.0, "cell_role": "configuration"},
            {"paper_table": 4, "entity": "Balanced", "market": "", "period": "", "metric": "random_motif_probability", "paper_value": 0.35, "cell_role": "configuration"},
            {"paper_table": 4, "entity": "Residual", "market": "", "period": "", "metric": "warmup", "paper_value": 300.0, "cell_role": "configuration"},
            {"paper_table": 4, "entity": "Residual", "market": "", "period": "", "metric": "memory_weight", "paper_value": 0.05, "cell_role": "configuration"},
        ]
    )
    rows.extend(_two_market_rows(5, TABLE_5_TEXT, METRICS_7))
    for line in TABLE_6_TEXT.strip().splitlines():
        entity, market, *values = line.split("|")
        for year, pair in zip(("2022", "2023", "2024", "2025"), (values[0:2], values[2:4], values[4:6], values[6:8])):
            for metric, value in zip(("IC", "RankIC"), pair):
                rows.append(
                    {
                        "paper_table": 6,
                        "entity": entity,
                        "market": market,
                        "period": year,
                        "metric": metric,
                        "paper_value": float(value),
                        "cell_role": "result",
                    }
                )
    for line in TABLE_7_TEXT.strip().splitlines():
        entity, seeds, effective = line.split("|")
        rows.extend(
            [
                {"paper_table": 7, "entity": entity, "market": "CSI500", "period": "fixed_budget", "metric": "seeds", "paper_value": float(seeds), "cell_role": "configuration"},
                {"paper_table": 7, "entity": entity, "market": "CSI500", "period": "fixed_budget", "metric": "mean_effective_factors", "paper_value": float(effective), "cell_role": "result"},
            ]
        )
    for line in TABLE_8_TEXT.strip().splitlines():
        entity, effective = line.split("|")
        rows.append(
            {"paper_table": 8, "entity": entity, "market": "CSI500", "period": "fixed_budget", "metric": "mean_effective_factors", "paper_value": float(effective), "cell_role": "result"}
        )
    for entity, (_formula, values) in PAPER_FACTORS.items():
        for metric, value in zip(("abs_IC", "abs_ICIR", "abs_RankICIR"), values):
            rows.append(
                {"paper_table": 9, "entity": entity, "market": "CSI500", "period": "selection", "metric": metric, "paper_value": value, "cell_role": "result"}
            )
    expected = {2: 140, 3: 48, 4: 6, 5: 182, 6: 80, 7: 8, 8: 5, 9: 15}
    if Counter(row["paper_table"] for row in rows) != expected:
        raise RuntimeError("Paper numeric-cell denominator changed")
    if Counter(row["cell_role"] for row in rows) != {"result": 474, "configuration": 10}:
        raise RuntimeError("Paper result/configuration boundary changed")
    return rows


def result_conformance() -> list[dict[str, Any]]:
    config_matches = {
        (4, "Balanced", "warmup"): 200.0,
        (4, "Balanced", "memory_weight"): 0.05,
        (4, "Balanced", "motif_sample_size"): 4.0,
        (4, "Balanced", "random_motif_probability"): 0.35,
    }
    rows = []
    for row in paper_numeric_rows():
        key = (row["paper_table"], row["entity"], row["metric"])
        if key in config_matches:
            observed: Any = config_matches[key]
            status = "configuration_match_active_official_runner"
            reason = "scripts/run_main.sh passes the same balanced operating-point value"
        elif row["cell_role"] == "configuration":
            observed = ""
            status = "configuration_not_reproduced_by_released_diagnostic_runner"
            reason = "parameter may be CLI-capable, but no exact paper diagnostic/seed runner is released"
        else:
            observed = ""
            status = "unavailable_missing_native_result_path"
            reason = "no paper data snapshot, native search trajectory/factor pool, or metric output is shipped"
        rows.append(
            {
                **row,
                "native_reproduced_value": observed,
                "absolute_difference": 0.0 if observed != "" else "",
                "status": status,
                "reason": reason,
            }
        )
    return rows


def _result_map(table: int) -> dict[tuple[str, str, str, str], float]:
    return {
        (row["entity"], row["market"], row["period"], row["metric"]): row["paper_value"]
        for row in paper_numeric_rows()
        if row["paper_table"] == table
    }


def paper_internal_identities() -> list[dict[str, Any]]:
    maps = {table: _result_map(table) for table in (2, 3, 5, 7, 8)}
    comparisons: list[tuple[int, int, tuple[str, str, str, str], tuple[str, str, str, str]]] = []
    # Selected balanced/residual metrics: Tables 2 and 3.
    for entity in ("AlphaMemo (balanced)", "AlphaMemo (residual)"):
        for market in ("CSI500", "S&P500"):
            for metric in METRICS_4:
                key = (entity, market, "aggregate", metric)
                comparisons.append((2, 3, key, key))
    # Full balanced/residual rows: Tables 2 and 5.
    for entity in ("AlphaMemo (balanced)", "AlphaMemo (residual)"):
        for market in ("CSI500", "S&P500"):
            for metric in METRICS_7:
                key = (entity, market, "aggregate", metric)
                comparisons.append((2, 5, key, key))
    # Selected Search-ledger/balanced/residual metrics: Tables 3 and 5.
    for entity in ("Search-ledger only", "AlphaMemo (balanced)", "AlphaMemo (residual)"):
        for market in ("CSI500", "S&P500"):
            for metric in METRICS_4:
                key = (entity, market, "aggregate", metric)
                comparisons.append((3, 5, key, key))
    comparisons.append(
        (
            7,
            8,
            ("AlphaMemo", "CSI500", "fixed_budget", "mean_effective_factors"),
            ("AlphaMemo", "CSI500", "fixed_budget", "mean_effective_factors"),
        )
    )
    rows = []
    for left_table, right_table, left_key, right_key in comparisons:
        left = maps[left_table][left_key]
        right = maps[right_table][right_key]
        rows.append(
            {
                "left_table": left_table,
                "right_table": right_table,
                "entity": left_key[0],
                "market": left_key[1],
                "metric": left_key[3],
                "left_value": left,
                "right_value": right,
                "absolute_difference": abs(left - right),
                "status": "paper_internal_identity_match_not_independent_reproduction" if left == right else "paper_internal_identity_mismatch",
            }
        )
    if len(rows) != 69 or any(row["absolute_difference"] != 0 for row in rows):
        raise RuntimeError("Published cross-table identities changed")
    return rows


def source_conformance(source_root: Path) -> list[dict[str, Any]]:
    def text(relative: str) -> str:
        return (source_root / relative).read_text(encoding="utf-8")

    run_main = text("scripts/run_main.sh")
    runner = text("sspm/runner.py")
    graph = text("sspm/strategies/graph_memory.py")
    residual = text("sspm/memory/residual.py")
    motifs = text("sspm/core/motifs.py")
    dag = text("sspm/core/dag.py")
    qlib_data = text("sspm/evaluation/qlib_data.py")
    qlib_export = text("sspm/evaluation/qlib_export.py")
    qrun = text("scripts/qrun_alphamemo.sh")
    generator = text("sspm/generation/openai_compatible.py")
    collect = text("scripts/collect_results.py")
    cli = text("sspm/cli.py")
    rows = [
        ("official_entrypoint", "paper AlphaMemo runner", "scripts/run_main.sh invokes sspm main-table", "component_present"),
        ("official_history", "complete reachable paper-era source history", "non-shallow official clone has two commits; only README.md changes from root to HEAD", "history_audited"),
        ("root_readme_main_configuration", "source-declared current-draft operating point", "root README pins budget=500, batch=10, warmup=200, weight=.05, motif sample=4, random=.35, max factors=50", "historical_configuration_recovered"),
        ("paper_markets", "CSI500 and S&P500", "official runner defaults to csi500 sp500", "configuration_match"),
        ("paper_split", "train 2016-2020; validation 2021; test 2022-2025-12-26", "paper2025 preset matches exact dates", "configuration_match"),
        ("label_horizon", "20 trading days", "official runner LABEL_DAYS=20 and Qlib label is h-day close-to-close", "configuration_match"),
        ("balanced_operating_point", "warmup=200 wm=.05 motif sample=4 prand=.35", "all four values match official runner", "configuration_match"),
        ("residual_operating_point", "residual SSPM warmup=300 wm=.05", "CLI supports sspm parameters; no official residual experiment command", "capable_but_no_released_run_path"),
        ("admission_quality_threshold", "tau_q=0.10 absolute ICIR", "official run_main.sh passes SUCCESS_ICIR=0.02", "mismatch_active_runner"),
        ("children_per_parent", "five children per selected parent", "batch=10 selects up to 10 parents and proposes one child per parent", "mismatch_active_runner"),
        ("parent_context", "category, quality bucket, depth bucket, retrieval-frequency bucket", "ResidualMemory key is only (category,motif)", "mismatch"),
        ("ast_diff_motif", "typed canonical AST differencing and normalized edit script", "motifs.py compares regex-derived operator/window/feature sets", "mismatch"),
        ("motifs_observed_not_commands", "labels extracted after generation, not hand-written mutation commands", "selected motif is explicitly sent to LLM as Requested edit motif", "mismatch"),
        ("residual_baseline", "weighted historical children from same full parent context", "source averages child quality only within low/medium/high parent-quality bucket", "mismatch"),
        ("confidence_gate", "n/(n+kappa) times min(1, abs(mu)/(sigma+epsilon))", "source combines count gate, beta-posterior entropy certainty, and variance penalty", "mismatch"),
        ("warmup_schedule", "zero through t0 then gradual ramp over Tw", "balanced graph strategy switches from random/warmup to full memory after one threshold", "mismatch"),
        ("apv_exclusion", "vetoed action excluded; choose next-best non-vetoed action", "balanced scorer retains vetoed motifs with negative severity and may select one", "mismatch"),
        ("ledger_all_evaluated_children", "add all evaluated children and edges", "runner adds to FactorDAG only when success and result.ok", "mismatch"),
        ("invalid_failure_memory", "invalid attempts update failure memory", "strategy update records failures, including invalid evaluations", "component_match"),
        ("lineage_prompt_context", "prompt includes parent lineage trace", "generator supports optional context but graph strategy never supplies it", "missing_active_path"),
        ("factor_length_threshold", "40", "generation request caps formula strings at 280 characters; no 40-unit admission check", "mismatch_or_unit_undisclosed"),
        ("factor_pool_capacity", "50 during common protocol", "export truncates to 50 only after search; search DAG is uncapped", "partial_mismatch"),
        ("fixed_budget_size", "same disclosed generation budget", "paper never gives numeric B; official main defaults to 500", "paper_underspecified"),
        ("fixed_budget_seeds", "5/2/5/5 by method", "benchmark defaults to seeds 0,1,2 and no paper diagnostic command is released", "mismatch_missing_runner"),
        ("mechanism_ablation_runner", "NoGate, AbsOLM, ManualMut, NoAPV", "none of these named variants/removed-component paths exist", "missing"),
        ("main_baseline_runner", "eight baselines in Table 2", "official runner strategies only alphamemo; collectors do not execute paper baselines", "missing"),
        ("native_input_snapshot", "exact CSI500/S&P500 Qlib panels", "current-download builder scripts only; no data snapshot", "missing"),
        ("qlib_template_resolution", "main-table resolves its repository-local Qlib templates", "qlib_data.py sets SELF_EVO_ROOT to parents[3], one level above the repository, so raw real-data export fails after search", "broken_active_path"),
        ("qlib_backtest_entrypoint_mode", "advertised qrun wrapper is directly executable", "scripts/qrun_alphamemo.sh is tracked and checked out as mode 100644, so raw qlib-backtest raises PermissionError", "broken_active_path"),
        ("factor_admission_to_backtest", "only factors passing the paper admission gate enter the pool/backtest", "main-table exports include_all_ok_candidates=True, so the probe backtests 12 valid candidates even though zero pass the 0.10 success threshold", "mismatch_active_runner"),
        ("native_output_snapshot", "paper trajectories, pools, predictions, returns, and metrics", "no tracked runs/data/result files", "missing"),
        ("representative_factor_snapshot", "five Table 9 formulas and metrics", "none of the factor names/formulas is tracked in source", "missing"),
        ("llm_model", "deepseek/deepseek-v4-flash through OpenRouter", "official runner default matches mutable model alias", "configuration_match_unpinned_endpoint"),
        ("llm_temperature_and_length", "temperature=.7 max generation=180 tokens", "OpenAI-compatible generator defaults match", "configuration_match"),
        ("llm_lineage_and_retry_provenance", "exact calls/responses and retry outcomes", "no prompts/responses/costs are shipped; terminal failures silently use a fixed fallback formula", "missing_and_behavioral_risk"),
        ("dependency_snapshot", "exact environment", "some packages pinned, core numpy/pandas/scipy and API endpoint are not", "partial_unpinned"),
        ("paper_result_collector", "all Tables 2--9", "collect_results reads main/variant metrics but no frozen inputs or outputs", "component_only"),
        ("released_strategy_aliases", "distinct named comparison methods", "structured and graph instantiate the same StructuredSearchStrategy; alphamemo and graphmemo instantiate GraphMemoryStrategy", "aliases_not_distinct_methods"),
        ("released_smoke_memory_branch", "exercise AlphaMemo memory policy", "official 12-step smoke has warmup=30 and never starts a batch beyond step 8", "pre_memory_component_only"),
    ]
    # Fail closed if the specific released paths supporting these observations drift.
    assert 'SUCCESS_ICIR="${SUCCESS_ICIR:-0.02}"' in run_main
    assert 'BATCH_SIZE="${BATCH_SIZE:-10}"' in run_main
    assert "--strategies alphamemo" in run_main
    assert "self.cells[(category, motif)]" in residual
    assert "re.findall" in motifs and "ast.parse" not in motifs
    assert "if success and result.ok" in graph
    assert "np.argsort(-scores)[:k]" in dag
    assert "factor_arrays[: config.max_factors]" in qlib_export
    assert "include_all_ok_candidates: bool = True" in qlib_export
    assert "SELF_EVO_ROOT = Path(__file__).resolve().parents[3]" in qlib_data
    assert (source_root / "scripts/qrun_alphamemo.sh").stat().st_mode & 0o111 == 0
    assert 'exec "${PYTHON_BIN}" -m qlib.cli.run "$@"' in qrun
    assert "Requested edit motif" in generator
    assert "read_variant_dirs" in collect
    assert "paper2025" in cli and "2025-12-26" in cli
    assert "strategy.update(candidate, result, success, step)" in runner
    return [
        {"dimension": dimension, "paper_requirement": paper, "released_evidence": evidence, "status": status}
        for dimension, paper, evidence, status in rows
    ]


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    result_tokens = ("run", "result", "output", "factor", "pool", "checkpoint", "log")
    rows = []
    for relative in git_files(source_root):
        path = source_root / relative
        lower = relative.lower()
        rows.append(
            {
                "file": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "name_looks_like_result_artifact": any(token in lower for token in result_tokens),
                "native_paper_result_artifact": False,
            }
        )
    return rows


def run_native_component_checks(source_root: Path, source_python: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not source_python.exists():
        raise RuntimeError(f"Source Python not found: {source_python}")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(source_root)
    subprocess.run(
        [str(source_python), "-m", "pytest", "-q"],
        cwd=source_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    with tempfile.TemporaryDirectory(prefix="alphamemo-audit-") as tmp:
        hashes = []
        summaries = []
        for index in (1, 2):
            path = Path(tmp) / f"smoke{index}.json"
            subprocess.run(
                [
                    str(source_python), "-m", "sspm", "run", "--strategy", "alphamemo",
                    "--budget", "12", "--batch-size", "4", "--seed", "7", "--n-days", "180",
                    "--n-assets", "40", "--quiet", "--out", str(path),
                ],
                cwd=source_root,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            hashes.append(sha256(path))
            summaries.append(payload["summary"])
        if len(set(hashes)) != 1 or summaries[0] != summaries[1]:
            raise RuntimeError("Pinned native synthetic smoke run is not deterministic")
        expected_summary = {
            "strategy": "alphamemo",
            "n_effective": 5,
            "n_ok": 12,
            "budget": 12,
            "mean_abs_ic_ok": 0.04637932219853949,
            "mean_abs_ic_discovered": 0.05564901407744506,
            "mean_abs_icir_discovered": 0.3618666753391596,
            "mean_abs_ric_discovered": 0.05496439758610393,
            "mean_abs_ricir_discovered": 0.35448448825152046,
        }
        if summaries[0] != expected_summary or hashes[0] != "82b09f8e2dbc77be1553295fad848b17354027b40fcd2e70c964be767f3955c1":
            raise RuntimeError("Pinned native smoke output changed")

        strategy_rows = []
        strategy_payloads: dict[str, dict[str, Any]] = {}
        for strategy in RELEASED_STRATEGIES:
            run_hashes = []
            run_summaries = []
            for index in (1, 2):
                path = Path(tmp) / f"active-{strategy}-{index}.json"
                subprocess.run(
                    [
                        str(source_python), "-m", "sspm", "run", "--strategy", strategy,
                        "--budget", "32", "--batch-size", "4", "--seed", "7", "--n-days", "180",
                        "--n-assets", "40", "--warmup", "8", "--quiet", "--out", str(path),
                    ],
                    cwd=source_root,
                    env=environment,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                payload = json.loads(path.read_text(encoding="utf-8"))
                run_hashes.append(sha256(path))
                run_summaries.append(payload["summary"])
                if index == 1:
                    strategy_payloads[strategy] = payload
            if len(set(run_hashes)) != 1 or run_summaries[0] != run_summaries[1]:
                raise RuntimeError(f"Pinned active {strategy} diagnostic is not deterministic")
            if run_hashes[0] != ACTIVE_DIAGNOSTIC_SHA256[strategy]:
                raise RuntimeError(f"Pinned active {strategy} diagnostic output changed")
            strategy_rows.append(
                {
                    "strategy": strategy,
                    "runs": 2,
                    "sha256": run_hashes[0],
                    "deterministic": True,
                    "budget": 32,
                    "warmup": 8,
                    "n_ok": run_summaries[0]["n_ok"],
                    "n_effective": run_summaries[0]["n_effective"],
                    "mean_abs_ic_ok": run_summaries[0]["mean_abs_ic_ok"],
                    "diagnostic_keys": sorted(strategy_payloads[strategy]["diagnostics"]),
                    "paper_configuration": False,
                    "paper_result_reproduction": False,
                }
            )

        def normalized_events(strategy: str) -> list[dict[str, Any]]:
            rows = json.loads(json.dumps(strategy_payloads[strategy]["events"]))
            for row in rows:
                row.pop("strategy")
            return rows

        if normalized_events("structured") != normalized_events("graph"):
            raise RuntimeError("Released structured/graph alias trajectory changed")

        instrumentation = r'''
import json, sys
from collections import Counter
from sspm.runner import RunConfig, run_search
from sspm.strategies.graph_memory import GraphMemoryStrategy
from sspm.strategies.sspm import SSPMStrategy
from sspm.strategies.veto_memory import VetoMemoryStrategy

strategy = sys.argv[1]
counts = Counter()
if strategy == "alphamemo":
    original = GraphMemoryStrategy._choose_motif
    def wrapped(self, category, step):
        motif, meta = original(self, category, step)
        counts[meta["memory_mode"]] += 1
        return motif, meta
    GraphMemoryStrategy._choose_motif = wrapped
elif strategy == "veto":
    original = VetoMemoryStrategy._choose_motif
    def wrapped(self, category, step):
        motif, meta = original(self, category, step)
        counts[meta["memory_mode"]] += 1
        return motif, meta
    VetoMemoryStrategy._choose_motif = wrapped
else:
    original = SSPMStrategy.propose
    def wrapped(self, n, step):
        candidates = original(self, n, step)
        for candidate in candidates:
            lam = candidate.meta.get("lambda")
            counts["lambda_positive" if lam and lam > 0 else "lambda_zero"] += 1
        return candidates
    SSPMStrategy.propose = wrapped
run_search(
    RunConfig(
        strategy=strategy, budget=32, batch_size=4, seed=7,
        n_days=180, n_assets=40, warmup=8,
    ),
    verbose=False,
)
print(json.dumps(counts, sort_keys=True))
'''
        branch_counts = {}
        for strategy in ACTIVE_DIAGNOSTIC_BRANCH_COUNTS:
            result = subprocess.run(
                [str(source_python), "-c", instrumentation, strategy],
                cwd=source_root,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            branch_counts[strategy] = json.loads(result.stdout)
        if branch_counts != ACTIVE_DIAGNOSTIC_BRANCH_COUNTS:
            raise RuntimeError(f"Pinned active memory branch counts changed: {branch_counts}")

    factor_program = """
import json, numpy as np, sys
from sspm.core.operators import evaluate_formula
from sspm.evaluation.synthetic import make_synthetic_market
formulas=json.loads(sys.argv[1]); market=make_synthetic_market(n_days=180,n_assets=40,seed=123)
out=[]
for name, formula in formulas.items():
    values=evaluate_formula(formula,market.features)
    out.append({'factor':name,'shape':list(values.shape),'finite_fraction':float(np.isfinite(values).mean())})
print(json.dumps(out))
"""
    factor_check = subprocess.run(
        [str(source_python), "-c", factor_program, json.dumps({name: item[0] for name, item in PAPER_FACTORS.items()})],
        cwd=source_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    factor_rows = json.loads(factor_check.stdout)
    for row in factor_rows:
        row.update(
            {
                "native_parser_executable": True,
                "paper_metric_reproduced": False,
                "status": "formula_executes_on_synthetic_data_not_paper_metric_reproduction",
            }
        )
    component = {
        "upstream_test_status": "passed",
        "upstream_test_summary": "1 passed",
        "upstream_tests_passed": 1,
        "source_python": str(source_python),
        "source_python_version": subprocess.run([str(source_python), "--version"], check=True, capture_output=True, text=True).stdout.strip(),
        "synthetic_smoke_runs": 2,
        "synthetic_smoke_sha256": hashes[0],
        "synthetic_smoke_deterministic": True,
        "synthetic_smoke_summary": summaries[0],
        "synthetic_smoke_configured_warmup": 30,
        "synthetic_smoke_max_batch_start_step": 8,
        "synthetic_smoke_memory_policy_branch_exercised": False,
        "synthetic_smoke_scope": "pre-memory parser/evaluator/search-loop diagnostic only",
        "active_strategy_diagnostic": {
            "strategies": list(RELEASED_STRATEGIES),
            "runs_per_strategy": 2,
            "config": {
                "budget": 32,
                "batch_size": 4,
                "seed": 7,
                "n_days": 180,
                "n_assets": 40,
                "warmup": 8,
                "generator": "heuristic",
                "evaluator": "synthetic",
            },
            "all_deterministic": True,
            "memory_branch_counts": branch_counts,
            "structured_and_graph_alias_trajectory_equal": True,
            "rows": strategy_rows,
            "paper_configuration": False,
            "paper_result_reproduction": False,
        },
        "paper_result_reproduction": False,
    }
    return component, factor_rows


def run_native_real_data_probe(
    source_root: Path,
    source_python: Path,
    provider: Path,
    qlib_source: Path,
    work_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if not REAL_DATA_DRIVER.exists():
        raise RuntimeError(f"AlphaMemo real-data probe driver is missing: {REAL_DATA_DRIVER}")
    result = subprocess.run(
        [
            sys.executable,
            str(REAL_DATA_DRIVER),
            "--source-root",
            str(source_root),
            "--source-python",
            str(source_python),
            "--provider",
            str(provider),
            "--qlib-source",
            str(qlib_source),
            "--work-root",
            str(work_root),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(
        (output_dir / "alphamemo_real_data_probe.json").read_text(encoding="utf-8")
    )
    current = payload["frozen_current_data"]
    raw = payload["raw_execution"]
    compatible = payload["compatible_execution"]
    guard = payload["network_guard"]
    if (
        guard["version"] != "alphamemo-python-audit-hook-v2"
        or guard["os_network_sandbox"] is not False
        or guard["positive_controls"]["interpreter_processes"] != 2
        or guard["positive_controls"]["blocked_operations"] != 20
        or guard["positive_controls"]["child_inherits_guard"] is not True
        or guard["startup_attestation_required"] is not True
        or guard["all_required_entrypoints_guarded"] is not True
        or guard["replay_blocked_operations"] != 2
        or guard["replay_network_silent"] is not False
        or guard["blocked_operation_counts"] != {"socket.getaddrinfo": 2}
    ):
        raise RuntimeError("AlphaMemo offline claim lacks a working, attested Python network guard")
    if [row["stage"] for row in guard["stages"]] != ["raw", "compatible-1", "compatible-2"]:
        raise RuntimeError("AlphaMemo network guard stage coverage changed")
    attempts = guard["blocked_attempts"]
    if len(attempts) != 2 or {row["stage"] for row in attempts} != {"compatible-1", "compatible-2"}:
        raise RuntimeError("AlphaMemo blocked-attempt stage coverage changed")
    if not all(any(frame["module"] == "mlflow.telemetry.client" and frame["function"] == "_get_config"
                   for frame in row["call_stack"]) for row in attempts):
        raise RuntimeError("AlphaMemo blocked DNS calls are not the observed MLflow telemetry fetches")
    for stage in guard["stages"]:
        if stage["entrypoints"].get("module:sspm") != 1:
            raise RuntimeError("AlphaMemo main process lacks guard evidence")
        if stage["stage"] != "raw" and any(
            stage["entrypoints"].get(entry) != 1
            for entry in ("module:qlib.cli.run", "file:read_exp_res.py")
        ):
            raise RuntimeError("AlphaMemo child process lacks guard evidence")
    if payload["source_commit"] != SOURCE_COMMIT or not payload["source_unmodified"]:
        raise RuntimeError("AlphaMemo real-data probe changed the pinned source")
    if current["trading_days"] != 2511 or current["market_assets"] != 14:
        raise RuntimeError("AlphaMemo frozen current-data surface changed")
    if raw["returncode"] == 0 or not raw["search_completed"]:
        raise RuntimeError("AlphaMemo raw real-data failure boundary changed")
    if compatible["runs"] != 2 or not compatible["search_byte_identical"]:
        raise RuntimeError("AlphaMemo compatible real-data search is not deterministic")
    if compatible["search_summary"]["n_ok"] != 12:
        raise RuntimeError("AlphaMemo compatible real-data evaluation count changed")
    if compatible["search_summary"]["n_effective"] != 0:
        raise RuntimeError("AlphaMemo compatible real-data admission boundary changed")
    if compatible["n_selected_factors"] != 12 or compatible["metric_count"] != 19:
        raise RuntimeError("AlphaMemo compatible export/backtest surface changed")
    if not compatible["metrics_repeat_atol_1e_12"]:
        raise RuntimeError("AlphaMemo compatible real-data metrics are not repeatable")
    if compatible["network_attempts"] != guard["blocked_attempts"] or compatible["llm_calls"] != 0:
        raise RuntimeError("AlphaMemo real-data replay network-attempt accounting changed")
    if compatible["paper_configuration"] or compatible["paper_result_credit"]:
        raise RuntimeError("AlphaMemo component probe received paper credit")
    if payload["paper_result_cells_reproduced"] != 0:
        raise RuntimeError("AlphaMemo real-data probe overclaimed paper results")
    if not result.stdout.strip():
        raise RuntimeError("AlphaMemo real-data probe emitted no manifest")
    return payload


def verify_pins(source_root: Path, paper_pdf: Path) -> str:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    observed_paper = sha256(paper_pdf)
    if observed_paper != PAPER_SHA256:
        raise RuntimeError(f"Expected paper SHA-256 {PAPER_SHA256}, found {observed_paper}")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        observed = sha256(source_root / relative)
        if observed != expected:
            raise RuntimeError(f"Pinned hash changed for {relative}: {observed}")
    return commit


def build_audit(
    source_root: Path,
    fork_root: Path,
    paper_pdf: Path,
    source_python: Path,
    paper_source_python: Path,
    real_data_provider: Path,
    qlib_source: Path,
    real_probe_work_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    commit = verify_pins(source_root, paper_pdf)
    history = source_history_audit(source_root)
    fork_branches, fork_heads, fork_summary = public_fork_audit(fork_root)
    conformance = result_conformance()
    identities = paper_internal_identities()
    config = source_conformance(source_root)
    source = source_inventory(source_root)
    component, factors = run_native_component_checks(source_root, source_python)
    output_dir.mkdir(parents=True, exist_ok=True)
    real_probe = run_native_real_data_probe(
        source_root,
        paper_source_python,
        real_data_provider,
        qlib_source,
        real_probe_work_root,
        output_dir,
    )

    if len(source) != 49:
        raise RuntimeError(f"Expected 49 tracked source files, got {len(source)}")
    if Counter(row["status"] for row in conformance) != {
        "unavailable_missing_native_result_path": 474,
        "configuration_match_active_official_runner": 4,
        "configuration_not_reproduced_by_released_diagnostic_runner": 6,
    }:
        raise RuntimeError("Pinned numeric conformance boundary changed")
    if len(factors) != 5 or not all(row["native_parser_executable"] for row in factors):
        raise RuntimeError("Published formula parser diagnostic changed")

    write_csv(output_dir / "tables_2_9_conformance.csv", conformance)
    write_csv(output_dir / "paper_internal_identities.csv", identities)
    write_csv(output_dir / "source_mechanism_conformance.csv", config)
    write_csv(output_dir / "representative_factor_parser_audit.csv", factors)
    write_csv(output_dir / "released_source_inventory.csv", source)
    write_csv(output_dir / "public_fork_branch_ref_snapshot.csv", fork_branches)
    write_csv(output_dir / "public_fork_unique_head_inventory.csv", fork_heads)
    (output_dir / "native_synthetic_component.json").write_text(
        json.dumps(component, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "official_source_history.json").write_text(
        json.dumps(history, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "public_fork_census.json").write_text(
        json.dumps(fork_summary, indent=2) + "\n", encoding="utf-8"
    )

    manifest: dict[str, Any] = {
        "audit": "AlphaMemo paper v1 Tables 2--9 versus pinned official source",
        "overall_status": "not_reproduced_native_current_data_pipeline_component_only",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": "arXiv:2606.20625v1",
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "source_commit_date": "2026-05-26",
        "source_history_reachable_commits": history["reachable_commit_count"],
        "source_history_root_commits": history["root_commit_count"],
        "source_history_local_branches": history["local_branch_count"],
        "source_history_remote_tracking_branches": history["remote_tracking_branch_count"],
        "source_history_tags": history["tag_count"],
        "source_history_root_to_head_only_readme_changed": history["root_to_head_changed_paths"] == ["M\tREADME.md"],
        "source_history_native_result_artifacts_found": False,
        "public_fork_census_date": fork_summary["census_date"],
        "public_forks_reported_by_github_rest": fork_summary["github_rest_reported_forks"],
        "public_forks_accessible_via_graphql": fork_summary["graphql_accessible_forks"],
        "public_fork_branch_refs_audited": fork_summary["graphql_accessible_branch_refs"],
        "public_fork_unique_heads_audited": fork_summary["unique_heads"],
        "public_fork_divergent_heads_audited": fork_summary["divergent_heads_reviewed"],
        "public_fork_paper_coauthor_heads_audited": fork_summary[
            "paper_coauthor_authored_divergent_heads"
        ],
        "public_fork_coauthor_provenance_corroborated": True,
        "public_fork_native_result_artifacts_found": False,
        "public_fork_paper_result_credit": False,
        "root_readme_configuration_recovered": True,
        "root_readme_stable_data_snapshot_warning_recovered": True,
        "paper_numeric_tables_audited": [2, 3, 4, 5, 6, 7, 8, 9],
        "paper_numeric_table_cells_total": 484,
        "paper_numeric_result_cells_total": 474,
        "paper_numeric_configuration_cells_total": 10,
        "paper_table_cell_counts": {"2": 140, "3": 48, "4": 6, "5": 182, "6": 80, "7": 8, "8": 5, "9": 15},
        "native_paper_result_cells_reproduced": 0,
        "paper_result_cells_unavailable": 474,
        "active_official_runner_configuration_cells_matched": 4,
        "paper_configuration_cells_not_reproduced_by_diagnostic_runner": 6,
        "paper_pairwise_internal_identity_checks": 69,
        "paper_pairwise_internal_identity_matches": 69,
        "paper_internal_identities_independent_reproductions": 0,
        "tracked_source_files_total": len(source),
        "native_source_tests_passed": 1,
        "paper_declared_python_environment_reproduced": True,
        "paper_declared_python_version": real_probe["environment"]["python"],
        "paper_declared_environment_package_count": real_probe["environment"][
            "package_count"
        ],
        "native_current_data_builder_snapshot_replayed": True,
        "native_current_data_trading_days": real_probe["frozen_current_data"][
            "trading_days"
        ],
        "native_current_data_market_assets": real_probe["frozen_current_data"][
            "market_assets"
        ],
        "native_current_data_benchmark_series": real_probe["frozen_current_data"][
            "benchmark_series"
        ],
        "native_current_data_raw_search_completed": real_probe["raw_execution"][
            "search_completed"
        ],
        "native_current_data_raw_export_failed_template_root": True,
        "native_current_data_raw_qrun_failed_nonexecutable": True,
        "native_current_data_compatible_end_to_end_runs": real_probe[
            "compatible_execution"
        ]["runs"],
        "native_current_data_search_byte_identical": real_probe[
            "compatible_execution"
        ]["search_byte_identical"],
        "native_current_data_valid_factor_evaluations": real_probe[
            "compatible_execution"
        ]["search_summary"]["n_ok"],
        "native_current_data_admitted_factors": real_probe["compatible_execution"][
            "search_summary"
        ]["n_effective"],
        "native_current_data_selected_backtest_factors": real_probe[
            "compatible_execution"
        ]["n_selected_factors"],
        "native_current_data_exported_metric_values": real_probe[
            "compatible_execution"
        ]["metric_count"],
        "native_current_data_metrics_repeat_atol_1e_12": real_probe[
            "compatible_execution"
        ]["metrics_repeat_atol_1e_12"],
        "native_current_data_max_reported_repeat_difference": real_probe[
            "compatible_execution"
        ]["max_reported_repeat_difference"],
        "native_current_data_replay_llm_calls": real_probe["compatible_execution"][
            "llm_calls"
        ],
        "native_current_data_replay_network_attempts": len(
            real_probe["compatible_execution"]["network_attempts"]
        ),
        "native_current_data_network_guard_version": real_probe["network_guard"]["version"],
        "native_current_data_network_guard_selftest_blocked_operations": real_probe[
            "network_guard"
        ]["positive_controls"]["blocked_operations"],
        "native_current_data_network_guard_child_inheritance_verified": True,
        "native_current_data_network_guard_entrypoints_attested": True,
        "native_current_data_network_guard_interpreters": sum(
            row["guarded_interpreters"] for row in real_probe["network_guard"]["stages"]
        ),
        "native_current_data_network_guard_is_os_sandbox": False,
        "native_current_data_replay_network_silent": False,
        "native_current_data_replay_blocked_dns_attempts": 2,
        "native_current_data_blocked_network_origin": "mlflow.telemetry.client._get_config",
        "native_current_data_probe_paper_configuration": False,
        "native_current_data_probe_paper_result_credit": False,
        "native_synthetic_smoke_deterministic": True,
        "native_synthetic_smoke_memory_policy_branch_exercised": False,
        "native_synthetic_smoke_paper_result_reproduction": False,
        "native_released_strategies_diagnosed": len(RELEASED_STRATEGIES),
        "native_active_strategy_diagnostic_runs": 2 * len(RELEASED_STRATEGIES),
        "native_active_strategy_diagnostics_deterministic": True,
        "native_active_memory_branches_exercised": True,
        "native_active_strategy_diagnostics_paper_configuration": False,
        "native_active_strategy_diagnostics_paper_result_reproduction": False,
        "released_structured_and_graph_are_aliases": True,
        "published_representative_formulas_native_parser_executable": 5,
        "published_representative_formula_metrics_reproduced": 0,
        "native_paper_data_snapshot_shipped": False,
        "native_paper_search_trajectories_shipped": False,
        "native_paper_factor_pools_shipped": False,
        "native_paper_predictions_or_returns_shipped": False,
        "native_paper_metric_outputs_shipped": False,
        "native_paper_prompt_response_or_cost_logs_shipped": False,
        "paper_ast_diff_mechanism_implemented_faithfully": False,
        "paper_parent_context_implemented_faithfully": False,
        "paper_active_runner_admission_threshold_matched": False,
        "paper_fixed_budget_size_disclosed": False,
        "paper_fixed_budget_and_ablation_runners_shipped": False,
        "audit_used_external_yahoo_api_to_acquire_frozen_current_snapshot": True,
        "real_data_replay_called_llm_or_external_data_api": False,
        "audit_called_llm_or_external_data_api": True,
        "interpretation": (
            "The complete reachable official history has only two commits and 49-file trees; only README.md "
            "changes, and no historical result artifact exists. Its deleted root README recovers the intended "
            "500-step operating point and explicitly says the Yahoo data builders are approximate. The release "
            "has one accessible public fork and one unique divergent head, authored by paper coauthor Fengxiang "
            "He. Its sole commit changes only README.md to replace placeholder BibTeX authors with the six paper "
            "authors; this corroborates provenance but adds no empirical artifact. The release "
            "is executable at the synthetic-component level: its sole test passes, all seven CLI strategies run "
            "deterministically in bounded diagnostics that activate the available memory branches, and all five "
            "paper formulas execute in the native parser on synthetic data. A separate Python 3.11 environment "
            "with the paper's declared direct pins replays a frozen current Yahoo/Qlib panel. The raw main-table "
            "path completes 12 factor evaluations before failing because qlib_data.py resolves templates one "
            "parent above the repository; the tracked qrun wrapper is also non-executable. With a scratch-only "
            "template symlink and byte-identical executable wrapper copy, two runs complete native factor export, "
            "LightGBM training, predictions, portfolio/cost simulation, and 19 metrics. Search output is byte-"
            "identical and metrics agree within 1e-12. The previous generated socket guard had invalid syntax, "
            "so an empty log was not proof of offline execution. Revalidation uses a compiled CPython audit-hook "
            "guard, 20 blocked loopback/socket/DNS positive controls across parent and child interpreters, and "
            "startup/entrypoint attestations for the main, Qlib, reader, and helper processes. The guard blocks "
            "two MLflow telemetry configuration-fetch DNS attempts, one per compatible run; the workloads are not network-"
            "silent. This is not an operating-system network sandbox. This bounded "
            "14-stock heuristic diagnostic admits zero factors at the 0.10 threshold and receives zero paper "
            "credit. None of that reproduces the paper. "
            "The official 12-step smoke itself never reaches its 30-step memory warmup. No Qlib input snapshot, reported LLM "
            "trajectory, factor pool, prediction, return, or table output is shipped, leaving 0/474 result cells "
            "natively reproduced. The active official runner also uses ICIR threshold 0.02 instead of the paper's "
            "0.10 and does not release the residual/fixed-budget/ablation runs. Source inspection shows deeper "
            "mechanism drift: regex motif extraction instead of typed canonical AST differencing, a category-only "
            "memory key instead of the four-part parent context, a different confidence gate/warmup schedule, "
            "and successful-only DAG insertion rather than adding all evaluated children."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
    }

    report = f"""# AlphaMemo paper-level conformance audit

Overall verdict: **not reproduced**. The official release contains runnable,
deterministic search components, but none of the paper's native inputs,
trajectories, factor pools, predictions, returns, or table outputs.

## Primary sources

- Official paper: {PAPER_URL} (arXiv v1; SHA-256 `{PAPER_SHA256}`).
- Official source: {SOURCE_URL}, commit `{commit}` (2026-05-26).

## Complete public-fork census

- GitHub reported one fork on 2026-08-14, accessible through GraphQL with one
  branch and one unique divergent head. The single extra commit was authored by
  paper coauthor Fengxiang He minutes after the official head.
- That commit changes only `README.md`, replacing `author={{...}}` with the six
  named paper authors. All 49 tree paths otherwise match the official head. This
  is useful author-provenance corroboration, but it adds no paper input, search
  trajectory, factor pool, prediction, return, metric, table, or figure artifact
  and therefore receives zero paper-result credit.

## Complete reachable source history

- The non-shallow official clone contains exactly two reachable commits, one root,
  one `main` lineage, no tags, and no unreachable objects. Both trees contain 49
  files; only `README.md` changed. There is no hidden paper-result tree analogous
  to AlphaAgent's public legacy branch.
- The root README (SHA-256 `{SOURCE_ROOT_README_SHA256}`) recovers the source's
  declared current-draft configuration: budget 500, batch size 10, label horizon
  20, warmup 200, memory weight 0.05, motif sample 4, random motif probability
  0.35, and maximum factor pool 50. It also explicitly calls the Yahoo builders
  approximate and says final numbers require a stable snapshot. Configuration
  provenance is valuable, but it cannot substitute for the absent snapshot.

## What genuinely passes

- The release's one smoke test passes under a compatible Python 3.12 environment.
  Separately, a central Python 3.11.11 environment imports the paper's exact
  declared `pyqlib==0.9.7`, `lightgbm==4.6.0`, `mlflow==3.12.0`, and
  `baostock==0.9.1` pins and passes the author test.
- Two identical native synthetic runs produce the same SHA-256 and the documented
  12-step summary. That smoke has warmup 30, so its last batch starts at step 8 and
  never exercises AlphaMemo's memory-policy branch.
- Two runs of each of all seven released CLI strategy names are deterministic in a
  bounded 32-step synthetic diagnostic with warmup shortened to 8. Instrumentation
  observes AlphaMemo motif-prior, SSPM positive-lambda, and veto APV-resampling
  branches. This validates released control flow only. The configuration is not a
  paper setting, and every diagnostic receives zero paper-result credit.
- `structured` and `graph` produce the same normalized trajectory because both
  names instantiate `StructuredSearchStrategy`; they are aliases, not separate
  replicated methods.
- All five Table 9 formulas execute in the released formula parser on synthetic
  arrays. Their paper metrics cannot be computed without the paper CSI500 panel.
- The active runner matches the two markets, 20-day label, date splits, model alias,
  and all four balanced operating-point values printed in Table 4.
- Sixty-nine pairwise cross-table identities agree exactly. These are repeated
  printed values, never independent empirical reproductions.

## Native current-data pipeline probe

- The released Yahoo builder was run on 2026-08-31 from a pinned official Qlib
  U.S. instrument file. Its first 20 sorted historical symbols yielded 14 market
  assets plus `^GSPC`; `ABC`, `ABK`, `ABMD`, `ABS`, `ACAS`, and `ADS` were no
  longer downloadable. The frozen probe contains 2,511 trading days from
  2016-01-04 through 2025-12-26 and 93 hash-pinned files.
- On that panel, raw `main-table` execution evaluates 12/12 factors, then fails
  during export because `qlib_data.py` defines `SELF_EVO_ROOT` as `parents[3]`,
  one level above the repository. The released qrun wrapper is also tracked as
  mode `100644`, so direct backtest execution raises `PermissionError`.
- A scratch-only template symlink and an executable copy of the byte-identical
  qrun wrapper let the otherwise unchanged source complete twice: factor export,
  LightGBM training, prediction, Top-k/drop portfolio simulation, costs, and all
  19 exported metrics. Search JSON and selected formulas are byte-identical; the
  maximum metric difference across repeats is below `1e-12`. Replay makes zero
  LLM calls; the repaired guard blocks two MLflow telemetry configuration-fetch
  DNS attempts, one per compatible replay.
- This is not a paper configuration. It uses only 14 current-source stocks, a
  heuristic generator, budget 12, warmup 4, and no CSI500. Zero factors pass the
  released 0.10 admission threshold, yet `main-table` still exports and backtests
  all 12 merely valid candidates because `include_all_ok_candidates=True`.
  Therefore all current-input search, prediction, portfolio, and metric outputs
  receive **zero paper-result credit**.

### Network-evidence correction

The earlier generated `sitecustomize.py` contained stray quotes and could fail to
import while Python continued running. Its empty attempt log therefore did not
establish that the guard was active. The updated audit compiles the generated code
and tests actual IPv4/IPv6 connect, connect-ex, UDP send, and four DNS/name-resolution
operations in both parent and child interpreters: all 20 positive-control calls are
blocked. These deliberate loopback-only controls are recorded separately from the
native replay, not reported as workload network traffic.

Every raw/compatible replay must now show startup activation and the required main,
Qlib, and metric-reader entrypoints. Missing or empty logs, startup errors, missing
child evidence, and unexpected attempt patterns fail closed. The corrected native
replays retain the prior search/formula hashes and 19 metrics while recording two
blocked DNS attempts originating at `mlflow.telemetry.client._get_config`, not at
market-data or LLM calls. They are network-restricted, not
network-silent. This is Python audit-hook evidence, **not an OS network sandbox**; it
does not claim to control arbitrary external binaries or native-library syscalls.
The source, current-data snapshot, and 0/474 paper-result boundary are unchanged.

## Why the paper is not replicated

- Across Tables 2--9 there are **484 numeric experimental cells**: 474 results and
  10 configuration cells. **0/474 result cells** have a native released result path.
  Four balanced configuration cells match the official runner; configuration is
  not performance.
- No Qlib CSI500/S&P500 snapshot, exact universe history, LLM request/response log,
  search trajectory, admitted pool, selected-factor artifact, prediction, holding,
  daily return, Qlib recorder, baseline output, random seed run, or table CSV is
  tracked. The current-download data builders cannot recreate the authors' frozen
  data state.
- The bounded real-data replay proves the native downstream pipeline can run only
  after two compatibility repairs; it cannot recover the missing full universe,
  paper-time rows, DeepSeek calls, admitted factor pool, five seeds, or reported
  outputs. Its 19 metrics are diagnostic values, not matches to Tables 2--9.
- The advertised `run_main.sh` uses `SUCCESS_ICIR=0.02`, while the paper specifies
  an admission threshold of 0.10. It runs only one balanced AlphaMemo seed; no exact
  residual, fixed-budget, eight-baseline, or NoGate/AbsOLM/ManualMut/NoAPV runner is
  released. The paper does not disclose the numeric fixed discovery budget.
- The paper describes typed, canonical AST differencing with insert/delete/replace/
  move/parameter edit scripts. Released motif extraction uses regex-derived sets of
  operator names, windows, and features. The selected label is also supplied to the
  generator as a mutation command, contrary to the paper's claim that labels are
  observed after generation rather than hand-written commands.
- The paper context is `(category, quality bucket, depth bucket, retrieval bucket)`;
  released memory is keyed only by `(category, motif)`. Its residual baseline,
  confidence formula, warmup schedule, and balanced APV selection differ from the
  equations, and only admitted successes enter the DAG although the paper says all
  evaluated children enter the ledger.

## Honest boundary

The native synthetic smoke, current-data real-pipeline replay, parser execution,
matching arguments, and internal paper identities remain component evidence. They
receive zero paper-result credit.
Run `scripts/audit_alphamemo_paper.py` to regenerate this package; use `--strict`
to fail until the exact paper inputs, trajectories, pools, outputs, mechanisms, and
all 474 result cells are independently reproduced.
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
        default=Path(os.environ.get("ALPHAMEMO_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_source")),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(os.environ.get("ALPHAMEMO_PAPER_PDF", "/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_paper.pdf")),
    )
    parser.add_argument(
        "--fork-root",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAMEMO_FORK_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_fork",
            )
        ),
    )
    parser.add_argument(
        "--source-python",
        type=Path,
        default=Path(os.environ.get("ALPHAMEMO_SOURCE_PYTHON", DEFAULT_SOURCE_PYTHON)),
    )
    parser.add_argument(
        "--paper-source-python",
        type=Path,
        default=Path(
            os.environ.get("ALPHAMEMO_PAPER_SOURCE_PYTHON", DEFAULT_PAPER_SOURCE_PYTHON)
        ),
    )
    parser.add_argument(
        "--real-data-provider",
        type=Path,
        default=Path(
            os.environ.get("ALPHAMEMO_REAL_DATA_PROVIDER", DEFAULT_REAL_DATA_PROVIDER)
        ),
    )
    parser.add_argument(
        "--qlib-source",
        type=Path,
        default=Path(os.environ.get("ALPHAMEMO_QLIB_SOURCE", DEFAULT_QLIB_SOURCE)),
    )
    parser.add_argument(
        "--real-probe-work-root",
        type=Path,
        default=Path(
            os.environ.get(
                "ALPHAMEMO_REAL_PROBE_WORK_ROOT", DEFAULT_REAL_PROBE_WORK_ROOT
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/alphamemo",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(),
        args.fork_root.resolve(),
        args.paper_pdf.resolve(),
        args.source_python.resolve(),
        args.paper_source_python.absolute(),
        args.real_data_provider.resolve(),
        args.qlib_source.resolve(),
        args.real_probe_work_root.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
