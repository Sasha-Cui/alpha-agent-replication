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
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/timi"
SPEC = importlib.util.spec_from_file_location(
    "audit_timi_paper", ROOT / "scripts/audit_timi_paper.py"
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest() -> dict:
    return json.loads((AUDIT_DIR / "manifest.json").read_text())


def test_both_official_sources_are_pinned_rebuilt_and_visually_checked() -> None:
    data = manifest()
    assert data["official_versions_audited"] == ["v1", "v2"]
    assert data["official_pdf_and_source_recovered"] is True
    assert data["document_rebuild_completed"] is True
    assert data["official_pages_visually_checked"] == 33
    assert data["rebuilt_pages_visually_checked"] == 33
    versions = rows("version_audit.csv")
    assert [row["official_pages"] for row in versions] == ["16", "17"]
    assert [row["rebuilt_pages"] for row in versions] == ["16", "17"]
    assert [row["source_files"] for row in versions] == ["21", "22"]
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    assert provenance["arxiv"]["id"] == "2510.04787"
    visual = provenance["arxiv"]["visual_qa"]
    assert visual["unreadable_clipped_overlapping_blank_or_missing_pages"] == 0
    assert len(visual["contact_sheet_sha256"]) == 5


def test_source_inventory_is_manuscript_material_not_system_or_data() -> None:
    inventory = rows("source_inventory.csv")
    assert len(inventory) == 43
    assert Counter(row["version"] for row in inventory) == {"v1": 21, "v2": 22}
    assert all(row["role"] == "official_manuscript_source" for row in inventory)
    assert all(row["paper_system_implementation"] == "False" for row in inventory)
    assert all(row["underlying_experiment_data"] == "False" for row in inventory)


def test_every_current_empirical_table_unit_fails_closed() -> None:
    results = rows("published_result_ledger.csv")
    expected = {label: count for label, (_, _, _, count) in audit.RESULT_TABLES.items()}
    assert len(results) == 349
    assert Counter(row["table_label"] for row in results) == expected
    assert all(row["source_document_recovered"] == "True" for row in results)
    assert all(row["author_native_experiment_executed"] == "False" for row in results)
    assert all(row["published_result_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)
    assert manifest()["native_numeric_units_regenerated"] == 0


def test_rendered_figures_are_not_misclassified_as_regenerated_results() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 6
    assert sum(int(row["panels"]) for row in figures) == 10
    assert sum(int(row["empirical_panels"]) for row in figures) == 8
    assert all(row["rendered_author_asset_recovered"] == "True" for row in figures)
    assert all(row["underlying_numeric_arrays_recovered"] == "False" for row in figures)
    assert all(row["author_native_figure_regenerated"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)
    assert manifest()["native_empirical_panels_regenerated"] == 0


def test_openreview_supplement_is_listed_but_not_claimed_as_inspected() -> None:
    provenance = json.loads((AUDIT_DIR / "source_provenance.json").read_text())
    opened = provenance["openreview"]
    assert opened["forum_id"] == "ROEwZAxqyS"
    assert opened["venue"] == "ICLR 2026 Poster"
    assert opened["license"] == "CC BY 4.0"
    assert opened["supplement_listed"] is True
    assert opened["supplement_immutable_path"] == audit.SUPPLEMENT_PATH
    assert opened["supplement_recovered"] is False
    assert (opened["logical_endpoint_status"], opened["immutable_endpoint_status"]) == (403, 404)
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["supplement"]["status"] == "listed_but_currently_unrecoverable"


def test_public_candidates_are_unaffiliated_and_receive_no_native_credit() -> None:
    release = json.loads((AUDIT_DIR / "release_search_audit.json").read_text())
    assert release["official_paper_implementation_recovered"] is False
    assert release["github_exact_arxiv_repository_matches"] == 0
    assert release["github_exact_title_code_candidates"] == ["cajias/nautilus-trading"]
    candidates = release["unaffiliated_candidates"]
    assert [row["repository"] for row in candidates] == [
        "qOeOp/vibe-trading", "cajias/nautilus-trading",
    ]
    assert all(row["native_paper_credit"] is False for row in candidates)
    assert "private, deleted, or unindexed" in release["bounded_negative_inference"]


def test_method_inventory_preserves_exact_reproduction_boundaries() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["paper_specific_release"]["status"] == "missing"
    assert methods["universe"]["status"] == "partially_specified"
    assert methods["market_data"]["status"] == "specified_not_frozen"
    assert methods["agent_architecture"]["status"] == "paper_specification_only"
    assert methods["prompts"]["status"] == "not_released"
    assert methods["costs_and_slippage"]["status"] == "underspecified"
    assert methods["replications_and_uncertainty"]["status"] == "not_released"
    assert methods["published_results"]["status"] == "not_regenerated"
    assert methods["search_for_release"]["status"] == "no_attributable_public_implementation_found"


def test_internal_conflicts_and_inference_boundaries_are_explicit() -> None:
    checks = {row["check"]: row for row in rows("internal_consistency_audit.csv")}
    assert "OM=61" in checks["transaction_figure_order_counts"]["detail"]
    assert "28 and 39" in checks["transaction_figure_order_counts"]["detail"]
    assert checks["annual_return_formula"]["status"] == "not_annualized_as_printed"
    assert "potential posterior information" in checks["posterior_information"]["detail"]
    assert checks["baseline_comparability"]["status"] == "partial_and_estimated"
    assert checks["version_result_lineage"]["status"] == "material_revision_without_raw_lineage"
    assert checks["code_release_language"]["status"] == "not_fulfilled_in_pinned_evidence"


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned TiMi source audit is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_timi_paper.py"),
         "--output", str(tmp_path / "strict"), "--strict"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert json.loads((tmp_path / "strict/manifest.json").read_text())[
        "full_end_to_end_pipeline_reproduced"
    ] is False


def test_manifest_hashes_every_output_and_readme_is_honest() -> None:
    data = manifest()
    expected = {
        path.name for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(data["output_sha256"]) == expected
    assert all(len(value) == 64 for value in data["output_sha256"].values())
    readme = (AUDIT_DIR / "README.md").read_text()
    for marker in (
        "33 official and all 33 rebuilt pages", "349 printed empirical numeric units",
        "eight of them empirical", "supplement therefore existed in metadata",
        "must not be treated as inspected or absent", "third-party adaptations",
        "0/349 active empirical table units", "0/8", "currently a defensible true",
    ):
        assert marker in readme
