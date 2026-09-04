from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M034_quantagents"
AUDIT = ROOT / "paper_runs/paper_replication_audits/quantagents"


def test_m034_selects_the_complete_four_agent_policy_and_rejects_the_proxy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv251004643"
    config = recipe["paper_configuration"]
    assert list(config["agents"]) == ["Otto", "Bob", "Dave", "Emily"]
    assert config["named_tools"] == 26
    assert config["described_indicators"] == 60
    assert config["retrieved_memories"] == 10
    assert config["foundation_model"] == "gpt-4o-2024-05-13"
    assert len(recipe["missing_headline_objects"]) == 9
    assert len(recipe["rejected_substitutes"]) == 5
    assert "previous momentum/quality/liquidity/low-risk" in recipe["rejected_substitutes"][0]["route"]


def test_m034_matches_the_pinned_document_and_static_release_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    provenance = json.loads((AUDIT / "source_provenance.json").read_text())
    release = json.loads((AUDIT / "release_execution_audit.json").read_text())
    assert recipe["paper_pdf_sha256"] == provenance["official_pdf_sha256"]
    assert recipe["paper_source_sha256"] == provenance["source_archive_sha256"]
    assert recipe["source_commit"] == provenance["project_repository_head"]
    assert manifest["official_pdf_pages"] == manifest["rebuilt_pdf_pages"] == 27
    assert manifest["public_system_source_files_recovered"] == 0
    assert manifest["published_numeric_table_cells"] == 238
    assert manifest["published_numeric_table_cells_faithfully_regenerated"] == 0
    assert manifest["published_empirical_panels"] == 14
    assert manifest["published_empirical_panels_faithfully_regenerated"] == 0
    assert release["rendered_algorithms"] == 4
    assert release["system_runner_files"] == release["python_files"] == 0
    live = recipe["live_source_recheck"]
    assert live["head_unchanged"] is True
    assert live["commits"] == 7
    assert live["tags"] == live["releases"] == live["forks"] == 0


def test_m034_preserves_the_specific_policy_identification_gaps():
    with (AUDIT / "method_specification_audit.csv").open(newline="") as handle:
        method = {row["dimension"]: row for row in csv.DictReader(handle)}
    assert method["project_repository"]["status"] == "r1_static_documentation"
    assert method["strategy_pool"]["status"] == "underspecified"
    assert method["risk_alert"]["status"] == "formula_incomplete"
    assert method["dual_reward_update"]["status"] == "nonoperational_formula"
    assert method["backtest_execution"]["status"] == "missing"
    with (AUDIT / "prompt_inventory.csv").open(newline="") as handle:
        prompts = list(csv.DictReader(handle))
    assert len(prompts) == 8
    assert all(row["actual_request_released"] == "False" for row in prompts)
    assert all(row["executable_prompt_path_released"] == "False" for row in prompts)


def test_m034_has_no_return_artifact_and_advances_the_ledger():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m034 = rows["M034"]
    assert m034["status"] == "closed_not_evaluable"
    assert m034["monthly_returns_path"] == m034["metrics_path"] == m034["run_manifest_path"] == ""
    assert m034["recipe_path"] and m034["verdict_path"] and m034["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 34
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 27
