from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper_runs/us_jkp_headline/M044_factorminer"
SCRIPT = ROOT / "scripts/run_factorminer_top40_milestone.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("factorminer_top40", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_recipe_freezes_current_v2_top40_ic_weighted_strategy():
    recipe = json.loads((OUTPUT / "recipe.json").read_text())
    assert recipe["status"] == "frozen_for_execution"
    assert recipe["paper_version"]["version"] == "v2"
    assert recipe["paper_version"]["source_archive_sha256"] == MODULE.PAPER_SOURCE_SHA256
    assert recipe["formula_evidence"]["formula_count"] == 110
    assert recipe["fixed_learning_policy"]["training_months"] == 12
    assert recipe["paper_headline"]["reported_csi500_ic"] == 0.1511
    assert recipe["classification_if_executed"] == "completed_partial"


def test_monthly_bar_mapping_uses_no_future_return():
    raw = pd.DataFrame(
        {"prc": [-110.0, 80.0], "prc_high": [115.0, 90.0], "prc_low": [95.0, 70.0],
         "tvol": [10.0, 20.0], "dolvol": [1000.0, 3000.0], "ret": [0.10, -0.20],
         "ret_exc_lead1m": [99.0, -99.0]}
    )
    bars = MODULE.monthly_bars(raw)
    np.testing.assert_allclose(bars["$open"], [100.0, 100.0])
    np.testing.assert_allclose(bars["$vwap"], [100.0, 150.0])
    changed = raw.copy()
    changed["ret_exc_lead1m"] *= -10
    pd.testing.assert_frame_equal(bars, MODULE.monthly_bars(changed))


def test_top40_selection_uses_absolute_training_ic_and_signed_weights():
    rows = []
    for month in pd.date_range("2000-01-31", periods=12, freq="ME"):
        for number in range(30):
            rows.append({"month": month, "security_id": f"s{number:02d}", "label": float(number)})
    panel = pd.DataFrame(rows)
    noisy = np.tile(np.r_[np.arange(0, 30, 2), np.arange(1, 30, 2)], 12)
    features = pd.DataFrame(
        {"001": panel.label, "002": -panel.label, "003": noisy},
        index=panel.index,
    )
    selection = MODULE.select_ic_weighted(features, panel, training_months=12, top_n=2)
    assert selection.loc[selection.selected, "factor_id"].tolist() == ["001", "002"]
    assert selection.loc[selection.factor_id.eq("001"), "direction"].iloc[0] == 1
    assert selection.loc[selection.factor_id.eq("002"), "direction"].iloc[0] == -1
    np.testing.assert_allclose(selection.loc[selection.selected, "weight"].sum(), 1.0)
