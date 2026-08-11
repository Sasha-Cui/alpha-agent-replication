from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_alphamemo_paper.py"
SPEC = importlib.util.spec_from_file_location("alphamemo_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_targets_cover_all_numeric_experimental_cells() -> None:
    rows = audit.paper_numeric_rows()
    assert len(rows) == 484
    assert Counter(row["paper_table"] for row in rows) == {
        2: 140,
        3: 48,
        4: 6,
        5: 182,
        6: 80,
        7: 8,
        8: 5,
        9: 15,
    }
    assert Counter(row["cell_role"] for row in rows) == {
        "result": 474,
        "configuration": 10,
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
    ) == 484


def test_cross_table_identities_are_only_internal_checks() -> None:
    rows = audit.paper_internal_identities()
    assert len(rows) == 69
    assert {row["absolute_difference"] for row in rows} == {0.0}
    assert {row["status"] for row in rows} == {
        "paper_internal_identity_match_not_independent_reproduction"
    }
    assert Counter((row["left_table"], row["right_table"]) for row in rows) == {
        (2, 3): 16,
        (2, 5): 28,
        (3, 5): 24,
        (7, 8): 1,
    }


def test_committed_audit_preserves_the_native_result_boundary() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/alphamemo"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "tables_2_9_conformance.csv")
    identities = read_csv(output / "paper_internal_identities.csv")
    source = read_csv(output / "source_mechanism_conformance.csv")
    formulas = read_csv(output / "representative_factor_parser_audit.csv")
    inventory = read_csv(output / "released_source_inventory.csv")
    component = json.loads((output / "native_synthetic_component.json").read_text(encoding="utf-8"))

    assert manifest["overall_status"] == "not_reproduced_native_synthetic_component_only"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_numeric_table_cells_total"] == 484
    assert manifest["paper_numeric_result_cells_total"] == 474
    assert manifest["native_paper_result_cells_reproduced"] == 0
    assert manifest["paper_result_cells_unavailable"] == 474
    assert manifest["active_official_runner_configuration_cells_matched"] == 4
    assert manifest["paper_pairwise_internal_identity_matches"] == 69
    assert manifest["native_source_tests_passed"] == 1
    assert manifest["native_synthetic_smoke_deterministic"] is True
    assert manifest["native_synthetic_smoke_paper_result_reproduction"] is False
    assert manifest["published_representative_formulas_native_parser_executable"] == 5
    assert manifest["published_representative_formula_metrics_reproduced"] == 0
    assert manifest["paper_ast_diff_mechanism_implemented_faithfully"] is False
    assert manifest["paper_parent_context_implemented_faithfully"] is False
    assert manifest["audit_called_llm_or_external_data_api"] is False

    assert Counter(row["status"] for row in conformance) == {
        "unavailable_missing_native_result_path": 474,
        "configuration_match_active_official_runner": 4,
        "configuration_not_reproduced_by_released_diagnostic_runner": 6,
    }
    assert len(identities) == 69
    assert len(source) == 32
    assert len(formulas) == 5
    assert {row["native_parser_executable"] for row in formulas} == {"True"}
    assert {row["paper_metric_reproduced"] for row in formulas} == {"False"}
    assert len(inventory) == 49

    assert component["upstream_tests_passed"] == 1
    assert component["synthetic_smoke_runs"] == 2
    assert component["synthetic_smoke_deterministic"] is True
    assert component["synthetic_smoke_sha256"] == (
        "82b09f8e2dbc77be1553295fad848b17354027b40fcd2e70c964be767f3955c1"
    )
    assert component["synthetic_smoke_summary"]["n_effective"] == 5
    assert component["paper_result_reproduction"] is False

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_source_static_checks_when_source_is_available() -> None:
    source_root = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_source")
    if not source_root.exists():
        return
    rows = audit.source_conformance(source_root)
    findings = {row["dimension"]: row for row in rows}
    assert audit.git_head(source_root) == audit.SOURCE_COMMIT
    assert findings["paper_split"]["status"] == "configuration_match"
    assert findings["admission_quality_threshold"]["status"] == "mismatch_active_runner"
    assert findings["ast_diff_motif"]["status"] == "mismatch"
    assert findings["parent_context"]["status"] == "mismatch"
    assert findings["native_output_snapshot"]["status"] == "missing"
