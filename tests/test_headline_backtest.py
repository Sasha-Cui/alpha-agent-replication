from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_evolve.headline_backtest import (
    build_factor_panel, build_strategy_path, evc_jkp_score,
    formation_universe, return_statistics,
)


SETTINGS = {"formation_start": "2020-01-31", "formation_end": "2020-03-31",
            "top_n_by_formation_market_equity": 12, "quantile": 0.25, "min_side": 1}


def panel():
    dates = pd.date_range("2020-01-31", periods=4, freq=pd.offsets.MonthEnd())
    return pd.DataFrame([{"id": security, "permno": security, "eom": month,
                          "me": 1.0, "ret": 0.01, "ret_exc_lead1m": 0.01,
                          "signal": float(security)}
                         for month in dates for security in range(12)])


def test_formation_membership_does_not_depend_on_future_return_availability():
    raw = panel()
    original = formation_universe(raw, "2020-01-31", "2020-03-31", 10)
    raw.loc[raw.id < 5, "ret_exc_lead1m"] = np.nan
    raw.loc[raw.eom == pd.Timestamp("2020-04-30"), "ret"] = np.nan
    changed = formation_universe(raw, "2020-01-31", "2020-03-31", 10)
    pd.testing.assert_frame_equal(original[["security_id", "month", "weight"]],
                                  changed[["security_id", "month", "weight"]])


def test_nonconsecutive_observation_is_not_a_one_month_total_return():
    raw = panel()
    raw = raw.loc[~((raw.id == 0) & (raw.eom == pd.Timestamp("2020-02-29")))]
    formed = formation_universe(raw, "2020-01-31", "2020-03-31", 12)
    value = formed.loc[(formed.security_id == 0) & (formed.month == pd.Timestamp("2020-01-31")), "ret_total_lead1m"].iloc[0]
    assert np.isnan(value)
    assert formed.loc[(formed.security_id == 1) & (formed.month == pd.Timestamp("2020-01-31")), "ret_total_lead1m"].iloc[0] == 0.01


def test_duplicate_security_month_fails_closed():
    raw = panel()
    with pytest.raises(ValueError, match="duplicate"):
        formation_universe(pd.concat([raw, raw.iloc[[0]]]), "2020-01-31", "2020-03-31", 12)


def test_jkp_evc_mapping_keeps_source_direction_and_undefined_ratio_boundaries():
    data = pd.DataFrame({"ni_at": [0.1, -0.1, 0.1, 0.0],
                         "ebitda_mev": [0.2, 0.2, 0.0, 0.2],
                         "ocf_me": [0.1, 0.1, 0.1, 0.1]})
    score = evc_jkp_score(data)
    assert score.iloc[:2].tolist() == pytest.approx([-0.2, 0.2])
    assert score.iloc[2:].isna().all()
    data["ret_exc_lead1m"] = [999.0] * len(data)
    pd.testing.assert_series_equal(score, evc_jkp_score(data))


def test_monthly_path_preserves_missing_security_weight_and_cost_notional():
    raw = panel()
    raw.loc[(raw.id == 11) & (raw.eom == pd.Timestamp("2020-01-31")), "ret_exc_lead1m"] = np.nan
    formed = formation_universe(raw, "2020-01-31", "2020-03-31", 12)
    primary, weights = build_strategy_path(formed, formed.signal, SETTINGS)
    adverse, adverse_weights = build_strategy_path(formed, formed.signal, SETTINGS, "adverse_100")
    pd.testing.assert_frame_equal(weights, adverse_weights)
    assert primary.iloc[0].traded_notional == pytest.approx(2.0)
    assert primary.iloc[0].gross_return - adverse.iloc[0].gross_return == pytest.approx(1 / 3)
    assert primary.iloc[0].missing_forward_return_gross_weight == pytest.approx(1 / 6)
    assert primary.month.tolist() == list(pd.date_range("2020-02-29", periods=3, freq=pd.offsets.MonthEnd()))
    for _, group in weights.groupby("formation_month"):
        assert group.weight.abs().sum() == pytest.approx(2.0)
        assert group.weight.sum() == pytest.approx(0.0)


def test_factor_builder_uses_realization_calendar_and_formation_eligible_market():
    formed = formation_universe(panel(), "2020-01-31", "2020-03-31", 12)
    factors, coverage = build_factor_panel(formed, ["signal"], SETTINGS)
    assert len(factors) == len(coverage) == 3
    assert factors.capm_top1000_mkt.tolist() == pytest.approx([0.01] * 3)
    assert factors["char__signal"].tolist() == pytest.approx([0.0] * 3)
    assert (factors.month == factors.formation_month + pd.offsets.MonthEnd(1)).all()


def test_return_statistics_include_initial_capital_in_drawdown():
    stats = return_statistics(np.array([-0.1, 0.0, 0.0]))
    assert stats["maximum_drawdown"] == pytest.approx(-0.1)
    assert stats["cumulative_return"] == pytest.approx(-0.1)
    with pytest.raises(ValueError, match="NAV"):
        return_statistics(np.array([0.1, -1.0]))
