#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Run the source drivers unchanged except for a strictly read-only cache client."""

from pathlib import Path
import sys
import argparse
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.publication_replay import ReadOnlyReplay


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", choices=["FinMem", "FinAgent", "TradingAgents"], required=True)
    p.add_argument("--output-name", required=True)
    p.add_argument("--max-steps", type=int)
    args = p.parse_args()
    names = {
        "FinMem": "run_finmem_economic_fidelity",
        "FinAgent": "run_finagent_economic_fidelity",
        "TradingAgents": "run_tradingagents_economic_fidelity",
    }
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
    sys.argv = [str(path), "--offline", "--output-name", args.output_name]
    if args.max_steps:
        sys.argv += ["--max-days" if args.case == "TradingAgents" else "--max-steps", str(args.max_steps)]
    module.main()
    if guard_events:
        from alpha_evolve.openrouter_budget import atomic_json

        atomic_json(
            ROOT / "artifacts/publication_upgrade_v1" / args.output_name / "guardrail_validation_events.json",
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


if __name__ == "__main__":
    main()
