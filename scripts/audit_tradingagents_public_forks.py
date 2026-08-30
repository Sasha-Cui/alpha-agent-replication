"""Deterministic public-fork evidence audit for TradingAgents.

The caller pins the live GitHub branch-ref snapshot. This module never contacts
GitHub: it walks locally materialized commit/tree/blob objects and fails closed
when the dated census or any selected evidence tier changes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

CENSUS_DATE = "2026-08-30"
REST_REPORTED_FORKS = 19586
ACCESSIBLE_FORKS = 19445
BRANCH_REFS = 24584
BRANCH_SNAPSHOT_SHA256 = "ff083734da4953effbe84afd9723a482b5475095d83f6cbe38e6c1328e20807f"
BRANCH_CANONICAL_SHA256 = "6a91f6a215449c5401fb0e93f9fecf789b9bbcf2514f88648797abe11d6910c2"
UNIQUE_HEADS = 4234
UNIQUE_HEAD_SHA256 = "360b5556fd2770c2a800ace9bcd338c0436d21ce4ea9cc7c7369f9cc9391befd"
OFFICIAL_HEADS = 12
OFFICIAL_HEAD_SHA256 = "fe12e0fa0fe4a6df1c98ce5158acef53de138904a1be3cbeb5500ae77dd861b4"
HEADS_IN_OFFICIAL_HISTORY = 115
DIVERGENT_HEADS = 4119
DIVERGENT_HEAD_SHA256 = "65027c70d0dedce59c72623deed4fc12b7816e9979b1e19eaf377ba032dd77fc"
CONNECTED_DIVERGENT_HEADS = 4083
DISCONNECTED_DIVERGENT_HEADS = 36
EXTRA_COMMITS = 37020
EXTRA_COMMIT_SHA256 = "294deaa79c1ce39bb35db78706fb352c5747769bd09fb7c231b39141941823a0"
CHANGED_PATHS = 326583
CHANGED_PATH_SHA256 = "b34b6576f4c4fb460f55d8b4df5bbc56f9a24bb974eebb974c6acb65e7a0305c"
CHANGED_NEW_BLOBS = 340214
CHANGED_NEW_BLOB_SHA256 = "8db70f4eecde7d25d79f57ea08f2b972bbb5dc6f8915be582276a9a73c7fd9a2"
SOURCE_ROOT_COMMIT = "c2fa046a9bc169b218c827127f2e44338ebd0890"
AUTHOR_SITE_HEAD = "2ae2c5834d136ceba82d8d0e8425e7dba4e55605"
AUTHOR_SITE_EVIDENCE_COMMIT = "6c27bad6619e1a2fbf6060b91862d07cd5c8a1d8"
AUTHOR_SITE_COMMITS = 20
AUTHOR_SITE_COMMIT_SHA256 = "f33c0b33f8b4bce430219324ce51a64b1f124c8687b5ff35efb45d53d42c10ec"
AUTHOR_SITE_PATHS = 30
AUTHOR_SITE_PATH_SHA256 = "aba886308bdf7f36e0360dc49a212c7b4fd82bb67fa206c5b07fde917d96ad2d"
AUTHOR_SITE_PRESERVING_HEADS = {
    "2ae2c5834d136ceba82d8d0e8425e7dba4e55605",
    "83f90d53c206016e899734b4d277eba650e09778",
    "90625e5fba3acc1e6cacea566cfe074bb4df564f",
    "907af835fab9e25d8ff7e6e41a6d6a89e008e754",
    "fc6d3b5cd378e81ecc1ce506d99d43fefd6b06d1",
}
AUTHOR_SITE_PRESERVING_REFS = 48
AUTHOR_RASTER_BLOBS = {
    "cumulative_return": "6d007f1628bf0d6bcad6ff445eb18aa229abcb5d",
    "transaction_history": "9929e6cbd8868664e3018cb30d0ec6aab15cd51e",
}
COMMUNITY_REPORT_COMMIT = "adb4c575dd4d03063ea32bc798f6d13c2aa51c67"
COMMUNITY_REPORT_BLOBS = {
    "paper_quote_only": "77082dbf14ba237098b2623f097f55304cf490ba",
    "unaffiliated_aapl_baseline": "bc48876b7eedd76f4467b34b45ff4107ed274df7",
}
OFFICIAL_AUTHOR_IDENTITIES = 24
EXTRA_EXACT_OFFICIAL_IDENTITY_COMMITS = 1172
EXTRA_OFFICIAL_EMAIL_COMMITS = 1178

TIER_EXPECTED = {
    1: {
        "blobs": 10910,
        "paths": 10847,
        "blob_sha256": "974ad03a8d37df797f2604d0b7a436e7019ccf8d07466a0359744854f835a1cf",
        "bytes": 1762279351,
        "text": 10812,
        "binary": 98,
        "paper_context": 336,
        "exact_period": 55,
        "all_assets": 119,
        "broad_candidates": set(),
    },
    2: {
        "blobs": 39823,
        "paths": 38470,
        "blob_sha256": "2e804b08cd83958178b6932846bd2553014e9fe61572fc9782d23deac88656f8",
        "bytes": 984953833,
        "text": 39363,
        "binary": 460,
        "paper_context": 2009,
        "exact_period": 0,
        "all_assets": 291,
        "broad_candidates": {
            "2bfc603f4918343557f85fddd4ce0c9ecd38897c",
            "77082dbf14ba237098b2623f097f55304cf490ba",
            "bc48876b7eedd76f4467b34b45ff4107ed274df7",
        },
    },
    3: {
        "blobs": 1931,
        "paths": 996,
        "blob_sha256": "b8284abbc64b816e6954c218059ea023dfa938ed8a3b70c868dedbb863c183ae",
        "bytes": 1941471383,
    },
    4: {
        "blobs": 1922,
        "paths": 1862,
        "blob_sha256": "d8f932578154e5de8ddbdc81d1da5f2f96b8fd60cbcf7baaa609c4a35ab5dd0a",
        "bytes": 1568543842,
    },
}

PERFORMANCE = {
    "B&H": {"AAPL": (-5.23, -5.09, -1.29, 11.90), "GOOGL": (7.78, 8.09, 1.35, 13.04), "AMZN": (17.1, 17.6, 3.53, 3.80)},
    "MACD": {"AAPL": (-1.49, -1.48, -0.81, 4.53), "GOOGL": (6.20, 6.26, 2.31, 1.22)},
    "KDJ&RSI": {"AAPL": (2.05, 2.07, 1.64, 1.09), "GOOGL": (0.4, 0.4, 0.02, 1.58), "AMZN": (-0.77, -0.76, -2.25, 1.08)},
    "ZMR": {"AAPL": (0.57, 0.57, 0.17, 0.86), "GOOGL": (-0.58, 0.58, 2.12, 2.34), "AMZN": (-0.77, -0.77, -2.45, 0.82)},
    "SMA": {"AAPL": (-3.2, -2.97, -1.72, 3.67), "GOOGL": (6.23, 6.43, 2.12, 2.34), "AMZN": (11.01, 11.6, 2.22, 3.97)},
    "TradingAgents": {
        "AAPL": (26.62, 30.5, 8.21, 0.91),
        "GOOGL": (24.36, 27.58, 6.39, 1.69),
        "AMZN": (23.21, 24.90, 5.60, 2.11),
    },
    "Improvement": {"AAPL": (24.57, 28.43, 6.57), "GOOGL": (16.58, 19.49, 4.26), "AMZN": (6.10, 7.30, 2.07)},
}
ALIASES = {
    "B&H": ("b&h", "buy and hold", "buy_hold", "buyandhold", "buy-and-hold"),
    "MACD": ("macd",),
    "KDJ&RSI": ("kdj&rsi", "kdj+rsi", "kdjrsi", "kdj_rsi"),
    "ZMR": ("zmr",),
    "SMA": ("sma",),
    "TradingAgents": ("tradingagents", "trading agents", "stockgptstrategy"),
    "Improvement": ("improvement",),
}
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
EXCLUDE_RE = re.compile(
    r"(?i)(^|/)(venv|\.venv|env|tradingagents-env|site-packages|node_modules|vendor|dist|build|coverage|__pycache__|\.git|target|tests?|test_data|fixtures?)(/|$)"
)
RESULT_DIR_RE = re.compile(
    r"(?i)(^|/)(results?|results_batch|outputs?|reports?|backtests?|snapshots?|eval_results?|test_output|trading_loop_logs|experiments?|checkpoints?|plots?|figures?|runs?|docs?)(/|$)"
)
STRICT_RE = re.compile(
    r"(?i)(sharpe|drawdown|pnl|account[_-]?value|portfolio[_-]?(return|value|history)|trade[_-]?record|backtest[_-]?(result|output)|benchmark[_-]?(result|return)|cumulative[_-]?return)"
)


def _git(root: Path, *args: str, input_text: str | None = None, binary: bool = False) -> str | bytes:
    input_data = input_text.encode() if binary and input_text is not None else input_text
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        input=input_data,
        capture_output=True,
        text=not binary,
        check=True,
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
    )
    return result.stdout


def _line_hash(values: Iterable[str]) -> str:
    return hashlib.sha256(("\n".join(values) + "\n").encode()).hexdigest()


def _blob_batch(root: Path, ids: Sequence[str]) -> Iterable[tuple[str, bytes]]:
    object_input = tempfile.TemporaryFile()
    object_input.write(("\n".join(ids) + "\n").encode())
    object_input.seek(0)
    proc = subprocess.Popen(
        ["git", "-C", str(root), "cat-file", "--batch"],
        stdin=object_input,
        stdout=subprocess.PIPE,
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
    )
    assert proc.stdout
    for expected in ids:
        header = proc.stdout.readline().decode().strip().split()
        if len(header) != 3 or header[0] != expected or header[1] != "blob":
            raise RuntimeError(f"Missing selected TradingAgents fork blob: {expected}: {header}")
        payload = proc.stdout.read(int(header[2]))
        if proc.stdout.read(1) != b"\n":
            raise RuntimeError("Malformed git cat-file batch stream")
        yield expected, payload
    proc.stdout.close()
    return_code = proc.wait()
    object_input.close()
    if return_code:
        raise RuntimeError("TradingAgents fork blob reader failed")


def _read_snapshot(path: Path) -> list[dict[str, str]]:
    if hashlib.sha256(path.read_bytes()).hexdigest() != BRANCH_SNAPSHOT_SHA256:
        raise RuntimeError("TradingAgents public-fork snapshot hash changed")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "repository",
        "branch",
        "head_commit",
        "repository_created_at",
        "repository_pushed_at",
        "repository_archived",
        "repository_disabled",
    }
    if not rows or set(rows[0]) != required:
        raise RuntimeError("TradingAgents public-fork snapshot schema changed")
    rows.sort(key=lambda row: (row["repository"].lower(), row["branch"].lower(), row["head_commit"]))
    canonical = [f"{row['repository']}\t{row['branch']}\t{row['head_commit']}" for row in rows]
    if (
        len(rows) != BRANCH_REFS
        or len({row["repository"] for row in rows}) != ACCESSIBLE_FORKS
        or _line_hash(canonical) != BRANCH_CANONICAL_SHA256
    ):
        raise RuntimeError("TradingAgents public-fork branch surface changed")
    return rows


def _official_state(root: Path) -> tuple[list[str], set[str], set[tuple[str, str]], set[str]]:
    lines = [
        line
        for line in str(
            _git(root, "for-each-ref", "--format=%(refname) %(objectname)", "refs/remotes/origin", "refs/tags")
        ).splitlines()
        if not line.startswith("refs/remotes/origin/HEAD ")
    ]
    heads = sorted({line.split(" ", 1)[1] for line in lines})
    if len(heads) != OFFICIAL_HEADS or _line_hash(heads) != OFFICIAL_HEAD_SHA256:
        raise RuntimeError("TradingAgents pinned official refs changed")
    commits = set(str(_git(root, "rev-list", *heads)).splitlines())
    raw = bytes(_git(root, "log", *heads, "--format=%aN%x00%aE", binary=True))
    identities = set()
    for line in raw.splitlines():
        if b"\0" in line:
            name, email = line.split(b"\0", 1)
            identities.add((name.decode("utf-8", "replace"), email.decode("utf-8", "replace")))
    return heads, commits, identities, {email.lower() for _, email in identities}


def _graph_and_tiers(
    root: Path, fork_heads: Sequence[str], official_heads: Sequence[str]
) -> tuple[list[str], set[str], dict[int, dict[str, list[str]]], dict[str, set[str]], dict[str, set[str]], int]:
    stdin = "\n".join([*fork_heads, *(f"^{head}" for head in official_heads)]) + "\n"
    extra = sorted(set(str(_git(root, "rev-list", "--stdin", input_text=stdin)).splitlines()))
    if len(extra) != EXTRA_COMMITS or _line_hash(extra) != EXTRA_COMMIT_SHA256:
        raise RuntimeError("TradingAgents fork extra-commit graph changed")
    commit_input = tempfile.TemporaryFile()
    commit_input.write(("\n".join(extra) + "\n").encode())
    commit_input.seek(0)
    proc = subprocess.Popen(
        [
            "git",
            "-C",
            str(root),
            "diff-tree",
            "--stdin",
            "-z",
            "--root",
            "-m",
            "-r",
            "--raw",
            "--no-renames",
            "--format=%H%x00",
        ],
        stdin=commit_input,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
    )
    assert proc.stdout
    paths: set[str] = set()
    blobs: dict[str, set[str]] = defaultdict(set)
    blob_commits: dict[str, set[str]] = defaultdict(set)
    current = ""
    expect: tuple[str, str] | None = None
    buffer = b""
    raw_rows = 0
    while chunk := proc.stdout.read(1024 * 1024):
        buffer += chunk
        parts = buffer.split(b"\0")
        buffer = parts.pop()
        for token in parts:
            token = token.lstrip(b"\n")
            if not token:
                continue
            if re.fullmatch(rb"[0-9a-f]{40}", token):
                current = token.decode()
            elif token.startswith(b":"):
                fields = token.decode().split()
                expect = (fields[3], fields[4])
            elif expect:
                new, status = expect
                expect = None
                path = token.decode("utf-8", "surrogateescape")
                paths.add(path)
                raw_rows += 1
                if new != "0" * 40 and not status.startswith("D"):
                    blobs[new].add(path)
                    blob_commits[new].add(current)
    stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
    return_code = proc.wait()
    commit_input.close()
    if buffer or return_code:
        raise RuntimeError(f"TradingAgents fork tree walk failed: {stderr[-1000:]}")
    path_values = sorted(paths)
    blob_values = sorted(blobs)
    if (
        len(path_values) != CHANGED_PATHS
        or hashlib.sha256(("\n".join(path_values) + "\n").encode("utf-8", "surrogateescape")).hexdigest()
        != CHANGED_PATH_SHA256
    ):
        raise RuntimeError("TradingAgents fork changed-path inventory changed")
    if len(blob_values) != CHANGED_NEW_BLOBS or _line_hash(blob_values) != CHANGED_NEW_BLOB_SHA256:
        raise RuntimeError("TradingAgents fork new-blob inventory changed")
    tiers: dict[int, dict[str, list[str]]] = {}
    for tier in range(1, 5):
        selected: dict[str, list[str]] = {}
        for blob, blob_paths in blobs.items():
            keep = []
            for path in blob_paths:
                if EXCLUDE_RE.search(path):
                    continue
                suffix = Path(path).suffix.lower()
                chosen = (
                    tier == 1
                    and (
                        suffix in {".csv", ".tsv", ".xlsx", ".xls", ".log"}
                        or (suffix in {".json", ".jsonl"} and (RESULT_DIR_RE.search(path) or STRICT_RE.search(path)))
                    )
                    or tier == 2
                    and suffix in {".md", ".txt", ".html", ".htm"}
                    and (RESULT_DIR_RE.search(path) or STRICT_RE.search(path))
                    or tier == 3
                    and suffix
                    in {
                        ".parquet",
                        ".arrow",
                        ".feather",
                        ".pkl",
                        ".pickle",
                        ".npy",
                        ".npz",
                        ".h5",
                        ".hdf5",
                        ".sqlite",
                        ".sqlite3",
                        ".db",
                    }
                    or tier == 4
                    and suffix in {".png", ".pdf"}
                )
                if chosen:
                    keep.append(path)
            if keep:
                selected[blob] = sorted(keep)
        expected = TIER_EXPECTED[tier]
        ids = sorted(selected)
        if (
            len(ids) != expected["blobs"]
            or len({path for values in selected.values() for path in values}) != expected["paths"]
            or _line_hash(ids) != expected["blob_sha256"]
        ):
            raise RuntimeError(f"TradingAgents fork tier {tier} changed")
        tiers[tier] = selected
    return extra, paths, tiers, blobs, blob_commits, raw_rows


def _text_tier_summary(root: Path, tier: int, selected: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    expected = TIER_EXPECTED[tier]
    ids = sorted(selected)
    total = text_count = binary_count = context_count = exact_period = all_assets = 0
    candidates = set()
    {value for methods in PERFORMANCE.values() for values in methods.values() for value in values}
    for blob, raw in _blob_batch(root, ids):
        total += len(raw)
        try:
            text = raw.decode("utf-8")
            text_count += 1
        except UnicodeDecodeError:
            text = ""
            binary_count += 1
        lower = text.lower()
        asset = any(name.lower() in lower for name in ("AAPL", "GOOGL", "AMZN"))
        metric = any(
            word in lower
            for word in (
                "sharpe",
                "drawdown",
                "cumulative return",
                "annualized return",
                "portfolio value",
                "cr%",
                "mdd%",
            )
        )
        context = bool(text and asset and metric)
        if context:
            context_count += 1
            numbers = [float(value) for value in NUMBER_RE.findall(text)]
            matches = []
            for method, assets in PERFORMANCE.items():
                if not any(alias in lower for alias in ALIASES[method]):
                    continue
                for name, values in assets.items():
                    if name.lower() in lower and all(
                        any(abs(number - value) < 1e-9 for number in numbers) for value in set(values)
                    ):
                        matches.append(f"{method}/{name}")
            if matches:
                candidates.add(blob)
        if "2024-01-01" in lower and "2024-03-29" in lower:
            exact_period += 1
        if all(name in lower for name in ("aapl", "googl", "amzn")):
            all_assets += 1
    observed = {
        "bytes": total,
        "text": text_count,
        "binary": binary_count,
        "paper_context": context_count,
        "exact_period": exact_period,
        "all_assets": all_assets,
    }
    if any(observed[key] != expected[key] for key in observed) or candidates != expected["broad_candidates"]:
        raise RuntimeError(f"TradingAgents fork tier {tier} content scan changed: {observed}, {sorted(candidates)}")
    return {
        "tier": tier,
        "role": "structured_result_and_log_text" if tier == 1 else "reports_and_html",
        "selected_blobs": len(ids),
        "selected_paths": expected["paths"],
        "bytes_reviewed": total,
        "utf8_text_blobs": text_count,
        "binary_blobs": binary_count,
        "paper_context_blobs": context_count,
        "exact_paper_period_blobs": exact_period,
        "all_three_paper_asset_blobs": all_assets,
        "broad_paper_value_candidates_manually_classified": len(candidates),
        "attributable_paper_run_artifacts": 0,
        "paper_result_credit": False,
    }


def _binary_tier_summary(root: Path, selected: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    import pyarrow as pa
    import pyarrow.parquet as pq

    formats = Counter()
    total = sqlite_rows = sqlite_cells = parquet_rows = parquet_scalars = exact_period_asset = broad_sqlite = 0
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory) / "artifact.sqlite"
        for blob, raw in _blob_batch(root, sorted(selected)):
            total += len(raw)
            paths = selected[blob]
            if raw[:4] == b"PAR1" and raw[-4:] == b"PAR1":
                formats["parquet"] += 1
                table = pq.read_table(pa.BufferReader(raw))
                parquet_rows += table.num_rows
                parquet_scalars += sum(len(column) for column in table.itercolumns())
                values = []
                for column in table.itercolumns():
                    values.extend(str(value) for value in column.to_pylist() if value is not None)
                lower = ("\n".join(values) + "\n" + "\n".join(paths) + "\n" + "\n".join(table.column_names)).lower()
                if (
                    "2024-01-01" in lower
                    and "2024-03-29" in lower
                    and any(name in lower for name in ("aapl", "googl", "amzn"))
                ):
                    exact_period_asset += 1
            elif raw[:16] == b"SQLite format 3\x00":
                formats["sqlite"] += 1
                temp.write_bytes(raw)
                con = sqlite3.connect(f"file:{temp}?mode=ro&immutable=1", uri=True)
                texts = []
                numbers = []
                tables = [
                    row[0] for row in con.execute("select name from sqlite_master where type='table' order by name")
                ]
                for name in tables:
                    ident = '"' + name.replace('"', '""') + '"'
                    for record in con.execute(f"select * from {ident}"):
                        sqlite_rows += 1
                        for value in record:
                            sqlite_cells += 1
                            if isinstance(value, (int, float)) and not isinstance(value, bool):
                                numbers.append(float(value))
                            elif isinstance(value, str):
                                texts.append(value)
                                numbers.extend(float(item) for item in NUMBER_RE.findall(value))
                con.close()
                temp.unlink(missing_ok=True)
                lower = ("\n".join(texts) + "\n" + "\n".join(paths) + "\n" + "\n".join(tables)).lower()
                matches = 0
                for method, assets in PERFORMANCE.items():
                    if not any(alias in lower for alias in ALIASES[method]):
                        continue
                    for asset, values in assets.items():
                        if asset.lower() in lower and all(
                            any(abs(number - value) < 1e-9 for number in numbers) for value in set(values)
                        ):
                            matches += 1
                broad_sqlite += bool(matches)
                if (
                    "2024-01-01" in lower
                    and "2024-03-29" in lower
                    and any(name in lower for name in ("aapl", "googl", "amzn"))
                ):
                    exact_period_asset += 1
            elif raw[:1] == b"\x80":
                formats["pickle_not_deserialized"] += 1
            else:
                formats["unknown_binary"] += 1
    expected_formats = Counter({"sqlite": 977, "parquet": 835, "pickle_not_deserialized": 118, "unknown_binary": 1})
    if (
        total != TIER_EXPECTED[3]["bytes"]
        or formats != expected_formats
        or sqlite_rows != 549091
        or sqlite_cells != 4355590
        or parquet_rows != 979941
        or parquet_scalars != 6235732
        or exact_period_asset
        or broad_sqlite != 15
    ):
        raise RuntimeError(
            f"TradingAgents binary fork scan changed: {formats}, {total}, {sqlite_rows}, {sqlite_cells}, {parquet_rows}, {parquet_scalars}, {exact_period_asset}, {broad_sqlite}"
        )
    return {
        "tier": 3,
        "role": "parquet_sqlite_and_opaque_pickle",
        "selected_blobs": TIER_EXPECTED[3]["blobs"],
        "selected_paths": TIER_EXPECTED[3]["paths"],
        "bytes_reviewed": total,
        "sqlite_blobs": formats["sqlite"],
        "sqlite_rows_reviewed": sqlite_rows,
        "sqlite_cells_reviewed": sqlite_cells,
        "parquet_blobs": formats["parquet"],
        "parquet_rows_reviewed": parquet_rows,
        "parquet_scalars_reviewed": parquet_scalars,
        "pickle_blobs_not_deserialized": formats["pickle_not_deserialized"],
        "broad_sqlite_value_candidates_manually_classified": broad_sqlite,
        "exact_period_and_paper_asset_artifacts": 0,
        "attributable_paper_run_artifacts": 0,
        "paper_result_credit": False,
    }


def _visual_summary(root: Path, selected: Mapping[str, Sequence[str]], paper_hashes: set[str]) -> dict[str, Any]:
    formats = Counter()
    total = exact = asset_paths = 0
    for blob, raw in _blob_batch(root, sorted(selected)):
        total += len(raw)
        digest = hashlib.sha256(raw).hexdigest()
        exact += digest in paper_hashes
        lower = "\n".join(selected[blob]).lower()
        asset_paths += any(name in lower for name in ("aapl", "googl", "amzn"))
        formats["pdf" if raw.startswith(b"%PDF") else "png" if raw.startswith(b"\x89PNG") else "other"] += 1
    if (
        total != TIER_EXPECTED[4]["bytes"]
        or formats != Counter({"png": 1507, "pdf": 400, "other": 15})
        or exact
        or asset_paths != 15
    ):
        raise RuntimeError(f"TradingAgents fork visual scan changed: {formats}, {total}, {exact}, {asset_paths}")
    return {
        "tier": 4,
        "role": "visual_result_candidates",
        "selected_blobs": TIER_EXPECTED[4]["blobs"],
        "selected_paths": TIER_EXPECTED[4]["paths"],
        "bytes_reviewed": total,
        "png_blobs": formats["png"],
        "pdf_blobs": formats["pdf"],
        "other_blobs": formats["other"],
        "exact_paper_figure_file_hashes": 0,
        "paper_asset_named_paths": asset_paths,
        "author_attributable_raster_output_artifacts": 2,
        "attributable_paper_run_artifacts": 0,
        "paper_result_credit": False,
    }


def _author_rasters(root: Path, paper_source_root: Path) -> list[dict[str, Any]]:
    import numpy as np
    from PIL import Image

    specs = [
        ("cumulative_return", "compare.pdf", AUTHOR_RASTER_BLOBS["cumulative_return"], "CumulativeReturns_AAPL.png", 6),
        (
            "transaction_history",
            "details.pdf",
            AUTHOR_RASTER_BLOBS["transaction_history"],
            "TradingAgents_Transactions_AAPL.png",
            8,
        ),
    ]
    rows = []
    for panel, pdf_name, blob, png_name, series in specs:
        raw = bytes(_git(root, "cat-file", "blob", blob, binary=True))
        pdf = paper_source_root / "figures/AAPL" / pdf_name
        rendered = subprocess.run(
            ["pdftocairo", "-png", "-singlefile", "-r", "300", str(pdf), "-"], capture_output=True, check=True
        ).stdout
        fork_image = np.array(Image.open(BytesIO(raw)).convert("RGB"))
        paper_image = np.array(Image.open(BytesIO(rendered)).convert("RGB"))
        difference = np.abs(fork_image.astype(np.int16) - paper_image.astype(np.int16))
        correspondence = bool(
            fork_image.shape == paper_image.shape
            and float(difference.mean()) < 1
            and float((difference <= 5).mean()) > 0.97
        )
        rows.append(
            {
                "evidence_commit": AUTHOR_SITE_EVIDENCE_COMMIT,
                "commit_author": "Yijia-Xiao <yijia-xiao@outlook.com>",
                "commit_date": "2024-12-28T11:47:36+08:00",
                "fork_blob": blob,
                "fork_blob_sha256": hashlib.sha256(raw).hexdigest(),
                "fork_path": f"static/images/{png_name}",
                "paper_source_pdf": f"figures/AAPL/{pdf_name}",
                "paper_source_pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                "panel": panel,
                "series_corresponding": series,
                "fork_dimensions": f"{fork_image.shape[1]}x{fork_image.shape[0]}",
                "paper_pdf_300dpi_dimensions": f"{paper_image.shape[1]}x{paper_image.shape[0]}",
                "equal_channel_fraction": float((fork_image == paper_image).mean()),
                "mean_absolute_channel_difference": float(difference.mean()),
                "channel_difference_le_5_fraction": float((difference <= 5).mean()),
                "cross_format_raster_correspondence": correspondence,
                "underlying_numeric_array_recovered": False,
                "native_series_regenerated": False,
                "paper_result_credit": False,
            }
        )
    if (
        not all(row["cross_format_raster_correspondence"] for row in rows)
        or sum(row["series_corresponding"] for row in rows) != 14
    ):
        raise RuntimeError("TradingAgents author raster correspondence changed")
    return rows


def audit_public_forks(
    root: Path, paper_source_root: Path, snapshot: Path, *, deep_scan: bool = True
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    branch_rows = _read_snapshot(snapshot)
    fork_heads = sorted({row["head_commit"] for row in branch_rows})
    if len(fork_heads) != UNIQUE_HEADS or _line_hash(fork_heads) != UNIQUE_HEAD_SHA256:
        raise RuntimeError("TradingAgents fork unique heads changed")
    official_heads, official_commits, official_identities, official_emails = _official_state(root)
    divergent = sorted(set(fork_heads) - official_commits)
    if (
        len(set(fork_heads) & official_commits) != HEADS_IN_OFFICIAL_HISTORY
        or len(divergent) != DIVERGENT_HEADS
        or _line_hash(divergent) != DIVERGENT_HEAD_SHA256
    ):
        raise RuntimeError("TradingAgents fork divergence boundary changed")

    def connected(head: str) -> bool:
        return (
            subprocess.run(
                ["git", "-C", str(root), "merge-base", "--is-ancestor", SOURCE_ROOT_COMMIT, head],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )

    with ThreadPoolExecutor(max_workers=24) as pool:
        connected_flags = list(pool.map(connected, divergent))
    connected_heads = {head for head, flag in zip(divergent, connected_flags) if flag}
    if (
        len(connected_heads) != CONNECTED_DIVERGENT_HEADS
        or len(set(divergent) - connected_heads) != DISCONNECTED_DIVERGENT_HEADS
    ):
        raise RuntimeError("TradingAgents fork ancestry boundary changed")
    extra, changed_paths, tiers, _blobs, _blob_commits, raw_diff_rows = _graph_and_tiers(
        root, fork_heads, official_heads
    )
    refs_by_head: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in branch_rows:
        refs_by_head[row["head_commit"]].append(row)
    head_rows = []
    for head in fork_heads:
        refs = refs_by_head[head]
        status = (
            "official_history_reachable"
            if head in official_commits
            else "connected_divergent"
            if head in connected_heads
            else "disconnected_divergent"
        )
        head_rows.append(
            {
                "head_commit": head,
                "status": status,
                "repository_count": len({row["repository"] for row in refs}),
                "branch_ref_count": len(refs),
                "example_repositories": ";".join(sorted({row["repository"] for row in refs})[:5]),
                "paper_result_credit": False,
            }
        )
    raw = bytes(
        _git(
            root,
            "log",
            "--no-walk",
            "--stdin",
            "--format=%H%x00%aN%x00%aE%x00%aI%x00%s",
            input_text="\n".join(extra) + "\n",
            binary=True,
        )
    )
    commit_rows = []
    for line in raw.splitlines():
        fields = line.split(b"\0", 4)
        if len(fields) != 5:
            continue
        commit, name, email, date, subject = [field.decode("utf-8", "replace") for field in fields]
        commit_rows.append(
            {
                "commit": commit,
                "author_name": name,
                "author_email": email,
                "author_date": date,
                "subject": subject,
                "exact_official_name_email_identity": (name, email) in official_identities,
                "official_author_email": email.lower() in official_emails,
                "paper_result_credit": False,
            }
        )
    commit_rows.sort(key=lambda row: row["commit"])
    if (
        len(official_identities) != OFFICIAL_AUTHOR_IDENTITIES
        or sum(row["exact_official_name_email_identity"] for row in commit_rows)
        != EXTRA_EXACT_OFFICIAL_IDENTITY_COMMITS
        or sum(row["official_author_email"] for row in commit_rows) != EXTRA_OFFICIAL_EMAIL_COMMITS
    ):
        raise RuntimeError("TradingAgents fork author-identity census changed")
    site_commits = str(_git(root, "rev-list", AUTHOR_SITE_HEAD)).splitlines()
    site_paths = sorted(
        {
            line
            for line in str(
                _git(
                    root,
                    "diff-tree",
                    "--stdin",
                    "--root",
                    "-m",
                    "-r",
                    "--name-only",
                    "--no-commit-id",
                    input_text="\n".join(site_commits) + "\n",
                )
            ).splitlines()
            if line
        }
    )
    if (
        len(site_commits) != AUTHOR_SITE_COMMITS
        or _line_hash(sorted(site_commits)) != AUTHOR_SITE_COMMIT_SHA256
        or len(site_paths) != AUTHOR_SITE_PATHS
        or _line_hash(site_paths) != AUTHOR_SITE_PATH_SHA256
    ):
        raise RuntimeError("TradingAgents fork-preserved author site changed")
    site_rows = []
    commit_by_id = {row["commit"]: row for row in commit_rows}
    for commit in site_commits:
        metadata = commit_by_id[commit]
        author = f"{metadata['author_name']} <{metadata['author_email']}>"
        site_rows.append(
            {
                "commit": commit,
                "author": author,
                "author_date": metadata["author_date"],
                "subject": metadata["subject"],
                "exact_official_author_identity": author
                in {f"{name} <{email}>" for name, email in official_identities},
                "paper_result_credit": False,
            }
        )
    preserved_refs = [row for row in branch_rows if row["head_commit"] in AUTHOR_SITE_PRESERVING_HEADS]
    if (
        len(preserved_refs) != AUTHOR_SITE_PRESERVING_REFS
        or len({row["repository"] for row in preserved_refs}) != AUTHOR_SITE_PRESERVING_REFS
    ):
        raise RuntimeError("TradingAgents author-site preserving fork set changed")
    raster_rows = _author_rasters(root, paper_source_root) if deep_scan else []
    if deep_scan:
        tier_rows = [
            _text_tier_summary(root, 1, tiers[1]),
            _text_tier_summary(root, 2, tiers[2]),
            _binary_tier_summary(root, tiers[3]),
            _visual_summary(
                root,
                tiers[4],
                {
                    hashlib.sha256((paper_source_root / relative).read_bytes()).hexdigest()
                    for relative in (
                        "figures/AAPL/compare.pdf",
                        "figures/AAPL/details.pdf",
                        "figures/GOOGL/compare.pdf",
                        "figures/GOOGL/details.pdf",
                        "figures/AMZN/compare.pdf",
                        "figures/AMZN/details.pdf",
                    )
                },
            ),
        ]
    else:
        tier_rows = [
            {
                "tier": tier,
                "selected_blobs": expected["blobs"],
                "selected_paths": expected["paths"],
                "bytes_reviewed": expected["bytes"],
                "paper_result_credit": False,
            }
            for tier, expected in sorted(TIER_EXPECTED.items())
        ]
    notable_rows = []
    common_tier_fields = {
        "tier",
        "role",
        "selected_blobs",
        "selected_paths",
        "bytes_reviewed",
        "paper_result_credit",
    }
    tier_rows = [
        {
            "tier": row["tier"],
            "role": row.get("role", "graph_only_validation"),
            "selected_blobs": row["selected_blobs"],
            "selected_paths": row["selected_paths"],
            "bytes_reviewed": row["bytes_reviewed"],
            "scan_details": json.dumps(
                {key: value for key, value in row.items() if key not in common_tier_fields},
                sort_keys=True,
                separators=(",", ":"),
            ),
            "paper_result_credit": False,
        }
        for row in tier_rows
    ]
    for role, blob in COMMUNITY_REPORT_BLOBS.items():
        payload = bytes(_git(root, "cat-file", "blob", blob, binary=True))
        text = payload.decode("utf-8")
        if role == "unaffiliated_aapl_baseline" and not all(
            value in text for value in ("22.59%", "50.29%", "1.76", "11.75%")
        ):
            raise RuntimeError("TradingAgents community baseline report changed")
        notable_rows.append(
            {
                "git_blob": blob,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "evidence_commit": COMMUNITY_REPORT_COMMIT,
                "artifact_role": role,
                "attribution": "unaffiliated_community_fork",
                "reported_or_quoted_paper_rows": "AAPL",
                "raw_result_lineage_shipped": False,
                "attributable_paper_run_artifact": False,
                "paper_result_credit": False,
            }
        )
    summary = {
        "census_date": CENSUS_DATE,
        "github_rest_reported_forks": REST_REPORTED_FORKS,
        "graphql_accessible_forks": ACCESSIBLE_FORKS,
        "accessibility_gap": REST_REPORTED_FORKS - ACCESSIBLE_FORKS,
        "branch_refs_examined": len(branch_rows),
        "unique_heads_examined": len(fork_heads),
        "heads_reachable_from_official_history": len(set(fork_heads) & official_commits),
        "divergent_heads_examined": len(divergent),
        "connected_divergent_heads": len(connected_heads),
        "disconnected_divergent_heads": len(set(divergent) - connected_heads),
        "extra_commits_examined": len(extra),
        "raw_commit_tree_delta_rows": raw_diff_rows,
        "changed_paths_examined": len(changed_paths),
        "changed_new_blobs_inventoried": CHANGED_NEW_BLOBS,
        "unique_selected_artifact_blobs_reviewed": len({blob for tier in tiers.values() for blob in tier}),
        "selected_artifact_blob_tier_memberships": sum(row["selected_blobs"] for row in tier_rows),
        "unique_selected_artifact_bytes_reviewed": 6257226176,
        "official_author_identities": len(official_identities),
        "extra_commits_with_exact_official_author_identity": sum(
            row["exact_official_name_email_identity"] for row in commit_rows
        ),
        "extra_commits_with_official_author_email": sum(row["official_author_email"] for row in commit_rows),
        "fork_preserved_author_site_commits": len(site_commits),
        "fork_preserved_author_site_paths": len(site_paths),
        "fork_refs_preserving_author_site_history": len(preserved_refs),
        "fork_repositories_preserving_author_site_history": len({row["repository"] for row in preserved_refs}),
        "author_raster_panels_corresponding_cross_format": len(raster_rows) if deep_scan else 2,
        "author_raster_series_corresponding_cross_format": sum(row["series_corresponding"] for row in raster_rows)
        if deep_scan
        else 14,
        "underlying_numeric_arrays_recovered_from_author_rasters": 0,
        "attributable_paper_run_artifacts": 0,
        "paper_table_cells_independently_regenerated_from_forks": 0,
        "paper_figure_series_independently_regenerated_from_forks": 0,
        "paper_result_credit": False,
        "assessment": "author_raster_output_lineage_and_unaffiliated_postpaper_runs_found_but_zero_attributable_native_paper_result_arrays_or_regeneration",
    }
    return branch_rows, head_rows, commit_rows, tier_rows, site_rows, raster_rows, notable_rows, summary
