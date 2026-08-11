from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_fincon_paper.py"
SPEC = importlib.util.spec_from_file_location("fincon_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_complete_table_and_unique_measurement_census_is_fail_closed() -> None:
    rows = audit.paper_table_rows()
    unique = audit.unique_measurement_rows(rows)
    assert len(rows) == 306
    assert Counter(row["paper_table"] for row in rows) == {
        "Table 2 single-asset comparison / part 1": 108,
        "Table 2 single-asset comparison / part 2": 99,
        "Table 3 portfolio comparison": 24,
        "Table 4 CVaR ablation": 18,
        "Table 5 belief-update ablation": 18,
        "Appendix extreme-market TSLA table": 27,
        "Appendix extreme-market P1 table": 12,
    }
    assert len(unique) == 288
    assert Counter(row["display_occurrences"] for row in unique) == {1: 279, 3: 9}
    assert {row["paper_result_credit"] for row in rows + unique} == {False}


def test_revision_drift_is_material_and_explicit() -> None:
    rows = audit.paper_table_rows()
    drift = audit.version_drift_rows(rows)
    summary = audit.version_summary_rows()
    assert len(drift) == 64
    assert {row["status"] for row in drift} == {"changed_in_v3"}
    assert len({row["display_cell_id"] for row in drift}) == 64
    assert summary[0]["numeric_cells"] == summary[1]["numeric_cells"] == 201
    assert summary[1]["shared_cells_changed_from_prior"] == 0
    assert summary[2]["numeric_cells"] == 306
    assert summary[2]["shared_cells_changed_from_prior"] == 64
    assert summary[2]["cells_added_from_prior"] == 105
    assert summary[-1]["authority"] is True


def test_raster_series_and_source_boundary_are_not_promoted() -> None:
    figures = audit.figure_rows()
    mechanisms = audit.mechanism_conformance()
    configs = audit.config_conformance()
    checks = audit.internal_checks()
    assert len(audit.FIGURES) == 18
    assert len(figures) == 106
    assert {row["paper_result_credit"] for row in figures} == {False}
    assert len(mechanisms) == 33
    assert sum(row["paper_mechanism_credit"] for row in mechanisms) == 0
    assert len(configs) == 26
    assert sum(row["paper_configuration_credit"] for row in configs) == 0
    assert len(audit.specification_gaps()) == 33
    assert Counter(row["status"] for row in checks)["claim_not_supported_by_table"] == 4
    assert any(row["status"] == "methodological_leakage_risk" for row in checks)


def test_committed_audit_records_no_released_implementation() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/fincon"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((output / "native_execution.json").read_text(encoding="utf-8"))
    table = read_csv(output / "paper_numeric_table_conformance.csv")
    unique = read_csv(output / "paper_unique_measurement_conformance.csv")
    figures = read_csv(output / "paper_figure_series_inventory.csv")
    history = read_csv(output / "released_source_history.csv")
    assert manifest["overall_status"] == (
        "paper_specification_audited_but_official_code_and_data_not_released"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_table_cells_total"] == len(table) == 306
    assert manifest["paper_unique_numeric_measurements_total"] == len(unique) == 288
    assert manifest["paper_figure_series_total"] == len(figures) == 106
    assert manifest["paper_numeric_table_cells_with_paper_result_credit"] == 0
    assert manifest["paper_mechanisms_verified_in_released_source"] == 0
    assert manifest["official_repository_commits_total"] == len(history) == 11
    assert manifest["official_repository_tracked_files_current"] == 1
    assert manifest["official_repository_source_code_files_current"] == 0
    assert {row["only_readme"] for row in history} == {"True"}
    assert native["native_system_execution_attempted"] is False
    assert native["paper_latex_compilation"]["exit_code"] == 0
    assert native["paper_latex_compilation"]["paper_result_credit"] is False
    assert native["paper_result_credit"] is False
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_primary_sources_when_available() -> None:
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/fincon_source")
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/fincon_paper")
    if not source.exists() or not paper.exists():
        return
    audit.validate_primary_inputs(source, paper)
    assert len(audit.source_inventory(source)) == 1
    assert len(audit.source_history_rows(source)) == 11
    assets = audit.source_asset_rows(paper)
    assert len(assets) == 37
    assert sum(row["active_result_figure"] for row in assets) == 18
