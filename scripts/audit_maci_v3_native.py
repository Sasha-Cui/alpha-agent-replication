#!/usr/bin/env python3
"""Execute the recoverable cryptoMAS v3 source without external API calls."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any


EXPECTED_HEAD = "318e0fe905fed8b7f544322c3db1dfed6784d178"
UNIVERSE = [
    "BTC",
    "ETH",
    "BNB",
    "XRP",
    "SOL",
    "TRX",
    "ADA",
    "BCH",
    "HYPE",
    "XMR",
    "ZEC",
    "LTC",
    "SUI",
    "AVAX",
    "HBAR",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def exc_text(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def compile_sources(repo: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(repo.rglob("*.py")):
        if ".git" in path.relative_to(repo).parts:
            continue
        try:
            compile(path.read_bytes(), str(path), "exec")
            rows.append({"path": path.relative_to(repo).as_posix(), "passed": True, "exception": ""})
        except Exception as exc:
            rows.append({"path": path.relative_to(repo).as_posix(), "passed": False, "exception": exc_text(exc)})
    return {
        "python_file_count": len(rows),
        "all_passed": all(row["passed"] for row in rows),
        "failures": [row for row in rows if not row["passed"]],
    }


def import_contract(repo: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="maci-v3-import-") as temp:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(repo)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["OPENAI_API_KEY"] = "audit-placeholder-no-call"
        result = subprocess.run(
            [sys.executable, "-m", "scripts.run_experiment", "--help"],
            cwd=temp,
            env=env,
            capture_output=True,
            text=True,
        )
    stderr = result.stderr.strip()
    last = stderr.splitlines()[-1] if stderr else ""
    return {
        "command": f"{sys.executable} -m scripts.run_experiment --help",
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "stderr_last_line": last,
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
    }


def dependency_contract(repo: Path) -> dict[str, Any]:
    source = (repo / "environ/agents/base.py").read_text(encoding="utf-8")
    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    readme = (repo / "README.md").read_text(encoding="utf-8")
    declared = [
        "numpy",
        "pandas",
        "scipy",
        "requests",
        "matplotlib",
        "seaborn",
        "openai",
        "beautifulsoup4",
        "lxml",
        "python-dateutil",
        "tqdm",
        "python-dotenv",
        "tiktoken",
        "torch",
        "scikit-learn",
        "neuralforecast",
    ]
    module_names = {
        "beautifulsoup4": "bs4",
        "python-dateutil": "dateutil",
        "python-dotenv": "dotenv",
        "scikit-learn": "sklearn",
    }
    installed = {name: importlib.util.find_spec(module_names.get(name, name)) is not None for name in declared}
    return {
        "declared_python_requirement": ">=3.10",
        "declared_dependency_count": len(declared),
        "declared_dependencies_in_current_audit_environment": installed,
        "anthropic_imported_by_source": "import anthropic" in source,
        "anthropic_declared": '"anthropic"' in pyproject,
        "readme_fetch_spaces_command_present": "python scripts/fetch_spaces.py" in readme,
        "readme_fetch_spaces_file_present": (repo / "scripts/fetch_spaces.py").is_file(),
        "missing_source_modules": [
            "environ.data.coingecko",
            "environ.data.cointelegraph",
            "environ.data.rag_store",
        ],
        "source_modules_present_in_any_public_history_commit": {
            "environ/data/coingecko.py": False,
            "environ/data/cointelegraph.py": False,
            "environ/data/rag_store.py": False,
        },
    }


def make_fake_run(kind: str, calls: list[dict[str, Any]]):
    def run(self, context: dict, memorize: bool = True):
        calls.append(
            {
                "kind": kind,
                "week": context.get("week"),
                "memorize": memorize,
                "context_keys": sorted(context),
            }
        )
        if kind == "crypto":
            output: Any = [{"symbol": "BTC", "signal": 0.25, "confidence": 0.8, "rationale": "fixture"}]
        elif kind == "news":
            output = {
                "week": context.get("week"),
                "overall_sentiment": 0.1,
                "overall_rationale": "fixture",
                "coin_signals": [],
            }
        else:
            output = [{"symbol": "BTC", "action": 0.2, "rationale": "fixture"}]
        if memorize:
            self._store_memory(context.get("week", "unknown"), output)
        return output

    return run


@contextmanager
def disabled_rag_build(module):
    original = module._build_rag_store
    module._build_rag_store = lambda capability, rag_end_date="2026-01-01": None
    try:
        yield
    finally:
        module._build_rag_store = original


def exercise_architecture(cls, capability: str, module, overlay: bool) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    context = disabled_rag_build(module) if overlay else nullcontext()
    try:
        with context:
            system = cls(
                capability=capability,
                model="gpt-4o",
                temperature=0.0,
            )
        system.crypto_agent.run = types.MethodType(make_fake_run("crypto", calls), system.crypto_agent)
        system.news_agent.run = types.MethodType(make_fake_run("news", calls), system.news_agent)
        system.trading_agent.run = types.MethodType(make_fake_run("trading", calls), system.trading_agent)
        result = system.run(
            week="2025-W02",
            indicators=[{"symbol": "BTC", "close": list(range(1, 31)), "volume": [1] * 30, "market_cap": [1] * 30}],
            articles=[{"title": "fixture"}],
            portfolio={"cash": 100000.0, "holdings": {}},
        )
        state = system.get_memory_state()
        return {
            "passed": result == [{"symbol": "BTC", "action": 0.2, "rationale": "fixture"}],
            "exception": "",
            "call_count": len(calls),
            "call_kinds": [row["kind"] for row in calls],
            "context_key_sets": [row["context_keys"] for row in calls],
            "memory_entry_counts": {name: len(value) for name, value in state.items()},
            "rag_store_overlay": overlay,
            "llm_calls": 0,
        }
    except Exception as exc:
        return {
            "passed": False,
            "exception": exc_text(exc),
            "call_count": len(calls),
            "rag_store_overlay": overlay,
            "llm_calls": 0,
        }


def architecture_contract() -> dict[str, Any]:
    hierarchical = importlib.import_module("environ.architectures.hierarchical")
    collaborative = importlib.import_module("environ.architectures.collaborative")
    debate = importlib.import_module("environ.architectures.debate")
    specs = [
        ("hierarchical", hierarchical.HierarchicalMAS, hierarchical),
        ("collaborative", collaborative.CollaborativeMAS, collaborative),
        ("debate", debate.DebateMAS, debate),
    ]
    rows = []
    for name, cls, module in specs:
        for capability in ("zero_shot", "chain_of_thought", "skill"):
            rows.append(
                {
                    "architecture": name,
                    "capability": capability,
                    "execution_kind": "unmodified_source_with_fixture_agent_outputs",
                    **exercise_architecture(cls, capability, module, overlay=False),
                }
            )
        direct = exercise_architecture(cls, "rag", module, overlay=False)
        rows.append(
            {
                "architecture": name,
                "capability": "rag",
                "execution_kind": "unmodified_source_expected_failure",
                **direct,
            }
        )
        rows.append(
            {
                "architecture": name,
                "capability": "rag",
                "execution_kind": "missing_rag_store_overlay_with_fixture_agent_outputs",
                **exercise_architecture(cls, "rag", module, overlay=True),
            }
        )
    return {
        "rows": rows,
        "unmodified_non_rag_passed": sum(
            row["passed"] and row["execution_kind"].startswith("unmodified") and row["capability"] != "rag"
            for row in rows
        ),
        "unmodified_non_rag_denominator": 9,
        "unmodified_rag_failures": sum(
            not row["passed"] and row["execution_kind"] == "unmodified_source_expected_failure" for row in rows
        ),
        "unmodified_rag_denominator": 3,
        "overlay_rag_passed": sum(row["passed"] and row["execution_kind"].startswith("missing_rag") for row in rows),
        "overlay_rag_denominator": 3,
        "paper_result_credit": False,
    }


def single_agent_alias_contract() -> dict[str, Any]:
    base_arch = importlib.import_module("environ.architectures.base_arch")
    mapped = {
        capability: base_arch._llm_capability(capability)
        for capability in ("zero_shot", "chain_of_thought", "rag", "skill")
    }
    return {
        "runner_capability_to_agent_capability": mapped,
        "rag_is_distinct_in_single_agent_wrapper": mapped["rag"] != mapped["zero_shot"],
        "skill_is_distinct_in_single_agent_wrapper": mapped["skill"] != mapped["zero_shot"],
        "paper_reports_distinct_single_agent_rag_and_skill_results": True,
        "paper_result_credit": False,
    }


def install_fake_data_modules() -> None:
    import pandas as pd

    package = types.ModuleType("environ.data")
    package.__path__ = []
    coingecko = types.ModuleType("environ.data.coingecko")
    coingecko.SYMBOL_TO_ID = {symbol: symbol.lower() for symbol in UNIVERSE}

    def load_asset(symbol: str):
        index = pd.date_range("2024-12-01", "2025-12-31", freq="D", tz="UTC")
        return pd.DataFrame({"close": [100.0] * len(index)}, index=index)

    def snapshots(as_of, lookback_days=30):
        return [
            {
                "symbol": symbol,
                "close": [100.0] * lookback_days,
                "volume": [1.0] * lookback_days,
                "market_cap": [10.0] * lookback_days,
            }
            for symbol in UNIVERSE
        ]

    coingecko.load_asset = load_asset
    coingecko.get_raw_snapshots_all = snapshots
    cointelegraph = types.ModuleType("environ.data.cointelegraph")

    class CointelegraphFetcher:
        def __init__(self, output_dir: str):
            self.output_dir = output_dir

        def load_week(self, week: str):
            return [{"week": week, "title": "fixture"}]

    cointelegraph.CointelegraphFetcher = CointelegraphFetcher
    sys.modules["environ.data"] = package
    sys.modules["environ.data.coingecko"] = coingecko
    sys.modules["environ.data.cointelegraph"] = cointelegraph


def runner_overlay_contract() -> dict[str, Any]:
    install_fake_data_modules()
    runner = importlib.import_module("scripts.run_experiment")
    with tempfile.TemporaryDirectory(prefix="maci-v3-dry-run-") as temp:
        output = Path(temp) / "output"
        runner.run_combination(
            "hierarchical",
            "zero_shot",
            ["2025-W02"],
            dry_run=True,
            model="gpt-4o",
            output_dir=output,
        )
        record_path = output / "hierarchical_zero_shot" / "2025-W02.json"
        state_path = output / "hierarchical_zero_shot" / "_state.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        state = json.loads(state_path.read_text(encoding="utf-8"))
    return {
        "passed": (
            len(record["trading_actions"]) == 15
            and record["portfolio_before"]["total_value"] == 100000.0
            and record["portfolio_after"]["total_value"] == 100000.0
            and state["memory"] == {}
        ),
        "week": record["week"],
        "universe": list(record["execution_prices"]),
        "record_keys": sorted(record),
        "source_modified": False,
        "supplied_overlay": "in_memory fake environ.data.coingecko and environ.data.cointelegraph modules",
        "dry_run_placeholder_only": True,
        "llm_calls": 0,
        "paper_result_credit": False,
    }


def metric_component_contract() -> dict[str, Any]:
    import numpy as np
    import pandas as pd

    metrics = importlib.import_module("environ.evaluation.metrics")
    weekly = np.array([0.01, -0.005, 0.02, -0.01] * 13)
    values = 100000.0 * np.cumprod(1.0 + weekly)
    frame = pd.DataFrame({"total_value": values, "weekly_return": weekly})
    first = metrics.compute_metrics(frame)
    second = metrics.compute_metrics(frame.copy())
    return {
        "passed": first == second and first["n_weeks"] == 52,
        "deterministic_result": first,
        "synthetic_input_only": True,
        "paper_result_credit": False,
    }


def source_claim_conflicts(repo: Path) -> list[dict[str, Any]]:
    runner = (repo / "scripts/run_experiment.py").read_text(encoding="utf-8")
    base = (repo / "environ/agents/base.py").read_text(encoding="utf-8")
    return [
        {
            "claim": "three backbone models execute by default",
            "status": "conflict",
            "evidence": "OPENAI_MODELS lists only gpt-4o and gpt-5; Claude is accepted only if manually supplied.",
            "validated": 'OPENAI_MODELS = ["gpt-4o", "gpt-5"]' in runner,
        },
        {
            "claim": "ReAct-style reasoning/action interleaving is compulsory in every configuration",
            "status": "not_implemented_as_claimed",
            "evidence": "Source has chain-of-thought reasoning tags and final JSON actions, but no ReAct observation/action loop.",
            "validated": "<reasoning>" in base and "observation" not in base.lower(),
        },
        {
            "claim": "all four single-agent capability variants are distinct",
            "status": "conflict",
            "evidence": "The single-agent wrapper maps both rag and skill to zero_shot.",
            "validated": "_llm_capability(capability)" in runner,
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    head = git(repo, "rev-parse", "HEAD").strip()
    if head != EXPECTED_HEAD:
        raise ValueError(f"cryptoMAS head changed: {head}")
    if git(repo, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise ValueError("cryptoMAS audit requires complete history")

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo))
    os.environ.setdefault("OPENAI_API_KEY", "audit-placeholder-no-call")
    os.chdir(tempfile.mkdtemp(prefix="maci-v3-native-cwd-"))

    payload = {
        "repository": "https://github.com/lyc0603/cryptoMAS",
        "head": head,
        "pyproject_sha256": sha256_file(repo / "pyproject.toml"),
        "compile": compile_sources(repo),
        "raw_runner_import": import_contract(repo),
        "dependency_and_setup_contract": dependency_contract(repo),
        "architecture_component_execution": architecture_contract(),
        "single_agent_capability_contract": single_agent_alias_contract(),
        "runner_dry_run_with_missing_data_overlay": runner_overlay_contract(),
        "metric_component_execution": metric_component_contract(),
        "paper_source_claim_conflicts": source_claim_conflicts(repo),
        "llm_calls_made": 0,
        "external_api_calls_made": 0,
        "full_paper_runner_executed": False,
        "paper_results_regenerated": 0,
        "component_execution_is_paper_result_replication": False,
    }
    encoded = json.dumps(payload, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
