#!/usr/bin/env python3
"""Validate the current public repository and canonical ICAIF submission.

This is the repository-level entry point. It checks the publication boundary,
rebuilds the collaborator handoff in a temporary directory, runs the canonical
paper validators, and executes the test suite without rewriting tracked files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


CANONICAL_PDF = Path("output/pdf/icaif2026_submission.pdf")
CANONICAL_SOURCE = Path("docs/paper/icaif2026_submission.tex")
HANDOFF_FILES = (
    Path("paper_runs/handoff/strategy_result_index.csv"),
    Path("paper_runs/handoff/manifest.json"),
)
REQUIRED_PATHS = (
    Path("README.md"),
    Path("COLLABORATOR_HANDOFF.md"),
    Path("docs/VALIDATION_STATUS.md"),
    Path("docs/SCIENTIFIC_AUDIT.md"),
    Path("docs/EXPERIMENT_INDEX.md"),
    Path("docs/DATA_AND_ARTIFACTS.md"),
    Path(".github/workflows/quality.yml"),
    Path("paper_runs/submission_evidence/replication_scope/mapping_scope_ledger.csv"),
    CANONICAL_SOURCE,
    CANONICAL_PDF,
    *HANDOFF_FILES,
)
EXCLUDED_TRACKED_PREFIXES = (
    "external_repos/",
    "external_repos_code_links/",
    "literature_review/papers/",
    "tmp/",
)
EXCLUDED_TRACKED_SUFFIXES = (".parquet", ".pyc", ".pyo")
MAX_TRACKED_BYTES = 100 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )


def git_paths(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [Path(value.decode("utf-8")) for value in completed.stdout.split(b"\0") if value]


def validate_publication_boundary(root: Path) -> dict[str, int]:
    missing = [path.as_posix() for path in REQUIRED_PATHS if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError(f"missing canonical repository files: {missing}")

    tracked = git_paths(root)
    tracked_names = {path.as_posix() for path in tracked}
    excluded = sorted(
        name
        for name in tracked_names
        if name.startswith(EXCLUDED_TRACKED_PREFIXES) or name.endswith(EXCLUDED_TRACKED_SUFFIXES)
    )
    if excluded:
        raise AssertionError(f"excluded local/raw files are tracked: {excluded}")

    output_pdfs = sorted(name for name in tracked_names if name.startswith("output/") and name.endswith(".pdf"))
    if output_pdfs != [CANONICAL_PDF.as_posix()]:
        raise AssertionError(f"ambiguous tracked submission PDFs: {output_pdfs}")

    oversized = sorted(
        (path.stat().st_size, relative.as_posix())
        for relative in tracked
        if (path := root / relative).is_file() and path.stat().st_size > MAX_TRACKED_BYTES
    )
    if oversized:
        raise AssertionError(f"tracked files exceed 100 MiB: {oversized}")

    return {
        "tracked_files": len(tracked),
        "tracked_output_pdfs": len(output_pdfs),
        "oversized_tracked_files": len(oversized),
    }


def validate_handoff(root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="alpha-handoff-check-") as temp:
        output_dir = Path(temp) / "handoff"
        run(
            [
                sys.executable,
                str(root / "scripts/build_collaborator_handoff.py"),
                "--root",
                str(root),
                "--output-dir",
                str(output_dir),
            ],
            cwd=root,
        )
        generated_index = output_dir / "strategy_result_index.csv"
        tracked_index = root / HANDOFF_FILES[0]
        if generated_index.read_bytes() != tracked_index.read_bytes():
            raise AssertionError("tracked collaborator index is stale")

        generated_manifest = json.loads((output_dir / "manifest.json").read_text())
        tracked_manifest = json.loads((root / HANDOFF_FILES[1]).read_text())
        generated_manifest["outputs"]["strategy_result_index"]["path"] = tracked_manifest[
            "outputs"
        ]["strategy_result_index"]["path"]
        if generated_manifest != tracked_manifest:
            raise AssertionError("tracked collaborator manifest is stale")


def pdf_page_count(pdf: Path) -> int:
    completed = subprocess.run(
        ["pdfinfo", str(pdf)],
        check=True,
        text=True,
        capture_output=True,
    )
    match = re.search(r"^Pages:\s+(\d+)$", completed.stdout, flags=re.MULTILINE)
    if not match:
        raise AssertionError("pdfinfo did not report a page count")
    return int(match.group(1))


def worktree_clean(root: Path) -> bool:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return not completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    pdf = (args.pdf or root / CANONICAL_PDF).resolve()
    boundary = validate_publication_boundary(root)
    validate_handoff(root)
    run(
        [
            sys.executable,
            str(root / "scripts/validate_icaif_submission.py"),
            "--root",
            str(root),
            "--pdf",
            str(pdf),
        ],
        cwd=root,
    )
    if not args.skip_tests:
        run([sys.executable, "-m", "pytest", "-q"], cwd=root)

    summary = {
        **boundary,
        "canonical_source_sha256": sha256(root / CANONICAL_SOURCE),
        "canonical_pdf_sha256": sha256(pdf),
        "canonical_pdf_pages": pdf_page_count(pdf),
        "handoff_rows": 50,
        "handoff_papers": 40,
        "worktree_clean": worktree_clean(root),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("submission package validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
