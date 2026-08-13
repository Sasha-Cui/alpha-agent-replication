#!/usr/bin/env python3
"""Build a fail-closed source, result, prompt, and release audit for BlindTrade."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/blind_trade_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/blindtrade"
WORK_ID = "CensusArxiv260317692"
SYSTEM_ID = "SYS-BLIND-TRADE"
ARXIV_ID = "2603.17692"

PINS = {
    "current/official.pdf": "3a4209a4b7530d2f8641ba3a63f13d44aeef1610c82a14e9e490fb09989a9416",
    "current/source.tar": "dbbc8be0a1370aacca6e7ac8690d646223774a085cf2b30621a4f235ed38997e",
    "current/rebuilt.pdf": "104f38906dba3773069bbae9466760d8c02fd2112c67ba16d8a4b0e3d9edd89e",
    "current/official.txt": "c53b99f790c472d29ed0cabb335a8fec7c1e4721b63bec980153af9914092ae8",
    "current/rebuilt.txt": "6795212c1b1536da6b81273f58ee5c2617ca823e6c215e64b9d6c83283c4f41c",
    "current/source/blindtrade_iclr2026.tex": "76bd511e836e7d2a5d46aa80eacc74a1a3d13c933c0305be5a48547b6a85b7bd",
    "discovery/arxiv-abs.html": "747224925a8d476fc6bab8d1125f8e08e8ac0cd9a2b1a06dcc568adb8d6bedb5",
    "discovery/arxiv-api.xml": "9f0641ee2113df494786e8895bb4ad3d6681f002bdafc1603f2af0a00e04f353",
    "discovery/openreview-observation.json": "2109f6583355932436cf77338a47d54dc9ddcc5eb717a7eecea4af1d44e32704",
    "discovery/github-repository-search.json": "18e39e6df4599de56d6669d36ac8164710df904cfbce152ab4fb0f6421cdebdf",
    "discovery/github-code-arxiv-search.json": "df4d5d586b2558307aa52ce133f5a26e67f7241a2c3fda6b960a3729de1841d6",
    "discovery/github-profile-ds-academy.json": "437f52f4ab6f10d72ba0d1d6a7d3b585898eeb638210abe02b64ce244aa19d12",
    "discovery/github-repos-ds-academy.json": "11686f27f2eb6f9e2c18c208216d8549eaba45cf1188c0c9159c8ea42c83e121",
    "discovery/github-code-ds-academy-blindtrade.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/huggingface-models-blindtrade.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-datasets-blindtrade.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/gemini-2.5-flash-model-card.pdf": "f3221d9458b2fed961c4eb8bef0b33a8164550a7e87b3805278209d12e9f34af",
    "discovery/gemini-2.5-flash-model-card.txt": "86cdc570d99b37941b9f6d14c5716c2cb51bbb3d7b18ac481e1e270b3d20c0ae",
    "discovery/invesco-eqwl-fact-sheet-page.html": "a2cc883a1ba8a4c367178f00eb19c956b648971cb074b0259db9c57c769ee469",
    "discovery/invesco-rsp-page.html": "f8c517c1254830269cb773481e46d2b4e780d5f852d8c67867c567b62c7f1437",
    "benchmark_data/SPY_yahoo_current.csv": "9d4233864f68c8674102f2e5831b1a47958902d871713b78d43ece07e07e7f99",
    "benchmark_data/EQWL_yahoo_current.csv": "502bf13cf367cb25757b9db2f95487d95c5768032fc96d98b471a6f5411a9853",
    "benchmark_data/RSP_yahoo_current.csv": "33082e5a17462bd5abce6e19b826eb645ddcbb04a085f1c3500932d4f1a77027",
    "benchmark_data/metadata.json": "10c03f10c8c0814f52815aee357e453af6bf50c8ed042b53d7c021bec3a16d10",
}

TABLE_EXPECTED = {
    "ic_comparison": 15,
    "main_results": 24,
    "stability": 9,
    "extended_oos_full": 30,
    "extended_oos_breakdown": 20,
}

FIGURES = (
    ("fig01_oos_wealth_blindtrade_vs_bench_v2.pdf", "main_oos_wealth", 1, True),
    ("figA10_leakage_negative_control_summary_v2.pdf", "leakage_controls", 2, True),
    ("figA11_intent_profile_train_val_oos_v2.pdf", "intent_profile", 2, True),
    ("figA12_intent_decision_metrics_v2.pdf", "intent_decision_metrics", 3, True),
    ("figA3_rl_state_tsne_train_val_oos_v2.pdf", "rl_state_tsne", 1, True),
    ("figures/fig00_blindtrade_pipeline_iclr.pdf", "pipeline", 1, False),
    ("figE_rl_policy_network_tikz.pdf", "policy_architecture", 1, False),
)


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


def token_jaccard(left: str, right: str) -> float:
    a = Counter(re.findall(r"\w+", left.lower()))
    b = Counter(re.findall(r"\w+", right.lower()))
    return sum((a & b).values()) / sum((a | b).values())


def clean_tex(value: str) -> str:
    previous = None
    while previous != value:
        previous = value
        value = re.sub(r"\\(?:textbf|mathbf|underline|textit|multirow)\{([^{}]*)\}", r"\1", value)
    value = value.replace(r"\%", "%").replace(r"\pm", "±").replace("$", "")
    value = value.replace(r"\times", "x").replace(r"\textbf", "")
    value = re.sub(r"\\[A-Za-z]+(?:\([^)]*\))?", "", value)
    value = value.replace("{", "").replace("}", "")
    return " ".join(value.split()).strip()


def table_block(source: str, label: str) -> str:
    marker = rf"\label{{tab:{label}}}"
    index = source.index(marker)
    start = source.rfind(r"\begin{table", 0, index)
    end = source.index(r"\end{table", index)
    block = source[start:end]
    return block[block.index(r"\midrule") + len(r"\midrule") : block.index(r"\bottomrule")]


def data_lines(block: str) -> list[list[str]]:
    rows = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("%", r"\midrule", r"\multirow")) or "&" not in line:
            continue
        cells = [clean_tex(cell.rstrip(" \\\r\n")) for cell in line.split("&")]
        rows.append(cells)
    return rows


def result_row(table: str, row: str, metric: str, printed: str) -> dict[str, Any]:
    if not re.search(r"\d", printed):
        raise ValueError(f"non-numeric result cell: {table}/{row}/{metric}={printed!r}")
    return {
        "table": table,
        "row": row,
        "metric": metric,
        "printed_value": printed,
        "source_tex_recovered": True,
        "author_native_experiment_executed": False,
        "published_result_regenerated": False,
        "native_paper_result_credit": False,
        "blocking_reason": (
            "no attributable code, frozen point-in-time data, LLM request/response corpus, "
            "trained checkpoints, seed-level paths, holdings, returns, or raw result arrays"
        ),
    }


def parse_published_results(source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordinary = {
        "ic_comparison": ("raw_ic_p", "llm_ic_p", "delta_ic"),
        "main_results": ("sharpe", "cumret", "mdd", "vol"),
        "stability": ("delta_sharpe_vs_spy", "std", "win_rate"),
    }
    for table, metrics in ordinary.items():
        for cells in data_lines(table_block(source, table)):
            if len(cells) != len(metrics) + 1:
                raise ValueError(f"column mismatch in {table}: {cells}")
            for metric, value in zip(metrics, cells[1:]):
                rows.append(result_row(table, cells[0], metric, value))

    extended_metrics = ("sharpe", "cumret", "annret", "vol", "mdd")
    extended_strategies = ("SPY", "EQWL", "Momentum", "MCap Top-20", "RAW Top-20", "BlindTrade")
    for cells in data_lines(table_block(source, "extended_oos_full")):
        if len(cells) != 7 or cells[0].lower().replace(" (%)", "") not in extended_metrics:
            raise ValueError(f"extended table changed: {cells}")
        metric = cells[0].lower().replace(" (%)", "")
        for strategy, value in zip(extended_strategies, cells[1:]):
            rows.append(result_row("extended_oos_full", strategy, metric, value))

    period = ""
    breakdown = table_block(source, "extended_oos_breakdown")
    for line in breakdown.splitlines():
        if "2024 (Bull)" in line:
            period = "2024_bull"
            continue
        if "2025 YTD (Volatile)" in line:
            period = "2025_ytd_volatile"
            continue
        if "&" not in line or line.strip().startswith(("%", r"\midrule")):
            continue
        cells = [clean_tex(cell.rstrip(" \\\r\n")) for cell in line.split("&")]
        if cells[0] != "" or len(cells) != 7 or not period:
            continue
        for metric, value in zip(("sharpe", "cumret", "annret", "vol", "mdd"), cells[2:]):
            rows.append(result_row("extended_oos_breakdown", f"{period}:{cells[1]}", metric, value))

    counts = Counter(row["table"] for row in rows)
    if counts != Counter(TABLE_EXPECTED):
        raise ValueError(f"published table denominator changed: {counts}")
    anchors = {(r["table"], r["row"], r["metric"]): r["printed_value"] for r in rows}
    expected = {
        ("main_results", "BlindTrade", "sharpe"): "1.40 ± 0.22",
        ("main_results", "SPY", "mdd"): "-19.00",
        ("extended_oos_full", "BlindTrade", "sharpe"): "0.69 ± 0.23",
        ("extended_oos_breakdown", "2024_bull:SPY", "mdd"): "-8.4",
    }
    for key, value in expected.items():
        if anchors.get(key) != value:
            raise ValueError(f"published anchor changed: {key}={anchors.get(key)!r}")
    return rows


def parse_prompts(source: str) -> list[dict[str, Any]]:
    section = source[source.index(r"\subsection{Full System Prompts (Verbatim)}") :]
    names = ("Momentum Agent", "News-Event Agent", "Mean-Reversion Agent", "Risk-Regime Agent")
    rows = []
    for name in names:
        marker = rf"\subsubsection{{{name}}}"
        start = section.index(marker)
        next_start = min(
            [
                position
                for position in (
                    section.find(r"\subsubsection", start + len(marker)),
                    section.find(r"\subsection", start + len(marker)),
                )
                if position >= 0
            ]
        )
        block = section[start:next_start]
        match = re.search(r"\\begin\{lstlisting\}.*?\n(.*?)\\end\{lstlisting\}", block, re.DOTALL)
        if not match:
            raise ValueError(f"missing printed prompt: {name}")
        text = match.group(1)
        schema = text[text.index("OUTPUT JSON SCHEMA:") + len("OUTPUT JSON SCHEMA:") :].strip()
        try:
            json.loads(schema)
            valid_json = True
            error = ""
        except json.JSONDecodeError as exc:
            valid_json = False
            error = f"{exc.msg} at line {exc.lineno} column {exc.colno}"
        rows.append(
            {
                "agent": name,
                "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "source_prompt_recovered": True,
                "printed_schema_valid_json": valid_json,
                "printed_schema_error": error,
                "schema_declares_cross_sectional_score": "cross_sectional_score" in schema,
                "batch_instruction_requires_cross_sectional_score": True,
                "filled_runtime_request_recovered": False,
                "filled_runtime_response_recovered": False,
                "native_execution_credit": False,
            }
        )
    return rows


def printed_scalar(value: str) -> float:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value.replace("$-$", "-"))
    if not match:
        raise ValueError(value)
    return float(match.group())


def decimals(value: str) -> int:
    token = re.search(r"[-+]?\d+(?:\.\d+)?", value.replace("$-$", "-"))
    assert token
    return len(token.group().partition(".")[2])


def price_metrics(path: Path, start: str, end: str) -> dict[str, float]:
    data = pd.read_csv(path, parse_dates=["Date"]).set_index("Date")
    prices = data.loc[start:end, "Close"].dropna()
    returns = prices.pct_change().dropna()
    cumulative = prices.iloc[-1] / prices.iloc[0] - 1
    return {
        "sharpe": float(returns.mean() / returns.std(ddof=1) * np.sqrt(252)),
        "cumret": float(cumulative * 100),
        "annret": float(((1 + cumulative) ** (252 / (len(prices) - 1)) - 1) * 100),
        "vol": float(returns.std(ddof=1) * np.sqrt(252) * 100),
        "mdd": float((prices / prices.cummax() - 1).min() * 100),
    }


def benchmark_replay(scratch: Path, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {(r["table"], r["row"], r["metric"]): r["printed_value"] for r in results}
    tasks = []
    for strategy in ("SPY", "EQWL"):
        tasks.append(("main_results", strategy, strategy, "2025-01-02", "2025-08-01"))
        tasks.append(("extended_oos_full", strategy, strategy, "2024-01-02", "2025-08-01"))
    tasks.extend(
        (
            ("extended_oos_breakdown", "2024_bull:SPY", "SPY", "2024-01-02", "2024-12-31"),
            ("extended_oos_breakdown", "2025_ytd_volatile:SPY", "SPY", "2025-01-02", "2025-08-01"),
        )
    )
    output = []
    for table, row, symbol, start, end in tasks:
        computed = price_metrics(scratch / f"benchmark_data/{symbol}_yahoo_current.csv", start, end)
        metrics = (
            ("sharpe", "cumret", "mdd", "vol")
            if table == "main_results"
            else (
                "sharpe",
                "cumret",
                "annret",
                "vol",
                "mdd",
            )
        )
        for metric in metrics:
            printed = lookup[(table, row, metric)]
            places = decimals(printed)
            match = round(computed[metric], places) == printed_scalar(printed)
            output.append(
                {
                    "table": table,
                    "row": row,
                    "metric": metric,
                    "printed_value": printed,
                    "symbol": symbol,
                    "start": start,
                    "end": end,
                    "price_basis": "unadjusted close",
                    "computed_value": f"{computed[metric]:.10f}",
                    "display_decimals": places,
                    "matches_printed_precision": match,
                    "evidence_class": "current_public_snapshot_component" if match else "nonmatch",
                    "author_native_credit": False,
                    "blindtrade_result_credit": False,
                }
            )
    if len(output) != 28 or sum(row["matches_printed_precision"] for row in output) != 6:
        raise ValueError("passive benchmark replay boundary changed")
    return output


def method_specs() -> list[dict[str, Any]]:
    values = (
        ("universe", "daily point-in-time S&P 500 constituents via EODHD", True),
        ("full sample", "2020-01-02 through 2025-08-01; 1,403 trading days", True),
        ("primary split", "train through 2024-09-30; validation 2024Q4; OOS 2025-01-02 to 2025-08-01", True),
        ("extended split", "train through 2023; six half-year rolling validation windows; OOS 2024-2025", True),
        ("anonymization", "ticker/company/product names replaced; Google Knowledge Graph used", False),
        ("LLM agents", "four roles; full system prompts printed", True),
        ("LLM model", "Gemini 2.5 Flash accessed September-October 2025", False),
        (
            "LLM request settings",
            "temperature, thinking budget, safety settings, exact version, and retries absent",
            False,
        ),
        ("news corpus", "up to five anonymized headlines per stock from t-60 to t-1", False),
        ("reasoning embedder", "all-MiniLM-L6-v2; 384 dimensions", True),
        ("semantic graph", "same-sector plus cosine > 0.75; top 10 semantic neighbors", True),
        ("GNN", "two GATv2 layers, four heads, 394 to 128 dimensions", False),
        ("GNN losses", "HL-Gauss 101 bins plus ranking, risk, and JS terms", False),
        ("RL", "PPO-DSR; top-20 equity-only Dirichlet policy", False),
        ("PPO hyperparameters", "lr 3e-4, gamma .99, GAE .95, clip .2", False),
        ("cost", "10 bps per unit turnover", True),
        ("primary Optuna", "eta .10, reward-cost scale .358, alpha0 466.8; search space/trials absent", False),
        ("extended Optuna", "eta .08 and cost scale .40; search space/trials absent", False),
        ("seeds", "20 independent seeds; identities and seed-level outputs absent", False),
        ("code and runtime", "not released", False),
        ("raw/LLM feature dataset", "promised upon publication; not exposed", False),
        ("checkpoints and predictions", "not released", False),
        ("holdings, returns, and plot arrays", "not released", False),
    )
    return [
        {"dimension": name, "paper_value_or_state": value, "sufficiently_specified": complete}
        for name, value, complete in values
    ]


def inconsistencies() -> list[dict[str, Any]]:
    values = (
        (
            "holdout_feature_selection",
            "features are retained when informative on holdout, and the Risk-Regime 2025 holdout IC is cited, contaminating the OOS used for headline performance",
            "test-set selection leakage",
        ),
        (
            "anonymization_not_ablated",
            "the paper claims anonymization supports signal legitimacy but says a direct anonymization ablation was not performed and remains future work",
            "headline causal claim not directly tested",
        ),
        (
            "shuffle_control_overclaim",
            "cross-sectional score shuffling destroys all structured signals, including structured leakage, so it cannot establish the signal is legitimate rather than leaked",
            "negative control is non-identifying",
        ),
        (
            "eqwl_identity",
            "the paper calls EQWL an S&P 500 equal-weight ETF; EQWL tracks the S&P 100 equal-weight index, while RSP is the S&P 500 equal-weight ETF",
            "benchmark mislabeled",
        ),
        (
            "printed_json_schemas",
            "all four exact output schemas use comments and symbolic float/string values, so none is valid JSON as printed",
            "claimed deterministic parseability is not literal",
        ),
        (
            "batch_schema_field",
            "the batch instruction requires cross_sectional_score, but none of the four full output schemas declares that field",
            "prompt/schema mismatch",
        ),
        (
            "fully_reproducible_claim",
            "the reproducibility statement says fully reproducible while code, data, requests, checkpoints, paths, and arrays are absent and the dataset is only planned for release",
            "claim exceeds public evidence",
        ),
        (
            "model_cutoff_overlap",
            "Gemini 2.5 Flash has an official January 2025 knowledge cutoff, overlapping the OOS beginning January 2025; a prompt cannot erase pretrained knowledge",
            "prospective LLM holdout not established",
        ),
    )
    return [{"issue": key, "evidence": evidence, "impact": impact} for key, evidence, impact in values]


def build(scratch: Path, output: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"missing or changed pinned evidence: {relative}")
    source = (scratch / "current/source/blindtrade_iclr2026.tex").read_text()
    results = parse_published_results(source)
    prompts = parse_prompts(source)
    replay = benchmark_replay(scratch, results)

    excluded = {
        "blindtrade_iclr2026.aux",
        "blindtrade_iclr2026.bbl",
        "blindtrade_iclr2026.blg",
        "blindtrade_iclr2026.log",
        "blindtrade_iclr2026.out",
        "blindtrade_iclr2026.pdf",
    }
    source_files = sorted(
        path.relative_to(scratch / "current/source").as_posix()
        for path in (scratch / "current/source").rglob("*")
        if path.is_file() and path.name not in excluded
    )
    if len(source_files) != 14:
        raise ValueError(f"source inventory changed: {source_files}")

    figure_rows = []
    for filename, role, panels, empirical in FIGURES:
        path = scratch / "current/source" / filename
        figure_rows.append(
            {
                "source_asset": filename,
                "role": role,
                "panels": panels,
                "empirical": empirical,
                "source_asset_sha256": sha256(path),
                "raw_numeric_array_recovered": False,
                "author_native_regeneration": False,
                "paper_result_credit": False,
            }
        )

    github_repos = json.loads((scratch / "discovery/github-repos-ds-academy.json").read_text())
    openreview = json.loads((scratch / "discovery/openreview-observation.json").read_text())
    model_card = (scratch / "discovery/gemini-2.5-flash-model-card.txt").read_text()
    if "knowledge cutoff date for Gemini 2.5 Flash" not in model_card or "January 2025" not in model_card:
        raise ValueError("Gemini cutoff evidence changed")
    if any("blindtrade" in item["name"].lower() for item in github_repos):
        raise ValueError("attributable BlindTrade repository now appears in pinned inventory")
    source_provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "arxiv_version": "v1",
        "submitted": "2026-03-18",
        "title": "Can Blindfolded LLMs Still Trade? An Anonymization-First Framework for Portfolio Optimization",
        "authors": ["Joohyoung Jeon", "Hongchul Lee"],
        "official_pages": len(PdfReader(scratch / "current/official.pdf").pages),
        "rebuilt_pages": len(PdfReader(scratch / "current/rebuilt.pdf").pages),
        "official_rebuilt_token_jaccard": token_jaccard(
            (scratch / "current/official.txt").read_text(),
            (scratch / "current/rebuilt.txt").read_text(),
        ),
        "source_files": len(source_files),
        "official_pages_visually_checked": 18,
        "rebuilt_pages_visually_checked": 18,
        "visual_defects_observed": 0,
        "openreview_forum_id": openreview["forum_id"],
        "openreview_license": openreview["license"],
        "openreview_supplement_exposed": openreview["supplement_exposed"],
        "openreview_code_or_dataset_exposed": openreview["code_link_exposed"] or openreview["dataset_link_exposed"],
        "openreview_revision_page": openreview["revision_page_text"],
        "first_author_github": "ds-academy",
        "first_author_public_repositories_checked": len(github_repos),
        "first_author_blindtrade_code_search_matches": 0,
        "generic_github_repository_search_count": json.loads(
            (scratch / "discovery/github-repository-search.json").read_text()
        )["total_count"],
        "generic_github_code_search_count": json.loads(
            (scratch / "discovery/github-code-arxiv-search.json").read_text()
        )["total_count"],
        "huggingface_model_matches": len(
            json.loads((scratch / "discovery/huggingface-models-blindtrade.json").read_text())
        ),
        "huggingface_dataset_matches": len(
            json.loads((scratch / "discovery/huggingface-datasets-blindtrade.json").read_text())
        ),
        "attributable_blindtrade_release_found": False,
        "negative_search_scope": (
            "bounded; does not prove that private, deleted, moved, or unindexed material never existed"
        ),
    }

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "passive_benchmark_replay.csv", replay)
    write_csv(output / "prompt_schema_audit.csv", prompts)
    write_csv(output / "figure_inventory.csv", figure_rows)
    write_csv(output / "method_specification_audit.csv", method_specs())
    write_csv(output / "internal_consistency_audit.csv", inconsistencies())
    write_json(output / "source_provenance.json", source_provenance)

    readme = (
        "# BlindTrade paper-level replication audit\n\n"
        "This fail-closed audit rebuilds and visually checks the full arXiv source, inventories every "
        "active empirical table cell and figure panel, validates the four printed prompt schemas, "
        "replays directly testable passive benchmarks, and checks the signed OpenReview record plus "
        "bounded author-attributable release surfaces.\n\n"
        "The manuscript is specification-rich but is not reproducible end to end from public artifacts. "
        "No BlindTrade code, input/output dataset, immutable model calls, checkpoints, seed-level paths, "
        "holdings, returns, or raw arrays is exposed. Thus 0/98 table cells and 0/9 empirical panels "
        "receive author-native result credit. A current public price snapshot matches 6/98 cells at "
        "printed precision, all passive benchmark components; this is not BlindTrade credit. All four "
        "verbatim output schemas fail JSON parsing as printed.\n\n"
        "The strongest validity boundary is more serious than missing files: features are screened on "
        "the reported holdout, anonymization is not directly ablated, and score shuffling cannot "
        "distinguish genuine structure from structured leakage. The paper also misidentifies EQWL as "
        "an S&P 500 equal-weight ETF.\n"
    )
    (output / "README.md").write_text(readme)

    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "official_pages_visually_checked": 18,
        "rebuilt_pages_visually_checked": 18,
        "published_numeric_table_cells": len(results),
        "author_native_table_cells_regenerated": 0,
        "current_public_passive_benchmark_cells_replayed": len(replay),
        "current_public_passive_benchmark_cells_matching": sum(row["matches_printed_precision"] for row in replay),
        "empirical_figure_panels": sum(row["panels"] for row in figure_rows if row["empirical"]),
        "author_native_empirical_panels_regenerated": 0,
        "full_system_prompts_recovered": len(prompts),
        "printed_prompt_schemas_valid_json": sum(row["printed_schema_valid_json"] for row in prompts),
        "attributable_code_or_data_release_found": False,
        "strict_success": False,
        "strict_failure_reason": (
            "no attributable BlindTrade pipeline or paper-result lineage; reported OOS is used for feature screening"
        ),
    }
    generated = sorted(path.name for path in output.iterdir() if path.is_file() and path.name != "manifest.json")
    manifest["generated_file_sha256"] = {name: sha256(output / name) for name in generated}
    write_json(output / "manifest.json", manifest)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    manifest = build(args.scratch, args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 1 if args.strict and not manifest["strict_success"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
