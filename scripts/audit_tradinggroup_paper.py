#!/usr/bin/env python3
"""Build a fail-closed paper/source audit for TradingGroup.

The paper publishes a substantial method description and uses the public
FINSABER data/framework, but does not release the TradingGroup implementation,
runtime prompts, trajectories, or Qwen3-Trader checkpoint.  This audit gives
document, data, formula-component, and source-adjacent baseline credit while
keeping native TradingGroup result reproduction at zero.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import pickle
import re
import subprocess
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path(
    "/nfs/roberts/scratch/pi_btk22/zc362/trading_group_audit"
)
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/tradinggroup"
WORK_ID = "CensusArxiv250817565"
SYSTEM_ID = "SYS-TRADING-GROUP"
ARXIV_ID = "2508.17565"
FINSABER_COMMIT = "0e794285e48fd71a4d9579ef022ee726b1e36f8a"
FINSABER_TREE = "ad47d1a27e39f359218d05e971d0599e09a489a1"
FINSABER_TWO_YEAR_DEFAULT_COMMIT = "1f3f83f4804f731d96fa95e4120cf7bffc93cc3c"
FINSABER_THREE_YEAR_RESTORE_COMMIT = "55e5c7532dcc94a4363efad3885914f117125124"
FINSABER_TRAINING_OVERRIDE_COMMIT = "5c4cbcff4b9f4b7e41fdf1deeb93371024f8cbab"

PINS = {
    "raw/api.xml": "730eb6cb45ed0b415baa486cc01c0df63d0847a9d8a6e8b36f9a067bf8834461",
    "raw/abs.html": "9db80cd480ac825de02476e83b1e72c2eb940b963e52997a612c39b8560e0432",
    "raw/abs-repeat.html": "9db80cd480ac825de02476e83b1e72c2eb940b963e52997a612c39b8560e0432",
    "raw/paper.pdf": "bcfae05f9032cad2eef9d37121eff4ed5da9ce0f80734d2e39f1abab58a040bc",
    "raw/paper-repeat.pdf": "bcfae05f9032cad2eef9d37121eff4ed5da9ce0f80734d2e39f1abab58a040bc",
    "raw/source.tar": "332a86d01cde473f020115b7518f5f4ba0d61d9cf0268c5376aee8d7af89619a",
    "raw/source-repeat.tar": "332a86d01cde473f020115b7518f5f4ba0d61d9cf0268c5376aee8d7af89619a",
    "source/arxiv.tex": "1f3155d3aad4d1307e019dec3726484bc8da458daa5e3ace0d7e2e9205123164",
    "rebuilt.pdf": "f31c5afec96f1501eb3d71b1bd4355e9feff2b75f9e27471bb3fb7aad11fc06b",
    "finsaber_selective_data.pkl": "f8bfd5b3b68796b82d1857c06e1bb39991b8a973dc6d41a7ec63ff29a4e2df6f",
    "finsaber_price_only.csv": "f67e3972dceefbbdf6c17b84b30957a7b83518401955fff8ae0bc4ae206fa83f",
    "finsaber_selective_data.safe-audit.json": "12daba1f8869463140b24846481779f82321fc9c6dbea00809d75ad1704ac1cf",
    "finsaber-test-window-summary.json": "5c4aa3986293c3454634ef5fc78a5cdb834a024cf39efea387fc139dcc141851",
    "finsaber-execution-pinned.json": "63a2bf3922c7d063815e0790c7dc4ccd70f91481dcd64ac25994b7b948548f86",
    "finsaber-execution-two-year-models.json": "bd387429c16d9d50dd40b87af9146e91f95bbe660cca46f901ef59207aa8133a",
    "finsaber-import-adapter.patch": "d35df9a3a948c76dcf272dd68c396679e613ba4e4d57323e5bbfe1c13961abd9",
    "discovery/github_code_title_arxiv.json": "66dbe8168d3d815eb63df27ad987bc092ced800e728ee06f6dbec5715963b09a",
    "discovery/github_code_checkpoint.json": "dc28063e8a4942ab20b81767b9645df891a70daee48927b440dfaad138c765e7",
    "discovery/github_repo_title.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/repo_tradinggroup.json": "f94f50429d26b94c93623d6b70032f635dc95e6425a57748e8b00ca2768c4c51",
    "discovery/repo_checkpoint.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/hf_checkpoint.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/hf_dataset.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/unattributed_collision_repo.json": "0faad050121435986d57815fdfc39b585959180ccf927c444fc19345542b5845",
    "primary_external/finsaber_repo_api.json": "227ae3363a3cd2ded7acab76fe4e3f02066a358db20b35461288292d51725fd3",
}

TICKERS = ("TSLA", "NFLX", "AMZN", "MSFT", "COIN")
METRICS = ("SPR", "CR", "MDD", "AV")
TABLE1_STRATEGIES = (
    "Buy and Hold", "SMA Cross", "WMA Cross", "ATR Band",
    "Bollinger Bands", "Turn of The Month", "ARIMA", "XGBoost",
    "A2C", "DDPG", "PPO", "SAC", "TD3", "FinMem", "FinAgent",
    "TradingGroup",
)
SOURCE_CSV_PATHS = {
    "Buy and Hold": "BuyAndHoldStrategy",
    "SMA Cross": "SMACrossStrategy",
    "WMA Cross": "WMAStrategy",
    "ATR Band": "ATRBandStrategy",
    "Bollinger Bands": "BollingerBandsStrategy",
    "Turn of The Month": "TurnOfTheMonthStrategy",
    "ARIMA": "ARIMAPredictorStrategy",
    "XGBoost": "XGBoostPredictorStrategy",
    "FinAgent": "FinAgentStrategy",
}
EXECUTION_CLASS_TO_PAPER = {value: key for key, value in SOURCE_CSV_PATHS.items()}
TABLE2_STRATEGIES = (
    "TradingGroup (Qwen3-8B)",
    "TradingGroup (Qwen3-Trader-8B-PEFT)",
)
TABLE3_CONFIGS = (
    "all_removed", "RM+PC", "SR+RE+PC_no_RM", "all_enabled",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    records = list(rows)
    if not records:
        raise ValueError(f"refusing to write empty ledger: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(records[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(records)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def git_output(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")

    repo = scratch / "finsaber"
    if not repo.is_dir():
        raise FileNotFoundError(repo)
    if git_output(repo, "rev-parse", f"{FINSABER_COMMIT}^{{commit}}").strip() != FINSABER_COMMIT:
        raise ValueError("pinned FINSABER commit is unavailable")
    if git_output(repo, "rev-parse", f"{FINSABER_COMMIT}^{{tree}}").strip() != FINSABER_TREE:
        raise ValueError("pinned FINSABER tree changed")

    for commit in (
        FINSABER_TWO_YEAR_DEFAULT_COMMIT,
        FINSABER_THREE_YEAR_RESTORE_COMMIT,
        FINSABER_TRAINING_OVERRIDE_COMMIT,
    ):
        if git_output(repo, "rev-parse", f"{commit}^{{commit}}").strip() != commit:
            raise ValueError(f"historical FINSABER commit is unavailable: {commit}")
    model_paths = (
        "backtest/strategy/timing/arima_predictor.py",
        "backtest/strategy/timing/xgboost_predictor.py",
    )
    for model_path in model_paths:
        two_year_source = git_output(
            repo, "show", f"{FINSABER_TWO_YEAR_DEFAULT_COMMIT}:{model_path}"
        )
        three_year_source = git_output(
            repo, "show", f"{FINSABER_THREE_YEAR_RESTORE_COMMIT}:{model_path}"
        )
        if '("train_period", 252 * 2)' not in two_year_source:
            raise ValueError(
                f"two-year FINSABER model default is absent at pinned commit: {model_path}"
            )
        if '("train_period", 252 * 3)' not in three_year_source:
            raise ValueError(
                f"three-year FINSABER model default is absent at pinned commit: {model_path}"
            )
    override_source = git_output(
        repo, "show", f"{FINSABER_TRAINING_OVERRIDE_COMMIT}:backtest/finsaber_bt.py"
    )
    if "test_config.training_years * 252" not in override_source:
        raise ValueError("FINSABER training-year override is not present at its pinned commit")

    with tarfile.open(scratch / "raw/source.tar") as archive:
        members = [
            PurePosixPath(member.name).name
            for member in archive.getmembers()
            if member.isfile()
        ]
    if sorted(members) != sorted(
        [
            "00README.json", "arxiv.bbl", "arxiv.tex",
            "ComparisonOfLLMs.pdf", "DataPipelinedrawio.pdf", "overalldrawio.pdf",
        ]
    ):
        raise ValueError(f"unexpected official source members: {members}")
    return {"official_source_members": sorted(members), "finsaber_repo": repo}


def active_table(tex: str, caption: str, after: int = 0) -> str:
    position = tex.find("\\caption{" + caption, after)
    if position < 0:
        raise ValueError(f"caption not found: {caption}")
    start = tex.rfind("\\begin{table}", 0, position)
    end = tex.index("\\end{table}", position)
    return tex[start:end]


def clean_result(field: str) -> tuple[str, float | None, int | None]:
    value = re.sub(r"\\color\[HTML\]\{[0-9A-Fa-f]+\}", "", field)
    value = value.replace("\\textbf", "").replace("{", "").replace("}", "")
    value = value.split(r"\\", 1)[0].strip()
    if value in {"—", "-", "--"}:
        return value, None, None
    match = re.match(r"([-+]?\d+(?:\.\d+)?)", value)
    if not match:
        raise ValueError(f"cannot parse result field: {field!r} -> {value!r}")
    rendered = match.group(1)
    decimals = len(rendered.partition(".")[2]) if "." in rendered else 0
    return rendered, float(rendered), decimals


def table1_rows(tex: str) -> tuple[list[dict[str, Any]], int]:
    section = active_table(tex, "Quantitative Backtesting", after=50_000)
    parsed: list[tuple[str, list[tuple[str, float | None, int | None]]]] = []
    for line in section.splitlines():
        if "&" not in line or line.lstrip().startswith("%"):
            continue
        fields = [part.strip() for part in line.split("&")]
        if len(fields) < 5 or "SPR" in fields[-4]:
            continue
        strategy = next(
            (name for name in TABLE1_STRATEGIES if name in fields[-5]), None
        )
        if strategy:
            parsed.append((strategy, [clean_result(field) for field in fields[-4:]]))
    if len(parsed) != 80:
        raise ValueError(f"expected 80 Table 1 rows, found {len(parsed)}")

    output: list[dict[str, Any]] = []
    dash_count = 0
    for group_index, ticker in enumerate(TICKERS):
        group = parsed[group_index * 16:(group_index + 1) * 16]
        if [row[0] for row in group] != list(TABLE1_STRATEGIES):
            raise ValueError(f"unexpected Table 1 strategy order for {ticker}")
        for strategy, values in group:
            for metric, (rendered, numeric, decimals) in zip(METRICS, values):
                if numeric is None:
                    dash_count += 1
                    continue
                output.append(
                    {
                        "table": "Table 1",
                        "ticker": ticker,
                        "result_group": strategy,
                        "metric": metric,
                        "rendered_value": rendered,
                        "numeric_value": numeric,
                        "decimal_places": decimals,
                        "native_tradinggroup_result": strategy == "TradingGroup",
                        "duplicate_kind": "none",
                        "duplicate_of": "",
                    }
                )
    return output, dash_count


def table2_rows(tex: str) -> list[dict[str, Any]]:
    section = active_table(
        tex, "Performance between Qwen3-Trader-8B-PEFT", after=112_000
    )
    parsed = []
    for line in section.splitlines():
        if "{TradingGroup (Qwen3" not in line or line.lstrip().startswith("%"):
            continue
        fields = [part.strip() for part in line.split("&")]
        strategy = next(name for name in TABLE2_STRATEGIES if name in fields[-5])
        parsed.append((strategy, [clean_result(field) for field in fields[-4:]]))
    if len(parsed) != 10:
        raise ValueError(f"expected 10 Table 2 rows, found {len(parsed)}")
    output = []
    for group_index, ticker in enumerate(TICKERS):
        group = parsed[group_index * 2:(group_index + 1) * 2]
        if [row[0] for row in group] != list(TABLE2_STRATEGIES):
            raise ValueError(f"unexpected Table 2 order for {ticker}")
        for strategy, values in group:
            for metric, (rendered, numeric, decimals) in zip(METRICS, values):
                if numeric is None:
                    raise ValueError("Table 2 unexpectedly contains a dash")
                output.append(
                    {
                        "table": "Table 2",
                        "ticker": ticker,
                        "result_group": strategy,
                        "metric": metric,
                        "rendered_value": rendered,
                        "numeric_value": numeric,
                        "decimal_places": decimals,
                        "native_tradinggroup_result": True,
                        "duplicate_kind": "none",
                        "duplicate_of": "",
                    }
                )
    return output


def table3_rows(tex: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    section = active_table(
        tex, "Ablation results across different module combinations", after=120_000
    )
    parsed = []
    for line in section.splitlines():
        if (
            not line.lstrip().startswith("\\multicolumn")
            or "&" not in line
            or "SPR" in line
            or line.lstrip().startswith("%")
        ):
            continue
        values = []
        annotations = []
        for field in line.split("&")[-4:]:
            values.append(clean_result(field))
            cleaned = re.sub(r"\\color\[HTML\]\{[0-9A-Fa-f]+\}", "", field)
            cleaned = cleaned.replace("{", "").replace("}", "")
            numbers = re.findall(r"(?<![A-Za-z])([-+]?\d+(?:\.\d+)?)", cleaned)
            annotations.append(numbers[1] if len(numbers) > 1 else "")
        parsed.append((values, annotations))
    if len(parsed) != 20:
        raise ValueError(f"expected 20 Table 3 rows, found {len(parsed)}")

    output = []
    annotation_audit = []
    for group_index, ticker in enumerate(TICKERS):
        group = parsed[group_index * 4:(group_index + 1) * 4]
        base_values = group[0][0]
        for config, (values, annotations) in zip(TABLE3_CONFIGS, group):
            for metric, (rendered, numeric, decimals), annotation, base in zip(
                METRICS, values, annotations, base_values
            ):
                if numeric is None or base[1] is None:
                    raise ValueError("Table 3 unexpectedly contains a dash")
                duplicate = config == "all_enabled"
                output.append(
                    {
                        "table": "Table 3",
                        "ticker": ticker,
                        "result_group": config,
                        "metric": metric,
                        "rendered_value": rendered,
                        "numeric_value": numeric,
                        "decimal_places": decimals,
                        "native_tradinggroup_result": True,
                        "duplicate_kind": (
                            "same_value_as_table1_tradinggroup" if duplicate else "none"
                        ),
                        "duplicate_of": (
                            f"Table 1|{ticker}|TradingGroup|{metric}" if duplicate else ""
                        ),
                    }
                )
                if annotation:
                    percent = (numeric - base[1]) / abs(base[1]) * 100
                    annotation_decimals = (
                        len(annotation.partition(".")[2]) if "." in annotation else 0
                    )
                    expected = round(percent, annotation_decimals)
                    annotation_audit.append(
                        {
                            "ticker": ticker,
                            "configuration": config,
                            "metric": metric,
                            "base_value": base[1],
                            "configuration_value": numeric,
                            "computed_percent": f"{percent:.9f}",
                            "printed_annotation": annotation,
                            "expected_at_printed_precision": expected,
                            "status": (
                                "passes_displayed_arithmetic"
                                if float(annotation) == expected
                                else "annotation_rounding_mismatch"
                            ),
                        }
                    )
    return output, annotation_audit


def source_csv_values(repo: Path) -> dict[tuple[str, str, str], float]:
    output: dict[tuple[str, str, str], float] = {}
    for strategy, directory in SOURCE_CSV_PATHS.items():
        relative = (
            "backtest/output/cherry_pick_both_finmem/"
            f"{directory}/results.csv"
        )
        text = git_output(repo, "show", f"{FINSABER_COMMIT}:{relative}")
        for row in csv.DictReader(text.splitlines()):
            if row["Period"] != "2022-10-06_2023-04-10":
                continue
            mapping = {
                "SPR": row["sharpe_ratio"],
                "CR": row["total_return (%)"],
                "MDD": row["max_drawdown"],
                "AV": row["annual_volatility (%)"],
            }
            for metric, value in mapping.items():
                output[(row["ticker"], strategy, metric)] = float(value)
    return output


def values_from_execution_document(
    document: Mapping[str, Any],
) -> dict[tuple[str, str, str], float]:
    output: dict[tuple[str, str, str], float] = {}
    for class_name, ticker_results in document["results"].items():
        strategy = EXECUTION_CLASS_TO_PAPER[class_name]
        for ticker, metrics in ticker_results.items():
            mapping = {
                "SPR": metrics["sharpe_ratio"],
                "CR": metrics["total_return"] * 100,
                "MDD": -metrics["max_drawdown"],
                "AV": metrics["annual_volatility"] * 100,
            }
            for metric, value in mapping.items():
                output[(ticker, strategy, metric)] = float(value)
    return output


def execution_values(
    scratch: Path,
) -> tuple[
    dict[tuple[str, str, str], float],
    dict[tuple[str, str, str], float],
    dict[str, Any],
]:
    default_document = json.loads(
        (scratch / "finsaber-execution-pinned.json").read_text(encoding="utf-8")
    )
    two_year_document = json.loads(
        (scratch / "finsaber-execution-two-year-models.json").read_text(
            encoding="utf-8"
        )
    )
    if two_year_document["inputs"]["config"].get("training_years") != 2:
        raise ValueError("paper-lineage model execution did not record two training years")
    if set(two_year_document["results"]) != {
        "ARIMAPredictorStrategy", "XGBoostPredictorStrategy",
    }:
        raise ValueError("paper-lineage execution must contain exactly ARIMA and XGBoost")

    default = values_from_execution_document(default_document)
    paper_lineage = dict(default)
    paper_lineage.update(values_from_execution_document(two_year_document))
    return paper_lineage, default, {
        "pinned_default_three_year": default_document,
        "paper_lineage_two_year_models": two_year_document,
    }


def within_display_precision(value: float, paper: Mapping[str, Any]) -> bool:
    tolerance = 0.5 * 10 ** -int(paper["decimal_places"]) + 1e-12
    return abs(value - float(paper["numeric_value"])) <= tolerance


def result_and_execution_ledgers(
    paper_rows: list[dict[str, Any]], repo: Path, scratch: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict]:
    source = source_csv_values(repo)
    execution, default_execution, execution_documents = execution_values(scratch)
    paper_by_key = {
        (row["ticker"], row["result_group"], row["metric"]): row
        for row in paper_rows if row["table"] == "Table 1"
    }

    published = []
    for row in paper_rows:
        key = (row["ticker"], row["result_group"], row["metric"])
        fresh = execution.get(key)
        matches = fresh is not None and within_display_precision(fresh, row)
        published.append(
            {
                **row,
                "baseline_framework_executed": fresh is not None,
                "baseline_execution_matches_paper": matches,
                "native_pipeline_executed": False,
                "native_result_regenerated": False,
                "paper_result_credit": matches,
                "credit_class": (
                    "source_adjacent_baseline_execution"
                    if matches else "none"
                ),
            }
        )

    execution_ledger = []
    for key in sorted(execution):
        ticker, strategy, metric = key
        paper = paper_by_key[key]
        source_value = source.get(key)
        default_value = default_execution.get(key)
        model_lineage = strategy in {"ARIMA", "XGBoost"}
        execution_ledger.append(
            {
                "ticker": ticker,
                "strategy": strategy,
                "metric": metric,
                "paper_rendered_value": paper["rendered_value"],
                "paper_numeric_value": paper["numeric_value"],
                "fresh_execution_value": f"{execution[key]:.12g}",
                "fresh_execution_matches_paper": within_display_precision(
                    execution[key], paper
                ),
                "execution_configuration": (
                    "historical_two_year_model_window"
                    if model_lineage else "pinned_default"
                ),
                "pinned_default_execution_value": (
                    "" if default_value is None else f"{default_value:.12g}"
                ),
                "pinned_default_execution_matches_paper": (
                    False if default_value is None
                    else within_display_precision(default_value, paper)
                ),
                "historical_source_csv_value": (
                    "" if source_value is None else source_value
                ),
                "historical_source_csv_matches_paper": (
                    False if source_value is None else within_display_precision(source_value, paper)
                ),
                "fresh_execution_matches_source_csv_at_3dp": (
                    False if source_value is None else abs(execution[key] - source_value) <= 0.0005 + 1e-12
                ),
                "native_tradinggroup_credit": False,
            }
        )

    source_ledger = []
    for key in sorted(source):
        ticker, strategy, metric = key
        paper = paper_by_key.get(key)
        if paper is None:
            status = "paper_dash_or_no_numeric_cell"
            paper_value: str | float = ""
            paper_rendered = "—"
        else:
            status = (
                "matches_paper_at_display_precision"
                if within_display_precision(source[key], paper)
                else "differs_from_paper"
            )
            paper_value = paper["numeric_value"]
            paper_rendered = paper["rendered_value"]
        source_ledger.append(
            {
                "ticker": ticker,
                "strategy": strategy,
                "metric": metric,
                "paper_rendered_value": paper_rendered,
                "paper_numeric_value": paper_value,
                "historical_source_csv_value": source[key],
                "status": status,
                "native_tradinggroup_credit": False,
            }
        )
    return published, execution_ledger, source_ledger, execution_documents


class RestrictedDataUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:
        if (module, name) == ("datetime", "date"):
            return dt.date
        raise pickle.UnpicklingError(f"forbidden global: {module}.{name}")

    def persistent_load(self, pid: object) -> Any:
        raise pickle.UnpicklingError(f"persistent ID forbidden: {pid!r}")


def has_payload(value: Any) -> bool:
    if value is None:
        return False
    return len(value) > 0 if isinstance(value, (str, bytes, list, tuple, dict)) else True


def test_dataset_audit(scratch: Path) -> list[dict[str, Any]]:
    payload = (scratch / "finsaber_selective_data.pkl").read_bytes()
    root = RestrictedDataUnpickler(io.BytesIO(payload)).load()
    start, end = dt.date(2022, 10, 6), dt.date(2023, 4, 10)
    window = {date: row for date, row in root.items() if start <= date <= end}
    expected = {
        "TSLA": (127, 127, 1, 1),
        "NFLX": (127, 0, 1, 1),
        "AMZN": (127, 22, 1, 1),
        "MSFT": (127, 127, 0, 1),
        "COIN": (127, 0, 1, 1),
    }
    rows = []
    for ticker in TICKERS:
        counts = []
        for field in ("price", "news", "filing_k", "filing_q"):
            counts.append(sum(
                ticker in row.get(field, {}) and has_payload(row[field][ticker])
                for row in window.values()
            ))
        rows.append(
            {
                "ticker": ticker,
                "price_date_count": counts[0],
                "news_date_count": counts[1],
                "annual_filing_date_count": counts[2],
                "quarterly_filing_date_count": counts[3],
                "paper_claimed_pattern": str(expected[ticker]),
                "matches_paper_claims": tuple(counts) == expected[ticker],
                "restricted_unpickler_only_allows_datetime_date": True,
                "data_layer_credit": tuple(counts) == expected[ticker],
                "native_agent_result_credit": False,
            }
        )
    if len(window) != 127:
        raise ValueError(f"expected 127 dated test records, found {len(window)}")
    return rows


def formula_inventory() -> list[dict[str, Any]]:
    formulas = [
        ("news_influence", "N_t=0.55*base+0.25*prob+0.20", "partial", "base keyword/length rule and top-k unspecified"),
        ("hybrid_retrieval", "H_i=1.0*dense+0.8*sparse", "specified", "embedding model revisions and chunking parameters incomplete"),
        ("simplified_atr20", "100*sqrt(mean((log_return-mean)^2))", "specified", "called ATR despite being close-return volatility"),
        ("breakout_threshold", "max(1%,0.5*SimplifiedATR20)", "specified", "hybrid gate uptrend threshold itself unspecified"),
        ("stop_loss", "m_s_sl*sigma_d_10", "partial", "style multipliers not published"),
        ("take_profit", "m_s_tp*sigma_d_10", "partial", "style multipliers not published"),
        ("forecast_epsilon", "max(alpha*mean(abs(log_return_20)),epsilon_min)", "partial", "alpha and epsilon_min not published"),
        ("realized_return", "P_d1/P_d0-1", "specified", "next-trading-day alignment described"),
        ("weighted_hit", "sign_ok*tanh(abs(pct)/epsilon)*p_true", "specified", "selection cutoff for high w_hit not published"),
        ("decision_reward", "r_eq-beta*r_bm-gamma*c_a", "specified", "beta=0.2 and gamma=1.0 published"),
        ("equity_return", "(E_a-E_prev)/E_prev", "specified", "counterfactual action simulator not released"),
        ("benchmark_return", "(P_curr-P_prev)/P_prev", "specified", "price convention not fully locked"),
        ("cost_ratio", "commission_a/E_prev", "specified", "commission schedule not stated in TradingGroup paper"),
    ]
    return [
        {
            "formula_id": formula_id,
            "paper_expression": expression,
            "specification_status": status,
            "unresolved_boundary": boundary,
            "synthetic_component_executed": True,
            "paper_input_used": False,
            "paper_result_credit": False,
        }
        for formula_id, expression, status, boundary in formulas
    ]


def formula_component_execution() -> dict[str, Any]:
    returns = [-0.012, 0.009, 0.014, -0.005, 0.006] * 4
    mean = math.fsum(returns) / len(returns)
    simplified_atr = 100 * math.sqrt(
        math.fsum((value - mean) ** 2 for value in returns) / len(returns)
    )
    epsilon = max(1.2 * math.fsum(abs(value) for value in returns) / 20, 0.005)
    values = {
        "news_influence": 0.55 * 0.6 + 0.25 * 0.8 + 0.20,
        "hybrid_retrieval": 1.0 * 0.5 + 0.8 * 0.25,
        "simplified_atr20_percent": simplified_atr,
        "breakout_threshold_percent": max(1.0, 0.5 * simplified_atr),
        "stop_loss": 0.8 * 0.02,
        "take_profit": 1.5 * 0.02,
        "forecast_epsilon": epsilon,
        "realized_return": 110 / 100 - 1,
        "weighted_hit": math.tanh((110 / 100 - 1) / epsilon) * 0.8,
        "decision_reward": 0.02 - 0.2 * 0.01 - 1.0 * 0.001,
        "equity_return": (102_000 - 100_000) / 100_000,
        "benchmark_return": (101 - 100) / 100,
        "cost_ratio": 100 / 100_000,
    }
    rendered = json.dumps(values, sort_keys=True, separators=(",", ":"))
    return {
        "classification": "audit-declared synthetic formula component",
        "formula_count": len(values),
        "values": values,
        "values_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
        "paper_market_or_runtime_inputs_used": False,
        "native_tradinggroup_evaluator_used": False,
        "paper_result_credit": False,
    }


def prompt_inventory() -> list[dict[str, Any]]:
    agents = (
        ("News-Sentiment Agent", "singlePrompt and overall_news_prompt fragments"),
        ("Financial-Report Agent", "prompt_q and prompt_k fragments"),
        ("Stock-Forecasting Agent", "prompt_SA section-name fragment"),
        ("Style-Preference Agent", "prompt_PA section-name fragment"),
        ("Trading-Decision Agent", "prompt_DA section-name fragment"),
    )
    return [
        {
            "agent": agent,
            "figure2_runtime_shaped_example": True,
            "published_fragment": fragment,
            "exact_full_template_recovered": False,
            "actual_complete_request_recovered": False,
            "actual_complete_response_recovered": False,
            "chain_of_thought_only_truncated_example": True,
            "native_prompt_call_credit": False,
        }
        for agent, fragment in agents
    ]


def figure_inventory() -> list[dict[str, Any]]:
    return [
        {"figure": "Figure 1", "kind": "system architecture", "panels": 1, "plotted_series": 0, "native_tradinggroup_series": 0, "underlying_array_released": False, "regenerated": False, "full_page_visual_qa": True},
        {"figure": "Figure 2", "kind": "data-pipeline examples", "panels": 1, "plotted_series": 0, "native_tradinggroup_series": 0, "underlying_array_released": False, "regenerated": False, "full_page_visual_qa": True},
        {"figure": "Figure 3", "kind": "cumulative-return curves", "panels": 5, "plotted_series": 25, "native_tradinggroup_series": 15, "underlying_array_released": False, "regenerated": False, "full_page_visual_qa": True},
    ]


def method_specification() -> list[dict[str, Any]]:
    rows = [
        ("agents", "specified", "five named roles and information flow"),
        ("test_window", "specified", "2022-10-06 through 2023-04-10"),
        ("test_tickers", "specified", "TSLA NFLX AMZN MSFT COIN"),
        ("test_data", "recovered", "hash-pinned FINSABER aggregate data and price CSV"),
        ("training_windows", "specified", "two nonoverlapping windows from 2020-06-16 to 2022-10-05"),
        ("training_trajectories", "count_only", "1,080 selected trajectories; rows not released"),
        ("base_training_teacher", "specified", "DeepSeek-R1"),
        ("comparison_core_model", "specified", "GPT-4o-mini"),
        ("peft_base_model", "specified", "Qwen3-8B"),
        ("peft_method", "partial", "LoRA plus int8, AdamW8bit, one epoch, 0.5301% trainable"),
        ("peft_hyperparameters", "missing", "rank, alpha, dropout, targets, LR, batch, seed absent"),
        ("checkpoint", "missing", "Qwen3-Trader-8B-PEFT not released"),
        ("full_prompts", "missing", "only truncated Figure 2 fragments"),
        ("runtime_model_requests", "missing", "no immutable requests/responses"),
        ("chain_of_thought", "missing", "only truncated examples; 1,080 trajectories absent"),
        ("news_rules", "partial", "score weights stated; base rule/top-k/dedup threshold absent"),
        ("report_rag", "partial", "models/weights/top-10/top-6 stated; chunking and deployment absent"),
        ("stock_gate", "partial", "several thresholds stated; uptrend probability threshold absent"),
        ("style_multipliers", "missing", "risk multipliers/configuration absent"),
        ("self_reflection", "partial", "20-day examples described; exact selector/summarizer absent"),
        ("risk_execution", "partial", "threshold equations stated; multipliers/fill semantics absent"),
        ("commission_and_cash", "missing", "paper omits exact backtest configuration"),
        ("random_seeds", "missing", "LLM and training seeds absent"),
        ("native_source", "missing", "no attributable TradingGroup implementation"),
        ("daily_actions_fills_nav", "missing", "no native path artifacts"),
        ("raw_table_arrays", "missing", "no raw results"),
        ("figure_curve_arrays", "missing", "no cumulative-return arrays"),
        ("baseline_framework", "recovered", "historical FINSABER commit and author-linked inputs"),
        ("baseline_environment", "reconstructed", "exact listed versions for relevant packages"),
        ("baseline_model_training_window", "recovered_but_paper_omitted", "two years exactly regenerates all 32 ARIMA/XGBoost cells; repository default changed from two to three years before submission"),
        ("inference_engine", "partial", "vLLM named; version/config absent"),
    ]
    return [
        {"dimension": dimension, "status": status, "evidence": evidence}
        for dimension, status, evidence in rows
    ]


def internal_consistency(annotation_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotation_counts = Counter(row["status"] for row in annotation_rows)
    return [
        {"claim_id": "dataset_claims", "status": "passes_recovered_data_check", "audit_finding": "All five ticker-specific price/news/filing claims match the hash-pinned aggregate data exactly."},
        {"claim_id": "table2_spr_cr", "status": "passes_displayed_arithmetic", "audit_finding": "PEFT exceeds base Qwen3 in SPR and CR for all 5/5 tickers."},
        {"claim_id": "table2_msft_risk", "status": "passes_displayed_arithmetic", "audit_finding": "MSFT PEFT also improves MDD and AV as claimed."},
        {"claim_id": "amzn_return_claim", "status": "passes_displayed_arithmetic", "audit_finding": "TradingGroup CR is 40.458%; the strongest baseline is SMA at 13.265%, which rounds to 13.27%."},
        {"claim_id": "table3_duplicate_all_enabled", "status": "exact_duplicate", "audit_finding": "All 20 all-enabled Table 3 measurements exactly repeat Table 1 TradingGroup cells."},
        {"claim_id": "table3_annotations", "status": "two_rounding_mismatches", "audit_finding": f"{annotation_counts['passes_displayed_arithmetic']}/60 annotations round from displayed values; {annotation_counts['annotation_rounding_mismatch']}/60 do not."},
        {"claim_id": "tsla_rm_pc_spr_annotation", "status": "annotation_rounding_mismatch", "audit_finding": "Displayed 1.070 to 0.409 is -61.776%, which rounds to -62%, not printed -61%."},
        {"claim_id": "tsla_rm_pc_cr_annotation", "status": "annotation_and_prose_rounding_mismatch", "audit_finding": "Displayed 21.904 to 5.276 is -75.913%, which rounds to -76%, not printed/prose -77%."},
        {"claim_id": "global_optimum", "status": "overbroad_ambiguous_claim", "audit_finding": "The claim of globally optimal overall performance is not a defined aggregate metric; TradingGroup is not best on every individual metric for TSLA or COIN."},
        {"claim_id": "finsaber_coin_execution", "status": "advertised_runner_conflict", "audit_finding": "The historical default runner omits COIN for all eight strategies under its prior-history guards; the recovered two-year model run still lacks enough COIN history, yet Table 1 prints a numeric XGBoost row."},
        {"claim_id": "deterministic_baselines", "status": "substantial_fresh_reproduction", "audit_finding": "Fresh pinned execution matches 96/96 paper cells for six deterministic strategies on four eligible tickers."},
        {"claim_id": "model_baselines", "status": "exact_historical_configuration_reproduction", "audit_finding": "A two-year training window reproduces 16/16 ARIMA and 16/16 XGBoost cells exactly; the paper omits this parameter and the source default was restored to three years before submission."},
        {"claim_id": "source_csv_lineage", "status": "historical_output_conflict", "audit_finding": "Historical committed FINSABER CSVs match only 59/168 comparable numeric paper cells; fresh deterministic execution matches more of the TradingGroup paper than those CSVs."},
        {"claim_id": "native_results", "status": "unverifiable_without_release", "audit_finding": "No native agent code, checkpoint, trajectories, actions, fills, NAVs, or figure arrays were released."},
    ]


def discovery_evidence(scratch: Path) -> list[dict[str, Any]]:
    records = [
        ("github_code_title_arxiv.json", "GitHub code: exact title/arXiv", 53, "paper mentions/indexes only"),
        ("github_code_checkpoint.json", "GitHub code: checkpoint name", 2, "paper-text copies only"),
        ("github_repo_title.json", "GitHub repositories: exact title phrase", 0, "no repository"),
        ("repo_tradinggroup.json", "GitHub repositories: TradingGroup", 1, "unattributed post-paper collision"),
        ("repo_checkpoint.json", "GitHub repositories: checkpoint name", 0, "no repository"),
        ("hf_checkpoint.json", "Hugging Face models: checkpoint name", 0, "no model"),
        ("hf_dataset.json", "Hugging Face datasets: TradingGroup", 0, "no dataset"),
    ]
    rows = []
    for filename, query, count, interpretation in records:
        rows.append(
            {
                "source_file": filename,
                "query": query,
                "result_count": count,
                "interpretation": interpretation,
                "attributable_tradinggroup_system_recovered": False,
                "negative_search_limit": "bounded negative search is not proof that private, deleted, inaccessible, or unindexed artifacts never existed",
            }
        )
    return rows


def source_provenance(
    scratch: Path, validated: dict[str, Any], execution_documents: dict
) -> dict[str, Any]:
    safe_audit = json.loads(
        (scratch / "finsaber_selective_data.safe-audit.json").read_text()
    )
    return {
        "arxiv": {
            "id": ARXIV_ID,
            "version": "v1",
            "submitted": "2025-08-25",
            "pdf_pages": 9,
            "source_file_count": len(validated["official_source_members"]),
            "source_members": validated["official_source_members"],
            "repeated_downloads_byte_identical": True,
            "source_rebuild_completed": True,
            "rebuild_pages": 9,
            "rebuild_extracted_token_multiset_jaccard": 0.9974937343358395,
            "visual_qa": {"pages_inspected": 9, "unreadable_or_clipped_pages": 0},
        },
        "finsaber": {
            "origin": "https://github.com/waylonli/FINSABER.git",
            "commit": FINSABER_COMMIT,
            "tree": FINSABER_TREE,
            "commit_authored": "2025-08-09T13:43:15+01:00",
            "tag_containing_commit": "v2.0.1",
            "selective_data_sha256": PINS["finsaber_selective_data.pkl"],
            "price_csv_sha256": PINS["finsaber_price_only.csv"],
            "safe_pickle_global_references": safe_audit["opcode_audit"]["global_references"],
            "safe_pickle_forbidden_construction_opcodes": safe_audit["opcode_audit"]["forbidden_construction_opcodes"],
            "execution_packages": execution_documents[
                "paper_lineage_two_year_models"
            ]["execution"]["packages"],
            "paper_lineage_execution_config": execution_documents[
                "paper_lineage_two_year_models"
            ]["inputs"]["config"],
            "pinned_default_execution_config": execution_documents[
                "pinned_default_three_year"
            ]["inputs"]["config"],
            "two_year_default_commit": FINSABER_TWO_YEAR_DEFAULT_COMMIT,
            "three_year_default_restore_commit": FINSABER_THREE_YEAR_RESTORE_COMMIT,
            "training_year_override_commit": FINSABER_TRAINING_OVERRIDE_COMMIT,
            "model_training_window_finding": "two years exactly regenerates all 32 eligible ARIMA/XGBoost cells; the paper does not state this parameter",
            "import_adapter_sha256": PINS["finsaber-import-adapter.patch"],
            "adapter_boundary": "removes eager imports of unused external/RL modules only; strategy, data transform, commission, dates, and metrics unchanged",
        },
        "release_boundary": {
            "attributable_tradinggroup_implementation_recovered": False,
            "qwen3_trader_checkpoint_recovered": False,
            "training_trajectories_recovered": False,
            "complete_runtime_prompts_recovered": False,
            "native_actions_fills_navs_or_curves_recovered": False,
            "finsaber_is_source_adjacent_baseline_framework_not_tradinggroup_source": True,
        },
    }


def readme() -> str:
    return """# TradingGroup paper-level replication audit

Overall verdict: **paper document, exact test data, formulas, and all eligible
source-adjacent baselines reproduced; native TradingGroup experiment not
reproduced**.

## What is faithfully recovered

- The official nine-page arXiv v1 PDF/source are byte-pinned, repeat-download
  identical, source-rebuilt, and visually checked on every page. The rebuild has
  99.75% extracted-token multiset overlap with the official PDF.
- All **360 displayed numeric table cells** are transcribed: 240 in Table 1, 40
  in Table 2, and 80 in Table 3. The 20 all-enabled Table 3 cells are exact
  duplicates of the Table 1 TradingGroup row, leaving 340 unique table cells.
- The hash-pinned author-linked FINSABER aggregate data exactly confirms all
  stated test-set facts: 127 dated price observations for every ticker; daily
  TSLA/MSFT news, 22 AMZN news dates, no NFLX/COIN news; MSFT quarterly-only
  filings; and both filing types for the other four tickers.
- The exact historical pre-submission FINSABER commit and both author-linked
  input files execute under the relevant versions from its requirements. Eight
  Table 1 strategies yield 128 eligible cells and reproduce **128/128** at paper
  display precision. The six deterministic strategies account for 96/96. A
  historical two-year training window exactly recovers the remaining 16/16
  ARIMA and 16/16 XGBoost cells. The paper omits this parameter, and FINSABER
  restored a three-year default before the paper's submission. The audited
  runner omits COIN; even the recovered two-year model window lacks enough prior
  COIN history.
- All 13 printed formula units execute on a declared synthetic fixture. This is
  formula-component evidence only. Figure 2 contains useful but truncated
  runtime-shaped examples for all five agents.

## Why native faithfulness remains zero

The paper publishes 140 displayed native TradingGroup table cells, of which 120
are unique after Table 3 duplicates. **0/120 unique native table cells** and
**0/15 native cumulative-return series** are regenerated. No attributable
TradingGroup implementation, Qwen3-Trader-8B-PEFT checkpoint, 1,080 training
trajectories, complete prompts/model calls, actions, orders, fills, NAVs, daily
returns, or raw figure/table arrays are public. FINSABER is the cited baseline
framework and data source; it is not the missing TradingGroup system.

## Important consistency and lineage findings

- The recovered data confirms the paper's detailed test-set claims exactly.
- All 128 eligible baseline cells regenerate exactly. The model cells require
  the source repository's historical two-year training window; its later
  three-year default produces 0/32 model-cell matches. Because the paper never
  states this parameter, result lineage is recovered but the method remains
  under-specified.
- The FINSABER repository's historical committed result CSVs match only 59/168
  comparable numeric paper cells and therefore are not the paper's result
  lineage.
- The advertised historical runner omits COIN because its three-year prior-data
  guard fails, while the paper prints COIN values for those baselines.
- Table 2 supports the claim that PEFT improves SPR and CR on all five tickers
  and improves both MDD and AV for MSFT.
- Only 58/60 Table 3 percentage annotations round from the displayed values.
  TSLA RM+PC SPR should round to -62%, not -61%; CR should round to -76%, not
  -77% as printed and repeated in prose.
- The paper's “globally optimal overall performance” language is not tied to a
  defined aggregate metric and is overbroad if read as dominance on every metric.

The bounded public search found no attributable implementation or checkpoint.
That is not proof that private, deleted, inaccessible, or unindexed artifacts
never existed. Run `scripts/audit_tradinggroup_paper.py` to regenerate the
ledgers. `--strict` intentionally exits nonzero while the native end-to-end
experiment remains unreproduced.
"""


def build(scratch: Path, output: Path) -> dict[str, Any]:
    validated = validate_inputs(scratch)
    output.mkdir(parents=True, exist_ok=True)
    tex = (scratch / "source/arxiv.tex").read_text(encoding="utf-8")
    table1, dash_count = table1_rows(tex)
    table2 = table2_rows(tex)
    table3, annotations = table3_rows(tex)
    paper_rows = table1 + table2 + table3
    published, execution, source_comparison, execution_documents = (
        result_and_execution_ledgers(
            paper_rows, validated["finsaber_repo"], scratch
        )
    )
    dataset = test_dataset_audit(scratch)
    consistency = internal_consistency(annotations)

    write_csv(output / "published_result_ledger.csv", published)
    write_csv(output / "finsaber_execution_ledger.csv", execution)
    write_csv(output / "finsaber_source_output_comparison.csv", source_comparison)
    write_csv(output / "test_dataset_audit.csv", dataset)
    write_csv(output / "formula_inventory.csv", formula_inventory())
    write_json(output / "formula_component_execution.json", formula_component_execution())
    write_csv(output / "prompt_inventory.csv", prompt_inventory())
    write_csv(output / "figure_inventory.csv", figure_inventory())
    write_csv(output / "method_specification_audit.csv", method_specification())
    write_csv(output / "table3_annotation_audit.csv", annotations)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(output / "discovery_evidence.csv", discovery_evidence(scratch))
    write_json(
        output / "source_provenance.json",
        source_provenance(scratch, validated, execution_documents),
    )
    (output / "README.md").write_text(readme(), encoding="utf-8")

    native = [row for row in published if row["native_tradinggroup_result"]]
    unique_native = [row for row in native if row["duplicate_kind"] == "none"]
    unique_total = [row for row in published if row["duplicate_kind"] == "none"]
    source_statuses = Counter(row["status"] for row in source_comparison)
    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "official_version_audited": "v1",
        "official_pdf_and_source_recovered": True,
        "official_document_rebuild_completed": True,
        "published_table1_slots": len(table1) + dash_count,
        "published_table1_numeric_cells": len(table1),
        "published_table1_dash_cells": dash_count,
        "published_table2_numeric_cells": len(table2),
        "published_table3_numeric_cells": len(table3),
        "published_numeric_table_cells": len(published),
        "published_unique_numeric_table_cells": len(unique_total),
        "displayed_native_tradinggroup_table_cells": len(native),
        "unique_native_tradinggroup_table_cells": len(unique_native),
        "native_tradinggroup_table_cells_regenerated": sum(
            row["native_result_regenerated"] for row in unique_native
        ),
        "source_adjacent_baseline_cells_executed": len(execution),
        "source_adjacent_baseline_cells_matching_paper": sum(
            row["fresh_execution_matches_paper"] for row in execution
        ),
        "source_adjacent_baseline_cells_matching_pinned_default": sum(
            row["pinned_default_execution_matches_paper"] for row in execution
        ),
        "model_baseline_training_years_recovered": 2,
        "model_baseline_cells_matching_paper": sum(
            row["fresh_execution_matches_paper"]
            for row in execution if row["strategy"] in {"ARIMA", "XGBoost"}
        ),
        "historical_source_csv_comparable_numeric_cells": len(source_comparison) - source_statuses["paper_dash_or_no_numeric_cell"],
        "historical_source_csv_cells_matching_paper": source_statuses["matches_paper_at_display_precision"],
        "test_ticker_data_claims_reproduced": sum(row["data_layer_credit"] for row in dataset),
        "test_ticker_data_claims_total": len(dataset),
        "printed_formula_units_conditionally_executed": len(formula_inventory()),
        "figure3_plotted_series": 25,
        "native_tradinggroup_figure_series": 15,
        "native_tradinggroup_figure_series_regenerated": 0,
        "attributable_implementation_source_files_recovered": 0,
        "qwen3_trader_checkpoint_recovered": False,
        "full_end_to_end_pipeline_reproduced": False,
        "paper_result_credit_for_formula_component": False,
        "paper_result_credit_for_finsaber_baselines_is_native_credit": False,
    }
    outputs = sorted(path for path in output.iterdir() if path.name != "manifest.json")
    manifest["output_sha256"] = {path.name: sha256(path) for path in outputs}
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
    return int(args.strict and not manifest["full_end_to_end_pipeline_reproduced"])


if __name__ == "__main__":
    raise SystemExit(main())
