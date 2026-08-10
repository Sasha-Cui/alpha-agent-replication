"""Tests for the authorization-gated monthly collaborator bundle."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_authorized_collaborator_bundle.py"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "build_authorized_collaborator_bundle", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_retained_ids_require_exactly_fifty_unique_candidates() -> None:
    strategy_index = pd.DataFrame(
        {"candidate_id": [f"candidate_{index:02d}" for index in range(50)]}
    )
    assert MODULE.retained_candidate_ids(strategy_index) == sorted(
        strategy_index["candidate_id"]
    )
    with pytest.raises(ValueError, match="exactly 50 unique"):
        MODULE.retained_candidate_ids(strategy_index.iloc[:-1])


def test_candidate_paths_compute_ten_bp_net_return_and_keep_flags() -> None:
    candidate_ids = [f"candidate_{index:02d}" for index in range(50)]
    source = pd.DataFrame(
        {
            "market": "USA",
            "formation_month": "2020-01-31",
            "month": "2020-02-29",
            "candidate_id": candidate_ids,
            "gross_return": np.linspace(-0.05, 0.05, 50),
            "traded_notional": 2.0,
            "analysis_eligible": True,
            "path_failure_event": False,
            "path_status": "ok",
            "failure_month": np.nan,
            "failure_total_return": np.nan,
            "missing_excess_return_gross_weight": 0.0,
            "missing_total_return_gross_weight": 0.0,
        }
    )
    result = MODULE.prepare_candidate_paths(source, candidate_ids, cost_bps=10.0)
    np.testing.assert_allclose(
        result["net_return_10bps"], result["gross_return"] - 0.002
    )
    assert result["formation_month"].unique().tolist() == ["2020-01-31"]
    assert result["realization_month"].unique().tolist() == ["2020-02-29"]
    assert result["analysis_eligible"].all()
    assert not result["path_failure_event"].any()


def test_factor_preparation_labels_both_clocks_and_freezes_order() -> None:
    primary_source = pd.DataFrame(
        {
            "market": ["USA"],
            "formation_month": ["2020-01-31"],
            "month": ["2020-02-29"],
            **{column: [0.01] for column in MODULE.PRIMARY_FACTOR_COLUMNS},
        }
    )
    primary = MODULE.prepare_primary_factors(primary_source)
    assert primary.columns.tolist() == [
        "market",
        "formation_month",
        "realization_month",
        *MODULE.PRIMARY_FACTOR_COLUMNS,
    ]

    base_characteristics = [
        column
        for column in MODULE.BASE_FACTOR_COLUMNS
        if column.startswith("char__")
    ]
    extra_characteristics = [
        f"char__synthetic_{index:03d}"
        for index in range(132 - len(base_characteristics))
    ]
    broad_source = pd.DataFrame(
        {
            "month": ["2020-01-31"],
            "capm_top1000_mkt": [0.01],
            **{
                column: [0.001]
                for column in [*base_characteristics, *extra_characteristics]
            },
            "newsfactor": [0.99],
        }
    )
    broad, factor_order = MODULE.prepare_broad_factors(broad_source)
    assert len(factor_order) == 133
    assert factor_order[: len(MODULE.BASE_FACTOR_COLUMNS)] == (
        MODULE.BASE_FACTOR_COLUMNS
    )
    assert "newsfactor" not in factor_order
    assert broad.loc[0, "formation_month"] == "2020-01-31"
    assert broad.loc[0, "realization_month"] == "2020-02-29"
