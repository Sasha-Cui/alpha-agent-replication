from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M066_alphaagentevo"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m066_recipe_freezes_agentic_rl_before_result():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["milestone_id"] == "M066"
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["paper_source"]["supplement_listed"] is True
    assert recipe["paper_source"]["supplement_recovered"] is False
    assert recipe["paper_source"]["paper_author_code_checkpoint_or_factor_pool_found"] is False
    assert recipe["factor_grammar"]["candidate_count"] == 210
    policy = recipe["agentic_rl_policy"]
    assert policy["training_steps"] == 150
    assert policy["offspring_tool_calls_per_step"] == 4
    assert policy["maximum_tool_calls"] == 4
    assert policy["elite_pool_capacity"] == 20
    reward = recipe["hierarchical_reward"]
    assert sum(reward[key] for key in reward if key.endswith("_weight")) == 1.0
    assert reward["tool_denominator_floor"] == 1.0
    assert recipe["portfolio_policy"]["common_or_post_training_returns_used_for_policy_or_alpha_selection"] is False


def test_m066_recipe_pins_openreview_and_audit_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert (
        recipe["paper_source"]["official_pdf_sha256"]
        == "5d26b8d22ef091fb89e1ae2b968821092f6f6b6ccc048f95b365713c4b182fd5"
    )
    for key, path_key in (
        ("audit_manifest", "audit_manifest_path"),
        ("source_provenance", "source_provenance_path"),
        ("method_specification", "method_specification_path"),
        ("candidate_release", "candidate_release_path"),
    ):
        assert digest(ROOT / recipe["strict_evidence"][path_key]) == recipe["strict_evidence"][f"{key}_sha256"]


def test_m066_recipe_discloses_distance_and_ledger_state():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["preserved_elements"] and recipe["approximated_elements"] and recipe["invented_elements"]
    assert recipe["anti_leakage"]["m066_common_result_seen_before_recipe_freeze"] is False
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M066"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
