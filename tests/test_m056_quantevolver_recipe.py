from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_quantevolver_headline import (  # noqa: E402
    CANDIDATE_ID,
    SOURCE_FORMULA,
    quant_evolver_return_sharpe_60,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def panel(periods: int = 80) -> pd.DataFrame:
    months = pd.date_range("2000-01-31", periods=periods, freq="ME")
    step = np.arange(periods, dtype=float)
    return pd.DataFrame(
        {
            "security_id": 1,
            "month": months,
            "prc": 25.0 + 0.07 * step + np.sin(step / 4.0),
        }
    )


def test_m056_recipe_selects_first_valid_released_seed_without_outcome_claim():
    recipe = json.loads(
        (ROOT / "paper_runs/us_jkp_headline/M056_quantevolver/recipe.json").read_text()
    )
    assert recipe["candidate_id"] == CANDIDATE_ID == "quantevolver_return_sharpe_60"
    assert recipe["source_seed_id"] == "seed_0001"
    assert recipe["source_formula"] == SOURCE_FORMULA
    assert "source order" in recipe["component_selection_reason"]
    assert recipe["prior_outcomes_seen"] is True
    assert recipe["preclassified_scope"] == "completed_partial_if_full_common_path_succeeds"
    source = recipe["source_repository"]
    assert sha256(ROOT / source["seed_snapshot_path"]) == source["seed_snapshot_sha256"]
    assert sha256(ROOT / source["evaluator_snapshot_path"]) == source["evaluator_snapshot_sha256"]


def test_m056_score_matches_released_nested_epsilon_semantics():
    data = panel()
    scored = quant_evolver_return_sharpe_60(data)
    close = data["prc"].abs().to_numpy()
    returns = np.diff(close[-61:]) / (close[-61:-1] + 1e-8)
    expected = float(np.mean(returns) / (abs(np.std(returns, ddof=0) + 1e-8) + 1e-8))
    np.testing.assert_allclose(scored["score"].iloc[-1], expected, rtol=0, atol=1e-12)
    assert scored["score"].iloc[:60].isna().all()


def test_m056_calendar_gap_breaks_the_sixty_return_window():
    data = panel(130).drop(index=65).reset_index(drop=True)
    scored = quant_evolver_return_sharpe_60(data)
    gap_month = pd.Timestamp("2005-07-31")
    after_gap = scored[scored["month"].between(gap_month, gap_month + pd.offsets.MonthEnd(59))]
    assert after_gap["score"].isna().all()
    assert np.isfinite(scored["score"].iloc[-1])


def test_m056_future_prices_do_not_change_prior_scores():
    data = panel(90)
    cutoff = data["month"].iloc[75]
    altered = data.copy()
    altered.loc[altered["month"] > cutoff, "prc"] *= 9.0
    baseline = quant_evolver_return_sharpe_60(data)
    counterfactual = quant_evolver_return_sharpe_60(altered)
    through_cutoff = baseline["month"] <= cutoff
    np.testing.assert_allclose(
        baseline.loc[through_cutoff, "score"],
        counterfactual.loc[through_cutoff, "score"],
        equal_nan=True,
        rtol=0,
        atol=0,
    )
