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
