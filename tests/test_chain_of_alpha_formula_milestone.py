from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "chain_formula", ROOT / "scripts/run_chain_of_alpha_formula_milestone.py"
)
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def test_average_tie_percentile_rank_matches_declared_semantics():
    assert runner.percentile_rank_last(np.array([1.0, 3.0, 2.0, 4.0, 5.0])) == 1.0
    assert runner.percentile_rank_last(np.array([1.0, 2.0, 2.0, 4.0, 2.0])) == pytest.approx(0.6)
    assert np.isnan(runner.percentile_rank_last(np.array([1.0, 2.0, np.nan])))


def test_formula_is_close_amount_correlation_without_return_input():
    months = pd.date_range("2000-01-31", periods=12, freq=pd.offsets.MonthEnd())
    pattern = [1, 3, 2, 5, 4, 6, 3, 7, 2, 8, 1, 9]
    rows = []
    for security in [1, 2]:
        for number, month in enumerate(months):
            rows.append({
                "security_id": security,
                "month": month,
                "prc": pattern[number] + 10 * security,
                "dolvol": 100 * security + 2 * pattern[number],
            })
    frame = pd.DataFrame(rows)
    score = runner.formula_score(frame)
    assert score.notna().sum() == 8
    np.testing.assert_allclose(score.dropna(), 1.0, atol=1e-12, rtol=0)
    perturbed = frame.assign(ret_exc_lead1m=np.arange(len(frame)))
    pd.testing.assert_series_equal(score, runner.formula_score(perturbed))
