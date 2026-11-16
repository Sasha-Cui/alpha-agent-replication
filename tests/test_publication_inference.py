import numpy as np
import pytest
from alpha_evolve.publication_inference import (
    stationary_indices,
    paired_effect,
    ols_alpha,
    refitted_alpha_bootstrap,
    chronological_projection,
    holm_adjust,
)


def test_factor_span_identity_recovers_zero_alpha_and_refits():
    rng = np.random.default_rng(41)
    x = rng.normal(size=(80, 4))
    y = x @ np.array([0.5, -0.2, 0.1, 0.7])
    point = ols_alpha(y, x)
    interval = refitted_alpha_bootstrap(y, x, replicates=99)
    assert abs(point["annualized_alpha"]) < 1e-12
    assert abs(interval["ci95_low"]) < 1e-12 and abs(interval["ci95_high"]) < 1e-12
    assert interval["estimator_refitted_every_draw"]
    shifted = refitted_alpha_bootstrap(y + 0.02 / 12, x, replicates=99)
    assert shifted["annualized_arithmetic_effect"] == pytest.approx(0.02, abs=1e-12)


def test_short_history_cannot_produce_full_jkp_alpha():
    rng = np.random.default_rng(7)
    with pytest.raises(ValueError, match="not identified"):
        ols_alpha(rng.normal(size=72), rng.normal(size=(72, 132)))


def test_paired_identity_and_practical_equivalence():
    r = np.arange(60) / 10000
    result = paired_effect(r, r, replicates=99)
    assert result["annualized_arithmetic_effect"] == 0 and not result["equivalent_within_margin_tost5"]
    assert result["degenerate_sampling_variation"]
    shifted = paired_effect(r + 0.003, r, replicates=99)
    assert shifted["annualized_arithmetic_effect"] == pytest.approx(0.036)
    assert not shifted["rules_out_positive_margin_one_sided5"]


def test_bootstrap_keeps_paired_dates_and_restarts():
    indexes = stationary_indices(30, 100, 6, np.random.default_rng(1))
    assert indexes.shape == (100, 30) and ((indexes >= 0) & (indexes < 30)).all()
    continuation = indexes[:, 1:] == (indexes[:, :-1] + 1) % 30
    assert 0.7 < continuation.mean() < 0.9


def test_projection_cannot_use_future_outcomes_or_standardization():
    rng = np.random.default_rng(18)
    x = rng.normal(size=(65, 12))
    y = x[:, 0] + rng.normal(size=65)
    original = chronological_projection(y, x, min_train=30, components=3)["predictions"]
    x[55:] *= 100
    y[55:] += 100
    changed = chronological_projection(y, x, min_train=30, components=3)["predictions"]
    assert np.array_equal(original[30:55], changed[30:55])
    assert "no unrestricted" in chronological_projection(y, x, min_train=30)["label"]


def test_holm_monotonic_family_correction():
    assert np.allclose(holm_adjust([0.04, 0.001, 0.03]), [0.06, 0.003, 0.06])


def test_hac_matches_independent_statsmodels_implementation():
    import statsmodels.api as sm
    from statsmodels.stats.sandwich_covariance import cov_hac

    rng = np.random.default_rng(606)
    x = rng.normal(0, 0.03, (100, 3))
    error = rng.normal(0, 0.02, 100)
    for i in range(1, len(error)):
        error[i] += 0.4 * error[i - 1]
    y = 0.001 + x @ np.array([0.7, -0.1, 0.2]) + error
    result = ols_alpha(y, x, hac_lags=4)
    fit = sm.OLS(y, sm.add_constant(x)).fit()
    reference = np.sqrt(cov_hac(fit, nlags=4, use_correction=True)[0, 0]) * 12
    assert result["hac_se_annualized"] == pytest.approx(reference, rel=1e-10)


def test_grouped_inference_matches_scipy_t_test_on_independent_block_estimates():
    from scipy.stats import ttest_1samp
    from alpha_evolve.publication_inference import grouped_t_effect

    values = np.repeat(np.array([0.002, -0.001, 0.004, 0.001]), 18)
    result = grouped_t_effect(values)
    reference = ttest_1samp([0.002, -0.001, 0.004, 0.001], 0)
    assert result["group_t_p_two_sided"] == pytest.approx(reference.pvalue)
    assert result["annualized_arithmetic_effect"] == pytest.approx(0.018)
    rng = np.random.default_rng(47)
    with pytest.raises(ValueError, match="Block-level"):
        grouped_t_effect(rng.normal(size=36), factors=rng.normal(size=(36, 6)))
