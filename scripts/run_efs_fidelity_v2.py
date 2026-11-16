#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source bootstrap
"""Additional independent EFS searches using the unchanged pinned economic engine."""

from pathlib import Path
import sys
import argparse
import json
import importlib.util
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.publication_llm import CohortOpenRouter
from alpha_evolve.publication_replay import ReadOnlyReplay
from alpha_evolve.openrouter_budget import atomic_json, sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    out = ROOT / "paper_runs/fidelity_completion_v2/efs" / args.trial
    private = ROOT / "artifacts/fidelity_completion_v2/efs" / args.trial
    recipe = json.loads((out / "recipe.json").read_text())
    path = ROOT / "scripts/run_efs_economic_fidelity.py"
    spec = importlib.util.spec_from_file_location("frozen_efs_driver", path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    driver.OUT = out
    driver.PRIVATE = private

    class Adapter:
        def __init__(self, root, key, model, **kwargs):
            cls = ReadOnlyReplay if args.offline else CohortOpenRouter
            self.meter = cls(
                root,
                "unused" if args.offline else key,
                model,
                study="fidelity_v2_efs_trials",
                study_cap=35,
                provider=recipe["provider_name"],
                input_price=recipe["input_usd_per_million"],
                output_price=recipe["output_usd_per_million"],
                offline=args.offline,
            )

        def complete(self, messages, **kwargs):
            return self.meter.chat(messages, seed=recipe["api_seed"], **kwargs)

        def snapshot(self):
            return self.meter.snapshot()

    driver.MeteredOpenRouter = Adapter
    atomic_json(
        private / "execution_wrapper.json",
        {
            "wrapper_sha256": sha256(Path(__file__)),
            "original_driver_sha256": sha256(path),
            "trial": args.trial,
            "api_seed": recipe["api_seed"],
            "provider": recipe["provider_name"],
            "scope": "Identical numerical engine and source prompt; distinct prespecified API seeds keep trial requests separate. Exact response replay, not a guarantee of deterministic vendor sampling.",
        },
    )
    driver.run(SimpleNamespace(mode="llm", key_env_file=ROOT.parent / "KnowledgeTemplate/.env"))


if __name__ == "__main__":
    main()
