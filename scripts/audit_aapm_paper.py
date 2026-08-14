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
        ("vector retrieval memory", "paper", "ChromaDB/FlagEmbedding wrapper is implemented", "present_component"),
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
        ("news input", "filtered WSJ article bodies", "only headline/category/time/url metadata is released", "missing"),
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


def run_native(repo: Path, python: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    def run(name: str, args: list[str]) -> tuple[dict[str, str], dict[str, Any]]:
        result = subprocess.run(args, cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        combined = (result.stdout + result.stderr).strip()
        return ({
            "component": name, "attempted": "yes", "command": " ".join(args),
            "returncode": str(result.returncode), "status": "pass" if result.returncode == 0 else "blocked_before_component",
            "detail": combined[-1500:], "end_to_end_result_credit": "no",
        }, {"command": args, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    rows: list[dict[str, str]] = []
    raw: dict[str, Any] = {}
    compile_row, compile_raw = run("source syntax compile", [str(python), "-m", "compileall", "-q", "."])
    rows.append(compile_row)
    raw["source syntax compile"] = compile_raw
    analysis_row, analysis_raw = run("analysis.py entrypoint", [str(python), "analysis.py", "0"])
    rows.append(analysis_row)
    raw["analysis.py entrypoint"] = analysis_raw
    model_row, model_raw = run("model.py entrypoint", [str(python), "model.py"])
    rows.append(model_row)
    raw["model.py entrypoint"] = model_raw
    if compile_row["status"] != "pass":
        raise ValueError("released Python sources no longer compile")
    rows += [
        {"component": "model training", "attempted": "no", "command": "", "returncode": "", "status": "not_reachable_no_entrypoint_and_inputs", "detail": "No Model instantiation/trainloop call; daily embeddings, returns, factors, and valid W&B credentials are absent.", "end_to_end_result_credit": "no"},
        {"component": "portfolio and pricing evaluation", "attempted": "no", "command": "", "returncode": "", "status": "not_released", "detail": "No TP/EW/VW, alpha/t/GRS, baseline, or figure-generation code exists in the official repository.", "end_to_end_result_credit": "no"},
        {"component": "end-to-end paper experiment", "attempted": "no", "command": "", "returncode": "", "status": "blocked_missing_code_data_outputs_and_provenance", "detail": "Executing paid LLM calls cannot reconstruct missing articles, CRSP/factors, v2 model lineage, baselines, portfolios, or result arrays.", "end_to_end_result_credit": "no"},
    ]
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
- The official repository is useful component code, not an executable paper
  replication. Five Python files compile, but `analysis.py` is blocked before
  analysis and `model.py` has no training entrypoint. The article bodies,
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

## Evidence boundary

This is a pinned, fail-closed audit and a component-level source inspection. It
does not substitute synthetic news, public price proxies, a newer LLM, or a
freshly invented evaluation pipeline for unavailable native inputs. Doing so
would create an adaptation, not a faithful replication of either paper version.
"""


def build(args: argparse.Namespace) -> dict[str, Any]:
    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)
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
    result.add_argument("--python", type=Path, required=True)
    result.add_argument("--output", type=Path, default=ROOT / "paper_runs/paper_replication_audits/aapm")
    return result


def main() -> None:
    print(json.dumps(build(parser().parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
