from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_icaif2026_format.py"
SPEC = importlib.util.spec_from_file_location("validate_icaif2026_format", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def poppler_fixture(*command: str) -> str:
    if command[0] == "pdfinfo":
        return """Title:
Author: Anonymous Author(s)
Creator: LaTeX with acmart 2026/06/27 v2.19
Pages:          7
Page size:       612 x 792 pts (letter)
"""
    if command[0] == "pdftotext":
        return (
            "Anonymous Author(s)\n"
            "Do Financial LLM Agents Discover New Alpha?\n"
            "References\n"
        )
    if command[0] == "pdffonts":
        return """name type encoding emb sub uni object ID
------------------------------------------------------
ABC Type 1 Custom yes yes yes 1 0
"""
    raise AssertionError(f"unexpected command: {command}")


def run_validator(
    monkeypatch,
    capsys,
    pdf: Path,
    *extra_args: str,
) -> tuple[int, str]:
    monkeypatch.setattr(MODULE, "command_text", poppler_fixture)
    monkeypatch.setattr(
        sys,
        "argv",
        ["validate_icaif2026_format.py", "--pdf", str(pdf), *extra_args],
    )
    status = MODULE.main()
    return status, capsys.readouterr().out


def test_copied_repository_without_build_log_passes_artifact_audit(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    clone_root = tmp_path / "fresh-clone"
    copied_script = clone_root / "scripts/validate_icaif2026_format.py"
    copied_script.parent.mkdir(parents=True)
    shutil.copy2(SCRIPT, copied_script)
    for relative_path in (
        Path("docs/paper/icaif2026_submission.tex"),
        Path("docs/paper/acm_template_2_19/acmart.cls"),
        Path("docs/paper/acm_template_2_19/ACM-Reference-Format.bst"),
    ):
        destination = clone_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative_path, destination)

    copied_spec = importlib.util.spec_from_file_location(
        "copied_validate_icaif2026_format", copied_script
    )
    copied_module = importlib.util.module_from_spec(copied_spec)
    assert copied_spec.loader is not None
    copied_spec.loader.exec_module(copied_module)

    assert not list(clone_root.rglob("*.log"))
    pdf = clone_root / "submission.pdf"
    pdf.write_bytes(b"%PDF fixture")
    monkeypatch.setattr(copied_module, "command_text", poppler_fixture)
    monkeypatch.setattr(
        sys, "argv", ["validate_icaif2026_format.py", "--pdf", str(pdf)]
    )
    status = copied_module.main()
    output = capsys.readouterr().out
    assert status == 0
    assert "ICAIF ARTIFACT AUDIT PASSED: 62 checks" in output
    assert "build-log checks were not requested" in output


def test_explicit_missing_build_log_fails(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    pdf = tmp_path / "submission.pdf"
    pdf.write_bytes(b"%PDF fixture")
    missing = tmp_path / "missing.log"
    status, output = run_validator(
        monkeypatch, capsys, pdf, "--log", str(missing), "--require-build-log"
    )
    assert status == 1
    assert "explicit LaTeX build log is missing" in output


def test_explicit_bad_build_log_fails(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    pdf = tmp_path / "submission.pdf"
    pdf.write_bytes(b"%PDF fixture")
    log = tmp_path / "submission.log"
    log.write_text(
        "Class acmart Info: Using format sigconf\n"
        "Using anonymous mode\n"
        "Overfull \\hbox\n",
        encoding="utf-8",
    )
    status, output = run_validator(
        monkeypatch, capsys, pdf, "--log", str(log), "--require-build-log"
    )
    assert status == 1
    assert "LaTeX log contains 'Overfull'" in output
    assert "across 71 checks" in output
