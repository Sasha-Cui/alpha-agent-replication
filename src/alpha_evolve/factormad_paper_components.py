"""Paper-derived mechanics for DOI 10.1145/3768292.3770377.

This module implements only operations uniquely fixed by the FactorMAD paper.
It is not author code, an LLM replay, a market-data reconstruction, or
regeneration of a published result. Ambiguous operations fail closed instead
of silently choosing conventions that the paper does not identify.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


PAPER_BOUNDARY = (
    "paper-derived controlled mechanic, not author code, native execution, "
    "or regeneration of a FactorMAD result"
)


class UnderspecifiedPaperMechanic(ValueError):
    """Raised when the paper does not determine one executable procedure."""


def _finite(value: float, name: str) -> float:
    checked = float(value)
    if not math.isfinite(checked):
        raise ValueError(f"{name} must be finite")
    return checked


def future_vwap_return(vwap: Sequence[float], *, time_index: int, horizon: int) -> float:
    """Section 4.1.1's label: VWAP[t+h+1] / VWAP[t+1] - 1."""
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if time_index < 0 or time_index + horizon + 1 >= len(vwap):
        raise IndexError("label window is outside the supplied VWAP series")
    start = _finite(vwap[time_index + 1], "starting VWAP")
    end = _finite(vwap[time_index + horizon + 1], "ending VWAP")
    if start <= 0 or end <= 0:
        raise ValueError("VWAP values must be positive")
    return end / start - 1


def proposing_agent_index(debate_round: int) -> int:
    """Equation 4's alternating proposer index j = t mod 2."""
    if debate_round < 0:
        raise ValueError("debate_round cannot be negative")
    return debate_round % 2


def choose_seed_source(*, uniform_draw: float, seed_probability: float) -> str:
    """Equation 3's existing-factor versus generated-factor branch."""
    draw = _finite(uniform_draw, "uniform_draw")
    probability = _finite(seed_probability, "seed_probability")
    if not 0 <= draw < 1 or not 0 <= probability <= 1:
        raise ValueError("draw must be in [0, 1) and probability in [0, 1]")
    return "existing_factor" if draw < probability else "generated_factor"


def accept_factor(
    *,
    metric: float,
    maximum_correlation: float,
    metric_threshold: float,
    correlation_threshold: float,
) -> bool:
    """Algorithm 1 line 25's two strict acceptance inequalities."""
    values = (
        _finite(metric, "metric"),
        _finite(maximum_correlation, "maximum_correlation"),
        _finite(metric_threshold, "metric_threshold"),
        _finite(correlation_threshold, "correlation_threshold"),
    )
    metric, maximum_correlation, metric_threshold, correlation_threshold = values
    return metric > metric_threshold and maximum_correlation < correlation_threshold


def equal_weight_top_k(scores: Sequence[float], k: int) -> list[float]:
    """Section 4.3's daily equal-weight TopK portfolio for unique scores."""
    checked = [_finite(value, "score") for value in scores]
    if not checked:
        raise ValueError("scores cannot be empty")
    if not 0 < k <= len(checked):
        raise ValueError("k must lie between one and the number of scores")
    ranked = sorted(range(len(checked)), key=checked.__getitem__, reverse=True)
    if k < len(checked) and checked[ranked[k - 1]] == checked[ranked[k]]:
        raise UnderspecifiedPaperMechanic(
            "the paper does not specify a tie policy at the TopK boundary"
        )
    selected = set(ranked[:k])
    return [1 / k if index in selected else 0.0 for index in range(len(checked))]


def noncomment_code_lines(source: str) -> int:
    """Section 4.4's factor-complexity unit for ordinary full-line comments."""
    if not isinstance(source, str):
        raise TypeError("source must be text")
    return sum(
        bool(line.strip()) and not line.lstrip().startswith("#")
        for line in source.splitlines()
    )


def initialize_agents(*_: object, **__: object) -> None:
    """Reject replay of the omitted example library, k, prompts, and sampling."""
    raise UnderspecifiedPaperMechanic(
        "the initial factor library, example count k, sampling distribution, "
        "perspective prompt, factor requirements, and model request are absent"
    )


def validate_factor_code(*_: object, **__: object) -> None:
    """Reject reconstruction of prose-only validation checks."""
    raise UnderspecifiedPaperMechanic(
        "Table 1 names error categories and suggestions but does not provide the "
        "validator, thresholds, timeout, dimension test, stationarity test, or parser"
    )


def correct_factor_code(*_: object, **__: object) -> None:
    """Reject replay of the omitted correction prompt and stopping behavior."""
    raise UnderspecifiedPaperMechanic(
        "the correction prompt, model request, maximum K, retry/error history "
        "serialization, and terminal failure disposition are absent"
    )


def train_prediction_models(*_: object, **__: object) -> None:
    """Reject reconstruction of LR/MLP/LGB training without hyperparameters."""
    raise UnderspecifiedPaperMechanic(
        "model hyperparameters, optimization, rolling or static fit schedule, seeds, "
        "missing-value policy, and exact train/validation slices are absent"
    )


def combine_overlapping_top_k_portfolios(*_: object, **__: object) -> None:
    """Reject the undefined daily rebalance/ten-day holding overlap convention."""
    raise UnderspecifiedPaperMechanic(
        "daily TopK selection with a ten-trading-day hold does not specify whether "
        "overlapping vintages are averaged, replaced, or maintained as sleeves"
    )


def calculate_investment_metrics(*_: object, **__: object) -> None:
    """Reject reconstruction of incompletely defined AR/IR/RoMaD metrics."""
    raise UnderspecifiedPaperMechanic(
        "the annualization factor, excess-return alignment, IR denominator, drawdown "
        "path convention, cost timing, and zero-denominator behavior are absent"
    )


def reproduce_llm_request(_: Mapping[str, object]) -> None:
    """Reject replay without complete prompts and immutable request/response logs."""
    raise UnderspecifiedPaperMechanic(
        "only the GPT-4o 2024-08-06 name is stated; prompts, API parameters, seed, "
        "responses, tool contracts, parser, and retry policy are not released"
    )
