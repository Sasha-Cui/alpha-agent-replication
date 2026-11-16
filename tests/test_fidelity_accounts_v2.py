import numpy as np
import pytest
from alpha_evolve.fidelity_accounts_v2 import binary_share_account, equal_initial_capital
from alpha_evolve.publication_economics import cash_account, categorical_targets


def test_price_jump_before_fill_is_not_earned_and_fees_are_self_financing():
    result = binary_share_account(["BUY", "HOLD", "SELL", "HOLD"], [10, 20, 30, 40], 100, 1)
    np.testing.assert_allclose(result[:, 3], [1, 1/1.01, 1.5/1.01, 2*.99/1.01])
    assert result[-1, 5] == 0
    assert result[-1, 4] == result[-1, 3]


@pytest.mark.parametrize("lag", [0, 1, 3])
@pytest.mark.parametrize("cost", [0, 10, 50])
def test_independent_units_match_generic_account(lag, cost):
    rng = np.random.default_rng(112)
    prices = 10*np.exp(np.cumsum(rng.normal(0, .04, 200)))
    actions = rng.choice(["BUY", "HOLD", "SELL"], len(prices)).tolist()
    realized = np.r_[0, prices[1:]/prices[:-1]-1][:, None]
    actual = binary_share_account(actions, prices, cost, lag)
    expected = cash_account(categorical_targets(actions, lag), realized, cost)
    for i, vector in enumerate(expected):
        np.testing.assert_allclose(actual[:, i], vector, rtol=0, atol=2e-14)


def test_equal_initial_capital_does_not_rebalance_winners():
    # Two initially equal accounts finish at 4 and 1, hence combined wealth 2.5.
    result = equal_initial_capital([[1, 0], [1, 0]])
    np.testing.assert_allclose(result, [.5, 2/3])
    assert np.prod(1+result) == 2.5


@pytest.mark.parametrize("prices", [[1, float("nan")], [1, 0], [1, -2]])
def test_missing_execution_price_fails(prices):
    with pytest.raises(ValueError):
        binary_share_account(["BUY", "HOLD"], prices)
