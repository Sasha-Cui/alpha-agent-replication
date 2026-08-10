from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_broad_jkp_crossfit.py"
SPEC = importlib.util.spec_from_file_location("broad_jkp_crossfit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_holm_adjustment_matches_step_down_definition() -> None:
    p = np.asarray([0.001, 0.01, 0.03, 0.8])
    adjusted = MODULE.holm_adjust(p)
    np.testing.assert_allclose(adjusted, [0.004, 0.03, 0.06, 0.8])


def test_crossfit_retains_alpha_in_test_residual() -> None:
    rng = np.random.default_rng(7)
    x = rng.normal(size=(90, 1))
    alpha = 0.012
    y = (alpha + 1.7 * x[:, 0])[:, None]
    residuals, chosen = MODULE.rolling_crossfit_residuals(
        x,
        y,
        train_months=48,
        validation_months=12,
        lambdas=np.asarray([1.0]),
        n_unpenalized=1,
    )
    np.testing.assert_allclose(residuals[:, 0], alpha, atol=1e-10)
    np.testing.assert_allclose(chosen[:, 0], 1.0)



def test_crossfit_reconstruction_exposes_predictions_penalties_and_loadings() -> None:
    rng = np.random.default_rng(17)
    x = rng.normal(size=(90, 2))
    y = (0.01 + x @ np.asarray([1.5, -0.4]))[:, None]
    result = MODULE.rolling_crossfit_reconstruction(
        x,
        y,
        train_months=48,
        validation_months=12,
        lambdas=np.asarray([0.0]),
        n_unpenalized=2,
    )
    assert result.residuals.shape == (42, 1)
    assert result.fitted_values.shape == (42, 1)
    assert result.selected_lambdas.shape == (42, 1)
    assert result.loadings.shape == (42, 2, 1)
    np.testing.assert_allclose(
        result.fitted_values + result.residuals, y[48:], atol=1e-12
    )
    np.testing.assert_allclose(
        result.loadings[:, :, 0], np.tile([1.5, -0.4], (42, 1)), atol=1e-12
    )
    np.testing.assert_allclose(result.selected_lambdas, 0.0)


def test_crossfit_uses_no_future_candidate_returns() -> None:
    rng = np.random.default_rng(11)
    x = rng.normal(size=(100, 2))
    y = (0.005 + x @ np.asarray([0.8, -0.3]) + rng.normal(scale=0.01, size=100))[:, None]
    kwargs = dict(
        train_months=48,
        validation_months=12,
        lambdas=np.asarray([0.1, 1.0, 10.0]),
        n_unpenalized=1,
    )
    original, _ = MODULE.rolling_crossfit_residuals(x, y, **kwargs)
    changed = y.copy()
    changed[80:] += 10.0
    perturbed, _ = MODULE.rolling_crossfit_residuals(x, changed, **kwargs)
    # Output row 31 corresponds to source month 79. Future changes cannot
    # alter any residual through that row.
    np.testing.assert_allclose(original[:32], perturbed[:32], atol=1e-12)


def test_circular_block_indices_are_shared_and_in_range() -> None:
    idx = MODULE.circular_block_indices(np.random.default_rng(3), n=17, block_length=6)
    assert idx.shape == (17,)
    assert np.all((idx >= 0) & (idx < 17))
    for start in range(0, 12, 6):
        np.testing.assert_array_equal((idx[start : start + 6] - idx[start]) % 17, np.arange(6))
