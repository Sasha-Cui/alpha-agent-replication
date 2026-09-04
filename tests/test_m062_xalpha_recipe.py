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

from run_xalpha_headline import CANDIDATE_ID, SOURCE_FUNCTION, xalpha_overshoot_pressure  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def panel(periods: int = 180, securities: int = 3) -> pd.DataFrame:
    months = pd.date_range("1990-01-31", periods=periods, freq="ME")
    rows = []
    for security in range(securities):
        step = np.arange(periods, dtype=float)
        close = 30.0 + 0.04 * step + 2.0 * np.sin(step / (5.0 + security))
        close[70 + security] *= 0.75
        rows.append(pd.DataFrame({"security_id": security, "month": months, "prc": close}))
    return pd.concat(rows, ignore_index=True)


def reference_listing(frame: pd.DataFrame) -> pd.Series:
    close = frame["close"]
    ma20 = close.rolling(20, min_periods=10).mean()
    ret = close.pct_change(fill_method=None)
    vol20 = ret.rolling(20, min_periods=10).std()
    high_vol = (vol20 > vol20.rolling(60, min_periods=30).median()).astype(float)
    threshold = (0.90 * high_vol + 0.95 * (1.0 - high_vol)) * ma20
    overshoot = (close < threshold).astype(float)
    pressure = (overshoot * ret.abs().fillna(0.0)).rolling(20, min_periods=1).sum()
    slow = pressure.ewm(span=15, adjust=False, min_periods=1).mean()
    fast = pressure.ewm(span=5, adjust=False, min_periods=1).mean()
    decayed = high_vol * fast + (1.0 - high_vol) * slow
    factor = decayed - decayed.expanding().quantile(0.75)
    factor.name = SOURCE_FUNCTION
    return factor


def test_m062_recipe_selects_main_representative_factor_and_pins_audit():
    recipe = json.loads((ROOT / "paper_runs/us_jkp_headline/M062_xalpha/recipe.json").read_text())
    assert recipe["candidate_id"] == CANDIDATE_ID
    assert recipe["source_function"] == SOURCE_FUNCTION
    assert recipe["source_direction"].startswith("positive")
    assert "main text singles out" in recipe["component_selection_reason"]
    assert recipe["preclassified_scope"] == "completed_partial_if_full_common_path_succeeds"
    audit = recipe["paper_audit"]
    assert sha256(ROOT / audit["manifest_path"]) == audit["manifest_sha256"]
    assert sha256(ROOT / audit["factor_execution_path"]) == audit["factor_execution_sha256"]


def test_m062_score_matches_verbatim_single_security_listing():
    data = panel(securities=1)
    actual = xalpha_overshoot_pressure(data)
    expected = reference_listing(data.assign(close=data.prc.abs()))
    np.testing.assert_allclose(actual.score, expected, equal_nan=True, rtol=0, atol=1e-14)


def test_m062_future_prices_do_not_change_prior_scores():
    data = panel()
    cutoff = pd.Timestamp("2002-07-31")
    altered = data.copy()
    altered.loc[altered.month > cutoff, "prc"] *= 8.0
    baseline = xalpha_overshoot_pressure(data)
    counterfactual = xalpha_overshoot_pressure(altered)
    through_cutoff = baseline.month <= cutoff
    np.testing.assert_allclose(
        baseline.loc[through_cutoff, "score"],
        counterfactual.loc[through_cutoff, "score"],
        equal_nan=True,
        rtol=0,
        atol=0,
    )
