from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_mapping_audit.py"
SPEC = importlib.util.spec_from_file_location("build_mapping_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_holm_adjustment_is_step_down_monotone() -> None:
    adjusted = MODULE.holm_adjust(np.asarray([0.001, 0.01, 0.03, 0.8]))
    np.testing.assert_allclose(adjusted, [0.004, 0.03, 0.06, 0.8])


def test_source_categories_match_frozen_discovery_table() -> None:
    assert MODULE.source_category(1) == "formula_or_factor_method"
    assert MODULE.source_category(23) == "sequential_trading_or_portfolio_method"
    assert MODULE.source_category(45) == "benchmark_or_audit"
    assert MODULE.source_category(52) == "community_repository"


def test_good_faith_boundary_for_narrative_mapping() -> None:
    row = pd.Series({
        "mapping_fidelity_tier": "M0_narrative_translation",
        "strategy": "long_short_decile_value_weighted",
    })
    fields = MODULE.good_faith_fields(row)
    assert fields[0] == "exploratory_favorable_stress_test"
    assert fields[5] == "exploratory_only_no_negative_inference"
    assert "cannot count as evidence against the source" in fields[4]


def test_good_faith_boundary_for_released_expression() -> None:
    row = pd.Series({
        "mapping_fidelity_tier": "M2_released_seed_expression",
        "strategy": "long_short_decile_value_weighted",
    })
    fields = MODULE.good_faith_fields(row)
    assert fields[0] == "source_grounded_component_test"
    assert fields[5] == "eligible_for_component_level_interpretation_only"
    assert "not the trained agent" in fields[4]
