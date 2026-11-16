"""Degenerate outputs cannot make another economic comparison significant."""

import pytest
from alpha_evolve.fidelity_inference_v2 import adjust_grouped_family


def row(p, degenerate=False):
    return {"group_t_p_two_sided": p, "degenerate_sampling_variation": degenerate}


def test_degenerate_zero_does_not_reduce_other_holm_penalty():
    inputs, adjusted = adjust_grouped_family([row(0, True), row(0.006)], 2, True)
    assert inputs == [1, 0.006]
    assert adjusted == [1, 0.012]


def test_partial_family_and_regular_holm_unchanged():
    assert adjust_grouped_family([row(0.14)], 2, False) == ([0.14], [0.28])
    assert adjust_grouped_family([row(0, True)], 54, False) == ([1], [1])
    assert adjust_grouped_family([row(0.003), row(0.009)], 2, True)[1] == [0.006, 0.009]


def test_missing_family_or_invalid_statistic_is_not_silently_omitted():
    for rows, size, complete in [([row(0.02)], 2, True), ([row(float("nan"))], 2, False), ([], 2, False)]:
        with pytest.raises(ValueError):
            adjust_grouped_family(rows, size, complete)
