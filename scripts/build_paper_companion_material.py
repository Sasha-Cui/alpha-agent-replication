#!/usr/bin/env python3
"""Preserve Census-ID paper copies and useful deterministic text extracts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
from pathlib import Path


PAPER_SOURCES = {
    "CensusACL2026findingsacl456": Path(
        "literature_review/papers/"
        "27_alphaquanter_an_end_to_end_tool_augmented_agentic_reinforcement_learning_framework_for_stock_trading.pdf"
    ),
    "CensusArxiv231113743": Path(
        "literature_review/papers/"
        "28_finmem_a_performance_enhanced_llm_trading_agent_with_layered_memory_and_character_design.pdf"
    ),
    "CensusArxiv241220138": Path(
        "literature_review/papers/23_tradingagents_multi_agents_llm_financial_trading_framework.pdf"
    ),
    "CensusArxiv250514738": Path(
        "literature_review/papers/06_r_d_agent_an_llm_agent_framework_towards_autonomous_data_science.pdf"
    ),
    "CensusArxiv251223515": Path(
        "literature_review/papers/17_alpha_r1_alpha_screening_with_llm_reasoning_via_reinforcement_learning.pdf"
    ),
    "CensusArxiv260207085": Path(
        "literature_review/papers/04_quantaalpha_an_evolutionary_framework_for_llm_driven_alpha_mining.pdf"
    ),
    "CensusArxiv250800554": Path(
        "literature_review/papers/24_contesttrade_a_multi_agent_trading_system_based_on_internal_contest_mechanism.pdf"
    ),
    "CensusArxiv250905080": Path(
        "literature_review/papers/32_mm_drex_multimodal_driven_dynamic_routing_of_llm_experts_for_financial_trading.pdf"
    ),
    "CensusArxiv260505580": Path(
        "literature_review/papers/18_alphacrafter_a_full_stack_multi_agent_framework_for_cross_sectional_quantitative_trading.pdf"
    ),
}

PRESERVED_PDF_IDS = {
    "CensusACL2026findingsacl456",
    "CensusArxiv231113743",
    "CensusArxiv241220138",
    "CensusArxiv250514738",
    "CensusArxiv251223515",
    "CensusArxiv260207085",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_metadata(root: Path) -> dict[str, dict[str, str]]:
    path = root / "literature_review/census_v1/primary_record_metadata.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        return {row["bibtex_key"]: row for row in csv.DictReader(stream)}


def build(root: Path, pdftotext: str) -> Path:
    metadata = load_metadata(root)
    pdf_dir = root / "literature_review/source_pdfs"
    text_dir = root / "literature_review/paper_texts"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str | int]] = []
    for source_id, relative_pdf in PAPER_SOURCES.items():
        if source_id not in metadata:
            raise KeyError(f"missing primary-record metadata for {source_id}")
        source_pdf = root / relative_pdf
        if source_pdf.read_bytes()[:5] != b"%PDF-":
            raise ValueError(f"not a PDF: {source_pdf}")

        preserved_relative = ""
        if source_id in PRESERVED_PDF_IDS:
            preserved = pdf_dir / f"{source_id}.pdf"
            shutil.copyfile(source_pdf, preserved)
            if sha256(preserved) != sha256(source_pdf):
                raise AssertionError(f"source-ID copy differs for {source_id}")
            preserved_relative = preserved.relative_to(root).as_posix()

        text_path = text_dir / f"{source_id}.txt"
        subprocess.run(
            [pdftotext, "-layout", "-enc", "UTF-8", str(source_pdf), str(text_path)],
            check=True,
        )
        if not text_path.read_text(encoding="utf-8", errors="replace").strip():
            raise ValueError(f"empty text extract: {text_path}")

        rows.append(
            {
                "source_record_id": source_id,
                "title": metadata[source_id]["title"],
                "primary_pdf_path": relative_pdf.as_posix(),
                "census_pdf_path": preserved_relative,
                "text_extract_path": text_path.relative_to(root).as_posix(),
                "pdf_sha256": sha256(source_pdf),
                "pdf_bytes": source_pdf.stat().st_size,
                "text_sha256": sha256(text_path),
                "text_bytes": text_path.stat().st_size,
                "text_extraction": "pdftotext -layout -enc UTF-8",
            }
        )

    manifest = root / "literature_review/source_material_manifest.csv"
    fieldnames = list(rows[0])
    with manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pdftotext", default="pdftotext")
    args = parser.parse_args()
    print(build(args.root.resolve(), args.pdftotext))


if __name__ == "__main__":
    main()
