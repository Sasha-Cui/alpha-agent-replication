from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M057_madevolve"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m057_recipe_freezes_joint_evolution_before_result():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["milestone_id"] == "M057"
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["paper_source"]["attributable_trading_program_or_actions_found"] is False
    assert recipe["candidate_library"]["total_features"] == 40
    assert recipe["baseline_program"] == {
        "terms": ["identity__ret_1_0", "identity__ret_6_1", "identity__ret_12_1"],
        "wrapper": "identity",
    }
    policy = recipe["evolution_policy"]
    assert policy["prehistory_formation_start"] == "1993-01-31"
    assert (policy["training_months"], policy["validation_months"], policy["frozen_test_months"]) == (48, 24, 24)
    assert policy["islands"] == 5 and policy["generations"] == 15
    assert policy["differential_patch_probability"] == 0.7
    assert policy["holistic_rewrite_probability"] == 0.3
    assert policy["migration_interval_generations"] == 5
    assert policy["migration_rate"] == 0.1
    assert policy["final_common_or_test_returns_used_for_program_selection"] is False


def test_m057_recipe_pins_primary_and_framework_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["paper_source"]["pdf_sha256"] == "9a8c776fddbeab3ca753dcaed8f04e74884b18d40e818e5d23ab9c0051751c16"
    assert recipe["paper_source"]["source_sha256"] == "e05e19e79fcf119e462c72bf7cd484b2c1cd9694fdca31d6f10ffbdafd4671ab"
    assert recipe["paper_source"]["framework_commit"] == "8b881d3a45d8f68050c28c8d64c2bb653001103a"
    for key, path_key in (
        ("audit_manifest", "audit_manifest_path"),
        ("source_provenance", "source_provenance_path"),
        ("method_specification", "method_specification_path"),
        ("release_execution", "release_execution_path"),
    ):
        assert digest(ROOT / recipe["strict_evidence"][path_key]) == recipe["strict_evidence"][f"{key}_sha256"]


def test_m057_recipe_discloses_distance_and_ledger_state():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["preserved_elements"] and recipe["approximated_elements"] and recipe["invented_elements"]
    assert recipe["anti_leakage"]["m057_common_result_seen_before_recipe_freeze"] is False
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M057"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
