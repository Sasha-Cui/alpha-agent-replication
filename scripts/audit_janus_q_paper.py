#!/usr/bin/env python3
"""Build a fail-closed primary-source and author-release audit for Janus-Q."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import tarfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

import numpy as np
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/janus_q_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/janus_q"
WORK_ID = "CensusArxiv260219919"
SYSTEM_ID = "SYS-JANUS-Q"
ARXIV_ID = "2602.19919"
PROJECT_URL = "https://cute-twilight-5f2400.netlify.app"
AUTHOR_REPOSITORY = "https://github.com/Jackson906E/Janus-Q-demo"
AUTHOR_DEFAULT_BRANCH = "main"
AUTHOR_DEFAULT_HEAD = "526ac4e32d1e6904f5f3e2af25ea18886b61d325"
AUTHOR_RELEASE_COMMIT = "4455e10202865d9fe0c167ed0bdea57af266fdc1"
AUTHOR_HISTORY_COMMITS = (
    "3473cef4fabe33cb1f77107c24376be13f1b89e4",
    "36b8ead0f60ad14cb8e44cf56a33c7494d36e1f8",
    "31bcd9bae449e6820b7c88ceb85fdc4000df879c",
    "8a8fae7b331fad8c0f3eabbf51de4830810866f3",
    "9eb81682c6c86b9c583697fcc9b0dff7bb92c921",
    "8bd11441d5dea7caef2bb689d042259f6151d5b9",
    AUTHOR_DEFAULT_HEAD,
    "e61562451a94cfaa4ea47e82b0267670c652bb3b",
    "1f07be86f0e237de6dae43c032ae0954485a54ab",
    AUTHOR_RELEASE_COMMIT,
)
AUTHOR_HISTORY_PATHS = {
    "README.md", "index.html", "static/Framework.png", "static/app.js",
    "static/backtest_multi_csv_all_results.png", "static/eqW_typeW.png",
    "static/holding_period_sr.png", "static/holding_period_tr.png", "static/intro.png",
    "static/logo.svg", "static/logo1.png", "static/logo2.png",
    "data/event_type_backtest.json", "data/event_type_nav_timeseries.json",
    "data/event_weights.json", "data/holding_period_data.json", "data/model_accuracy.json",
    "data/nav_timeseries.json", "data/summary_stats.json", "data/unified_backtest.json",
}
DATASET_URL = "https://drive.google.com/drive/folders/1bAuItyl0ARatopOPiyEZaq_BaaDkZiES"
CODE_ARCHIVE_URL = "https://anonymous.4open.science/r/test-AF0E/"

PINS = {
    "primary/arxiv-api.xml": "50493c8c1722c502391bece9f5105a3491751b4ff75deccbe64690bd46446b24",
    "primary/official.pdf": "496fc31f7600674acbaf1780273d4311141ed9cbaf89a26c12950c40f5886e7e",
    "primary/official.txt": "49168e259752753bc4fcaf6bf7d4b420c94f9527457fe0e7dcf83f077704c982",
    "primary/rebuilt.pdf": "4a5cadda4d4f061b18828b15f33bdb7b6fa86fee0e789377c96842776614b86c",
    "primary/rebuilt.txt": "75e15162dc992e2b101f0f71bacca5e1eac10402b3bf274e93a47ec493d23312",
    "primary/source.tar": "a57e323865be314127bb8bf02f8dd73b9717a8b2698db8bdd3408e8559923e49",
    "release/anonymous-4open-status.txt": "302353950c26242a16bd1b8fcd2f180750f220e20b83f5332609fb43a94d1784",
    "release/author_repo-gh-page.tar.gz": "2d167729ced890f32f4151037c9e33a0638eb9b66fe6e74701bb622adcccdb48",
    "release/dataset_download/news_with_label.csv": "6bf5983de36df3fe1712e738cd5317904c0acec504c3f4a124b989f6a0be2871",
    "release/dataset_download/stock_CAR_series.csv": "e58dbdc1ac84b9c935fc8e9cbb75eae894cb6d253fb73a712a5f7ca63e9e9393",
    "release/dataset_download/stock_industry_profile.csv": "4c04904dcce406bc1b85f90bea056ee53f2e1e293debbc2eac9e21b489047e9f",
    "release/dataset_download/test.jsonl": "f35692c4adf6d77f4977324fc82b0e6b18ef8f42c7e8ac08613deeae6a5b1b6f",
    "release/dataset_download/train.jsonl": "fa5e8c188629228ac256142509446f391675e50dea305da5347290ad918d3883",
    "release/dataset_download/val.jsonl": "a32c2e183b9d0cc01f8e611e5dae5214a9ab3971c4ffe6b1aa8e333a8779aeb1",
    "release/project_page/app.js": "9e8c5f01878383df7d410d2187e98f917e5a7f9e07b65be7d3607ed4d360b09b",
    "release/project_page/assets/Framework.png": "f8e538fffaf5e8730bd3944b0fed17a1e5280bdff0103c24ba8af1596eeab068",
    "release/project_page/assets/eqW_typeW.png": "0338503f4a255e060da4ddb89d65dfd8e82652aead295f664287e50610782974",
    "release/project_page/assets/intro.png": "1aca44b0abc1cff03e70ee7a8e04ff68c22e4742a1e3ecfa946639a4d518127e",
    "release/project_page/assets/logo1.png": "3ae6be05005a6b894f761c1d1a26fa78db262b11a10e18bbdd40e8019a0ea10d",
    "release/project_page/data/event_type_backtest.json": "25522f4566e31e63d43976c17a560601a1cd0cade528b85aab6c4a89d04563d3",
    "release/project_page/data/event_type_nav_timeseries.json": "043564e21b44284d84fa0cb936822454afc961701904fb741a13ccc73180213f",
    "release/project_page/data/event_weights.json": "740804412b355042b99b5452fad71089cf46a887287201a9e71b985361440636",
    "release/project_page/data/holding_period_data.json": "7c16ad2d606476e78b75043a2bfec9f9d694fa0f34f2aab453ef647541717f91",
    "release/project_page/data/model_accuracy.json": "0542b5db741a9e108fdbe6170a287edddaf7b7fe104695d319129129298330da",
    "release/project_page/data/nav_timeseries.json": "8562b02e87753d49502913eec5200264161712f71801325afe157745ceebd9e5",
    "release/project_page/data/summary_stats.json": "525d5980cbc4725a72aab7bcbff4f15d9704e7956c12bae8d6eb04ddfb7b0767",
    "release/project_page/data/unified_backtest.json": "e86393527c60b6f1114aa882d47bd97817de85c7f928344e5877dc4c5f556f55",
    "release/project_page/index.html": "fe6dfc0a9b509945fd7a71194a611f859f87494fbe725c007a001535bf46088f",
}

DISCOVERY_PINS = {
    "author_repo-gh-page-commit.json": "3a145c796c455ae471b142a637b3459581182da1042fd039ef8f098b2898a4ed",
    "author_repo_git_log.tsv": "6cd5c0a284c717b4ad666b3b9705931bbb5e7b4fc9432c2ba95a2420555b3927",
    "coauthor-publication.md": "c0e0cb636ef17adc83e8f6b6c6233d3953a574dd9120530970214a3d1cb12538",
    "github-code-4open.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github-code-car-file.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github-code-netlify.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github-code-title.json": "f80fcc630a23887eb973a0d571a46c7348f22659390d3bd8f11b810ec6a1e33a",
    "github-commits-title.json": "ece8e31a29e236d6fd961adcacb38f54923885b6f96d88d220c082d55b9016e5",
    "github-branches.json": "a2b2e164c26f3eb257debdba196c239f2b7b73bd71d8a48306c27a9404cd65a0",
    "github-tags.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "github-releases.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "github-repos-exact.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github-repos-title.json": "32c237a4a22247928bc48dea19e7ea49849824ddc91968ff312caeafb3d27c63",
    "huggingface-datasets.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "huggingface-models.json": "621bf45053ea817fa15abd3a4b8d25410e7c84a669b294991e775e3a998d7aea",
    "repo-Jackson906E__Janus-Q-demo-contents.json": "8c3e3fc71526efcf9e76f14c36f099b85a0831be4b37c948b3cec6aa22a6a40f",
    "repo-Jackson906E__Janus-Q-demo-summary.json": "797e5629aefb493fb18575910b80c78d6854b991396c4c5777d1e4bd9e47f7f4",
    "user-Jackson906E.json": "e5cf633e96d4cd5fa87dc847cc451826ed13da7a64f2f9c439bc291bc5a084eb",
}

EXPECTED_RESULT_UNITS = 130
JSONL_FILES = ("train.jsonl", "val.jsonl", "test.jsonl")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty ledger: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def history_blob(repo: Path, commit: str, path: str) -> Any:
    return json.loads(git(repo, "show", f"{commit}:{path}"))


def targeted_event_output_consistency(repo: Path, commit: str) -> dict[str, Any]:
    """Check the only two JSON files edited after the duplicated site upload."""
    nav = history_blob(repo, commit, "data/event_type_nav_timeseries.json")
    backtest = history_blob(repo, commit, "data/event_type_backtest.json")
    values = np.asarray(nav["Risk Warning"]["series"]["DeepSeek-v3.1-nex-n1"], dtype=float)
    record = next(
        row["metrics"]
        for row in backtest["风险警示与消除"]
        if row["modelName"] == "DeepSeek-v3.1-nex-n1"
    )
    returns = values[1:] / values[:-1] - 1.0
    mdd = float(np.max(1.0 - values / np.maximum.accumulate(values)))
    total_return = float(values[-1] / values[0] - 1.0)
    annual_return = float((1.0 + total_return) ** (252.0 / len(returns)) - 1.0)
    derived = {
        "arr": annual_return,
        "sr": float(returns.mean() / returns.std(ddof=0) * np.sqrt(252)),
        "mdd": mdd,
        "cr": annual_return / mdd,
        "totalReturn": total_return,
    }
    matched = {
        metric: abs(value - float(record[metric]))
        <= (5e-7 if metric in {"arr", "mdd", "totalReturn"} else 5e-5)
        for metric, value in derived.items()
    }
    return {
        "nav_terminal_value": format(values[-1], ".12g"),
        "reported_total_return": format(float(record["totalReturn"]), ".12g"),
        "derived_total_return": format(total_return, ".12g"),
        "reported_arr": format(float(record["arr"]), ".12g"),
        "derived_arr": format(annual_return, ".12g"),
        "reported_sr": format(float(record["sr"]), ".12g"),
        "derived_sr": format(derived["sr"], ".12g"),
        "reported_mdd": format(float(record["mdd"]), ".12g"),
        "derived_mdd": format(mdd, ".12g"),
        "reported_cr": format(float(record["cr"]), ".12g"),
        "derived_cr": format(derived["cr"], ".12g"),
        "matching_metrics": sum(matched.values()),
        "mismatching_metrics": ";".join(metric for metric, passed in matched.items() if not passed),
    }


def source_history_rows(scratch: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Inventory every public revision/ref and the revisioned supplementary edit."""
    repo = scratch / "author_repo"
    if git(repo, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise ValueError("Janus-Q history checkout is shallow")
    commits = git(repo, "rev-list", "--reverse", "--all").splitlines()
    if commits != list(AUTHOR_HISTORY_COMMITS):
        raise ValueError(f"Janus-Q public history changed: {commits}")
    unreachable = git(repo, "fsck", "--full", "--no-reflogs", "--unreachable", "--no-progress").strip()
    if unreachable:
        raise ValueError(f"Janus-Q has unreviewed unreachable objects: {unreachable}")
    branches = json.loads((scratch / "discovery/github-branches.json").read_text())
    branch_heads = sorted((row["name"], row["commit"]["sha"]) for row in branches)
    if branch_heads != sorted((("gh-page", AUTHOR_RELEASE_COMMIT), ("main", AUTHOR_DEFAULT_HEAD))):
        raise ValueError(f"Janus-Q public branches changed: {branch_heads}")
    if json.loads((scratch / "discovery/github-tags.json").read_text()) or json.loads(
        (scratch / "discovery/github-releases.json").read_text()
    ):
        raise ValueError("Janus-Q now exposes an unreviewed tag or release")

    rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []
    for commit in commits:
        authored_at, subject = git(repo, "show", "-s", "--format=%aI%x09%s", commit).rstrip().split("\t", 1)
        paths = git(repo, "ls-tree", "-r", "--name-only", commit).splitlines()
        unexpected = set(paths) - AUTHOR_HISTORY_PATHS
        if unexpected:
            raise ValueError(f"Janus-Q history contains unreviewed paths: {sorted(unexpected)}")
        system_source = [
            path for path in paths
            if path.endswith((".py", ".ipynb", ".r", ".jl", ".c", ".cpp", ".java", ".sh"))
        ]
        payloads = [path for path in paths if path.startswith("data/") and path.endswith(".json")]
        rows.append({
            "commit": commit,
            "authored_at": authored_at,
            "subject": subject,
            "tracked_paths": len(paths),
            "static_site_script_paths": sum(path.endswith(".js") for path in paths),
            "structured_output_payload_paths": len(payloads),
            "native_system_source_paths": len(system_source),
            "native_system_source_found": bool(system_source),
        })
        if "data/event_type_backtest.json" in paths:
            consistency = targeted_event_output_consistency(repo, commit)
            output_rows.append({
                "commit": commit,
                "authored_at": authored_at,
                **consistency,
                "paper_result_credit": False,
                "boundary": "supplementary event-specific output consistency; not native experiment regeneration",
            })
    if [row["matching_metrics"] for row in output_rows] != [5, 5, 1, 1, 1]:
        raise ValueError("Janus-Q historical supplementary-output consistency changed")
    return rows, output_rows


def token_jaccard(left: str, right: str) -> float:
    a = Counter(re.findall(r"\w+", left.lower()))
    b = Counter(re.findall(r"\w+", right.lower()))
    return sum((a & b).values()) / sum((a | b).values())


def verify_pins(scratch: Path) -> None:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != expected:
            raise ValueError(f"pin mismatch: {relative}={observed}; expected {expected}")
    for relative, expected in DISCOVERY_PINS.items():
        path = scratch / "discovery" / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != expected:
            raise ValueError(f"discovery pin mismatch: {relative}={observed}; expected {expected}")


def paper_sources(scratch: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(scratch / "primary/source.tar", "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe source member: {member.name}")
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError(f"unreadable source member: {member.name}")
            files[member.name] = handle.read()
    if len(files) != 23:
        raise ValueError(f"paper source file count changed: {len(files)}")
    return files


def strip_comments(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("%"))


def table_environment(source: str, label: str) -> str:
    source = strip_comments(source)
    marker = rf"\label{{{label}}}"
    location = source.index(marker)
    begin = max(source.rfind(r"\begin{table", 0, location), source.rfind(r"\begin{wraptable", 0, location))
    ends = [value for value in (source.find(r"\end{table", location), source.find(r"\end{wraptable", location)) if value >= 0]
    if begin < 0 or not ends:
        raise ValueError(f"table boundary missing: {label}")
    return source[begin:min(ends)]


def clean_tex(value: str) -> str:
    previous = None
    while previous != value:
        previous = value
        value = re.sub(r"\\(?:textbf|underline|mathrm|text|cellcolor\{[^{}]*\})\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\cellcolor\{[^{}]*\}", "", value)
    value = re.sub(r"\\multirow\{[^{}]*\}\{[^{}]*\}\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"[{}$~]", "", value)
    return " ".join(value.split())


def table_data_rows(environment: str) -> list[list[str]]:
    match = re.search(r"\\begin\{tabular\}\{[^\n]*\}(.*?)\\end\{tabular\}", environment, re.S)
    if match is None:
        raise ValueError("tabular body missing")
    rows: list[list[str]] = []
    for chunk in re.split(r"\\\\", match.group(1)):
        if "&" not in chunk or any(token in chunk for token in (r"\toprule", r"\bottomrule", r"\cmidrule", r"\multicolumn")):
            continue
        chunk = re.sub(r"\\(?:midrule|addlinespace(?:\[[^]]*\])?)", "", chunk)
        rows.append([clean_tex(cell) for cell in chunk.split("&")])
    return rows


def normalize_model(name: str) -> str:
    compact = re.sub(r"[^a-z0-9]", "", name.lower())
    aliases = {
        "grok3minibeta": "grok3minibeta",
        "janusqours": "janusq",
        "janusqfull": "janusq",
        "hgrmfull": "janusq",
    }
    return aliases.get(compact, compact)


def result_rows(files: Mapping[str, bytes], released: Path) -> list[dict[str, Any]]:
    source = files["main.tex"].decode("utf-8")
    unified = {
        normalize_model(row["name"]): row["metrics"]
        for row in json.loads((released / "data/unified_backtest.json").read_text())
    }
    accuracy = {
        normalize_model(name): values
        for name, values in json.loads((released / "data/model_accuracy.json").read_text()).items()
    }
    rows: list[dict[str, Any]] = []
    table_specs = (
        ("tab:model_comparison", ("MAE", "RMSE", "DA", "ETA", "SR", "MDD"), 90),
        ("tab:ablation module component", ("MAE", "DA", "ETA", "SR"), 20),
        ("tab:ablation reward model", ("MAE", "DA", "ETA", "SR"), 20),
    )
    for label, metrics, expected in table_specs:
        parsed = table_data_rows(table_environment(source, label))
        table_rows: list[dict[str, Any]] = []
        for row_index, cells in enumerate(parsed, 1):
            if label == "tab:model_comparison":
                if len(cells) < 8:
                    raise ValueError(f"short main table row: {cells}")
                row_name = cells[1]
                values = cells[2:8]
            else:
                if len(cells) < 5:
                    raise ValueError(f"short ablation row: {cells}")
                row_name = cells[0]
                values = cells[1:5]
            model_key = normalize_model(row_name)
            if len(metrics) != len(values):
                raise ValueError(f"metric/value width changed in {label}: {cells}")
            for metric, cell in zip(metrics, values):
                if cell in {"--", "-", ""} or not re.search(r"\d", cell):
                    continue
                printed = float(cell)
                released_value: float | None = None
                evidence_file = ""
                if label == "tab:model_comparison" and metric in {"DA", "ETA"} and model_key in accuracy:
                    released_value = float(accuracy[model_key][metric.lower()])
                    evidence_file = "data/model_accuracy.json"
                elif label == "tab:model_comparison" and metric in {"SR", "MDD"} and model_key in unified:
                    released_value = float(unified[model_key][metric.lower()])
                    evidence_file = "data/unified_backtest.json"
                exact = released_value is not None and round(released_value, 4) == round(printed, 4)
                contradiction = released_value is not None and not exact
                status = "verified_author_linked_output" if exact else ("contradicted_by_author_linked_output" if contradiction else "no_released_numeric_backing")
                table_rows.append(
                    {
                        "table_label": label,
                        "row_index": row_index,
                        "row_label": row_name,
                        "metric": metric,
                        "printed_value": format(printed, ".4f"),
                        "released_value": "" if released_value is None else format(released_value, ".6f"),
                        "author_release_evidence": evidence_file,
                        "verification_status": status,
                        "printed_cell_exactly_verified": exact,
                        "author_native_experiment_executed": False,
                        "published_result_regenerated": False,
                        "paper_result_credit": False,
                        "boundary": "author-linked output corroboration is not regeneration through the unreleased training/backtest pipeline",
                    }
                )
        if len(table_rows) != expected:
            raise ValueError(f"published denominator changed for {label}: {len(table_rows)} != {expected}")
        rows.extend(table_rows)
    counts = Counter(row["verification_status"] for row in rows)
    if len(rows) != EXPECTED_RESULT_UNITS or counts != {
        "verified_author_linked_output": 61,
        "contradicted_by_author_linked_output": 1,
        "no_released_numeric_backing": 68,
    }:
        raise ValueError(f"published result accounting changed: {len(rows)} {counts}")
    return rows


def nav_metric_rows(released: Path) -> list[dict[str, Any]]:
    nav = json.loads((released / "data/nav_timeseries.json").read_text())
    published = {
        normalize_model(row["name"]): row
        for row in json.loads((released / "data/unified_backtest.json").read_text())
    }
    if len(nav["dates"]) != 55 or len(nav["series"]) != 17:
        raise ValueError("released NAV dimensions changed")
    rows: list[dict[str, Any]] = []
    for model, values in nav["series"].items():
        array = np.asarray(values, dtype=float)
        returns = array[1:] / array[:-1] - 1.0
        running = np.maximum.accumulate(array)
        total_return = float(array[-1] / array[0] - 1.0)
        mdd = float(np.max(1.0 - array / running))
        days = len(returns)
        derived = {
            "totalReturn": total_return,
            "mdd": mdd,
            "sr": float(returns.mean() / returns.std(ddof=0) * np.sqrt(252)),
            "arr": float((1.0 + total_return) ** (252.0 / days) - 1.0),
            "cr": float(((1.0 + total_return) ** (252.0 / days) - 1.0) / mdd),
        }
        record = published[normalize_model(model)]["metrics"]
        for metric, value in derived.items():
            reported = float(record[metric])
            tolerance = 5e-7 if metric in {"totalReturn", "mdd", "arr"} else 5e-5
            passed = abs(value - reported) <= tolerance
            rows.append(
                {
                    "model": model,
                    "metric": metric,
                    "independently_recomputed": format(value, ".12g"),
                    "author_release_value": format(reported, ".12g"),
                    "absolute_error": format(abs(value - reported), ".12g"),
                    "tolerance": tolerance,
                    "verification_passed": passed,
                    "source": "55-point author-linked NAV array",
                    "boundary": "validates released output arithmetic; does not reproduce predictions, trades, or portfolio construction",
                }
            )
    if len(rows) != 85 or not all(row["verification_passed"] for row in rows):
        raise ValueError("NAV-derived metric verification changed")
    return rows


def parse_user_record(content: str) -> tuple[str, str, str]:
    company = re.search(r"公司简称：([^\n]+)", content)
    code = re.search(r"股票代码：([^\n]+)", content)
    timestamp = re.search(r"时间：([^\n]+)", content)
    if not (company and code and timestamp):
        raise ValueError("released JSONL user template changed")
    return timestamp.group(1).strip(), company.group(1).strip(), code.group(1).strip().zfill(6)


def load_dataset_rows(dataset: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
    with (dataset / "news_with_label.csv").open(newline="", encoding="utf-8-sig") as stream:
        news = list(csv.DictReader(stream))
    with (dataset / "stock_CAR_series.csv").open(newline="", encoding="utf-8-sig") as stream:
        car = list(csv.DictReader(stream))
    with (dataset / "stock_industry_profile.csv").open(newline="", encoding="utf-8-sig") as stream:
        profiles = list(csv.DictReader(stream))
    jsonl: list[dict[str, Any]] = []
    for split in JSONL_FILES:
        with (dataset / split).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                row["_split"] = split.removesuffix(".jsonl")
                jsonl.append(row)
    return news, car, profiles, jsonl


def dataset_audit_rows(dataset: Path, news: list[dict[str, str]], car: list[dict[str, str]], profiles: list[dict[str, str]], jsonl: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_split = Counter(row["_split"] for row in jsonl)
    news_ids = {row["NEWS_ID"] for row in news}
    event_counts = Counter(row["事件类型"] for row in news)
    finite_post = sum(math.isfinite(float(row["post_car"])) for row in car if row["post_car"] not in {"", "nan", "NaN"})
    file_rows = [
        ("news_with_label.csv", len(news), len(news_ids), min(row["新闻时间"] for row in news), max(row["新闻时间"] for row in news), "64,326 event-stock rows; 62,265 unique NEWS_IDs"),
        ("stock_CAR_series.csv", len(car), finite_post, min(row["新闻时间"] for row in car), max(row["新闻时间"] for row in car), "44 columns; 62,462 finite post_car labels"),
        ("stock_industry_profile.csv", len(profiles), len({row["股票代码"] for row in profiles}), "", "", "5,500 code rows; 380 industries"),
        ("train.jsonl", by_split["train"], by_split["train"], "2023-10-25 14:48:23", "2024-08-28 18:12:17", "three messages plus structured ground_truth"),
        ("val.jsonl", by_split["val"], by_split["val"], "2024-08-28 18:14:13", "2024-11-12 17:42:25", "three messages plus structured ground_truth"),
        ("test.jsonl", by_split["test"], by_split["test"], "2024-11-12 17:46:24", "2025-01-25 00:17:12", "assistant content intentionally empty"),
    ]
    inventory = [
        {
            "file": name,
            "sha256": PINS[f"release/dataset_download/{name}"],
            "bytes": (dataset / name).stat().st_size,
            "records": records,
            "secondary_count": secondary,
            "minimum_timestamp": start,
            "maximum_timestamp": end,
            "schema_or_scope": scope,
        }
        for name, records, secondary, start, end, scope in file_rows
    ]

    aligned = sum(
        left["新闻时间"] == right["新闻时间"] and left["公司简称"] == right["公司简称"]
        for left, right in zip(news, car)
    )
    post_valid = 0
    post_total = 0
    lookup: dict[tuple[str, str], tuple[dict[str, str], dict[str, str]]] = {}
    if len(news) != len(car):
        raise ValueError("news/CAR row counts differ")
    for left, right in zip(news, car):
        lookup[(left["新闻时间"], left["公司简称"])] = (left, right)
        if right["post_car"] in {"", "nan", "NaN"}:
            continue
        post_total += 1
        post_valid += abs(float(right["post_car"]) - (float(right["CAR(20)"]) - float(right["CAR(0)"]))) <= 1e-14

    linked = direction_valid = strength_valid = event_valid = 0
    assistant_filled = Counter()
    duplicate_reasoning_header = 0
    for row in jsonl:
        timestamp, company, _code = parse_user_record(row["messages"][1]["content"])
        raw_news, raw_car = lookup[(timestamp, company)]
        truth = row["ground_truth"]
        linked += abs(float(raw_car["post_car"]) - float(truth["car"])) <= 1e-14
        event_valid += raw_news["事件类型"] == truth["event_type"]
        expected_direction = "positive" if float(truth["car"]) > 0 else ("negative" if float(truth["car"]) < 0 else "neutral")
        direction_valid += truth["direction"] == expected_direction
        strength_valid += truth["strength"] == ("strong" if abs(float(truth["car"])) > 0.0015 else "weak")
        content = row["messages"][2]["content"]
        assistant_filled[row["_split"]] += bool(content)
        duplicate_reasoning_header += content.count("【推理过程】") > 1

    checks = [
        ("news_car_row_alignment", len(news), aligned, "timestamp and company match row by row"),
        ("post_car_definition", post_total, post_valid, "post_car equals CAR(20)-CAR(0) within 1e-14"),
        ("jsonl_raw_record_linkage", len(jsonl), linked, "timestamp/company and exact CAR recover a released raw pair"),
        ("jsonl_event_type_labels", len(jsonl), event_valid, "ground_truth event type equals released expert label"),
        ("jsonl_direction_labels", len(jsonl), direction_valid, "ground_truth direction equals sign(post_car)"),
        ("jsonl_strength_labels", len(jsonl), strength_valid, "ground_truth strength equals abs(post_car)>0.0015"),
        ("train_assistant_outputs_present", by_split["train"], assistant_filled["train"], "filled SFT response"),
        ("validation_assistant_outputs_present", by_split["val"], assistant_filled["val"], "filled SFT response"),
        ("test_assistant_outputs_empty", by_split["test"], by_split["test"] - assistant_filled["test"], "test response field is blank"),
        ("event_type_cardinality", 10, len(event_counts), json.dumps(dict(sorted(event_counts.items())), ensure_ascii=False, sort_keys=True)),
        ("unique_stock_codes_in_news", 5282, len({row["股票代码"] for row in news}), "matches paper's stated universe count"),
    ]
    integrity = [
        {
            "check": name,
            "denominator": denominator,
            "successes": successes,
            "passed": denominator == successes,
            "evidence": evidence,
            "boundary": "released-data integrity check; not proof of annotation quality, CAR factor construction, model training, or trading execution",
        }
        for name, denominator, successes, evidence in checks
    ]
    if len(news) != 64326 or len(news_ids) != 62265 or len(car) != 64326 or len(profiles) != 5500:
        raise ValueError("released dataset dimensions changed")
    if by_split != {"train": 20000, "val": 6000, "test": 5999}:
        raise ValueError(f"JSONL dimensions changed: {by_split}")
    if not all(row["passed"] for row in integrity):
        raise ValueError("released dataset integrity check failed")
    if duplicate_reasoning_header == 0:
        raise ValueError("known duplicated reasoning-header condition changed")
    return inventory, integrity


def historical_stat_rows(news: list[dict[str, str]], car: list[dict[str, str]], jsonl: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prompt = jsonl[0]["messages"][0]["content"]
    printed: dict[str, tuple[float, float]] = {}
    for event, mean, mean_abs in re.findall(r"([^\n：]+)：平均CAR = ([+-]?\d+\.\d+)，\|CAR\|平均 = (\d+\.\d+)", prompt):
        printed[event] = (float(mean), float(mean_abs))
    aliases: dict[str, str] = {}
    values: dict[str, list[float]] = defaultdict(list)
    if len(news) != len(car):
        raise ValueError("news/CAR row counts differ")
    for left, right in zip(news, car):
        if left["新闻时间"] >= "2023-10-25" or right["post_car"] in {"", "nan", "NaN"}:
            continue
        values[left["事件类型"]].append(float(right["post_car"]))
    rows = []
    for prompt_event, pair in printed.items():
        raw_event = aliases.get(prompt_event, prompt_event)
        data = np.asarray(values[raw_event], dtype=float)
        computed = (round(float(data.mean()), 4), round(float(np.abs(data).mean()), 4))
        rows.append(
            {
                "event_type": prompt_event,
                "prompt_mean_car": format(pair[0], "+.4f"),
                "raw_cutoff_mean_car": format(computed[0], "+.4f"),
                "prompt_mean_abs_car": format(pair[1], ".4f"),
                "raw_cutoff_mean_abs_car": format(computed[1], ".4f"),
                "both_values_match": pair == computed,
                "simple_cutoff": "released rows strictly before 2023-10-25 with finite post_car",
            }
        )
    if len(rows) != 10 or sum(not row["both_values_match"] for row in rows) != 3:
        raise ValueError("historical prompt-stat reconciliation changed")
    return rows


def figure_rows(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    specs = (
        ("fig:nav_curve", "Fig/backtest1.pdf", 1, True, "17 released 55-point NAV series"),
        ("fig:human_model_eval", "Fig/direction_comparison.png;Fig/event_type_comparison.png", 2, False, "rendered bars only; 200 sampled cases and judge records absent"),
        ("fig:distribution", "Fig/car_distribution.png", 1, True, "released post_car rows and event labels support regrouping"),
        ("fig:event_weights_barplot", "Fig/event_weights_barplot.png", 1, True, "10 released event weights"),
        ("fig:two type weight", "Fig/eqW_typeW.png", 1, False, "exact author raster recovered but curve arrays absent"),
        ("fig:holding_period_sensitivity", "Fig/holding_period_tr.png;Fig/holding_period_sr.png", 2, True, "4 models x 10 horizons for TR and SR released"),
        ("fig:max_position", "Fig/max_position_ratio_hp5.png;Fig/max_position_ratio_hp10.png", 2, False, "rendered bars only; position-limit run records absent"),
    )
    rows = []
    for figure, paths, panels, numeric, detail in specs:
        hashes = ";".join(sha256_bytes(files[path]) for path in paths.split(";"))
        rows.append(
            {
                "figure": figure,
                "source_assets": paths,
                "source_asset_sha256": hashes,
                "active_empirical_panels": panels,
                "author_linked_numeric_backing_recovered": numeric,
                "author_native_figure_pipeline_regenerated": False,
                "paper_result_credit": False,
                "detail": detail,
                "boundary": "numeric backing or author raster recovery is not native regeneration through the unreleased experiment pipeline",
            }
        )
    if sum(row["active_empirical_panels"] for row in rows) != 10 or sum(row["active_empirical_panels"] for row in rows if row["author_linked_numeric_backing_recovered"]) != 5:
        raise ValueError("empirical panel denominator changed")
    return rows


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official paper/source", "complete", "arXiv v1 PDF and complete 23-file source archive pinned; 16 official and rebuilt pages visually inspected"),
        ("attributable release", "static_outputs_and_data", "first-author repository commit, live project page, eight JSON outputs, figures, prompts and six dataset files pinned"),
        ("native implementation", "not_released", "paper-linked 4open archive is expired; first-author repository history contains only a static website and outputs, no training or backtest code"),
        ("public repository history", "complete_two_branch_static_history", "all 10 revisions across main and gh-page audited; no tags, releases, unreachable objects, or native system source paths"),
        ("supplementary event outputs", "revisioned_internal_conflict", "a historical Risk Warning/DeepSeek NAV tail was edited from 1.526124 to 1.426124; the paired metric record was then partly hand-edited and only total return remains consistent with the revised array"),
        ("license", "missing", "no license was observed for the project repository, project page, or Drive dataset"),
        ("base model", "missing", "Janus-Q backbone/checkpoint and immutable revision are not named"),
        ("SFT setup", "partial", "LoRA and optimizer grid/settings are printed, but selected epoch, GPU count, target modules, seed, code and checkpoint are absent"),
        ("GRPO setup", "grid_only", "ranges are printed without selected configuration, seed, environment, trainer implementation or checkpoint"),
        ("reward model", "equations_partial_parameters_missing", "reward hierarchy is described, but tau/kappa/rho/alpha/sigma/lambda/weights and process-reward implementation are absent; released labels reveal tau=0.0015 only"),
        ("reward pseudocode consistency", "conflicting", "active algorithm does not gate PnL on strength and omits the separately described strength regularization/gate penalty"),
        ("raw news/labels", "substantially_released", "64,326 event-stock rows, 62,265 unique NEWS_IDs, 10 event labels and news bodies/links are available"),
        ("annotation protocol", "partial", "six professionals are mentioned, but per-item annotator IDs, agreement, adjudication and quality records are absent"),
        ("CAR arrays", "derived_arrays_released", "41-day CAR series and post_car are released, but Tushare rows, benchmark mapping, CNE5 exposures/factor returns and construction code are absent"),
        ("company profiles", "partial", "code/name/industry are released; paper-mentioned market share is absent"),
        ("JSONL examples/prompts", "substantially_released", "31,999 system/user/assistant records and ground truth are released; test assistants are blank"),
        ("split boundaries", "contradictory", "JSONL intraday endpoints cross the calendar-day ranges printed in the paper; released total is 31,999 rather than nominal 32,000"),
        ("baseline models", "names_only", "model names are printed without exact prompts, API/model revisions, decoding, raw responses or serving logs"),
        ("backtest timing", "partial", "collection window, next-open entry and subsequent-two-day close exit are described"),
        ("portfolio construction", "partial", "event-type weighting and within-type equal weighting are described without budget, leverage, overlap/conflict handling, eligibility, missing-price rules or trade ledger"),
        ("costs/execution", "missing_for_backtest", "reward transaction cost kappa is symbolic; actual backtest fees, slippage, shorting, corporate actions and fills are absent"),
        ("published output arrays", "substantial_but_incomplete", "17 NAV series, accuracies, unified metrics, event weights and holding-period arrays released; MAE/RMSE, ablations, predictions, orders and returns generator absent"),
        ("seeds/run lineage", "missing", "no seeds, run IDs, experiment logs, model outputs, checkpoint hashes or repeated-run distribution"),
        ("compute/environment", "missing", "no dependency lock, container, hardware allocation, runtime log or executable runner"),
    )
    return [{"dimension": dimension, "status": status, "detail": detail} for dimension, status, detail in specs]


def internal_rows() -> list[dict[str, str]]:
    specs = (
        ("dataset_headline", "conflict", "paper says 62,400 articles; release has 62,265 unique NEWS_IDs and 64,326 event-stock rows"),
        ("jsonl_total", "off_by_one", "released train/validation/test sizes are 20,000/6,000/5,999 = 31,999"),
        ("split_dates", "conflict", "released train extends into Aug 28 and validation into Nov 12, while paper ends those splits Aug 27 and Nov 11"),
        ("project_model_count", "conflict", "project page prose says 20 models; summary JSON, NAV, and main table contain 17 series/rows including indices"),
        ("csi1000_sharpe", "direct_contradiction", "paper prints -0.1036; author output and released NAV independently yield -1.0360"),
        ("historical_event_statistics", "partially_unreconciled", "3/10 event types (6/20 displayed mean/absolute-mean values) differ from a simple released-row historical cutoff"),
        ("nav_start", "one_day_difference", "paper caption begins Nov 12, 2024; released NAV starts Nov 13, plausibly the first tradable observation but unreconciled"),
        ("test_and_backtest_end", "unreconciled_extension", "test news ends Jan 25 while backtest/NAV ends Feb 6; a holding/price extension is plausible but not formally joined"),
        ("sharpe_formula", "incomplete", "paper prints E[r]/sigma_r without annualization; released output uses population standard deviation times sqrt(252)"),
        ("holding_csi300", "conflict", "holding-period JSON calls CSI 300 unchanged but its TR/SR differ from the main released backtest"),
        ("event_specific_history_edit", "direct_internal_conflict", "the initial event-specific NAV/metric pair matches 5/5 metrics; after the public NAV and metric edits only 1/5 matches, while Calmar remains at its obsolete value"),
        ("reward_strength_gate", "method_conflict", "prose activates PnL only for strong signals; active algorithm applies it after direction gating without a strength condition"),
        ("reward_regularization", "method_conflict", "strength regularization/gate penalties are described or present in commented pseudocode but omitted from the active aggregate algorithm"),
        ("sharpe_improvement_claim", "rounding_overstatement", "1.3088 versus 0.6481 is a 101.94% relative increase, not strictly above 102.0%"),
        ("source_project_link", "commented_but_attributable", "the exact live project URL is commented out in TeX; first-author repository history and matching assets corroborate attribution"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def release_rows(scratch: Path) -> list[dict[str, Any]]:
    discovery = scratch / "discovery"
    contents = json.loads((discovery / "repo-Jackson906E__Janus-Q-demo-contents.json").read_text())
    summary = json.loads((discovery / "repo-Jackson906E__Janus-Q-demo-summary.json").read_text())
    history = (discovery / "author_repo_git_log.tsv").read_text()
    status = (scratch / "release/anonymous-4open-status.txt").read_text()
    if contents != [{**contents[0]}] or contents[0]["name"] != "README.md" or contents[0]["size"] != 1:
        raise ValueError("current first-author repository state changed")
    if summary["owner"] != "Jackson906E" or "4455e102" not in history:
        raise ValueError("first-author provenance changed")
    if "The repository is expired." not in status:
        raise ValueError("paper-linked code archive disposition changed")
    zero_queries = ("github-code-4open.json", "github-code-car-file.json", "github-code-netlify.json", "github-repos-exact.json", "huggingface-datasets.json")
    for filename in zero_queries:
        data = json.loads((discovery / filename).read_text())
        count = data.get("total_count", 0) if isinstance(data, dict) else len(data)
        if count != 0:
            raise ValueError(f"bounded zero-result search changed: {filename}")
    specs = (
        ("paper source", PROJECT_URL, True, "exact project URL is commented in main.tex"),
        ("live project page", PROJECT_URL, True, "static page plus eight JSON output endpoints and figures"),
        ("first-author GitHub history", f"{AUTHOR_REPOSITORY}@{AUTHOR_RELEASE_COMMIT}", True, "20-file static site/output tree; no training or backtest implementation"),
        ("current first-author GitHub branch", AUTHOR_REPOSITORY, True, "one-byte README only; historical gh-page branch retains static release"),
        ("paper-linked code archive", CODE_ARCHIVE_URL, False, "browser-visible state: The repository is expired"),
        ("paper-linked Drive dataset", DATASET_URL, True, "six downloadable author-linked data files"),
        ("coauthor publication page", "nathanielwei.github.io", True, "links arXiv only; no additional implementation"),
        ("bounded exact public searches", "GitHub repo/code/commit plus Hugging Face", False, "no additional attributable implementation or checkpoint found"),
    )
    return [
        {
            "surface": surface,
            "target": target,
            "reachable_or_found": found,
            "observation": observation,
            "native_system_code_found": False,
            "negative_search_boundary": "current public indexed surfaces and pinned observations only; private, renamed, deleted or later artifacts may exist",
        }
        for surface, target, found, observation in specs
    ]


def controlled_component_rows() -> list[dict[str, Any]]:
    car = -0.012
    direction = "negative"
    kappa, rho, alpha, sigma = 0.0015, 0.02, 0.5, 0.01
    pnl = -car - kappa
    clipped = float(np.clip(alpha * pnl, -rho, rho))
    magnitude = math.exp(-abs(-0.010 - car) / sigma)
    rows = (
        ("direction_and_strength_labels", {"direction": direction, "strength": "strong"}, direction == "negative" and abs(car) > 0.0015),
        ("single_event_pnl", {"negative_direction_payoff": pnl}, math.isclose(pnl, 0.0105)),
        ("event_discount_and_clip", {"discounted_clipped_pnl": clipped}, math.isclose(clipped, 0.00525)),
        ("magnitude_reward", {"reward": magnitude}, math.isclose(magnitude, math.exp(-0.2))),
    )
    return [
        {
            "component": name,
            "controlled_output": json.dumps(output, sort_keys=True),
            "deterministic_control_passed": passed,
            "parameters_are_control_values_not_paper_settings": True,
            "paper_derived_not_author_code": True,
            "author_native_pipeline_executed": False,
            "published_result_regenerated": False,
            "paper_result_credit": False,
            "boundary": "controlled equation check only; missing paper parameters prevent native reward reproduction",
        }
        for name, output, passed in rows
    ]


def build(scratch: Path, output: Path) -> dict[str, Any]:
    verify_pins(scratch)
    files = paper_sources(scratch)
    official_pages = len(PdfReader(scratch / "primary/official.pdf").pages)
    rebuilt_pages = len(PdfReader(scratch / "primary/rebuilt.pdf").pages)
    overlap = token_jaccard(
        (scratch / "primary/official.txt").read_text(errors="replace"),
        (scratch / "primary/rebuilt.txt").read_text(errors="replace"),
    )
    if (official_pages, rebuilt_pages) != (16, 16) or overlap < 0.998:
        raise ValueError("paper rebuild/page evidence changed")
    main = files["main.tex"].decode("utf-8")
    if PROJECT_URL not in main or "Code and materials" not in main:
        raise ValueError("source-commented author project route changed")

    released = scratch / "release/project_page"
    dataset = scratch / "release/dataset_download"
    results = result_rows(files, released)
    nav_metrics = nav_metric_rows(released)
    news, car, profiles, jsonl = load_dataset_rows(dataset)
    dataset_inventory, dataset_integrity = dataset_audit_rows(dataset, news, car, profiles, jsonl)
    history_stats = historical_stat_rows(news, car, jsonl)
    figures = figure_rows(files)
    methods = method_rows()
    consistency = internal_rows()
    releases = release_rows(scratch)
    components = controlled_component_rows()
    history, historical_outputs = source_history_rows(scratch)

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "released_nav_metric_verification.csv", nav_metrics)
    write_csv(output / "released_dataset_inventory.csv", dataset_inventory)
    write_csv(output / "released_dataset_integrity.csv", dataset_integrity)
    write_csv(output / "historical_prompt_stat_reconciliation.csv", history_stats)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(output / "release_search_audit.csv", releases)
    write_csv(output / "component_execution_audit.csv", components)
    write_csv(output / "released_source_history_inventory.csv", history)
    write_csv(output / "historical_output_revision_consistency.csv", historical_outputs)

    result_counts = Counter(row["verification_status"] for row in results)
    source_provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "arxiv_version": "v1",
        "published_utc": "2026-02-23T14:58:51Z",
        "updated_utc": "2026-02-27T08:50:00Z",
        "source_files": len(files),
        "official_pages": official_pages,
        "rebuilt_pages": rebuilt_pages,
        "official_pages_visually_checked": 16,
        "rebuilt_pages_visually_checked": 16,
        "visual_defects_observed": 0,
        "official_rebuilt_token_jaccard": overlap,
        "author_project_url": PROJECT_URL,
        "author_repository": AUTHOR_REPOSITORY,
        "author_repository_default_branch": AUTHOR_DEFAULT_BRANCH,
        "author_repository_default_branch_head": AUTHOR_DEFAULT_HEAD,
        "author_release_commit": AUTHOR_RELEASE_COMMIT,
        "author_release_commit_tree_files": 20,
        "author_release_contains_system_code": False,
        "full_public_repository_history_audited": True,
        "public_repository_commits": len(history),
        "public_repository_branches": 2,
        "public_repository_tags": 0,
        "public_repository_releases": 0,
        "unreachable_git_objects": 0,
        "historical_native_system_source_paths": sum(row["native_system_source_paths"] for row in history),
        "historical_supplementary_output_revisions_checked": len(historical_outputs),
        "latest_supplementary_output_metrics_matching_array": historical_outputs[-1]["matching_metrics"],
        "paper_linked_code_archive": CODE_ARCHIVE_URL,
        "paper_linked_code_archive_observed_state": "expired",
        "author_dataset_url": DATASET_URL,
        "released_dataset_files": 6,
        "released_dataset_bytes": sum((dataset / name).stat().st_size for name in ("news_with_label.csv", "stock_CAR_series.csv", "stock_industry_profile.csv", *JSONL_FILES)),
        "observed_license": "NOASSERTION",
        "negative_search_scope": "bounded public first-author/coauthor GitHub history, exact GitHub repository/code/commit searches and Hugging Face name searches; not proof of permanent absence",
        "pins": {**PINS, **{f"discovery/{key}": value for key, value in DISCOVERY_PINS.items()}},
    }
    write_json(output / "source_provenance.json", source_provenance)

    readme = f"""# Janus-Q paper-level replication audit

**Verdict: strong author-linked data and published-output recovery, but not an end-to-end replication.** The pinned arXiv `2602.19919v1` source rebuilds to the official 16-page count with {overlap:.2%} extracted-token multiset overlap. All 16 official and 16 rebuilt pages were visually inspected without observed clipping, overlap, missing assets, or unreadable research content.

The source comments out—but clearly identifies—the live author project page. The page links a six-file Drive release and an anonymous 4open repository. The Drive data are downloadable; the 4open page now says **“The repository is expired.”** A repository with the exact paper name is owned by first author Xiang Li. Its current branch has only a one-byte README, but commit `{AUTHOR_RELEASE_COMMIT}` recovers a 20-file static website with the same eight JSON outputs and figures as the live page. The complete public history has 10 revisions across `main` and `gh-page`, no tags, releases, or unreachable objects, and zero native system-source paths. No revision contains model-training, reward, prediction, CAR-construction, or backtest implementation. No license was observed.

The history also exposes an important supplementary-output revision. The two branches initially uploaded byte-identical 20-file trees. On `gh-page`, the Risk Warning/DeepSeek NAV tail was later changed from `1.526124` to `1.426124`; its paired record was then edited in a separate commit from total return `0.526124` to `0.426124`, with ARR, Sharpe, and MDD changed independently while Calmar remained at its old `48.203`. Before the edits the array reproduces all 5/5 paired metrics. After them, only total return matches the revised array (1/5); derived ARR, Sharpe, MDD, and Calmar do not. These event-specific outputs are supplementary and do not change the separate main-table 61/130 accounting, but their current internal consistency is materially weaker than previously documented.

The active empirical denominator is **130 displayed quantitative cells**: 90 in the main comparison table and 40 across two ablation tables. Author-linked JSON exactly corroborates **61/130 cells**, directly contradicts **1/130**, and provides no numeric backing for **68/130** (28 MAE/RMSE cells and all 40 ablation cells). The contradiction is material: the paper prints CSI 1000 Sharpe `-0.1036`; the author output and released NAV both give `-1.0360`. Corroboration is not regeneration: **0/130 cells were produced through the author-native experiment pipeline**.

Five of ten active empirical figure panels have underlying author-linked numeric backing: the 17-series NAV panel, CAR distribution, event weights, and two holding-period panels. The other five have only rendered rasters. **0/10 panels were regenerated through the native pipeline.** Independently recomputing total return, MDD, annualized Sharpe, annualized return, and Calmar from every released NAV yields **85/85 matching output metrics** within the release's rounding. This validates the published static arrays, not the missing predictions, orders, fills, costs, or portfolio engine.

The released dataset is substantial and internally useful: 64,326 event-stock rows, 62,265 unique news IDs, 5,282 stock codes, 10 event types, 64,326 CAR rows, and 31,999 train/validation/test JSONL records. All 62,462 finite `post_car` values equal `CAR(20)-CAR(0)`; all 31,999 JSONL records link exactly to raw rows and reproduce event, direction, and `abs(CAR)>0.0015` strength labels. This is **data-integrity evidence**, not validation of expert annotation or the unreleased Tushare/CNE5 factor construction.

Important boundaries remain. The paper never names Janus-Q's base model or checkpoint; gives GRPO grids rather than selected settings; omits reward constants/weights and executable process/strength gates; supplies no dependency lock, seed, model outputs, trade log, transaction-cost configuration, or backtest runner; and does not release raw prices, benchmark mappings, CNE5 exposures, factor returns, or regression code. The active reward pseudocode also fails to gate PnL on strength despite the prose and omits a separately described strength/gate regularizer.

The audit preserves further discrepancies rather than resolving them by guesswork: the paper's 62,400-article headline versus 62,265 unique released IDs; 31,999 released JSONL records; split files crossing printed calendar-day boundaries; project prose claiming 20 models while its data and paper show 17 series/rows; 3/10 prompt event-stat pairs not matching a simple released-data cutoff; the NAV starting one day after the figure caption; an unreconciled Jan-25-to-Feb-6 news/backtest extension; and a paper Sharpe formula that omits the release's `sqrt(252)` annualization.

Four controlled paper-equation checks pass and every author-data integrity check passes. They are labeled as component/data checks only. `strict_success` remains false because no native training, inference, CAR-construction, portfolio, or backtest pipeline ran and no printed cell was regenerated through such a pipeline.
"""
    (output / "README.md").write_text(readme)

    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "published_numeric_table_cells": EXPECTED_RESULT_UNITS,
        "author_linked_table_cells_exactly_verified": result_counts["verified_author_linked_output"],
        "author_linked_table_cells_contradicted": result_counts["contradicted_by_author_linked_output"],
        "published_table_cells_without_numeric_backing": result_counts["no_released_numeric_backing"],
        "author_native_table_cells_regenerated": 0,
        "active_empirical_figure_panels": 10,
        "author_linked_numeric_panels_recovered": 5,
        "author_native_figure_panels_regenerated": 0,
        "released_nav_derived_metrics_verified": 85,
        "released_data_files": 6,
        "released_data_bytes": source_provenance["released_dataset_bytes"],
        "released_event_stock_rows": 64326,
        "released_unique_news_ids": 62265,
        "released_jsonl_records": 31999,
        "released_jsonl_records_exactly_linked": 31999,
        "paper_linked_code_archive_expired": True,
        "first_author_historical_tree_files": 20,
        "first_author_system_source_files": 0,
        "first_author_public_history_commits_audited": len(history),
        "first_author_public_branches_audited": 2,
        "historical_native_system_source_paths": 0,
        "historical_supplementary_output_revisions_checked": len(historical_outputs),
        "latest_supplementary_output_metrics_matching_array": historical_outputs[-1]["matching_metrics"],
        "author_native_training_executed": False,
        "author_native_backtest_executed": False,
        "full_end_to_end_pipeline_reproduced": False,
        "strict_success": False,
    }
    generated = sorted(path for path in output.iterdir() if path.name != "manifest.json")
    manifest["generated_file_sha256"] = {path.name: sha256(path) for path in generated}
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch, args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if args.strict and not manifest["strict_success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
