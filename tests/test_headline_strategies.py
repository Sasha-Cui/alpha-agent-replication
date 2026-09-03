from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_strategies import gpt_signal_evc, gpt_signal_evc_trading_score


def test_evc_preserves_published_reciprocals_and_signs():
    values = gpt_signal_evc(pd.Series([0.1, -0.1]), pd.Series([5.0, 5.0]), pd.Series([10.0, 10.0]))
    assert values.tolist() == pytest.approx([0.2, -0.2])
    assert gpt_signal_evc_trading_score(values).tolist() == pytest.approx([-0.2, 0.2])


@pytest.mark.parametrize("bad", [0.0, np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("column", [0, 1, 2])
def test_evc_does_not_fill_or_regularize_undefined_inputs(bad, column):
    inputs = [pd.Series([0.1]), pd.Series([5.0]), pd.Series([10.0])]
    inputs[column] = pd.Series([bad])
    assert gpt_signal_evc(*inputs).isna().all()


def test_evc_rejects_misaligned_inputs():
    with pytest.raises(ValueError, match="aligned"):
        gpt_signal_evc(pd.Series([0.1], index=[1]), pd.Series([5.0], index=[2]), pd.Series([10.0], index=[1]))


def test_future_row_changes_cannot_change_past_evc_scores():
    index = pd.date_range("2020-01-31", periods=3, freq=pd.offsets.MonthEnd())
    roa = pd.Series([0.1, 0.2, 0.3], index=index)
    ev = pd.Series([5.0, 6.0, 7.0], index=index)
    pcf = pd.Series([10.0, 11.0, 12.0], index=index)
    original = gpt_signal_evc(roa, ev, pcf)
    roa.iloc[-1], ev.iloc[-1], pcf.iloc[-1] = 999.0, -999.0, 0.0
    pd.testing.assert_series_equal(original.iloc[:-1], gpt_signal_evc(roa, ev, pcf).iloc[:-1])
