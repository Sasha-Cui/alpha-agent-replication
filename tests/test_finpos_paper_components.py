from __future__ import annotations

import math

import pytest

from alpha_evolve import finpos_paper_components as component


def test_printed_return_and_position_equations() -> None:
    assert component.single_step_log_return(1, 100, 110) == pytest.approx(math.log(1.1))
    assert component.single_step_log_return(-1, 100, 110) == pytest.approx(-math.log(1.1))
    assert component.position_log_return(2, 100, 110) == pytest.approx(2 * math.log(1.1))
    assert component.update_position(5, -1, 2) == 3


def test_multiscale_score_and_literal_reward_preserve_paper_semantics() -> None:
    prices = [100.0 + index for index in range(31)]
    assert component.multi_timescale_score(prices, 0) == 38
    assert component.literal_reward(2, 2, 3) == -9
    assert component.literal_reward(3, 2, 3) == 6
    # Selling one unit while remaining long earns positive reward in a rising
    # market under the printed total-position formula.  Preserve this defect.
    new_position = component.update_position(3, -1, 1)
    assert component.literal_reward(3, new_position, 3) == 6


def test_printed_metrics_execute_for_explicit_inputs() -> None:
    assert component.sharpe_ratio(0.02, 0.005, 0.01) == pytest.approx(1.5)
    assert component.maximum_drawdown_future_trough([100, 120, 90, 110]) == 0.25
    pnl = [-4.0, -3.0, -2.0, -1.0] + [float(index) for index in range(16)]
    assert component.empirical_var_cvar(pnl, 0.05) == (-4.0, -4.0)
    assert component.empirical_var_cvar(pnl, 0.95) == (14.0, 5.0)
    assert component.calmar_ratio(0.2, 0.1) == 2


def test_underspecified_conversions_fail_closed() -> None:
    with pytest.raises(component.UnderspecifiedPaperMechanic, match="CR%"):
        component.cumulative_log_return_to_reported_percent(0.1)
    with pytest.raises(component.UnderspecifiedPaperMechanic, match="integer maxcvar"):
        component.cvar_to_maximum_order_quantity(-0.02)


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: component.single_step_log_return(2, 100, 101), "action"),
        (lambda: component.position_log_return(1, 0, 101), "positive"),
        (lambda: component.update_position(1, 1, -1), "negative"),
        (lambda: component.multi_timescale_score([100.0] * 30, 0), r"t\+30"),
        (lambda: component.sharpe_ratio(1, 0, 0), "positive"),
        (lambda: component.empirical_var_cvar([], 0.05), "at least one"),
    ],
)
def test_invalid_inputs_are_rejected(call, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        call()
