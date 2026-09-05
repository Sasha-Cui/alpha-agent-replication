"""Transparent researcher-authored reconstructions for the in-spirit study."""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


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


def flag_trader_rolling_scores(
    frame: pd.DataFrame,
    features: list[str],
    semantic_prior: list[float],
    *,
    common_start: str,
    replay_months: int = 60,
    minimum_training_months: int = 24,
    ridge_penalty: float = 1.0,
    learning_rate: float = 0.0005,
    clip_coefficient: float = 0.2,
    maximum_gradient_norm: float = 0.5,
    action_memory_weight: float = 0.2,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a transparent past-only actor/critic surrogate for FLAG-TRADER."""
    missing = {"month", "security_id", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing FLAG-TRADER state: {sorted(missing)}")
    if len(features) != len(semantic_prior) or len(set(features)) != len(features):
        raise ValueError("FLAG-TRADER features and prior weights must align uniquely")
    if not 0 <= action_memory_weight < 1:
        raise ValueError("action-memory weight must be in [0, 1)")
    ranked = cross_sectional_unit_rank(frame, features)
    prior = np.asarray(semantic_prior, dtype=float)
    if not np.isfinite(prior).all() or np.linalg.norm(prior) == 0:
        raise ValueError("semantic prior must be finite and nonzero")
    actor = prior / np.linalg.norm(prior)
    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    previous_scores = pd.Series(dtype="float64")
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    for month in months:
        history_months = sorted(pd.Timestamp(value) for value in frame.loc[frame["month"] < month, "month"].unique())[-replay_months:]
        if len(history_months) != replay_months or len(history_months) < minimum_training_months:
            raise ValueError(f"FLAG-TRADER warm-up is incomplete at {month.date()}")
        history_mask = frame["month"].isin(history_months)
        x = ranked.loc[history_mask, features].to_numpy(dtype=float)
        y = pd.to_numeric(frame.loc[history_mask, "ret_exc_lead1m"], errors="coerce").to_numpy(dtype=float)
        valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
        x, y = x[valid], y[valid]
        if len(y) < 1000:
            raise ValueError("too few finite replay observations")
        design = np.column_stack([np.ones(len(x)), x])
        penalty = np.eye(design.shape[1]) * ridge_penalty
        penalty[0, 0] = 0.0
        critic = np.linalg.solve(design.T @ design + penalty, design.T @ y)
        predicted = design @ critic
        advantage = y - predicted
        advantage_deviation = advantage.std(ddof=1)
        if not np.isfinite(advantage_deviation) or advantage_deviation == 0:
            raise ValueError("FLAG-TRADER replay advantage is degenerate")
        advantage = (advantage - advantage.mean()) / advantage_deviation
        expected_action = np.tanh(x @ actor)
        gradient = np.mean(
            x * (advantage * (1.0 - expected_action**2))[:, None],
            axis=0,
        )
        raw_gradient_norm = float(np.linalg.norm(gradient))
        if raw_gradient_norm > maximum_gradient_norm:
            gradient *= maximum_gradient_norm / raw_gradient_norm
        clipped_gradient_norm = float(np.linalg.norm(gradient))
        delta = np.clip(
            learning_rate * gradient,
            -clip_coefficient,
            clip_coefficient,
        )
        actor = actor + delta

        indices = month_groups[month]
        current_x = ranked.loc[indices, features].to_numpy(dtype=float)
        current = np.full(len(indices), np.nan)
        current_valid = np.isfinite(current_x).all(axis=1)
        current[current_valid] = np.tanh(current_x[current_valid] @ actor)
        securities = frame.loc[indices, "security_id"]
        lagged = securities.map(previous_scores).to_numpy(dtype=float)
        remembered = np.isfinite(current) & np.isfinite(lagged)
        current[remembered] = (
            (1.0 - action_memory_weight) * current[remembered]
            + action_memory_weight * lagged[remembered]
        )
        result.loc[indices] = current
        previous_scores = pd.Series(current, index=securities.to_numpy())
        centered = y - y.mean()
        critic_r2 = 1.0 - float(np.sum((y - predicted) ** 2) / np.sum(centered**2))
        diagnostic: dict[str, object] = {
            "formation_month": str(month.date()),
            "training_start": str(history_months[0].date()),
            "training_end": str(history_months[-1].date()),
            "training_months": len(history_months),
            "training_observations": len(y),
            "critic_r2": critic_r2,
            "raw_gradient_norm": raw_gradient_norm,
            "clipped_gradient_norm": clipped_gradient_norm,
            "parameter_delta_norm": float(np.linalg.norm(delta)),
            "finite_current_scores": int(np.isfinite(current).sum()),
            "action_memory_weight": action_memory_weight,
        }
        diagnostic.update({f"actor_weight__{name}": float(value) for name, value in zip(features, actor)})
        diagnostic.update({f"critic_weight__{name}": float(value) for name, value in zip(["intercept", *features], critic)})
        diagnostics.append(diagnostic)
    return result, pd.DataFrame(diagnostics)


ALPHAQUANTER_TOOL_COLUMNS = [
    "market_technical",
    "fundamental",
    "sentiment_proxy",
    "macro_proxy",
]


def alphaquanter_tool_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """Build four disclosed JKP tool-category substitutes without future returns."""
    primitives = [
        "ret_12_1",
        "ret_6_1",
        "rvol_21d",
        "be_me",
        "gp_at",
        "f_score",
        "ocf_at",
        "ret_1_0",
        "rmax5_21d",
        "turnover_126d",
        "beta_60m",
    ]
    missing = {"month", "weight", "ret", *primitives} - set(frame)
    if missing:
        raise ValueError(f"missing AlphaQuanter tool inputs: {sorted(missing)}")
    ranked = cross_sectional_unit_rank(frame, primitives)
    raw = pd.DataFrame(index=frame.index)
    raw["market_technical"] = (
        ranked["ret_12_1"] + ranked["ret_6_1"] - ranked["rvol_21d"]
    ) / 3.0
    raw["fundamental"] = (
        ranked["be_me"] + ranked["gp_at"] + ranked["f_score"] + ranked["ocf_at"]
    ) / 4.0
    raw["sentiment_proxy"] = (
        ranked["ret_1_0"] + ranked["rmax5_21d"] + ranked["turnover_126d"]
    ) / 3.0
    market_rows = []
    for month, indices in frame.groupby("month", sort=True).groups.items():
        weight = pd.to_numeric(frame.loc[indices, "weight"], errors="coerce")
        current_return = pd.to_numeric(frame.loc[indices, "ret"], errors="coerce").fillna(0.0)
        market_rows.append((pd.Timestamp(month), float(np.sum(weight * current_return) / weight.sum())))
    market = pd.Series(dict(market_rows)).sort_index().rolling(6, min_periods=1).mean()
    regime = frame["month"].map(np.sign(market).replace(0.0, 1.0))
    raw["macro_proxy"] = ranked["beta_60m"].mul(regime.to_numpy()) - ranked["rvol_21d"]
    ranked_tools = pd.concat([frame[["month"]], raw], axis=1)
    return cross_sectional_unit_rank(ranked_tools, ALPHAQUANTER_TOOL_COLUMNS)


def multi_horizon_monthly_return(
    frame: pd.DataFrame,
    *,
    horizons: tuple[int, ...] = (1, 3, 6),
    eta: float = 0.8,
    return_column: str = "ret_total_lead1m",
) -> pd.Series:
    """Construct an exponentially blended forward label for past-only training."""
    if not horizons or tuple(sorted(set(horizons))) != horizons or horizons[0] < 1:
        raise ValueError("reward horizons must be unique increasing positive integers")
    if not 0 < eta < 1:
        raise ValueError("eta must lie strictly between zero and one")
    missing = {"month", "security_id", return_column} - set(frame)
    if missing:
        raise ValueError(f"missing multi-horizon label inputs: {sorted(missing)}")
    ordered = frame[["security_id", "month", return_column]].sort_values(
        ["security_id", "month"], kind="mergesort"
    )
    if ordered.duplicated(["security_id", "month"]).any():
        raise ValueError("duplicate security-month observations")
    groups = ordered.groupby("security_id", sort=False)
    labels = []
    for horizon in horizons:
        growth = np.ones(len(ordered))
        valid = np.ones(len(ordered), dtype=bool)
        for step in range(horizon):
            shifted_return = groups[return_column].shift(-step)
            shifted_month = groups["month"].shift(-step)
            expected_month = ordered["month"] + pd.offsets.MonthEnd(step)
            values = pd.to_numeric(shifted_return, errors="coerce").to_numpy(dtype=float)
            step_valid = shifted_month.eq(expected_month).to_numpy() & np.isfinite(values) & (values > -1.0)
            valid &= step_valid
            growth *= np.where(step_valid, 1.0 + values, 1.0)
        labels.append(pd.Series(np.where(valid, growth - 1.0, np.nan), index=ordered.index))
    weights = np.asarray([eta**number for number in range(len(horizons))], dtype=float)
    weights /= weights.sum()
    matrix = np.column_stack([label.to_numpy() for label in labels])
    blended = np.where(np.isfinite(matrix).all(axis=1), matrix @ weights, np.nan)
    result = pd.Series(blended, index=ordered.index, name="multi_horizon_return")
    return result.reindex(frame.index)


def alphaquanter_rolling_scores(
    frame: pd.DataFrame,
    tools: pd.DataFrame,
    reward: pd.Series,
    *,
    common_start: str,
    reward_gap_months: int = 6,
    training_months: int = 60,
    ridge_penalty: float = 1.0,
    maximum_selected_tools: int = 2,
    decision_threshold: float = 0.015,
) -> tuple[pd.Series, pd.DataFrame]:
    """Fit a past-only selective-tool policy to fully realized reward labels."""
    if not tools.index.equals(frame.index) or not reward.index.equals(frame.index):
        raise ValueError("AlphaQuanter tools, rewards, and frame must align")
    if list(tools.columns) != ALPHAQUANTER_TOOL_COLUMNS:
        raise ValueError("AlphaQuanter tool columns differ from the frozen recipe")
    if not 1 <= maximum_selected_tools <= len(tools.columns):
        raise ValueError("invalid number of selected tools")
    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    for month in months:
        reward_cutoff = month - pd.offsets.MonthEnd(reward_gap_months)
        eligible_months = sorted(
            pd.Timestamp(value)
            for value in frame.loc[frame["month"] <= reward_cutoff, "month"].unique()
        )[-training_months:]
        if len(eligible_months) != training_months:
            raise ValueError(f"AlphaQuanter warm-up is incomplete at {month.date()}")
        training = frame["month"].isin(eligible_months)
        x = tools.loc[training].to_numpy(dtype=float)
        y = reward.loc[training].to_numpy(dtype=float)
        valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
        x, y = x[valid], y[valid]
        if len(y) < 1000:
            raise ValueError("too few finite AlphaQuanter reward observations")
        design = np.column_stack([np.ones(len(x)), x])
        penalty = np.eye(design.shape[1]) * ridge_penalty
        penalty[0, 0] = 0.0
        fitted = np.linalg.solve(design.T @ design + penalty, design.T @ y)
        coefficient = pd.Series(fitted[1:], index=tools.columns)
        selected = sorted(
            tools.columns,
            key=lambda name: (-abs(float(coefficient[name])), name),
        )[:maximum_selected_tools]
        sparse = coefficient.where(coefficient.index.isin(selected), 0.0)
        indices = month_groups[month]
        current_x = tools.loc[indices].to_numpy(dtype=float)
        current = np.full(len(indices), np.nan)
        current_valid = np.isfinite(current_x).all(axis=1)
        current[current_valid] = fitted[0] + current_x[current_valid] @ sparse.to_numpy()
        result.loc[indices] = current
        predicted = design @ fitted
        centered = y - y.mean()
        r2 = 1.0 - float(np.sum((y - predicted) ** 2) / np.sum(centered**2))
        diagnostics.append(
            {
                "formation_month": str(month.date()),
                "training_start": str(eligible_months[0].date()),
                "training_end": str(eligible_months[-1].date()),
                "reward_ready_cutoff": str(reward_cutoff.date()),
                "training_months": len(eligible_months),
                "training_observations": len(y),
                "ridge_r2": r2,
                "selected_tool_1": selected[0],
                "selected_tool_2": selected[1],
                "buy_count": int(np.sum(current > decision_threshold)),
                "sell_count": int(np.sum(current < -decision_threshold)),
                "hold_count": int(np.sum(np.isfinite(current) & (np.abs(current) <= decision_threshold))),
                "finite_current_scores": int(np.isfinite(current).sum()),
                **{f"coefficient__{name}": float(sparse[name]) for name in tools.columns},
            }
        )
    return result, pd.DataFrame(diagnostics)


def finmem_layered_scores(
    frame: pd.DataFrame,
    layers: dict[str, dict[str, object]],
    *,
    common_start: str,
    memory_horizon_months: int = 60,
    top_k: int = 5,
    trading_days_per_month: int = 21,
    risk_adjustment_magnitude: float = 0.25,
) -> tuple[pd.Series, pd.DataFrame]:
    """Retrieve numeric shallow/intermediate/deep memories using past outcomes."""
    if list(layers) != ["shallow", "intermediate", "deep"]:
        raise ValueError("FinMem layers must be shallow, intermediate, and deep")
    feature_names = list(
        dict.fromkeys(
            feature
            for layer in layers.values()
            for feature in layer["features"]  # type: ignore[index]
        )
    )
    missing = {"month", "security_id", "weight", "ret", "ret_exc_lead1m", *feature_names} - set(frame)
    if missing:
        raise ValueError(f"missing FinMem inputs: {sorted(missing)}")
    ranked = cross_sectional_unit_rank(frame, feature_names)
    importance = (
        pd.to_numeric(frame["ret_exc_lead1m"], errors="coerce")
        .abs()
        .groupby(frame["month"], sort=False)
        .rank(method="average", pct=True)
    )
    vote_arrays = {name: np.full(len(frame), np.nan) for name in layers}
    retrieved_arrays = {name: np.zeros(len(frame), dtype=int) for name in layers}
    frame_months = pd.to_datetime(frame["month"])
    month_number = (frame_months.dt.year * 12 + frame_months.dt.month).to_numpy(dtype=int)
    outcome_values = pd.to_numeric(frame["ret_exc_lead1m"], errors="coerce").to_numpy(dtype=float)
    importance_values = importance.to_numpy(dtype=float)
    common_timestamp = pd.Timestamp(common_start)
    for indices in frame.groupby("security_id", sort=False).groups.values():
        positions = frame.index.get_indexer(indices)
        positions = positions[np.argsort(month_number[positions], kind="mergesort")]
        months = month_number[positions]
        lag = months[:, None] - months[None, :]
        temporal = (lag >= 1) & (lag <= memory_horizon_months)
        current_positions = np.flatnonzero(frame_months.iloc[positions].ge(common_timestamp).to_numpy())
        if not len(current_positions):
            continue
        outcomes = outcome_values[positions]
        event_importance = importance_values[positions]
        for layer_name, specification in layers.items():
            features = list(specification["features"])  # type: ignore[arg-type]
            state = ranked.iloc[positions][features].to_numpy(dtype=float)
            state_valid = np.isfinite(state).all(axis=1)
            norms = np.linalg.norm(state, axis=1)
            denominator = norms[:, None] * norms[None, :]
            relevance = np.divide(
                state @ state.T,
                denominator,
                out=np.zeros_like(denominator),
                where=denominator > 0,
            )
            relevance = (np.clip(relevance, -1.0, 1.0) + 1.0) / 2.0
            alpha = float(specification["daily_decay_alpha"])
            recency = np.where(
                temporal,
                alpha ** (trading_days_per_month * np.maximum(lag, 0)),
                0.0,
            )
            weights = specification["retrieval_weights"]
            retrieval_score = (
                float(weights["recency"]) * recency  # type: ignore[index]
                + float(weights["relevance"]) * relevance  # type: ignore[index]
                + float(weights["importance"]) * event_importance[None, :]  # type: ignore[index]
            )
            eligible = (
                temporal
                & state_valid[:, None]
                & state_valid[None, :]
                & np.isfinite(outcomes)[None, :]
                & np.isfinite(event_importance)[None, :]
            )
            retrieval_score = np.where(eligible, retrieval_score, -np.inf)
            for current_position in current_positions:
                candidate_positions = np.flatnonzero(np.isfinite(retrieval_score[current_position]))
                if not len(candidate_positions):
                    continue
                ordered = candidate_positions[
                    np.argsort(-retrieval_score[current_position, candidate_positions], kind="mergesort")
                ][:top_k]
                chosen_weight = retrieval_score[current_position, ordered]
                if chosen_weight.sum() <= 0:
                    continue
                global_position = positions[current_position]
                vote_arrays[layer_name][global_position] = float(
                    np.average(outcomes[ordered], weights=chosen_weight)
                )
                retrieved_arrays[layer_name][global_position] = len(ordered)

    votes = {
        name: pd.Series(value, index=frame.index, dtype="float64")
        for name, value in vote_arrays.items()
    }
    retrieved = {
        name: pd.Series(value, index=frame.index, dtype="int64")
        for name, value in retrieved_arrays.items()
    }

    common = frame["month"] >= common_start
    vote_frame = pd.DataFrame({name: value for name, value in votes.items()})
    ranked_votes = pd.concat([frame[["month"]], vote_frame], axis=1)
    ranked_votes = cross_sectional_unit_rank(ranked_votes, list(layers))
    current_fact = cross_sectional_unit_rank(frame, ["ret_1_0"])["ret_1_0"]
    risk = cross_sectional_unit_rank(frame, ["rvol_21d"])["rvol_21d"]
    market_rows = []
    for month, indices in frame.groupby("month", sort=True).groups.items():
        weight = pd.to_numeric(frame.loc[indices, "weight"], errors="coerce")
        current_return = pd.to_numeric(frame.loc[indices, "ret"], errors="coerce").fillna(0.0)
        market_rows.append((pd.Timestamp(month), float(np.sum(weight * current_return) / weight.sum())))
    market = pd.Series(dict(market_rows)).sort_index()
    trailing_market = (1.0 + market).rolling(3, min_periods=3).apply(np.prod, raw=True) - 1.0
    character = frame["month"].map(pd.Series(np.where(trailing_market >= 0, 1.0, -1.0), index=trailing_market.index))
    components = pd.concat([current_fact.rename("current_fact"), ranked_votes], axis=1)
    reflected = components.mean(axis=1, skipna=True)
    score = reflected + risk_adjustment_magnitude * character * risk
    score = score.where(common & components.notna().sum(axis=1).ge(2))
    diagnostics = []
    for month, indices in frame.loc[common].groupby("month", sort=True).groups.items():
        row: dict[str, object] = {
            "formation_month": str(pd.Timestamp(month).date()),
            "trailing_three_month_market_return": float(trailing_market.loc[pd.Timestamp(month)]),
            "risk_character": "risk_seeking" if character.loc[indices].iloc[0] > 0 else "risk_averse",
            "finite_scores": int(score.loc[indices].notna().sum()),
        }
        for layer_name in layers:
            row[f"{layer_name}_memory_coverage"] = int(votes[layer_name].loc[indices].notna().sum())
            row[f"{layer_name}_mean_retrieved"] = float(retrieved[layer_name].loc[indices].mean())
        diagnostics.append(row)
    return score, pd.DataFrame(diagnostics)


def alpha_gpt2_rolling_scores(
    frame: pd.DataFrame,
    seeds: list[str],
    risk_features: list[str],
    *,
    common_start: str,
    training_months: int = 60,
    minimum_rankic_months: int = 24,
    selected_factors: int = 5,
    ridge_penalty: float = 1.0,
    high_risk_quantile: float = 0.2,
    high_risk_multiplier: float = 0.5,
) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
    """Run a past-only Alpha-GPT 2.0 mining/modeling/analysis cycle."""
    missing = {"month", "ret_exc_lead1m", *seeds, *risk_features} - set(frame)
    if missing:
        raise ValueError(f"missing Alpha-GPT 2.0 inputs: {sorted(missing)}")
    if len(seeds) != 6 or len(set(seeds)) != 6:
        raise ValueError("Alpha-GPT 2.0 requires six unique mining seeds")
    if not 0 < high_risk_quantile < 0.5 or not 0 < high_risk_multiplier <= 1:
        raise ValueError("invalid Alpha-GPT 2.0 risk adjustment")
    oriented = frame.copy()
    oriented[seeds] = -oriented[seeds]
    candidates = fama_candidate_library(oriented, seeds)
    rankics = monthly_rankic(frame, candidates)
    risk_rank = cross_sectional_unit_rank(frame, risk_features)
    risk_raw = risk_rank[risk_features[0]] + risk_rank[risk_features[1]] - risk_rank[risk_features[2]]
    risk_frame = pd.DataFrame({"month": frame["month"], "risk": risk_raw}, index=frame.index)
    risk_score = cross_sectional_unit_rank(risk_frame, ["risk"])["risk"]
    high_risk_cutoff = 1.0 - 2.0 * high_risk_quantile

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    for month in months:
        history = rankics.loc[rankics.index < month].tail(training_months)
        if len(history) != training_months:
            raise ValueError(f"Alpha-GPT 2.0 warm-up is incomplete at {month.date()}")
        mean, quality = _rankicir(history, minimum_rankic_months)
        selected = sorted(
            quality.dropna().index,
            key=lambda name: (-float(quality[name]), name),
        )[:selected_factors]
        if len(selected) != selected_factors:
            raise ValueError("too few eligible Alpha-GPT 2.0 mined factors")
        training = frame["month"].isin(history.index)
        x = candidates.loc[training, selected].to_numpy(dtype=float)
        y = pd.to_numeric(frame.loc[training, "ret_exc_lead1m"], errors="coerce").to_numpy(dtype=float)
        valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
        x, y = x[valid], y[valid]
        if len(y) < 1000:
            raise ValueError("too few Alpha-GPT 2.0 modeling observations")
        design = np.column_stack([np.ones(len(x)), x])
        penalty = np.eye(design.shape[1]) * ridge_penalty
        penalty[0, 0] = 0.0
        model = np.linalg.solve(design.T @ design + penalty, design.T @ y)
        indices = month_groups[month]
        current_x = candidates.loc[indices, selected].to_numpy(dtype=float)
        current = np.full(len(indices), np.nan)
        current_valid = np.isfinite(current_x).all(axis=1)
        current[current_valid] = model[0] + current_x[current_valid] @ model[1:]
        current_risk = risk_score.loc[indices].to_numpy(dtype=float)
        analyzed = np.isfinite(current) & np.isfinite(current_risk) & (current_risk >= high_risk_cutoff)
        current[analyzed] *= high_risk_multiplier
        result.loc[indices] = current
        predicted = design @ model
        centered = y - y.mean()
        r2 = 1.0 - float(np.sum((y - predicted) ** 2) / np.sum(centered**2))
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "training_start": str(history.index[0].date()),
            "training_end": str(history.index[-1].date()),
            "training_months": len(history),
            "training_observations": len(y),
            "eligible_candidates": int(quality.notna().sum()),
            "selected_factors": len(selected),
            "model_r2": r2,
            "high_risk_count": int(analyzed.sum()),
            "finite_scores": int(np.isfinite(current).sum()),
        }
        for number, name in enumerate(selected, start=1):
            row[f"factor_{number}"] = name
            row[f"factor_{number}_rankicir"] = float(quality[name])
            row[f"factor_{number}_mean_rankic"] = float(mean[name])
            row[f"factor_{number}_coefficient"] = float(model[number])
        diagnostics.append(row)
    catalog = pd.DataFrame(
        {
            "candidate_id": candidates.columns,
            "operator": [name.split("__", 1)[0] for name in candidates.columns],
            "seed_orientation": "negative_mean_reversion",
        }
    )
    return result, pd.DataFrame(diagnostics), catalog


FINAGENT_MEMORY_QUERIES = {
    "short": (0.25, 0.75),
    "medium": (0.5, 0.5),
    "long": (0.75, 0.25),
}


def finagent_rolling_scores(
    frame: pd.DataFrame,
    *,
    common_start: str,
    memory_window_months: int = 60,
    top_k: int = 5,
    training_months: int = 60,
    ridge_penalty: float = 1.0,
    high_level_weight: float = 0.25,
    tool_weight: float = 0.25,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a numeric FinAgent multimodal-memory-reflection reconstruction."""
    primitives = [
        "be_me",
        "gp_at",
        "ocf_at",
        "ret_1_0",
        "turnover_126d",
        "ret_3_1",
        "ret_6_1",
        "ret_12_1",
        "rvol_21d",
        "prc_highprc_252d",
    ]
    missing = {"month", "security_id", "ret_exc_lead1m", *primitives} - set(frame)
    if missing:
        raise ValueError(f"missing FinAgent inputs: {sorted(missing)}")
    if top_k < 1 or high_level_weight + tool_weight >= 1:
        raise ValueError("invalid FinAgent memory or reflection weights")
    ranked = cross_sectional_unit_rank(frame, primitives)
    raw_modalities = pd.DataFrame(index=frame.index)
    raw_modalities["market_intelligence"] = ranked[
        ["be_me", "gp_at", "ocf_at", "ret_1_0", "turnover_126d"]
    ].mean(axis=1)
    raw_modalities["price_chart"] = pd.concat(
        [
            ranked["ret_1_0"],
            ranked["ret_3_1"],
            ranked["ret_6_1"],
            -ranked["rvol_21d"],
            ranked["prc_highprc_252d"],
        ],
        axis=1,
    ).mean(axis=1)
    modality_frame = pd.concat([frame[["month"]], raw_modalities], axis=1)
    modalities = cross_sectional_unit_rank(modality_frame, list(raw_modalities))

    memory_arrays = {name: np.full(len(frame), np.nan) for name in FINAGENT_MEMORY_QUERIES}
    retrieved_arrays = {name: np.zeros(len(frame), dtype=int) for name in FINAGENT_MEMORY_QUERIES}
    frame_months = pd.to_datetime(frame["month"])
    month_number = (frame_months.dt.year * 12 + frame_months.dt.month).to_numpy(dtype=int)
    outcomes_all = pd.to_numeric(frame["ret_exc_lead1m"], errors="coerce").to_numpy(dtype=float)
    for indices in frame.groupby("security_id", sort=False).groups.values():
        positions = frame.index.get_indexer(indices)
        positions = positions[np.argsort(month_number[positions], kind="mergesort")]
        months = month_number[positions]
        lag = months[:, None] - months[None, :]
        temporal = (lag >= 1) & (lag <= memory_window_months)
        outcomes = outcomes_all[positions]
        base_state = modalities.iloc[positions][["market_intelligence", "price_chart"]].to_numpy(dtype=float)
        for query, query_weights in FINAGENT_MEMORY_QUERIES.items():
            state = base_state * np.sqrt(np.asarray(query_weights))[None, :]
            valid_state = np.isfinite(state).all(axis=1)
            norms = np.linalg.norm(state, axis=1)
            denominator = norms[:, None] * norms[None, :]
            similarity = np.divide(
                state @ state.T,
                denominator,
                out=np.zeros_like(denominator),
                where=denominator > 0,
            )
            similarity = (np.clip(similarity, -1.0, 1.0) + 1.0) / 2.0
            eligible = temporal & valid_state[:, None] & valid_state[None, :] & np.isfinite(outcomes)[None, :]
            similarity = np.where(eligible, similarity, -np.inf)
            for current_position in range(len(positions)):
                candidates = np.flatnonzero(np.isfinite(similarity[current_position]))
                if not len(candidates):
                    continue
                chosen = candidates[
                    np.argsort(-similarity[current_position, candidates], kind="mergesort")
                ][:top_k]
                weights = similarity[current_position, chosen]
                if weights.sum() <= 0:
                    continue
                global_position = positions[current_position]
                memory_arrays[query][global_position] = float(np.average(outcomes[chosen], weights=weights))
                retrieved_arrays[query][global_position] = len(chosen)
    memories = pd.DataFrame(memory_arrays, index=frame.index)

    tool_candidates = pd.DataFrame(
        {
            "medium_term_momentum": ranked["ret_12_1"],
            "short_term_reversal": -ranked["ret_1_0"],
            "price_breakout": ranked["prc_highprc_252d"],
        },
        index=frame.index,
    )
    tool_rankics = monthly_rankic(frame, tool_candidates)
    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    low_level_columns = ["market_intelligence", "price_chart", *FINAGENT_MEMORY_QUERIES]
    low_level_inputs = pd.concat([modalities, memories], axis=1)[low_level_columns]
    for month in months:
        history = tool_rankics.loc[tool_rankics.index < month].tail(training_months)
        if len(history) != training_months:
            raise ValueError(f"FinAgent warm-up is incomplete at {month.date()}")
        training = frame["month"].isin(history.index)
        x = low_level_inputs.loc[training].to_numpy(dtype=float)
        y = pd.to_numeric(frame.loc[training, "ret_exc_lead1m"], errors="coerce").to_numpy(dtype=float)
        valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
        x, y = x[valid], y[valid]
        if len(y) < 1000:
            raise ValueError("too few finite FinAgent reflection observations")
        design = np.column_stack([np.ones(len(x)), x])
        penalty = np.eye(design.shape[1]) * ridge_penalty
        penalty[0, 0] = 0.0
        low_model = np.linalg.solve(design.T @ design + penalty, design.T @ y)
        tool_mean, tool_quality = _rankicir(history, 24)
        selected_tool = sorted(
            tool_quality.dropna().index,
            key=lambda name: (-float(tool_quality[name]), name),
        )[0]
        tool_orientation = 1.0 if tool_mean[selected_tool] > 0 else -1.0
        indices = month_groups[month]
        current_x = low_level_inputs.loc[indices].to_numpy(dtype=float)
        low_prediction = np.full(len(indices), np.nan)
        current_valid = np.isfinite(current_x).all(axis=1)
        low_prediction[current_valid] = low_model[0] + current_x[current_valid] @ low_model[1:]
        high_reflection = memories.loc[indices].mean(axis=1).to_numpy(dtype=float)
        tool_signal = tool_orientation * tool_candidates.loc[indices, selected_tool].to_numpy(dtype=float)
        component_frame = pd.DataFrame(
            {
                "month": month,
                "low": low_prediction,
                "high": high_reflection,
                "tool": tool_signal,
            },
            index=indices,
        )
        component_rank = cross_sectional_unit_rank(component_frame, ["low", "high", "tool"])
        current = (
            (1.0 - high_level_weight - tool_weight) * component_rank["low"]
            + high_level_weight * component_rank["high"]
            + tool_weight * component_rank["tool"]
        )
        result.loc[indices] = current
        predicted = design @ low_model
        centered = y - y.mean()
        r2 = 1.0 - float(np.sum((y - predicted) ** 2) / np.sum(centered**2))
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "training_start": str(history.index[0].date()),
            "training_end": str(history.index[-1].date()),
            "training_months": len(history),
            "training_observations": len(y),
            "low_level_r2": r2,
            "selected_tool": selected_tool,
            "selected_tool_rankicir": float(tool_quality[selected_tool]),
            "selected_tool_orientation": int(tool_orientation),
            "finite_scores": int(current.notna().sum()),
        }
        for query in FINAGENT_MEMORY_QUERIES:
            row[f"{query}_memory_coverage"] = int(memories.loc[indices, query].notna().sum())
            row[f"{query}_mean_retrieved"] = float(retrieved_arrays[query][frame.index.get_indexer(indices)].mean())
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def llmfactor_rolling_scores(
    frame: pd.DataFrame,
    factor_candidates: list[str],
    peer_features: list[str],
    peer_inputs: list[str],
    *,
    common_start: str,
    training_months: int = 60,
    selected_factors: int = 5,
    ridge_penalty: float = 1.0,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a numeric relation/factor/five-price LLMFactor reconstruction."""
    required = {
        "month",
        "security_id",
        "ret",
        "ret_exc_lead1m",
        *factor_candidates,
        *peer_features,
        *peer_inputs,
    }
    missing = required - set(frame)
    if missing:
        raise ValueError(f"missing LLMFactor inputs: {sorted(missing)}")
    if len(factor_candidates) != 8 or selected_factors != 5:
        raise ValueError("LLMFactor requires eight candidates and five selected factors")
    all_rank_features = list(dict.fromkeys([*factor_candidates, *peer_features, *peer_inputs]))
    ranked = cross_sectional_unit_rank(frame, all_rank_features)

    relation = pd.DataFrame(np.nan, index=frame.index, columns=[f"peer__{name}" for name in peer_inputs])
    relation_coverage: dict[pd.Timestamp, int] = {}
    for month, indices in frame.groupby("month", sort=True).groups.items():
        states = ranked.loc[indices, peer_features]
        valid = states.notna().all(axis=1)
        valid_indices = states.index[valid]
        if len(valid_indices) < 2:
            relation_coverage[pd.Timestamp(month)] = 0
            continue
        tree = cKDTree(states.loc[valid_indices].to_numpy(dtype=float))
        _, nearest = tree.query(states.loc[valid_indices].to_numpy(dtype=float), k=2)
        neighbor_indices = valid_indices.to_numpy()[nearest[:, 1]]
        relation.loc[valid_indices] = ranked.loc[neighbor_indices, peer_inputs].to_numpy(dtype=float)
        relation_coverage[pd.Timestamp(month)] = len(valid_indices)

    price_history = pd.DataFrame(index=frame.index)
    ordered = frame[["security_id", "month", "ret"]].sort_values(
        ["security_id", "month"], kind="mergesort"
    )
    groups = ordered.groupby("security_id", sort=False)
    for lag in range(5):
        values = pd.to_numeric(groups["ret"].shift(lag), errors="coerce")
        observed_month = groups["month"].shift(lag)
        expected_month = ordered["month"] - pd.offsets.MonthEnd(lag)
        price_history.loc[ordered.index, f"price_lag_{lag}"] = values.where(observed_month.eq(expected_month))
    price_rank_frame = pd.concat([frame[["month"]], price_history], axis=1)
    price_history = cross_sectional_unit_rank(price_rank_frame, list(price_history))

    factor_scores = ranked[factor_candidates]
    rankics = monthly_rankic(frame, factor_scores)
    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    for month in months:
        history = rankics.loc[rankics.index < month].tail(training_months)
        if len(history) != training_months:
            raise ValueError(f"LLMFactor warm-up is incomplete at {month.date()}")
        mean, quality = _rankicir(history, 24)
        selected = sorted(
            quality.dropna().index,
            key=lambda name: (-float(quality[name]), name),
        )[:selected_factors]
        if len(selected) != selected_factors:
            raise ValueError("too few LLMFactor factor candidates")
        prediction_inputs = pd.concat(
            [
                factor_scores[selected],
                relation,
                price_history,
            ],
            axis=1,
        )
        training = frame["month"].isin(history.index)
        x = prediction_inputs.loc[training].to_numpy(dtype=float)
        realized = pd.to_numeric(frame.loc[training, "ret_exc_lead1m"], errors="coerce").to_numpy(dtype=float)
        y = np.sign(realized)
        valid = np.isfinite(x).all(axis=1) & np.isfinite(realized) & (y != 0)
        x, y = x[valid], y[valid]
        if len(y) < 1000:
            raise ValueError("too few finite LLMFactor classification observations")
        design = np.column_stack([np.ones(len(x)), x])
        penalty = np.eye(design.shape[1]) * ridge_penalty
        penalty[0, 0] = 0.0
        model = np.linalg.solve(design.T @ design + penalty, design.T @ y)
        indices = month_groups[month]
        current_x = prediction_inputs.loc[indices].to_numpy(dtype=float)
        current = np.full(len(indices), np.nan)
        current_valid = np.isfinite(current_x).all(axis=1)
        current[current_valid] = model[0] + current_x[current_valid] @ model[1:]
        result.loc[indices] = current
        predicted = design @ model
        accuracy = float(np.mean(np.sign(predicted) == y))
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "training_start": str(history.index[0].date()),
            "training_end": str(history.index[-1].date()),
            "training_months": len(history),
            "training_observations": len(y),
            "training_direction_accuracy": accuracy,
            "peer_relation_coverage": relation_coverage[month],
            "five_price_history_coverage": int(price_history.loc[indices].notna().all(axis=1).sum()),
            "finite_scores": int(np.isfinite(current).sum()),
        }
        for number, name in enumerate(selected, start=1):
            row[f"factor_{number}"] = name
            row[f"factor_{number}_rankicir"] = float(quality[name])
            row[f"factor_{number}_mean_rankic"] = float(mean[name])
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def fincon_rolling_scores(
    frame: pd.DataFrame,
    analysts: dict[str, list[str]],
    *,
    common_start: str,
    procedural_memory_months: int = 60,
    minimum_rankic_months: int = 24,
    belief_learning_rate: float = 0.25,
    cvar_history_months: int = 60,
    cvar_tail_probability: float = 0.05,
    cvar_penalty: float = 0.5,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a numerical FinCon manager/analyst and dual-risk-control policy."""
    if list(analysts) != ["market", "fundamental", "attention", "risk"]:
        raise ValueError("FinCon requires the frozen four analyst roles")
    features = list(dict.fromkeys(feature for values in analysts.values() for feature in values))
    missing = {"month", "security_id", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing FinCon analyst inputs: {sorted(missing)}")
    if not 0 < belief_learning_rate <= 1 or not 0 < cvar_tail_probability <= 0.5:
        raise ValueError("invalid FinCon belief or CVaR parameter")
    ranked = cross_sectional_unit_rank(frame, features)
    raw_analysts = pd.DataFrame(index=frame.index)
    raw_analysts["market"] = (
        ranked["ret_12_1"] + ranked["ret_6_1"] - ranked["rvol_21d"]
    ) / 3.0
    raw_analysts["fundamental"] = ranked[
        ["be_me", "gp_at", "ocf_at", "f_score"]
    ].mean(axis=1)
    raw_analysts["attention"] = ranked[
        ["ret_1_0", "rmax5_21d", "turnover_126d"]
    ].mean(axis=1)
    raw_analysts["risk"] = (
        ranked["z_score"] - ranked["o_score"] - ranked["rvol_21d"]
    ) / 3.0
    analyst_frame = pd.concat([frame[["month"]], raw_analysts], axis=1)
    analyst_scores = cross_sectional_unit_rank(analyst_frame, list(analysts))
    rankics = monthly_rankic(frame, analyst_scores)

    cvar = pd.Series(np.nan, index=frame.index, dtype="float64")
    outcomes_all = pd.to_numeric(frame["ret_exc_lead1m"], errors="coerce").to_numpy(dtype=float)
    frame_months = pd.to_datetime(frame["month"])
    month_number = (frame_months.dt.year * 12 + frame_months.dt.month).to_numpy(dtype=int)
    for indices in frame.groupby("security_id", sort=False).groups.values():
        positions = frame.index.get_indexer(indices)
        positions = positions[np.argsort(month_number[positions], kind="mergesort")]
        months = month_number[positions]
        outcomes = outcomes_all[positions]
        for current_position in range(len(positions)):
            lag = months[current_position] - months[:current_position]
            history_positions = np.flatnonzero((lag >= 1) & (lag <= cvar_history_months))
            values = outcomes[history_positions]
            values = values[np.isfinite(values)]
            if len(values) < minimum_rankic_months:
                continue
            tail_count = max(1, int(np.ceil(cvar_tail_probability * len(values))))
            cvar.iloc[positions[current_position]] = float(np.sort(values)[:tail_count].mean())
    cvar_frame = pd.DataFrame({"month": frame["month"], "cvar": cvar}, index=frame.index)
    cvar_rank = cross_sectional_unit_rank(cvar_frame, ["cvar"])["cvar"]

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    beliefs = pd.Series(0.25, index=list(analysts), dtype="float64")
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    previous_cvar = pd.Series(dtype="float64")
    for month in months:
        history = rankics.loc[rankics.index < month].tail(procedural_memory_months)
        if len(history) != procedural_memory_months:
            raise ValueError(f"FinCon warm-up is incomplete at {month.date()}")
        count = history.count()
        mean = history.mean().where(count >= minimum_rankic_months)
        if mean.isna().any():
            raise ValueError("FinCon analyst history is incomplete")
        logits = mean - mean.max()
        target_beliefs = np.exp(logits)
        target_beliefs /= target_beliefs.sum()
        beliefs = (1.0 - belief_learning_rate) * beliefs + belief_learning_rate * target_beliefs
        beliefs /= beliefs.sum()
        indices = month_groups[month]
        manager = analyst_scores.loc[indices].mul(beliefs, axis=1).sum(axis=1, min_count=len(analysts))
        current_cvar = cvar.loc[indices]
        current_cvar_rank = cvar_rank.loc[indices]
        score = manager + cvar_penalty * current_cvar_rank
        score = score.where(manager.notna() & current_cvar.notna())
        result.loc[indices] = score
        current_by_security = pd.Series(
            current_cvar.to_numpy(),
            index=frame.loc[indices, "security_id"].to_numpy(),
        )
        prior = frame.loc[indices, "security_id"].map(previous_cvar)
        alerts = current_cvar.notna() & prior.notna() & current_cvar.lt(prior.to_numpy())
        previous_cvar = current_by_security
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "procedural_start": str(history.index[0].date()),
            "procedural_end": str(history.index[-1].date()),
            "procedural_months": len(history),
            "cvar_coverage": int(current_cvar.notna().sum()),
            "cvar_alerts": int(alerts.sum()),
            "finite_scores": int(score.notna().sum()),
        }
        for name in analysts:
            row[f"analyst_rankic__{name}"] = float(mean[name])
            row[f"belief_weight__{name}"] = float(beliefs[name])
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def aapm_rolling_scores(
    frame: pd.DataFrame,
    stock_report_features: list[str],
    manual_factors: list[str],
    asset_features: list[str],
    *,
    common_start: str,
    report_memory_weight: float = 0.5,
    pretraining_months: int = 120,
    ridge_penalty: float = 10.0,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a hybrid AAPM report/manual/asset pricing reconstruction."""
    if [len(stock_report_features), len(manual_factors), len(asset_features)] != [5, 6, 3]:
        raise ValueError("AAPM requires frozen 5/6/3 feature blocks")
    if not 0 <= report_memory_weight < 1:
        raise ValueError("AAPM report-memory weight must be in [0, 1)")
    features = list(dict.fromkeys([*stock_report_features, *manual_factors, *asset_features]))
    missing = {"month", "security_id", "weight", "ret", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing AAPM inputs: {sorted(missing)}")
    ranked = cross_sectional_unit_rank(frame, features)

    smoothed_report = pd.DataFrame(np.nan, index=frame.index, columns=stock_report_features)
    month_number = (
        pd.to_datetime(frame["month"]).dt.year * 12
        + pd.to_datetime(frame["month"]).dt.month
    ).to_numpy(dtype=int)
    for indices in frame.groupby("security_id", sort=False).groups.values():
        positions = frame.index.get_indexer(indices)
        positions = positions[np.argsort(month_number[positions], kind="mergesort")]
        previous = np.full(len(stock_report_features), np.nan)
        previous_month: int | None = None
        for position in positions:
            current = ranked.iloc[position][stock_report_features].to_numpy(dtype=float)
            if (
                previous_month is not None
                and month_number[position] == previous_month + 1
                and np.isfinite(previous).all()
                and np.isfinite(current).all()
            ):
                current = (
                    (1.0 - report_memory_weight) * current
                    + report_memory_weight * previous
                )
            smoothed_report.iloc[position] = current
            previous = current
            previous_month = month_number[position]

    macro_rows = []
    previous_macro = np.zeros(3)
    for month, indices in frame.groupby("month", sort=True).groups.items():
        weight = pd.to_numeric(frame.loc[indices, "weight"], errors="coerce")
        current_return = pd.to_numeric(frame.loc[indices, "ret"], errors="coerce")
        valid = weight.notna() & current_return.notna() & weight.gt(0)
        normalized = weight.loc[valid] / weight.loc[valid].sum()
        market_return = float(np.sum(normalized * current_return.loc[valid]))
        market_volatility = float(
            np.sqrt(np.sum(normalized * (current_return.loc[valid] - market_return) ** 2))
        )
        breadth = float(current_return.loc[valid].gt(0).mean())
        current_macro = np.array([market_return, market_volatility, breadth])
        current_macro = (
            (1.0 - report_memory_weight) * current_macro
            + report_memory_weight * previous_macro
        )
        previous_macro = current_macro
        macro_rows.append((pd.Timestamp(month), current_macro.copy()))
    macro_by_month = dict(macro_rows)
    macro = np.vstack([macro_by_month[pd.Timestamp(month)] for month in frame["month"]])

    stock_mean = smoothed_report.mean(axis=1).to_numpy(dtype=float)
    manual = ranked[manual_factors].to_numpy(dtype=float)
    asset = ranked[asset_features].to_numpy(dtype=float)
    interactions = np.column_stack(
        [
            np.tanh(stock_mean[:, None] * macro),
            np.tanh(asset * manual[:, :3]),
        ]
    )
    hybrid = np.column_stack([smoothed_report.to_numpy(dtype=float), macro, manual, asset, interactions])
    hybrid_columns = [
        *[f"report__{name}" for name in stock_report_features],
        "macro__market_return",
        "macro__market_volatility",
        "macro__positive_breadth",
        *[f"manual__{name}" for name in manual_factors],
        *[f"asset__{name}" for name in asset_features],
        "interaction__report_market_return",
        "interaction__report_market_volatility",
        "interaction__report_positive_breadth",
        *[f"interaction__asset_manual_{number}" for number in range(1, 4)],
    ]
    if hybrid.shape[1] != len(hybrid_columns):
        raise AssertionError("AAPM hybrid feature names do not align")

    outcomes = pd.to_numeric(frame["ret_exc_lead1m"], errors="coerce").to_numpy(dtype=float)
    month_cross_products: dict[pd.Timestamp, tuple[np.ndarray, np.ndarray, int]] = {}
    for month, indices in frame.groupby("month", sort=True).groups.items():
        positions = frame.index.get_indexer(indices)
        x = hybrid[positions]
        y = outcomes[positions]
        valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
        design = np.column_stack([np.ones(valid.sum()), x[valid]])
        month_cross_products[pd.Timestamp(month)] = (
            design.T @ design,
            design.T @ y[valid],
            int(valid.sum()),
        )

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    all_months = sorted(month_cross_products)
    for month in months:
        history_months = [value for value in all_months if value < month][-pretraining_months:]
        if len(history_months) != pretraining_months:
            raise ValueError(f"AAPM pretraining is incomplete at {month.date()}")
        xtx = sum((month_cross_products[value][0] for value in history_months), np.zeros_like(next(iter(month_cross_products.values()))[0]))
        xty = sum((month_cross_products[value][1] for value in history_months), np.zeros_like(next(iter(month_cross_products.values()))[1]))
        observations = sum(month_cross_products[value][2] for value in history_months)
        penalty = np.eye(xtx.shape[0]) * ridge_penalty
        penalty[0, 0] = 0.0
        model = np.linalg.solve(xtx + penalty, xty)
        indices = month_groups[month]
        positions = frame.index.get_indexer(indices)
        current_x = hybrid[positions]
        current = np.full(len(indices), np.nan)
        valid = np.isfinite(current_x).all(axis=1)
        current[valid] = model[0] + current_x[valid] @ model[1:]
        result.loc[indices] = current
        diagnostics.append(
            {
                "formation_month": str(month.date()),
                "pretraining_start": str(history_months[0].date()),
                "pretraining_end": str(history_months[-1].date()),
                "pretraining_months": len(history_months),
                "pretraining_observations": observations,
                "hybrid_feature_count": hybrid.shape[1],
                "stock_report_coverage": int(smoothed_report.loc[indices].notna().all(axis=1).sum()),
                "finite_scores": int(np.isfinite(current).sum()),
                "coefficient_norm": float(np.linalg.norm(model[1:])),
            }
        )
    catalog = pd.DataFrame({"feature": hybrid_columns})
    return result, pd.DataFrame(diagnostics), catalog


def finvision_consensus_scores(
    frame: pd.DataFrame,
    *,
    common_start: str,
    reliability_months: int = 60,
    minimum_rankic_months: int = 24,
    softmax_temperature: float = 10.0,
    hold_threshold: float = 0.1,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a numerical FinVision news/chart/reflection consensus."""
    features = [
        "niq_su",
        "saleq_su",
        "ret_1_0",
        "turnover_126d",
        "ret_3_1",
        "ret_6_1",
        "prc_highprc_252d",
        "rvol_21d",
    ]
    missing = {"month", "security_id", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing FinVision agent inputs: {sorted(missing)}")
    if reliability_months < minimum_rankic_months or softmax_temperature <= 0:
        raise ValueError("invalid FinVision reliability configuration")
    ranked = cross_sectional_unit_rank(frame, features)
    agents = pd.DataFrame(index=frame.index)
    agents["news_summary"] = ranked[
        ["niq_su", "saleq_su", "ret_1_0", "turnover_126d"]
    ].mean(axis=1)
    agents["technical_chart"] = pd.concat(
        [
            ranked["ret_3_1"],
            ranked["ret_6_1"],
            ranked["prc_highprc_252d"],
            -ranked["rvol_21d"],
        ],
        axis=1,
    ).mean(axis=1)

    short = pd.Series(np.nan, index=frame.index, dtype="float64")
    medium = pd.Series(np.nan, index=frame.index, dtype="float64")
    outcomes_all = pd.to_numeric(frame["ret_exc_lead1m"], errors="coerce").to_numpy(dtype=float)
    frame_months = pd.to_datetime(frame["month"])
    month_number = (frame_months.dt.year * 12 + frame_months.dt.month).to_numpy(dtype=int)
    for indices in frame.groupby("security_id", sort=False).groups.values():
        positions = frame.index.get_indexer(indices)
        positions = positions[np.argsort(month_number[positions], kind="mergesort")]
        months = month_number[positions]
        outcomes = outcomes_all[positions]
        for current_position, global_position in enumerate(positions):
            lag = months[current_position] - months[:current_position]
            for horizon, destination in ((3, short), (12, medium)):
                history_positions = np.flatnonzero((lag >= 1) & (lag <= horizon))
                values = outcomes[history_positions]
                values = values[np.isfinite(values)]
                if len(values):
                    destination.iloc[global_position] = float(values.mean())
    reflection_frame = pd.DataFrame(
        {"month": frame["month"], "short_reflection": short, "medium_reflection": medium},
        index=frame.index,
    )
    reflection_rank = cross_sectional_unit_rank(
        reflection_frame, ["short_reflection", "medium_reflection"]
    )
    agents = pd.concat([agents, reflection_rank], axis=1)
    agents = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], agents], axis=1), list(agents)
    )
    rankics = monthly_rankic(frame, agents)

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    for month in months:
        history = rankics.loc[rankics.index < month].tail(reliability_months)
        if len(history) != reliability_months:
            raise ValueError(f"FinVision reliability history is incomplete at {month.date()}")
        count = history.count()
        mean = history.mean().where(count >= minimum_rankic_months)
        if mean.isna().any():
            raise ValueError("FinVision agent RankIC history is incomplete")
        logits = softmax_temperature * mean
        reliability = np.exp(logits - logits.max())
        reliability /= reliability.sum()
        indices = month_groups[month]
        consensus = agents.loc[indices].mul(reliability, axis=1).sum(
            axis=1, min_count=len(agents.columns)
        )
        result.loc[indices] = consensus
        finite = consensus.dropna()
        position_size = np.ceil(10.0 * finite.abs()).clip(1, 10)
        hold = finite.abs() <= hold_threshold
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "reliability_start": str(history.index[0].date()),
            "reliability_end": str(history.index[-1].date()),
            "reliability_months": len(history),
            "finite_scores": len(finite),
            "buy_count": int((finite > hold_threshold).sum()),
            "sell_count": int((finite < -hold_threshold).sum()),
            "hold_count": int(hold.sum()),
            "average_active_position_size": float(position_size.loc[~hold].mean()),
        }
        for name in agents:
            row[f"agent_rankic__{name}"] = float(mean[name])
            row[f"reliability_weight__{name}"] = float(reliability[name])
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def tradingagents_debate_scores(
    frame: pd.DataFrame,
    analysts: dict[str, list[str]],
    *,
    common_start: str,
    reflection_months: int = 60,
    minimum_rankic_months: int = 24,
    softmax_temperature: float = 10.0,
    risk_multipliers: dict[str, float] | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a numerical TradingAgents analyst/debate/risk/manager graph."""
    if list(analysts) != ["market", "social", "news", "fundamental"]:
        raise ValueError("TradingAgents requires the frozen analyst roles")
    risk_multipliers = risk_multipliers or {
        "risk_seeking": 1.25,
        "neutral": 1.0,
        "conservative": 0.75,
    }
    if risk_multipliers != {"risk_seeking": 1.25, "neutral": 1.0, "conservative": 0.75}:
        raise ValueError("TradingAgents risk proposals differ from the frozen recipe")
    features = list(dict.fromkeys(feature for values in analysts.values() for feature in values))
    missing = {"month", "weight", "ret", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing TradingAgents inputs: {sorted(missing)}")
    ranked = cross_sectional_unit_rank(frame, features)
    raw = pd.DataFrame(index=frame.index)
    raw["market"] = pd.concat(
        [ranked["ret_12_1"], ranked["ret_6_1"], ranked["prc_highprc_252d"], -ranked["rvol_21d"]],
        axis=1,
    ).mean(axis=1)
    raw["social"] = ranked[["ret_1_0", "rmax5_21d", "turnover_126d"]].mean(axis=1)
    raw["news"] = ranked[["niq_su", "saleq_su", "ret_1_0"]].mean(axis=1)
    raw["fundamental"] = pd.concat(
        [ranked["be_me"], ranked["gp_at"], ranked["ocf_at"], ranked["f_score"], -ranked["o_score"]],
        axis=1,
    ).mean(axis=1)
    analyst_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], raw], axis=1), list(raw)
    )
    rankics = monthly_rankic(frame, analyst_scores)
    security_risk = cross_sectional_unit_rank(frame, ["rvol_21d"])["rvol_21d"]

    market_volatility = {}
    for month, indices in frame.groupby("month", sort=True).groups.items():
        weight = pd.to_numeric(frame.loc[indices, "weight"], errors="coerce")
        current_return = pd.to_numeric(frame.loc[indices, "ret"], errors="coerce")
        valid = weight.notna() & current_return.notna() & weight.gt(0)
        normalized = weight.loc[valid] / weight.loc[valid].sum()
        center = float(np.sum(normalized * current_return.loc[valid]))
        market_volatility[pd.Timestamp(month)] = float(
            np.sqrt(np.sum(normalized * (current_return.loc[valid] - center) ** 2))
        )
    volatility = pd.Series(market_volatility).sort_index()
    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    for month in months:
        history = rankics.loc[rankics.index < month].tail(reflection_months)
        if len(history) != reflection_months:
            raise ValueError(f"TradingAgents reflection history is incomplete at {month.date()}")
        count = history.count()
        mean = history.mean().where(count >= minimum_rankic_months)
        if mean.isna().any():
            raise ValueError("TradingAgents analyst history is incomplete")
        logits = softmax_temperature * mean
        reliability = np.exp(logits - logits.max())
        reliability /= reliability.sum()
        trailing_volatility = volatility.loc[volatility.index <= month].tail(reflection_months)
        lower, upper = trailing_volatility.quantile([1 / 3, 2 / 3])
        current_volatility = volatility.loc[month]
        risk_choice = (
            "risk_seeking"
            if current_volatility <= lower
            else "conservative"
            if current_volatility >= upper
            else "neutral"
        )
        indices = month_groups[month]
        weighted = analyst_scores.loc[indices].mul(reliability, axis=1)
        bull_case = weighted.clip(lower=0).sum(axis=1, min_count=len(analysts))
        bear_case = weighted.clip(upper=0).sum(axis=1, min_count=len(analysts))
        trader = bull_case + bear_case
        manager = trader + (risk_multipliers[risk_choice] - 1.0) * security_risk.loc[indices]
        manager = manager.where(trader.notna() & security_risk.loc[indices].notna())
        result.loc[indices] = manager
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "reflection_start": str(history.index[0].date()),
            "reflection_end": str(history.index[-1].date()),
            "reflection_months": len(history),
            "market_volatility": current_volatility,
            "risk_choice": risk_choice,
            "risk_multiplier": risk_multipliers[risk_choice],
            "mean_bull_case": float(bull_case.mean()),
            "mean_bear_case": float(bear_case.mean()),
            "finite_scores": int(manager.notna().sum()),
        }
        for name in analysts:
            row[f"analyst_rankic__{name}"] = float(mean[name])
            row[f"reliability_weight__{name}"] = float(reliability[name])
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def marketsenseai_signal_scores(
    frame: pd.DataFrame,
    specialists: dict[str, list[str]],
    *,
    common_start: str,
    reliability_months: int = 60,
    minimum_rankic_months: int = 24,
    softmax_temperature: float = 10.0,
    buy_threshold: float = 0.1,
    sell_threshold: float = -0.1,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a numerical MarketSenseAI four-specialist signal agent."""
    if list(specialists) != ["news", "fundamentals", "dynamics", "macro"]:
        raise ValueError("MarketSenseAI requires the frozen specialist roles")
    if buy_threshold <= sell_threshold or softmax_temperature <= 0:
        raise ValueError("invalid MarketSenseAI signal configuration")
    features = list(
        dict.fromkeys(
            feature
            for name, values in specialists.items()
            for feature in values
            if name != "macro" and feature not in {"ret", "weight"}
        )
    )
    features.extend(
        feature
        for feature in specialists["macro"]
        if feature not in {"ret", "weight"} and feature not in features
    )
    missing = {"month", "weight", "ret", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing MarketSenseAI inputs: {sorted(missing)}")
    ranked = cross_sectional_unit_rank(frame, features)
    raw = pd.DataFrame(index=frame.index)
    raw["news"] = ranked[["niq_su", "saleq_su", "ret_1_0", "turnover_126d"]].mean(axis=1)
    raw["fundamentals"] = pd.concat(
        [ranked["be_me"], ranked["gp_at"], ranked["ocf_at"], ranked["f_score"], -ranked["o_score"]],
        axis=1,
    ).mean(axis=1)
    raw["dynamics"] = pd.concat(
        [
            ranked["ret_12_1"],
            ranked["ret_6_1"],
            ranked["prc_highprc_252d"],
            -ranked["rvol_21d"],
            ranked["beta_60m"],
        ],
        axis=1,
    ).mean(axis=1)
    market_rows = []
    for month, indices in frame.groupby("month", sort=True).groups.items():
        weight = pd.to_numeric(frame.loc[indices, "weight"], errors="coerce")
        current_return = pd.to_numeric(frame.loc[indices, "ret"], errors="coerce").fillna(0.0)
        market_rows.append((pd.Timestamp(month), float(np.sum(weight * current_return) / weight.sum())))
    market = pd.Series(dict(market_rows)).sort_index().rolling(6, min_periods=1).mean()
    regime = frame["month"].map(np.sign(market).replace(0.0, 1.0))
    raw["macro"] = regime.to_numpy() * ranked["beta_60m"] - ranked["rvol_21d"]
    scores = cross_sectional_unit_rank(pd.concat([frame[["month"]], raw], axis=1), list(raw))
    rankics = monthly_rankic(frame, scores)

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    for month in months:
        history = rankics.loc[rankics.index < month].tail(reliability_months)
        if len(history) != reliability_months:
            raise ValueError(f"MarketSenseAI reliability history is incomplete at {month.date()}")
        count = history.count()
        mean = history.mean().where(count >= minimum_rankic_months)
        if mean.isna().any():
            raise ValueError("MarketSenseAI specialist history is incomplete")
        logits = softmax_temperature * mean
        reliability = np.exp(logits - logits.max())
        reliability /= reliability.sum()
        indices = month_groups[month]
        signal = scores.loc[indices].mul(reliability, axis=1).sum(
            axis=1, min_count=len(scores.columns)
        )
        result.loc[indices] = signal
        finite = signal.dropna()
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "reliability_start": str(history.index[0].date()),
            "reliability_end": str(history.index[-1].date()),
            "reliability_months": len(history),
            "finite_scores": len(finite),
            "buy_count": int((finite > buy_threshold).sum()),
            "sell_count": int((finite < sell_threshold).sum()),
            "hold_count": int(finite.between(sell_threshold, buy_threshold, inclusive="both").sum()),
        }
        for name in specialists:
            row[f"specialist_rankic__{name}"] = float(mean[name])
            row[f"reliability_weight__{name}"] = float(reliability[name])
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def hedgeagents_conference_scores(
    frame: pd.DataFrame,
    specialists: dict[str, list[str]],
    *,
    common_start: str,
    history_months: int = 60,
    minimum_rankic_months: int = 24,
    cvar_tail_probability: float = 0.05,
    variance_penalty: float = 0.5,
    cvar_penalty: float = 0.5,
    experience_sharing_weight: float = 0.1,
    extreme_one_month_threshold: float = 0.05,
    extreme_three_month_threshold: float = 0.1,
    extreme_defensive_minimum_weight: float = 0.5,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a HedgeAgents-style specialist allocation conference on U.S. sleeves."""
    if list(specialists) != ["speculative", "equity", "defensive"]:
        raise ValueError("HedgeAgents requires speculative, equity, and defensive sleeves")
    if not 0 <= experience_sharing_weight < 1 or not 0 < cvar_tail_probability <= 0.5:
        raise ValueError("invalid HedgeAgents conference parameters")
    features = list(dict.fromkeys(feature for values in specialists.values() for feature in values))
    missing = {"month", "weight", "ret", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing HedgeAgents specialist inputs: {sorted(missing)}")
    ranked = cross_sectional_unit_rank(frame, features)
    raw = pd.DataFrame(index=frame.index)
    raw["speculative"] = pd.concat(
        [ranked["beta_60m"], ranked["rvol_21d"], ranked["ret_12_1"], -ranked["at_me"]],
        axis=1,
    ).mean(axis=1)
    raw["equity"] = ranked[["ret_12_1", "ret_6_1", "be_me", "gp_at", "f_score"]].mean(axis=1)
    raw["defensive"] = pd.concat(
        [
            ranked["z_score"],
            ranked["qmj_safety"],
            ranked["qmj_prof"],
            -ranked["rvol_21d"],
            -ranked["beta_60m"],
        ],
        axis=1,
    ).mean(axis=1)
    sleeve_scores = cross_sectional_unit_rank(pd.concat([frame[["month"]], raw], axis=1), list(raw))
    rankics = monthly_rankic(frame, sleeve_scores)

    market_rows = []
    for month, indices in frame.groupby("month", sort=True).groups.items():
        weight = pd.to_numeric(frame.loc[indices, "weight"], errors="coerce")
        current_return = pd.to_numeric(frame.loc[indices, "ret"], errors="coerce").fillna(0.0)
        market_rows.append((pd.Timestamp(month), float(np.sum(weight * current_return) / weight.sum())))
    market = pd.Series(dict(market_rows)).sort_index()
    market_three = (1.0 + market).rolling(3, min_periods=3).apply(np.prod, raw=True) - 1.0

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    for month in months:
        history = rankics.loc[rankics.index < month].tail(history_months)
        if len(history) != history_months:
            raise ValueError(f"HedgeAgents conference history is incomplete at {month.date()}")
        if (history.count() < minimum_rankic_months).any():
            raise ValueError("HedgeAgents specialist history is incomplete")
        mean = history.mean().to_numpy(dtype=float)
        covariance = history.cov().to_numpy(dtype=float)
        tail_count = max(1, int(np.ceil(cvar_tail_probability * len(history))))
        cvar = np.sort(history.to_numpy(dtype=float), axis=0)[:tail_count].mean(axis=0)
        adjusted_mean = mean - cvar_penalty * np.abs(cvar)
        utility = np.linalg.solve(
            covariance + variance_penalty * np.eye(len(specialists)),
            adjusted_mean,
        )
        allocation = np.exp(utility - utility.max())
        allocation /= allocation.sum()
        allocation = (
            (1.0 - experience_sharing_weight) * allocation
            + experience_sharing_weight / len(specialists)
        )
        extreme = bool(
            abs(market.loc[month]) > extreme_one_month_threshold
            or abs(market_three.loc[month]) > extreme_three_month_threshold
        )
        defensive_index = list(specialists).index("defensive")
        if extreme and allocation[defensive_index] < extreme_defensive_minimum_weight:
            other = [index for index in range(len(allocation)) if index != defensive_index]
            scale = (1.0 - extreme_defensive_minimum_weight) / allocation[other].sum()
            allocation[other] *= scale
            allocation[defensive_index] = extreme_defensive_minimum_weight
        indices = month_groups[month]
        weights = pd.Series(allocation, index=list(specialists))
        score = sleeve_scores.loc[indices].mul(weights, axis=1).sum(
            axis=1, min_count=len(specialists)
        )
        result.loc[indices] = score
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "conference_start": str(history.index[0].date()),
            "conference_end": str(history.index[-1].date()),
            "conference_months": len(history),
            "market_return": float(market.loc[month]),
            "three_month_market_return": float(market_three.loc[month]),
            "extreme_conference": extreme,
            "finite_scores": int(score.notna().sum()),
        }
        for position, name in enumerate(specialists):
            row[f"mean_rankic__{name}"] = float(mean[position])
            row[f"cvar__{name}"] = float(cvar[position])
            row[f"allocation__{name}"] = float(allocation[position])
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def mass_simulation_scores(
    frame: pd.DataFrame,
    investor_features: list[str],
    *,
    common_start: str,
    agents_per_type: int = 32,
    candidate_pool_size: int = 20,
    selections_per_agent: int = 5,
    aggregation_alpha: float = 0.5,
    history_months: int = 60,
    minimum_rankic_months: int = 24,
    annealing_initial_temperature: float = 40.0,
    annealing_iterations: int = 100,
    annealing_cooling: float = 0.95,
    objective_scale: float = 1000.0,
    risk_penalty: float = 0.5,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a deterministic heterogeneous-agent MASS simulation."""
    if len(investor_features) != 16 or len(set(investor_features)) != 16:
        raise ValueError("MASS requires 16 unique investor types")
    if [agents_per_type, candidate_pool_size, selections_per_agent] != [32, 20, 5]:
        raise ValueError("MASS agent and candidate-pool cardinalities changed")
    missing = {"month", "security_id", "ret_exc_lead1m", *investor_features} - set(frame)
    if missing:
        raise ValueError(f"missing MASS investor inputs: {sorted(missing)}")
    base_types = cross_sectional_unit_rank(frame, investor_features)
    type_signals = pd.DataFrame(np.nan, index=frame.index, columns=investor_features)
    month_groups = frame.groupby("month", sort=False).groups
    for month, indices in frame.groupby("month", sort=True).groups.items():
        ordered_indices = frame.loc[indices].sort_values("security_id", kind="mergesort").index.to_numpy()
        n = len(ordered_indices)
        if n < candidate_pool_size:
            raise ValueError("MASS candidate universe is smaller than 20 stocks")
        month_code = pd.Timestamp(month).year * 12 + pd.Timestamp(month).month
        for type_number, feature in enumerate(investor_features):
            values = base_types.loc[ordered_indices, feature].to_numpy(dtype=float)
            votes = np.zeros(n)
            for agent in range(agents_per_type):
                start = (month_code * 13 + type_number * 17 + agent * 31) % n
                pool = (start + np.arange(candidate_pool_size) * 37) % n
                pool_values = values[pool]
                valid = np.isfinite(pool_values)
                if valid.sum() < selections_per_agent:
                    continue
                candidates = pool[valid]
                selected = candidates[
                    np.argsort(-values[candidates], kind="mergesort")[:selections_per_agent]
                ]
                votes[selected] += 1.0
            vote_frame = pd.DataFrame({"month": month, "vote": votes}, index=ordered_indices)
            type_signals.loc[ordered_indices, feature] = cross_sectional_unit_rank(
                vote_frame, ["vote"]
            )["vote"]
    rankics = monthly_rankic(frame, type_signals)

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    months = sorted(pd.Timestamp(month) for month in frame.loc[frame["month"] >= common_start, "month"].unique())
    for month in months:
        history = rankics.loc[rankics.index < month].tail(history_months)
        if len(history) != history_months or (history.count() < minimum_rankic_months).any():
            raise ValueError(f"MASS annealing history is incomplete at {month.date()}")
        signs = np.where(history.mean().to_numpy(dtype=float) >= 0, 1.0, -1.0)
        oriented_history = history.to_numpy(dtype=float) * signs
        mean = oriented_history.mean(axis=0)
        covariance = np.cov(oriented_history, rowvar=False, ddof=1)
        tail_count = max(1, int(np.ceil(0.05 * len(history))))
        cvar = np.sort(oriented_history, axis=0)[:tail_count].mean(axis=0)

        def objective(weights: np.ndarray) -> float:
            expected = float(weights @ mean)
            variance = float(weights @ covariance @ weights)
            downside = float(abs(weights @ cvar))
            return expected - risk_penalty * variance - risk_penalty * downside

        rng = np.random.default_rng(month.year * 100 + month.month)
        allocation = np.full(len(investor_features), 1.0 / len(investor_features))
        current_objective = objective(allocation)
        accepted = 0
        temperature = annealing_initial_temperature
        for _ in range(annealing_iterations):
            source, target = rng.choice(len(allocation), size=2, replace=False)
            amount = min(float(allocation[source]), float(rng.uniform(0.0, 0.1)))
            proposal = allocation.copy()
            proposal[source] -= amount
            proposal[target] += amount
            proposed_objective = objective(proposal)
            improvement = proposed_objective - current_objective
            if improvement >= 0 or rng.random() < np.exp(objective_scale * improvement / temperature):
                allocation = proposal
                current_objective = proposed_objective
                accepted += 1
            temperature *= annealing_cooling
        indices = month_groups[month]
        current_types = type_signals.loc[indices].to_numpy(dtype=float) * signs
        learned = current_types @ allocation
        shared = np.nanmean(current_types, axis=1)
        score_values = aggregation_alpha * learned + (1.0 - aggregation_alpha) * shared
        valid = np.isfinite(current_types).all(axis=1)
        score_values = np.where(valid, score_values, np.nan)
        result.loc[indices] = score_values
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "annealing_start": str(history.index[0].date()),
            "annealing_end": str(history.index[-1].date()),
            "annealing_history_months": len(history),
            "annealing_iterations": annealing_iterations,
            "accepted_proposals": accepted,
            "final_objective": current_objective,
            "total_agent_selections": len(investor_features) * agents_per_type * selections_per_agent,
            "finite_scores": int(np.isfinite(score_values).sum()),
        }
        for position, feature in enumerate(investor_features):
            row[f"orientation__{feature}"] = int(signs[position])
            row[f"type_weight__{feature}"] = float(allocation[position])
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def rd_agent_search_scores(
    frame: pd.DataFrame,
    branches: dict[str, list[tuple[str, int]]],
    *,
    common_start: str,
    history_months: int = 120,
    research_months: int = 96,
    validation_months: int = 24,
    minimum_rankic_months: int = 48,
    validation_folds: int = 3,
    validation_fold_months: int = 8,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a deterministic R&D-Agent-style parallel formula search."""
    if len(branches) != 6 or any(len(specifications) != 3 for specifications in branches.values()):
        raise ValueError("R&D-Agent requires six branches with three hypotheses each")
    if history_months != research_months + validation_months:
        raise ValueError("research and validation windows must partition history")
    if validation_months != validation_folds * validation_fold_months:
        raise ValueError("validation folds must partition the validation window")
    features = list(
        dict.fromkeys(
            feature
            for specifications in branches.values()
            for feature, _ in specifications
        )
    )
    missing = {"month", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing R&D-Agent hypothesis inputs: {sorted(missing)}")
    for specifications in branches.values():
        if any(sign not in {-1, 1} for _, sign in specifications):
            raise ValueError("R&D-Agent hypothesis signs must be -1 or 1")

    ranked = cross_sectional_unit_rank(frame, features)
    candidates: dict[str, pd.Series] = {}
    branch_candidates: dict[str, list[str]] = {}
    for branch, specifications in branches.items():
        signed = pd.concat(
            [ranked[feature] * sign for feature, sign in specifications],
            axis=1,
        )
        signed.columns = [feature for feature, _ in specifications]
        names = [
            f"{branch}__leader",
            f"{branch}__pair_mean",
            f"{branch}__all_mean",
            f"{branch}__consensus_median",
        ]
        candidates[names[0]] = signed.iloc[:, 0]
        candidates[names[1]] = signed.iloc[:, :2].mean(axis=1, skipna=False)
        candidates[names[2]] = signed.mean(axis=1, skipna=False)
        candidates[names[3]] = signed.median(axis=1, skipna=False)
        branch_candidates[branch] = names
    candidate_frame = pd.DataFrame(candidates, index=frame.index)
    candidate_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], candidate_frame], axis=1),
        list(candidate_frame),
    )
    rankics = monthly_rankic(frame, candidate_scores)

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    months = sorted(
        pd.Timestamp(month)
        for month in frame.loc[frame["month"] >= common_start, "month"].unique()
    )

    def aggregate_validation(validation: pd.DataFrame, members: list[str]) -> float:
        monthly = validation[members].mean(axis=1, skipna=False)
        if monthly.notna().sum() != validation_months:
            raise ValueError("R&D-Agent finalist has incomplete validation history")
        values = monthly.to_numpy(dtype=float)
        fold_means = np.asarray(
            [
                values[start : start + validation_fold_months].mean()
                for start in range(0, validation_months, validation_fold_months)
            ]
        )
        if len(fold_means) != validation_folds:
            raise AssertionError("R&D-Agent validation fold count changed")
        return float(fold_means.mean() - 0.5 * fold_means.std(ddof=0))

    for month in months:
        history = rankics.loc[rankics.index < month].tail(history_months)
        if len(history) != history_months:
            raise ValueError(f"R&D-Agent search history is incomplete at {month.date()}")
        research = history.iloc[:research_months]
        validation = history.iloc[research_months:]
        counts = research.count()
        training_scores = research.mean() - research.std(ddof=1) / np.sqrt(counts)
        training_scores = training_scores.where(counts >= minimum_rankic_months)
        winners: dict[str, str] = {}
        winner_training: dict[str, float] = {}
        winner_validation: dict[str, float] = {}
        for branch, names in branch_candidates.items():
            eligible = [name for name in names if np.isfinite(training_scores[name])]
            if not eligible:
                raise ValueError(f"R&D-Agent branch {branch} has no eligible hypothesis")
            winner = sorted(eligible, key=lambda name: (-float(training_scores[name]), name))[0]
            winners[branch] = winner
            winner_training[branch] = float(training_scores[winner])
            winner_validation[branch] = aggregate_validation(validation, [winner])
        strongest = sorted(
            winners,
            key=lambda branch: (-winner_validation[branch], branch),
        )[:3]
        finalists = {
            **{f"single__{branch}": [winner] for branch, winner in winners.items()},
            "merge__all": list(winners.values()),
            "merge__top3": [winners[branch] for branch in strongest],
        }
        finalist_scores = {
            name: aggregate_validation(validation, members)
            for name, members in finalists.items()
        }
        selected = sorted(
            finalists,
            key=lambda name: (-finalist_scores[name], name),
        )[0]
        selected_members = finalists[selected]
        indices = month_groups[month]
        score = candidate_scores.loc[indices, selected_members].mean(
            axis=1,
            skipna=False,
        )
        result.loc[indices] = score
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "research_start": str(research.index[0].date()),
            "research_end": str(research.index[-1].date()),
            "research_months": len(research),
            "validation_start": str(validation.index[0].date()),
            "validation_end": str(validation.index[-1].date()),
            "validation_months": len(validation),
            "explored_candidate_count": len(candidate_frame.columns),
            "branch_winner_count": len(winners),
            "finalist_count": len(finalists),
            "selected_solution": selected,
            "selected_members": "|".join(selected_members),
            "selected_solution_size": len(selected_members),
            "selected_validation_score": finalist_scores[selected],
            "finite_scores": int(score.notna().sum()),
        }
        for branch in branches:
            row[f"winner__{branch}"] = winners[branch]
            row[f"training_score__{branch}"] = winner_training[branch]
            row[f"validation_score__{branch}"] = winner_validation[branch]
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def mountainlion_fusion_scores(
    frame: pd.DataFrame,
    modalities: dict[str, list[tuple[str, int]]],
    ml_features: list[str],
    *,
    common_start: str,
    ml_training_months: int = 60,
    fusion_history_months: int = 24,
    minimum_fusion_rankic_months: int = 18,
    ridge_lambda: float = 1.0,
    fusion_temperature: float = 10.0,
    alpha_floor: float = 0.1,
    alpha_ceiling: float = 0.9,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a deterministic MountainLion-style dual-track adaptive fusion."""
    expected_modalities = [
        "technical",
        "market_dynamics",
        "fundamental_quality",
        "valuation_safety",
    ]
    if list(modalities) != expected_modalities:
        raise ValueError("MountainLion requires the four frozen modalities in order")
    if not 0 < alpha_floor < alpha_ceiling < 1:
        raise ValueError("MountainLion alpha bounds must lie strictly inside (0, 1)")
    features = list(
        dict.fromkeys(
            feature
            for specifications in modalities.values()
            for feature, _ in specifications
        )
    )
    if not set(ml_features).issubset(features):
        raise ValueError("MountainLion ML features must be modality inputs")
    missing = {"month", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing MountainLion inputs: {sorted(missing)}")
    for specifications in modalities.values():
        if not specifications or any(sign not in {-1, 1} for _, sign in specifications):
            raise ValueError("MountainLion modality signs must be -1 or 1")

    ranked = cross_sectional_unit_rank(frame, features)
    modality_raw: dict[str, pd.Series] = {}
    for modality, specifications in modalities.items():
        signed = pd.concat(
            [ranked[feature] * sign for feature, sign in specifications],
            axis=1,
        )
        modality_raw[modality] = signed.mean(axis=1, skipna=False)
    modality_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(modality_raw)], axis=1),
        expected_modalities,
    )

    recommendation = modality_scores.mean(axis=1, skipna=False)
    semantic_consensus = modality_scores.median(axis=1, skipna=False)
    agreement = modality_scores.apply(np.sign).mean(axis=1, skipna=False).abs()
    llm_raw = (0.5 * recommendation + 0.5 * semantic_consensus) * (0.5 + 0.5 * agreement)

    all_months = sorted(pd.Timestamp(month) for month in frame["month"].unique())
    month_groups = frame.groupby("month", sort=False).groups
    ml_raw = pd.Series(np.nan, index=frame.index, dtype="float64", name="ml")
    ridge_diagnostics: dict[pd.Timestamp, dict[str, object]] = {}
    for position in range(ml_training_months, len(all_months)):
        month = all_months[position]
        training = all_months[position - ml_training_months : position]
        training_indices = frame.index[frame["month"].isin(training)]
        current_indices = month_groups[month]
        x_train = ranked.loc[training_indices, ml_features].fillna(0.0).to_numpy(dtype=float)
        y_train = pd.to_numeric(
            frame.loc[training_indices, "ret_exc_lead1m"],
            errors="coerce",
        )
        training_month_labels = frame.loc[training_indices, "month"]
        y_train = y_train - y_train.groupby(training_month_labels).transform("mean")
        valid = np.isfinite(y_train.to_numpy(dtype=float))
        if valid.sum() < len(ml_features) + 1:
            raise ValueError(f"MountainLion ridge history is incomplete at {month.date()}")
        x_valid = x_train[valid]
        y_valid = y_train.to_numpy(dtype=float)[valid]
        gram = x_valid.T @ x_valid + ridge_lambda * np.eye(len(ml_features))
        coefficients = np.linalg.solve(gram, x_valid.T @ y_valid)
        current = ranked.loc[current_indices, ml_features].fillna(0.0).to_numpy(dtype=float)
        ml_raw.loc[current_indices] = current @ coefficients
        ridge_diagnostics[month] = {
            "ml_training_start": str(training[0].date()),
            "ml_training_end": str(training[-1].date()),
            "ml_training_months": len(training),
            "ml_training_rows": int(valid.sum()),
            "ridge_coefficient_norm": float(np.linalg.norm(coefficients)),
        }

    track_scores = cross_sectional_unit_rank(
        pd.DataFrame({"month": frame["month"], "llm": llm_raw, "ml": ml_raw}),
        ["llm", "ml"],
    )
    rankics = monthly_rankic(frame, track_scores)
    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    common_months = sorted(
        pd.Timestamp(month)
        for month in frame.loc[frame["month"] >= common_start, "month"].unique()
    )
    for month in common_months:
        history = rankics.loc[rankics.index < month].tail(fusion_history_months)
        if len(history) != fusion_history_months:
            raise ValueError(f"MountainLion fusion history is incomplete at {month.date()}")
        count = history.count()
        if (count < minimum_fusion_rankic_months).any():
            raise ValueError(f"MountainLion track history is ineligible at {month.date()}")
        mean = history.mean()
        win_rate = history.gt(0).sum() / count
        quality = mean + 0.10 * (win_rate - 0.5)
        logit = fusion_temperature * float(quality["llm"] - quality["ml"])
        alpha = 1.0 / (1.0 + np.exp(-logit))
        alpha = float(np.clip(alpha, alpha_floor, alpha_ceiling))
        indices = month_groups[month]
        current = track_scores.loc[indices]
        score = alpha * current["llm"] + (1.0 - alpha) * current["ml"]
        score = score.where(current.notna().all(axis=1))
        result.loc[indices] = score
        modality_current = modality_scores.loc[indices]
        sign_count = modality_current.apply(np.sign).nunique(axis=1)
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            **ridge_diagnostics[month],
            "fusion_start": str(history.index[0].date()),
            "fusion_end": str(history.index[-1].date()),
            "fusion_history_months": len(history),
            "agent_count": 4,
            "modality_count": len(modalities),
            "llm_mean_rankic": float(mean["llm"]),
            "ml_mean_rankic": float(mean["ml"]),
            "llm_directional_win_rate": float(win_rate["llm"]),
            "ml_directional_win_rate": float(win_rate["ml"]),
            "llm_alpha": alpha,
            "modality_disagreement_rate": float(sign_count.gt(1).mean()),
            "finite_scores": int(score.notna().sum()),
        }
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def contesttrade_dual_contest_scores(
    frame: pd.DataFrame,
    data_agents: list[tuple[str, int]],
    research_agents: dict[str, dict[str, object]],
    *,
    common_start: str,
    data_history_months: int = 24,
    data_recent_trend_months: int = 6,
    data_context_budget_agents: int = 8,
    research_context_weight: float = 0.5,
    research_belief_weight: float = 0.5,
    research_history_months: int = 24,
    qualitative_judge_weight: float = 0.1,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run deterministic ContestTrade-style Data and Research contests."""
    if len(data_agents) != 16 or len({feature for feature, _ in data_agents}) != 16:
        raise ValueError("ContestTrade requires sixteen unique Data Agents")
    expected_research = [
        "momentum",
        "reversal",
        "fundamentals",
        "event_driven",
        "risk_control",
    ]
    if list(research_agents) != expected_research:
        raise ValueError("ContestTrade requires the five frozen Research Agents in order")
    if research_context_weight + research_belief_weight != 1.0:
        raise ValueError("ContestTrade context and belief weights must sum to one")
    if not 0 <= qualitative_judge_weight < 1:
        raise ValueError("ContestTrade qualitative judge weight is invalid")
    all_specifications = [
        *data_agents,
        *[
            (str(item["column"]), int(item["sign"]))
            for specification in research_agents.values()
            for item in specification["features"]
        ],
    ]
    features = list(dict.fromkeys(feature for feature, _ in all_specifications))
    missing = {"month", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing ContestTrade inputs: {sorted(missing)}")
    if any(sign not in {-1, 1} for _, sign in all_specifications):
        raise ValueError("ContestTrade feature signs must be -1 or 1")

    ranked = cross_sectional_unit_rank(frame, features)
    data_names = [feature for feature, _ in data_agents]
    data_raw = pd.DataFrame(
        {feature: ranked[feature] * sign for feature, sign in data_agents},
        index=frame.index,
    )
    data_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], data_raw], axis=1),
        data_names,
    )
    data_rankics = monthly_rankic(frame, data_scores)

    beliefs: dict[str, pd.Series] = {}
    judge_scores: dict[str, float] = {}
    for agent, specification in research_agents.items():
        signed = pd.concat(
            [
                ranked[str(item["column"])] * int(item["sign"])
                for item in specification["features"]
            ],
            axis=1,
        )
        beliefs[agent] = signed.mean(axis=1, skipna=False)
        judge = float(specification["judge_score_1_to_5"])
        if not 1 <= judge <= 5:
            raise ValueError("ContestTrade judge scores must be between one and five")
        judge_scores[agent] = judge
    belief_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(beliefs)], axis=1),
        expected_research,
    )

    all_months = sorted(pd.Timestamp(month) for month in frame["month"].unique())
    month_groups = frame.groupby("month", sort=False).groups
    research_raw = pd.DataFrame(np.nan, index=frame.index, columns=expected_research)
    data_diagnostics: dict[pd.Timestamp, dict[str, object]] = {}
    for position in range(data_history_months, len(all_months)):
        month = all_months[position]
        history = data_rankics.iloc[position - data_history_months : position]
        if len(history) != data_history_months:
            raise AssertionError("ContestTrade Data Contest history changed")
        recent = history.iloc[-data_recent_trend_months:]
        preceding = history.iloc[-2 * data_recent_trend_months : -data_recent_trend_months]
        utility = history.mean() + 0.5 * (recent.mean() - preceding.mean())
        if not np.isfinite(utility).all():
            raise ValueError(f"ContestTrade Data Agent utility is incomplete at {month.date()}")
        indices = month_groups[month]
        current = data_scores.loc[indices]
        similarity = current.corr(min_periods=20).abs().fillna(0.0)
        np.fill_diagonal(similarity.values, 1.0)
        positive = sorted(name for name in data_names if utility[name] > 0)
        fallback = not positive
        if fallback:
            positive = [sorted(data_names, key=lambda name: (-float(utility[name]), name))[0]]
        selected: list[str] = []
        coverage = np.zeros(len(data_names), dtype=float)
        while len(selected) < min(data_context_budget_agents, len(positive)):
            candidates = [name for name in positive if name not in selected]
            gains = {}
            for name in candidates:
                effective_utility = max(float(utility[name]), 0.0)
                if fallback:
                    effective_utility = 1.0
                candidate_coverage = effective_utility * similarity.loc[name, data_names].to_numpy(dtype=float)
                gains[name] = float(np.maximum(coverage, candidate_coverage).sum() - coverage.sum())
            chosen = sorted(candidates, key=lambda name: (-gains[name], name))[0]
            effective_utility = max(float(utility[chosen]), 0.0)
            if fallback:
                effective_utility = 1.0
            coverage = np.maximum(
                coverage,
                effective_utility * similarity.loc[chosen, data_names].to_numpy(dtype=float),
            )
            selected.append(chosen)
        selected_utility = utility[selected].clip(lower=0.0)
        if fallback:
            selected_utility[:] = 1.0
        data_weights = selected_utility / selected_utility.sum()
        selected_values = current[selected].to_numpy(dtype=float)
        finite = np.isfinite(selected_values)
        numerator = np.where(finite, selected_values * data_weights.to_numpy(), 0.0).sum(axis=1)
        denominator = np.where(finite, data_weights.to_numpy(), 0.0).sum(axis=1)
        context = np.divide(
            numerator,
            denominator,
            out=np.full(len(indices), np.nan),
            where=denominator > 0,
        )
        for agent in expected_research:
            belief = belief_scores.loc[indices, agent].to_numpy(dtype=float)
            research_raw.loc[indices, agent] = (
                research_context_weight * context + research_belief_weight * belief
            )
        data_diagnostics[month] = {
            "data_history_start": str(history.index[0].date()),
            "data_history_end": str(history.index[-1].date()),
            "data_history_months": len(history),
            "data_candidate_count": len(data_names),
            "data_positive_utility_count": len(positive) if not fallback else 0,
            "data_selected_count": len(selected),
            "selected_data_agents": "|".join(selected),
            "data_no_positive_fallback": fallback,
        }

    research_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], research_raw], axis=1),
        expected_research,
    )
    research_rankics = monthly_rankic(frame, research_scores)
    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    common_months = sorted(
        pd.Timestamp(month)
        for month in frame.loc[frame["month"] >= common_start, "month"].unique()
    )
    for month in common_months:
        history = research_rankics.loc[research_rankics.index < month].tail(
            research_history_months
        )
        if len(history) != research_history_months or history.notna().sum().min() != research_history_months:
            raise ValueError(f"ContestTrade Research Contest history is incomplete at {month.date()}")
        predicted_sharpe = history.mean() / history.std(ddof=1)
        quantitative = predicted_sharpe.clip(lower=0.0)
        judge = pd.Series(judge_scores)
        weighted = quantitative * (
            1.0 - qualitative_judge_weight + qualitative_judge_weight * judge / 5.0
        )
        fallback = not bool((weighted > 0).any())
        if fallback:
            chosen = sorted(
                expected_research,
                key=lambda name: (-float(predicted_sharpe[name]), name),
            )[0]
            allocation = pd.Series(0.0, index=expected_research)
            allocation[chosen] = 1.0
        else:
            allocation = weighted / weighted.sum()
        indices = month_groups[month]
        current = research_scores.loc[indices, expected_research].to_numpy(dtype=float)
        finite = np.isfinite(current)
        numerator = np.where(finite, current * allocation.to_numpy(), 0.0).sum(axis=1)
        denominator = np.where(finite, allocation.to_numpy(), 0.0).sum(axis=1)
        score = np.divide(
            numerator,
            denominator,
            out=np.full(len(indices), np.nan),
            where=denominator > 0,
        )
        result.loc[indices] = score
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            **data_diagnostics[month],
            "research_history_start": str(history.index[0].date()),
            "research_history_end": str(history.index[-1].date()),
            "research_history_months": len(history),
            "research_agent_count": len(expected_research),
            "research_positive_utility_count": int((quantitative > 0).sum()),
            "research_no_positive_fallback": fallback,
            "finite_scores": int(np.isfinite(score).sum()),
        }
        for agent in expected_research:
            row[f"predicted_sharpe__{agent}"] = float(predicted_sharpe[agent])
            row[f"judge_score__{agent}"] = judge_scores[agent]
            row[f"allocation__{agent}"] = float(allocation[agent])
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def alphaagents_debate_scores(
    frame: pd.DataFrame,
    specialists: dict[str, list[tuple[str, int]]],
    *,
    speaker_order: list[str],
    round_robin_passes: int = 2,
    peer_median_update_weight: float = 0.35,
    own_specialist_retention_weight: float = 0.65,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a deterministic three-specialist AlphaAgents round-robin debate."""
    expected = ["fundamental", "sentiment", "valuation"]
    if list(specialists) != expected or speaker_order != expected:
        raise ValueError("AlphaAgents requires the three frozen specialists in order")
    if round_robin_passes < 2:
        raise ValueError("AlphaAgents must give every specialist at least two turns")
    if peer_median_update_weight + own_specialist_retention_weight != 1.0:
        raise ValueError("AlphaAgents debate weights must sum to one")
    features = list(
        dict.fromkeys(
            feature
            for specifications in specialists.values()
            for feature, _ in specifications
        )
    )
    missing = {"month", *features} - set(frame)
    if missing:
        raise ValueError(f"missing AlphaAgents inputs: {sorted(missing)}")
    if any(
        sign not in {-1, 1}
        for specifications in specialists.values()
        for _, sign in specifications
    ):
        raise ValueError("AlphaAgents specialist signs must be -1 or 1")

    ranked = cross_sectional_unit_rank(frame, features)
    raw: dict[str, pd.Series] = {}
    for specialist, specifications in specialists.items():
        signed = pd.concat(
            [ranked[feature] * sign for feature, sign in specifications],
            axis=1,
        )
        raw[specialist] = signed.mean(axis=1, skipna=False)
    initial = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(raw)], axis=1),
        expected,
    )

    consensus_raw = pd.Series(np.nan, index=frame.index, dtype="float64")
    diagnostics: list[dict[str, object]] = []
    for month, indices in frame.groupby("month", sort=True).groups.items():
        opinions = initial.loc[indices, expected].to_numpy(dtype=float)
        starting = opinions.copy()
        for _ in range(round_robin_passes):
            for position, _specialist in enumerate(speaker_order):
                peers = np.delete(opinions, position, axis=1)
                peer_finite = np.isfinite(peers)
                peer_count = peer_finite.sum(axis=1)
                peer_median = np.divide(
                    np.where(peer_finite, peers, 0.0).sum(axis=1),
                    peer_count,
                    out=np.full(len(peers), np.nan),
                    where=peer_count > 0,
                )
                own = opinions[:, position]
                valid = np.isfinite(own) & np.isfinite(peer_median)
                opinions[valid, position] = (
                    own_specialist_retention_weight * own[valid]
                    + peer_median_update_weight * peer_median[valid]
                )
        finite_count = np.isfinite(opinions).sum(axis=1)
        consensus = np.ma.median(
            np.ma.masked_invalid(opinions),
            axis=1,
        ).filled(np.nan)
        consensus[finite_count < 2] = np.nan
        consensus_raw.loc[indices] = consensus

        starting_signs = np.sign(starting)
        final_signs = np.sign(opinions)
        starting_valid = np.isfinite(starting).all(axis=1)
        final_valid = np.isfinite(opinions).all(axis=1)
        starting_disagreement = np.ptp(starting_signs, axis=1) > 0
        final_disagreement = np.ptp(final_signs, axis=1) > 0
        change = np.abs(opinions - starting)
        diagnostics.append(
            {
                "formation_month": str(pd.Timestamp(month).date()),
                "specialist_count": len(expected),
                "round_robin_passes": round_robin_passes,
                "speaking_turns": round_robin_passes * len(expected),
                "initial_disagreement_rate": float(
                    starting_disagreement[starting_valid].mean()
                ),
                "final_disagreement_rate": float(final_disagreement[final_valid].mean()),
                "unanimous_after_debate_rate": float((~final_disagreement[final_valid]).mean()),
                "mean_absolute_opinion_change": float(np.nanmean(change)),
                "finite_scores": int(np.isfinite(consensus).sum()),
                "buy_consensus_count": int(np.nansum(consensus > 0)),
                "sell_consensus_count": int(np.nansum(consensus < 0)),
            }
        )
    score = cross_sectional_unit_rank(
        pd.DataFrame({"month": frame["month"], "consensus": consensus_raw}),
        ["consensus"],
    )["consensus"]
    return score, pd.DataFrame(diagnostics)


def treevo_evolution_scores(
    frame: pd.DataFrame,
    seed_features: list[tuple[str, int]],
    *,
    common_start: str,
    training_start: str,
    training_end: str,
    validation_start: str,
    validation_end: str,
    population_size: int = 10,
    evaluation_budget: int = 200,
    offspring_generations: int = 19,
    offspring_per_generation: int = 10,
    operator_rotation: tuple[str, ...] = ("crossover", "mutation", "pruning"),
    mutation_probabilities: tuple[float, float, float] = (0.4, 0.4, 0.2),
    random_seed: int = 16334,
    maximum_initial_depth: int = 3,
    complexity_penalty_per_extra_node: float = 0.0001,
) -> tuple[pd.Series, pd.DataFrame, dict[str, object]]:
    """Evolve an interpretable hierarchy with a frozen TreEvo-style search."""
    if len(seed_features) != 6 or len({feature for feature, _ in seed_features}) != 6:
        raise ValueError("TreEvo requires six unique seed features")
    if population_size != 10 or evaluation_budget != 200:
        raise ValueError("TreEvo population or evaluation budget changed")
    if population_size + offspring_generations * offspring_per_generation != evaluation_budget:
        raise ValueError("TreEvo generations do not exhaust the evaluation budget")
    if operator_rotation != ("crossover", "mutation", "pruning"):
        raise ValueError("TreEvo operator rotation changed")
    if not np.isclose(sum(mutation_probabilities), 1.0):
        raise ValueError("TreEvo mutation probabilities must sum to one")
    features = [feature for feature, _ in seed_features]
    missing = {"month", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing TreEvo inputs: {sorted(missing)}")
    if any(sign not in {-1, 1} for _, sign in seed_features):
        raise ValueError("TreEvo seed signs must be -1 or 1")

    train_start = pd.Timestamp(training_start)
    train_end = pd.Timestamp(training_end)
    valid_start = pd.Timestamp(validation_start)
    valid_end = pd.Timestamp(validation_end)
    search_mask = frame["month"].between(train_start, valid_end)
    search_frame = frame.loc[search_mask]
    train_months = sorted(search_frame.loc[search_frame["month"].between(train_start, train_end), "month"].unique())
    valid_months = sorted(search_frame.loc[search_frame["month"].between(valid_start, valid_end), "month"].unique())
    if len(train_months) != 96 or len(valid_months) != 24 or train_end >= valid_start:
        raise ValueError("TreEvo requires the frozen 96/24-month chronological split")

    ranked = cross_sectional_unit_rank(frame, features)
    ranked_search = ranked.loc[search_frame.index]
    signed_search = {
        feature: ranked_search[feature] * sign
        for feature, sign in seed_features
    }
    signed_full = {
        feature: ranked[feature] * sign
        for feature, sign in seed_features
    }
    search_return_ranks = pd.to_numeric(
        search_frame["ret_exc_lead1m"],
        errors="coerce",
    ).groupby(search_frame["month"], sort=False).rank(method="average")
    search_month_groups = search_frame.groupby("month", sort=True).groups
    rng = np.random.default_rng(random_seed)
    internal_operators = ("mean", "difference", "product")

    def expression(tree: tuple) -> str:
        if tree[0] == "leaf":
            return str(tree[1])
        return f"{tree[0]}({expression(tree[1])},{expression(tree[2])})"

    def node_count(tree: tuple) -> int:
        if tree[0] == "leaf":
            return 1
        return 1 + node_count(tree[1]) + node_count(tree[2])

    def paths(tree: tuple, *, leaves: bool | None = None, prefix: tuple[int, ...] = ()) -> list[tuple[int, ...]]:
        is_leaf = tree[0] == "leaf"
        selected = leaves is None or leaves == is_leaf
        result = [prefix] if selected else []
        if not is_leaf:
            result.extend(paths(tree[1], leaves=leaves, prefix=(*prefix, 1)))
            result.extend(paths(tree[2], leaves=leaves, prefix=(*prefix, 2)))
        return result

    def subtree(tree: tuple, path: tuple[int, ...]) -> tuple:
        current = tree
        for position in path:
            current = current[position]
        return current

    def replace(tree: tuple, path: tuple[int, ...], replacement: tuple) -> tuple:
        if not path:
            return replacement
        values = list(tree)
        position = path[0]
        values[position] = replace(values[position], path[1:], replacement)
        return tuple(values)

    def random_tree(depth: int) -> tuple:
        if depth <= 0 or rng.random() < 0.25:
            return ("leaf", features[int(rng.integers(len(features)))])
        operator = internal_operators[int(rng.integers(len(internal_operators)))]
        return (operator, random_tree(depth - 1), random_tree(depth - 1))

    def crossover(left: tuple, right: tuple) -> tuple:
        left_path = paths(left)[int(rng.integers(len(paths(left))))]
        right_path = paths(right)[int(rng.integers(len(paths(right))))]
        return replace(left, left_path, subtree(right, right_path))

    def mutate(tree: tuple) -> tuple[tuple, str]:
        draw = rng.random()
        root_probability, internal_probability, _fine_probability = mutation_probabilities
        if draw < root_probability:
            return random_tree(maximum_initial_depth), "root"
        if draw < root_probability + internal_probability:
            internal_paths = paths(tree, leaves=False)
            if not internal_paths:
                operator = internal_operators[int(rng.integers(len(internal_operators)))]
                new_leaf = ("leaf", features[int(rng.integers(len(features)))])
                return (operator, tree, new_leaf), "internal"
            path = internal_paths[int(rng.integers(len(internal_paths)))]
            return replace(tree, path, random_tree(maximum_initial_depth - 1)), "internal"
        leaf_paths = paths(tree, leaves=True)
        path = leaf_paths[int(rng.integers(len(leaf_paths)))]
        old_feature = subtree(tree, path)[1]
        alternatives = [feature for feature in features if feature != old_feature]
        replacement = ("leaf", alternatives[int(rng.integers(len(alternatives)))])
        return replace(tree, path, replacement), "fine"

    def prune(tree: tuple) -> tuple:
        internal_paths = paths(tree, leaves=False)
        if not internal_paths:
            return tree
        path = internal_paths[int(rng.integers(len(internal_paths)))]
        target = subtree(tree, path)
        child = target[1 + int(rng.integers(2))]
        return replace(tree, path, child)

    def evaluate_tree(tree: tuple, values: dict[str, pd.Series]) -> pd.Series:
        if tree[0] == "leaf":
            return values[str(tree[1])]
        left = evaluate_tree(tree[1], values)
        right = evaluate_tree(tree[2], values)
        if tree[0] == "mean":
            return (left + right) / 2.0
        if tree[0] == "difference":
            return left - right
        if tree[0] == "product":
            return left * right
        raise AssertionError(f"unknown TreEvo node: {tree[0]}")

    history_rows: list[dict[str, object]] = []
    evaluation_number = 0

    def evaluate_candidate(tree: tuple, generation: int, operator: str, mutation_scope: str = "") -> dict[str, object]:
        nonlocal evaluation_number
        evaluation_number += 1
        name = expression(tree)
        raw_score = evaluate_tree(tree, signed_search).replace([np.inf, -np.inf], np.nan)
        ranked_score = cross_sectional_unit_rank(
            pd.DataFrame({"month": search_frame["month"], "candidate": raw_score}),
            ["candidate"],
        )
        rankic_values = []
        rankic_months = []
        candidate_score = ranked_score["candidate"]
        for month, indices in search_month_groups.items():
            x = candidate_score.loc[indices].to_numpy(dtype=float)
            y = search_return_ranks.loc[indices].to_numpy(dtype=float)
            valid = np.isfinite(x) & np.isfinite(y)
            if valid.sum() < 20:
                correlation = np.nan
            else:
                centered_x = x[valid] - x[valid].mean()
                centered_y = y[valid] - y[valid].mean()
                denominator = float(
                    np.sqrt(np.sum(centered_x**2) * np.sum(centered_y**2))
                )
                correlation = (
                    float(np.sum(centered_x * centered_y) / denominator)
                    if denominator > 0
                    else np.nan
                )
            rankic_values.append(correlation)
            rankic_months.append(pd.Timestamp(month))
        rankic = pd.Series(rankic_values, index=pd.DatetimeIndex(rankic_months))
        train = rankic.loc[(rankic.index >= train_start) & (rankic.index <= train_end)]
        validation = rankic.loc[(rankic.index >= valid_start) & (rankic.index <= valid_end)]
        nodes = node_count(tree)
        penalty = complexity_penalty_per_extra_node * (nodes - 1)
        train_count = int(train.notna().sum())
        validation_count = int(validation.notna().sum())
        valid_candidate = train_count == 96 and validation_count == 24
        if valid_candidate:
            train_mean = float(train.mean())
            direction = 1 if train_mean >= 0 else -1
            validation_mean = float(direction * validation.mean())
            fitness = abs(train_mean) - penalty
        else:
            train_mean = 0.0
            direction = 1
            validation_mean = -1.0
            fitness = -1.0 - penalty
        candidate = {
            "tree": tree,
            "expression": name,
            "node_count": nodes,
            "training_mean_rankic": train_mean,
            "training_direction": direction,
            "validation_mean_oriented_rankic": validation_mean,
            "complexity_penalty": penalty,
            "training_fitness": fitness,
            "valid_candidate": valid_candidate,
            "evaluation": evaluation_number,
        }
        history_rows.append(
            {
                "evaluation": evaluation_number,
                "generation": generation,
                "operator": operator,
                "mutation_scope": mutation_scope,
                "expression": name,
                "node_count": nodes,
                "training_mean_rankic": train_mean,
                "training_direction": direction,
                "training_rankic_months": train_count,
                "validation_rankic_months": validation_count,
                "valid_candidate": valid_candidate,
                "validation_mean_oriented_rankic": validation_mean,
                "complexity_penalty": penalty,
                "training_fitness": fitness,
            }
        )
        return candidate

    initial_trees: list[tuple] = []
    initial_expressions: set[str] = set()
    while len(initial_trees) < population_size:
        tree = random_tree(maximum_initial_depth)
        name = expression(tree)
        if name not in initial_expressions:
            initial_trees.append(tree)
            initial_expressions.add(name)
    population = [evaluate_candidate(tree, 0, "initialization") for tree in initial_trees]
    for generation in range(1, offspring_generations + 1):
        operator = operator_rotation[(generation - 1) % len(operator_rotation)]
        offspring = []
        for _ in range(offspring_per_generation):
            if operator == "crossover":
                parent_indices = rng.choice(len(population), size=2, replace=False)
                child = crossover(
                    population[int(parent_indices[0])]["tree"],
                    population[int(parent_indices[1])]["tree"],
                )
                scope = ""
            elif operator == "mutation":
                parent = population[int(rng.integers(len(population)))]["tree"]
                child, scope = mutate(parent)
            else:
                parent = population[int(rng.integers(len(population)))]["tree"]
                child = prune(parent)
                scope = ""
            offspring.append(evaluate_candidate(child, generation, operator, scope))
        population = sorted(
            [*population, *offspring],
            key=lambda candidate: (
                -float(candidate["training_fitness"]),
                str(candidate["expression"]),
                int(candidate["evaluation"]),
            ),
        )[:population_size]
    if evaluation_number != evaluation_budget:
        raise AssertionError("TreEvo did not exhaust the frozen evaluation budget")
    selected = sorted(
        population,
        key=lambda candidate: (
            -float(candidate["validation_mean_oriented_rankic"]),
            -float(candidate["training_fitness"]),
            str(candidate["expression"]),
        ),
    )[0]
    if not bool(selected["valid_candidate"]):
        raise ValueError("TreEvo search produced no valid final candidate")
    final_expressions = {str(candidate["expression"]) for candidate in population}
    for row in history_rows:
        row["survives_final_population"] = row["expression"] in final_expressions
        row["selected_final"] = row["evaluation"] == selected["evaluation"]

    final_raw = evaluate_tree(selected["tree"], signed_full).replace([np.inf, -np.inf], np.nan)
    final_score = cross_sectional_unit_rank(
        pd.DataFrame({"month": frame["month"], "selected": final_raw}),
        ["selected"],
    )["selected"] * int(selected["training_direction"])
    final_score = final_score.where(frame["month"] >= pd.Timestamp(common_start))
    history = pd.DataFrame(history_rows)
    summary = {
        "selected_evaluation": int(selected["evaluation"]),
        "selected_expression": str(selected["expression"]),
        "selected_node_count": int(selected["node_count"]),
        "selected_training_direction": int(selected["training_direction"]),
        "selected_training_mean_rankic": float(selected["training_mean_rankic"]),
        "selected_training_fitness": float(selected["training_fitness"]),
        "selected_validation_mean_oriented_rankic": float(selected["validation_mean_oriented_rankic"]),
        "final_population_size": len(population),
        "evaluation_budget": evaluation_number,
    }
    return final_score, history, summary


def tradinggroup_reflection_scores(
    frame: pd.DataFrame,
    information_agents: dict[str, list[tuple[str, int]]],
    styles: dict[str, dict[str, float]],
    *,
    risk_features: list[str],
    safety_features: list[str],
    common_start: str,
    forecast_reflection_months: int = 60,
    minimum_forecast_rankic_months: int = 36,
    forecast_reliability_temperature: float = 20.0,
    style_reflection_months: int = 20,
    minimum_style_rankic_months: int = 12,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a deterministic TradingGroup-style reflected agent chain."""
    expected_agents = ["news_sentiment", "financial_report", "technical"]
    expected_styles = ["aggressive", "balanced", "conservative"]
    if list(information_agents) != expected_agents:
        raise ValueError("TradingGroup requires the three frozen information agents in order")
    if list(styles) != expected_styles:
        raise ValueError("TradingGroup requires aggressive, balanced, and conservative styles")
    specifications = [
        specification
        for agent_specifications in information_agents.values()
        for specification in agent_specifications
    ]
    features = list(
        dict.fromkeys(
            [feature for feature, _ in specifications]
            + list(risk_features)
            + list(safety_features)
        )
    )
    missing = {"month", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing TradingGroup inputs: {sorted(missing)}")
    if any(sign not in {-1, 1} for _, sign in specifications):
        raise ValueError("TradingGroup feature signs must be -1 or 1")

    ranked = cross_sectional_unit_rank(frame, features)
    agent_raw: dict[str, pd.Series] = {}
    for agent, agent_specifications in information_agents.items():
        signed = pd.concat(
            [ranked[feature] * sign for feature, sign in agent_specifications],
            axis=1,
        )
        agent_raw[agent] = signed.mean(axis=1, skipna=False)
    agent_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(agent_raw)], axis=1),
        expected_agents,
    )
    agent_rankics = monthly_rankic(frame, agent_scores)

    all_months = sorted(pd.Timestamp(month) for month in frame["month"].unique())
    month_groups = frame.groupby("month", sort=False).groups
    forecast_raw = pd.Series(np.nan, index=frame.index, dtype="float64")
    forecast_diagnostics: dict[pd.Timestamp, dict[str, object]] = {}
    for position in range(forecast_reflection_months, len(all_months)):
        month = all_months[position]
        history = agent_rankics.iloc[
            position - forecast_reflection_months : position
        ]
        count = history.count()
        if len(history) != forecast_reflection_months or (
            count < minimum_forecast_rankic_months
        ).any():
            raise ValueError(f"TradingGroup forecast reflection is incomplete at {month.date()}")
        mean = history.mean()
        logits = forecast_reliability_temperature * mean
        reliability = np.exp(logits - logits.max())
        reliability /= reliability.sum()
        indices = month_groups[month]
        current = agent_scores.loc[indices, expected_agents].to_numpy(dtype=float)
        finite = np.isfinite(current)
        numerator = np.where(finite, current * reliability.to_numpy(), 0.0).sum(axis=1)
        denominator = np.where(finite, reliability.to_numpy(), 0.0).sum(axis=1)
        forecast = np.divide(
            numerator,
            denominator,
            out=np.full(len(indices), np.nan),
            where=denominator > 0,
        )
        forecast_raw.loc[indices] = forecast
        row: dict[str, object] = {
            "forecast_reflection_start": str(history.index[0].date()),
            "forecast_reflection_end": str(history.index[-1].date()),
            "forecast_reflection_months": len(history),
        }
        for agent in expected_agents:
            row[f"agent_mean_rankic__{agent}"] = float(mean[agent])
            row[f"agent_reliability__{agent}"] = float(reliability[agent])
        forecast_diagnostics[month] = row
    forecast_score = cross_sectional_unit_rank(
        pd.DataFrame({"month": frame["month"], "forecast": forecast_raw}),
        ["forecast"],
    )["forecast"]

    risk_raw = ranked[risk_features].mean(axis=1, skipna=False)
    safety_raw = ranked[safety_features].mean(axis=1, skipna=False)
    risk_score = cross_sectional_unit_rank(
        pd.DataFrame({"month": frame["month"], "risk": risk_raw}),
        ["risk"],
    )["risk"]
    safety_score = cross_sectional_unit_rank(
        pd.DataFrame({"month": frame["month"], "safety": safety_raw}),
        ["safety"],
    )["safety"]
    style_raw = pd.DataFrame(index=frame.index)
    for style, parameters in styles.items():
        style_raw[style] = (
            forecast_score
            - float(parameters["risk_penalty"]) * risk_score
            + float(parameters["safety_bonus"]) * safety_score
        )
    style_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], style_raw], axis=1),
        expected_styles,
    )
    style_rankics = monthly_rankic(frame, style_scores)

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    common_months = sorted(
        pd.Timestamp(month)
        for month in frame.loc[frame["month"] >= common_start, "month"].unique()
    )
    for month in common_months:
        history = style_rankics.loc[style_rankics.index < month].tail(
            style_reflection_months
        )
        count = history.count()
        if len(history) != style_reflection_months or (
            count < minimum_style_rankic_months
        ).any():
            raise ValueError(f"TradingGroup style reflection is incomplete at {month.date()}")
        mean = history.mean()
        selected_style = sorted(
            expected_styles,
            key=lambda style: (-float(mean[style]), style),
        )[0]
        indices = month_groups[month]
        score = style_scores.loc[indices, selected_style].copy()
        risk_percentile = (risk_score.loc[indices] + 1.0) / 2.0
        threshold = float(styles[selected_style]["positive_risk_intercept_quantile"])
        intercepted = score.gt(0) & risk_percentile.gt(threshold)
        score.loc[intercepted] = 0.0
        result.loc[indices] = score
        row = {
            "formation_month": str(month.date()),
            **forecast_diagnostics[month],
            "style_reflection_start": str(history.index[0].date()),
            "style_reflection_end": str(history.index[-1].date()),
            "style_reflection_months": len(history),
            "selected_style": selected_style,
            "risk_intercept_quantile": threshold,
            "risk_intercept_count": int(intercepted.sum()),
            "finite_scores": int(score.notna().sum()),
        }
        for style in expected_styles:
            row[f"style_mean_rankic__{style}"] = float(mean[style])
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def mm_arc_routing_scores(
    frame: pd.DataFrame,
    experts: dict[str, list[tuple[str, int]]],
    *,
    view_weights: dict[str, float],
    rabo_rank_weights: dict[str, float],
    common_start: str,
    audit_history_months: int = 120,
    minimum_regime_months: int = 12,
    audit_blocks: int = 6,
    admitted_per_pool: int = 5,
    router_performance_temperature: float = 20.0,
    router_robustness_tilt: float = 0.5,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run deterministic MM-ARC-style RABO pools and capital routing."""
    expected_experts = ["trend", "reversal", "breakout", "exposure_control"]
    if list(experts) != expected_experts:
        raise ValueError("MM-ARC requires the four frozen experts in order")
    if any(len(specifications) != 6 for specifications in experts.values()):
        raise ValueError("MM-ARC requires six feature inputs per expert")
    if view_weights != {
        "numerical_pool": 0.5,
        "chart_proxy": 0.25,
        "technical_summary_proxy": 0.25,
    }:
        raise ValueError("MM-ARC aligned-view weights changed")
    if rabo_rank_weights != {
        "benchmark_exceedance": 0.3,
        "lower_tail_5pct": 0.3,
        "median": 0.15,
        "stability": 0.15,
        "turnover_penalty": -0.1,
    }:
        raise ValueError("MM-ARC RABO weights changed")
    specifications = [
        specification
        for expert_specifications in experts.values()
        for specification in expert_specifications
    ]
    features = list(dict.fromkeys(feature for feature, _ in specifications))
    missing = {"month", "security_id", "ret", "weight", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing MM-ARC inputs: {sorted(missing)}")
    if any(sign not in {-1, 1} for _, sign in specifications):
        raise ValueError("MM-ARC expert feature signs must be -1 or 1")

    ranked = cross_sectional_unit_rank(frame, features)
    candidate_forms = [
        "primary",
        "secondary",
        "pair_mean",
        "triple_mean",
        "interaction",
        "risk_adjusted",
    ]
    candidate_raw: dict[str, pd.Series] = {}
    expert_candidates: dict[str, list[str]] = {}
    chart_raw: dict[str, pd.Series] = {}
    summary_raw: dict[str, pd.Series] = {}
    for expert, expert_specifications in experts.items():
        signed = pd.concat(
            [ranked[feature] * sign for feature, sign in expert_specifications],
            axis=1,
        )
        signed.columns = [feature for feature, _ in expert_specifications]
        names = [f"{expert}__{form}" for form in candidate_forms]
        candidate_raw[names[0]] = signed.iloc[:, 0]
        candidate_raw[names[1]] = signed.iloc[:, 1]
        candidate_raw[names[2]] = signed.iloc[:, :2].mean(axis=1, skipna=False)
        candidate_raw[names[3]] = signed.iloc[:, :3].mean(axis=1, skipna=False)
        candidate_raw[names[4]] = signed.iloc[:, 0] * signed.iloc[:, 2]
        candidate_raw[names[5]] = signed.mean(axis=1, skipna=False)
        expert_candidates[expert] = names
        chart_raw[expert] = signed.iloc[:, :3].mean(axis=1, skipna=False)
        summary_raw[expert] = signed.iloc[:, :3].apply(np.sign).mean(axis=1, skipna=False)
    candidate_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(candidate_raw)], axis=1),
        list(candidate_raw),
    )
    candidate_rankics = monthly_rankic(frame, candidate_scores)
    chart_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(chart_raw)], axis=1),
        expected_experts,
    )
    summary_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(summary_raw)], axis=1),
        expected_experts,
    )

    turnover = pd.DataFrame(index=candidate_rankics.index, columns=candidate_scores.columns, dtype=float)
    base_order = frame[["security_id", "month"]].copy()
    for candidate in candidate_scores:
        values = base_order.assign(score=candidate_scores[candidate]).sort_values(
            ["security_id", "month"],
            kind="mergesort",
        )
        prior_score = values.groupby("security_id")["score"].shift(1)
        prior_month = values.groupby("security_id")["month"].shift(1)
        consecutive = values["month"].eq(prior_month + pd.offsets.MonthEnd(1))
        change = (values["score"] - prior_score).abs().where(consecutive)
        turnover[candidate] = change.groupby(values["month"]).mean().reindex(turnover.index)

    market_rows = []
    for month, indices in frame.groupby("month", sort=True).groups.items():
        weights = pd.to_numeric(frame.loc[indices, "weight"], errors="coerce")
        returns = pd.to_numeric(frame.loc[indices, "ret"], errors="coerce").fillna(0.0)
        market_rows.append((pd.Timestamp(month), float(np.sum(weights * returns) / weights.sum())))
    market = pd.Series(dict(market_rows)).sort_index()
    trailing_six = (1.0 + market).rolling(6, min_periods=6).apply(np.prod, raw=True) - 1.0
    regimes = pd.Series("sideways", index=market.index)
    regimes.loc[trailing_six > 0.05] = "bull"
    regimes.loc[trailing_six < -0.05] = "bear"

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    common_months = sorted(
        pd.Timestamp(month)
        for month in frame.loc[frame["month"] >= common_start, "month"].unique()
    )
    for month in common_months:
        complete_history = candidate_rankics.loc[candidate_rankics.index < month].tail(
            audit_history_months
        )
        if len(complete_history) != audit_history_months:
            raise ValueError(f"MM-ARC audit history is incomplete at {month.date()}")
        regime = str(regimes.loc[month])
        same_regime = complete_history.index[regimes.reindex(complete_history.index).eq(regime)]
        sparse_fallback = len(same_regime) < minimum_regime_months
        audit_index = complete_history.index if sparse_fallback else same_regime
        audit = candidate_rankics.loc[audit_index]
        audit_turnover = turnover.loc[audit_index]
        blocks = [indices for indices in np.array_split(np.arange(len(audit)), audit_blocks) if len(indices)]
        if len(blocks) != audit_blocks:
            raise ValueError("MM-ARC has too few observations for six audit blocks")

        current_indices = month_groups[month]
        routed_expert_scores: dict[str, pd.Series] = {}
        expert_performance: dict[str, float] = {}
        expert_robustness: dict[str, float] = {}
        selected_by_expert: dict[str, list[str]] = {}
        for expert, names in expert_candidates.items():
            benchmark = names[0]
            metrics: dict[str, dict[str, float]] = {}
            benchmark_blocks = np.asarray(
                [audit.iloc[block][benchmark].mean() for block in blocks],
                dtype=float,
            )
            for name in names:
                block_values = np.asarray(
                    [audit.iloc[block][name].mean() for block in blocks],
                    dtype=float,
                )
                metrics[name] = {
                    "benchmark_exceedance": float(np.mean(block_values > benchmark_blocks)),
                    "lower_tail_5pct": float(np.quantile(block_values, 0.05)),
                    "median": float(np.median(block_values)),
                    "stability": float(-block_values.std(ddof=0)),
                    "turnover_penalty": float(audit_turnover[name].mean()),
                }
            metric_frame = pd.DataFrame(metrics).T
            ranks = metric_frame.rank(method="average", pct=True)
            rabo = sum(
                float(weight) * ranks[metric]
                for metric, weight in rabo_rank_weights.items()
            )
            selected = sorted(names, key=lambda name: (-float(rabo[name]), name))[
                :admitted_per_pool
            ]
            selected_by_expert[expert] = selected
            pool = candidate_scores.loc[current_indices, selected].mean(axis=1, skipna=False)
            expert_score = (
                view_weights["numerical_pool"] * pool
                + view_weights["chart_proxy"] * chart_scores.loc[current_indices, expert]
                + view_weights["technical_summary_proxy"] * summary_scores.loc[current_indices, expert]
            )
            routed_expert_scores[expert] = expert_score
            expert_performance[expert] = float(audit[selected].mean(axis=1).mean())
            expert_robustness[expert] = float(np.clip(rabo[selected].mean(), 0.0, 1.0))

        performance = pd.Series(expert_performance)
        robustness = pd.Series(expert_robustness)
        logits = router_performance_temperature * performance + router_robustness_tilt * robustness
        router_weights = np.exp(logits - logits.max())
        router_weights /= router_weights.sum()
        expert_frame = pd.DataFrame(routed_expert_scores, index=current_indices)
        current = expert_frame[expected_experts].to_numpy(dtype=float)
        finite = np.isfinite(current)
        numerator = np.where(finite, current * router_weights.to_numpy(), 0.0).sum(axis=1)
        denominator = np.where(finite, router_weights.to_numpy(), 0.0).sum(axis=1)
        score = np.divide(
            numerator,
            denominator,
            out=np.full(len(current_indices), np.nan),
            where=denominator > 0,
        )
        result.loc[current_indices] = score
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "regime": regime,
            "trailing_six_month_market_return": float(trailing_six.loc[month]),
            "audit_start": str(complete_history.index[0].date()),
            "audit_end": str(complete_history.index[-1].date()),
            "audit_history_months": len(complete_history),
            "regime_audit_months": len(audit),
            "regime_sparse_fallback": sparse_fallback,
            "single_market_pool_count": len(expected_experts) * 3,
            "admitted_pool_members": len(expected_experts) * admitted_per_pool,
            "finite_scores": int(np.isfinite(score).sum()),
        }
        for expert in expected_experts:
            row[f"selected__{expert}"] = "|".join(selected_by_expert[expert])
            row[f"pool_performance__{expert}"] = expert_performance[expert]
            row[f"pool_robustness__{expert}"] = expert_robustness[expert]
            row[f"router_weight__{expert}"] = float(router_weights[expert])
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def trading_r1_reward_policy_scores(
    frame: pd.DataFrame,
    reasoning_groups: dict[str, list[tuple[str, int]]],
    *,
    action_names: list[str],
    action_values: list[float],
    truth_quantiles: list[float],
    reward_matrix: np.ndarray,
    common_start: str,
    label_horizons: list[int],
    horizon_weights: list[float],
    volatility_lookback_months: int = 20,
    label_purge_months: int = 6,
    policy_training_months: int = 60,
    ridge_lambda: float = 10.0,
    confidence_scale: float = 0.10,
) -> tuple[pd.Series, pd.DataFrame]:
    """Fit a past-only five-action Trading-R1-style contextual reward policy."""
    expected_groups = ["technical", "fundamental", "sentiment"]
    expected_actions = ["STRONG SELL", "SELL", "HOLD", "BUY", "STRONG BUY"]
    if list(reasoning_groups) != expected_groups:
        raise ValueError("Trading-R1 requires the three frozen reasoning groups in order")
    if action_names != expected_actions or action_values != [-1.0, -0.5, 0.0, 0.5, 1.0]:
        raise ValueError("Trading-R1 five-action ordering changed")
    if truth_quantiles != [0.03, 0.15, 0.53, 0.85]:
        raise ValueError("Trading-R1 truth quantiles changed")
    if reward_matrix.shape != (5, 5):
        raise ValueError("Trading-R1 decision reward matrix must be five by five")
    if label_horizons != [1, 3, 6] or horizon_weights != [0.3, 0.5, 0.2]:
        raise ValueError("Trading-R1 multi-horizon label policy changed")
    if label_purge_months < max(label_horizons):
        raise ValueError("Trading-R1 label purge is shorter than the longest horizon")
    specifications = [
        specification
        for group_specifications in reasoning_groups.values()
        for specification in group_specifications
    ]
    features = list(dict.fromkeys(feature for feature, _ in specifications))
    missing = {"month", "security_id", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing Trading-R1 inputs: {sorted(missing)}")
    if any(sign not in {-1, 1} for _, sign in specifications):
        raise ValueError("Trading-R1 reasoning feature signs must be -1 or 1")

    ranked = cross_sectional_unit_rank(frame, features)
    group_raw: dict[str, pd.Series] = {}
    for group, group_specifications in reasoning_groups.items():
        signed = pd.concat(
            [ranked[feature] * sign for feature, sign in group_specifications],
            axis=1,
        )
        group_raw[group] = signed.mean(axis=1, skipna=False)
    group_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(group_raw)], axis=1),
        expected_groups,
    )
    evidence_raw = pd.DataFrame(index=frame.index)
    evidence_raw[expected_groups] = group_scores[expected_groups]
    evidence_raw["consensus"] = group_scores.mean(axis=1, skipna=False)
    evidence_raw["dispersion"] = group_scores.std(axis=1, ddof=0, skipna=False)
    evidence_raw["technical_x_fundamental"] = group_scores["technical"] * group_scores["fundamental"]
    evidence_raw["technical_x_sentiment"] = group_scores["technical"] * group_scores["sentiment"]
    evidence_raw["fundamental_x_sentiment"] = group_scores["fundamental"] * group_scores["sentiment"]
    evidence_columns = list(evidence_raw)
    evidence = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], evidence_raw], axis=1),
        evidence_columns,
    )

    ordered = frame[["security_id", "month", "ret_exc_lead1m"]].copy().sort_values(
        ["security_id", "month"],
        kind="mergesort",
    )
    forward_scores: dict[int, pd.Series] = {}
    for horizon in label_horizons:
        components = []
        for offset in range(horizon):
            shifted_return = ordered.groupby("security_id")["ret_exc_lead1m"].shift(-offset)
            shifted_month = ordered.groupby("security_id")["month"].shift(-offset)
            expected_month = ordered["month"] + pd.offsets.MonthEnd(offset)
            components.append(shifted_return.where(shifted_month.eq(expected_month)))
        component_frame = pd.concat(components, axis=1)
        forward = (1.0 + component_frame).prod(axis=1, min_count=horizon) - 1.0
        volatility = (
            forward.groupby(ordered["security_id"])
            .rolling(volatility_lookback_months, min_periods=volatility_lookback_months)
            .std(ddof=1)
            .reset_index(level=0, drop=True)
        )
        normalized = forward / volatility.replace(0.0, np.nan)
        forward_scores[horizon] = normalized.reindex(frame.index)
    label_signal = sum(
        weight * forward_scores[horizon]
        for horizon, weight in zip(label_horizons, horizon_weights)
    )

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    common_months = sorted(
        pd.Timestamp(month)
        for month in frame.loc[frame["month"] >= common_start, "month"].unique()
    )
    action_value_array = np.asarray(action_values, dtype=float)
    for month in common_months:
        label_cutoff = month - pd.offsets.MonthEnd(label_purge_months)
        eligible_months = sorted(
            pd.Timestamp(value)
            for value in frame.loc[frame["month"] <= label_cutoff, "month"].unique()
        )[-policy_training_months:]
        if len(eligible_months) != policy_training_months:
            raise ValueError(f"Trading-R1 policy history is incomplete at {month.date()}")
        training_indices = frame.index[frame["month"].isin(eligible_months)]
        training_signal = label_signal.loc[training_indices]
        valid = training_signal.notna()
        if valid.sum() <= len(evidence_columns) + 1:
            raise ValueError(f"Trading-R1 has too few realized labels at {month.date()}")
        thresholds = training_signal.loc[valid].quantile(truth_quantiles).to_numpy(dtype=float)
        truth = np.searchsorted(
            thresholds,
            training_signal.loc[valid].to_numpy(dtype=float),
            side="right",
        )
        x_train = evidence.loc[training_indices[valid], evidence_columns].fillna(0.0).to_numpy(dtype=float)
        x_train = np.column_stack([x_train, np.ones(len(x_train))])
        rewards = reward_matrix[:, truth].T
        penalty = ridge_lambda * np.eye(x_train.shape[1])
        penalty[-1, -1] = 0.0
        coefficients = np.linalg.solve(
            x_train.T @ x_train + penalty,
            x_train.T @ rewards,
        )
        indices = month_groups[month]
        current = evidence.loc[indices, evidence_columns].fillna(0.0).to_numpy(dtype=float)
        current = np.column_stack([current, np.ones(len(current))])
        predicted_rewards = current @ coefficients
        centered_rewards = predicted_rewards - predicted_rewards.mean(axis=1, keepdims=True)
        chosen = np.argmax(centered_rewards, axis=1)
        sorted_rewards = np.sort(centered_rewards, axis=1)
        margin = sorted_rewards[:, -1] - sorted_rewards[:, -2]
        score = action_value_array[chosen] + confidence_scale * np.tanh(margin)
        result.loc[indices] = score
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "label_cutoff": str(label_cutoff.date()),
            "training_start": str(eligible_months[0].date()),
            "training_end": str(eligible_months[-1].date()),
            "policy_training_months": len(eligible_months),
            "training_rows": int(valid.sum()),
            "ridge_coefficient_norm": float(np.linalg.norm(coefficients)),
            "mean_group_relative_advantage": float(
                centered_rewards[np.arange(len(chosen)), chosen].mean()
            ),
            "mean_best_second_reward_margin": float(margin.mean()),
            "finite_scores": int(np.isfinite(score).sum()),
        }
        for quantile, threshold in zip(truth_quantiles, thresholds):
            row[f"label_threshold_q{int(quantile * 100):02d}"] = float(threshold)
        for action, action_number in zip(action_names, range(len(action_names))):
            row[f"action_count__{action.lower().replace(' ', '_')}"] = int(
                np.sum(chosen == action_number)
            )
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def quantagents_meeting_scores(
    frame: pd.DataFrame,
    strategy_pool: dict[str, list[tuple[str, int]]],
    *,
    common_start: str,
    memory_history_months: int = 120,
    retrieved_similar_cases: int = 10,
    new_strategy_members: int = 3,
    market_report_weight: float = 0.2,
    strategy_policy_weight: float = 0.8,
    adaptive_reward_window: int = 12,
    risk_component_weights: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25),
    risk_alert_threshold: float = 0.75,
    risk_policy_weight_when_triggered: float = 0.5,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run deterministic QuantAgents meetings, memories, and dual rewards."""
    expected_pool = [
        "momentum_short",
        "momentum_medium",
        "momentum_long",
        "breakout",
        "reversal",
        "value_quality",
        "sentiment_surprise",
        "low_risk",
        "financial_safety",
        "balanced_multi_factor",
    ]
    if list(strategy_pool) != expected_pool:
        raise ValueError("QuantAgents requires the ten frozen strategy-pool members")
    if retrieved_similar_cases != 10 or new_strategy_members != 3:
        raise ValueError("QuantAgents retrieval or proposed-strategy count changed")
    if market_report_weight + strategy_policy_weight != 1.0:
        raise ValueError("QuantAgents policy and market-report weights must sum to one")
    if not np.isclose(sum(risk_component_weights), 1.0):
        raise ValueError("QuantAgents risk weights must sum to one")
    specifications = [
        specification
        for strategy_specifications in strategy_pool.values()
        for specification in strategy_specifications
    ]
    features = list(dict.fromkeys(feature for feature, _ in specifications))
    missing = {"month", "security_id", "ret", "weight", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing QuantAgents inputs: {sorted(missing)}")
    if any(sign not in {-1, 1} for _, sign in specifications):
        raise ValueError("QuantAgents strategy signs must be -1 or 1")

    ranked = cross_sectional_unit_rank(frame, features)
    strategy_raw: dict[str, pd.Series] = {}
    for strategy, strategy_specifications in strategy_pool.items():
        signed = pd.concat(
            [ranked[feature] * sign for feature, sign in strategy_specifications],
            axis=1,
        )
        strategy_raw[strategy] = signed.mean(axis=1, skipna=False)
    strategy_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(strategy_raw)], axis=1),
        expected_pool,
    )
    strategy_rankics = monthly_rankic(frame, strategy_scores)
    market_report = cross_sectional_unit_rank(
        pd.DataFrame(
            {
                "month": frame["month"],
                "report": strategy_scores[["sentiment_surprise", "momentum_short"]].mean(
                    axis=1,
                    skipna=False,
                ),
            }
        ),
        ["report"],
    )["report"]
    defensive = cross_sectional_unit_rank(
        pd.DataFrame(
            {
                "month": frame["month"],
                "defensive": strategy_scores[["low_risk", "financial_safety"]].mean(
                    axis=1,
                    skipna=False,
                ),
            }
        ),
        ["defensive"],
    )["defensive"]

    state_rows = []
    risk_rows = []
    for month, indices in frame.groupby("month", sort=True).groups.items():
        weights = pd.to_numeric(frame.loc[indices, "weight"], errors="coerce")
        weights = weights / weights.sum()
        returns = pd.to_numeric(frame.loc[indices, "ret"], errors="coerce").fillna(0.0)

        def weighted_mean(values: pd.Series) -> float:
            valid = values.notna() & weights.notna()
            if not valid.any():
                return float("nan")
            normalized = weights.loc[valid] / weights.loc[valid].sum()
            return float(np.sum(normalized * values.loc[valid]))

        state_rows.append(
            {
                "month": pd.Timestamp(month),
                "market_return": float(np.sum(weights * returns)),
                "weighted_momentum": weighted_mean(ranked.loc[indices, "ret_12_1"]),
                "weighted_value": weighted_mean(ranked.loc[indices, "be_me"]),
                "weighted_sentiment": weighted_mean(strategy_scores.loc[indices, "sentiment_surprise"]),
            }
        )
        risk_rows.append(
            {
                "month": pd.Timestamp(month),
                "market_beta": weighted_mean(ranked.loc[indices, "beta_60m"].abs()),
                "liquidity": weighted_mean((ranked.loc[indices, "turnover_126d"] + 1.0) / 2.0),
                "concentration": float(np.sum(weights**2)),
            }
        )
    states = pd.DataFrame(state_rows).set_index("month")
    states["market_volatility_6m"] = states["market_return"].rolling(6, min_periods=2).std(ddof=1).fillna(0.0)
    states = states[
        [
            "market_return",
            "market_volatility_6m",
            "weighted_momentum",
            "weighted_value",
            "weighted_sentiment",
        ]
    ]
    risk_states = pd.DataFrame(risk_rows).set_index("month")
    risk_states["market_volatility_6m"] = states["market_volatility_6m"]

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    common_months = sorted(
        pd.Timestamp(month)
        for month in frame.loc[frame["month"] >= common_start, "month"].unique()
    )
    simulated_rewards: list[float] = []
    real_rewards: list[float] = []
    deployed_members: list[str] = []
    for month in common_months:
        memory = states.loc[states.index < month].tail(memory_history_months)
        if len(memory) != memory_history_months or not np.isfinite(memory.to_numpy()).all():
            raise ValueError(f"QuantAgents memory history is incomplete at {month.date()}")
        mean = memory.mean()
        scale = memory.std(ddof=1).replace(0.0, 1.0)
        current_state = states.loc[month]
        distance = ((memory - mean) / scale - (current_state - mean) / scale).pow(2).sum(axis=1).pow(0.5)
        retrieved = sorted(distance.index, key=lambda value: (float(distance[value]), value))[
            :retrieved_similar_cases
        ]
        simulated_history = strategy_rankics.loc[retrieved, expected_pool]
        utility = simulated_history.mean() - 0.5 * simulated_history.std(ddof=1)
        proposed = sorted(expected_pool, key=lambda name: (-float(utility[name]), name))[
            :new_strategy_members
        ]
        simulated_reward = float(utility[proposed].mean())
        latest_real_month = strategy_rankics.index[strategy_rankics.index < month][-1]
        if deployed_members:
            real_reward = float(strategy_rankics.loc[latest_real_month, deployed_members].mean())
        else:
            deployed_members = list(proposed)
            real_reward = simulated_reward
        simulated_rewards.append(simulated_reward)
        real_rewards.append(real_reward)
        sim_sum = float(np.sum(simulated_rewards[-adaptive_reward_window:]))
        real_sum = float(np.sum(real_rewards[-adaptive_reward_window:]))
        ratio = sim_sum / (abs(sim_sum) + abs(real_sum) + 1e-12)
        simulated_weight = float(1.0 / (1.0 + np.exp(-ratio)))
        real_weight = 1.0 - simulated_weight

        indices = month_groups[month]
        proposed_score = strategy_scores.loc[indices, proposed].mean(axis=1, skipna=False)
        deployed_score = strategy_scores.loc[indices, deployed_members].mean(axis=1, skipna=False)
        policy_score = simulated_weight * proposed_score + real_weight * deployed_score
        integrated = (
            strategy_policy_weight * policy_score
            + market_report_weight * market_report.loc[indices]
        )

        risk_history = risk_states.loc[risk_states.index < month].tail(memory_history_months)
        current_risk = risk_states.loc[month]

        def percentile(name: str, value: float) -> float:
            series = risk_history[name].dropna()
            return float((series <= value).mean())

        risk_components = np.asarray(
            [
                percentile("market_beta", float(current_risk["market_beta"])),
                1.0 - percentile("liquidity", float(current_risk["liquidity"])),
                percentile("concentration", float(current_risk["concentration"])),
                percentile(
                    "market_volatility_6m",
                    float(current_risk["market_volatility_6m"]),
                ),
            ]
        )
        risk_score = float(risk_components @ np.asarray(risk_component_weights))
        risk_trigger = risk_score > risk_alert_threshold
        final = integrated.copy()
        if risk_trigger:
            final = (
                (1.0 - risk_policy_weight_when_triggered) * integrated
                + risk_policy_weight_when_triggered * defensive.loc[indices]
            )
        result.loc[indices] = final
        diagnostics.append(
            {
                "formation_month": str(month.date()),
                "memory_start": str(memory.index[0].date()),
                "memory_end": str(memory.index[-1].date()),
                "memory_history_months": len(memory),
                "memory_type_count": 3,
                "retrieved_similar_cases": len(retrieved),
                "retrieved_months": "|".join(str(value.date()) for value in retrieved),
                "strategy_pool_size": len(expected_pool),
                "proposed_strategy_members": "|".join(proposed),
                "deployed_strategy_members": "|".join(deployed_members),
                "simulated_reward": simulated_reward,
                "real_reward": real_reward,
                "simulated_reward_weight": simulated_weight,
                "real_reward_weight": real_weight,
                "risk_beta_component": float(risk_components[0]),
                "risk_inverse_liquidity_component": float(risk_components[1]),
                "risk_concentration_component": float(risk_components[2]),
                "risk_volatility_component": float(risk_components[3]),
                "risk_score": risk_score,
                "risk_alert_triggered": risk_trigger,
                "finite_scores": int(final.notna().sum()),
            }
        )
        deployed_members = list(proposed)
    return result, pd.DataFrame(diagnostics)


def factfin_counterfactual_mcts_scores(
    frame: pd.DataFrame,
    rag_state: dict[str, list[tuple[str, int]]],
    *,
    common_start: str,
    training_start: str,
    training_end: str,
    validation_start: str,
    validation_end: str,
    initial_weights: list[float],
    mutation_step: float = 0.25,
    weight_bounds: tuple[float, float] = (-1.0, 1.0),
    hold_band: tuple[float, float] = (-0.2, 0.2),
    mcts_depth: int = 10,
    ucb_exploration_constant: float = 0.5,
    mcts_iterations: int = 100,
    counterfactual_finalists: int = 10,
    counterfactual_scenarios: int = 50,
    counterfactual_seed: int = 79020,
    final_objective_weights: dict[str, float] | None = None,
) -> tuple[pd.Series, pd.DataFrame, dict[str, object]]:
    """Run a deterministic leakage-safe FactFin-style MCTS and counterfactual audit."""
    expected_groups = ["price", "factors", "factorized_news"]
    if list(rag_state) != expected_groups:
        raise ValueError("FactFin requires price, factors, and factorized-news state")
    if mcts_depth != 10 or ucb_exploration_constant != 0.5:
        raise ValueError("FactFin MCTS depth or UCB constant changed")
    if mcts_iterations != 100 or counterfactual_scenarios != 50:
        raise ValueError("FactFin search or counterfactual budget changed")
    objective_weights = final_objective_weights or {
        "validation_rankic": 1.0,
        "prediction_consistency": -0.01,
        "confidence_invariance": -0.01,
        "input_dependency_score": 0.01,
    }
    if objective_weights != {
        "validation_rankic": 1.0,
        "prediction_consistency": -0.01,
        "confidence_invariance": -0.01,
        "input_dependency_score": 0.01,
    }:
        raise ValueError("FactFin counterfactual objective changed")
    specifications = [
        specification
        for group_specifications in rag_state.values()
        for specification in group_specifications
    ]
    features = list(dict.fromkeys(feature for feature, _ in specifications))
    missing = {"month", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing FactFin inputs: {sorted(missing)}")
    if any(sign not in {-1, 1} for _, sign in specifications):
        raise ValueError("FactFin state feature signs must be -1 or 1")

    train_start = pd.Timestamp(training_start)
    train_end = pd.Timestamp(training_end)
    valid_start = pd.Timestamp(validation_start)
    valid_end = pd.Timestamp(validation_end)
    train_months = sorted(frame.loc[frame["month"].between(train_start, train_end), "month"].unique())
    validation_months = sorted(frame.loc[frame["month"].between(valid_start, valid_end), "month"].unique())
    if len(train_months) != 96 or len(validation_months) != 24 or train_end >= valid_start:
        raise ValueError("FactFin requires the frozen 96/24-month chronological split")

    ranked = cross_sectional_unit_rank(frame, features)
    group_raw: dict[str, pd.Series] = {}
    for group, group_specifications in rag_state.items():
        signed = pd.concat(
            [ranked[feature] * sign for feature, sign in group_specifications],
            axis=1,
        )
        group_raw[group] = signed.mean(axis=1, skipna=False)
    group_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(group_raw)], axis=1),
        expected_groups,
    )
    search_mask = frame["month"].between(train_start, valid_end)
    search_frame = frame.loc[search_mask]
    search_groups = group_scores.loc[search_frame.index, expected_groups]

    def normalize_weights(values: np.ndarray) -> tuple[float, float, float]:
        values = np.clip(values, weight_bounds[0], weight_bounds[1])
        norm = float(np.abs(values).sum())
        if norm == 0:
            values = np.asarray(initial_weights, dtype=float)
            norm = float(np.abs(values).sum())
        return tuple(float(np.round(value / norm, 12)) for value in values)

    def ranked_strategy(values: pd.DataFrame, weights: tuple[float, float, float], months: pd.Series) -> pd.Series:
        raw = values.to_numpy(dtype=float) @ np.asarray(weights, dtype=float)
        score = pd.Series(raw, index=values.index)
        return cross_sectional_unit_rank(
            pd.DataFrame({"month": months, "score": score}),
            ["score"],
        )["score"]

    reward_cache: dict[tuple[float, float, float], float] = {}

    def training_reward(weights: tuple[float, float, float]) -> float:
        if weights in reward_cache:
            return reward_cache[weights]
        score = ranked_strategy(search_groups, weights, search_frame["month"])
        rankic = monthly_rankic(
            search_frame,
            pd.DataFrame({"score": score}),
        )["score"]
        reward = float(rankic.loc[(rankic.index >= train_start) & (rankic.index <= train_end)].mean())
        reward_cache[weights] = reward
        return reward

    actions = [(dimension, direction) for dimension in range(3) for direction in (-1, 1)]
    rng = np.random.default_rng(counterfactual_seed)
    root_weights = normalize_weights(np.asarray(initial_weights, dtype=float))
    nodes: list[dict[str, object]] = [
        {
            "weights": root_weights,
            "parent": None,
            "depth": 0,
            "children": [],
            "untried": list(actions),
            "visits": 0,
            "total_reward": 0.0,
        }
    ]
    history_rows: list[dict[str, object]] = []

    def record_evaluation(node_index: int, iteration: int) -> None:
        node = nodes[node_index]
        weights = node["weights"]
        reward = training_reward(weights)
        current = node_index
        while current is not None:
            nodes[current]["visits"] = int(nodes[current]["visits"]) + 1
            nodes[current]["total_reward"] = float(nodes[current]["total_reward"]) + reward
            current = nodes[current]["parent"]
        history_rows.append(
            {
                "iteration": iteration,
                "node_id": node_index,
                "parent_id": -1 if node["parent"] is None else int(node["parent"]),
                "depth": int(node["depth"]),
                "price_weight": float(weights[0]),
                "factor_weight": float(weights[1]),
                "news_weight": float(weights[2]),
                "training_mean_rankic": reward,
            }
        )

    record_evaluation(0, 1)
    for iteration in range(2, mcts_iterations + 1):
        node_index = 0
        while int(nodes[node_index]["depth"]) < mcts_depth:
            untried = nodes[node_index]["untried"]
            if untried:
                action_index = int(rng.integers(len(untried)))
                dimension, direction = untried.pop(action_index)
                child_values = np.asarray(nodes[node_index]["weights"], dtype=float)
                child_values[dimension] += direction * mutation_step
                child_weights = normalize_weights(child_values)
                child_index = len(nodes)
                nodes.append(
                    {
                        "weights": child_weights,
                        "parent": node_index,
                        "depth": int(nodes[node_index]["depth"]) + 1,
                        "children": [],
                        "untried": list(actions),
                        "visits": 0,
                        "total_reward": 0.0,
                    }
                )
                nodes[node_index]["children"].append(child_index)
                node_index = child_index
                break
            parent_visits = max(1, int(nodes[node_index]["visits"]))

            def ucb(child_index: int) -> float:
                child = nodes[child_index]
                visits = max(1, int(child["visits"]))
                mean_reward = float(child["total_reward"]) / visits
                return mean_reward + ucb_exploration_constant * np.sqrt(
                    np.log(parent_visits + 1) / visits
                )

            node_index = sorted(
                nodes[node_index]["children"],
                key=lambda child_index: (
                    -ucb(child_index),
                    tuple(nodes[child_index]["weights"]),
                    child_index,
                ),
            )[0]
        record_evaluation(node_index, iteration)

    unique_nodes: dict[tuple[float, float, float], dict[str, object]] = {}
    for row in history_rows:
        weights = (
            float(row["price_weight"]),
            float(row["factor_weight"]),
            float(row["news_weight"]),
        )
        current = unique_nodes.get(weights)
        if current is None or float(row["training_mean_rankic"]) > float(current["training_mean_rankic"]):
            unique_nodes[weights] = row
    finalists = sorted(
        unique_nodes.values(),
        key=lambda row: (
            -float(row["training_mean_rankic"]),
            float(row["price_weight"]),
            float(row["factor_weight"]),
            float(row["news_weight"]),
        ),
    )[:counterfactual_finalists]
    if len(finalists) != counterfactual_finalists:
        raise ValueError("FactFin MCTS produced too few distinct finalists")

    validation_mask = frame["month"].between(valid_start, valid_end)
    validation_frame = frame.loc[validation_mask]
    validation_groups = group_scores.loc[validation_frame.index, expected_groups]
    month_positions = [
        np.flatnonzero(validation_frame["month"].to_numpy() == month)
        for month in validation_months
    ]
    counterfactual_groups: list[np.ndarray] = []
    validation_values = validation_groups.to_numpy(dtype=float)
    for scenario in range(counterfactual_scenarios):
        changed = validation_values.copy()
        dimension = scenario % len(expected_groups)
        for positions in month_positions:
            changed[positions, dimension] = changed[rng.permutation(positions), dimension]
        counterfactual_groups.append(changed)

    def action_probabilities(score: np.ndarray) -> np.ndarray:
        logits = np.column_stack([-2.0 * score, -2.0 * np.abs(score), 2.0 * score])
        logits -= logits.max(axis=1, keepdims=True)
        probability = np.exp(logits)
        return probability / probability.sum(axis=1, keepdims=True)

    finalist_metrics: dict[tuple[float, float, float], dict[str, float]] = {}
    for finalist in finalists:
        weights = (
            float(finalist["price_weight"]),
            float(finalist["factor_weight"]),
            float(finalist["news_weight"]),
        )
        original = ranked_strategy(validation_groups, weights, validation_frame["month"])
        validation_rankic = monthly_rankic(
            validation_frame,
            pd.DataFrame({"score": original}),
        )["score"].mean()
        original_values = original.to_numpy(dtype=float)
        original_actions = np.where(
            original_values > hold_band[1],
            1,
            np.where(original_values < hold_band[0], -1, 0),
        )
        consistency = []
        invariance = []
        dependency = []
        for changed in counterfactual_groups:
            changed_frame = pd.DataFrame(changed, index=validation_frame.index, columns=expected_groups)
            counterfactual = ranked_strategy(
                changed_frame,
                weights,
                validation_frame["month"],
            ).to_numpy(dtype=float)
            counterfactual_actions = np.where(
                counterfactual > hold_band[1],
                1,
                np.where(counterfactual < hold_band[0], -1, 0),
            )
            valid_pair = np.isfinite(original_values) & np.isfinite(counterfactual)
            if valid_pair.sum() < 20:
                raise ValueError("FactFin counterfactual scenario has insufficient overlap")
            consistency.append(
                float(np.mean(original_actions[valid_pair] == counterfactual_actions[valid_pair]))
            )
            invariance.append(
                float(
                    1.0
                    - np.mean(
                        np.abs(
                            np.abs(original_values[valid_pair])
                            - np.abs(counterfactual[valid_pair])
                        )
                    )
                )
            )
            original_probability = action_probabilities(original_values[valid_pair])
            counterfactual_probability = action_probabilities(counterfactual[valid_pair])
            dependency.append(
                float(
                    np.mean(
                        np.sum(
                            original_probability
                            * np.log(
                                np.clip(original_probability, 1e-12, None)
                                / np.clip(counterfactual_probability, 1e-12, None)
                            ),
                            axis=1,
                        )
                    )
                )
            )
        metrics = {
            "validation_rankic": float(validation_rankic),
            "prediction_consistency": float(np.mean(consistency)),
            "confidence_invariance": float(np.mean(invariance)),
            "input_dependency_score": float(np.mean(dependency)),
        }
        metrics["counterfactual_objective"] = float(
            sum(objective_weights[name] * metrics[name] for name in objective_weights)
        )
        finalist_metrics[weights] = metrics
    selected_row = sorted(
        finalists,
        key=lambda row: (
            -finalist_metrics[
                (
                    float(row["price_weight"]),
                    float(row["factor_weight"]),
                    float(row["news_weight"]),
                )
            ]["counterfactual_objective"],
            float(row["price_weight"]),
            float(row["factor_weight"]),
            float(row["news_weight"]),
        ),
    )[0]
    selected_weights = (
        float(selected_row["price_weight"]),
        float(selected_row["factor_weight"]),
        float(selected_row["news_weight"]),
    )
    for row in history_rows:
        weights = (
            float(row["price_weight"]),
            float(row["factor_weight"]),
            float(row["news_weight"]),
        )
        row["counterfactual_finalist"] = weights in finalist_metrics
        row["selected_final"] = weights == selected_weights and int(row["node_id"]) == int(selected_row["node_id"])
        for metric in [
            "validation_rankic",
            "prediction_consistency",
            "confidence_invariance",
            "input_dependency_score",
            "counterfactual_objective",
        ]:
            row[metric] = finalist_metrics.get(weights, {}).get(metric, np.nan)

    final_score = ranked_strategy(group_scores, selected_weights, frame["month"])
    final_score = final_score.where(frame["month"] >= pd.Timestamp(common_start))
    selected_metrics = finalist_metrics[selected_weights]
    summary = {
        "selected_weights": list(selected_weights),
        "selected_training_mean_rankic": float(selected_row["training_mean_rankic"]),
        **selected_metrics,
        "mcts_iterations": len(history_rows),
        "distinct_programs": len(unique_nodes),
        "counterfactual_finalists": len(finalists),
        "counterfactual_scenarios": counterfactual_scenarios,
    }
    return final_score, pd.DataFrame(history_rows), summary


def atlas_adaptive_opro_scores(
    frame: pd.DataFrame,
    analysts: dict[str, list[tuple[str, int]]],
    *,
    common_start: str,
    evaluation_window_decisions: int = 5,
    initial_analyst_weights: dict[str, float] | None = None,
    initial_hold_threshold: float = 0.1,
    hold_threshold_bounds: tuple[float, float] = (0.0, 0.4),
    poor_window_threshold_increment: float = 0.05,
    successful_window_threshold_decrement: float = 0.02,
    analyst_weight_update_rate: float = 0.25,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a deterministic ATLAS-style five-decision Adaptive-OPRO loop."""
    expected_analysts = ["market", "news", "fundamental"]
    if list(analysts) != expected_analysts:
        raise ValueError("ATLAS requires the three frozen analysts in order")
    if evaluation_window_decisions != 5:
        raise ValueError("ATLAS requires five-decision evaluation windows")
    weights = pd.Series(
        initial_analyst_weights
        or {name: 1.0 / len(expected_analysts) for name in expected_analysts},
        dtype=float,
    ).reindex(expected_analysts)
    if not np.isclose(weights.sum(), 1.0) or (weights <= 0).any():
        raise ValueError("ATLAS analyst weights must be positive and sum to one")
    specifications = [
        specification
        for analyst_specifications in analysts.values()
        for specification in analyst_specifications
    ]
    features = list(dict.fromkeys(feature for feature, _ in specifications))
    missing = {"month", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing ATLAS inputs: {sorted(missing)}")
    if any(sign not in {-1, 1} for _, sign in specifications):
        raise ValueError("ATLAS analyst feature signs must be -1 or 1")

    ranked = cross_sectional_unit_rank(frame, features)
    analyst_raw: dict[str, pd.Series] = {}
    for analyst, analyst_specifications in analysts.items():
        signed = pd.concat(
            [ranked[feature] * sign for feature, sign in analyst_specifications],
            axis=1,
        )
        analyst_raw[analyst] = signed.mean(axis=1, skipna=False)
    analyst_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(analyst_raw)], axis=1),
        expected_analysts,
    )

    common_months = sorted(
        pd.Timestamp(month)
        for month in frame.loc[frame["month"] >= common_start, "month"].unique()
    )
    if len(common_months) % evaluation_window_decisions:
        raise ValueError("ATLAS common calendar does not partition into five-decision windows")
    month_groups = frame.groupby("month", sort=False).groups
    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    history: list[dict[str, object]] = []
    hold_threshold = initial_hold_threshold

    def monthly_decile_return(score: pd.Series, indices: pd.Index) -> float:
        values = score.loc[indices]
        outcome = pd.to_numeric(frame.loc[indices, "ret_exc_lead1m"], errors="coerce")
        valid = values.notna() & outcome.notna()
        values = values.loc[valid]
        outcome = outcome.loc[valid]
        if len(values) < 20:
            raise ValueError("ATLAS window return has insufficient score coverage")
        low = values.quantile(0.1)
        high = values.quantile(0.9)
        return float(outcome.loc[values >= high].mean() - outcome.loc[values <= low].mean())

    windows = [
        common_months[start : start + evaluation_window_decisions]
        for start in range(0, len(common_months), evaluation_window_decisions)
    ]
    for version, window in enumerate(windows):
        prompt_scores: dict[pd.Timestamp, pd.Series] = {}
        for month in window:
            indices = month_groups[month]
            raw = analyst_scores.loc[indices, expected_analysts].mul(weights, axis=1).sum(
                axis=1,
                min_count=len(expected_analysts),
            )
            order_score = raw.where(raw.abs() >= hold_threshold, 0.0)
            result.loc[indices] = order_score
            prompt_scores[month] = order_score

        central_returns = [
            monthly_decile_return(prompt_scores[month], month_groups[month])
            for month in window
        ]
        analyst_returns = {
            analyst: [
                monthly_decile_return(
                    analyst_scores.loc[month_groups[month], analyst],
                    month_groups[month],
                )
                for month in window
            ]
            for analyst in expected_analysts
        }
        window_roi = float(np.prod(1.0 + np.asarray(central_returns)) - 1.0)
        standalone_roi = pd.Series(
            {
                analyst: float(np.prod(1.0 + np.asarray(returns)) - 1.0)
                for analyst, returns in analyst_returns.items()
            }
        )
        feedback_score = float(np.clip(50.0 + 250.0 * window_roi, 0.0, 100.0))
        next_weights = weights.copy()
        next_threshold = hold_threshold
        update_applied = version < len(windows) - 1
        if update_applied:
            deviation = float(standalone_roi.std(ddof=0))
            diagnosis = (
                (standalone_roi - standalone_roi.mean()) / deviation
                if deviation > 0
                else pd.Series(0.0, index=standalone_roi.index)
            )
            logits = np.log(weights) + analyst_weight_update_rate * diagnosis
            next_weights = np.exp(logits - logits.max())
            next_weights /= next_weights.sum()
            if feedback_score < 50.0:
                next_threshold = min(
                    hold_threshold_bounds[1],
                    hold_threshold + poor_window_threshold_increment,
                )
            else:
                next_threshold = max(
                    hold_threshold_bounds[0],
                    hold_threshold - successful_window_threshold_decrement,
                )
        action_scores = pd.concat(prompt_scores.values())
        row: dict[str, object] = {
            "prompt_version": version,
            "window_start": str(window[0].date()),
            "window_end": str(window[-1].date()),
            "window_decisions": len(window),
            "window_roi": window_roi,
            "feedback_score": feedback_score,
            "hold_threshold": hold_threshold,
            "next_hold_threshold": next_threshold,
            "update_applied": update_applied,
            "buy_count": int((action_scores > 0).sum()),
            "hold_count": int((action_scores == 0).sum()),
            "sell_count": int((action_scores < 0).sum()),
            "finite_scores": int(action_scores.notna().sum()),
        }
        for analyst in expected_analysts:
            row[f"analyst_weight__{analyst}"] = float(weights[analyst])
            row[f"standalone_roi__{analyst}"] = float(standalone_roi[analyst])
            row[f"next_analyst_weight__{analyst}"] = float(next_weights[analyst])
        history.append(row)
        weights = next_weights
        hold_threshold = next_threshold
    return result, pd.DataFrame(history)


def p1gpt_layered_workflow_scores(
    frame: pd.DataFrame,
    domain_agents: dict[str, list[tuple[str, int]]],
    risk_features: list[tuple[str, int]],
    *,
    integration_median_weight: float = 0.75,
    integration_mean_weight: float = 0.25,
    decision_integration_weight: float = 0.8,
    decision_risk_weight: float = 0.2,
    minimum_trade_confidence: float = 0.35,
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a deterministic five-layer P1GPT-style workflow."""
    expected_domains = ["fundamental", "technical", "semiconductor_cycle", "news"]
    if list(domain_agents) != expected_domains:
        raise ValueError("P1GPT requires the four frozen domain agents in order")
    if integration_median_weight + integration_mean_weight != 1.0:
        raise ValueError("P1GPT integration weights must sum to one")
    if decision_integration_weight + decision_risk_weight != 1.0:
        raise ValueError("P1GPT decision weights must sum to one")
    specifications = [
        *[
            specification
            for agent_specifications in domain_agents.values()
            for specification in agent_specifications
        ],
        *risk_features,
    ]
    features = list(dict.fromkeys(feature for feature, _ in specifications))
    missing = {"month", *features} - set(frame)
    if missing:
        raise ValueError(f"missing P1GPT inputs: {sorted(missing)}")
    if any(sign not in {-1, 1} for _, sign in specifications):
        raise ValueError("P1GPT feature signs must be -1 or 1")

    ranked = cross_sectional_unit_rank(frame, features)
    domain_raw: dict[str, pd.Series] = {}
    for agent, agent_specifications in domain_agents.items():
        signed = pd.concat(
            [ranked[feature] * sign for feature, sign in agent_specifications],
            axis=1,
        )
        domain_raw[agent] = signed.mean(axis=1, skipna=False)
    domain_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(domain_raw)], axis=1),
        expected_domains,
    )
    supporting_raw = pd.DataFrame(
        {
            "external_search": domain_scores[["fundamental", "news"]].mean(
                axis=1,
                skipna=False,
            ),
            "revenue_forecasting": domain_scores[
                ["fundamental", "semiconductor_cycle"]
            ].mean(axis=1, skipna=False),
            "market_trend": domain_scores[["technical", "semiconductor_cycle"]].mean(
                axis=1,
                skipna=False,
            ),
        },
        index=frame.index,
    )
    supporting_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], supporting_raw], axis=1),
        list(supporting_raw),
    )
    reports = pd.concat([domain_scores, supporting_scores], axis=1)
    recommendation = reports.median(axis=1, skipna=False)
    integration = (
        integration_median_weight * recommendation
        + integration_mean_weight * reports.mean(axis=1, skipna=False)
    )
    risk_signed = pd.concat(
        [ranked[feature] * sign for feature, sign in risk_features],
        axis=1,
    )
    risk_raw = risk_signed.mean(axis=1, skipna=False)
    risk_score = cross_sectional_unit_rank(
        pd.DataFrame({"month": frame["month"], "risk": risk_raw}),
        ["risk"],
    )["risk"]
    decision = decision_integration_weight * integration + decision_risk_weight * risk_score
    confidence = (1.0 - reports.std(axis=1, ddof=0, skipna=False)).clip(0.0, 1.0)
    decision = decision.where(confidence >= minimum_trade_confidence, 0.0)

    diagnostics = []
    for month, indices in frame.groupby("month", sort=True).groups.items():
        score = decision.loc[indices]
        current_confidence = confidence.loc[indices]
        diagnostics.append(
            {
                "formation_month": str(pd.Timestamp(month).date()),
                "layer_count": 5,
                "agent_count": 9,
                "domain_agent_count": 4,
                "supporting_agent_count": 4,
                "integrated_report_count": reports.shape[1],
                "mean_confidence": float(current_confidence.mean()),
                "conflict_hold_count": int((current_confidence < minimum_trade_confidence).sum()),
                "buy_count": int((score > 0).sum()),
                "hold_count": int((score == 0).sum()),
                "sell_count": int((score < 0).sum()),
                "finite_scores": int(score.notna().sum()),
            }
        )
    return decision.rename("score"), pd.DataFrame(diagnostics)


def finpos_position_scores(
    frame: pd.DataFrame,
    signal_memory: dict[str, list[tuple[str, int]]],
    *,
    common_start: str,
    reward_horizons: list[int],
    multi_timescale_weights: list[float],
    reward_label_purge_months: int = 6,
    reward_history_months: int = 60,
    minimum_reward_months: int = 36,
    memory_reliability_temperature: float = 20.0,
    direction_hold_threshold: float = 0.1,
    position_bounds: tuple[float, float] = (-1.0, 1.0),
    base_trade_quantity: float = 0.25,
    cvar_history_months: int = 20,
    cvar_tail_probability: float = 0.05,
    cvar_risk_budget: float = 0.05,
    cvar_position_cap_bounds: tuple[float, float] = (0.25, 1.0),
) -> tuple[pd.Series, pd.DataFrame]:
    """Run a deterministic FinPos-style dual decision with carried positions."""
    expected_memory = ["shallow_news", "middle_technical", "deep_fundamental"]
    if list(signal_memory) != expected_memory:
        raise ValueError("FinPos requires the three frozen memory layers in order")
    if reward_horizons != [1, 3, 6] or not np.allclose(
        multi_timescale_weights,
        [1.0 / 3.0] * 3,
    ):
        raise ValueError("FinPos multi-timescale reward changed")
    if reward_label_purge_months < max(reward_horizons):
        raise ValueError("FinPos reward purge is shorter than the longest horizon")
    specifications = [
        specification
        for layer_specifications in signal_memory.values()
        for specification in layer_specifications
    ]
    features = list(dict.fromkeys(feature for feature, _ in specifications))
    missing = {"month", "security_id", "ret", "ret_exc_lead1m", *features} - set(frame)
    if missing:
        raise ValueError(f"missing FinPos inputs: {sorted(missing)}")
    if any(sign not in {-1, 1} for _, sign in specifications):
        raise ValueError("FinPos memory feature signs must be -1 or 1")

    ranked = cross_sectional_unit_rank(frame, features)
    layer_raw: dict[str, pd.Series] = {}
    for layer, layer_specifications in signal_memory.items():
        signed = pd.concat(
            [ranked[feature] * sign for feature, sign in layer_specifications],
            axis=1,
        )
        layer_raw[layer] = signed.mean(axis=1, skipna=False)
    layer_scores = cross_sectional_unit_rank(
        pd.concat([frame[["month"]], pd.DataFrame(layer_raw)], axis=1),
        expected_memory,
    )

    ordered = frame[["security_id", "month", "ret", "ret_exc_lead1m"]].copy().sort_values(
        ["security_id", "month"],
        kind="mergesort",
    )
    forward_outcomes: dict[int, pd.Series] = {}
    for horizon in reward_horizons:
        components = []
        for offset in range(horizon):
            shifted_return = ordered.groupby("security_id")["ret_exc_lead1m"].shift(-offset)
            shifted_month = ordered.groupby("security_id")["month"].shift(-offset)
            expected_month = ordered["month"] + pd.offsets.MonthEnd(offset)
            components.append(shifted_return.where(shifted_month.eq(expected_month)))
        component_frame = pd.concat(components, axis=1)
        forward_outcomes[horizon] = (
            (1.0 + component_frame).prod(axis=1, min_count=horizon) - 1.0
        ).reindex(frame.index)
    multi_outcome = sum(
        weight * forward_outcomes[horizon]
        for horizon, weight in zip(reward_horizons, multi_timescale_weights)
    )
    reward_frame = frame.assign(_multi_outcome=multi_outcome)
    reward_rankics = monthly_rankic(
        reward_frame,
        layer_scores,
        return_column="_multi_outcome",
    )

    ordered_return = pd.to_numeric(ordered["ret"], errors="coerce")
    tail_count = max(1, int(np.ceil(cvar_tail_probability * cvar_history_months)))
    cvar = (
        ordered_return.groupby(ordered["security_id"])
        .rolling(cvar_history_months, min_periods=cvar_history_months)
        .apply(lambda values: np.sort(values)[:tail_count].mean(), raw=True)
        .reset_index(level=0, drop=True)
        .reindex(frame.index)
    )

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    month_groups = frame.groupby("month", sort=False).groups
    common_months = sorted(
        pd.Timestamp(month)
        for month in frame.loc[frame["month"] >= common_start, "month"].unique()
    )
    positions: dict[object, float] = {}
    last_seen: dict[object, pd.Timestamp] = {}
    for month in common_months:
        label_cutoff = month - pd.offsets.MonthEnd(reward_label_purge_months)
        history = reward_rankics.loc[reward_rankics.index <= label_cutoff].tail(
            reward_history_months
        )
        count = history.count()
        if len(history) != reward_history_months or (count < minimum_reward_months).any():
            raise ValueError(f"FinPos reward history is incomplete at {month.date()}")
        mean = history.mean()
        logits = memory_reliability_temperature * mean
        reliability = np.exp(logits - logits.max())
        reliability /= reliability.sum()
        indices = month_groups[month]
        current_layers = layer_scores.loc[indices, expected_memory]
        direction_score = current_layers.mul(reliability, axis=1).sum(
            axis=1,
            min_count=len(expected_memory),
        )
        confidence = direction_score.abs().clip(0.0, 1.0)
        direction = pd.Series(
            np.where(
                direction_score > direction_hold_threshold,
                1,
                np.where(direction_score < -direction_hold_threshold, -1, 0),
            ),
            index=indices,
        )
        current_cvar = cvar.loc[indices].abs()
        cap = (cvar_risk_budget / current_cvar.replace(0.0, np.nan)).clip(
            cvar_position_cap_bounds[0],
            cvar_position_cap_bounds[1],
        ).fillna(cvar_position_cap_bounds[0])
        score_values = []
        quantities = []
        stale_resets = 0
        increases = 0
        decreases = 0
        unchanged = 0
        security_ids = frame.loc[indices, "security_id"]
        for index, security in security_ids.items():
            previous = positions.get(security, 0.0)
            if security in last_seen and last_seen[security] != month - pd.offsets.MonthEnd(1):
                previous = 0.0
                stale_resets += 1
            confidence_value = float(confidence.loc[index])
            quantity = (
                base_trade_quantity * confidence_value
                if np.isfinite(confidence_value)
                else 0.0
            )
            proposed = previous + int(direction.loc[index]) * quantity
            bounded = float(np.clip(proposed, -float(cap.loc[index]), float(cap.loc[index])))
            bounded = float(np.clip(bounded, position_bounds[0], position_bounds[1]))
            actual_quantity = abs(bounded - previous)
            if bounded > previous:
                increases += 1
            elif bounded < previous:
                decreases += 1
            else:
                unchanged += 1
            positions[security] = bounded
            last_seen[security] = month
            score_values.append(bounded)
            quantities.append(actual_quantity)
        score = pd.Series(score_values, index=indices, dtype=float)
        result.loc[indices] = score
        row: dict[str, object] = {
            "formation_month": str(month.date()),
            "label_cutoff": str(label_cutoff.date()),
            "reward_history_start": str(history.index[0].date()),
            "reward_history_end": str(history.index[-1].date()),
            "reward_history_months": len(history),
            "direction_buy_count": int((direction > 0).sum()),
            "direction_hold_count": int((direction == 0).sum()),
            "direction_sell_count": int((direction < 0).sum()),
            "position_increase_count": increases,
            "position_decrease_count": decreases,
            "position_unchanged_count": unchanged,
            "long_position_count": int((score > 0).sum()),
            "flat_position_count": int((score == 0).sum()),
            "short_position_count": int((score < 0).sum()),
            "mean_absolute_position": float(score.abs().mean()),
            "mean_trade_quantity": float(np.mean(quantities)),
            "mean_cvar_position_cap": float(cap.mean()),
            "minimum_cvar_position_cap": float(cap.min()),
            "stale_position_resets": stale_resets,
            "finite_scores": int(score.notna().sum()),
        }
        for layer in expected_memory:
            row[f"memory_mean_rankic__{layer}"] = float(mean[layer])
            row[f"memory_reliability__{layer}"] = float(reliability[layer])
        diagnostics.append(row)
    return result, pd.DataFrame(diagnostics)


def finrs_risk_sensitive_scores(
    frame: pd.DataFrame,
    signal_memory: dict[str, list[tuple[str, int]]],
    *,
    common_start: str,
    reward_horizons: list[int],
    multi_timescale_weights: list[float],
    reward_label_purge_months: int = 6,
    reward_history_months: int = 60,
    direction_hold_threshold: float = 0.1,
    base_trade_quantity: float = 0.25,
    kelly_history_months: int = 20,
    scaled_kelly_fraction: float = 0.5,
    cvar_history_months: int = 20,
    cvar_tail_probability: float = 0.05,
    cvar_risk_budget: float = 0.05,
    maximum_absolute_exposure: float = 0.75,
) -> tuple[pd.Series, pd.DataFrame]:
    """Apply FINRS-style Kelly, CVaR, volatility, and exposure controls."""
    base_scores, base_history = finpos_position_scores(
        frame,
        signal_memory,
        common_start=common_start,
        reward_horizons=reward_horizons,
        multi_timescale_weights=multi_timescale_weights,
        reward_label_purge_months=reward_label_purge_months,
        reward_history_months=reward_history_months,
        direction_hold_threshold=direction_hold_threshold,
        base_trade_quantity=base_trade_quantity,
        cvar_history_months=cvar_history_months,
        cvar_tail_probability=cvar_tail_probability,
        cvar_risk_budget=cvar_risk_budget,
    )
    if kelly_history_months != 20 or scaled_kelly_fraction != 0.5:
        raise ValueError("FINRS Kelly configuration changed")
    if maximum_absolute_exposure != 0.75:
        raise ValueError("FINRS exposure ceiling changed")

    ordered = frame[["security_id", "month", "ret"]].copy().sort_values(
        ["security_id", "month"],
        kind="mergesort",
    )
    returns = pd.to_numeric(ordered["ret"], errors="coerce")
    grouped = returns.groupby(ordered["security_id"])

    def mean_positive(values: np.ndarray) -> float:
        selected = values[values > 0]
        return float(selected.mean()) if len(selected) else np.nan

    def mean_negative_magnitude(values: np.ndarray) -> float:
        selected = values[values < 0]
        return float(abs(selected.mean())) if len(selected) else np.nan

    mean_gain = (
        grouped.rolling(kelly_history_months, min_periods=kelly_history_months)
        .apply(mean_positive, raw=True)
        .reset_index(level=0, drop=True)
        .reindex(frame.index)
    )
    mean_loss = (
        grouped.rolling(kelly_history_months, min_periods=kelly_history_months)
        .apply(mean_negative_magnitude, raw=True)
        .reset_index(level=0, drop=True)
        .reindex(frame.index)
    )
    volatility = (
        grouped.rolling(kelly_history_months, min_periods=kelly_history_months)
        .std(ddof=1)
        .reset_index(level=0, drop=True)
        .reindex(frame.index)
    )
    tail_count = max(1, int(np.ceil(cvar_tail_probability * cvar_history_months)))
    cvar = (
        grouped.rolling(cvar_history_months, min_periods=cvar_history_months)
        .apply(lambda values: np.sort(values)[:tail_count].mean(), raw=True)
        .reset_index(level=0, drop=True)
        .reindex(frame.index)
    )

    result = pd.Series(np.nan, index=frame.index, dtype="float64", name="score")
    diagnostics: list[dict[str, object]] = []
    base_diagnostics = base_history.set_index("formation_month")
    for month, indices in frame.loc[frame["month"] >= common_start].groupby(
        "month",
        sort=True,
    ).groups.items():
        base = base_scores.loc[indices]
        probability = 0.5 + 0.25 * base.abs().clip(0.0, 1.0)
        payoff_odds = (mean_gain.loc[indices] / mean_loss.loc[indices]).clip(0.5, 2.0)
        full_kelly = (
            (payoff_odds * probability - (1.0 - probability)) / payoff_odds
        ).clip(lower=0.0)
        scaled_kelly = scaled_kelly_fraction * full_kelly
        current_volatility = volatility.loc[indices]
        median_volatility = float(current_volatility.median())
        volatility_adjustment = 1.0 / (
            1.0 + current_volatility / max(median_volatility, 1e-12)
        )
        cvar_cap = (cvar_risk_budget / cvar.loc[indices].abs().replace(0.0, np.nan)).clip(
            0.0,
            maximum_absolute_exposure,
        )
        risk_capacity = pd.concat(
            [
                base.abs(),
                scaled_kelly * volatility_adjustment,
                cvar_cap,
                pd.Series(maximum_absolute_exposure, index=indices),
            ],
            axis=1,
        ).min(axis=1, skipna=False)
        risk_capacity = risk_capacity.fillna(0.0)
        score = np.sign(base) * risk_capacity
        result.loc[indices] = score
        base_row = base_diagnostics.loc[str(pd.Timestamp(month).date())]
        diagnostics.append(
            {
                "formation_month": str(pd.Timestamp(month).date()),
                "label_cutoff": base_row["label_cutoff"],
                "reward_history_start": base_row["reward_history_start"],
                "reward_history_end": base_row["reward_history_end"],
                "reward_history_months": int(base_row["reward_history_months"]),
                "mean_base_absolute_position": float(base.abs().mean()),
                "mean_win_probability": float(probability.mean()),
                "mean_payoff_odds": float(payoff_odds.mean()),
                "mean_scaled_kelly": float(scaled_kelly.mean()),
                "mean_volatility_adjustment": float(volatility_adjustment.mean()),
                "mean_cvar_cap": float(cvar_cap.mean()),
                "mean_final_absolute_exposure": float(score.abs().mean()),
                "risk_shrunk_count": int((score.abs() < base.abs()).sum()),
                "risk_zeroed_count": int(score.eq(0.0).sum()),
                "finite_scores": int(score.notna().sum()),
            }
        )
    return result, pd.DataFrame(diagnostics)
