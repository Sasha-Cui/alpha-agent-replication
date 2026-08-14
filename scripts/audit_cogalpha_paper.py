#!/usr/bin/env python3
"""Build a fail-closed paper/source/release audit for CogAlpha.

CogAlpha has two materially different paper editions and a late, author-owned
prompt-only release.  This audit grants document, prompt-specification,
author-output correspondence, and synthetic code-listing component credit.  It
does not convert any of those into native experiment/result reproduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/cogalpha_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/cogalpha"
WORK_ID = "CensusArxiv251118850"
SYSTEM_ID = "SYS-COG-ALPHA"
ARXIV_ID = "2511.18850"
PROMPT_COMMIT = "6294d9ffa9dfc286fb14e82343f8f22a5f928c1c"
PROMPT_REPOSITORY = "https://github.com/uwFengyuan/CogAlpha_Prompt"
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_REPOSITORY = "qifox/CogAlpha_Prompt"
RESULT_ARTIFACT_SUFFIXES = (
    ".ckpt", ".csv", ".db", ".json", ".jsonl", ".npy", ".npz", ".parquet",
    ".pickle", ".pkl", ".pt", ".pth", ".safetensors", ".sqlite", ".tsv",
    ".xls", ".xlsx",
)
PAPER_RESULT_LITERALS = (
    "0.0591", "0.0814", "0.3410", "0.4350", "1.8999", "0.4385",
)

PINS = {
    "primary/acl-final.bib": "7cae59d5f9ecef2a0b8285fb02b346b2f3487271dc714da81669d64b3c537fac",
    "primary/acl-final.pdf": "c6fa623e4e4890d2497c8a75a76da286cbdbdc99c88387132873d0f1222bdc10",
    "primary/arxiv-abs.html": "df9f068704a4a3903cdcc79aab05b71e78ecccccecc5866c2ab580f83ad6973a",
    "primary/arxiv-api.xml": "b40f236f09facd275055bb0248d49a08d5ec226be44fad795c9a337ecca9532b",
    "primary/arxiv-v1.pdf": "abffd95bcfabe30422ee6adbb280e5d30c92dc42b5c6723f8df4ba59562a86da",
    "primary/arxiv-v1.tar": "8958d73a85115fd90daa6a52a17149537fe634d55e4bca2dce4c02aeda66207e",
    "primary/arxiv-v4.pdf": "20c6c76a0e9ea5fdf869ee0a20a3594ab61181fee9913b1ec9361b3669ecea45",
    "primary/arxiv-v4.tar": "9106f0b56ff27219d78b35d9d5e3f113e02e60211263a0eb2825282bcef7967f",
    "primary/arxiv-v4-rebuilt.pdf": "67ea28ff4fd6ee0d1b2ac9b08a579d09aee8bf11561de5c544eaa6e460cd6fac",
    "primary/prompt-repo.tar.gz": "fd51d57bb161a6efa2130ea2630f6dc9742c65dd423ca8ab349d54ab45266f0e",
    "primary/v1-build-failure.log": "06e19c8c3f3c24e4b29716888c7fe924281358c8b894645448a4761583de2e3c",
    "primary/v4-build-final.log": "ac681e7b7389301c10aeafaf05569f429b11c30d05b079d67044efe781dc1d68",
    "repo_api/commits.json": "2c6e2d98fca8b38ba57158afc69d3408cb93e62036de4c916b46f899917750ad",
    "repo_api/repository.json": "b20fbbe4f901e6f6b34c3361d1b8c754411c654eb9fe3104870ce920d6b1cd48",
    "repo_api/tree.json": "75f0a0f9b60dc974c29de850e73de48ae9b7f54cd53b2098c316a595f9efd376",
    "source-v1/main.tex": "fb8be224c0323a10500fa8ba5844c4c3096bc0b0b3452c517416f26cd9e3d04d",
    "source-v4/acl.tex": "edd39eb294d5601d66574b22fe5c073fc69c352c775748dc85f1a043b9eecc25",
    "source-v1/CogAlpha.pdf": "51a0aaf6ec1b48d168c231e731851ab3a8aa6501ca13bbe6593b65c5330be975",
    "source-v1/cum_returns_comparison_50_5_10.png": "e836d109ff283e44b5d415ba9210c4aa01ef673a94a4bacd2f49242cb7ef0bc2",
    "source-v4/CogAlpha.pdf": "51a0aaf6ec1b48d168c231e731851ab3a8aa6501ca13bbe6593b65c5330be975",
    "source-v4/cum_returns_comparison_50_5_10.png": "e836d109ff283e44b5d415ba9210c4aa01ef673a94a4bacd2f49242cb7ef0bc2",
    "prompt-repo/README.md": "e867ffa8bbf6f02868e452203f753d64f5512178af1c5e060b65044902bab3ee",
    "prompt-repo/assets/overview.png": "66af0b001d75dd1e1b11a447a6f3a2a6b8bf2867f5c851b72651a8657f8c0fbe",
    "discovery/github-author-repos.json": "a6161bb8a9483384ca4895773f4d5c6503e5b211f33f2a7fccbb1da4103fd265",
    "discovery/github-code-arxiv.json": "82c65d4b5d67496bbccbffcc5b58f02ba643075b744a1f41e1cbf252b58930da",
    "discovery/github-code-title.json": "73d1da5c78a779c8858fe4b6cfdea8639d31fdd61271bbc4c2364011d7bf9419",
    "discovery/github-repositories-title.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/hf-datasets.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/hf-models.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
}

TREE_DIGESTS = {
    "source-v1": ("019cc4173f1f30ce02fe26c384ac2c768d23d9d1b7febfad9b631dcae808a431", 6),
    "source-v4": ("69b7bad7dca0146a5f40911eb462868afd9d2ba5c0ce578e9083391356961dc2", 7),
    "prompt-repo": ("06fa8362cdfe36ef40ec5afc6d85918e940ec6f9ee82aae85fad7d23d499c643", 47),
}

BASELINE_V1 = (
    "Linear", "MLP", "RandomForest", "LightGBM", "XGBoost", "CatBoost",
    "Adaboost", "Transformer", "GRU", "LSTM", "CNN", "Alpha158",
    "Alpha360", "Llama3-8B", "Llama3-70B", "gpt-oss-20B", "gpt-oss-120B",
    "GPT-4.1", "o3", "CogAlpha",
)
BASELINE_V4 = BASELINE_V1[:13] + ("AutoAlpha", "AlphaAgent") + BASELINE_V1[13:]
ABLATION = ("Agent", "Agent_E", "Agent_EA", "Agent_EAG", "Agent_EAGH-CogAlpha")
HYPERPARAM = (
    "P16_G24_H8", "P32_G24_H8", "P48_G24_H8", "P32_G24_H2",
    "P32_G24_H4", "P32_G24_H12", "P32_G8_H8", "P32_G16_H8",
)
SETTINGS = (
    ("CSI300-10", "CNN"), ("CSI300-10", "Linear"),
    ("CSI300-10", "XGBoost"), ("CSI300-10", "CogAlpha-Ridge"),
    ("CSI300-10", "CogAlpha-LightGBM"), ("CSI300-30", "CNN"),
    ("CSI300-30", "Linear"), ("CSI300-30", "XGBoost"),
    ("CSI300-30", "CogAlpha-Ridge"), ("CSI300-30", "CogAlpha-LightGBM"),
    ("CSI500-10", "CNN"), ("CSI500-10", "Linear"),
    ("CSI500-10", "XGBoost"), ("CSI500-10", "CogAlpha-Ridge"),
    ("SP500-10", "CNN"), ("SP500-10", "Linear"),
    ("SP500-10", "XGBoost"), ("SP500-10", "CogAlpha-Ridge"),
    ("HSI-10", "CNN"), ("HSI-10", "Linear"),
    ("HSI-10", "XGBoost"), ("HSI-10", "CogAlpha-Ridge"),
    ("HSCI-10", "CNN"), ("HSCI-10", "Linear"),
    ("HSCI-10", "XGBoost"), ("HSCI-10", "CogAlpha-Ridge"),
)
METRICS6 = ("IC", "RankIC", "ICIR", "RankICIR", "AER", "IR")
METRICS4 = ("IC", "RankIC", "ICIR", "RankICIR")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(
    repository: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def tree_digest(path: Path) -> tuple[str, int]:
    rows = []
    files = sorted(item for item in path.rglob("*") if item.is_file())
    for item in files:
        rows.append(f"{item.relative_to(path)}\0{sha256(item)}\n")
    return hashlib.sha256("".join(rows).encode()).hexdigest(), len(files)


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty ledger: {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def safe_tar_members(path: Path) -> set[str]:
    members = set()
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe archive member: {member.name}")
            if member.isfile():
                members.add(str(pure))
    return members


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    for relative, expected in TREE_DIGESTS.items():
        actual = tree_digest(scratch / relative)
        if actual != expected:
            raise ValueError(f"tree mismatch for {relative}: {actual} != {expected}")

    v1_members = {PurePosixPath(item).name for item in safe_tar_members(scratch / "primary/arxiv-v1.tar")}
    v4_members = {PurePosixPath(item).name for item in safe_tar_members(scratch / "primary/arxiv-v4.tar")}
    if v1_members != {"00README.json", "CogAlpha.pdf", "cum_returns_comparison_50_5_10.png", "main.bbl", "main.tex", "neurips_2025.sty"}:
        raise ValueError(f"unexpected v1 source members: {sorted(v1_members)}")
    if v4_members != {"00README.json", "CogAlpha.pdf", "acl.bib", "acl.sty", "acl.tex", "acl_natbib.bst", "cum_returns_comparison_50_5_10.png"}:
        raise ValueError(f"unexpected v4 source members: {sorted(v4_members)}")
    safe_tar_members(scratch / "primary/prompt-repo.tar.gz")

    repository = json.loads((scratch / "repo_api/repository.json").read_text())
    commits = json.loads((scratch / "repo_api/commits.json").read_text())
    if repository["full_name"] != "uwFengyuan/CogAlpha_Prompt":
        raise ValueError("prompt repository identity changed")
    if repository["created_at"] != "2026-07-14T02:46:37Z" or repository["license"] is not None:
        raise ValueError("prompt repository creation/license boundary changed")
    if len(commits) != 1 or commits[0]["sha"] != PROMPT_COMMIT:
        raise ValueError("prompt repository commit history changed")
    if commits[0]["commit"]["author"]["date"] != "2026-07-14T03:09:02Z":
        raise ValueError("prompt release date changed")

    abs_html = (scratch / "primary/arxiv-abs.html").read_text()
    required = (
        "Submitted on 24 Nov 2025", "last revised 11 Jul 2026", "2511.18850v4",
        "Wed, 15 Apr 2026 23:10:51 UTC", "Mon, 20 Apr 2026 11:45:12 UTC",
    )
    if not all(marker in abs_html for marker in required):
        raise ValueError("arXiv version history does not match pinned record")
    failure = (scratch / "primary/v1-build-failure.log").read_text(errors="replace")
    if "Bibliography not compatible with author-year citations" not in failure:
        raise ValueError("v1 build failure is not the pinned natbib conflict")
    final_log = (scratch / "primary/v4-build-final.log").read_text(errors="replace")
    if "Output written on acl.pdf (35 pages" not in final_log:
        raise ValueError("v4 unmodified rebuild did not finish at 35 pages")
    return {
        "v1_source_members": sorted(v1_members),
        "v4_source_members": sorted(v4_members),
        "prompt_commit": PROMPT_COMMIT,
    }


def public_history_and_fork_audit(
    scratch: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Audit the entire one-commit prompt history and its sole public fork."""
    repository = scratch / "repository_history"
    if not repository.is_dir():
        raise FileNotFoundError(repository)
    if git(repository, "rev-parse", "--is-shallow-repository").stdout.strip() != "false":
        raise ValueError("CogAlpha prompt history checkout is shallow")
    origin = git(repository, "remote", "get-url", "origin").stdout.strip()
    if origin.removesuffix(".git") != PROMPT_REPOSITORY:
        raise ValueError(f"CogAlpha prompt origin changed: {origin}")
    fsck = git(
        repository,
        "fsck",
        "--full",
        "--no-reflogs",
        "--unreachable",
        "--no-progress",
    )
    if fsck.stdout.strip() or fsck.stderr.strip():
        raise ValueError(f"CogAlpha prompt checkout has unreviewed objects: {fsck.stdout}")
    commits = git(repository, "rev-list", "--reverse", "--all").stdout.splitlines()
    if commits != [PROMPT_COMMIT]:
        raise ValueError(f"CogAlpha prompt history changed: {commits}")
    if git(repository, "rev-parse", "refs/remotes/origin/main").stdout.strip() != PROMPT_COMMIT:
        raise ValueError("CogAlpha official main head changed")
    fork_refs = {}
    for line in git(
        repository,
        "for-each-ref",
        "--format=%(refname)%09%(objectname)",
        "refs/remotes/forks",
    ).stdout.splitlines():
        refname, head = line.split("\t")
        fork_refs[refname] = head
    if fork_refs != {"refs/remotes/forks/qifox/main": PROMPT_COMMIT}:
        raise ValueError(f"CogAlpha public-fork refs changed: {fork_refs}")
    if git(repository, "for-each-ref", "--format=%(refname)", "refs/tags").stdout.strip():
        raise ValueError("CogAlpha prompt repository now exposes an unreviewed tag")

    paths = git(repository, "ls-tree", "-r", "--name-only", PROMPT_COMMIT).stdout.splitlines()
    if len(paths) != 47 or sum(path.endswith(".md") for path in paths) != 45:
        raise ValueError("CogAlpha prompt release tree changed")
    snapshot_root = scratch / "prompt-repo"
    literal_hits: list[str] = []
    result_paths = [path for path in paths if path.lower().endswith(RESULT_ARTIFACT_SUFFIXES)]
    for path in paths:
        payload = subprocess.run(
            ["git", "-C", str(repository), "show", f"{PROMPT_COMMIT}:{path}"],
            check=True,
            capture_output=True,
        ).stdout
        snapshot_path = snapshot_root / path
        if not snapshot_path.is_file() or sha256_bytes(payload) != sha256(snapshot_path):
            raise ValueError(f"CogAlpha Git/archive snapshot mismatch: {path}")
        if path.endswith(".md"):
            text = payload.decode("utf-8", errors="replace")
            literal_hits.extend(literal for literal in PAPER_RESULT_LITERALS if literal in text)
    if result_paths or literal_hits:
        raise ValueError(
            "CogAlpha prompt history contains an unreviewed result artifact: "
            f"paths={result_paths}, literals={sorted(set(literal_hits))}"
        )
    authored_at, committed_at, author_name, author_email, subject = git(
        repository,
        "show",
        "-s",
        "--format=%aI%x09%cI%x09%an%x09%ae%x09%s",
        PROMPT_COMMIT,
    ).stdout.rstrip("\n").split("\t", 4)
    history_rows = [{
        "commit": PROMPT_COMMIT,
        "authored_at": authored_at,
        "committed_at": committed_at,
        "author_name": author_name,
        "author_email": author_email,
        "subject": subject,
        "tracked_paths": len(paths),
        "markdown_paths": sum(path.endswith(".md") for path in paths),
        "archive_snapshot_paths_exact": len(paths),
        "structured_result_or_data_payload_paths": len(result_paths),
        "distinctive_paper_result_literal_hits": len(literal_hits),
        "native_result_artifact_found": False,
        "paper_result_credit": False,
    }]
    fork_only = git(
        repository,
        "rev-list",
        "refs/remotes/forks/qifox/main",
        "--not",
        "refs/remotes/origin/main",
    ).stdout.splitlines()
    if fork_only:
        raise ValueError(f"CogAlpha public fork adds unreviewed commits: {fork_only}")
    fork_rows = [{
        "repository": PUBLIC_FORK_REPOSITORY,
        "url": f"https://github.com/{PUBLIC_FORK_REPOSITORY}",
        "branch": "main",
        "head_commit": PROMPT_COMMIT,
        "relation_to_official_head": "official_head_exact",
        "commits_ahead_of_official": 0,
        "commits_behind_official": 0,
        "tag_refs": 0,
        "unique_commits_beyond_official_history": 0,
        "unique_blobs_beyond_official_history": 0,
        "native_result_artifact_found": False,
        "paper_result_credit": False,
    }]
    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "official_history_commits": len(history_rows),
        "official_history_tracked_paths": len(paths),
        "official_history_archive_snapshot_paths_exact": len(paths),
        "official_history_result_artifacts_found": 0,
        "github_rest_reported_forks": 1,
        "accessible_public_forks": 1,
        "accessible_branch_refs": 1,
        "tag_refs": 0,
        "unique_heads": 1,
        "official_head_exact_unique_heads": 1,
        "divergent_unique_heads": 0,
        "unique_commits_beyond_official_history": 0,
        "unique_blobs_beyond_official_history": 0,
        "native_result_artifacts_found": 0,
        "paper_result_credit": False,
        "interpretation": (
            "the complete official prompt-repository history is one commit whose 47 paths "
            "exactly match the audited archive and contain no structured result payload or "
            "distinctive paper-result value; the sole accessible fork resolves exactly to "
            "that official head and adds no commit, blob, or result lineage"
        ),
    }
    return history_rows, fork_rows, summary


def empirical_table_blocks(tex: str) -> dict[str, str]:
    blocks = {}
    for match in re.finditer(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", tex, re.S):
        block = match.group(0)
        label = re.search(r"\\label\{([^}]+)\}", block)
        if label and label.group(1) in {"T: Baselines", "T: Ablation", "tab:hyperparam", "T: Different Settings"}:
            blocks[label.group(1)] = block
    return blocks


def numeric_rows(block: str, expected_metrics: int) -> list[list[str]]:
    block = re.sub(r"%[^\n]*", "", block)
    # The empirical tables contain nested one-cell ``tabular`` labels.  Keep
    # the outer body by ending at the final tabular close in this table block.
    body_match = re.search(r"\\begin\{tabular\}\{[^\n]+\}\s*(.*)\\end\{tabular\}", block, re.S)
    if not body_match:
        raise ValueError("empirical tabular body missing")
    rows = []
    for raw in re.split(r"\\\\", body_match.group(1)):
        values = re.findall(r"(?<![A-Za-z0-9])(-?\d+\.\d+)(?![A-Za-z0-9])", raw)
        if len(values) >= expected_metrics:
            rows.append(values[-expected_metrics:])
    return rows


def table_ledger(scratch: Path) -> list[dict[str, Any]]:
    ledgers = []
    editions = (
        ("arxiv_v1", scratch / "source-v1/main.tex", BASELINE_V1),
        ("arxiv_v4_acl_final", scratch / "source-v4/acl.tex", BASELINE_V4),
    )
    for edition, path, baseline_names in editions:
        blocks = empirical_table_blocks(path.read_text())
        specifications: list[tuple[str, tuple[Any, ...], tuple[str, ...]]] = [
            ("main_baselines", baseline_names, METRICS6),
            ("ablation", ABLATION, METRICS6),
        ]
        source_labels = ["T: Baselines", "T: Ablation"]
        if edition == "arxiv_v4_acl_final":
            specifications.extend(
                (("hyperparameters", HYPERPARAM, METRICS4), ("cross_dataset", SETTINGS, METRICS4))
            )
            source_labels.extend(("tab:hyperparam", "T: Different Settings"))
        main_values: dict[tuple[str, str], str] = {}
        for source_label, (table, row_ids, metrics) in zip(source_labels, specifications):
            parsed = numeric_rows(blocks[source_label], len(metrics))
            if len(parsed) != len(row_ids):
                raise ValueError(f"{edition} {table} row count {len(parsed)} != {len(row_ids)}")
            for row_number, (identity, values) in enumerate(zip(row_ids, parsed), 1):
                if isinstance(identity, tuple):
                    context, row_name = identity
                else:
                    context, row_name = "CSI300-10", identity
                for metric, display in zip(metrics, values):
                    semantic = (context, row_name, metric)
                    duplicate = "none"
                    if table == "main_baselines":
                        main_values[(row_name, metric)] = display
                    elif table == "ablation" and row_name == "Agent":
                        if display != main_values[("gpt-oss-120B", metric)]:
                            raise ValueError("base ablation row does not repeat gpt-oss-120B")
                        duplicate = "exact_repeat_of_main_table"
                    elif table == "ablation" and row_name == "Agent_EAGH-CogAlpha":
                        if display != main_values[("CogAlpha", metric)]:
                            raise ValueError("full ablation row does not repeat CogAlpha")
                        duplicate = "exact_repeat_of_main_table"
                    elif table == "cross_dataset" and context == "CSI300-10":
                        corresponding = row_name.replace("CogAlpha-LightGBM", "CogAlpha")
                        if corresponding in {"CNN", "Linear", "XGBoost", "CogAlpha"}:
                            if display != main_values[(corresponding, metric)]:
                                raise ValueError(f"cross-dataset repeat mismatch: {semantic}")
                            duplicate = "exact_repeat_of_main_table"
                    ledgers.append(
                        {
                            "edition": edition,
                            "table": table,
                            "row_number": row_number,
                            "context": context,
                            "row": row_name,
                            "metric": metric,
                            "display_value": display,
                            "numeric_value": float(display),
                            "duplicate_kind": duplicate,
                            "native_pipeline_executed": False,
                            "native_result_regenerated": False,
                            "paper_result_credit": False,
                        }
                    )
    counts = Counter((row["edition"], row["table"]) for row in ledgers)
    expected = {
        ("arxiv_v1", "main_baselines"): 120,
        ("arxiv_v1", "ablation"): 30,
        ("arxiv_v4_acl_final", "main_baselines"): 132,
        ("arxiv_v4_acl_final", "ablation"): 30,
        ("arxiv_v4_acl_final", "hyperparameters"): 32,
        ("arxiv_v4_acl_final", "cross_dataset"): 104,
    }
    if counts != expected:
        raise ValueError(f"table-cell denominator mismatch: {counts}")
    return ledgers


def prose_and_figure_ledger() -> list[dict[str, Any]]:
    rows = []
    factor_values = (
        ("initial_factor", "IC", "0.0090"), ("initial_factor", "RankIC", "0.0061"),
        ("mutated_factor", "IC", "0.0073"), ("mutated_factor", "RankIC", "0.0021"),
        ("evolved_factor", "IC", "0.0141"), ("evolved_factor", "RankIC", "0.0087"),
        ("many_factor_threshold", "absolute_IC_above", "0.05"),
        ("many_factor_threshold", "absolute_RankIC_above", "0.07"),
    )
    for edition in ("arxiv_v1", "arxiv_v4_acl_final"):
        for result, metric, display in factor_values:
            rows.append(
                {
                    "edition": edition, "location": "prose_or_listing", "result": result,
                    "metric": metric, "display_value": display, "numeric_value": float(display),
                    "duplicate_kind": "none", "author_output_correspondence": False,
                    "native_result_regenerated": False, "paper_result_credit": False,
                }
            )
        for series in ("65-80 Strategy", "80-90 Strategy", "85-95 Strategy", "Benchmark"):
            rows.append(
                {
                    "edition": edition, "location": "cumulative_return_figure", "result": series,
                    "metric": "line_series", "display_value": "author_shipped_raster_only",
                    "numeric_value": "", "duplicate_kind": "none",
                    "author_output_correspondence": True,
                    "native_result_regenerated": False, "paper_result_credit": False,
                }
            )
    elite = (
        ("elite_factor_1_train", ("-0.0498", "-0.0791", "-0.3416", "-0.5016")),
        ("elite_factor_1_test", ("0.0507", "0.0704", "0.3116", "0.4262")),
        ("elite_factor_2_train", ("-0.0473", "-0.0668", "-0.3749", "-0.4473")),
        ("elite_factor_2_test", ("0.0491", "0.069", "0.2717", "0.3604")),
        ("elite_factor_3_train", ("-0.0552", "-0.0742", "-0.475", "-0.5141")),
        ("elite_factor_3_test", ("0.0503", "0.0663", "0.3017", "0.392")),
    )
    for result, values in elite:
        for metric, display in zip(METRICS4, values):
            rows.append(
                {
                    "edition": "arxiv_v4_acl_final", "location": "appendix_elite_factor",
                    "result": result, "metric": metric, "display_value": display,
                    "numeric_value": float(display), "duplicate_kind": "none",
                    "author_output_correspondence": False,
                    "native_result_regenerated": False, "paper_result_credit": False,
                }
            )
    return rows


def prompt_inventory(scratch: Path) -> list[dict[str, Any]]:
    prompt_root = scratch / "prompt-repo/prompts"
    rows = []
    for path in sorted(prompt_root.rglob("*.md")):
        if path.name == "README.md":
            continue
        relative = str(path.relative_to(scratch / "prompt-repo"))
        text = path.read_text()
        family = path.relative_to(prompt_root).parts[0]
        placeholders = sorted(set(re.findall(r"\{[A-Za-z][A-Za-z0-9_]*\}", text)))
        rows.append(
            {
                "path": relative,
                "family": family,
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "placeholders": "|".join(placeholders),
                "author_owned_release": True,
                "release_commit": PROMPT_COMMIT,
                "release_date_utc": "2026-07-14T03:09:02Z",
                "postdates_arxiv_v1": True,
                "postdates_arxiv_v4": True,
                "native_prompt_specification_credit": True,
                "runtime_model_call_replayed": False,
                "paper_result_credit": False,
            }
        )
    if len(rows) != 39:
        raise ValueError(f"expected 39 prompt templates, got {len(rows)}")
    expected_families = {
        "multi_agent_quality_checker": 4,
        "seven_level_agent_hierarchy": 22,
        "shared": 11,
        "thinking_evolution": 2,
    }
    if Counter(row["family"] for row in rows) != expected_families:
        raise ValueError("prompt-family denominator changed")
    return rows


def fenced_text(path: Path) -> str:
    match = re.search(r"````text\n(.*?)\n````", path.read_text(), re.S)
    if not match:
        raise ValueError(f"missing text fence: {path}")
    return match.group(1).strip()


def component_execution(scratch: Path) -> dict[str, Any]:
    frame = pd.DataFrame(
        {
            "open": [10.0, 20.0], "high": [12.0, 24.0], "low": [8.0, 18.0],
            "close": [11.0, 19.0], "volume": [100.0, 200.0],
        }
    )
    upward = (frame["high"] - frame["close"]) / (frame["volume"] + 1e-9)
    range_factor = (frame["high"] - frame["low"]) / (frame["volume"] + 1e-9)
    evolved = np.tanh(
        (frame["close"] - frame["open"]).abs()
        / (frame["volume"] * frame["close"] + 1e-9)
    )
    prompt_root = scratch / "prompt-repo/prompts"
    agent = fenced_text(prompt_root / "seven_level_agent_hierarchy/agent_market_cycle.md")
    agent = agent.split("\n---\n\n## Shared Blocks", maxsplit=1)[0]
    substitutions = {
        "{columns_num}": "5", "{columns_desc}": "open, high, low, close, volume",
        "{num_per_request}": "2", "{forecast_horizon}": "10",
    }
    for key, value in substitutions.items():
        agent = agent.replace(key, value)
    shared = [
        fenced_text(prompt_root / "shared/requirements.md"),
        fenced_text(prompt_root / "shared/libraries_and_coding_guidelines.md"),
        fenced_text(prompt_root / "shared/output_format.md"),
    ]
    assembled = "\n\n---\n\n".join([agent, *shared])
    unresolved = sorted(set(re.findall(r"\{[A-Za-z][A-Za-z0-9_]*\}", assembled)))
    if unresolved:
        raise ValueError(f"unresolved declared prompt placeholders: {unresolved}")
    return {
        "declared_synthetic_fixture": frame.to_dict(orient="list"),
        "published_factor_listings_executed": 3,
        "computed": {
            "factor_upward_impact_per_vol": [round(value, 12) for value in upward],
            "factor_dayhigh_impact_per_vol": [round(value, 12) for value in range_factor],
            "factor_price_impact_per_vol_tanh_1d": [round(value, 12) for value in evolved],
        },
        "prompt_component": {
            "family": "seven_level_agent_hierarchy/agent_market_cycle",
            "assembled_user_prompt_bytes": len(assembled.encode()),
            "assembled_user_prompt_sha256": hashlib.sha256(assembled.encode()).hexdigest(),
            "unresolved_declared_placeholders": unresolved,
            "model_request_sent": False,
            "model_response_received": False,
        },
        "paper_input_used": False,
        "native_experiment_runner_used": False,
        "paper_result_credit": False,
    }


def method_audit() -> list[dict[str, str]]:
    values = (
        ("framework_architecture", "described", "Seven-level hierarchy, quality checker, adaptive generation, and thinking evolution are described."),
        ("prompt_templates", "released_post_v4", "39 author-owned templates are pinned at the sole 2026-07-14 commit."),
        ("prompt_assembly", "documented", "The release documents prompt blocks, ordering, and placeholders."),
        ("runtime_source", "missing", "The prompt repository explicitly excludes runtime code."),
        ("exact_dependency_lock", "missing", "No executable environment or dependency lock is released."),
        ("dataset_sources", "named", "Qlib and Yahoo Finance are named for five datasets."),
        ("point_in_time_data_snapshot", "missing", "No frozen OHLCV files, download timestamps, or hashes are released."),
        ("universe_membership", "missing", "No date-specific CSI300/CSI500/SP500/HSI/HSCI constituent membership is released."),
        ("calendar_and_adjustment", "missing", "Trading calendars and price adjustment conventions are not operationally locked."),
        ("train_validation_test_dates", "described", "Chronological dates are printed for each dataset."),
        ("forecast_horizons", "described", "10-day and selected 30-day horizons are printed."),
        ("label_construction", "partial", "Open-to-open target prose lacks full alignment and missing-day implementation."),
        ("base_fields", "described", "Daily OHLCV fields are named."),
        ("portfolio_rule", "partial", "Top-50/drop-5, open execution, and costs are described without a complete runner."),
        ("model_family", "described", "gpt-oss-120b is the default local model."),
        ("immutable_model_checkpoint", "missing", "No checkpoint hash, serving stack, or tokenizer lock is released."),
        ("runtime_requests_responses", "missing", "No actual prompt instances, model outputs, or request logs are released."),
        ("sampling_parameters", "missing", "Temperature, decoding parameters, batching, and retry behavior are absent."),
        ("random_seeds", "missing", "The paper acknowledges randomness but supplies no seeds."),
        ("single_run_selection", "under_specified", "Results are from one mining round, with no selection trace or rerun distribution."),
        ("initial_factor_pool", "missing", "The realized initial pool is not released."),
        ("evolved_factor_pool", "missing", "The realized candidates, parents, children, elites, and failures are not released."),
        ("quality_checker_outputs", "missing", "No judgments, repairs, unit-test reports, or leakage-test traces are released."),
        ("adaptive_generation_memory", "missing", "No effective/ineffective summaries or feedback trajectory is released."),
        ("baseline_implementations", "missing", "Exact baseline code, versions, tuning, and seeds are not released."),
        ("lightgbm_ridge_configuration", "missing", "Learner hyperparameters and training seeds are not operationally locked."),
        ("metric_equations", "described", "IC, RankIC, ICIR, RankICIR, AER, and IR equations appear in the appendix."),
        ("metric_edge_cases", "missing", "Cross-section filters, NaNs, ties, annualization N, and aggregation details are incomplete."),
        ("transaction_costs", "described", "Open 0.05%, close 0.15%, and 5 CNY minimum fee are printed."),
        ("actions_orders_fills", "missing", "No orders, fills, turnover, or holdings are released."),
        ("predictions", "missing", "No per-date/per-security predictions are released."),
        ("portfolio_returns", "missing", "No dated native return array is released."),
        ("raw_result_arrays", "missing", "No table-cell or statistical-result arrays are released."),
        ("author_curve_raster", "released", "The exact four-series cumulative-return raster is present in both source archives."),
        ("full_end_to_end_pipeline", "missing", "No public artifact can regenerate prompts-to-factors-to-results end to end."),
    )
    return [{"dimension": a, "status": b, "evidence": c} for a, b, c in values]


def consistency_audit() -> list[dict[str, str]]:
    values = (
        ("v1_source_rebuild", "fails_unmodified", "The declared v1 pdflatex build aborts because numeric main.bbl conflicts with author-year natbib."),
        ("v4_source_rebuild", "passes", "Unmodified v4 source builds to 35 pages with 99.968% extracted-token multiset overlap."),
        ("v4_acl_lineage", "passes_near_identity", "ACL final and arXiv v4 have 99.49% token overlap; differences are principally proceedings layout/pagination."),
        ("v1_baseline_count", "passes", "The v1 table contains 19 baselines plus CogAlpha."),
        ("v4_baseline_count", "passes", "The v4 table contains 21 baselines plus CogAlpha."),
        ("v1_all_metric_superiority", "contradicted", "RandomForest RankICIR 0.4385 exceeds CogAlpha 0.4350 despite v1 claiming all-metric superiority."),
        ("v4_all_metric_superiority", "qualified_in_prose", "V4 explicitly identifies RandomForest RankICIR as the sole exception."),
        ("ablation_repeat_lineage", "passes_exact_display", "Base and full ablation rows exactly repeat main-table gpt-oss-120B and CogAlpha values."),
        ("cross_dataset_repeat_lineage", "passes_exact_display", "Sixteen CSI300-10 cells exactly repeat the main table."),
        ("significantly_improved_factor", "no_statistical_test", "The 0.0141/0.0087 factor is called significantly improved without an uncertainty estimate or test."),
        ("threshold_curve_claim", "author_output_only", "The shipped raster visually supports 65-80 endpoint dominance but no dates or curve arrays permit regeneration."),
        ("all_datasets_public", "source_named_not_snapshot_released", "Qlib/Yahoo are named, but exact point-in-time panels and memberships are not released."),
        ("source_code_release_claim", "prompt_only_release", "V1 promises all source code; the sole author release explicitly contains prompts only."),
        ("single_round_randomness", "not_reproducible", "The paper reports one stochastic mining round without seeds, requests, responses, or selection traces."),
    )
    return [{"check": a, "status": b, "evidence": c} for a, b, c in values]


def discovery_ledger(scratch: Path) -> list[dict[str, Any]]:
    files = (
        ("author_prompt_repository", "repo_api/repository.json", 1, True, "prompt_templates_only"),
        ("github_exact_title_repository_search", "discovery/github-repositories-title.json", 0, False, "no_exact_title_repository"),
        ("github_arxiv_code_search", "discovery/github-code-arxiv.json", 68, False, "indexes_and_citations_no_additional_native_system"),
        ("github_title_code_search", "discovery/github-code-title.json", 46, False, "prompt_repo_plus_indexes_or_citations"),
        ("author_account_repository_inventory", "discovery/github-author-repos.json", 27, False, "only_prompt_repo_attributable_to_cogalpha"),
        ("huggingface_model_search", "discovery/hf-models.json", 0, False, "no_cogalpha_model"),
        ("huggingface_dataset_search", "discovery/hf-datasets.json", 0, False, "no_cogalpha_dataset"),
    )
    return [
        {
            "route": route, "pinned_source": source, "result_count": count,
            "attributable_native_artifact_recovered": recovered,
            "finding": finding,
            "negative_search_limit": "Bounded current search; not proof that private, deleted, moved, or unindexed artifacts never existed.",
        }
        for route, source, count, recovered, finding in files
    ]


def build(scratch: Path, output: Path) -> dict[str, Any]:
    validated = validate_inputs(scratch)
    history, fork_branches, fork_summary = public_history_and_fork_audit(scratch)
    output.mkdir(parents=True, exist_ok=True)
    tables = table_ledger(scratch)
    prose_figures = prose_and_figure_ledger()
    prompts = prompt_inventory(scratch)
    write_csv(output / "published_table_result_ledger.csv", tables)
    write_csv(output / "published_prose_figure_ledger.csv", prose_figures)
    write_csv(output / "prompt_release_inventory.csv", prompts)
    write_csv(output / "method_specification_audit.csv", method_audit())
    write_csv(output / "internal_consistency_audit.csv", consistency_audit())
    write_csv(output / "discovery_evidence.csv", discovery_ledger(scratch))
    write_csv(output / "released_source_history_inventory.csv", history)
    write_csv(output / "public_fork_branch_ref_snapshot.csv", fork_branches)
    write_json(output / "public_fork_census.json", fork_summary)
    write_json(output / "component_execution.json", component_execution(scratch))

    by_edition = {}
    for edition in ("arxiv_v1", "arxiv_v4_acl_final"):
        table_rows = [row for row in tables if row["edition"] == edition]
        other_rows = [row for row in prose_figures if row["edition"] == edition]
        by_edition[edition] = {
            "table_cells": len(table_rows),
            "unique_table_cells_after_declared_repeats": sum(row["duplicate_kind"] == "none" for row in table_rows),
            "additional_unique_prose_numeric_units": sum(bool(row["numeric_value"]) for row in other_rows),
            "figure_line_series": sum(row["metric"] == "line_series" for row in other_rows),
            "total_unique_empirical_units": (
                sum(row["duplicate_kind"] == "none" for row in table_rows) + len(other_rows)
            ),
            "native_empirical_units_regenerated": 0,
        }
    if by_edition != {
        "arxiv_v1": {
            "table_cells": 150, "unique_table_cells_after_declared_repeats": 138,
            "additional_unique_prose_numeric_units": 8, "figure_line_series": 4,
            "total_unique_empirical_units": 150, "native_empirical_units_regenerated": 0,
        },
        "arxiv_v4_acl_final": {
            "table_cells": 298, "unique_table_cells_after_declared_repeats": 270,
            "additional_unique_prose_numeric_units": 32, "figure_line_series": 4,
            "total_unique_empirical_units": 306, "native_empirical_units_regenerated": 0,
        },
    }:
        raise ValueError(f"edition denominators changed: {by_edition}")

    provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv": {
            "id": ARXIV_ID,
            "v1_submitted_utc": "2025-11-24T07:45:59Z",
            "v4_submitted_utc": "2026-07-11T07:17:04Z",
            "versions": 4,
            "v1_pages": 27,
            "v4_pages": 35,
            "v1_unmodified_rebuild": False,
            "v1_build_blocker": "numeric main.bbl incompatible with author-year natbib",
            "v4_unmodified_rebuild": True,
            "v4_rebuild_pages": 35,
            "v4_rebuild_extracted_token_multiset_jaccard": 0.9996825396825397,
            "acl_final_pages": 35,
            "v4_to_acl_final_extracted_token_multiset_jaccard": 0.9949420442571127,
            "visual_qa": {
                "editions_inspected": 3, "pages_inspected": 97,
                "unreadable_blank_clipped_or_overlapping_pages": 0,
            },
        },
        "prompt_release": {
            "repository": PROMPT_REPOSITORY,
            "commit": PROMPT_COMMIT,
            "created_utc": "2026-07-14T02:46:37Z",
            "commit_utc": "2026-07-14T03:09:02Z",
            "commit_count": 1,
            "license": None,
            "templates": 39,
            "runtime_code_included": False,
            "datasets_included": False,
            "experiment_outputs_included": False,
            "complete_public_history_audited": True,
            "public_history_commits": len(history),
            "public_history_tracked_paths": history[0]["tracked_paths"],
            "public_history_archive_snapshot_paths_exact": history[0][
                "archive_snapshot_paths_exact"
            ],
            "public_history_result_artifacts_found": 0,
            "public_fork_census_date": fork_summary["census_date"],
            "public_forks_accessible": fork_summary["accessible_public_forks"],
            "public_fork_branch_refs_audited": fork_summary["accessible_branch_refs"],
            "public_fork_unique_heads_audited": fork_summary["unique_heads"],
            "public_fork_divergent_heads_audited": fork_summary[
                "divergent_unique_heads"
            ],
            "public_fork_native_result_artifacts_found": False,
            "public_fork_paper_result_credit": False,
        },
        "validated_inputs": validated,
    }
    write_json(output / "source_provenance.json", provenance)

    readme = """# CogAlpha paper-faithfulness audit

This fail-closed audit separates the 27-page arXiv v1 study, the materially
expanded 35-page arXiv v4/ACL-final study, and the late author-owned prompt-only
release.  It does not use the existence of prompts or manuscript assets as a
substitute for native experiment reproduction.

## Honest reproduction boundary

The native CogAlpha experiments are **not reproduced**.  ArXiv v1 contains 150
unique empirical units after accounting for table repeats, and arXiv v4/ACL
final contains 306; 0/150 and 0/306 regenerate from a native pipeline.  The
author source does ship the exact four-series cumulative-return raster, so 4/4
curve series receive author-output correspondence credit, not regeneration
credit.  Three published factor listings and one declared prompt assembly run
on synthetic fixtures and receive source-component credit only.

The sole author repository is a single 2026-07-14 commit, after arXiv v4.  It
contains 39 attributable prompt templates and explicit assembly instructions,
but its README says it intentionally excludes runtime code, datasets,
experiment outputs, private model endpoints, and local paths.  No experiment
runner, frozen constituent memberships/OHLCV snapshot, immutable model
checkpoint or request log, realized factor pools, checker/evolution traces,
seeds, predictions, actions, holdings, dated returns, or raw result arrays are
released.

The complete public Git surface was also exhausted as of 2026-08-14.  The
official history has exactly that one commit, and all 47 Git paths are
byte-for-byte identical to the pinned release archive.  Across the full history
there is no structured result/data payload and none of six distinctive
published result values.  GitHub reports one accessible fork with one branch
ref and no tag refs; it resolves exactly to the official head and adds zero
result lineage.  It adds zero unique commits, zero unique blobs, and zero
paper-result credit.

## Edition denominators

- ArXiv v1: 150 table cells, 138 unique after 12 repeated cells; eight
  additional numeric factor claims; four cumulative-return series; 150 unique
  empirical units in total; 0 regenerated.
- ArXiv v4 / ACL final: 298 table cells, 270 unique after 28 repeated cells;
  32 additional numeric factor claims; four cumulative-return series; 306
  unique empirical units in total; 0 regenerated.
- Prompt release: 39 templates (22 hierarchy, 11 shared, four quality-checker,
  two thinking-evolution), all attributable and pinned, but zero model calls or
  paper outputs replayed.

## Source and claim findings

ArXiv v4 rebuilds unmodified to 35 pages at 0.999683 extracted-token multiset
Jaccard, and the ACL final is 0.994942 aligned with v4.  ArXiv v1 does not build
unmodified: its declared numeric `main.bbl` conflicts with author-year
`natbib`.  V1 also claims CogAlpha wins every metric although RandomForest's
0.4385 RankICIR exceeds CogAlpha's 0.4350; v4 explicitly acknowledges that
exception.  The paper calls one factor improvement significant without a test,
and its single stochastic mining round has no seeds or trace.

All 97 pages across v1, v4, and ACL final were visually inspected without a
blank, clipped, overlapping, or unreadable page.  Negative artifact searches
are bounded observations, not proof that private, deleted, moved, or unindexed
artifacts never existed.  No local proxy is credited as CogAlpha.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")

    manifest: dict[str, Any] = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "editions": by_edition,
        "author_prompt_repository_recovered": True,
        "author_prompt_template_count": len(prompts),
        "author_prompt_model_calls_replayed": 0,
        "author_output_curve_series_correspondence": 4,
        "author_output_curve_series_regenerated": 0,
        "published_factor_listings_executed_on_synthetic_fixture": 3,
        "native_empirical_units_regenerated": 0,
        "repository_history_commits_audited": len(history),
        "repository_history_tracked_paths": history[0]["tracked_paths"],
        "repository_history_archive_snapshot_paths_exact": history[0][
            "archive_snapshot_paths_exact"
        ],
        "repository_history_result_artifacts_found": 0,
        "public_fork_census_date": fork_summary["census_date"],
        "public_forks_reported_by_github_rest": fork_summary[
            "github_rest_reported_forks"
        ],
        "public_forks_accessible": fork_summary["accessible_public_forks"],
        "public_fork_branch_refs_audited": fork_summary["accessible_branch_refs"],
        "public_fork_tag_refs_audited": fork_summary["tag_refs"],
        "public_fork_unique_heads_audited": fork_summary["unique_heads"],
        "public_fork_divergent_heads_audited": fork_summary["divergent_unique_heads"],
        "public_fork_unique_commits_beyond_official_history": fork_summary[
            "unique_commits_beyond_official_history"
        ],
        "public_fork_unique_blobs_beyond_official_history": fork_summary[
            "unique_blobs_beyond_official_history"
        ],
        "public_fork_native_result_artifacts_found": False,
        "public_fork_paper_result_credit": False,
        "full_end_to_end_pipeline_reproduced": False,
        "paper_evidence_route": "public_prompt_specification_only",
        "output_sha256": {},
    }
    output_files = sorted(
        path for path in output.iterdir()
        if path.is_file() and path.name != "manifest.json"
    )
    manifest["output_sha256"] = {path.name: sha256(path) for path in output_files}
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch, args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if args.strict and not manifest["full_end_to_end_pipeline_reproduced"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
