from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M047_blindtrade"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m047_recipe_pins_paper_source_and_release_gap():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M047"
    assert recipe["paper_source"]["attributable_implementation_found"] is False
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_specification_path", "method_specification_sha256"),
        ("prompt_schema_path", "prompt_schema_sha256"),
        ("published_result_ledger_path", "published_result_ledger_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    provenance = json.loads((ROOT / evidence["source_provenance_path"]).read_text())
    assert provenance["attributable_blindtrade_release_found"] is False
    assert provenance["official_pages_visually_checked"] == 18


def test_m047_recipe_freezes_four_agent_graph_intent_policy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    agents = recipe["anonymized_agents"]
    assert list(agents) == ["momentum", "news_event", "mean_reversion", "risk_regime"]
    assert all(len(features) == 5 for features in agents.values())
    assert all(item["sign"] in {-1, 1} for features in agents.values() for item in features)
    intents = recipe["intent_role_weights"]
    assert list(intents) == ["defensive", "neutral", "aggressive"]
    assert all(set(weights) == set(agents) for weights in intents.values())
    assert all(abs(sum(weights.values()) - 1.0) < 1e-15 for weights in intents.values())
    policy = recipe["blindtrade_policy"]
    assert policy["identity_features_used"] is False
    assert policy["agent_count"] == 4
    assert policy["agent_ic_history_months"] == 60
    assert policy["agent_reward_purge_months"] == 1
    assert policy["semantic_similarity_threshold"] == 0.75
    assert policy["semantic_neighbors"] == 10
    assert policy["semantic_graph_layers"] == 2
    assert policy["graph_self_weight"] + policy["graph_neighbor_weight"] == 1.0
    assert policy["intent_reward_history_months"] == 60
    assert policy["intent_reward_purge_months"] == 1
    assert policy["execution_inertia_eta"] == 0.10
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 12
    assert len(recipe["approximated_elements"]) >= 9
    assert len(recipe["invented_elements"]) >= 9


def test_m047_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M047"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
