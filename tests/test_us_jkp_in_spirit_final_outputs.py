from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "paper_runs/us_jkp_in_spirit"
BUILDER = ROOT / "scripts/build_us_jkp_in_spirit_final.py"
VALIDATOR = ROOT / "scripts/validate_us_jkp_in_spirit_final.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_final_synthesis_is_current_and_visually_valid():
    subprocess.run([sys.executable, str(BUILDER), "--root", str(ROOT), "--check"], check=True)
    subprocess.run([sys.executable, str(VALIDATOR), "--root", str(ROOT)], check=True)


def test_final_manifest_pins_exact_scope_and_all_outputs():
    manifest = json.loads((STUDY / "final_manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["paper_milestones"] == 69
    assert manifest["carried_strict_evaluations"] == 17
    assert manifest["researcher_authored_in_spirit_reconstructions"] == 45
    assert manifest["structural_discards"] == 7
    assert manifest["common_paths_evaluated"] == 62
    assert manifest["full_native_systems_reproduced_end_to_end"] == 0
    assert manifest["native_empirical_claims_tested"] == 0
    assert manifest["positive_full_cagr_count"] == 29
    assert manifest["positive_jkp_excess_count"] == 20
    assert manifest["raw_primary_rejections_at_5pct"] == 4
    assert manifest["holm_rejections_at_5pct"] == 1
    for relative, expected in manifest["output_sha256"].items():
        assert digest(STUDY / relative) == expected


def test_final_audit_keeps_fidelity_classes_and_missing_discards_separate():
    table = pd.read_csv(STUDY / "visual_tables/complete_results_full_audit.csv")
    family = pd.read_csv(STUDY / "visual_tables/family_inference_full_audit.csv")
    assert table.disposition.value_counts().to_dict() == {
        "completed_in_spirit": 45,
        "carried_common_evaluation": 17,
        "discarded_structural_mismatch": 7,
    }
    assert table.common_jkp_evaluated.sum() == 62
    assert not table.native_system_end_to_end_reproduced.any()
    assert not table.native_empirical_claim_tested.any()
    discards = table.loc[table.disposition.eq("discarded_structural_mismatch")]
    assert discards.full_cagr.isna().all()
    assert discards.jkp_excess_annualized.isna().all()
    assert len(family) == 62
    assert family.holm_reject_5pct.sum() == 1
    survivor = family.loc[family.holm_reject_5pct].iloc[0]
    assert survivor.milestone_id == "M008"
    assert survivor.jkp_excess_annualized < 0
