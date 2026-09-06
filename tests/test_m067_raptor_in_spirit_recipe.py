from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_in_spirit/M067_raptor"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m067_recipe_freezes_orchestration_and_bl_before_result():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["milestone_id"] == "M067"
    assert recipe["status"] == "frozen_before_jkp_result"
    assert recipe["fidelity_label"] == "in_spirit_reconstruction"
    assert recipe["paper_source"]["native_output_snapshots_found"] == 166
    assert recipe["paper_source"]["causal_cross_sectional_message_and_input_lineage_found"] is False
    assert list(recipe["analyst_signal_cards"]) == [
        "fundamental",
        "macro",
        "market",
        "news",
        "social",
        "valuation",
    ]
    orchestration = recipe["orchestration_policy"]
    assert sum(orchestration["analyst_weights"].values()) == 1.0
    assert orchestration["debate_rounds_per_side"] == 2
    assert orchestration["frozen_role_formulas"] == {
        "analyst_consensus": "0.22*fundamental + 0.16*macro + 0.22*market + 0.18*news + 0.10*social + 0.12*valuation",
        "bull": "0.35*fundamental + 0.30*market + 0.20*news + 0.15*social",
        "bear": "0.45*valuation + 0.35*defensive + 0.20*fundamental",
        "defensive": "mean(-rank(beta_60m), -rank(rvol_21d), -rank(turnover_126d))",
        "research_manager": "0.60*analyst_consensus + 0.20*bull + 0.20*bear",
        "conservative": "0.60*bear + 0.40*defensive",
        "neutral": "research_manager",
        "aggressive": "0.60*bull + 0.40*market",
        "risk_judge": "0.50*neutral + 0.30*conservative + 0.20*aggressive",
    }
    bl = recipe["black_litterman_policy"]
    assert bl["categorical_annualized_views"] == {"BUY": 0.02, "HOLD": 0.0, "SELL": -0.02}
    assert (bl["risk_aversion"], bl["tau"], bl["omega_scale"]) == (3.0, 0.025, 0.5)
    assert bl["common_or_current_forward_returns_used_for_views"] is False


def test_m067_recipe_pins_paper_repository_and_audit_evidence():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["paper_source"]["official_pdf_sha256"] == "917b30a7ab49693c863720b4677de2f00329fd31f001f9a058c94298d81d6796"
    assert recipe["paper_source"]["author_repository_commit"] == "1793abf29ecde15597cb2bb4cb345accf655531f"
    for key, path_key in (
        ("audit_manifest", "audit_manifest_path"),
        ("source_provenance", "source_provenance_path"),
        ("method_specification", "method_specification_path"),
        ("native_execution", "native_execution_path"),
    ):
        assert digest(ROOT / recipe["strict_evidence"][path_key]) == recipe["strict_evidence"][f"{key}_sha256"]


def test_m067_recipe_discloses_distance_and_ledger_state():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["preserved_elements"] and recipe["approximated_elements"] and recipe["invented_elements"]
    assert recipe["anti_leakage"]["m067_common_result_seen_before_recipe_freeze"] is False
    ledger = json.loads((ROOT / "paper_runs/us_jkp_in_spirit/milestones.json").read_text())
    rows = {row["milestone_id"]: row for row in ledger["milestones"]}
    assert rows["M067"]["status"] in {"in_progress_in_spirit", "completed_in_spirit"}
