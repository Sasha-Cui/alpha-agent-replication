from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_finrl_deepseek_paper.py"
SPEC = importlib.util.spec_from_file_location("finrl_deepseek_paper_audit", SCRIPT)
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
    assert len(rows) == 36
    assert Counter(row["paper_table"] for row in rows) == {
        "Table 1 main 100-epoch comparison": 12,
        "Table 2 PPO infusion": 12,
        "Table 3 CPPO infusion": 12,
    }
    assert len(unique) == 24
    assert {row["paper_result_credit"] for row in rows + unique} == {False}


def test_stored_notebook_outputs_are_incomplete_mismatches_and_stale() -> None:
    rows = audit.notebook_conformance_rows()
    stale = audit.notebook_stale_output_rows()
    assert len(rows) == 36
    assert Counter(row["status"] for row in rows) == {
        "stored_output_mismatch": 27,
        "missing_stored_output": 9,
    }
    assert len(stale) == 6
    assert {row["status"] for row in stale} == {
        "same_series_different_stored_output"
    }


def test_raster_results_and_mechanism_boundary_are_explicit() -> None:
    figures = audit.figure_rows()
    labels = audit.figure_metric_rows()
    mechanisms = audit.mechanism_conformance()
    configs = audit.config_conformance()
    assert len(figures) == 32
    assert Counter(row["figure"] for row in figures) == {
        "Figure 1 / download4.png": 5,
        "Figure 2 / download10.png": 7,
        "Figure 3 / download15.png": 5,
        "Figure 4 / download13.png": 5,
        "Figure 5 / download17.png": 5,
        "Figure 6 / download18.png": 5,
    }
    assert len(labels) == 4
    assert {row["paper_result_credit"] for row in figures + labels} == {False}
    assert len(mechanisms) == 26
    assert sum(row["paper_mechanism_credit"] for row in mechanisms) == 7
    assert len(configs) == 20
    assert len(audit.specification_gaps()) == 20


def test_committed_audit_records_native_execution_without_promoting_it() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/finrl_deepseek"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads(
        (output / "native_released_agent_execution.json").read_text(encoding="utf-8")
    )
    table = read_csv(output / "paper_numeric_table_conformance.csv")
    notebook = read_csv(output / "released_notebook_metric_conformance.csv")
    assert manifest["overall_status"] == (
        "released_data_checkpoints_and_code_execute_but_paper_results_not_reproduced"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_table_cells_total"] == 36
    assert manifest["paper_unique_numeric_measurements_total"] == 24
    assert manifest["native_table_cells_display_precision_matches"] == 0
    assert manifest["native_table_cells_with_paper_result_credit"] == 0
    assert manifest["stored_notebook_table_cells_present"] == 27
    assert manifest["stored_notebook_table_cells_missing"] == 9
    assert manifest["stored_notebook_table_cells_matching_paper"] == 0
    assert manifest["paper_figure_series_total"] == 32
    assert manifest["native_exact_figure_series_reproduced"] == 0
    assert manifest["paper_relevant_released_checkpoints_executed"] == 8
    assert manifest["native_evaluation_protocols_executed"] == 3
    assert manifest["released_dataset_files_total"] == 12
    assert manifest["released_checkpoint_files_total"] == 15
    assert manifest["current_tracked_source_files_total"] == 47
    assert manifest["pre_submission_python_files_compiled"] == 25
    assert manifest["pre_submission_python_files_total"] == 25
    assert manifest["current_python_files_compiled"] == 26
    assert manifest["current_python_files_total"] == 27
    assert len(table) == 36 and len(notebook) == 36
    assert {row["paper_result_credit"] for row in table} == {"False"}
    assert native["source_revision"] == audit.CURRENT_COMMIT
    assert set(native["runs"]) == {
        "native_seed0.json",
        "native_seed42.json",
        "native_mean.json",
    }
    assert all(len(run["results"]) == 8 for run in native["runs"].values())
    assert native["paper_result_credit"] is False
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_primary_sources_when_available() -> None:
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_source")
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_paper")
    artifacts = Path("/nfs/roberts/scratch/pi_btk22/zc362/finrl_deepseek_artifacts")
    if not source.exists() or not paper.exists() or not artifacts.exists():
        return
    assert str(audit.run_git(source, "rev-parse", "HEAD")).strip() == audit.CURRENT_COMMIT
    assert audit.sha256(paper / "paper.pdf") == audit.PAPER_PDF_SHA256
    assert audit.sha256(paper / "source.tar") == audit.PAPER_SOURCE_SHA256
    assert audit.sha256(paper / "arxiv_api.xml") == audit.ARXIV_API_SHA256
    assert len(audit.source_inventory(source)) == 47
    native = audit.validate_native_inputs(artifacts)
    assert len(native["input_artifacts"]) == 11
