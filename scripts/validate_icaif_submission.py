#!/usr/bin/env python3
"""Run the current ICAIF 2026 format and evidence-validation gates.

This command is retained as the stable entry point used by older automation.
The authoritative checks now live in ``validate_icaif2026_format.py`` and
``validate_icaif_major_revision.py`` so obsolete pre-revision expectations
cannot contradict the manuscript's locked evidence boundary.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--bbl", type=Path)
    parser.add_argument("--require-build-log", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    pdf = (args.pdf or root / "output/pdf/icaif2026_submission.pdf").resolve()
    format_command = [
        sys.executable,
        str(root / "scripts/validate_icaif2026_format.py"),
        "--pdf",
        str(pdf),
    ]
    if args.log:
        format_command.extend(("--log", str(args.log.resolve())))
    if args.require_build_log:
        format_command.append("--require-build-log")
    evidence_command = [
        sys.executable,
        str(root / "scripts/validate_icaif_major_revision.py"),
        "--root",
        str(root),
        "--pdf",
        str(pdf),
    ]
    if args.bbl:
        evidence_command.extend(("--bbl", str(args.bbl.resolve())))
    commands = (
        format_command,
        evidence_command,
    )
    for command in commands:
        subprocess.run(command, check=True)

    print("ICAIF submission validation passed: format and locked evidence verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
