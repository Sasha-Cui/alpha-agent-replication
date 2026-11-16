#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Source FinAgent pipeline with causal validation, actual vision and memory calls."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/nfs/roberts/scratch/pi_btk22/zc362/finagent_source")
sys.path[:0] = [str(ROOT / "src"), str(SOURCE)]
import argparse
import ast
import copy
import json
import os
import random
import sqlite3
import types
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="finagent.tools.strategy_agents")
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import faiss

faiss.omp_set_num_threads(1)
from mmengine.config import Config
from alpha_evolve.openrouter_budget import atomic_json, read_key, sha256
from alpha_evolve.fidelity_transport_v2 import LockedLiveMeter
from alpha_evolve.publication_embeddings import ConcurrentEmbeddingCache
from finagent.provider.provider import OpenAIProvider
from alpha_evolve.publication_economics import cash_account as daily_account
from finagent.registry import PROMPT
from finagent.asset import ASSET
from finagent.utils import read_resource_file
from finagent.prompt import (
    prepare_latest_market_intelligence_params,
    prepare_low_level_reflection_params,
    prepare_high_level_reflection_params,
)
from finagent.memory import MemoryInterface
from finagent.memory.basic_memory import BasicMemory
from finagent.query import DiverseQuery, QUERY_TYPES
from finagent.tools import StrategyAgents
from finagent.environment.trading import EnvironmentTrading

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"
RECORD_KEYS = [
    "symbol",
    "day",
    "value",
    "cash",
    "position",
    "ret",
    "date",
    "price",
    "discount",
    "kline_path",
    "trading_path",
    "total_profit",
    "total_return",
    "action",
    "reasoning",
]


class WaitingMeter(LockedLiveMeter):
    def request(self, *args, **kwargs):
        import time

        deadline = time.monotonic() + 200
        while True:
            try:
                return super().request(*args, **kwargs)
            except RuntimeError as exc:
                if "Unresolved previous request:" not in str(exc):
                    raise
                key = str(exc).rsplit(" ", 1)[-1]
                entry = self.request_status(key)
                if entry.get("status") != "reserved" or time.monotonic() >= deadline:
                    raise
                # Only await another worker's existing request; never duplicate it.
                time.sleep(0.25)


class Provider:
    def __init__(self, meter):
        self.meter = meter
        # Execute the released provider's actual tokenization, per-document
        # chunking and normalization with a metered SDK transport binding.
        native = object.__new__(OpenAIProvider)
        native.embedding_model = "text-embedding-3-large"
        native.provider_cfg = {"is_azure": False}
        native.retries = 1

        def create(**kwargs):
            response, _ = meter.embeddings(kwargs["input"], model="openai/" + kwargs["model"], price_per_million=0.13)
            return types.SimpleNamespace(
                data=[
                    types.SimpleNamespace(embedding=row["embedding"])
                    for row in sorted(response["data"], key=lambda row: row["index"])
                ]
            )

        native.client = types.SimpleNamespace(embeddings=types.SimpleNamespace(create=create))
        self.embedding_dim = native.get_embedding_dim()
        self.native_embedding_provider = native
        self.embedding_cache = ConcurrentEmbeddingCache(native.embed_query, dimensions=self.embedding_dim, workers=4)

    def create_completion(self, messages, model=None, **kwargs):
        response, key = self.meter.chat(messages, max_tokens=2048, temperature=self.temperature)
        return response["choices"][0]["message"]["content"], {
            "request_hash": key,
            "usage": response.get("usage"),
            "requested_source_model": model,
            "actual_route": self.meter.model,
        }

    def embed_query(self, text):
        return self.embedding_cache.embed(text)

    def prefetch(self, texts):
        self.embedding_cache.prefetch(texts)


class PrefetchedDiverseQuery(DiverseQuery):
    def diverse_query(self, params, query_types=["plain", "short_term", "long_term"], top_k=None):
        self.provider.prefetch([QUERY_TYPES[k](params) for k in query_types])
        return super().diverse_query(params, query_types=query_types, top_k=top_k)


class ArtifactStore:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.execute("CREATE TABLE IF NOT EXISTS objects (path TEXT PRIMARY KEY,kind TEXT,body BLOB)")

    def put(self, path, kind, body):
        self.connection.execute("INSERT OR REPLACE INTO objects VALUES (?,?,?)", (str(path), kind, body))
        self.connection.commit()

    def save_json(self, value, path, **kwargs):
        self.put(path, "json", json.dumps(value, default=str, sort_keys=True).encode())

    def save_html(self, value, path, **kwargs):
        self.put(path, "html", str(value).encode())


class CausalPlots:
    def __init__(self, path, store, mode):
        self.path = path
        self.store = store
        self.mode = mode
        path.mkdir(parents=True, exist_ok=True)
        self.trace = []

    def _style(self, ax):
        ax.set_facecolor("#ffffff")
        ax.tick_params(colors="#172033")
        ax.title.set_color("#172033")
        ax.xaxis.label.set_color("#172033")
        ax.yaxis.label.set_color("#172033")
        ax.grid(color="#d4dce6", alpha=0.6)
        for spine in ax.spines.values():
            spine.set_color("#667085")

    def plot_kline(self, state, info, save_dir, mode=None):
        price = state["price"].copy()
        cutoff = pd.Timestamp(info["date"])
        if self.mode == "valid" and (price.index > cutoff).any():
            raise ValueError("Future price reached validation chart")
        fig, (ax, vol) = plt.subplots(
            2, 1, figsize=(12, 7), gridspec_kw={"height_ratios": [4, 1]}, sharex=True, facecolor="#ffffff"
        )
        for a in (ax, vol):
            self._style(a)
        for i, row in enumerate(price.itertuples()):
            color = "#15803d" if row.close >= row.open else "#b91c1c"
            ax.vlines(i, row.low, row.high, color=color)
            ax.add_patch(
                Rectangle(
                    (i - 0.3, min(row.open, row.close)),
                    0.6,
                    max(abs(row.close - row.open), 0.001),
                    facecolor=color,
                    edgecolor=color,
                )
            )
            vol.bar(i, row.volume, color=color)
        ticks = list(range(0, len(price), max(1, len(price) // 7)))
        vol.set_xticks(ticks, [price.index[i].strftime("%m-%d") for i in ticks])
        ax.set_title(
            self.symbol + " daily OHLC through " + str(price.index.max().date()) + "; decision " + info["date"],
            color="#172033",
        )
        ax.set_ylabel("Price (USD)")
        vol.set_ylabel("Volume")
        vol.set_xlabel("Session date")
        ax.axvline(np.flatnonzero(price.index == cutoff)[0], color="#172033", linestyle="--", linewidth=1)
        fig.tight_layout()
        path = self.path / "current_kline.jpeg"
        fig.savefig(path, dpi=110, facecolor="#ffffff")
        plt.close(fig)
        self.store.put(self.mode + "/" + info["date"] + "/kline.jpeg", "image/jpeg", path.read_bytes())
        self.trace.append(
            {
                "decision": info["date"],
                "mode": self.mode,
                "latest_chart_date": str(price.index.max().date()),
                "sha256": sha256(path),
            }
        )
        return str(path)

    def plot_trading(self, records, info, save_dir):
        fig, ax = plt.subplots(figsize=(12, 5), facecolor="#ffffff")
        self._style(ax)
        ax.plot(pd.to_datetime(records["date"]), records["value"], color="#164eaa", label="Account value")
        ax.set_title("Executed account history before " + info["date"], color="#172033")
        ax.set_ylabel("Account value (USD)")
        ax.set_xlabel("Date")
        fig.autofmt_xdate()
        fig.tight_layout()
        path = self.path / "current_trading.jpeg"
        fig.savefig(path, dpi=110, facecolor="#ffffff")
        plt.close(fig)
        self.store.put(self.mode + "/" + info["date"] + "/trading.jpeg", "image/jpeg", path.read_bytes())
        return str(path)


def unique_memory_add(self, data, embedding_key, **kwargs):
    # Storage repair: the released second-resolution clock overwrites cached additions.
    name = f"memory_{len(self.memory):08d}"
    if embedding_key not in data:
        raise ValueError("Missing embedding")
    self.memory[name] = data
    self.vectorstore.add_embeddings([name], [data[embedding_key]])


class NoRetrieval(PrefetchedDiverseQuery):
    def diverse_query(self, params, query_types=["plain", "short_term", "long_term"], top_k=None):
        result = super().diverse_query(params, query_types=query_types, top_k=top_k)
        return {key: {**value, "query_items": []} for key, value in result.items()}


class RuleTools:
    def __init__(self, prices, strategy_agents):
        self.prices = prices
        self.strategy_agents = strategy_agents
        self.rows = {}
        self.names = ["Buy and hold", "MACD", "KDJ & RSI", "Stochastic Bollinger", "Mean Reversion"]
        signals = {k: [] for k in range(1, 5)}
        explanations = {k: [] for k in range(1, 5)}
        for i in range(len(prices)):
            for k in signals:
                if i < 14:
                    action, reason = "HOLD", "Insufficient source 15-session history"
                else:
                    actions, reasons = strategy_agents.wrapper(k, prices.iloc[i - 14 : i + 1].copy())
                    action, reason = actions[-1], reasons[-1]
                signals[k].append(action)
                explanations[k].append(reason)
        returns = prices.adj_close.pct_change().fillna(0).to_numpy()
        self.histories = {}
        self.explanations = explanations
        self.signals = signals
        for k in range(5):
            target = np.zeros(len(prices))
            holding = 0
            for i in range(len(prices)):
                signal = "BUY" if k == 0 else signals[k][i]
                if signal == "BUY":
                    holding = 1
                elif signal == "SELL":
                    holding = 0
                # Target selected at i is executed at i+1, then earns return i+2.
                if i + 1 < len(prices):
                    target[i + 1] = holding
            self.histories[k] = daily_account(target[:, None], returns[:, None], 10)[0]

    def __call__(
        self,
        state,
        info,
        params,
        memory=None,
        provider=None,
        diverse_query=None,
        strategy_agents=None,
        cfg=None,
        mode="valid",
    ):
        date = pd.Timestamp(info["date"])
        i = self.prices.index.get_loc(date)
        res = copy.deepcopy(params)
        res.update(guidance="Unavailable: no original point-in-time guidance archive.", sentiment=None)
        # Use only returns already realized by this date; records are not opaque shipped result summaries.
        end = min(i, self.prices.index.searchsorted(pd.Timestamp("2023-06-01")) - 1) if mode == "valid" else i

        def summary(k):
            r = self.histories[k][14 : end + 1]
            if len(r) < 20:
                return "Insufficient chronological record; no future performance supplied."
            wealth = np.cumprod(1 + r)
            sd = r.std(ddof=1)
            return f"Alternative-input, default-rule, next-close, 10bp historical record through {self.prices.index[end].date()}: annualized geometric return {wealth[-1] ** (252 / len(r)) - 1:.6f}; zero-cash-rate Sharpe {np.sqrt(252) * r.mean() / sd if sd else 0:.6f}; maximum drawdown {np.min(wealth / np.maximum.accumulate(np.r_[1.0, wealth])[1:] - 1):.6f}. Not an author-reported metric."

        for k in range(1, 5):
            res[f"strategy{k}"] = (
                f"Strategy: {self.names[k]}\nDecision: {self.signals[k][i]}\nReasoning: {self.explanations[k][i]}"
            )
            res[f"trading_record{k}"] = summary(k)
        res["buy_and_hold_record"] = summary(0)
        return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true")
    p.add_argument("--output-name", required=True)
    p.add_argument("--recipe", required=True)
    p.add_argument("--max-steps", type=int)
    args = p.parse_args()
    recipe_path = Path(args.recipe).resolve()
    recipe = json.loads(recipe_path.read_text())
    symbol = recipe["symbol"]
    view_path = Path(recipe["input_file"])
    view = json.loads(view_path.read_text())
    output = PRIVATE / args.output_name
    output.mkdir(parents=True, exist_ok=True)
    os.chdir(output)
    meter = WaitingMeter(
        ROOT / "runs/economic_fidelity/openrouter",
        "unused" if args.offline else read_key(ROOT.parent / "KnowledgeTemplate/.env"),
        "openai/gpt-4o",
        study="fidelity_v2_finagent_source_settings",
        study_cap=160,
        input_price=2.5,
        output_price=10,
        offline=args.offline,
    )
    provider = Provider(meter)
    provider.temperature = recipe["temperature"]
    store = ArtifactStore(output / "source_artifacts.sqlite3")
    BasicMemory.add = unique_memory_add
    from finagent.prompt.trading.latest_market_intelligence_summary import LatestMarketIntelligenceSummaryTrading

    native_add_news = LatestMarketIntelligenceSummaryTrading.add_to_memory

    def add_news_with_prefetch(self, state=None, info=None, res=None, memory=None, provider=None):
        news = state["news"]
        news = news[news.index == info["date"]]
        # Exactly the released embedding-text construction; the original method
        # still performs every real memory insertion after prefetching vectors.
        provider.prefetch([f"Heading: {row['title']}\nContent: {row['text']}\n" for _, row in news.iterrows()])
        return native_add_news(self, state=state, info=info, res=res, memory=memory, provider=provider)

    LatestMarketIntelligenceSummaryTrading.add_to_memory = add_news_with_prefetch
    # Keep prompt/response content intact in SQLite instead of thousands of HTML/JSON files.
    import finagent.prompt.trading as prompt_package  # noqa: F401 - register source prompt classes

    for name, module in list(sys.modules.items()):
        if name.startswith("finagent.prompt.trading."):
            if hasattr(module, "save_json"):
                module.save_json = store.save_json
            if hasattr(module, "save_html"):
                module.save_html = store.save_html
    cfg = Config.fromfile(str(SOURCE / "configs/exp/trading" / (symbol + ".py")))
    cfg.root = str(SOURCE)
    cfg.tool_use_best_params = False
    # Source's full released template variant includes guidance/rule-tool sections;
    # the generic 'trading' templates omit them despite computing tool parameters.
    for template_mode in ["train", "valid"]:
        for stage in [
            "latest_market_intelligence_summary",
            "past_market_intelligence_summary",
            "low_level_reflection",
            "high_level_reflection",
            "decision",
        ]:
            relative = f"res/prompts/template/{template_mode}/trading_mi-w-low-w-high-w-tool-w-decision/{stage}.html"
            if not (SOURCE / relative).exists():
                raise FileNotFoundError(relative)
            cfg[f"{template_mode}_{stage}_template_path"] = relative
    prices = pd.DataFrame(view["prices"]).rename(columns={"date": "timestamp", "adjusted_close": "adj_close"})
    prices.timestamp = pd.to_datetime(prices.timestamp)
    prices = prices.set_index("timestamp")
    news = pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp(r["available_date"]),
                "id": n,
                "title": "Dated alternative company news",
                "text": r["text"],
                "source_date": r["date"],
            }
            for n, r in enumerate(view["items"])
            if r["kind"] == "news_items"
        ]
    ).set_index("timestamp")
    strategy_agents = StrategyAgents()
    rule_tools = RuleTools(prices, strategy_agents)
    # Execute the exact released run_step body without its CLI dotenv/config side effects.
    source_text = (SOURCE / "tools/main.py").read_text()
    tree = ast.parse(source_text)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_step")
    namespace = {
        "PROMPT": PROMPT,
        "ASSET": ASSET,
        "read_resource_file": read_resource_file,
        "prepared_tools_params": rule_tools,
        "prepare_latest_market_intelligence_params": prepare_latest_market_intelligence_params,
        "prepare_low_level_reflection_params": prepare_low_level_reflection_params,
        "prepare_high_level_reflection_params": prepare_high_level_reflection_params,
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE / "tools/main.py"), "exec"), namespace)
    run_step = namespace["run_step"]
    memory = MemoryInterface(
        root=str(output),
        symbols=[symbol],
        memory_path="memory",
        embedding_dim=provider.embedding_dim,
        max_recent_steps=5,
        workdir="native",
        tag="shared",
    )
    random.seed(recipe["seed"])
    np.random.seed(recipe["seed"])
    steps = 0
    decisions = []
    charts = []

    def execute(arm, memory, mode, start, end):
        nonlocal steps
        pframe = prices.loc[:"2023-05-31"] if mode == "train" else prices
        nframe = news.loc[:"2023-05-31"] if mode == "train" else news
        dataset = types.SimpleNamespace(
            prices={symbol: pframe.reset_index()},
            news={symbol: nframe.reset_index()},
            guidances=None,
            sentiments=None,
            economics=None,
        )
        env = EnvironmentTrading(
            mode=mode,
            dataset=dataset,
            selected_asset=symbol,
            start_date=start,
            end_date=end,
            look_back_days=14,
            look_forward_days=14 if mode == "train" else 0,
            initial_amount=10000,
            transaction_cost_pct=0.001,
        )
        query = (NoRetrieval if arm == "no_retrieval" else PrefetchedDiverseQuery)(
            memory=memory, provider=provider, top_k=5
        )
        plots = CausalPlots(output / arm / "charts", store, mode)
        plots.symbol = symbol
        records = {k: [] for k in RECORD_KEYS}
        state, info = env.reset()
        pending = "HOLD"
        pending_reason = "Initial cash state; no prior trading decision."
        previous_nav = 10000.0
        while True:
            day = info["date"]
            before = len(meter.request_trace)
            terminal = False
            if mode == "valid":
                # Execute the prior order and mark NAV at THIS close before the
                # actor sees its account. The released step labels prior-close
                # NAV with the next date; use its buy/sell rules with a repaired clock.
                env.price = env.get_current_price()
                executed = pending
                if pending == "BUY":
                    env.buy(env.price)
                elif pending == "SELL":
                    env.sell(env.price)
                else:
                    env.hold_on(env.price)
                actual_execution = env.action
                env.value = env.current_value(env.price)
                realized = env.value / previous_nav - 1
                env.ret = realized
                env.total_return += env.discount * realized
                env.discount *= 0.99
                env.total_profit = 100 * (env.value / env.initial_amount - 1)
                info.update(
                    value=float(env.value),
                    cash=float(env.cash),
                    position=int(env.position),
                    price=float(env.price),
                    ret=float(realized),
                    total_profit=float(env.total_profit),
                    total_return=float(env.total_return),
                    discount=float(env.discount),
                    action=actual_execution,
                )
                state = env.get_state()
                terminal = env.day >= env.end_day
                assert state["price"].index.max() <= pd.Timestamp(day)
                assert len(state["news"]) == 0 or state["news"].index.max() <= pd.Timestamp(day)
                pre_value = previous_nav
            else:
                pre_value = info["value"]
                executed = None
                actual_execution = None
            np.random.seed(recipe["seed"] + int(day.replace("-", "")))
            if terminal:
                action = None
                reasoning = "Terminal valuation; no new decision."
            else:
                action = run_step(
                    cfg, state, info, plots, memory, provider, query, strategy_agents, str(output / arm), records, mode
                )
                if action not in env.action_map:
                    raise ValueError("Invalid native action")
                reasoning = records["reasoning"][-1]
            if mode == "train":
                executed = action
                next_state, reward, done, truncated, next_info = env.step(env.action_map[action])
                after_value = next_info["value"]
                realized = after_value / pre_value - 1
                actual_execution = next_info["action"]
                cash_after = next_info["cash"]
                shares_after = next_info["position"]
                records["action"][-1] = actual_execution
            else:
                after_value = env.value
                cash_after = env.cash
                shares_after = env.position
                done = terminal
                if not terminal:
                    records["action"][-1] = actual_execution
                    records["reasoning"][-1] = pending_reason
            record = {
                "date": day,
                "arm": arm,
                "mode": mode,
                "decision": action,
                "terminal_valuation": terminal,
                "executed_previous_decision": executed,
                "actual_execution": actual_execution,
                "realization_date": day,
                "native_value_before": pre_value,
                "native_value_after": after_value,
                "realized_return": realized,
                "cash_after": float(cash_after),
                "shares_after": int(shares_after),
                "reasoning": reasoning,
                "requests": meter.request_trace[before:],
                "latest_price_in_state": str(state["price"].index.max().date()),
                "latest_news_available_date": str(state["news"].index.max().date()) if len(state["news"]) else None,
            }
            decisions.append(record)
            steps += 1
            with (output / "decisions.jsonl").open("a") as f:
                f.write(json.dumps(record, default=str) + "\n")
            atomic_json(output / "progress.json", {"arm": arm, "date": day, "steps": steps, "usage": meter.snapshot()})
            print("PROGRESS", arm, day, action, "executed", executed, meter.snapshot(), flush=True)
            if args.max_steps and steps >= args.max_steps:
                raise SystemExit(0)
            if (PRIVATE / "PAUSE_FINAGENT").exists():
                raise SystemExit("Paused after a completed day; all paid responses are durable.")
            if done:
                break
            if mode == "train":
                state, info = next_state, next_info
            else:
                pending = action
                pending_reason = reasoning
                previous_nav = after_value
                env.day += 1
                env.date = env.get_current_date()
                env.price = env.get_current_price()
                info = {**info, "date": env.date.strftime("%Y-%m-%d"), "day": int(env.day), "price": float(env.price)}
        charts.extend(plots.trace)
        store.save_json(records, arm + "/trading_records.json")
        return memory

    (output / "decisions.jsonl").write_text("")
    execute("shared_training", memory, "train", recipe["train_start"], recipe["train_end"])
    trained = copy.deepcopy(memory)
    parent_output = output
    parent_records = list(decisions)
    parent_charts = list(charts)
    # Independent validation paths use separate RNGs, accounts and artifact stores.
    # Fork only between completed requests; native FAISS/OpenBLAS use one thread.
    store.connection.close()
    workers = []
    atomic_json(
        parent_output / "progress.json",
        {"arm": "parallel_validation", "training_steps": steps, "usage": meter.snapshot()},
    )
    for arm in recipe["arms"]:
        pid = os.fork()
        if pid == 0:
            try:
                output = parent_output / "validation_arms" / arm
                output.mkdir(parents=True, exist_ok=True)
                store = ArtifactStore(output / "source_artifacts.sqlite3")
                for module_name, module in list(sys.modules.items()):
                    if module_name.startswith("finagent.prompt.trading."):
                        if hasattr(module, "save_json"):
                            module.save_json = store.save_json
                        if hasattr(module, "save_html"):
                            module.save_html = store.save_html
                decisions = []
                charts = []
                steps = 0
                (output / "decisions.jsonl").write_text("")
                execute(arm, copy.deepcopy(trained), "valid", recipe["test_start"], recipe["test_end"])
                atomic_json(output / "chart_availability.json", charts)
                atomic_json(
                    output / "completion.json",
                    {
                        "status": "complete",
                        "arm": arm,
                        "records": len(decisions),
                        "decision_sha256": sha256(output / "decisions.jsonl"),
                    },
                )
                store.connection.close()
                sys.stdout.flush()
                sys.stderr.flush()
                os._exit(0)
            except BaseException:
                import traceback

                traceback.print_exc()
                sys.stdout.flush()
                sys.stderr.flush()
                os._exit(1)
        workers.append((arm, pid))
    statuses = {}
    for arm, pid in workers:
        _, wait_status = os.waitpid(pid, 0)
        statuses[arm] = os.waitstatus_to_exitcode(wait_status)
    output = parent_output
    decisions = parent_records
    charts = parent_charts
    if any(statuses.values()):
        raise RuntimeError("Validation worker failed; others were allowed to finish: " + str(statuses))
    for arm in recipe["arms"]:
        arm_output = output / "validation_arms" / arm
        decisions.extend(json.loads(line) for line in (arm_output / "decisions.jsonl").read_text().splitlines())
        charts.extend(json.loads((arm_output / "chart_availability.json").read_text()))
    steps = len(decisions)
    (output / "decisions.jsonl").write_text("".join(json.dumps(row, default=str) + "\n" for row in decisions))
    atomic_json(output / "chart_availability.json", charts)
    atomic_json(
        output / "completion.json",
        {
            "status": "complete",
            "steps": steps,
            "arm_counts": {
                arm: sum(r["arm"] == arm for r in decisions) for arm in ["shared_training"] + recipe["arms"]
            },
            "recipe_sha256": sha256(recipe_path),
            "input_sha256": sha256(view_path),
            "script_sha256": sha256(Path(__file__)),
            "source_sha256": {
                str(p.relative_to(SOURCE)): sha256(p) for p in sorted((SOURCE / "finagent").rglob("*.py"))
            },
            "decision_sha256": sha256(output / "decisions.jsonl"),
            "usage": meter.snapshot(),
            "offline": args.offline,
            "validation_future_chart_count": sum(
                r["mode"] == "valid" and r["latest_chart_date"] > r["decision"] for r in charts
            ),
        },
    )


if __name__ == "__main__":
    main()
