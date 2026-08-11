from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from analyze_fidelity_formula_components import multiplicity_description  # noqa: E402
from run_fidelity_formula_components import (  # noqa: E402
    FORMULAS,
    INPUT_COLUMNS,
    apply_efs_cross_sectional_roots,
    portfolio_targets,
    rolling_corr,
    scores,
    top_path,
)


def monthly_panel() -> pd.DataFrame:
    months = pd.date_range("2000-01-31", periods=150, freq="ME")
    panels = []
    for permno, phase in ((1, 0.0), (2, 0.7)):
        step = np.arange(len(months), dtype=float)
        close = 20.0 + 0.04 * step + np.sin(step / 7.0 + phase)
        panels.append(
            pd.DataFrame(
                {
                    "permno": permno,
                    "month": months,
                    "ret": 0.01 + 0.02 * np.sin(step / 5.0 + phase),
                    "prc": close,
                    "prc_high": close + 1.0 + 0.1 * np.cos(step / 4.0),
                    "prc_low": close - 1.0 - 0.1 * np.sin(step / 6.0),
                    "tvol": 1000.0 + 3.0 * step + 20.0 * np.cos(step / 8.0 + phase),
                }
            )
        )
    return pd.concat(panels, ignore_index=True)


def test_formula_registry_and_multiplicity_are_dynamic() -> None:
    assert len(FORMULAS) == 12
    assert {"prc_high", "prc_low"}.issubset(INPUT_COLUMNS)
    assert multiplicity_description(len(FORMULAS)) == (
        "Holm across 12 formula components within each benchmark; not across benchmark specifications"
    )


def test_portfolio_targets_preserve_source_specific_rules() -> None:
    frame = pd.DataFrame({"permno": range(10), "quantevolver_score": range(10)})
    _, weights, rule, n_long, n_short = portfolio_targets(frame, "quantevolver_score", top_m=3)
    assert rule == "source_top_bottom_quintile_equal_weight"
    assert (n_long, n_short) == (2, 2)
    assert weights == {9: 0.5, 8: 0.5, 0: -0.5, 1: -0.5}

    tied = pd.DataFrame({"permno": [3, 1, 2], "efs_score": [1.0, 1.0, 0.0]})
    _, weights, rule, n_long, n_short = portfolio_targets(tied, "efs_score", top_m=2)
    assert rule == "researcher_top_m_equal_weight"
    assert (n_long, n_short) == (2, 0)
    assert weights == {1: 0.5, 3: 0.5}

    qa = pd.DataFrame(
        {
            "permno": [1, 2, 3],
            "quantagent_atr14_breakout_literal": [0.0, 2.0, 1.0],
        }
    )
    selected, weights, rule, n_long, n_short = portfolio_targets(qa, "quantagent_atr14_breakout_literal", top_m=10)
    assert rule == "researcher_positive_top_m_equal_weight"
    assert (n_long, n_short) == (2, 0)
    assert selected["permno"].tolist() == [2, 3]
    assert weights == {2: 0.5, 3: 0.5}


def test_quantevolver_path_is_dollar_neutral_and_costed_on_gross_turnover() -> None:
    frame = pd.DataFrame(
        {
            "month": pd.Timestamp("2024-01-31"),
            "permno": range(10),
            "quantevolver_score": range(10),
            "ret_exc_lead1m": np.arange(10) / 100.0,
            "ret_lead1m": np.arange(10) / 100.0,
            "lead_is_consecutive": True,
        }
    )
    path, holdings, _ = top_path(frame, "quantevolver_score", top_m=10, cost_bps=10.0)
    row = path.iloc[0]
    assert row["gross_excess_return"] == pytest.approx(0.08)
    assert row["traded_notional"] == pytest.approx(2.0)
    assert row["net_excess_return"] == pytest.approx(0.078)
    assert (row["n_long"], row["n_short"]) == (2, 2)
    assert holdings["target_weight"].sum() == pytest.approx(0.0)


def test_missing_quantevolver_returns_use_same_leg_means_and_preserve_drift_state() -> None:
    rows = []
    for month in (pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-29")):
        for permno in range(10):
            rows.append(
                {
                    "month": month,
                    "permno": permno,
                    "quantevolver_score": permno,
                    "ret_exc_lead1m": permno / 100.0,
                    "ret_lead1m": permno / 100.0 + 0.001,
                    "lead_is_consecutive": True,
                }
            )
    frame = pd.DataFrame(rows)
    first_month = frame["month"] == pd.Timestamp("2024-01-31")
    frame.loc[first_month & frame["permno"].isin([0, 9]), "ret_exc_lead1m"] = np.nan
    path, holdings, diagnostics = top_path(frame, "quantevolver_score", top_m=10, cost_bps=10.0)

    assert path["n_selected"].tolist() == [4, 4]
    assert path["n_observed"].tolist() == [2, 4]
    assert path["n_imputed"].tolist() == [2, 0]
    assert path["imputed_target_weight"].tolist() == pytest.approx([1.0, 0.0])
    assert path.iloc[0]["gross_excess_return"] == pytest.approx(0.07)
    expected_turnover = 2 * abs(0.5 - 0.5 * 1.081 / 1.07) + 2 * abs(-0.5 - (-0.5 * 1.011 / 1.07))
    assert path.iloc[1]["traded_notional"] == pytest.approx(expected_turnover)
    assert path.iloc[1]["traded_notional"] < 2.0

    first_holdings = holdings[holdings["formation_month"] == pd.Timestamp("2024-01-31")]
    assert first_holdings["permno"].tolist() == [9, 8, 0, 1]
    expected_weights = [0.5, 0.5, -0.5, -0.5]
    assert first_holdings["target_weight"].tolist() == pytest.approx(expected_weights)
    assert first_holdings["realized_return_weight"].tolist() == pytest.approx(expected_weights)
    assert first_holdings["realized_return_observed"].tolist() == [False, True, False, True]
    assert first_holdings["return_was_imputed"].tolist() == [True, False, True, False]
    assert first_holdings["imputed_excess_return"].tolist() == pytest.approx([0.08, np.nan, 0.01, np.nan], nan_ok=True)
    assert first_holdings["imputed_total_return"].tolist() == pytest.approx([0.081, np.nan, 0.011, np.nan], nan_ok=True)
    assert diagnostics["n_imputed_months"] == 1
    assert diagnostics["n_imputed_holdings"] == 2
    assert diagnostics["total_imputed_target_weight"] == pytest.approx(1.0)
    assert diagnostics["n_complete_case_months"] == 1


def test_empty_required_leg_and_terminal_horizons_are_omitted() -> None:
    frame = pd.DataFrame(
        {
            "month": (
                [pd.Timestamp("2024-01-31")] * 2
                + [pd.Timestamp("2024-02-29")] * 2
                + [pd.Timestamp("2024-03-31")]
                + [pd.Timestamp("2024-04-30")]
            ),
            "permno": [1, 3, 2, 3, 3, 3],
            "efs_score": [3.0, 1.0, 3.0, 1.0, 1.0, 4.0],
            "ret_exc_lead1m": [np.nan, 0.1, 0.2, 0.1, 0.15, np.nan],
            "ret_lead1m": [0.3, 0.1, 0.2, 0.1, 0.15, np.nan],
            "lead_is_consecutive": [True, True, False, True, True, False],
        }
    )
    january = frame[frame["month"] == pd.Timestamp("2024-01-31")]
    february = frame[frame["month"] == pd.Timestamp("2024-02-29")]
    jan_selected = portfolio_targets(january, "efs_score", top_m=1)[0]
    feb_selected = portfolio_targets(february, "efs_score", top_m=1)[0]
    assert jan_selected["permno"].tolist() == [1]
    assert feb_selected["permno"].tolist() == [2]
    path, holdings, _ = top_path(frame, "efs_score", top_m=1, cost_bps=10.0)
    assert len(path) == 1
    assert path.iloc[0]["formation_month"] == pd.Timestamp("2024-03-31")
    assert path.iloc[0]["month"] == pd.Timestamp("2024-04-30")
    assert holdings["permno"].tolist() == [3]
    assert path.iloc[0]["gross_excess_return"] == pytest.approx(0.15)


def test_quantagent_holds_only_positive_signals_and_uses_cash_when_none() -> None:
    frame = pd.DataFrame(
        {
            "month": [pd.Timestamp("2024-01-31")] * 3 + [pd.Timestamp("2024-02-29")] * 3,
            "permno": [1, 2, 3, 1, 2, 3],
            "quantagent_atr14_breakout_literal": [2.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            "ret_exc_lead1m": [0.1, 0.2, -0.8, 0.0, 0.0, 0.0],
            "ret_lead1m": [0.1, 0.2, -0.8, 0.0, 0.0, 0.0],
            "lead_is_consecutive": True,
        }
    )
    path, holdings, _ = top_path(frame, "quantagent_atr14_breakout_literal", top_m=10, cost_bps=10.0)
    assert len(path) == 2
    assert holdings["permno"].tolist() == [1, 2]
    assert (holdings["score"] > 0).all()
    assert path["n_holdings"].tolist() == [2, 0]
    assert path.iloc[1]["gross_excess_return"] == 0.0
    assert path.iloc[1]["traded_notional"] > 0.0


def test_quantevolver_return_sharpe_matches_released_epsilon_semantics() -> None:
    panel = monthly_panel()
    scored = scores(panel)
    source = panel[panel["permno"] == 1]
    close = source["prc"].abs()
    previous = close.shift(1)
    returns = (close - previous) / (previous + 1e-8)
    window = returns.iloc[-60:].to_numpy()
    std_result = np.std(window, ddof=0) + 1e-8
    expected = np.mean(window) / (abs(std_result) + 1e-8)
    actual = scored[scored["permno"] == 1]["quantevolver_return_sharpe_60"].iloc[-1]
    assert actual == pytest.approx(expected, rel=1e-12, abs=1e-12)


def test_quantevolver_correlation_uses_released_near_constant_cutoff() -> None:
    tiny = pd.DataFrame({"permno": 1, "left": [0.0, 1e-13, 2e-13], "right": [0.0, 1.0, 2.0]})
    assert rolling_corr(tiny, "left", "right", 3, source_fallback=True).iloc[-1] == 0.0
    varying = tiny.assign(left=[0.0, 1e-10, 2e-10])
    assert rolling_corr(varying, "left", "right", 3, source_fallback=True).iloc[-1] == pytest.approx(1.0)


def test_efs_root_cross_sectional_operators_are_applied() -> None:
    frame = pd.DataFrame({"month": pd.Timestamp("2024-01-31"), "permno": [1, 2, 3, 4]})
    zscore_ids = [
        "efs_regime_switched_return_volatility",
        "efs_multi_horizon_mean_volatility",
        "efs_skew_gated_breakout",
        "efs_decay_return_dispersion",
    ]
    for candidate_id in zscore_ids:
        frame[candidate_id] = [1.0, 2.0, 3.0, 4.0]
    rank_id = "efs_regime_momentum_normalized_mean"
    frame[rank_id] = [4.0, 1.0, 2.0, 3.0]
    rooted = apply_efs_cross_sectional_roots(frame)
    for candidate_id in zscore_ids:
        assert rooted[candidate_id].mean() == pytest.approx(0.0)
        assert rooted[candidate_id].std(ddof=0) == pytest.approx(1.0)
    np.testing.assert_allclose(rooted[rank_id], [1.0, -0.5, 0.0, 0.5])


def test_scores_have_no_future_row_lookahead() -> None:
    panel = monthly_panel()
    cutoff = panel["month"].drop_duplicates().iloc[129]
    altered = panel.copy()
    future = altered["month"] > cutoff
    altered.loc[future, "ret"] = -0.5
    altered.loc[future, ["prc", "prc_high", "prc_low", "tvol"]] *= 7.0
    columns = [
        "efs_regime_switched_return_volatility",
        "quantevolver_return_sharpe_60",
        "alpha_jungle_multiscale_price_volume",
        "quantagent_atr14_breakout_literal",
    ]
    baseline = apply_efs_cross_sectional_roots(scores(panel))
    counterfactual = apply_efs_cross_sectional_roots(scores(altered))
    through_cutoff = baseline["month"] <= cutoff
    np.testing.assert_allclose(
        baseline.loc[through_cutoff, columns],
        counterfactual.loc[through_cutoff, columns],
        equal_nan=True,
        rtol=1e-5,
        atol=2e-9,
    )


def test_all_formula_scores_accept_high_low_and_use_close_for_efs_prices() -> None:
    scored = scores(monthly_panel())
    np.testing.assert_allclose(scored["prices"], scored["prc"].abs())
    last = scored.groupby("permno", sort=False).tail(1)
    assert last[list(FORMULAS)].notna().all().all()
