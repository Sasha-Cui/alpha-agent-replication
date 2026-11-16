import numpy as np
import pandas as pd
import pytest
from alpha_evolve.economic_fidelity import (
    Factor, InvalidFactor, compile_factor, daily_account, monthly_compound,
    seed_factors, top_weights,
)


def test_disclosed_seed_families_keep_daily_horizons():
    factors = seed_factors()
    assert len(factors) == 42
    p = np.column_stack([100 * 1.01 ** np.arange(30), 100 * .99 ** np.arange(30)])
    momentum = next(f for f in factors if f.name == 'momentum_7_v1')
    assert np.allclose(momentum.score(p), [1.01**7-1, .99**7-1])
    ma = next(f for f in factors if f.name == 'ma_21_v1')
    assert np.allclose(ma.score(p), p[-21:].mean(axis=0))
    for f in factors:
        assert np.isfinite(f.score(p)).all()


@pytest.mark.parametrize('code', [
    'import os\ndef f_3_v1(prices, window=3): return 1',
    'def f_3_v1(prices, window=3): return open("x").read()',
    'def f_3_v1(prices, window=3): return np.load("x")',
    'def f_3_v1(prices, window=3): return prices.__class__',
    'def f_3_v1(prices, window=3):\n    while True: pass',
    'def f_3_v1(prices, window=3):\n    prices[0] = 7\n    return 1',
    'def f_3_v1(prices, window=open("x")): return 1',
    '@print\ndef f_3_v1(prices, window=3): return 1',
])
def test_generated_code_cannot_access_files_or_mutate_input(code):
    with pytest.raises(InvalidFactor):
        compile_factor(code)


def test_no_price_backfill_or_future_eligibility():
    factor = Factor('def momentum_3_v1(prices, window=3):\n    return prices[-1]/prices[-4]-1')
    p = np.column_stack([np.arange(1, 31), np.arange(2, 32)]).astype(float)
    p[0, 1] = np.nan
    score = factor.score(p)
    assert np.isfinite(score[0]) and np.isnan(score[1])
    assert top_weights(score, 1).tolist() == [1, 0]


def test_close_execution_requires_one_day_before_earning_return():
    targets = np.array([[1., 0.], [0., 1.], [0., 1.]])
    returns = np.array([[99., 99.], [.1, .8], [.2, .05]])
    result, _, _ = daily_account(targets, returns, 0)
    assert np.allclose(result, [0, .1, .05])


def test_costs_are_self_financing_and_drift_aware():
    targets = np.array([[.5, .5], [.5, .5]])
    returns = np.array([[0., 0.], [.2, 0.]])
    result, turnover, fees = daily_account(targets, returns, 10)
    assert result[0] == pytest.approx(1 / 1.001 - 1)
    assert turnover[1] > 0  # Equal targets require trading after differential returns.
    assert np.allclose(fees, .001 * turnover)
    assert result[1] < .1


def test_missing_held_returns_fail_without_reweighting():
    with pytest.raises(ValueError, match='held stock'):
        daily_account(np.array([[1., 0.], [0., 1.]]), np.array([[np.nan, 0.], [np.nan, .1]]), 0)


def test_compounding_preserves_daily_wealth_and_calendar():
    dates = pd.to_datetime(['2024-01-30', '2024-01-31', '2024-02-01'])
    returns = np.array([.1, -.1, .2])
    monthly = monthly_compound(dates, returns)
    assert monthly.iloc[0] == pytest.approx(-.01)
    assert np.prod(1 + monthly) == pytest.approx(np.prod(1 + returns))


def test_feedback_never_uses_outcomes_after_decision_date():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).parents[1] / 'scripts/run_efs_economic_fidelity.py'
    spec = importlib.util.spec_from_file_location('efs_runner_test', path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    rng = np.random.default_rng(24)
    prices = 100 * np.cumprod(1 + rng.normal(.0002, .01, (110, 15)), axis=0)
    dates = pd.bdate_range('2020-01-01', periods=110)
    recipe = {'portfolio_assets': 5, 'feedback_days': 30}
    factor = next(f for f in seed_factors() if f.name == 'momentum_7_v1')
    a = runner.ResearchEngine(prices, dates, list(range(15)), recipe).performance(factor, 85)
    changed = prices.copy()
    changed[86:] *= 10
    b = runner.ResearchEngine(changed, dates, list(range(15)), recipe).performance(factor, 85)
    assert a == b
    changed[85] *= 1.2
    c = runner.ResearchEngine(changed, dates, list(range(15)), recipe).performance(factor, 85)
    assert c['mean_return'] != a['mean_return']  # The last completed close is usable.


def test_efs_search_feedback_uses_source_nonsparse_25_asset_heuristic():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('efs_feedback_test', Path(__file__).parents[1] / 'scripts/run_efs_economic_fidelity.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    daily = np.arange(1, 41) * .0001
    prices = 100 * (1 + daily[None, :]) ** np.arange(110)[:, None]
    recipe = {'portfolio_assets':10,'feedback_portfolio_assets':25,'recall_assets':20,'feedback_days':30}
    engine = runner.ResearchEngine(prices, pd.bdate_range('2020-01-01',periods=110), list(range(40)), recipe)
    factor = next(f for f in seed_factors() if f.name == 'momentum_7_v1')
    metrics = engine.performance(factor,85)
    assert metrics['mean_return'] == pytest.approx(daily[-25:].mean())
    assert metrics['mean_return'] != pytest.approx(daily[-10:].mean())
    assert metrics['mean_recall_at_20'] == 1


def test_factor_provenance_index_is_json_serializable():
    import json
    factor = Factor('def momentum_3_v1(prices, window=3): return prices[-1]/prices[-4]-1', created_index=np.int64(42))
    assert json.loads(json.dumps({'created_index':factor.created_index})) == {'created_index':42}
