from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M049_trusttrade"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m049_recipe_pins_paper_and_interface_boundaries():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M049"
    assert recipe["paper_source"]["attributable_trusttrade_pipeline_found"] is False
    assert recipe["paper_source"]["human_interfaces_found"] is True
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_specification_path", "method_specification_sha256"),
        ("human_interface_protocol_path", "human_interface_protocol_sha256"),
        ("input_temporal_contamination_path", "input_temporal_contamination_sha256"),
        ("published_result_panel_ledger_path", "published_result_panel_ledger_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]


def test_m049_recipe_freezes_selective_consensus_temporal_and_memory_policy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    domains = recipe["independent_domain_reports"]
    assert list(domains) == ["fundamentals", "market", "news", "sentiment"]
    assert all(len(reports) == 3 for reports in domains.values())
    assert all(len(specifications) == 3 for reports in domains.values() for specifications in reports.values())
    consensus = recipe["selective_consensus"]
    assert consensus["report_agents_per_domain"] == 3
    assert consensus["semantic_weight_lambda"] == 0.5
    assert consensus["support_weight_alpha"] == 0.5
    assert consensus["high_consensus_threshold"] == 0.6
    assert consensus["low_consensus_weight"] == 0.25
    policy = recipe["temporal_and_memory_policy"]
    assert policy["temporal_horizons_months"] == [1, 3, 6, 12]
    assert policy["reflection_reward_purge_months"] == 12
    assert policy["short_reflection_history_months"] == 12
    assert policy["long_reflection_history_months"] == 60
    assert policy["consensus_evidence_weight"] + policy["temporal_anchor_weight"] == 1.0
    assert policy["position_sizes"] == [0.25, 0.5, 0.75, 1.0]
    assert policy["minimum_risk_cap"] == 0.25
    assert policy["maximum_risk_cap"] == 0.75
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 12
    assert len(recipe["approximated_elements"]) >= 9
    assert len(recipe["invented_elements"]) >= 9


def test_m049_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M049"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    assert sum(ledger["progress_summary"].values()) == 69
