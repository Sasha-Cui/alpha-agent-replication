from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M046_factorengine"
SCRIPT = ROOT / "scripts/run_factorengine_evolved_factor_milestone.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("factorengine_evolved", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_recipe_freezes_the_showcased_evolved_program_and_one_line_repair():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_for_execution"
    assert recipe["milestone_id"] == "M046"
    assert recipe["candidate_id"] == "factorengine_showcased_evolved_factor_40"
    assert recipe["source_program"]["function"] == "trend_factor"
    assert recipe["source_program"]["default_weights"] == {"w1": 0.25, "w2": 0.25, "w3": 0.5}
    assert recipe["source_program"]["repair_changes_economic_logic"] is False
    assert "high - low" in recipe["source_program"]["compatibility_repair"]


def test_evolved_factor_matches_hand_calculation_without_future_returns():
    close = np.arange(10.0, 20.0)
    raw = pd.DataFrame(
        {
            "security_id": [f"s{i}" for i in range(10)],
            "month": pd.to_datetime(["2000-01-31"] * 10),
            "prc": close,
            "prc_high": close + np.array([1, 3, 2, 4, 1, 2, 5, 3, 2, 4]),
            "prc_low": close - np.array([2, 1, 3, 1, 4, 2, 1, 5, 2, 3]),
            "tvol": np.array([9, 3, 8, 2, 7, 1, 6, 4, 10, 5]) * 100.0,
            "ret": [0.10, -0.05, 0.03, -0.08, 0.12, -0.02, 0.07, -0.04, 0.01, -0.10],
            "ret_exc_lead1m": np.arange(10.0),
        }
    )
    first = MODULE.evolved_factor_score(raw, smoothing_window=1)
    changed = raw.copy()
    changed["ret_exc_lead1m"] *= -100
    second = MODULE.evolved_factor_score(changed, smoothing_window=1)
    np.testing.assert_allclose(first, second, rtol=0, atol=0)
    assert np.isfinite(first).all()
    np.testing.assert_allclose(first.mean(), 0.0, atol=1e-12)
    np.testing.assert_allclose(first.std(ddof=0), 1.0, atol=1e-12)


def test_invalid_monthly_open_or_range_is_not_fabricated():
    raw = pd.DataFrame(
        {"security_id": ["a", "b"], "month": pd.to_datetime(["2000-01-31"] * 2),
         "prc": [10.0, 10.0], "prc_high": [10.0, 11.0], "prc_low": [10.0, 9.0],
         "tvol": [100.0, 100.0], "ret": [0.0, -1.0]}
    )
    result = MODULE.evolved_factor_score(raw, smoothing_window=1)
    assert result.isna().all()
