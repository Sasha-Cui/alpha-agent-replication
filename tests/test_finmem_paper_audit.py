from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_finmem_paper.py"
SPEC = importlib.util.spec_from_file_location("finmem_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_paper_targets_cover_every_table_2_to_5_metric_cell() -> None:
    rows = audit.paper_table_rows()
    assert len(rows) == 235
    assert Counter(row["paper_table"] for row in rows) == {
        2: 160,
        3: 30,
        4: 20,
        5: 25,
    }
    groups = {
        (row["paper_table"], row["scope"], row["strategy_or_configuration"])
        for row in rows
    }
    assert len(groups) == 47
    assert Counter(row["metric"] for row in rows) == {metric: 47 for metric in audit.METRICS}


def test_table_4_encodes_the_papers_volatility_values_without_repairing_them() -> None:
    rows = audit.volatility_identity_audit()
    mismatches = [
        row for row in rows if row["status"] == "paper_internal_annualization_mismatch"
    ]
    assert len(rows) == 47
    assert len(mismatches) == 4
    assert {row["paper_table"] for row in mismatches} == {4}
    assert {row["strategy_or_configuration"] for row in mismatches} == {
        "buy_and_hold",
        "self_adaptive",
        "risk_seeking",
        "risk_averse",
    }


def test_committed_audit_is_non_reproduction_and_fail_closed() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/finmem"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "tables_2_5_conformance.csv")
    volatility = read_csv(output / "paper_volatility_identity_audit.csv")
    archive = read_csv(output / "released_archive_inventory.csv")

    assert manifest["overall_status"] == "not_reproduced_missing_native_actions_and_original_inputs"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_result_rows_total"] == 47
    assert manifest["paper_result_cells_total"] == 235
    assert manifest["buy_hold_cells_recomputed"] == 40
    assert manifest["buy_hold_cells_matched"] == 16
    assert manifest["buy_hold_cells_mismatched_against_current_yahoo"] == 24
    assert manifest["non_buy_hold_cells_unverifiable"] == 195
    assert manifest["paper_result_rows_fully_matched"] == 2
    assert manifest["paper_result_rows_mismatched_against_current_yahoo"] == 6
    assert manifest["paper_result_rows_unverifiable"] == 39
    assert manifest["native_action_or_return_files_shipped"] == 0
    assert manifest["original_paper_news_filings_snapshot_shipped"] is False
    assert manifest["paper_selects_best_risk_profile_on_test_outcome"] is True
    assert manifest["paper_metric_is_self_financing_portfolio_return"] is False

    assert len(conformance) == 235
    assert Counter(row["status"] for row in conformance) == {
        "exact_displayed_precision_match": 16,
        "mismatch_against_pinned_2026_yahoo_retrieval": 24,
        "unverifiable_missing_native_action_series": 195,
    }
    buy_hold = [row for row in conformance if row["strategy_or_configuration"] == "buy_and_hold"]
    assert Counter((row["paper_table"], row["status"]) for row in buy_hold) == {
        ("2", "exact_displayed_precision_match"): 3,
        ("2", "mismatch_against_pinned_2026_yahoo_retrieval"): 22,
        ("3", "exact_displayed_precision_match"): 5,
        ("4", "exact_displayed_precision_match"): 3,
        ("4", "mismatch_against_pinned_2026_yahoo_retrieval"): 2,
        ("5", "exact_displayed_precision_match"): 5,
    }

    assert Counter(row["status"] for row in volatility) == {
        "rounding_consistent": 43,
        "paper_internal_annualization_mismatch": 4,
    }
    assert len(archive) == 10
    assert all("agent_action" in row["role"] or "paper_data" in row["role"] for row in archive)
    assert not any(row["role"] in {"native_action", "paper_result"} for row in archive)

    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected
