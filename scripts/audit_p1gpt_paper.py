#!/usr/bin/env python3
"""Build a fail-closed primary-source audit for the P1GPT paper.

The arXiv bundle contains the complete manuscript and seven rendered assets,
but not the multi-agent service, prompts, requests, responses, source snapshots,
or backtest runner.  A separate P1GPT-organization repository is an attributable
Neurowatt web client.  Its model endpoint and database are private.

This audit deliberately separates:

* deterministic manuscript reconstruction;
* exact result *verification* recoverable from author-rendered position bars;
* independently recomputed rule baselines from a pinned present-day Yahoo chart
  response (useful, but not a paper-time data-lineage artifact); and
* end-to-end P1GPT agent reproduction, which remains zero.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import statistics
import subprocess
import tarfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_ROOT = Path("/nfs/roberts/scratch/pi_btk22/zc362/p1gpt_audit")
DEFAULT_WEB_DEMO_HISTORY = Path(
    "/nfs/roberts/scratch/pi_btk22/zc362/p1gpt_web_demo_history"
)
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/p1gpt"

WORK_ID = "CensusArxiv251023032"
SYSTEM_ID = "SYS-P1GPT"
ARXIV_ID = "2510.23032"
VERSION = "2510.23032v1"

PDF_PIN = {
    "path": "2510.23032v1.pdf",
    "url": "https://arxiv.org/pdf/2510.23032v1",
    "sha256": "de403cff8dd9a645d1499a7fe91b34bdbdcf2783bd9d7d362b079680e72337ad",
    "pages": 17,
}
SOURCE_PIN = {
    "path": "2510.23032v1.tar",
    "url": "https://export.arxiv.org/e-print/2510.23032v1",
    "sha256": "91feaaf3828e49b2907d08203dda7c4c3560e4f999a4a39960f97ad673a63ce8",
    "file_count": 12,
    "main_sha256": "943a5b914ea123e310671df8762b2a7d0b7a4b88dfa16dd70fd42e09359a93c7",
}
LOCAL_PDF = (
    ROOT
    / "literature_review/papers/"
    "39_p1gpt_a_multi_agent_llm_workflow_module_for.pdf"
)
LOCAL_PDF_SHA256 = PDF_PIN["sha256"]
REBUILD_PIN = {
    "first": "build_v1_a/Main.pdf",
    "repeat": "build_v1_b/Main.pdf",
    "sha256": "52d407e76b15bf40d1fa507553263feaa797a5a7a9a7702303169201a3b9e31c",
    "pages": 17,
    "normalized_text_equal": True,
    "normalized_text_sequence_ratio": 1.0,
    "max_100dpi_raster_mad": 0.279841,
    "max_100dpi_changed_fraction": 0.003759,
}

WEB_DEMO = {
    "repository": "https://github.com/P1GPT/web_demo",
    "commit": "a88a3a7c731063d0d1ca7ac15946eb600753f358",
    "commit_author": "Ray-neurowatt <ray@neurowatt.ai>",
    "commit_time": "2024-12-05T13:42:22Z",
    "archive": "web_demo_a88a3a7c731063d0d1ca7ac15946eb600753f358.tar.gz",
    "repeat_archive": "web_demo_a88a3a7c731063d0d1ca7ac15946eb600753f358.repeat.tar.gz",
    "archive_sha256": "81f201afa31f8a7f277e17d51622ece94bf907a8cc7e0f4a73248a28c5d50e0f",
    "archive_bytes": 22_970,
    "file_count": 38,
    "python_file_count": 22,
    "license": "MIT",
}
WEB_DEMO_HISTORY = {
    "root_commit": "1140ce0afd741becd43d4e0a91acad4f8d7e35b7",
    "commit_count": 36,
    "unique_path_count": 47,
    "branch_heads": {
        "origin/main": "a88a3a7c731063d0d1ca7ac15946eb600753f358",
        "origin/develop": "8269b5e2c08481a0b93f202f6f8df64d619680a0",
        "origin/gke/test": "82a2437e8a025390bc1dd59abe7bcc2bfd91ca9a",
    },
}
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_REST_COUNT = 1
PUBLIC_FORK_GRAPHQL_ACCESSIBLE_COUNT = 1
PUBLIC_FORK_GRAPHQL_BRANCH_REF_COUNT = 1
PUBLIC_FORK_GRAPHQL_REF_SHA256 = "e930ff33bb18d98c30c1b630d936b2cc5d20ca2008d9931cecb4984add10e603"
PUBLIC_FORK_REPOSITORY = "milksteak1111/web_demo"
PUBLIC_FORK_HEAD = WEB_DEMO_HISTORY["branch_heads"]["origin/main"]

YAHOO_PINS = {
    "AAPL": {
        "path": "yahoo_AAPL_current.json",
        "sha256": "f4d0a46f8682884b999dd94c2807785b630664cace6794a17d30d06305e05a84",
    },
    "GOOGL": {
        "path": "yahoo_GOOGL_current.json",
        "sha256": "58eb638643fbc55714002ae69f316238d077d9c96c03d835cf81d0ca6f2647ec",
    },
    "TSLA": {
        "path": "yahoo_TSLA_current.json",
        "sha256": "010229882908fc0b204d650a8d9d1d25a051a645245798eebcd3500aee49056c",
    },
}
YAHOO_QUERY = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    "?period1=1738368000&period2=1759276800&interval=1d"
    "&events=history&includeAdjustedClose=true"
)

FIGURE_KINDS = {
    "images/Workflow.png": "architecture_diagram",
    "images/AAPL_actions_2025-02-01_2025-09-30.png": "author_result_plot",
    "images/GOOGL_actions_2025-02-01_2025-09-30.png": "author_result_plot",
    "images/TSLA_actions_2025-02-01_2025-09-30.png": "author_result_plot",
    "images/strategy_comparison_cum_returns.png": "author_result_plot",
    "images/AAPL_Report_2025-03-24.pdf": "author_case_report",
    "images/AAPL_Report_2025-04-10.pdf": "author_case_report",
}

TABLE_VALUES = {
    "B&H": {
        "AAPL": (2.66, 4.07, 0.56, 7.33),
        "GOOGL": (4.19, 6.42, 1.05, 6.41),
        "TSLA": (6.10, 9.41, 0.52, 16.89),
    },
    "MACD": {
        "AAPL": (-1.87, -2.83, -0.59, 4.79),
        "GOOGL": (2.67, 4.09, 0.83, 4.11),
        "TSLA": (7.36, 11.38, 0.88, 10.69),
    },
    "KDJ+RSI": {
        "AAPL": (2.92, 4.46, 1.24, 1.78),
        "GOOGL": (0.98, 1.49, 0.60, 1.28),
        "TSLA": (8.65, 13.43, 1.13, 6.37),
    },
    "ZMR": {
        "AAPL": (2.50, 3.83, 0.64, 5.46),
        "GOOGL": (-0.62, -0.94, -0.22, 4.69),
        "TSLA": (3.61, 5.53, 0.41, 15.60),
    },
    "SMA": {
        "AAPL": (-3.73, -5.60, -1.03, 7.57),
        "GOOGL": (8.23, 12.76, 2.90, 1.32),
        "TSLA": (6.31, 9.73, 0.68, 11.43),
    },
    "P1GPT": {
        "AAPL": (16.16, 25.53, 3.38, 2.02),
        "GOOGL": (31.64, 51.78, 2.71, 7.08),
        "TSLA": (22.79, 36.57, 2.31, 6.50),
    },
}
METRICS = ("CR", "AR", "SR", "MDD")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = list(rows)
    if not materialized:
        raise ValueError(f"refusing to write empty audit artifact: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(materialized[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(materialized)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def pinned_path(root: Path, relative: str, expected_sha256: str) -> Path:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(path)
    observed = sha256(path)
    if observed != expected_sha256:
        raise ValueError(f"hash mismatch for {path}: {observed}")
    return path


def git(history_root: Path, *args: str, allow_no_match: bool = False) -> str:
    result = subprocess.run(
        ["git", "-C", str(history_root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode and not (allow_no_match and result.returncode == 1):
        raise RuntimeError(
            f"git {' '.join(args)} failed in {history_root}: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def source_history_inventory(history_root: Path) -> list[dict[str, Any]]:
    """Audit every reachable revision of the attributable P1GPT web client."""

    if not (history_root / ".git").is_dir():
        raise FileNotFoundError(history_root / ".git")
    if git(history_root, "rev-parse", "--is-shallow-repository") != "false":
        raise ValueError("P1GPT web-demo history must be a complete non-shallow clone")
    commits = git(history_root, "rev-list", "--all", "--reverse").splitlines()
    if len(commits) != WEB_DEMO_HISTORY["commit_count"]:
        raise ValueError(f"web-demo reachable commit count changed: {len(commits)}")
    if commits[0] != WEB_DEMO_HISTORY["root_commit"]:
        raise ValueError("web-demo root commit changed")
    for branch, expected in WEB_DEMO_HISTORY["branch_heads"].items():
        observed = git(history_root, "rev-parse", branch)
        if observed != expected:
            raise ValueError(f"web-demo branch head changed for {branch}: {observed}")
    all_paths = {
        line
        for line in git(history_root, "log", "--all", "--format=", "--name-only").splitlines()
        if line
    }
    if len(all_paths) != WEB_DEMO_HISTORY["unique_path_count"]:
        raise ValueError(f"web-demo unique path count changed: {len(all_paths)}")

    pipeline_pattern = re.compile(
        r"backtest|experiment|result|metric|position|portfolio|trade|2510\.23032|table",
        re.IGNORECASE,
    )
    paper_content_pattern = (
        r"KDJ|ZMR|2510\.23032|Table 2|"
        r"Given today.?s market conditions|should I buy, sell, or hold"
    )
    rows = []
    for index, commit in enumerate(commits, start=1):
        metadata = git(
            history_root,
            "show",
            "-s",
            "--format=%aI%x1f%an <%ae>%x1f%s",
            commit,
        ).split("\x1f")
        if len(metadata) != 3:
            raise ValueError(f"cannot parse web-demo commit metadata: {commit}")
        paths = git(history_root, "ls-tree", "-r", "--name-only", commit).splitlines()
        candidate_paths = sorted(path for path in paths if pipeline_pattern.search(path))
        content_paths = sorted(
            filter(
                None,
                git(
                    history_root,
                    "grep",
                    "-Il",
                    "-E",
                    paper_content_pattern,
                    commit,
                    "--",
                    allow_no_match=True,
                ).splitlines(),
            )
        )
        reachable_heads = []
        for branch, head in WEB_DEMO_HISTORY["branch_heads"].items():
            ancestor = subprocess.run(
                ["git", "-C", str(history_root), "merge-base", "--is-ancestor", commit, head],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            if ancestor.returncode == 0:
                reachable_heads.append(branch)
            elif ancestor.returncode != 1:
                raise RuntimeError(ancestor.stderr.decode(errors="replace").strip())
        rows.append(
            {
                "repository": WEB_DEMO["repository"],
                "commit_index": index,
                "commit_sha": commit,
                "author_time": metadata[0],
                "author_identity": metadata[1],
                "subject": metadata[2],
                "reachable_branch_heads": ";".join(reachable_heads),
                "tracked_files": len(paths),
                "candidate_paper_pipeline_paths": ";".join(candidate_paths),
                "paper_specific_content_paths": ";".join(content_paths),
                "native_p1gpt_result_pipeline_found": False,
                "paper_result_credit": False,
            }
        )
    if any(row["candidate_paper_pipeline_paths"] for row in rows):
        raise ValueError("candidate paper pipeline path appeared in web-demo history")
    if any(row["paper_specific_content_paths"] for row in rows):
        raise ValueError("paper-specific implementation content appeared in web-demo history")
    return rows


def public_fork_census(
    history_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Audit every accessible P1GPT/web_demo fork branch at the dated census."""
    if git(history_root, "cat-file", "-t", PUBLIC_FORK_HEAD) != "commit":
        raise ValueError("P1GPT public-fork head is absent from the pinned complete history")
    if git(history_root, "rev-parse", "origin/main") != PUBLIC_FORK_HEAD:
        raise ValueError("P1GPT public-fork head no longer equals the official main head")
    extra_commits = git(
        history_root,
        "rev-list",
        PUBLIC_FORK_HEAD,
        "--not",
        WEB_DEMO_HISTORY["branch_heads"]["origin/main"],
    ).splitlines()
    if extra_commits:
        raise ValueError("P1GPT public fork gained a divergent commit surface")

    branch_rows = [
        {
            "repository": PUBLIC_FORK_REPOSITORY,
            "branch": "main",
            "head_commit": PUBLIC_FORK_HEAD,
            "repository_created_at": "2025-08-30T01:29:02Z",
            "repository_pushed_at": "2025-01-23T05:23:18Z",
            "head_committed_at": "2024-12-05T13:42:22Z",
            "head_author_login": "Ray-neurowatt",
            "head_author_name": "Ray-neurowatt",
            "head_author_email": "ray@neurowatt.ai",
            "head_subject": 'fix : remove "json" in gpt.py',
        }
    ]
    canonical_refs = [
        f'{row["repository"]}\t{row["branch"]}\t{row["head_commit"]}' for row in branch_rows
    ]
    canonical_sha256 = hashlib.sha256(
        "".join(f"{line}\n" for line in canonical_refs).encode("utf-8")
    ).hexdigest()
    if canonical_sha256 != PUBLIC_FORK_GRAPHQL_REF_SHA256:
        raise ValueError("P1GPT public-fork branch-ref census changed")

    unique_heads = [
        {
            "head_commit": PUBLIC_FORK_HEAD,
            "repository": PUBLIC_FORK_REPOSITORY,
            "branch": "main",
            "extra_commit_count_beyond_official_main": 0,
            "extra_changed_path_count": 0,
            "head_already_exhausted_in_official_history": True,
            "native_agent_prompt_request_response_signal_return_or_result_added": False,
            "classification": "official_main_history_reachable_no_divergence",
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
        "heads_reachable_from_exhaustively_audited_official_history": 1,
        "divergent_heads_reviewed": 0,
        "divergent_extra_commits_reviewed": 0,
        "divergent_changed_paths_reviewed": 0,
        "native_agent_prompt_request_response_signal_return_or_result_paths_discovered": 0,
        "exact_paper_result_table_or_figure_paths_discovered": 0,
        "paper_result_credit": False,
    }
    return branch_rows, unique_heads, summary


def cited_protocol_lineage() -> list[dict[str, Any]]:
    """Separate the cited protocol from later unaffiliated implementation guesses."""

    return [
        {
            "source": "P1GPT arXiv v1 manuscript",
            "url": "https://arxiv.org/abs/2510.23032v1",
            "source_date": "2025-10-27",
            "relationship": "claiming_paper",
            "kdj_rsi_parameters_or_code": "not_provided",
            "zmr_parameters_or_code": "not_provided",
            "attributable_to_p1gpt_authors": True,
            "available_by_p1gpt_v1": True,
            "native_p1gpt_method_or_result_credit": False,
            "finding": "Names TradingAgents evaluation protocol but supplies only qualitative baseline descriptions.",
        },
        {
            "source": "TradingAgents arXiv v7 manuscript",
            "url": "https://arxiv.org/abs/2412.20138v7",
            "source_date": "2025-06-03",
            "relationship": "explicitly_cited_protocol_paper",
            "kdj_rsi_parameters_or_code": "not_provided",
            "zmr_parameters_or_code": "not_provided",
            "attributable_to_p1gpt_authors": False,
            "available_by_p1gpt_v1": True,
            "native_p1gpt_method_or_result_credit": False,
            "finding": "Appendix defines indicator families qualitatively without windows, thresholds, equilibrium, or action rules.",
        },
        {
            "source": "TradingAgents official v0.1.0 source",
            "url": "https://github.com/TauricResearch/TradingAgents/tree/cc97cb6d5deb10eac370db0c6678e2796a62eba8",
            "source_date": "2025-06-05",
            "relationship": "nearest_official_source_for_cited_protocol",
            "kdj_rsi_parameters_or_code": "not_shipped",
            "zmr_parameters_or_code": "not_shipped",
            "attributable_to_p1gpt_authors": False,
            "available_by_p1gpt_v1": True,
            "native_p1gpt_method_or_result_credit": False,
            "finding": "Official release contains no baseline implementation, metric code, or paper backtest runner.",
        },
        {
            "source": "later unaffiliated TradingAgents replication",
            "url": "https://github.com/lucas020695/tradingagents_replicated/tree/e85988694bbd3cbbcf250bd045b1ac16cd870b2f",
            "source_date": "2025-11-17",
            "relationship": "rejected_post_paper_third_party_guess",
            "kdj_rsi_parameters_or_code": "guessed_14_day_RSI_30_70_and_9_day_KDJ_with_placeholder_J",
            "zmr_parameters_or_code": "guessed_50_day_mean_and_1.5_z_score",
            "attributable_to_p1gpt_authors": False,
            "available_by_p1gpt_v1": False,
            "native_p1gpt_method_or_result_credit": False,
            "finding": "Postdates P1GPT, is unaffiliated, leaves KDJ J as a placeholder, and contradicts P1GPT's stated SMA windows; excluded from native credit.",
        },
    ]


def safe_tar_files(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(path, mode="r:*") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError(f"unsafe archive member: {member.name}")
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError(f"cannot read archive member: {member.name}")
            # GitHub archives have a generated single top-level directory.
            parts = pure.parts
            normalized = (
                "/".join(parts[1:])
                if path.suffixes[-2:] == [".tar", ".gz"]
                else member.name
            )
            files[normalized] = handle.read()
    return files


def paper_sources(audit_root: Path) -> dict[str, bytes]:
    archive = pinned_path(audit_root, SOURCE_PIN["path"], SOURCE_PIN["sha256"])
    files = safe_tar_files(archive)
    if len(files) != SOURCE_PIN["file_count"]:
        raise ValueError(f"paper source file count changed: {len(files)}")
    if sha256_bytes(files["Main.tex"]) != SOURCE_PIN["main_sha256"]:
        raise ValueError("Main.tex changed")
    return files


def classify_paper_source(path: str) -> str:
    if path == "Main.tex":
        return "primary_tex"
    if path.endswith((".bib", ".bbl")):
        return "bibliography"
    if path.endswith(".sty"):
        return "style"
    if path.endswith(".json"):
        return "submission_metadata"
    if path in FIGURE_KINDS:
        return FIGURE_KINDS[path]
    return "other"


def paper_source_inventory(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    return [
        {
            "paper_version": VERSION,
            "source_path": path,
            "bytes": len(value),
            "sha256": sha256_bytes(value),
            "source_kind": classify_paper_source(path),
            "operational_agent_or_backtest_code": False,
            "raw_machine_readable_result_array": False,
            "paper_result_reproduction_credit": False,
        }
        for path, value in sorted(files.items())
    ]


def paper_version_summary(audit_root: Path) -> list[dict[str, Any]]:
    pdf = pinned_path(audit_root, PDF_PIN["path"], PDF_PIN["sha256"])
    source = pinned_path(audit_root, SOURCE_PIN["path"], SOURCE_PIN["sha256"])
    if sha256(LOCAL_PDF) != LOCAL_PDF_SHA256:
        raise ValueError("repository P1GPT PDF changed")
    pages = len(PdfReader(str(pdf)).pages)
    if pages != PDF_PIN["pages"]:
        raise ValueError("paper page count changed")
    return [
        {
            "paper_version": VERSION,
            "paper_url": PDF_PIN["url"],
            "paper_sha256": PDF_PIN["sha256"],
            "repository_pdf_sha256": LOCAL_PDF_SHA256,
            "repository_pdf_byte_identical": sha256(LOCAL_PDF) == sha256(pdf),
            "pages": pages,
            "source_url": SOURCE_PIN["url"],
            "source_sha256": sha256(source),
            "source_file_count": SOURCE_PIN["file_count"],
        }
    ]


def figure_inventory(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    rows = []
    for path, kind in FIGURE_KINDS.items():
        value = files[path]
        if path.endswith(".png"):
            image = Image.open(io.BytesIO(value))
            dimensions = f"{image.width}x{image.height}px"
            pages = ""
        else:
            reader = PdfReader(io.BytesIO(value))
            dimensions = (
                f"{float(reader.pages[0].mediabox.width):g}x"
                f"{float(reader.pages[0].mediabox.height):g}pt"
            )
            pages = len(reader.pages)
        rows.append(
            {
                "source_path": path,
                "asset_kind": kind,
                "bytes": len(value),
                "sha256": sha256_bytes(value),
                "dimensions": dimensions,
                "pages": pages,
                "author_rendered_output_correspondence": kind
                in {"author_result_plot", "author_case_report"},
                "underlying_agent_request_response_or_source_array_shipped": False,
                "faithfully_regenerated_from_native_agent_pipeline": False,
                "paper_result_credit": False,
            }
        )
    return rows


def published_result_ledger() -> list[dict[str, Any]]:
    rows = []
    for method, by_ticker in TABLE_VALUES.items():
        for ticker, values in by_ticker.items():
            for metric, value in zip(METRICS, values):
                rows.append(
                    {
                        "table": "Performance comparison across all methods",
                        "method": method,
                        "ticker": ticker,
                        "metric": metric,
                        "paper_value": f"{value:.2f}",
                        "result_kind": (
                            "native_p1gpt_result" if method == "P1GPT" else "baseline_result"
                        ),
                        "exact_native_agent_pipeline_regeneration": False,
                        "paper_result_credit": False,
                    }
                )
    if len(rows) != 72:
        raise ValueError("published result denominator changed")
    return rows


def parse_yahoo_rows(audit_root: Path, ticker: str) -> list[dict[str, Any]]:
    pin = YAHOO_PINS[ticker]
    path = pinned_path(audit_root, pin["path"], pin["sha256"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    adjusted = result["indicators"]["adjclose"][0]["adjclose"]
    rows = []
    for index, timestamp in enumerate(timestamps):
        rows.append(
            {
                "date": datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(),
                "open": float(quote["open"][index]),
                "high": float(quote["high"][index]),
                "low": float(quote["low"][index]),
                "close": float(quote["close"][index]),
                "volume": int(quote["volume"][index]),
                "adjclose": float(adjusted[index]),
            }
        )
    if len(rows) != 166 or rows[0]["date"] != "2025-02-03" or rows[-1]["date"] != "2025-09-30":
        raise ValueError(f"unexpected Yahoo observation window for {ticker}")
    return rows


def ema(values: Sequence[float], span: int) -> list[float]:
    alpha = 2.0 / (span + 1.0)
    output = []
    for value in values:
        output.append(value if not output else alpha * value + (1 - alpha) * output[-1])
    return output


def metrics_from_positions(
    closes: Sequence[float], positions: Sequence[int]
) -> dict[str, float]:
    if len(closes) != len(positions):
        raise ValueError("price/position length mismatch")
    pnl = [0.0] + [
        positions[index - 1] * (closes[index] - closes[index - 1])
        for index in range(1, len(closes))
    ]
    equity = []
    value = 1000.0
    for change in pnl:
        value += change
        equity.append(value)
    daily_returns = [
        equity[index] / equity[index - 1] - 1.0
        for index in range(1, len(equity))
    ]
    peak = equity[0]
    drawdown = 0.0
    for item in equity:
        peak = max(peak, item)
        drawdown = max(drawdown, (peak - item) / peak)
    cumulative = (equity[-1] / equity[0] - 1.0) * 100.0
    annualized = ((equity[-1] / equity[0]) ** (252.0 / len(closes)) - 1.0) * 100.0
    sharpe = (
        statistics.mean(daily_returns)
        / statistics.pstdev(daily_returns)
        * math.sqrt(252.0)
    )
    return {
        "CR": cumulative,
        "AR": annualized,
        "SR": sharpe,
        "MDD": drawdown * 100.0,
    }


def baseline_positions(method: str, closes: Sequence[float]) -> list[int]:
    if method == "B&H":
        return [1] * len(closes)
    if method == "MACD":
        fast = ema(closes, 12)
        slow = ema(closes, 26)
        macd = [a - b for a, b in zip(fast, slow)]
        signal = ema(macd, 9)
        return [int(a > b) for a, b in zip(macd, signal)]
    if method == "SMA":
        # pandas rolling defaults were not used by the authors.  The printed cells
        # require expanding means until each 10/20-day window is full.
        positions = []
        for index in range(len(closes)):
            short = statistics.mean(closes[max(0, index - 9) : index + 1])
            long = statistics.mean(closes[max(0, index - 19) : index + 1])
            positions.append(int(short > long))
        return positions
    raise ValueError(f"unsupported baseline: {method}")


def recover_plot_positions(image_bytes: bytes, ticker: str) -> list[int]:
    """Recover discrete author-plotted bars, not hidden agent decisions.

    The three PNGs share an exact Matplotlib canvas.  Bars use RGB (136,136,255),
    daily centers map linearly from x=163.5 to 1327.5, and bar tops encode the
    integer position.  Thresholds below are independently evident from the exact
    horizontal pixel levels.  This does not reconstruct why an agent chose them.
    """

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if image.size != (1478, 936):
        raise ValueError(f"unexpected {ticker} plot dimensions: {image.size}")
    color = (136, 136, 255)
    xs = [x for x in range(150, 1400) if image.getpixel((x, 884)) == color]
    runs: list[tuple[int, int]] = []
    if xs:
        start = previous = xs[0]
        for x in xs[1:]:
            if x > previous + 1:
                runs.append((start, previous))
                start = x
            previous = x
        runs.append((start, previous))
    positions = [0] * 166
    assigned: set[int] = set()
    for start, end in runs:
        center = (start + end) / 2.0
        index = round((center - 163.5) * 165.0 / (1327.5 - 163.5))
        tops = [
            y
            for x in range(start, end + 1)
            for y in range(620, 885)
            if image.getpixel((x, y)) == color
        ]
        top = min(tops)
        if ticker == "AAPL":
            value = 3 if top < 675 else 2 if top < 760 else 1
        elif ticker == "GOOGL":
            value = round((886 - top) / 36.25)
        elif ticker == "TSLA":
            value = 2 if top < 700 else 1
        else:
            raise ValueError(ticker)
        if index in assigned or not 0 <= index < 166:
            raise ValueError(f"ambiguous plotted bar for {ticker} at {index}")
        assigned.add(index)
        positions[index] = value
    expected_nonzero = {"AAPL": 103, "GOOGL": 122, "TSLA": 96}[ticker]
    expected_max = {"AAPL": 3, "GOOGL": 7, "TSLA": 2}[ticker]
    if sum(value > 0 for value in positions) != expected_nonzero or max(positions) != expected_max:
        raise ValueError(f"plot-position recovery changed for {ticker}")
    return positions


def result_recovery_checks(
    audit_root: Path, files: Mapping[str, bytes]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    checks = []
    position_rows = []
    method_values: dict[str, dict[str, dict[str, float]]] = {
        method: {} for method in ("B&H", "MACD", "SMA", "P1GPT")
    }
    for ticker in ("AAPL", "GOOGL", "TSLA"):
        yahoo = parse_yahoo_rows(audit_root, ticker)
        closes = [row["close"] for row in yahoo]
        image_path = f"images/{ticker}_actions_2025-02-01_2025-09-30.png"
        recovered = recover_plot_positions(files[image_path], ticker)
        for index, (market, position) in enumerate(zip(yahoo, recovered)):
            position_rows.append(
                {
                    "ticker": ticker,
                    "date": market["date"],
                    "recovered_author_plotted_position": position,
                    "close_from_pinned_current_yahoo_response": f"{market['close']:.12g}",
                    "position_source": image_path,
                    "agent_decision_or_rationale_recovered": False,
                    "paper_result_credit": False,
                }
            )
        method_values["P1GPT"][ticker] = metrics_from_positions(closes, recovered)
        for method in ("B&H", "MACD", "SMA"):
            positions = baseline_positions(method, closes)
            method_values[method][ticker] = metrics_from_positions(closes, positions)

    for method, by_ticker in method_values.items():
        for ticker, observed in by_ticker.items():
            for metric in METRICS:
                paper = TABLE_VALUES[method][ticker][METRICS.index(metric)]
                calculated = observed[metric]
                matched = round(calculated, 2) == paper
                checks.append(
                    {
                        "method": method,
                        "ticker": ticker,
                        "metric": metric,
                        "paper_value": f"{paper:.2f}",
                        "calculated_value": f"{calculated:.12g}",
                        "display_rounding_exact_match": matched,
                        "input_evidence": (
                            "author_rendered_position_bars_plus_pinned_current_yahoo_response"
                            if method == "P1GPT"
                            else "declared_or_conventional_rule_plus_pinned_current_yahoo_response"
                        ),
                        "verification_class": (
                            "author_output_result_verification_not_signal_regeneration"
                            if method == "P1GPT"
                            else "independent_baseline_recalculation_current_snapshot_not_paper_lineage"
                        ),
                        "native_agent_pipeline_executed": False,
                        "paper_time_data_snapshot_shipped": False,
                        "paper_result_reproduction_credit": False,
                    }
                )
    if len(checks) != 48 or len(position_rows) != 498:
        raise ValueError("result-recovery denominator changed")
    return checks, position_rows


def market_snapshot_checks(audit_root: Path) -> list[dict[str, Any]]:
    rows = []
    for ticker in ("AAPL", "GOOGL", "TSLA"):
        data = parse_yahoo_rows(audit_root, ticker)
        rows.append(
            {
                "ticker": ticker,
                "query_url": YAHOO_QUERY.format(ticker=ticker),
                "response_sha256": YAHOO_PINS[ticker]["sha256"],
                "retrieved_for_audit_utc": "2026-08-12T17:19:00Z",
                "rows": len(data),
                "first_date": data[0]["date"],
                "last_date": data[-1]["date"],
                "price_field_used": "unadjusted_close",
                "paper_time_snapshot": False,
                "exact_paper_data_source_identified": False,
                "paper_result_credit": False,
                "boundary": (
                    "present-day API response exactly matches recoverable displayed cells, "
                    "but the paper did not freeze or identify this endpoint/response"
                ),
            }
        )
    return rows


def web_demo_inventory(audit_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    first = pinned_path(audit_root, WEB_DEMO["archive"], WEB_DEMO["archive_sha256"])
    repeat = pinned_path(
        audit_root, WEB_DEMO["repeat_archive"], WEB_DEMO["archive_sha256"]
    )
    if first.read_bytes() != repeat.read_bytes():
        raise ValueError("repeated GitHub archives differ")
    files = safe_tar_files(first)
    if len(files) != WEB_DEMO["file_count"]:
        raise ValueError(f"web-demo file count changed: {len(files)}")
    python_files = [path for path in files if path.endswith(".py")]
    if len(python_files) != WEB_DEMO["python_file_count"]:
        raise ValueError("web-demo Python file count changed")
    for path in python_files:
        compile(files[path], path, "exec")
    combined = b"\n".join(files.values()).decode("utf-8", errors="ignore")
    prompt_block = re.search(
        r"prompt_chart:\s*dict\[str,\s*str\]\s*=\s*\{(?P<body>.*?)\n\s*\}",
        combined,
        flags=re.DOTALL,
    )
    prompt_count = (
        len(re.findall(r'^\s*"[^"]+"\s*:', prompt_block.group("body"), re.MULTILINE))
        if prompt_block
        else 0
    )
    if prompt_count != 5:
        raise ValueError("web-demo prompt count changed")
    rows = [
        {
            "source_path": path,
            "bytes": len(value),
            "sha256": sha256_bytes(value),
            "source_kind": (
                "python" if path.endswith(".py")
                else "environment" if path == "requirements.txt"
                else "runner_or_deployment" if path in {"Dockerfile", "compose.yaml", "deployment.yaml"}
                else "configuration" if path in {"rxconfig.py", "service.yaml", "nginx.conf"}
                else "documentation_or_asset"
            ),
            "paper_agent_or_backtest_result_generator": False,
            "paper_result_array": False,
            "paper_result_credit": False,
        }
        for path, value in sorted(files.items())
    ]
    execution = {
        "repository": WEB_DEMO["repository"],
        "commit": WEB_DEMO["commit"],
        "commit_author": WEB_DEMO["commit_author"],
        "commit_time": WEB_DEMO["commit_time"],
        "archive_sha256": WEB_DEMO["archive_sha256"],
        "repeated_archive_byte_identical": True,
        "tracked_files": len(files),
        "python_files_compiled": len(python_files),
        "python_compile_exit": 0,
        "static_fidelity_tier": "R3",
        "component_correspondence": (
            "attributable pre-paper P1GPT/Neurowatt multimodal chat web client"
        ),
        "client_prompt_cards": prompt_count,
        "paper_daily_prompt_present": False,
        "private_model_endpoint": "http://main-llm:8090/invoke/",
        "model_service_source_shipped": False,
        "database_state_shipped": False,
        "public_test_functions": 0,
        "full_service_started": False,
        "runtime_boundary": (
            "the checked-in client requires an unreleased main-llm service and "
            "private database; committed plaintext credentials were not used or exposed"
        ),
        "paper_result_credit": False,
    }
    return rows, execution


def prompt_inventory() -> list[dict[str, Any]]:
    return [
        {
            "prompt_id": "daily_trading_query",
            "verbatim_paper_template": (
                "Given today's market conditions, should I buy, sell, or hold [TICKER]?"
            ),
            "template_shipped_in_tex": True,
            "complete_system_or_agent_prompts_shipped": False,
            "substituted_runtime_requests_shipped": False,
            "runtime_responses_shipped": False,
            "model_name_version_shipped": False,
            "temperature_seed_shipped": False,
            "prompt_execution_reproduced": False,
            "paper_result_credit": False,
        }
    ]


def mechanism_conformance() -> list[dict[str, Any]]:
    dimensions = [
        ("five-layer architecture", "paper_specification_only", "diagram and prose only"),
        ("controller ISA", "missing_runtime", "no implementation or prompt"),
        ("fundamental ISA", "missing_runtime", "no implementation or prompt"),
        ("technical ISA", "missing_runtime", "no implementation or prompt"),
        ("semiconductor ISA", "missing_runtime", "no implementation or prompt"),
        ("news ISA", "missing_runtime", "no implementation or prompt"),
        ("external search agent", "missing_runtime", "Perplexity is named but no call log/config"),
        ("revenue forecasting agent", "missing_runtime", "no model or output"),
        ("investment recommender", "missing_runtime", "no decision code or prompt"),
        ("market trend agent", "missing_runtime", "no implementation or output"),
        ("overall integration ISA", "missing_runtime", "weights/confidence/fusion are unspecified"),
        ("structured inter-agent protocol", "missing_runtime", "no schema/template/message trace"),
        ("dynamic task allocation", "missing_runtime", "no routing policy or trace"),
        ("rule-priority conflict resolution", "missing_runtime", "no rules or configuration"),
        ("data ingestion", "missing_runtime", "providers named only as examples"),
        ("timestamp alignment", "contradicted_by_case_output", "March report contains future product news"),
        ("same-day close execution", "result_computation_recovered", "plot bars and closes recover metrics"),
        ("no transaction costs", "declared_component", "explicit paper assumption"),
        ("no leverage", "contradicted_by_author_plot", "author plots show integer exposure up to 7"),
        ("single-stock constraint", "declared_component", "three separate single-ticker runs"),
        ("buy/sell/hold", "underspecified", "buy sizing and repeated-buy behavior omitted"),
        ("initial capital", "recovered_not_declared", "$1000 is uniquely consistent with table/plots"),
        ("market price field", "recovered_not_declared", "unadjusted close matches displayed cells"),
        ("annualization", "recovered_not_declared", "252/166 exactly matches AR cells"),
        ("Sharpe annualization", "recovered_not_declared", "sqrt(252), zero RF, population SD"),
        ("risk-free rate", "paper_equation_conflict", "printed cells use zero despite Treasury statement"),
        ("MACD baseline", "independently_recomputed", "12/26/9 EMA with expanding initialization"),
        ("SMA baseline", "independently_recomputed", "10/20 expanding-window initialization"),
        ("KDJ+RSI baseline", "missing_parameters", "thresholds/windows/action rules absent"),
        ("ZMR baseline", "missing_parameters", "equilibrium/window/threshold/action rules absent"),
        ("model identity", "missing", "no LLM or checkpoint name/version"),
        ("randomness control", "missing", "no seed, temperature, or replicate policy"),
        ("native agent result runner", "missing", "not in TeX or attributable web client"),
        ("native requests/responses", "missing", "no machine-readable logs"),
        ("ablation", "missing", "no ablation experiment"),
        ("cross-window robustness", "missing", "one hand-selected 2025 interval"),
    ]
    return [
        {
            "dimension": dimension,
            "status": status,
            "evidence": evidence,
            "exact_native_paper_mechanism_reproduced": False,
            "paper_result_credit": False,
        }
        for dimension, status, evidence in dimensions
    ]


def specification_gaps() -> list[dict[str, Any]]:
    gaps = [
        ("agent source", "all agent implementations and orchestration"),
        ("model configuration", "LLM names, versions, checkpoints, temperature, seeds"),
        ("agent prompts", "system/developer/tool prompts for every role"),
        ("fusion procedure", "weights, confidence scores, conflict and retry logic"),
        ("data lineage", "exact endpoints, queries, timestamps, and frozen responses"),
        ("decision timing", "time of query relative to market close and source publication"),
        ("portfolio policy", "initial capital, buy size, repeated-buy and cash constraints"),
        ("baseline parameters", "KDJ/RSI and ZMR definitions; MACD initialization"),
        ("metric details", "return convention, RF conversion, annualization, ddof"),
        ("raw outputs", "daily prompts, responses, decisions, positions and equity arrays"),
        ("result runner", "code that produces Table 2 and Figures 2--5"),
        ("statistical protocol", "replicates, uncertainty, significance, selection policy"),
    ]
    return [
        {
            "missing_item": item,
            "required_detail": detail,
            "blocking_effect": "blocks_exact_end_to_end_p1gpt_reproduction",
            "recoverable_by_installing_public_packages": False,
        }
        for item, detail in gaps
    ]


def internal_consistency_checks() -> list[dict[str, Any]]:
    gaps = [
        ("march_report_future_iphone_air", "March 24 report cites iPhone Air preorders/eSIM approval", "Apple introduced iPhone Air September 9 and opened preorders September 12, 2025", "direct_lookahead_counterexample"),
        ("march_report_market_cap", "March 24 report prints $3.68T market cap at $220.73", "$220.73 times the then-reported 15.022073B shares is about $3.316T", "internally_inconsistent_or_future_snapshot"),
        ("lookahead_claim", "paper says simulation strictly avoids lookahead", "at least one dated case report contains future information", "claim_contradicted_by_embedded_output"),
        ("same_close_timing", "agents receive current context and execute at same-day close", "decision timestamp and publication cutoff are absent", "lookahead_boundary_undefined"),
        ("risk_free_rate", "Sharpe equation subtracts 3-month Treasury yield", "zero RF, sqrt(252), population SD recovers 11 P1GPT cells exactly; AAPL SR is 3.3877 and normally rounds to 3.39 rather than 3.38", "equation_execution_conflict"),
        ("buy_hold_googl_mdd", "Table 2 prints 6.41% MDD for GOOGL buy-and-hold", "the same close series that exactly recovers CR, AR, and SR gives 6.14% conventional MDD", "displayed_cell_not_recovered"),
        ("no_leverage", "paper assumes no leverage", "plotted positions reach 3 AAPL, 7 GOOGL, 2 TSLA units against $1000 NAV", "meaning_of_leverage_or_position_undefined"),
        ("buy_semantics", "Buy means enter a position", "plots repeatedly accumulate integer units", "execution_policy_underspecified"),
        ("start_date", "paper states February 1", "figures and 166-row calculation start February 3, first trading day", "calendar_boundary_underspecified"),
        ("annualized_return", "AR uses N years", "printed values exactly use 252/166 trading-day annualization", "unreported_metric_convention"),
        ("sma_initialization", "SMA is 10-day vs 20-day", "AAPL printed values require expanding means before 20 observations", "unreported_baseline_convention"),
        ("model_reproducibility", "paper claims reproducible and auditable decisions", "no model, prompts, logs, seeds, source snapshots, or code are released", "claim_not_operationally_supported"),
        ("generalization", "paper claims cross-asset/market-regime generalization", "three hand-selected stocks over one 166-trading-day window", "claim_exceeds_evaluation_design"),
        ("best_baseline_gap", "annual returns exceed best rules by over 20 pp on average", "displayed gaps are 21.07, 39.02 and 23.14 pp; mean 27.74 pp", "passes_displayed_table_arithmetic"),
        ("drawdown_prose", "P1GPT drawdowns around 2% and below 7% for other assets", "GOOGL is 7.08%, not below 7%", "rounded_prose_overstatement"),
        ("paper_source_code", "arXiv source is complete manuscript bundle", "zero operational agent/backtest Python or raw result arrays", "document_only_source"),
        ("web_demo_boundary", "attributable P1GPT web client is public", "paper daily prompt absent; private /invoke service and database are not released", "component_not_experiment"),
    ]
    return [
        {
            "check_id": check_id,
            "paper_statement": statement,
            "audit_observation": observation,
            "status": status,
            "paper_result_credit": False,
        }
        for check_id, statement, observation, status in gaps
    ]


def discovery_evidence() -> list[dict[str, Any]]:
    checked = "2026-08-13T16:30:00Z"
    entries = [
        ("arxiv_v1_pdf_and_source", "https://arxiv.org/abs/2510.23032", "primary_paper_source", "17-page PDF and 12-file manuscript bundle; no operational agent/backtest code", True),
        ("p1gpt_web_demo", "https://github.com/P1GPT/web_demo/tree/a88a3a7c731063d0d1ca7ac15946eb600753f358", "attributable_product_component", "38-file MIT Reflex web client; 22 Python files compile; private /invoke service absent", True),
        ("p1gpt_web_demo_full_history", "https://github.com/P1GPT/web_demo", "attributable_product_history", "complete non-shallow history has 36 reachable commits across main, develop, and gke/test; no paper-specific or result-pipeline path/content at any revision", True),
        ("organization_attribution", "https://github.com/P1GPT", "attribution_evidence", "organization owns one P1GPT web-demo repository", True),
        ("neurowatt_commit_attribution", "https://github.com/P1GPT/web_demo/commit/a88a3a7c731063d0d1ca7ac15946eb600753f358", "attribution_evidence", "Ray-neurowatt committed with @neurowatt.ai email; paper authors have same affiliation/domain", True),
        ("cited_tradingagents_paper", "https://arxiv.org/abs/2412.20138v7", "explicitly_cited_protocol_source", "qualitative KDJ+RSI and ZMR descriptions omit windows, thresholds, equilibrium, and action rules", True),
        ("cited_tradingagents_source", "https://github.com/TauricResearch/TradingAgents/tree/cc97cb6d5deb10eac370db0c6678e2796a62eba8", "official_cited_protocol_source", "nearest official release contains no baseline implementation, metric code, or paper backtest runner", True),
        ("rejected_later_third_party_guess", "https://github.com/lucas020695/tradingagents_replicated/tree/e85988694bbd3cbbcf250bd045b1ac16cd870b2f", "post_paper_unaffiliated_source", "postdates P1GPT, uses a placeholder KDJ J value and guessed ZMR parameters, and is excluded from native credit", False),
        ("exact_title_repository_search", "https://github.com/search?q=%22multi-agent+LLM+workflow+module%22&type=repositories", "bounded_negative_search", "two bibliography/awesome-list results; no implementation", False),
        ("arxiv_id_code_search", "https://github.com/search?q=%222510.23032%22&type=code", "bounded_negative_search", "18 indexed mentions, none an author implementation", False),
        ("author_email_code_search", "https://github.com/search?q=%22peter%40neurowatt.ai%22&type=code", "bounded_negative_search", "only a paper-text mirror; same for oro/luka addresses", False),
        ("apple_iphone_air_timing", "https://www.apple.com/newsroom/2025/09/introducing-iphone-air-a-powerful-new-iphone-with-a-breakthrough-design/", "primary_external_timing_check", "Apple introduced iPhone Air on September 9, 2025", True),
        ("apple_iphone_air_preorders", "https://www.apple.com/newsroom/2025/09/get-ready-to-discover-the-next-generation-of-iphone-apple-watch-and-airpods/", "primary_external_timing_check", "Apple opened iPhone Air preorders September 12, 2025", True),
        ("apple_share_count", "https://www.sec.gov/Archives/edgar/data/320193/000032019325000008/aapl-20241228.htm", "primary_external_financial_check", "15,022,073,000 shares outstanding January 17, 2025", True),
    ]
    return [
        {
            "search_or_source": name,
            "url": url,
            "evidence_kind": kind,
            "checked_at_utc": checked,
            "bounded_result": result,
            "attributable_primary_or_component_source": attributable,
            "native_p1gpt_agent_result_pipeline_found": False,
            "negative_inference_boundary": (
                "absence in checked public surfaces is not proof that private, deleted, "
                "historical, or unindexed artifacts never existed"
            ),
        }
        for name, url, kind, result, attributable in entries
    ]


def manuscript_rebuild(audit_root: Path) -> list[dict[str, Any]]:
    first = pinned_path(audit_root, REBUILD_PIN["first"], REBUILD_PIN["sha256"])
    repeat = pinned_path(audit_root, REBUILD_PIN["repeat"], REBUILD_PIN["sha256"])
    pages = len(PdfReader(str(first)).pages)
    if pages != REBUILD_PIN["pages"]:
        raise ValueError("rebuilt page count changed")
    return [
        {
            "paper_version": VERSION,
            "build_method": "unmodified_primary_TeX_three_pdflatex_passes_TeX_Live_2024",
            "build_sha256": sha256(first),
            "repeat_build_sha256": sha256(repeat),
            "same_hash_across_independent_build_directories": first.read_bytes() == repeat.read_bytes(),
            "page_count": pages,
            "published_page_count": PDF_PIN["pages"],
            "normalized_extracted_text_equal": REBUILD_PIN["normalized_text_equal"],
            "normalized_extracted_text_sequence_ratio": REBUILD_PIN["normalized_text_sequence_ratio"],
            "max_100dpi_raster_mean_absolute_difference": REBUILD_PIN["max_100dpi_raster_mad"],
            "max_100dpi_raster_changed_fraction": REBUILD_PIN["max_100dpi_changed_fraction"],
            "full_contact_sheet_visual_qa": "passed_all_17_author_and_17_rebuilt_pages_readable_no_clipping_overlap_or_missing_content",
            "embedded_asset_visual_qa": "passed_all_7_assets_including_2_report_pdfs_and_3_position_plots",
            "document_reconstruction_credit": True,
            "paper_result_reproduction": False,
        }
    ]


def readme_text(manifest: Mapping[str, Any]) -> str:
    return f"""# P1GPT primary-source replication audit

## Honest outcome

P1GPT is **not faithfully reproduced end to end**. The manuscript is fully and
deterministically reconstructed, and {manifest['displayed_table_cells_exactly_verified']}/72 displayed Table 2
cells can be checked exactly. Those checks are not the same as regenerating the
multi-agent experiment:

- document reconstruction: 1/1 arXiv version rebuilds twice to byte-identical
  17-page PDFs; normalized extracted text is identical to the published PDF and
  all 34 author/rebuilt pages plus seven embedded assets pass visual QA;
- native P1GPT output verification: 11/12 P1GPT cells match after recovering the
  author-rendered daily position bars and applying them to the pinned present-day
  Yahoo response; AAPL Sharpe computes to 3.3877, normally 3.39 rather than the
  printed 3.38;
- rule baselines: 35/36 cells for B&H, MACD, and SMA independently match; the
  same GOOGL close series that recovers B&H CR, AR, and SR gives 6.14% MDD,
  rather than the printed 6.41%;
- unsupported baselines: 0/24 KDJ+RSI and ZMR cells can be regenerated because
  their windows, thresholds, equilibrium definition, and action rules are absent;
- actual agent replay: 0/12 P1GPT cells regenerate from agent code, prompts,
  requests, responses, and paper-time data, because those inputs are not public.

The 46 exact matches are therefore **result verification**, not full-system
replication. The Yahoo response was pinned during this audit, not by the paper.
The plotted positions are author-rendered outputs, not independently generated
agent decisions.

## Material lookahead finding

The embedded report dated March 24, 2025 discusses iPhone Air preorders and eSIM
approval. Apple did not introduce iPhone Air until September 9 and did not open
preorders until September 12. The same report prints a $3.68T market cap alongside
a $220.73 price; using Apple's then-public 15.022073B share count gives about
$3.316T. This is direct counterevidence to the paper's statement that the
simulation "strictly avoids lookahead bias." It does not prove every daily signal
uses future data, but it prevents unqualified faithfulness or causal-performance
credit.

## Recovered metric conventions

The plots and pinned close series reveal conventions omitted or misstated in the
paper: $1,000 initial capital; unadjusted close; previous-day position applied to
close-to-close P&L; 252/166 annualization; annualized Sharpe with zero risk-free
rate and population standard deviation; and integer positions as high as seven.
The zero risk-free rate conflicts with the paper's 3-month-Treasury statement,
and multi-unit accumulation needs clarification against the "no leverage" claim.

## Public component boundary

`P1GPT/web_demo` is attributable: the P1GPT GitHub organization owns it and its
commits use Neurowatt identities/emails. Its 38 tracked files include 22 Python
files that compile, a dependency manifest, Docker/Compose/Kubernetes runners,
five Chinese finance prompt cards, and a multimodal request client. It is genuine
R3 static/component evidence. It is not the paper experiment: the paper's daily
prompt is absent, the source sends requests to an unreleased `main-llm` service,
and the database, agents, backtest, and outputs are not shipped. Committed
plaintext credentials were neither used nor reproduced here.

The checked archive is not the only revision inspected. A complete non-shallow
clone contains 36 reachable commits across `main`, `develop`, and `gke/test`.
Every revision was searched for paper-specific content and backtest, result,
metric, position, portfolio, and trade paths; none contains the P1GPT experiment.
The complete public-fork census on 2026-08-14 finds one accessible fork and one
branch ref. Its head is byte-identical to the already-audited official `main`
head, so it adds no commits, paths, prompts, outputs, or result evidence.

## Cited baseline-protocol boundary

The paper says its baselines follow TradingAgents. The cited TradingAgents v7
appendix also describes KDJ+RSI and ZMR only qualitatively, and the nearest
official v0.1.0 source ships no baseline implementation, metric code, or paper
backtest. A later unaffiliated repository guesses 14/9-day KDJ+RSI and 50-day,
1.5-z-score ZMR rules, but it postdates P1GPT, leaves KDJ J as a placeholder,
and contradicts P1GPT's stated SMA windows. It is recorded and explicitly
excluded from native-method or result credit.

## Evidence files

- `paper_version_summary.csv`: pinned primary PDF/source and local identity.
- `paper_source_inventory.csv`: all 12 arXiv source files.
- `author_figure_inventory.csv`: all seven embedded assets.
- `published_result_ledger.csv`: all 72 Table 2 cells.
- `result_recovery_checks.csv`: 48 exact displayed-cell checks and boundaries.
- `recovered_author_plot_positions.csv`: 498 author-rendered daily bar values.
- `market_snapshot_checks.csv`: three pinned present-day Yahoo responses.
- `prompt_inventory.csv`: the sole paper prompt and missing runtime evidence.
- `mechanism_conformance.csv`: 36 mechanism dimensions.
- `specification_gaps.csv`: inputs required for exact replay.
- `internal_consistency.csv`: lookahead, metric, execution, and claim conflicts.
- `public_source_file_inventory.csv`: all 38 web-client files.
- `source_history_inventory.csv`: all 36 reachable web-client revisions.
- `public_fork_branch_ref_snapshot.csv`: the complete dated accessible fork/branch surface.
- `public_fork_unique_head_inventory.csv`: the sole fork head and zero-divergence boundary.
- `public_fork_census.json`: fork completeness, head equivalence, and zero-credit verdict.
- `cited_protocol_lineage.csv`: cited official sources and rejected later guess.
- `public_component_execution.json`: attribution, compile, and private-service boundary.
- `manuscript_rebuilds.json`: deterministic reconstruction and visual-QA record.
- `public_source_discovery.csv`: bounded primary-source and GitHub search record.

Installing additional packages cannot recover the private model service, exact
prompts, paper-time source snapshots, or missing requests/responses. The bounded
search does not prove that private, deleted, historical, or unindexed artifacts
never existed.
"""


def build_audit(
    audit_root: Path,
    output_dir: Path,
    web_demo_history: Path = DEFAULT_WEB_DEMO_HISTORY,
) -> dict[str, Any]:
    files = paper_sources(audit_root)
    versions = paper_version_summary(audit_root)
    source_inventory = paper_source_inventory(files)
    figures = figure_inventory(files)
    table = published_result_ledger()
    recoveries, positions = result_recovery_checks(audit_root, files)
    snapshots = market_snapshot_checks(audit_root)
    prompts = prompt_inventory()
    mechanisms = mechanism_conformance()
    gaps = specification_gaps()
    consistency = internal_consistency_checks()
    public_files, public_execution = web_demo_inventory(audit_root)
    history = source_history_inventory(web_demo_history)
    fork_branches, fork_heads, fork_summary = public_fork_census(web_demo_history)
    protocol = cited_protocol_lineage()
    discovery = discovery_evidence()
    rebuilds = manuscript_rebuild(audit_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "paper_version_summary.csv", versions)
    write_csv(output_dir / "paper_source_inventory.csv", source_inventory)
    write_csv(output_dir / "author_figure_inventory.csv", figures)
    write_csv(output_dir / "published_result_ledger.csv", table)
    write_csv(output_dir / "result_recovery_checks.csv", recoveries)
    write_csv(output_dir / "recovered_author_plot_positions.csv", positions)
    write_csv(output_dir / "market_snapshot_checks.csv", snapshots)
    write_csv(output_dir / "prompt_inventory.csv", prompts)
    write_csv(output_dir / "mechanism_conformance.csv", mechanisms)
    write_csv(output_dir / "specification_gaps.csv", gaps)
    write_csv(output_dir / "internal_consistency.csv", consistency)
    write_csv(output_dir / "public_source_file_inventory.csv", public_files)
    write_csv(output_dir / "source_history_inventory.csv", history)
    write_csv(output_dir / "public_fork_branch_ref_snapshot.csv", fork_branches)
    write_csv(output_dir / "public_fork_unique_head_inventory.csv", fork_heads)
    write_csv(output_dir / "cited_protocol_lineage.csv", protocol)
    write_csv(output_dir / "public_source_discovery.csv", discovery)
    write_json(output_dir / "public_component_execution.json", public_execution)
    write_json(output_dir / "manuscript_rebuilds.json", rebuilds)
    write_json(output_dir / "public_fork_census.json", fork_summary)

    recovery_classes = Counter(
        row["verification_class"]
        for row in recoveries
        if row["display_rounding_exact_match"]
    )
    manifest: dict[str, Any] = {
        "audit": "P1GPT primary-source and attributable-component replication audit",
        "canonical_work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "overall_status": "not_reproduced_author_output_and_baseline_verification_only",
        "full_paper_reproduced": False,
        "paper_versions_pinned": len(versions),
        "paper_source_files": len(source_inventory),
        "manuscripts_rebuilt_deterministically": len(rebuilds),
        "manuscript_rebuilds_receive_result_credit": False,
        "published_table_result_cells": len(table),
        "published_native_p1gpt_result_cells": 12,
        "published_baseline_result_cells": 60,
        "displayed_table_cells_recalculated_or_checked": len(recoveries),
        "displayed_table_cells_exactly_verified": sum(
            row["display_rounding_exact_match"] for row in recoveries
        ),
        "p1gpt_cells_verified_from_author_plot_outputs": recovery_classes[
            "author_output_result_verification_not_signal_regeneration"
        ],
        "p1gpt_cells_checked_from_author_plot_outputs": 12,
        "baseline_cells_independently_recalculated": recovery_classes[
            "independent_baseline_recalculation_current_snapshot_not_paper_lineage"
        ],
        "baseline_cells_recalculated": 36,
        "unsupported_kdj_rsi_zmr_cells": 24,
        "native_p1gpt_result_cells_faithfully_regenerated_end_to_end": 0,
        "native_p1gpt_agent_decisions_independently_regenerated": 0,
        "author_plot_daily_position_values_recovered": len(positions),
        "paper_time_market_snapshots_shipped": 0,
        "verbatim_paper_prompt_templates": len(prompts),
        "runtime_prompt_requests_replayed": 0,
        "runtime_prompt_responses_replayed": 0,
        "author_figure_assets": len(figures),
        "author_figure_assets_faithfully_regenerated_from_native_pipeline": 0,
        "attributable_public_repositories": 1,
        "attributable_public_commits_exhaustively_audited": len(history),
        "attributable_public_branch_heads_audited": len(WEB_DEMO_HISTORY["branch_heads"]),
        "historical_revisions_with_native_result_pipeline": sum(
            row["native_p1gpt_result_pipeline_found"] for row in history
        ),
        "public_fork_census_date": fork_summary["census_date"],
        "public_forks_reported_by_github_rest": fork_summary["github_rest_reported_forks"],
        "public_forks_accessible_via_graphql": fork_summary["graphql_accessible_forks"],
        "public_fork_branch_refs_audited": fork_summary["graphql_accessible_branch_refs"],
        "public_fork_unique_heads_audited": fork_summary["unique_heads"],
        "public_fork_heads_reachable_from_audited_official_history": fork_summary[
            "heads_reachable_from_exhaustively_audited_official_history"
        ],
        "public_fork_divergent_heads_audited": fork_summary["divergent_heads_reviewed"],
        "public_fork_native_result_artifacts_found": False,
        "public_fork_paper_result_credit": False,
        "paper_relevant_public_source_files": len(public_files),
        "public_python_files_compiled": public_execution["python_files_compiled"],
        "public_static_fidelity_tier": public_execution["static_fidelity_tier"],
        "native_result_generation_pipeline_found": False,
        "cited_protocol_sources_audited": 3,
        "post_paper_third_party_guesses_rejected": 1,
        "cited_protocol_kdj_rsi_zmr_parameterizations_recovered": 0,
        "paper_mechanism_dimensions_audited": len(mechanisms),
        "exact_native_paper_mechanism_dimensions_reproduced": 0,
        "material_internal_or_specification_issues": len(consistency),
        "direct_lookahead_counterexamples": sum(
            row["status"] == "direct_lookahead_counterexample" for row in consistency
        ),
        "precise_blocker": (
            "the attributable public repository is a web client whose private model "
            "service is absent; the paper releases no model identities, agent prompts, "
            "requests/responses, exact source snapshots, independent decisions, seeds, "
            "KDJ/RSI or ZMR parameters, or result runner"
        ),
        "negative_inference_boundary": (
            "no native P1GPT result pipeline found in the pinned public sources and "
            "checked surfaces; not proof that private, deleted, historical, or "
            "unindexed artifacts never existed"
        ),
    }
    (output_dir / "README.md").write_text(readme_text(manifest), encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-root", type=Path, default=DEFAULT_AUDIT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--web-demo-history", type=Path, default=DEFAULT_WEB_DEMO_HISTORY
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return nonzero while the full paper remains unreproduced.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(args.audit_root, args.output_dir, args.web_demo_history)
    print(json.dumps(manifest, indent=2))
    return 1 if args.strict and not manifest["full_paper_reproduced"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
