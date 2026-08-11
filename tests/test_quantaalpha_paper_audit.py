from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_quantaalpha_paper.py"
SPEC = importlib.util.spec_from_file_location("quantaalpha_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_complete_numeric_table_census_is_fail_closed() -> None:
    rows = audit.paper_table_rows()
    assert len(rows) == 344
    assert Counter(row["paper_table"] for row in rows) == {
        "Table 1 Main CSI300 results": 196,
        "Table 2 Evolution-component ablation": 28,
        "Appendix Table 2 Cross-seed core metrics": 12,
        "Appendix Table 3 Cross-seed variance": 16,
        "Appendix Table 4 Daily IC statistics": 28,
        "Appendix C Parent trajectory metrics": 6,
        "Appendix C Backtest metrics": 10,
        "Appendix C Detailed statistics": 6,
        "Appendix D Representative factors": 26,
        "Appendix D Factor summary": 16,
    }
    assert sum(row["value_role"] == "displayed_delta" for row in rows) == 12
    assert {row["paper_result_credit"] for row in rows} == {False}
    assert {row["native_reproduced_value"] for row in rows} == {""}


def test_numeric_figure_boundary_is_separate_and_complete() -> None:
    labels = audit.figure_label_rows()
    points = audit.plot_point_rows()
    assert len(labels) == 40
    assert Counter(row["figure"] for row in labels) == {
        "Figure 3 quality-gate ablation": 20,
        "Appendix E iterative case-study raster": 17,
        "Appendix C evolution-path diagram": 3,
    }
    assert len(points) == 47
    assert Counter(row["figure_panel"] for row in points) == {
        "Figure 4 IC": 16,
        "Figure 4 Rank IC": 16,
        "Figure 5 evolutionary alpha-mining efficiency": 15,
    }
    assert {row["paper_result_credit"] for row in labels + points} == {False}


def test_revision_conflicts_and_missing_artifacts_are_explicit() -> None:
    drift = audit.paper_version_drift()
    checks = {row["check"]: row["status"] for row in audit.internal_and_source_checks()}
    gaps = audit.specification_gaps()
    mechanisms = audit.mechanism_conformance()
    assert len(drift) == 5
    assert {row["status"] for row in drift} == {"large_unexplained_revision"}
    assert drift[0]["v1_value"] == 0.1501 and drift[0]["v3_value"] == 0.0472
    assert checks["Figure 1 curve endpoints versus prose transfer returns"] == "paper_graphic_prose_conflict"
    assert checks["Figure 4 year coverage versus prose"] == "paper_graphic_prose_conflict"
    assert checks["Appendix C factor identity versus evolution diagram"] == "paper_internal_round_conflict"
    assert len(gaps) == 48 and {row["resolved"] for row in gaps} == {"no"}
    assert len(mechanisms) == 34
    assert Counter(row["status"] for row in mechanisms) == {
        "implemented_match": 15,
        "implemented_analogue": 1,
        "partial_analogue": 2,
        "not_implemented_as_claimed": 7,
        "config_conflict": 4,
        "missing_artifact": 5,
    }
    assert sum(row["paper_mechanism_credit"] for row in mechanisms) == 15


def test_committed_audit_is_self_hashing_and_never_promotes_components() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/quantaalpha"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((output / "native_component_execution.json").read_text(encoding="utf-8"))
    tables = read_csv(output / "paper_numeric_table_conformance.csv")
    labels = read_csv(output / "paper_numeric_figure_labels.csv")
    points = read_csv(output / "paper_plot_point_inventory.csv")
    configs = read_csv(output / "source_config_conformance.csv")
    inventory = read_csv(output / "released_source_inventory.csv")
    datasets = read_csv(output / "released_dataset_inventory.csv")
    assert manifest["overall_status"] == "native_architecture_substantial_but_full_paper_not_reproduced_zero_published_results"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_table_cells_total"] == 344
    assert manifest["native_numeric_table_cells_reproduced"] == 0
    assert manifest["paper_numeric_figure_labels_total"] == 40
    assert manifest["paper_discrete_unlabeled_marker_points_total"] == 47
    assert manifest["paper_raster_return_curves_total"] == 10
    assert manifest["paper_result_arrays_shipped"] == 0
    assert manifest["paper_factor_pool_shipped"] is False
    assert manifest["tracked_source_files_total"] == 237
    assert manifest["tracked_source_python_files_total"] == 135
    assert manifest["native_current_python_files_compiled"] == 135
    assert manifest["native_initial_python_files_compiled"] == 135
    assert manifest["native_component_driver_passed"] is True
    assert manifest["native_upstream_tests_passed"] == 0
    assert manifest["native_upstream_tests_failed"] == 1
    assert manifest["local_motif_proxy_paper_result_credit"] is False
    assert len(tables) == 344 and len(labels) == 40 and len(points) == 47
    assert len(configs) == 28 and Counter(row["status"] for row in configs)["conflict"] == 11
    assert len(inventory) == 237 and {row["paper_result_artifact"] for row in inventory} == {"False"}
    assert len(datasets) == 5 and {row["paper_result_artifact"] for row in datasets} == {"False"}
    assert native["component_driver_returncode"] == 0
    assert native["component_checks"]["trajectory_roundtrip"] is True
    assert native["component_checks"]["lineage_roundtrip"] is True
    assert native["component_checks"]["llm_or_market_api_called"] is False
    assert native["component_execution_is_paper_result_credit"] is False
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_primary_sources_when_available() -> None:
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_source")
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/quantaalpha_paper")
    if not source.exists() or not paper.exists():
        return
    assert str(audit.run_git(source, "rev-parse", "HEAD")).strip() == audit.SOURCE_COMMIT
    assert audit.sha256(paper / "paper.pdf") == audit.PAPER_VERSIONS["v3"]["pdf_sha256"]
    assert audit.sha256(paper / "daily_pv_debug.h5") == audit.HF_DEBUG_SHA256
    assert len(audit.source_inventory(source)) == 237
    assert len(audit.paper_source_inventory(paper / "source")) == 36
