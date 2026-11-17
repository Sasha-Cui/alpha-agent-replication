#!/usr/bin/env python3
"""Lint every Python file, preserving only exact recorded immutable-source debt.

The legacy manifest is not an exclusion list: every file still runs through Ruff.
An allowed diagnostic requires unchanged file bytes and exact per-rule counts.
All unlisted files and findings remain strict. There is no baseline-update mode.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys


LEGACY_RULES = frozenset({"E401", "E402", "E701", "E702", "E731", "E741", "F401", "F541", "F841"})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_diagnostics(root: Path, diagnostics: list[dict], baseline: dict) -> list[str]:
    """Reject new findings or any drift in an explicitly frozen source entry."""
    errors = []
    current = defaultdict(Counter)
    for diagnostic in diagnostics:
        path = Path(diagnostic["filename"])
        if not path.is_absolute():
            path = root / path
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            errors.append("Ruff returned a path outside the repository: " + str(path))
            continue
        current[relative][diagnostic["code"]] += 1

    recorded = baseline["files"]
    for relative, record in recorded.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.parts[0] not in {"src", "scripts", "tests"}:
            errors.append("Invalid frozen-source path: " + relative)
            continue
        expected = Counter(record["diagnostics"])
        if set(expected) - LEGACY_RULES:
            errors.append("Unsupported legacy rule in frozen record: " + relative)
        source = root / relative
        if not source.is_file() or source.is_symlink():
            errors.append("Frozen source is missing or replaced by a symlink: " + relative)
        elif sha256(source) != record["sha256"]:
            errors.append("Frozen source bytes changed; preserve/version it rather than rebaseline silently: " + relative)
        if current.pop(relative, Counter()) != expected:
            errors.append("Frozen diagnostic counts changed: " + relative)

    for relative, counts in sorted(current.items()):
        errors.append("New lint findings: {} {}".format(relative, dict(sorted(counts.items()))))
    recorded_count = sum(sum(item["diagnostics"].values()) for item in recorded.values())
    if recorded_count != baseline["diagnostic_count"]:
        errors.append("Frozen manifest diagnostic total is inconsistent.")
    return errors


def check(root: Path, baseline_path: Path, ruff_binary: Path | None = None) -> dict:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline["schema_version"] != 1 or baseline["scope"] != ["src", "scripts", "tests"]:
        raise ValueError("Unsupported frozen lint policy or lint scope.")
    if sha256(root / "pyproject.toml") != baseline["configuration_sha256"]:
        raise ValueError("Lint configuration changed; explicitly review the frozen-source policy.")
    command = [str(ruff_binary)] if ruff_binary else [sys.executable, "-m", "ruff"]
    version = subprocess.run(command + ["--version"], check=True, capture_output=True, text=True).stdout.strip()
    if version != baseline["ruff_version"]:
        raise ValueError("Expected {}, found {}.".format(baseline["ruff_version"], version))
    run = subprocess.run(
        command + ["check", "src", "scripts", "tests", "--output-format", "json"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if run.returncode not in (0, 1):
        raise RuntimeError("Ruff failed before diagnostics: " + run.stderr)
    diagnostics = json.loads(run.stdout)
    errors = compare_diagnostics(root, diagnostics, baseline)
    return {
        "status": "FAIL" if errors else "PASS",
        "ruff_version": version,
        "configured_source_script_test_scope_linted": True,
        "unchanged_historical_files": len(baseline["files"]),
        "recorded_historical_diagnostics": baseline["diagnostic_count"],
        "current_diagnostics": len(diagnostics),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--ruff-binary", type=Path, help="Use an existing pinned Ruff binary; never installs packages.")
    args = parser.parse_args()
    root = args.root.resolve()
    baseline = args.baseline or root / "docs/ci/frozen_lint_baseline.json"
    try:
        result = check(root, baseline, args.ruff_binary)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
