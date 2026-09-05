from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M029_tradinggroup"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m029_recipe_pins_primary_source_and_strict_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M029"
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_audit_path", "method_audit_sha256"),
        ("prompt_inventory_path", "prompt_inventory_sha256"),
        ("formula_inventory_path", "formula_inventory_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    provenance = json.loads((ROOT / evidence["source_provenance_path"]).read_text())
    assert provenance["arxiv"]["id"] == recipe["paper_source"]["arxiv_id"]
    assert provenance["release_boundary"]["attributable_tradinggroup_implementation_recovered"] is False


def test_m029_recipe_freezes_five_agents_reflection_styles_and_hard_intercept():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["information_agents"]) == [
        "news_sentiment",
        "financial_report",
        "technical",
    ]
    assert len(recipe["five_agent_roles"]) == 5
    policy = recipe["reflection_and_risk_policy"]
    assert policy["forecast_reflection_months"] == 60
    assert policy["style_reflection_months"] == 20
    assert list(policy["styles"]) == ["aggressive", "balanced", "conservative"]
    assert policy["styles"]["aggressive"]["positive_risk_intercept_quantile"] == 1.0
    assert policy["styles"]["balanced"]["positive_risk_intercept_quantile"] == 0.8
    assert policy["styles"]["conservative"]["positive_risk_intercept_quantile"] == 0.6
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 7
    assert len(recipe["invented_elements"]) >= 7


def test_m029_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M029"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
