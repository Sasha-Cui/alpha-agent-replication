from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_census_citation_assets.py"
SPEC = importlib.util.spec_from_file_location("build_census_citation_assets", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def metadata_rows() -> list[dict[str, str]]:
    with (ROOT / "literature_review/census_v1/primary_record_metadata.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        return list(csv.DictReader(stream))


def test_pretrim_and_retained_work_counts_are_explicit() -> None:
    rows = metadata_rows()
    assert len(rows) == 104
    assert len({row["canonical_work_id"] for row in rows}) == 98
    assert sum(row["main_ft"] == "yes" for row in rows) == 71
    assert len({row["canonical_work_id"] for row in rows if row["main_ft"] == "yes"}) == 69


def test_each_work_has_one_preferred_citation_and_complete_metadata() -> None:
    rows = metadata_rows()
    for work_id in {row["canonical_work_id"] for row in rows}:
        assert sum(
            row["canonical_work_id"] == work_id and row["preferred_citation"] == "yes"
            for row in rows
        ) == 1
    assert all(row["title"] and row["authors"] and row["year"] and row["venue"] for row in rows)


def test_generated_bibliography_and_macros_cover_the_declared_universe() -> None:
    rows = metadata_rows()
    preferred = [row for row in rows if row["preferred_citation"] == "yes"]
    bibliography = (ROOT / "docs/paper/census_primary_records.bib").read_text(encoding="utf-8")
    bib_keys = set(re.findall(r"^@\w+\{([^,]+),", bibliography, flags=re.MULTILINE))
    assert bib_keys == {row["bibtex_key"] for row in preferred}
    macros = (ROOT / "docs/paper/generated_corpus_citations.tex").read_text(encoding="utf-8")
    cited = {
        key.strip()
        for body in re.findall(r"\\cite\{([^}]+)\}", macros)
        for key in body.split(",")
    }
    retained_works = {row["canonical_work_id"] for row in rows if row["main_ft"] == "yes"}
    expected = {row["bibtex_key"] for row in preferred if row["canonical_work_id"] in retained_works}
    assert cited == expected


def test_latex_conversion_removes_unsupported_cjk_aliases() -> None:
    assert MODULE.latex_text("Ran Song (宋燃)") == "Ran Song"
