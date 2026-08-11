from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_finagent_paper.py"
SPEC = importlib.util.spec_from_file_location("finagent_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_committed_result_census_is_complete_and_fail_closed() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/finagent"
    table = read_csv(output / "paper_numeric_table_conformance.csv")
    figures = read_csv(output / "paper_figure_display_inventory.csv")
    assert len(table) == 959
    assert Counter(row["paper_table"] for row in table) == {
        "Table 4 main comparison": 242,
        "Appendix Table 7 panel 1": 335,
        "Appendix Table 7 panel 2": 334,
        "Table 5 ablation": 48,
    }
    assert len(figures) == 102
    assert Counter(row["paper_figure"] for row in figures) == {
        "Figure 4 cumulative return": 66,
        "Figure 5 component ablation": 4,
        "Figure 5 retrieval/diversification": 3,
        "Appendix qualitative/performance cases": 29,
    }
    assert {row["paper_result_credit"] for row in table + figures} == {"False"}


def test_committed_manifest_keeps_document_and_experiment_credit_separate() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/finagent"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((output / "native_execution.json").read_text(encoding="utf-8"))
    assert manifest["overall_status"] == (
        "substantial_author_linked_source_but_zero_of_1061_published_result_units_reproduced"
    )
    assert manifest["replication_tier"] == (
        "R2_substantial_static_implementation_no_paper_result_reproduction"
    )
    assert manifest["paper_document_reproduced"] is True
    assert manifest["full_paper_reproduced"] is False
    assert manifest["published_result_display_units_total"] == 1061
    assert manifest["published_result_display_units_reproduced"] == 0
    assert manifest["paper_result_credit"] is False
    assert native["paper_source_compilation"]["exit_code"] == 0
    assert native["paper_source_compilation"]["compiled_pages"] == 43
    assert native["paper_source_compilation"]["paper_result_credit"] is False
    assert native["full_native_system_execution_attempted"] is False
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_committed_source_diagnostics_capture_material_conflicts() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/finagent"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    mechanisms = read_csv(output / "paper_mechanism_conformance.csv")
    references = read_csv(output / "released_missing_reference_diagnostics.csv")
    routes = read_csv(output / "released_processor_route_diagnostics.csv")
    metrics = read_csv(output / "paper_source_metric_formula_diagnostics.csv")
    strategies = read_csv(output / "released_strategy_record_inventory.csv")
    configs = read_csv(output / "released_config_conformance.csv")
    static = read_csv(output / "released_python_static_compilation.csv")
    artifacts = read_csv(output / "released_data_artifact_inventory.csv")
    assert len(mechanisms) == manifest["paper_mechanisms_audited"] == 31
    assert sum(row["released_source_conformance_credit"] == "True" for row in mechanisms) == 13
    statuses = {row["status"] for row in mechanisms}
    assert "conflict_future_14_days_rendered" in statuses
    assert "conflict_release_is_long_only" in statuses
    assert "conflict_signal_overwritten_by_default_parameters" in statuses
    assert Counter(row["issue"] for row in references) == {
        "nonexistent_stock_list_directory": 21,
        "missing_training_prompt_template": 60,
    }
    assert sum(row["matching_downloader_tag"] == "False" for row in routes) == 3
    assert len(metrics) == 3
    assert {row["matches_paper_formula"] for row in metrics} == {"False"}
    assert len(strategies) == 90
    assert sum(row["record_kind"] == "best_params" and row["nonempty"] == "True" for row in strategies) == 24
    assert len(configs) == 42
    assert all(row["all_reported_core_fields_match"] == "True" for row in configs)
    assert Counter(row["reflection_model"] for row in configs) == {"True": 36, "False": 6}
    assert {row["valid_environment_declared_mode"] for row in configs} == {"train"}
    assert len(static) == 142
    assert {row["status"] for row in static} == {"compiled"}
    assert all(row["released_count"] == "0" for row in artifacts)


def test_pinned_primary_sources_and_dynamic_parsers_when_available() -> None:
    source = Path("/nfs/roberts/scratch/pi_btk22/zc362/finagent_source")
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/finagent_paper")
    if not source.exists() or not paper.exists():
        return
    audit.validate_primary_inputs(source, paper)
    tables = audit.paper_table_rows(paper / "source_v3")
    figures = audit.paper_figure_rows(paper / "source_v3")
    assert len(tables) == 959
    assert len(figures) == 102
    assert len(audit.source_inventory(source)) == 341
    assert len(audit.strategy_record_rows(source)) == 90
    assert len(audit.config_conformance_rows(source)) == 42
    assert len(audit.source_reference_diagnostics(source)) == 81
    assert len(audit.static_python_rows(source)) == 142
