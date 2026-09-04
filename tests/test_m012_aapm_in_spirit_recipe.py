from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M012_aapm"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m012_recipe_pins_primary_method_and_native_component_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["milestone_id"] == "M012"
    assert digest(ROOT / recipe["paper_source"]["path"]) == recipe["paper_source"]["sha256"]
    evidence = recipe["strict_evidence"]
    for path_key, hash_key in (
        ("audit_manifest_path", "audit_manifest_sha256"),
        ("method_path", "method_sha256"),
        ("native_execution_path", "native_execution_sha256"),
    ):
        assert digest(ROOT / evidence[path_key]) == evidence[hash_key]
    assert len(recipe["source_anchors"]) == 4


def test_m012_recipe_freezes_reports_embeddings_factors_and_pretraining():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert len(recipe["stock_report_proxy"]) == 5
    assert len(recipe["macro_report_proxy"]) == 3
    assert len(recipe["manual_factors"]) == 6
    assert len(recipe["asset_embedding_proxy"]) == 3
    model = recipe["hybrid_model"]
    assert model["report_memory_weight"] == 0.5
    assert model["pretraining_window_months"] == 120
    assert model["ridge_penalty"] == 10.0
    assert recipe["chronological_policy"]["final_common_returns_used_for_policy_choice"] is False
    assert len(recipe["preserved_elements"]) >= 6
    assert len(recipe["approximated_elements"]) >= 5
    assert len(recipe["invented_elements"]) >= 5


def test_m012_recipe_remains_pinned_after_the_ledger_advances():
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    milestone = next(row for row in ledger["milestones"] if row["milestone_id"] == "M012")
    assert milestone["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
    if milestone["status"] == "completed_in_spirit":
        manifest = json.loads((OUTPUT / "run_manifest.json").read_text())
        assert manifest["recipe_sha256"] == digest(OUTPUT / "recipe.json")
