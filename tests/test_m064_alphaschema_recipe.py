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

from run_alphaschema_headline import (  # noqa: E402
    CANDIDATE_ID,
    SOURCE_PERIOD,
    alphaschema_example_factor,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def panel(periods: int = 90, securities: int = 5) -> pd.DataFrame:
    months = pd.date_range("2000-01-31", periods=periods, freq="ME")
    rows = []
    for security in range(securities):
        step = np.arange(periods, dtype=float)
        rows.append(pd.DataFrame({
            "security_id": security,
            "month": months,
            "prc": 20.0 + 0.05 * step + np.sin(step / (4.0 + security)),
            "tvol": 1000.0 + (security + 2) * step + 40.0 * np.cos(step / 6.0 + security),
        }))
    return pd.concat(rows, ignore_index=True)


def reference_listing(data: pd.DataFrame, period: int) -> pd.DataFrame:
    close = data.pivot(index="month", columns="security_id", values="prc").abs()
    volume = data.pivot(index="month", columns="security_id", values="tvol").fillna(0.0)
    pct_chg = close.pct_change(fill_method=None).fillna(0.0)
    vol_chg = volume.pct_change(fill_method=None).fillna(0.0)
    synergy = pct_chg * vol_chg
    event_z = synergy.sub(synergy.mean(axis=1), axis=0).div(
        synergy.std(axis=1).replace(0.0, 1.0), axis=0
    ).fillna(0.0)
    sma = close.rolling(period, min_periods=1).mean()
    distance = ((close - sma).abs() / sma.replace(0.0, np.nan)).fillna(0.0)
    context_z = distance.sub(distance.mean(axis=1), axis=0).div(
        distance.std(axis=1).replace(0.0, 1.0), axis=0
    ).fillna(0.0)
    combined = event_z + 0.5 * context_z
    cooled = combined / (1.0 + combined.ewm(span=period, adjust=False).mean().abs() * 0.3)
    direction = np.sign(synergy).replace(0.0, 0.01)
    return (cooled.abs() * direction).ewm(span=period, adjust=False).mean().fillna(0.0).clip(-5.0, 5.0)


def test_m064_recipe_selects_complete_example_and_pins_audit():
    recipe = json.loads((ROOT / "paper_runs/us_jkp_headline/M064_alphaschema/recipe.json").read_text())
    assert recipe["candidate_id"] == CANDIDATE_ID
    assert recipe["source_period"] == SOURCE_PERIOD == 20
    assert recipe["source_direction"].startswith("positive")
    assert "only source-selected executable factor" in recipe["component_selection_reason"]
    assert recipe["preclassified_scope"] == "completed_partial_if_full_common_path_succeeds"
    audit = recipe["paper_audit"]
    assert sha256(ROOT / audit["manifest_path"]) == audit["manifest_sha256"]


def test_m064_long_adapter_matches_complete_matrix_listing():
    data = panel()
    actual = alphaschema_example_factor(data).pivot(index="month", columns="security_id", values="score")
    expected = reference_listing(data, SOURCE_PERIOD)
    np.testing.assert_allclose(actual, expected, equal_nan=True, rtol=0, atol=1e-14)


def test_m064_future_inputs_do_not_change_prior_scores():
    data = panel()
    cutoff = pd.Timestamp("2005-12-31")
    altered = data.copy()
    future = altered.month > cutoff
    altered.loc[future, "prc"] *= 6.0
    altered.loc[future, "tvol"] *= 9.0
    baseline = alphaschema_example_factor(data)
    counterfactual = alphaschema_example_factor(altered)
    through_cutoff = baseline.month <= cutoff
    np.testing.assert_allclose(
        baseline.loc[through_cutoff, "score"], counterfactual.loc[through_cutoff, "score"],
        equal_nan=True, rtol=0, atol=0,
    )
