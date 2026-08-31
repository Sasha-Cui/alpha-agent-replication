#!/usr/bin/env python3
"""Build a fail-closed original-source audit for arXiv:2607.12233v1."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/fin_analyst_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/fin_analyst"
NATIVE_ENV = Path(
    "/nfs/roberts/project/pi_btk22/zc362/environments/venvs/"
    "alpha-fin-analyst-native-py312-20260813"
)
WORK_ID = "CensusArxiv260712233"
SYSTEM_ID = "SYS-FIN-ANALYST"
ARXIV_ID = "2607.12233"
AUTHOR_SPACE = "https://huggingface.co/spaces/Mohotarema/Fin_Analyst"
DATASET_URL = "https://huggingface.co/datasets/TheFinAI/CLEF_Task3_Trading"
ARENA_SPACE = "https://huggingface.co/spaces/TheFinAI/Agent-Market-Arena"
AUTHOR_COMMIT = "85ab4781e74ed3deb9a7ef49bca3fa23b1ed9738"
DATASET_COMMIT = "3ae0b896ed02e882c362f8edc90fd276159f5c5e"
ARENA_COMMIT = "70c388c317b22322145ca8c2a5fe7aa5fe89dba3"
ORGANIZER_PERF_SHA256 = (
    "62e6e637900d6e5d84c6671df19ab7d17641d7ebc4dce8127930b7f1d65315b5"
)
ORGANIZER_RUNNER = ROOT / "scripts/run_fin_analyst_organizer_scorer.mjs"
ORGANIZER_RUNNER_SHA256 = (
    "4112e9d74b065130e98636f69d7942258503c8a37094cea67541b48b0837434f"
)
AUTHOR_ARCHIVE_COMMIT = "5c7db3f9dd34108979218187eb2a81d9efe581d0"
AUTHOR_ARCHIVE_DELETION_COMMIT = "65273e6cc6bf1c10577bb02095a099d6bcefb584"
AUTHOR_ARCHIVE_LFS_SHA256 = (
    "906caf4995c1984853d05fc7e70812d3d2f6050035a5851ff17aa0c49e766036"
)
AUTHOR_ARCHIVE_BYTES = 9_356
OFFLINE_BASELINE_REVISIONS = {
    "TSLA": {
        "commit": "5b6ddd542ff5c940c87901ed2dff132888ce66fc",
        "dataset_end": "2026-05-20",
    },
    "BTC": {
        "commit": "c1b9ecd98b7ccc913d915621e313867e19e44555",
        "dataset_end": "2026-05-21",
    },
}
DECLARED_OFFLINE_END = "2026-05-10"
EXPECTED_HISTORY_COUNTS = {
    "author_space": {"commits": 5, "objects": 25, "paths": 13},
    "dataset": {"commits": 103, "objects": 615, "paths": 4},
    "organizer": {"commits": 327, "objects": 1807, "paths": 104},
}

OFFLINE_BASELINE_SEARCH_PATTERNS = {
    "exact_offline_identifiers": (
        r"Always[ _-]+HOLD|NewsOnly|Fin-Analyst[ _-]*\(rule-based\)|"
        r"alpha[_ -]*BH|sigma\S{0,8}42"
    ),
    "random_generator_calls": (
        r"np\.random|numpy\.random|random\.(seed|choice|choices|randint|random)|"
        r"Math\.random|seed\S{0,8}42"
    ),
    "random_term": r"(?<![A-Za-z])Random(?![A-Za-z])",
    "momentum_term": r"(?<![A-Za-z])Momentum(?![A-Za-z])",
    "backtest_term": r"(?<![A-Za-z])backtest(?![A-Za-z])",
}
OFFLINE_BASELINE_GIT_GREP_PATTERN = (
    r"Always[ _-]+HOLD|NewsOnly|Fin-Analyst[ _-]*\(rule-based\)|"
    r"alpha[_ -]*BH|sigma[^[:space:]]{0,8}42|np\.random|numpy\.random|"
    r"random\.(seed|choice|choices|randint|random)|Math\.random|"
    r"seed[^[:space:]]{0,8}42|(^|[^A-Za-z])(Random|Momentum|backtest)([^A-Za-z]|$)"
)
SOURCE_LIKE_SUFFIXES = {
    ".py", ".js", ".ts", ".vue", ".mjs", ".md", ".txt", ".json", ".toml", ".yaml", ".yml"
}



PINS = {
    "primary/arxiv-abs.html": "95bdb9c6838813a55180f04675179f29d988d99555418ffb2767304f57380875",
    "primary/arxiv-api.xml": "a9ae0cdc05b10433dbfda5af323fd7a3bc6a3672f8d59a218e1c5d7243177065",
    "primary/official-v1.pdf": "8b03c2ae99aff919be41757bb465fb958d69a3b0ccc4ceb35aef1706e2e46a79",
    "primary/official-v1.txt": "4d2b454b7cb41ba886668ed1a45ccc6ce152e58a62fe82f18a167bf0910ed9fe",
    "primary/rebuilt-v1.pdf": "3af9106916268664dba4800f52e7c90289d935c97f0dd0397bff5006258443bf",
    "primary/rebuilt-v1.txt": "46db4283ad7a0ab6bfe73af5836ee3fb93a991735b23d92b815a9b7ddf56f37b",
    "primary/source-v1.tar": "6f8d42ec5c5aec1855c5e6db096949e96e40a3b469f68c9a5d25b68bf62470c9",
    "discovery/github-code-arxiv.json": "12d4a95746967e8f197f7552ed15cc3af36c5d3f37ba4f3dc9b3f3dde2b193a5",
    "discovery/github-code-title.json": "b43041bf98ae4e66d68a1211a90bed8005416e36bdc8debe25415ce3558d64dc",
    "discovery/github-repositories-arxiv.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-repositories-title.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/huggingface-spaces-arxiv.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-spaces-title.json": "1691349b81cd6b6a73915f117a33029c79f4a2f9774302a5459f6b1ce95af033",
    "discovery/huggingface-space-author-api.json": "6d5bafec6f69da4271f37be84f27c5e7c627d905df5223fec37a0a55e96842f2",
    "discovery/huggingface-dataset-api.json": "a5860736eddc0950658c8d381fb135a5176752da11fd47094906503c13e223de",
    "discovery/arena-fin-analyst-rows.json": "8817fd68587630ab5eff44e93dfa3135399ad135c40e913963bee2c0c81a4a06",
    "dataset-may11/TSLA.parquet": "7f7493e8e94e92ac2ebd4cc0626fa23be8f331ddab1e61e4ff8bc03e8aa5fe98",
    "dataset-may11/BTC.parquet": "718cf95e62d1a035375630387b2b38b044d9bde71aa8b75ba6739ac53dc1aa2f",
    "replay/TSLA.json": "0b4574340b8c987eb3c67732b73f22cf7f080a5483c5bce988dccad400ba4728",
    "replay/BTC.json": "09462f433ecd282abcdd699181ba75f4450a1a45f7068e97fc78716ba14712d8",
    "replay/perf.mjs": "62e6e637900d6e5d84c6671df19ab7d17641d7ebc4dce8127930b7f1d65315b5",
    "native/Fin_Analyst/app.py": "85ca91dd10ae9009093fc7b113d7347f6fd0a6d240281e609a0b9443b366eef1",
    "native/Fin_Analyst/requirements.txt": "96617c24565c1d5528cbca62730ad85e0d3c9c92d1c23a23c4c1daa0e008e88a",
    "native/Fin_Analyst/Dockerfile": "ede3a50786b8b29726bc5f284c4548542633bc63e6192ac32066c03c2a82f3d1",
}

TABLE_SPECS = {
    "tab:results": ({"TSLA", "BTC"}, 10),
    "tab:tsla": ({"Buy & Hold", "Always HOLD", "Random (sigma=42)", "Momentum", "NewsOnly", "Fin-Analyst"}, 42),
    "tab:btc": ({"Buy & Hold", "Always HOLD", "Random", "Momentum", "Fin-Analyst (rule-based)"}, 35),
    "tab:ablation": ({"Event (8-K)", "Quarterly (10-Q)", "News (daily bundle)", "Annual (10-K)", "Fundamentals (Compustat)"}, 20),
    "tab:error_attribution": ({"Final return (net of fees)", "Acted days / exposure", "Hit rate (acted days)", "Long days: hit / total PnL", "Short days: hit / total PnL", "Max equity drawdown"}, 12),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    ).stdout


def git_text(root: Path, *args: str) -> str:
    return git_bytes(root, *args).decode("utf-8").strip()


def repository_history_facts(root: Path) -> dict[str, Any]:
    commits = int(git_text(root, "rev-list", "--all", "--count"))
    object_lines = git_text(root, "rev-list", "--objects", "--all").splitlines()
    path_lines = git_text(root, "log", "--all", "--name-only", "--format=").splitlines()
    paths = sorted({line for line in path_lines if line})
    unique_heads = {
        line
        for line in git_text(
            root,
            "for-each-ref",
            "--format=%(objectname)",
            "refs/heads",
            "refs/remotes",
        ).splitlines()
        if line
    }
    return {
        "commits": commits,
        "objects": len(object_lines),
        "paths": len(paths),
        "unique_ref_heads": len(unique_heads),
        "historical_paths": paths,
    }


def offline_baseline_generator_search(scratch: Path) -> list[dict[str, Any]]:
    """Exhaust every pinned history for the missing Random/Momentum baseline generators."""
    repositories = {
        "author_space": scratch / "native/Fin_Analyst",
        "dataset": scratch / "native/CLEF_Task3_Trading",
        "organizer": scratch / "native/Agent-Market-Arena",
    }
    compiled = {
        family: re.compile(pattern, re.IGNORECASE)
        for family, pattern in OFFLINE_BASELINE_SEARCH_PATTERNS.items()
    }
    expected_momentum_paths = {
        "author_space": {"app.py"},
        "dataset": {"README.md"},
        "organizer": {"src/views/RequestView.vue"},
    }
    output: list[dict[str, Any]] = []
    for repository, root in repositories.items():
        commits = git_text(root, "rev-list", "--all").splitlines()
        expected_commits = EXPECTED_HISTORY_COUNTS[repository]["commits"]
        if len(commits) != expected_commits:
            raise ValueError(f"{repository} baseline-search commit census changed")
        completed = subprocess.run(
            [
                "git", "-C", str(root), "grep", "-n", "-I", "-i", "-E",
                OFFLINE_BASELINE_GIT_GREP_PATTERN, *commits,
            ],
            capture_output=True,
            text=True,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError(f"{repository} historical baseline grep failed")
        parsed = []
        for line in completed.stdout.splitlines():
            match = re.match(r"^([0-9a-f]{40}):([^:]+):(\d+):(.*)$", line)
            if match is None:
                raise ValueError(f"unexpected historical grep row: {line[:120]}")
            commit, path, line_number, content = match.groups()
            source_like = (
                Path(path).suffix.lower() in SOURCE_LIKE_SUFFIXES
                and not path.endswith((".jsonl", ".csv"))
            )
            parsed.append(
                {
                    "commit": commit,
                    "path": path,
                    "line_number": int(line_number),
                    "content": content,
                    "source_like": source_like,
                }
            )
        for family, pattern in compiled.items():
            matches = [row for row in parsed if pattern.search(row["content"])]
            source_matches = [row for row in matches if row["source_like"]]
            unique_source = sorted(
                {
                    (row["path"], row["line_number"], row["content"])
                    for row in source_matches
                }
            )
            source_paths = sorted({row[0] for row in unique_source})
            candidate = bool(unique_source) and family in {
                "exact_offline_identifiers",
                "random_generator_calls",
                "random_term",
                "backtest_term",
            }
            if family == "exact_offline_identifiers":
                interpretation = (
                    "potential exact offline baseline identifier requires review"
                    if candidate
                    else "no exact offline table label, sigma-42 marker, or alpha_BH identifier"
                )
            elif family == "random_generator_calls":
                interpretation = (
                    "potential random baseline generator requires review"
                    if candidate
                    else "no random sampling call or seed-42 implementation"
                )
            elif family == "random_term":
                interpretation = (
                    "potential source-level Random baseline reference requires review"
                    if candidate
                    else "Random appears only in bundled corpus text or not at all"
                )
            elif family == "momentum_term":
                interpretation = (
                    "momentum appears only as a live-agent/input term, not an offline generator"
                    if unique_source
                    else "no source-level momentum term"
                )
            else:
                interpretation = (
                    "potential source-level backtest generator requires review"
                    if candidate
                    else "backtest appears only in bundled corpus text or not at all"
                )
            output.append(
                {
                    "repository": repository,
                    "reachable_commits_examined": len(commits),
                    "search_family": family,
                    "python_regex": OFFLINE_BASELINE_SEARCH_PATTERNS[family],
                    "raw_matches_across_commits_and_text": len(matches),
                    "source_matches_across_commits": len(source_matches),
                    "unique_source_hits": len(unique_source),
                    "source_paths": ";".join(source_paths),
                    "offline_baseline_generator_candidate": candidate,
                    "interpretation": interpretation,
                }
            )
        momentum_row = next(
            row
            for row in output
            if row["repository"] == repository and row["search_family"] == "momentum_term"
        )
        if set(filter(None, momentum_row["source_paths"].split(";"))) != expected_momentum_paths[
            repository
        ]:
            raise ValueError(f"{repository} momentum-source boundary changed")
    if len(output) != 15 or any(
        row["offline_baseline_generator_candidate"] for row in output
    ):
        raise ValueError("Fin-Analyst offline baseline generator search boundary changed")
    return output



def lfs_pointer(value: bytes) -> tuple[str, int]:
    text = value.decode("ascii")
    match = re.fullmatch(
        r"version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize (\d+)\n?",
        text,
    )
    if match is None:
        raise ValueError("malformed Git LFS pointer")
    return match.group(1), int(match.group(2))


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty ledger: {path}")
    fieldnames = list(values[0])
    fieldnames.extend(
        key for row in values for key in row if key not in fieldnames
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def token_jaccard(left: str, right: str) -> float:
    a = Counter(re.findall(r"\w+", left.lower()))
    b = Counter(re.findall(r"\w+", right.lower()))
    return sum((a & b).values()) / sum((a | b).values())


def verify_pins(scratch: Path) -> None:
    for relative, expected in PINS.items():
        observed = sha256(scratch / relative)
        if observed != expected:
            raise ValueError(f"pin mismatch: {relative}={observed}; expected {expected}")
    repos = {
        "native/Fin_Analyst": AUTHOR_COMMIT,
        "native/CLEF_Task3_Trading": "eae085ce5b82fa3ca852e10372882b5ef2644705",
        "native/Agent-Market-Arena": ARENA_COMMIT,
    }
    for relative, expected in repos.items():
        observed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=scratch / relative, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        if observed != expected:
            raise ValueError(f"repository pin mismatch: {relative}={observed}")
    ancestor = subprocess.run(
        ["git", "cat-file", "-e", f"{DATASET_COMMIT}^{{commit}}"],
        cwd=scratch / "native/CLEF_Task3_Trading", check=False,
    )
    if ancestor.returncode:
        raise ValueError("pinned pre-live dataset revision is absent")


def paper_sources(scratch: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(scratch / "primary/source-v1.tar", "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe source member: {member.name}")
            if member.isfile():
                handle = archive.extractfile(member)
                if handle is None:
                    raise ValueError(f"unreadable source member: {member.name}")
                files[member.name] = handle.read()
    if len(files) != 9:
        raise ValueError(f"paper source file count changed: {len(files)}")
    return files


def strip_comments(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("%"))


def table_environment(source: str, label: str) -> str:
    source = strip_comments(source)
    location = source.index(rf"\label{{{label}}}")
    begin = source.rfind(r"\begin{table", 0, location)
    end = source.find(r"\end{table", location)
    if begin < 0 or end < 0:
        raise ValueError(f"table boundary missing: {label}")
    return source[begin:end]


def clean_tex(value: str) -> str:
    value = value.replace(r"\&", "&").replace(r"\%", "%").replace(r"\,", "")
    value = value.replace(r"\textsc", r"\textbf").replace(r"\sigma", "sigma")
    value = re.sub(r"\\(?:textbf|textit|emph|mathbf|boldsymbol)\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\text\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\(?:alpha|Delta)_\{[^{}]*\}", "", value)
    value = re.sub(r"\\(?:alpha|Delta)", "", value)
    value = re.sub(r"\\(?:toprule|midrule|bottomrule|small)", "", value)
    value = value.replace("~", " ")
    value = re.sub(r"[{}$]", "", value)
    value = value.replace("\\", "")
    return " ".join(value.split()).strip()


def table_rows(environment: str) -> list[list[str]]:
    match = re.search(r"\\begin\{tabular\}\{.*?\}(.*?)\\end\{tabular\}", environment, re.S)
    if match is None:
        raise ValueError("tabular body missing")
    values = []
    for chunk in re.split(r"\\\\", match.group(1)):
        if "&" in chunk:
            values.append([clean_tex(cell) for cell in re.split(r"(?<!\\)&", chunk)])
    return values


def result_rows(
    source: str,
    error_replay: list[dict[str, Any]] | None = None,
    baseline_replay: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    error_evidence = {
        (row["row_label"], row["asset"]): row for row in (error_replay or [])
    }
    all_rows: list[dict[str, Any]] = []
    baseline_evidence = {
        (row["table_label"], row["row_label"], row["quantitative_column_index"]): row
        for row in (baseline_replay or [])
    }
    for label, (expected_labels, expected_count) in TABLE_SPECS.items():
        selected: list[dict[str, Any]] = []
        for row_index, cells in enumerate(table_rows(table_environment(source, label)), 1):
            row_label = cells[0]
            match_label = next((name for name in expected_labels if row_label == name), None)
            if match_label is None:
                continue
            value_cells = cells[1:]
            if label == "tab:ablation":
                value_cells = value_cells[:4]
            for column_index, cell in enumerate(value_cells, 1):
                if not re.search(r"\d", cell):
                    continue
                asset = ("TSLA", "BTC")[column_index - 1] if label == "tab:error_attribution" else ""
                error_row = error_evidence.get((match_label, asset))
                baseline_row = baseline_evidence.get(
                    (label, match_label, column_index)
                )
                recovered = (
                    (label == "tab:results" and column_index <= 4)
                    or error_row is not None
                    or baseline_row is not None
                )
                regenerated = bool(
                    (error_row and error_row["full_printed_cell_match"])
                    or (baseline_row and baseline_row["matches_at_display_precision"])
                )
                selected.append({
                    "table_label": label,
                    "row_index": row_index,
                    "row_label": match_label,
                    "quantitative_column_index": column_index,
                    "printed_cell": cell,
                    "unit_definition": "one populated displayed empirical quantitative table cell",
                    "source_document_recovered": True,
                    "official_input_or_result_record_recovered": recovered,
                    "author_native_decision_pipeline_reexecuted": False,
                    "organizer_postprocessor_replayed": bool(
                        error_row or (label == "tab:results" and column_index <= 4)
                    ),
                    "organizer_native_scorer_executed": bool(
                        error_row or (label == "tab:results" and column_index <= 4)
                    ),
                    "official_historical_dataset_replayed": baseline_row is not None,
                    "paper_protocol_period_match": (
                        baseline_row["paper_protocol_period_match"]
                        if baseline_row
                        else ""
                    ),
                    "published_result_regenerated_at_display_precision": regenerated,
                    "paper_result_credit": False,
                    "blocking_reason": (
                        "official-history baseline regeneration: the printed cell is recovered exactly from a later asset-specific dataset revision whose endpoint conflicts with the paper's declared 2026-05-10 cutoff"
                        if baseline_row and regenerated else
                        "native-organizer verification: official decisions and exact pinned perf.js execution reproduce the printed cell; action-generation LLM calls were not rerun"
                        if regenerated else
                        "native-organizer partial check: official decisions recover part of the composite cell but not every printed component"
                        if error_row and error_row["matching_components"] else
                        "native-organizer conflict: official decisions and exact pinned perf.js execution do not reproduce the printed cell"
                        if error_row else
                        "live: official actions and exact current organizer perf.js execution disagree with the printed cell"
                        if recovered else
                        "offline: no author actions, model calls, seed, raw path, or result generator was released"
                    ),
                })
        if len(selected) != expected_count:
            raise ValueError(f"denominator changed for {label}: {len(selected)} != {expected_count}")
        all_rows.extend(selected)
    if len(all_rows) != 119:
        raise ValueError(f"published table denominator changed: {len(all_rows)}")
    return all_rows


def parse_prompt_constants(app_source: str) -> dict[str, str]:
    tree = ast.parse(app_source)
    result: dict[str, str] = {}
    names = {
        "NEWS_PROMPT": "News", "EVENT_PROMPT": "Event", "EARNINGS_PROMPT": "Earnings",
        "STRATEGY_PROMPT": "Strategy", "FUNDAMENTALS_PROMPT": "Fundamentals",
        "ANALYST_PROMPT": "Analyst", "TECHNICAL_PROMPT": "Technical",
        "SOCIAL_PROMPT": "Social", "META_PROMPT": "Meta agent",
    }
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            key = node.targets[0].id
            if key in names and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                result[names[key]] = node.value.value
    if set(result) != set(names.values()):
        raise ValueError("native prompt constant inventory changed")
    return result


def prompt_rows(source: str, app_source: str) -> list[dict[str, Any]]:
    native = parse_prompt_constants(app_source)
    prompt_table = source[source.index(r"\label{tab:prompts}"):source.index(r"\end{longtable}")]
    rows = []
    for name, text in native.items():
        printed_marker = rf"\textbf{{{name.replace('Meta agent', 'Meta agent')}}}"
        if printed_marker not in prompt_table:
            raise ValueError(f"paper prompt row missing: {name}")
        rows.append({
            "agent": name,
            "native_system_prompt_sha256": sha256_bytes(text.encode()),
            "native_system_prompt_characters": len(text),
            "paper_labels_prompts_full": True,
            "paper_row_present": True,
            "paper_row_is_byte_identical_to_native_prompt": False,
            "correspondence": "same role/rules but materially abridged prose",
            "result_credit": False,
        })
    return rows


def corpus_rows(scratch: Path) -> list[dict[str, Any]]:
    import pandas as pd

    base = scratch / "native/Fin_Analyst"
    specs = {
        "TSLA_10k_signals.jsonl": (2, "filed_date", "2025-01-30", "2026-01-29"),
        "TSLA_10q_signals.jsonl": (3, "date", "2025-04-23", "2025-10-23"),
        "TSLA_8k_signals.jsonl": (12, "date", "2025-01-02", "2025-11-07"),
        "TSLA_compustat_signals.jsonl": (29, "rdq", "2019-04-24", "2026-04-22"),
        "TSLA_ibes_signals.jsonl": (14, "date", "2025-01-16", "2026-02-19"),
        "TSLA_wsb_2025.jsonl": (5721, "date", "2025-01-01", "2026-04-12"),
        "TSLA_TA_2025.csv": (249, "date", "2025-01-02", "2025-12-30"),
    }
    rows = []
    for name, (expected_count, field, expected_min, expected_max) in specs.items():
        path = base / name
        if path.suffix == ".csv":
            records = pd.read_csv(path).to_dict("records")
        else:
            records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        values = [str(record.get(field, ""))[:10] for record in records]
        observed = (len(records), min(values), max(values))
        if observed != (expected_count, expected_min, expected_max):
            raise ValueError(f"native corpus inventory changed: {name}={observed}")
        rows.append({
            "file": name, "records": len(records), "date_field": field,
            "minimum_date": min(values), "maximum_date": max(values),
            "sha256": sha256(path), "loaded_by_native_startup": True,
            "paper_window_boundary": (
                "technical rows stop 2025-12-30 and are stale for the entire May-June 2026 live window"
                if name == "TSLA_TA_2025.csv" else
                "no 7-day WSB records exist after 2026-04-12, so Social defaults HOLD throughout live window"
                if name == "TSLA_wsb_2025.jsonl" else "most-recent record is carried forward"
            ),
        })
    return rows


def dataset_rows(scratch: Path) -> list[dict[str, Any]]:
    import pandas as pd

    rows = []
    expected = {
        "TSLA": (283, 194, 302.6300048828125, 489.8800048828125, 41.542477346020505, 0.379),
        "BTC": (283, 283, 62754.09, 124797.86, -27.517082642510637, -0.315),
    }
    for asset, values in expected.items():
        frame = pd.read_parquet(scratch / f"dataset-may11/{asset}.parquet")
        row_count, distinct_days, low, high, raw_return, printed_bh = values
        changes = int(frame["prices"].diff().fillna(1).ne(0).sum())
        observed_return = 100 * (frame["prices"].iloc[-1] / frame["prices"].iloc[0] - 1)
        if len(frame) != row_count or changes != distinct_days:
            raise ValueError(f"dataset row/trading-day count changed for {asset}")
        if abs(float(frame["prices"].min()) - low) > 1e-9 or abs(float(frame["prices"].max()) - high) > 1e-9:
            raise ValueError(f"dataset range changed for {asset}")
        rows.append({
            "asset": asset, "revision": DATASET_COMMIT, "calendar_rows": len(frame),
            "distinct_price_observations_including_initial": changes,
            "start_date": frame["date"].iloc[0], "end_date": frame["date"].iloc[-1],
            "minimum_price": float(frame["prices"].min()), "maximum_price": float(frame["prices"].max()),
            "raw_start_to_end_return_pct": observed_return,
            "paper_buy_hold_return_pct": 100 * printed_bh,
            "paper_buy_hold_matches_raw_dataset": abs(observed_return - 100 * printed_bh) < 0.05,
            "boundary": "paper range/count matches pinned pre-live dataset; printed B&H return does not",
        })
        if abs(observed_return - raw_return) > 1e-10:
            raise ValueError(f"dataset return changed for {asset}")
    return rows


def dataset_revision_rows(scratch: Path) -> list[dict[str, Any]]:
    """Verify and inventory every official historical dataset payload."""
    import pandas as pd

    repository = scratch / "native/CLEF_Task3_Trading"
    payload_root = scratch / "historical/dataset_revisions"
    printed_returns = {"TSLA": 0.379, "BTC": -0.315}
    output: list[dict[str, Any]] = []
    for asset in ("TSLA", "BTC"):
        relative = f"data/{asset}-00000-of-00001.parquet"
        revisions = [
            line.split("|", 1)
            for line in git_text(
                repository,
                "log",
                "--all",
                "--format=%H|%cI",
                "--",
                relative,
            ).splitlines()
            if line
        ]
        if len(revisions) != 102:
            raise ValueError(f"historical {asset} revision count changed")
        for commit, committed_at in revisions:
            oid, expected_size = lfs_pointer(
                git_bytes(repository, "show", f"{commit}:{relative}")
            )
            path = payload_root / f"{commit}_{asset}.parquet"
            if path.stat().st_size != expected_size or sha256(path) != oid:
                raise ValueError(f"historical dataset payload mismatch: {path.name}")
            frame = pd.read_parquet(path, columns=["date", "prices"])
            dates = frame["date"].astype(str)
            paper_slice = frame[
                dates.between("2025-08-01", DECLARED_OFFLINE_END)
            ]
            values = paper_slice["prices"].astype("<f8").to_numpy()
            observed_return = float(values[-1] / values[0] - 1)
            output.append(
                {
                    "asset": asset,
                    "commit": commit,
                    "committed_at": committed_at,
                    "lfs_sha256": oid,
                    "lfs_bytes": expected_size,
                    "payload_verified_against_lfs_pointer": True,
                    "dataset_rows": len(frame),
                    "dataset_start": str(frame["date"].iloc[0]),
                    "dataset_end": str(frame["date"].iloc[-1]),
                    "declared_period_rows_available": len(paper_slice),
                    "declared_period_price_sha256": sha256_bytes(values.tobytes()),
                    "declared_period_raw_return": observed_return,
                    "fully_covers_declared_period": (
                        str(frame["date"].iloc[-1]) >= DECLARED_OFFLINE_END
                    ),
                    "declared_period_return_matches_printed": (
                        round(observed_return, 3) == printed_returns[asset]
                    ),
                    "recovered_table_baseline_revision": (
                        commit == OFFLINE_BASELINE_REVISIONS[asset]["commit"]
                    ),
                }
            )
    if len(output) != 204:
        raise ValueError("official historical dataset payload census changed")
    for asset in ("TSLA", "BTC"):
        rows = [row for row in output if row["asset"] == asset]
        full = [row for row in rows if row["fully_covers_declared_period"]]
        if (
            len(rows) != 102
            or len(full) != 20
            or len({row["declared_period_price_sha256"] for row in full}) != 1
            or any(row["declared_period_return_matches_printed"] for row in full)
            or sum(row["recovered_table_baseline_revision"] for row in rows) != 1
        ):
            raise ValueError(f"historical dataset lineage boundary changed: {asset}")
    return output


def offline_baseline_reproduction(
    scratch: Path,
) -> list[dict[str, Any]]:
    """Regenerate both seven-cell Buy-and-Hold rows from hidden later snapshots."""
    import numpy as np
    import pandas as pd

    payload_root = scratch / "historical/dataset_revisions"
    printed = {
        "TSLA": (0.379, 0.000, 0.96, 0.318, 0.299, 0.37, 293),
        "BTC": (-0.315, 0.000, -0.68, -0.277, 0.497, 0.49, 294),
    }
    metrics = ("CR", "alpha_BH", "Sharpe", "AR", "MDD", "WR", "N_tr")
    formulas = (
        "last_price / first_price - 1",
        "CR_buy_and_hold - CR_buy_and_hold",
        "mean(simple_daily_return) / sample_sd(simple_daily_return) * sqrt(252)",
        "(last_price / first_price) ** (252 / total_rows) - 1",
        "absolute maximum drawdown of the price index",
        "fraction of N-1 simple daily returns greater than zero",
        "total dataset rows (despite the N_tr label)",
    )
    decimals = (3, 3, 2, 3, 3, 2, 0)
    output: list[dict[str, Any]] = []
    for asset in ("TSLA", "BTC"):
        revision = OFFLINE_BASELINE_REVISIONS[asset]
        path = payload_root / f"{revision['commit']}_{asset}.parquet"
        frame = pd.read_parquet(path, columns=["date", "prices"])
        prices = frame["prices"].astype(float)
        returns = prices.pct_change().dropna()
        cumulative_return = float(prices.iloc[-1] / prices.iloc[0] - 1)
        reproduced = (
            cumulative_return,
            0.0,
            float(returns.mean() / returns.std(ddof=1) * np.sqrt(252)),
            float((1 + cumulative_return) ** (252 / len(frame)) - 1),
            float(-(prices / prices.cummax() - 1).min()),
            float((returns > 0).mean()),
            len(frame),
        )
        table_label = "tab:tsla" if asset == "TSLA" else "tab:btc"
        for column_index, (metric, formula, expected, observed, digits) in enumerate(
            zip(metrics, formulas, printed[asset], reproduced, decimals),
            1,
        ):
            matches = round(float(observed), digits) == round(float(expected), digits)
            output.append(
                {
                    "table_label": table_label,
                    "row_label": "Buy & Hold",
                    "asset": asset,
                    "quantitative_column_index": column_index,
                    "metric": metric,
                    "printed_value": expected,
                    "reproduced_value": observed,
                    "display_decimals": digits,
                    "absolute_difference": abs(float(observed) - float(expected)),
                    "matches_at_display_precision": matches,
                    "formula": formula,
                    "dataset_commit": revision["commit"],
                    "dataset_start": str(frame["date"].iloc[0]),
                    "dataset_end": str(frame["date"].iloc[-1]),
                    "declared_dataset_end": DECLARED_OFFLINE_END,
                    "paper_protocol_period_match": False,
                    "author_native_agent_pipeline_reexecuted": False,
                    "paper_result_credit": False,
                    "verification_class": (
                        "official_history_baseline_cell_regenerated_wrong_declared_endpoint"
                        if matches
                        else "official_history_baseline_cell_mismatch"
                    ),
                }
            )
    if len(output) != 14 or not all(
        row["matches_at_display_precision"] for row in output
    ):
        raise ValueError("historical offline baseline reproduction changed")
    return output


def offline_always_hold_reproduction(
    scratch: Path,
) -> list[dict[str, Any]]:
    """Regenerate both seven-cell Always-HOLD rows from the recovered baseline snapshots."""
    import pandas as pd

    payload_root = scratch / "historical/dataset_revisions"
    printed = {
        "TSLA": (0.000, -0.379, 0.00, 0.000, 0.000, 0.00, 0),
        "BTC": (0.000, 0.315, 0.00, 0.000, 0.000, 0.00, 0),
    }
    metrics = ("CR", "alpha_BH", "Sharpe", "AR", "MDD", "WR", "N_tr")
    formulas = (
        "constant cash portfolio ending at its initial value",
        "zero Always-HOLD return minus recovered Buy-and-Hold return",
        "zero-return convention for the otherwise zero-over-zero Sharpe",
        "constant cash portfolio has zero annualized return",
        "constant cash portfolio has zero drawdown",
        "paper's zero-trade convention reports zero win rate",
        "Always HOLD executes zero trades",
    )
    decimals = (3, 3, 2, 3, 3, 2, 0)
    output: list[dict[str, Any]] = []
    for asset in ("TSLA", "BTC"):
        revision = OFFLINE_BASELINE_REVISIONS[asset]
        path = payload_root / f"{revision['commit']}_{asset}.parquet"
        frame = pd.read_parquet(path, columns=["date", "prices"])
        prices = frame["prices"].astype(float)
        buy_hold_return = float(prices.iloc[-1] / prices.iloc[0] - 1)
        reproduced = (0.0, -buy_hold_return, 0.0, 0.0, 0.0, 0.0, 0)
        table_label = "tab:tsla" if asset == "TSLA" else "tab:btc"
        for column_index, (metric, formula, expected, observed, digits) in enumerate(
            zip(metrics, formulas, printed[asset], reproduced, decimals),
            1,
        ):
            matches = round(float(observed), digits) == round(float(expected), digits)
            output.append(
                {
                    "table_label": table_label,
                    "row_label": "Always HOLD",
                    "asset": asset,
                    "quantitative_column_index": column_index,
                    "metric": metric,
                    "printed_value": expected,
                    "reproduced_value": observed,
                    "display_decimals": digits,
                    "absolute_difference": abs(float(observed) - float(expected)),
                    "matches_at_display_precision": matches,
                    "formula": formula,
                    "dataset_commit": revision["commit"],
                    "dataset_start": str(frame["date"].iloc[0]),
                    "dataset_end": str(frame["date"].iloc[-1]),
                    "declared_dataset_end": DECLARED_OFFLINE_END,
                    "paper_protocol_period_match": False,
                    "author_native_agent_pipeline_reexecuted": False,
                    "paper_result_credit": False,
                    "verification_class": (
                        "official_history_deterministic_hold_baseline_cell_regenerated_"
                        "wrong_declared_endpoint"
                        if matches
                        else "official_history_deterministic_hold_baseline_cell_mismatch"
                    ),
                }
            )
    if len(output) != 14 or not all(
        row["matches_at_display_precision"] for row in output
    ):
        raise ValueError("historical Always-HOLD baseline reproduction changed")
    return output



def release_history_audit(
    scratch: Path,
    revisions: list[dict[str, Any]],
) -> dict[str, Any]:
    repositories = {
        "author_space": scratch / "native/Fin_Analyst",
        "dataset": scratch / "native/CLEF_Task3_Trading",
        "organizer": scratch / "native/Agent-Market-Arena",
    }
    facts = {
        name: repository_history_facts(path)
        for name, path in repositories.items()
    }
    for name, expected in EXPECTED_HISTORY_COUNTS.items():
        observed = facts[name]
        if any(observed[key] != value for key, value in expected.items()):
            raise ValueError(f"{name} full-history census changed: {observed}")

    author_repository = repositories["author_space"]
    pointer = git_bytes(
        author_repository,
        "show",
        f"{AUTHOR_ARCHIVE_COMMIT}:files.zip",
    )
    oid, size = lfs_pointer(pointer)
    if (oid, size) != (AUTHOR_ARCHIVE_LFS_SHA256, AUTHOR_ARCHIVE_BYTES):
        raise ValueError("deleted author archive pointer changed")
    deleted = subprocess.run(
        [
            "git",
            "-C",
            str(author_repository),
            "cat-file",
            "-e",
            f"{AUTHOR_ARCHIVE_DELETION_COMMIT}:files.zip",
        ],
        capture_output=True,
    )
    if deleted.returncode == 0:
        raise ValueError("historical author archive is no longer deleted at the pin")
    archive_path = scratch / "historical/files-5c7db3f.zip"
    if archive_path.stat().st_size != size or sha256(archive_path) != oid:
        raise ValueError("deleted author archive payload does not match LFS pointer")
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if any(
            PurePosixPath(name).is_absolute()
            or ".." in PurePosixPath(name).parts
            for name in names
        ):
            raise ValueError("unsafe deleted author archive member")
        member_rows = [
            {
                "path": member.filename,
                "bytes": member.file_size,
                "sha256": sha256_bytes(archive.read(member)),
            }
            for member in members
            if not member.is_dir()
        ]
    if names != ["app.py", "Dockerfile", "requirements.txt", "README.md"]:
        raise ValueError(f"deleted author archive inventory changed: {names}")
    if sum(row["bytes"] for row in member_rows) != 26_747:
        raise ValueError("deleted author archive uncompressed size changed")

    full_by_asset = {
        asset: [
            row
            for row in revisions
            if row["asset"] == asset and row["fully_covers_declared_period"]
        ]
        for asset in ("TSLA", "BTC")
    }
    recovered_rows = {
        row["asset"]: row for row in revisions if row["recovered_table_baseline_revision"]
    }
    if git_bytes(
        repositories["organizer"],
        "show",
        f"{ARENA_COMMIT}:public/data/asset_requests.json",
    ).strip() != b"[]":
        raise ValueError("organizer's sole historical data JSON changed")
    primitive_suffixes = {".csv", ".parquet", ".jsonl", ".db", ".sqlite", ".pkl", ".zip"}
    primitive_paths = [
        path
        for path in facts["organizer"]["historical_paths"]
        if PurePosixPath(path).suffix.lower() in primitive_suffixes
    ]
    if primitive_paths:
        raise ValueError(
            f"organizer history gained primitive decision/result candidates: {primitive_paths}"
        )
    return {
        "author_space": {
            **{key: facts["author_space"][key] for key in ("commits", "objects", "paths", "unique_ref_heads")},
            "deleted_lfs_archive_commit": AUTHOR_ARCHIVE_COMMIT,
            "deleted_lfs_archive_deletion_commit": AUTHOR_ARCHIVE_DELETION_COMMIT,
            "deleted_lfs_archive_sha256": oid,
            "deleted_lfs_archive_bytes": size,
            "deleted_lfs_archive_members": member_rows,
            "deleted_lfs_archive_contains_decisions_or_results": False,
        },
        "dataset": {
            **{key: facts["dataset"][key] for key in ("commits", "objects", "paths", "unique_ref_heads")},
            "historical_paths": facts["dataset"]["historical_paths"],
            "lfs_payload_revisions": len(revisions),
            "lfs_payloads_verified": sum(
                row["payload_verified_against_lfs_pointer"] for row in revisions
            ),
            "fully_covering_declared_period_revisions_per_asset": {
                asset: len(rows) for asset, rows in full_by_asset.items()
            },
            "unique_declared_period_price_paths_among_full_revisions": {
                asset: len({row["declared_period_price_sha256"] for row in rows})
                for asset, rows in full_by_asset.items()
            },
            "full_declared_period_revisions_matching_printed_return": {
                asset: sum(row["declared_period_return_matches_printed"] for row in rows)
                for asset, rows in full_by_asset.items()
            },
            "recovered_table_baseline_revisions": {
                asset: {
                    "commit": row["commit"],
                    "dataset_rows": row["dataset_rows"],
                    "dataset_end": row["dataset_end"],
                }
                for asset, row in recovered_rows.items()
            },
            "historical_action_or_result_paths": 0,
        },
        "organizer": {
            **{key: facts["organizer"][key] for key in ("commits", "objects", "paths", "unique_ref_heads")},
            "historical_database_contents_in_git": False,
            "historical_primitive_decision_or_result_paths": 0,
            "sole_data_json": "public/data/asset_requests.json",
            "sole_data_json_value": [],
        },
        "paper_result_credit": False,
    }


def official_decision_rows(scratch: Path, asset: str) -> list[dict[str, Any]]:
    snapshot_path = scratch / "discovery/arena-fin-analyst-rows.json"
    if sha256(snapshot_path) != PINS["discovery/arena-fin-analyst-rows.json"]:
        raise ValueError("official organizer decision snapshot changed")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    rows = sorted(
        (
            row
            for row in snapshot
            if row.get("agent_name") == "Fin_Analyst"
            and row.get("asset") == asset
        ),
        key=lambda row: row["date"],
    )
    expected_raw = 47 if asset == "TSLA" else 55
    if len(rows) != expected_raw:
        raise ValueError(f"official {asset} decision count changed")
    return rows if asset == "TSLA" else rows[:50]


def native_organizer_scorer_execution(
    scratch: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    repository = scratch / "native/Agent-Market-Arena"
    perf_path = repository / "src/lib/perf.js"
    decisions_path = scratch / "discovery/arena-fin-analyst-rows.json"
    if git_text(repository, "rev-parse", "HEAD") != ARENA_COMMIT:
        raise ValueError("organizer checkout is not pinned to the scorer commit")
    if sha256(perf_path) != ORGANIZER_PERF_SHA256:
        raise ValueError("organizer perf.js source changed")
    if not ORGANIZER_RUNNER.exists():
        raise ValueError("native organizer scorer runner is absent")
    if sha256(ORGANIZER_RUNNER) != ORGANIZER_RUNNER_SHA256:
        raise ValueError("native organizer scorer runner changed")

    with tempfile.TemporaryDirectory() as temporary_directory:
        output_path = Path(temporary_directory) / "native-organizer.json"
        completed = subprocess.run(
            [
                "node",
                str(ORGANIZER_RUNNER),
                "--source",
                str(perf_path),
                "--decisions",
                str(decisions_path),
                "--source-commit",
                ARENA_COMMIT,
                "--output",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    if completed.stdout or completed.stderr:
        raise ValueError("native organizer scorer emitted unexpected output")
    if (
        payload["source_commit"] != ARENA_COMMIT
        or payload["source_sha256"] != ORGANIZER_PERF_SHA256
        or payload["decision_snapshot_sha256"]
        != PINS["discovery/arena-fin-analyst-rows.json"]
        or payload["decision_snapshot_rows"] != 102
        or payload["selected_decision_rows"] != 97
        or payload["excluded_post_window_btc_rows"] != 5
        or payload["runtime"]
        != {"node": "v20.13.1", "platform": "linux", "architecture": "x64"}
        or payload["network_calls"] != 0
        or set(payload["results"]) != {"TSLA", "BTC"}
    ):
        raise ValueError("native organizer scorer provenance changed")

    rows: list[dict[str, Any]] = []
    for asset in ("TSLA", "BTC"):
        selected = official_decision_rows(scratch, asset)
        saved = json.loads(
            (scratch / f"replay/{asset}.json").read_text(encoding="utf-8")
        )
        current = payload["results"][asset]
        arrays = {
            "equity_with_fees": "eq",
            "equity_without_fees": "eq0",
            "buy_and_hold_equity": "bh",
        }
        array_exact = {
            name: current[name] == saved[saved_name]
            for name, saved_name in arrays.items()
        }
        metrics_with_fees_exact = current["metrics_with_fees"] == saved["metrics"]
        metrics_without_fees_exact = (
            current["metrics_without_fees"] == saved["metrics0"]
        )
        win_rate_exact = current["win_rate"] == saved["wr"]
        decisions_exact = selected == saved["rows"]
        all_exact = (
            decisions_exact
            and all(array_exact.values())
            and metrics_with_fees_exact
            and metrics_without_fees_exact
            and win_rate_exact
        )
        rows.append(
            {
                "asset": asset,
                "raw_snapshot_asset_rows": 47 if asset == "TSLA" else 55,
                "selected_paper_window_rows": len(selected),
                "excluded_post_window_rows": 0 if asset == "TSLA" else 5,
                "selected_rows_match_saved_replay_rows": decisions_exact,
                "equity_with_fees_points": len(current["equity_with_fees"]),
                "equity_without_fees_points": len(
                    current["equity_without_fees"]
                ),
                "buy_and_hold_equity_points": len(
                    current["buy_and_hold_equity"]
                ),
                "equity_with_fees_exact": array_exact["equity_with_fees"],
                "equity_without_fees_exact": array_exact[
                    "equity_without_fees"
                ],
                "buy_and_hold_equity_exact": array_exact[
                    "buy_and_hold_equity"
                ],
                "five_metrics_with_fees_exact": metrics_with_fees_exact,
                "five_metrics_without_fees_exact": metrics_without_fees_exact,
                "win_rate_and_trade_count_exact": win_rate_exact,
                "all_native_scorer_outputs_exact": all_exact,
                "published_cells_verified_via_native_scorer": (
                    2 if asset == "TSLA" else 3
                ),
                "author_native_decision_pipeline_reexecuted": False,
                "paper_result_credit": False,
            }
        )
    if (
        len(rows) != 2
        or not all(row["all_native_scorer_outputs_exact"] for row in rows)
        or sum(
            row["published_cells_verified_via_native_scorer"] for row in rows
        )
        != 5
    ):
        raise ValueError("native organizer scorer conformance changed")
    payload["runner_path"] = "scripts/run_fin_analyst_organizer_scorer.mjs"
    payload["runner_sha256"] = ORGANIZER_RUNNER_SHA256
    payload["conformance"] = {
        "assets_executed": 2,
        "selected_official_decision_rows": 97,
        "equity_arrays_exact": 6,
        "equity_points_exact": 291,
        "metric_scalars_exact": 20,
        "win_rate_trade_scalars_exact": 4,
        "published_cells_verified_via_native_scorer": 5,
        "author_native_decision_pipeline_reexecuted": False,
        "paper_result_credit": False,
    }
    return payload, rows


def replay_rows(
    scratch: Path,
    organizer_execution: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    paper = {
        "TSLA": {"return": 13.51, "alpha": 28.33, "sharpe": 4.10, "win": 88.0, "rank": "1st / gold"},
        "BTC": {"return": -5.30, "alpha": 17.63, "sharpe": -1.09, "win": 36.0, "rank": "13th"},
    }
    if organizer_execution is None:
        organizer_execution = native_organizer_scorer_execution(scratch)[0]
    rows = []
    for asset in ("TSLA", "BTC"):
        decisions = official_decision_rows(scratch, asset)
        current = organizer_execution["results"][asset]
        metrics = current["metrics_with_fees"]
        buy_and_hold = current["buy_and_hold_equity"]
        bh = 100 * (buy_and_hold[-1] / buy_and_hold[0] - 1)
        alpha = metrics["total_return"] - bh
        wr = current["win_rate"]
        rows.append({
            "asset": asset, "decision_rows": len(decisions),
            "window_start": decisions[0]["date"], "window_end": decisions[-1]["date"],
            "paper_return_pct": paper[asset]["return"], "organizer_replay_return_pct": metrics["total_return"],
            "paper_vs_buy_hold_pp": paper[asset]["alpha"], "organizer_replay_vs_buy_hold_pp": alpha,
            "paper_sharpe": paper[asset]["sharpe"], "organizer_replay_sharpe": metrics["sharpe_ratio"],
            "paper_win_rate_pct": paper[asset]["win"], "organizer_replay_win_rate_pct": wr["winRate"],
            "organizer_replay_trade_count": wr["trades"], "paper_rank": paper[asset]["rank"],
            "organizer_native_scorer_executed": True,
            "organizer_native_scorer_source_sha256": ORGANIZER_PERF_SHA256,
            "organizer_native_scorer_network_calls": 0,
            "historical_rank_reproducible": False,
            "all_printed_live_metrics_match": False,
            "boundary": "official decisions + exact pinned organizer perf.js execution; action-generation LLM calls not rerun",
        })
    return rows


def error_attribution_replay(
    scratch: Path,
    organizer_execution: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Replay the paper's day-level Table 7 statistics from official decisions."""
    if organizer_execution is None:
        organizer_execution = native_organizer_scorer_execution(scratch)[0]
    paper = {
        "TSLA": {
            "Final return (net of fees)": (13.51,),
            "Acted days / exposure": (19.0, 33.0, 58.0),
            "Hit rate (acted days)": (0.632,),
            "Long days: hit / total PnL": (0.75, -1.55),
            "Short days: hit / total PnL": (0.60, 15.17),
            "Max equity drawdown": (-6.1,),
        },
        "BTC": {
            "Final return (net of fees)": (-5.30,),
            "Acted days / exposure": (31.0, 50.0, 62.0),
            "Hit rate (acted days)": (0.387,),
            "Long days: hit / total PnL": (0.17, -6.50),
            "Short days: hit / total PnL": (0.44, 7.71),
            "Max equity drawdown": (-11.1,),
        },
    }
    output: list[dict[str, Any]] = []
    for asset in ("TSLA", "BTC"):
        decisions = official_decision_rows(scratch, asset)
        scorer = organizer_execution["results"][asset]["metrics_with_fees"]
        if asset == "TSLA":
            observations = [row for row in decisions if row["trade_day"]]
            transitions = observations[:-1]
            evaluated = []
            for index, row in enumerate(transitions):
                move = float(observations[index + 1]["price"]) / float(row["price"]) - 1
                action = str(row["recommended_action"]).upper()
                # The paper's 19 acted opportunities exclude the one exactly-flat
                # TSLA next move; its denominator is the 33 observable transitions.
                if action in {"BUY", "SELL"} and abs(move) > 1e-15:
                    evaluated.append((action, move))
            exposure_numerator = len(evaluated)
            exposure_denominator = len(transitions)
            action_denominators = {
                action: sum(item[0] == action for item in evaluated)
                for action in ("BUY", "SELL")
            }
        else:
            observations = decisions
            transitions = observations[:-1]
            evaluated = []
            for index, row in enumerate(transitions):
                move = float(observations[index + 1]["price"]) / float(row["price"]) - 1
                action = str(row["recommended_action"]).upper()
                if action in {"BUY", "SELL"}:
                    evaluated.append((action, move))
            # The printed BTC exposure includes the final action although no
            # within-window next move exists. It consequently counts as no hit.
            exposure_numerator = sum(
                str(row["recommended_action"]).upper() in {"BUY", "SELL"}
                for row in observations
            )
            exposure_denominator = len(observations)
            action_denominators = {
                action: sum(
                    str(row["recommended_action"]).upper() == action for row in observations
                )
                for action in ("BUY", "SELL")
            }

        hits = {
            "BUY": sum(action == "BUY" and move > 0 for action, move in evaluated),
            "SELL": sum(action == "SELL" and move < 0 for action, move in evaluated),
        }
        pnl = {
            "BUY": 100 * sum(move for action, move in evaluated if action == "BUY"),
            "SELL": -100 * sum(move for action, move in evaluated if action == "SELL"),
        }
        replay_values = {
            "Final return (net of fees)": (float(scorer["total_return"]),),
            "Acted days / exposure": (
                float(exposure_numerator),
                float(exposure_denominator),
                float(round(100 * exposure_numerator / exposure_denominator)),
            ),
            "Hit rate (acted days)": (
                (hits["BUY"] + hits["SELL"]) / exposure_numerator,
            ),
            "Long days: hit / total PnL": (
                hits["BUY"] / action_denominators["BUY"],
                pnl["BUY"],
            ),
            "Short days: hit / total PnL": (
                hits["SELL"] / action_denominators["SELL"],
                pnl["SELL"],
            ),
            "Max equity drawdown": (float(scorer["max_drawdown"]),),
        }
        decimals = {
            "Final return (net of fees)": (2,),
            "Acted days / exposure": (0, 0, 0),
            "Hit rate (acted days)": (3,),
            "Long days: hit / total PnL": (2, 2),
            "Short days: hit / total PnL": (2, 2),
            "Max equity drawdown": (1,),
        }
        for row_label, paper_values in paper[asset].items():
            replay_values_row = replay_values[row_label]
            component_matches = [
                round(observed, places) == expected
                for observed, expected, places in zip(
                    replay_values_row, paper_values, decimals[row_label]
                )
            ]
            output.append({
                "row_label": row_label,
                "asset": asset,
                "paper_components": json.dumps(paper_values),
                "organizer_replay_components": json.dumps(replay_values_row),
                "matching_components": sum(component_matches),
                "total_components": len(component_matches),
                "full_printed_cell_match": all(component_matches),
                "author_native_decision_pipeline_reexecuted": False,
                "organizer_native_scorer_executed": True,
                "verification_class": (
                    "official_decision_and_native_organizer_scorer_verification"
                    if all(component_matches)
                    else "partial_component_match_not_full_printed_cell"
                    if any(component_matches)
                    else "organizer_output_conflict"
                ),
                "paper_result_credit": False,
            })
    if len(output) != 12:
        raise ValueError("Fin-Analyst error-attribution denominator changed")
    exact = {(row["row_label"], row["asset"]) for row in output if row["full_printed_cell_match"]}
    expected_exact = {
        ("Acted days / exposure", "TSLA"),
        ("Acted days / exposure", "BTC"),
        ("Hit rate (acted days)", "TSLA"),
        ("Hit rate (acted days)", "BTC"),
        ("Max equity drawdown", "BTC"),
    }
    if exact != expected_exact:
        raise ValueError(f"Fin-Analyst Table 7 exact replay set changed: {exact}")
    return output


def figure_rows(
    scratch: Path,
    organizer_execution: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if organizer_execution is None:
        organizer_execution = native_organizer_scorer_execution(scratch)[0]
    values = {}
    for asset, paper_agent, paper_buy_hold in (
        ("TSLA", 113326.0, 85313.0),
        ("BTC", 99906.0, 73708.0),
    ):
        decisions = official_decision_rows(scratch, asset)
        raw_buy_hold = (
            100000 * float(decisions[-1]["price"]) / float(decisions[0]["price"])
        )
        values[asset] = (
            paper_agent,
            paper_buy_hold,
            organizer_execution["results"][asset]["equity_with_fees"][-1],
            raw_buy_hold,
            organizer_execution["results"][asset]["buy_and_hold_equity"][-1],
        )
    rows = [{
        "figure": "Figure 1", "panel": "architecture", "empirical": False,
        "source_asset_sha256": "7498eb4bb7139482bca56df56f0b5efb19b3adbb2b057f0e13199a24225f04a0",
        "full_panel_regenerated": False, "exact_displayed_endpoint_annotations_verified": "not_applicable",
        "boundary": "conceptual diagram",
    }]
    for asset, (
        paper_agent,
        paper_bh,
        replay_agent,
        raw_bh,
        native_bh,
    ) in values.items():
        rows.append({
            "figure": "Figure 2", "panel": asset, "empirical": True,
            "source_asset_sha256": "394e57057eaee99b2002a8dea8438c8df9ce31ddc2bfdfc43362727de7e50baf",
            "paper_agent_endpoint": paper_agent, "organizer_replay_agent_endpoint": replay_agent,
            "paper_buy_hold_endpoint": paper_bh, "raw_price_ratio_buy_hold_endpoint": raw_bh,
            "organizer_native_buy_hold_endpoint": native_bh,
            "agent_endpoint_matches": abs(paper_agent - replay_agent) < 0.5,
            "buy_hold_endpoint_matches_rounding": round(raw_bh) == round(paper_bh),
            "organizer_native_buy_hold_matches_rounding": (
                round(native_bh) == round(paper_bh)
            ),
            "full_panel_regenerated": False,
            "exact_displayed_endpoint_annotations_verified": "1/2",
            "boundary": "raw price-ratio Buy-and-Hold endpoint verifies; exact native organizer Buy-and-Hold includes fees/slippage and does not; agent curve/end also conflicts",
        })
    return rows


def native_execution(scratch: Path) -> dict[str, Any]:
    source = scratch / "native/Fin_Analyst"
    if not NATIVE_ENV.exists():
        raise ValueError(f"native audit environment absent: {NATIVE_ENV}")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update({"DATA_DIR": str(source), "OPENAI_API_KEY": "audit-dummy-never-called"})
    check = subprocess.run(
        [str(NATIVE_ENV / "bin/python"), "-m", "pip", "check"],
        env=env, check=True, capture_output=True, text=True,
    )
    compile_result = subprocess.run(
        [str(NATIVE_ENV / "bin/python"), "-m", "py_compile", "app.py"],
        cwd=source, env=env, check=True, capture_output=True, text=True,
    )
    harness = r'''
import asyncio, json
import app
app.load_all()
def btc(score, momentum, history):
    app.get_fear_greed = (lambda: (score, "fixture")) if score is not None else (lambda: (None, None))
    return app.decide_btc(momentum, {"BTC": [{"price": x} for x in history]})
result = {
    "btc_three_hold_case": btc(50, "neutral", [100, 100]),
    "btc_missing_fear_greed_case": btc(None, "bearish", [100, 100]),
    "btc_unanimous_buy_control": btc(70, "bullish", [100, 101]),
}
calls = []
def fake(system, user, max_tokens=120, use_cache=True):
    calls.append({"max_tokens": max_tokens, "use_cache": use_cache})
    return {"action": "SELL", "confidence": 0.7, "reasoning": "fixture"}
app.call_llm = fake
response = asyncio.run(app.predict({
    "symbol": ["TSLA"], "date": "2026-05-11", "price": {"TSLA": 445.08},
    "news": {"TSLA": "negative fixture"}, "momentum": {"TSLA": "bearish"},
    "history_price": {"TSLA": [{"price": 445.08}]}, "10k": ["ignored"], "10q": ["ignored"],
}))
result["tsla_endpoint"] = {
    "response": response, "llm_call_seams_exercised": len(calls),
    "token_caps": [item["max_tokens"] for item in calls],
    "memory_counts": {key: len(value) for key, value in app.sigs.items()},
    "ta_rows": len(app.ta_data),
}
print(json.dumps(result, sort_keys=True))
'''
    run = subprocess.run(
        [str(NATIVE_ENV / "bin/python"), "-c", harness], cwd=source, env=env,
        check=True, capture_output=True, text=True,
    )
    result = json.loads(run.stdout.strip().splitlines()[-1])
    expected_memory = {"8k": 12, "10q": 3, "10k": 2, "compustat": 29, "ibes": 14, "wsb": 5721}
    if result["tsla_endpoint"]["memory_counts"] != expected_memory:
        raise ValueError("native startup memory counts changed")
    if result["tsla_endpoint"]["llm_call_seams_exercised"] != 8:
        raise ValueError("native TSLA controlled call count changed")
    if result["btc_three_hold_case"][0] != "BUY" or "H=3" not in result["btc_three_hold_case"][1]:
        raise ValueError("documented BTC all-HOLD defect changed")
    if "S=2" not in result["btc_missing_fear_greed_case"][1]:
        raise ValueError("documented BTC duplicate-momentum defect changed")
    return {
        "author_commit": AUTHOR_COMMIT,
        "native_environment_python": "3.12 audit reconstruction; author Dockerfile specifies mutable python:3.11-slim",
        "author_requirements_are_lower_bounds_not_a_lock": True,
        "pip_check_passed": check.stdout.strip() == "No broken requirements found.",
        "app_py_compiles": compile_result.returncode == 0,
        "paid_or_external_model_calls": 0,
        "external_fear_greed_calls": 0,
        "controlled_execution": result,
        "native_components_executed": ["startup loaders", "seven corpus paths", "TSLA /predict router", "eight LLM call seams", "BTC voting", "endpoint exception boundary"],
        "author_native_paper_actions_regenerated": 0,
        "published_table_cells_regenerated": 0,
        "strict_success": False,
    }


def method_rows() -> list[dict[str, str]]:
    values = (
        ("official paper and source", "complete", "single 13-page arXiv-v1 PDF and nine-file source archive pinned; all official/rebuilt pages visually checked"),
        ("author implementation", "substantial_pre_live_R3", "complete five-commit first-author Space history, 12 unique paths, Docker runner, requirements and seven corpora; the deleted four-file LFS archive is source-only"),
        ("license", "absent", "no license file or declared license observed in author Space"),
        ("dependency environment", "unlocked", "python:3.11-slim plus six lower-bounded requirements; no exact lock or image digest"),
        ("model", "mutable_alias", "gpt-4o-mini, temperature .1, JSON mode, token caps; no dated snapshot, seed, request IDs, or responses"),
        ("paper prompts", "abridged", "nine paper rows correspond to source constants but are not the full byte-identical prompts despite the full-prompts label"),
        ("TSLA runtime", "native_controlled", "startup, lookups, router, and eight call seams execute under deterministic model stubs; no paid model call"),
        ("BTC runtime", "native_controlled_with_defects", "native vote runs; three HOLD votes become BUY and missing Fear & Greed duplicates momentum"),
        ("persistent corpora", "complete_static_snapshot", "7/7 files load, 6,030 JSONL records plus 249 TA rows"),
        ("live freshness", "partial", "TA stops 2025-12-30 and WSB stops 2026-04-12 before May-June live evaluation"),
        ("official live decisions", "recovered", "97 paper-window rows: 47 TSLA and 50 BTC, from organizer public database snapshot"),
        (
            "organizer scoring",
            "native_exact_current",
            "exact pinned perf.js executes 97 official rows with 6-bp fees and 10-bp execution slippage; six equity arrays and 24 scalar outputs match the stored replay exactly",
        ),
        ("live result reproduction", "partial_output_verification", "headline return/alpha/Sharpe/win cells conflict, but five Table 7 cells reproduce from the official decisions and pinned organizer output"),
        ("offline dataset", "complete_103_commit_history", "all 204 TSLA/BTC LFS payloads verify; the 20 revisions per asset covering the declared May-10 endpoint share one identical period path that conflicts with both printed returns"),
        ("offline actions", "missing_after_full_history_search", "all 435 author/dataset/organizer commits contain no Random generator, seed-42 implementation, exact offline table identifier, or backtest generator; momentum source hits are limited to the live app and input documentation"),
        ("offline results", "deterministic_baselines_only_recovered_from_mislabeled_period", "all 28 Buy-and-Hold and Always-HOLD cells regenerate from asset-specific May-20/May-21 dataset endpoints, not the paper's declared May-10 endpoint; random, momentum, agent, and ablation paths remain absent"),
        ("cost model", "paper_partial_source_current", "paper says net of fees but omits full implementation; current organizer source uses 6-bp fees plus 10-bp slippage"),
        ("rank provenance", "not_recoverable", "current dynamic leaderboard cannot prove historical ranks as displayed on 2026-07-05"),
        ("statistical inference", "absent", "paper explicitly reports no significance testing"),
    )
    return [{"dimension": a, "status": b, "evidence": c} for a, b, c in values]


def consistency_rows() -> list[dict[str, str]]:
    values = (
        ("btc_live_table_vs_figure", "major_numeric_conflict", "table reports -5.30%, but Figure 2 ends at $99,906 (~-0.09%) and prose says essentially flat"),
        ("btc_live_table_vs_discussion", "major_numeric_conflict", "table alpha is +17.63pp, while discussion reports +26.2pp and B&H down 26.3%, consistent with the figure/raw price ratio"),
        ("btc_live_table_vs_official_replay", "major_numeric_conflict", "97-row official-log window plus pinned organizer scorer yields -0.0976%, Sharpe 0.108, win rate 40%, not -5.30%, -1.09, 36%"),
        ("tsla_live_table_vs_official_replay", "major_numeric_conflict", "official actions plus pinned scorer yield +4.791%, Sharpe 1.578, win rate 45%, not +13.51%, 4.10, 88%"),
        ("figure_buy_hold_lineage", "verified_component", "raw first/last price ratios round exactly to $85,313 TSLA and $73,708 BTC figure endpoints"),
        ("figure_agent_lineage", "not_reproduced", "official actions/current scorer end at $104,623 TSLA and $99,743 BTC rather than $113,326 and $99,906"),
        ("offline_buy_hold_tsla", "major_numeric_conflict", "pinned pre-live dataset raw return is +41.542%, not printed +37.9%"),
        ("offline_buy_hold_btc", "major_numeric_conflict", "pinned pre-live dataset raw return is -27.517%, not printed -31.5%"),
        ("btc_all_hold_majority", "source_method_conflict", "paper says final action is majority of three votes; source converts B=0,S=0,H=3 to BUY because it tests B==S only"),
        ("btc_missing_fear_greed", "source_method_conflict", "when endpoint fails, source adds the momentum vote in the fallback and then adds it again unconditionally"),
        ("fear_greed_interpretation", "narrative_rule_tension", "paper calls extreme fear a long opportunity but maps scores <=40 to SELL"),
        ("full_prompts_claim", "specification_conflict", "appendix says full prompts, but all nine rows are abridged versions of the released native constants"),
        ("live_error_attribution_denominators", "mixed_conventions_exactly_replayed", "TSLA uses 33 observable market-session transitions and excludes one zero next move; BTC counts all 50 rows including its terminal action with no within-window next move. These distinct conventions reproduce both printed exposure and hit-rate cells but are not one uniform rule."),
        ("declared_offline_period_vs_table_lineage", "major_protocol_conflict", "all 20 official revisions per asset covering the declared May-10 endpoint have identical period prices and yield +41.542% TSLA/-27.517% BTC, not +37.9%/-31.5%"),
        ("offline_baseline_mixed_asset_endpoints", "exact_hidden_lineage_recovered", "all 14 TSLA Buy-and-Hold and Always-HOLD cells require the May-20 endpoint, while all 14 BTC cells require May-21; both are later than the common May-10 period printed in the paper"),
        ("offline_ntr_semantics", "label_and_protocol_conflict", "the displayed N_tr values 293/294 equal total calendar rows in the recovered later snapshots, exceed the declared 283 calendar rows and 194 TSLA trading days, and are not an executed-trade count"),
        ("mutable_model_replay", "irrecoverable_exactness", "gpt-4o-mini alias, SDK/image dependencies, requests/responses, cache state, and API seed are not frozen"),
    )
    return [{"check": a, "status": b, "detail": c} for a, b, c in values]


def release_rows() -> list[dict[str, Any]]:
    values = (
        ("paper/arXiv exact GitHub search", "no repository", "bounded search result pinned; negative search is not proof of absence", False),
        ("first-author Hugging Face Space", AUTHOR_SPACE, f"all five commits and 12 paths audited; deleted LFS payload recovered; pinned {AUTHOR_COMMIT}", True),
        ("organizer dataset", DATASET_URL, f"all 103 commits, four paths and 204 LFS payload revisions audited; pre-live dataset pin {DATASET_COMMIT}", True),
        ("organizer arena", ARENA_SPACE, f"all 327 commits, 104 paths and two unique ref heads audited; scorer pin {ARENA_COMMIT}; public database snapshot separately hashed", True),
    )
    return [{"search_or_artifact": a, "result": b, "boundary": c, "attributable_or_official": d} for a, b, c, d in values]


def build(scratch: Path, output: Path) -> None:
    verify_pins(scratch)
    files = paper_sources(scratch)
    source = files["fin_mm_eval_working_notes.tex"].decode()
    app_source = (scratch / "native/Fin_Analyst/app.py").read_text()
    overlap = token_jaccard(
        (scratch / "primary/official-v1.txt").read_text(errors="replace"),
        (scratch / "primary/rebuilt-v1.txt").read_text(errors="replace"),
    )
    if overlap < 0.999:
        raise ValueError(f"source rebuild overlap regressed: {overlap}")
    dataset_revisions = dataset_revision_rows(scratch)
    baseline_replay = [
        *offline_baseline_reproduction(scratch),
        *offline_always_hold_reproduction(scratch),
    ]
    baseline_search = offline_baseline_generator_search(scratch)
    history = release_history_audit(scratch, dataset_revisions)
    organizer_execution, organizer_conformance = (
        native_organizer_scorer_execution(scratch)
    )
    error_replay = error_attribution_replay(scratch, organizer_execution)
    tables = result_rows(source, error_replay, baseline_replay)
    prompts = prompt_rows(source, app_source)
    corpora = corpus_rows(scratch)
    datasets = dataset_rows(scratch)
    replays = replay_rows(scratch, organizer_execution)
    figures = figure_rows(scratch, organizer_execution)
    execution = native_execution(scratch)
    execution["organizer_native_scorer"] = organizer_execution["conformance"]
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "published_result_ledger.csv", tables)
    write_csv(output / "prompt_correspondence.csv", prompts)
    write_csv(output / "native_corpus_inventory.csv", corpora)
    write_csv(output / "offline_dataset_audit.csv", datasets)
    write_csv(output / "live_result_replay.csv", replays)
    write_csv(output / "dataset_revision_lineage.csv", dataset_revisions)
    write_csv(output / "offline_baseline_reproduction.csv", baseline_replay)
    write_csv(output / "offline_baseline_generator_search.csv", baseline_search)
    write_json(output / "release_history_audit.json", history)
    write_csv(output / "error_attribution_replay.csv", error_replay)
    write_csv(
        output / "organizer_native_scorer_conformance.csv",
        organizer_conformance,
    )
    write_json(
        output / "organizer_native_scorer_execution.json",
        organizer_execution,
    )
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "internal_consistency_audit.csv", consistency_rows())
    write_csv(output / "release_search_audit.csv", release_rows())
    write_json(output / "native_execution.json", execution)
    provenance = {
        "work_id": WORK_ID, "system_id": SYSTEM_ID, "arxiv_id": ARXIV_ID,
        "paper_version": "v1 (2026-07-14)", "official_pages": 13, "rebuilt_pages": 13,
        "source_files": len(files), "official_rebuilt_token_jaccard": overlap,
        "all_official_and_rebuilt_pages_visually_checked": True,
        "paper_source_sha256": {name: sha256_bytes(value) for name, value in sorted(files.items())},
        "author_space": {"url": AUTHOR_SPACE, "commit": AUTHOR_COMMIT, "tracked_files": 13, "license": "NOASSERTION"},
        "dataset": {"url": DATASET_URL, "pre_live_commit": DATASET_COMMIT},
        "organizer": {
            "url": ARENA_SPACE,
            "source_commit": ARENA_COMMIT,
            "scorer_path": "src/lib/perf.js",
            "scorer_sha256": ORGANIZER_PERF_SHA256,
            "decision_snapshot_sha256": PINS[
                "discovery/arena-fin-analyst-rows.json"
            ],
            "native_scorer_executed": True,
        },
        "negative_search_boundary": "bounded searches do not prove private, deleted, moved, renamed, or unindexed artifacts never existed",
    }
    write_json(output / "source_provenance.json", provenance)
    readme = """# Fin-Analyst paper-faithfulness audit

This audit uses the official 13-page arXiv-v1 paper and source, the complete five-commit first-author Space history, every one of the official dataset's 103 commits and 204 LFS payload revisions, all 327 organizer commits, and a pinned public per-day decision log. The unmodified source rebuild reaches 99.96% extracted-token overlap; all official and rebuilt pages were visually checked.

The paper has **119 displayed empirical table cells** and **two empirical figure panels**. The attributable R3 deployment materially improves source-level fidelity: its Docker/FastAPI runner, nine native prompts, seven corpora, TSLA routing, BTC vote and failure behavior are inspectable. A dependency-isolated controlled run loads all corpora and exercises the native endpoint and voting paths without paid or external model calls. The public organizer log recovers 97 paper-window decisions. The exact pinned src/lib/perf.js scorer now executes those raw rows with zero network calls: all six with-fee/no-fee/Buy-and-Hold equity arrays (291 points), 20 metric values, and four win-rate/trade scalars match the prior replay exactly.

That evidence does **not** reproduce the headline empirical claims or the LLM action-generation pipeline. **Thirty-three of 119 printed cells regenerate exactly:** five live error-attribution cells from official decisions and exact native organizer scoring, plus all 28 cells in the Buy-and-Hold and deterministic Always-HOLD rows. The baseline lineage exposes a major protocol conflict: both TSLA rows require the official May-21 revision ending May 20, while both BTC rows require the May-22 revision ending May 21; the paper declares one common May-10 endpoint. All 20 official revisions per asset that fully cover the declared period contain one identical May-10 price path, and none matches the printed Buy-and-Hold return or the Always-HOLD alpha derived from it. The Buy-and-Hold N_tr values 293/294 are total rows of the later snapshots, not trades under the stated daily protocol; Always HOLD correctly yields zero trades. The four composite live hit/PnL cells recover their hit-rate components but not their PnL components. Zero of two full empirical panels regenerate. Current official decisions still yield TSLA +4.79%/Sharpe 1.58/45% rather than +13.51%/4.10/88%, while BTC replays essentially flat (-0.10%) rather than the table's -5.30%.

Native inspection also finds method-level defects. Three BTC HOLD votes become BUY because the code compares only BUY and SELL counts; a failed Fear & Greed request double-counts momentum. All nine appendix prompt rows are abridged relative to the released constants despite being labeled full prompts. The deleted first-author LFS ZIP is recoverable but contains only four source files already represented in the surviving release. The complete dataset and organizer histories add no action, ablation, cache, database, or result artifact. The model alias, API calls, cache state, image, SDK and dependencies are not immutably frozen, and the released TA and WSB corpora are stale before the live window ends.

A full-history generator census searches all 435 reachable author, dataset, and organizer commits. It finds zero source-level Random sampling calls, seed-42 implementations, exact offline table identifiers, or backtest generators. Momentum appears only in the live app and input schema/examples; bundled corpus mentions receive no implementation credit. The Random and Momentum rows therefore remain unrecoverable rather than being guessed from their labels.

Therefore `strict_success` is false. This is strong source, baseline and output-lineage recovery, not an end-to-end Fin-Analyst regeneration. The empirical record is materially closer than a paper-only proxy, but its four deterministic baseline rows reproduce only under asset-specific endpoints that contradict the paper, and no native agent, random/momentum baseline, or ablation result is regenerated.
"""
    (output / "README.md").write_text(readme)
    generated_names = [path.name for path in output.iterdir() if path.name != "manifest.json"]
    manifest = {
        "work_id": WORK_ID, "system_id": SYSTEM_ID, "arxiv_id": ARXIV_ID,
        "active_empirical_table_cells": 119, "empirical_figure_panels": 2,
        "attributable_pre_live_native_implementation_found": True,
        "native_controlled_execution_passed": True,
        "author_space_history_commits": history["author_space"]["commits"],
        "author_space_deleted_lfs_archive_recovered": True,
        "author_space_deleted_lfs_archive_contains_results": False,
        "official_dataset_history_commits": history["dataset"]["commits"],
        "official_dataset_lfs_payloads_verified": history["dataset"][
            "lfs_payloads_verified"
        ],
        "official_dataset_full_declared_period_revisions_per_asset": history[
            "dataset"
        ]["fully_covering_declared_period_revisions_per_asset"],
        "official_dataset_full_declared_period_revisions_matching_printed_return": history[
            "dataset"
        ]["full_declared_period_revisions_matching_printed_return"],
        "organizer_history_commits": history["organizer"]["commits"],
        "organizer_historical_primitive_decision_or_result_paths": history[
            "organizer"
        ]["historical_primitive_decision_or_result_paths"],
        "paper_window_official_decision_rows_recovered": 97,
        "paper_window_official_rows_replayed_with_organizer_scorer": 97,
        "organizer_native_scorer_executed": True,
        "organizer_native_scorer_source_commit": ARENA_COMMIT,
        "organizer_native_scorer_source_sha256": ORGANIZER_PERF_SHA256,
        "organizer_native_scorer_runner_sha256": ORGANIZER_RUNNER_SHA256,
        "organizer_native_scorer_runtime": organizer_execution["runtime"],
        "organizer_native_scorer_network_calls": organizer_execution[
            "network_calls"
        ],
        "organizer_native_scorer_assets_executed": organizer_execution[
            "conformance"
        ]["assets_executed"],
        "organizer_native_scorer_official_decision_rows": organizer_execution[
            "conformance"
        ]["selected_official_decision_rows"],
        "organizer_native_scorer_equity_arrays_exact": organizer_execution[
            "conformance"
        ]["equity_arrays_exact"],
        "organizer_native_scorer_equity_points_exact": organizer_execution[
            "conformance"
        ]["equity_points_exact"],
        "organizer_native_scorer_metric_scalars_exact": organizer_execution[
            "conformance"
        ]["metric_scalars_exact"],
        "organizer_native_scorer_win_rate_trade_scalars_exact": (
            organizer_execution["conformance"]["win_rate_trade_scalars_exact"]
        ),
        "published_table_cells_regenerated": sum(
            row["published_result_regenerated_at_display_precision"] for row in tables
        ),
        "published_table_cells_verified_from_official_decisions_and_organizer_output": 5,
        "published_table_cells_verified_via_exact_native_organizer_scorer": (
            organizer_execution["conformance"][
                "published_cells_verified_via_native_scorer"
            ]
        ),
        "published_table_cells_reproduced_from_native_llm_decisions": 0,
        "published_baseline_cells_regenerated_from_official_history": 28,
        "published_baseline_cells_regenerated_with_declared_endpoint": 0,
        "published_baseline_cells_regenerated_with_recovered_mixed_endpoints": 28,
        "published_buy_hold_cells_regenerated_with_recovered_mixed_endpoints": 14,
        "published_always_hold_cells_regenerated_with_recovered_mixed_endpoints": 14,
        "offline_baseline_history_commits_examined": sum(
            {
                row["repository"]: row["reachable_commits_examined"]
                for row in baseline_search
            }.values()
        ),
        "offline_baseline_history_search_rows": len(baseline_search),
        "offline_baseline_history_search_families": len(OFFLINE_BASELINE_SEARCH_PATTERNS),
        "offline_baseline_generator_candidates": sum(
            row["offline_baseline_generator_candidate"] for row in baseline_search
        ),
        "offline_exact_identifier_source_hits": sum(
            row["source_matches_across_commits"]
            for row in baseline_search
            if row["search_family"] == "exact_offline_identifiers"
        ),
        "offline_random_generator_source_hits": sum(
            row["source_matches_across_commits"]
            for row in baseline_search
            if row["search_family"] == "random_generator_calls"
        ),
        "offline_random_term_source_hits": sum(
            row["source_matches_across_commits"]
            for row in baseline_search
            if row["search_family"] == "random_term"
        ),
        "offline_momentum_source_paths": {
            row["repository"]: row["source_paths"]
            for row in baseline_search
            if row["search_family"] == "momentum_term"
        },

        "published_table_cells_reproduced_end_to_end_from_native_llm_pipeline": 0,
        "full_empirical_figure_panels_regenerated": 0,
        "displayed_figure_endpoints_verified": 2,
        "paper_appendix_prompt_rows": 9,
        "byte_identical_full_native_prompts_in_paper": 0,
        "full_end_to_end_pipeline_reproduced": False,
        "strict_success": False,
        "generated_file_sha256": {name: sha256(output / name) for name in sorted(generated_names)},
    }
    write_json(output / "manifest.json", manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.scratch.resolve(), args.output.resolve())
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
