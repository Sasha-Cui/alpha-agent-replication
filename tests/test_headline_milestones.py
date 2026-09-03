from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "paper_runs/us_jkp_headline"


def test_headline_milestones_cover_exactly_the_existing_69_papers():
    ledger = json.loads((STUDY / "milestones.json").read_text())
    with (ROOT / "paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv").open(newline="") as handle:
        source = list(csv.DictReader(handle))
    rows = ledger["milestones"]
    assert len(rows) == len(source) == ledger["required_paper_count"] == 69
    assert len({row["milestone_id"] for row in rows}) == 69
    assert {row["canonical_work_id"] for row in rows} == {row["canonical_work_id"] for row in source}
    assert sum(row["status"] == "in_progress" for row in rows) <= 1
    assert (ROOT / ledger["protocol_path"]).is_file()
    assert (ROOT / ledger["benchmark_contract_path"]).is_file()
    counts = {status: sum(row["status"] == status for row in rows)
              for status in ["completed_adapted", "completed_partial", "closed_not_evaluable", "in_progress", "queued"]}
    assert ledger["progress_summary"] == {"closed": sum(counts[status] for status in ledger["terminal_statuses"]), **counts}


def test_closed_milestones_require_evaluation_or_an_explicit_non_evaluability_record():
    ledger = json.loads((STUDY / "milestones.json").read_text())
    allowed = {"queued", "in_progress", *ledger["terminal_statuses"]}
    for row in ledger["milestones"]:
        assert row["status"] in allowed
        if row["status"] in ledger["terminal_statuses"]:
            assert row["closure_reason"]
            assert row["verdict_path"] and (ROOT / row["verdict_path"]).is_file()
        if row["status"] in {"completed_adapted", "completed_partial"}:
            assert row["evaluated_scope"]
            for field in ["recipe_path", "implementation_path", "run_manifest_path", "monthly_returns_path", "metrics_path"]:
                assert row[field] and (ROOT / row[field]).is_file()


def test_common_headline_contract_preserves_retrospective_and_no_lookahead_boundaries():
    contract = json.loads((STUDY / "benchmark_contract.json").read_text())
    assert contract["benchmark_id"] == "us_jkp_headline_v1"
    assert contract["retrospective_design"] is True
    assert contract["pristine_holdout_claim"] is False
    assert contract["formation_may_use_future_return_availability"] is False
    assert contract["future_filling_allowed"] is False
    assert contract["inference_family_size"] == 69
    assert contract["primary_factor_benchmark"] == "ff5_mom_jkp132"
    assert contract["corrected_accounting_module"] == "src/alpha_evolve/submission_analysis.py"


def test_frozen_common_benchmark_has_full_calendar_and_pinned_preflight():
    contract = json.loads((STUDY / "benchmark_contract.json").read_text())
    assert contract["status"] == "frozen"
    preflight_path = ROOT / contract["preflight_path"]
    factors_path = ROOT / contract["factor_panel_path"]
    assert hashlib.sha256(preflight_path.read_bytes()).hexdigest() == contract["preflight_sha256"]
    assert hashlib.sha256(factors_path.read_bytes()).hexdigest() == contract["factor_panel_sha256"]
    preflight = json.loads(preflight_path.read_text())
    assert preflight["status"] == "passed"
    assert preflight["candidate_strategy_returns_computed"] is False
    assert preflight["formation_months"] == 305
    assert preflight["benchmark_factor_count"] == contract["factor_count"] == 133
    assert preflight["corrected_market_max_absolute_error"] < 1e-12
    assert preflight["legacy_market_clock_correlation"] > 0.99
    with factors_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 305
    assert rows[0]["month"] == "1999-08-31"
    assert rows[-1]["month"] == "2024-12-31"
    assert sum(name.startswith("char__") for name in rows[0]) == 132


def test_first_headline_is_source_selected_evc_not_best_of_six_jkp_backtests():
    recipe = json.loads((STUDY / "M001_gpt_signal/recipe.json").read_text())
    assert recipe["canonical_work_id"] == "CensusArxiv241018448"
    assert recipe["headline_signal"] == "Efficiency Value Composite (EVC)"
    assert recipe["trading_score_direction"] == -1
    assert recipe["paper_signed_all_sector_correlation"] == -0.14
    with (ROOT / "paper_runs/paper_replication_audits/gpt_signal/correlation_cell_reproduction.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    target = next(row for row in rows if row["matrix"] == "all_3m_all" and row["row"] == "EVC" and row["column"] == "Return")
    assert float(target["paper_display"]) == recipe["paper_signed_all_sector_correlation"]
    assert (ROOT / recipe["implementation_path"]).is_file()
    assert "portfolio" in recipe["portfolio_rule_scope"]
