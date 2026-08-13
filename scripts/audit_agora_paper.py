#!/usr/bin/env python3
"""Build a fail-closed primary-source audit for the Agora/SJS paper."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import tarfile
import warnings
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

import numpy as np
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/agora_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/agora"
WORK_ID = "CensusArxiv260629194"
SYSTEM_ID = "SYS-AGORA"
ARXIV_ID = "2606.29194"

PINS = {
    "primary/official.pdf": "8e340c26444145bcb00c0f8761b9adc4404c757ca741ffc9c3281ef88833a40a",
    "primary/official.txt": "f72aafd19cfbd68c309e76a9e497f9ad6c5db27dbe69b2b06c9f8145c0260a23",
    "primary/source.tar": "5e77d5f98b8e60a0d6b425a318e314274480e4a46f03eab10d5be30c05c182e1",
    "primary/rebuilt.pdf": "594363bef7228dd131a59edd5ab99cd21af08018702e0f46d337db814e5b4fff",
    "primary/rebuilt.txt": "38a3bf4c39c6bc1f9a91a027bc027bedd4993fed2e106b483901e8d8a0d7f484",
    "primary/arxiv-api.xml": "7f97361faf162b7cab88d169aec472852c26329556624bfd812b2f0d15c27a31",
    "primary/arxiv-abs.html": "70ed3f4ef91a30864d963461a0ec2b8e017e731a10a4391c844670becfa2b66b",
    "discovery/github-repos-arxiv.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-repos-title.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-repos-sjs.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-repos-agora-alphagen.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-code-top-alphas-audit.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-code-incremental-ppo.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-code-avg-pred-corr.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-code-author-email.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-code-metric-name.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery/github-commits-author-email.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-users-domain.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-repos-pandaai-domain.json": "eb398af106b05ea130756cceb862e5f655430e6a2e700807859a243c0a07d6c5",
    "discovery/huggingface-models.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-datasets.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/pandaai-domain.html": "ee6a4d41f80eb9796a353ce5d560080aa72f61ccecfa2df7c2735e47f6583e6f",
    "discovery/quantskills-repo.json": "3dca0a2a3cce393757a2a11d6d862703f478dc9e12ead841bf823a03d2f4dbc0",
    "discovery/quantskills-tree.json": "46938d851cb3cbc0a837da2fb8a821a1d9c6d06076437a4918b4b95e9c5b5116",
    "discovery/quantskills-readme.md": "576d8df242804d0763ac0171491a6dc8efd7b15165f00096ffa6eee845ebf2df",
}

# One result unit is one populated quantitative table cell. A compound cell
# such as mean +/- SD or a confidence interval remains one displayed unit.
TABLE_SPECS = {
    "tab:headline": ("sections/05_results.tex", (1, 2, 3, 4, 5, 6), 48),
    "tab:sig_summary": ("sections/05_results.tex", (1, 2), 14),
    "tab:libstate": ("sections/05_results.tex", (1, 2, 3, 4), 40),
    "tab:decomp": ("sections/05_results.tex", (1,), 9),
    "tab:cost_sensitivity": ("figures/cost_sensitivity.tex", (1, 2, 3, 4, 5), 20),
    "tab:multiseed": ("figures/multi_seed_table.tex", (3, 4, 5, 6), 8),
    "tab:nw_ci": ("figures/nw_ci_table.tex", (1, 2, 3, 4), 31),
    "tab:robustness": ("figures/robustness_topk.tex", (1, 2, 3, 4), 32),
    "tab:rolling": ("figures/rolling_holdout.tex", (1, 2, 3, 4, 5, 6, 7), 49),
    "tab:sigtests": ("figures/sig_table.tex", (1, 2, 3, 4, 5, 6), 42),
}
EXPECTED_RESULT_UNITS = 293


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
    if len(files) != 25:
        raise ValueError(f"paper source file count changed: {len(files)}")
    return files


def source_text(files: Mapping[str, bytes], path: str) -> str:
    return files[path].decode("utf-8")


def table_environment(source: str, label: str) -> str:
    marker = rf"\label{{{label}}}"
    location = source.index(marker)
    begin = source.rfind(r"\begin{table", 0, location)
    end = source.index(r"\end{table}", location) + len(r"\end{table}")
    if begin < 0:
        raise ValueError(f"table start missing: {label}")
    return source[begin:end]


def clean_tex(value: str) -> str:
    value = value.replace(r"\midrule", " ").replace(r"\textbf", " ")
    value = value.replace(r"$-$", "-").replace(r"\%", "%")
    value = value.replace(r"\{", "{").replace(r"\}", "}")
    value = re.sub(r"\\(?:textsubscript|mathrm|text)\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"[{}$]", "", value)
    return " ".join(value.split())


def table_data_rows(environment: str) -> list[list[str]]:
    match = re.search(r"\\begin\{tabular\}\{[^\n]*\}(.*?)\\end\{tabular\}", environment, re.S)
    if match is None:
        raise ValueError("tabular body missing")
    rows: list[list[str]] = []
    for chunk in re.split(r"\\\\", match.group(1)):
        if "&" not in chunk or any(token in chunk for token in (r"\toprule", r"\bottomrule", r"\cmidrule")):
            continue
        rows.append([clean_tex(cell) for cell in chunk.split("&")])
    return rows


def result_rows(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    blocker = (
        "the author experiment package, RiceQuant/CSI1000 snapshot, factor pools, run state, "
        "daily returns, baseline outputs, and result generator are unrecovered"
    )
    for label, (path, columns, expected) in TABLE_SPECS.items():
        parsed = table_data_rows(table_environment(source_text(files, path), label))
        table_rows: list[dict[str, Any]] = []
        for row_index, cells in enumerate(parsed, 1):
            if not cells:
                continue
            row_label = cells[0]
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
    specs = (
        ("fig:sjs-arch", "figures/fig0_sjs_architecture.pdf", 0, 0, "SJS architecture schematic"),
        ("fig:nav", "figures/fig1_holdout_nav.pdf", 1, 8, "eight holdout NAV trajectories"),
        ("fig:per-alpha-box", "figures/fig2_per_alpha_sharpe.pdf", 1, 8, "eight per-alpha distributions"),
        ("fig:evol", "figures/fig3_evolution_timeline.pdf", 1, 2, "cumulative-pass and pass-rate series"),
        ("fig:abl-bar", "figures/fig4_ablation_bar.pdf", 1, 8, "eight portfolio-Sharpe bars"),
    )
    return [
        {
            "figure": figure,
            "source_asset": path,
            "source_asset_sha256": sha256_bytes(files[path]),
            "empirical_panels": empirical,
            "empirical_series_or_groups": series,
            "description": description,
            "author_rendered_asset_recovered": True,
            "underlying_numeric_array_recovered": False,
            "author_native_figure_regenerated": False,
            "paper_result_credit": False,
        }
        for figure, path, empirical, series, description in specs
    ]


def metric_blocks(files: Mapping[str, bytes]) -> list[str]:
    source = source_text(files, "sections/C_metric_source.tex")
    blocks = re.findall(r"\\begin\{verbatim\}\s*\n(.*?)\\end\{verbatim\}", source, re.S)
    if len(blocks) != 2:
        raise ValueError(f"promoted metric listing count changed: {len(blocks)}")
    return [block.rstrip() + "\n" for block in blocks]


def execute_metric(code: str, listing: str) -> dict[str, Any]:
    tree = ast.parse(code, filename=listing)
    imports = sorted(
        {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
    )
    namespace: dict[str, Any] = {}
    exec(compile(tree, listing, "exec"), namespace)
    compute = namespace["compute"]
    rng = np.random.default_rng(20260628)
    factors = rng.normal(size=(40, 50))
    returns = 0.015 * factors + rng.normal(scale=0.02, size=(40, 50))
    value = float(compute(factors, returns))
    repeat = float(compute(factors, returns))
    ordered = np.tile(np.arange(50, dtype=float), (40, 1))
    positive = np.tile(np.linspace(-0.02, 0.02, 50), (40, 1))
    negative = positive[:, ::-1]
    flat = np.zeros((40, 50), dtype=float)
    positive_value = float(compute(ordered, positive))
    negative_value = float(compute(ordered, negative))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        flat_value = float(compute(ordered, flat))
    small_value = float(compute(ordered[:5, :9], flat[:5, :9]))
    return {
        "listing": listing,
        "function": "compute",
        "source_lines": len(code.splitlines()),
        "imports": ";".join(imports),
        "ast_parse_passed": True,
        "paper_code_executed_verbatim": True,
        "controlled_shape": "40x50",
        "controlled_seed": 20260628,
        "controlled_value": f"{value:.16g}",
        "repeat_value": f"{repeat:.16g}",
        "deterministic": value == repeat,
        "finite_and_bounded": bool(np.isfinite(value) and -1.0 <= value <= 1.0),
        "positive_order_value": f"{positive_value:.16g}",
        "negative_order_value": f"{negative_value:.16g}",
        "flat_value": f"{flat_value:.16g}",
        "small_input_value": f"{small_value:.16g}",
        "direction_and_guard_checks_passed": bool(
            positive_value > 0.0 and negative_value < 0.0 and small_value == 0.0
        ),
        "author_native_pipeline_executed": False,
        "published_metric_result_regenerated": False,
        "paper_result_credit": False,
        "boundary": (
            "complete paper listing executed on a controlled panel; the author run, promotion history, "
            "and published predictive correlations were not regenerated"
        ),
    }


def metric_rows(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    names = ("monotonicity_score_v1", "excess_drawdown_penalty_v1")
    return [execute_metric(code, name) for name, code in zip(names, metric_blocks(files))]


def method_rows() -> list[dict[str, str]]:
    specs = (
        ("official paper and source", "complete", "arXiv v1 PDF and complete 25-file TeX bundle are pinned; all 42 official and rebuilt pages inspected"),
        ("claimed public release", "claimed_but_unrecovered", "contribution says implementation/baselines/audit/registries are released; Appendix A.8 says the release will include them and provides no URL"),
        ("market universe", "specified_not_released", "daily dynamic CSI1000 membership and 2,782-instrument RiceQuant post-adjusted panel are stated without the files or immutable export"),
        ("market schema", "substantially_specified", "OHLCV, reconstructed VWAP, membership, limit-up and suspension masks, next-open execution and daily frequency are stated"),
        ("temporal split", "specified", "train 2014-10--2019-12, test 2020-01--2025-12, holdout 2026-01--2026-05 with stated day counts"),
        ("prediction target", "specified", "five-day open-to-open target Ref(open,-6)/Ref(open,-1)-1 is stated"),
        ("agent topology", "substantially_specified", "five roles, nine LLM clients, three channels, role-scoped records, commit sequence and promotion rules are described"),
        ("exact prompts and model calls", "missing", "roles and one baseline prompt are described; system prompts, filled calls, responses, request IDs and immutable model snapshot are absent"),
        ("skill stores and state", "partial_with_count_conflict", "builtins and final counts are printed, but registries/stats, 78 rejected trial programs and all per-round transitions are absent; paper alternates eight and nine stores"),
        ("promoted metric programs", "complete_component", "two full Python listings are printed and both execute verbatim on controlled panels"),
        ("alpha programs and pools", "missing", "94 unique alphas, top-30 selection and AlphaGen vocabulary are stated; expressions, scores, pools and panels are absent"),
        ("PPO relay", "partially_specified", "MaskablePPO, 15,000 steps/round and key network settings are stated; weights, environments, checkpoints and trajectories are absent"),
        ("portfolio and execution", "partially_specified", "z-score top-30, ten deciles, five-day rebalance, next-open and nominal costs are stated; executable backtester, weights, fills and daily returns are absent"),
        ("baselines", "detailed_configs_no_runs", "seven baseline configurations are unusually detailed, but claimed implementations, inputs, factors, outputs and complete seeds are unrecovered"),
        ("randomness and run lineage", "insufficient", "seed 42 is stated for B1/B2 and a few extra B2/B6 seeds are summarized; full Agora seed, LLM nondeterminism and run IDs are absent"),
        ("compute", "partially_specified", "Python/PyTorch/CUDA/SDK/package versions, RTX5090/AMD Ryzen and approximate runtime/calls are stated without lockfile or logs"),
        ("raw empirical outputs", "missing", "293 table cells and four vector-rendered empirical panels are present without underlying arrays or result generator"),
    )
    return [{"dimension": dimension, "status": status, "detail": detail} for dimension, status, detail in specs]


def internal_rows() -> list[dict[str, str]]:
    specs = (
        ("release_claim_tense", "conflict", "Introduction says 'we release'; Appendix A.8 says the accompanying release 'will include' the artifacts; no URL appears in PDF or source"),
        ("skill_library_count", "conflict", "paper repeatedly says eight libraries, but Table libstate lists nine non-total libraries including macro_regime_library"),
        ("agora_per_alpha_median", "conflict", "headline table/figure say Agora median Sharpe 1.06; the significance table repeatedly uses 2.461 for the same top-30 holdout distribution"),
        ("b6_per_alpha_median", "conflict", "headline table says B6 median Sharpe +0.227; the significance table uses -0.000 for the same named distribution"),
        ("positive_baseline_count", "conflict", "prose says four of seven baselines are negative and only B2 has median above zero; headline table has four positive baselines and three negative"),
        ("holdout_observation_count", "conflict", "data/NAV/NW sections state 91 holdout days; rolling table attaches n=60 to the same 2026H1 Sharpe/return/monotonicity result"),
        ("same_holdout_ic", "unexplained_difference", "headline reports portfolio IC 0.0894 while rolling table reports 0.0865 for the same named 2026 holdout"),
        ("same_holdout_sharpe", "unexplained_difference", "headline reports Agora/B2/B6 Sharpes 1.872/1.334/-0.379; NW table reports 1.989/1.202/-0.310 without a stated estimator bridge"),
        ("cost_sensitivity", "directional_anomaly", "as cost rises 9 to 45 bps, printed long-short annualized return rises 0.4843 to 0.4984; standard self-financing long-short costs debit both legs, so raw returns/turnover and code are needed to resolve the sign"),
        ("cost_wording", "ambiguous", "paper calls the same charge 'round-trip cost ... one-way' and combines double-sided commission with sell-side stamp tax into 9 bps one-way"),
        ("test_segment_feedback", "explicit_limitation", "paper correctly discloses categorical 2020--2025 feedback and limits the fully clean claim to the 2026 holdout"),
        ("full_system_seed", "explicit_limitation", "the 100-round Agora result is one seed and its seed variance is uncharacterized"),
        ("metric_novelty", "appropriately_bounded", "paper explicitly says both promoted metrics are standard quant practice rather than novel inventions"),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in specs]


def release_rows(scratch: Path) -> list[dict[str, Any]]:
    discovery = scratch / "discovery"
    zero_arrays = {
        "GitHub repository arXiv ID": "github-repos-arxiv.json",
        "GitHub repository exact title": "github-repos-title.json",
        "GitHub repository Sealed Joint Search": "github-repos-sjs.json",
        "GitHub repository Agora AlphaGen": "github-repos-agora-alphagen.json",
        "GitHub code top_alphas_audit.json": "github-code-top-alphas-audit.json",
        "GitHub code enable_incremental_ppo": "github-code-incremental-ppo.json",
        "GitHub code avg_pred_corr": "github-code-avg-pred-corr.json",
        "GitHub code author email": "github-code-author-email.json",
        "GitHub code promoted metric name": "github-code-metric-name.json",
    }
    rows = []
    for surface, filename in zero_arrays.items():
        data = json.loads((discovery / filename).read_text())
        if data:
            raise ValueError(f"bounded zero-result search changed: {filename}")
        rows.append(
            {
                "surface": surface,
                "query_or_endpoint": filename,
                "observed_matches": 0,
                "attributable_agora_release_found": False,
                "observation": "complete bounded exact public search returned zero",
                "negative_search_boundary": "zero results do not prove private, deleted, moved, renamed, unindexed or later artifacts do not exist",
            }
        )
    for surface, filename in (
        ("GitHub commits author email", "github-commits-author-email.json"),
        ("GitHub users affiliation domain", "github-users-domain.json"),
    ):
        data = json.loads((discovery / filename).read_text())
        count = int(data.get("total_count", 0))
        rows.append(
            {
                "surface": surface,
                "query_or_endpoint": filename,
                "observed_matches": count,
                "attributable_agora_release_found": False,
                "observation": "bounded public identity search",
                "negative_search_boundary": "public indexed identities only",
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
                "query_or_endpoint": "Agora AlphaGen",
                "observed_matches": len(data),
                "attributable_agora_release_found": False,
                "observation": "bounded name-token search",
                "negative_search_boundary": "name search only",
            }
        )
    domain = (discovery / "pandaai-domain.html").read_text(errors="replace")
    rows.append(
        {
            "surface": "paper-author affiliation domain",
            "query_or_endpoint": "https://pandaai.online",
            "observed_matches": 1,
            "attributable_agora_release_found": False,
            "observation": "reachable page metadata describes a generic CRMEB/Java e-commerce storefront and contains no Agora/SJS/code link",
            "negative_search_boundary": "current landing-page observation only",
        }
    )
    if "CRMEB" not in domain or "Agora" in domain or "Sealed Joint Search" in domain:
        raise ValueError("affiliation-domain disposition changed")
    repo_matches = json.loads((discovery / "github-repos-pandaai-domain.json").read_text())
    repo = json.loads((discovery / "quantskills-repo.json").read_text())
    tree = json.loads((discovery / "quantskills-tree.json").read_text())
    readme = (discovery / "quantskills-readme.md").read_text()
    files = [item for item in tree["tree"] if item["type"] == "blob"]
    if len(repo_matches) != 1 or len(files) != 47 or "非官方、不隶属 PandaAI" not in readme:
        raise ValueError("post-paper PandaAI-domain candidate changed")
    rows.append(
        {
            "surface": "GitHub repository affiliation-domain token",
            "query_or_endpoint": repo["html_url"],
            "observed_matches": len(repo_matches),
            "attributable_agora_release_found": False,
            "observation": "47-file competition/onboarding skill created 2026-08-04; README explicitly says unofficial/not affiliated and contains no Agora/SJS/AlphaGen system",
            "negative_search_boundary": "candidate inspected and rejected for attribution/task mismatch, not treated as absence proof",
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
    if (official_pages, rebuilt_pages) != (42, 42) or overlap < 0.999:
        raise ValueError("paper rebuild/page evidence changed")

    output.mkdir(parents=True, exist_ok=True)
    results = result_rows(files)
    figures = figure_rows(files)
    metrics = metric_rows(files)
    methods = method_rows()
    consistency = internal_rows()
    releases = release_rows(scratch)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "metric_execution_audit.csv", metrics)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(output / "release_search_audit.csv", releases)

    provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "arxiv_version": "v1",
        "published_utc": "2026-06-28T04:41:00Z",
        "source_files": len(files),
        "official_pages": official_pages,
        "rebuilt_pages": rebuilt_pages,
        "official_pages_visually_checked": 42,
        "rebuilt_pages_visually_checked": 42,
        "visual_defects_observed": 0,
        "official_rebuilt_token_jaccard": overlap,
        "paper_contains_repository_url": False,
        "attributable_agora_implementation_found": False,
        "negative_search_scope": (
            "bounded public GitHub repository/code/commit/user searches, affiliation-domain inspection, "
            "one later domain-token candidate, and Hugging Face name search; not proof of permanent absence"
        ),
        "pins": PINS,
    }
    write_json(output / "source_provenance.json", provenance)

    readme = f"""# Agora / Sealed Joint Search paper-level replication audit

**Verdict: highly specification-rich, but the claimed release is not recoverable and the paper is not reproducible end to end.** The pinned arXiv `2606.29194v1` source rebuilds to the official 42-page count with {overlap:.2%} extracted-token multiset overlap. All 42 official and all 42 rebuilt pages were visually inspected without observed clipping, overlap, missing assets, or unreadable research content.

The active empirical denominator is **293 displayed quantitative result cells across ten tables and four empirical figure panels**. A unit is one populated quantitative table cell; compound mean-plus-standard-deviation and confidence-interval cells remain one displayed unit. The four empirical vector assets contain 26 plotted series, distributions, or bar groups. **Zero of 293 cells and 0/4 panels are author-natively regenerated.** The source archive contains rendered figures and TeX tables, not the underlying arrays, CSI1000/RiceQuant snapshot, point-in-time membership, 94 alpha programs, top-30 pool, daily signals/returns, orders/fills, model calls, per-round registries, PPO checkpoints, baseline outputs, or result generator.

The paper's contribution section says the implementation, seven baselines, leakage audit, and per-round registries are released. Appendix A.8 instead says the accompanying release *will include* them. Neither the PDF nor TeX contains a repository URL. Four exact GitHub repository searches, five source-unique code searches, author-email commit search, affiliation-domain user search, and Hugging Face model/dataset searches find no attributable Agora implementation. The current affiliation-domain page is a generic e-commerce storefront. One later 47-file GitHub hit uses a PandaAI domain token, but it was created on 2026-08-04, is a factor-competition onboarding skill, explicitly says it is unofficial/not affiliated, and contains no Agora/SJS system. These are bounded observations, not proof that private, deleted, moved, renamed, unindexed, or later artifacts do not exist.

The strongest executable evidence is narrower but real. Appendix C prints complete source for `monotonicity_score_v1` and `excess_drawdown_penalty_v1`; both programs AST-parse and execute verbatim on deterministic 40-by-50 controlled panels, return finite bounded deterministic values, pass directional checks, and return their documented zero guard on undersized input. These are **paper-derived component executions**, not the author pipeline: the reported R21/R50 proposals, predictive correlations, promotion events, 100-round effects, and portfolio results cannot be regenerated from the release state.

The paper is unusually candid about categorical test-window feedback, its single full-system seed, anti-conservative per-alpha tests, and the non-novelty of its two metrics. The audit also records material internal conflicts: eight claimed skill libraries versus nine rows; Agora per-alpha median Sharpe 1.06 versus 2.461; B6 median +0.227 versus -0.000; prose claims about positive baselines contradicted by the headline table; 91 versus 60 observations for the same holdout; unexplained headline/NW Sharpe and holdout-IC differences; and long-short annualized return increasing as costs rise from 9 to 45 bps, which is directionally inconsistent with standard self-financing cost debits on both legs absent an undisclosed convention or defect. Raw arrays and code are required to resolve the latter issues. `strict_success` remains false.
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
        "empirical_figure_series_or_groups": sum(int(row["empirical_series_or_groups"]) for row in figures),
        "author_native_empirical_panels_regenerated": 0,
        "complete_paper_metric_programs_executed": len(metrics),
        "paper_metric_programs_passing_controlled_checks": sum(
            bool(row["deterministic"] and row["finite_and_bounded"] and row["direction_and_guard_checks_passed"])
            for row in metrics
        ),
        "attributable_agora_implementation_found": False,
        "raw_result_arrays_recovered": 0,
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
