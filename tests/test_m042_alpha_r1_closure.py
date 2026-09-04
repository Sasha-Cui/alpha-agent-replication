from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M042_alpha_r1"
AUDIT = ROOT / "paper_runs/paper_replication_audits/alpha_r1"


def test_m042_selects_the_trained_semantic_gate_and_rejects_proxies():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "closed_not_evaluable"
    assert recipe["canonical_work_id"] == "CensusArxiv251223515"
    config = recipe["paper_configuration"]
    assert config["backbone"] == "Qwen3-8B"
    assert config["training_method"] == "GRPO"
    assert config["retained_factor_zoo_size"] == 82
    assert config["testing_candidate_factors"] == 40
    assert config["holding_days"] == config["slots"] == 5
    assert config["top_n_per_slot"] == 10
    assert config["reported_runs"] == 5
    assert len(recipe["missing_headline_objects"]) == 12
    assert len(recipe["rejected_substitutes"]) == 5


def test_m042_matches_pinned_paper_and_live_placeholder_release():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    manifest = json.loads((AUDIT / "manifest.json").read_text())
    assert recipe["paper_pdf_sha256"] == manifest["paper_sha256"]
    assert recipe["paper_source_sha256"] == manifest["paper_source_sha256"]
    assert recipe["source_commit"] == manifest["source_commit"]
    assert manifest["published_table_and_heatmap_numeric_result_cells_total"] == 652
    assert manifest["native_table_and_heatmap_result_cells_reproduced"] == 0
    assert manifest["source_mechanism_dimensions_total"] == 70
    assert manifest["source_mechanism_matches_or_analogues"] == 0
    assert manifest["paper_source_release_claim_conflict"] is True
    live = recipe["release_evidence"]
    assert live["live_head_unchanged"] is True
    assert live["live_tracked_files"] == 1
    assert live["live_file"] == "README.md"
    assert live["live_file_bytes"] == 1101
    assert live["live_commits"] == 3
    assert live["live_tags"] == live["live_releases"] == 0


def test_m042_preserves_signal_reward_and_portfolio_gaps():
    with (AUDIT / "paper_specification_gaps.csv").open(newline="") as handle:
        gaps = list(csv.DictReader(handle))
    assert len(gaps) == 50
    assert all(row["resolved"] == "no" for row in gaps)
    missing = {row["missing_specification_or_artifact"] for row in gaps}
    assert "identities of the 82 retained Alpha101 factors" in missing
    assert "identities of the 40 test factors" in missing
    assert "all beta coefficients and intercept" in missing
    assert "trained Alpha-R1 checkpoint" in missing
    assert "per-run selections, actions, fills, returns, and NAVs" in missing
    with (AUDIT / "source_mechanism_conformance.csv").open(newline="") as handle:
        mechanisms = list(csv.DictReader(handle))
    assert len(mechanisms) == 70
    assert all(row["paper_mechanism_credit"] == "False" for row in mechanisms)


def test_m042_has_no_return_artifact_and_advances_the_ledger():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_headline/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    m042 = rows["M042"]
    assert m042["status"] == "closed_not_evaluable"
    assert m042["monthly_returns_path"] == m042["metrics_path"] == m042["run_manifest_path"] == ""
    assert m042["recipe_path"] and m042["verdict_path"] and m042["closure_reason"]
    assert ledger["progress_summary"]["closed"] >= 42
    assert ledger["progress_summary"]["closed_not_evaluable"] >= 34
