from pathlib import Path

from scripts.build_paper_companion_material import PAPER_SOURCES, PRESERVED_PDF_IDS, sha256


ROOT = Path(__file__).resolve().parents[1]


def test_companion_paper_sources_exist_and_are_pdfs() -> None:
    assert len(PAPER_SOURCES) == 9
    assert len(PRESERVED_PDF_IDS) == 6
    assert PRESERVED_PDF_IDS <= set(PAPER_SOURCES)
    for relative in PAPER_SOURCES.values():
        path = ROOT / relative
        assert path.read_bytes()[:5] == b"%PDF-"


def test_preserved_source_ids_and_text_extracts_are_present() -> None:
    for source_id, relative in PAPER_SOURCES.items():
        text = ROOT / "literature_review/paper_texts" / f"{source_id}.txt"
        assert text.read_text(encoding="utf-8", errors="replace").strip()
        if source_id in PRESERVED_PDF_IDS:
            preserved = ROOT / "literature_review/source_pdfs" / f"{source_id}.pdf"
            assert preserved.read_bytes()[:5] == b"%PDF-"
            assert sha256(preserved) == sha256(ROOT / relative)
