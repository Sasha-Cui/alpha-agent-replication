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

from run_alphagpt_headline import CANDIDATE_ID, SOURCE_FORMULA, rolling_price_volume_correlation  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def panel(periods: int = 45, securities: int = 3) -> pd.DataFrame:
    months = pd.date_range("2000-01-31", periods=periods, freq="ME")
    rows = []
    for security in range(securities):
        step = np.arange(periods, dtype=float)
        rows.append(pd.DataFrame({
            "security_id": security, "month": months,
            "prc": 20.0 + 0.08 * step + np.sin(step / (4.0 + security)),
            "tvol": 1000.0 + (security + 1) * step + 20.0 * np.cos(step / 6.0 + security),
        }))
    return pd.concat(rows, ignore_index=True)


def test_m068_recipe_selects_first_valid_formula_and_pins_audit():
    recipe = json.loads((ROOT / "paper_runs/us_jkp_headline/M068_alphagpt/recipe.json").read_text())
    assert recipe["candidate_id"] == CANDIDATE_ID
    assert recipe["source_formula_id"] == "AGPT-FORM-02"
    assert recipe["source_formula"] == SOURCE_FORMULA
    assert "first source-ordered arity-valid" in recipe["component_selection_reason"]
    assert recipe["preclassified_scope"] == "completed_partial_if_full_common_path_succeeds"
    audit = recipe["paper_audit"]
    assert sha256(ROOT / audit["manifest_path"]) == audit["manifest_sha256"]
    assert sha256(ROOT / audit["formula_conformance_path"]) == audit["formula_conformance_sha256"]


def test_m068_rolling_correlation_matches_conventional_stub():
    data = panel()
    actual = rolling_price_volume_correlation(data)
    for security, source in data.groupby("security_id", sort=False):
        expected = source.prc.abs().rolling(20).corr(source.tvol)
        observed = actual.loc[actual.security_id.eq(security), "correlation"]
        np.testing.assert_allclose(observed, expected, equal_nan=True, rtol=0, atol=1e-14)


def test_m068_future_inputs_do_not_change_prior_scores():
    data = panel()
    cutoff = pd.Timestamp("2002-12-31")
    altered = data.copy()
    future = altered.month > cutoff
    altered.loc[future, "prc"] *= 7.0
    altered.loc[future, "tvol"] *= 11.0
    baseline = rolling_price_volume_correlation(data)
    counterfactual = rolling_price_volume_correlation(altered)
    through_cutoff = baseline.month <= cutoff
    np.testing.assert_allclose(
        baseline.loc[through_cutoff, "correlation"], counterfactual.loc[through_cutoff, "correlation"],
        equal_nan=True, rtol=0, atol=0,
    )
