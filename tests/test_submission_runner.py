from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_submission_evidence as runner


def test_country_pool_requires_identical_complete_market_set() -> None:
    months = pd.date_range("2020-01-31", periods=3, freq="ME")
    candidate_rows = []
    factor_rows = []
    for market_index, market in enumerate(["AAA", "BBB"]):
        for month_index, month in enumerate(months):
            for candidate_index, candidate in enumerate(["c1", "c2"]):
                candidate_rows.append(
                    {
                        "market": market,
                        "month": month,
                        "candidate_id": candidate,
                        "gross_return": 0.01 * (1 + market_index + candidate_index),
                        "traded_notional": 0.5,
                        "missing_excess_return_gross_weight": 0.0,
                        "missing_total_return_gross_weight": 0.0,
                        "n_long": 20,
                        "n_short": 20,
                        "max_abs_weight": 0.05,
                        "weight_hhi": 0.1,
                        "gross_exposure": 2.0,
                    }
                )
            factor_row = {
                "market": market,
                "month": month,
                "n_stocks": 100,
                "market_cap_sum": 1_000.0,
            }
            factor_row.update({column: 0.01 for column in runner.FACTOR_COLS})
            if market == "BBB" and month_index == 1:
                factor_row[runner.FACTOR_COLS[0]] = np.nan
            factor_rows.append(factor_row)

    candidates, factors = runner.pool_country_sleeves(
        pd.DataFrame(candidate_rows), pd.DataFrame(factor_rows)
    )
    assert set(candidates["month"]) == {months[0], months[2]}
    assert set(factors["month"]) == {months[0], months[2]}
    assert (candidates["n_countries"] == 2).all()
    assert (factors["n_countries"] == 2).all()


def test_bankrupt_candidate_is_retained_but_cannot_set_common_calendar() -> None:
    months = pd.date_range("2020-01-31", periods=3, freq="ME")
    candidate_rows = []
    factor_rows = []
    for market in ["AAA", "BBB"]:
        for month_index, month in enumerate(months):
            for candidate in ["survivor", "bankrupt"]:
                failed = candidate == "bankrupt" and market == "AAA" and month_index == 1
                candidate_rows.append(
                    {
                        "market": market,
                        "month": month,
                        "candidate_id": candidate,
                        "gross_return": np.nan if candidate == "bankrupt" and market == "AAA" else 0.01,
                        "traded_notional": np.nan if candidate == "bankrupt" and market == "AAA" else 0.5,
                        "path_failure_event": failed,
                        "missing_excess_return_gross_weight": 0.0,
                        "missing_total_return_gross_weight": 0.0,
                        "n_long": 20,
                        "n_short": 20,
                        "max_abs_weight": 0.05,
                        "weight_hhi": 0.1,
                        "gross_exposure": 2.0,
                    }
                )
            factor_row = {
                "market": market,
                "month": month,
                "n_stocks": 100,
                "market_cap_sum": 1_000.0,
            }
            factor_row.update({column: 0.01 for column in runner.FACTOR_COLS})
            factor_rows.append(factor_row)
    candidates, factors = runner.pool_country_sleeves(
        pd.DataFrame(candidate_rows), pd.DataFrame(factor_rows)
    )
    survivor = candidates[candidates["candidate_id"] == "survivor"]
    failed = candidates[candidates["candidate_id"] == "bankrupt"]
    assert len(survivor) == len(months)
    assert (survivor["n_countries"] == 2).all()
    assert failed["path_failed"].all()
    assert failed["gross_return"].isna().all()


def test_break_even_cost_uses_alpha_cost_slope() -> None:
    pooled = pd.DataFrame(
        {
            "candidate_id": ["c1", "c1"],
            "gross_return": [0.01, 0.01],
            "traded_notional": [1.0, 1.0],
            "missing_excess_return_gross_weight": [0.0, 0.0],
            "missing_total_return_gross_weight": [0.0, 0.0],
            "n_countries": [6, 6],
            "n_long": [20, 20],
            "n_short": [20, 20],
            "max_abs_weight": [0.05, 0.05],
            "weight_hhi": [0.1, 0.1],
        }
    )
    costs = pd.DataFrame(
        {
            "candidate_id": ["c1"] * 5,
            "cost_bps_one_way": [0, 5, 10, 25, 50],
            "alpha_annualized": [0.12, 0.11, 0.10, 0.07, 0.02],
            "status": ["ok"] * 5,
        }
    )
    summary = runner.turnover_summary(pooled, costs).iloc[0]
    assert np.isclose(summary["alpha_drag_annualized_per_cost_bp"], 0.002)
    assert np.isclose(summary["alpha_break_even_cost_bps"], 60.0)


def test_failed_candidate_stays_in_multiplicity_denominator() -> None:
    rng = np.random.default_rng(44)
    months = pd.date_range("2010-01-31", periods=36, freq="ME")
    candidate_rows = []
    for month, value in zip(months, rng.normal(0.001, 0.02, len(months))):
        candidate_rows.extend(
            [
                {
                    "month": month,
                    "candidate_id": "ok_candidate",
                    "gross_return": value,
                    "traded_notional": 0.5,
                },
                {
                    "month": month,
                    "candidate_id": "failed_candidate",
                    "gross_return": np.nan,
                    "traded_notional": np.nan,
                },
            ]
        )
    factors = pd.DataFrame({"month": months})
    for index, column in enumerate(runner.FACTOR_COLS):
        factors[column] = rng.normal(0.0, 0.01 + index * 0.001, len(months))
    metadata = pd.DataFrame(
        {
            "candidate_id": ["ok_candidate", "failed_candidate"],
            "paper_ref": ["test", "test"],
        }
    )
    _, primary, multiplicity, _ = runner.run_pooled_analysis(
        pd.DataFrame(candidate_rows), factors, metadata, n_bootstrap=20
    )
    failed = primary.set_index("candidate_id").loc["failed_candidate"]
    adjusted = multiplicity.set_index("candidate_id").loc["failed_candidate"]
    assert failed["status"] == "failed:insufficient_return_history"
    assert np.isclose(adjusted["adjustment_input_p_value"], 1.0)
