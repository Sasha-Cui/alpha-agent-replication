from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_automate_strategy_headline import CANDIDATE_ID, SOURCE_FORMULA, price_momentum_14  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def panel(periods: int = 40) -> pd.DataFrame:
    months = pd.date_range("2000-01-31", periods=periods, freq="ME")
    step = np.arange(periods, dtype=float)
    return pd.DataFrame({
        "security_id": 1, "month": months,
        "prc": 20.0 + 0.1 * step + np.sin(step / 4.0),
    })


def test_m069_recipe_selects_first_table3_alpha_and_pins_audit():
    recipe = json.loads((ROOT / "paper_runs/us_jkp_headline/M069_strategy_finding/recipe.json").read_text())
    assert recipe["candidate_id"] == CANDIDATE_ID
    assert recipe["source_seed_index"] == 1
    assert recipe["source_formula"] == SOURCE_FORMULA
    assert recipe["source_signed_ic"] == 0.020881912
    assert recipe["source_direction"].startswith("positive")
    assert recipe["preclassified_scope"] == "completed_partial_if_full_common_path_succeeds"
    audit = recipe["paper_audit"]
    assert sha256(ROOT / audit["manifest_path"]) == audit["manifest_sha256"]
    assert sha256(ROOT / audit["table_3_conformance_path"]) == audit["table_3_conformance_sha256"]


def test_m069_score_is_literal_fourteen_bar_price_difference():
    data = panel()
    actual = price_momentum_14(data)
    expected = data.prc.abs() - data.prc.abs().shift(14)
    np.testing.assert_allclose(actual.score, expected, equal_nan=True, rtol=0, atol=0)


def test_m069_future_prices_do_not_change_prior_scores():
    data = panel()
    cutoff = pd.Timestamp("2002-06-30")
    altered = data.copy()
    altered.loc[altered.month > cutoff, "prc"] *= 8.0
    baseline = price_momentum_14(data)
    counterfactual = price_momentum_14(altered)
    through_cutoff = baseline.month <= cutoff
    np.testing.assert_allclose(
        baseline.loc[through_cutoff, "score"], counterfactual.loc[through_cutoff, "score"],
        equal_nan=True, rtol=0, atol=0,
    )
