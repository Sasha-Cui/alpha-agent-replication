from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M008_alpha_gpt_2_0"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m008_recipe_pins_the_unevaluated_primary_draft_and_lineage():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M008"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("method_audit_path", "method_audit_sha256"),
        ("lineage_path", "lineage_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    assert len(recipe["source_anchors"]) == 4


def test_m008_recipe_freezes_human_mining_modeling_and_analysis_stages():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["human_instruction"].startswith("Search from six price-reversal")
    assert recipe["mining_stage"]["candidate_count"] == 51
    assert recipe["mining_stage"]["selected_factors"] == 5
    assert recipe["modeling_stage"]["model"] == "rolling_ridge"
    assert recipe["modeling_stage"]["training_window_months"] == 60
    assert recipe["analysis_stage"]["high_risk_quantile"] == 0.2
    assert recipe["analysis_stage"]["high_risk_score_multiplier"] == 0.5
    assert recipe["chronological_policy"]["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m008_recipe_remains_pinned_after_the_ledger_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    milestone = next(row for row in ledger["milestones"] if row["milestone_id"] == "M008")
    assert milestone["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    if milestone["status"] == "completed_in_spirit":
        manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
        assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
