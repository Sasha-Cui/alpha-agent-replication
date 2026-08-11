from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_cryptotrade_paper.py"
SPEC = importlib.util.spec_from_file_location("cryptotrade_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_paper_targets_cover_every_table_2_to_4_metric_cell() -> None:
    rows = audit.paper_result_rows()
    assert len(rows) == 3 * 13 * 3 * 4 == 468
    assert {(row["asset"], row["strategy"], row["regime"]) for row in rows}
    counts = Counter(row["strategy"] for row in rows)
    assert set(counts.values()) == {36}
    assert set(audit.TRADITIONAL_STRATEGIES) | set(audit.TIME_SERIES_STRATEGIES) | set(audit.LLM_STRATEGIES) == set(
        counts
    )


def test_paper_ablation_conflict_is_encoded_without_resolving_it() -> None:
    assert audit.PAPER_ABLATION["full"] == (28.47, 0.23)
    rows = audit.paper_result_rows()
    btc = {
        row["metric"]: row["paper_value"]
        for row in rows
        if row["asset"] == "btc" and row["strategy"] == "gpt_4o" and row["regime"] == "bull"
    }
    eth = {
        row["metric"]: row["paper_value"]
        for row in rows
        if row["asset"] == "eth" and row["strategy"] == "gpt_4o" and row["regime"] == "bull"
    }
    assert audit.PAPER_ABLATION["full"] == (
        btc["total_return_pct"],
        btc["sharpe_ratio"],
    )
    assert audit.PAPER_ABLATION["full"] != (
        eth["total_return_pct"],
        eth["sharpe_ratio"],
    )


def test_committed_audit_is_partial_and_fail_closed() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/cryptotrade"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    conformance = read_csv(output / "tables_2_4_conformance.csv")
    selection = read_csv(output / "parameter_selection_audit.csv")

    assert manifest["overall_status"] == "partial_reproduction_traditional_baselines_only"
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_result_metric_cells_total"] == 468
    assert manifest["native_deterministic_metric_cells_recomputed"] == 180
    assert manifest["native_deterministic_metric_cells_matched"] == 174
    assert manifest["native_deterministic_metric_cells_mismatched"] == 6
    assert manifest["paper_result_metric_cells_unverifiable"] == 288
    assert manifest["paper_strategy_regime_rows_fully_matched"] == 43
    assert manifest["paper_strategy_regime_rows_mismatched"] == 2
    assert manifest["paper_strategy_regime_rows_unverifiable"] == 72
    assert manifest["full_period_llm_result_logs_shipped"] is False
    assert manifest["full_period_time_series_result_logs_shipped"] is False
    assert manifest["source_contains_hardcoded_credential_literal"] is False
    assert manifest["audit_imported_or_used_credential_module"] is False

    assert len(conformance) == 468
    statuses = Counter(row["status"] for row in conformance)
    assert statuses == {
        "exact_displayed_precision_match": 174,
        "mismatch": 6,
        "unverifiable_no_shipped_full_period_output": 288,
    }
    mismatches = [row for row in conformance if row["status"] == "mismatch"]
    assert {(row["asset"], row["strategy"], row["regime"]) for row in mismatches} == {
        ("eth", "sma", "sideways"),
        ("sol", "sma", "bear"),
    }
    sol = [row for row in mismatches if row["asset"] == "sol"]
    eth = [row for row in mismatches if row["asset"] == "eth"]
    assert {row["metric"] for row in sol} == set(audit.METRICS)
    assert {row["metric"] for row in eth} == {
        "daily_return_mean_pct",
        "daily_return_std_pct",
    }

    assert len(selection) == 6
    assert Counter(row["status"] for row in selection) == {
        "selection_rule_mismatch": 5,
        "selection_rule_match": 1,
    }
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected
