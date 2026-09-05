from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M030_mm_arc"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m030_recipe_pins_v3_paper_release_and_missing_payload_audit():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M030"
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_audit_path", "method_audit_sha256"),
        ("release_execution_path", "release_execution_sha256"),
        ("lfs_recovery_path", "lfs_recovery_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    provenance = json.loads((ROOT / evidence["source_provenance_path"]).read_text())
    assert provenance["arxiv"]["pdf_sha256"]["v3"] == recipe["paper_source"]["pdf_sha256"]
    assert provenance["arxiv"]["source_sha256"]["v3"] == recipe["paper_source"]["source_sha256"]


def test_m030_recipe_freezes_experts_pools_rabo_and_router():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["expert_candidate_features"]) == [
        "trend",
        "reversal",
        "breakout",
        "exposure_control",
    ]
    schema = recipe["candidate_schema"]
    assert schema["candidates_per_expert_regime"] == 6
    assert schema["admitted_per_pool"] == 5
    assert schema["single_market_pool_count"] == 12
    assert sum(schema["view_weights"].values()) == 1.0
    policy = recipe["routing_and_audit_policy"]
    assert policy["audit_history_months"] == 120
    assert policy["minimum_regime_months"] == 12
    assert policy["purged_block_proxy_count"] == 6
    assert policy["rabo_rank_weights"] == {
        "benchmark_exceedance": 0.3,
        "lower_tail_5pct": 0.3,
        "median": 0.15,
        "stability": 0.15,
        "turnover_penalty": -0.1,
    }
    assert policy["final_common_returns_used_for_pool_or_router_choice"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 7
    assert len(recipe["invented_elements"]) >= 8


def test_m030_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M030"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
