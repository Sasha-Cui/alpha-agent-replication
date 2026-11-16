#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Pinned TradingAgents v0.1.0 graph; explicit historical-data/model/account adapters."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SOURCE = Path("/nfs/roberts/scratch/pi_btk22/zc362/tradingagents_v010")
sys.path.insert(0, str(SOURCE))
import argparse
import json
import os

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["OPENAI_API_KEY"] = "unused-network-rebound-to-meter"
import pandas as pd
from stockstats import StockDataFrame
from langchain_core.runnables import Runnable
from langchain_core.messages import AIMessage, convert_to_openai_messages
from langchain_core.utils.function_calling import convert_to_openai_tool
from alpha_evolve.publication_llm import canonical_meter
from alpha_evolve.openrouter_budget import atomic_json, read_key, sha256

PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


class MeteredModel(Runnable):
    def __init__(self, meter, model, temperature=0.1, bound_tools=None):
        self.meter = meter
        self.model = model
        self.temperature = temperature
        self.bound_tools = bound_tools

    def bind_tools(self, tools, **kwargs):
        return MeteredModel(self.meter, self.model, self.temperature, [convert_to_openai_tool(t) for t in tools])

    def invoke(self, input, config=None, **kwargs):
        if isinstance(input, str):
            messages = [{"role": "user", "content": input}]
        else:
            messages = convert_to_openai_messages(input.to_messages() if hasattr(input, "to_messages") else input)
        parameters = {"tools": self.bound_tools} if self.bound_tools else {}
        prices = {"openai/o4-mini": (1.1, 4.4), "openai/gpt-4o-mini": (0.15, 0.6)}
        body = {"model": self.model, "messages": messages, "max_tokens": 16384, **parameters}
        if self.temperature is not None:
            body["temperature"] = self.temperature
        response, _ = self.meter.request(
            "chat/completions", body, input_price=prices[self.model][0], output_price=prices[self.model][1]
        )
        if response["choices"][0].get("finish_reason") == "length":
            raise RuntimeError("Truncated source-role response; retain cost and inspect before continuation")
        raw = response["choices"][0]["message"]
        calls = []
        for call in raw.get("tool_calls") or []:
            calls.append(
                {
                    "name": call["function"]["name"],
                    "args": json.loads(call["function"]["arguments"]),
                    "id": call["id"],
                    "type": "tool_call",
                }
            )
        return AIMessage(content=raw.get("content") or "", tool_calls=calls)


class DatedTools:
    def __init__(self, view):
        self.symbol = view["symbol"]
        self.prices = pd.DataFrame(view["prices"])
        self.items = view["items"]
        self.cutoff = ""
        self.trace = []

    def call(self, name, kwargs):
        # Every tool is bounded by the driver's decision date, regardless of LLM-supplied dates.
        cutoff = min(str(kwargs.get("curr_date", kwargs.get("end_date", self.cutoff))), self.cutoff)
        symbol = kwargs.get("symbol", kwargs.get("ticker", self.symbol))
        record = {"tool": name, "arguments": kwargs, "driver_cutoff": self.cutoff, "effective_cutoff": cutoff}
        self.trace.append(record)
        if symbol.upper() != self.symbol:
            return "Unavailable: this frozen case includes only " + self.symbol
        if "YFin" in name:
            frame = self.prices[
                (self.prices.date <= cutoff) & (self.prices.date >= str(kwargs.get("start_date", "1900-01-01")))
            ]
            record["latest_input_date"] = frame.date.max() if len(frame) else None
            return "Frozen FINSABER alternative OHLCV; original Yahoo snapshot unavailable.\n" + frame.to_csv(
                index=False
            )
        if "stockstats" in name:
            frame = self.prices[self.prices.date <= cutoff].copy()
            record["latest_input_date"] = frame.date.max() if len(frame) else None
            frame = StockDataFrame.retype(frame.set_index("date"))
            indicator = kwargs["indicator"]
            try:
                series = frame[indicator].tail(min(int(kwargs.get("look_back_days", 30)), len(frame)))
                return "Stockstats indicator from dated alternative OHLCV.\n" + series.to_csv()
            except (KeyError, AttributeError, ValueError) as exc:
                return "Unavailable indicator: " + str(exc)
        if any(s in name for s in ["reddit", "insider"]):
            record["unavailable"] = True
            return "Unavailable: no point-in-time Reddit or insider dataset in this frozen source replacement. Do not invent observations."
        if "simfin" in name or "fundamentals" in name:
            items = [r for r in self.items if r["kind"] in ["filingk", "filingq"] and r["available_date"] <= cutoff]
            selected = sorted(items, key=lambda r: r["available_date"])[-2:]
            record["latest_input_date"] = max((r["date"] for r in selected), default=None)
            return (
                "Alternative SEC 10-K/10-Q summaries, not SimFin statement tables. Full filings summarized with provenance.\n"
                + json.dumps(selected)
            )
        if "news" in name:
            lower = (pd.Timestamp(cutoff) - pd.Timedelta(days=int(kwargs.get("look_back_days", 7)))).strftime(
                "%Y-%m-%d"
            )
            selected = [r for r in self.items if r["kind"] == "news_items" and lower <= r["available_date"] <= cutoff]
            record["latest_input_date"] = max((r["date"] for r in selected), default=None)
            return "Alternative dated FNSPID/FINSABER company news; no contemporaneous web access.\n" + json.dumps(
                selected
            )
        raise ValueError("Unmapped tool " + name)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true")
    p.add_argument("--output-name", required=True)
    p.add_argument("--recipe", required=True)
    p.add_argument("--inspect-config", action="store_true")
    p.add_argument("--max-days", type=int)
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--stop-index", type=int)
    args = p.parse_args()
    recipe_path = Path(args.recipe).resolve()
    recipe = json.loads(recipe_path.read_text())
    input_path = Path(recipe["input_file"])
    view = json.loads(input_path.read_text())
    meter = canonical_meter(
        ROOT,
        "unused" if args.offline else read_key(ROOT.parent / "KnowledgeTemplate/.env"),
        model="openai/gpt-4o",
        study="fidelity_v2_tradingagents_source_roles",
        cap=20,
        input_price=2.5,
        output_price=10,
        offline=args.offline,
    )
    adapter = DatedTools(view)
    output = PRIVATE / args.output_name
    output.mkdir(parents=True, exist_ok=True)
    os.chdir(output)
    import tradingagents.graph.trading_graph as native
    from tradingagents.agents.utils.memory import FinancialSituationMemory
    import chromadb
    from chromadb.config import Settings

    class BoundMemory(FinancialSituationMemory):
        def __init__(self, name):
            self.chroma_client = chromadb.Client(Settings(allow_reset=True, anonymized_telemetry=False))
            self.situation_collection = self.chroma_client.create_collection(name="fidelity_" + name)

            def create(**kwargs):
                from types import SimpleNamespace

                response, _ = meter.embeddings(kwargs["input"], model="openai/" + kwargs["model"])
                return SimpleNamespace(
                    data=[
                        SimpleNamespace(embedding=row["embedding"])
                        for row in sorted(response["data"], key=lambda x: x["index"])
                    ]
                )

            from types import SimpleNamespace

            self.client = SimpleNamespace(embeddings=SimpleNamespace(create=create))

    native.FinancialSituationMemory = BoundMemory
    native.ChatOpenAI = lambda model, temperature=None: MeteredModel(meter, "openai/" + model, temperature)
    # Preserve source tool schemas and source graph; replace only their data function bindings.
    for name in dir(native.Toolkit):
        tool = getattr(native.Toolkit, name)
        if not hasattr(tool, "args_schema"):
            continue

        def bound(_name=name, **kwargs):
            return adapter.call(_name, kwargs)

        tool.func = bound
    config = dict(native.DEFAULT_CONFIG)
    config.update(
        project_dir=str(output),
        data_dir=str(output),
        data_cache_dir=str(output / "cache"),
        online_tools=False,
        quick_think_llm="gpt-4o-mini",
        deep_think_llm="o4-mini",
    )
    graph = native.TradingAgentsGraph(config=config)
    if args.inspect_config:
        proof = {"status": "configuration_only", "deep_model": graph.deep_thinking_llm.model, "deep_temperature": graph.deep_thinking_llm.temperature, "quick_model": graph.quick_thinking_llm.model, "quick_temperature": graph.quick_thinking_llm.temperature, "native_embedding_method_preserved": BoundMemory.get_embedding is FinancialSituationMemory.get_embedding}
        atomic_json(output / "configuration_validation.json", proof)
        print(json.dumps(proof))
        return
    # The release does not automatically train/update memories in propagate(); keep that behavior.
    price = pd.DataFrame(view["prices"])
    dates = price.loc[(price.date >= recipe["start"]) & (price.date <= recipe["end"]), "date"].tolist()
    dates = dates[args.start_index : args.stop_index]
    if args.max_days:
        dates = dates[: args.max_days]
    records = []
    for day in dates:
        adapter.cutoff = day
        before = len(meter.request_trace)
        tool_before = len(adapter.trace)
        state, signal = graph.propagate(recipe["symbol"], day)
        if signal.strip().upper() not in ["BUY", "SELL", "HOLD"]:
            raise ValueError("Invalid native signal " + repr(signal))
        no_risk_signal = None
        simple_signal = None
        no_risk_state = {"final_trade_decision": None}
        simple = type("UnusedControl", (), {"content": None})()
        reports = {
            name: state[name] for name in ["market_report", "fundamentals_report", "news_report", "sentiment_report"]
        }
        record = {
            "date": day,
            "native": signal.strip().upper(),
            "no_risk_debate": no_risk_signal,
            "same_reports_single_decision": simple_signal,
            "requests": meter.request_trace[before:],
            "tool_trace": adapter.trace[tool_before:],
            "reports": reports,
            "investment_debate": state["investment_debate_state"],
            "risk_debate": state["risk_debate_state"],
            "investment_plan": state["investment_plan"],
            "native_final": state["final_trade_decision"],
            "no_risk_final": no_risk_state["final_trade_decision"],
            "simple_final": simple.content,
        }
        records.append(record)
        atomic_json(output / "decisions.json", records)
        atomic_json(output / "progress.json", {"date": day, "days": len(records), "usage": meter.snapshot()})
        print(
            day,
            record["native"],
            record["no_risk_debate"],
            record["same_reports_single_decision"],
            meter.snapshot(),
            flush=True,
        )
        if (PRIVATE / "PAUSE_TRADINGAGENTS").exists():
            raise SystemExit("Paused after completed day; responses are durable.")
    atomic_json(
        output / "completion.json",
        {
            "status": "worker_shard_complete"
            if args.start_index or args.stop_index is not None
            else ("plumbing_probe" if args.max_days else "complete"),
            "days": len(records),
            "recipe_sha256": sha256(recipe_path),
            "input_sha256": sha256(input_path),
            "script_sha256": sha256(Path(__file__)),
            "source_sha256": {
                str(p.relative_to(SOURCE)): sha256(p) for p in sorted((SOURCE / "tradingagents").rglob("*.py"))
            },
            "decisions_sha256": sha256(output / "decisions.json"),
            "usage": meter.snapshot(),
            "offline": args.offline,
        },
    )


if __name__ == "__main__":
    main()
