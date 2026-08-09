from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_usa_missing_return_sensitivity import apply_position_adverse_unit_move


def test_position_adverse_policy_uses_frozen_gross_missing_weight() -> None:
    monthly = pd.DataFrame(
        {
            "gross_return": [0.03, -0.01, 0.02],
            "gross_exposure": [2.0, 1.0, 2.0],
            "missing_excess_return_gross_weight": [0.10, 0.25, np.nan],
        }
    )
    result = apply_position_adverse_unit_move(monthly)
    np.testing.assert_allclose(
        result["missing_return_adverse_contribution"],
        [-0.20, -0.25, 0.0],
    )
    np.testing.assert_allclose(result["gross_return"], [-0.17, -0.26, 0.02])
    np.testing.assert_allclose(monthly["gross_return"], [0.03, -0.01, 0.02])
