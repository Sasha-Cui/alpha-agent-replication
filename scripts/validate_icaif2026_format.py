#!/usr/bin/env python3
"""Audit the final PDF against the manuscript-controlled ICAIF 2026 rules."""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "docs" / "paper"
EXPECTED_CLASS_SHA256 = "2f949e6e3f2a79f2cdc218b9dcdbaa7dd451adb4ee0be1af6dc7ebe00b318ea7"
EXPECTED_BST_SHA256 = "8ec002c927068bfc5b3cfe71b66aa4767b9e485530ac3c67ba5c064df4c2e6ac"
EXPECTED_TITLE = (
    "Can Public Artifacts Substantiate Financial-Agent Alpha? "
    "A 98-Work Evidence Audit and Descriptive Spanning Exercise"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command_text(*command: str) -> str:
    return subprocess.run(command, check=True, text=True, capture_output=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=ROOT / "output/pdf/icaif2026_submission.pdf")
    args = parser.parse_args()
    pdf = args.pdf.resolve()
    source_path = PAPER / "icaif2026_submission.tex"
    log_path = PAPER / "icaif2026_submission.log"
    failures: list[str] = []
    checks = 0

    def require(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(message)

    class_file = PAPER / "acm_template_2_19/acmart.cls"
    bst_file = PAPER / "acm_template_2_19/ACM-Reference-Format.bst"
    require(class_file.is_file(), "vendored acmart.cls is missing")
    require(bst_file.is_file(), "vendored ACM bibliography style is missing")
    if class_file.is_file():
        require(sha256(class_file) == EXPECTED_CLASS_SHA256, "acmart.cls is not production version 2.19")
    if bst_file.is_file():
        require(sha256(bst_file) == EXPECTED_BST_SHA256, "ACM bibliography style checksum mismatch")

    source = source_path.read_text(encoding="utf-8")
    require(source.startswith(r"\documentclass[sigconf,anonymous]{acmart}"),
            "first source line is not the required anonymous sigconf class")
    require("manuscript" not in source.splitlines()[0], "manuscript layout used instead of sigconf")
    require("authordraft" not in source.splitlines()[0], "authordraft watermark mode is enabled")
    require("review" not in source.splitlines()[0], "review line-number mode is enabled")
    require(r"\author{Anonymous Author(s)}" in source, "anonymous author label is missing")
    require(r"\affiliation{\institution{Anonymous Institution}}" in source,
            "anonymous affiliation label is missing")
    require(r"\acmConference[ICAIF '26]{7th ACM International Conference on AI in Finance}{November 14--17, 2026}{Milan, Italy}" in source,
            "conference name, dates, or location do not match the official call")
    require(r"\acmYear{2026}" in source, "ACM year is not 2026")
    require(r"\acmDOI{}" in source and r"\acmISBN{}" in source,
            "unassigned DOI or ISBN metadata is not explicitly blank")
    require(r"\bibliographystyle{ACM-Reference-Format}" in source,
            "ACM numeric bibliography style is not selected")
    require(r"\keywords{" in source and source.count(r"\ccsdesc") >= 1,
            "ACM keywords or CCS concepts are missing")
    require(r"\Description{" in source, "accessible figure descriptions are missing")

    for pattern, label in (
        (r"\\appendix\b", "appendix command"),
        (r"\\begin\{appendices\}", "appendices environment"),
        (r"\\(?:section|section\*)\{\s*(?:Supplement|Appendix)", "supplement/appendix section"),
        (r"\\input\{[^}]*(?:supp|appendix)[^}]*\}", "supplement/appendix input"),
    ):
        require(re.search(pattern, source, flags=re.IGNORECASE) is None, f"forbidden {label} found")

    for command in (
        r"\geometry", r"\baselinestretch", r"\linespread", r"\textfloatsep",
        r"\topmargin", r"\oddsidemargin", r"\evensidemargin", r"\hoffset",
        r"\voffset", r"\headheight", r"\pagestyle", r"\raggedbottom",
    ):
        require(command not in source, f"template-altering command found: {command}")

    for token in (
        "Sasha Cui", "zc362", "/nfs/", "/Users/", "alpha_evolve",
        "@yale.edu", "Yale University",
    ):
        require(token not in source, f"source identity or local-path leak: {token}")
    for command in (r"\email{", r"\orcid{", r"\authornote{", r"\thanks{"):
        require(command not in source, f"double-blind source contains {command}")

    require(pdf.is_file(), f"final PDF is missing: {pdf}")
    if pdf.is_file():
        info = command_text("pdfinfo", str(pdf))
        text = command_text("pdftotext", str(pdf), "-")
        fonts = command_text("pdffonts", str(pdf))
        page_match = re.search(r"^Pages:\s+(\d+)", info, flags=re.MULTILINE)
        require(page_match is not None, "PDF page count is unavailable")
        if page_match:
            pages = int(page_match.group(1))
            require(1 <= pages <= 8, f"PDF has {pages} pages; ICAIF maximum is eight total")
        require("Page size:       612 x 792 pts (letter)" in info, "PDF is not US Letter")
        require("acmart 2026/06/27 v2.19" in info, "PDF was not built with acmart 2.19")
        author_metadata = re.search(r"^Author:\s*(.*)$", info, flags=re.MULTILINE)
        require(author_metadata is None or author_metadata.group(1).strip() in {"", "Anonymous Author(s)"},
                "PDF Author metadata is not anonymous")
        require("Anonymous Author(s)" in text, "rendered title block is not anonymous")
        require("Can Public Artifacts Substantiate Financial-Agent Alpha?" in text,
                "rendered paper title is missing")
        require("References" in text, "references are missing from the PDF")
        require("978-x-xxxx-xxxx-x" not in text and "YYYY/MM" not in text,
                "PDF contains an unassigned ACM production placeholder")
        require(not re.search(r"^\s*(?:Appendix|Supplementary Materials?)\s*$", text,
                              flags=re.IGNORECASE | re.MULTILINE),
                "PDF contains an appendix or supplement heading")
        for token in ("Sasha Cui", "zc362", "/nfs/", "/Users/", "alpha_evolve"):
            require(token not in text and token not in info, f"PDF identity or path leak: {token}")

        font_rows = [line.split() for line in fonts.splitlines()[2:] if line.strip()]
        require(bool(font_rows), "PDF font inventory is empty")
        # ``pdffonts`` uses variable-width type and encoding columns (for
        # example, ``Type 1`` and ``CID TrueType``), but its five trailing
        # fields are stable: embedded, subset, Unicode, object ID, generation.
        require(all(len(row) >= 6 and row[-5] == "yes" for row in font_rows),
                "one or more PDF fonts are not embedded")
        require(all("Type 3" not in " ".join(row) for row in font_rows),
                "PDF contains Type 3 fonts; figures must use embedded TrueType/Type 1 fonts")

    require(log_path.is_file(), "LaTeX build log is missing")
    if log_path.is_file():
        log = log_path.read_text(encoding="utf-8", errors="replace")
        require("Class acmart Info: Using format sigconf" in log, "LaTeX log does not confirm sigconf")
        require("Using anonymous mode" in log, "LaTeX log does not confirm anonymous mode")
        for marker in (
            "Overfull", "undefined references", "Citation(s) may have changed",
            "There were undefined citations", "Fatal error", "Emergency stop",
        ):
            require(marker not in log, f"LaTeX log contains {marker!r}")

    if failures:
        print(f"ICAIF FORMAT AUDIT FAILED: {len(failures)} failure(s) across {checks} checks")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"ICAIF FORMAT AUDIT PASSED: {checks} checks; latest template, layout, anonymity, and PDF verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
