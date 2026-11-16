#!/usr/bin/env python3
# ruff: noqa: E402 - runtime source bootstrap
"""Execute pinned QuantaAlpha planning/evolution with metered source-default LLM calls."""

from pathlib import Path
import sys
import os
import json
import argparse
import subprocess
import copy
import random
import hashlib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/fidelity_completion_v2/dependencies/quantaalpha_b7ceb27"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"
sys.path[:0] = [str(ROOT / "src"), str(SOURCE)]
from alpha_evolve.publication_llm import CohortOpenRouter
from alpha_evolve.publication_replay import ReadOnlyReplay
from alpha_evolve.openrouter_budget import read_key, atomic_json, sha256


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--probe", action="store_true")
    p.add_argument("--baseline-probe", action="store_true")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--resume-prefix", type=Path)
    p.add_argument("--output-name", default="quantaalpha_fresh")
    args = p.parse_args()
    if args.resume_prefix:
        args.resume_prefix = args.resume_prefix.resolve()
    output = PRIVATE / args.output_name
    output.mkdir(exist_ok=True)
    data = json.loads((PRIVATE / "quantaalpha_data/manifest.json").read_text())
    os.environ.update(
        OPENAI_API_KEY="unused-native-network-rebound-to-meter",
        CHAT_OPENAI_API_KEY="unused-native-network-rebound-to-meter",
        DATA_RESULTS_DIR=str(output / "results"),
        QLIB_DATA_DIR=data["provider_path"],
        FACTOR_CoSTEER_data_folder=str(PRIVATE / "quantaalpha_data/full"),
        FACTOR_CoSTEER_data_folder_debug=str(PRIVATE / "quantaalpha_data/debug"),
        FACTOR_CoSTEER_python_bin=sys.executable,
        LITELLM_LOCAL_MODEL_COST_MAP="True",
        MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING="false",
    )
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    os.environ["PYTHONPATH"] = str(SOURCE) + os.pathsep + str(ROOT / "src")
    os.chdir(output)
    import numpy as np
    import pandas as pd
    import yaml

    np.random.seed(20260917)
    random.seed(20260917)
    from quantaalpha.llm.client import APIBackend
    from quantaalpha.llm.config import LLM_SETTINGS

    LLM_SETTINGS.openai_api_key = "unused-native-network-rebound-to-meter"
    LLM_SETTINGS.chat_model = "gpt-4-turbo"
    LLM_SETTINGS.reasoning_model = "gpt-4-turbo"
    LLM_SETTINGS.openai_base_url = "https://openrouter.ai/api/v1"
    LLM_SETTINGS.chat_temperature = 0.5
    LLM_SETTINGS.chat_max_tokens = 3000
    # Preserve released JSON/format retries. MeteredStop bypasses only transport/budget retries.
    meter_class = ReadOnlyReplay if args.offline else CohortOpenRouter
    meter = meter_class(
        ROOT / "runs/economic_fidelity/openrouter",
        "unused"
        if args.offline or args.probe or args.baseline_probe
        else read_key(ROOT.parent / "KnowledgeTemplate/.env"),
        "openai/gpt-4-turbo",
        study="fidelity_v2_quantaalpha_fresh_search",
        study_cap=75,
        input_price=10,
        output_price=30,
        offline=args.offline or args.probe or args.baseline_probe,
    )
    embedding_recipe_path = ROOT / "paper_runs/fidelity_completion_v2/quantaalpha_embedding_amendment.json"
    embedding_recipe = json.loads(embedding_recipe_path.read_text())
    LLM_SETTINGS.embedding_model = embedding_recipe["model"]
    embedding_meter = meter_class(
        ROOT / "runs/economic_fidelity/openrouter",
        "unused"
        if args.offline or args.probe or args.baseline_probe
        else read_key(ROOT.parent / "KnowledgeTemplate/.env"),
        embedding_recipe["model"],
        study="fidelity_v2_quantaalpha_fresh_search",
        study_cap=75,
        provider=embedding_recipe["provider"],
        input_price=embedding_recipe["input_price_per_million"],
        output_price=0,
        offline=args.offline or args.probe or args.baseline_probe,
    )
    prior_calls = json.loads(args.resume_prefix.resolve().read_text()) if args.resume_prefix else []
    calls = []
    embedding_calls = []

    from types import SimpleNamespace

    class MeteredStop(BaseException):
        pass

    def sdk_completion(**kwargs):
        index = len(calls)
        body = copy.deepcopy(kwargs)
        streaming = body.pop("stream", False)
        model = body.pop("model")
        if model != "gpt-4-turbo":
            raise MeteredStop("Unexpected source model route: " + repr(model))
        body["model"] = "openai/" + model
        body["seed"] = 170000 + index
        if args.probe or args.baseline_probe:
            raise MeteredStop("Model call forbidden during construction probe")
        if index < len(prior_calls):
            request = {**body, "provider": {"order": ["OpenAI"], "allow_fallbacks": False}}
            envelope = {"endpoint": "chat/completions", "request": request}
            key = hashlib.sha256(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if key != prior_calls[index]["request_hash"]:
                atomic_json(
                    output / "prefix_mismatch.json",
                    {"index": index, "expected": prior_calls[index]["request_hash"], "actual": key, "request": request},
                )
                raise MeteredStop("Saved chat prefix differs; no new charge permitted before inspection")
        try:
            response, key = meter.request("chat/completions", body)
        except Exception as exc:
            raise MeteredStop("Metered transport/budget failure; retain reservation and inspect") from exc
        choice = response["choices"][0]
        calls.append(
            {
                "index": index,
                "request_hash": key,
                "response_id": response.get("id"),
                "finish_reason": choice.get("finish_reason"),
                "api_seed": body["seed"],
            }
        )
        atomic_json(output / "model_calls.json", calls)
        if prior_calls and len(calls) == len(prior_calls):
            atomic_json(
                output / "prefix_validation.json",
                {
                    "status": "pass",
                    "chat_calls": len(prior_calls),
                    "exact_request_identities": True,
                    "prior_calls_sha256": sha256(args.resume_prefix.resolve()),
                },
            )
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
        if args.probe or args.baseline_probe:
            raise MeteredStop("Embedding calls forbidden during probe")
        body = copy.deepcopy(kwargs)
        if body.get("model") != embedding_recipe["model"]:
            raise MeteredStop("Unexpected embedding model route")
        body["dimensions"] = embedding_recipe["dimensions"]
        try:
            response, key = embedding_meter.request(
                "embeddings", body, input_price=embedding_recipe["input_price_per_million"], output_price=0
            )
        except Exception as exc:
            raise MeteredStop("Embedding transport/budget failure; retain reservation") from exc
        rows = sorted(response["data"], key=lambda row: row["index"])
        if any(len(row["embedding"]) != embedding_recipe["dimensions"] for row in rows):
            raise MeteredStop("Unexpected embedding dimensions")
        embedding_calls.append({"request_hash": key, "rows": len(rows), "dimensions": embedding_recipe["dimensions"]})
        atomic_json(output / "embedding_calls.json", embedding_calls)
        return SimpleNamespace(data=[SimpleNamespace(embedding=row["embedding"]) for row in rows])

    native_backend_init = APIBackend.__init__

    def backend_init(self, *backend_args, **backend_kwargs):
        native_backend_init(self, *backend_args, **backend_kwargs)
        self.chat_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=sdk_completion)))
        self.embedding_client = SimpleNamespace(embeddings=SimpleNamespace(create=sdk_embedding))

    APIBackend.__init__ = backend_init

    from quantaalpha.factors.workspace import QlibFBWorkspace
    from rdagent.scenarios.qlib.experiment.workspace import QlibFBWorkspace as BaseWorkspace

    def before_execute(self):
        BaseWorkspace.before_execute(self)
        # Other copied files include unrendered Jinja model templates.
        # Only the selected configuration is concrete YAML, parsed at execution.

    def execute(self, qlib_config_name="conf.yaml", run_env=None, **kwargs):
        path = self.workspace_path / qlib_config_name
        config = yaml.safe_load(path.read_text())
        if not isinstance(config, dict) or "qlib_init" not in config:
            raise ValueError("Selected backtest config has no qlib_init")
        config["qlib_init"]["provider_uri"] = data["provider_path"]
        path.write_text(yaml.safe_dump(config, sort_keys=False))
        env = {**os.environ, **(run_env or {})}
        logs = []
        for command in [
            [sys.executable, str(ROOT / "scripts/run_quantaalpha_child_v2.py"), qlib_config_name],
            [sys.executable, "read_exp_res.py"],
        ]:
            completed = subprocess.run(
                command,
                cwd=self.workspace_path,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=1200,
            )
            logs.append(completed.stdout)
            (self.workspace_path / ("native_qrun.log" if len(logs) == 1 else "native_metrics.log")).write_text(
                completed.stdout
            )
            if completed.returncode:
                raise RuntimeError("Native Qlib child failed; inspect " + str(self.workspace_path))
        result = self.workspace_path / "qlib_res.csv"
        if not result.exists():
            raise RuntimeError("Native metrics were not produced")
        return pd.read_csv(result, index_col=0).iloc[:, 0], "\n".join(logs)

    QlibFBWorkspace.before_execute = before_execute
    QlibFBWorkspace.execute = execute
    recipe = {
        "study": "quantaalpha_fresh_source_defaults",
        "source_commit": "b7ceb27b1001261d7a95b209a963664ae1f8ab23",
        "config_sha256": sha256(SOURCE / "configs/experiment.yaml"),
        "model": "openai/gpt-4-turbo",
        "temperature": 0.5,
        "max_tokens": 3000,
        "initial_direction": "Price-Volume Factor Mining",
        "settings": "Exact release defaults:2directions,3evolutionrounds,1factor perhypothesis; consistency off, complexity/redundancy on as configured",
        "cache_identity": "Distinct prespecified API seed per source call to prevent repeated prompts sharing one cached generation; exact saved-response replay, no vendor determinism claim",
        "adaptations": [
            "Metered SDK binding reassembles the response as one stream chunk; original message construction, JSON repair, penalties and auto-continuation execute unchanged",
            "Budget/transport errors stop rather than bypass accounting",
            "Native qrun/read_exp_res executed in central runtime instead of Docker/conda provisioning",
            "Qlib provider path rebound to verified archive; Git metadata hooks disabled",
            "Runtime-description prompt reflects actual central packages instead of attempting absent conda introspection",
        ],
        "data_manifest_sha256": sha256(PRIVATE / "quantaalpha_data/manifest.json"),
        "wrapper_sha256": sha256(Path(__file__)),
        "embedding_amendment_sha256": sha256(embedding_recipe_path),
        "embedding_model": embedding_recipe["model"],
        "embedding_dimensions": embedding_recipe["dimensions"],
        "embedding_method_preserved": True,
        "full_original_paper_reproduced": False,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    recipe_path = output / "recipe.json"
    if recipe_path.exists():
        saved = json.loads(recipe_path.read_text())
        if saved["embedding_amendment_sha256"] != recipe["embedding_amendment_sha256"]:
            raise ValueError("Embedding amendment changed after freeze")
        for key in [
            "source_commit",
            "config_sha256",
            "model",
            "temperature",
            "max_tokens",
            "initial_direction",
            "data_manifest_sha256",
            "wrapper_sha256",
            "embedding_amendment_sha256",
        ]:
            if saved[key] != recipe[key]:
                raise ValueError("Execution changed after recipe freeze: " + key)
    else:
        atomic_json(recipe_path, recipe)
    from quantaalpha.log import logger

    logger.set_trace_path(output / "log")
    import importlib.metadata
    from quantaalpha.factors.experiment import QlibAlphaAgentScenario

    runtime_description = json.dumps(
        {
            "python": sys.version.split()[0],
            "runtime": "Central CPU virtual environment; no conda provisioning",
            "packages": {
                name: importlib.metadata.version(name)
                for name in ["numpy", "pandas", "scipy", "rdagent", "pyqlib", "tables", "lightgbm", "mlflow"]
            },
        },
        sort_keys=True,
    )
    QlibAlphaAgentScenario.get_runtime_environment = lambda self: runtime_description
    atomic_json(output / "runtime.json", json.loads(runtime_description))
    from quantaalpha.pipeline.loop import AlphaAgentLoop
    from quantaalpha.pipeline.settings import ALPHA_AGENT_FACTOR_PROP_SETTING

    if args.probe or args.baseline_probe:
        instance = AlphaAgentLoop(
            ALPHA_AGENT_FACTOR_PROP_SETTING,
            potential_direction="Price-Volume Factor Mining",
            stop_event=None,
            use_local=True,
        )
        if args.baseline_probe:
            from quantaalpha.factors.experiment import QlibFactorExperiment

            exp = QlibFactorExperiment(sub_tasks=[])
            result = instance.runner.develop(exp, use_local=True)
            if result.result is None:
                raise RuntimeError("Baseline returned no native result")
            result.result.to_csv(output / "native_baseline_metrics.csv")
            atomic_json(
                output / "baseline_probe.json",
                {"status": "pass", "paid_calls": len(calls), "workspace": str(exp.experiment_workspace.workspace_path)},
            )
            print("NATIVE_BASELINE_PROBE_PASS")
            return
        atomic_json(
            output / "construction_probe.json",
            {
                "status": "pass",
                "class": type(instance).__name__,
                "paid_calls": 0,
                "source_config_sha256": recipe["config_sha256"],
            },
        )
        print("SOURCE_CONSTRUCTION_PROBE_PASS")
        return
    from quantaalpha.pipeline.factor_mining import main as native_main

    native_main(
        direction=recipe["initial_direction"], config_path=str(SOURCE / "configs/experiment.yaml"), evolution_mode=True
    )
    atomic_json(
        output / "execution_exit.json",
        {
            "status": "native_pipeline_returned",
            "model_calls": len(calls),
            "usage": meter.snapshot(),
            "requires_trajectory_and_account_validation": True,
        },
    )


if __name__ == "__main__":
    main()
