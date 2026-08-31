#!/usr/bin/env python3
"""Execute QuantaAlpha's released factor-coder test with minimal source adapters.

The public test names an unshipped ``template_debug.jinjia2`` although the same
directory ships ``template.jinjia2``.  Its expression also requires ``$return``,
while the official pinned debug HDF contains price/volume columns plus ``$factor``.
This driver runs the unmodified test from a temporary Git archive, aliases the
shipped template byte-for-byte, and derives ``$return`` with the exact formula
used by the released factor calculator.  These adapters exercise an attributable
native component; they do not reproduce a published QuantaAlpha result.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import subprocess
import sys
import tarfile
import tempfile
import warnings
from pathlib import Path
from typing import Any

import pandas as pd


SOURCE_COMMIT = "b7ceb27b1001261d7a95b209a963664ae1f8ab23"
TEST_SHA256 = "df4473a6c38603183be4da9ca05b844cd1173e525c83f3843454047a97525eba"
TEMPLATE_SHA256 = "838ef362ae15474358410d54f79d52054b4dd2b1d4db8b5b3f30fd3b87af0829"
REQUIREMENTS_SHA256 = "6d4c6587b1ffdac4bf446b9d4e5e3e4d888948a7609e2847dd3ccc91f86df729"
DEBUG_H5_SHA256 = "03816baa04a9ccefeaca8ccd6968c30f6a9a879330ae496d6fa19d6cd3208ebc"
EXPECTED_INPUT_ROWS = 48_700
EXPECTED_INPUT_COLUMNS = ["$open", "$close", "$high", "$low", "$volume", "$factor"]
EXPECTED_RETURN_CANONICAL_SHA256 = "3e49b0d8342a2345b6afd3a080a3ea7a1c6536bd9c479aa68351948238fbd6f5"
EXPECTED_STDOUT_SHA256 = "2be2c6101124b42e8d2e85e377fc92d6decbbb81aeac48bd000083770673a265"
EXPECTED_OUTPUT_CANONICAL_SHA256 = "6b894e78abebc6e83022e95241a2753a0edb8343cea79e974becdd7e0433cd53"
EXPECTED_OUTPUT_FINITE = 48_600
EXPECTED_OUTPUT_NAN = 100
EXPECTED_WARNING = "llama is not installed."

NETWORK_GUARD = r'''from __future__ import annotations
import atexit
import json
import os
import socket
from pathlib import Path

attempts = []
def blocked_connect(_self, address):
    attempts.append(repr(address))
    raise RuntimeError(f"network disabled during QuantaAlpha audit: {address!r}")
def write_attempts():
    Path(os.environ["QUANTAALPHA_NETWORK_AUDIT_PATH"]).write_text(
        json.dumps(attempts, sort_keys=True) + "\n", encoding="utf-8"
    )
socket.socket.connect = blocked_connect
atexit.register(write_attempts)
'''


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bytes_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_series(series: pd.Series) -> tuple[str, int, int]:
    lines = []
    finite = 0
    for index, value in series.items():
        parts = index if isinstance(index, tuple) else (index,)
        key = "|".join(map(str, parts))
        numeric = float(value)
        if math.isfinite(numeric):
            encoded = format(numeric, ".17g")
            finite += 1
        else:
            encoded = "nan"
        lines.append(f"{key}|{encoded}")
    return bytes_sha256("\n".join(lines).encode()), finite, len(series) - finite


def git(source_root: Path, *args: str, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return completed.stdout


def normalize_stderr(stderr: str) -> list[str]:
    messages = []
    for line in stderr.splitlines():
        if " - " in line:
            messages.append(line.rsplit(" - ", 1)[1])
        elif line.strip():
            messages.append(line.strip())
    return messages


def environment_evidence(python: Path) -> tuple[dict[str, Any], str]:
    check = subprocess.run(
        [str(python), "-m", "pip", "check"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if check != "No broken requirements found.":
        raise RuntimeError(f"QuantaAlpha dependency check changed: {check}")
    freeze_lines = sorted(
        line
        for line in subprocess.run(
            [str(python), "-m", "pip", "freeze", "--all"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        if line
    )
    freeze = "\n".join(freeze_lines) + "\n"
    versions = {
        name: importlib.metadata.version(name)
        for name in ("jinja2", "numpy", "pandas", "pyqlib", "rdagent", "seaborn", "tables")
    }
    if versions["rdagent"] != "0.8.0" or versions["pyqlib"] != "0.9.7":
        raise RuntimeError(f"QuantaAlpha pinned dependency versions changed: {versions}")
    return (
        {
            "python": sys.version.split()[0],
            "pip_check": check,
            "freeze_lines": len(freeze_lines),
            "freeze_sha256": bytes_sha256(freeze.encode()),
            "resolved_versions": versions,
        },
        freeze,
    )


def prepare_input(debug_h5: Path, target: Path) -> dict[str, Any]:
    frame = pd.read_hdf(debug_h5, key="data")
    if (
        frame.shape != (EXPECTED_INPUT_ROWS, len(EXPECTED_INPUT_COLUMNS))
        or list(frame.columns) != EXPECTED_INPUT_COLUMNS
        or list(frame.index.names) != ["datetime", "instrument"]
    ):
        raise RuntimeError("QuantaAlpha official debug HDF schema changed")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        returns = frame.groupby("instrument")["$close"].pct_change().fillna(0)
    return_hash, finite, missing = canonical_series(returns)
    if (
        return_hash != EXPECTED_RETURN_CANONICAL_SHA256
        or finite != EXPECTED_INPUT_ROWS
        or missing != 0
    ):
        raise RuntimeError("QuantaAlpha derived return adapter changed")
    frame["$return"] = returns
    frame.to_hdf(target, key="data", mode="w")
    return {
        "source_rows": EXPECTED_INPUT_ROWS,
        "source_columns": EXPECTED_INPUT_COLUMNS,
        "adapted_columns": list(frame.columns),
        "return_formula": (
            "df.groupby('instrument')['$close'].pct_change().fillna(0)"
        ),
        "return_rows": len(returns),
        "return_finite_rows": finite,
        "return_canonical_sha256": return_hash,
    }


def run_unadapted_once(
    source_root: Path,
    debug_h5: Path,
    python: Path,
    work_root: Path | None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(dir=work_root) as temporary:
        temp = Path(temporary)
        archive_path = temp / "source.tar"
        archive_path.write_bytes(bytes(git(source_root, "archive", "HEAD", binary=True)))
        extracted = temp / "source"
        extracted.mkdir()
        with tarfile.open(archive_path) as archive:
            archive.extractall(extracted, filter="data")
        coder = extracted / "quantaalpha/factors/coder"
        (coder / "daily_pv.h5").write_bytes(debug_h5.read_bytes())

        guard = temp / "sitecustomize.py"
        guard.write_text(NETWORK_GUARD, encoding="utf-8")
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
        env.update(
            {
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": os.pathsep.join((str(temp), str(extracted))),
                "QUANTAALPHA_NETWORK_AUDIT_PATH": str(attempts_path),
            }
        )
        completed = subprocess.run(
            [str(python), str(coder / "test.py")],
            cwd=coder,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        attempts = json.loads(attempts_path.read_text(encoding="utf-8"))
        if (
            completed.returncode != 1
            or attempts
            or completed.stdout
            or "FileNotFoundError" not in completed.stderr
            or "template_debug.jinjia2" not in completed.stderr
            or "No module named 'jinja2'" in completed.stderr
        ):
            raise RuntimeError(
                "QuantaAlpha unadapted upstream-test boundary changed: "
                f"returncode={completed.returncode}, attempts={attempts}, "
                f"stdout={completed.stdout[-500:]}, stderr={completed.stderr[-1000:]}"
            )
        return {
            "returncode": completed.returncode,
            "dependency_import_passed": True,
            "failure": "missing template_debug.jinjia2",
            "network_attempts": attempts,
            "paper_result_credit": False,
        }


def run_once(
    source_root: Path,
    debug_h5: Path,
    python: Path,
    work_root: Path | None,
) -> tuple[dict[str, Any], str]:
    with tempfile.TemporaryDirectory(dir=work_root) as temporary:
        temp = Path(temporary)
        archive_path = temp / "source.tar"
        archive_path.write_bytes(bytes(git(source_root, "archive", "HEAD", binary=True)))
        extracted = temp / "source"
        extracted.mkdir()
        with tarfile.open(archive_path) as archive:
            archive.extractall(extracted, filter="data")

        coder = extracted / "quantaalpha/factors/coder"
        template = coder / "template.jinjia2"
        alias = coder / "template_debug.jinjia2"
        alias.write_bytes(template.read_bytes())
        if sha256(alias) != TEMPLATE_SHA256:
            raise RuntimeError("QuantaAlpha debug-template alias changed")
        input_evidence = prepare_input(debug_h5, coder / "daily_pv.h5")

        guard = temp / "sitecustomize.py"
        guard.write_text(NETWORK_GUARD, encoding="utf-8")
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
        env.update(
            {
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": os.pathsep.join((str(temp), str(extracted))),
                "QUANTAALPHA_NETWORK_AUDIT_PATH": str(attempts_path),
            }
        )
        completed = subprocess.run(
            [str(python), str(coder / "test.py")],
            cwd=coder,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        attempts = json.loads(attempts_path.read_text(encoding="utf-8"))
        warnings_seen = normalize_stderr(completed.stderr)
        if completed.returncode != 0 or attempts or warnings_seen != [EXPECTED_WARNING]:
            raise RuntimeError(
                "QuantaAlpha upstream test boundary changed: "
                f"returncode={completed.returncode}, attempts={attempts}, "
                f"stderr={warnings_seen}, tail={completed.stderr[-1000:]}"
            )
        stdout_hash = bytes_sha256(completed.stdout.encode())
        if stdout_hash != EXPECTED_STDOUT_SHA256:
            raise RuntimeError("QuantaAlpha upstream test stdout changed")

        result_path = coder / "result.h5"
        series = pd.read_hdf(result_path, key="data")
        canonical_hash, finite, missing = canonical_series(series)
        if (
            len(series) != EXPECTED_INPUT_ROWS
            or finite != EXPECTED_OUTPUT_FINITE
            or missing != EXPECTED_OUTPUT_NAN
            or canonical_hash != EXPECTED_OUTPUT_CANONICAL_SHA256
        ):
            raise RuntimeError("QuantaAlpha upstream native factor output changed")
        return (
            {
                "returncode": completed.returncode,
                "network_attempts": attempts,
                "warning_messages": warnings_seen,
                "stdout_sha256": stdout_hash,
                "result_hdf_container_sha256": sha256(result_path),
                "result_rows": len(series),
                "result_finite_rows": finite,
                "result_nan_rows": missing,
                "result_canonical_sha256": canonical_hash,
                "result_minimum": float(series.min()),
                "result_maximum": float(series.max()),
                "result_mean": float(series.mean()),
                "result_sample_std": float(series.std()),
                "input_adapter": input_evidence,
            },
            completed.stdout,
        )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--debug-h5", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--work-root", type=Path)
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    debug_h5 = args.debug_h5.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    python = Path(sys.executable).absolute()
    if str(git(source_root, "rev-parse", "HEAD")).strip() != SOURCE_COMMIT:
        raise RuntimeError("QuantaAlpha source commit changed")
    test_path = source_root / "quantaalpha/factors/coder/test.py"
    template_path = source_root / "quantaalpha/factors/coder/template.jinjia2"
    requirements_path = source_root / "requirements.txt"
    if (
        sha256(test_path) != TEST_SHA256
        or sha256(template_path) != TEMPLATE_SHA256
        or sha256(requirements_path) != REQUIREMENTS_SHA256
        or sha256(debug_h5) != DEBUG_H5_SHA256
    ):
        raise RuntimeError("QuantaAlpha upstream-test primary-source pins changed")
    tracked_before = str(git(source_root, "status", "--porcelain", "--untracked-files=no"))
    if tracked_before:
        raise RuntimeError("QuantaAlpha source checkout has tracked modifications")

    environment, freeze = environment_evidence(python)
    unadapted = run_unadapted_once(
        source_root,
        debug_h5,
        python,
        args.work_root,
    )
    runs_and_logs = [
        run_once(source_root, debug_h5, python, args.work_root)
        for _ in range(2)
    ]
    runs = [item[0] for item in runs_and_logs]
    logs = [item[1] for item in runs_and_logs]
    if (
        logs[0] != logs[1]
        or runs[0]["result_canonical_sha256"]
        != runs[1]["result_canonical_sha256"]
        or runs[0]["input_adapter"] != runs[1]["input_adapter"]
    ):
        raise RuntimeError("QuantaAlpha upstream test is nondeterministic")
    for run in runs:
        del run["result_hdf_container_sha256"]
    if str(git(source_root, "status", "--porcelain", "--untracked-files=no")) != tracked_before:
        raise RuntimeError("QuantaAlpha source checkout changed during the audit")

    evidence = {
        "author_source_commit": SOURCE_COMMIT,
        "author_source_modified": False,
        "source_pins": {
            "test_path": "quantaalpha/factors/coder/test.py",
            "test_sha256": TEST_SHA256,
            "shipped_template_path": "quantaalpha/factors/coder/template.jinjia2",
            "shipped_template_sha256": TEMPLATE_SHA256,
            "requirements_sha256": REQUIREMENTS_SHA256,
            "official_debug_h5_sha256": DEBUG_H5_SHA256,
        },
        "environment": environment,
        "unadapted_test_execution": unadapted,
        "execution_runs": 2,
        "original_test_modified": False,
        "adapters": {
            "template_alias": (
                "template_debug.jinjia2 is a byte-identical temporary alias of the "
                "shipped template.jinjia2"
            ),
            "return_column": runs[0]["input_adapter"],
            "adapter_scope": "temporary Git-archive copies only",
        },
        "runs": runs,
        "canonical_outputs_identical": True,
        "raw_hdf_container_hashes_excluded": (
            "PyTables container metadata is not stable; indexed canonical values "
            "are hash-pinned instead"
        ),
        "native_upstream_test_passed": True,
        "native_factor_series_generated": True,
        "llm_or_market_api_called": False,
        "paper_experiment_executed": False,
        "published_result_cells_reproduced": 0,
        "paper_result_credit": False,
    }
    (output / "quantaalpha_upstream_test_execution.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "quantaalpha_upstream_environment_freeze.txt").write_text(
        freeze,
        encoding="utf-8",
    )
    for index, log in enumerate(logs, start=1):
        (output / f"quantaalpha_upstream_test_run_{index}.stdout.txt").write_text(
            log,
            encoding="utf-8",
        )
    write_csv(
        output / "quantaalpha_upstream_test_conformance.csv",
        [
            {
                "dimension": "declared_dependency_environment",
                "released_state": "requirements.txt pins rdagent 0.8.0; remaining packages unpinned",
                "audit_adapter": f"resolved {environment['freeze_lines']} package lines",
                "execution_outcome": environment["pip_check"],
                "paper_result_credit": False,
            },
            {
                "dimension": "debug_template",
                "released_state": "test.py requests missing template_debug.jinjia2",
                "audit_adapter": "byte-identical alias of shipped template.jinjia2",
                "execution_outcome": "template rendered in both runs",
                "paper_result_credit": False,
            },
            {
                "dimension": "return_input",
                "released_state": "official debug HDF lacks the test expression's $return column",
                "audit_adapter": "released instrument-level close pct_change formula",
                "execution_outcome": f"{EXPECTED_INPUT_ROWS} finite return rows",
                "paper_result_credit": False,
            },
            {
                "dimension": "original_upstream_test",
                "released_state": "unmodified test cannot run against shipped paths/schema",
                "audit_adapter": "two temporary copied-tree runs with network blocked",
                "execution_outcome": (
                    "unadapted full-environment run fails on missing template; "
                    "adapted 2/2 passed; zero network attempts"
                ),
                "paper_result_credit": False,
            },
            {
                "dimension": "native_factor_output",
                "released_state": "no published target or result lineage",
                "audit_adapter": "none beyond the two disclosed input/path repairs",
                "execution_outcome": (
                    f"{EXPECTED_INPUT_ROWS} rows; {EXPECTED_OUTPUT_FINITE} finite; "
                    f"canonical sha256 {EXPECTED_OUTPUT_CANONICAL_SHA256}"
                ),
                "paper_result_credit": False,
            },
        ],
    )
    print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
