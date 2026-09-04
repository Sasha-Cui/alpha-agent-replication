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
