from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M022_rd_agent"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m022_recipe_pins_primary_source_and_strict_audit():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M022"
    assert "not R&D-Agent-Quant" in recipe["claim_boundary"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("mechanism_conformance_path", "mechanism_conformance_sha256"),
        ("native_execution_path", "native_execution_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    manifest = json.loads((ROOT / evidence["audit_manifest_path"]).read_text())
    assert manifest["paper_hashes"]["arxiv_v2_pdf"] == recipe["paper_source"]["pdf_sha256_from_pinned_audit"]
    assert manifest["paper_era_source_revision"] == recipe["paper_source"]["paper_era_source_commit"]


def test_m022_recipe_freezes_parallel_search_and_chronological_evaluation():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    branches = recipe["hypothesis_branches"]
    assert len(branches) == 6
    assert all(len(features) == 3 for features in branches.values())
    policy = recipe["research_development_policy"]
    assert policy["history_months"] == 120
    assert policy["research_months"] == 96
    assert policy["validation_months"] == 24
    assert policy["branch_candidate_operators"] == [
        "leader",
        "pair_mean",
        "all_mean",
        "consensus_median",
    ]
    assert policy["branch_winners_retained"] == 6
    assert policy["validation_folds"] == 3
    assert policy["validation_fold_months"] == 8
    assert policy["final_common_returns_used_for_search_or_selection"] is False
    assert len(recipe["preserved_elements"]) >= 8
    assert len(recipe["approximated_elements"]) >= 6
    assert len(recipe["invented_elements"]) >= 7


def test_m022_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M022"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
