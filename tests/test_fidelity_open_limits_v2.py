import numpy as np
import pandas as pd
from alpha_evolve.fidelity_open_limits_v2 import opening_flags, PREVIOUS_CLOSE


def test_closing_information_cannot_change_opening_eligibility():
    frame = pd.DataFrame(
        {
            "$open": [100.0, 110.0, 90.0],
            PREVIOUS_CLOSE: [100.0, 100.0, 100.0],
            "$close": [90.0, 110.0, 90.0],
            "$change": [-0.1, 0.1, -0.1],
        }
    )
    buy, sell = opening_flags(frame, 0.095)
    assert buy.tolist() == [False, True, False] and sell.tolist() == [False, False, True]
    changed = frame.copy()
    changed["$close"] = [150.0, 80.0, 200.0]
    changed["$change"] = [0.5, -0.2, 1.0]
    buy2, sell2 = opening_flags(changed, 0.095)
    pd.testing.assert_series_equal(buy, buy2)
    pd.testing.assert_series_equal(sell, sell2)


def test_missing_or_nonpositive_opening_inputs_block_both_sides():
    frame = pd.DataFrame({"$open": [np.nan, 0.0, 100.0, 100.0], PREVIOUS_CLOSE: [100.0, 100.0, np.nan, 0.0]})
    buy, sell = opening_flags(frame, 0.095)
    assert buy.all() and sell.all()
