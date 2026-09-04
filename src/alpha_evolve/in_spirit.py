"""Transparent researcher-authored reconstructions for the in-spirit study."""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd


def cross_sectional_unit_rank(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Map each monthly cross section to [-1, 1] without filling missing values."""
    if "month" not in frame or not columns:
        raise ValueError("month and at least one score column are required")
    values = frame[columns].apply(pd.to_numeric, errors="coerce")
    grouped = values.groupby(frame["month"], sort=False)
    ranks = grouped.rank(method="average")
    counts = grouped.transform("count")
    result = 2.0 * (ranks - 1.0) / (counts - 1.0) - 1.0
    return result.where(counts >= 2)


def fama_candidate_library(frame: pd.DataFrame, seeds: list[str]) -> pd.DataFrame:
    """Generate the fixed FAMA-inspired identity/mean/difference/product grammar."""
    missing = {"month", *seeds} - set(frame)
    if missing:
        raise ValueError(f"missing FAMA seed inputs: {sorted(missing)}")
    if len(seeds) != 6 or len(set(seeds)) != 6:
        raise ValueError("the frozen FAMA reconstruction requires six unique seeds")
    seed_scores = cross_sectional_unit_rank(frame, seeds)
    raw: dict[str, pd.Series] = {}
    for seed in seeds:
        raw[f"identity__{seed}"] = seed_scores[seed]
    for left, right in combinations(seeds, 2):
        raw[f"mean__{left}__{right}"] = (seed_scores[left] + seed_scores[right]) / 2.0
        raw[f"difference__{left}__{right}"] = seed_scores[left] - seed_scores[right]
        raw[f"product__{left}__{right}"] = seed_scores[left] * seed_scores[right]
    candidates = pd.DataFrame(raw, index=frame.index)
    if candidates.shape[1] != 51:
        raise AssertionError("frozen FAMA grammar must generate 51 candidates")
    ranked = pd.concat([frame[["month"]], candidates], axis=1)
    return cross_sectional_unit_rank(ranked, list(candidates))


def monthly_rankic(
    frame: pd.DataFrame,
    candidates: pd.DataFrame,
    *,
    return_column: str = "ret_exc_lead1m",
    minimum_cross_section: int = 20,
) -> pd.DataFrame:
    """Compute formation-month candidate RankIC using only same-row next returns."""
    if not candidates.index.equals(frame.index):
        raise ValueError("candidate scores must align with the formation frame")
    if return_column not in frame:
        raise ValueError(f"missing RankIC outcome: {return_column}")
    rows: list[pd.Series] = []
    months: list[pd.Timestamp] = []
    for month, indices in frame.groupby("month", sort=True).groups.items():
        returns = pd.to_numeric(frame.loc[indices, return_column], errors="coerce")
        returns = returns.rank(method="average")
        values = candidates.loc[indices]
        valid_counts = values.notna().mul(returns.notna(), axis=0).sum()
        correlation = values.corrwith(returns).where(valid_counts >= minimum_cross_section)
        rows.append(correlation)
        months.append(pd.Timestamp(month))
    result = pd.DataFrame(rows, index=pd.DatetimeIndex(months, name="formation_month"))
    return result.reindex(columns=candidates.columns)


def _rankicir(history: pd.DataFrame, minimum_months: int) -> tuple[pd.Series, pd.Series]:
    count = history.count()
    mean = history.mean()
    deviation = history.std(ddof=1)
    quality = mean.abs() / deviation
    eligible = (count >= minimum_months) & np.isfinite(quality) & mean.ne(0.0)
    return mean.where(eligible), quality.where(eligible)


def _farthest_first_groups(
    history: pd.DataFrame,
    quality: pd.Series,
    cluster_count: int,
    minimum_months: int,
) -> dict[str, list[str]]:
    eligible = sorted(quality.dropna().index)
    if len(eligible) < cluster_count:
        raise ValueError("too few eligible candidate histories for frozen FAMA groups")
    correlation = history[eligible].corr(min_periods=minimum_months).abs().fillna(0.0)
    np.fill_diagonal(correlation.values, 1.0)

    def quality_order(name: str) -> tuple[float, str]:
        return (-float(quality[name]), name)

    centers = [sorted(eligible, key=quality_order)[0]]
    while len(centers) < cluster_count:
        remaining = [name for name in eligible if name not in centers]
        distance = {
            name: 1.0 - float(correlation.loc[name, centers].max())
            for name in remaining
        }
        next_center = sorted(
            remaining,
            key=lambda name: (-distance[name], -float(quality[name]), name),
        )[0]
        centers.append(next_center)
    groups = {center: [] for center in centers}
    for candidate in eligible:
        center = sorted(
            centers,
            key=lambda name: (-float(correlation.loc[candidate, name]), name),
        )[0]
        groups[center].append(candidate)
    return groups


def fama_rolling_scores(
    frame: pd.DataFrame,
    candidates: pd.DataFrame,
    rankics: pd.DataFrame,
    *,
    common_start: str,
    training_months: int = 60,
    minimum_rankic_months: int = 24,
    cluster_count: int = 7,
    selected_cross_samples: int = 2,
) -> tuple[pd.Series, pd.DataFrame]:
    """Select and orient two correlation-diverse candidates from past RankIC only."""
    if not candidates.index.equals(frame.index):
        raise ValueError("candidate scores must align with the formation frame")
    if list(rankics.columns) != list(candidates.columns):
        raise ValueError("RankIC and candidate columns differ")
    if selected_cross_samples > cluster_count:
        raise ValueError("cannot select more cross-samples than diversity groups")
    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    month_groups = frame.groupby("month", sort=False).groups
    for month in months:
        history = rankics.loc[rankics.index < month].tail(training_months)
        if len(history) != training_months:
            raise ValueError(f"FAMA warm-up is incomplete at {month.date()}")
        mean, quality = _rankicir(history, minimum_rankic_months)
        groups = _farthest_first_groups(history, quality, cluster_count, minimum_rankic_months)
        representatives = []
        for members in groups.values():
            representative = sorted(
                members,
                key=lambda name: (-float(quality[name]), name),
            )[0]
            representatives.append(representative)
        chosen = sorted(
            representatives,
            key=lambda name: (-float(quality[name]), name),
        )[:selected_cross_samples]
        indices = month_groups[month]
        oriented = np.column_stack(
            [
                candidates.loc[indices, name].to_numpy(dtype=float) * (1.0 if mean[name] > 0 else -1.0)
                for name in chosen
            ]
        )
        finite = np.isfinite(oriented)
        count = finite.sum(axis=1)
        combined = np.divide(
            np.where(finite, oriented, 0.0).sum(axis=1),
            count,
            out=np.full(len(indices), np.nan),
            where=count > 0,
        )
        result.loc[indices] = combined
        diagnostics.append(
            {
                "formation_month": str(month.date()),
                "training_start": str(history.index[0].date()),
                "training_end": str(history.index[-1].date()),
                "training_months": len(history),
                "eligible_candidates": int(quality.notna().sum()),
                "cluster_count": len(groups),
                "selected_1": chosen[0],
                "selected_1_mean_rankic": float(mean[chosen[0]]),
                "selected_1_rankicir": float(quality[chosen[0]]),
                "selected_1_orientation": 1 if mean[chosen[0]] > 0 else -1,
                "selected_2": chosen[1],
                "selected_2_mean_rankic": float(mean[chosen[1]]),
                "selected_2_rankicir": float(quality[chosen[1]]),
                "selected_2_orientation": 1 if mean[chosen[1]] > 0 else -1,
            }
        )
    return result, pd.DataFrame(diagnostics)
