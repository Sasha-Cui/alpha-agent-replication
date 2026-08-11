from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_faithful_component_replications import (  # noqa: E402
    PRIMARY_COMPONENTS,
    evaluate_released_seeds,
    faithfulness_ledger,
    released_cross_sectional_path,
)
from validate_faithful_component_replications import validation_failures  # noqa: E402


def source_reference(close: np.ndarray, volume: np.ndarray) -> dict[str, float]:
    returns = np.diff(close[-61:]) / (close[-61:-1] + 1e-8)
    std = float(np.std(returns) + 1e-8)
    sharpe = float(np.mean(returns) / (abs(std) + 1e-8))
    close120 = close[-120:]
    reversal = -float(
        (close120[-1] - np.mean(close120)) / (np.std(close120) + 1e-8)
    )
    log_volume = np.log(np.abs(volume[-60:]) + 1e-8)
    if np.std(returns) <= 1e-12 or np.std(log_volume) <= 1e-12:
        correlation = 0.0
    else:
        correlation = float(np.corrcoef(returns, log_volume)[0, 1])
    return {
        "quantevolver_return_sharpe_60": sharpe,
        "quantevolver_price_zscore_reversal_120": reversal,
        "quantevolver_return_log_volume_corr_60": correlation,
    }


def test_all_counted_components_are_plain_grade_b_and_form_a_source_census() -> None:
    ledger = faithfulness_ledger(1000)
    assert set(ledger["candidate_id"]) == set(PRIMARY_COMPONENTS)
    assert ledger["counted_primary"].all()
    assert set(ledger["grade"]) == {"B"}
    assert ledger[
        [
            "source_expression_exact",
            "source_operator_semantics_exact",
            "source_evaluator_rule_exact",
            "source_return_definition_exact",
            "formula_census_outcome_independent",
            "only_permitted_mechanical_changes",
        ]
    ].all().all()
    assert not ledger["native_agent_replication"].any()
    assert not ledger["full_search_or_training_pipeline_reproduced"].any()


def test_released_seed_scores_match_independent_source_semantics() -> None:
    months = pd.date_range("1990-01-31", periods=260, freq="ME")
    step = np.arange(len(months), dtype=float)
    close = 20.0 + 0.03 * step + np.sin(step / 7.0)
    volume = 1000.0 + 4.0 * step + 20.0 * np.cos(step / 11.0)
    panel = pd.DataFrame(
        {
            "permno": 1,
            "month": months,
            "prc": -close,
            "tvol": volume,
            "me": 1000.0,
        }
    )
    scored = evaluate_released_seeds(panel)
    expected = source_reference(close, volume)
    for candidate_id, value in expected.items():
        assert scored.iloc[-1][candidate_id] == pytest.approx(
            value, rel=1e-10, abs=1e-12
        )


def test_released_evaluator_drops_missing_pairs_before_ranking() -> None:
    candidate_id = "quantevolver_return_sharpe_60"
    frame = pd.DataFrame(
        {
            "month": pd.Timestamp("2024-01-31"),
            "permno": range(10),
            candidate_id: range(10),
            "source_forward_return": np.arange(10) / 100.0,
            "source_forward_observation_month": pd.Timestamp("2024-02-29"),
        }
    )
    # The highest score is removed before q=floor(n/5), exactly as source
    # pair.dropna() does. Nine eligible pairs imply one stock per leg.
    frame.loc[frame["permno"] == 9, "source_forward_return"] = np.nan
    repeated = pd.concat(
        [frame.assign(month=pd.Timestamp("2024-01-31") + pd.offsets.MonthEnd(i)) for i in range(20)],
        ignore_index=True,
    )
    path, holdings = released_cross_sectional_path(repeated, candidate_id)
    assert len(path) == 20
    assert (path["n_eligible_source_pairs"] == 9).all()
    assert (path["n_long"] == 1).all()
    assert (path["n_short"] == 1).all()
    assert path.iloc[0]["gross_excess_return"] == pytest.approx(0.08)
    first = holdings[holdings["formation_month"] == pd.Timestamp("2024-01-31")]
    assert first.loc[first["side"] == "long", "permno"].tolist() == [8]
    assert first.loc[first["side"] == "short", "permno"].tolist() == [0]


def test_released_evaluator_return_reconstructs_from_holding_means() -> None:
    candidate_id = "quantevolver_price_zscore_reversal_120"
    frame = pd.DataFrame(
        {
            "month": pd.Timestamp("2024-01-31"),
            "permno": range(10),
            candidate_id: range(10),
            "source_forward_return": np.arange(10) / 100.0,
            "source_forward_observation_month": pd.Timestamp("2024-02-29"),
        }
    )
    repeated = pd.concat(
        [frame.assign(month=pd.Timestamp("2024-01-31") + pd.offsets.MonthEnd(i)) for i in range(20)],
        ignore_index=True,
    )
    path, holdings = released_cross_sectional_path(repeated, candidate_id)
    first = holdings[holdings["formation_month"] == path.iloc[0]["formation_month"]]
    reconstructed = (
        first.loc[first["side"] == "long", "source_forward_return"].mean()
        - first.loc[first["side"] == "short", "source_forward_return"].mean()
    )
    assert path.iloc[0]["gross_excess_return"] == pytest.approx(reconstructed)
    assert path.iloc[0]["net_excess_return"] == pytest.approx(reconstructed)
    assert path.iloc[0]["cost_bps_one_way"] == 0.0


def test_fail_closed_validator_rejects_a_conditional_counted_grade(
    tmp_path: Path,
) -> None:
    source = Path(__file__).resolve().parents[1] / "paper_runs/faithful_component_replications"
    for name in (
        "manifest.json",
        "faithfulness_ledger.csv",
        "monthly_return_paths.csv",
        "formation_holdings.csv",
    ):
        shutil.copy2(source / name, tmp_path / name)
    ledger_path = tmp_path / "faithfulness_ledger.csv"
    ledger = pd.read_csv(ledger_path)
    ledger.loc[0, "grade"] = "B-conditional"
    ledger.to_csv(ledger_path, index=False)
    failures = validation_failures(tmp_path)
    assert "every counted row must have strict grade A or B" in failures
    assert "conditional grades are forbidden in the counted sample" in failures
    assert any(failure.startswith("tracked output hash mismatch") for failure in failures)
