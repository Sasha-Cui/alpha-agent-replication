#!/usr/bin/env python3
"""Build a fail-closed paper/source audit for AAPM.

The audit treats arXiv v1, arXiv v2, the paper-era repository commit, the
current official repository, and the released metadata as distinct evidence.
It never promotes a paper-displayed number or author-generated raster image to
an independently reproduced result.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]

ARXIV_RECORD = "https://arxiv.org/abs/2409.17266"
V1_PDF_URL = "https://arxiv.org/pdf/2409.17266v1"
V2_PDF_URL = "https://arxiv.org/pdf/2409.17266v2"
OFFICIAL_REPOSITORY = "https://github.com/chengjunyan1/AAPM"
V1_PDF_SHA256 = "ef2642acb9ac61b2fd87849a97b81c0aad281ab247f27d7f3deb8fea935ee61f"
V2_PDF_SHA256 = "7e485996d52da6e48b1ac253947b2e9e01904a744c79f5af5dc1b91d1c3f4ded"
V1_SOURCE_SHA256 = "c2fe1b9cf4efc069873b83fe32d74f14fa77f167394007dd0746ac2944b84a01"
V2_SOURCE_SHA256 = "4c81eea6f0d9184258620ede7774350e94916f4e1cebc05fde8067942a81a782"
V1_PAGES = 14
V2_PAGES = 19

CURRENT_HEAD = "cc54e4337fcd4089dc69e4a1173e82a675648475"
PAPER_ERA_COMMIT = "f7096b19c9387377b7f3c9ca9795345321968a7c"
PAPER_ERA_COMMIT_UTC = "2024-09-25T18:06:58Z"
PAPER_ERA_TREE_SHA256 = "4617508f0c4fc984a97ca258d575963adeb589aef4db7b9bee86d48d9315856c"
PAPER_ERA_ARCHIVE_SHA256 = "3e5b0a22abe15a3d55ff933c03f8e4859190dca23a75eb2980983765836022f3"
CURRENT_TREE_SHA256 = "fe28d88828b080f86f7493c182d5d7f29d4e4cd92a2d9f4e526cc08dfb7794e3"
CURRENT_ARCHIVE_SHA256 = "50a30166b77a2835852585b1a164e96e11e03d42e4b1b1e6038485480f5e829b"
METADATA_SHA256 = "0cf4923806f6c2d6b87aa06cae6a1651aa6ba4e146f90ee74d941592bdabc641"
EXPECTED_TRACKED_FILES = 10
EXPECTED_PYTHON_FILES = 5
EXPECTED_METADATA_ROWS = 65_733
EXPECTED_V1_RESULT_CELLS = 114
EXPECTED_V2_RESULT_CELLS = 162
REPOSITORY_ROOT = "498688d8dccb0bbbb667589eca1a0f94091dbc88"
REPOSITORY_COMMIT_COUNT = 9
PUBLIC_FORK_CENSUS_DATE = "2026-08-14"
PUBLIC_FORK_SNAPSHOT_SHA256 = "fb406e6fcc3a4f6baed2eeadf0f48f714f540a8f22d951c086dbdda48163491f"
PUBLIC_FORK_BRANCHES = (
    ("jingmouren/chengjunyan1-AAPM", "6c97ee30007dcc74871bbac23aeab9af13f850bd", 5),
    ("shu-cj/AAPM", "6c97ee30007dcc74871bbac23aeab9af13f850bd", 5),
    ("pengmeishu/AAPM", "6c8324fddc6ba5d2f548cc4da06aa851507929a2", 4),
    ("yinsenm/AAPM", "65e724d17a87de08789b3b97e4c920152e3220d4", 3),
    ("potpen/AAPM", "65e724d17a87de08789b3b97e4c920152e3220d4", 3),
    ("HS991023/AAPM", "65e724d17a87de08789b3b97e4c920152e3220d4", 3),
    ("Lycokie/AAPM", "65e724d17a87de08789b3b97e4c920152e3220d4", 3),
    ("d3p10y/AAPM", "65e724d17a87de08789b3b97e4c920152e3220d4", 3),
    ("Minisoco/AAPM", "65e724d17a87de08789b3b97e4c920152e3220d4", 3),
    ("coder-drinker/AAPM", "65e724d17a87de08789b3b97e4c920152e3220d4", 3),
    ("tufo830/AAPM", "65e724d17a87de08789b3b97e4c920152e3220d4", 3),
    ("tutuna/AAPM", "65e724d17a87de08789b3b97e4c920152e3220d4", 3),
    ("ch1plus1/AAPM", CURRENT_HEAD, 0),
    ("yangkedc1984/AAPM", CURRENT_HEAD, 0),
)
PUBLIC_FORK_COUNT = 14
PUBLIC_FORK_BRANCH_REF_COUNT = 14
PUBLIC_FORK_UNIQUE_HEAD_COUNT = 4
PUBLIC_FORK_TAG_REF_COUNT = 0
REQUIREMENTS_SHA256 = "f0e7f9acc96283e678b3f5bc1f78b84a65f360ff327d31adf67f982510f0a77d"
DEFAULT_PAPER_PYTHON = ROOT / "scripts/run_aapm_paper_python.sh"
PAPER_ENV_FREEZE_SHA256 = (
    "b6010c0bca5dd6bb77adb1872e79c488f08679331ea04f34acacf75949028d7a"
)
METADATA_INDEX_DRIVER_SHA256 = (
    "37f7308f6a3339f64693a832abc66b7a64cc3496bbdbd85f48490122f7bf8f10"
)
METADATA_INDEX_EVIDENCE_SHA256 = {
    "aapm_embedding_model_snapshot.csv": "8e2724d206b22892751090a751a0c3c31ac40aaf926f519dfd60142da9076892",
    "aapm_metadata_index_conformance.csv": "64cfed5af4d3d400ffb9293d8f609457c5e67fdc1d339ca9667637e5104430db",
    "aapm_metadata_index_probe.json": "e1d265dbd7d469ae92f9173d2ff341fad92c1ac5802d1f886ca24aa12654c942",
    "aapm_reconstructed_metadata_index.csv": "aabf06376b8cf51ea02a42f90cc0aab0abcf46ed99ce52495aa70a8b5d9f149c",
}
METADATA_INDEX_ROWS = 65_733
METADATA_INDEX_BYTES = 1_901_562
METADATA_INDEX_SHA256 = (
    "aabf06376b8cf51ea02a42f90cc0aab0abcf46ed99ce52495aa70a8b5d9f149c"
)
EMBEDDING_MODEL_REPOSITORY = "BAAI/bge-large-en-v1.5"
EMBEDDING_MODEL_REVISION = "d4aa6901d3a41ba39fb536a557fa166f842b0e09"
EMBEDDING_MODEL_MANIFEST_SHA256 = (
    "7b0b0c8f2a12c68ef6160da7d9e2b0a37404d35f3eded172a52856c0b6959a67"
)

TABLE_METRICS = {
    "table:sr": ["SR_TP", "SR_EW", "SR_VW", "MDD_TP", "MDD_EW", "MDD_VW"],
    "table:ape": ["avg_abs_alpha", "avg_abs_t_alpha", "significant_share", "GRS"],
    "table:abl": ["SR_EW", "MDD_EW", "avg_abs_alpha", "avg_abs_t_alpha"],
    "table:abl_fm": ["SR_EW", "MDD_EW", "avg_abs_alpha", "avg_abs_t_alpha", "input_cost", "output_cost"],
}
RESULT_FIGURES = {"ablation_nk.png", "deciles.png", "econ_preds.png", "tickers_preds.png"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git(repo: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=not binary,
    )
    return result.stdout


def ref_tree_sha256(repo: Path, ref: str) -> str:
    return bytes_sha256(bytes(git(repo, "ls-tree", "-r", ref, binary=True)))


def ref_archive_sha256(repo: Path, ref: str) -> str:
    return bytes_sha256(bytes(git(repo, "archive", "--format=tar", ref, binary=True)))


def validate_pdf(path: Path, version: str) -> tuple[str, list[dict[str, str]]]:
    expected_sha = V1_PDF_SHA256 if version == "v1" else V2_PDF_SHA256
    expected_pages = V1_PAGES if version == "v1" else V2_PAGES
    if sha256(path) != expected_sha:
        raise ValueError(f"{version} PDF hash changed")
    reader = PdfReader(path)
    if len(reader.pages) != expected_pages:
        raise ValueError(f"{version} page count changed: {len(reader.pages)}")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized = " ".join(text.split())
    title = (
        "AAPM: Large Language Model Agent-based Asset Pricing Models"
        if version == "v1" else "EMPIRICAL ASSET PRICING WITH LARGE LANGUAGE MODEL AGENTS"
    )
    required = [title, "Junyan Cheng", "Peter Chin"]
    if version == "v1":
        required += ["two years of news", "9.6%", "10.8%"]
    else:
        required += ["three years of news", "10.6%", "10.0%", "O1-Preview"]
    for phrase in required:
        if phrase not in normalized:
            raise ValueError(f"{version} required text missing: {phrase}")
    links: list[dict[str, str]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        for annotation_ref in page.get("/Annots", []):
            annotation = annotation_ref.get_object()
            action = annotation.get("/A")
            uri = action.get("/URI") if action else None
            if uri:
                links.append({"page": str(page_number), "uri": str(uri)})
    if not any(row["uri"].rstrip("/") == OFFICIAL_REPOSITORY for row in links):
        raise ValueError(f"{version} official repository annotation missing")
    return text, links


def validate_sources(v1_archive: Path, v2_archive: Path, v1_source: Path, v2_source: Path) -> tuple[str, str]:
    if sha256(v1_archive) != V1_SOURCE_SHA256:
        raise ValueError("v1 source archive hash changed")
    if sha256(v2_archive) != V2_SOURCE_SHA256:
        raise ValueError("v2 source archive hash changed")
    v1_tex = (v1_source / "acl.tex").read_text(encoding="utf-8")
    v2_tex = (v2_source / "iclr2025_conference.tex").read_text(encoding="utf-8")
    for version, text in (("v1", v1_tex), ("v2", v2_tex)):
        if OFFICIAL_REPOSITORY not in text:
            raise ValueError(f"official repository URL missing from {version} source")
    return v1_tex, v2_tex


def validate_repo(repo: Path) -> list[str]:
    if str(git(repo, "rev-parse", "HEAD")).strip() != CURRENT_HEAD:
        raise ValueError("official repository HEAD changed")
    if ref_tree_sha256(repo, PAPER_ERA_COMMIT) != PAPER_ERA_TREE_SHA256:
        raise ValueError("paper-era repository tree changed")
    if ref_archive_sha256(repo, PAPER_ERA_COMMIT) != PAPER_ERA_ARCHIVE_SHA256:
        raise ValueError("paper-era repository archive changed")
    if ref_tree_sha256(repo, "HEAD") != CURRENT_TREE_SHA256:
        raise ValueError("current repository tree changed")
    if ref_archive_sha256(repo, "HEAD") != CURRENT_ARCHIVE_SHA256:
        raise ValueError("current repository archive changed")
    if subprocess.run(["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--"]).returncode:
        raise ValueError("official repository tracked files are dirty")
    paths = str(git(repo, "ls-files")).splitlines()
    if len(paths) != EXPECTED_TRACKED_FILES:
        raise ValueError(f"tracked file count changed: {len(paths)}")
    changed = str(git(repo, "diff", "--name-only", f"{PAPER_ERA_COMMIT}..HEAD")).splitlines()
    if changed != ["README.md"]:
        raise ValueError(f"unexpected paper-era/current changes: {changed}")
    return paths


def source_inventory(repo: Path, paths: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    compiled = 0
    for name in paths:
        path = repo / name
        payload = ("SYMLINK:" + os.readlink(path)).encode() if path.is_symlink() else path.read_bytes()
        status = "not_python"
        if name.endswith(".py"):
            try:
                compile(path.read_text(encoding="utf-8", errors="replace"), name, "exec")
                status = "compiled"
                compiled += 1
            except Exception as error:  # pragma: no cover - future source drift
                status = f"{type(error).__name__}:{error}"
        if name == "data/wsj_metadata.json":
            role = "released_metadata_only"
        elif name == "config.yaml":
            role = "configuration"
        elif name == "requirements.txt":
            role = "dependency_manifest"
        elif name == "LICENSE":
            role = "license"
        elif name == "README.md":
            role = "documentation"
        else:
            role = "implementation_source"
        rows.append({
            "path": name, "bytes": str(len(payload)), "sha256": bytes_sha256(payload),
            "role": role, "compile_status": status,
            "author_result_output": "no", "end_to_end_result_credit": "no",
        })
    if compiled != EXPECTED_PYTHON_FILES:
        raise ValueError(f"compiled Python count changed: {compiled}")
    return rows


def source_history_inventory(repo: Path) -> list[dict[str, Any]]:
    """Inventory every public revision and verify that later changes are documentation-only."""
    if str(git(repo, "rev-parse", "--is-shallow-repository")).strip() != "false":
        raise ValueError("AAPM history checkout is shallow")
    commits = str(
        git(repo, "rev-list", "--reverse", "refs/remotes/origin/main")
    ).splitlines()
    if len(commits) != REPOSITORY_COMMIT_COUNT:
        raise ValueError(f"AAPM public commit count changed: {len(commits)}")
    if commits[0] != REPOSITORY_ROOT or commits[-1] != CURRENT_HEAD:
        raise ValueError(f"AAPM public-history endpoints changed: {commits}")

    rows: list[dict[str, Any]] = []
    for commit in commits:
        authored_at, subject = str(
            git(repo, "show", "-s", "--format=%aI%x09%s", commit)
        ).rstrip("\n").split("\t", 1)
        paths = str(git(repo, "ls-tree", "-r", "--name-only", commit)).splitlines()
        result_paths = [
            path
            for path in paths
            if any(
                part in {
                    "checkpoint", "checkpoints", "embedding", "embeddings", "factor", "factors",
                    "log", "logs", "output", "outputs", "portfolio", "portfolios", "prediction",
                    "predictions", "result", "results", "return", "returns", "run", "runs",
                }
                for part in path.lower().split("/")
            )
            or path.lower().endswith((
                ".ckpt", ".csv", ".jsonl", ".npy", ".npz", ".parquet", ".pickle", ".pkl",
                ".pt", ".pth", ".safetensors", ".xls", ".xlsx",
            ))
        ]
        if result_paths:
            raise ValueError(f"AAPM history contains an unreviewed paper-result path: {result_paths}")
        rows.append({
            "commit": commit,
            "authored_at": authored_at,
            "subject": subject,
            "tracked_paths": len(paths),
            "python_paths": sum(path.endswith(".py") for path in paths),
            "metadata_payload_present": "data/wsj_metadata.json" in paths,
            "paper_result_or_training_artifact_paths": 0,
            "paper_result_artifact_found": False,
        })
    return rows


def public_fork_audit(
    repo: Path, github_evidence_dir: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Exhaust every captured public fork ref without re-crediting official history."""
    snapshot_path = github_evidence_dir / "forks.json"
    if sha256(snapshot_path) != PUBLIC_FORK_SNAPSHOT_SHA256:
        raise ValueError("AAPM public-fork API snapshot changed")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot_by_repo = {item["full_name"]: item for item in snapshot}
    expected_repositories = {repository for repository, _head, _behind in PUBLIC_FORK_BRANCHES}
    if set(snapshot_by_repo) != expected_repositories or len(snapshot) != PUBLIC_FORK_COUNT:
        raise ValueError("AAPM public-fork API repository surface changed")
    if any(item["default_branch"] != "main" for item in snapshot):
        raise ValueError("AAPM public-fork default branch surface changed")

    actual_refs = {}
    for line in str(
        git(
            repo,
            "for-each-ref",
            "--format=%(refname)%09%(objectname)",
            "refs/remotes/forks",
        )
    ).splitlines():
        refname, head = line.split("\t")
        actual_refs[refname] = head
    expected_refs = {
        f"refs/remotes/forks/{repository.split('/', 1)[0]}/main": head
        for repository, head, _behind in PUBLIC_FORK_BRANCHES
    }
    if actual_refs != expected_refs:
        raise ValueError(f"AAPM public-fork branch refs changed: {actual_refs}")
    if str(git(repo, "for-each-ref", "--format=%(refname)", "refs/tags")).strip():
        raise ValueError("AAPM public-fork checkout unexpectedly contains tag refs")

    official = str(git(repo, "rev-parse", "refs/remotes/origin/main")).strip()
    if official != CURRENT_HEAD:
        raise ValueError("AAPM official remote head changed")
    branch_rows = []
    repositories_by_head: dict[str, list[str]] = {}
    for repository, head, expected_behind in PUBLIC_FORK_BRANCHES:
        behind, ahead = map(
            int,
            str(
                git(
                    repo,
                    "rev-list",
                    "--left-right",
                    "--count",
                    f"{official}...{head}",
                )
            ).split(),
        )
        if (ahead, behind) != (0, expected_behind):
            raise ValueError(f"AAPM public-fork relationship changed: {repository}")
        merge_base = str(git(repo, "merge-base", official, head)).strip()
        if merge_base != head:
            raise ValueError(f"AAPM public fork is no longer an official-history head: {repository}")
        extra_commits = str(
            git(repo, "rev-list", head, "--not", "refs/remotes/origin/main")
        ).splitlines()
        if extra_commits:
            raise ValueError(f"AAPM public fork adds unreviewed commits: {repository}")
        captured = snapshot_by_repo[repository]
        branch_rows.append(
            {
                "repository": repository,
                "url": captured["html_url"],
                "branch": "main",
                "head_commit": head,
                "relation_to_official_head": (
                    "official_head_exact" if head == official else "official_history_ancestor"
                ),
                "commits_ahead_of_official": ahead,
                "commits_behind_official": behind,
                "fork_created_at": captured["created_at"],
                "fork_pushed_at": captured["pushed_at"],
                "tag_refs": 0,
                "unique_commits_beyond_official_history": 0,
                "unique_blobs_beyond_official_history": 0,
                "native_result_artifact_found": False,
                "paper_result_credit": False,
            }
        )
        repositories_by_head.setdefault(head, []).append(repository)

    unique_rows = []
    for head in sorted(repositories_by_head):
        subject = str(git(repo, "show", "-s", "--format=%s", head)).strip()
        unique_rows.append(
            {
                "head_commit": head,
                "repositories": ";".join(sorted(repositories_by_head[head])),
                "branch_ref_count": len(repositories_by_head[head]),
                "official_history_reachable": True,
                "official_history_subject": subject,
                "unique_commits_beyond_official_history": 0,
                "unique_blobs_beyond_official_history": 0,
                "native_result_artifact_found": False,
                "paper_result_credit": False,
            }
        )
    if len(unique_rows) != PUBLIC_FORK_UNIQUE_HEAD_COUNT:
        raise ValueError("AAPM public-fork unique-head count changed")
    summary = {
        "census_date": PUBLIC_FORK_CENSUS_DATE,
        "github_rest_reported_forks": PUBLIC_FORK_COUNT,
        "accessible_public_forks": len(branch_rows),
        "accessible_branch_refs": len(branch_rows),
        "tag_refs": PUBLIC_FORK_TAG_REF_COUNT,
        "unique_heads": len(unique_rows),
        "official_history_reachable_unique_heads": len(unique_rows),
        "divergent_unique_heads": 0,
        "unique_commits_beyond_official_history": 0,
        "unique_blobs_beyond_official_history": 0,
        "native_result_artifacts_found": 0,
        "paper_result_credit": False,
        "interpretation": (
            "all accessible public fork refs resolve exactly to the current official "
            "head or commits already covered by the complete nine-commit official-history "
            "audit; the forks add no code, data, checkpoint, prediction, portfolio, return, "
            "training, or result lineage"
        ),
    }
    return branch_rows, unique_rows, summary


def metadata_audit(repo: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    path = repo / "data/wsj_metadata.json"
    if sha256(path) != METADATA_SHA256:
        raise ValueError("released metadata hash changed")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or len(data) != EXPECTED_METADATA_ROWS:
        raise ValueError("released metadata record count changed")
    keys = Counter()
    dates: list[str] = []
    years = Counter()
    months = {
        name: f"{number:02d}" for number, name in enumerate(
            ("", "january", "february", "march", "april", "may", "june",
             "july", "august", "september", "october", "november", "december")
        ) if name
    }
    for key, row in data.items():
        keys.update(row.keys())
        parts = key.split("/")
        date = f"{parts[0]}-{months.get(parts[1], '00')}-{int(parts[2]):02d}" if len(parts) >= 3 else ""
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            dates.append(date)
            years[date[:4]] += 1
    rows = [
        {"check": "records", "value": str(len(data)), "assessment": "present", "paper_result_credit": "no"},
        {"check": "fields", "value": ";".join(sorted(keys)), "assessment": "metadata_only", "paper_result_credit": "no"},
        {"check": "minimum_date", "value": min(dates), "assessment": "outside_claim_by_two_days", "paper_result_credit": "no"},
        {"check": "maximum_date", "value": max(dates), "assessment": "short_of_v2_claim_by_ten_months", "paper_result_credit": "no"},
        {"check": "year_counts", "value": json.dumps(dict(sorted(years.items()))), "assessment": "metadata_only", "paper_result_credit": "no"},
        {"check": "article_bodies", "value": "0", "assessment": "missing", "paper_result_credit": "no"},
        {"check": "returns_or_factors", "value": "0", "assessment": "missing", "paper_result_credit": "no"},
    ]
    facts = {"records": len(data), "fields": sorted(keys), "min_date": min(dates), "max_date": max(dates), "year_counts": dict(sorted(years.items()))}
    return rows, facts


def strip_tex(value: str) -> str:
    value = value.strip()
    previous = None
    while previous != value:
        previous = value
        value = re.sub(r"\\(?:textit|textbf|underline)\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\(?:midrule|bottomrule|toprule).*", "", value)
    value = value.replace("\\", "").strip()
    return " ".join(value.split())


def table_block(tex: str, label: str) -> str:
    for match in re.finditer(r"\\begin\{table\}.*?\\end\{table\}", tex, re.DOTALL):
        block = match.group(0)
        if f"\\label{{{label}}}" in block:
            return block
    raise ValueError(f"table not found: {label}")


def parse_table(tex: str, version: str, label: str) -> list[dict[str, str]]:
    metrics = TABLE_METRICS[label]
    block = table_block(tex, label)
    # v1 breaks the Memory row immediately before its row terminator.
    block = re.sub(r"\r?\n\s*\\\\\s*\r?\n", r"\\\\\n", block)
    rows: list[dict[str, str]] = []
    row_number = 0
    for line in block.splitlines():
        if "&" not in line or "\\" not in line:
            continue
        cells = [strip_tex(cell) for cell in line.split("&")]
        method = cells[0]
        if not method or method in {"Parameter"} or "multicolumn" in line:
            continue
        values: list[str] = []
        for cell in cells[1:]:
            match = re.search(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", cell)
            if match:
                values.append(match.group(0))
        if len(values) != len(metrics):
            continue
        row_number += 1
        for metric, value in zip(metrics, values):
            rows.append({
                "version": version, "table": label, "row_number": str(row_number),
                "method": method, "metric": metric, "displayed_value": value,
                "author_output_available": "no", "independent_end_to_end_reproduction": "no",
                "credit_boundary": "paper_display_only_no_result_credit",
            })
    return rows


def displayed_results(v1_tex: str, v2_tex: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    v1 = sum((parse_table(v1_tex, "v1", label) for label in ("table:sr", "table:ape", "table:abl")), [])
    v2 = sum((parse_table(v2_tex, "v2", label) for label in ("table:sr", "table:ape", "table:abl", "table:abl_fm")), [])
    if len(v1) != EXPECTED_V1_RESULT_CELLS or len(v2) != EXPECTED_V2_RESULT_CELLS:
        raise ValueError(f"result-cell denominator drift: v1={len(v1)} v2={len(v2)}")
    return v1, v2


def version_comparison(v1: list[dict[str, str]], v2: list[dict[str, str]]) -> list[dict[str, str]]:
    def keyed(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, str]]:
        return {(row["table"], row["row_number"], row["metric"]): row for row in rows}
    left, right = keyed(v1), keyed(v2)
    rows: list[dict[str, str]] = []
    for key in sorted(left):
        lrow, rrow = left[key], right[key]
        rows.append({
            "table": key[0], "row_number": key[1], "metric": key[2],
            "v1_method": lrow["method"], "v1_value": lrow["displayed_value"],
            "v2_method": rrow["method"], "v2_value": rrow["displayed_value"],
            "exact_value_match": "yes" if lrow["displayed_value"] == rrow["displayed_value"] else "no",
            "same_experiment_provenance_demonstrated": "no",
        })
    return rows


def figure_inventory(v1_source: Path, v2_source: Path) -> list[dict[str, str]]:
    v1 = {path.name: path for path in sorted((v1_source / "figs").glob("*")) if path.is_file()}
    v2 = {path.name: path for path in sorted((v2_source / "figs").glob("*")) if path.is_file()}
    if set(v1) != set(v2) or len(v1) != 16:
        raise ValueError("figure source inventory changed")
    rows: list[dict[str, str]] = []
    for name in sorted(v1):
        left, right = sha256(v1[name]), sha256(v2[name])
        rows.append({
            "figure": name, "v1_sha256": left, "v2_sha256": right,
            "relationship": "byte_identical" if left == right else "changed",
            "role": "empirical_result_figure" if name in RESULT_FIGURES else "method_or_data_description",
            "underlying_numeric_data_released": "no",
            "independent_reproduction": "no",
        })
    if Counter(row["relationship"] for row in rows) != {"byte_identical": 15, "changed": 1}:
        raise ValueError("v1/v2 figure relationship changed")
    return rows


def figure_units() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    def add(figure: str, unit: str, kind: str, points: int, relationship: str) -> None:
        rows.append({
            "figure": figure, "unit": unit, "unit_kind": kind, "displayed_points": str(points),
            "v1_v2_relationship": relationship, "underlying_array_released": "no",
            "independent_reproduction": "no", "credit_boundary": "raster_display_only_no_result_credit",
        })
    add("ablation_nk.png", "K series", "named_series", 7, "changed")
    add("ablation_nk.png", "N series", "named_series", 7, "changed")
    for decile in range(1, 11):
        add("deciles.png", f"decile {decile}", "named_series", -1, "byte_identical")
    for panel in ("SP500", "DGS10", "BAAFF", "T10YIE", "DCOILBRENTEU", "OBMMIC30YF"):
        add("econ_preds.png", f"{panel} Pred", "named_series", -1, "byte_identical")
        add("econ_preds.png", f"{panel} GT", "named_series", -1, "byte_identical")
        add("econ_preds.png", f"{panel} R2", "title_scalar", 1, "byte_identical")
    for ticker in ("AMZN", "AAPL", "TSLA", "MSFT", "GOOGL", "META", "NVDA", "NFLX"):
        add("tickers_preds.png", f"{ticker} Pred", "named_series", -1, "byte_identical")
        add("tickers_preds.png", f"{ticker} GT", "named_series", -1, "byte_identical")
        add("tickers_preds.png", f"{ticker} R2", "title_scalar", 1, "byte_identical")
    if len(rows) != 54:
        raise AssertionError(len(rows))
    return rows


def claim(version: str, name: str, reported: float, computed: float, basis: str, semantic_issue: str = "") -> dict[str, str]:
    return {
        "version": version, "claim": name, "reported_percent": f"{reported:.1f}",
        "computed_percent": f"{computed:.6f}", "basis": basis,
        "rounded_numeric_match": "yes" if round(computed, 1) == round(reported, 1) else "no",
        "semantic_issue": semantic_issue,
    }


def improvement_claims() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    def imp(new: float, old: float) -> float:
        return (new / old - 1) * 100

    def red(new: float, old: float) -> float:
        return (old - new) / old * 100
    # v1 main tables
    v1_sr = [(4.38, 4.10, 6.8), (3.29, 3.02, 8.9), (3.01, 2.66, 13.2)]
    for label, (new, old, reported) in zip(("TP", "EW", "VW"), v1_sr):
        rows.append(claim("v1", f"Ours SR improvement {label}", reported, imp(new, old), "best displayed baseline"))
    rows.append(claim("v1", "mean Ours SR improvement", 9.6, sum(imp(a, b) for a, b, _ in v1_sr) / 3, "arithmetic mean of three relative improvements"))
    for label, new, old, reported in (("TP", 3.66, 3.77, 2.9), ("EW", 5.64, 5.77, 2.3)):
        rows.append(claim("v1", f"Ours MDD gain {label}", reported, red(new, old), "IPCA"))
    rows.append(claim("v1", "Ours VW MDD underperformance", 10.9, imp(5.17, 4.66), "CA"))
    for label, new, old, reported in (("TP", 4.45, 4.10, 8.5), ("EW", 3.43, 3.02, 13.6), ("VW", 3.09, 2.66, 16.2)):
        rows.append(claim("v1", f"GPT-4 SR improvement {label}", reported, imp(new, old), "best displayed baseline"))
    for label, new, old, reported in (("TP", 3.82, 3.77, 1.3), ("EW", 5.57, 5.77, 3.5), ("VW", 4.77, 4.66, -2.4)):
        rows.append(claim("v1", f"GPT-4 MDD gain {label}", reported, red(new, old), "best displayed baseline", "paper sign is wrong" if label == "TP" else ""))
    for name, new, old, reported in (("Ours alpha reduction", .66, .74, 10.8), ("GPT-4 alpha reduction", .64, .74, 13.5), ("Ours t-value reduction", 2.40, 2.44, 1.6), ("GPT-4 t-value reduction", 2.36, 2.44, 3.3), ("Ours significant-share reduction", .46, .49, 6.1), ("GPT-4 significant-share reduction", .46, .49, 6.1), ("Ours GRS reduction", 6.34, 6.38, .6), ("GPT-4 GRS reduction", 6.28, 6.38, 1.6)):
        issue = "paper calls a lower t-value an increase" if "t-value" in name else ""
        rows.append(claim("v1", name, reported, red(new, old), "paper-named baseline", issue))
    # v2 main tables
    v2_sr = [(4.21, 3.86, 9.0), (3.07, 2.76, 11.2), (2.77, 2.48, 11.7)]
    for label, (new, old, reported) in zip(("TP", "EW", "VW"), v2_sr):
        rows.append(claim("v2", f"Ours SR improvement {label}", reported, imp(new, old), "best displayed baseline"))
    rows.append(claim("v2", "mean Ours SR improvement", 10.6, sum(imp(a, b) for a, b, _ in v2_sr) / 3, "arithmetic mean of three relative improvements"))
    rows.append(claim("v2", "Ours TP MDD gain", 4.3, red(4.00, 4.42), "paper says IPCA; 4.3 is only obtained against CA", "wrong comparator"))
    rows.append(claim("v2", "Ours EW MDD gain", 9.7, red(5.71, 6.32), "IPCA"))
    rows.append(claim("v2", "Ours VW MDD underperformance", 2.3, imp(5.36, 5.24), "actual best is SDF-GAN, not paper-named CA", "wrong comparator name"))
    for label, new, old, reported in (("TP", 4.31, 3.86, 9.1), ("EW", 3.15, 2.76, 14.1), ("VW", 2.90, 2.48, 12.9)):
        rows.append(claim("v2", f"O1 SR improvement {label}", reported, imp(new, old), "best displayed baseline"))
    for label, new, old, reported in (("TP", 3.72, 4.18, 11.0), ("EW", 5.33, 6.32, 15.7), ("VW", 5.27, 5.24, -.6)):
        rows.append(claim("v2", f"O1 MDD gain {label}", reported, red(new, old), "best displayed baseline"))
    for name, new, old, reported in (("Ours alpha reduction", .72, .80, 10.0), ("O1 alpha reduction", .69, .80, 13.8), ("Ours t-value reduction", 2.47, 2.55, 3.1), ("O1 t-value reduction", 2.41, 2.55, 5.5), ("Ours significant-share reduction", .55, .58, 5.2), ("O1 significant-share reduction", .55, .58, 5.2), ("Ours GRS reduction", 6.48, 6.67, 2.8), ("O1 GRS reduction", 6.32, 6.67, 5.3)):
        issue = "paper calls a lower t-value an increase" if "t-value" in name else ""
        rows.append(claim("v2", name, reported, red(new, old), "paper-named leading baseline", issue))
    for name, new, old, reported, basis in (
        ("GPT-4 vs GPT-3.5 SR", 3.03, 2.89, 4.6, "standard relative increase uses GPT-3.5 denominator"),
        ("GPT-3.5 vs SDF-GAN SR", 2.89, 2.73, 5.9, "SDF-GAN"),
        ("GPT-4 vs SDF-GAN SR", 3.03, 2.73, 11.0, "SDF-GAN"),
        ("O1-preview vs GPT-4o SR", 3.15, 3.07, 2.6, "GPT-4o"),
        ("O1-mini vs GPT-4o SR", 3.12, 3.07, 1.6, "GPT-4o"),
    ):
        rows.append(claim("v2", name, reported, imp(new, old), basis))
    rows.append(claim("v2", "GPT-3.5 alpha reduction vs SDF-GAN", 6.3, red(.75, .80), "SDF-GAN"))
    rows.append(claim("v2", "GPT-4 alpha reduction vs SDF-GAN", 8.8, red(.73, .80), "SDF-GAN"))
    return rows


def method_audit(repo: Path) -> list[dict[str, str]]:
    analysis = (repo / "analysis.py").read_text(encoding="utf-8")
    model = (repo / "model.py").read_text(encoding="utf-8")
    prompt = (repo / "prompt.py").read_text(encoding="utf-8")
    config = (repo / "config.yaml").read_text(encoding="utf-8")
    checks = [
        ("official code lineage", "paper/source", "paper-era commit contains code and metadata; current code differs only in README", "pinned"),
        ("LLM iterative refinement", "paper", "dialog loop and retrieved documents are implemented", "present_component"),
        ("vector retrieval memory", "paper", "ChromaDB/FlagEmbedding wrapper is implemented and the immutable paper-era-compatible BGE model snapshot is pinned and loads offline", "present_component_public_model_pinned"),
        ("analysis prompts", "paper", "analysis, refinement, note, and summary prompts are released", "present_component"),
        ("v1 default LLM", "GPT-3.5-Turbo-1106", "config uses gpt-3.5-turbo-1106", "match"),
        ("v2 default LLM", "GPT-4o-0806 plus O1-Preview", "config still uses gpt-3.5-turbo-1106", "different"),
        ("temperature", "0.2 for all experiments", "OpenAI calls do not pass temperature", "missing"),
        ("manual financial factors", "concatenated with LLM features", "Model.forward concatenates only report and PERMNO embeddings", "missing"),
        ("historical factor pretraining", "Hybrid pricing network pretraining", "no pretraining implementation or checkpoint is released", "missing"),
        ("macro note update", "continuously LLM-updated note", "analysis.py assigns the formatted macro_update prompt without an LLM call", "implementation_bug"),
        ("SKIP path", "same four-value process contract", "SKIP branch returns three values while caller unpacks four", "implementation_bug"),
        ("training entrypoint", "README says run model.py", "model.py defines Model but never instantiates it or calls trainloop", "missing"),
        ("evaluation mode", "deterministic held-out evaluation", "Model.eval overrides nn.Module.eval and never disables dropout/BatchNorm training mode", "implementation_bug"),
        ("best checkpoint", "load best validation model", "model.pt is periodic/latest, not the best epoch selected by validation", "implementation_bug"),
        ("seed", "config seed 42", "seed is never applied to Python, NumPy, Torch, CUDA, or DataLoader", "missing"),
        ("v1 temporal split", "9 months train, 3 months validation, 1 year test", "hard-coded cutoffs match the v1 two-year interval", "match_static"),
        ("v2 temporal split", "three-year input but 9+3+12 months described", "source has no end bound and paper-described durations total two years", "different"),
        ("news input", "filtered WSJ article bodies", "65,733 metadata keys deterministically reconstruct the date/path index; article bodies and derived Tickers/Topics/Content analyses remain absent", "metadata_index_reconstructed_article_analysis_missing"),
        ("daily returns", "CRSP and Kenneth French inputs", "daily_ret_dapm.csv and all returns are absent", "missing_external"),
        ("factor input", "Jensen et al. characteristics with imputation", "factor files and construction code are absent", "missing_external"),
        ("analysis feature input", "generated report embeddings", "daily_emb_dapm.csv is absent", "missing"),
        ("baseline replications", "five paper baselines with searched hyperparameters", "no baseline code/configs/results are released", "missing"),
        ("hyperparameter sweep", "W&B sweep over disclosed distributions", "no sweep configuration, run IDs, or histories are released", "missing"),
        ("portfolio construction", "TP/EW/VW long-short portfolios", "no portfolio construction implementation is released", "missing"),
        ("pricing tests", "alpha/t-value/significant share/GRS", "no anomaly-portfolio evaluation implementation is released", "missing"),
        ("published outputs", "tables and figures", "no checkpoints, prediction arrays, portfolio returns, or result tables are released", "missing"),
        ("universe", "market-wide assets", "dsize is hard-coded to 12000 without released mapping validation", "under_specified"),
        ("dependency lock", "reconstructable environment", "requirements are unpinned and request package 'yaml' rather than PyYAML", "missing"),
    ]
    static_required = [
        ("macro=P.macro_update.format", analysis), ("return emb,texts,messages", analysis),
        ("self.p_embs(pnos)", model), ("def eval(self, test=True)", model),
        ("wandb.login", model), ("macro_update='''", prompt), ("seed: 42", config),
    ]
    for needle, haystack in static_required:
        if needle not in haystack:
            raise ValueError(f"source signature changed: {needle}")
    return [
        {"dimension": a, "paper_requirement": b, "released_evidence": c, "assessment": d, "end_to_end_credit": "no"}
        for a, b, c, d in checks
    ]


def consistency_audit() -> list[dict[str, str]]:
    issues = [
        ("v2", "duration", "main experiment says three years (2021-09-29 to 2024-09-29), while agent discussion still says two years"),
        ("v2", "split arithmetic", "9 months + 3 months + last 1 year accounts for two years, not the claimed three-year input"),
        ("v2", "released metadata coverage", "metadata ends 2023-11-30, ten months before the claimed v2 endpoint, and contains no article bodies"),
        ("v2", "decile test period", "byte-identical v1/v2 decile raster shows 2022-10 through 2023-09 rather than a new final v2 year"),
        ("v2", "figure provenance", "15/16 raster assets are byte-identical to v1 despite revised data, default model, baselines, and nearly all table cells"),
        ("v2", "implementation lineage", "official current code is unchanged from the paper-era code except README and still defaults to GPT-3.5"),
        ("v2", "Ours TP MDD comparator", "paper reports 4.3% against IPCA; displayed IPCA values imply 9.5%, while 4.3% uses CA"),
        ("v2", "Ours VW MDD comparator", "paper names CA as top baseline, but SDF-GAN has the lower displayed MDD and yields the stated 2.3%"),
        ("v2", "O1 SR percentages", "displayed best-baseline comparisons imply 11.7%, 14.1%, and 16.9%, not 9.1%, 14.1%, and 12.9%"),
        ("v2", "ablation prose", "average-alpha sentence lists three percentages for two components and is not grammatically attributable"),
        ("v2", "foundation-model percentage", "standard GPT-3.5-denominator calculation gives 4.8%, not the reported 4.6%"),
        ("v1", "GPT-4 TP MDD sign", "GPT-4 MDD 3.82 is worse than best baseline 3.77, but prose calls +1.3% a gain"),
        ("both", "t-value direction", "tables mark lower as better, while prose calls reductions increases"),
        ("both", "code-and-data claim", "repository releases metadata only, not article bodies, returns, factors, report embeddings, or native outputs"),
        ("both", "macro note algorithm", "paper describes an LLM-updated note but code stores an ever-growing unexecuted update prompt"),
        ("both", "manual-factor model", "paper's central hybrid factor input is absent from Model.forward"),
    ]
    return [{"version": version, "issue": issue, "evidence": evidence, "result_credit": "none"} for version, issue, evidence in issues]


def github_evidence(directory: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    repository = json.loads((directory / "repository.json").read_text(encoding="utf-8"))
    commits = json.loads((directory / "commits.json").read_text(encoding="utf-8"))
    forks = json.loads((directory / "forks.json").read_text(encoding="utf-8"))
    if repository.get("full_name") != "chengjunyan1/AAPM" or repository.get("license", {}).get("spdx_id") != "MIT":
        raise ValueError("official GitHub metadata changed")
    if len(commits) != 9 or commits[0].get("sha") != CURRENT_HEAD:
        raise ValueError("captured commit evidence changed")
    if len(forks) != 14:
        raise ValueError("captured fork evidence changed")
    rows: list[dict[str, str]] = []
    for filename, query in (
        ("search_daily_emb.json", "filename:daily_emb_dapm.csv"),
        ("search_daily_ret.json", "filename:daily_ret_dapm.csv"),
        ("search_wsj_metadata.json", "filename:wsj_metadata.json repo:chengjunyan1/AAPM"),
        ("search_result_421.json", "\"4.21\" repo:chengjunyan1/AAPM"),
    ):
        payload = json.loads((directory / filename).read_text(encoding="utf-8"))
        rows.append({
            "query": query, "total_count": str(payload["total_count"]),
            "incomplete_results": str(payload["incomplete_results"]).lower(),
            "interpretation": "GitHub code-search snapshot; direct repository inventory remains authoritative",
            "native_result_found": "no",
        })
    facts = {
        "official_repository": repository["html_url"], "license": repository["license"]["spdx_id"],
        "default_branch": repository["default_branch"], "captured_commits": len(commits),
        "captured_forks": len(forks), "current_head": commits[0]["sha"],
    }
    return rows, facts


def _marked_json(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        if line.startswith("@@@"):
            return json.loads(line.removeprefix("@@@"))
    raise RuntimeError(f"Subprocess did not emit marked JSON:\n{stdout}")


def verify_metadata_index_probe(output: Path) -> dict[str, Any]:
    """Fail closed on the two-run metadata-index and embedding-model evidence."""
    for name, expected in METADATA_INDEX_EVIDENCE_SHA256.items():
        if sha256(output / name) != expected:
            raise RuntimeError(f"AAPM metadata-index evidence hash changed: {name}")
    driver = Path(__file__).with_name("run_aapm_metadata_index_probe.py")
    if sha256(driver) != METADATA_INDEX_DRIVER_SHA256:
        raise RuntimeError("AAPM metadata-index probe driver changed")
    payload = json.loads(
        (output / "aapm_metadata_index_probe.json").read_text(encoding="utf-8")
    )
    index = payload.get("reconstructed_index", {})
    model = payload.get("embedding_model_snapshot", {})
    runs = payload.get("runs", [])
    if (
        payload.get("source_head") != CURRENT_HEAD
        or payload.get("source_files_modified") is not False
        or index.get("rows") != METADATA_INDEX_ROWS
        or index.get("bytes") != METADATA_INDEX_BYTES
        or index.get("sha256") != METADATA_INDEX_SHA256
        or index.get("columns") != ["date", "path"]
        or index.get("first_row")
        != {"date": "2021-10-01", "path": "2021/october/1/1"}
        or index.get("last_row")
        != {"date": "2023-11-30", "path": "2023/november/30/107"}
    ):
        raise RuntimeError("AAPM reconstructed metadata index drifted")
    if (
        model.get("repository") != EMBEDDING_MODEL_REPOSITORY
        or model.get("revision") != EMBEDDING_MODEL_REVISION
        or model.get("files") != 10
        or model.get("bytes") != 1_341_561_506
        or model.get("manifest_sha256") != EMBEDDING_MODEL_MANIFEST_SHA256
        or model.get("last_modified_before_paper_source_cutoff") is not True
    ):
        raise RuntimeError("AAPM immutable embedding-model snapshot drifted")
    if len(runs) != 2 or payload.get("execution_runs") != 2:
        raise RuntimeError("AAPM metadata-index probe repeat census drifted")
    for run in runs:
        if (
            run.get("returncode") != 1
            or run.get("network_attempts") != []
            or run.get("embedding_model_constructed_offline") is not True
            or run.get("analysis_loop_started") is not True
            or run.get("first_missing_private_path")
            != "Data/library/news_analysis/2021_october_1_1.json"
            or run.get("first_observed_exception") != "KeyError: 'Tickers'"
            or run.get("missing_required_fields")
            != ["Tickers", "Topics", "Content"]
            or run.get("llm_calls_made") != 0
            or run.get("paper_result_credit") is not False
        ):
            raise RuntimeError("AAPM metadata-index analysis boundary drifted")
    if (
        payload.get("analysis_runner_completed") is not False
        or payload.get("paper_inputs_recovered") is not False
        or payload.get("paper_result_cells_reproduced") != 0
        or payload.get("paper_result_credit") is not False
    ):
        raise RuntimeError("AAPM metadata-index result-credit boundary drifted")
    return {
        "evidence": payload,
        "evidence_sha256": dict(METADATA_INDEX_EVIDENCE_SHA256),
        "driver_sha256": METADATA_INDEX_DRIVER_SHA256,
    }


def run_native(repo: Path, python: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if not python.is_file():
        raise FileNotFoundError(python)
    if sha256(repo / "requirements.txt") != REQUIREMENTS_SHA256:
        raise RuntimeError("AAPM requirements changed")
    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)
    clean_env.update(
        {
            "WANDB_MODE": "disabled",
            "WANDB_SILENT": "true",
            "ANONYMIZED_TELEMETRY": "false",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    pip_check = subprocess.run(
        [str(python), "-m", "pip", "check"], check=True,
        cwd=repo, env=clean_env, text=True, capture_output=True,
    )
    freeze = subprocess.run(
        [str(python), "-m", "pip", "freeze", "--all"], check=True,
        cwd=repo, env=clean_env, text=True, capture_output=True,
    ).stdout
    freeze_sha256 = bytes_sha256(freeze.encode())
    if freeze_sha256 != PAPER_ENV_FREEZE_SHA256:
        raise RuntimeError(
            f"AAPM environment changed: {freeze_sha256} != {PAPER_ENV_FREEZE_SHA256}"
        )

    def run(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args, cwd=repo, env=clean_env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
        )

    compile_raw = run([str(python), "-m", "compileall", "-q", "."])
    if compile_raw.returncode != 0:
        raise ValueError("released Python sources no longer compile")
    analysis_raw = run([str(python), "analysis.py", "0"], timeout=180)
    analysis_combined = analysis_raw.stdout + analysis_raw.stderr
    if (
        analysis_raw.returncode != 1
        or "Data/library/index.csv" not in analysis_combined
        or "ModuleNotFoundError" in analysis_combined
    ):
        raise RuntimeError(f"AAPM analysis boundary changed:\n{analysis_combined}")
    model_raw = run([str(python), "model.py"], timeout=180)
    if model_raw.returncode != 0:
        raise RuntimeError(f"AAPM model module no longer loads:\n{model_raw.stderr}")

    import_program = r"""
import aiohttp, httpx, importlib, importlib.metadata, json, requests
network_attempts = []
def block_httpx(self, request, *args, **kwargs):
    network_attempts.append(f'httpx:{request.method}:{request.url}')
    raise RuntimeError('network disabled during AAPM audit')
async def block_httpx_async(self, request, *args, **kwargs):
    network_attempts.append(f'httpx-async:{request.method}:{request.url}')
    raise RuntimeError('network disabled during AAPM audit')
def block_requests(self, request, *args, **kwargs):
    network_attempts.append(f'requests:{request.method}:{request.url}')
    raise RuntimeError('network disabled during AAPM audit')
async def block_aiohttp(self, method, url, *args, **kwargs):
    network_attempts.append(f'aiohttp:{method}:{url}')
    raise RuntimeError('network disabled during AAPM audit')
httpx.Client.send = block_httpx
httpx.AsyncClient.send = block_httpx_async
requests.sessions.Session.send = block_requests
aiohttp.ClientSession._request = block_aiohttp
modules = ['utils', 'prompt', 'memdb', 'model']
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
packages = {
    name: importlib.metadata.version(name)
    for name in (
        'chromadb', 'FlagEmbedding', 'numpy', 'openai', 'pandas', 'peft',
        'PyYAML', 'torch', 'transformers', 'wandb'
    )
}
print('@@@' + json.dumps({
    'selected_modules': modules,
    'imported_modules': imported,
    'failures': failures,
    'network_attempts': network_attempts,
    'resolved_packages': packages,
}, sort_keys=True))
"""
    import_outputs = []
    for _ in range(2):
        completed = run([str(python), "-c", import_program], timeout=240)
        if completed.returncode != 0:
            raise RuntimeError(f"AAPM module inventory failed:\n{completed.stderr}")
        import_outputs.append(_marked_json(completed.stdout))
    if import_outputs[0] != import_outputs[1]:
        raise RuntimeError("AAPM module imports are nondeterministic")
    imports = import_outputs[0]
    if (
        imports["imported_modules"] != ["utils", "prompt", "memdb", "model"]
        or imports["failures"]
        or imports["network_attempts"]
        or imports["resolved_packages"]["torch"] != "2.4.1+cpu"
    ):
        raise RuntimeError(f"AAPM module boundary changed: {imports}")

    memory_program = r"""
import aiohttp, httpx, json, requests, tempfile
from memdb import MemDB
network_attempts = []
def block_httpx(self, request, *args, **kwargs):
    network_attempts.append(f'httpx:{request.method}:{request.url}')
    raise RuntimeError('network disabled during AAPM memory audit')
async def block_httpx_async(self, request, *args, **kwargs):
    network_attempts.append(f'httpx-async:{request.method}:{request.url}')
    raise RuntimeError('network disabled during AAPM memory audit')
def block_requests(self, request, *args, **kwargs):
    network_attempts.append(f'requests:{request.method}:{request.url}')
    raise RuntimeError('network disabled during AAPM memory audit')
async def block_aiohttp(self, method, url, *args, **kwargs):
    network_attempts.append(f'aiohttp:{method}:{url}')
    raise RuntimeError('network disabled during AAPM memory audit')
httpx.Client.send = block_httpx
httpx.AsyncClient.send = block_httpx_async
requests.sessions.Session.send = block_requests
aiohttp.ClientSession._request = block_aiohttp
with tempfile.TemporaryDirectory() as tmp:
    config = {
        'name': 'fixture', 'dirs': {'ckpt': tmp},
        'model': {'emb_type': 'openai', 'embed': 'text-embedding-3-small'},
        'apikeys': {'openai': 'test'},
    }
    database = MemDB('fixture', config)
    database.add(
        ['alpha document', 'beta document'],
        [
            {'Type': 'News', 'Datetime': '2024-01-01'},
            {'Type': 'Excert', 'Source': 'fixture'},
        ],
        emb=[[1.0, 0.0], [0.0, 1.0]], path=['alpha', 'beta'],
    )
    exact = database.query(emb=[[1.0, 0.0]], k=2, ret_emb=True)
    padded, masks = database.query(
        emb=[[1.0, 0.0]], k=3, filter=[['alpha']], ret_emb=False, pad=True
    )
    result = {
        'count': database.collection.count(),
        'query_ids': exact['ids'],
        'query_documents': exact['documents'],
        'filtered_ids': padded['ids'],
        'masks': masks,
        'network_attempts': network_attempts,
    }
print('@@@' + json.dumps(result, sort_keys=True))
"""
    memory_outputs = []
    for _ in range(2):
        completed = run([str(python), "-c", memory_program], timeout=240)
        if completed.returncode != 0:
            raise RuntimeError(f"AAPM memory component failed:\n{completed.stderr}")
        memory_outputs.append(_marked_json(completed.stdout))
    if memory_outputs[0] != memory_outputs[1]:
        raise RuntimeError("AAPM memory component is nondeterministic")
    memory = memory_outputs[0]
    if (
        memory["count"] != 2
        or memory["query_ids"] != [["alpha", "beta"]]
        or memory["filtered_ids"] != [["beta", "", ""]]
        or memory["masks"] != [[True, False, False]]
        or memory["network_attempts"]
    ):
        raise RuntimeError(f"AAPM memory boundary changed: {memory}")

    model_program = r"""
import json, os, sys, tempfile
from pathlib import Path
import pandas as pd
import torch
source = Path.cwd()
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    data = root / 'Data'
    (data / 'library').mkdir(parents=True)
    (root / 'Ckpt').mkdir()
    (root / 'config.yaml').write_text('''name: fixture
dirs:
  root: ./
  data: ./Data
  ckpt: ./Ckpt
apikeys:
  wandb: YOUR_KEY
model:
  dsize: 2
  d_emb: 4
  d_model: 2
  dropout: 0.0
  lr: 0.001
  batchsize: 2
  epochs: 1
  earlystop: 1
''')
    dates = [
        '2022-06-29', '2022-06-30', '2022-07-01',
        '2022-09-30', '2022-10-01', '2022-10-02',
    ]
    pd.DataFrame({
        'date': dates,
        'embedding': ['[1.0, 0.0, 0.0, 0.0]'] * len(dates),
    }).to_csv(data / 'daily_emb_dapm.csv', index=False)
    pd.DataFrame([
        {'date': date, 'PERMNO': permno, 'RET': 0.01 * (index + 1)}
        for index, date in enumerate(dates) for permno in (10001, 10002)
    ]).to_csv(data / 'daily_ret_dapm.csv', index=False)
    pd.DataFrame({'path': []}).to_csv(data / 'library/index.csv', index=False)
    os.chdir(root)
    sys.path.insert(0, str(source))
    import model
    original_cuda = torch.nn.Module.cuda
    torch.nn.Module.cuda = lambda self, *args, **kwargs: self
    try:
        torch.manual_seed(42)
        instance = model.Model(model.config, 'fixture')
        instance.train()
        output = instance(
            torch.tensor([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]),
            torch.tensor([0, 1]),
        )
        result = {
            'parameters': sum(parameter.numel() for parameter in instance.parameters()),
            'train_rows': len(instance.train_df),
            'dev_rows': len(instance.dev_df),
            'test_rows': len(instance.test_df),
            'output': output.detach().tolist(),
            'finite': bool(torch.isfinite(output).all()),
            'cuda_available': torch.cuda.is_available(),
        }
    finally:
        torch.nn.Module.cuda = original_cuda
print('@@@' + json.dumps(result, sort_keys=True))
"""
    model_outputs = []
    for _ in range(2):
        completed = run([str(python), "-c", model_program], timeout=240)
        if completed.returncode != 0:
            raise RuntimeError(f"AAPM model component failed:\n{completed.stderr}")
        model_outputs.append(_marked_json(completed.stdout))
    if model_outputs[0] != model_outputs[1]:
        raise RuntimeError("AAPM model forward component is nondeterministic")
    model = model_outputs[0]
    if (
        model["parameters"] != 49
        or model["train_rows"] != 4
        or model["dev_rows"] != 4
        or model["test_rows"] != 4
        or not model["finite"]
        or model["cuda_available"]
    ):
        raise RuntimeError(f"AAPM model component boundary changed: {model}")

    environment = {
        "dependency_environment_reproduced": True,
        "exact_historical_dependency_versions_recovered": False,
        "dependency_release_cutoff_utc": PAPER_ERA_COMMIT_UTC,
        "requirements_sha256": REQUIREMENTS_SHA256,
        "requirements_yaml_name_repaired_to_pyyaml": True,
        "flagembedding_missing_peft_repaired": True,
        "python": str(python),
        "python_version": subprocess.run(
            [str(python), "--version"], check=True, env=clean_env,
            text=True, capture_output=True,
        ).stdout.strip(),
        "pip_check": pip_check.stdout.strip(),
        "dependency_freeze_sha256": freeze_sha256,
        "dependency_freeze_lines": len(freeze.splitlines()),
        "resolved_packages": imports["resolved_packages"],
        "source_tests_shipped": 0,
        "source_modules_selected": imports["selected_modules"],
        "source_modules_imported": imports["imported_modules"],
        "source_module_import_failures": imports["failures"],
        "network_attempts": imports["network_attempts"],
        "wandb_disabled": True,
        "model_hub_offline": True,
        "chroma_telemetry_disabled": True,
        "cpu_torch_substitution": True,
        "analysis_entrypoint_reached_missing_private_input": True,
        "analysis_missing_private_input": "Data/library/index.csv",
        "model_module_entrypoint_passed": True,
        "memory_component_runs": len(memory_outputs),
        "memory_component_deterministic": True,
        "memory_component": memory,
        "model_forward_component_runs": len(model_outputs),
        "model_forward_component_deterministic": True,
        "model_forward_component": model,
        "model_forward_cpu_cuda_noop_adaptation": True,
        "model_forward_audit_seed": 42,
        "paper_result_reproduction": False,
    }
    rows = [
        {
            "component": "dependency environment", "attempted": "yes",
            "command": f"{python} -m pip check", "returncode": "0", "status": "pass",
            "detail": "135-line date-bounded freeze; four source modules import twice with zero HTTP attempts",
            "end_to_end_result_credit": "no",
        },
        {
            "component": "source syntax compile", "attempted": "yes",
            "command": f"{python} -m compileall -q .", "returncode": "0", "status": "pass",
            "detail": "five released Python files compile", "end_to_end_result_credit": "no",
        },
        {
            "component": "analysis.py entrypoint", "attempted": "yes",
            "command": f"{python} analysis.py 0", "returncode": "1",
            "status": "blocked_missing_private_input",
            "detail": "dependency resolution succeeds; Data/library/index.csv is not released",
            "end_to_end_result_credit": "no",
        },
        {
            "component": "model.py entrypoint", "attempted": "yes",
            "command": f"{python} model.py", "returncode": "0", "status": "pass",
            "detail": "module definitions load with W&B disabled; no training entrypoint exists",
            "end_to_end_result_credit": "no",
        },
        {
            "component": "native Chroma memory", "attempted": "yes",
            "command": f"{python} -c <controlled memory fixture>", "returncode": "0",
            "status": "pass",
            "detail": "supplied-embedding add/query/filter/pad path passes twice without API or model calls",
            "end_to_end_result_credit": "no",
        },
        {
            "component": "native model forward", "attempted": "yes",
            "command": f"{python} -c <controlled CPU model fixture>", "returncode": "0",
            "status": "pass_with_disclosed_cpu_adaptation",
            "detail": "released report+asset embedding forward path emits finite values twice; CUDA no-op and audit seed are not paper execution",
            "end_to_end_result_credit": "no",
        },
        {
            "component": "model training", "attempted": "no", "command": "",
            "returncode": "", "status": "not_reachable_no_entrypoint_and_inputs",
            "detail": "No Model instantiation/trainloop call; daily embeddings, returns, factors, and valid W&B credentials are absent.",
            "end_to_end_result_credit": "no",
        },
        {
            "component": "portfolio and pricing evaluation", "attempted": "no",
            "command": "", "returncode": "", "status": "not_released",
            "detail": "No TP/EW/VW, alpha/t/GRS, baseline, or figure-generation code exists in the official repository.",
            "end_to_end_result_credit": "no",
        },
        {
            "component": "end-to-end paper experiment", "attempted": "no",
            "command": "", "returncode": "",
            "status": "blocked_missing_code_data_outputs_and_provenance",
            "detail": "Executing paid LLM calls cannot reconstruct missing articles, CRSP/factors, v2 model lineage, baselines, portfolios, or result arrays.",
            "end_to_end_result_credit": "no",
        },
    ]
    raw = {
        "dependency environment": environment,
        "source syntax compile": {
            "command": [str(python), "-m", "compileall", "-q", "."],
            "returncode": compile_raw.returncode,
            "stdout": compile_raw.stdout,
            "stderr": compile_raw.stderr,
        },
        "analysis.py entrypoint": {
            "command": [str(python), "analysis.py", "0"],
            "returncode": analysis_raw.returncode,
            "stdout": analysis_raw.stdout,
            "stderr": analysis_raw.stderr,
        },
        "model.py entrypoint": {
            "command": [str(python), "model.py"],
            "returncode": model_raw.returncode,
            "stdout": model_raw.stdout,
            "stderr": model_raw.stderr,
        },
        "native Chroma memory": memory,
        "native model forward": model,
        "_dependency_freeze_text": freeze,
    }
    return rows, raw


def readme(manifest: dict[str, Any]) -> str:
    return f"""# AAPM paper/source replication audit

This package audits both official arXiv versions, both source bundles, the
complete nine-commit official GitHub history, every released file, all
{manifest['released_metadata_records']:,} metadata records, {manifest['v1_table_result_cells']} v1 table cells,
{manifest['v2_table_result_cells']} v2 table cells, and 54 quantitative figure units.

## Honest verdict

- **End-to-end AAPM result cells reproduced: 0/{manifest['v2_table_result_cells']}.** No native
  checkpoint, prediction array, portfolio-return series, baseline output, or
  table-valued result is released.
- The official repository is runnable component code, not an executable paper
  replication. A 135-package environment passes dependency checks; all four
  importable source modules load twice without HTTP, native Chroma memory and
  model-forward fixtures pass twice, and `model.py` exits cleanly offline.
  `analysis.py` first reaches the unreleased `Data/library/index.csv`. The
  released metadata keys deterministically reconstruct all 65,733 date/path rows,
  and an immutable `BAAI/bge-large-en-v1.5` snapshot last modified before the
  source cutoff loads fully offline. Two copied-tree runs then enter the first
  5,000-row chunk and stop at the first absent `news_analysis` record because
  `Tickers`, `Topics`, and `Content` are unavailable. The source still has no
  training entrypoint. The article bodies,
  returns, manual factors, generated embeddings, baselines, evaluation code,
  sweep histories, and native outputs are absent.
- The central hybrid claim is not implemented in the released model:
  `Model.forward` combines report and asset embeddings but never ingests manual
  financial factors or performs the stated historical-factor pretraining.
- The v2 experiment has no demonstrated code lineage. The current code differs
  from the September 2024 paper-era tree only in `README.md`; all six later
  commits are README-only. It still defaults to
  GPT-3.5-Turbo-1106, and the released metadata ends 2023-11-30 rather than the
  claimed 2024-09-29 endpoint.
- GitHub's complete dated public-fork surface contains 14 accessible forks, 14
  branch refs, no tags, and four unique heads. Every head is either the current
  official head or an official-history ancestor already covered by the complete
  nine-commit audit. The forks add zero unique commits and zero unique blobs, so
  they cannot recover any missing training or empirical-result lineage.

## Version and display integrity

- v1 contains {manifest['v1_table_result_cells']} empirical table cells; v2 contains
  {manifest['v2_table_result_cells']} after adding the 48-cell foundation-model table. These
  are paper displays, not reproduced results.
- {manifest['common_table_cells_changed']} of {manifest['common_table_cells']} common-position table cells changed.
  Yet 15/16 source raster figures are byte-identical. The unchanged decile plot
  still spans roughly October 2022 to September 2023, not a new v2 final year.
- The v2 paper says three years of news, but its 9-month/3-month/1-year split
  accounts for two years. Several prose percentages use the wrong comparator or
  disagree with displayed values; `paper_improvement_claim_audit.csv` gives the
  arithmetic rather than silently accepting the prose.

## Released-code defects that prevent faithful execution

- The `SKIP` path returns three values while its caller unpacks four.
- The macro note is assigned a formatted instruction prompt instead of an LLM
  response.
- `Model.eval` does not switch dropout/BatchNorm to evaluation mode; the alleged
  best-checkpoint path loads the periodic/latest checkpoint; and seed 42 is
  never applied.
- The paper fixes LLM temperature at 0.2, but the released API calls do not pass
  a temperature. Requirements are unpinned and list `yaml` rather than PyYAML.
- FlagEmbedding 1.2.11 omits its required `peft` dependency. The reconstructed
  environment adds the date-bounded package and substitutes PyYAML for the
  invalid `yaml` requirement. PyTorch 2.4.1 CPU satisfies the README's >=2.0
  instruction but not its contradictory statement that 1.10.1 was tested.

## Native component boundary

- The paper-era source-date cutoff, complete freeze, and clean dependency check
  are tracked. Exact historical versions remain unknown because every author
  requirement is unpinned.
- A supplied-embedding fixture executes the released Chroma add, query, filter,
  and pad paths without loading a model or calling an API.
- A two-run source-faithful probe pins ten files / 1,341,561,506 bytes from the
  immutable BGE commit `{EMBEDDING_MODEL_REVISION}` and reconstructs the
  1,901,562-byte metadata index. The model constructs offline and `analysis.py`
  starts deterministically with zero network attempts, but the first record lacks
  its private `news_analysis` JSON and fails on `Tickers` before any LLM call.
  This advances the native entrypoint without inventing article content and earns
  no result credit.
- A controlled six-date/two-asset fixture executes the released report-plus-asset
  embedding forward method with 49 parameters and finite outputs. The audit uses
  a disclosed CUDA no-op and seed 42 on CPU; this is component conformance, not
  training or paper-result credit.
- W&B, Chroma telemetry, model hubs, and outbound HTTP are disabled. No LLM,
  embedding-model, paid-data, or credentialed call is made.

## Evidence boundary

This is a pinned, fail-closed audit and a component-level source inspection. It
does not substitute synthetic news, public price proxies, a newer LLM, or a
freshly invented evaluation pipeline for unavailable native inputs. Doing so
would create an adaptation, not a faithful replication of either paper version.
"""


def build(args: argparse.Namespace) -> dict[str, Any]:
    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)
    metadata_probe = verify_metadata_index_probe(output)
    _, v1_links = validate_pdf(args.v1_pdf, "v1")
    _, v2_links = validate_pdf(args.v2_pdf, "v2")
    v1_tex, v2_tex = validate_sources(args.v1_source_archive, args.v2_source_archive, args.v1_source, args.v2_source)
    paths = validate_repo(args.repo)
    inventory = source_inventory(args.repo, paths)
    history = source_history_inventory(args.repo)
    fork_branches, fork_heads, fork_summary = public_fork_audit(
        args.repo, args.github_evidence_dir
    )
    metadata_rows, metadata_facts = metadata_audit(args.repo)
    v1_results, v2_results = displayed_results(v1_tex, v2_tex)
    comparison = version_comparison(v1_results, v2_results)
    figures = figure_inventory(args.v1_source, args.v2_source)
    units = figure_units()
    claims = improvement_claims()
    methods = method_audit(args.repo)
    consistency = consistency_audit()
    searches, github_facts = github_evidence(args.github_evidence_dir)
    execution, execution_raw = run_native(args.repo, args.python)
    dependency_freeze = execution_raw.pop("_dependency_freeze_text")
    execution.append(
        {
            "component": "analysis.py with reconstructed metadata index",
            "attempted": "yes_twice",
            "command": "run_aapm_metadata_index_probe.py",
            "returncode": "1",
            "status": "blocked_missing_private_article_analysis",
            "detail": (
                "65,733-row index and immutable BGE model load; first record "
                "fails on missing Tickers/Topics/Content"
            ),
            "end_to_end_result_credit": "no",
        }
    )
    execution_raw["metadata index analysis probe"] = metadata_probe["evidence"]

    write_csv(output / "source_file_inventory.csv", inventory, list(inventory[0]))
    write_csv(output / "released_source_history_inventory.csv", history, list(history[0]))
    write_csv(
        output / "public_fork_branch_ref_snapshot.csv",
        fork_branches,
        list(fork_branches[0]),
    )
    write_csv(
        output / "public_fork_unique_head_inventory.csv",
        fork_heads,
        list(fork_heads[0]),
    )
    write_json(output / "public_fork_census.json", fork_summary)
    write_csv(output / "released_metadata_audit.csv", metadata_rows, list(metadata_rows[0]))
    write_csv(output / "displayed_result_conformance.csv", v1_results + v2_results, list(v1_results[0]))
    write_csv(output / "version_result_comparison.csv", comparison, list(comparison[0]))
    write_csv(output / "source_figure_inventory.csv", figures, list(figures[0]))
    write_csv(output / "figure_series_conformance.csv", units, list(units[0]))
    write_csv(output / "paper_improvement_claim_audit.csv", claims, list(claims[0]))
    write_csv(output / "method_specification_audit.csv", methods, list(methods[0]))
    write_csv(output / "paper_internal_consistency_audit.csv", consistency, list(consistency[0]))
    write_csv(output / "source_search_inventory.csv", searches, list(searches[0]))
    write_csv(output / "native_execution.csv", execution, list(execution[0]))
    write_json(output / "native_execution.json", execution_raw)
    (output / "paper_era_environment_freeze.txt").write_text(
        dependency_freeze, encoding="utf-8"
    )
    provenance = {
        "arxiv_record": ARXIV_RECORD, "v1_pdf_url": V1_PDF_URL, "v2_pdf_url": V2_PDF_URL,
        "v1_pdf_sha256": V1_PDF_SHA256, "v2_pdf_sha256": V2_PDF_SHA256,
        "v1_source_sha256": V1_SOURCE_SHA256, "v2_source_sha256": V2_SOURCE_SHA256,
        "official_repository": OFFICIAL_REPOSITORY, "paper_era_commit": PAPER_ERA_COMMIT,
        "current_head": CURRENT_HEAD, "paper_era_tree_sha256": PAPER_ERA_TREE_SHA256,
        "current_tree_sha256": CURRENT_TREE_SHA256, "repository_change_since_paper_era": ["README.md"],
        "full_public_history_commits_audited": len(history),
        "historical_paper_result_or_training_artifact_paths": sum(
            row["paper_result_or_training_artifact_paths"] for row in history
        ),
        "v1_pdf_links": v1_links, "v2_pdf_links": v2_links, "github_snapshot": github_facts,
        "public_fork_boundary": fork_summary,
        "metadata_index_probe": {
            "embedding_model_repository": EMBEDDING_MODEL_REPOSITORY,
            "embedding_model_revision": EMBEDDING_MODEL_REVISION,
            "embedding_model_manifest_sha256": EMBEDDING_MODEL_MANIFEST_SHA256,
            "reconstructed_index_sha256": METADATA_INDEX_SHA256,
            "paper_result_credit": False,
        },
    }
    write_json(output / "source_provenance.json", provenance)
    common_changed = sum(row["exact_value_match"] == "no" for row in comparison)
    manifest = {
        "paper": "AAPM / Empirical Asset Pricing with Large Language Model Agents",
        "official_pdf_pages_audited": V1_PAGES + V2_PAGES,
        "official_pdf_pages_visually_inspected": V1_PAGES + V2_PAGES,
        "source_rebuild_pages_visually_inspected": V1_PAGES + V2_PAGES,
        "tracked_source_files": len(inventory), "compiled_python_files": EXPECTED_PYTHON_FILES,
        "repository_history_commits_audited": len(history),
        "repository_history_paper_result_or_training_artifact_paths": sum(
            row["paper_result_or_training_artifact_paths"] for row in history
        ),
        "repository_history_paper_result_artifacts_found": sum(
            bool(row["paper_result_artifact_found"]) for row in history
        ),
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
        "released_metadata_records": metadata_facts["records"],
        "released_metadata_min_date": metadata_facts["min_date"], "released_metadata_max_date": metadata_facts["max_date"],
        "v1_table_result_cells": len(v1_results), "v2_table_result_cells": len(v2_results),
        "common_table_cells": len(comparison), "common_table_cells_changed": common_changed,
        "v2_foundation_model_cells": 48, "quantitative_figure_units": len(units),
        "author_output_result_cells_available": 0, "end_to_end_result_cells_reproduced": 0,
        "llm_calls_made": 0, "paid_or_credentialed_data_calls_made": 0,
        "paper_era_dependency_environment_reproduced": execution_raw[
            "dependency environment"
        ]["dependency_environment_reproduced"],
        "paper_era_exact_historical_dependency_versions_recovered": execution_raw[
            "dependency environment"
        ]["exact_historical_dependency_versions_recovered"],
        "paper_era_source_modules_imported": len(
            execution_raw["dependency environment"]["source_modules_imported"]
        ),
        "paper_era_analysis_reached_missing_private_input": execution_raw[
            "dependency environment"
        ]["analysis_entrypoint_reached_missing_private_input"],
        "reconstructed_metadata_index_rows": metadata_probe["evidence"][
            "reconstructed_index"
        ]["rows"],
        "reconstructed_metadata_index_bytes": metadata_probe["evidence"][
            "reconstructed_index"
        ]["bytes"],
        "reconstructed_metadata_index_sha256": metadata_probe["evidence"][
            "reconstructed_index"
        ]["sha256"],
        "paper_era_embedding_model_repository": EMBEDDING_MODEL_REPOSITORY,
        "paper_era_embedding_model_revision": EMBEDDING_MODEL_REVISION,
        "paper_era_embedding_model_files_pinned": metadata_probe["evidence"][
            "embedding_model_snapshot"
        ]["files"],
        "paper_era_embedding_model_bytes_pinned": metadata_probe["evidence"][
            "embedding_model_snapshot"
        ]["bytes"],
        "paper_era_embedding_model_manifest_sha256": metadata_probe["evidence"][
            "embedding_model_snapshot"
        ]["manifest_sha256"],
        "metadata_index_analysis_probe_runs": metadata_probe["evidence"][
            "execution_runs"
        ],
        "metadata_index_analysis_probe_network_attempts": 0,
        "metadata_index_analysis_first_missing_private_path": metadata_probe[
            "evidence"
        ]["runs"][0]["first_missing_private_path"],
        "metadata_index_analysis_missing_required_fields": metadata_probe["evidence"][
            "runs"
        ][0]["missing_required_fields"],
        "metadata_index_analysis_paper_result_cells_reproduced": 0,
        "metadata_index_analysis_evidence_sha256": metadata_probe["evidence_sha256"],
        "metadata_index_analysis_driver_sha256": metadata_probe["driver_sha256"],
        "paper_era_model_module_entrypoint_passed": execution_raw[
            "dependency environment"
        ]["model_module_entrypoint_passed"],
        "paper_era_memory_component_runs": execution_raw[
            "dependency environment"
        ]["memory_component_runs"],
        "paper_era_model_forward_component_runs": execution_raw[
            "dependency environment"
        ]["model_forward_component_runs"],
        "overall_fidelity": "official_papers_sources_code_and_metadata_audited_zero_of_162_v2_result_cells_reproduced",
        "paper_result_credit": "no_result_credit_component_source_audit_only",
    }
    write_json(output / "manifest.json", manifest)
    (output / "README.md").write_text(readme(manifest), encoding="utf-8")
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--v1-pdf", type=Path, default=ROOT / "literature_review/papers/57_aapm_large_language_model_agent_based_asset_pricing_models_v1.pdf")
    result.add_argument("--v2-pdf", type=Path, default=ROOT / "literature_review/papers/58_empirical_asset_pricing_with_large_language_model_agents_v2.pdf")
    result.add_argument("--v1-source-archive", type=Path, required=True)
    result.add_argument("--v2-source-archive", type=Path, required=True)
    result.add_argument("--v1-source", type=Path, required=True)
    result.add_argument("--v2-source", type=Path, required=True)
    result.add_argument("--repo", type=Path, required=True)
    result.add_argument("--github-evidence-dir", type=Path, required=True)
    result.add_argument("--python", type=Path, default=DEFAULT_PAPER_PYTHON)
    result.add_argument("--output", type=Path, default=ROOT / "paper_runs/paper_replication_audits/aapm")
    return result


def main() -> None:
    print(json.dumps(build(parser().parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
