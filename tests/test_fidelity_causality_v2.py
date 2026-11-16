import pandas as pd
import pytest
from alpha_evolve.fidelity_causality_v2 import compare_prefix


def prices():
    index = pd.MultiIndex.from_product(
        [pd.date_range("2020-01-01", periods=8), ["a"]], names=["datetime", "instrument"]
    )
    return pd.Series([1, 2, 5, 3, 6, 2, 9, 4], index=index, name="factor", dtype=float)


def test_causal_rolling_values_unchanged():
    raw = prices()
    assert compare_prefix(raw.rolling(3).mean(), raw.iloc[:5].rolling(3).mean(), "2020-01-05")["status"] == "pass"


def test_future_shift_and_centered_window_fail():
    raw = prices()
    for operation in [lambda x: x.shift(-1), lambda x: x.rolling(3, center=True).mean()]:
        result = compare_prefix(operation(raw), operation(raw.iloc[:5]), "2020-01-05")
        assert result["status"] == "fail"
        assert result["nan_mask_differences"] > 0


def test_global_normalization_future_dependence_fails():
    raw = prices()
    prefix = raw.iloc[:5]
    result = compare_prefix(raw / raw.mean(), prefix / prefix.mean(), "2020-01-05")
    assert result["status"] == "fail"
    assert result["changed_values"] == 5


def test_dropped_boundary_rows_cannot_hide_future_dependency():
    raw = prices()
    assert compare_prefix(raw, raw.iloc[:4], "2020-01-05")["status"] == "fail"
    with pytest.raises(ValueError):
        compare_prefix(raw, raw.iloc[:0], "2019-12-31")


def test_vacuous_future_removal_cannot_certify_causality():
    raw = prices()
    with pytest.raises(ValueError, match="remove actual future"):
        compare_prefix(raw, raw, "2021-01-01", require_future_rows=True)
    assert compare_prefix(raw, raw, "2021-01-01")["status"] == "pass"
