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

from run_alphamemo_headline import (  # noqa: E402
    CANDIDATE_ID,
    EPS,
    SOURCE_FORMULA,
    alphamemo_sspm_000,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def panel(periods: int = 120, securities: int = 4) -> pd.DataFrame:
    months = pd.date_range("2000-01-31", periods=periods, freq="ME")
    rows = []
    for security in range(securities):
        step = np.arange(periods, dtype=float)
        rows.append(
            pd.DataFrame(
                {
                    "security_id": security,
                    "month": months,
                    "prc": 20.0 + 0.08 * step + np.sin(step / (4.0 + security)),
                    "tvol": 1000.0 + (security + 1) * step + 30.0 * np.cos(step / 7.0 + security),
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def test_m059_recipe_selects_first_printed_factor_and_pins_audit():
    recipe = json.loads(
        (ROOT / "paper_runs/us_jkp_headline/M059_alphamemo/recipe.json").read_text()
    )
    assert recipe["candidate_id"] == CANDIDATE_ID == "alphamemo_sspm_000"
    assert recipe["source_factor_id"] == "SSPM_000"
    assert recipe["source_formula"] == SOURCE_FORMULA
    assert "first listed factor" in recipe["component_selection_reason"]
    assert recipe["preclassified_scope"] == "completed_partial_if_full_common_path_succeeds"
    audit = recipe["paper_audit"]
    assert sha256(ROOT / audit["manifest_path"]) == audit["manifest_sha256"]
    assert sha256(ROOT / audit["representative_formula_audit_path"]) == audit[
        "representative_formula_audit_sha256"
    ]


def test_m059_score_matches_independent_operator_construction():
    data = panel()
    actual = alphamemo_sspm_000(data)
    work = data.sort_values(["security_id", "month"], kind="mergesort").copy()
    work["close"] = work.prc.abs()
    log_volume = np.log(np.abs(work.tvol + 1.0) + EPS)
    delayed_close = work.groupby("security_id", sort=False).close.shift(5)
    delta_volume = log_volume - log_volume.groupby(work.security_id, sort=False).shift(5)
    gated = delta_volume.where(work.close > delayed_close, 0.0)
    accumulated = gated.groupby(work.security_id, sort=False).transform(
        lambda x: x.rolling(10, min_periods=1).sum()
    )
    scale = accumulated.groupby(work.security_id, sort=False).transform(
        lambda x: x.rolling(60, min_periods=1).std(ddof=0)
    )
    normalized = accumulated / (scale + EPS)
    minimum = normalized.groupby(work.security_id, sort=False).transform(
        lambda x: x.rolling(20, min_periods=1).min()
    )
    expected = minimum.groupby(work.month, sort=False).rank(method="average", pct=True)
    np.testing.assert_allclose(actual.score, expected, equal_nan=True, rtol=0, atol=1e-12)


def test_m059_future_inputs_do_not_change_prior_scores():
    data = panel()
    cutoff = pd.Timestamp("2008-04-30")
    altered = data.copy()
    future = altered.month > cutoff
    altered.loc[future, "prc"] *= 7.0
    altered.loc[future, "tvol"] *= 11.0
    baseline = alphamemo_sspm_000(data)
    counterfactual = alphamemo_sspm_000(altered)
    through_cutoff = baseline.month <= cutoff
    np.testing.assert_allclose(
        baseline.loc[through_cutoff, "score"],
        counterfactual.loc[through_cutoff, "score"],
        equal_nan=True,
        rtol=0,
        atol=0,
    )
