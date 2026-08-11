#!/usr/bin/env python3
"""Build the anonymous ICAIF 2026 PDF with the vendored ACM 2.19 template."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "docs" / "paper"
TEMPLATE = PAPER / "acm_template_2_19"
OUTPUT = ROOT / "output" / "pdf" / "icaif2026_submission.pdf"
EXPECTED_CLASS_SHA256 = "2f949e6e3f2a79f2cdc218b9dcdbaa7dd451adb4ee0be1af6dc7ebe00b318ea7"
EXPECTED_BST_SHA256 = "8ec002c927068bfc5b3cfe71b66aa4767b9e485530ac3c67ba5c064df4c2e6ac"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(*command: str, environment: dict[str, str]) -> None:
    completed = subprocess.run(
        command,
        cwd=PAPER,
        env=environment,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if completed.returncode:
        print(completed.stdout)
        print(completed.stderr)
        raise subprocess.CalledProcessError(completed.returncode, command)


def main() -> int:
    for script in (
        "build_paper_evidence_routes.py",
        "build_strict_proxy_fidelity_audit.py",
    ):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, check=True
        )
    class_file = TEMPLATE / "acmart.cls"
    bst_file = TEMPLATE / "ACM-Reference-Format.bst"
    if sha256(class_file) != EXPECTED_CLASS_SHA256:
        raise RuntimeError("vendored acmart.cls does not match ACM 2.19 production release")
    if sha256(bst_file) != EXPECTED_BST_SHA256:
        raise RuntimeError("vendored ACM bibliography style checksum mismatch")

    environment = os.environ.copy()
    environment.pop("TEXMFHOME", None)
    environment["TEXINPUTS"] = f"{TEMPLATE}//:{environment.get('TEXINPUTS', '')}"
    environment["BSTINPUTS"] = f"{TEMPLATE}//:{environment.get('BSTINPUTS', '')}"

    stem = "icaif2026_submission"
    for suffix in (".aux", ".bbl", ".blg", ".log", ".out"):
        candidate = PAPER / f"{stem}{suffix}"
        if candidate.is_file():
            candidate.unlink()

    latex = ("pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"{stem}.tex")
    run(*latex, environment=environment)
    run("bibtex", stem, environment=environment)
    run(*latex, environment=environment)
    run(*latex, environment=environment)

    built = PAPER / f"{stem}.pdf"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, OUTPUT)
    result = {
        "pdf": str(OUTPUT),
        "pdf_sha256": sha256(OUTPUT),
        "template": "acmart 2.19 (2026-06-27)",
        "template_sha256": sha256(class_file),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
