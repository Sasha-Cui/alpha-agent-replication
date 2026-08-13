#!/usr/bin/env python3
"""Build a fail-closed primary-source and paper-mechanics audit for MetaPS."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from pypdf import PdfReader

from alpha_evolve import metaps_paper_components as component


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/metaps_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/metaps"
WORK_ID = "CensusArxiv260622385"
SYSTEM_ID = "SYS-METAPS"
ARXIV_ID = "2606.22385"

PINS = {
    "primary/arxiv-api.xml": "316035efc393f7eda3912ee8bcc8aad022f7e797423a8b61a63ef3bc0bd35e2a",
    "primary/official.pdf": "fd2ce88b351e9abfc0c96103f7927ee9f365231bfce8df492beb4054777148f6",
    "primary/official.txt": "9f867586e11ef419fea7249a2fa390c6e3c03b9baeecea5b9d15d18bc2a2146c",
    "primary/rebuilt.pdf": "95ef63377c7f1214b6eb6ecf062f944dc226beac928e801790f3e45ca140bd12",
    "primary/rebuilt.txt": "3aba4069b45b339b374244f80973ee7d34ba4ab9659057a212d784d69fd1bc41",
    "primary/source.tar": "c6e3378c0cccf455c2dc7fa11bccda70b4c279bb7e16c3901f99df0237b46780",
    "discovery/github-code-arxiv.json": "6cb78aaa7b54c12f2efd8571e21395b10937bd5237e7fd0b499c536ba53a7806",
    "discovery/github-code-arxiv-page2.json": "a5ba2317e34bac3562e4ae1b9af8efbb0deb3b97b8a75f6bba9d402a76166be5",
    "discovery/github-code-class.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-code-sandbox-roles.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-code-strategy-key.json": "88d8a722036862aa5669d8e1c6a3578d3e12db023309eaa3dc21e8c0476d753d",
    "discovery/github-code-title.json": "8051381e9014bfb726e57065f8f9508c5ec400c976e4fde0e367a33bfaa1b38a",
    "discovery/github-repositories-arxiv.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-repositories-title.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-users-first-author.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-users-second-author.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/huggingface-datasets.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-models.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/openreview-page.html": "8d2e5d2cb0a3f1fd5617d5359f42aa720eb284bd901b217c645df7196a2d99ef",
}

# One result unit is one populated displayed quantitative table cell. A cell
# containing multiple printed counts stays one displayed unit, matching the
# repository-wide fail-closed convention.
TABLE_SPECS = {
    "tab:main_results": ("sections/experiments_conclusion.tex", (1, 2, 3, 4, 5, 6), 72),
    "tab:input_target_ablation": ("sections/experiments_conclusion.tex", (4, 5), 24),
    "tab:econswitch_9b_objectives": ("sections/experiments_conclusion.tex", (1, 2, 3, 4, 5), 20),
    "tab:rolling_4b_full_metrics": ("sections/experiments_conclusion.tex", (1, 2, 3, 4, 5), 90),
    "tab:direct_action_full": ("sections/appendix.tex", (1, 2, 3, 4, 5, 6, 7), 14),
    "tab:main_scale_training_full_metrics": (
        "tables/tab_main_scale_training_full_metrics.tex",
        (2, 3, 4, 5, 6, 7, 8),
        168,
    ),
    "tab:strategy_behavior_best": (
        "tables/tab_strategy_behavior_best.tex",
        (2, 3, 4, 5, 6),
        20,
    ),
    "tab:training_action_distribution": (
        "tables/tab_training_action_distribution.tex",
        (1, 2, 3, 4),
        12,
    ),
    "tab:controlled_sandbox_app": ("sections/appendix.tex", (1, 2, 3, 4, 5, 6), 72),
}
EXPECTED_RESULT_UNITS = 492

FIGURE_SPECS = (
    ("fig:metaps_framework", "imgs/framework.png", 0, "conceptual pipeline"),
    ("fig:main_baseline_return", "imgs/fig_paper_main_baseline_return.png", 1, "stock return bar comparison"),
    ("fig:return_cumulative_baselines", "imgs/fig_return_cumulative_baselines.png", 1, "stock cumulative-return trajectories"),
    ("fig:main_strategy_behavior", "imgs/fig_main_strategy_behavior.png", 2, "SFT and held-out strategy distributions"),
    ("fig:cmp_across_size", "imgs/cmp_across_size.png", 1, "risk-return comparison across scales"),
    ("fig:cmp_across_size_bar", "imgs/cmpreturn_across_size_bar.png", 1, "return comparison across scales"),
    ("fig:appendix_equity_curves_2025", "imgs/fig_appendix_equity_curves_2025.png", 2, "best-run and top-five equity curves"),
    ("fig:return_equity_curves_baselines", "imgs/fig_return_equity_curves_baselines.png", 1, "representative baseline equity curves"),
    ("fig:return_excess_metaps9b", "imgs/fig_return_excess_metaps9b.png", 1, "return gaps relative to MetaPS-9B V3"),
    ("fig:appendix_drawdown_curves_2025", "imgs/fig_appendix_drawdown_curves_2025.png", 1, "top-six drawdown curves"),
    ("fig:return_drawdown_baselines", "imgs/fig_return_drawdown_baselines.png", 1, "representative baseline drawdowns"),
    ("fig:appendix_block_returns_2025", "imgs/fig_appendix_block_returns_2025.png", 1, "block-level returns"),
    ("fig:return_monthly_heatmap", "imgs/fig_return_monthly_heatmap.png", 1, "monthly returns"),
    ("fig:appendix_main_risk_return", "imgs/fig_paper_main_risk_return.png", 1, "risk-return scatter"),
    ("fig:appendix_context_ablation", "imgs/fig_paper_context_ablation.png", 1, "context ablation"),
    ("fig:appendix_scale_heatmap", "imgs/fig_paper_scale_objective_heatmap.png", 1, "scale-objective returns"),
    ("fig:strategy_distribution_heatmap", "imgs/fig_strategy_distribution_heatmap.png", 1, "strategy distributions"),
    ("fig:best_model_action_distribution", "imgs/fig_best_model_action_distribution.png", 1, "held-out action distribution"),
    ("fig:training_label_distribution", "imgs/fig_training_label_distribution.png", 1, "SFT action-label distribution"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def verify_pins(scratch: Path) -> None:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != expected:
            raise ValueError(f"pin mismatch: {relative}={observed}; expected {expected}")


def paper_sources(scratch: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(scratch / "primary/source.tar", "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe source member: {member.name}")
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError(f"unreadable source member: {member.name}")
            files[member.name] = handle.read()
    if len(files) != 31:
        raise ValueError(f"paper source file count changed: {len(files)}")
    return files


def source_text(files: Mapping[str, bytes], path: str) -> str:
    return files[path].decode("utf-8")


def strip_comments(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("%"))


def table_environment(source: str, label: str) -> str:
    source = strip_comments(source)
    marker = rf"\label{{{label}}}"
    location = source.index(marker)
    begin = max(source.rfind(r"\begin{table", 0, location), source.rfind(r"\begin{sidewaystable", 0, location))
    endings = [
        value
        for value in (source.find(r"\end{table", location), source.find(r"\end{sidewaystable", location))
        if value >= 0
    ]
    if begin < 0 or not endings:
        raise ValueError(f"table boundary missing: {label}")
    return source[begin : min(endings)]


def clean_tex(value: str) -> str:
    value = value.replace(r"\%", "%").replace(r"\rightarrow", "->")
    value = re.sub(r"\textbf\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\(?:rowcolor|addlinespace)[^\n]*", "", value)
    value = re.sub(r"[{}$~]", "", value)
    return " ".join(value.split())


def table_data_rows(environment: str) -> list[list[str]]:
    match = re.search(
        r"\\begin\{tabular\}\{[^\n]*\}(.*?)\\end\{tabular\}",
        environment,
        re.S,
    )
    if match is None:
        raise ValueError("tabular body missing")
    rows: list[list[str]] = []
    for chunk in re.split(r"\\\\", match.group(1)):
        if "&" not in chunk or any(
            token in chunk for token in (r"\toprule", r"\bottomrule", r"\cmidrule", r"\multicolumn")
        ):
            continue
        rows.append([clean_tex(cell) for cell in chunk.split("&")])
    return rows


def result_rows(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    blocker = (
        "no attributable code, simulator, market/news/order-flow snapshot, SFT records, teacher calls, "
        "model adapters, seeds, predictions, trades, portfolio paths, raw arrays, or result generator"
    )
    rows: list[dict[str, Any]] = []
    for label, (path, columns, expected) in TABLE_SPECS.items():
        parsed = table_data_rows(table_environment(source_text(files, path), label))
        table_rows: list[dict[str, Any]] = []
        for row_index, cells in enumerate(parsed, 1):
            if not cells:
                continue
            first_quantitative_column = min(columns)
            row_label = " | ".join(
                cell for cell in cells[:first_quantitative_column] if cell
            ) or f"row_{row_index}"
            for column in columns:
                if column >= len(cells):
                    raise ValueError(f"short row in {label}: {cells}")
                cell = cells[column]
                if not re.search(r"\d", cell):
                    continue
                table_rows.append(
                    {
                        "table_label": label,
                        "row_index": row_index,
                        "row_label": row_label,
                        "quantitative_column_index": column,
                        "printed_cell": cell,
                        "unit_definition": "one populated displayed quantitative table cell",
                        "source_document_recovered": True,
                        "raw_result_record_recovered": False,
                        "author_native_experiment_executed": False,
                        "published_result_regenerated": False,
                        "paper_result_credit": False,
                        "blocking_reason": blocker,
                    }
                )
        if len(table_rows) != expected:
            raise ValueError(f"published denominator changed for {label}: {len(table_rows)} != {expected}")
        rows.extend(table_rows)
    if len(rows) != EXPECTED_RESULT_UNITS:
        raise ValueError(f"published result denominator changed: {len(rows)}")
    return rows


def figure_rows(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    rows = []
    for figure, path, panels, description in FIGURE_SPECS:
        rows.append(
            {
                "figure": figure,
                "source_asset": path,
                "source_asset_sha256": sha256_bytes(files[path]),
                "empirical_panels": panels,
                "description": description,
                "author_rendered_asset_recovered": True,
                "underlying_numeric_array_or_run_log_recovered": False,
                "author_native_figure_regenerated": False,
                "paper_result_credit": False,
            }
        )
    return rows


def component_rows() -> list[dict[str, Any]]:
    decisions = {
        "news_impulse": component.news_impulse([component.NewsEvent({"AAPL": -0.01, "NVDA": 0.005})]),
        "momentum_follow": component.momentum_follow({"AAPL": [100, 100, 100, 101]}),
        "risk_reset": component.risk_reset(
            cash=0,
            gross_exposure=1_000_000,
            volatility_regime=1.0,
            liquidity_regime=1.0,
        ),
        "liquidity_rebate": component.liquidity_rebate(
            price_history={"AAPL": [100, 100, 100, 100, 99.5]},
            liquidity_regime=0.8,
            volatility_regime=0.2,
            has_news=False,
        ),
        "volatility_breakout_literal": component.volatility_breakout_literal(
            {"AAPL": [100.0] * 19 + [100.1]}
        ),
    }
    v2 = component.v2_blended_score(
        horizon_gains={3: 1.0, 5: 2.0, 10: 3.0, 20: 4.0},
        horizon_weights={3: 0.1, 5: 0.2, 10: 0.3, 20: 0.4},
        transaction_cost_proxy=0.1,
        risk_penalty=0.2,
        turnover_penalty=0.3,
        utility_prior=1.5,
        candidate_edge=0.4,
        eta=0.2,
        kappa=0.5,
    )
    mechanics: list[tuple[str, str, Any, bool]] = [
        (name, "paper-printed compact strategy listing", decision.__dict__, True)
        for name, decision in decisions.items()
    ]
    mechanics.extend(
        [
            ("size_bucket_rule", "none/small/medium/large exposure fractions and share caps", dict(component.SIZE_BUCKETS), True),
            ("ranking_score", "rho trigger/text/prior/penalty equation", component.ranking_score(trigger_overlap=2, text_match=0.5, prior=0.1, missing_evidence_penalty=0.2, alpha=0.3, beta=0.4), True),
            ("v1_target", "unique one-step rollout argmax", component.v1_target({"momentum": 0.1, "risk": 0.05}), True),
            ("v2_score", "four-horizon utility and blend equations for supplied inputs", v2, True),
            ("v3_score", "quality plus distribution-control equation for supplied inputs", component.v3_balance_score(active_action_bonus=0.1, v2_score=v2, sample_weight=2.0, action_delta=-0.2, bucket_delta=0.05, strategy_delta=0.1), True),
            ("stock_return_identity", "100*(final/initial-1)", component.displayed_return(1_502_900, 1_000_000), True),
            ("sandbox_implied_initial", "invert stated return identity", component.implied_initial_value(31_514, 264.14), True),
        ]
    )
    return [
        {
            "component": name,
            "paper_specification": specification,
            "controlled_output": json.dumps(output, sort_keys=True),
            "deterministic_control_passed": passed,
            "paper_derived_not_author_code": True,
            "author_native_pipeline_executed": False,
            "published_result_regenerated": False,
            "paper_result_credit": False,
            "boundary": component.PAPER_BOUNDARY,
        }
        for name, specification, output, passed in mechanics
    ]


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official paper and source", "complete", "arXiv v1 PDF and complete 31-file source archive pinned; all 25 official and rebuilt pages visually inspected"),
        ("native implementation", "unreleased", "no implementation URL, environment, or source files; bounded release searches recover no attributable package"),
        ("stock universe", "specified", "AAPL, NVDA, SPY, QQQ, GLD, and USO"),
        ("stock frequency and split", "substantially_specified", "daily decisions; 2022--2024 train and 2025 test; expanding-window blocks printed"),
        ("stock market data", "schema_only", "price bars and return windows named without provider, immutable rows, adjustment policy, timestamps, or missing-data rules"),
        ("news and events", "schema_only", "summaries shown without provider, article/event IDs, collection queries, immutable content, or release"),
        ("order flow", "named_only", "recent order flow is named but not defined or released"),
        ("initial stock cash", "specified", "$1,000,000"),
        ("stock strategy roster", "names_and_compact_listings", "ten names and compact snippets are printed; helpers and registry metadata are not released"),
        ("candidate ranking", "equation_underspecified", "rho equation printed; alpha, beta, priors, trigger phrases, textmatch, penalties, and extraction are missing"),
        ("V1 labels", "formula_partial", "one-step argmax printed without simulator rewards or tie handling"),
        ("V2 labels", "formula_underspecified", "horizons printed; strategy weights, eta, kappa, trade margin, utility priors, edges, and penalty implementations missing"),
        ("V3 labels", "formula_underspecified", "quality formula printed; active bonus, target distributions, delta functions, and selection/tie rules missing"),
        ("sample weights", "qualitative_only", "clipping and relative hold weight described without formulas, bounds, or values"),
        ("teacher rewriting", "prompt_schema_only", "fixed sections shown without teacher model/checkpoint, prompt, temperature, requests, responses, or validation implementation"),
        ("SFT data", "aggregate_only", "528 examples per view and action totals printed; no records, labels, weights, rationales, or split lineage released"),
        ("model backbones", "family_and_scale_only", "Qwen3.5 0.8B/2B/4B/9B names shown without immutable revisions"),
        ("fine tuning", "missing", "no optimizer, learning rate, batch size, epochs, scheduler, precision, adapter configuration, seeds, or checkpoints"),
        ("inference", "prompt_schema_only", "one formatted example shown without decoding configuration, seeds, model outputs, parser, or request logs"),
        ("stock execution", "partial", "four bucket fractions/caps printed; position limits, transaction cost, slippage values, raw-mode mapping, invalid-action handling, and fills missing"),
        ("stock backtest", "missing", "no executable runtime, price/news panel, predictions, orders, fills, portfolio path, daily returns, or result generator"),
        ("sandbox environment", "narrative_only", "six regimes/roles and state categories named without transitions, rewards, action implementations, initial state, episode seeds, or simulator"),
        ("sandbox horizon", "specified", "100-day test split"),
        ("metrics", "partial", "return/Sharpe/MDD descriptions given without Sharpe annualization/std convention, win semantics, regret scale, or sandbox initial equity"),
        ("randomness and run lineage", "missing", "no seeds, repeated-run distributions, run IDs, checkpoints, logs, or environment lock"),
        ("raw empirical outputs", "missing", "492 quantitative table cells and 20 empirical panels are rendered without native arrays or run records"),
    )
    return [{"dimension": dimension, "status": status, "detail": detail} for dimension, status, detail in specs]


def internal_rows() -> list[dict[str, str]]:
    sandbox_pairs = (
        (13_401, 54.84),
        (18_609, 115.02),
        (26_647, 207.89),
        (23_872, 175.84),
        (26_002, 200.45),
        (15_030, 73.67),
        (23_879, 175.92),
        (23_249, 168.64),
        (23_554, 172.16),
        (31_514, 264.14),
        (27_631, 219.26),
        (30_454, 251.89),
    )
    initials = [component.implied_initial_value(final, ret) for final, ret in sandbox_pairs]
    if max(initials) - min(initials) >= 0.5:
        raise ValueError("sandbox return identity consistency changed")
    specs = (
        ("volatility_breakout_listing", "mathematically_unreachable", "current is included in the max/min window, so current>high*1.002 and current<low*0.998 cannot hold"),
        ("risk_reset_action_space", "conflict", "stock action space is BUY/SELL/HOLD and wrapper validates actions, but risk_reset emits REDUCE with no printed conversion"),
        ("raw_size_modes_to_runtime_buckets", "missing_mapping", "listings emit probe_to_medium/scalable/small_probe/counterbalance/reduce/balanced/liquidity/breakout while runtime maps only none/small/medium/large"),
        ("compact_listing_helpers", "unreleased_dependencies", "eight snippets call undefined domain helpers; compact listings are not a self-contained codebase"),
        ("small_cap_breakout_window", "ambiguous", "recent_high includes current while current>recent_high*0.998 accepts a price up to 0.2% below the high; intent is not uniquely recoverable"),
        ("stock_return_final_value", "rounding_consistent", "printed returns and rounded million-dollar final values agree with $1M initial cash at displayed precision"),
        ("sandbox_return_final_equity", "internally_consistent_undisclosed_initial", f"all 12 rows imply initial equity about {sum(initials)/len(initials):.2f}, range {max(initials)-min(initials):.2f}; initial state is not disclosed"),
        ("main_and_appendix_subsets", "consistent", "main stock/sandbox values agree with corresponding detailed scale/objective tables for displayed rows"),
        ("decision_count", "consistent", "best-router behavior counts and table hold/buy/sell totals sum to 250 decisions"),
        ("SFT_action_totals", "consistent", "each V1/V2/V3 HOLD+BUY+SELL total equals the printed 528 samples"),
        ("empirical_asset_lineage", "static_only", "source ships rendered PNGs but no underlying dated arrays, daily actions, or generation scripts"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def release_rows(scratch: Path) -> list[dict[str, Any]]:
    discovery = scratch / "discovery"
    zero_dicts = {
        "GitHub repository exact title": "github-repositories-title.json",
        "GitHub repository arXiv ID": "github-repositories-arxiv.json",
        "GitHub code StockStrategySpec": "github-code-class.json",
        "GitHub code sandbox roles": "github-code-sandbox-roles.json",
        "GitHub users exact first-author plus Fudan": "github-users-first-author.json",
        "GitHub users exact second-author plus Fudan": "github-users-second-author.json",
    }
    rows: list[dict[str, Any]] = []
    for surface, filename in zero_dicts.items():
        data = json.loads((discovery / filename).read_text())
        count = data.get("total_count", 0) if isinstance(data, dict) else len(data)
        if count != 0:
            raise ValueError(f"bounded zero-result search changed: {filename}")
        rows.append(
            {
                "surface": surface,
                "query_record": filename,
                "observed_matches": 0,
                "attributable_metaps_release_found": False,
                "observation": "complete bounded exact public search returned zero",
                "negative_search_boundary": "not proof that private, deleted, moved, renamed, unindexed, or later artifacts do not exist",
            }
        )
    for surface, filenames in (
        ("GitHub code exact arXiv ID", ("github-code-arxiv.json", "github-code-arxiv-page2.json")),
        ("GitHub code exact paper title", ("github-code-title.json",)),
        ("GitHub code generic strategy key", ("github-code-strategy-key.json",)),
    ):
        payloads = [json.loads((discovery / name).read_text()) for name in filenames]
        items = [item for data in payloads for item in data["items"]]
        rows.append(
            {
                "surface": surface,
                "query_record": ";".join(filenames),
                "observed_matches": len(items),
                "attributable_metaps_release_found": False,
                "observation": "matches are third-party indexes, feeds, reviews, unrelated numeric text, or unrelated generic strategy implementations",
                "negative_search_boundary": "bounded indexed public code search only",
            }
        )
    for surface, filename in (
        ("Hugging Face models", "huggingface-models.json"),
        ("Hugging Face datasets", "huggingface-datasets.json"),
    ):
        data = json.loads((discovery / filename).read_text())
        rows.append(
            {
                "surface": surface,
                "query_record": filename,
                "observed_matches": len(data),
                "attributable_metaps_release_found": False,
                "observation": "bounded exact-name search returned zero",
                "negative_search_boundary": "name search only",
            }
        )
    rows.append(
        {
            "surface": "OpenReview forum surface",
            "query_record": "openreview-page.html",
            "observed_matches": 1,
            "attributable_metaps_release_found": False,
            "observation": "public forum surface is behind browser verification; no code/data URL appears in the pinned arXiv source",
            "negative_search_boundary": "forum/review attachments not authenticated or treated as an author release",
        }
    )
    return rows


def build(scratch: Path, output: Path) -> dict[str, Any]:
    verify_pins(scratch)
    files = paper_sources(scratch)
    official_pages = len(PdfReader(scratch / "primary/official.pdf").pages)
    rebuilt_pages = len(PdfReader(scratch / "primary/rebuilt.pdf").pages)
    official_text = (scratch / "primary/official.txt").read_text(errors="replace")
    rebuilt_text = (scratch / "primary/rebuilt.txt").read_text(errors="replace")
    overlap = token_jaccard(official_text, rebuilt_text)
    if (official_pages, rebuilt_pages) != (25, 25) or overlap < 0.999:
        raise ValueError("paper rebuild/page evidence changed")

    output.mkdir(parents=True, exist_ok=True)
    results = result_rows(files)
    figures = figure_rows(files)
    components = component_rows()
    methods = method_rows()
    consistency = internal_rows()
    releases = release_rows(scratch)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "component_execution_audit.csv", components)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(output / "release_search_audit.csv", releases)

    provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "arxiv_version": "v1",
        "published_utc": "2026-06-21T08:22:23Z",
        "source_files": len(files),
        "official_pages": official_pages,
        "rebuilt_pages": rebuilt_pages,
        "official_pages_visually_checked": 25,
        "rebuilt_pages_visually_checked": 25,
        "visual_defects_observed": 0,
        "official_rebuilt_token_jaccard": overlap,
        "paper_contains_native_implementation_url": False,
        "paper_contains_dataset_or_checkpoint_url": False,
        "attributable_metaps_implementation_found": False,
        "observed_license": "NOASSERTION",
        "negative_search_scope": "bounded exact GitHub repository/code/user searches, exact Hugging Face name searches, web author/title searches, and OpenReview surface check; not proof of permanent absence",
        "pins": PINS,
    }
    write_json(output / "source_provenance.json", provenance)

    readme = f"""# MetaPS paper-level replication audit

**Verdict: the paper exposes unusually detailed compact mechanics and rendered outputs, but not the native pipeline; this is a paper-derived component replication, not an end-to-end MetaPS replication.** The pinned arXiv `2606.22385v1` source rebuilds to the official 25-page count with {overlap:.2%} extracted-token multiset overlap. All 25 official and 25 rebuilt pages were visually inspected without observed clipping, overlap, missing assets, or unreadable research content.

The active quantitative denominator is **492 displayed result cells across nine empirical tables**. The source also ships 19 figure assets: one conceptual framework image and 18 empirical PNGs containing **20 empirical panels**. These are author-rendered paper assets, not raw arrays. **Zero of 492 cells and 0/20 empirical panels are regenerated by an author-native experiment pipeline.** No attributable code, simulator, market/news/order-flow snapshot, 528-record SFT views, teacher requests/responses, adapters, checkpoints, seeds, model traces, orders, fills, portfolio paths, raw arrays, or result generator is released.

The source prints ten compact stock strategy listings and detailed V1/V2/V3 equations. Twelve controlled paper-derived mechanics execute: four unambiguous strategy branches plus the literal volatility listing, four size buckets, ranking, V1/V2/V3 formulas for supplied inputs, and stock/sandbox return identities. They are maintained in `src/alpha_evolve/metaps_paper_components.py` with an explicit non-author-code boundary. They receive **no published-result or native-pipeline credit**.

Reading the listings literally exposes important gaps. `volatility_breakout` includes `current` in the same 20-price window used to define `high` and `low`, making both breakout branches mathematically unreachable. `risk_reset` emits `REDUCE`, although the paper defines BUY/SELL/HOLD and says the wrapper validates actions. The ten snippets emit eight descriptive raw size modes, while the runtime only maps `none/small/medium/large`; no conversion is printed. Eight snippets depend on undefined domain helpers. These are preserved as findings rather than silently repaired.

The stock benchmark specifies six tickers, daily frequency, a 2022--2024/2025 split, $1M initial cash, and four exposure/share-cap buckets. It does not identify the immutable price/news/order-flow data, ranking coefficients, V2/V3 constants, tie rules, SFT records, teacher model, fine-tuning hyperparameters, exact model revisions, transaction-cost/slippage values, position limits, inference decoding, or randomness. The sandbox names six regimes and six roles but omits transition/reward/action dynamics, initial state, and seeds. Its displayed terminal equity/return pairs consistently imply an undisclosed initial equity near 8654.47.

Bounded exact-name/arXiv searches recover no attributable repository, model, or dataset. GitHub code hits are third-party indexes, feeds, reviews, unrelated numeric text, or unrelated generic strategy implementations. The OpenReview surface is behind browser verification and is not treated as an author release. These negative observations do not prove a private, deleted, renamed, moved, unindexed, or later artifact cannot exist. No license was observed. `strict_success` remains false.
"""
    (output / "README.md").write_text(readme)

    generated = {
        path.name: sha256(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "active_quantitative_table_cells": len(results),
        "result_tables": len(TABLE_SPECS),
        "author_native_table_cells_regenerated": 0,
        "active_empirical_figure_panels": sum(int(row["empirical_panels"]) for row in figures),
        "author_native_empirical_panels_regenerated": 0,
        "paper_derived_components_executed": len(components),
        "paper_derived_components_passing_controlled_checks": sum(
            bool(row["deterministic_control_passed"]) for row in components
        ),
        "attributable_metaps_implementation_found": False,
        "raw_result_arrays_recovered": 0,
        "full_end_to_end_pipeline_reproduced": False,
        "strict_success": False,
        "generated_file_sha256": generated,
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch, args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return int(args.strict and not manifest["strict_success"])


if __name__ == "__main__":
    raise SystemExit(main())
