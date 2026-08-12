from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/marketsenseai"
SPEC = importlib.util.spec_from_file_location(
    "audit_marketsenseai_papers", ROOT / "scripts/audit_marketsenseai_papers.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_2025_result_table_denominator_is_exhaustive_and_fail_closed() -> None:
    ledger = audit.market_2025_table_rows()
    assert len(ledger) == 157
    assert Counter(row["paper_table"] for row in ledger) == {
        "Sentiment statistics": 21,
        "Retrieval performance": 45,
        "Performance metrics": 56,
        "Performance attribution": 24,
        "Factor model results": 11,
    }
    assert all(row["paper_result_credit"] is False for row in ledger)
    assert all(row["native_reproduced_value"] == "" for row in ledger)


def test_2026_table_denominator_separates_configuration_from_results() -> None:
    ledger = audit.validation_2026_table_rows()
    assert len(ledger) == 256
    assert Counter(row["cell_kind"] for row in ledger) == {
        "configuration": 6,
        "direct_result": 250,
    }
    assert sum(row["paper_table"] == "Appendix Monte Carlo results by date" for row in ledger) == 100
    assert all(row["paper_result_credit"] is False for row in ledger)


def test_manifest_never_promotes_manuscript_or_rendered_figures_to_results() -> None:
    data = manifest()
    assert data["full_papers_reproduced"] == 0
    assert data["paper_2025_result_table_units"] == 157
    assert data["paper_2026_result_table_units"] == 250
    assert data["paper_2025_result_table_units_faithfully_regenerated"] == 0
    assert data["paper_2026_result_table_units_faithfully_regenerated"] == 0
    assert data["author_rendered_empirical_assets_verified"] == 22
    assert data["raw_empirical_figure_arrays_shipped"] == 0
    assert data["manuscript_rebuilds_receive_result_credit"] is False
    assert data["operational_system_source_found"] is False


def test_source_archives_are_classified_as_manuscript_only() -> None:
    inventory = rows("paper_source_inventory.csv")
    assert Counter(row["paper_version"] for row in inventory) == {
        "2502.00415v1": 18,
        "2502.00415v2": 14,
        "2604.17327v1": 13,
    }
    assert all(row["operational_system_code"] == "False" for row in inventory)
    assert all(row["raw_numeric_result_array"] == "False" for row in inventory)
    assert all(row["native_signal_or_portfolio_output"] == "False" for row in inventory)


def test_all_empirical_source_assets_have_output_but_not_reproduction_credit() -> None:
    figures = rows("empirical_figure_inventory.csv")
    assert Counter(row["paper_version"] for row in figures) == {
        "2502.00415v1": 6,
        "2502.00415v2": 6,
        "2604.17327v1": 10,
    }
    assert all(row["author_rendered_output_correspondence"] == "True" for row in figures)
    assert all(row["underlying_numeric_array_shipped"] == "False" for row in figures)
    assert all(row["faithfully_regenerated_from_native_pipeline"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)


def test_consistency_audit_records_beta_conflict_and_p_value_sidedness() -> None:
    checks = {row["check"]: row for row in rows("paper_internal_consistency_checks.csv")}
    beta = checks["Prose says S&P500 portfolios have beta 1.24--1.27"]
    assert beta["status"] == "fails_against_displayed_attribution_table"
    p_side = checks["Paper's |ICIR| threshold versus reported p_t convention"]
    assert p_side["status"] == "internally_inconsistent_test_sidedness"
    p500 = checks["S&P500 reported p_t sidedness"]
    assert p500["status"] == "matches_one_sided_absolute_tail"
    assert "0.047084" in p500["implication"]
    risk = checks["Strong-buy delta UpDn as defined versus displayed hold ratio"]
    assert risk["status"] == "fails_published_delta_definition"
    assert risk["paper_value"] == "0.17"
    assert risk["reconstructed_from_displayed_values"] == "0.28"
    assert manifest()["material_internal_conflicts"] == 4


def test_paper_specification_components_do_not_become_native_mechanisms() -> None:
    mechanisms = rows("paper_mechanism_conformance.csv")
    assert len(mechanisms) == 38
    assert any(row["paper_specification_reconstructable"] == "True" for row in mechanisms)
    assert all(row["native_mechanism_credit"] == "False" for row in mechanisms)
    assert all(row["paper_result_credit"] == "False" for row in mechanisms)


def test_public_source_search_is_bounded_and_not_overclaimed() -> None:
    discovery = rows("public_source_discovery.csv")
    assert len(discovery) == 10
    assert all(row["attributable_operational_release_found"] == "False" for row in discovery)
    assert all("not_proof" in row["negative_inference_boundary"] for row in discovery)


def test_three_rebuilds_are_deterministic_document_evidence_only() -> None:
    rebuilds = json.loads((AUDIT_DIR / "manuscript_rebuilds.json").read_text(encoding="utf-8"))
    assert len(rebuilds) == 3
    assert all(row["same_hash_after_repeated_final_compile"] is True for row in rebuilds)
    assert all(row["paper_result_reproduction"] is False for row in rebuilds)
    assert all(row["normalized_extracted_text_sequence_similarity"] > 0.99 for row in rebuilds)
    assert all("passed_no_clipping" in row["full_contact_sheet_visual_qa"] for row in rebuilds)


def test_manifest_hashes_every_nonmanifest_output_and_readme_is_honest() -> None:
    data = manifest()
    expected = {
        path.name
        for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    assert "Neither paper is faithfully reproduced" in text
    assert "0/157" in text
    assert "0/250" in text
    assert "not independently\ndemonstrated" in text
    assert "does **not** prove" in text


def test_both_papers_route_through_the_targeted_paper_only_audit() -> None:
    route_path = (
        ROOT
        / "paper_runs/submission_evidence/replication_scope/"
        "paper_evidence_route_ledger.csv"
    )
    with route_path.open(newline="", encoding="utf-8") as stream:
        routed = [
            row
            for row in csv.DictReader(stream)
            if row["canonical_work_id"] in {audit.WORK_2025, audit.WORK_2026}
        ]
    assert len(routed) == 2
    expected_status = (
        "paper_audit:completed_2025_zero_of_157_2026_zero_of_250_"
        "no_operational_release"
    )
    for row in routed:
        assert row["paper_evidence_route"] == "paper_only_underspecified"
        assert row["native_pipeline_disposition"] == (
            "paper_only_audit_recorded_no_native_code_pipeline"
        )
        assert row["native_execution_audit_status"] == expected_status
        assert "Zero table-result units" in row["precise_native_or_access_blocker"]
        assert row["full_prompt_search_training_pipeline_reproduced"] == "no"
