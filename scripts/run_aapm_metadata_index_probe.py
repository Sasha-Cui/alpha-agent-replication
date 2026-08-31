#!/usr/bin/env python3
"""Advance AAPM analysis through its recoverable metadata/model boundary.

The release ships WSJ metadata whose dictionary keys encode article paths, but
omits ``Data/library/index.csv``.  This driver reconstructs that index from the
released keys, points a temporary source archive at an immutable paper-era-
compatible BGE snapshot, blocks network access, and runs ``analysis.py`` twice.
The expected next boundary is the first missing private ``news_analysis`` record;
the probe does not invent article bodies, topics, tickers, embeddings, or results.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


SOURCE_HEAD = "cc54e4337fcd4089dc69e4a1173e82a675648475"
ANALYSIS_SHA256 = "4e93971b07f30cd890dfde31e92e42482ba08c63604d72c1f792f6ee67bc6c2e"
CONFIG_SHA256 = "7912a17f37f8a1bac3c8e679439c404ac927f67eb4ffa0e865645ee531058225"
METADATA_SHA256 = "0cf4923806f6c2d6b87aa06cae6a1651aa6ba4e146f90ee74d941592bdabc641"
EXPECTED_ROWS = 65_733
EXPECTED_INDEX_BYTES = 1_901_562
EXPECTED_INDEX_SHA256 = "aabf06376b8cf51ea02a42f90cc0aab0abcf46ed99ce52495aa70a8b5d9f149c"
MODEL_REPO = "BAAI/bge-large-en-v1.5"
MODEL_REVISION = "d4aa6901d3a41ba39fb536a557fa166f842b0e09"
MODEL_LAST_MODIFIED_UTC = "2024-02-21T02:51:44.000Z"
MODEL_MANIFEST_SHA256 = "7b0b0c8f2a12c68ef6160da7d9e2b0a37404d35f3eded172a52856c0b6959a67"
MODEL_FILES = {
    "1_Pooling/config.json": (191, "e54c164a07274f2eb45bb724f54a79d1efcc90c41573887cd9a29aeee0597352"),
    "config.json": (779, "446712fac367857b4b1302762fe1cd7bfa8b3c4b77b4dc5d77c4025407660896"),
    "config_sentence_transformers.json": (124, "940d5f50db195fa6e5e6a4f122c095f77880de259d74b14a65779ed48bdd7c56"),
    "model.safetensors": (1_340_616_616, "45e1954914e29bd74080e6c1510165274ff5279421c89f76c418878732f64ae7"),
    "modules.json": (349, "84e40c8e006c9b1d6c122e02cba9b02458120b5fb0c87b746c41e0207cf642cf"),
    "sentence_bert_config.json": (52, "84e39fda68ccbff05bfa723ae9c0e70e23e2ec373b76e0f8c6e71af72a693cbf"),
    "special_tokens_map.json": (125, "b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3"),
    "tokenizer.json": (711_396, "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66"),
    "tokenizer_config.json": (366, "9261e7d79b44c8195c1cada2b453e55b00aeb81e907a6664974b4d7776172ab3"),
    "vocab.txt": (231_508, "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3"),
}
MONTHS = {
    name: f"{number:02d}"
    for number, name in enumerate(
        (
            "",
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        )
    )
    if name
}

PROBE_PROGRAM = r'''
import aiohttp
import atexit
import httpx
import json
import os
import requests
import runpy
import socket
import sys
from pathlib import Path

attempts = []
def blocked(*args, **kwargs):
    attempts.append(repr(args[1:] if len(args) > 1 else args))
    raise RuntimeError("network disabled during AAPM metadata-index audit")
def write_attempts():
    Path(os.environ["AAPM_NETWORK_AUDIT_PATH"]).write_text(
        json.dumps(attempts, sort_keys=True) + "\n", encoding="utf-8"
    )
httpx.Client.send = blocked
httpx.AsyncClient.send = blocked
requests.sessions.Session.send = blocked
aiohttp.ClientSession._request = blocked
socket.socket.connect = blocked
atexit.register(write_attempts)
sys.argv = ["analysis.py", "0"]
runpy.run_path("analysis.py", run_name="__main__")
'''


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bytes_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git(source: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(source), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return result.stdout


def model_manifest(model_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    lines = []
    for name, (expected_bytes, expected_sha) in sorted(MODEL_FILES.items()):
        path = model_root / name
        if not path.is_file() or path.stat().st_size != expected_bytes or sha256(path) != expected_sha:
            raise RuntimeError(f"AAPM BGE model file changed: {name}")
        rows.append(
            {
                "path": name,
                "bytes": expected_bytes,
                "sha256": expected_sha,
                "paper_result_credit": False,
            }
        )
        lines.append(f"{name}\t{expected_bytes}\t{expected_sha}")
    manifest_hash = bytes_sha256("\n".join(lines).encode())
    if manifest_hash != MODEL_MANIFEST_SHA256:
        raise RuntimeError("AAPM BGE model manifest changed")
    return rows, {
        "repository": MODEL_REPO,
        "revision": MODEL_REVISION,
        "official_api_last_modified_utc": MODEL_LAST_MODIFIED_UTC,
        "last_modified_before_paper_source_cutoff": True,
        "files": len(rows),
        "bytes": sum(int(row["bytes"]) for row in rows),
        "manifest_sha256": manifest_hash,
        "duplicate_pytorch_and_onnx_weights_downloaded": False,
        "paper_result_credit": False,
    }


def reconstruct_index(source: Path, output: Path) -> dict[str, Any]:
    metadata = json.loads((source / "data/wsj_metadata.json").read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or len(metadata) != EXPECTED_ROWS:
        raise RuntimeError("AAPM metadata census changed")
    years: Counter[str] = Counter()
    rows = []
    for path in metadata:
        parts = path.split("/")
        if len(parts) != 4 or parts[1] not in MONTHS:
            raise RuntimeError(f"AAPM metadata key schema changed: {path}")
        date = f"{parts[0]}-{MONTHS[parts[1]]}-{int(parts[2]):02d}"
        years[date[:4]] += 1
        rows.append({"date": date, "path": path})
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["date", "path"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    if output.stat().st_size != EXPECTED_INDEX_BYTES or sha256(output) != EXPECTED_INDEX_SHA256:
        raise RuntimeError("AAPM reconstructed metadata index changed")
    return {
        "rows": len(rows),
        "columns": ["date", "path"],
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
        "minimum_date": min(row["date"] for row in rows),
        "maximum_date": max(row["date"] for row in rows),
        "year_counts": dict(sorted(years.items())),
        "first_row": rows[0],
        "last_row": rows[-1],
        "path_is_exact_released_metadata_key": True,
        "date_is_deterministically_derived_from_path": True,
    }


def run_once(
    source: Path,
    index_path: Path,
    model_root: Path,
    python_wrapper: Path,
    work_root: Path | None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(dir=work_root) as temporary:
        temp = Path(temporary)
        archive_path = temp / "source.tar"
        archive_path.write_bytes(bytes(git(source, "archive", "HEAD", binary=True)))
        extracted = temp / "source"
        extracted.mkdir()
        with tarfile.open(archive_path) as archive:
            archive.extractall(extracted, filter="data")
        library = extracted / "Data/library"
        library.mkdir(parents=True)
        (library / "index.csv").write_bytes(index_path.read_bytes())
        config = extracted / "config.yaml"
        config_text = config.read_text(encoding="utf-8")
        old = "embed: BAAI/bge-large-en-v1.5"
        if config_text.count(old) != 1:
            raise RuntimeError("AAPM embedding-model config reference changed")
        config.write_text(
            config_text.replace(old, f"embed: {model_root}"),
            encoding="utf-8",
        )
        attempts_path = temp / "network_attempts.json"
        env = {
            key: value
            for key, value in os.environ.items()
            if key
            not in {
                "ANTHROPIC_API_KEY",
                "AZURE_OPENAI_API_KEY",
                "OPENAI_API_KEY",
                "PYTHONPATH",
                "SK_PROJ_KEY",
            }
        }
        env["AAPM_NETWORK_AUDIT_PATH"] = str(attempts_path)
        completed = subprocess.run(
            [str(python_wrapper), "-c", PROBE_PROGRAM],
            cwd=extracted,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        attempts = json.loads(attempts_path.read_text(encoding="utf-8"))
        stderr = completed.stderr.replace("\r", "\n")
        if (
            completed.returncode != 1
            or attempts
            or "KeyError: 'Tickers'" not in stderr
            or "Processing:" not in stderr
            or "huggingface_hub.errors" in stderr
            or "LocalEntryNotFoundError" in stderr
        ):
            raise RuntimeError(
                "AAPM metadata-index analysis boundary changed: "
                f"returncode={completed.returncode}, attempts={attempts}, "
                f"tail={stderr[-2000:]}"
            )
        first_path = "2021/october/1/1"
        missing_analysis = (
            extracted
            / "Data/library/news_analysis"
            / f"{first_path.replace('/', '_')}.json"
        )
        if missing_analysis.exists():
            raise RuntimeError("AAPM private news-analysis payload unexpectedly exists")
        return {
            "returncode": completed.returncode,
            "network_attempts": attempts,
            "embedding_model_constructed_offline": True,
            "analysis_loop_started": True,
            "chunk_start": 0,
            "chunk_end": 5_000,
            "first_record_date": "2021-10-01",
            "first_record_path": first_path,
            "first_missing_private_path": (
                "Data/library/news_analysis/2021_october_1_1.json"
            ),
            "first_observed_exception": "KeyError: 'Tickers'",
            "missing_required_fields": ["Tickers", "Topics", "Content"],
            "llm_calls_made": 0,
            "paper_result_credit": False,
        }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--embedding-model-root", type=Path, required=True)
    parser.add_argument("--python-wrapper", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--work-root", type=Path)
    args = parser.parse_args()

    source = args.source_root.resolve()
    model_root = args.embedding_model_root.resolve()
    python_wrapper = args.python_wrapper.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if str(git(source, "rev-parse", "HEAD")).strip() != SOURCE_HEAD:
        raise RuntimeError("AAPM source HEAD changed")
    if (
        sha256(source / "analysis.py") != ANALYSIS_SHA256
        or sha256(source / "config.yaml") != CONFIG_SHA256
        or sha256(source / "data/wsj_metadata.json") != METADATA_SHA256
    ):
        raise RuntimeError("AAPM metadata-index source pins changed")
    tracked_before = str(git(source, "status", "--porcelain", "--untracked-files=no"))
    if tracked_before:
        raise RuntimeError("AAPM source checkout has tracked modifications")

    model_rows, model = model_manifest(model_root)
    index_path = output / "aapm_reconstructed_metadata_index.csv"
    index = reconstruct_index(source, index_path)
    runs = [
        run_once(
            source,
            index_path,
            model_root,
            python_wrapper,
            args.work_root,
        )
        for _ in range(2)
    ]
    if runs[0] != runs[1]:
        raise RuntimeError("AAPM metadata-index analysis probe is nondeterministic")
    if str(git(source, "status", "--porcelain", "--untracked-files=no")) != tracked_before:
        raise RuntimeError("AAPM source checkout changed during metadata-index probe")

    evidence = {
        "source_head": SOURCE_HEAD,
        "source_files_modified": False,
        "source_pins": {
            "analysis_sha256": ANALYSIS_SHA256,
            "config_sha256": CONFIG_SHA256,
            "metadata_sha256": METADATA_SHA256,
        },
        "reconstructed_index": index,
        "embedding_model_snapshot": model,
        "execution_runs": 2,
        "runs": runs,
        "analysis_runner_completed": False,
        "paper_inputs_recovered": False,
        "paper_result_cells_reproduced": 0,
        "paper_result_credit": False,
    }
    (output / "aapm_metadata_index_probe.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(output / "aapm_embedding_model_snapshot.csv", model_rows)
    write_csv(
        output / "aapm_metadata_index_conformance.csv",
        [
            {
                "dimension": "released_metadata_index",
                "released_state": "65,733 metadata records with date-encoded dictionary keys",
                "audit_adapter": "date/path index reconstructed deterministically",
                "execution_outcome": "analysis.py accepts 65,733-row index",
                "paper_result_credit": False,
            },
            {
                "dimension": "embedding_model",
                "released_state": "unpinned BAAI/bge-large-en-v1.5 reference",
                "audit_adapter": f"immutable {MODEL_REVISION} snapshot; 10 minimal files",
                "execution_outcome": "1,341,561,506-byte model constructs offline",
                "paper_result_credit": False,
            },
            {
                "dimension": "analysis_entrypoint",
                "released_state": "missing index, article analyses, embeddings, and bodies",
                "audit_adapter": "index plus immutable embedding model only; network blocked",
                "execution_outcome": "2/2 reach first record then KeyError: Tickers",
                "paper_result_credit": False,
            },
            {
                "dimension": "next_private_boundary",
                "released_state": "news_analysis JSONs absent from every public artifact",
                "audit_adapter": "none",
                "execution_outcome": "Tickers, Topics, and Content remain unavailable",
                "paper_result_credit": False,
            },
        ],
    )
    print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
