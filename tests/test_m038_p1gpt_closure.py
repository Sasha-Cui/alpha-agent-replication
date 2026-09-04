from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M038_p1gpt"
AUDIT = ROOT / "paper_runs/paper_replication_audits/p1gpt"


def test_m038_selects_the_layered_daily_policy_and_rejects_the_proxy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv251023032"
    config = recipe["paper_configuration"]
    assert config["layers"] == ["Input", "Planning", "Analysis", "Integration", "Decision"]
    assert config["action_space"] == ["Buy", "Sell", "Hold"]
    assert config["frequency"] == "daily"
    assert config["native_assets"] == ["AAPL", "GOOGL", "TSLA"]
    assert config["transaction_costs"] == 0
    assert len(recipe["missing_headline_objects"]) == 10
    assert len(recipe["rejected_substitutes"]) == 5
    assert "prior value/quality/momentum/low-risk" in recipe["rejected_substitutes"][0]["route"]


def test_m038_matches_the_pinned_paper_component_and_live_source_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    component = json.loads((AUDIT / "public_component_execution.json").read_text())
    with (AUDIT / "paper_version_summary.csv").open(newline="") as handle:
        paper = next(csv.DictReader(handle))
    assert recipe["paper_pdf_sha256"] == paper["paper_sha256"]
    assert recipe["paper_source_sha256"] == paper["source_sha256"]
    assert recipe["source_commit"] == component["commit"]
    assert component["python_files_compiled"] == 22
    assert component["paper_daily_prompt_present"] is False
    assert component["model_service_source_shipped"] is False
    assert component["database_state_shipped"] is False
    assert manifest["native_result_generation_pipeline_found"] is False
    live = recipe["live_source_recheck"]
    assert live["heads_unchanged"] is True
    assert live["branch_heads"]["main"] == component["commit"]
    assert live["tags"] == live["releases"] == 0


def test_m038_preserves_output_verification_without_policy_credit():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    credit = recipe["result_verification_credit"]
    assert credit["published_p1gpt_cells"] == 12
    assert credit["author_plot_position_values_recovered"] == 498
    assert credit["p1gpt_cells_matching_ordinary_rounding"] == 11
    assert credit["native_p1gpt_cells_regenerated_end_to_end"] == 0
    assert credit["native_agent_decisions_regenerated"] == 0
    assert manifest["direct_lookahead_counterexamples"] == 1
    with (AUDIT / "mechanism_conformance.csv").open(newline="") as handle:
        mechanisms = {row["dimension"]: row for row in csv.DictReader(handle)}
    assert mechanisms["timestamp alignment"]["status"] == "contradicted_by_case_output"
    assert mechanisms["no leverage"]["status"] == "contradicted_by_author_plot"
    assert mechanisms["native agent result runner"]["status"] == "missing"


def test_m038_has_no_return_artifact_and_advances_the_ledger():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m038 = rows["M038"]
    assert m038["status"] == "closed_not_evaluable"
    assert m038["monthly_returns_path"] == m038["metrics_path"] == m038["run_manifest_path"] == ""
    assert m038["recipe_path"] and m038["verdict_path"] and m038["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 38
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 31
