from pathlib import Path

from scripts.build_paper_companion_material import PAPER_SOURCES, PRESERVED_PDF_IDS


ROOT = Path(__file__).resolve().parents[1]


def test_companion_paper_sources_exist_and_are_pdfs() -> None:
    assert len(PAPER_SOURCES) == 9
    assert len(PRESERVED_PDF_IDS) == 6
    assert PRESERVED_PDF_IDS <= set(PAPER_SOURCES)
    for relative in PAPER_SOURCES.values():
        path = ROOT / relative
        assert path.read_bytes()[:5] == b"%PDF-"
