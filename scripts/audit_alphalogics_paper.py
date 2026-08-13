#!/usr/bin/env python3
"""Build a fail-closed paper/source/release audit for AlphaLogics."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/alphalogics_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/alphalogics"
WORK_ID = "CensusArxiv260320247"
SYSTEM_ID = "SYS-ALPHA-LOGICS"
ARXIV_ID = "2603.20247"

PINS = {
    "discovery/tracked.pdf": "d6ae7ed961bc6d358607497f6815dc2c8f4081afb1c04203b3693f63d2929c01",
    "discovery/arxiv-abs.html": "6dddebedff6a8fc4d99cca22830d4cde9210a457b9f52f6852e2ea494075ecc8",
    "discovery/arxiv-api.xml": "91212e7c41272a18bbbd101a4ad84feabc45500a050f966217220a9349bd2365",
    "discovery/arxiv-source.tar": "1439c0b14100dd1d5261cff44b348ca705d949a088051f3168b3a41573538f1a",
    "discovery/official.txt": "2df3d9b27d3052cf9fbb86350e8ffe545163f79210948c36b251f71b95a3809e",
    "discovery/rebuilt.txt": "6ba0d3c42454c1531512367c2df295a6c5f5dbb3396de9501846253f1c548967",
    "source-v1/arxiv.tex": "033535f009398e4998529b2ec37eeb14070aaae86cb193a7ed595e2abc2231f0",
    "source-v1/arxiv.pdf": "417cf96f3e68572f9df0a8ad4d29f9107a7146e60d1cc732904ee9d9f974f04a",
    "source-v1/figure1_alpha_evolution.png": "a2d5d57f1cd569daf312761d272973f9038e5d149d563d100b52625b875f2f54",
    "source-v1/figure2_framework.png": "675c9164b35083681edf13ecb5f958b7fd9aeff22f0fa73825fe0fd8d0fb8005",
    "source-v1/figure3_hypothesis_guided.png": "83945f4d5c5bc2e7c7447cc2b9aa7b91e6ef0cedadb47d509dbf3fd415d4cf1c",
    "source-v1/figure4_evolution.png": "842364ac4b41bedb3d89f2b784bb23584aab03c441f91884fef900fc7fd8d8a5",
    "source-v1/figure5_ablation.png": "83147241911967775a3682b1ac406d736fd3d95b4b7d6d0e5dca0f63a138d7c7",
    "render/contact-official-1.jpg": "98af34d49dca2c387bde8815c5b50db62d39c1aa56fe01743a86303da920521f",
    "render/contact-official-2.jpg": "08db4b92844b518041c265611e0e48a519d23c026046db2501f05d2b6c224890",
    "render/contact-official-3.jpg": "daa9a70f3b7aa7c346725dc588d56afd6f9c7766fb6b0beea4ec935ed4d7724d",
    "render/contact-rebuilt-1.jpg": "90116757b6f00e943f24e81924356e40c9b0cd24f4a2e535ee8a741f68523d6e",
    "render/contact-rebuilt-2.jpg": "399e89e6e319c5ccee206724acadb284abd87747f53a3920ec17b251ad8598bf",
    "render/contact-rebuilt-3.jpg": "daa9a70f3b7aa7c346725dc588d56afd6f9c7766fb6b0beea4ec935ed4d7724d",
    "discovery/github-repos-AlphaLogics_in_name_description_readme.json": "a4f38932ede9015ef36c39d65cefa25a196c9e70c2c5c29f0db5391a9b690254",
    "discovery/github-code-2603.20247.json": "fbd6d777690f7cf1528bb4805427b2be0d0f9b4974c5a1f28dc2575516f782aa",
    "discovery/github-author-repos-_Zhangyuhua_Weng_.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-author-repos-_Shengli_Zhang_AlphaLogics.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-author-repos-_Taotao_Wang_AlphaLogics.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-author-repos-_Yihan_Xia_AlphaLogics.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-user-deAiLab.json": "8b01720a2c5c81cd7b5d7b3c6322b23f0775cd3df0838e106893131a1cb1cad3",
    "discovery/github-user-deAiLab-repos.json": "2e5bb99550887f070c3de55d56b16550d9407045f7446d87d4fc598b777da961",
    "discovery/qlib-signal_strategy.py": "b1b4145e94065879768cfc9750c08a7c3af8880d3c338e0de675f5fb6b78d932",
    "discovery/sn0wfree__QuantNodes-alpha_logics-history.json": "0ec9b3ed01eccc9011dcff06fe4b6feb382e83edf9bc7828e58b5451b46bb12a",
    "candidates/sjkncs__alphalogics-reproduction/main.py": "152b9fa59f1e9d7d21f7a187da219e5c8fcd69306b755f8b932845afb641c30c",
    "candidates/sjkncs__alphalogics-reproduction/run.log": "5c5816a5ff9de48b170a2e6ab6d2a83b5cb20c6fe5196941c8948a5610e85d48",
    "candidates/kaihenglin__ai-factor-mining/compileall.log": "f3bc2e85d26cc88e12440651daccb864a88627a0a8ce3b59156cc9495065d0a1",
    "candidates/kaihenglin__ai-factor-mining/compileall.rc": "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
    "candidates/sn0wfree__QuantNodes/QuantNodes/research/quant_alpha/workflow/alpha_logics.py": "73f940c5459f3aa361d054867e44db198375f80f09020f2822e029a8e2247a99",
    "candidates/sn0wfree__QuantNodes/QuantNodes/research/quant_alpha/logic_mining/models.py": "4262189e5d531f02d9ef9b581f580d06a1d5e014c2da25e53f794c3808839e9a",
    "candidates/sn0wfree__QuantNodes/alphalogics-tests.log": "be253214e2f3bc8e9054bad0c61ecc1c1287a8da6dcc06a8cf3fbe54d8ef583f",
    "candidates/sn0wfree__QuantNodes/pip-check.log": "9261363b733079a641c2e4cc9bc46ffa1d8336945a87f807b6cf68847dbc9b09",
}

TABLE_COLUMNS = {
    "main_results": (
        "csi500_ic", "csi500_icir", "csi500_ar", "csi500_ir", "csi500_mdd",
        "sp500_ic", "sp500_icir", "sp500_ar", "sp500_ir", "sp500_mdd",
    ),
    "hypothesis_accuracy": ("mathematical_explanation", "financial_explanation"),
    "ablation": ("transient_ic", "persistent_ic", "transient_icir", "persistent_icir"),
}
TABLE_EXPECTED = {"main_results": 130, "hypothesis_accuracy": 8, "ablation": 20}

FIGURES = (
    ("figure_1_alpha_evolution", 1, 0, 0, "qualitative method comparison"),
    ("figure_2_framework", 1, 0, 0, "three-stage framework diagram"),
    ("figure_3_constraint_ablation", 6, 6, 60, "three models by two markets; two five-axis radar traces per panel"),
    ("figure_4_logic_evolution", 8, 8, 120, "two markets by four metrics; three models by five rounds per panel"),
    ("figure_5_library_size", 4, 4, 24, "four metrics by six library-size bars"),
)

CANDIDATE_COMMITS = {
    "sjkncs/alphalogics-reproduction": "a2a73583f37920b84aa9b7b5b223a25feb6da4e6",
    "kaihenglin/ai-factor-mining": "b4870e468d5e0602f536996be6b97602ecad86ef",
    "sn0wfree/QuantNodes": "6a168093528a0a578e99b03065dd5d5f1d2dcf4f",
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
        raise ValueError(f"refusing to write empty ledger: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def active_tex(source: str) -> str:
    return re.sub(r"\\iffalse.*?\\fi", "", source, flags=re.DOTALL)


def clean_label(value: str) -> str:
    value = re.sub(r"\\cite\{[^}]+\}", "", value)
    value = re.sub(r"\\(?:textbf|textit)\{([^}]*)\}", r"\1", value)
    value = value.replace(r"\&", "&")
    value = re.sub(r"[{}]", "", value)
    return " ".join(value.split())


def table_block(source: str, label: str) -> str:
    marker = rf"\label{{tab:{label}}}"
    index = source.index(marker)
    start = source.rfind(r"\begin{table", 0, index)
    end = source.index(r"\end{table", index)
    block = source[start:end]
    return block[block.index(r"\midrule") + len(r"\midrule"):block.index(r"\bottomrule")]


def parse_published_results(source: str) -> list[dict[str, Any]]:
    number = re.compile(r"(?<![A-Za-z0-9.])-?\d+(?:\.\d+)?%?")
    rows = []
    blocker = (
        "no attributable experiment package, frozen market panel, filled model calls, "
        "seeds, predictions, holdings, returns, or raw result arrays"
    )
    for table, columns in TABLE_COLUMNS.items():
        block = table_block(source, table)
        for line in block.splitlines():
            if "&" not in line or line.lstrip().startswith(r"\cmidrule"):
                continue
            cells = line.split("&")
            label = clean_label(cells[0])
            data = []
            for cell in cells[1:]:
                matches = number.findall(cell)
                if len(matches) != 1:
                    raise ValueError(f"unexpected numeric cell in {table}: {cell!r}")
                data.append(matches[0])
            if len(data) != len(columns):
                raise ValueError(f"column mismatch in {table}/{label}: {len(data)}")
            for column, value in zip(columns, data):
                rows.append({
                    "table": table,
                    "row": label,
                    "metric": column,
                    "printed_value": value,
                    "source_tex_recovered": True,
                    "author_native_experiment_executed": False,
                    "published_result_regenerated": False,
                    "paper_result_credit": False,
                    "blocking_reason": blocker,
                })
    counts = Counter(row["table"] for row in rows)
    if counts != Counter(TABLE_EXPECTED):
        raise ValueError(f"published result count changed: {counts}")
    anchors = {(row["table"], row["row"], row["metric"]): row["printed_value"] for row in rows}
    expected = {
        ("main_results", "AlphaLogics", "csi500_ir"): "1.5266",
        ("main_results", "AlphaLogics", "sp500_ir"): "1.2658",
        ("hypothesis_accuracy", "Alpha191", "mathematical_explanation"): "94.9",
        ("ablation", "5", "persistent_icir"): "0.2137",
    }
    for key, value in expected.items():
        if anchors.get(key) != value:
            raise ValueError(f"published anchor changed: {key}={anchors.get(key)}")
    return rows


def parse_prompts(source: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"\\textbf\{([^}]+Agent)\.\}\s*\\begin\{tcblisting\}.*?\n"
        r"(\{.*?\n\})\n\\end\{tcblisting\}",
        re.DOTALL,
    )
    rows = []
    for index, (agent, raw) in enumerate(pattern.findall(active_tex(source)), 1):
        template = json.loads(raw)
        if sorted(template) != ["input_schema", "instruction", "output_schema", "system"]:
            raise ValueError(f"prompt keys changed for {agent}")
        rows.append({
            "prompt_index": index,
            "agent": agent,
            "valid_json": True,
            "input_fields": ";".join(template["input_schema"]),
            "output_fields": ";".join(template["output_schema"]),
            "template_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "filled_runtime_request_recovered": False,
            "filled_runtime_response_recovered": False,
            "native_execution_credit": False,
        })
    if len(rows) != 8:
        raise ValueError(f"active prompt count changed: {len(rows)}")
    return rows


def parse_dsl(source: str) -> list[dict[str, Any]]:
    active = active_tex(source)
    block = active[
        active.index(r"\subsection{Factor Operations Library}"):
        active.index(r"\subsection{Logic Schema and Compilation Example}")
    ]
    section_pattern = re.compile(
        r"\\textbf\{([^}]+)\.\}\s*\\begin\{itemize\}(.*?)\\end\{itemize\}",
        re.DOTALL,
    )
    rows = []
    for family, section in section_pattern.findall(block):
        for signature, description in re.findall(
            r"\\item \\texttt\{([^}]+)\}:(.*?)(?=\n\s*\\item|\Z)", section, re.DOTALL
        ):
            rows.append({
                "operation_index": len(rows) + 1,
                "family": family,
                "printed_signature": signature,
                "printed_description": " ".join(description.split()),
                "source_specification_recovered": True,
                "author_native_implementation_recovered": False,
                "native_execution_credit": False,
            })
    if len(rows) != 59:
        raise ValueError(f"DSL operation count changed: {len(rows)}")
    return rows


def figure_rows() -> list[dict[str, Any]]:
    return [{
        "figure": figure,
        "display_panels": panels,
        "empirical_panels": empirical,
        "displayed_result_markers": markers,
        "description": description,
        "author_raster_recovered": True,
        "underlying_numeric_array_recovered": False,
        "author_native_figure_regenerated": False,
        "paper_result_credit": False,
    } for figure, panels, empirical, markers, description in FIGURES]


def figure_marker_rows() -> list[dict[str, Any]]:
    rows = []
    specifications = (
        ("figure_3_constraint_ablation", ("gpt35", "deepseek_v3", "gemini_2_5_flash"),
         ("csi500", "sp500"), ("constrained", "unconstrained"),
         ("ic", "icir", "ar", "ir", "mdd")),
        ("figure_4_logic_evolution", ("csi500", "sp500"),
         ("ic", "icir", "ar", "ir"),
         ("gpt35", "deepseek_v3", "gemini_2_5_flash"), tuple(f"round_{x}" for x in range(1, 6))),
        ("figure_5_library_size", ("ic", "icir", "ar", "ir"),
         tuple(f"logic_count_{x}" for x in range(1, 7))),
    )
    for specification in specifications:
        figure, *dimensions = specification
        combinations = [[]]
        for values in dimensions:
            combinations = [prefix + [value] for prefix in combinations for value in values]
        for combination in combinations:
            rows.append({
                "figure": figure,
                "marker_index": sum(row["figure"] == figure for row in rows) + 1,
                "coordinates": ";".join(combination),
                "exact_numeric_value_printed": False,
                "underlying_numeric_array_recovered": False,
                "published_marker_regenerated": False,
                "paper_result_credit": False,
            })
    if len(rows) != 204:
        raise ValueError(f"figure marker count changed: {len(rows)}")
    return rows


def simulate_inner_loop(scores: Sequence[float], early_stop: int = 3) -> dict[str, Any]:
    best = None
    no_improvement = 0
    trace = []
    for iteration, score in enumerate(scores, 1):
        if no_improvement >= early_stop:
            break
        improved = best is None or score > best
        if improved:
            best = score
            no_improvement = 0
        else:
            no_improvement += 1
        trace.append({
            "iteration": iteration, "score": score, "improved": improved,
            "best": best, "no_improvement": no_improvement,
            "feedback_called": no_improvement < early_stop,
        })
    return {"best": best, "iterations": len(trace), "trace": trace}


def simulate_outer_loop(scores: Sequence[float]) -> dict[str, Any]:
    generated = ["logic_0"]
    evaluated = []
    best_logic = None
    best_score = None
    for attempt, score in enumerate(scores):
        current = generated[-1]
        evaluated.append(current)
        if best_score is None or score > best_score:
            best_logic, best_score = current, score
        generated.append(f"logic_{attempt + 1}")
    return {
        "attempts": len(scores), "generated": generated, "evaluated": evaluated,
        "best_logic": best_logic, "best_score": best_score,
        "unevaluated_generated_logics": generated[len(evaluated):],
    }


def algorithm_audit(source: str) -> dict[str, Any]:
    active = active_tex(source)
    algorithms = re.findall(r"\\label\{alg:([^}]+)\}", active)
    if algorithms != ["inner-loop", "outer-loop"]:
        raise ValueError(f"algorithm labels changed: {algorithms}")
    inner = simulate_inner_loop([1.0, 0.8, 1.2, 1.1, 1.0, 0.9, 2.0], 3)
    if inner["best"] != 1.2 or inner["iterations"] != 6:
        raise ValueError("paper-derived inner-loop state machine changed")
    outer = simulate_outer_loop([0.1, 0.4, 0.3, 0.2, 0.5])
    if len(outer["generated"]) != 6 or len(outer["evaluated"]) != 5:
        raise ValueError("paper-derived outer-loop call count changed")
    return {
        "source_algorithms": algorithms,
        "paper_derived_not_author_native": True,
        "inner_loop_scripted_check": inner,
        "outer_loop_scripted_check": outer,
        "control_flow_findings": [
            "inner-loop improvement resets the no-improvement counter to zero",
            "the stopping iteration does not call factor feedback",
            "Algorithm 2 generates T+1 logics for T evaluated attempts",
            "the final generated logic is never evaluated by the printed pseudocode",
        ],
        "published_result_credit": False,
    }


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official_document", "complete", "v1 PDF, TeX source, bibliography, style files, and all five source rasters recovered"),
        ("source_rebuild", "complete", "unmodified TeX source rebuilt to a readable 19-page PDF; all 38 official/rebuilt pages visually inspected"),
        ("agent_prompts", "template_complete_runtime_missing", "eight active JSON templates parse exactly; no filled requests, responses, model parameters, or call traces"),
        ("factor_dsl", "operation_inventory_complete_implementation_missing", "59 allowed operation signatures are printed; no author DSL parser/executor or exact alias policy released"),
        ("logic_schema", "example_only", "typed H_struct and one Gamma example are printed, not the full deterministic compilation mapping"),
        ("algorithms", "control_flow_complete_services_missing", "inner and outer pseudocode are executable as control flow, but agent and backtest services are unreleased"),
        ("data", "sources_and_splits_named_snapshot_missing", "Baostock CSI500 and Yahoo S&P500 OHLCV/splits are named without point-in-time universes, retrieval dates, adjustments, missing-data rules, or frozen files"),
        ("models", "families_named_configs_missing", "LightGBM and LLM names are given without versions for most models, hyperparameters, temperatures, seeds, exact requests, or responses"),
        ("objective", "underspecified", "J may be IR, IC, ICIR, AR, or MDD; the actual scalar definition and tie handling are not fixed"),
        ("budgets", "partially_specified", "20 trials, five rounds, and early stop 3 are stated; exact LLM-call and per-round candidate caps are not stated"),
        ("portfolio", "misdescribed_and_incomplete", "paper says top-outside/top 50/exclude bottom 5; Qlib defines topk as holdings and n_drop as positions replaced per trade date"),
        ("costs", "rates_specified_execution_missing", "market-specific buy/sell rates are stated without trade frequency, exchange settings, limit rules, slippage, price, benchmark, or exact Qlib config"),
        ("factor_reconstruction", "criterion_underspecified", "100 Gemini repeats and >90 percent ranking/trend agreement are stated without formula sample, data, metric implementation, prompts, or outputs"),
        ("uncertainty", "not_reported", "independent trials are claimed but seeds, per-trial results, dispersion, intervals, and significance tests are absent"),
        ("published_tables", "not_regenerated", "zero of 158 exact empirical table units regenerated by an attributable native pipeline"),
        ("published_figures", "not_regenerated", "zero of 204 empirical raster markers across 18 empirical panels regenerated from recovered arrays"),
        ("first_party_release", "not_found_in_bounded_search", "primary record/source list no code; exact paper/author searches and a likely coauthor account expose no AlphaLogics repository"),
        ("independent_reproductions", "components_only", "three post-paper unaffiliated candidates were inspected; none supplies native paper inputs or result lineage"),
    )
    return [{"dimension": key, "status": status, "detail": detail} for key, status, detail in specs]


def internal_rows() -> list[dict[str, str]]:
    specs = (
        ("math_consistency_prose", "literal_contradiction", "prose says math consistency is above 95 percent, while Alpha191 is printed as 94.9 percent"),
        ("mdd_sign", "definition_table_conflict", "appendix defines nonnegative maximum drawdown, but the main table reports negative MDD values"),
        ("portfolio_term", "qlib_semantics_conflict", "Qlib n_drop is positions replaced each trading date, not stocks excluded from the bottom of the universe"),
        ("outer_loop_final_generation", "unevaluated_candidate", "printed Algorithm 2 calls the generator after every attempt, including the last, producing T+1 logics but evaluating T"),
        ("dsl_aliases", "undefined_aliases", "family table names ts_corr/ts_cov/ts_decay/ts_wma, while the exclusive operation list instead exposes TS_COVARIANCE, DECAYLINEAR, and WMA and no TS_CORR"),
        ("objective_selection", "material_ambiguity", "paper names five possible validation metrics but never identifies the scalar J used for reported selection"),
        ("result_arrays", "raster_only", "Figures 3--5 ship as rasters; source archive contains no numeric plotting arrays or plotting scripts"),
        ("model_reproducibility", "unpinned_services", "GPT-3.5-turbo, DeepSeek variants, Gemini 2.5 Flash, GPT-5-mini, and O3-mini lack snapshots and inference settings"),
        ("trial_reproducibility", "missing_lineage", "20-trial averages are not accompanied by seeds, trial values, errors, or uncertainty"),
    )
    return [{"check": key, "status": status, "detail": detail} for key, status, detail in specs]


def git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()


def candidate_audit(scratch: Path) -> dict[str, Any]:
    roots = {
        "sjkncs/alphalogics-reproduction": scratch / "candidates/sjkncs__alphalogics-reproduction",
        "kaihenglin/ai-factor-mining": scratch / "candidates/kaihenglin__ai-factor-mining",
        "sn0wfree/QuantNodes": scratch / "candidates/sn0wfree__QuantNodes",
    }
    for name, path in roots.items():
        if git_head(path) != CANDIDATE_COMMITS[name]:
            raise ValueError(f"candidate head changed for {name}")
    sjkncs_source = (roots["sjkncs/alphalogics-reproduction"] / "main.py").read_text()
    ast.parse(sjkncs_source)
    sjkncs_log = (roots["sjkncs/alphalogics-reproduction"] / "run.log").read_text()
    if "组合因子IC: +0.0224" not in sjkncs_log or "接受因子数: 20" not in sjkncs_log:
        raise ValueError("sjkncs synthetic run output changed")
    kai_log = (roots["kaihenglin/ai-factor-mining"] / "compileall.log").read_text()
    if kai_log.count("SyntaxError:") != 2 or (
        roots["kaihenglin/ai-factor-mining"] / "compileall.rc"
    ).read_text().strip() != "1":
        raise ValueError("kaihenglin compile boundary changed")
    quant_log = (roots["sn0wfree/QuantNodes"] / "alphalogics-tests.log").read_text()
    pip_log = (roots["sn0wfree/QuantNodes"] / "pip-check.log").read_text()
    if "52 passed" not in quant_log or pip_log.strip() != "No broken requirements found.":
        raise ValueError("QuantNodes focused test boundary changed")
    quant_source = (
        roots["sn0wfree/QuantNodes"]
        / "QuantNodes/research/quant_alpha/workflow/alpha_logics.py"
    ).read_text()
    for marker in (
        'max_outer_rounds: int = 4',
        'initial_logic_sources: Tuple[str, ...] = ("alpha101", "alpha158")',
        'best_ic=float(best_ir),  #',
    ):
        if marker not in quant_source:
            raise ValueError(f"QuantNodes mismatch marker changed: {marker}")
    history = json.loads(
        (scratch / "discovery/sn0wfree__QuantNodes-alpha_logics-history.json").read_text()
    )
    if len(history) != 1 or history[0]["sha"] != "2425999b56f6dc147507ed5def900e12ab157755":
        raise ValueError("QuantNodes AlphaLogics file history changed")
    return {
        "native_paper_credit": False,
        "paper_author_identity_matches": 0,
        "candidates": [
            {
                "repository": "sjkncs/alphalogics-reproduction",
                "commit": CANDIDATE_COMMITS["sjkncs/alphalogics-reproduction"],
                "created": "2026-06-21",
                "execution": "completed deterministic synthetic demonstration; 20 accepted factors and composite Pearson IC 0.0224",
                "paper_mismatch": "invented three-role Gaussian-return demo; no eight-agent pipeline, DSL compiler, Qlib/LightGBM, markets, costs, portfolio, or paper result units",
                "native_paper_credit": False,
            },
            {
                "repository": "kaihenglin/ai-factor-mining",
                "commit": CANDIDATE_COMMITS["kaihenglin/ai-factor-mining"],
                "created": "2026-06-10",
                "execution": "compileall failed with two syntax errors",
                "paper_mismatch": "crypto/live-trading adaptation; no paper data, model calls, trials, predictions, or result lineage",
                "native_paper_credit": False,
            },
            {
                "repository": "sn0wfree/QuantNodes",
                "commit": CANDIDATE_COMMITS["sn0wfree/QuantNodes"],
                "alpha_logics_first_commit": history[0]["sha"],
                "alpha_logics_first_commit_date": history[0]["commit"]["author"]["date"],
                "execution": "clean isolated Python 3.12 environment; pip check clean; 52 focused tests passed",
                "paper_mismatch": "IR is copied into best_ic, default outer rounds are four, initial libraries omit Alpha191/Alpha360, and no paper experiment/result lineage exists",
                "native_paper_credit": False,
            },
        ],
        "bounded_negative_inference": (
            "No attributable public implementation was found in the primary record, TeX source, "
            "exact arXiv/title searches, four author-name repository searches, or the seven public "
            "repositories of a likely Shenzhen University coauthor account. This does not exclude "
            "private, deleted, newly released, differently named, or unindexed artifacts."
        ),
    }


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    official = scratch / "discovery/tracked.pdf"
    rebuilt = scratch / "source-v1/arxiv.pdf"
    if len(PdfReader(official).pages) != 19 or len(PdfReader(rebuilt).pages) != 19:
        raise ValueError("official/rebuilt page count changed")
    source = (scratch / "source-v1/arxiv.tex").read_text()
    if source.count(r"\begin{figure") != 5 or source.count(r"\begin{algorithm}") != 2:
        raise ValueError("source figure/algorithm structure changed")
    official_tokens = Counter((scratch / "discovery/official.txt").read_text().split())
    rebuilt_tokens = Counter((scratch / "discovery/rebuilt.txt").read_text().split())
    intersection = sum((official_tokens & rebuilt_tokens).values())
    union = sum((official_tokens | rebuilt_tokens).values())
    comparison = {
        "official_tokens": sum(official_tokens.values()),
        "rebuilt_tokens": sum(rebuilt_tokens.values()),
        "multiset_intersection": intersection,
        "multiset_union": union,
        "multiset_jaccard": intersection / union,
    }
    if comparison["multiset_jaccard"] < 0.999:
        raise ValueError(f"source rebuild text diverged: {comparison}")
    return {"source": source, "text_comparison": comparison}


def readme() -> str:
    return """# AlphaLogics paper/source and public-release audit

This is a fail-closed audit of arXiv:2603.20247 v1, not a claim that the paper's
experiments have been reproduced. The official 19-page PDF, complete TeX source,
bibliography/style files, and all five source raster figures are pinned. The TeX
source rebuilds unmodified to 19 readable pages. All 19 official and all 19
rebuilt pages were visually inspected; no research page was unreadable, clipped,
overlapping, blank, or missing.

The source provides unusually useful specification evidence: both algorithms,
eight active JSON agent templates, 59 explicit DSL operation signatures, the
data-source/split narrative, four base-factor descriptions, costs, early stop,
and printed results. The eight templates are valid JSON and the printed loop
control passes deterministic scripted checks. These are paper-derived
specification checks, not execution of an author implementation.

The empirical gap remains complete. The audit enumerates 158 exact table result
units and 204 displayed raster markers across 18 empirical panels. No
attributable author code, frozen CSI500/S&P500 panel, point-in-time universe,
filled model calls, model snapshots, inference settings, seeds, exact budgets,
LightGBM/Qlib configuration, predictions, holdings, returns, trial arrays, or
plot arrays was found. Therefore 0/158 table units, 0/204 figure markers, and
0/18 empirical panels have been regenerated by an author-native pipeline.

There are material paper-level ambiguities and inconsistencies. The prose says
mathematical reconstruction consistency is above 95%, but Alpha191 is 94.9%.
The appendix defines nonnegative MDD while Table 1 prints negative MDD. The
paper's "top-outside" description treats 5 as bottom-universe exclusions, while
Qlib's TopkDropoutStrategy defines n_drop as positions replaced per trading
date. Algorithm 2 generates one new logic after the final evaluated attempt, so
its printed control flow makes T+1 generator calls for T evaluated logics. The
actual scalar selection objective J is not identified.

Three later, unaffiliated repositories were inspected. The sjkncs program runs
but is an invented Gaussian synthetic demo. The kaihenglin repository fails
bytecode compilation with two syntax errors and targets a crypto/live-trading
adaptation. QuantNodes passes 52 focused tests in a clean isolated Python 3.12
environment, providing useful independent logic/outer-loop component evidence,
but it substitutes IR for IC, defaults to four outer rounds, starts with only
Alpha101/Alpha158, and ships no paper experiment lineage. All three receive zero
native-paper and zero published-result credit.

Maximum honest faithfulness is therefore strong document/specification
recovery plus independently tested component behavior and an explicit release
boundary. It is not a true empirical replication of the reported AlphaLogics
results.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    inputs = validate_inputs(scratch)
    source = inputs["source"]
    output.mkdir(parents=True, exist_ok=True)
    results = parse_published_results(source)
    prompts = parse_prompts(source)
    operations = parse_dsl(source)
    figures = figure_rows()
    markers = figure_marker_rows()
    algorithms = algorithm_audit(source)
    candidates = candidate_audit(scratch)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "prompt_template_ledger.csv", prompts)
    write_csv(output / "dsl_operation_ledger.csv", operations)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "figure_marker_ledger.csv", markers)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "internal_consistency_audit.csv", internal_rows())
    write_json(output / "algorithm_conformance.json", algorithms)
    write_json(output / "candidate_release_audit.json", candidates)
    write_json(output / "source_provenance.json", {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv": {
            "identifier": ARXIV_ID,
            "version": "v1",
            "submitted": "2026-03-10T12:18:02Z",
            "authors": ["Zhangyuhua Weng", "Shengli Zhang", "Taotao Wang", "Yihan Xia"],
            "official_pdf_sha256": PINS["discovery/tracked.pdf"],
            "source_archive_sha256": PINS["discovery/arxiv-source.tar"],
            "source_tex_sha256": PINS["source-v1/arxiv.tex"],
            "official_pages": 19,
            "source_files": 10,
        },
        "rebuild": {
            "unmodified_source_compiled": True,
            "rebuilt_pdf_sha256": PINS["source-v1/arxiv.pdf"],
            "rebuilt_pages": 19,
            "text_comparison": inputs["text_comparison"],
            "visual_qa": {
                "official_pages_inspected": 19,
                "rebuilt_pages_inspected": 19,
                "unreadable_clipped_overlapping_blank_or_missing_research_pages": 0,
                "contact_sheet_sha256": {
                    relative.split("/")[-1]: digest
                    for relative, digest in PINS.items() if relative.startswith("render/contact-")
                },
            },
        },
        "release_boundary": {
            "attributable_alphalogics_code_recovered": False,
            "complete_research_inputs_recovered": False,
            "published_result_lineage_recovered": False,
            "post_paper_independent_candidates_counted_as_native": False,
        },
    })
    (output / "README.md").write_text(readme(), encoding="utf-8")
    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "official_pdf_recovered": True,
        "official_source_recovered": True,
        "official_pages_visually_checked": 19,
        "rebuilt_pages_visually_checked": 19,
        "unmodified_source_rebuild_completed": True,
        "active_agent_prompt_templates": len(prompts),
        "valid_json_prompt_templates": sum(row["valid_json"] for row in prompts),
        "filled_runtime_prompts_recovered": 0,
        "dsl_operations_specified": len(operations),
        "author_native_dsl_operations_executed": 0,
        "algorithms_specified": 2,
        "paper_derived_algorithm_checks_passed": 2,
        "attributable_alphalogics_code_recovered": False,
        "published_numeric_table_units": len(results),
        "native_numeric_table_units_regenerated": 0,
        "figures": len(figures),
        "display_panels": sum(row["display_panels"] for row in figures),
        "empirical_panels": sum(row["empirical_panels"] for row in figures),
        "native_empirical_panels_regenerated": 0,
        "displayed_figure_result_markers": len(markers),
        "native_figure_result_markers_regenerated": 0,
        "independent_candidate_repositories": 3,
        "independent_candidates_with_native_credit": 0,
        "full_end_to_end_pipeline_reproduced": False,
        "strict_success": False,
    }
    manifest["output_sha256"] = {
        path.name: sha256(path) for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch, args.output)
    print(args.output)
    if args.strict and not manifest["strict_success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
