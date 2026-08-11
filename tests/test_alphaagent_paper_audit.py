from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_alphaagent_paper.py"
SPEC = importlib.util.spec_from_file_location("alphaagent_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_targets_cover_all_numeric_table_cells() -> None:
    rows = audit.paper_numeric_rows()
    assert len(rows) == 106
    assert Counter(row["paper_table"] for row in rows) == {1: 6, 2: 100}
    assert Counter(row["cell_role"] for row in rows) == {
        "result": 100,
        "configuration": 6,
    }
    assert len(
        {
            (
                row["paper_table"],
                row["entity"],
                row["market"],
                row["period"],
                row["metric"],
            )
            for row in rows
        }
    ) == 106


def test_non_table_claims_preserve_result_boundary() -> None:
    rows = audit.published_non_table_claims()
    assert len(rows) == 26
    assert Counter(row["claim_role"] for row in rows) == {
        "result": 18,
        "configuration": 8,
    }
    assert {row["paper_result_credit"] for row in rows} == {False}


def test_committed_audit_is_fail_closed() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/alphaagent"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    table = read_csv(output / "tables_1_2_conformance.csv")
    claims = read_csv(output / "published_non_table_claims.csv")
    mechanisms = read_csv(output / "source_mechanism_conformance.csv")
    gaps = read_csv(output / "paper_specification_gaps.csv")
    inventory = read_csv(output / "released_source_inventory.csv")
    registry = read_csv(output / "post_paper_registry_metrics.csv")
    data_release = read_csv(output / "data_release_provenance.csv")
    factors = read_csv(output / "synthetic_base_factor_component.csv")
    component = json.loads((output / "native_component.json").read_text(encoding="utf-8"))

    assert manifest["overall_status"] == (
        "not_reproduced_post_paper_component_analogue_only"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_era_source_revision_available"] is False
    assert manifest["paper_numeric_table_cells_total"] == 106
    assert manifest["paper_numeric_result_cells_total"] == 100
    assert manifest["native_paper_table_result_cells_reproduced"] == 0
    assert manifest["published_non_table_result_claims_total"] == 18
    assert manifest["native_non_table_result_claims_reproduced"] == 0
    assert manifest["paper_specification_gaps_total"] == 17
    assert manifest["source_mechanism_dimensions_total"] == 32
    assert manifest["source_mechanism_component_matches_or_analogues"] == 4
    assert manifest["source_mechanism_fully_faithful"] is False
    assert manifest["post_paper_dsl_expressions_shipped"] == 13
    assert manifest["post_paper_registry_metric_entries"] == 8
    assert manifest["post_paper_registry_entries_receiving_paper_credit"] == 0
    assert manifest["current_post_paper_data_release_available"] is True
    assert manifest["current_post_paper_data_release_bytes"] == 524248466
    assert manifest["current_post_paper_data_release_valid_paper_input"] is False
    assert manifest["native_source_tests_passed_with_dependency_stubs"] == 80
    assert manifest["native_source_tests_dependency_faithful"] is False
    assert manifest["native_synthetic_base_factors_executable"] == 4
    assert manifest["native_synthetic_component_paper_result_reproduction"] is False

    assert Counter(row["status"] for row in table) == {
        "unavailable_missing_native_paper_result_path": 100,
        "configuration_not_reproduced_by_post_paper_release": 6,
    }
    assert Counter(row["claim_role"] for row in claims) == {
        "result": 18,
        "configuration": 8,
    }
    assert len(mechanisms) == 32
    assert Counter(row["paper_mechanism_credit"] for row in mechanisms) == {
        "False": 28,
        "True": 4,
    }
    assert len(gaps) == 17
    assert len(inventory) == 141
    assert len(registry) == 8
    assert {row["paper_result_credit"] for row in registry} == {"False"}
    assert len(data_release) == 1
    assert data_release[0]["paper_data_credit"] == "False"
    assert int(data_release[0]["bytes"]) == 524248466
    assert len(factors) == 4
    assert {row["native_parser_executable"] for row in factors} == {"True"}
    assert {row["paper_metric_reproduced"] for row in factors} == {"False"}
    assert component["upstream_tests"]["tests_passed"] == 80
    assert component["upstream_tests"]["status"] == (
        "passed_with_import_only_dependency_stubs"
    )
    assert component["synthetic_base_factor_component"]["deterministic"] is True
    assert component["synthetic_base_factor_component"]["sha256"] == (
        "e0bd090308b893c6bcf97cc1589538e4fcedc4a896bb90d21a0848e92d7a5dc9"
    )
    assert component["paper_result_reproduction"] is False

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_source_static_checks_when_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphaagent_source")
    if not source_root.exists():
        return
    assert audit.git_head(source_root) == audit.SOURCE_COMMIT
    first_commit, first_date = audit.git_first_commit(source_root)
    assert first_commit == audit.SOURCE_FIRST_COMMIT
    assert first_date.startswith("2026-07-01")
    mechanisms = {row["dimension"]: row for row in audit.source_conformance(source_root)}
    assert mechanisms["paper_era_source"]["status"] == "mismatch_post_paper_rewrite"
    assert mechanisms["ast_representation"]["status"] == "mismatch"
    assert mechanisms["largest_common_subtree"]["status"] == "missing"
    assert mechanisms["similarity_kind"]["status"] == "mismatch"
    assert mechanisms["paper_lightgbm"]["status"] == "missing"
    assert mechanisms["operator_library"]["status"] == "component_match"
