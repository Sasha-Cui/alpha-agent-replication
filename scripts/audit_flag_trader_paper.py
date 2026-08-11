#!/usr/bin/env python3
"""Fail-closed paper-level audit of FLAG-Trader.

The ACL 2025 proceedings PDF is the result authority.  The arXiv v3 TeX is a
supporting machine-readable source.  No author-linked FLAG-Trader code, model,
trajectory, or result release was found.  The paper explicitly adopts its
baseline agents from InvestorBench, so the first author-linked InvestorBench
code release is audited separately and may receive baseline-cell credit only.
An unaffiliated GitHub implementation receives no native-source credit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


ACL_URL = "https://aclanthology.org/2025.findings-acl.716/"
ACL_PDF_URL = "https://aclanthology.org/2025.findings-acl.716.pdf"
ACL_PDF_SHA256 = "38d188a03105f07911d05c6fc14ba7cb2333939f3871f45a48f9cc541401d099"
ARXIV_URL = "https://arxiv.org/abs/2502.11433v3"
ARXIV_SOURCE_URL = "https://export.arxiv.org/e-print/2502.11433v3"
ARXIV_SOURCE_SHA256 = "b57ac81b8c705817e055ece553e5cbc1d0ef1f37b615e6cdbfa3eb896823eb23"
ARXIV_V3_SUBMITTED = "2025-02-19T03:40:56Z"

INVESTORBENCH_URL = "https://github.com/felis33/INVESTOR-BENCH"
INVESTORBENCH_COMMIT = "3509aeca668824cf2970e3950781d4d09f6c2adb"
INVESTORBENCH_TREE = "d7ba083da72c2023e9f0135c7db9e9d15841c231"
INVESTORBENCH_COMMIT_DATE = "2025-06-22T15:08:30-04:00"
INVESTORBENCH_ARCHIVE_SHA256 = "1675cf2cbe6039598d33c68a82b1a8cbe3abc8d59cda9eeca31ea2a1748e374b"
INVESTORBENCH_LICENSE_SHA256 = "6dc54f189d8ef19c4a74a7a489ed2de098a70e0764c0e105f60edd699ed10183"
INVESTORBENCH_DATA_SHA256 = {
    "MSFT": "f3af207052f2580ce5d03079a1ba17c4314a715ad55b365dc45e954dd15c5509",
    "JNJ": "ba557598af05ed9947a710cb328462e279d59be19b18907339805d503c45ca8c",
    "UVV": "2a09c02d67d7c69150f130306a1b924656a32ba85959a70017933a75472505d4",
    "HON": "ff90bea4e8ff35cb2752e24ad74d321eb94f06e72953acaaa48e02595e12850b",
    "BTC": "938962b2a1ed76387c82d260d51c9afff3de303284e923cd79695629775c7e38",
}

UNAFFILIATED_URL = "https://github.com/parkxlab/flag-trader"
UNAFFILIATED_COMMIT = "f43eebb6576e3ef8904ad838f7dcabc85f128713"
UNAFFILIATED_TREE = "fc214320582c2ac9d7e51dc9828993e5f18617d7"
UNAFFILIATED_COMMIT_DATE = "2025-04-18T13:32:00-05:00"
UNAFFILIATED_ARCHIVE_SHA256 = "868fc11a9dad5ca9a3c97837187b666d02d22573f6c7bd872d3d601a13c9685d"

GITHUB_SEARCH_SNAPSHOT_SHA256 = "0bbf2c09299701341ee98bf95261225d5c37aaecad5acfedbe14a9f1cb5e17f0"
THE_FINAI_REPOS_SNAPSHOT_SHA256 = "0832f1f1caabe241dc6daadc1cd045ed397fda9ca9c42a931b33d067effb4f1b"
AUDIT_DATE = "2026-08-11"

TABLE_ASSETS = (("MSFT", "JNJ", "UVV"), ("HON", "TSLA", "BTC"))
ALL_ASSETS = tuple(asset for group in TABLE_ASSETS for asset in group)
METRICS = ("CR_pct", "SR", "AV_pct", "MDD_pct")
HIGHER_IS_BETTER = {"CR_pct": True, "SR": True, "AV_pct": False, "MDD_pct": False}
MODELS = (
    "Buy & Hold",
    "Palmyra-Fin-70B",
    "GPT-o1-preview",
    "GPT-4",
    "GPT-4o",
    "Qwen2.5-72B-Instruct",
    "Llama-3.1-70B-Instruct",
    "DeepSeek-67B-Chat",
    "Yi-1.5-34B-Chat",
    "Qwen2.5-32B-Instruct",
    "DeepSeek-V2-Lite (15.7B)",
    "Yi-1.5-9B-Chat",
    "Llama-3.1-8B-Instruct",
    "Qwen-2.5-Instruct-7B",
    "SmolLM2-135M-Instruct",
)
FLAG_MODEL = "SmolLM2-135M-Instruct"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(source: Path, *args: str, binary: bool = False) -> Any:
    proc = subprocess.run(
        ["git", "-C", str(source), *args],
        check=True,
        capture_output=True,
        text=not binary,
    )
    return proc.stdout


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source_dir(paper_root: Path) -> Path:
    return paper_root / "source_v3"


def parse_paper_results(paper_root: Path) -> list[dict[str, Any]]:
    experiments = _source_dir(paper_root) / "sections/5_Experiments.tex"
    text = experiments.read_text(encoding="utf-8")
    blocks = re.findall(r"\\begin\{tabular\}.*?\n(.*?)\\end\{tabular\}", text, re.DOTALL)
    if len(blocks) < 2:
        raise ValueError("FLAG-Trader result tables were not found")
    records: list[dict[str, Any]] = []
    observed_model_orders: list[list[str]] = []
    for table_index, block in enumerate(blocks[:2], start=1):
        parsed_rows: list[tuple[str, list[str]]] = []
        for match in re.finditer(
            r"(?m)^\\textbf\{([^\n{}]+)\}\s*(.*?)\\\\",
            block,
            re.DOTALL,
        ):
            model = match.group(1).replace(r"\&", "&")
            values = re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", match.group(2))
            if len(values) == 12:
                parsed_rows.append((model, values))
        observed_model_orders.append([model for model, _values in parsed_rows])
        for model, values in parsed_rows:
            for asset_offset, asset in enumerate(TABLE_ASSETS[table_index - 1]):
                for metric_offset, metric in enumerate(METRICS):
                    records.append(
                        {
                            "paper_table": f"Table {table_index}",
                            "model": model,
                            "asset": asset,
                            "metric": metric,
                            "paper_value": values[asset_offset * 4 + metric_offset],
                        }
                    )
    if observed_model_orders != [list(MODELS), list(MODELS)]:
        raise ValueError("FLAG-Trader table model ordering drifted")
    if len(records) != 360:
        raise ValueError("FLAG-Trader result census must contain 360 cells")
    return records


def validate_final_pdf_tables(paper_root: Path, records: Sequence[Mapping[str, Any]]) -> None:
    pdf = paper_root / "flag_trader_acl.pdf"
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in records:
        grouped.setdefault((str(row["paper_table"]), str(row["model"])), []).append(row)
    for table, page in (("Table 1", 7), ("Table 2", 8)):
        proc = subprocess.run(
            ["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
        page_text = proc.stdout
        if "across six assets" not in page_text:
            raise ValueError(f"ACL final {table} caption did not identify six assets")
        for model in MODELS:
            row_pattern = re.compile(rf"^{re.escape(model)}(?:\s{{2,}}|\t)")
            matches = [
                line.strip()
                for line in page_text.splitlines()
                if row_pattern.search(line.strip())
            ]
            if len(matches) != 1:
                raise ValueError(f"ACL final {table} row lookup failed for {model}: {len(matches)}")
            tail = matches[0][len(model):]
            observed = re.findall(r"[-+]?\d+(?:\.\d+)?", tail)
            expected = [str(row["paper_value"]) for row in grouped[(table, model)]]
            if observed != expected:
                raise ValueError(f"ACL final {table} values differ from v3 source for {model}")


def parse_hyperparameters(paper_root: Path) -> list[dict[str, Any]]:
    appendix = (_source_dir(paper_root) / "sections/z_appendix.tex").read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^\\texttt\{([^}]+)\}\s*&\s*(.*?)\s*&\s*(.*?)\s*\\\\\s*$",
        re.MULTILINE,
    )
    for parameter, value, description in pattern.findall(appendix):
        rows.append(
            {
                "parameter": parameter.replace(r"\_", "_"),
                "paper_value_tex": value.strip(),
                "description": description.strip().replace(r"\(", "").replace(r"\)", ""),
                "released_flag_trader_config_value": "",
                "status": "paper_setting_only_no_flag_trader_config_released",
                "paper_result_credit": False,
            }
        )
    if len(rows) != 22:
        raise ValueError(f"expected 22 FLAG-Trader settings, found {len(rows)}")
    return rows


def extract_prompt_template(paper_root: Path) -> str:
    prompt_pdf = _source_dir(paper_root) / "figures/FinRL_Prompt.pdf"
    proc = subprocess.run(
        ["pdftotext", "-layout", str(prompt_pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    text = proc.stdout.replace("\f", "").strip() + "\n"
    required = (
        "Financial Stock Trading",
        "historical_prices",
        "account_status",
        "previous_decision_metrics",
        "minimize transaction costs",
        "Output Action",
    )
    if not all(value in text for value in required):
        raise ValueError("prompt figure transcription is incomplete")
    return text


def _archive_sha(source: Path, commit: str) -> str:
    data = run_git(source, "archive", "--format=tar", commit, binary=True)
    return bytes_sha256(data)


def validate_primary_inputs(
    paper_root: Path,
    investorbench_source: Path,
    unaffiliated_source: Path,
) -> dict[str, Any]:
    expected_files = {
        paper_root / "flag_trader_acl.pdf": ACL_PDF_SHA256,
        paper_root / "source_v3.tar": ARXIV_SOURCE_SHA256,
        paper_root / "github_search_flag_trader.json": GITHUB_SEARCH_SNAPSHOT_SHA256,
        paper_root / "the_finai_repos.json": THE_FINAI_REPOS_SNAPSHOT_SHA256,
        investorbench_source / "LICENSE": INVESTORBENCH_LICENSE_SHA256,
    }
    for path, expected in expected_files.items():
        if sha256(path) != expected:
            raise ValueError(f"pinned input hash mismatch: {path}")
    if run_git(investorbench_source, "rev-parse", "HEAD").strip() != INVESTORBENCH_COMMIT:
        raise ValueError("InvestorBench commit mismatch")
    if run_git(investorbench_source, "rev-parse", "HEAD^{tree}").strip() != INVESTORBENCH_TREE:
        raise ValueError("InvestorBench tree mismatch")
    if _archive_sha(investorbench_source, INVESTORBENCH_COMMIT) != INVESTORBENCH_ARCHIVE_SHA256:
        raise ValueError("InvestorBench archive mismatch")
    if run_git(unaffiliated_source, "rev-parse", "HEAD").strip() != UNAFFILIATED_COMMIT:
        raise ValueError("unaffiliated implementation commit mismatch")
    if run_git(unaffiliated_source, "rev-parse", "HEAD^{tree}").strip() != UNAFFILIATED_TREE:
        raise ValueError("unaffiliated implementation tree mismatch")
    if _archive_sha(unaffiliated_source, UNAFFILIATED_COMMIT) != UNAFFILIATED_ARCHIVE_SHA256:
        raise ValueError("unaffiliated implementation archive mismatch")
    for asset, expected in INVESTORBENCH_DATA_SHA256.items():
        if sha256(investorbench_source / f"data/{asset.lower()}.json") != expected:
            raise ValueError(f"InvestorBench {asset} data hash mismatch")
    search = json.loads((paper_root / "github_search_flag_trader.json").read_text(encoding="utf-8"))
    org = json.loads((paper_root / "the_finai_repos.json").read_text(encoding="utf-8"))
    if search.get("total_count") != 47 or len(org) != 25:
        raise ValueError("source-discovery snapshot counts drifted")
    if any(repo.get("name", "").lower() == "flag-trader" for repo in org):
        raise ValueError("The-FinAI snapshot unexpectedly contains FLAG-Trader")
    return {
        "github_exact_name_or_readme_search_results": 47,
        "the_finai_public_repositories": 25,
        "the_finai_flag_trader_repositories": 0,
    }


def source_inventory(source: Path) -> list[dict[str, Any]]:
    paths = run_git(source, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    rows: list[dict[str, Any]] = []
    for relative in paths:
        path = source / relative
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "python_source": path.suffix == ".py",
                "market_dataset": relative.startswith("data/") and path.suffix == ".json",
                "native_result_artifact": relative.startswith("results/"),
                "flag_trader_artifact": False,
            }
        )
    if len(rows) != 48 or sum(row["python_source"] for row in rows) != 23:
        raise ValueError("InvestorBench release inventory drifted")
    return rows


def compile_python_sources(source: Path) -> int:
    paths = run_git(source, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    python_paths = [source / relative for relative in paths if relative.endswith(".py")]
    for path in python_paths:
        compile(path.read_bytes(), str(path), "exec")
    return len(python_paths)


def compile_paper(paper_root: Path) -> dict[str, Any]:
    archive = paper_root / "source_v3.tar"
    with tempfile.TemporaryDirectory(prefix="flag_trader_paper_") as tmp:
        tmp_root = Path(tmp)
        with tarfile.open(archive, "r:gz") as handle:
            members = handle.getmembers()
            for member in members:
                parts = Path(member.name).parts
                if Path(member.name).is_absolute() or ".." in parts:
                    raise ValueError("unsafe arXiv source member")
            handle.extractall(tmp_root, filter="data")
        codes: list[int] = []
        for _ in range(2):
            proc = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                cwd=tmp_root,
                capture_output=True,
                text=True,
            )
            codes.append(proc.returncode)
            if proc.returncode:
                raise RuntimeError(proc.stdout[-4000:] + proc.stderr[-4000:])
        info = subprocess.run(
            ["pdfinfo", str(tmp_root / "main.pdf")],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        page_match = re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE)
        if not page_match or int(page_match.group(1)) != 14:
            raise ValueError("compiled arXiv v3 paper page count drifted")
        return {
            "exit_codes": codes,
            "pages": int(page_match.group(1)),
            "source_files": len([member for member in members if member.isfile()]),
            "paper_result_credit": False,
        }


def _sample_standard_deviation(values: Sequence[float]) -> float:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return variance**0.5


def _buy_hold_metrics(prices: Sequence[float], trading_days: int) -> dict[str, float]:
    returns = [math.log(right / left) for left, right in zip(prices, prices[1:])]
    standard_deviation = _sample_standard_deviation(returns)
    annualized_volatility = standard_deviation * math.sqrt(trading_days)
    cumulative_return = sum(returns)
    sharpe = (cumulative_return / (len(prices) / trading_days)) / annualized_volatility
    cumulative = [1.0]
    for value in returns:
        cumulative.append(cumulative[-1] * (1.0 + value))
    peak = cumulative[0]
    max_drawdown = 0.0
    for value in cumulative:
        peak = max(peak, value)
        max_drawdown = max(max_drawdown, (peak - value) / peak)
    return {
        "CR_pct": 100.0 * cumulative_return,
        "SR": sharpe,
        "AV_pct": 100.0 * annualized_volatility,
        "MDD_pct": 100.0 * max_drawdown,
    }


def buy_hold_reproduction(
    investorbench_source: Path,
    paper_results: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    paper_values = {
        (str(row["asset"]), str(row["metric"])): str(row["paper_value"])
        for row in paper_results
        if row["model"] == "Buy & Hold"
    }
    rows: list[dict[str, Any]] = []
    for asset in ("MSFT", "JNJ", "UVV", "HON", "BTC"):
        start, end = (
            ("2023-04-05", "2023-11-05")
            if asset == "BTC"
            else ("2020-10-01", "2021-05-06")
        )
        payload = json.loads(
            (investorbench_source / f"data/{asset.lower()}.json").read_text(encoding="utf-8")
        )
        prices = [
            float(contents["prices"])
            for date, contents in sorted(payload.items())
            if start <= date <= end and contents is not None and contents.get("prices") is not None
        ]
        expected_n = 215 if asset == "BTC" else 150
        if len(prices) != expected_n:
            raise ValueError(f"unexpected {asset} test observations: {len(prices)}")
        trading_days = 365 if asset == "BTC" else 252
        literal = _buy_hold_metrics(prices, trading_days)
        compatible = dict(literal)
        if asset == "BTC":
            returns = [math.log(right / left) for left, right in zip(prices, prices[1:])]
            annualized_volatility = _sample_standard_deviation(returns) * math.sqrt(365)
            compatible["SR"] = (sum(returns) / (len(prices) / 252)) / annualized_volatility
        for metric in METRICS:
            paper_text = paper_values[(asset, metric)]
            paper_value = float(paper_text)
            literal_value = literal[metric]
            compatible_value = compatible[metric]
            literal_match = round(literal_value, 3) == paper_value
            compatible_match = round(compatible_value, 3) == paper_value
            rows.append(
                {
                    "asset": asset,
                    "metric": metric,
                    "paper_value": paper_text,
                    "released_investorbench_literal_value": f"{literal_value:.9f}",
                    "released_investorbench_literal_match_at_paper_precision": literal_match,
                    "paper_compatible_value": f"{compatible_value:.9f}",
                    "paper_compatible_match_at_paper_precision": compatible_match,
                    "observations": len(prices),
                    "test_start": start,
                    "test_end": end,
                    "source_data_sha256": INVESTORBENCH_DATA_SHA256[asset],
                    "status": (
                        "author_linked_baseline_literal_match"
                        if literal_match
                        else (
                            "paper_match_requires_mixed_252_return_365_volatility_annualization"
                            if compatible_match and asset == "BTC" and metric == "SR"
                            else "author_linked_baseline_literal_conflict"
                        )
                    ),
                    "paper_result_credit": literal_match,
                    "native_flag_trader_result_credit": False,
                }
            )
    if len(rows) != 20 or sum(row["paper_result_credit"] for row in rows) != 6:
        raise ValueError("FLAG-Trader Buy & Hold reproduction count drifted")
    return rows


def result_conformance(
    paper_results: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    reproduced = {
        (row["asset"], row["metric"]): row
        for row in baseline_rows
        if row["paper_result_credit"]
    }
    rows: list[dict[str, Any]] = []
    for record in paper_results:
        key = (record["asset"], record["metric"])
        baseline = reproduced.get(key) if record["model"] == "Buy & Hold" else None
        rows.append(
            {
                **record,
                "reproduced_value": (
                    baseline["released_investorbench_literal_value"] if baseline else ""
                ),
                "reproduction_scope": "author_linked_investorbench_baseline" if baseline else "",
                "paper_result_credit": baseline is not None,
                "native_flag_trader_result_credit": False,
                "status": (
                    "reproduced_author_linked_baseline_cell"
                    if baseline
                    else "not_reproduced_no_exact_model_actions_trajectory_or_result_output"
                ),
            }
        )
    if sum(row["paper_result_credit"] for row in rows) != 6:
        raise ValueError("paper result credit must remain six baseline cells")
    return rows


def qualitative_claim_audit(paper_results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    values = {
        (str(row["model"]), str(row["asset"]), str(row["metric"])): float(row["paper_value"])
        for row in paper_results
    }
    flag_best = 0
    flag_best_primary = 0
    flag_best_risk = 0
    vs_buy_hold = Counter()
    for asset in ALL_ASSETS:
        for metric in METRICS:
            direction = 1.0 if HIGHER_IS_BETTER[metric] else -1.0
            flag_value = direction * values[(FLAG_MODEL, asset, metric)]
            best = max(direction * values[(model, asset, metric)] for model in MODELS)
            is_best = flag_value == best
            flag_best += int(is_best)
            flag_best_primary += int(is_best and metric in {"CR_pct", "SR"})
            flag_best_risk += int(is_best and metric in {"AV_pct", "MDD_pct"})
            buy_hold_value = direction * values[("Buy & Hold", asset, metric)]
            relation = "win" if flag_value > buy_hold_value else "tie" if flag_value == buy_hold_value else "loss"
            vs_buy_hold[relation] += 1
    primary_wins = sum(
        (
            (values[(FLAG_MODEL, asset, metric)] > values[("Buy & Hold", asset, metric)])
            if HIGHER_IS_BETTER[metric]
            else (values[(FLAG_MODEL, asset, metric)] < values[("Buy & Hold", asset, metric)])
        )
        for asset in ALL_ASSETS
        for metric in ("CR_pct", "SR")
    )
    rows = [
        {
            "claim": "FLAG-Trader consistently surpasses LLM-agentic baselines across metrics",
            "audit_measure": "best cells among all 15 rows",
            "observed": f"{flag_best}/24 overall; {flag_best_primary}/12 CR-or-SR; {flag_best_risk}/12 AV-or-MDD",
            "assessment": "overstated_not_best_on_17_of_24_metric_asset_cells",
            "paper_result_credit": False,
        },
        {
            "claim": "FLAG-Trader consistently outperforms Buy & Hold",
            "audit_measure": "strict cell comparisons",
            "observed": f"{vs_buy_hold['win']} wins, {vs_buy_hold['tie']} ties, {vs_buy_hold['loss']} losses",
            "assessment": "mostly_true_not_consistent_across_all_metrics",
            "paper_result_credit": False,
        },
        {
            "claim": "FLAG-Trader prioritizes CR and SR",
            "audit_measure": "primary metric comparisons with Buy & Hold",
            "observed": f"{primary_wins}/12 strict wins",
            "assessment": "one_primary_loss_uvv_sharpe",
            "paper_result_credit": False,
        },
        {
            "claim": "FLAG-Trader converges to a stable optimal policy",
            "audit_measure": "released convergence traces or uncertainty",
            "observed": "none",
            "assessment": "unsupported_no_trace_checkpoint_seed_or_statistical_test",
            "paper_result_credit": False,
        },
        {
            "claim": "best numbers are highlighted in red",
            "audit_measure": "ACL final Tables 1 and 2 plus v3 TeX",
            "observed": "zero red-highlight commands and no visible red values",
            "assessment": "paper_footnote_not_implemented",
            "paper_result_credit": False,
        },
    ]
    if flag_best != 7 or flag_best_primary != 7 or flag_best_risk != 0:
        raise ValueError("FLAG-Trader best-cell audit drifted")
    if vs_buy_hold != Counter({"win": 17, "loss": 5, "tie": 2}) or primary_wins != 11:
        raise ValueError("FLAG-Trader Buy & Hold comparison drifted")
    return rows


def method_specification_audit() -> list[dict[str, Any]]:
    entries = [
        ("asset_universe", "MSFT, JNJ, UVV, HON, TSLA, BTC", "six assets in final tables", "specified", "none"),
        ("stock_window", "warm-up 2020-07-01..09-30; test 2020-10-01..2021-05-06", "dates stated", "specified", "none"),
        ("btc_window", "warm-up 2023-02-11..04-04; test 2023-04-05..11-05", "dates stated", "specified", "none"),
        ("actions", "all-in Buy, all-out Sell, Hold", "three actions stated", "specified", "none"),
        ("backbone", "SmolLM2-135M-Instruct", "model family named", "partial", "major"),
        ("temperature", "0.6", "inference temperature stated", "specified", "none"),
        ("ppo_settings", "22 Table 3 settings", "paper values inventoried", "paper_only", "major"),
        ("hardware", "A6000/A100 tiers by model size", "GPU counts stated", "partial", "minor"),
        ("prompt_template", "Figure 3 vector prompt", "template text recovered", "partial", "major"),
        ("source_code", "none linked or released", "no author FLAG-Trader repository", "missing", "blocking"),
        ("trained_checkpoint", "none", "no model/adapter weights", "missing", "blocking"),
        ("optimizer_state", "none", "no checkpoint lineage", "missing", "blocking"),
        ("action_trajectories", "none", "no test decisions", "missing", "blocking"),
        ("equity_or_pnl_paths", "none", "only aggregate table cells", "missing", "blocking"),
        ("result_outputs", "none", "no raw results or plot arrays", "missing", "blocking"),
        ("random_seeds", "not stated", "no seed or seed count", "missing", "blocking"),
        ("replications", "median test trajectory across unspecified epochs", "number of epochs/runs absent", "missing", "blocking"),
        ("model_revision", "SmolLM2 family only", "no immutable model hash/revision", "missing", "blocking"),
        ("frozen_trainable_layers", "top layers trainable", "N and M omitted", "missing", "blocking"),
        ("head_architecture", "MLP policy/value heads", "dimensions, activations, initialization omitted", "missing", "blocking"),
        ("optimizer", "text says SGD; table says learning rate of optimizer", "optimizer type absent", "missing", "blocking"),
        ("data_vendor", "not stated", "no exact upstream source", "missing", "blocking"),
        ("data_snapshot", "not stated", "no retrieval time or raw FLAG snapshot", "missing", "blocking"),
        ("price_adjustment", "not stated", "released baseline adjusted prices conflict with four equity CR cells", "conflict", "blocking"),
        ("tsla_data", "evaluated in paper", "absent from author-linked InvestorBench release", "missing", "blocking"),
        ("news_macro_data", "state includes news sentiment or macro indicators", "sources, fields, timing and preprocessing absent", "missing", "blocking"),
        ("state_representation", "text says price/news; equation says Price/Vol/RSI; prompt shows history/account/memory", "three incompatible descriptions", "conflict", "blocking"),
        ("transaction_costs", "prompt instructs minimizing costs", "no cost parameter or transition deduction", "conflict", "blocking"),
        ("slippage_execution", "not stated", "no market-impact or execution convention", "missing", "blocking"),
        ("initial_cash", "not stated", "account initialization absent", "missing", "blocking"),
        ("risk_free_rate", "symbol r_f only", "value and frequency absent", "missing", "blocking"),
        ("reward_initialization", "SR_t minus SR_{t-1}", "sample SD undefined at first observation; SR_0 unspecified", "conflict", "blocking"),
        ("reward_units", "mean dollar PnL minus risk-free rate", "dimension/scale convention absent", "conflict", "major"),
        ("action_mask", "formula masks a not in global A", "does not encode state-dependent invalid Sell example", "conflict", "major"),
        ("test_model_selection", "median trajectory selected from test epochs", "test outcomes used for checkpoint/result selection", "conflict", "blocking"),
        ("btc_sharpe_annualization", "paper AV states 252", "paper SR matches 252 return over 365 volatility, not released evaluator", "conflict", "blocking"),
        ("kl_penalty", "kl_coef=0.05", "KL term absent from displayed total loss", "conflict", "major"),
        ("value_loss_clipping", "clip_vloss=True", "displayed value loss is unclipped", "conflict", "major"),
        ("replay_buffer_lifecycle", "Algorithm 2 appends B", "buffer clearing/rollout replacement not specified", "missing", "major"),
        ("batch_geometry", "num_steps=40, minibatch_size=32, num_envs=1", "remainder handling unspecified", "missing", "major"),
        ("update_geometry", "total_timesteps=13860 and rollout size=40", "346.5 rollouts; truncation convention absent", "missing", "major"),
        ("baseline_model_snapshots", "13 named models", "immutable revisions and API dates absent", "missing", "blocking"),
        ("software_environment", "vLLM named", "no FLAG dependency lock/container/source", "missing", "blocking"),
        ("uncertainty", "single displayed value per cell", "no seeds, intervals or dispersion", "missing", "blocking"),
        ("statistical_tests", "none", "no paired or multiple-comparison tests", "missing", "major"),
        ("red_best_highlights", "footnote says red", "no red commands/visible red values", "conflict", "minor"),
        ("arxiv_acl_caption", "v3 says seven stocks; ACL final says six assets", "final fixes caption but source revision differs", "conflict", "minor"),
        ("investorbench_release", "baseline framework explicitly cited", "post-preprint/pre-proceedings source has five of six data files", "partial", "major"),
    ]
    return [
        {
            "dimension": dimension,
            "paper_statement": paper,
            "available_evidence": evidence,
            "assessment": assessment,
            "severity": severity,
            "native_flag_trader_verified": False,
            "paper_result_credit": False,
        }
        for dimension, paper, evidence, assessment, severity in entries
    ]


def unaffiliated_candidate_audit(source: Path) -> list[dict[str, Any]]:
    checks = [
        ("provenance", "JunseongPark commit identity; no paper-author link", "unaffiliated_no_native_credit"),
        ("tracked_files", "18", "small_third_party_pilot"),
        ("python_files", "7/7 compile", "static_syntax_only"),
        ("license", "no license file", "reuse_rights_unresolved"),
        ("ppo", "no PPO ratio, clipping, GAE, critic, or value head", "paper_core_mechanism_absent"),
        ("training", "one episode; mean reward times mean token log probability", "not_paper_training_algorithm"),
        ("metrics", "AV and MDD hard-coded to zero", "not_paper_evaluator"),
        ("data", "MSFT only; snapshot extends to 2025", "not_paper_six_asset_snapshot"),
        ("native_results", "none shipped", "zero_paper_result_credit"),
    ]
    if len(run_git(source, "ls-tree", "-r", "--name-only", "HEAD").splitlines()) != 18:
        raise ValueError("unaffiliated candidate inventory drifted")
    return [
        {
            "check": check,
            "observed": observed,
            "assessment": assessment,
            "paper_author_linked": False,
            "native_flag_trader_source_credit": False,
            "paper_result_credit": False,
        }
        for check, observed, assessment in checks
    ]


def build_readme(manifest: Mapping[str, Any]) -> str:
    return f"""# FLAG-Trader paper-level replication audit

The ACL 2025 proceedings PDF is the result authority. The arXiv v3 source is
machine-readable supporting evidence and compiles to {manifest['paper_compile_pages']} pages. Its two
result tables contain {manifest['paper_table_cells_total']} displayed numeric cells.

## Honest outcome

- **FLAG-Trader itself: 0/{manifest['paper_table_cells_total']} cells reproduced.** No author-linked
  FLAG-Trader code, checkpoint, configuration, seed, action trajectory, PnL/equity
  path, or raw result output was found.
- **Paper baseline only: {manifest['paper_table_cells_reproduced']} / {manifest['paper_table_cells_total']} cells reproduced.** The paper says its
  13 baseline agents come from InvestorBench. The first author-linked
  InvestorBench release supplies five of the six datasets and an evaluator. A
  literal pinned execution matches four equity Buy-and-Hold MDD cells plus BTC
  AV and MDD. The BTC CR differs in the last displayed digit. This is baseline
  evidence, not FLAG-Trader evidence.
- The BTC Sharpe cell matches only when return annualization uses 252 days while
  volatility uses 365; the released evaluator uses one calendar consistently.
- FLAG-Trader is best in only 7/24 metric-by-asset comparisons (7/12 CR/SR and
  0/12 risk cells). Against Buy-and-Hold it has 17 wins, 2 ties, and 5 losses.

## Why this is not a faithful replication

The paper specifies useful high-level architecture and 22 settings, but the
executable procedure is not identified. Blocking omissions include the exact
data snapshot/vendor, price adjustment, TSLA data, news/macro inputs, model
revision, trainable-layer split, optimizer, initialization, seeds, run count,
checkpoint selection, action paths, and result files. The displayed state,
transaction-cost instruction, action mask, reward initialization, BTC
annualization, KL penalty, and value clipping also contain source-level
conflicts documented in `method_specification_audit.csv`.

The exact-name `parkxlab/flag-trader` repository is unaffiliated and does not
implement the paper's PPO/value-network method; it receives no native-source or
result credit.

## Evidence boundary

Compiling TeX, parsing the vector prompt, compiling related Python files, and
executing InvestorBench's Buy-and-Hold formula establish document/static or
baseline evidence only. They do not reconstruct the unavailable FLAG-Trader
training or test pipeline. The work remains `paper_only_underspecified`.
"""


def audit(
    paper_root: Path,
    investorbench_source: Path,
    unaffiliated_source: Path,
    output: Path,
) -> dict[str, Any]:
    discovery = validate_primary_inputs(paper_root, investorbench_source, unaffiliated_source)
    paper_results = parse_paper_results(paper_root)
    validate_final_pdf_tables(paper_root, paper_results)
    hyperparameters = parse_hyperparameters(paper_root)
    prompt = extract_prompt_template(paper_root)
    baseline = buy_hold_reproduction(investorbench_source, paper_results)
    conformance = result_conformance(paper_results, baseline)
    claims = qualitative_claim_audit(paper_results)
    methods = method_specification_audit()
    inventory = source_inventory(investorbench_source)
    candidate = unaffiliated_candidate_audit(unaffiliated_source)
    paper_compile = compile_paper(paper_root)
    investor_python = compile_python_sources(investorbench_source)
    unaffiliated_python = compile_python_sources(unaffiliated_source)

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "paper_table_result_conformance.csv", conformance)
    write_csv(output / "buy_hold_baseline_reproduction.csv", baseline)
    write_csv(output / "paper_hyperparameters.csv", hyperparameters)
    write_csv(output / "qualitative_claim_audit.csv", claims)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "investorbench_source_inventory.csv", inventory)
    write_csv(output / "unaffiliated_candidate_audit.csv", candidate)
    (output / "paper_prompt_template.txt").write_text(prompt, encoding="utf-8")

    native_execution = {
        "flag_trader_native_execution_attempted": False,
        "reason": "no author-linked FLAG-Trader implementation, checkpoint, config, or trajectory released",
        "investorbench_baseline_formula_executed": True,
        "investorbench_baseline_cells_with_paper_result_credit": 6,
        "investorbench_python_files_compiled": investor_python,
        "unaffiliated_candidate_executed_as_flag_trader": False,
        "unaffiliated_candidate_python_files_compiled": unaffiliated_python,
        "unaffiliated_candidate_credit": False,
        "paper_latex_compilation": paper_compile,
        "acl_final_result_tables_crosschecked_against_v3_source": True,
    }
    write_json(output / "native_execution.json", native_execution)

    source_provenance = {
        "result_authority": {
            "url": ACL_PDF_URL,
            "sha256": ACL_PDF_SHA256,
            "pages": 14,
        },
        "supporting_arxiv_source": {
            "url": ARXIV_SOURCE_URL,
            "version": 3,
            "submitted": ARXIV_V3_SUBMITTED,
            "sha256": ARXIV_SOURCE_SHA256,
        },
        "author_linked_baseline_release": {
            "url": INVESTORBENCH_URL,
            "commit": INVESTORBENCH_COMMIT,
            "tree": INVESTORBENCH_TREE,
            "commit_date": INVESTORBENCH_COMMIT_DATE,
            "archive_sha256": INVESTORBENCH_ARCHIVE_SHA256,
            "relationship": "paper_explicitly_adopts_InvestorBench_baselines_not_FLAG_Trader_source",
        },
        "unaffiliated_candidate": {
            "url": UNAFFILIATED_URL,
            "commit": UNAFFILIATED_COMMIT,
            "tree": UNAFFILIATED_TREE,
            "commit_date": UNAFFILIATED_COMMIT_DATE,
            "archive_sha256": UNAFFILIATED_ARCHIVE_SHA256,
            "paper_credit": False,
        },
        "source_discovery": discovery,
    }
    write_json(output / "source_provenance.json", source_provenance)

    assessment_counts = Counter(row["assessment"] for row in methods)
    severity_counts = Counter(row["severity"] for row in methods)
    manifest: dict[str, Any] = {
        "audit_date": AUDIT_DATE,
        "paper": "FLAG-TRADER: Fusion LLM-Agent with Gradient-based Reinforcement Learning for Financial Trading",
        "acl_url": ACL_URL,
        "arxiv_url": ARXIV_URL,
        "overall_status": (
            "partial_6_of_360_author_linked_buy_hold_baseline_cells_reproduced_"
            "zero_flag_trader_native_results"
        ),
        "full_paper_reproduced": False,
        "paper_evidence_route": "paper_only_underspecified",
        "paper_table_cells_total": len(conformance),
        "paper_table_cells_reproduced": sum(row["paper_result_credit"] for row in conformance),
        "flag_trader_native_result_cells_reproduced": sum(
            row["native_flag_trader_result_credit"] for row in conformance
        ),
        "paper_compile_pages": paper_compile["pages"],
        "paper_hyperparameter_settings": len(hyperparameters),
        "paper_prompt_template_recovered": True,
        "investorbench_release_tracked_files": len(inventory),
        "investorbench_release_python_files": investor_python,
        "investorbench_release_native_result_artifacts": sum(
            row["native_result_artifact"] for row in inventory
        ),
        "buy_hold_cells_checked_against_released_baseline": len(baseline),
        "buy_hold_cells_literal_matches": sum(row["paper_result_credit"] for row in baseline),
        "buy_hold_cells_paper_compatible_matches": sum(
            row["paper_compatible_match_at_paper_precision"] for row in baseline
        ),
        "flag_trader_best_metric_asset_cells": 7,
        "flag_trader_best_primary_cells": 7,
        "flag_trader_best_risk_cells": 0,
        "flag_trader_vs_buy_hold": {"wins": 17, "ties": 2, "losses": 5},
        "method_specification_dimensions": len(methods),
        "method_assessment_counts": dict(sorted(assessment_counts.items())),
        "method_severity_counts": dict(sorted(severity_counts.items())),
        "official_flag_trader_source_released": False,
        "official_flag_trader_checkpoint_released": False,
        "official_flag_trader_trajectory_released": False,
        "unaffiliated_candidate_paper_credit": False,
        "native_execution": native_execution,
        "input_sha256": {
            "acl_final_pdf": ACL_PDF_SHA256,
            "arxiv_v3_source": ARXIV_SOURCE_SHA256,
            "investorbench_archive": INVESTORBENCH_ARCHIVE_SHA256,
            "unaffiliated_archive": UNAFFILIATED_ARCHIVE_SHA256,
        },
    }
    readme = build_readme(manifest)
    (output / "README.md").write_text(readme, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--paper-root",
        type=Path,
        default=Path("/nfs/roberts/scratch/pi_btk22/zc362/flag_trader_paper"),
    )
    parser.add_argument(
        "--investorbench-source",
        type=Path,
        default=Path(
            "/nfs/roberts/scratch/pi_btk22/zc362/flag_trader_paper/investorbench_source"
        ),
    )
    parser.add_argument(
        "--unaffiliated-source",
        type=Path,
        default=Path(
            "/nfs/roberts/scratch/pi_btk22/zc362/flag_trader_paper/candidate_parkxlab"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("paper_runs/paper_replication_audits/flag_trader"),
    )
    args = parser.parse_args()
    manifest = audit(
        args.paper_root,
        args.investorbench_source,
        args.unaffiliated_source,
        args.output,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
