from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M043_quantaalpha"
SCRIPT = ROOT / "scripts/run_quantaalpha_factor_pool_milestone.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("quantaalpha_factor_pool", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_recipe_freezes_the_strongest_released_complete_pool_before_results():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_for_execution"
    assert recipe["milestone_id"] == "M043"
    assert recipe["canonical_work_id"] == "CensusArxiv260207085"
    assert recipe["candidate_id"] == "quantaalpha_prepublication_gpt_complete_170"
    assert recipe["release_evidence"]["custom_factor_count"] == 150
    assert recipe["release_evidence"]["complete_source_profile_factor_count"] == 170
    assert recipe["release_evidence"]["v3_factor_pool_released"] is False
    assert recipe["paper_headline"]["reported_ic"] == 0.0472
    assert recipe["paper_headline"]["reported_arr"] == 0.0468


def test_source_periods_are_retained_as_monthly_observation_counts():
    expression = "RANK(TS_CORR(LOG($close),SEQUENCE(40),40))+DELAY($close,252)"
    assert MODULE.translate_expression(expression) == expression
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert "retained exactly" in recipe["jkp_mapping"]["period_translation"]


def test_monthly_bar_mapping_uses_no_future_return():
    raw = pd.DataFrame(
        {
            "prc": [-110.0, 80.0, 10.0],
            "prc_high": [115.0, 90.0, 11.0],
            "prc_low": [95.0, 70.0, 9.0],
            "tvol": [1000.0, 2000.0, 3000.0],
            "ret": [0.10, -0.20, -1.0],
            "ret_total_lead1m": [9.0, -9.0, 4.0],
        }
    )
    bars = MODULE.monthly_bars(raw)
    np.testing.assert_allclose(bars["$close"], [110.0, 80.0, 10.0])
    np.testing.assert_allclose(bars["$open"].iloc[:2], [100.0, 100.0])
    assert np.isnan(bars["$open"].iloc[2])
    changed = raw.copy()
    changed["ret_total_lead1m"] *= -100
    pd.testing.assert_frame_equal(bars, MODULE.monthly_bars(changed))


def test_source_order_cross_sectional_preprocessing_is_deterministic():
    index = pd.MultiIndex.from_tuples(
        [(pd.Timestamp("2000-01-31"), "a"), (pd.Timestamp("2000-01-31"), "b"),
         (pd.Timestamp("2000-01-31"), "c")],
        names=["datetime", "instrument"],
    )
    frame = pd.DataFrame({"x": [np.nan, 2.0, np.inf], "y": [1.0, 3.0, 2.0]}, index=index)
    result = MODULE.source_cs_rank_norm(frame)
    np.testing.assert_allclose(result["x"], [-0.5766666666666667, 1.73, 0.5766666666666667])
    np.testing.assert_allclose(result["y"], [-0.5766666666666667, 1.73, 0.5766666666666667])


def test_formation_window_excludes_the_realization_only_terminal_month():
    metadata = pd.DataFrame(
        {"month": pd.to_datetime(["1999-07-31", "2024-11-30", "2024-12-31"])}
    )
    assert MODULE.formation_window_mask(metadata, "1999-07-31", "2024-11-30").tolist() == [
        True,
        True,
        False,
    ]


def test_topk_dropout_preserves_incumbents_except_bottom_replacements():
    positions = {f"s{i}": 0.02 for i in range(50)}
    scores = {f"s{i}": float(i) for i in range(55)}
    updated, traded, bought, sold = MODULE.topk_dropout_trade(
        positions, 0.0, scores, topk=50, n_drop=5
    )
    assert sold == ["s4", "s3", "s2", "s1", "s0"]
    assert bought == ["s54", "s53", "s52", "s51", "s50"]
    assert len(updated) == 50
    np.testing.assert_allclose(sum(updated.values()), 1.0, atol=1e-12, rtol=0)
    np.testing.assert_allclose(traded, 0.2)
    assert all(updated[f"s{i}"] == 0.02 for i in range(5, 50))
