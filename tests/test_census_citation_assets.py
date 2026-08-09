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
    expected = {row["bibtex_key"] for row in preferred}
    assert cited == expected


def test_work_level_waterfall_reconciles_every_canonical_work() -> None:
    with (
        ROOT
        / "paper_runs/submission_evidence/replication_scope/work_level_evidence_waterfall.csv"
    ).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len({row["canonical_work_id"] for row in rows}) == 98
    assert sum(row["screen_decision"] == "retained_formula_or_trading" for row in rows) == 69
    assert sum(row["screen_decision"] == "screened_out" for row in rows) == 29
    assert sum(row["good_faith_reconstruction"] == "yes" for row in rows) == 40
    assert sum(int(row["mapping_count"]) for row in rows) == 50
    assert sum(row["reconstruction_fidelity"] == "source_grounded_component_test" for row in rows) == 5
    assert sum(row["reconstruction_fidelity"] == "narrative_favorable_stress_test" for row in rows) == 35
    assert sum(row["reconstruction_fidelity"] == "availability_only" for row in rows) == 29
    assert sum(row["direct_code_route"] == "retained_code_attempt" for row in rows) == 8
    assert sum(row["direct_code_route"] == "diagnostic_code_attempt" for row in rows) == 6
    assert sum(row["native_agent_replication"] == "yes" for row in rows) == 0
    assert sum(row["code_backed_adaptation"] == "yes_released_seed_expression" for row in rows) == 1


def test_latex_conversion_removes_unsupported_cjk_aliases() -> None:
    assert MODULE.latex_text("Ran Song (宋燃)") == "Ran Song"


def test_mapping_scope_ledger_reconciles_62_candidates_to_headline_50() -> None:
    with (
        ROOT
        / "paper_runs/submission_evidence/replication_scope/mapping_scope_ledger.csv"
    ).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    included = [row for row in rows if row["headline_50_scope"] == "included"]
    excluded = [row for row in rows if row["headline_50_scope"] == "excluded"]
    assert len(rows) == len({row["candidate_id"] for row in rows}) == 62
    assert len(included) == 50
    assert len(excluded) == 12
    assert len({row["canonical_work_id"] for row in included}) == 40
    assert {row["screen_main_ft"] for row in included} == {"Y"}
    assert {row["screen_main_ft"] for row in excluded} == {"N"}
    assert {
        row["mapping_fidelity_tier"] for row in excluded
    } == {"M0_narrative_translation"}
    assert {
        row["source_category"] for row in excluded
    } == {
        "formula_or_factor_method",
        "benchmark_or_audit",
        "community_repository",
    }
    assert {
        category: sum(row["source_category"] == category for row in excluded)
        for category in {row["source_category"] for row in excluded}
    } == {
        "formula_or_factor_method": 4,
        "benchmark_or_audit": 6,
        "community_repository": 2,
    }
    assert all(
        row["headline_scope_reason"].startswith(
            "excluded: screened lineage has main_FT=N; OUT:"
        )
        for row in excluded
    )
