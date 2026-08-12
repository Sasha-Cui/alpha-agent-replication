#!/usr/bin/env python3
"""Build a fail-closed paper/source audit for FactorMiner.

The official arXiv source discloses 110 formulas and all rendered manuscript
figures, but no author-attributable runtime, data, prompts, model calls, or raw
results.  A later unaffiliated implementation can parse and evaluate the exact
printed formulas on synthetic inputs.  That is useful component evidence only:
its normalized catalog is materially different and it receives no native
FactorMiner experiment or result credit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/factorminer_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/factorminer"
WORK_ID = "CensusArxiv260214670"
SYSTEM_ID = "SYS-FACTOR-MINER"
ARXIV_ID = "2602.14670"
INDEPENDENT_COMMIT = "201309cfe3df51f84af8eeb509354d3853ae512a"

PINS = {
    "primary/arxiv-abs.html": "9c2407faad50295bb64ccd4672f52e47c840425539b3d057537fb841bbb7e6b3",
    "primary/arxiv-api.xml": "e89d8341fc41b540324a17f0700983a2a973eac642d3d35ee58ce2e050aebc8c",
    "primary/arxiv-v1.pdf": "14d1a3f7752a06284c6f5aef1e5cbdb857293fab8b6d5d6a6a3987679493ff72",
    "primary/arxiv-v1.tar": "161b8f7234b47eef3848153cfc9af2e6416f5132a22ad72dada1401a95eb5788",
    "primary/gemini-3-flash-release.html": "b5814a1f5503fe921c92c38e02da0b606a3fd6fae368bc13b244164f0ae472bf",
    "rebuilt/arxiv-v1-source-rebuilt.pdf": "3710dceb2c87c26a01bca23d0cb93f16f3098289b41b7e5aa4614a464ef236a3",
    "build/pass3.log": "9bb30556eb87b7eb38c4ad577358d849888297e7a83a251daded0e431da16045",
    "discovery/repositories-title.json": "63186d6b1a7d20d1dd3b0b6bbb238e4b81d975a4fc2f7871a4d7cd3fbb273841",
    "discovery/code-arxiv.json": "b398d37d0430d24cf2a280280d01e8826e67f6bd55a301a67e1064a5f48417ae",
    "discovery/code-title.json": "c72745a4174a44a23a21b4c2d2d96c39291dd33796a4a399ff3d7c9418df3a16",
    "discovery/commits-wang.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/commits-xu.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/commits-zhang.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/mini_repo.json": "6c68f728883e2c30701863ad7b79ae540bb8e2150ca922bc293ee8831e59565e",
    "discovery/mini_user.json": "6f040823ddad179867ef8ae7fb29feebd070c8e9c9ad6aecfc941d677f7eba78",
    "discovery/minihellboy/commit.txt": "055deecc3fa08bee7273cb131f062eab66984efd7267b4736cd88720fdd55b09",
    "discovery/minihellboy/factorminer-201309c.tar.gz": "62ecb74beb59f08c5f2233b9a773932c6034ef65e31007d457387c194e55848c",
    "discovery/minihellboy/exact-paper-formula-smoke.json": "660f44e75e10dd3c7ef65f05992eb75c4b1f0631f509f10b9deeb9c7463a5a9f",
    "discovery/minihellboy/catalog-comparison.json": "22525533fd6c4e66628980491711ee8fdd64139b32c8fa3112350173f4d321dd",
    "discovery/heatmap.txt": "21089e90a94b01ecfff5ef22d98ff3e2b21634b1682c5260aa4102edbb4c7e9b",
    "discovery/heatmap-appendix-name-comparison.json": "a00f726f20e8346d6d297398b0c5d7e8d6c8ec7ff7a8714ea1d974ff57836c41",
}

SOURCE_TREE = ("dba5118c046871e7ebf74c0cd38d66ae4b93544680d49b80224b77699827053a", 33)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(path: Path) -> tuple[str, int]:
    rows = []
    files = sorted(item for item in path.rglob("*") if item.is_file())
    for item in files:
        rows.append(f"{item.relative_to(path)}\0{sha256(item)}\n")
    return hashlib.sha256("".join(rows).encode()).hexdigest(), len(files)


def safe_tar(path: Path) -> None:
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe archive member: {member.name}")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty ledger: {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    actual_tree = tree_digest(scratch / "source")
    if actual_tree != SOURCE_TREE:
        raise ValueError(f"source tree mismatch: {actual_tree} != {SOURCE_TREE}")
    safe_tar(scratch / "primary/arxiv-v1.tar")
    safe_tar(scratch / "discovery/minihellboy/factorminer-201309c.tar.gz")
    html = (scratch / "primary/arxiv-abs.html").read_text(errors="replace")
    for marker in ("Submitted on 16 Feb 2026", "2602.14670v1", "Yanlong Wang"):
        if marker not in html:
            raise ValueError(f"arXiv marker changed: {marker}")
    release = (scratch / "primary/gemini-3-flash-release.html").read_text(errors="replace")
    if 'article:published_time" content="2025-12-17"' not in release:
        raise ValueError("Gemini 3 Flash release marker changed")
    log = (scratch / "build/pass3.log").read_text(errors="replace")
    if "Output written on main.pdf (20 pages" not in log:
        raise ValueError("official source rebuild did not finish at 20 pages")
    repo = json.loads((scratch / "discovery/mini_repo.json").read_text())
    user = json.loads((scratch / "discovery/mini_user.json").read_text())
    if repo["full_name"] != "minihellboy/factorminer" or repo["created_at"] != "2026-02-26T13:40:58Z":
        raise ValueError("independent repository identity changed")
    if user["login"] != "minihellboy" or user["name"] != "aaron":
        raise ValueError("independent repository owner identity changed")
    if INDEPENDENT_COMMIT not in (scratch / "discovery/minihellboy/commit.txt").read_text():
        raise ValueError("independent implementation commit marker changed")
    return {"source_files": SOURCE_TREE[1]}


def parse_formulas(tex: str) -> list[dict[str, str]]:
    rows = []
    pattern = re.compile(r"^(\d{3}) & (.*?) & \\texttt\{(.*)\} \\\\$", re.M)
    for match in pattern.finditer(tex):
        rows.append(
            {
                "factor_id": match.group(1),
                "name": match.group(2).replace(r"\_", "_"),
                "formula": match.group(3).replace(r"\$", "$"),
            }
        )
    if len(rows) != 110 or len({row["formula"] for row in rows}) != 110:
        raise ValueError(f"expected 110 unique printed formulas, found {len(rows)}")
    return rows


def formula_rows(scratch: Path, tex: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    formulas = parse_formulas(tex)
    smoke = json.loads(
        (scratch / "discovery/minihellboy/exact-paper-formula-smoke.json").read_text()
    )
    comparison = json.loads(
        (scratch / "discovery/minihellboy/catalog-comparison.json").read_text()
    )
    if len(smoke) != 110 or len(comparison) != 110:
        raise ValueError("independent formula evidence must contain 110 rows")
    if not all(item["parsed"] and item["evaluated"] and item["finite"] > 0 for item in smoke):
        raise ValueError("an exact printed formula did not execute in the pinned smoke run")
    exact_ids = {item["id"] for item in comparison if item["formula_exact"]}
    if exact_ids != {"006", "046"}:
        raise ValueError(f"normalized-catalog exact-formula boundary changed: {exact_ids}")
    rows = []
    for formula, result in zip(formulas, smoke):
        if formula["factor_id"] != result["id"] or formula["formula"] != result["formula"]:
            raise ValueError(f"formula smoke lineage mismatch: {formula['factor_id']}")
        rows.append(
            {
                **formula,
                "printed_syntax_recovered": True,
                "independent_exact_syntax_parsed": True,
                "independent_synthetic_evaluation_completed": True,
                "finite_synthetic_values": result["finite"],
                "semantic_operator_contract_author_released": False,
                "author_native_runtime_used": False,
                "paper_market_data_used": False,
                "reported_result_lineage_verified": False,
                "paper_result_credit": False,
            }
        )
    operators = sorted(
        set(re.findall(r"(?<![$])\b([A-Za-z][A-Za-z0-9_]*)\s*\(", "\n".join(x["formula"] for x in formulas)))
    )
    if len(operators) != 39:
        raise ValueError(f"expected 39 operators in printed formulas, found {len(operators)}")
    return rows, {
        "printed_formula_count": 110,
        "printed_formula_operator_names": operators,
        "independent_exact_formula_parse_count": 110,
        "independent_exact_formula_synthetic_evaluation_count": 110,
        "independent_normalized_catalog_count": 110,
        "independent_normalized_catalog_exact_formula_matches": 2,
        "independent_normalized_catalog_exact_name_matches": 3,
        "independent_commit": INDEPENDENT_COMMIT,
        "author_native_code_used": False,
        "paper_result_credit": False,
    }


def clean_number(value: str) -> float:
    clean = value.replace("$", "").replace(r"\%", "").replace("%", "")
    clean = clean.replace(r"\textbf{", "").replace(r"\underline{", "").replace("}", "")
    clean = clean.replace(r"\times", "e").replace("−", "-").replace("$-$", "-")
    match = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?(?:\s*e\s*10\^\{?[-+]?\d+\}?)?", clean)
    if not match:
        raise ValueError(f"numeric value missing: {value}")
    token = match.group().replace(",", "").replace(" ", "")
    power = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)e10\^\{?([-+]?\d+)\}?", token)
    return float(power.group(1)) * 10 ** int(power.group(2)) if power else float(token)


def result_cell(table: str, identity: str, metric: str, rendered: str) -> dict[str, Any]:
    return {
        "table": table,
        "identity": identity,
        "metric": metric,
        "rendered_value": rendered,
        "numeric_value": clean_number(rendered),
        "native_pipeline_executed": False,
        "native_result_regenerated": False,
        "paper_result_credit": False,
    }


def main_table_rows(table_tex: str) -> list[dict[str, Any]]:
    datasets = ("CSI500", "CSI1000", "HS300", "Crypto")
    methods = ("RF", "Alpha101 Classic", "Alpha101 Adapted", "GPLearn", "AlphaForge", "AlphaAgent", "FactorMiner")
    metrics = ("Library IC", "Library ICIR", "Avg abs rho", "EW IC", "EW ICIR", "ICW IC", "ICW ICIR", "Lasso IC", "Lasso ICIR", "XGB IC", "XGB ICIR")
    body = table_tex.split(r"\midrule", 1)[1].rsplit(r"\bottomrule", 1)[0]
    dataset = ""
    rows = []
    method_index = 0
    for raw in body.splitlines():
        if r"\multirow{7}" in raw:
            match = re.search(r"\\textbf\{(CSI500|CSI1000|HS300|Crypto)\}", raw)
            if not match:
                raise ValueError("main table dataset marker missing")
            dataset = match.group(1)
            method_index = 0
            continue
        if not raw.lstrip().startswith("&"):
            continue
        cells = [cell.strip() for cell in raw.split("&")]
        if len(cells) != 13:
            continue
        values = cells[2:]
        values[-1] = values[-1].split(r"\\", 1)[0].strip()
        if len(values) != 11:
            raise ValueError("main table result row width changed")
        method = methods[method_index]
        method_index += 1
        for metric, value in zip(metrics, values):
            rows.append(result_cell("main_results_top40", f"{dataset}/{method}", metric, value))
    if len(rows) != 308 or set(datasets) != {row["identity"].split("/")[0] for row in rows}:
        raise ValueError(f"expected 308 main result cells, found {len(rows)}")
    return rows


def fixed_table_rows() -> list[dict[str, Any]]:
    rows = []
    for identity, values in {
        "CsRank": ("93", "3.6", "26"),
        "TsRank": ("97", "6.0", "17"),
        "Rolling Corr": ("76", "11", "6.8"),
        "Rolling Std": ("13", "3.4", "3.7"),
        "TsDecay": ("45", "5.0", "9"),
    }.items():
        for metric, value in zip(("CPU ms", "GPU ms", "Speedup"), values):
            rows.append(result_cell("gpu_speedup", identity, metric, value))
    for identity, values in {
        "IC Mean": ("0.1451", "0.1496", "0.1400"),
        "ICIR": ("1.2053", "1.2430", "1.1933"),
        "IC Win Rate": ("85.0%", "85.8%", "84.8%"),
        "Q1 Return": ("-0.0422%", "-0.0441%", "-0.0406%"),
        "Q5 Return": ("0.0603%", "0.0619%", "0.0564%"),
        "L-S Return": ("0.0513%", "0.0531%", "0.0486%"),
        "L-S Cumulative": ("23.72", "26.67", "19.84"),
        "Monotonicity": ("1.0", "1.0", "1.0"),
        "Avg Turnover": ("20.14%", "20.43%", "19.67%"),
    }.items():
        for metric, value in zip(("Equal-Weight", "IC-Weighted", "Orthogonal"), values):
            rows.append(result_cell("combination_110", identity, metric, value))
    for identity, values in {
        "Selected Factors": ("8", "18", "110"),
        "IC Mean": ("0.1562", "0.1556", "0.1633"),
        "ICIR": ("1.2039", "1.3827", "1.4929"),
        "IC Win Rate": ("87.2%", "88.5%", "92.6%"),
        "Q1 Return": ("-0.0604%", "-0.0485%", "-0.0609%"),
        "Q5 Return": ("0.0678%", "0.0625%", "0.0804%"),
        "L-S Return": ("0.0642%", "0.0556%", "0.0708%"),
        "L-S Cumulative": ("54.69", "31.51", "82.63"),
        "Monotonicity": ("1.0", "1.0", "1.0"),
        "Avg Turnover": ("19.92%", "20.02%", "19.32%"),
    }.items():
        for metric, value in zip(("Lasso", "Stepwise", "XGBoost"), values):
            rows.append(result_cell("selection_110", identity, metric, value))
    for identity, value in zip(("006", "002", "079", "040", "011", "045", "009", "022"), ("3.23e-4", "7.23e-5", "2.58e-5", "1.14e-5", "8.18e-6", "7.18e-6", "4.28e-6", "2.59e-6")):
        rows.append(result_cell("lasso_selected", identity, "Coefficient", value))
    step_values = (
        ("0.129", "0.150", "1.163", None), ("0.109", "0.145", "1.184", "+0.021"),
        ("0.103", "0.145", "1.234", "+0.050"), ("0.100", "0.145", "1.271", "+0.037"),
        ("0.097", "0.145", "1.296", "+0.025"), ("0.095", "0.145", "1.299", "+0.003"),
        ("0.092", "0.148", "1.304", "+0.005"), ("0.090", "0.147", "1.304", "+0.000"),
        ("0.082", "0.150", "1.308", "+0.004"), ("0.078", "0.151", "1.315", "+0.007"),
        ("0.073", "0.150", "1.316", "+0.001"), ("0.066", "0.153", "1.357", "+0.041"),
        ("0.063", "0.153", "1.366", "+0.009"), ("0.063", "0.154", "1.370", "+0.004"),
        ("0.055", "0.154", "1.370", "+0.000"), ("0.055", "0.154", "1.378", "+0.008"),
        ("0.049", "0.155", "1.381", "+0.003"), ("0.047", "0.156", "1.383", "+0.002"),
    )
    for step, values in enumerate(step_values, 1):
        for metric, value in zip(("Individual IC", "Combined IC", "ICIR", "Delta ICIR"), values):
            if value is not None:
                rows.append(result_cell("stepwise_trajectory", str(step), metric, value))
    xgb = ("6.04%", "4.06%", "3.59%", "3.55%", "3.03%", "2.27%", "2.26%", "2.15%", "1.62%", "1.57%", "1.47%", "1.46%", "1.44%", "1.41%", "1.34%", "1.24%", "1.20%", "1.16%", "1.16%", "1.11%")
    for rank, value in enumerate(xgb, 1):
        rows.append(result_cell("xgboost_importance", str(rank), "Importance", value))
    for metric, value in {
        "IC Mean": "0.1087", "ICIR": "0.9422", "IC Win Rate": "80.1%",
        "Q1 Return": "-0.0380%", "Q5 Return": "0.0402%", "L-S Return": "0.0390%",
        "L-S Cumulative": "10.57", "Monotonicity": "1.0", "Avg Turnover": "15.69%",
    }.items():
        rows.append(result_cell("factor046_tearsheet", "046", metric, value))
    if len(rows) != 180:
        raise ValueError(f"expected 180 fixed appendix result cells, found {len(rows)}")
    return rows


def figure_rows() -> list[dict[str, Any]]:
    specs = (
        ("library_correlation_heatmap", 1, 12100, "110x110 printed matrix; 6,105 upper-triangle-plus-diagonal positions"),
        ("memory_ablation", 2, 10, "counts and rates for have/no-memory variants"),
        ("backend_efficiency", 2, 24, "four operators and four factors across three backends"),
        ("combination_ic", 3, 0, "three IC time-series/distribution panels"),
        ("combination_quantiles", 3, 0, "three quintile-return/cumulative panels"),
        ("selection_ic", 3, 0, "three IC time-series/distribution panels"),
        ("selection_quantiles", 3, 0, "three quintile-return/cumulative panels"),
        ("cost_pressure", 6, 0, "six methods, each with five cost curves on linear and log axes"),
        ("factor046_tearsheet", 4, 0, "IC, quantile, distribution, and turnover panels"),
    )
    return [
        {
            "figure": name,
            "empirical_vector_pdf_panels": panels,
            "visible_numeric_annotations": annotations,
            "description": description,
            "underlying_numeric_array_released": False,
            "author_native_figure_regenerated": False,
            "paper_result_credit": False,
        }
        for name, panels, annotations, description in specs
    ]


def heatmap_audit(scratch: Path) -> dict[str, Any]:
    rows = []
    for line in (scratch / "discovery/heatmap.txt").read_text().splitlines():
        values = [float(value) for value in re.findall(r"(?<![\w.])-?\d+\.\d+", line)]
        if len(values) == 110:
            rows.append(values)
    if len(rows) != 110 or any(len(row) != 110 for row in rows):
        raise ValueError("heatmap extraction is not 110x110")
    if any(rows[i][i] != 1.0 for i in range(110)):
        raise ValueError("heatmap diagonal changed")
    if any(rows[i][j] != rows[j][i] for i in range(110) for j in range(110)):
        raise ValueError("heatmap is not exactly symmetric at printed precision")
    offdiag = [abs(rows[i][j]) for i in range(110) for j in range(i + 1, 110)]
    full = [abs(value) for row in rows for value in row]
    names = json.loads((scratch / "discovery/heatmap-appendix-name-comparison.json").read_text())
    mismatches = [item["id"] for item in names if not item["truncated_prefix_match"]]
    if mismatches != ["012", "016", "040", "049", "051", "055", "107", "108", "109", "110"]:
        raise ValueError(f"heatmap catalog mismatch set changed: {mismatches}")
    return {
        "shape": [110, 110],
        "printed_numeric_annotations": 12100,
        "unique_offdiagonal_pairs": len(offdiag),
        "printed_mean_absolute_offdiagonal": sum(offdiag) / len(offdiag),
        "printed_mean_absolute_including_diagonal": sum(full) / len(full),
        "caption_claimed_average_absolute_correlation": 0.203,
        "pairs_at_or_above_admission_threshold_0_5": sum(value >= 0.5 for value in offdiag),
        "pairs_strictly_above_admission_threshold_0_5": sum(value > 0.5 for value in offdiag),
        "maximum_printed_absolute_offdiagonal": max(offdiag),
        "appendix_heatmap_name_prefix_matches": 100,
        "appendix_heatmap_name_mismatches": 10,
        "mismatching_factor_ids": mismatches,
        "raw_matrix_released": False,
        "result_lineage_verified": False,
    }


def method_rows() -> list[dict[str, str]]:
    values = (
        ("native_source", "missing", "official source contains manuscript TeX and rendered vector figures, not the FactorMiner runtime"),
        ("printed_factor_formulas", "complete_syntax_only", "110 unique formula strings are printed, but no author runtime or complete semantic operator contract links them to results"),
        ("operator_registry", "partial", "39 operator names occur in formulas; the paper says 60+ and lists representative categories, not exact implementations"),
        ("formula_semantics", "ambiguous", "Factor 001 uses Max/Min with a window-like constant although the operator table lists Max/Min as elementwise arithmetic; independent code normalizes these to TsMax/TsMin"),
        ("a_share_universes", "missing", "CSI500/CSI1000/HS300 named without constituent vintages, membership history, security identifiers, or inclusion date arrays"),
        ("crypto_universe", "missing", "64 major Binance assets named without asset list, market type, symbol snapshot, or eligibility rule"),
        ("market_data", "missing", "10-minute OHLCV/amount-like fields named; vendor for A shares, Binance endpoint, retrieval snapshot, adjustments, timezone, halts, and missing-data rules absent"),
        ("train_window", "partial", "2024 Q1-Q4 supplied without exact endpoints or timestamp array"),
        ("test_window", "partial", "2025 supplied without exact endpoints or timestamp array"),
        ("target", "partial", "next 10-minute open-to-close ratio named; bar alignment, session boundary, tradability, and execution timing absent"),
        ("prompts", "missing", "no exact system/user prompts, retrieved memory payloads, candidate responses, or parsing logs"),
        ("model", "partial", "Gemini 3.0 Flash named without immutable endpoint/version, requests, or provider snapshots"),
        ("model_parameters", "missing", "temperature, top-p, token budget, seed, retry, safety, and concurrency settings absent"),
        ("random_seeds", "missing", "no generation, baseline, selection, or repeated-run seeds"),
        ("memory_state", "partial", "recommended/forbidden summaries and one batch narrative are printed; exact evolving memory snapshots and trajectory ledger absent"),
        ("admission_rules", "partial", "thresholds and replacement inequalities printed; missing exact preprocessing, sign handling, ties, NaNs, and complete replacement implementation"),
        ("top40_freeze", "partial", "ranking/filter/fill prose supplied; exact selected IDs per method and frozen weight/sign artifacts absent"),
        ("baseline_implementations", "missing", "no candidate sets, code locks, seeds, search budgets, or full implementations for six displayed baselines"),
        ("alpha101_tuning", "partial", "up to ten parameter variants stated, but grids, tuning metric, candidate formulas, and selection records absent"),
        ("combination", "partial", "EW, historical-IC weighting, and Gram-Schmidt named; fit interval details, signs, normalization, and serialized weights absent"),
        ("selection", "partial", "Lasso, forward stepwise, and XGBoost named; hyperparameters, features, preprocessing, seeds, and model artifacts absent"),
        ("transaction_costs", "partial", "five bps settings and rendered curves supplied; turnover/execution convention and raw arrays absent"),
        ("runtime_environment", "missing", "no author lockfile, package versions, hardware/software details beyond A100/40 workers and broad libraries"),
        ("raw_results", "missing", "no signals, IC arrays, correlations, candidate logs, predictions, positions, returns, weights, or benchmark traces"),
        ("prospective_freeze", "missing", "Gemini 3 Flash became public 2025-12-17, so no literal pre-2025 model freeze is possible; no timestamped retrospective freeze is released"),
    )
    return [{"dimension": a, "status": b, "evidence": c} for a, b, c in values]


def consistency_rows(heatmap: Mapping[str, Any], main_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    values = {(r["identity"], r["metric"]): r["numeric_value"] for r in main_rows}
    methods = ("RF", "Alpha101 Classic", "Alpha101 Adapted", "GPLearn", "AlphaForge", "AlphaAgent", "FactorMiner")
    datasets = ("CSI500", "CSI1000", "HS300", "Crypto")
    metrics = ("Library IC", "Library ICIR", "Avg abs rho", "EW IC", "EW ICIR", "ICW IC", "ICW ICIR", "Lasso IC", "Lasso ICIR", "XGB IC", "XGB ICIR")
    wins_or_ties = 0
    strict_wins = 0
    for dataset in datasets:
        for metric in metrics:
            scores = [values[(f"{dataset}/{method}", metric)] for method in methods]
            factor = scores[-1]
            target = min(scores) if metric == "Avg abs rho" else max(scores)
            wins_or_ties += factor == target
            strict_wins += factor == target and scores.count(target) == 1
    if (wins_or_ties, strict_wins) != (29, 28):
        raise ValueError(f"main-table dominance accounting changed: {(wins_or_ties, strict_wins)}")
    xgb_sum = sum((6.04, 4.06, 3.59, 3.55, 3.03, 2.27, 2.26, 2.15, 1.62, 1.57, 1.47, 1.46, 1.44, 1.41, 1.34, 1.24, 1.20, 1.16, 1.16, 1.11))
    rows = (
        ("main_table_global_best_claim", "overbroad", f"FactorMiner is best or tied on {wins_or_ties}/44 dataset-metric columns and strictly best on {strict_wins}/44, not all columns"),
        ("main_vs_ensemble_prose", "protocol_or_version_mismatch", "CSI500 prose says FactorMiner EW/ICW ICIR 1.52/1.54 and Lasso/XGB 1.42/1.52 while the cited main Top-40 table says 1.29/1.31 and 1.21/1.29"),
        ("heatmap_caption_average", "does_not_match_printed_matrix", f"caption claims off-diagonal Avg abs rho 0.203; visible rounded matrix yields {heatmap['printed_mean_absolute_offdiagonal']:.6f} off-diagonal and {heatmap['printed_mean_absolute_including_diagonal']:.6f} including diagonal"),
        ("heatmap_admission_constraint", "visible_threshold_violations", f"printed matrix has {heatmap['pairs_strictly_above_admission_threshold_0_5']} unique pairs above 0.5 and {heatmap['pairs_at_or_above_admission_threshold_0_5']} at or above 0.5 despite the stated global abs-correlation constraint"),
        ("heatmap_formula_catalog_lineage", "catalog_mismatch", "10/110 heatmap factor labels do not prefix-match the same-ID appendix formula names: 012,016,040,049,051,055,107,108,109,110"),
        ("factor046_financial_logic", "formula_description_conflict", "printed formula branches between 3-bar close reversal and close-in-range reversal; prose instead says volume-price divergence and volatility-normalized VWAP deviation"),
        ("factor046_turnover_units", "hundredfold_display_conflict", "table reports 15.69% Avg Turnover while the source vector plot prints Avg Daily Turnover 1569.1%"),
        ("xgboost_top20_total", "arithmetic_conflict", f"20 printed importances sum to {xgb_sum:.2f}%, not the claimed 43.8%"),
        ("baseline_inventory", "setup_omission", "main table includes AlphaForge, but the experimental-setup baseline enumeration names only Alpha101 Classic/Adapted, RF, GPLearn, and AlphaAgent"),
        ("memory_ablation_denominators", "arithmetic_recoverable", "32/20%=160 and 96/60%=160 candidates; 14/32=43.75% and 53/96=55.21% rejection, implying 18 and 43 admitted as plotted"),
        ("gpu_appendix_vs_main_benchmark", "different_unreconciled_protocols", "appendix A100 table reports Python/GPU only with values unlike the main three-backend chart; shapes and benchmark protocol needed to reconcile them are absent"),
        ("model_test_chronology", "prospective_interpretation_impossible", "Gemini 3 Flash first became public 2025-12-17, inside the paper's unspecified full-year 2025 test window; retrospective holdout remains possible but unverified"),
    )
    return [{"check": a, "status": b, "detail": c} for a, b, c in rows]


def discovery_rows(scratch: Path) -> list[dict[str, Any]]:
    repos = json.loads((scratch / "discovery/repositories-title.json").read_text())
    arxiv = json.loads((scratch / "discovery/code-arxiv.json").read_text())
    title = json.loads((scratch / "discovery/code-title.json").read_text())
    commits = sum(
        json.loads((scratch / f"discovery/commits-{name}.json").read_text())["total_count"]
        for name in ("wang", "xu", "zhang")
    )
    return [
        {"route": "arxiv_source", "result_count": 33, "finding": "manuscript TeX and 26 vector PDFs; no runtime, data, prompt, call, or raw-result archive", "attributable_native_artifact_recovered": False, "negative_search_limit": "describes pinned v1 source bundle only"},
        {"route": "github_repository_title", "result_count": repos["total_count"], "finding": "many generic/name matches; visible exact-description repositories are post-paper independent implementations", "attributable_native_artifact_recovered": False, "negative_search_limit": "bounded current indexed search; not proof about private, deleted, moved, or unindexed material"},
        {"route": "github_code_arxiv_id", "result_count": arxiv["total_count"], "finding": "visible matches are citations, indexes, or independent implementations", "attributable_native_artifact_recovered": False, "negative_search_limit": "GitHub code search caps visible results and is not proof of nonexistence"},
        {"route": "github_code_exact_title", "result_count": title["total_count"], "finding": "visible matches do not establish an author-attributable release", "attributable_native_artifact_recovered": False, "negative_search_limit": "bounded current indexed search only"},
        {"route": "github_academic_author_emails", "result_count": commits, "finding": "zero public commit matches for the first three Tsinghua academic emails", "attributable_native_artifact_recovered": False, "negative_search_limit": "email search cannot rule out aliases, private repositories, or different accounts"},
        {"route": "minihellboy_factorminer", "result_count": 1, "finding": "post-paper implementation by aaron/proton account; documentation says it follows/extends the paper and lacks paper datasets/baselines/A100 results", "attributable_native_artifact_recovered": False, "negative_search_limit": "absence of a public author link is not proof of identity; no affirmative attribution evidence was found"},
    ]


def build(scratch: Path, output: Path) -> dict[str, Any]:
    validated = validate_inputs(scratch)
    table_tex = (scratch / "source/main_results_table.tex").read_text(encoding="utf-8")
    formula_ledger, component = formula_rows(scratch, (scratch / "source/appendix_factors.tex").read_text())
    main_results = main_table_rows(table_tex)
    results = main_results + fixed_table_rows()
    if len(results) != 488:
        raise ValueError(f"expected 488 numeric table result cells, found {len(results)}")
    figures = figure_rows()
    heatmap = heatmap_audit(scratch)
    methods = method_rows()
    consistency = consistency_rows(heatmap, main_results)
    discovery = discovery_rows(scratch)

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "formula_component_ledger.csv", formula_ledger)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(output / "discovery_evidence.csv", discovery)
    write_json(output / "independent_formula_execution.json", component)
    write_json(output / "heatmap_audit.json", heatmap)
    write_json(
        output / "model_release_chronology.json",
        {
            "paper_train_window": "2024-Q1 through 2024-Q4",
            "paper_test_window": "2025 (exact endpoints absent)",
            "paper_model_identifier": "Gemini 3.0 Flash",
            "closest_public_primary_record": "Google Gemini 3 Flash",
            "first_public_date": "2025-12-17",
            "literal_model_available_before_2025_test_window": False,
            "retrospective_data_layer_holdout_possible": True,
            "retrospective_data_layer_holdout_verified": False,
        },
    )
    write_json(
        output / "source_provenance.json",
        {
            "arxiv": {"id": ARXIV_ID, "version": "v1", "submitted": "2026-02-16", "pages": 20, "source_files": validated["source_files"], "rebuild_pages": 20, "rebuild_token_multiset_jaccard": 0.9997785405824383, "visual_qa": {"pages_inspected": 20, "unreadable_clipped_or_overlapping_pages": 0}},
            "independent_implementation": {"repository": "https://github.com/minihellboy/factorminer", "commit": INDEPENDENT_COMMIT, "repository_created": "2026-02-26", "paper_submitted": "2026-02-16", "owner_public_name": "aaron", "owner_public_email_domain": "proton.me", "author_attribution_evidence_recovered": False, "classification": "unaffiliated_post_paper_interpretation"},
            "release_boundary": {"attributable_native_implementation_recovered": False, "exact_printed_formula_syntax_recovered": True, "complete_author_operator_semantics_recovered": False, "paper_data_recovered": False, "prompts_or_model_calls_recovered": False, "raw_result_arrays_recovered": False, "reported_results_linked_to_appendix_formula_catalog": False, "bounded_negative_search_is_proof_of_nonexistence": False},
        },
    )

    readme = """# FactorMiner paper-faithfulness audit

This fail-closed audit pins the sole official arXiv edition, rebuilds its
unmodified 20-page source at 0.999779 extracted-token multiset Jaccard, and
visually checks all 20 published pages.  It inventories 488 numeric table-result
cells, a 110x110 printed correlation heatmap (12,100 annotations), 24 additional
efficiency annotations, 10 memory-ablation annotations, and every empirical
vector source panel.  None is regenerated by an author-native experiment.

## What is genuinely reproducible

The paper discloses 110 unique formula strings.  At pinned commit
`201309cfe3df51f84af8eeb509354d3853ae512a`, a post-paper independent
implementation parses and evaluates all 110 exact strings on deterministic
synthetic OHLCV arrays, each producing finite values.  This establishes syntax
and conditional component executability only.  It does **not** establish the
authors' operator semantics, market results, or pipeline: the paper gives only
representative definitions for a claimed 60+ operator registry, Factor 001's
`Max/Min(..., 48)` is semantically ambiguous, and the independent repository's
own normalized 110-factor catalog matches only 2/110 printed formulas exactly.
It is therefore classified as an unaffiliated interpretation and receives zero
native FactorMiner result credit.

## Honest end-to-end boundary

The native FactorMiner experiment is **not reproduced**.  No attributable
runtime, A-share/Binance data snapshot, point-in-time constituent lists, exact
date arrays, prompts, memory states, Gemini requests, generated/rejected
candidates, baseline implementations, selected Top-40 IDs, fitted weights or
models, seeds, environment lock, signals, predictions, positions, returns, or
raw result arrays are released.  Gemini 3 Flash first became public on
2025-12-17, inside the paper's unspecified full-year 2025 test window; a later
retrospective 2024-to-2025 holdout is possible, but no timestamped freeze or
runtime evidence verifies it.

The independent release appeared ten days after the paper and publicly
identifies its owner as `aaron` with a Proton address, while the manuscript lists
six academic authors and addresses.  Its own reproducibility contract says it
follows/extends the paper and lacks the exact paper panels, faithful external
baselines, and A100 evidence.  No affirmative author link was recovered, so it
cannot be promoted to native code.  Bounded negative searches are not proof that
private, deleted, moved, or unindexed material never existed.

## Material internal findings

- The 110-factor heatmap does not fully identify the formula appendix catalog:
  10 same-ID labels conflict (012, 016, 040, 049, 051, 055, 107--110).  Thus
  printed formulas cannot safely be assumed to have generated all reported
  figures/tables.
- The caption claims off-diagonal Avg absolute correlation 0.203.  The visible
  symmetric matrix yields 0.193169 off diagonal (0.200504 only when including
  its 110 unit diagonal cells), and contains 15 unique pairs strictly above the
  stated 0.5 admission constraint.
- “Performs best ... across all four markets” is overbroad: FactorMiner is best
  or tied on 29/44 displayed dataset-metric columns, strictly best on 28/44.
- CSI500 ensemble prose gives 1.52/1.54 and 1.42/1.52 while its cited main table
  gives 1.29/1.31 and 1.21/1.29, indicating mixed protocols or result versions.
- Factor 046's prose describes different branches from its printed formula, and
  its table reports 15.69% turnover while its source plot prints 1569.1%.
- The 20 printed XGBoost importances sum to 43.13%, not the claimed 43.8%.
- AlphaForge appears in the main table but is omitted from the experimental
  setup's enumerated baselines.

These findings do not prove the reported effects are false.  They mean the
current public package supports strong document/formula-specification evidence,
not an independently verified paper-level market replication.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")

    manifest: dict[str, Any] = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "official_versions_audited": ["v1"],
        "official_pdf_and_source_recovered": True,
        "official_document_rebuild_completed": True,
        "official_pages_visually_checked": 20,
        "printed_formula_syntax_recovered": 110,
        "independent_exact_formula_synthetic_executions": 110,
        "author_native_formula_executions": 0,
        "published_numeric_table_cells": len(results),
        "published_heatmap_numeric_annotations": 12100,
        "published_other_exact_figure_annotations": 34,
        "empirical_vector_pdf_panels": sum(row["empirical_vector_pdf_panels"] for row in figures),
        "native_numeric_table_cells_regenerated": 0,
        "native_heatmap_cells_regenerated": 0,
        "native_figure_panels_regenerated": 0,
        "attributable_native_implementation_recovered": False,
        "full_end_to_end_pipeline_reproduced": False,
        "retrospective_data_layer_holdout_verified": False,
        "paper_evidence_route": "paper_only_formula_syntax_component_no_native_results",
        "output_sha256": {},
    }
    output_files = sorted(path for path in output.iterdir() if path.is_file() and path.name != "manifest.json")
    manifest["output_sha256"] = {path.name: sha256(path) for path in output_files}
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
    if args.strict and not manifest["full_end_to_end_pipeline_reproduced"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
