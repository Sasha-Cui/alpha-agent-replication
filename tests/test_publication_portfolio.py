import numpy as np
from alpha_evolve.publication_portfolio import walk_forward_augmentation


def test_allocator_has_no_future_information_and_long_only_agent():
    rng = np.random.default_rng(541)
    f = rng.normal(0.003, 0.025, (70, 7))
    a = rng.normal(0.01, 0.06, 70)
    original = walk_forward_augmentation(f, a, min_train=30)
    f[60:] += 1.0
    a[60:] += 1.0
    changed = walk_forward_augmentation(f, a, min_train=30)
    assert np.array_equal(original["returns"][:30], changed["returns"][:30])
    assert np.array_equal(original["weights"][:30], changed["weights"][:30])
    assert (original["weights"][:, 1, -1] >= 0).all()


def test_constant_factor_scaling_and_sign_conventions_cancel():
    rng = np.random.default_rng(52)
    f = rng.normal(0.002, 0.025, (65, 6))
    a = rng.normal(0.004, 0.06, 65)
    first = walk_forward_augmentation(f, a, min_train=30)
    second = walk_forward_augmentation(f * np.array([0.1, -2, 30, -0.2, 7, 0.05]), a, min_train=30)
    assert np.allclose(first["returns"], second["returns"], atol=1e-12, rtol=0)
