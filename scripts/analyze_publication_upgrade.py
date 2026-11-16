#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Assemble native/control evidence with explicit incomplete-case and inference gates."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import argparse
import json
import numpy as np
import pandas as pd
from alpha_evolve.publication_economics import cash_account, categorical_targets
from alpha_evolve.publication_inference import (
    grouped_t_effect,
    ols_alpha,
    chronological_projection,
    holm_adjust,
)
from alpha_evolve.openrouter_budget import atomic_json, sha256

PRIVATE = ROOT / "artifacts/publication_upgrade_v1"
PUBLIC = ROOT / "paper_runs/publication_upgrade_v1"


def series(dates, values):
    s = pd.Series(np.asarray(values, float), index=pd.to_datetime(dates)).sort_index()
    if s.index.has_duplicates or not np.isfinite(s).all() or (s <= -1).any():
        raise ValueError("Invalid return series")
    return s


def monthly(s):
    return (1 + s).groupby(s.index.to_period("M")).prod() - 1


def metrics(s, frequency=252):
    r = s.to_numpy()
    wealth = np.cumprod(1 + r)
    sd = r.std(ddof=1)
    return {
        "observations": len(r),
        "start": str(s.index[0]),
        "end": str(s.index[-1]),
        "cagr": float(np.expm1(np.log1p(r).mean() * frequency)),
        "annualized_arithmetic_return": float(r.mean() * frequency),
        "annualized_volatility": float(sd * np.sqrt(frequency)),
        "sharpe_zero_cash_rate": float(r.mean() / sd * np.sqrt(frequency)) if sd > 1e-14 else None,
        "max_drawdown": float(np.min(wealth / np.maximum.accumulate(np.r_[1.0, wealth])[1:] - 1)),
        "ending_wealth": float(wealth[-1]),
    }


def whole_account(actions, prices, cost_bps=10, lag=1):
    cash = 10000.0
    shares = 0
    previous = 10000.0
    pending = "HOLD"
    values = []
    turns = []
    for action, price in zip(actions, prices):
        execution = action if lag == 0 else pending
        marked = cash + shares * price
        traded = 0.0
        if execution == "BUY":
            buy = int(np.floor(cash / (price * (1 + cost_bps / 10000))))
            cash -= buy * price * (1 + cost_bps / 10000)
            shares += buy
            traded = buy * price
        elif execution == "SELL":
            traded = shares * price
            cash += traded * (1 - cost_bps / 10000)
            shares = 0
        elif execution not in ["HOLD", None]:
            raise ValueError("Invalid action")
        nav = cash + shares * price
        values.append(nav / previous - 1)
        turns.append(traded / marked)
        previous = nav
        pending = action
    return np.asarray(values), np.asarray(turns)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    out = PUBLIC / ("analysis_preview" if args.allow_partial else "analysis")
    out.mkdir(parents=True, exist_ok=True)
    cases = {}
    pairs = []
    performance = []
    stress = []
    validation = {}
    open_cases = []
    paper_scores = {}

    def add(case, arm, s, frequency=252):
        cases.setdefault(case, {})[arm] = s
        performance.append({"case": case, "arm": arm, **metrics(s, frequency)})

    def compare(case, left, right, role="secondary", frequency=12, label=None):
        pairs.append(
            {
                "case": case,
                "left": left,
                "right": right,
                "role": role,
                "frequency": frequency,
                "label": label or left + " minus " + right,
            }
        )

    # EFS: ten seeds are randomization replicates, never ten independent histories.
    controls = PRIVATE / "efs_controls/daily_returns.parquet"
    seed_paths = [PRIVATE / f"efs_matched/seed_{seed}/daily_returns.csv" for seed in range(101, 111)]
    if controls.exists() and all(p.exists() for p in seed_paths):
        data = pd.read_parquet(controls)
        for arm in ["llm", "initial", "equal_weight"]:
            x = data[(data.arm == arm) & (data.cadence == "daily") & (data.cost_bps == 10)]
            add("EFS", arm, series(x.date, x["return"]))
        for cadence in ["weekly", "monthly"]:
            for arm in ["llm", "initial", "equal_weight"]:
                subset = data[(data.arm == arm) & (data.cadence == cadence) & (data.cost_bps == 10)]
                add("EFS", arm + "__" + cadence, series(subset.date, subset["return"]))
            compare("EFS", "llm__" + cadence, "llm", label="Trading cadence: " + cadence + " minus daily")
            compare(
                "EFS",
                "llm__" + cadence,
                "initial__" + cadence,
                label="LLM minus initial at " + cadence + " trading cadence",
            )
            compare(
                "EFS",
                "llm__" + cadence,
                "equal_weight__" + cadence,
                label="LLM minus equal weight at " + cadence + " trading cadence",
            )
        matrix = []
        for seed, path in enumerate(seed_paths, 101):
            x = pd.read_csv(path)
            s = series(x.date, x.total_cost_10)
            add("EFS", f"grammar_seed_{seed}", s)
            matrix.append(s.rename(str(seed)))
        seeds = pd.concat(matrix, axis=1)
        if seeds.isna().any().any():
            raise ValueError("EFS seed calendars differ")
        add("EFS", "grammar_seed_mean", seeds.mean(axis=1))
        compare("EFS", "llm", "grammar_seed_mean", "primary")
        compare("EFS", "llm", "initial")
        compare("EFS", "llm", "equal_weight")
        for seed in range(101, 111):
            compare("EFS", "llm", f"grammar_seed_{seed}", label=f"LLM minus grammar seed {seed}")
        for (arm, cadence, cost), g in data.groupby(["arm", "cadence", "cost_bps"]):
            stress.append(
                {
                    "case": "EFS",
                    "arm": arm,
                    "adapter": cadence,
                    "cost_bps": int(cost),
                    "mean_daily_traded_notional": float(g.traded_notional.mean()),
                    **metrics(series(g.date, g["return"])),
                }
            )
    else:
        open_cases.append("EFS")
    # GuruAgents: same archived inputs, actual one-call versus tool-routing execution.
    path = PRIVATE / "guruagents_controls/daily_returns.parquet"
    if path.exists():
        data = pd.read_parquet(path)
        for mode in ["tool-routing", "archived-final"]:
            for agent in ["ensemble", "altman", "buffett", "graham", "greenblatt", "piotroski"]:
                name = f"replay__results_22_24__{mode}__{agent}"
                g = data[(data.candidate_id == name) & (data.extra_information_lag_days == 0) & (data.cost_bps == 1)]
                if not len(g):
                    raise ValueError("Missing GuruAgents primary candidate " + name)
                add("GuruAgents", mode + "__" + agent, series(g.date, g["return"]))
        compare("GuruAgents", "tool-routing__ensemble", "archived-final__ensemble", "primary")
        for agent in ["altman", "buffett", "graham", "greenblatt", "piotroski"]:
            compare("GuruAgents", "tool-routing__" + agent, "archived-final__" + agent)
        for (name, delay, cost), g in data.groupby(["candidate_id", "extra_information_lag_days", "cost_bps"]):
            if name.endswith("__ensemble"):
                stress.append(
                    {
                        "case": "GuruAgents",
                        "arm": name,
                        "adapter": f"extra_information_lag_{delay}d",
                        "cost_bps": int(cost),
                        "mean_daily_traded_notional": float(g.traded_notional.mean()),
                        **metrics(series(g.date, g["return"])),
                    }
                )
    else:
        open_cases.append("GuruAgents")
    # Released QuantaAlpha library: native Chinese account, not a fresh LLM search.
    if (PRIVATE / "quantaalpha_native/completion.json").exists():
        for arm in ["released_170", "alpha158_20"]:
            d = pd.read_parquet(PRIVATE / f"quantaalpha_native/{arm}/daily_account.parquet")
            add("QuantaAlpha", arm, series(d.index, d["return"] - d["cost"]))
            for multiplier in [0, 1, 2, 5]:
                stress.append(
                    {
                        "case": "QuantaAlpha",
                        "arm": arm,
                        "adapter": f"reported_cost_multiplier_{multiplier}",
                        "cost_bps": None,
                        "stress_kind": "Fixed executed positions; linear fee stress, not a new quantity/portfolio simulation",
                        **metrics(series(d.index, d["return"] - multiplier * d["cost"])),
                    }
                )
        compare("QuantaAlpha", "released_170", "alpha158_20", "primary")
    else:
        open_cases.append("QuantaAlpha")
    # Categorical source actors: original score and the economic account remain distinct.
    for case, folder, recipe_name, input_name in [
        ("FinMem", "finmem_native", "finmem_recipe.json", "finmem_inputs.json"),
        (
            "TradingAgents",
            "tradingagents_native",
            "tradingagents_recipe.json",
            "AAPL_2024-01-02_2024-03-28_inputs.json",
        ),
    ]:
        completion = PRIVATE / folder / "completion.json"
        if not completion.exists():
            open_cases.append(case)
            continue
        status = json.loads(completion.read_text())
        if status.get("status") != "complete":
            open_cases.append(case)
            continue
        recipe = json.loads((PUBLIC / recipe_name).read_text())
        raw = json.loads((PRIVATE / input_name).read_text())
        if case == "FinMem":
            price = pd.DataFrame(raw["rows"]).set_index("date").adjusted_close
            records = [json.loads(line) for line in (PRIVATE / folder / "decisions.jsonl").read_text().splitlines()]
            records = [r for r in records if r["mode"] == "Test"]
            start, end = recipe["test_start"], recipe["test_end"]
            arms = {"native": "native", "semantic_only": "semantic_only"}
        else:
            price = pd.DataFrame(raw["prices"]).set_index("date").adjusted_close
            records = json.loads((PRIVATE / folder / "decisions.json").read_text())
            start, end = recipe["start"], recipe["end"]
            arms = {k: k for k in ["native", "no_risk_debate", "same_reports_single_decision"]}
        price.index = pd.to_datetime(price.index)
        returns = price.pct_change(fill_method=None)
        dates = price.index[(price.index >= start) & (price.index <= end)]
        r = returns.reindex(dates).to_numpy()[:, None]
        for arm in arms:
            if case == "FinMem":
                actions = {
                    pd.Timestamp(row["date"]): {1: "BUY", 0: "HOLD", -1: "SELL"}[row["direction"]]
                    for row in records
                    if row["arm"] == arm
                }
            else:
                actions = {pd.Timestamp(row["date"]): row[arm] for row in records}
            action_list = [actions.get(date, "HOLD") for date in dates]
            for lag in [0, 1]:
                for cost in [0, 10, 25, 50]:
                    value, turn, _ = cash_account(categorical_targets(action_list, lag=lag), r, cost)
                    s = series(dates, value)
                    stress.append(
                        {
                            "case": case,
                            "arm": arm,
                            "adapter": "next_close" if lag else "same_close_infeasible_diagnostic",
                            "cost_bps": cost,
                            "mean_daily_traded_notional": float(turn.mean()),
                            **metrics(s),
                        }
                    )
                    if lag == 1 and cost == 10:
                        add(case, arm, s)
            if case == "FinMem":
                scored = [
                    (day, 1 if action == "BUY" else -1 if action == "SELL" else 0)
                    for day, action in actions.items()
                    if price.index.get_loc(day) + 1 < len(price)
                    and price.index[price.index.get_loc(day) + 1] <= pd.Timestamp(end)
                ]
                score = sum(
                    sign * np.log(price.iloc[price.index.get_loc(day) + 1] / price.loc[day]) for day, sign in scored
                )
                paper_scores[arm] = {
                    "signed_log_return_sum": float(score),
                    "scored_decisions": len(scored),
                    "label": "Source score, not cumulative portfolio return or self-financing NAV",
                }
        for name, action_list in [
            ("buy_hold_matched_clock", ["BUY"] + ["HOLD"] * (len(dates) - 1)),
            (
                "momentum3_price_only",
                ["BUY" if price.loc[d] > price.iloc[price.index.get_loc(d) - 3] else "SELL" for d in dates],
            ),
        ]:
            value, _, _ = cash_account(categorical_targets(action_list, lag=1), r, 10)
            add(case, name, series(dates, value))
            compare(case, "native", name, frequency=252)
        compare(case, "native", "semantic_only" if case == "FinMem" else "no_risk_debate", "primary", 252)
        if case == "TradingAgents":
            compare(case, "native", "same_reports_single_decision", frequency=252)
    # FinAgent: independently reconstruct its whole-share order/cash path.
    if (PRIVATE / "finagent_native/completion.json").exists():
        records = [json.loads(line) for line in (PRIVATE / "finagent_native/decisions.jsonl").read_text().splitlines()]
        raw = json.loads((PRIVATE / "TSLA_2022-06-01_2023-12-29_inputs.json").read_text())
        price = pd.DataFrame(raw["prices"]).set_index("date").adjusted_close
        price.index = pd.to_datetime(price.index)
        for arm in ["native_causal", "no_retrieval"]:
            selected = sorted([r for r in records if r["arm"] == arm], key=lambda r: r["date"])
            dates = pd.to_datetime([r["date"] for r in selected])
            actions = [r["decision"] for r in selected]
            prices = price.reindex(dates).to_numpy()
            reported = np.array([r["realized_return"] for r in selected])
            for lag in [0, 1]:
                for cost in [0, 10, 25, 50]:
                    values, turn = whole_account(actions, prices, cost, lag)
                    s = series(dates, values)
                    stress.append(
                        {
                            "case": "FinAgent",
                            "arm": arm,
                            "adapter": "next_close_whole_shares" if lag else "same_close_fixed_decision_diagnostic",
                            "cost_bps": cost,
                            "mean_daily_traded_notional": float(turn.mean()),
                            **metrics(s),
                        }
                    )
                    if lag == 1 and cost == 10:
                        error = float(np.max(np.abs(values - reported)))
                        if error > 1e-12:
                            raise ValueError("Independent FinAgent account mismatch " + str(error))
                        validation[arm + "_maximum_return_error"] = error
                        add("FinAgent", arm, s)
        baseline = ["BUY"] + ["HOLD"] * (len(dates) - 1)
        v, _ = whole_account(baseline, prices, 10, 1)
        add("FinAgent", "buy_hold_matched_clock", series(dates, v))
        compare("FinAgent", "native_causal", "no_retrieval", "primary", 252)
        compare("FinAgent", "native_causal", "buy_hold_matched_clock", frequency=252)
    else:
        open_cases.append("FinAgent")
    if open_cases and not args.allow_partial:
        atomic_json(
            out / "status.json",
            {"status": "waiting_for_cases", "open_cases": open_cases, "complete_cases": list(cases)},
        )
        raise SystemExit("Final analysis requires completed cases: " + ", ".join(open_cases))
    # Primary inference: conservative grouped-t bounds; uncertainty is conditional
    # on these realized model trajectories, not a distribution over model seeds.
    effects = []
    for pair in pairs:
        left, right = cases[pair["case"]][pair["left"]], cases[pair["case"]][pair["right"]]
        if pair["frequency"] == 12:
            left, right = monthly(left), monthly(right)
        matched = pd.concat([left.rename("left"), right.rename("right")], axis=1).dropna()
        result = grouped_t_effect(
            matched.left.to_numpy(), matched.right.to_numpy(), frequency=pair["frequency"], groups=4, confidence=0.99
        )
        result = {k: v for k, v in result.items() if not isinstance(v, (list, dict))}
        if result["degenerate_sampling_variation"]:
            result["primary_ci_low"] = None
            result["primary_ci_high"] = None
            result["group_t_p_two_sided"] = None
            result["verdict"] = "identical_or_degenerate_observed_path_no_population_bound"
        elif result["primary_ci_low"] > 0.02:
            result["verdict"] = "conditional_effect_exceeds_2pp"
        elif result["equivalent_within_margin_tost5"]:
            result["verdict"] = "conditional_equivalence_within_2pp"
        elif result["rules_out_positive_margin_one_sided5"]:
            result["verdict"] = "conditional_positive_2pp_advantage_excluded"
        else:
            result["verdict"] = "inconclusive_at_2pp_margin"
        effects.append({**pair, **result})
    effects = pd.DataFrame(effects)
    primary = (effects.role == "primary") & effects.group_t_p_two_sided.notna()
    effects.loc[primary, "holm_p_primary_family"] = holm_adjust(effects.loc[primary, "group_t_p_two_sided"].to_numpy())
    effects["familywise_positive_primary"] = False
    effects.loc[primary, "familywise_positive_primary"] = (effects.loc[primary, "holm_p_primary_family"] < 0.01) & (
        effects.loc[primary, "primary_ci_low"] > 0
    )
    effects["interval_scope"] = "casewise nominal99%; model-seed uncertainty excluded"
    effects.to_csv(out / "paired_effects.csv", index=False)
    pd.DataFrame(performance).to_csv(out / "economic_performance.csv", index=False)
    pd.DataFrame(stress).to_csv(out / "controlled_adaptations.csv", index=False)
    # Identified low-dimensional factor checks; unrestricted short JKP132 is refused.
    factors_path = ROOT / "paper_runs/prompt_replay/guruagents/performance/factor_panel_extended_realization.csv"
    factors = pd.read_csv(factors_path)
    factors.index = pd.to_datetime(factors.realization_month).dt.to_period("M")
    full_columns = ["capm_top1000_mkt"] + [c for c in factors if c.startswith("char__")]
    core = ["capm_top1000_mkt", "char__be_me", "char__market_equity", "char__at_gr1", "char__ope_be", "char__ret_12_1"]
    attribution = []
    projection = []
    for pair in [p for p in pairs if p["role"] == "primary" and p["case"] != "QuantaAlpha"]:
        difference = monthly(cases[pair["case"]][pair["left"]]) - monthly(cases[pair["case"]][pair["right"]])
        joined = factors[full_columns].join(difference.rename("difference"), how="inner").dropna()
        base = {"case": pair["case"], "comparison": pair["label"], "months": len(joined)}
        try:
            full = ols_alpha(joined.difference, joined[full_columns])
            attribution.append(
                {
                    **base,
                    "model": "full_JKP132_plus_market",
                    "status": "identified",
                    "annualized_alpha": full["annualized_alpha"],
                }
            )
        except ValueError as exc:
            attribution.append(
                {**base, "model": "full_JKP132_plus_market", "status": "not_identified", "reason": str(exc)}
            )
        if len(joined) >= 30:
            groups = 4 if len(joined) // 4 > len(core) + 3 else 3
            try:
                g = grouped_t_effect(
                    joined.difference.to_numpy(), factors=joined[core].to_numpy(), groups=groups, confidence=0.99
                )
                attribution.append(
                    {
                        **base,
                        "model": "prespecified_six_factor_projection",
                        "status": "identified_conditional_model",
                        **{k: v for k, v in g.items() if not isinstance(v, (list, dict))},
                    }
                )
            except ValueError as exc:
                attribution.append(
                    {
                        **base,
                        "model": "prespecified_six_factor_projection",
                        "status": "insufficient_for_grouped_inference",
                        "reason": str(exc),
                    }
                )
        if len(joined) > 36:
            for name, components in [("ridge_all_factors", None), ("pca5_ridge", 5)]:
                g = chronological_projection(
                    joined.difference.to_numpy(), joined[full_columns].to_numpy(), min_train=36, components=components
                )
                projection.append(
                    {**base, "model": name, **{k: v for k, v in g.items() if k not in ["predictions", "residual"]}}
                )
    pd.DataFrame(attribution).to_csv(out / "factor_attribution.csv", index=False)
    pd.DataFrame(projection).to_csv(out / "regularized_projection_diagnostics.csv", index=False)
    atomic_json(out / "finmem_source_scores.json", paper_scores)
    atomic_json(out / "independent_account_validation.json", validation)
    daily_rows = [
        {"case": case, "arm": arm, "date": str(date.date()), "return": float(value)}
        for case, arms in cases.items()
        for arm, s in arms.items()
        for date, value in s.items()
    ]
    pd.DataFrame(daily_rows).to_parquet(
        PRIVATE / ("analysis_preview_returns.parquet" if args.allow_partial else "analysis_returns.parquet"),
        index=False,
    )
    atomic_json(
        out / "status.json",
        {
            "status": "provisional" if open_cases else "complete",
            "open_cases": open_cases,
            "complete_cases": list(cases),
            "primary_comparisons": int((effects.role == "primary").sum()),
            "nominal_primary_confidence": 0.99,
            "economic_margin": 0.02,
            "human_review": "pending",
            "prospective_returns": "not_yet_observed",
            "source_paper_reproduction_claim": False,
            "interpretation": "Historical conditional mechanism comparisons; no insignificant result is treated as proof of no alpha. Model-seed uncertainty is not estimated.",
            "script_sha256": sha256(Path(__file__)),
        },
    )
    print("ANALYSIS_COMPLETE", list(cases), "pending", open_cases, flush=True)


if __name__ == "__main__":
    main()
