from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M002_cryptotrade"


def test_m002_closes_the_headline_agent_without_relabelling_baselines():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["headline_strategy"].startswith("Full reflective LLM agent")
    assert recipe["released_step_llm_calls"] == ["on-chain analyst", "news analyst", "reflection analyst", "trader"]
    assert recipe["direct_port_decisions"] == 305 * 1000
    assert recipe["direct_port_llm_calls"] == 4 * 305 * 1000
    assert len(recipe["rejected_substitutes"]) == 5
    assert any("baselines" in route["reason"] for route in recipe["rejected_substitutes"])
    assert "No synthetic or zero return" in recipe["result_policy"]
    report = (OUTPUT / "verdict.md").read_text()
    assert "174/180 deterministic baseline matches" in report
    assert "40 historical LLM-output correspondences" in report
    assert "None of those is relabelled" in report


def test_m002_prior_audit_remains_partial_original_task_evidence():
    manifest = json.loads((ROOT / "paper_runs/paper_replication_audits/cryptotrade/manifest.json").read_text())
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert manifest["full_paper_reproduced"] is False
    assert manifest["paper_result_metric_cells_total"] == 480
    assert manifest["paper_sha256"] == recipe["paper_sha256"]
    assert manifest["source_commit"] == recipe["source_commit"]
    expected = json.loads((OUTPUT / "effort_record.json").read_text())["source_files_checked_for_headline_transfer"]
    for name in ["run_agent.py", "eth_trial.py", "env_history.py", "eth_env.py"]:
        assert expected[name] == manifest["source_file_sha256"][name]


def test_m002_has_no_fabricated_common_task_returns():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    m002 = next(row for row in ledger["milestones"] if row["milestone_id"] == "M002")
    assert m002["status"] == "closed_not_evaluable"
    assert m002["monthly_returns_path"] == m002["metrics_path"] == m002["run_manifest_path"] == ""
    assert m002["recipe_path"] and m002["verdict_path"] and m002["closure_reason"]
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 1
