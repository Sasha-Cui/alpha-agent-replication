#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Replay v2 source executions with no network or ledger mutations, then compare every record."""

from pathlib import Path
import sys
import argparse
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.publication_replay import ReadOnlyReplay
from alpha_evolve.openrouter_budget import atomic_json, sha256
from validate_publication_replay import compare, read


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", choices=["FinMem", "FinAgent", "TradingAgents"], required=True)
    p.add_argument("--output-name", required=True)
    p.add_argument("--recipe", required=True)
    p.add_argument("--original-name", required=True)
    args = p.parse_args()
    names = {
        "FinMem": "run_finmem_fidelity_v2",
        "FinAgent": "run_finagent_fidelity_v2",
        "TradingAgents": "run_tradingagents_fidelity_v2",
    }
    private = ROOT / "artifacts/fidelity_completion_v2"
    if args.output_name == args.original_name or (private / args.output_name / "completion.json").exists():
        raise ValueError("Replay must use a distinct, unfinished output directory")
    original_completion = json.loads((private / args.original_name / "completion.json").read_text())
    if original_completion["status"] != "complete":
        raise ValueError("Only completed original executions can be validated")
    if original_completion["recipe_sha256"] != sha256(Path(args.recipe)):
        raise ValueError("Recipe changed since execution")
    path = ROOT / "scripts" / (names[args.case] + ".py")
    spec = importlib.util.spec_from_file_location("native_replay_driver", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def factory(root, key, *, model, study, cap, input_price, output_price, offline=False):
        return ReadOnlyReplay(
            root / "runs/economic_fidelity/openrouter",
            key,
            model,
            study=study,
            study_cap=cap,
            input_price=input_price,
            output_price=output_price,
        )

    wrapper_path = private / args.original_name / "wrapper.json"
    if args.case == "TradingAgents" and wrapper_path.exists():
        wrapper = json.loads(wrapper_path.read_text())
        if wrapper.get("news_view") == "source_style_full_text":
            from alpha_evolve.alphabet_news_view_v2 import install_news_view

            if sha256(ROOT / "src/alpha_evolve/alphabet_news_view_v2.py") != wrapper["news_view_implementation_sha256"]:
                raise ValueError("News view implementation changed since native execution")
            install_news_view(module.DatedTools)
        if wrapper.get("news_source_policy") == "single_frozen_company_corpus":
            from alpha_evolve.alphabet_news_sources_v2 import install_single_news_source

            if (
                sha256(ROOT / "src/alpha_evolve/alphabet_news_sources_v2.py")
                != wrapper["news_source_policy_implementation_sha256"]
            ):
                raise ValueError("News source policy changed since native execution")
            install_single_news_source(module.DatedTools)

    if args.case == "FinAgent" and wrapper_path.exists():
        wrapper = json.loads(wrapper_path.read_text())
        if wrapper.get("schema_repair") == "released_long_term_reasonig_alias":
            from alpha_evolve.finagent_schema_repair_v2 import install_schema_repair

            if (
                sha256(ROOT / "src/alpha_evolve/finagent_schema_repair_v2.py")
                != wrapper["schema_repair_implementation_sha256"]
            ):
                raise ValueError("Schema repair changed since execution")
            install_schema_repair(private / args.output_name)

    guard_events = []
    if args.case == "FinMem":
        import guardrails

        context = {}
        native_import = module.import_native

        def audited_import(meter):
            Agent, Mode = native_import(meter)
            native_step = Agent.step

            def step(self, market_info, run_mode):
                context.update(date=str(market_info[0]), mode=run_mode.name)
                return native_step(self, market_info, run_mode)

            Agent.step = step
            return Agent, Mode

        module.import_native = audited_import
        native_guard_call = guardrails.Guard.__call__

        def audited_guard(self, *call_args, **call_kwargs):
            try:
                result = native_guard_call(self, *call_args, **call_kwargs)
                guard_events.append(
                    {
                        **context,
                        "validation_passed": getattr(result, "validation_passed", None),
                        "validated_dictionary": isinstance(getattr(result, "validated_output", None), dict),
                    }
                )
                return result
            except Exception as error:
                guard_events.append({**context, "validation_passed": False, "exception_type": type(error).__name__})
                raise

        guardrails.Guard.__call__ = audited_guard
    module.canonical_meter = factory
    if args.case == "FinAgent":
        module.WaitingMeter = ReadOnlyReplay
    sys.argv = [str(path), "--offline", "--output-name", args.output_name, "--recipe", args.recipe]
    module.main()
    if guard_events:
        atomic_json(
            private / args.output_name / "guardrail_validation_events.json",
            {
                "events": guard_events,
                "test_validation_failures": sum(
                    event["mode"] == "Test" and event["validation_passed"] is False for event in guard_events
                ),
                "training_validation_failures": sum(
                    event["mode"] == "Train" and event["validation_passed"] is False for event in guard_events
                ),
                "scope": "Read-only instrumentation of the original Guard and Agent.step methods; outcomes are returned without modification.",
            },
        )

    extension = "json" if args.case == "TradingAgents" else "jsonl"
    original_path = private / args.original_name / ("decisions." + extension)
    replay_path = private / args.output_name / ("decisions." + extension)
    original, replay = read(original_path), read(replay_path)
    hash_key = "decisions_sha256" if args.case == "TradingAgents" else "decision_sha256"
    if hash_key in original_completion and sha256(original_path) != original_completion[hash_key]:
        raise ValueError("Original decisions changed since completion")
    prefix_proof = None
    if args.case == "FinAgent":
        symbol = json.loads(Path(args.recipe).read_text())["symbol"]
        prefix_path = private / "nfs_resume_20260917" / symbol / "decisions.jsonl"
        if prefix_path.exists():
            prefix = read(prefix_path)
            prefix_errors, prefix_maximum = compare(prefix, original[: len(prefix)])
            prefix_proof = {
                "status": "fail" if prefix_errors else "pass",
                "records": len(prefix),
                "maximum_numeric_difference": prefix_maximum[0],
                "differences": prefix_errors[:50],
                "prefix_sha256": sha256(prefix_path),
            }
            atomic_json(private / (args.original_name + "_preserved_prefix_validation.json"), prefix_proof)
            if prefix_errors:
                raise ValueError("Resumed native run differs from preserved pre-failure prefix")
    if wrapper_path.exists():
        wrapper = json.loads(wrapper_path.read_text())
        if wrapper.get("preserved_prefix_path"):
            partial = read(Path(wrapper["preserved_prefix_path"]))
            issues, delta = compare(partial, original[: len(partial)])
            atomic_json(
                private / (args.original_name + "_schema_prefix_validation.json"),
                {
                    "status": "fail" if issues else "pass",
                    "records": len(partial),
                    "maximum_numeric_difference": delta[0],
                    "differences": issues[:50],
                },
            )
            if issues:
                raise ValueError("Resumed run changed the completed pre-repair prefix")
    transport_prefixes = []
    for recovery in sorted(private.glob("transport_recovery*/recovery.json")):
        metadata = json.loads(recovery.read_text())
        for row in metadata["runs"]:
            if row["name"] != args.original_name:
                continue
            saved = recovery.parent / args.original_name / "artifacts/fidelity_completion_v2" / args.original_name / ("decisions." + extension)
            if not saved.exists():
                raise ValueError("Transport recovery is missing its preserved decisions")
            prefix = read(saved)
            errors, delta = compare(prefix, original[:len(prefix)])
            transport_prefixes.append({"status": "fail" if errors else "pass", "records": len(prefix), "maximum_numeric_difference": delta[0], "differences": errors[:50], "prefix_sha256": sha256(saved), "recovery": str(recovery.relative_to(ROOT))})
            if errors:
                raise ValueError("Transport resume changed completed economic/reasoning history")
    if transport_prefixes:
        atomic_json(private / (args.original_name + "_transport_prefix_validation.json"), transport_prefixes)
    differences, maximum = compare(original, replay)
    result = {
        "status": "pass" if not differences else "fail",
        "case": args.case,
        "original": args.original_name,
        "replay": args.output_name,
        "records": len(original),
        "replay_records": len(replay),
        "maximum_numeric_difference": maximum[0],
        "difference_count": len(differences),
        "differences": differences[:50],
        "original_sha256": sha256(original_path),
        "replay_sha256": sha256(replay_path),
        "recipe_sha256": sha256(Path(args.recipe)),
        "original_script_sha256": original_completion.get("script_sha256"),
        "replayed_script_sha256": sha256(path),
        "replay_wrapper_sha256": sha256(Path(__file__)),
        "network_allowed": False,
        "ledger_mutations_allowed": False,
        "preserved_prefix_validation": prefix_proof,
        "transport_prefix_validation": transport_prefixes,
        "ignored": "Only cached flags and order of independent transport events; all request identities, economic, timing, reasoning and memory fields compared.",
    }
    atomic_json(private / (args.original_name + "_full_replay_validation.json"), result)
    print(json.dumps(result), flush=True)
    if differences:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
