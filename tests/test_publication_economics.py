import numpy as np
import pytest
from alpha_evolve.publication_economics import cash_account, categorical_targets
from alpha_evolve.economic_fidelity import daily_account


def test_cash_is_not_a_second_fee_bearing_trade():
    values, turnover, _ = cash_account(np.array([[1.0], [0.0]]), np.zeros((2, 1)), 100)
    assert np.allclose(values, [1 / 1.01 - 1, -0.01], atol=1e-14)
    assert np.allclose(turnover, [1 / 1.01, 1.0], atol=1e-14)


def test_next_close_cannot_earn_signal_day_or_execution_day_return():
    weights = categorical_targets(["BUY", "HOLD", "SELL", "HOLD"])
    values, _, _ = cash_account(weights, np.array([[0.5], [0.5], [0.1], [0.2]]), 0)
    assert np.allclose(values, [0, 0, 0.1, 0.2], atol=1e-14)


def test_generic_cash_account_matches_frozen_fully_invested_efs():
    rng = np.random.default_rng(31)
    weights = rng.dirichlet(np.ones(5), size=70)
    returns = rng.normal(0, 0.02, (70, 5))
    for cost in [0, 10, 50]:
        original = daily_account(weights, returns, cost)
        general = cash_account(weights, returns, cost)
        for left, right in zip(original, general):
            assert np.allclose(left, right, atol=3e-13, rtol=0)


def test_future_prices_do_not_change_earlier_account_values():
    weights = categorical_targets(["BUY", "HOLD", "HOLD", "HOLD"])
    returns = np.array([[0], [0.1], [0.2], [0.3]])
    first = cash_account(weights, returns, 10)[0]
    returns[3] = -0.9
    second = cash_account(weights, returns, 10)[0]
    assert np.array_equal(first[:3], second[:3])
    with pytest.raises(ValueError):
        cash_account([[1.2]], [[0]], 10)


def test_monthly_hold_does_not_accidentally_rebalance_daily():
    weights = np.array([[0.5, 0.5], [0.5, 0.5], [0.5, 0.5]])
    returns = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    values, turn, _ = cash_account(weights, returns, 0, rebalance_mask=[True, False, False])
    assert np.allclose(values, [0, 0.5, 1 / 3], atol=1e-14)
    assert np.allclose(turn, [1, 0, 0])
    assert np.prod(1 + values) == pytest.approx(2.0)
