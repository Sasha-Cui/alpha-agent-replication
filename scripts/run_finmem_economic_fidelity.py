#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Execute pinned FinMem actor/BrainDB/Portfolio with metered network bindings."""

from pathlib import Path
import argparse
import copy
import importlib.machinery
import json
import os
import random
import sys
import types
import numpy as np
import guardrails  # noqa: F401 - load optional checks before the unused-tokenizer sentinel
import toml
from alpha_evolve.openrouter_budget import atomic_json, read_key, sha256
from alpha_evolve.publication_llm import canonical_meter

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "artifacts/publication_upgrade_v1"
SOURCE = Path("/nfs/roberts/scratch/pi_btk22/zc362/finmem_source")
LAYERS = ["short_term_memory", "mid_term_memory", "long_term_memory", "reflection_memory"]


def import_native(meter):
    optional = types.ModuleType("transformers")
    optional.__spec__ = importlib.machinery.ModuleSpec("transformers", loader=None)

    class UnusedTokenizer:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            raise RuntimeError("Unused TGI tokenizer branch invoked")

    optional.AutoTokenizer = UnusedTokenizer
    sys.modules["transformers"] = optional
    sys.path.insert(0, str(SOURCE))
    import puppy.memorydb as db
    import faiss

    faiss.omp_set_num_threads(1)
    from puppy.embedding import OpenAILongerThanContextEmb as NativeEmbedding

    class MeteredEmbedding(NativeEmbedding):
        def __init__(self, **kwargs):
            super().__init__(**{**kwargs, "openai_api_key": "unused-metered-transport"})

            def create(**parameters):
                response, _ = meter.embeddings(
                    parameters["input"], model="openai/" + parameters["model"], price_per_million=0.1
                )
                return response

            self.emb_model.client = types.SimpleNamespace(create=create)

        def __call__(self, text):
            if isinstance(text, list) and not text:
                return np.empty((0, 1536), dtype="float32")
            return super().__call__(text)

        def __deepcopy__(self, memo):
            # The embedding transport has no per-agent learned state. Share its
            # immutable configuration rather than copying SDK connection locks.
            return self

    db.OpenAILongerThanContextEmb = MeteredEmbedding
    from puppy import LLMAgent, RunMode

    return LLMAgent, RunMode


def semantic_query(self, query_text, top_k, symbol):
    # Preserve native retrieved cardinality and candidate-memory availability.
    native_text, native_ids = self._fidelity_native_query(query_text, top_k, symbol)
    k = len(native_ids)
    if not k:
        return [], []
    emb = self.emb_func(query_text)
    _, ids = self.universe[symbol]["index"].search(emb, k)
    lookup = {r["id"]: r for r in self.universe[symbol]["score_memory"]}
    selected = [lookup[int(i)] for i in ids[0] if int(i) in lookup]
    return [r["text"] for r in selected], [r["id"] for r in selected]


def memory_summary(agent):
    return {
        layer: {
            "count": len(getattr(agent.brain, layer).universe.get("TSLA", {}).get("score_memory", [])),
            "ids": [int(r["id"]) for r in getattr(agent.brain, layer).universe.get("TSLA", {}).get("score_memory", [])],
        }
        for layer in LAYERS
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output-name", default="finmem_native")
    parser.add_argument("--max-steps", type=int)
    args = parser.parse_args()
    recipe = json.loads((ROOT / "paper_runs/publication_upgrade_v1/finmem_recipe.json").read_text())
    key = "unused" if args.offline else read_key(ROOT.parent / "KnowledgeTemplate/.env")
    meter = canonical_meter(
        ROOT,
        key,
        model=recipe["model"],
        study="finmem_native_actor_v1",
        cap=recipe["actor_budget_usd"],
        input_price=10,
        output_price=30,
        offline=args.offline,
    )
    Agent, RunMode = import_native(meter)
    output = PRIVATE / args.output_name
    output.mkdir(parents=True, exist_ok=True)
    (output / "data/04_model_output_log").mkdir(parents=True, exist_ok=True)
    os.chdir(output)
    config = toml.load(SOURCE / "config/tsla_gpt_config.toml")
    config["general"]["top_k"] = recipe["top_k"]
    config["chat"]["model"] = "gpt-4-turbo"
    config["chat"]["end_point"] = "https://openrouter.ai/api/v1/chat/completions"
    rows = json.loads((PRIVATE / "finmem_inputs.json").read_text())["rows"]
    # The native training oracle can use next-day prices only through the first test decision close.
    rows = [r for r in rows if recipe["train_start"] <= r["date"] <= "2023-04-12"]
    train = [(i, r) for i, r in enumerate(rows) if r["date"] < recipe["train_end"]]
    test = [(i, r) for i, r in enumerate(rows) if recipe["test_start"] <= r["date"] < recipe["test_end"]]
    errors = []

    def endpoint(input, **kwargs):
        try:
            response, _ = meter.chat(
                [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant only capable of communicating with valid JSON, and no other text.",
                    },
                    {"role": "user", "content": str(input)},
                ],
                max_tokens=2048,
                temperature=recipe["temperature"],
            )
            return response["choices"][0]["message"]["content"]
        except Exception as exc:
            errors.append(type(exc).__name__ + ": " + str(exc))
            raise

    random.seed(recipe["seed"])
    np.random.seed(recipe["seed"])
    agent = Agent.from_config(config)
    agent.guardrail_endpoint = endpoint
    all_records = []
    step_count = 0

    def step(actor, i, row, arm, mode):
        nonlocal step_count
        before = len(meter.request_trace)
        # Do not even deliver an evaluation target to the source test actor.
        label = rows[i + 1]["adjusted_close"] - row["adjusted_close"] if mode == RunMode.Train else None
        if mode == RunMode.Train and rows[i + 1]["date"] > recipe["train_end"]:
            raise ValueError("Training label crosses the final training close")
        info = (
            __import__("datetime").date.fromisoformat(row["date"]),
            row["adjusted_close"],
            "\n".join(row["filingk"]) or None,
            "\n".join(row["filingq"]) or None,
            row["news"],
            label,
            False,
        )
        actor.step(info, mode)
        if errors:
            raise RuntimeError("Native handler intercepted transport error: " + errors[-1])
        record = {
            "date": row["date"],
            "arm": arm,
            "mode": mode.name,
            "direction": int(actor.portfolio.action_series[info[0]]),
            "native_cumulative_shares": int(actor.portfolio.holding_shares),
            "reflection": actor.reflection_result_series_dict[info[0]],
            "memory": memory_summary(actor),
            "requests": meter.request_trace[before:],
            "input_count": len(row["news"]) + len(row["filingk"]) + len(row["filingq"]),
            "latest_external_input_date": max(row["input_dates"], default=None),
        }
        all_records.append(record)
        step_count += 1
        with (output / "decisions.jsonl").open("a") as stream:
            stream.write(json.dumps(record, default=str) + "\n")
        atomic_json(
            output / "progress.json", {"arm": arm, "date": row["date"], "steps": step_count, "usage": meter.snapshot()}
        )
        print(
            arm,
            row["date"],
            record["direction"],
            "calls",
            len(record["requests"]),
            "spend",
            round(meter.snapshot()["study_committed_usd"], 4),
            flush=True,
        )
        if args.max_steps and step_count >= args.max_steps:
            raise SystemExit(0)
        if (PRIVATE / "PAUSE_FINMEM").exists():
            raise SystemExit("Paused after completed day; responses are durable.")

    # Overwrite only this driver's selected output record; paid requests always replay by content hash.
    (output / "decisions.jsonl").write_text("")
    for i, row in train:
        step(agent, i, row, "shared_training", RunMode.Train)
    trained = copy.deepcopy(agent)
    rng_state = (random.getstate(), np.random.get_state())
    for arm in recipe["arms"]:
        actor = copy.deepcopy(trained)
        actor.guardrail_endpoint = endpoint
        random.setstate(rng_state[0])
        np.random.set_state(rng_state[1])
        if arm == "semantic_only":
            for layer in LAYERS:
                memory = getattr(actor.brain, layer)
                memory._fidelity_native_query = memory.query
                memory.query = types.MethodType(semantic_query, memory)
        for i, row in test:
            step(actor, i, row, arm, RunMode.Test)
    atomic_json(
        output / "completion.json",
        {
            "status": "complete",
            "recipe_sha256": sha256(ROOT / "paper_runs/publication_upgrade_v1/finmem_recipe.json"),
            "input_sha256": sha256(PRIVATE / "finmem_inputs.json"),
            "script_sha256": sha256(Path(__file__)),
            "source_sha256": {str(p.relative_to(SOURCE)): sha256(p) for p in sorted((SOURCE / "puppy").glob("*.py"))},
            "decision_sha256": sha256(output / "decisions.jsonl"),
            "training_days": len(train),
            "test_days_per_arm": len(test),
            "usage": meter.snapshot(),
            "offline": args.offline,
            "source_failures": sum(not r["reflection"] for r in all_records),
            "api_errors": errors,
        },
    )
    print("COMPLETE", meter.snapshot(), flush=True)


if __name__ == "__main__":
    main()
