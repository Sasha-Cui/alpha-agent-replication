from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "paper_runs/paper_replication_audits/trusttrade"
SPEC = importlib.util.spec_from_file_location("audit_trusttrade_paper", ROOT / "scripts/audit_trusttrade_paper.py")
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_json(name: str) -> dict:
    return json.loads((AUDIT_DIR / name).read_text())


def test_original_source_rebuild_and_visual_audit_are_pinned() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["arxiv_id"] == "2603.22567"
    assert provenance["arxiv_version"] == "v1"
    assert provenance["source_files"] == 44
    assert provenance["official_pages"] == 24
    assert provenance["rebuilt_pages"] == 24
    assert provenance["official_pages_visually_checked"] == 24
    assert provenance["rebuilt_pages_visually_checked"] == 24
    assert provenance["visual_defects_observed"] == 0
    assert provenance["official_rebuilt_token_jaccard"] > 0.999


def test_all_active_published_result_panels_fail_closed() -> None:
    results = rows("published_result_panel_ledger.csv")
    assert len(results) == 26
    assert Counter(row["figure"] for row in results) == {
        "study1": 7,
        "human_analysis": 9,
        "study3": 3,
        "main": 4,
        "main_2026q1": 3,
    }
    assert all(row["source_panel_recovered"] == "True" for row in results)
    assert all(row["raw_result_array_recovered"] == "False" for row in results)
    assert all(row["author_native_pipeline_executed"] == "False" for row in results)
    assert all(row["author_native_panel_regenerated"] == "False" for row in results)
    assert all(row["paper_result_credit"] == "False" for row in results)


def test_active_figure_denominators_and_source_assets_are_pinned() -> None:
    figures = rows("figure_inventory.csv")
    assert len(figures) == 27
    assert sum(int(row["active_panels"]) for row in figures) == 32
    assert sum(int(row["empirical_panels"]) for row in figures) == 26
    assert all(len(row["source_asset_sha256"]) == 64 for row in figures)
    assert all(row["source_asset_recovered"] == "True" for row in figures)
    assert all(row["author_native_regeneration"] == "False" for row in figures)
    assert all(row["paper_result_credit"] == "False" for row in figures)


def test_paper_linked_interfaces_recover_full_source_and_input_lineage() -> None:
    interfaces = rows("interface_artifact_inventory.csv")
    assert [row["ticker"] for row in interfaces] == ["AAPL", "GOOG", "NVDA"]
    assert all(row["source_map_entries"] == "847" for row in interfaces)
    assert all(row["source_contents_present"] == "847" for row in interfaces)
    assert all(row["trading_days"] == "61" for row in interfaces)
    assert all(row["first_date"] == "2024-01-02" for row in interfaces)
    assert all(row["last_date"] == "2024-03-28" for row in interfaces)
    assert all(row["input_fields"] == "15" for row in interfaces)
    assert all(row["human_interface_source_recovered"] == "True" for row in interfaces)
    assert all(row["human_interface_protocol_executable"] == "True" for row in interfaces)
    assert all(row["trusttrade_pipeline_source_recovered"] == "False" for row in interfaces)
    assert all(row["participant_output_recovered"] == "False" for row in interfaces)
    assert all(row["private_participant_endpoint_probed"] == "False" for row in interfaces)


def test_recovered_human_protocol_is_exact_and_not_conflated_with_baseline_schema() -> None:
    protocol = rows("human_interface_protocol.csv")
    assert [row["stage"] for row in protocol] == ["d0", "d1", "d2", "d3", "d4", "final"]
    assert all(row["action_required"] == "True" for row in protocol)
    assert all(row["reliability_1_to_100_required"] == "True" for row in protocol)
    assert all(row["rationale_recorded"] == "True" for row in protocol)
    assert [row["ai_decision_visibility_flag_recorded"] for row in protocol] == [
        "False", "True", "True", "True", "True", "False"
    ]
    assert protocol[-1]["trade_percentage_recorded"] == "True"
    assert "floor(cash*pct/close)" in protocol[-1]["execution_rule"]
    replay = rows("inactive_baseline_replay.csv")
    assert all(row["baseline_percentages_follow_human_widget_choices"] == "False" for row in replay)


def test_inactive_baseline_replay_preserves_convention_sensitivities() -> None:
    replay = rows("inactive_baseline_replay.csv")
    assert len(replay) == 36
    assert Counter(row["variant"] for row in replay) == {
        "paper_literal_production_loader": 12,
        "common_post_day_production_loader": 12,
        "raw_csv_sensitivity": 12,
    }
    matches = Counter(row["variant"] for row in replay if row["matches_printed_precision"] == "True")
    assert matches == {
        "paper_literal_production_loader": 1,
        "common_post_day_production_loader": 3,
        "raw_csv_sensitivity": 7,
    }
    assert all(row["table_active_in_published_pdf"] == "False" for row in replay)
    assert all(row["trusttrade_result_credit"] == "False" for row in replay)
    assert all(row["evidence_class"] == "paper_linked_interface_baseline_component_sensitivity" for row in replay)


def test_temporal_contamination_preserves_broad_and_strict_boundaries() -> None:
    evidence = rows("input_temporal_contamination.csv")
    assert len(evidence) == 76
    affected = {(row["ticker"], row["nominal_trade_date"]) for row in evidence}
    strict = {
        (row["ticker"], row["nominal_trade_date"])
        for row in evidence
        if row["strong_realized_future_fact_candidate"] == "True"
    }
    assert len(affected) == 68
    assert len(strict) == 30
    by_ticker = Counter(ticker for ticker, _ in affected)
    assert by_ticker == {"AAPL": 24, "GOOG": 24, "NVDA": 20}
    strict_by_ticker = Counter(ticker for ticker, _ in strict)
    assert strict_by_ticker == {"AAPL": 12, "GOOG": 7, "NVDA": 11}
    assert all("not a claim that every mention is leakage" in row["classification_boundary"] for row in evidence)
    anchors = {(row["ticker"], row["nominal_trade_date"], row["displayed_report_field"]): row for row in evidence}
    assert "January 3, 2026" in anchors[("AAPL", "2024-01-12", "fundamentals_report")]["example"]
    assert "Q3 2025" in anchors[("GOOG", "2024-01-03", "fundamentals_report")]["example"]
    assert "March 26, 2025" in anchors[("NVDA", "2024-03-27", "sentiment_report")]["example"]


def test_decision_content_removal_claim_has_four_direct_counterexamples() -> None:
    priming = rows("decision_priming_audit.csv")
    assert len(priming) == 4
    assert {(row["ticker"], row["nominal_trade_date"]) for row in priming} == {
        ("GOOG", "2024-01-25"),
        ("NVDA", "2024-01-09"),
        ("NVDA", "2024-01-17"),
        ("NVDA", "2024-02-22"),
    }
    assert all(row["raw_report_rendered_open_by_default"] == "True" for row in priming)
    assert all(row["paper_claims_decision_related_content_removed"] == "True" for row in priming)
    assert all(row["participant_priming_possible"] == "True" for row in priming)


def test_method_gaps_and_internal_conflicts_are_explicit() -> None:
    methods = {row["dimension"]: row for row in rows("method_specification_audit.csv")}
    assert methods["human stage order"]["sufficiently_specified"] == "True"
    assert methods["human execution rule"]["sufficiently_specified"] == "True"
    assert methods["consensus graph semantics"]["sufficiently_specified"] == "True"
    assert methods["temporal horizons"]["sufficiently_specified"] == "True"
    assert methods["memory horizon sets"]["sufficiently_specified"] == "True"
    for dimension in (
        "human participant outputs", "consensus agent count", "claim embedding model",
        "consensus hyperparameters", "temporal polynomial", "temporal forecast",
        "memory rolling window", "reflection prompts", "baseline parameters",
        "risk-free rate", "transaction costs and liquidity", "human ellipse", "2026 forward run",
    ):
        assert methods[dimension]["sufficiently_specified"] == "False"
    issues = {row["issue"]: row for row in rows("internal_consistency_audit.csv")}
    assert set(issues) == {
        "code_availability", "historical_information_time", "decision_content_removal",
        "interface_sizing", "memory_slope_symbol", "memory_backfill_index",
        "memory_sharpe_time_direction", "inactive_baseline_table",
        "baseline_percentage_domain", "human_data_availability", "real_time_auditability",
    }
    assert "31-repository" in issues["code_availability"]["evidence"]
    assert "68/183" in issues["historical_information_time"]["evidence"]
    assert "Four raw deployed reports" in issues["decision_content_removal"]["evidence"]


def test_bounded_release_search_never_becomes_absence_proof() -> None:
    provenance = load_json("source_provenance.json")
    assert provenance["paper_code_url"] == "https://github.com/Harvard-AI-and-Robotics-Lab"
    assert provenance["public_organization_repositories_checked"] == 31
    assert provenance["bounded_exact_searches_checked"] == 5
    assert provenance["bounded_exact_search_matches"] == 0
    assert provenance["attributable_trusttrade_pipeline_found"] is False
    assert "does not prove" in provenance["negative_search_scope"]
    assert provenance["participant_endpoint_probed"] is False


def test_manifest_and_readme_state_the_exact_fail_closed_boundary() -> None:
    manifest = load_json("manifest.json")
    assert manifest["active_empirical_result_panels"] == 26
    assert manifest["author_native_empirical_panels_regenerated"] == 0
    assert manifest["active_numeric_result_table_cells"] == 0
    assert manifest["inactive_source_table_cells"] == 12
    assert manifest["strict_literal_inactive_cells_matching"] == 1
    assert manifest["production_post_day_sensitivity_cells_matching"] == 3
    assert manifest["raw_csv_sensitivity_cells_matching"] == 7
    assert manifest["paper_linked_interfaces_recovered"] == 3
    assert manifest["paper_linked_stock_days_recovered"] == 183
    assert manifest["future_year_affected_stock_days"] == 68
    assert manifest["strong_future_fact_candidate_stock_days"] == 30
    assert manifest["decision_related_markers_exposed"] == 4
    assert manifest["baseline_percentages_outside_human_widget_days"] == 43
    assert manifest["participant_outputs_recovered"] == 0
    assert manifest["attributable_interface_component_recovered"] is True
    assert manifest["attributable_trusttrade_pipeline_found"] is False
    assert manifest["strict_success"] is False
    expected = {path.name for path in AUDIT_DIR.iterdir() if path.is_file() and path.name != "manifest.json"}
    assert set(manifest["generated_file_sha256"]) == expected
    readme = " ".join((AUDIT_DIR / "README.md").read_text().split())
    for marker in (
        "not reproducible end to end", "0/26", "183 stock-days", "1/12 displayed cells",
        "3/12", "7/12", "68/183", "four raw reports", "missing TrustTrade selective-consensus",
        "strict_success` remains false",
    ):
        assert marker in readme


def test_generator_is_deterministic_and_strict_mode_fails_closed(tmp_path: Path) -> None:
    if not audit.DEFAULT_SCRATCH.is_dir():
        pytest.skip("pinned TrustTrade audit evidence is only available on Bouchet")
    first = tmp_path / "first"
    second = tmp_path / "second"
    audit.build(audit.DEFAULT_SCRATCH, first)
    audit.build(audit.DEFAULT_SCRATCH, second)
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_trusttrade_paper.py"), "--output", str(tmp_path / "strict"), "--strict"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    strict = json.loads((tmp_path / "strict/manifest.json").read_text())
    assert strict["author_native_empirical_panels_regenerated"] == 0
    assert strict["strict_success"] is False
