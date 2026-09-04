from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M041_cogalpha"
SCRIPT = ROOT / "scripts/run_cogalpha_evolved_factor_milestone.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("cogalpha_evolved_factor", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_recipe_selects_the_paper_showcased_evolved_factor_before_results():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_for_execution"
    assert recipe["canonical_work_id"] == "CensusArxiv251118850"
    assert recipe["source_function"] == "factor_price_impact_per_vol_tanh_1d"
    assert recipe["source_formula"] == "tanh(abs(close-open)/(volume*close+1e-9))"
    assert recipe["paper_factor"]["reported_ic"] == 0.0141
    assert recipe["paper_factor"]["reported_rankic"] == 0.0087
    assert recipe["paper_factor"]["direction"] == "positive"
    assert recipe["release_evidence"]["both_fork_heads_equal_official"] is True


def test_monthly_price_impact_preserves_formula_shape_and_invalid_volume_rule():
    frame = pd.DataFrame(
        {
            "ret": [0.10, -0.20, 0.0, 0.10, np.nan],
            "prc": [20.0, 10.0, 5.0, 5.0, 5.0],
            "dolvol": [1000.0, 2000.0, 500.0, 0.0, 100.0],
        }
    )
    score = MODULE.monthly_price_impact(frame)
    expected = np.tanh(np.array([2.0 / (1000.0 + 1e-9), 2.0 / (2000.0 + 1e-9), 0.0]))
    np.testing.assert_allclose(score.iloc[:3], expected, rtol=0, atol=1e-15)
    assert np.isnan(score.iloc[3])
    assert np.isnan(score.iloc[4])


def test_monthly_factor_uses_formation_return_not_next_month_return():
    frame = pd.DataFrame(
        {
            "ret": [0.10, -0.20],
            "prc": [20.0, 10.0],
            "dolvol": [1000.0, 2000.0],
            "ret_exc_lead1m": [99.0, -99.0],
        }
    )
    first = MODULE.monthly_price_impact(frame)
    changed = frame.copy()
    changed["ret_exc_lead1m"] *= -100
    second = MODULE.monthly_price_impact(changed)
    np.testing.assert_allclose(first, second, rtol=0, atol=0)


def test_mapping_and_nonclaims_are_explicit():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    mapping = recipe["jkp_mapping"]
    assert mapping["monthly_absolute_price_move"] == "abs(ret)*abs(prc)"
    assert mapping["monthly_dollar_volume"] == "dolvol"
    assert "no opening price" in mapping["semantic_assessment"]
    assert len(recipe["full_system_not_reproduced"]) == 7
    assert recipe["common_task_adaptations"]["portfolio"].startswith(
        "common value-weighted long/short deciles"
    )
