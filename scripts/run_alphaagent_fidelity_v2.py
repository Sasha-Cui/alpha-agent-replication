#!/usr/bin/env python3
# ruff: noqa: E402 - pinned native source bootstrap
"""Run the recovered AlphaAgent paper-era loop with budgeted SDK and CPU bindings."""

from pathlib import Path
import sys
import os
import json
import copy
import argparse
import subprocess
import random
from types import SimpleNamespace
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/fidelity_completion_v2/dependencies/alphaagent_95e478"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"
sys.path[:0] = [str(ROOT / "src"), str(SOURCE)]
from alpha_evolve.publication_llm import CohortOpenRouter
from alpha_evolve.publication_replay import ReadOnlyReplay
from alpha_evolve.openrouter_budget import read_key, sha256, atomic_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", choices=["source_gpt4turbo", "paper_gpt35"], default="source_gpt4turbo")
    parser.add_argument("--baseline-probe", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output-name", required=True)
    args = parser.parse_args()
    output = PRIVATE / args.output_name
    output.mkdir(parents=True, exist_ok=True)
    protocol_path = ROOT / "paper_runs/fidelity_completion_v2/alphaagent_search_protocol.json"
    protocol = json.loads(protocol_path.read_text())
    recipe = protocol["trials"][args.trial]
    data = json.loads((PRIVATE / "quantaalpha_data/manifest.json").read_text())
    os.environ.update(
        OPENAI_API_KEY="unused-SDK-bound-to-canonical-meter",
        CHAT_OPENAI_API_KEY="unused-SDK-bound-to-canonical-meter",
        OPENAI_BASE_URL="https://openrouter.ai/api/v1",
        FACTOR_CoSTEER_data_folder=str(PRIVATE / "quantaalpha_data/full"),
        FACTOR_CoSTEER_data_folder_debug=str(PRIVATE / "quantaalpha_data/debug"),
        FACTOR_CoSTEER_python_bin=sys.executable,
        MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING="false",
    )
    os.environ["PYTHONPATH"] = str(SOURCE) + os.pathsep + str(ROOT / "src")
    os.chdir(output)
    (output / "factor_zoo").mkdir(exist_ok=True)
    zoo = output / "factor_zoo/alpha101.csv"
    if not zoo.exists():
        os.link(SOURCE / "factor_zoo/alpha101.csv", zoo)
    if sha256(zoo) != protocol["alpha101_sha256"]:
        raise ValueError("Reference zoo changed")
    import numpy as np
    import pandas as pd
    import yaml

    np.random.seed(20260917)
    random.seed(20260917)
    from rdagent.oai.llm_utils import APIBackend
    from rdagent.oai.llm_conf import LLM_SETTINGS
    from rdagent.core.conf import RD_AGENT_SETTINGS

    LLM_SETTINGS.openai_api_key = "unused-SDK-bound-to-canonical-meter"
    LLM_SETTINGS.chat_model = recipe["source_model_name"]
    LLM_SETTINGS.embedding_model = "text-embedding-3-small"
    LLM_SETTINGS.openai_base_url = "https://openrouter.ai/api/v1"
    # Preserve original source decoding, JSON retry, streaming and continuation
    # behavior. The hard-budget transport exception bypasses network retries.
    if RD_AGENT_SETTINGS.multi_proc_n != 1:
        raise ValueError("Expected released serial worker default")
    meter_class = ReadOnlyReplay if args.offline else CohortOpenRouter
    meter = meter_class(
        ROOT / "runs/economic_fidelity/openrouter",
        "unused" if args.offline or args.baseline_probe else read_key(ROOT.parent / "KnowledgeTemplate/.env"),
        recipe["openrouter_model"],
        study="fidelity_v2_alphaagent_source_search",
        study_cap=20,
        input_price=recipe["input_price_per_million"],
        output_price=recipe["output_price_per_million"],
        offline=args.offline or args.baseline_probe,
    )
    calls, stages = [], []
    embedding_calls = []

    class MeteredStop(BaseException):
        pass

    def sdk_completion(**kwargs):
        if args.baseline_probe:
            raise MeteredStop("LLM calls forbidden in baseline probe")
        body = copy.deepcopy(kwargs)
        streaming = body.pop("stream", False)
        if body.pop("model") != recipe["source_model_name"]:
            raise MeteredStop("Unexpected model route")
        body["model"] = recipe["openrouter_model"]
        body["seed"] = recipe["api_seed_base"] + len(calls)
        try:
            response, key = meter.request("chat/completions", body)
        except Exception as exc:
            raise MeteredStop("Transport/budget failure; preserve reservation and inspect") from exc
        choice = response["choices"][0]
        calls.append(
            {
                "index": len(calls),
                "request_hash": key,
                "response_id": response.get("id"),
                "finish_reason": choice.get("finish_reason"),
                "api_seed": body["seed"],
            }
        )
        atomic_json(output / "model_calls.json", calls)
        content = choice["message"].get("content") or ""
        if streaming:
            return iter(
                [
                    SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                delta=SimpleNamespace(content=content), finish_reason=choice.get("finish_reason")
                            )
                        ]
                    )
                ]
            )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=choice.get("finish_reason"))
            ],
            usage=SimpleNamespace(**response.get("usage", {})),
        )

    def sdk_embedding(**kwargs):
        if args.baseline_probe:
            raise MeteredStop("Embedding calls forbidden in baseline probe")
        body = copy.deepcopy(kwargs)
        if body.pop("model") != "text-embedding-3-small":
            raise MeteredStop("Unexpected embedding route")
        body["model"] = "openai/text-embedding-3-small"
        try:
            response, key = meter.request("embeddings", body, input_price=0.02, output_price=0)
        except Exception as exc:
            raise MeteredStop("Embedding transport/budget failure; preserve reservation") from exc
        rows = sorted(response["data"], key=lambda row: row["index"])
        if any(len(row["embedding"]) != 1536 for row in rows):
            raise MeteredStop("Unexpected source-example embedding dimension")
        embedding_calls.append({"request_hash": key, "rows": len(rows), "dimensions": 1536})
        atomic_json(output / "embedding_calls.json", embedding_calls)
        return SimpleNamespace(data=[SimpleNamespace(embedding=row["embedding"]) for row in rows])

    original_init = APIBackend.__init__

    def bound_init(self, *a, **kw):
        original_init(self, *a, **kw)
        self.chat_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=sdk_completion)))
        self.embedding_client = SimpleNamespace(embeddings=SimpleNamespace(create=sdk_embedding))

    APIBackend.__init__ = bound_init

    from rdagent.scenarios.qlib.experiment.workspace import QlibFBWorkspace
    from rdagent.log import rdagent_logger as logger

    def execute(self, qlib_config_name="conf.yaml", run_env=None, *a, **kw):
        path = self.workspace_path / qlib_config_name
        config = yaml.safe_load(path.read_text())
        config["qlib_init"]["provider_uri"] = data["provider_path"]
        path.write_text(yaml.safe_dump(config, sort_keys=False))
        qlib_wrapper = str(ROOT / "scripts/run_alphaagent_paper_qlib_python.sh")
        for i, command in enumerate(
            [
                [qlib_wrapper, str(ROOT / "scripts/run_quantaalpha_child_v2.py"), qlib_config_name],
                [qlib_wrapper, "read_exp_res.py"],
            ]
        ):
            completed = subprocess.run(
                command,
                cwd=self.workspace_path,
                env={**os.environ, **(run_env or {})},
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
            )
            (self.workspace_path / ("native_qrun.log" if i == 0 else "native_metrics.log")).write_text(completed.stdout)
            if completed.returncode:
                raise RuntimeError("Native Qlib child failed: " + str(self.workspace_path))
        result = self.workspace_path / "qlib_res.csv"
        if not result.exists():
            raise RuntimeError("Native Qlib metrics absent")
        logger.log_object(pd.read_pickle(self.workspace_path / "ret.pkl"), tag="Quantitative Backtesting Chart")
        return pd.read_csv(result, index_col=0).iloc[:, 0]

    QlibFBWorkspace.execute = execute
    logger.set_trace_path(output / "log")
    source_hashes = {str(p.relative_to(SOURCE)): sha256(p) for p in sorted((SOURCE / "rdagent").rglob("*.py"))}
    execution_recipe = {
        "trial": args.trial,
        "protocol_sha256": sha256(protocol_path),
        "wrapper_sha256": sha256(Path(__file__)),
        "child_wrapper_sha256": sha256(ROOT / "scripts/run_quantaalpha_child_v2.py"),
        "data_manifest_sha256": sha256(PRIVATE / "quantaalpha_data/manifest.json"),
        "source_python_hashes": source_hashes,
        "actual_source_defaults": {
            "temperature": LLM_SETTINGS.chat_temperature,
            "max_tokens": LLM_SETTINGS.chat_max_tokens,
            "max_retry": LLM_SETTINGS.max_retry,
            "stream": LLM_SETTINGS.chat_stream,
            "multi_proc_n": RD_AGENT_SETTINGS.multi_proc_n,
        },
        "model": recipe["openrouter_model"],
        "embedding_model": "openai/text-embedding-3-small",
        "native_embedding_method_preserved": True,
    }
    record_path = output / "execution_recipe.json"
    if record_path.exists() and json.loads(record_path.read_text()) != execution_recipe:
        raise ValueError("Execution changed after freeze; preserve attempt and record an amendment")
    atomic_json(record_path, execution_recipe)
    from rdagent.components.workflow.alphaagent_loop import AlphaAgentLoop
    from rdagent.app.qlib_rd_loop.conf import ALPHA_AGENT_FACTOR_PROP_SETTING

    for name in AlphaAgentLoop.steps:
        original = getattr(AlphaAgentLoop, name)

        def audited(self, *a, _original=original, _name=name, **kw):
            event = {
                "stage": _name,
                "loop_index": self.loop_idx,
                "model_calls_before": len(calls),
                "started_utc": datetime.now(timezone.utc).isoformat(),
            }
            stages.append(event)
            atomic_json(output / "stages.json", stages)
            result = _original(self, *a, **kw)
            event.update(completed=True, model_calls_after=len(calls))
            atomic_json(output / "stages.json", stages)
            return result

        setattr(AlphaAgentLoop, name, audited)
    instance = AlphaAgentLoop(ALPHA_AGENT_FACTOR_PROP_SETTING, None)
    if args.baseline_probe:
        from rdagent.scenarios.qlib.experiment.factor_experiment import QlibFactorExperiment

        exp = instance.runner.develop(QlibFactorExperiment(sub_tasks=[]))
        if exp.result is None:
            raise RuntimeError("Baseline has no result")
        exp.result.to_csv(output / "native_baseline_metrics.csv")
        atomic_json(
            output / "baseline_probe.json",
            {
                "status": "pass",
                "paid_calls": len(calls),
                "workspace": str(exp.experiment_workspace.workspace_path),
                "reference_zoo_rows": len(instance.factor_constructor.alphazoo),
            },
        )
        print("ALPHAAGENT_NATIVE_BASELINE_PASS", flush=True)
        return
    instance.run(step_n=recipe["source_steps"])
    trajectories = []
    for hypothesis, experiment, feedback in instance.trace.hist:
        trajectories.append(
            {
                "hypothesis": str(hypothesis),
                "factors": [task.get_task_information_and_implementation_result() for task in experiment.sub_tasks],
                "feedback": str(feedback),
                "metrics": {str(k): float(v) for k, v in experiment.result.items()}
                if experiment.result is not None
                else None,
                "workspace": str(experiment.experiment_workspace.workspace_path),
                "factor_workspaces": [str(workspace.workspace_path) for workspace in experiment.sub_workspace_list],
            }
        )
    atomic_json(output / "trajectories.json", trajectories)
    atomic_json(
        output / "execution_exit.json",
        {
            "status": "native_loop_returned",
            "completed_trajectories": len(trajectories),
            "requested_source_steps": recipe["source_steps"],
            "finished_stages": sum(e.get("completed", False) for e in stages),
            "model_calls": len(calls),
            "usage": meter.snapshot(),
            "requires_independent_trajectory_causality_and_account_validation": True,
            "full_original_paper_reproduced": False,
        },
    )
    print("NATIVE_SOURCE_LOOP_RETURNED", len(trajectories), len(calls), flush=True)


if __name__ == "__main__":
    main()
