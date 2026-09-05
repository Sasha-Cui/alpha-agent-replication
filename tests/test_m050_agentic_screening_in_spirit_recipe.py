from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M050_agentic_screening"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m050_recipe_pins_v2_and_missing_runtime_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["milestone_id"] == "M050"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["paper_source"]["version"] == "arXiv v2"
    assert recipe["paper_source"]["attributable_native_implementation_found"] is False
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_specification_path", "method_specification_sha256"),
        ("linked_news_dataset_audit_path", "linked_news_dataset_audit_sha256"),
        ("independent_implementation_audit_path", "independent_implementation_audit_sha256"),
        ("prompt_component_inventory_path", "prompt_component_inventory_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]


def test_m050_recipe_freezes_two_agent_consensus_and_precision_stage():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    fundamental = recipe["fundamental_llm_s"]
    assert [item["column"] for item in fundamental["inputs"]] == ["market_equity", "be_me", "ret_12_1"]
    sentiment = recipe["finbert_sentiment_proxy"]
    assert len(sentiment["inputs"]) == 4
    assert sentiment["buy_threshold"] == 0.10
    assert sentiment["sell_threshold"] == -0.10
    policy = recipe["consensus_and_quant_policy"]
    assert policy["formation_history_months"] == 180
    assert policy["minimum_security_history_months"] == 60
    assert policy["portfolio_objective"] == "maximum Sharpe ratio"
    assert policy["precision_winsorization"] == [0.01, 0.99]
    assert policy["transaction_cost_bps_one_way"] == 10
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 11
    assert len(recipe["approximated_elements"]) >= 8
    assert len(recipe["invented_elements"]) >= 8


def test_m050_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M050"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    assert sum(ledger["progress_summary"].values()) == 69
