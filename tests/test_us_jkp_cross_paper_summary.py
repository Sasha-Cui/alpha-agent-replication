from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "paper_runs/us_jkp_headline"
SCRIPT = ROOT / "scripts/build_us_jkp_cross_paper_summary.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("cross_paper_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_holm_uses_declared_family_size_and_step_down_monotonicity():
    builder = load_builder()
    rows = [
        {"milestone_id": "M001", "title": "a", "jkp_excess_p_two_sided": 0.0001},
        {"milestone_id": "M002", "title": "b", "jkp_excess_p_two_sided": 0.001},
        {"milestone_id": "M003", "title": "c", "jkp_excess_p_two_sided": 0.2},
    ]
    result = builder.holm_rows(rows, 69)
    assert [row["holm_multiplier"] for row in result] == [69, 68, 67]
    assert result[0]["holm_adjusted_p"] == pytest.approx(0.0069)
    assert result[1]["holm_adjusted_p"] == pytest.approx(0.068)
    assert result[2]["holm_adjusted_p"] == 1.0
    assert [row["holm_reject_5pct"] for row in result] == [True, False, False]


def test_final_summary_is_current_and_keeps_missing_results_missing():
    subprocess.run([sys.executable, str(SCRIPT), "--root", str(ROOT), "--check"], check=True)
    table = pd.read_csv(STUDY / "cross_paper_summary.csv")
    assert len(table) == 69
    assert table.milestone_id.tolist() == [f"M{number:03d}" for number in range(1, 70)]
    assert table.status.value_counts().to_dict() == {
        "closed_not_evaluable": 52,
        "completed_partial": 16,
        "completed_adapted": 1,
    }
    assert table.common_jkp_evaluated.sum() == 17
    assert not table.original_system_end_to_end_reproduced.any()
    unavailable = table.loc[~table.common_jkp_evaluated]
    assert unavailable.full_cagr.isna().all()
    assert unavailable.jkp_excess_p_two_sided.isna().all()
    assert unavailable.holm_adjusted_p.isna().all()


def test_final_family_inference_matches_primary_metrics_and_has_no_rejections():
    family = pd.read_csv(STUDY / "family_inference.csv")
    table = pd.read_csv(STUDY / "cross_paper_summary.csv")
    assert len(family) == 17
    assert family.raw_p_two_sided.is_monotonic_increasing
    assert family.holm_adjusted_p.is_monotonic_increasing
    assert set(family.milestone_id) == set(table.loc[table.common_jkp_evaluated, "milestone_id"])
    assert not family.holm_reject_5pct.any()
    assert (family.holm_adjusted_p == 1.0).all()
    assert (family.holm_multiplier == range(69, 52, -1)).all()


def test_final_manifest_pins_inputs_outputs_and_honest_claim_boundary():
    manifest = json.loads((STUDY / "final_manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["paper_milestones"] == manifest["closed_milestones"] == 69
    assert manifest["headline_adaptations_evaluated"] == 1
    assert manifest["central_partial_adaptations_evaluated"] == 16
    assert manifest["closed_not_evaluable"] == 52
    assert manifest["full_original_systems_reproduced_end_to_end"] == 0
    assert manifest["raw_primary_rejections_at_5pct"] == 0
    assert manifest["holm_family_size"] == 69
    assert manifest["holm_rejections_at_5pct"] == 0
    assert manifest["non_evaluable_performance_policy"] == "missing_not_zero"
    assert len(manifest["input_sha256"]) == 19
    assert set(manifest["output_sha256"]) == {
        "cross_paper_summary.csv",
        "family_inference.csv",
        "FINAL_SUMMARY.md",
    }
