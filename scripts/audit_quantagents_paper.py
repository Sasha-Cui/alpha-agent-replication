#!/usr/bin/env python3
"""Build a fail-closed primary-source audit for QuantAgents.

The author-linked repository is a static project site, not the released
QuantAgents trading system.  Manuscript rebuilding, author-site table matches,
pseudocode images, profile images, and meeting videos are documentation
evidence only.  They receive no native execution or paper-result credit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantagents_paper_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/quantagents"

TITLE = "QuantAgents: Towards Multi-agent Financial System via Simulated Trading"
AUTHORS = ["Xiangyu Li", "Yawen Zeng", "Xiaofen Xing", "Jin Xu", "Xiangmin Xu"]
WORK_ID = "CensusArxiv251004643"
SYSTEM_ID = "SYS-QUANT-AGENTS"
ARXIV_ID = "2510.04643"
ARXIV_RECORD = "https://arxiv.org/abs/2510.04643v1"
PROJECT_SITE = "https://quantagents.github.io/"
REPOSITORY_URL = "https://github.com/QuantAgents/quantagents.github.io"
REPOSITORY_HEAD = "a1d0d56d04d2b73a5fbc472ec9af865a29be6ef7"
REPOSITORY_HISTORY_COMMITS = (
    "1e20f5c3c1d65eaad9778cbd978950ad9e2f00e6",
    "361777a10e89df05f1eacb3d459dedd3c8a430b9",
    "c7483135265b2b88f8c9da84e500b9ecfd4d485b",
    "39ba3f6f25eb12a65e113257d60927b27ad9a44e",
    "423689e6e90b7306fe72d3b3d0b96a7bd7cd307d",
    "fa59e764a9eae50db0ab24d3f29a4174aaf619b7",
    REPOSITORY_HEAD,
)
REPOSITORY_HISTORY_PATHS_SHA256 = "aefd98d87e676627ab9ef9c2ea82dc4dbdb36d9ccee708045c96bf3daad83b8e"
PUBLIC_SOURCE_CENSUS_DATE = "2026-08-14"
OPENAI_MODEL_PAGE = "https://developers.openai.com/api/docs/models/gpt-4o"
OPENAI_SYSTEM_CARD = "https://cdn.openai.com/gpt-4o-system-card.pdf"

PINS = {
    "primary/arxiv-abs.html": "55272f13a4bdd1619f3e8c129735910864fb59dc348f68e9566c72b2f7ee4893",
    "primary/arxiv-api.xml": "8bf0d86fcc1b0a9260c031ff04dec16419b798456e9020088a1cac04c484ca09",
    "primary/arxiv.pdf": "a1cc7214ce25cab2b9cdfb6a771f1fb8606cb0fd7319bccf25d233e6c005fd73",
    "source/source.tar": "b978a8d7be609ded462b8ed778fe45d2f4f5ef4014994589a2a0d8fbdfdcabab",
    "release/a1d0d56d04d2b73a5fbc472ec9af865a29be6ef7.tar.gz": "33b11602cc4e1a326b7677f8155d580f0caf38a4a80189bcca45db1b0ded17c3",
    "release/repo.json": "f3f487f8887678cfd25f826d0fed367043cc1919a67ee247a0e1fb0ce2bd9139",
    "release/commits.json": "89cfa9ac62174bd7bc4360c6d85363cc8f4ff50587aba1cc23945cd5d143b0a7",
    "release/owner.json": "d17e539a701b79491584e09283b010d51e2f0dfb50ecd64635fdcd53c3ab1d61",
    "release/owner-repos.json": "bf175d4254963c47110e0cf0236376390e6e64c60fdfc87a0dae0bd3e9efa33d",
    "release/branches.json": "a63ac844078dc4d2b967d873870954ef06725578e149dc966a1d7e9b97abd965",
    "release/tags.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "release/search-quantagents.json": "9dca6b580c75bef459d137c1ec1b7b555144aa659560baa999164253c2e1ef0d",
    "release/search-title.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "release/search-simulated.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "build/camera.pdf": "a2c917bae2712cb48f443c4f062ba7674c4e187d5af1795f7a4e601ce96aef0a",
    "build/pass1.txt": "0dc3ba7283114d4edfee7cb0d0449e523f46ca0431fcf8419eebe8a9e38f5b1f",
    "build/pass2.txt": "19a6c4efa81663c860004bf82aa8c428983f6f94bca8fc968363b6fcc8f14014",
    "build/pass3.txt": "19a6c4efa81663c860004bf82aa8c428983f6f94bca8fc968363b6fcc8f14014",
    "discovery/openai-gpt-4o.html": "5fb406e018738389d85e56cae7634198e5024c9a6392c8fded5cc10337e95d07",
    "discovery/gpt-4o-system-card.pdf": "e2579ecb185cbc13bac39f9dbf25e1917f78e1ea5a3a5023165c6614fb5db724",
    "viz/official-contact-1-9.jpg": "7812bc6b9530578ba63c765ef124b4a7228ec2b52d46e8c5dc249a4645f43729",
    "viz/official-contact-10-18.jpg": "8364a8aa30912d09953c7e60ee281b7c4c3b0192c4f9c7503c45a1d037bde1b0",
    "viz/official-contact-19-27.jpg": "6ae78f6a830b80b0523e6401a8094c34f1ecd814948eca1315111007f13d4baa",
    "viz/rebuilt-contact-1-9.jpg": "5f6f3ee7ce5338aec3d2ed32d64b788609811457a25b38fc7862624c1d673c2a",
    "viz/rebuilt-contact-10-18.jpg": "a5507d7edb7ae96754bb9881f88258af26279ed8665d8daf334999d412422721",
    "viz/rebuilt-contact-19-27.jpg": "c4925446c0279ca0eb0e8e9e9f4e61fcf8a4d2dad52098f5e0da42dd5e5ea808",
    "viz/source-assets/source-assets-contact.jpg": "516b3f7fd982804212dbbb585adb668643769664b89b0cb2ab08cc7515b1ddf8",
    "viz/site-algorithms-profiles-contact.jpg": "8be9d21bf91fe88c2f9958d2071812ac3517970b3f857a2178be79831f93ae7f",
    "viz/videos/vis1-contact.jpg": "533bc2198aab07ce2f3bd5559a4d5a6d3ecc9432e3151dff4eda2b66c418619d",
    "viz/videos/vis2-contact.jpg": "32a5ef7371f8c1332157e1cad023453fe4f0ad5b76241df6033b06d8947632c4",
    "viz/videos/vis3-contact.jpg": "fdf3f32883de70fd4609e5366f1265782290a72d7e158eb652760c59b0c33d70",
}

METRICS = ("ARR_pct", "TR_pct", "SR", "CR", "SoR", "MDD_pct", "Vol_pct", "ENT", "ENB")
MAIN_RESULTS: list[tuple[str, str, tuple[float | None, ...]]] = [
    ("Market Index", "NDX", (9.84, 32.52, 0.64, 1.38, 13.07, 35.58, 1.52, None, None)),
    ("Classical", "MV", (11.3, 37.87, 0.72, 3.27, 22.05, 64.15, 5.79, 1.01, 1.02)),
    ("Classical", "ZMR", (4.19, 13.1, 0.63, 2.52, 18.43, 72.89, 5.82, 1.43, 1.09)),
    ("Classical", "TSM", (5.68, 18.02, 0.64, 3.11, 17.27, 58.36, 5.65, 1.03, 1.07)),
    ("RL-based", "SAC", (22.14, 82.23, 0.84, 2.99, 23.63, 40.13, 2.85, 1.49, 1.11)),
    ("RL-based", "DeepTrader", (32.06, 130.29, 1.27, 7.16, 30.31, 29.16, 2.81, 1.88, 1.19)),
    ("RL-based", "AlphaMix+", (32.51, 132.72, 1.49, 5.76, 30.66, 40.71, 2.85, 2.76, 1.36)),
    ("LLM-based", "FinGPT", (36.71, 155.52, 1.66, 6.34, 42.31, 37.99, 2.83, 1.94, 1.21)),
    ("LLM-based", "FinMem", (37.73, 161.25, 1.89, 6.16, 43.02, 40.19, 2.82, 2.25, 1.24)),
    ("LLM-based", "FinAgent", (45.31, 206.83, 2.25, 6.98, 47.66, 38.48, 2.92, 2.71, 1.38)),
    ("LLM-based", "HedgeAgents", (49.25, 230.39, 2.41, 6.53, 45.21, 23.65, 1.99, 2.68, 1.35)),
    ("Ours", "QuantAgents", (58.68, 299.55, 3.11, 11.38, 66.94, 16.86, 1.43, 2.97, 1.49)),
    ("Derived comparison", "Improvement", (19.15, 30.02, 29.05, 58.94, 40.45, 28.71, 5.92, 7.61, 7.97)),
]
ABLATION_RESULTS = [
    ("MAM", (40.89, 179.66, 1.81, 5.27, 51.23, 28.61, 1.66, 1.73, 1.22)),
    ("SDM", (43.25, 193.97, 1.93, 6.27, 53.41, 24.99, 1.63, 1.89, 1.33)),
    ("RAM", (35.53, 148.93, 1.88, 5.94, 52.01, 21.73, 1.34, 1.65, 1.19)),
    ("SDM+RAM", (48.59, 228.07, 2.79, 8.54, 58.85, 19.21, 1.38, 2.37, 1.39)),
    ("MAM+RAM", (46.42, 213.94, 2.51, 7.82, 55.21, 20.52, 1.28, 2.18, 1.35)),
    ("MAM+SDM", (52.71, 256.12, 2.86, 9.14, 61.46, 21.85, 1.33, 2.55, 1.43)),
    ("MAM+SDM+RAM", (58.68, 299.55, 3.11, 11.38, 66.94, 16.86, 1.23, 2.97, 1.49)),
]
LLM_RESULTS = [
    ("ChatGLM3-6B", (37.32, 158.99, 2.14, 6.89, 45.98, 28.56, 1.62, 2.41, 1.22)),
    ("Llama-2-13b-chat", (40.38, 176.66, 2.35, 8.08, 50.77, 24.15, 1.51, 2.53, 1.26)),
    ("Qwen2-72B-Instruct", (44.13, 199.41, 2.23, 8.59, 49.22, 24.52, 1.77, 2.66, 1.33)),
    ("GPT-4-1106-preview", (53.77, 263.63, 2.71, 8.76, 60.11, 23.79, 1.61, 2.79, 1.38)),
    ("Claude 3.5 Sonnet", (57.95, 294.07, 2.67, 10.87, 53.74, 22.33, 1.76, 2.86, 1.47)),
    ("GPT-4o-2024-05-13", (58.68, 299.55, 3.11, 11.38, 66.94, 16.86, 1.43, 2.97, 1.49)),
]
LIVE_RESULTS = [
    ("A-stocks", (111.87, 2.02, 61.23)),
    ("HK-stocks", (97.69, 1.76, 59.71)),
]

FIGURE_ASSET_SHA256 = {
    "1.pdf": "d6c9b3feb92eb08df09bd3701a773cb3849497c6748ee32b970b398254dd7c9f",
    "2.pdf": "1bc5fae935ba3539f61f9c5719935fa9b8b9bd1e67cc44a0f5746226ca57a85a",
    "3.pdf": "125503484b975a7eb6d64ab3514ba063976c724a1e10c7225f258ff8267044af",
    "4.pdf": "c81e132cc1df600826abac1d00493904dba95d93a1f414a52d6acdba9a943aac",
    "5.pdf": "b5ae2652a3f13bbd6064bc8acf0f37d6a6d624f7eb88f2f10e369b86518d627e",
    "6.pdf": "0bb82b01dfd504c5150117a44543c8b46a3887e94b9235f5af6ad6a6452d23c9",
    "7.pdf": "b0fa23d5de19ca3259dbeb615d5846b49a274b5726bf20eee6c6b4b1caf29ad4",
    "8.pdf": "02fb0ef1bcbf1004b8adb7dafabab164a59f1474fd30efe493f0be098f7408c8",
    "9.pdf": "7f5c83a6bc36682d4a2bf21610aa4ce504a89decfc9023aa0434243098a8075b",
    "10.pdf": "40e5833a89c8ad9400b9cbc6a296588ad0daf6cc7a413d040d0cc259ded057fe",
}
VIDEO_SHA256 = {
    "vis1.mp4": "1bce0184da448e10d83f5c8dc78b6dcaee23f2519b01c6f7838c78d1d13fa6cd",
    "vis2.mp4": "2af66b37f447361264c403994ee9eb5dff56bf6571fbd304ed119a3b6c8c57d7",
    "vis3.mp4": "cc7c4eb44ae9967a8c98fa4d681951f7c3c6c72924783c49a08ffd449a7ab5fe",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fields: Sequence[str] | None = None) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty audit artifact: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fields or values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def validate_tar(path: Path, expected_files: int, expected_bytes: int) -> list[tarfile.TarInfo]:
    with tarfile.open(path, "r:*") as archive:
        files = [member for member in archive.getmembers() if member.isfile()]
    for member in files:
        pure = PurePosixPath(member.name)
        if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
            raise ValueError(f"unsafe archive member: {member.name}")
    if (len(files), sum(item.size for item in files)) != (expected_files, expected_bytes):
        raise ValueError(f"archive inventory changed for {path.name}")
    return files


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        if sha256(path) != expected:
            raise ValueError(f"pin mismatch for {relative}")
    source_files = validate_tar(scratch / "source/source.tar", 16, 1_812_381)
    release_files = validate_tar(
        scratch / f"release/{REPOSITORY_HEAD}.tar.gz", 41, 88_003_221
    )
    for name, expected in FIGURE_ASSET_SHA256.items():
        if sha256(scratch / "source/src" / name) != expected:
            raise ValueError(f"source figure changed: {name}")
    for name, expected in VIDEO_SHA256.items():
        if sha256(scratch / "release/tree/static/images" / name) != expected:
            raise ValueError(f"site video changed: {name}")
    official = PdfReader(scratch / "primary/arxiv.pdf")
    rebuilt = PdfReader(scratch / "build/camera.pdf")
    if (len(official.pages), len(rebuilt.pages)) != (27, 27):
        raise ValueError("official/rebuilt page count changed")
    text = " ".join(" ".join((page.extract_text() or "").split()) for page in official.pages)
    for marker in (TITLE, "GPT-4o-2024-05-13", "299.55", "111.87", "HK-stocks"):
        if marker not in text:
            raise ValueError(f"paper marker missing: {marker}")
    return {"source_files": source_files, "release_files": release_files}


def repository_history_audit(
    scratch: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Exhaust the complete official history and the zero-fork public surface."""
    repo = scratch / "release/repository"
    if git(repo, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise ValueError("QuantAgents history checkout is shallow")
    if git(repo, "rev-parse", "HEAD").strip() != REPOSITORY_HEAD:
        raise ValueError("QuantAgents history checkout head changed")
    origin = git(repo, "remote", "get-url", "origin").strip().removesuffix(".git")
    if origin != REPOSITORY_URL:
        raise ValueError(f"QuantAgents history origin changed: {origin}")
    commits = git(repo, "rev-list", "--reverse", "HEAD").splitlines()
    if commits != list(REPOSITORY_HISTORY_COMMITS):
        raise ValueError(f"QuantAgents official history changed: {commits}")
    api_commits = json.loads((scratch / "release/commits.json").read_text())
    if [row["sha"] for row in api_commits] != list(reversed(REPOSITORY_HISTORY_COMMITS)):
        raise ValueError("QuantAgents pinned GitHub commit snapshot changed")
    branches = json.loads((scratch / "release/branches.json").read_text())
    if [(row["name"], row["commit"]["sha"]) for row in branches] != [
        ("main", REPOSITORY_HEAD)
    ]:
        raise ValueError("QuantAgents public branch surface changed")
    if json.loads((scratch / "release/tags.json").read_text()):
        raise ValueError("QuantAgents public tag surface changed")
    repository = json.loads((scratch / "release/repo.json").read_text())
    if (
        repository["default_branch"] != "main"
        or repository["forks_count"] != 0
        or repository["network_count"] != 0
    ):
        raise ValueError("QuantAgents public fork surface changed")
    unreachable = git(
        repo, "fsck", "--full", "--no-reflogs", "--unreachable", "--no-progress"
    ).strip()
    if unreachable:
        raise ValueError(f"QuantAgents has unreviewed unreachable objects: {unreachable}")

    all_paths = sorted(
        set(
            git(
                repo,
                "-c",
                "core.quotePath=false",
                "log",
                "HEAD",
                "--name-only",
                "--pretty=format:",
            ).splitlines()
        )
        - {""}
    )
    current_paths = sorted(git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    digest = sha256_bytes(("\n".join(all_paths) + "\n").encode())
    if (
        len(all_paths) != 41
        or all_paths != current_paths
        or digest != REPOSITORY_HISTORY_PATHS_SHA256
    ):
        raise ValueError("QuantAgents historical path surface changed")

    rows: list[dict[str, Any]] = []
    previous_paths: set[str] = set()
    for commit in commits:
        authored_at, subject = git(
            repo, "show", "-s", "--format=%aI%x00%s", commit
        ).rstrip("\n").split("\x00", 1)
        paths = set(git(repo, "ls-tree", "-r", "--name-only", commit).splitlines())
        added = paths - previous_paths
        removed = previous_paths - paths
        python_paths = [path for path in paths if path.endswith(".py")]
        manifest_paths = [
            path
            for path in paths
            if Path(path).name
            in {"pyproject.toml", "requirements.txt", "environment.yml", "package.json"}
        ]
        rows.append({
            "commit": commit,
            "authored_at": authored_at,
            "subject": subject,
            "tracked_paths": len(paths),
            "paths_added_since_parent": len(added),
            "paths_removed_since_parent": len(removed),
            "python_paths": len(python_paths),
            "package_or_environment_manifests": len(manifest_paths),
            "quantagents_trading_system_source_found": False,
            "quantagents_raw_result_array_found": False,
            "paper_result_credit": False,
        })
        previous_paths = paths
    if any(
        row["paths_removed_since_parent"]
        or row["python_paths"]
        or row["package_or_environment_manifests"]
        for row in rows
    ):
        raise ValueError("QuantAgents append-only static-site boundary changed")

    summary = {
        "census_date": PUBLIC_SOURCE_CENSUS_DATE,
        "official_commits_reviewed": len(commits),
        "official_branches_reviewed": len(branches),
        "official_tags": 0,
        "github_reported_public_forks": repository["forks_count"],
        "accessible_public_forks": 0,
        "unreachable_objects": 0,
        "historical_unique_paths_reviewed": len(all_paths),
        "history_only_or_deleted_paths": len(set(all_paths) - set(current_paths)),
        "append_only_history": True,
        "python_paths_in_any_revision": 0,
        "package_or_environment_manifests_in_any_revision": 0,
        "quantagents_trading_system_source_found": False,
        "quantagents_raw_result_arrays_found": 0,
        "paper_result_credit": False,
        "interpretation": (
            "The complete seven-commit history is append-only and its 41-path union "
            "exactly equals the current static-site tree; no deleted implementation or "
            "raw result payload exists in public history, and GitHub reports zero forks."
        ),
    }
    return rows, summary


def _strip_html(value: str) -> str:
    plain = html.unescape(re.sub(r"<[^>]+>", " ", value))
    for token in ("🥇", "🥈", "🥉", "👑️", "🎮", "🛠", "🛠️"):
        plain = plain.replace(token, "")
    return " ".join(plain.split())


def parse_site_leaderboard(index: str) -> dict[str, tuple[float, ...]]:
    match = re.search(r'<table class="js-sort-table" id="results">(.*?)</table>', index, re.S)
    if not match:
        raise ValueError("author-site leaderboard not found")
    # The released HTML omits the closing </tr> after AlphaMix+, so use the
    # fixed 13-column cell grid instead of trusting malformed row boundaries.
    cells = [_strip_html(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", match.group(1), re.S)]
    if len(cells) != 13 * 11:
        raise ValueError(f"unexpected site leaderboard cell count: {len(cells)}")
    parsed: dict[str, tuple[float, ...]] = {}
    for offset in range(13, len(cells), 13):
        row = cells[offset:offset + 13]
        parsed[row[1]] = tuple(float(value) for value in row[4:13])
    if len(parsed) != 10:
        raise ValueError(f"expected 10 site rows, got {len(parsed)}")
    return parsed


def performance_rows(site_values: Mapping[str, tuple[float, ...]]) -> list[dict[str, Any]]:
    main = {model: values for _, model, values in MAIN_RESULTS}
    for model, values in site_values.items():
        expected = main.get(model)
        if expected is None or any(value is None for value in expected):
            raise ValueError(f"unexpected site model: {model}")
        if tuple(float(value) for value in expected) != values:
            raise ValueError(f"site/paper value mismatch for {model}")
    rows: list[dict[str, Any]] = []

    def append(table: str, category: str, variant: str, metrics: Sequence[str], values: Sequence[float | None], own: bool) -> None:
        for metric, value in zip(metrics, values):
            if value is None:
                continue
            corroborated = table == "main" and variant in site_values
            rows.append({
                "table": table,
                "category": category,
                "variant": variant,
                "metric": metric,
                "paper_value": value,
                "quantagents_system_output": own,
                "arxiv_source_verified": True,
                "author_site_corroborated": corroborated,
                "native_reproduced_value": "",
                "paper_result_credit": False,
                "status": "author_site_duplicate_zero_credit" if corroborated else "paper_value_only_zero_credit",
                "note": "No released native system, frozen inputs, action/order path, or metric-generation lineage.",
            })

    for category, variant, values in MAIN_RESULTS:
        append("main", category, variant, METRICS, values, variant == "QuantAgents")
    for variant, values in ABLATION_RESULTS:
        append("meeting_ablation", "QuantAgents variant", variant, METRICS, values, True)
    for variant, values in LLM_RESULTS:
        append("llm_backbone", "QuantAgents backbone", variant, METRICS, values, True)
    for variant, values in LIVE_RESULTS:
        append("live_trading", "QuantAgents live", variant, ("TR_pct", "SR", "win_rate_pct"), values, True)
    if len(rows) != 238:
        raise ValueError(f"expected 238 displayed numeric table cells, got {len(rows)}")
    return rows


def source_inventory(source_files: Sequence[tarfile.TarInfo], source_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for member in sorted(source_files, key=lambda value: value.name):
        path = source_dir / member.name
        if not path.is_file() or path.stat().st_size != member.size:
            raise ValueError(f"source extraction mismatch: {member.name}")
        role = (
            "primary_manuscript_source" if member.name == "camera.tex" else
            "published_figure" if re.fullmatch(r"(?:[1-9]|10)\.pdf", member.name) else
            "bibliography_or_typesetting_support"
        )
        rows.append({
            "path": member.name,
            "bytes": member.size,
            "sha256": sha256(path),
            "role": role,
            "is_executable_system_source": False,
            "replication_credit": False,
        })
    return rows


def figure_rows() -> list[dict[str, Any]]:
    specs = (
        ("Figure 1", "1.pdf", 1, 1, "PRUDEX radar comparison"),
        ("Figure 2", "2.pdf", 1, 0, "system workflow diagram"),
        ("Figure 3", "3.pdf", 1, 0, "simulated/real trading diagram"),
        ("Figure 4", "4.pdf", 1, 1, "main cumulative-return chart"),
        ("Figure 5", "5.pdf", 6, 6, "six LLM-backbone radar charts"),
        ("Figure 6", "6.pdf", 2, 2, "market report and strategy-meeting examples"),
        ("Figure 7", "7.pdf", 1, 1, "A/H-share live cumulative returns"),
        ("Figure 8", "8.pdf", 1, 1, "meeting-ablation cumulative returns"),
        ("Figure 9", "9.pdf", 1, 1, "LLM-backbone cumulative returns"),
        ("Figure 10", "10.pdf", 1, 1, "AAPL cumulative returns"),
    )
    return [{
        "figure": figure,
        "source_asset": asset,
        "panels": panels,
        "empirical_panels": empirical,
        "description": description,
        "rendered_author_asset_recovered": True,
        "underlying_numeric_array_released": False,
        "native_figure_regenerated": False,
        "paper_result_credit": False,
    } for figure, asset, panels, empirical, description in specs]


def prompt_rows() -> list[dict[str, Any]]:
    specs = (
        ("simplified_agent_decision", "Section 3.3", "Dave/profile-prices-news-tools-example JSON template"),
        ("market_analysis", "Appendix B", "Emily/current-prices/recent-news/tool-results JSON template"),
        ("strategy_development", "Appendix B", "Bob/strategy-parameters/simulation-data/performance-metrics JSON template"),
        ("risk_management", "Appendix B", "Dave/risk-indicators/events JSON template"),
        ("investment_decision", "Appendix B", "Otto/opportunities/market-data JSON template"),
        ("phi_D_action_prompt", "Equation 2", "symbol only; exact production prompt absent"),
        ("phi_R_report_prompt", "Section 3.4.1", "symbol only; exact production prompt absent"),
        ("response_parser_D", "Equation 2", "symbol only; schema/parser implementation absent"),
    )
    return [{
        "artifact": name,
        "location": location,
        "publication_form": form,
        "paper_template_or_symbol_recovered": True,
        "runtime_fill_released": False,
        "actual_request_released": False,
        "actual_response_released": False,
        "executable_prompt_path_released": False,
    } for name, location, form in specs]


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official_document_source", "complete", "16-file arXiv source and 27-page PDF recovered; source rebuilds to 27 pages"),
        ("project_provenance", "direct", "arXiv abstract and manuscript directly link quantagents.github.io"),
        ("project_repository", "r1_static_documentation", "41-file MIT site tree with HTML, figures, profiles, pseudocode images, and meeting videos; no system implementation"),
        ("project_repository_date", "precedes_paper", "site head is 2024-08-14; arXiv v1 is 2025-10-06"),
        ("asset_universe", "partially_specified", "NASDAQ-100 constituents named, but no point-in-time membership list or security identifiers"),
        ("market_data", "source_named_not_released", "Yahoo daily OHLCV plus 60 indicators; exact downloads, adjustments, calendars, and rows absent"),
        ("text_data", "source_named_not_released", "Alpaca news plus financial reports/macro policy; article IDs, snapshots, timing, and preprocessing absent"),
        ("temporal_split", "specified", "train 2010-01-01 through 2020-12-31; test 2021-01-01 through 2023-12-31"),
        ("foundation_model", "named_deprecated", "gpt-4o-2024-05-13 at temperature 0.7 is named but is now deprecated"),
        ("embedding_model", "named", "text-embedding-3-large and top-10 retrieval are specified"),
        ("agents", "documented_not_implemented", "four named roles and XML-like profiles are published"),
        ("tools", "labels_and_some_formulas_only", "26 labels and 60 indicator descriptions are published; callable implementations are absent"),
        ("actions", "internally_conflicting", "main paper says 10 actions; appendix gives both an 8-action and a 10-action list"),
        ("memory", "architecture_only", "three memories and top-10 retrieval are described; schema, update code, stores, and records are absent"),
        ("prompts", "example_templates_only", "five templates are examples/simplifications; exact runtime prompts, fills, schemas, and parser are absent"),
        ("meetings", "pseudocode_and_video_only", "four pseudocode screenshots and three dated localhost UI videos document behavior but provide no runnable path"),
        ("strategy_pool", "underspecified", "described as permutations of indicators and parameters without a complete grammar, parameter grid, or realized pool"),
        ("risk_alert", "formula_incomplete", "threshold 0.75 is stated, but weights, component normalizations, and risk-reward function are absent"),
        ("dual_reward_update", "nonoperational_formula", "adaptive equations are printed; n, rewards, policy parameterization, optimizer, and training code are absent"),
        ("backtest_execution", "missing", "capital, order timing, fills, costs, slippage, constraints, rebalancing, and corporate actions are not operationally specified"),
        ("baselines", "names_only", "nine baselines are named without commits, adapters, configurations, seeds, or predictions"),
        ("repeated_runs", "missing", "no random seeds, number of runs, uncertainty estimates, selection traces, or robustness protocol"),
        ("live_trading", "claims_without_lineage", "rendered curves/table exist; brokerage records, capital, positions, orders, fills, costs, and dated path are absent"),
        ("published_results", "not_regenerated", "zero of 238 numeric table cells and zero of 14 empirical panels were regenerated"),
    )
    return [{"dimension": dimension, "status": status, "detail": detail} for dimension, status, detail in specs]


def consistency_rows() -> list[dict[str, str]]:
    specs = (
        ("full_system_volatility", "hard_internal_conflict", "main and LLM tables print 1.43%; all-meetings ablation row prints 1.23%"),
        ("action_count", "hard_internal_conflict", "main text says ten actions; appendix prints a first eight-action list and then a second ten-action list"),
        ("author_site_dataset", "author_source_scope_conflict", "site says Bitcoin/FX/DJIA, 2015--2023; paper says NASDAQ-100, 2010--2023"),
        ("author_site_code_dataset_controls", "unfulfilled_release", "Paper/Code/Dataset controls are commented and point to HedgeAgents; no QuantAgents code or dataset is released"),
        ("live_period", "hard_internal_conflict", "table/prose/plot say Q3 2024--Q1 2025; appendix overview says Q1--Q3 2024"),
        ("annual_return_equation", "mathematical_specification_error", "printed ARR raises (terminal/initial minus one) to 1/h instead of subtracting one after annualizing terminal/initial"),
        ("risk_alert_weights", "underspecified", "w1--w4, component scaling, and f(Rscore, eta, tau) are absent"),
        ("strategy_pool", "underspecified", "paper promises permutations but omits the finite indicator/parameter domains and realized strategies"),
        ("prompt_disclosure", "overbroad_claim", "paper says templates are fully disclosed; appendix gives examples while phi_D, phi_R, parser, fills, and runtime requests remain absent"),
        ("result_improvements", "consistent", "nine improvement percentages follow the displayed best comparators to rounding"),
        ("paper_site_table", "partial_exact_duplicate", "90 site leaderboard cells match the paper; this is corroboration, not native regeneration"),
        ("model_temporal_boundary", "material_contamination_risk", "2021--2023 test mostly lies inside GPT-4o's official October 2023 pretraining horizon; not proof any cell is false"),
        ("site_template_residue", "excluded_unrelated_artifact", "6,141-record MathVista/VQA data and visualizer code are unrelated to QuantAgents"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def site_documentation_rows() -> list[dict[str, Any]]:
    rows = []
    for index, name in enumerate(("market_analysis_meeting", "strategy_development_meeting", "risk_alert_meeting", "otto_decision"), 1):
        rows.append({
            "artifact": f"algorithm_{index}", "name": name,
            "format": "rendered pseudocode PNG", "runnable": False,
            "raw_trace": False, "system_source_credit": False,
        })
    for index, name in enumerate(("Bob", "Dave", "Emily", "Otto"), 1):
        rows.append({
            "artifact": f"agent{index}.png", "name": f"{name} profile",
            "format": "XML-like profile screenshot", "runnable": False,
            "raw_trace": False, "system_source_credit": False,
        })
    videos = (
        ("vis1.mp4", "market_analysis_meeting", "2021-07-02", 91.788481, 2752),
        ("vis2.mp4", "strategy_development_meeting", "2022-09-30", 92.090340, 2761),
        ("vis3.mp4", "risk_alert_meeting", "2023-10-26", 84.288435, 2527),
    )
    for filename, name, shown_date, duration, frames in videos:
        rows.append({
            "artifact": filename, "name": name, "format": "1728x1080 H.264 UI recording",
            "shown_date": shown_date, "duration_seconds": duration, "video_frames": frames,
            "runnable": False, "raw_trace": False, "system_source_credit": False,
        })
    return rows


def artifact_access_rows() -> list[dict[str, Any]]:
    return [
        {"artifact": "official arXiv v1 PDF/source", "url": ARXIV_RECORD, "status": "recovered", "tier": "primary paper source", "system_source_credit": False},
        {"artifact": "paper-linked project site", "url": PROJECT_SITE, "status": "recovered and revision-pinned", "tier": "R1 author documentation", "system_source_credit": False},
        {"artifact": "project repository", "url": REPOSITORY_URL, "status": "complete seven-commit history; 41 static-site files; MIT; zero public forks", "tier": "R1 author documentation", "system_source_credit": False},
        {"artifact": "QuantAgents code", "url": "", "status": "not released; no matching exact-title repository found", "tier": "missing", "system_source_credit": False},
        {"artifact": "QuantAgents dataset", "url": "", "status": "not released; site control is commented and misroutes to HedgeAgents", "tier": "missing", "system_source_credit": False},
        {"artifact": "MathVista template data", "url": "", "status": "6,141 unrelated VQA records explicitly excluded", "tier": "unrelated template residue", "system_source_credit": False},
        {"artifact": "GPT-4o system card/model page", "url": OPENAI_SYSTEM_CARD, "status": "recovered; October 2023 horizon and snapshot deprecation recorded", "tier": "official dependency provenance", "system_source_credit": False},
    ]


def readme() -> str:
    return f"""# QuantAgents paper-level replication audit

Overall verdict: **not reproduced**. This package pins arXiv `{ARXIV_ID}v1`,
the complete 16-file manuscript bundle, the authors' first-party project site
repository at `{REPOSITORY_HEAD[:8]}`, official GPT-4o provenance, and bounded
repository searches. The 27-page source rebuild and every official/rebuilt page
passed visual review. Document recovery is not system execution.

## What is genuinely recovered

- The manuscript specifies four agents, 26 named tools, three memory types,
  ten claimed actions, three meetings, five example/simplified prompt templates,
  top-10 `text-embedding-3-large` retrieval, `gpt-4o-2024-05-13` at temperature
  0.7, a 2010--2020/2021--2023 temporal split, formulas, metrics, profiles, and
  qualitative strategy-pool/risk workflows.
- The 41-file MIT project repository contains the exact title, 90 exact
  duplicates of main-table cells, four rendered meeting algorithms, four
  XML-like profile images, 15 QuantAgents images, and three dated 1080p meeting
  demonstrations. These are valuable R1 author documentation, not executable
  QuantAgents source or raw runtime traces.
- All **238** displayed numeric table cells are inventoried: 115 in the main
  table, 63 in the meeting ablation, 54 in the LLM table, and 6 in live trading.
  The ten published figures contain 14 empirical panels. **Zero of 238 cells and
  zero of 14 empirical panels are natively regenerated.**

## Release and template boundary

The repository has no Python/system source, package manifest, environment,
runner, tests, configuration, market/news data, prompts with runtime fills,
LLM requests/responses, memory store, strategy pool, action log, orders, fills,
portfolio path, or result arrays. Its Paper/Code/Dataset buttons are commented
and point to HedgeAgents. The bundled 6,141-record MathVista/VQA visualizer is
unrelated template residue and receives no QuantAgents evidence credit.

The complete official Git history is also exhausted as of
{PUBLIC_SOURCE_CENSUS_DATE}: seven commits, one branch, zero tags, and 41 unique
paths. The history is append-only, so its full path union exactly equals the
current static-site tree; there are no deleted or history-only payloads. Every
revision predates the paper by more than a year, and GitHub reports zero public
forks. Thus neither official history nor a fork surface conceals a runnable
QuantAgents implementation or raw result array.

## Material specification conflicts

- Full-system volatility is 1.43% in the main and LLM tables but 1.23% in the
  all-meetings ablation row.
- The appendix prints both an eight-action list and a ten-action list.
- The site describes an older Bitcoin/FX/DJIA 2015--2023 dataset while the paper
  specifies NASDAQ-100 constituents for 2010--2023.
- Live-trading table/prose/plot say Q3 2024--Q1 2025, but the appendix overview
  says Q1--Q3 2024.
- The printed ARR equation annualizes `(terminal/initial - 1)` rather than the
  terminal/initial ratio, and key execution, risk-weight, prompt/parser, strategy
  pool, baseline, seed, and repeated-run details remain absent.

## Temporal-validity boundary

The reported historical test spans 2021--2023, while OpenAI's official system
card says GPT-4o was pretrained using data through October 2023. Most of the
test window is therefore inside the model's knowledge horizon. This is a
material contamination risk, **not** proof that any reported result is false.
The exact `gpt-4o-2024-05-13` snapshot is now deprecated; substituting another
model would be an adaptation rather than exact replication.

A defensible full reproduction requires the actual implementation, point-in-time
NASDAQ-100 membership and frozen Yahoo/Alpaca inputs, complete prompts/tools,
strategy pool, model traces, seeds, execution/cost rules, orders/fills, dated
portfolio paths, baseline lineage, and result-generation code. The local M0
narrative portfolio remains a proxy and receives no QuantAgents mechanism or
result credit. `--strict` intentionally exits nonzero while these boundaries
remain.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    inventory = validate_inputs(scratch)
    source_dir = scratch / "source/src"
    site_dir = scratch / "release/tree"
    tex = (source_dir / "camera.tex").read_text(encoding="utf-8")
    index = (site_dir / "index.html").read_text(encoding="utf-8")
    for marker in (
        "QuantAgents: Towards Multi-agent Financial System via",
        "Simulated Trading",
        PROJECT_SITE,
        "we will release all datasets and codes",
        "GPT-4o-2024-05-13",
    ):
        if marker not in tex:
            raise ValueError(f"manuscript marker missing: {marker}")
    for marker in (
        "Towards Multi-agent Financial System via Simulated Trading",
        "hedgeagents.github.io",
        "MathVista Visualizer",
        "QuantAgents 🥇",
    ):
        if marker not in index and marker != "MathVista Visualizer":
            raise ValueError(f"site marker missing: {marker}")
    explore = (site_dir / "visualizer/explore.html").read_text(encoding="utf-8")
    filters = (site_dir / "visualizer/data/filters_num.json").read_text(encoding="utf-8")
    if "MathVista Visualizer" not in explore or "All (6141)" not in filters:
        raise ValueError("unrelated MathVista residue boundary changed")
    if "<span>Code</span>" not in index or "https://hedgeagents.github.io/#1" not in index:
        raise ValueError("commented/misdirected release controls changed")
    if any((site_dir / name).exists() for name in ("pyproject.toml", "requirements.txt", "package.json", "setup.py")):
        raise ValueError("site implementation boundary changed")
    if list(site_dir.rglob("*.py")):
        raise ValueError("site unexpectedly contains Python source")
    model_page = (scratch / "discovery/openai-gpt-4o.html").read_text(encoding="utf-8")
    if "gpt-4o-2024-05-13" not in model_page or "Deprecated" not in model_page:
        raise ValueError("official model deprecation evidence changed")
    system_card = " ".join(
        " ".join((page.extract_text() or "").split())
        for page in PdfReader(scratch / "discovery/gpt-4o-system-card.pdf").pages
    )
    if "pre-trained using data up to October 2023" not in system_card:
        raise ValueError("official GPT-4o temporal-boundary evidence changed")

    site_values = parse_site_leaderboard(index)
    results = performance_rows(site_values)
    figures = figure_rows()
    methods = method_rows()
    consistency = consistency_rows()
    source_rows = source_inventory(inventory["source_files"], source_dir)
    documentation = site_documentation_rows()
    history_rows, source_surface = repository_history_audit(scratch)

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "paper_source_inventory.csv", source_rows)
    write_csv(output / "published_performance_ledger.csv", results)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "prompt_inventory.csv", prompt_rows())
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(
        output / "site_documentation_inventory.csv",
        documentation,
        ("artifact", "name", "format", "shown_date", "duration_seconds", "video_frames", "runnable", "raw_trace", "system_source_credit"),
    )
    write_csv(output / "artifact_access_audit.csv", artifact_access_rows())
    write_csv(output / "released_source_history_inventory.csv", history_rows)
    write_json(output / "public_source_surface_audit.json", source_surface)

    repository = json.loads((scratch / "release/repo.json").read_text())
    owner = json.loads((scratch / "release/owner.json").read_text())
    release_audit = {
        "url": REPOSITORY_URL,
        "head_sha": REPOSITORY_HEAD,
        "head_commit_date": "2024-08-14T16:37:52Z",
        "paper_submission_date": "2025-10-06T09:45:57Z",
        "archive_sha256": PINS[f"release/{REPOSITORY_HEAD}.tar.gz"],
        "archive_bytes": 81_460_192,
        "archive_files": len(inventory["release_files"]),
        "archive_uncompressed_bytes": sum(item.size for item in inventory["release_files"]),
        "repository_license": repository["license"]["spdx_id"],
        "license_text_file_present": (site_dir / "LICENSE").is_file(),
        "owner_type": owner["type"],
        "owner_public_repositories": owner["public_repos"],
        "branches": ["main"],
        "tags": [],
        "commit_count": 7,
        "complete_public_history_audit": source_surface,
        "python_files": 0,
        "package_or_environment_manifests": 0,
        "system_runner_files": 0,
        "author_test_files": 0,
        "quantagents_images": 15,
        "meeting_videos": 3,
        "rendered_algorithms": 4,
        "rendered_profiles": 4,
        "site_leaderboard_cells_matching_paper": 90,
        "unrelated_mathvista_vqa_records": 6_141,
        "paper_code_released": False,
        "paper_dataset_released": False,
        "paper_result_arrays_released": False,
        "native_execution_possible": False,
        "paper_result_credit": False,
    }
    write_json(output / "release_execution_audit.json", release_audit)

    source_provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "title": TITLE,
        "authors": AUTHORS,
        "arxiv_id": ARXIV_ID,
        "arxiv_version": "v1 only; submitted 2025-10-06 09:45:57 UTC",
        "paper_license": "CC BY 4.0",
        "official_pdf_sha256": PINS["primary/arxiv.pdf"],
        "official_pdf_pages": 27,
        "source_archive_sha256": PINS["source/source.tar"],
        "source_files": len(source_rows),
        "source_file_bytes": sum(int(row["bytes"]) for row in source_rows),
        "project_site": PROJECT_SITE,
        "project_repository": REPOSITORY_URL,
        "project_repository_head": REPOSITORY_HEAD,
        "project_repository_archive_sha256": release_audit["archive_sha256"],
        "attribution": "arXiv abstract and manuscript directly link the exact-title first-party project site",
        "bounded_repository_search": {
            "exact_title_matches": 0,
            "exact_title_plus_simulated_trading_matches": 0,
            "broad_quantagents_metadata_matches": 246,
            "interpretation": "broad matches are unrelated names, aggregators, or third-party adaptations; no author system implementation recovered",
            "negative_search_limit": "repository metadata/readme search cannot rule out private, deleted, aliased, or unindexed releases",
        },
        "visual_qa": {
            "official_pages_inspected": 27,
            "rebuilt_pages_inspected": 27,
            "source_figure_assets_inspected": 10,
            "site_algorithm_profile_images_inspected": 8,
            "site_video_contact_sheets_inspected": 3,
            "unreadable_clipped_overlapping_blank_or_missing_research_content": 0,
            "contact_sheet_sha256": {
                key.removeprefix("viz/").removesuffix(".jpg"): value
                for key, value in PINS.items() if key.startswith("viz/")
            },
        },
        "model_dependency": {
            "snapshot": "gpt-4o-2024-05-13",
            "current_status": "deprecated",
            "official_pretraining_horizon": "October 2023",
            "official_system_card_sha256": PINS["discovery/gpt-4o-system-card.pdf"],
            "interpretation": "material contamination risk for most of the 2021--2023 test, not proof that a reported cell is false",
        },
        "release_boundary": {
            "author_documentation_recovered": True,
            "complete_official_history_reviewed": True,
            "public_fork_surface_reviewed": True,
            "trading_system_source_recovered": False,
            "complete_research_data_recovered": False,
            "published_result_lineage_recovered": False,
        },
    }
    write_json(output / "source_provenance.json", source_provenance)

    native = {
        "manuscript_source_rebuilt": True,
        "manuscript_rebuild_is_system_execution": False,
        "author_site_static_assets_validated": True,
        "author_site_meeting_videos_reviewed": 3,
        "complete_official_repository_history_reviewed": True,
        "public_forks_reported_and_reviewed": 0,
        "public_quantagents_system_source_found": False,
        "quantagents_pipeline_executed": False,
        "llm_calls_made": 0,
        "original_market_rows_loaded": 0,
        "original_news_rows_loaded": 0,
        "native_memory_rows_loaded": 0,
        "native_agent_actions_loaded": 0,
        "native_orders_or_fills_loaded": 0,
        "native_portfolio_trajectories_loaded": 0,
        "published_table_cells_faithfully_regenerated": 0,
        "published_empirical_panels_faithfully_regenerated": 0,
        "strict_boundary": "document builds, author-site duplicates, pseudocode, profiles, videos, and plot digitization receive zero paper-result credit",
    }
    write_json(output / "native_execution.json", native)
    (output / "README.md").write_text(readme(), encoding="utf-8")

    manifest: dict[str, Any] = {
        "audit": "QuantAgents primary-source, public-artifact, internal-consistency, and result-fidelity audit",
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "overall_status": "not_reproduced_no_public_system_source_frozen_inputs_runtime_traces_or_portfolio_path",
        "official_versions_audited": ["v1"],
        "official_pdf_and_source_recovered": True,
        "official_pdf_pages": 27,
        "document_rebuild_completed": True,
        "rebuilt_pdf_pages": 27,
        "official_pages_visually_checked": 27,
        "rebuilt_pages_visually_checked": 27,
        "arxiv_source_files": len(source_rows),
        "published_numeric_table_cells": len(results),
        "quantagents_own_numeric_table_cells": sum(bool(row["quantagents_system_output"]) for row in results),
        "author_site_corroborated_main_table_cells": sum(bool(row["author_site_corroborated"]) for row in results),
        "published_numeric_table_cells_faithfully_regenerated": 0,
        "published_figures": len(figures),
        "published_figure_panels": sum(int(row["panels"]) for row in figures),
        "published_empirical_panels": sum(int(row["empirical_panels"]) for row in figures),
        "published_empirical_panels_faithfully_regenerated": 0,
        "project_repository_files": len(inventory["release_files"]),
        "project_repository_commits_audited": source_surface[
            "official_commits_reviewed"
        ],
        "project_repository_historical_unique_paths_audited": source_surface[
            "historical_unique_paths_reviewed"
        ],
        "project_repository_history_only_or_deleted_paths": source_surface[
            "history_only_or_deleted_paths"
        ],
        "project_repository_public_forks_audited": source_surface[
            "accessible_public_forks"
        ],
        "public_system_source_files_recovered": 0,
        "author_tests_passed": 0,
        "site_meeting_videos": 3,
        "site_rendered_algorithms": 4,
        "site_rendered_profiles": 4,
        "site_unrelated_vqa_records": 6_141,
        "prompt_templates_or_symbols_inventoried": len(prompt_rows()),
        "actual_llm_requests_recovered": 0,
        "actual_llm_responses_recovered": 0,
        "hard_or_material_consistency_findings": sum(
            row["status"] in {"hard_internal_conflict", "author_source_scope_conflict", "mathematical_specification_error", "material_contamination_risk"}
            for row in consistency
        ),
        "full_end_to_end_pipeline_reproduced": False,
        "strict_success": False,
    }
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch.resolve(), args.output.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return int(args.strict and not manifest["strict_success"])


if __name__ == "__main__":
    sys.exit(main())
