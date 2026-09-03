from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "alphaagent_factor_pool", ROOT / "scripts/run_alphaagent_factor_pool_milestone.py"
)
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def test_ridge_uses_only_prior_formation_outcomes():
    months = pd.date_range("2000-01-31", periods=26, freq=pd.offsets.MonthEnd())
    rows = []
    for number, month in enumerate(months):
        for security in range(3):
            row = {"month": month, "lead_is_consecutive": True,
                   "ret_exc_lead1m": 0.01 * security + number / 10_000}
            row.update({name: (security - 1) / 2 for name in runner.FEATURES})
            rows.append(row)
    frame = pd.DataFrame(rows)
    base, coefficients = runner.chronological_ridge_scores(frame, minimum_months=24)
    changed = frame.copy()
    changed.loc[changed.month.eq(months[-1]), "ret_exc_lead1m"] = 1000
    perturbed, _ = runner.chronological_ridge_scores(changed, minimum_months=24)
    assert base.loc[frame.month.eq(months[-1])].notna().all()
    np.testing.assert_allclose(base.loc[frame.month.eq(months[-1])],
                               perturbed.loc[frame.month.eq(months[-1])])
    assert base.loc[frame.month.isin(months[:24])].isna().all()
    assert len(coefficients) == 2


def test_source_feature_ranks_are_bounded_and_open_proxy_is_lagged():
    months = pd.date_range("2000-01-31", periods=100, freq=pd.offsets.MonthEnd())
    rows = []
    for security in [1, 2]:
        for number, month in enumerate(months):
            rows.append({"id": security, "month": month, "prc": 10 + security + number / 10,
                         "prc_high": 11 + security + number / 10, "prc_low": 9 + security + number / 10,
                         "tvol": 1000 + 10 * security + number})
    raw = runner.time_series_ingredients(pd.DataFrame(rows))
    assert raw.loc[raw.id.eq(1), "open"].iloc[1] == raw.loc[raw.id.eq(1), "close"].iloc[0]
    ranked = runner.source_features(raw)
    finite = ranked[runner.FEATURES].to_numpy(float)
    finite = finite[np.isfinite(finite)]
    assert finite.size > 0
    assert finite.min() >= -1 and finite.max() <= 1
