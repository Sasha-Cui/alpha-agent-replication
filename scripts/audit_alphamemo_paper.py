#!/usr/bin/env python3
"""Audit AlphaMemo paper v1 against its pinned official source release.

The audit enumerates all numeric experimental cells in Tables 2--9, separates
result cells from configuration cells, checks repeated-paper identities, traces
the active official runner, and executes only the release's deterministic
synthetic smoke component. It does not call an LLM, download market data, or
count synthetic outputs, repeated cells, or source-code presence as paper
result reproduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


SOURCE_COMMIT = "412fee13d905bf5a25f0958aa572b7c668ccb925"
SOURCE_URL = "https://github.com/jarrettyu/AlphaMemo"
PAPER_URL = "https://arxiv.org/pdf/2606.20625v1"
PAPER_SHA256 = "64dbd4558ec63a88bbf8fc8245b7eb43443878969531a9661e15c31f6fcedcd0"
DEFAULT_SOURCE_PYTHON = "/nfs/roberts/project/pi_btk22/zc362/environments/bin/kt-python"

PINNED_SOURCE_SHA256 = {
    "README.md": "2df79fa9f1e5112669110bb4b8df4c94f9a90bc94f0623542b0c48fb4c04d74d",
    "pyproject.toml": "8f554cb584ff999d6504801b0c51ad8c464403676373113113e197d9451c24c1",
    "requirements.txt": "60052cd488ab7fa3e5130a594c1b1f1c90ed96f8fbb3573a8ff804eb685f7e23",
    "environment.yml": "2151faddf34a46f8d3255ee5f22a11a45367eb26b2c49027b297b4cb8a16c6b7",
    "configs/demo.json": "88ef9da7f9badfa565ece811e00ec710fb12349121ab891f09ae9f92d4652f9c",
    "scripts/run_main.sh": "77257d925cdf882f15816db88411cb0d12bcc8821c63c734142f438ee100b636",
    "scripts/collect_results.py": "f6b64c62f9a44ac1856e18f0f5df3279006708d878a77cacf2d3fab2427ed454",
    "scripts/alpha_decay.py": "d7e1f88ab5372207c445e9cdb033d7ac1fb5cbb34cbb3baed1b7dd6060988f1f",
    "scripts/qrun_alphamemo.sh": "763585181461fa76eb948d0d21643d5bd3b5508f5a88915a6ea0b1a5761f944b",
    "sspm/cli.py": "57393f8e07eb42c53b81a566984e7057455ea2f5f86c8f7fb99faee509d1bbf9",
    "sspm/runner.py": "d791034f19d3c720218c62c5b76e7451454cdeeb3238754051f28256ac493cdf",
    "sspm/core/dag.py": "e9445a7184ddce311332314acd3d2d7767369c421a5403c53585943863424a03",
    "sspm/core/motifs.py": "d55ef9e25a49cb231635123209a70c24fdc4920295ff9333a64974633df7da6c",
    "sspm/core/types.py": "58fda3c6c1229cb005e34cc801eeecb3673ce3bc6fbf4354c7b9f62c4fba58ca",
    "sspm/generation/heuristic.py": "64a175a49c37c06ff7af71c21a0935ed2786ff6334effb8087c724c0cb9b1b5f",
    "sspm/generation/openai_compatible.py": "a8dffb012ad4fc3e5d4094babec83fb8604abcb561c45dfd554be5eebd41b594",
    "sspm/memory/residual.py": "c2e8ea489c94aba35e157e92bc811894bd73a0d095b759b796960a18ebbecbe5",
    "sspm/strategies/graph_memory.py": "20c90744382be3a3326ef3c3b4f9352f08ca2db207585609975a0d4da788e356",
    "sspm/strategies/sspm.py": "b77f9330ef16b431ad55969acdcc789c8915b879d75a7c79e129173f0c523a05",
    "sspm/strategies/veto_memory.py": "ac427f4313441a57247a396dd66d2a8a73d0979deef2a860eb4ded502496606f",
    "sspm/evaluation/formula_eval.py": "81d77caa5251f3df4158297d0a8536d9805f142e84b3fe301207a50fcc5b5683",
    "sspm/evaluation/qlib_export.py": "c7ced10d1a1b018ffbd162801044a15b6a15a871f14f744445b1fd95f2d2b80c",
    "templates/qlib_factor_template/conf_cn_combined_kdd_ver.yaml": "251d90128426316a754bcb051388aeab653f0a59071a1943fca547f9779defe8",
    "templates/qlib_factor_template/conf_us_combined_kdd_ver.yaml": "70cb8bcadf8f818bf846632ab556ecddcf100c4b027f61459287daf14e4ad659",
    "tests/test_smoke.py": "20f7d652028256ce7203789f177c800a7c9921e4e398f8523b06d6270dc1772c",
}

METRICS_7 = ("IC", "ICIR", "RankIC", "RankICIR", "AR_pct", "MDD_pct", "Sharpe")
METRICS_4 = ("ICIR", "RankICIR", "AR_pct", "Sharpe")

# entity|CSI500 seven metrics|S&P500 seven metrics
TABLE_2_TEXT = """
Alpha158|0.0053|0.0634|0.0115|0.1188|7.70|-24.34|0.4055|0.0155|0.1300|0.0081|0.0611|14.36|-21.86|0.6186
GP|0.0226|0.2404|0.0326|0.3403|6.75|-30.28|0.3197|0.0062|0.0494|-0.0013|-0.0096|14.10|-24.58|0.6534
LightGBM|0.0095|0.1124|-0.0115|-0.1085|8.85|-33.83|0.4028|0.0133|0.1009|0.0046|0.0377|15.46|-26.67|0.6040
LSTM|0.0222|0.2384|0.0096|0.0939|9.95|-40.23|0.4047|0.0138|0.0853|0.0068|0.0412|16.36|-28.84|0.5792
AlphaGen|0.0311|0.2988|0.0436|0.4156|8.03|-30.99|0.4040|0.0348|0.3569|0.0101|0.1153|19.44|-24.22|0.9471
AlphaGPT|0.0077|0.0909|0.0011|0.0118|8.08|-30.39|0.3903|0.0163|0.1202|0.0005|0.0038|17.36|-26.14|0.7501
AlphaSAGE|0.0031|0.0335|0.0190|0.2341|5.49|-37.12|0.2541|0.0256|0.2187|0.0079|0.0745|14.26|-29.96|0.6040
AlphaAgent|0.0102|0.1150|-0.0156|-0.1437|4.27|-40.16|0.1818|0.0306|0.2569|0.0133|0.1023|19.40|-24.77|0.8077
AlphaMemo (residual)|0.0101|0.1104|0.0165|0.1808|6.97|-26.08|0.3511|0.0410|0.3434|0.0228|0.1984|23.65|-23.62|1.0672
AlphaMemo (balanced)|0.0401|0.3462|0.0496|0.4597|11.63|-23.43|0.6109|0.0288|0.2406|0.0144|0.1207|17.07|-22.54|0.7743
"""

# entity|CSI500 four metrics|S&P500 four metrics
TABLE_3_TEXT = """
Search-ledger only|0.2313|0.3707|7.00|0.3536|0.1414|0.0044|13.80|0.6282
AlphaMemo (balanced)|0.3462|0.4597|11.63|0.6109|0.2406|0.1207|17.07|0.7743
Weaker memory|0.1455|0.2886|5.80|0.3011|0.1001|-0.0299|17.09|0.7393
Stronger memory|0.2208|0.3454|11.57|0.5646|0.1579|0.0402|16.20|0.7105
APV-only memory|0.2405|0.3993|7.72|0.3875|0.1718|0.0243|15.99|0.6493
AlphaMemo (residual)|0.1104|0.1808|6.97|0.3511|0.3434|0.1984|23.65|1.0672
"""

# entity|CSI500 seven metrics|S&P500 seven metrics
TABLE_5_TEXT = """
Search-ledger only|0.0218|0.2313|0.0347|0.3707|7.00|-30.63|0.3536|0.0173|0.1414|0.0006|0.0044|13.80|-26.83|0.6282
AlphaMemo (balanced)|0.0401|0.3462|0.0496|0.4597|11.63|-23.43|0.6109|0.0288|0.2406|0.0144|0.1207|17.07|-22.54|0.7743
AlphaMemo (residual)|0.0101|0.1104|0.0165|0.1808|6.97|-26.08|0.3511|0.0410|0.3434|0.0228|0.1984|23.65|-23.62|1.0672
Weaker memory|0.0138|0.1455|0.0295|0.2886|5.80|-29.10|0.3011|0.0130|0.1001|-0.0039|-0.0299|17.09|-22.64|0.7393
Stronger memory|0.0205|0.2208|0.0283|0.3454|11.57|-26.27|0.5646|0.0196|0.1579|0.0048|0.0402|16.20|-25.19|0.7105
Late weak memory|0.0181|0.2231|0.0137|0.1708|8.57|-32.39|0.3917|0.0109|0.0847|-0.0008|-0.0061|15.60|-23.58|0.6814
Late weak memory, seed 2|0.0285|0.2681|0.0195|0.2329|10.39|-28.80|0.4806|0.0223|0.1736|-0.0010|-0.0076|17.15|-25.66|0.7794
APV-only memory|0.0220|0.2405|0.0363|0.3993|7.72|-30.79|0.3875|0.0242|0.1718|0.0035|0.0243|15.99|-26.06|0.6493
Warmup 180, weak memory|0.0339|0.3291|0.0490|0.5074|10.88|-30.82|0.4850|0.0294|0.2266|0.0048|0.0384|19.37|-24.82|0.8605
Warmup 220, weak memory|0.0155|0.2043|0.0089|0.1039|7.94|-29.77|0.3863|0.0308|0.2322|0.0102|0.0778|19.34|-27.28|0.8623
Warmup 240|0.0150|0.1828|0.0213|0.2341|8.78|-24.59|0.4504|0.0210|0.1609|0.0026|0.0192|17.10|-24.57|0.7607
Weak memory, seed 1|0.0041|0.0402|-0.0024|-0.0224|2.50|-45.00|0.1104|0.0330|0.2410|0.0050|0.0374|22.10|-26.82|0.9340
Balanced, seed 3|0.0291|0.3541|0.0350|0.4462|4.08|-38.90|0.1798|0.0246|0.1910|0.0023|0.0179|18.61|-27.98|0.8042
"""

# entity|market|2022 IC/RankIC|...|2025 IC/RankIC
TABLE_6_TEXT = """
AlphaMemo (balanced)|CSI500|0.0030|0.0048|-0.0090|0.0004|0.0087|0.0209|0.0354|0.0289
AlphaMemo (balanced)|S&P500|0.0186|0.0134|-0.0007|0.0016|0.0036|-0.0131|0.0195|0.0157
Weaker memory|CSI500|0.0152|0.0328|-0.0250|-0.0149|0.0293|0.0399|0.0209|0.0251
Weaker memory|S&P500|0.0201|0.0182|0.0010|0.0000|0.0110|-0.0027|0.0191|0.0125
Stronger memory|CSI500|0.0076|0.0149|-0.0099|-0.0087|0.0275|0.0343|0.0221|0.0245
Stronger memory|S&P500|0.0126|0.0089|0.0041|0.0062|0.0078|-0.0079|0.0172|0.0111
APV-only memory|CSI500|0.0219|0.0385|0.0031|0.0273|0.0320|0.0452|0.0407|0.0596
APV-only memory|S&P500|0.0172|0.0175|0.0083|0.0117|0.0024|-0.0093|0.0164|0.0129
AlphaMemo (residual)|CSI500|0.0066|0.0047|-0.0106|0.0011|0.0111|0.0205|0.0223|0.0181
AlphaMemo (residual)|S&P500|-0.0164|0.0229|0.0651|0.0009|0.0658|0.0335|0.0547|0.0478
"""

TABLE_7_TEXT = """
Random search|5|10.4
Result-level memory|2|34.5
Search-Ledger Agent|5|52.4
AlphaMemo|5|76.0
"""

TABLE_8_TEXT = """
AlphaMemo|76.0
NoGate|34.6
AbsOLM|55.6
ManualMut|33.4
NoAPV|70.8
"""

PAPER_FACTORS = {
    "SSPM_000": (
        "CsRank(TsMin(Div(TsSum(Where(Greater($close,Delay($close,5)),Delta(Log(Add($volume,1.0)),5),0.0),10),"
        "TsStd(TsSum(Where(Greater($close,Delay($close,5)),Delta(Log(Add($volume,1.0)),5),0.0),10),60)),20))",
        (0.0325, 0.4461, 0.5237),
    ),
    "SSPM_017": (
        "TsRank(Where(Greater($close,Delay($close,5)),TsMean(Log(Add($volume,1.0)),5),0.0),20)",
        (0.0268, 0.2877, 0.1979),
    ),
    "SSPM_033": (
        "CsRank(Add(Where(Greater($close,Delay($close,5)),Delta(Log(Add($volume,1.0)),5),0.0),"
        "Where(Less($close,Delay($close,5)),Neg(Delta(Log(Add($volume,1.0)),5)),0.0)))",
        (0.0159, 0.2310, 0.3745),
    ),
    "SSPM_038": (
        "CsRank(Add(CsRank(Where(Greater($close,Delay($close,5)),Delta(Log(Add($volume,1.0)),5),"
        "Neg(Delta(Log(Add($volume,1.0)),5)))),CsRank(Mul(Delta(Log(Add($volume,1.0)),5),Delta($close,5)))))",
        (0.0173, 0.2243, 0.3743),
    ),
    "SSPM_036": (
        "CsRank(Add(CsRank(Where(Greater($close,Delay($close,10)),Delta(Log(Add($volume,1.0)),10),0.0)),"
        "CsRank(Mul(Delta(Log(Add($volume,1.0)),5),Delta($close,5)))))",
        (0.0191, 0.2299, 0.3881),
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def git_files(root: Path) -> list[str]:
    output = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in output.splitlines() if line]


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _two_market_rows(table: int, text: str, metrics: Sequence[str]) -> list[dict[str, Any]]:
    rows = []
    for line in text.strip().splitlines():
        entity, *values = line.split("|")
        if len(values) != 2 * len(metrics):
            raise RuntimeError(f"Malformed Table {table} row: {line}")
        for market, part in zip(("CSI500", "S&P500"), (values[: len(metrics)], values[len(metrics) :])):
            for metric, value in zip(metrics, part):
                rows.append(
                    {
                        "paper_table": table,
                        "entity": entity,
                        "market": market,
                        "period": "aggregate",
                        "metric": metric,
                        "paper_value": float(value),
                        "cell_role": "result",
                    }
                )
    return rows


def paper_numeric_rows() -> list[dict[str, Any]]:
    rows = []
    rows.extend(_two_market_rows(2, TABLE_2_TEXT, METRICS_7))
    rows.extend(_two_market_rows(3, TABLE_3_TEXT, METRICS_4))
    rows.extend(
        [
            {"paper_table": 4, "entity": "Balanced", "market": "", "period": "", "metric": "warmup", "paper_value": 200.0, "cell_role": "configuration"},
            {"paper_table": 4, "entity": "Balanced", "market": "", "period": "", "metric": "memory_weight", "paper_value": 0.05, "cell_role": "configuration"},
            {"paper_table": 4, "entity": "Balanced", "market": "", "period": "", "metric": "motif_sample_size", "paper_value": 4.0, "cell_role": "configuration"},
            {"paper_table": 4, "entity": "Balanced", "market": "", "period": "", "metric": "random_motif_probability", "paper_value": 0.35, "cell_role": "configuration"},
            {"paper_table": 4, "entity": "Residual", "market": "", "period": "", "metric": "warmup", "paper_value": 300.0, "cell_role": "configuration"},
            {"paper_table": 4, "entity": "Residual", "market": "", "period": "", "metric": "memory_weight", "paper_value": 0.05, "cell_role": "configuration"},
        ]
    )
    rows.extend(_two_market_rows(5, TABLE_5_TEXT, METRICS_7))
    for line in TABLE_6_TEXT.strip().splitlines():
        entity, market, *values = line.split("|")
        for year, pair in zip(("2022", "2023", "2024", "2025"), (values[0:2], values[2:4], values[4:6], values[6:8])):
            for metric, value in zip(("IC", "RankIC"), pair):
                rows.append(
                    {
                        "paper_table": 6,
                        "entity": entity,
                        "market": market,
                        "period": year,
                        "metric": metric,
                        "paper_value": float(value),
                        "cell_role": "result",
                    }
                )
    for line in TABLE_7_TEXT.strip().splitlines():
        entity, seeds, effective = line.split("|")
        rows.extend(
            [
                {"paper_table": 7, "entity": entity, "market": "CSI500", "period": "fixed_budget", "metric": "seeds", "paper_value": float(seeds), "cell_role": "configuration"},
                {"paper_table": 7, "entity": entity, "market": "CSI500", "period": "fixed_budget", "metric": "mean_effective_factors", "paper_value": float(effective), "cell_role": "result"},
            ]
        )
    for line in TABLE_8_TEXT.strip().splitlines():
        entity, effective = line.split("|")
        rows.append(
            {"paper_table": 8, "entity": entity, "market": "CSI500", "period": "fixed_budget", "metric": "mean_effective_factors", "paper_value": float(effective), "cell_role": "result"}
        )
    for entity, (_formula, values) in PAPER_FACTORS.items():
        for metric, value in zip(("abs_IC", "abs_ICIR", "abs_RankICIR"), values):
            rows.append(
                {"paper_table": 9, "entity": entity, "market": "CSI500", "period": "selection", "metric": metric, "paper_value": value, "cell_role": "result"}
            )
    expected = {2: 140, 3: 48, 4: 6, 5: 182, 6: 80, 7: 8, 8: 5, 9: 15}
    if Counter(row["paper_table"] for row in rows) != expected:
        raise RuntimeError("Paper numeric-cell denominator changed")
    if Counter(row["cell_role"] for row in rows) != {"result": 474, "configuration": 10}:
        raise RuntimeError("Paper result/configuration boundary changed")
    return rows


def result_conformance() -> list[dict[str, Any]]:
    config_matches = {
        (4, "Balanced", "warmup"): 200.0,
        (4, "Balanced", "memory_weight"): 0.05,
        (4, "Balanced", "motif_sample_size"): 4.0,
        (4, "Balanced", "random_motif_probability"): 0.35,
    }
    rows = []
    for row in paper_numeric_rows():
        key = (row["paper_table"], row["entity"], row["metric"])
        if key in config_matches:
            observed: Any = config_matches[key]
            status = "configuration_match_active_official_runner"
            reason = "scripts/run_main.sh passes the same balanced operating-point value"
        elif row["cell_role"] == "configuration":
            observed = ""
            status = "configuration_not_reproduced_by_released_diagnostic_runner"
            reason = "parameter may be CLI-capable, but no exact paper diagnostic/seed runner is released"
        else:
            observed = ""
            status = "unavailable_missing_native_result_path"
            reason = "no paper data snapshot, native search trajectory/factor pool, or metric output is shipped"
        rows.append(
            {
                **row,
                "native_reproduced_value": observed,
                "absolute_difference": 0.0 if observed != "" else "",
                "status": status,
                "reason": reason,
            }
        )
    return rows


def _result_map(table: int) -> dict[tuple[str, str, str, str], float]:
    return {
        (row["entity"], row["market"], row["period"], row["metric"]): row["paper_value"]
        for row in paper_numeric_rows()
        if row["paper_table"] == table
    }


def paper_internal_identities() -> list[dict[str, Any]]:
    maps = {table: _result_map(table) for table in (2, 3, 5, 7, 8)}
    comparisons: list[tuple[int, int, tuple[str, str, str, str], tuple[str, str, str, str]]] = []
    # Selected balanced/residual metrics: Tables 2 and 3.
    for entity in ("AlphaMemo (balanced)", "AlphaMemo (residual)"):
        for market in ("CSI500", "S&P500"):
            for metric in METRICS_4:
                key = (entity, market, "aggregate", metric)
                comparisons.append((2, 3, key, key))
    # Full balanced/residual rows: Tables 2 and 5.
    for entity in ("AlphaMemo (balanced)", "AlphaMemo (residual)"):
        for market in ("CSI500", "S&P500"):
            for metric in METRICS_7:
                key = (entity, market, "aggregate", metric)
                comparisons.append((2, 5, key, key))
    # Selected Search-ledger/balanced/residual metrics: Tables 3 and 5.
    for entity in ("Search-ledger only", "AlphaMemo (balanced)", "AlphaMemo (residual)"):
        for market in ("CSI500", "S&P500"):
            for metric in METRICS_4:
                key = (entity, market, "aggregate", metric)
                comparisons.append((3, 5, key, key))
    comparisons.append(
        (
            7,
            8,
            ("AlphaMemo", "CSI500", "fixed_budget", "mean_effective_factors"),
            ("AlphaMemo", "CSI500", "fixed_budget", "mean_effective_factors"),
        )
    )
    rows = []
    for left_table, right_table, left_key, right_key in comparisons:
        left = maps[left_table][left_key]
        right = maps[right_table][right_key]
        rows.append(
            {
                "left_table": left_table,
                "right_table": right_table,
                "entity": left_key[0],
                "market": left_key[1],
                "metric": left_key[3],
                "left_value": left,
                "right_value": right,
                "absolute_difference": abs(left - right),
                "status": "paper_internal_identity_match_not_independent_reproduction" if left == right else "paper_internal_identity_mismatch",
            }
        )
    if len(rows) != 69 or any(row["absolute_difference"] != 0 for row in rows):
        raise RuntimeError("Published cross-table identities changed")
    return rows


def source_conformance(source_root: Path) -> list[dict[str, Any]]:
    def text(relative: str) -> str:
        return (source_root / relative).read_text(encoding="utf-8")

    run_main = text("scripts/run_main.sh")
    runner = text("sspm/runner.py")
    graph = text("sspm/strategies/graph_memory.py")
    residual = text("sspm/memory/residual.py")
    motifs = text("sspm/core/motifs.py")
    dag = text("sspm/core/dag.py")
    qlib_export = text("sspm/evaluation/qlib_export.py")
    generator = text("sspm/generation/openai_compatible.py")
    collect = text("scripts/collect_results.py")
    cli = text("sspm/cli.py")
    rows = [
        ("official_entrypoint", "paper AlphaMemo runner", "scripts/run_main.sh invokes sspm main-table", "component_present"),
        ("paper_markets", "CSI500 and S&P500", "official runner defaults to csi500 sp500", "configuration_match"),
        ("paper_split", "train 2016-2020; validation 2021; test 2022-2025-12-26", "paper2025 preset matches exact dates", "configuration_match"),
        ("label_horizon", "20 trading days", "official runner LABEL_DAYS=20 and Qlib label is h-day close-to-close", "configuration_match"),
        ("balanced_operating_point", "warmup=200 wm=.05 motif sample=4 prand=.35", "all four values match official runner", "configuration_match"),
        ("residual_operating_point", "residual SSPM warmup=300 wm=.05", "CLI supports sspm parameters; no official residual experiment command", "capable_but_no_released_run_path"),
        ("admission_quality_threshold", "tau_q=0.10 absolute ICIR", "official run_main.sh passes SUCCESS_ICIR=0.02", "mismatch_active_runner"),
        ("children_per_parent", "five children per selected parent", "batch=10 selects up to 10 parents and proposes one child per parent", "mismatch_active_runner"),
        ("parent_context", "category, quality bucket, depth bucket, retrieval-frequency bucket", "ResidualMemory key is only (category,motif)", "mismatch"),
        ("ast_diff_motif", "typed canonical AST differencing and normalized edit script", "motifs.py compares regex-derived operator/window/feature sets", "mismatch"),
        ("motifs_observed_not_commands", "labels extracted after generation, not hand-written mutation commands", "selected motif is explicitly sent to LLM as Requested edit motif", "mismatch"),
        ("residual_baseline", "weighted historical children from same full parent context", "source averages child quality only within low/medium/high parent-quality bucket", "mismatch"),
        ("confidence_gate", "n/(n+kappa) times min(1, abs(mu)/(sigma+epsilon))", "source combines count gate, beta-posterior entropy certainty, and variance penalty", "mismatch"),
        ("warmup_schedule", "zero through t0 then gradual ramp over Tw", "balanced graph strategy switches from random/warmup to full memory after one threshold", "mismatch"),
        ("apv_exclusion", "vetoed action excluded; choose next-best non-vetoed action", "balanced scorer retains vetoed motifs with negative severity and may select one", "mismatch"),
        ("ledger_all_evaluated_children", "add all evaluated children and edges", "runner adds to FactorDAG only when success and result.ok", "mismatch"),
        ("invalid_failure_memory", "invalid attempts update failure memory", "strategy update records failures, including invalid evaluations", "component_match"),
        ("lineage_prompt_context", "prompt includes parent lineage trace", "generator supports optional context but graph strategy never supplies it", "missing_active_path"),
        ("factor_length_threshold", "40", "generation request caps formula strings at 280 characters; no 40-unit admission check", "mismatch_or_unit_undisclosed"),
        ("factor_pool_capacity", "50 during common protocol", "export truncates to 50 only after search; search DAG is uncapped", "partial_mismatch"),
        ("fixed_budget_size", "same disclosed generation budget", "paper never gives numeric B; official main defaults to 500", "paper_underspecified"),
        ("fixed_budget_seeds", "5/2/5/5 by method", "benchmark defaults to seeds 0,1,2 and no paper diagnostic command is released", "mismatch_missing_runner"),
        ("mechanism_ablation_runner", "NoGate, AbsOLM, ManualMut, NoAPV", "none of these named variants/removed-component paths exist", "missing"),
        ("main_baseline_runner", "eight baselines in Table 2", "official runner strategies only alphamemo; collectors do not execute paper baselines", "missing"),
        ("native_input_snapshot", "exact CSI500/S&P500 Qlib panels", "current-download builder scripts only; no data snapshot", "missing"),
        ("native_output_snapshot", "paper trajectories, pools, predictions, returns, and metrics", "no tracked runs/data/result files", "missing"),
        ("representative_factor_snapshot", "five Table 9 formulas and metrics", "none of the factor names/formulas is tracked in source", "missing"),
        ("llm_model", "deepseek/deepseek-v4-flash through OpenRouter", "official runner default matches mutable model alias", "configuration_match_unpinned_endpoint"),
        ("llm_temperature_and_length", "temperature=.7 max generation=180 tokens", "OpenAI-compatible generator defaults match", "configuration_match"),
        ("llm_lineage_and_retry_provenance", "exact calls/responses and retry outcomes", "no prompts/responses/costs are shipped; terminal failures silently use a fixed fallback formula", "missing_and_behavioral_risk"),
        ("dependency_snapshot", "exact environment", "some packages pinned, core numpy/pandas/scipy and API endpoint are not", "partial_unpinned"),
        ("paper_result_collector", "all Tables 2--9", "collect_results reads main/variant metrics but no frozen inputs or outputs", "component_only"),
    ]
    # Fail closed if the specific released paths supporting these observations drift.
    assert 'SUCCESS_ICIR="${SUCCESS_ICIR:-0.02}"' in run_main
    assert 'BATCH_SIZE="${BATCH_SIZE:-10}"' in run_main
    assert "--strategies alphamemo" in run_main
    assert "self.cells[(category, motif)]" in residual
    assert "re.findall" in motifs and "ast.parse" not in motifs
    assert "if success and result.ok" in graph
    assert "np.argsort(-scores)[:k]" in dag
    assert "factor_arrays[: config.max_factors]" in qlib_export
    assert "Requested edit motif" in generator
    assert "read_variant_dirs" in collect
    assert "paper2025" in cli and "2025-12-26" in cli
    assert "strategy.update(candidate, result, success, step)" in runner
    return [
        {"dimension": dimension, "paper_requirement": paper, "released_evidence": evidence, "status": status}
        for dimension, paper, evidence, status in rows
    ]


def source_inventory(source_root: Path) -> list[dict[str, Any]]:
    result_tokens = ("run", "result", "output", "factor", "pool", "checkpoint", "log")
    rows = []
    for relative in git_files(source_root):
        path = source_root / relative
        lower = relative.lower()
        rows.append(
            {
                "file": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "name_looks_like_result_artifact": any(token in lower for token in result_tokens),
                "native_paper_result_artifact": False,
            }
        )
    return rows


def run_native_component_checks(source_root: Path, source_python: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not source_python.exists():
        raise RuntimeError(f"Source Python not found: {source_python}")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(source_root)
    subprocess.run(
        [str(source_python), "-m", "pytest", "-q"],
        cwd=source_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    with tempfile.TemporaryDirectory(prefix="alphamemo-audit-") as tmp:
        hashes = []
        summaries = []
        for index in (1, 2):
            path = Path(tmp) / f"smoke{index}.json"
            subprocess.run(
                [
                    str(source_python), "-m", "sspm", "run", "--strategy", "alphamemo",
                    "--budget", "12", "--batch-size", "4", "--seed", "7", "--n-days", "180",
                    "--n-assets", "40", "--quiet", "--out", str(path),
                ],
                cwd=source_root,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            hashes.append(sha256(path))
            summaries.append(payload["summary"])
    if len(set(hashes)) != 1 or summaries[0] != summaries[1]:
        raise RuntimeError("Pinned native synthetic smoke run is not deterministic")
    expected_summary = {
        "strategy": "alphamemo",
        "n_effective": 5,
        "n_ok": 12,
        "budget": 12,
        "mean_abs_ic_ok": 0.04637932219853949,
        "mean_abs_ic_discovered": 0.05564901407744506,
        "mean_abs_icir_discovered": 0.3618666753391596,
        "mean_abs_ric_discovered": 0.05496439758610393,
        "mean_abs_ricir_discovered": 0.35448448825152046,
    }
    if summaries[0] != expected_summary or hashes[0] != "82b09f8e2dbc77be1553295fad848b17354027b40fcd2e70c964be767f3955c1":
        raise RuntimeError("Pinned native smoke output changed")

    factor_program = """
import json, numpy as np, sys
from sspm.core.operators import evaluate_formula
from sspm.evaluation.synthetic import make_synthetic_market
formulas=json.loads(sys.argv[1]); market=make_synthetic_market(n_days=180,n_assets=40,seed=123)
out=[]
for name, formula in formulas.items():
    values=evaluate_formula(formula,market.features)
    out.append({'factor':name,'shape':list(values.shape),'finite_fraction':float(np.isfinite(values).mean())})
print(json.dumps(out))
"""
    factor_check = subprocess.run(
        [str(source_python), "-c", factor_program, json.dumps({name: item[0] for name, item in PAPER_FACTORS.items()})],
        cwd=source_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    factor_rows = json.loads(factor_check.stdout)
    for row in factor_rows:
        row.update(
            {
                "native_parser_executable": True,
                "paper_metric_reproduced": False,
                "status": "formula_executes_on_synthetic_data_not_paper_metric_reproduction",
            }
        )
    component = {
        "upstream_test_status": "passed",
        "upstream_test_summary": "1 passed",
        "upstream_tests_passed": 1,
        "source_python": str(source_python),
        "source_python_version": subprocess.run([str(source_python), "--version"], check=True, capture_output=True, text=True).stdout.strip(),
        "synthetic_smoke_runs": 2,
        "synthetic_smoke_sha256": hashes[0],
        "synthetic_smoke_deterministic": True,
        "synthetic_smoke_summary": summaries[0],
        "paper_result_reproduction": False,
    }
    return component, factor_rows


def verify_pins(source_root: Path, paper_pdf: Path) -> str:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected source commit {SOURCE_COMMIT}, found {commit}")
    observed_paper = sha256(paper_pdf)
    if observed_paper != PAPER_SHA256:
        raise RuntimeError(f"Expected paper SHA-256 {PAPER_SHA256}, found {observed_paper}")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        observed = sha256(source_root / relative)
        if observed != expected:
            raise RuntimeError(f"Pinned hash changed for {relative}: {observed}")
    return commit


def build_audit(source_root: Path, paper_pdf: Path, source_python: Path, output_dir: Path) -> dict[str, Any]:
    commit = verify_pins(source_root, paper_pdf)
    conformance = result_conformance()
    identities = paper_internal_identities()
    config = source_conformance(source_root)
    source = source_inventory(source_root)
    component, factors = run_native_component_checks(source_root, source_python)

    if len(source) != 49:
        raise RuntimeError(f"Expected 49 tracked source files, got {len(source)}")
    if Counter(row["status"] for row in conformance) != {
        "unavailable_missing_native_result_path": 474,
        "configuration_match_active_official_runner": 4,
        "configuration_not_reproduced_by_released_diagnostic_runner": 6,
    }:
        raise RuntimeError("Pinned numeric conformance boundary changed")
    if len(factors) != 5 or not all(row["native_parser_executable"] for row in factors):
        raise RuntimeError("Published formula parser diagnostic changed")

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "tables_2_9_conformance.csv", conformance)
    write_csv(output_dir / "paper_internal_identities.csv", identities)
    write_csv(output_dir / "source_mechanism_conformance.csv", config)
    write_csv(output_dir / "representative_factor_parser_audit.csv", factors)
    write_csv(output_dir / "released_source_inventory.csv", source)
    (output_dir / "native_synthetic_component.json").write_text(
        json.dumps(component, indent=2) + "\n", encoding="utf-8"
    )

    manifest: dict[str, Any] = {
        "audit": "AlphaMemo paper v1 Tables 2--9 versus pinned official source",
        "overall_status": "not_reproduced_native_synthetic_component_only",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_version": "arXiv:2606.20625v1",
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "source_commit_date": "2026-05-26",
        "paper_numeric_tables_audited": [2, 3, 4, 5, 6, 7, 8, 9],
        "paper_numeric_table_cells_total": 484,
        "paper_numeric_result_cells_total": 474,
        "paper_numeric_configuration_cells_total": 10,
        "paper_table_cell_counts": {"2": 140, "3": 48, "4": 6, "5": 182, "6": 80, "7": 8, "8": 5, "9": 15},
        "native_paper_result_cells_reproduced": 0,
        "paper_result_cells_unavailable": 474,
        "active_official_runner_configuration_cells_matched": 4,
        "paper_configuration_cells_not_reproduced_by_diagnostic_runner": 6,
        "paper_pairwise_internal_identity_checks": 69,
        "paper_pairwise_internal_identity_matches": 69,
        "paper_internal_identities_independent_reproductions": 0,
        "tracked_source_files_total": len(source),
        "native_source_tests_passed": 1,
        "native_synthetic_smoke_deterministic": True,
        "native_synthetic_smoke_paper_result_reproduction": False,
        "published_representative_formulas_native_parser_executable": 5,
        "published_representative_formula_metrics_reproduced": 0,
        "native_paper_data_snapshot_shipped": False,
        "native_paper_search_trajectories_shipped": False,
        "native_paper_factor_pools_shipped": False,
        "native_paper_predictions_or_returns_shipped": False,
        "native_paper_metric_outputs_shipped": False,
        "native_paper_prompt_response_or_cost_logs_shipped": False,
        "paper_ast_diff_mechanism_implemented_faithfully": False,
        "paper_parent_context_implemented_faithfully": False,
        "paper_active_runner_admission_threshold_matched": False,
        "paper_fixed_budget_size_disclosed": False,
        "paper_fixed_budget_and_ablation_runners_shipped": False,
        "audit_called_llm_or_external_data_api": False,
        "interpretation": (
            "The 49-file official release is executable at the synthetic-component level: its sole test passes, "
            "a pinned heuristic smoke run is deterministic, and all five paper formulas execute in the native "
            "parser on synthetic data. None of that reproduces the paper. No Qlib input snapshot, reported LLM "
            "trajectory, factor pool, prediction, return, or table output is shipped, leaving 0/474 result cells "
            "natively reproduced. The active official runner also uses ICIR threshold 0.02 instead of the paper's "
            "0.10 and does not release the residual/fixed-budget/ablation runs. Source inspection shows deeper "
            "mechanism drift: regex motif extraction instead of typed canonical AST differencing, a category-only "
            "memory key instead of the four-part parent context, a different confidence gate/warmup schedule, "
            "and successful-only DAG insertion rather than adding all evaluated children."
        ),
        "source_file_sha256": PINNED_SOURCE_SHA256,
    }

    report = f"""# AlphaMemo paper-level conformance audit

Overall verdict: **not reproduced**. The official release contains runnable,
deterministic search components, but none of the paper's native inputs,
trajectories, factor pools, predictions, returns, or table outputs.

## Primary sources

- Official paper: {PAPER_URL} (arXiv v1; SHA-256 `{PAPER_SHA256}`).
- Official source: {SOURCE_URL}, commit `{commit}` (2026-05-26).

## What genuinely passes

- The release's one smoke test passes under a compatible Python 3.12 environment.
- Two identical native synthetic runs produce the same SHA-256 and the documented
  12-step summary. This validates a deterministic heuristic component only.
- All five Table 9 formulas execute in the released formula parser on synthetic
  arrays. Their paper metrics cannot be computed without the paper CSI500 panel.
- The active runner matches the two markets, 20-day label, date splits, model alias,
  and all four balanced operating-point values printed in Table 4.
- Sixty-nine pairwise cross-table identities agree exactly. These are repeated
  printed values, never independent empirical reproductions.

## Why the paper is not replicated

- Across Tables 2--9 there are **484 numeric experimental cells**: 474 results and
  10 configuration cells. **0/474 result cells** have a native released result path.
  Four balanced configuration cells match the official runner; configuration is
  not performance.
- No Qlib CSI500/S&P500 snapshot, exact universe history, LLM request/response log,
  search trajectory, admitted pool, selected-factor artifact, prediction, holding,
  daily return, Qlib recorder, baseline output, random seed run, or table CSV is
  tracked. The current-download data builders cannot recreate the authors' frozen
  data state.
- The advertised `run_main.sh` uses `SUCCESS_ICIR=0.02`, while the paper specifies
  an admission threshold of 0.10. It runs only one balanced AlphaMemo seed; no exact
  residual, fixed-budget, eight-baseline, or NoGate/AbsOLM/ManualMut/NoAPV runner is
  released. The paper does not disclose the numeric fixed discovery budget.
- The paper describes typed, canonical AST differencing with insert/delete/replace/
  move/parameter edit scripts. Released motif extraction uses regex-derived sets of
  operator names, windows, and features. The selected label is also supplied to the
  generator as a mutation command, contrary to the paper's claim that labels are
  observed after generation rather than hand-written commands.
- The paper context is `(category, quality bucket, depth bucket, retrieval bucket)`;
  released memory is keyed only by `(category, motif)`. Its residual baseline,
  confidence formula, warmup schedule, and balanced APV selection differ from the
  equations, and only admitted successes enter the DAG although the paper says all
  evaluated children enter the ledger.

## Honest boundary

The native synthetic smoke, parser execution, matching arguments, and internal
paper identities remain component evidence. They receive zero paper-result credit.
Run `scripts/audit_alphamemo_paper.py` to regenerate this package; use `--strict`
to fail until the exact paper inputs, trajectories, pools, outputs, mechanisms, and
all 474 result cells are independently reproduced.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(os.environ.get("ALPHAMEMO_SOURCE_ROOT", "/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_source")),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(os.environ.get("ALPHAMEMO_PAPER_PDF", "/nfs/roberts/scratch/pi_btk22/zc362/alphamemo_paper.pdf")),
    )
    parser.add_argument(
        "--source-python",
        type=Path,
        default=Path(os.environ.get("ALPHAMEMO_SOURCE_PYTHON", DEFAULT_SOURCE_PYTHON)),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/alphamemo",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(),
        args.paper_pdf.resolve(),
        args.source_python.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
