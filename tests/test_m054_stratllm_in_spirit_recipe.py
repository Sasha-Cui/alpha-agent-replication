from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M054_stratllm"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m054_recipe_pins_paper_and_missing_release():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result" and recipe["milestone_id"] == "M054"
    assert recipe["paper_source"]["attributable_implementation_or_actions_found"] is False
    evidence = recipe["strict_evidence"]
    for p, h in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_specification_path", "method_specification_sha256"),
        ("strategy_specification_path", "strategy_specification_sha256"),
        ("procedure_component_path", "procedure_component_sha256"),
    ):
        assert digest(ROOT / evidence[p]) == evidence[h]


def test_m054_recipe_freezes_sources_strategies_and_modes():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["multi_source_state"]) == ["price", "news", "annual_report"]
    assert len(recipe["expert_strategy_taxonomy"]) == 4
    policy = recipe["alignment_policy"]
    assert policy["source_reliability_history_months"] == 60
    assert policy["reward_purge_months"] == 1
    assert policy["free_mode_threshold"] == 0.05
    assert policy["guided_mode_lower_threshold"] == 0.0
    assert policy["action_hold_threshold"] == 0.10
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 7
    assert len(recipe["invented_elements"]) >= 7


def test_m054_is_active_when_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M054"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    assert sum(ledger["progress_summary"].values()) == 69
