#!/usr/bin/env python3
"""Build a fail-closed paper/source/release audit for FactorEngine."""

from __future__ import annotations

import argparse
import ast
import csv
import difflib
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/factorengine_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/factorengine"
WORK_ID = "CensusArxiv260316365"
SYSTEM_ID = "SYS-FACTOR-ENGINE"
ARXIV_ID = "2603.16365"

PINS = {
    "v1/official.pdf": "1851415a21ae7c12e91ad014c75e3d802264d24c88659dae0075f54400f2962e",
    "v1/source.tar": "a49529a134a47ed554e3348812719599538f709f953397139cd43709e75fe23b",
    "v1/rebuilt.pdf": "09b6016ae9b5f757196ec909b1cd4cb1bd8e015b400e30d0035f6d7f2c201222",
    "v1/official.txt": "8f249a7d0ff9aadf645e1c52cf0504daed6a67b305e49f211eff1d156a7cf54f",
    "v1/rebuilt.txt": "8b4e00ab31caa1d151f626d0be6ec0fd704df678eb37c39b532663b7150ebe67",
    "v1/source/paper.tex": "0632098037c20d22c66030c88ef5962d70a3fd4b3421f3af311c82fcc9733438",
    "v2/official.pdf": "d79130ffeab415aef06c718d5d51be221af820ff1e971fe48f1f144a2991b870",
    "v2/source.tar": "942e4c2e053ab912dd041ccf77282e9e58ffa69daeac2631ae6accbaa960a6eb",
    "v2/rebuilt.pdf": "98f83fd9d12f150c6f1cefc824a4f94953f7671a99c20e535529933462ec7a60",
    "v2/official.txt": "aadf0252ce5610d7411ca92ff5c30d160bbb4356c28e69ef8a39216c987dd0fe",
    "v2/rebuilt.txt": "043aa9f42c0693bff32b81897fa3a485003d3f3bfedd259e75bd9bac22b5db2b",
    "v2/source/paper.tex": "8bd0907153512dc41dbce1272b3dd92aa301d3cb88770304aa414349d2e620e9",
    "discovery/arxiv-abs.html": "2a6cdf4f5ce3375b1cc859dc98d880c5eb91309120f2bacc5966238660a76974",
    "discovery/arxiv-api.xml": "a34e8dcaceeeb09bf474f4a257a325b3b5004bab05b05e87eab8c277a93a1ba8",
    "discovery/github-repository-search.json": "3b3c9ea05330c93299891c9e0a0c447380fe3cd9898c9289bd68d7e7ac83aef0",
    "discovery/github-code-arxiv-search.json": "9cc7330e62381a06135fd8f12833b3155fe15331e8bc5d3e70eff1021e85d1cf",
    "discovery/github-repos-qinhonglin.json": "891393fa55cc08d82e56b41f09e7be29bd2274ff585cb9e259eeee39caee9947",
    "discovery/github-repos-fengruitao.json": "4854583f1d3529e1b93d72e43a2f2dc5b3b61f0180d1b9c761254ac5e4bb579b",
    "discovery/github-repos-valuesimplex.json": "ab1eb145070b25466b847d264befa4e1b8bef21eaa391a6c867277940706a720",
    "discovery/huggingface-models-factorengine.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-datasets-factorengine.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/candidate-repo-metadata.json": "93b2aadda4865f9d0811c78ef7bc95f9dab93749ba6cb7aac80f1ad828969dc3",
    "paper-listing-execution.log": "f33e0b02c22baff24753b16dd780432404c1950b3146327dba33c7f6729e3d4c",
    "candidates/asher21600-svg__factor_engine_reproduction/candidate-pip-check.log": "9261363b733079a641c2e4cc9bc46ffa1d8336945a87f807b6cf68847dbc9b09",
    "candidates/asher21600-svg__factor_engine_reproduction/candidate-compileall.rc": "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    "candidates/asher21600-svg__factor_engine_reproduction/candidate-pytest.log": "385482a839232e528bf2c95f5d6b25079cfb082804bdb2e3857e975067abf637",
    "candidates/asher21600-svg__factor_engine_reproduction/candidate-pytest.rc": "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
    "candidates/asher21600-svg__factor_engine_reproduction/candidate-build-synthetic.log": "102371045152dcdd1aca383a629fb021984e24049710aab75d991ab819f5306a",
    "candidates/asher21600-svg__factor_engine_reproduction/candidate-evolution-smoke.log": "7e6de4a456772fd9c4f7c86789dd3640ffac252eca0929458a35c9da5bd9b0b7",
    "candidates/asher21600-svg__factor_engine_reproduction/audit-smoke-evolution.json": "adb261d3f95e2cba6ea4e7ab193b98e967901123dd1d9a6dbec1aaa85443b72f",
}

FIGURES = (
    ("framework_tight_v1.pdf", "framework", 1, False),
    ("bootstrap_v1.pdf", "bootstrapping", 1, False),
    ("csi300_limit_k50_n5_new_backtest_comparison_without_title.pdf", "csi300_cumulative_return", 1, True),
    ("csi500_limit_k50_n5_backtest_comparison_without_title.pdf", "csi500_cumulative_return", 1, True),
    ("csi500_factor_dispersion_comparison.pdf", "factor_diversity", 1, True),
    ("csi300_ic_without_title.pdf", "yearly_ic", 1, True),
    ("csi300_ric_without_title.pdf", "yearly_rank_ic", 1, True),
    ("lag_length_ic_ric_comparison_without_title.pdf", "lag_sensitivity", 1, True),
    ("bayesian_ablation_plot.pdf", "bayesian_ablation", 1, True),
    ("radar_csi300.pdf", "backbone_ablation", 1, True),
)

CANDIDATE_COMMIT = "2b16ed52ea7da7d5fea10ba505ba16c9501880d7"


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


def clean_label(value: str) -> str:
    value = re.sub(r"\\(?:textbf|underline|textit)\{([^{}]*)\}", r"\1", value)
    value = value.replace(r"\%", "%").replace("$", "")
    value = re.sub(r"[{}]", "", value)
    return " ".join(value.split())


def table_block(source: str, label: str) -> str:
    marker = rf"\label{{tab:{label}}}"
    index = source.index(marker)
    start = source.rfind(r"\begin{table", 0, index)
    end = source.index(r"\end{table", index)
    block = source[start:end]
    return block[block.index(r"\midrule") + len(r"\midrule") : block.index(r"\bottomrule")]


def parse_numbers(cells: Sequence[str]) -> list[str]:
    number = re.compile(r"(?<![A-Za-z0-9.])-?\d+(?:\.\d+)?(?:\\?%)?")
    values = []
    for cell in cells:
        matches = number.findall(cell)
        if len(matches) != 1:
            raise ValueError(f"unexpected numeric table cell: {cell!r}")
        values.append(matches[0].replace(r"\%", "%"))
    return values


def parse_published_results(source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    blocker = (
        "no attributable experiment package, frozen Qlib panel, report corpus, "
        "filled model calls, generated factor pools, predictions, returns, or raw arrays"
    )
    specs = (
        (
            "table_main_result",
            0,
            tuple(
                f"{market}_{metric}"
                for market in ("csi300", "csi500")
                for metric in ("ic", "icir", "ric", "ricir", "ar", "mdd", "ir", "sr")
            ),
        ),
        ("cost", 2, ("cost_usd", "time_hours", "executable_ratio", "debug_ratio")),
        ("parameter_ablation", 0, ("ric", "ricir", "ar", "ir", "mdd")),
    )
    expected_counts = {"table_main_result": 224, "cost": 12, "parameter_ablation": 40}
    for table, skip, metrics in specs:
        for line in table_block(source, table).splitlines():
            stripped = line.lstrip()
            if stripped.startswith("%") or "&" not in line or stripped.startswith(r"\midrule"):
                continue
            cells = line.split("&")
            label = clean_label(cells[0])
            values = parse_numbers(cells[1 + skip :])
            if len(values) != len(metrics):
                raise ValueError(f"column mismatch in {table}/{label}: {len(values)}")
            for metric, value in zip(metrics, values):
                rows.append(
                    {
                        "table": table,
                        "row": label,
                        "metric": metric,
                        "printed_value": value,
                        "source_tex_recovered": True,
                        "author_native_experiment_executed": False,
                        "published_result_regenerated": False,
                        "paper_result_credit": False,
                        "blocking_reason": blocker,
                    }
                )
    counts = Counter(row["table"] for row in rows)
    if counts != Counter(expected_counts):
        raise ValueError(f"published result count changed: {counts}")
    anchors = {(r["table"], r["row"], r["metric"]): r["printed_value"] for r in rows}
    expected = {
        ("table_main_result", "FE-report-2", "csi300_ic"): "0.0474",
        ("table_main_result", "FE-report-2", "csi300_ar"): "0.1899",
        ("cost", "FactorEngine", "time_hours"): "0.5",
        ("parameter_ablation", "10alpha,2island,top-k", "ric"): "0.0353",
    }
    for key, value in expected.items():
        if anchors.get(key) != value:
            raise ValueError(f"published anchor changed: {key}={anchors.get(key)}")
    return rows


def parse_prompts(source: str) -> list[dict[str, Any]]:
    blocks = re.findall(r"\\begin\{lstlisting\}\[caption=([^]]+)\]\s*\n(.*?)\\end\{lstlisting\}", source, re.DOTALL)
    rows = []
    for caption, text in blocks[:2]:
        rows.append(
            {
                "template": "system_prompt" if "System prompt" in caption else "chain_of_experience",
                "template_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "source_tex_recovered": True,
                "filled_runtime_request_recovered": False,
                "filled_runtime_response_recovered": False,
                "native_execution_credit": False,
            }
        )
    if [row["template"] for row in rows] != ["system_prompt", "chain_of_experience"]:
        raise ValueError("evolution prompt templates changed")
    return rows


def listing_audit(source: str, execution_log: str) -> list[dict[str, Any]]:
    blocks = re.findall(r"\\begin\{lstlisting\}.*?\n(.*?)\\end\{lstlisting\}", source, re.DOTALL)
    code = blocks[-2:]
    if len(code) != 2:
        raise ValueError("expected two printed factor programs")
    names = ("seed_factor", "evolved_factor_after_40_iterations")
    statuses = {}
    for line in execution_log.splitlines():
        parts = line.split("|")
        statuses[parts[0]] = parts[1:]
    rows = []
    for name, text, function in zip(names, code, ("factor", "trend_factor")):
        ast.parse(text)
        status = statuses[function]
        passed = status[0] == "PASS"
        rows.append(
            {
                "listing": name,
                "function": function,
                "syntax_valid": True,
                "verbatim_controlled_execution_passed": passed,
                "finite_output_rows": 35 if passed else 0,
                "observed_failure": "" if passed else "NameError: daily_range_expr is not defined",
                "paper_component_credit": passed,
                "author_native_system_credit": False,
                "published_result_credit": False,
                "listing_sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
        )
    return rows


def method_specs() -> list[dict[str, Any]]:
    values = (
        ("raw factor inputs", "OHLCV only", True),
        ("evaluation universes", "CSI300 and CSI500 from full-market Qlib data", True),
        ("train/validation/test dates", "2008-2014 / 2015-2016 / 2017-2024", True),
        ("iteration budgets", "200 and 400; one factor per iteration", True),
        ("islands and migration", "2 islands; every 7 iterations; top 3 programs", True),
        ("seed sets", "5 and 10 listed Alpha158-derived factors", True),
        ("fitness", "(10 IC + ICIR + 10 RIC + RICIR) / 4", True),
        ("tree exploration", "UCT with c=sqrt(2)", True),
        ("experience paths", "three high-performance/low-overlap paths", True),
        ("lag objectives", "1, 3, 5, and 10 trading days", True),
        ("elite selection", "top 5 nodes above 0.4; top 10 parameter configs", True),
        ("portfolio", "top 50 equal-weight; five overlapping 5-day tranches", True),
        ("trading frictions", "0.00015 bilateral commission; 0.0005 sell stamp; 0.0008 slippage", True),
        ("execution constraints", "100-share lot; 10% daily-volume cap; price limits", True),
        ("initial capital", "CNY 100,000,000", True),
        ("agent backbone", "Gemini-2.5-Pro for main agent baselines", False),
        ("agent inference revision/settings", "not reported", False),
        ("random seeds and repeated-run protocol", "not reported", False),
        ("Bayesian optimizer/trial budget", "multiple methods supported; exact choice/budget absent", False),
        ("Qlib revision and market-data snapshot", "not reported", False),
        ("point-in-time constituent snapshot", "not released", False),
        ("pre-2017 research-report corpus", "not released", False),
        ("LightGBM configuration", "not reported", False),
        ("Python/dependency environment", "not reported", False),
        ("generated factor pools and trajectories", "not released", False),
        ("predictions/holdings/returns/raw arrays", "not released", False),
        ("bootstrapping-agent prompts", "not printed", False),
    )
    return [
        {"dimension": name, "paper_value_or_state": value, "sufficiently_specified": complete}
        for name, value, complete in values
    ]


def inconsistencies() -> list[dict[str, Any]]:
    values = (
        (
            "mdd_200_run",
            "prose says FE-report MDD falls from 15.57%; active Table 1 prints 15.89%",
            "direct numeric conflict",
        ),
        ("evolved_listing", "Listing 1.4 uses daily_range_expr without defining it", "verbatim execution fails"),
        (
            "initial_factor_count",
            "main setup and appendix say 5-factor set; configuration table labels the comparable arm 6alpha",
            "configuration ambiguity",
        ),
        (
            "expected_improvement_sign",
            "the method maximizes f but prints max(y* - y, 0), the usual minimization-direction improvement",
            "objective/sign ambiguity",
        ),
        (
            "yearly_ric_caption",
            "caption calls the middle panel CSI500; its source asset is csi300_ric_without_title.pdf and prose calls both first panels CSI300",
            "figure-label conflict",
        ),
        ("coverage_symbol", "Eq. 2 defines S_cov, while Eq. 4 subtracts S_Cvg", "notation mismatch"),
    )
    return [{"issue": key, "evidence": evidence, "impact": impact} for key, evidence, impact in values]


def candidate_audit(scratch: Path) -> dict[str, Any]:
    candidate = scratch / "candidates/asher21600-svg__factor_engine_reproduction"
    commit = subprocess.run(
        ["git", "-C", str(candidate), "rev-parse", "HEAD"], check=True, text=True, capture_output=True
    ).stdout.strip()
    if commit != CANDIDATE_COMMIT:
        raise ValueError(f"candidate commit changed: {commit}")
    smoke = json.loads((candidate / "audit-smoke-evolution.json").read_text())
    return {
        "repository": "asher21600-svg/factor_engine_reproduction",
        "pinned_commit": commit,
        "created_at": "2026-06-07T08:45:41Z",
        "paper_v2_date": "2026-04-09",
        "author_attribution": False,
        "declared_requirements_install_and_pip_check": "pass",
        "compileall": "pass",
        "only_repository_test": "fails because unshipped Qlib bundle is absent",
        "synthetic_smoke": {
            "iterations": smoke["config"]["iterations"],
            "islands": smoke["config"]["islands"],
            "evaluations": smoke["n_evals"],
            "seed_reward": smoke["seed_reward"],
            "best_reward": smoke["best_reward"],
        },
        "tracked_real_data_panels": False,
        "tracked_report_corpus": False,
        "paper_model_used": False,
        "paper_iteration_budget_used_in_audited_smoke": False,
        "paper_result_cells_regenerated": 0,
        "native_credit": False,
        "assessment": (
            "Substantial unaffiliated post-paper reimplementation. Its deterministic UCT/Bayesian/island "
            "machinery executes on synthetic data, but it repairs the broken printed evolved listing, substitutes "
            "the LLM, omits FE-report lineage, and does not ship the real panels behind its claimed real-data outputs."
        ),
    }


def build(scratch: Path, output: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"missing or changed pinned evidence: {relative}")
    source_v1 = (scratch / "v1/source/paper.tex").read_text()
    source_v2 = (scratch / "v2/source/paper.tex").read_text()
    results = parse_published_results(source_v2)
    prompts = parse_prompts(source_v2)
    listings = listing_audit(source_v2, (scratch / "paper-listing-execution.log").read_text())

    source_files_v1 = sorted(
        p.relative_to(scratch / "v1/source").as_posix()
        for p in (scratch / "v1/source").rglob("*")
        if p.is_file() and p.name not in {"paper.aux", "paper.bbl", "paper.blg", "paper.log", "paper.out", "paper.pdf"}
    )
    source_files_v2 = sorted(
        p.relative_to(scratch / "v2/source").as_posix()
        for p in (scratch / "v2/source").rglob("*")
        if p.is_file() and p.name not in {"paper.aux", "paper.bbl", "paper.blg", "paper.log", "paper.out", "paper.pdf"}
    )
    if source_files_v1 != source_files_v2 or len(source_files_v2) != 15:
        raise ValueError("source archive inventory changed")
    changed_assets = [
        name for name in source_files_v2 if sha256(scratch / "v1/source" / name) != sha256(scratch / "v2/source" / name)
    ]
    if changed_assets != ["paper.tex"]:
        raise ValueError(f"unexpected revision asset changes: {changed_assets}")
    diff = "\n".join(difflib.unified_diff(source_v1.splitlines(), source_v2.splitlines()))
    if "entropyreduce.com" not in diff or "greenred99@bupt.edu.cn" not in diff:
        raise ValueError("revision diff is no longer institution-email-only")

    figure_rows = []
    for filename, role, panels, empirical in FIGURES:
        path = scratch / "v2/source/figure" / filename
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

    repository_search = json.loads((scratch / "discovery/github-repository-search.json").read_text())
    code_search = json.loads((scratch / "discovery/github-code-arxiv-search.json").read_text())
    hf_models = json.loads((scratch / "discovery/huggingface-models-factorengine.json").read_text())
    hf_datasets = json.loads((scratch / "discovery/huggingface-datasets-factorengine.json").read_text())
    first_party = {
        name: [item["name"] for item in json.loads((scratch / f"discovery/github-repos-{name}.json").read_text())]
        for name in ("qinhonglin", "fengruitao", "valuesimplex")
    }
    if any("factorengine" in repo.lower() for repos in first_party.values() for repo in repos):
        raise ValueError("an attributable FactorEngine repository now appears in the pinned search")
    source_provenance = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "title": "FactorEngine: A Program-level Knowledge-Infused Factor Mining Framework for Quantitative Investment",
        "authors": [
            "Qinhong Lin",
            "Ruitao Feng",
            "Yinglun Feng",
            "Zhenxin Huang",
            "Yukun Chen",
            "Zhongliang Yang",
            "Linna Zhou",
            "Binjie Fei",
            "Jiaqi Liu",
            "Yu Li",
        ],
        "versions": {
            "v1": {
                "submitted": "2026-03-17",
                "pages": len(PdfReader(scratch / "v1/official.pdf").pages),
                "official_rebuilt_token_jaccard": token_jaccard(
                    (scratch / "v1/official.txt").read_text(), (scratch / "v1/rebuilt.txt").read_text()
                ),
            },
            "v2": {
                "submitted": "2026-04-09",
                "pages": len(PdfReader(scratch / "v2/official.pdf").pages),
                "official_rebuilt_token_jaccard": token_jaccard(
                    (scratch / "v2/official.txt").read_text(), (scratch / "v2/rebuilt.txt").read_text()
                ),
            },
        },
        "v1_v2_official_token_jaccard": token_jaccard(
            (scratch / "v1/official.txt").read_text(), (scratch / "v2/official.txt").read_text()
        ),
        "source_files_each_revision": 15,
        "revision_changed_assets": changed_assets,
        "revision_scientific_content_change": False,
        "official_pages_visually_checked": {"v1": 26, "v2": 26},
        "rebuilt_pages_visually_checked": {"v1": 26, "v2": 26},
        "visual_defects_observed": 0,
        "first_party_namespaces_checked": first_party,
        "github_repository_search_count": repository_search["total_count"],
        "github_code_search_count": code_search["total_count"],
        "huggingface_model_matches": len(hf_models),
        "huggingface_dataset_matches": len(hf_datasets),
        "attributable_factorengine_release_found": False,
        "negative_search_scope": "bounded; does not prove that private, deleted, moved, or unindexed material never existed",
    }

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "figure_inventory.csv", figure_rows)
    write_csv(output / "prompt_template_ledger.csv", prompts)
    write_csv(output / "factor_program_execution.csv", listings)
    write_csv(output / "method_specification_audit.csv", method_specs())
    write_csv(output / "internal_consistency_audit.csv", inconsistencies())
    write_json(output / "source_provenance.json", source_provenance)
    write_json(output / "candidate_release_audit.json", candidate_audit(scratch))

    manifest = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "paper_versions_audited": 2,
        "official_pages_visually_checked": 52,
        "rebuilt_pages_visually_checked": 52,
        "published_numeric_table_units": len(results),
        "native_table_units_regenerated": 0,
        "source_figure_assets": len(figure_rows),
        "empirical_figure_assets": sum(row["empirical"] for row in figure_rows),
        "empirical_panels": sum(row["panels"] for row in figure_rows if row["empirical"]),
        "native_empirical_panels_regenerated": 0,
        "evolution_prompt_templates": len(prompts),
        "printed_factor_programs": len(listings),
        "verbatim_factor_programs_executing": sum(row["verbatim_controlled_execution_passed"] for row in listings),
        "attributable_code_release_found": False,
        "unattributable_candidates_audited": 1,
        "strict_success": False,
        "strict_failure_reason": "no attributable FactorEngine experiment package or paper-result lineage",
    }
    readme = (
        "# FactorEngine paper-level replication audit\n\n"
        "This fail-closed audit reconstructs both official arXiv revisions, inventories every active "
        "numeric table value and source figure, executes the two printed factor programs verbatim, and "
        "separates a later unaffiliated reimplementation from author-native evidence.\n\n"
        "The released TeX is highly reconstructable and unusually informative, but the paper experiment "
        "is not reproducible end to end from public first-party artifacts. The seed listing executes on a "
        "controlled panel; the claimed evolved listing does not because `daily_range_expr` is undefined. "
        "No native credit is assigned to the local narrative proxy or to the unaffiliated candidate.\n\n"
        f"Audited outcomes: 0/{len(results)} table measurements and 0/"
        f"{sum(r['panels'] for r in figure_rows if r['empirical'])} empirical panels are regenerated; "
        "1/2 printed factor programs executes verbatim. The two evolution prompt templates are source "
        "specifications, not recovered runtime traces.\n"
    )
    (output / "README.md").write_text(readme)
    generated = [
        "README.md",
        "candidate_release_audit.json",
        "factor_program_execution.csv",
        "figure_inventory.csv",
        "internal_consistency_audit.csv",
        "method_specification_audit.csv",
        "prompt_template_ledger.csv",
        "published_result_ledger.csv",
        "source_provenance.json",
    ]
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
