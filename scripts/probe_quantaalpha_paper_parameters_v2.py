#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Outcome-free real-source scheduler and active-parameter checks; no model calls."""

from pathlib import Path
import os
import sys
import socket
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/fidelity_completion_v2/dependencies/quantaalpha_b7ceb27"
OUT = ROOT / "artifacts/fidelity_completion_v2/quantaalpha_paper_parameter_validation"
sys.path[:0] = [str(ROOT / "src"), str(SOURCE)]
os.environ["OPENAI_API_KEY"] = "unused-offline-parameter-check"
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
OUT.mkdir(exist_ok=True)
os.chdir(OUT)


def offline(*args, **kwargs):
    raise RuntimeError("Source scheduler/parameter probe may not access network")


socket.create_connection = offline
socket.socket.connect = offline
urllib.request.urlopen = offline
from alpha_evolve.openrouter_budget import atomic_json, sha256
from quantaalpha.pipeline.evolution.controller import EvolutionConfig, EvolutionController
from quantaalpha.pipeline.evolution.trajectory import StrategyTrajectory
from quantaalpha.factors import proposal
from alpha_evolve.quantaalpha_paper_parameters_v2 import install_paper_parameters


def schedule(label):
    config = EvolutionConfig(
        num_directions=10,
        max_rounds=5,
        crossover_size=2,
        crossover_n=10,
        parallel_enabled=False,
        fresh_start=True,
        pool_save_path=str(OUT / (label + "_synthetic_scheduler_pool.json")),
    )
    controller = EvolutionController(config)
    guidance = []
    controller.mutation_op.generate_mutation_prompt_suffix = (
        lambda parent: guidance.append("mutation") or "OFFLINE SCHEDULER FIXTURE"
    )
    controller.crossover_op.generate_crossover_prompt_suffix = (
        lambda parents: guidance.append("crossover") or "OFFLINE SCHEDULER FIXTURE"
    )
    tasks = []
    while not controller.is_complete():
        task = controller.get_next_task()
        if task is None:
            break
        tasks.append({"round": task["round_idx"], "phase": task["phase"].value, "direction": task["direction_id"]})
        trajectory = StrategyTrajectory(
            trajectory_id=label + "_" + str(len(tasks)),
            direction_id=task["direction_id"],
            round_idx=task["round_idx"],
            phase=task["phase"],
            parent_ids=[p.trajectory_id for p in task["parent_trajectories"]],
            backtest_metrics={"RankIC": 0.01 + len(tasks) * 0.00001},
            extra_info={"synthetic_scheduler_fixture": True, "economic_result": False},
        )
        controller.report_task_complete(task, trajectory)
        if len(tasks) > 60:
            raise RuntimeError("Unexpected unbounded schedule")
    return {"tasks": tasks, "guidance_calls_stubbed": len(guidance), "actual_model_calls": 0}


before = schedule("unmodified")
wiring = install_paper_parameters()
after = schedule("guarded")
if len(before["tasks"]) != 51 or len(after["tasks"]) != 50 or max(t["round"] for t in after["tasks"]) != 4:
    raise ValueError("Native recursive-boundary regression did not reproduce/fix")
constructor = proposal.AlphaAgentHypothesis2FactorExpression(consistency_enabled=True)
gate = constructor.quality_gate
actual = {
    "symbol_length": constructor.factor_regulator.symbol_length_threshold,
    "base_features": constructor.factor_regulator.base_features_threshold,
    "duplication": constructor.factor_regulator.duplication_threshold,
    "consistency_enabled": constructor.consistency_enabled,
    "gate_consistency_enabled": gate.consistency_checker.enabled,
    "gate_symbol_length": gate.complexity_checker.symbol_length_threshold,
    "gate_base_features": gate.complexity_checker.base_features_threshold,
    "reference_zoo_rows": len(constructor.factor_regulator.alphazoo),
}
assert actual == {
    "symbol_length": 250,
    "base_features": 6,
    "duplication": 5,
    "consistency_enabled": True,
    "gate_consistency_enabled": True,
    "gate_symbol_length": 250,
    "gate_base_features": 6,
    "reference_zoo_rows": 0,
}
record = {
    "status": "pass",
    "scope": "Synthetic scheduler fixture only; no model, market data, account, economic result or historical trajectory is fabricated as evidence.",
    "before": before,
    "after": after,
    "active_parameters": actual,
    "wiring": wiring,
    "script_sha256": sha256(Path(__file__)),
    "helper_sha256": sha256(ROOT / "src/alpha_evolve/quantaalpha_paper_parameters_v2.py"),
}
atomic_json(OUT / "validation.json", record)
print("NATIVE_SCHEDULER_AND_PARAMETER_PROBE_PASS", len(before["tasks"]), len(after["tasks"]), flush=True)
