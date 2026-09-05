from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M040_finrs"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m040_recipe_pins_paper_components_and_reused_result_boundary():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M040"
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("source_provenance_path", "source_provenance_sha256"),
        ("method_audit_path", "method_audit_sha256"),
        ("component_execution_path", "component_execution_sha256"),
        ("cross_paper_lineage_path", "cross_paper_lineage_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    provenance = json.loads((ROOT / evidence["source_provenance_path"]).read_text())
    assert provenance["pinned_input_sha256"]["primary/official-v1.pdf"] == recipe["paper_source"]["pdf_sha256"]
    assert provenance["pinned_input_sha256"]["primary/source-v1.tar"] == recipe["paper_source"]["source_sha256"]


def test_m040_recipe_freezes_named_risk_mechanics_and_explicit_substitutions():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert list(recipe["hierarchical_signal_memory"]) == [
        "shallow_news",
        "middle_technical",
        "deep_fundamental",
    ]
    policy = recipe["risk_sensitive_policy"]
    assert policy["monthly_reward_horizons"] == [1, 3, 6]
    assert policy["reward_label_purge_months"] == 6
    assert policy["kelly_history_months"] == 20
    assert policy["scaled_kelly_fraction"] == 0.5
    assert policy["cvar_history_months"] == 20
    assert policy["cvar_tail_probability"] == 0.05
    assert policy["cvar_risk_budget"] == 0.05
    assert policy["maximum_absolute_exposure"] == 0.75
    assert policy["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 10
    assert len(recipe["approximated_elements"]) >= 7
    assert len(recipe["invented_elements"]) >= 8


def test_m040_is_active_when_recipe_is_frozen():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M040"]["status"] in {
        "in_progress_in_spirit",
        "completed_in_spirit",
    }
    assert sum(ledger["progress_summary"].values()) == 69
