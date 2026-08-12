from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/hubble"
SPEC = importlib.util.spec_from_file_location(
    "audit_hubble_paper", ROOT / "scripts/audit_hubble_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_both_official_editions_are_pinned_rebuilt_and_visually_checked() -> None:
    data = manifest()
    assert data["official_versions_audited"] == ["v1", "v2"]
    assert data["official_pdfs_and_sources_recovered"] is True
    assert data["official_document_rebuilds_completed"] is True
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    versions = {item["version"]: item for item in provenance["arxiv"]["versions"]}
    assert versions["v1"]["submitted"] == "2026-03-09"
    assert versions["v2"]["submitted"] == "2026-04-14"
    assert versions["v1"]["pages"] == versions["v1"]["rebuild_pages"] == 11
    assert versions["v2"]["pages"] == versions["v2"]["rebuild_pages"] == 17
    assert versions["v1"]["source_files"] == 11
    assert versions["v2"]["source_files"] == 19
    assert versions["v1"]["rebuild_token_multiset_jaccard"] > 0.997
    assert versions["v2"]["rebuild_token_multiset_jaccard"] > 0.999
    assert sum(item["visual_qa"]["pages_inspected"] for item in versions.values()) == 28
    assert all(
        item["visual_qa"]["unreadable_clipped_or_overlapping_pages"] == 0
        for item in versions.values()
    )


def test_complete_table_denominators_keep_native_credit_zero() -> None:
    ledger = rows("published_result_ledger.csv")
    data = manifest()
    by_edition = Counter(row["edition"] for row in ledger)
    assert by_edition == {"arxiv_v1": 50, "arxiv_v2": 108}
    assert data["published_v1_numeric_cells"] == 50
    assert data["published_v1_unique_numeric_cells"] == 47
    assert data["published_v2_numeric_cells"] == 108
    assert data["published_v2_unique_numeric_cells"] == 102
    assert Counter(row["duplicate_kind"] for row in ledger) == {
        "none": 149,
        "exact_semantic_repeat": 9,
    }
    assert data["native_empirical_units_regenerated"] == 0
    assert all(row["native_pipeline_executed"] == "False" for row in ledger)
    assert all(row["native_result_regenerated"] == "False" for row in ledger)
    assert all(row["paper_result_credit"] == "False" for row in ledger)


def test_figure_inventory_does_not_substitute_rendered_images_for_arrays() -> None:
    figures = rows("figure_series_inventory.csv")
    assert len(figures) == 16
    assert sum(int(row["displayed_series"]) for row in figures) == 50
    assert manifest()["published_empirical_figure_series"] == 50
    assert manifest()["native_figure_series_regenerated"] == 0
    assert all(row["underlying_numeric_array_released"] == "False" for row in figures)
    assert all(row["native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)


def test_release_chronology_rejects_literal_pre_oos_freeze() -> None:
    chronology = json.loads((AUDIT_DIR / "model_release_chronology.json").read_text())
    assert chronology["oos_start"] == "2025-06-01"
    assert chronology["oos_end"] == "2026-03-13"
    assert {item["first_public_date"] for item in chronology["models"]} == {"2026-03-11"}
    assert all(item["after_oos_start"] for item in chronology["models"])
    assert chronology["literal_fixed_before_oos_window_begins_supported"] is False
    assert chronology["retrospective_data_layer_holdout_possible"] is True
    assert chronology["retrospective_data_layer_holdout_verified"] is False
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert checks["v2_literal_pre_oos_freeze"]["status"] == (
        "contradicted_by_model_release_chronology"
    )
    assert checks["v2_defensible_temporal_interpretation"]["status"] == (
        "retrospective_holdout_possible_but_unverified"
    )
    assert manifest()["literal_pre_oos_freeze_supported"] is False


def test_method_ledger_records_intentional_and_accidental_blockers() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert len(methods) == 30
    assert methods["exact_factor_formulas"]["status"] == "intentionally_withheld"
    for dimension in (
        "native_source",
        "data_universe_v1",
        "data_universe_v2",
        "market_data",
        "survivorship_controls",
        "prompts",
        "rag_corpus",
        "model_v1",
        "model_call_parameters",
        "random_seeds",
        "scoring_v2",
        "family_assignment",
        "duplicate_detection",
        "transaction_costs",
        "neutralization",
        "runtime_artifacts",
        "candidate_formulas",
        "raw_result_arrays",
        "environment_dependencies",
    ):
        assert methods[dimension]["status"] == "missing"


def test_internal_consistency_audit_is_honest_about_both_editions() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert len(checks) == 14
    assert checks["v1_round_accounting"]["status"] == "caption_and_counts_conflict"
    assert checks["v1_round1_duplicates"]["status"] == "prose_conflicts_with_table_and_figure"
    assert checks["v1_pass_rate"]["status"] == "passes_displayed_arithmetic"
    assert checks["v2_discovery_day_count"]["status"] == "underspecified_against_public_calendar"
    assert checks["v2_oos_day_count"]["status"] == "underspecified_against_public_calendar"
    assert checks["v2_formula_disclosure"]["status"] == "intentional_reproduction_blocker"
    assert checks["v2_backend_identity"]["status"] == "hunter_alpha_later_disclosed"
    assert checks["author_name_rendering"]["status"] == "metadata_source_inconsistency"


def test_component_and_discovery_do_not_invent_native_hubble_release() -> None:
    component = json.loads((AUDIT_DIR / "sandbox_component_execution.json").read_text())
    assert len(component["cases"]) == 6
    assert sum(item["accepted"] for item in component["cases"]) == 2
    assert component["native_hubble_code_used"] is False
    assert component["paper_candidate_or_output_used"] is False
    assert component["paper_result_credit"] is False
    discovery = rows("discovery_evidence.csv")
    assert len(discovery) == 6
    assert all(row["attributable_native_artifact_recovered"] == "False" for row in discovery)
    assert all(
        "not proof" in row["negative_search_limit"]
        or "outside" in row["negative_search_limit"]
        or "only" in row["negative_search_limit"]
        or "may exist" in row["negative_search_limit"]
        for row in discovery
    )
    boundary = json.loads((AUDIT_DIR / "source_provenance.json").read_text())["release_boundary"]
    assert boundary["attributable_native_implementation_recovered"] is False
    assert boundary["exact_factor_formulas_recovered"] is False
    assert boundary["bounded_negative_search_is_proof_of_nonexistence"] is False


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned Hubble primary-source scratch is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audit_hubble_paper.py"),
            "--output",
            str(tmp_path / "strict"),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    strict = json.loads((tmp_path / "strict/manifest.json").read_text())
    assert strict["full_end_to_end_pipeline_reproduced"] is False


def test_manifest_hashes_every_output_and_readme_states_boundary() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "native Hubble experiment is **not reproduced**" in text
    assert "0/47 for v1" in text
    assert "0/102 for v2" in text
    assert "0/50 figure series" in text
    assert "Unaffiliated" in text
