from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_us_jkp_cross_paper_summary.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("cross_paper_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_holm_uses_declared_family_size_and_step_down_monotonicity():
    builder = load_builder()
    rows = [
        {"milestone_id": "M001", "title": "a", "jkp_excess_p_two_sided": 0.0001},
        {"milestone_id": "M002", "title": "b", "jkp_excess_p_two_sided": 0.001},
        {"milestone_id": "M003", "title": "c", "jkp_excess_p_two_sided": 0.2},
    ]
    result = builder.holm_rows(rows, 69)
    assert [row["holm_multiplier"] for row in result] == [69, 68, 67]
    assert result[0]["holm_adjusted_p"] == pytest.approx(0.0069)
    assert result[1]["holm_adjusted_p"] == pytest.approx(0.068)
    assert result[2]["holm_adjusted_p"] == 1.0
    assert [row["holm_reject_5pct"] for row in result] == [True, False, False]
