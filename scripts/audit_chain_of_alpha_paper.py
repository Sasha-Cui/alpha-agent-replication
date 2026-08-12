#!/usr/bin/env python3
"""Build a fail-closed paper-level audit for Chain-of-Alpha.

The current arXiv record is withdrawn and has no downloadable PDF or source.
This audit therefore treats the byte-pinned ar5iv transformation and its five
assets as historical document evidence only.  It never promotes the recovered
paper, vector plots, demo prompts, synthetic formula execution, or later
unaffiliated adaptations into a native paper-result reproduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
WORK_ID = "CensusArxiv250806312"
SYSTEM_ID = "SYS-CHAIN-OF-ALPHA"
ARXIV_ID = "2508.06312"
TITLE = (
    "Chain-of-Alpha: Unleashing the Power of Large Language Models for Alpha "
    "Mining in Quantitative Trading"
)
HISTORICAL_AUTHORS = ["Lang Cao", "Zekun Xi", "Long Liao", "Ziwei Yang", "Zheng Cao"]

DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/chain_of_alpha_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/chain_of_alpha"

PINS = {
    "arxiv_abs_current.html": "96d7717cf1effac37ec81bccc530b14e331ad148aecbc468661e0834969fdee0",
    "arxiv_api.xml": "09633b76d0cbbaa5712790fbae92296ddf3f5247068e0c64e2263da2dac84287",
    "ar5iv.html": "aa7d79e1ab37a614ffd75d67b81cb514cf951ed0699004859cb1f160ef55776b",
    "arxiv_vanity.html": "aa7d79e1ab37a614ffd75d67b81cb514cf951ed0699004859cb1f160ef55776b",
    "assets/framework.png": "363ca01b26ce26dd5ce1f7052124a9b59777457957466b591e599381db001a4c",
    "assets/return.svg": "8659a3591baa411728500511c887008bb2ca00cafb955d988e67c440957fbc75",
    "assets/excess.svg": "1ca4752a39368c40426db3c765a3729017744ee0873f16b383915ab49e3b0485",
    "assets/prompt_gen.svg": "68ff8bf67897f8e380ad0f215c90ec770bda8dcba27860bf05bbb1bd1f5a0ef5",
    "assets/prompt_opt.svg": "197c7d8abeaa48491646dc1c9128dc22986e005399a3aa80eea0dc80e2b573ad",
    "db2f9e02c7cc85af058fea03c2adf4e7b8458928_index.html": "1c21a65382e5ee8641c4a9d20c82ae8586057c59e94b0620763b25fe25bb7895",
    "cbcde61e6ef9b9b33aa0bd781b6a176a22775383_index.html": "66ebe30d819ceaf39c428d25aae0e0720f14153eda0c979e0b8f2a6e2531efe1",
    "07afcaa24680109501937fe5e0e7efed7410fb36_source__bibs__coa.bib.txt": "83342cfa8644d35e13178e92043ec4e85db048dc86be3af926377b0fff1d1a2a",
    "author_repos.json": "46fb4ebf157052da681aaafb755da0f2ce2d613891a13f1e27752cf95d5b2b73",
    "github_repo_search_1.json": "b9e92063099e6b573c363df7dd084a07dbe959569600f9c6f5398a6cd0dc84f0",
    "github_repo_search_2.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github_repo_search_3.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github_repo_search_4.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "github_code_search_5.json": "3631096f6f4efd623ce2543bc4e040d7764b5458b961a8c186c16c1a926bc59d",
    "github_code_search_6.json": "f6775859a7dc730803204ea0f477ac3b4cfc8e1e5c68bf4cead7894b7dbe87d8",
    "github_code_search_7.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
}

CANDIDATES = [
    {
        "repository": "skipsuzuki/Chain-of-Alpha",
        "commit": "2ce41ca4b9a6293e9de270357e30abef903d100c",
        "archive": "candidates/skipsuzuki__Chain-of-Alpha__2ce41ca4b9a6293e9de270357e30abef903d100c.tar.gz",
        "sha256": "3c248317aa118a470097c09e55131876285159336c9585096e66ffd086cdfd70",
        "created": "2025-12-06T12:22:44Z",
        "files": 1,
        "python_files": 0,
        "compiled": 0,
        "classification": "post-paper empty name match",
        "mechanism": "one two-line README; no implementation",
    },
    {
        "repository": "Haoyu-tech/LLM---Factor-generation",
        "commit": "e34652414d9f4c15e4d75115a95ac65409fd73ca",
        "archive": "candidates/Haoyu-tech__LLM---Factor-generation__e34652414d9f4c15e4d75115a95ac65409fd73ca.tar.gz",
        "sha256": "7e860cac8f79dfe645a34085f87abda7cb46928321f6f48c2afab81b71e6ea91",
        "created": "2026-07-07T00:10:04Z",
        "files": 1290,
        "python_files": 34,
        "compiled": 34,
        "classification": "post-paper independent research project",
        "mechanism": "monthly US S&P 500 hypothesis generation and asset-pricing validation; cites Chain-of-Alpha as prior work",
    },
    {
        "repository": "lavender1203/worldquant-alpha-aiac",
        "commit": "8ffda431d08703b7f6ae13c8287806fd76eb63e0",
        "archive": "candidates/lavender1203__worldquant-alpha-aiac__8ffda431d08703b7f6ae13c8287806fd76eb63e0.tar.gz",
        "sha256": "12b69ecf168ac874cb7f708cf6305132671e777d73ccab21c0a26a6d2744acba",
        "created": "2026-01-22T05:32:43Z",
        "files": 217,
        "python_files": 150,
        "compiled": 150,
        "classification": "post-paper unaffiliated inspired adaptation",
        "mechanism": "WorldQuant BRAIN/Alpha-GPT platform with a deterministic local-rewrite module explicitly inspired by the optimization chain",
    },
]

METRICS = ("IC", "RankIC", "ICIR", "RankICIR", "AR", "IR")
TABLE1 = [
    ("Alpha 101", (0.0345, 0.0617, 0.2170, 0.4239, 0.0568, 0.7311), (0.0615, 0.0832, 0.3845, 0.5391, 0.1006, 1.1219)),
    ("Alpha 158", (0.0477, 0.0686, 0.3202, 0.4685, 0.0989, 1.0424), (0.0591, 0.0800, 0.4420, 0.5817, 0.1205, 1.2307)),
    ("Alpha 360", (0.0457, 0.0524, 0.3345, 0.3975, 0.1092, 1.1017), (0.0551, 0.0649, 0.4384, 0.5175, 0.0965, 0.9801)),
    ("GP", (0.0351, 0.0659, 0.2185, 0.4308, 0.0792, 0.9535), (0.0602, 0.0823, 0.3741, 0.5281, 0.1116, 1.2457)),
    ("DSO", (0.0436, 0.0638, 0.3140, 0.4716, 0.0984, 1.2640), (0.0616, 0.0765, 0.4583, 0.5304, 0.1235, 1.3079)),
    ("AlphaGen", (0.0460, 0.0769, 0.2786, 0.4711, 0.1150, 1.2751), (0.0655, 0.0889, 0.4224, 0.5573, 0.1247, 1.2043)),
    ("AlphaForge", (0.0463, 0.0638, 0.3291, 0.4630, 0.0989, 1.1918), (0.0617, 0.0768, 0.4602, 0.5327, 0.1325, 1.2657)),
    ("LLM + CoT", (0.0404, 0.0711, 0.2558, 0.4870, 0.0759, 0.9659), (0.0620, 0.0847, 0.4464, 0.6152, 0.1181, 1.2625)),
    ("LLM + ToT", (0.0292, 0.0607, 0.2227, 0.4883, 0.0994, 1.2693), (0.0597, 0.0876, 0.4169, 0.6024, 0.1267, 1.3258)),
    ("LLM + MCTS", (0.0347, 0.0595, 0.3083, 0.5268, 0.0815, 1.0736), (0.0465, 0.0713, 0.4320, 0.5930, 0.1235, 1.3342)),
    ("Chain-of-Alpha", (0.0485, 0.0771, 0.3047, 0.5013, 0.1324, 1.4178), (0.0672, 0.0902, 0.4630, 0.6228, 0.1471, 1.4043)),
]
TABLE2 = [
    ("Chain-of-Alpha", (0.0672, 0.0902, 0.4630, 0.6228, 0.1471, 1.4043)),
    ("Factor Generation Chain", (0.0586, 0.0867, 0.4078, 0.6203, 0.1346, 1.3492)),
    ("Factor Optimization Chain", (0.0620, 0.0847, 0.4464, 0.6152, 0.1181, 1.2625)),
]
TABLE3 = [
    ("Best of Baselines", "", (0.0655, 0.0889, 0.4602, 0.6152, 0.1325, 1.3342)),
    ("Chain-of-Alpha", "GPT-4o", (0.0672, 0.0902, 0.4630, 0.6228, 0.1471, 1.4043)),
    ("Chain-of-Alpha", "DeepSeek-V3", (0.0671, 0.1011, 0.4492, 0.6063, 0.1517, 1.4020)),
    ("Chain-of-Alpha", "Qwen3-32B", (0.0653, 0.0939, 0.4597, 0.6342, 0.1365, 1.5804)),
]
FORMULAS = [
    {
        "name": "VWAP_Stability_Enhance",
        "expression": "Div(Sub($close, Mean($vwap, 2)), Std($amount, 5))",
        "description": "close minus 2-day mean VWAP, divided by 5-day amount standard deviation",
        "rankic": 0.0688,
        "rankir": 0.7051,
        "fields": 3,
        "dimensionally_unitless": False,
    },
    {
        "name": "Volume_Adjusted_Mean_Corr",
        "expression": "Corr(Rank($close, 5), Rank($amount, 5), 5)",
        "description": "rolling correlation of rolling close and amount ranks",
        "rankic": 0.0375,
        "rankir": 0.5084,
        "fields": 2,
        "dimensionally_unitless": True,
    },
    {
        "name": "VWAP_Flow_Variance_Optimization",
        "expression": "Div(Abs(Sub($close, $vwap)), Add(Sum(Var($amount, 2), 4), 1))",
        "description": "absolute close-VWAP deviation divided by rolling amount-variance sum plus one",
        "rankic": 0.0838,
        "rankir": 0.7590,
        "fields": 3,
        "dimensionally_unitless": False,
    },
]

DATA_FIELDS = [
    ("$open", "Open"), ("$high", "High"), ("$low", "Low"),
    ("$close", "Close"), ("$volume", "Volume"), ("$amount", "Amount"),
    ("$change", "Change"), ("$vwap", "VWAP"),
]
OPERATORS = {
    "Mathematical": ["Add", "Sub", "Mul", "Div", "Log", "Abs", "Power", "Sign"],
    "Time Series (rolling)": ["Mean", "Std", "Var", "Sum", "Max", "Min", "Med", "Mad", "Rank", "Quantile", "Count", "Ref", "Delta", "IdxMax", "IdxMin"],
    "Regression (rolling)": ["Resi", "Slope", "Rsquare"],
    "Statistical (rolling)": ["Skew", "Kurt", "Corr", "Cov"],
    "Conditional": ["If", "Gt", "Lt", "Ge", "Le", "Eq", "Ne"],
    "Logical": ["And", "Or", "Not"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty output: {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def validate_pins(scratch: Path) -> None:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != expected:
            raise ValueError(f"pin changed for {relative}: {observed}")
    for candidate in CANDIDATES:
        path = scratch / candidate["archive"]
        if not path.is_file() or sha256(path) != candidate["sha256"]:
            raise ValueError(f"candidate archive pin changed: {path}")


def archive_files(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(path, mode="r:gz") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe archive member: {member.name}")
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError(f"cannot read archive member: {member.name}")
            files["/".join(pure.parts[1:])] = handle.read()
    return files


def candidate_archive_checks(scratch: Path) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    for candidate in CANDIDATES:
        first = scratch / candidate["archive"]
        repeat = scratch / "candidate_repeat" / first.name
        if not repeat.is_file() or sha256(repeat) != candidate["sha256"]:
            raise ValueError(f"repeat candidate archive changed: {repeat}")
        files = archive_files(first)
        python_files = {name: value for name, value in files.items() if name.endswith(".py")}
        for name, value in python_files.items():
            compile(value, name, "exec")
        license_files = [
            name for name in files
            if PurePosixPath(name).name.lower().startswith(("license", "copying"))
        ]
        observed = {
            "files": len(files),
            "python_files": len(python_files),
            "compiled": len(python_files),
            "license_files": license_files,
            "repeated_archive_byte_identical": first.read_bytes() == repeat.read_bytes(),
        }
        for key in ("files", "python_files", "compiled"):
            if observed[key] != candidate[key]:
                raise ValueError(
                    f"candidate inventory changed for {candidate['repository']} {key}: "
                    f"{observed[key]}"
                )
        if license_files or not observed["repeated_archive_byte_identical"]:
            raise ValueError(f"candidate archive boundary changed: {candidate['repository']}")
        checks[candidate["repository"]] = observed
    return checks


def execute_adaptation_component(scratch: Path) -> dict[str, Any]:
    candidate = CANDIDATES[2]
    files = archive_files(scratch / candidate["archive"])
    with tempfile.TemporaryDirectory(prefix="chain_of_alpha_adaptation_") as temporary:
        root = Path(temporary)
        for name, value in files.items():
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(value)
        code = """
import json
from backend.optimization_chain import generate_local_rewrites
rows = generate_local_rewrites(
    'ts_mean(close, 22)',
    {'is': {'sharpe': 0.7, 'turnover': 0.5, 'fitness': 0.4}, 'checks': []},
    max_variants=5,
)
print(json.dumps(rows, sort_keys=True))
"""
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(root)},
        )
    rows = json.loads(completed.stdout)
    expected = [
        "ts_mean(close, 44)",
        "ts_mean(close, 66)",
        "ts_mean(close, 126)",
        "ts_mean(close, 252)",
        "winsorize(ts_mean(close, 22), std=2)",
    ]
    observed = [row["expression"] for row in rows]
    if observed != expected:
        raise ValueError(f"inspired adaptation output changed: {observed}")
    return {
        "repository": candidate["repository"],
        "commit": candidate["commit"],
        "executed_component": "backend.optimization_chain.generate_local_rewrites",
        "synthetic_input_expression": "ts_mean(close, 22)",
        "synthetic_variants_returned": len(rows),
        "first_variants": observed,
        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "classification": "unaffiliated post-paper deterministic inspired component",
        "paper_data_or_native_evaluator_used": False,
        "paper_result_credit": False,
    }


def result_ledger() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(table: str, method: str, backbone: str, universe: str, metric: str, value: float, native: bool, group: str = "") -> None:
        rows.append({
            "table": table,
            "method": method,
            "backbone": backbone,
            "universe": universe,
            "metric": metric,
            "printed_value": f"{value:.4f}",
            "chain_of_alpha_or_ablation_output": native,
            "duplicate_native_measurement_group": group,
            "native_pipeline_regenerated_value": "",
            "native_pipeline_executed": False,
            "paper_result_credit": False,
        })

    for method, csi500, csi1000 in TABLE1:
        for universe, values in (("CSI 500", csi500), ("CSI 1000", csi1000)):
            for metric, value in zip(METRICS, values):
                group = f"chain_csi1000_{metric}" if method == "Chain-of-Alpha" and universe == "CSI 1000" else ""
                add("Table 1", method, "", universe, metric, value, method == "Chain-of-Alpha", group)
    for method, values in TABLE2:
        for metric, value in zip(METRICS, values):
            group = f"chain_csi1000_{metric}" if method == "Chain-of-Alpha" else ""
            add("Table 2", method, "", "CSI 1000", metric, value, True, group)
    for method, backbone, values in TABLE3:
        for metric, value in zip(METRICS, values):
            group = f"chain_csi1000_{metric}" if backbone == "GPT-4o" else ""
            add("Table 3", method, backbone, "CSI 1000", metric, value, method == "Chain-of-Alpha", group)
    for factor in FORMULAS:
        for metric, value in (("RankIC", factor["rankic"]), ("RankIR", factor["rankir"])):
            add("Table 4", factor["name"], "", "CSI 1000", metric, value, True)
    if len(rows) != 180:
        raise AssertionError(len(rows))
    return rows


TOKEN = re.compile(r"\s*(?:(\$[A-Za-z_][A-Za-z0-9_]*)|([A-Za-z_][A-Za-z0-9_]*)|([0-9]+(?:\.[0-9]+)?)|(.))")


class ExpressionParser:
    def __init__(self, text: str):
        self.tokens: list[tuple[str, str]] = []
        for field, name, number, other in TOKEN.findall(text):
            if field:
                self.tokens.append(("field", field))
            elif name:
                self.tokens.append(("name", name))
            elif number:
                self.tokens.append(("number", number))
            elif other in "(),":
                self.tokens.append((other, other))
            else:
                raise ValueError(f"unsupported token: {other}")
        self.index = 0

    def take(self, kind: str) -> str:
        if self.index >= len(self.tokens) or self.tokens[self.index][0] != kind:
            raise ValueError(f"expected {kind} at token {self.index}: {self.tokens[self.index:self.index+1]}")
        value = self.tokens[self.index][1]
        self.index += 1
        return value

    def parse(self) -> Any:
        result = self.expression()
        if self.index != len(self.tokens):
            raise ValueError(f"trailing tokens: {self.tokens[self.index:]}")
        return result

    def expression(self) -> Any:
        kind, value = self.tokens[self.index]
        if kind == "field":
            self.index += 1
            return ("field", value)
        if kind == "number":
            self.index += 1
            return ("number", float(value))
        name = self.take("name")
        self.take("(")
        args = [self.expression()]
        while self.index < len(self.tokens) and self.tokens[self.index][0] == ",":
            self.index += 1
            args.append(self.expression())
        self.take(")")
        return ("call", name, args)


def rolling_unary(x: np.ndarray, window: int, function: str) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    for t in range(window - 1, len(x)):
        values = x[t - window + 1:t + 1]
        if function == "Mean":
            out[t] = np.mean(values, axis=0)
        elif function == "Std":
            out[t] = np.std(values, axis=0, ddof=0)
        elif function == "Var":
            out[t] = np.var(values, axis=0, ddof=0)
        elif function == "Sum":
            out[t] = np.sum(values, axis=0)
        elif function == "Rank":
            last = values[-1]
            out[t] = (np.sum(values < last, axis=0) + 0.5 * np.sum(values == last, axis=0)) / window
        else:
            raise ValueError(function)
    return out


def rolling_corr(x: np.ndarray, y: np.ndarray, window: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    for t in range(window - 1, len(x)):
        xv, yv = x[t - window + 1:t + 1], y[t - window + 1:t + 1]
        for asset in range(x.shape[1]):
            mask = np.isfinite(xv[:, asset]) & np.isfinite(yv[:, asset])
            if mask.sum() >= 2 and np.std(xv[mask, asset]) > 0 and np.std(yv[mask, asset]) > 0:
                out[t, asset] = np.corrcoef(xv[mask, asset], yv[mask, asset])[0, 1]
    return out


def evaluate(node: Any, fields: Mapping[str, np.ndarray]) -> np.ndarray | float:
    if node[0] == "field":
        return fields[node[1]]
    if node[0] == "number":
        return node[1]
    name, args = node[1], [evaluate(value, fields) for value in node[2]]
    if name == "Add":
        return np.asarray(args[0]) + np.asarray(args[1])
    if name == "Sub":
        return np.asarray(args[0]) - np.asarray(args[1])
    if name == "Abs":
        return np.abs(np.asarray(args[0]))
    if name == "Div":
        left, right = np.asarray(args[0], dtype=float), np.asarray(args[1], dtype=float)
        return np.divide(left, right, out=np.full(np.broadcast_shapes(left.shape, right.shape), np.nan), where=np.abs(right) > 1e-12)
    if name in {"Mean", "Std", "Var", "Sum", "Rank"}:
        return rolling_unary(np.asarray(args[0], dtype=float), int(args[1]), name)
    if name == "Corr":
        return rolling_corr(np.asarray(args[0]), np.asarray(args[1]), int(args[2]))
    raise ValueError(f"unsupported evaluated operator: {name}")


def formula_execution() -> list[dict[str, Any]]:
    t = np.arange(32, dtype=float)[:, None]
    a = np.arange(5, dtype=float)[None, :]
    fields = {
        "$close": 90.0 + 0.08 * t + 0.7 * a + 2.0 * np.sin((t + a) / 2.7),
        "$vwap": 89.8 + 0.07 * t + 0.68 * a + 1.7 * np.cos((t + 2 * a) / 3.4),
        "$amount": 1_000_000.0 + 1_000 * t + 23_000 * a + 55_000 * np.sin((t + a) / 3.1),
    }
    output = []
    for factor in FORMULAS:
        tree = ExpressionParser(factor["expression"]).parse()
        values = np.asarray(evaluate(tree, fields), dtype="<f8")
        finite = values[np.isfinite(values)]
        if values.shape != (32, 5) or finite.size == 0:
            raise AssertionError(f"conditional formula execution failed: {factor['name']}")
        canonical = np.nan_to_num(values, nan=9.87654321e99).tobytes()
        output.append({
            "factor": factor["name"],
            "expression": factor["expression"],
            "parser_status": "parsed",
            "synthetic_output_shape": list(values.shape),
            "finite_values": int(finite.size),
            "finite_min": float(finite.min()),
            "finite_max": float(finite.max()),
            "synthetic_output_sha256": hashlib.sha256(canonical).hexdigest(),
            "semantics": "audit-declared conventional rolling semantics; population variance/std; average-tie percentile rank; NaN warm-up",
            "native_evaluator_used": False,
            "paper_result_credit": False,
        })
    return output


def prompt_inventory() -> list[dict[str, Any]]:
    return [
        {
            "prompt": "seed factor generation",
            "asset": "prompt_gen.svg",
            "runtime_slots": 4,
            "slots": "available_data_fields; available_operators; effective_factors; non_effective_factors",
            "response_fields": "factor_name; factor_expression; description",
            "publication_status": "paper explicitly calls it a demo version",
            "actual_filled_prompt_released": False,
            "actual_request_response_released": False,
            "native_prompt_credit": False,
        },
        {
            "prompt": "factor optimization",
            "asset": "prompt_opt.svg",
            "runtime_slots": 10,
            "slots": "available_data_fields; available_operators; factor_name; factor_expression; description; rankic; rankicir; turnover; diversity; optimization_history",
            "response_fields": "factor_name; factor_expression; description; reason",
            "publication_status": "paper explicitly calls it a demo version",
            "actual_filled_prompt_released": False,
            "actual_request_response_released": False,
            "native_prompt_credit": False,
        },
    ]


def consistency_audit() -> list[dict[str, Any]]:
    t1_best = []
    for universe_index in (1, 2):
        columns = list(zip(*(row[universe_index] for row in TABLE1)))
        own = TABLE1[-1][universe_index]
        t1_best.extend(math.isclose(value, max(column)) for value, column in zip(own, columns))
    baseline = TABLE3[0][2]
    wins = {backbone: sum(value > base for value, base in zip(values, baseline)) for _, backbone, values in TABLE3[1:]}
    rows = [
        ("table1_best_10_of_12", "best in 10 of 12 metrics", f"{sum(t1_best)}/12 strict column maxima", "passes_displayed_arithmetic"),
        ("ablation_optimization_ar", "optimization-only AR is 0.1211 in prose", "Table 2 prints 0.1181", "hard_prose_table_conflict"),
        ("ablation_generation_ir", "generation-only IR is 1.4492 in prose", "Table 2 prints 1.3492", "hard_prose_table_conflict"),
        ("all_backbones_all_metrics", "all three backbones outperform the best baseline across all metrics", f"wins out of six: {wins}", "claim_contradicted_by_displayed_table"),
        ("appendix_figure_numbers", "Appendix E says Figures 4 and 5 show the two prompts", "the assets are numbered Figures 3 and 4", "hard_numbering_conflict"),
        ("production_prompt_boundary", "demo prompts guide generation", "paper says more carefully crafted prompts are needed; filled production prompts are absent", "demo_not_runtime_prompt"),
        ("diversity_definition", "method defines diversity as minimum 1-Corr to effective factors", "Appendix B defines 1 minus the average top-k absolute Spearman correlations", "hard_metric_definition_conflict"),
        ("prompt_diversity_threshold", "Appendix requires Diversity >= 0.2 and higher is preferred", "optimization demo prompt says Diversity < 0.8", "direction_or_variable_semantics_conflict"),
        ("rankir_naming", "Table 4 and demo prompt report RankIR", "method and evaluation sections define RankICIR", "metric_alias_undefined"),
        ("volume_corr_description", "Table 4 description says ranked returns of closing price", "formula applies Rank directly to $close", "description_expression_conflict"),
        ("operator_appendix_intro", "Appendix D introduces a complete list of data fields", "Table 6 is the operator list", "copy_editing_conflict"),
        ("formula_1_units", "seed prompt requires a unitless factor", "price deviation is divided by amount standard deviation", "published_formula_not_unitless"),
        ("formula_3_units", "seed prompt requires a unitless factor", "price is divided by amount variance and adds dimensionless 1 to a dimensioned quantity", "published_formula_not_unitless"),
        ("excess_return_equations", "all results are benchmarked relative to the market index", "AR/IR equations use portfolio returns without defining index subtraction", "metric_execution_underspecified"),
        ("drop_n_rounding", "daily drop n is k/w with k equal to 10% of the universe", "integer rounding and constituent-count changes are not defined", "portfolio_execution_underspecified"),
    ]
    return [{"claim_id": a, "paper_statement": b, "audit_finding": c, "status": d, "paper_result_credit": False} for a, b, c, d in rows]


def method_audit() -> list[dict[str, Any]]:
    rows = [
        ("paper_record", "withdrawn_no_pdf_or_source", "current arXiv record says submitter lacked rights to agree to license"),
        ("historical_document", "recoverable_transformation_only", "ar5iv HTML and five assets are byte-pinned; no official version/source identity is exposed"),
        ("authors", "historically_corrobated_current_record_differs", "historic paper/author page list five authors; current withdrawn API lists Lang Cao only"),
        ("market", "specified", "China A-share CSI 500 and CSI 1000"),
        ("data_dates", "specified", "2010-01-01 through 2025-06-30; train 2010-2019, validation 2020-2021, test 2022-2025-06-30"),
        ("data_vendor_snapshot", "missing", "no frozen OHLCV/amount/index data or vendor is released"),
        ("point_in_time_membership", "missing", "index constituent history and delisting/suspension/ST rules are absent"),
        ("price_adjustments", "missing", "corporate-action adjustment and $change/$vwap construction rules are absent"),
        ("prediction_horizon", "specified", "10 trading days"),
        ("search_budget", "specified", "up to 1,000 candidates per method; top 100 by RankIC"),
        ("actual_factor_pool", "missing", "candidate/deprecated pools, 1,000 attempts, and 100 selected factors are absent"),
        ("default_llm", "specified_partial", "Azure OpenAI gpt-4o-2024-11-20, temperature 1.0; other parameters default"),
        ("robustness_llms", "underspecified", "DeepSeek-V3 and Qwen3-32B named without immutable checkpoint/API request details"),
        ("prompts", "demo_only", "two unfilled demo templates; actual carefully crafted runtime prompts and values absent"),
        ("llm_requests_responses", "missing", "no immutable calls, outputs, seeds, retries, or parsing failures"),
        ("expression_parser", "missing", "no native parser/validator or exception policy"),
        ("operator_semantics", "underspecified", "NaNs, min periods, ties, ddof, safe division, regression x-axis, and conditional behavior omitted"),
        ("factor_thresholds", "specified_with_conflict", "RankIC 0.015, RankICIR 0.2, turnover 1.5, diversity 0.2; prompt/metric definitions conflict"),
        ("optimization_depth", "example_not_run_setting", "m <= 5 is given as an example, not a frozen per-run trace"),
        ("parallel_execution", "architecture_only", "independent optimization chains claimed; scheduler/concurrency/logs absent"),
        ("integration_model", "specified_partial", "LightGBM MSE, 24 leaves, depth 8, 2,000 estimators, lr .005, L1/L2 .1, early stop 200"),
        ("integration_randomness", "missing", "LightGBM version, seed, feature ordering, missing-value and deterministic settings absent"),
        ("portfolio", "specified_partial", "daily equal-weight top 10%, drop n=k/10, close execution"),
        ("costs", "specified", "open 0.03%, close 0.1%"),
        ("portfolio_edge_cases", "missing", "integer rounding, limits, suspensions, cash, fills, ties, and same-close signal timing absent"),
        ("metrics", "equations_partial", "IC/RankIC/ratios/AR/IR/turnover/diversity equations given, but implementation conventions conflict or are absent"),
        ("baselines", "names_only", "baseline forks, versions, configs, seeds, and candidate outputs absent"),
        ("environment", "missing", "no dependency lock, Qlib version, executable code, or hardware/runtime record"),
        ("result_arrays", "missing", "no predictions, factors, portfolios, returns, metric arrays, or table exports"),
        ("uncertainty", "missing", "no repeated runs, intervals, significance, multiple-testing correction, or seed sensitivity"),
    ]
    return [{"dimension": a, "status": b, "evidence": c, "native_execution_credit": False} for a, b, c in rows]


def figure_inventory() -> list[dict[str, Any]]:
    rows = [
        ("Figure 1", "framework.png", 1, 0, "architecture diagram", False),
        ("Figure 2", "return.svg; excess.svg", 2, 9, "cumulative absolute/excess return curves", True),
        ("Figure 3", "prompt_gen.svg", 1, 0, "seed-factor demo prompt", True),
        ("Figure 4", "prompt_opt.svg", 1, 0, "optimization demo prompt", True),
    ]
    return [{
        "figure": a, "assets": b, "panels": c, "empirical_curve_series": d,
        "kind": e, "vector_or_exact_image_text_recovered": f,
        "underlying_dated_result_array_released": False,
        "native_pipeline_regenerated": False, "paper_result_credit": False,
        "visual_qa": "pass: legible, no clipped/overlapping/invisible content in full-resolution render",
    } for a, b, c, d, e, f in rows]


def adaptation_audit(scratch: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checks = candidate_archive_checks(scratch)
    rows = []
    for item in CANDIDATES:
        observed = checks[item["repository"]]
        rows.append({
            "repository": item["repository"], "commit": item["commit"],
            "created": item["created"], "archive_sha256": item["sha256"],
            "repeated_archive_byte_identical": observed["repeated_archive_byte_identical"],
            "tracked_files": observed["files"],
            "python_files": observed["python_files"],
            "python_files_compiled": observed["compiled"],
            "repository_license_file": "absent", "author_attribution_recovered": False,
            "classification": item["classification"], "mechanism_boundary": item["mechanism"],
            "native_chain_of_alpha_credit": False, "paper_result_credit": False,
        })
    execution = execute_adaptation_component(scratch)
    return rows, execution


def source_provenance(scratch: Path) -> dict[str, Any]:
    historical = (scratch / "ar5iv.html").read_text(encoding="utf-8", errors="replace")
    return {
        "current_arxiv_record": "https://arxiv.org/abs/2508.06312",
        "current_status": "withdrawn; no PDF; no license",
        "admin_comment": "version removed because submitter did not have rights to agree to the license at submission",
        "submissions": ["v1 2025-08-08 353 KB withdrawn", "v2 2025-08-28 353 KB withdrawn"],
        "official_pdf_endpoint_status": {"v1": 404, "v2": 404},
        "official_source_endpoint_status": {"v1": 404, "v2": 404},
        "historical_transformation_url": "https://ar5iv.labs.arxiv.org/html/2508.06312",
        "historical_transformation_sha256": PINS["ar5iv.html"],
        "independent_frontend_same_bytes": True,
        "historical_authors": HISTORICAL_AUTHORS,
        "numbered_equations": 21,
        "numbered_tables": 6,
        "numbered_figures": 4,
        "data_fields": 8,
        "operators": 40,
        "historical_html_math_elements": len(re.findall(r"<math\b", historical, flags=re.I)),
        "document_reconstruction_credit": False,
        "reason": "a transformed historical copy is not an official licensed PDF/source bundle and cannot establish experiment lineage",
        "author_site_history": {
            "added_commit": "db2f9e02c7cc85af058fea03c2adf4e7b8458928",
            "added_time": "2025-08-23T23:28:51Z",
            "removed_commit": "cbcde61e6ef9b9b33aa0bd781b6a176a22775383",
            "removed_time": "2025-12-21T17:21:46Z",
            "links_when_present": "paper and bibtex only; no code",
        },
    }


def discovery_evidence() -> list[dict[str, Any]]:
    rows = [
        ("lead_author_public_repositories", "18 repositories inventoried", "no Chain-of-Alpha implementation"),
        ("author_site_historical_entry", "five authors, Under Review, paper+bibtex links", "no code link; entry later commented out"),
        ("github_repository_name_description_readme", "24 results", "all candidate names inspected; no attributable release"),
        ("github_exact_arxiv_id_repository", "0 results", "no repository match"),
        ("github_exact_title_repository", "0 results", "no repository match"),
        ("github_author_title_repository", "0 results", "no repository match"),
        ("github_arxiv_id_code", "69 results", "citations/notes/secondary projects; no attributable experiment"),
        ("github_title_code", "105 results first 100 returned", "notes/adaptations/citations; no author-linked release"),
        ("github_exact_published_factor_name", "0 results", "no implementation match"),
        ("official_pdf_source_endpoints", "v1/v2 PDF and source all HTTP 404", "withdrawal prevents primary bundle recovery"),
    ]
    return [{
        "search": a, "coverage": b, "finding": c,
        "attributable_system_recovered": False,
        "negative_search_limit": "bounded public search; not proof that private, deleted, inaccessible, or unindexed artifacts never existed",
    } for a, b, c in rows]


def build(scratch: Path, output: Path) -> dict[str, Any]:
    validate_pins(scratch)
    output.mkdir(parents=True, exist_ok=True)
    results = result_ledger()
    formulas = formula_execution()
    adaptations, adaptation_execution = adaptation_audit(scratch)

    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "data_field_inventory.csv", [
        {"field": symbol, "name": name, "exact_paper_data_released": False, "paper_result_credit": False}
        for symbol, name in DATA_FIELDS
    ])
    write_csv(output / "operator_inventory.csv", [
        {"category": category, "operator": operator, "native_implementation_released": False, "paper_result_credit": False}
        for category, values in OPERATORS.items() for operator in values
    ])
    write_csv(output / "published_factor_inventory.csv", [
        {
            **factor,
            "exact_expression_released": True,
            "native_data_or_evaluator_released": False,
            "conditional_synthetic_execution": True,
            "paper_result_credit": False,
        }
        for factor in FORMULAS
    ])
    write_json(output / "conditional_formula_execution.json", formulas)
    write_csv(output / "prompt_inventory.csv", prompt_inventory())
    write_csv(output / "figure_inventory.csv", figure_inventory())
    write_csv(output / "method_specification_audit.csv", method_audit())
    write_csv(output / "internal_consistency_audit.csv", consistency_audit())
    write_csv(output / "candidate_adaptation_audit.csv", adaptations)
    write_json(output / "adaptation_component_execution.json", adaptation_execution)
    write_json(output / "source_provenance.json", source_provenance(scratch))
    write_csv(output / "discovery_evidence.csv", discovery_evidence())

    searches = []
    for relative, expected in PINS.items():
        path = scratch / relative
        searches.append({"artifact": relative, "sha256": expected, "bytes": path.stat().st_size, "committed_copy": False})
    write_csv(output / "pinned_input_inventory.csv", searches)

    native = [row for row in results if row["chain_of_alpha_or_ablation_output"]]
    duplicate_groups = Counter(row["duplicate_native_measurement_group"] for row in native if row["duplicate_native_measurement_group"])
    manifest: dict[str, Any] = {
        "audit": "Chain-of-Alpha withdrawn-paper primary-record and historical-document audit",
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "title": TITLE,
        "overall_status": "not_reproduced_withdrawn_primary_record_no_attributable_system_or_native_experiment_lineage",
        "current_primary_record_withdrawn": True,
        "current_primary_pdf_available": False,
        "current_primary_source_available": False,
        "historical_document_transformation_recovered": True,
        "full_end_to_end_pipeline_reproduced": False,
        "published_numeric_result_cells": len(results),
        "chain_or_ablation_numeric_result_cells": len(native),
        "unique_chain_or_ablation_measurements_after_repeated_full_row": len(native) - sum(value - 1 for value in duplicate_groups.values()),
        "published_result_cells_faithfully_regenerated": 0,
        "chain_result_cells_faithfully_regenerated": 0,
        "published_factor_expressions": len(FORMULAS),
        "published_factor_expressions_conditionally_executed_on_synthetic_arrays": len(formulas),
        "native_factor_evaluator_executed": False,
        "demo_prompt_templates": 2,
        "actual_filled_prompts_recovered": 0,
        "actual_llm_requests_responses_recovered": 0,
        "attributable_system_source_files_recovered": 0,
        "candidate_adaptations_audited": len(adaptations),
        "unaffiliated_inspired_components_executed": 1,
        "native_market_rows_predictions_factors_portfolios_or_returns_recovered": 0,
        "material_internal_consistency_findings": len(consistency_audit()),
        "visual_qa_passed": True,
        "interpretation": (
            "All 180 displayed Table 1-4 numeric result cells, 40 operators, eight fields, three formulas, "
            "two demo prompts, four numbered figures, method settings, current withdrawn record, historical "
            "author provenance, bounded public searches, and three unaffiliated candidates are audited. The "
            "three printed formulas parse and run only under declared conventional synthetic semantics. No "
            "attributable system, frozen A-share inputs, exact runtime prompts/calls, factor pools, evaluator, "
            "predictions, portfolios, returns, or result arrays are public in the pinned evidence; therefore "
            "zero paper result cells are faithfully regenerated."
        ),
    }

    readme = """# Chain-of-Alpha paper-level replication audit

Overall verdict: **not reproduced**. The current arXiv record is withdrawn, has
no PDF/source, and states that the submitter lacked the rights to agree to the
license. A historical ar5iv transformation preserves a highly auditable paper
document, but it is not an official licensed source release and it contains no
experiment implementation or raw result lineage.

## Honest denominator and positive evidence

- All **180** displayed numeric result cells in Tables 1-4 are transcribed. **54**
  are full-system, ablation, backbone, or generated-factor outputs; **42** are
  unique after the full CSI-1000 row is repeated in three tables. **Zero of 180**
  are regenerated by the native pipeline.
- All three published formula expressions parse and execute deterministically on
  synthetic 32x5 arrays under audit-declared rolling semantics. This is useful
  formula-component evidence, not evidence for their 0.0688/0.0375/0.0838 RankIC
  values or for Chain-of-Alpha.
- All 40 listed operators, eight fields, 21 numbered equations, six tables, four
  figures, two return panels (nine plotted series), and both demo prompt images
  are inventoried. Full-resolution visual inspection found them legible and
  unclipped. Vector plot geometry is author-rendered output, not the dated return
  arrays that generated it.
- Table 1's “best in 10 of 12” claim is arithmetically correct.

## Provenance and public-code boundary

The first author's site added a five-author Under Review entry in August 2025
with paper and BibTeX links only—no code—and commented it out in December 2025.
The current withdrawn API lists only Lang Cao. Eighteen public author repositories,
exact title/arXiv/factor searches, and broader GitHub searches recover no
attributable Chain-of-Alpha implementation. This is a bounded public search, not
proof that private, deleted, inaccessible, or unindexed artifacts never existed.

Three post-paper candidates were pinned twice and inspected. The exact-name repo
contains only a two-line README. `Haoyu-tech/LLM---Factor-generation` is a distinct
US-monthly asset-pricing project. `lavender1203/worldquant-alpha-aiac` is a distinct
WorldQuant/Alpha-GPT platform; all 150 Python files compile and one deterministic
local-rewrite function inspired by Chain-of-Alpha runs on a synthetic expression.
It is unaffiliated, changes the universe, data, grammar, metrics, models, and
pipeline, and therefore receives zero native or paper-result credit. None of the
three archives contains a license file.

## Direct paper conflicts

- Ablation prose prints optimization-only AR 0.1211 versus Table 2's 0.1181, and
  generation-only IR 1.4492 versus 1.3492.
- The claim that every backbone beats the best baseline on all six metrics is
  false: GPT-4o wins 6/6, but DeepSeek-V3 and Qwen3-32B each win only 4/6.
- The paper says its published prompts are demo versions and that more carefully
  crafted prompts are needed. Filled production prompts and all actual requests,
  responses, retries, seeds, and parse failures are absent.
- Diversity is defined once as minimum `1-Corr` and later as one minus an average
  of top-k absolute Spearman correlations. The optimization demo prompt then uses
  `Diversity < 0.8`, despite the paper's `Diversity >= 0.2` and higher-is-better
  definition.
- Two of the three showcased factors violate the seed prompt's unitless-expression
  requirement. The correlation factor's prose says ranked close *returns*, while
  its expression ranks close prices.
- Appendix E refers to Figures 4 and 5 although the prompts are Figures 3 and 4;
  Appendix D introduces “data fields” although it lists operators.

## Installing packages does not close the gap

The missing objects are scientific inputs and lineage, not Python dependencies:
point-in-time CSI membership and frozen OHLCV/amount data, adjustment and market
microstructure rules, exact runtime prompts/model calls, 1,000-candidate search
traces, accepted/deprecated pools, native parser/operator semantics, selected 100
factors, baseline forks/configs, LightGBM state, predictions, top-k/drop-n holdings,
orders/fills, daily returns, seeds, and raw metric/table arrays. Without those,
recreating a plausible dual-chain system would be a new implementation rather
than a faithful replication.

Regenerate this audit with `scripts/audit_chain_of_alpha_paper.py`. `--strict`
intentionally exits nonzero while end-to-end reproduction remains false.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path) for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch-root", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build(args.scratch_root.resolve(), args.output_dir.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return int(args.strict and not manifest["full_end_to_end_pipeline_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
