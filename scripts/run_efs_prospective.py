#!/usr/bin/env python3
# ruff: noqa: E401, E731 - preserve the committed prospective semantic snapshot
# ruff: noqa: E402 - standalone source-path bootstrap
"""Commit an auditable EFS-style prospective research forecast; never place orders."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import argparse, hashlib, json, os, urllib.request, urllib.parse  # noqa: F401 - retain sealed imports
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import numpy as np, pandas as pd
import pandas_market_calendars as calendars
from alpha_evolve.prospective import locked, ensure_seal, read_chain, commit_forecast, commit_outcome
from alpha_evolve.openrouter_budget import atomic_json, sha256, read_key
from alpha_evolve.publication_llm import canonical_meter
from alpha_evolve.economic_fidelity import Factor, seed_factors, top_weights
from run_efs_economic_fidelity import ResearchEngine, rank_pool, user_prompt, parse_proposals
from run_efs_matched_search import proposal

PRIVATE = ROOT / "artifacts/publication_upgrade_v1"
OUT = PRIVATE / "prospective_efs_v1"
HISTORIC = ROOT / "paper_runs/economic_fidelity/efs_v1"


def clock():
    return datetime.now(timezone.utc)


def market_schedule(now):
    cal = calendars.get_calendar("NYSE")
    return cal.schedule(start_date="2018-10-01", end_date=(now + timedelta(days=20)).date())


def fetch_prices(now, tickers, schedule):
    completed = schedule.index[schedule.market_close <= pd.Timestamp(now)]
    last = completed[-1]
    snapshot = OUT / f"prices_as_first_observed_{last.date()}.parquet"
    manifest_path = snapshot.with_suffix(".json")
    if snapshot.exists():
        return pd.read_parquet(snapshot), json.loads(manifest_path.read_text())
    start = int(datetime(2018, 10, 1, tzinfo=timezone.utc).timestamp())
    end = int(now.timestamp())
    metadata = []

    def fetch(ticker):
        yahoo = ticker.replace(".", "-")
        url = (
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            + urllib.parse.quote(yahoo, safe="")
            + f"?period1={start}&period2={end}&interval=1d"
        )
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 alpha-agent-replication research"}
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
            result = json.loads(body)["chart"]["result"][0]
            quotes = result["indicators"]["quote"][0]
            adjusted = result["indicators"]["adjclose"][0]["adjclose"]
            dates = (
                pd.to_datetime(result["timestamp"], unit="s", utc=True)
                .tz_convert("America/New_York")
                .tz_localize(None)
                .normalize()
            )
            frame = pd.DataFrame(
                {
                    "date": dates,
                    "ticker": ticker,
                    "close": quotes["close"],
                    "adjusted_close": adjusted,
                    "volume": quotes["volume"],
                }
            )
            frame = frame[frame.date.isin(completed)].drop_duplicates("date", keep="last")
            return frame, {
                "ticker": ticker,
                "requested_yahoo_symbol": yahoo,
                "response_symbol": result["meta"].get("symbol"),
                "source_url": url,
                "response_sha256": hashlib.sha256(body).hexdigest(),
                "rows": len(frame),
                "status": "retrieved",
            }
        except Exception as exc:
            return pd.DataFrame(columns=["date", "ticker", "close", "adjusted_close", "volume"]), {
                "ticker": ticker,
                "requested_yahoo_symbol": yahoo,
                "status": "unavailable",
                "reason": type(exc).__name__ + ": " + str(exc)[:180],
            }

    frames = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for frame, meta in pool.map(fetch, tickers):
            frames.append(frame)
            metadata.append(meta)
    frame = pd.concat(frames, ignore_index=True)
    frame.to_parquet(snapshot, index=False)
    manifest = {
        "observed_at_utc": now.isoformat(),
        "latest_completed_session": str(last.date()),
        "latest_input_available_at_utc": schedule.loc[last, "market_close"].isoformat(),
        "quote_snapshot_sha256": sha256(snapshot),
        "sources": metadata,
        "input_kind": "Alternative public Yahoo split-adjusted close for signals and dividend-adjusted close for return measurements; completed sessions only",
    }
    atomic_json(manifest_path, manifest)
    return frame, manifest


def pool_record(pool):
    return {key: {"code": f.code, "origin": f.origin, "created_index": int(f.created_index)} for key, f in pool.items()}


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--settle-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with locked(OUT):
        now = clock()
        schedule = market_schedule(now)
        future = schedule[schedule.market_close > pd.Timestamp(now)]
        execution_session = future.index[0]
        evaluation_session = future.index[1]
        universe = pd.read_parquet(ROOT / "artifacts/economic_fidelity/v1/llm_daily_weights.parquet").columns.tolist()
        universe = sorted(universe)
        protocol = {
            "study": "prospective development pilot; not a confirmatory study",
            "universe": universe,
            "data_source": "Public Yahoo daily chart, completed NYSE sessions only",
            "initial_library": "All historically admitted EFS functions, shared between the forward LLM and grammar arms; a declared cold start, not uninterrupted continuation of the 2019-2024 state",
            "historical_library_sha256": sha256(HISTORIC / "llm_factor_library.json"),
            "source_system_prompt_sha256": sha256(HISTORIC / "system_prompt.txt"),
            "model": "openai/gpt-4.1",
            "temperature": 0.3,
            "seed": 20260907,
            "max_tokens": 2048,
            "search_interval_sessions": 5,
            "proposal_slots": 3,
            "pool_max": 64,
            "selected_factors": 5,
            "portfolio_assets": 10,
            "feedback_assets": 25,
            "feedback_days": 60,
            "factor_history": 30,
            "primary_pair": "Fresh LLM search versus fixed-grammar search from the same historical library",
            "reference_arms": ["initial_seed_library", "equal_weight"],
            "execution": "First future NYSE close after the decision is recorded; evaluate the following close",
            "cost_bps": 10,
            "project_soft_cap": 450,
            "forward_study_cap": 10,
            "minimum_latest_session_quotes": 45,
            "human_review": "pending",
            "external_registration": "pending",
            "no_real_orders": True,
        }
        code_paths = [
            Path(__file__),
            ROOT / "src/alpha_evolve/prospective.py",
            ROOT / "src/alpha_evolve/publication_llm.py",
            ROOT / "src/alpha_evolve/economic_fidelity.py",
            ROOT / "scripts/run_efs_economic_fidelity.py",
            ROOT / "scripts/run_efs_matched_search.py",
        ]
        seal = ensure_seal(OUT, protocol, code_paths)
        prior = read_chain(OUT / "forecasts.jsonl")
        if not args.settle_only and any(
            row["payload"]["execution_at_utc"] == future.iloc[0].market_close.isoformat() for row in prior
        ):
            print("FORECAST_ALREADY_COMMITTED", flush=True)
            return
        frame, data_manifest = fetch_prices(now, universe, schedule)
        prices_df = frame.pivot(index="date", columns="ticker", values="close").reindex(
            index=schedule.index[schedule.market_close <= pd.Timestamp(now)], columns=universe
        )
        volumes = frame.pivot(index="date", columns="ticker", values="volume").reindex(
            index=prices_df.index, columns=universe
        )
        latest = prices_df.index[-1]
        eligible = (
            np.isfinite(prices_df.tail(30).to_numpy()).all(axis=0)
            & prices_df.iloc[-1].gt(0).to_numpy()
            & volumes.iloc[-1].gt(0).to_numpy()
        )
        if eligible.sum() < 45:
            raise RuntimeError(
                f"Only {eligible.sum()} of 50 current quote histories are eligible; do not manufacture a forecast"
            )
        # Outcomes are appended only once the committed evaluation close is observable.
        adjusted = frame.pivot(index="date", columns="ticker", values="adjusted_close").reindex(columns=universe)
        settled = {row["payload"]["forecast_sha256"] for row in read_chain(OUT / "outcomes.jsonl")}
        for forecast in prior:
            p = forecast["payload"]
            if forecast["sha256"] in settled or pd.Timestamp(p["evaluation_at_utc"]) > pd.Timestamp(now):
                continue
            begin = pd.Timestamp(p["execution_session"])
            end = pd.Timestamp(p["evaluation_session"])
            if begin not in adjusted.index or end not in adjusted.index:
                continue
            asset_return = adjusted.loc[end] / adjusted.loc[begin] - 1
            values = {}
            for arm, weights in p["targets"].items():
                w = pd.Series(weights).reindex(universe).fillna(0)
                held = w > 0
                if not np.isfinite(asset_return[held]).all():
                    raise ValueError("Missing future held-asset realization")
                gross = float((w[held] * asset_return[held]).sum())
                values[arm] = {
                    "gross_holding_period_return": gross,
                    "entry_fee_mark_to_market_return": (1 + gross) / (1 + protocol["cost_bps"] / 10000) - 1,
                }
            outcome = commit_outcome(
                OUT,
                forecast,
                {
                    "observed_at_utc": clock().isoformat(),
                    "quote_snapshot_sha256": data_manifest["quote_snapshot_sha256"],
                    "payoffs": values,
                    "interpretation": "One committed next-close holding-period payoff, with a separate first-entry fee calculation. These rows are not concatenated into a continuous portfolio and carry no significance claim.",
                },
            )
            print("OUTCOME_COMMITTED", outcome["sha256"], flush=True)
        if args.settle_only:
            return
        if (now.date() - latest.date()).days > 7:
            raise ValueError("Latest completed price is stale")
        prices = prices_df.to_numpy(float)
        anchors = np.array(
            [
                column[np.flatnonzero(np.isfinite(column) & (column > 0))[0]]
                if np.any(np.isfinite(column) & (column > 0))
                else 1.0
                for column in prices.T
            ]
        )
        prices = prices / anchors * 100
        recipe = {"feedback_portfolio_assets": 25, "portfolio_assets": 10, "feedback_days": 60, "recall_assets": 20}
        engine = ResearchEngine(prices, pd.DatetimeIndex(prices_df.index), universe, recipe)
        decision_index = len(prices) - 1
        history = json.loads((HISTORIC / "llm_factor_library.json").read_text())
        seed_pool = {f.sha256: f for f in seed_factors()}
        previous = prior[-1]["payload"]["state_after"] if prior else None
        pools = {}
        for arm in ["llm", "grammar"]:
            records = previous["pools"][arm] if previous else history
            pools[arm] = {key: Factor(row["code"], row["origin"], row["created_index"]) for key, row in records.items()}
        last_search = previous.get("last_search_session") if previous else None
        search = (
            last_search is None
            or prices_df.index.get_loc(latest) - prices_df.index.get_loc(pd.Timestamp(last_search)) >= 5
        )
        events = []
        targets = {}
        retained = {}
        round_number = (previous.get("search_rounds", 0) if previous else 0) + int(search)
        for arm, pool in list(pools.items()) + [("initial_seed_library", seed_pool)]:
            statistics = {}
            valid = {}
            for key, factor in pool.items():
                try:
                    value = engine.performance(factor, decision_index)
                    if not all(np.isfinite(v) for v in value.values() if isinstance(v, (int, float))):
                        raise ValueError("Nonfinite feedback metric")
                    statistics[key] = value
                    valid[key] = factor
                except Exception as exc:
                    events.append(
                        {
                            "arm": arm,
                            "factor_sha256": key,
                            "status": "numerically_unavailable",
                            "reason": str(exc)[:180],
                        }
                    )
            ranking = rank_pool(valid, statistics)
            pool = {key: valid[key] for key in ranking[:64]}
            if search and arm in ["llm", "grammar"]:
                if arm == "llm":
                    top = ranking[:8]
                    message = user_prompt(
                        [pool[k] for k in top if pool[k].origin == "paper_seed_family"],
                        [pool[k] for k in top if pool[k].origin != "paper_seed_family"],
                        [statistics[k] for k in top],
                    )
                    meter = canonical_meter(
                        ROOT,
                        read_key(ROOT.parent / "KnowledgeTemplate/.env"),
                        model=protocol["model"],
                        study="efs_forward_pilot_v1",
                        cap=10,
                        input_price=2,
                        output_price=8,
                    )
                    response, key = meter.chat(
                        [
                            {"role": "system", "content": (HISTORIC / "system_prompt.txt").read_text()},
                            {"role": "user", "content": message},
                        ],
                        max_tokens=2048,
                        temperature=0.3,
                        seed=20260907,
                    )
                    try:
                        codes = parse_proposals(response["choices"][0]["message"].get("content") or "")[:3]
                    except (ValueError, SyntaxError):
                        codes = []
                    events.append(
                        {
                            "arm": arm,
                            "request_hash": key,
                            "response_id": response.get("id"),
                            "response_created": response.get("created"),
                            "status": "model_response",
                            "proposals_received": len(codes),
                        }
                    )
                else:
                    rng = np.random.default_rng(20260907 + round_number)
                    codes = [proposal(rng, 10000 + round_number * 3 + i) for i in range(3)]
                for slot in range(3):
                    if slot >= len(codes):
                        events.append({"arm": arm, "slot": slot, "status": "missing_proposal"})
                        continue
                    code = codes[slot]
                    try:
                        factor = Factor(code, "forward_" + arm, decision_index)
                        if factor.sha256 in pool:
                            raise ValueError("Duplicate factor")
                        value = engine.performance(factor, decision_index)
                        if value["mean_return"] <= value["benchmark_mean_return"] or value["mean_rankic"] <= 0:
                            raise ValueError("Training-only admission threshold not met")
                        pool[factor.sha256] = factor
                        statistics[factor.sha256] = value
                        events.append({"arm": arm, "slot": slot, "status": "accepted", "factor_sha256": factor.sha256})
                    except Exception as exc:
                        events.append({"arm": arm, "slot": slot, "status": "rejected", "reason": str(exc)[:180]})
            ranking = rank_pool(pool, statistics)
            chosen = ranking[:5]
            if len(chosen) < 5:
                raise ValueError("Too few valid factors")
            scores = np.stack([engine.scores(pool[key], decision_index) for key in chosen])
            common = np.isfinite(scores).all(axis=0) & eligible
            combined = np.full(len(universe), np.nan)
            combined[common] = scores[:, common].mean(axis=0)
            weights = top_weights(combined, 10)
            targets[arm] = {ticker: float(w) for ticker, w in zip(universe, weights) if w > 0}
            if arm in ["llm", "grammar"]:
                retained[arm] = pool_record(pool)
        targets["equal_weight"] = {ticker: float(1 / eligible.sum()) for ticker, ok in zip(universe, eligible) if ok}
        forecast = {
            "execution_session": str(execution_session.date()),
            "evaluation_session": str(evaluation_session.date()),
            "execution_at_utc": future.iloc[0].market_close.isoformat(),
            "evaluation_at_utc": future.iloc[1].market_close.isoformat(),
            "maximum_input_available_at_utc": data_manifest["latest_input_available_at_utc"],
            "latest_completed_input_session": str(latest.date()),
            "quote_snapshot_sha256": data_manifest["quote_snapshot_sha256"],
            "eligible_assets": int(eligible.sum()),
            "targets": targets,
            "search_events": events,
            "state_after": {
                "pools": retained,
                "last_search_session": str(latest.date()) if search else last_search,
                "search_rounds": round_number,
            },
            "study_status": "prospective development pilot; human review and external registration pending; no observed future returns yet",
        }
        record = commit_forecast(OUT, seal, forecast)
        atomic_json(
            OUT / "latest_forecast_summary.json",
            {
                "forecast_sha256": record["sha256"],
                "seal_sha256": seal["sha256"],
                "recorded_at_utc": record["payload"]["recorded_at_utc"],
                "execution_at_utc": forecast["execution_at_utc"],
                "evaluation_at_utc": forecast["evaluation_at_utc"],
                "eligible_assets": int(eligible.sum()),
                "arms": list(targets),
                "no_real_orders": True,
            },
        )
        print(
            "FORECAST_COMMITTED", json.dumps(json.loads((OUT / "latest_forecast_summary.json").read_text())), flush=True
        )


if __name__ == "__main__":
    run()
