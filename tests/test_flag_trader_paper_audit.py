from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_flag_trader_paper.py"
SPEC = importlib.util.spec_from_file_location("flag_trader_paper_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_committed_result_census_is_complete_and_fail_closed() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/flag_trader"
    rows = read_csv(output / "paper_table_result_conformance.csv")
    assert len(rows) == 360
    assert Counter(row["paper_table"] for row in rows) == {"Table 1": 180, "Table 2": 180}
    assert Counter(row["asset"] for row in rows) == {
        "MSFT": 60,
        "JNJ": 60,
        "UVV": 60,
        "HON": 60,
        "TSLA": 60,
        "BTC": 60,
    }
    assert Counter(row["metric"] for row in rows) == {
        "CR_pct": 90,
        "SR": 90,
        "AV_pct": 90,
        "MDD_pct": 90,
    }
    credited = [row for row in rows if row["paper_result_credit"] == "True"]
    assert len(credited) == 6
    assert {row["model"] for row in credited} == {"Buy & Hold"}
    assert {row["native_flag_trader_result_credit"] for row in rows} == {"False"}
    current = [row for row in rows if row["current_public_response_verification"] == "True"]
    assert len(current) == 4
    assert {(row["asset"], row["metric"]) for row in current} == {
        ("TSLA", "CR_pct"), ("TSLA", "SR"), ("TSLA", "AV_pct"), ("TSLA", "MDD_pct")
    }
    assert {row["paper_result_credit"] for row in current} == {"False"}


def test_author_linked_baseline_execution_is_partial_and_formula_specific() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/flag_trader"
    rows = read_csv(output / "buy_hold_baseline_reproduction.csv")
    assert len(rows) == 20
    literal = [row for row in rows if row["paper_result_credit"] == "True"]
    assert len(literal) == 6
    assert Counter((row["asset"], row["metric"]) for row in literal) == Counter(
        {
            ("MSFT", "MDD_pct"): 1,
            ("JNJ", "MDD_pct"): 1,
            ("UVV", "MDD_pct"): 1,
            ("HON", "MDD_pct"): 1,
            ("BTC", "AV_pct"): 1,
            ("BTC", "MDD_pct"): 1,
        }
    )
    compatible = [
        row for row in rows if row["paper_compatible_match_at_paper_precision"] == "True"
    ]
    assert len(compatible) == 7
    btc_sharpe = next(row for row in rows if row["asset"] == "BTC" and row["metric"] == "SR")
    assert btc_sharpe["paper_value"] == "0.683"
    assert btc_sharpe["released_investorbench_literal_match_at_paper_precision"] == "False"
    assert btc_sharpe["paper_compatible_match_at_paper_precision"] == "True"
    assert btc_sharpe["status"] == (
        "paper_match_requires_mixed_252_return_365_volatility_annualization"
    )


def test_paper_claims_do_not_overstate_table_dominance() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/flag_trader"
    claims = read_csv(output / "qualitative_claim_audit.csv")
    dominance = next(row for row in claims if "LLM-agentic baselines" in row["claim"])
    assert dominance["observed"] == "7/24 overall; 7/12 CR-or-SR; 0/12 AV-or-MDD"
    buy_hold = next(row for row in claims if row["claim"].endswith("Buy & Hold"))
    assert buy_hold["observed"] == "17 wins, 2 ties, 5 losses"
    convergence = next(row for row in claims if "stable optimal policy" in row["claim"])
    assert convergence["assessment"].startswith("unsupported")


def test_current_tsla_response_verifies_four_cells_without_paper_time_credit() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/flag_trader"
    rows = read_csv(output / "tsla_current_response_reproduction.csv")
    assert len(rows) == 4
    assert {row["metric"] for row in rows} == {"CR_pct", "SR", "AV_pct", "MDD_pct"}
    assert {row["match_at_paper_precision"] for row in rows} == {"True"}
    assert {row["paper_time_snapshot"] for row in rows} == {"False"}
    assert {row["paper_result_credit"] for row in rows} == {"False"}
    assert next(row for row in rows if row["metric"] == "CR_pct")[
        "pinned_current_yahoo_value"
    ].startswith("39.243875")
    assert next(row for row in rows if row["metric"] == "AV_pct")[
        "pinned_current_yahoo_value"
    ].startswith("75.853563")
    assert next(row for row in rows if row["metric"] == "SR")[
        "pinned_current_yahoo_value"
    ].startswith("0.869170")
    assert audit.sha256(output / "yahoo_tsla_response.json") == audit.YAHOO_TSLA_SHA256


def test_configuration_and_method_gaps_remain_separate_from_execution() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/flag_trader"
    hyperparameters = read_csv(output / "paper_hyperparameters.csv")
    methods = read_csv(output / "method_specification_audit.csv")
    candidate = read_csv(output / "unaffiliated_candidate_audit.csv")
    assert len(hyperparameters) == 22
    assert {row["released_flag_trader_config_value"] for row in hyperparameters} == {""}
    assert len(methods) == 48
    assert sum(row["severity"] == "blocking" for row in methods) >= 20
    assert {row["native_flag_trader_verified"] for row in methods} == {"False"}
    assert len(candidate) == 9
    assert {row["paper_author_linked"] for row in candidate} == {"False"}
    assert {row["paper_result_credit"] for row in candidate} == {"False"}


def test_manifest_and_all_committed_evidence_hashes_are_consistent() -> None:
    output = ROOT / "paper_runs/paper_replication_audits/flag_trader"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    native = json.loads((output / "native_execution.json").read_text(encoding="utf-8"))
    provenance = json.loads((output / "source_provenance.json").read_text(encoding="utf-8"))
    assert manifest["overall_status"] == (
        "partial_6_of_360_author_linked_buy_hold_baseline_cells_reproduced_"
        "4_current_response_verified_zero_flag_trader_native_results"
    )
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_evidence_route"] == "paper_only_underspecified"
    assert manifest["paper_table_cells_total"] == 360
    assert manifest["paper_table_cells_reproduced"] == 6
    assert manifest["paper_table_cells_verified_current_public_response"] == 4
    assert manifest["paper_table_cells_checked_total"] == 10
    assert manifest["flag_trader_native_result_cells_reproduced"] == 0
    assert manifest["paper_compile_pages"] == 14
    assert manifest["paper_hyperparameter_settings"] == 22
    assert manifest["investorbench_release_tracked_files"] == 48
    assert manifest["investorbench_release_python_files"] == 23
    assert manifest["investorbench_release_native_result_artifacts"] == 0
    assert manifest["buy_hold_cells_paper_compatible_matches"] == 7
    assert manifest["tsla_current_response_cells_checked"] == 4
    assert manifest["tsla_current_response_cells_matching"] == 4
    assert manifest["official_flag_trader_source_released"] is False
    assert native["flag_trader_native_execution_attempted"] is False
    assert native["paper_latex_compilation"]["exit_codes"] == [0, 0]
    assert provenance["author_linked_baseline_release"]["commit"] == audit.INVESTORBENCH_COMMIT
    assert provenance["unaffiliated_candidate"]["paper_credit"] is False
    assert provenance["current_tsla_market_response"]["paper_time_snapshot"] is False
    assert provenance["current_tsla_market_response"]["paper_result_credit"] is False
    for filename, expected in manifest["output_sha256"].items():
        assert audit.sha256(output / filename) == expected


def test_pinned_sources_and_dynamic_parsers_when_available() -> None:
    paper = Path("/nfs/roberts/scratch/pi_btk22/zc362/flag_trader_paper")
    investorbench = paper / "investorbench_source"
    candidate = paper / "candidate_parkxlab"
    if not paper.exists() or not investorbench.exists() or not candidate.exists():
        return
    audit.validate_primary_inputs(paper, investorbench, candidate)
    results = audit.parse_paper_results(paper)
    assert len(results) == 360
    audit.validate_final_pdf_tables(paper, results)
    assert len(audit.parse_hyperparameters(paper)) == 22
    baseline = audit.buy_hold_reproduction(investorbench, results)
    assert sum(row["paper_result_credit"] for row in baseline) == 6
    current = audit.tsla_current_response_reproduction(paper, results)
    assert len(current) == 4 and all(row["match_at_paper_precision"] for row in current)
    assert len(audit.source_inventory(investorbench)) == 48
