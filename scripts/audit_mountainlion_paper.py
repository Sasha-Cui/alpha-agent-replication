#!/usr/bin/env python3
"""Build a fail-closed primary-source audit for the MountainLion paper.

This audit separates four kinds of evidence that the paper blends together:

* deterministic reconstruction of the arXiv manuscript;
* author-rendered diagrams and case-study output embedded in that manuscript;
* attributable MountainLion frontend and generic GenAI-platform components; and
* the unreleased experiment that produced the forecasting table and material
  performance claims.

The first three categories are useful provenance and component evidence.  They
never receive paper-result credit.  The public sources ship no training panel,
split, fitted model, inference record, prediction array, portfolio path, or
result-generation runner, so the audit intentionally reports zero faithfully
regenerated performance cells.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import re
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_ROOT = Path("/nfs/roberts/scratch/pi_btk22/zc362/mountainlion_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/mountainlion"

WORK_ID = "CensusArxiv250720474"
SYSTEM_ID = "SYS-MOUNTAIN-LION"
ARXIV_ID = "2507.20474"

PDF_PINS = {
    "2507.20474v1": {
        "path": "2507.20474v1.pdf",
        "url": "https://arxiv.org/pdf/2507.20474v1",
        "sha256": "373c801bde8b0b09544eb1631bc97f8ca86e72789f23dd7e7c1a812bab96b6bf",
        "pages": 17,
    },
    "2507.20474v2": {
        "path": "2507.20474v2.pdf",
        "url": "https://arxiv.org/pdf/2507.20474v2",
        "sha256": "7c44766c7cacc8eef123ae7a55346e21401bac964283811d917b228ed6af7a7c",
        "pages": 17,
    },
}

SOURCE_PINS = {
    "2507.20474v1": {
        "path": "2507.20474v1.tar",
        "url": "https://export.arxiv.org/e-print/2507.20474v1",
        "sha256": "62735223795a103ef72b46098e1d0729e8b5d5e80362b0108055daa364211961",
        "file_count": 11,
        "main_sha256": "1c9f26c99d821627a3e4cf5c8e3487c7e6d42d3068654cf18050aad1ebe37c06",
    },
    "2507.20474v2": {
        "path": "2507.20474v2.tar",
        "url": "https://export.arxiv.org/e-print/2507.20474v2",
        "sha256": "6174f61c84265a4f6d7ef0bc741c3c32d738758c8f3ff4bcb6d96af461e507bb",
        "file_count": 10,
        "main_sha256": "72067a2a5527ce89c57168a50cd32994ff4a8216b99b6280585824eaac1e23df",
    },
}

REBUILD_PINS = {
    "2507.20474v1": {
        "first_glob": "build_v1_a.*/main.pdf",
        "repeat_glob": "build_v1_b.*/main.pdf",
        "sha256": "636ee1ff22e0f24970cdf16f50a53a5308a8f33e72c5856bd56bdafff5df5414",
        "pages": 17,
        "normalized_text_word_set_jaccard": 0.9986779481755684,
        "normalized_raster_mean_absolute_difference": 0.00006587193358907521,
        "normalized_raster_max_page_difference": 0.0011198,
    },
    "2507.20474v2": {
        "first_glob": "build_v2_a.*/main.pdf",
        "repeat_glob": "build_v2_b.*/main.pdf",
        "sha256": "6c6f9ea7f196d188742fd2e99c3cff5273810b26be4297b1a0b80f912be2239b",
        "pages": 17,
        "normalized_text_word_set_jaccard": 0.9989443124835049,
        "normalized_raster_mean_absolute_difference": 0.0000865630636805057,
        "normalized_raster_max_page_difference": 0.00114519,
    },
}

LOCAL_PDF = (
    ROOT
    / "literature_review/papers/"
    "38_mountainlion_a_multi_modal_llm_based_agent_system_for.pdf"
)
LOCAL_PDF_SHA256 = "6b898a90ad7d6d30c422cfc9b23c5bc4cc44a2d86744db0577253de3e8cd2018"

PUBLIC_SOURCE_PINS = {
    "frontend": {
        "repository": "https://github.com/MountainLionAi/MountainLion",
        "commit": "f7819f3537808d398f6c3da37e43b51ecebdbd42",
        "commit_time": "2023-09-19T01:55:41-05:00",
        "archive": "frontend_f7819f3537808d398f6c3da37e43b51ecebdbd42.tar",
        "archive_sha256": "e336674987252aa8e1df3ccbc1f7a8609f242ef57b4ee9c21c06006608774478",
        "archive_bytes": 2_426_880,
        "file_count": 153,
        "license": "MIT",
        "paper_time_relation": "predates_paper_and_matches_appendix_endpoints",
    },
    "backend_paper_time": {
        "repository": "https://github.com/MountainLionAi/GenAI-Platform",
        "commit": "98b98d31dec6d29a5c518943d980300612030a40",
        "commit_time": "2025-07-11T17:03:52+08:00",
        "archive": "backend_paper_98b98d31dec6d29a5c518943d980300612030a40.tar",
        "archive_sha256": "66aa61c5ae03a6d587e94a1252421cae1f66579eeb3cec29875d09061e6efb88",
        "archive_bytes": 13_854_720,
        "file_count": 199,
        "license": "Apache-2.0",
        "paper_time_relation": "last_public_commit_before_arxiv_v1",
    },
    "backend_current": {
        "repository": "https://github.com/MountainLionAi/GenAI-Platform",
        "commit": "3f76de1fe4d8d423f7d4e46e45f19f5bd43992ec",
        "commit_time": "2026-05-25T12:42:14+08:00",
        "archive": "backend_current_3f76de1fe4d8d423f7d4e46e45f19f5bd43992ec.tar",
        "archive_sha256": "1524ffc672b40b0f8185b328caf63609ff09e234bb98eab6ed492ab771c31af9",
        "archive_bytes": 14_161_920,
        "file_count": 220,
        "license": "Apache-2.0",
        "paper_time_relation": "post_paper_drift_boundary_only",
    },
}

RUNTIME_FILE_PINS = {
    "frontend_build_repeat1.log": "0bfa5cf5c57a1e8161c98c8d907bc57968a7c93fca2cda7427943686ce45b977",
    "frontend_build_repeat2.log": "72085104fccf7cb584d05d424be42c3531649895a543f22be482ae96c061bb6a",
    "frontend_build_repeat1.manifest": "9726a9b6a16c28b471ea8fb8e63b82814351290a1ba54a1397587da36efe0a83",
    "frontend_build_repeat2.manifest": "9726a9b6a16c28b471ea8fb8e63b82814351290a1ba54a1397587da36efe0a83",
    "backend_compile_core.log": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "backend_compile_full.log": "276d92a5232286dba2dc2403e4e2aa420781ae937783d9cdff40fe15e8a42dd5",
}

FIGURE_KINDS = {
    "fig/Mlion_teaser.pdf": "conceptual_comparison",
    "fig/system_overview.pdf": "architecture_diagram",
    "fig/report_generation.pdf": "workflow_diagram",
    "fig/price_forecast.pdf": "workflow_diagram",
    "fig/news_driven_recommendation.pdf": "workflow_diagram",
    "fig/comp.pdf": "author_rendered_case_study_output",
}

TABLE_VALUES = [
    ("ADA", "1", "-0.000496", "0.000396", "Excellent fit, highly stable"),
    ("BTC", "1", "-1,997,859.43", "3,211,419.56", "Large error, unstable trend"),
    ("ARB", "1", "-0.000421", "0.000199", "Very good"),
    ("SOL", "1", "-0.000459", "0.000159", "Good model, potentially high volatility"),
    ("XRP", "0.1", "-0.000221", "0.001122", "Medium fit, moderate noise"),
    ("DOGE", "1", "-0.000362", "4.25E-05", "Very good"),
    ("TRX", "0.01", "-9.87E-06", "6.40E-06", "Best performer"),
    ("ETH", "1", "-2,169,147.17", "3,016,065.13", "Large error, unstable for ETH"),
    ("MATIC", "1", "-0.000432", "0.000341", "Stable, medium confidence"),
    ("BNB", "1", "-945.57", "180.95", "High deviation, unstable in 7-day window"),
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = list(rows)
    if not materialized:
        raise ValueError(f"refusing to write empty audit artifact: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(materialized[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(materialized)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def pinned_path(root: Path, relative: str, expected_sha256: str) -> Path:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(path)
    observed = sha256(path)
    if observed != expected_sha256:
        raise ValueError(f"hash mismatch for {path}: {observed}")
    return path


def unique_glob(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected one match for {pattern}, found {len(matches)}")
    return matches[0]


def safe_tar_files(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(path, mode="r:*") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError(f"unsafe archive member: {member.name}")
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError(f"cannot read archive member: {member.name}")
            files[member.name] = handle.read()
    return files


def paper_sources(audit_root: Path) -> dict[str, dict[str, bytes]]:
    bundles: dict[str, dict[str, bytes]] = {}
    for version, pin in SOURCE_PINS.items():
        archive = pinned_path(audit_root, pin["path"], pin["sha256"])
        files = safe_tar_files(archive)
        if len(files) != pin["file_count"]:
            raise ValueError(f"{version} source file count changed")
        if "main.tex" not in files:
            raise ValueError(f"{version} has no main.tex")
        if sha256_bytes(files["main.tex"]) != pin["main_sha256"]:
            raise ValueError(f"{version} main.tex changed")
        bundles[version] = files
    return bundles


def paper_version_summary(audit_root: Path) -> list[dict[str, Any]]:
    if sha256(LOCAL_PDF) != LOCAL_PDF_SHA256:
        raise ValueError("repository MountainLion PDF changed")
    rows: list[dict[str, Any]] = []
    for version, pdf_pin in PDF_PINS.items():
        source_pin = SOURCE_PINS[version]
        pdf = pinned_path(audit_root, pdf_pin["path"], pdf_pin["sha256"])
        pages = len(PdfReader(str(pdf)).pages)
        if pages != pdf_pin["pages"]:
            raise ValueError(f"{version} page count changed")
        rows.append(
            {
                "canonical_work_id": WORK_ID,
                "paper_version": version,
                "paper_url": pdf_pin["url"],
                "paper_sha256": pdf_pin["sha256"],
                "page_count": pages,
                "source_url": source_pin["url"],
                "source_sha256": source_pin["sha256"],
                "source_file_count": source_pin["file_count"],
                "repository_pdf_sha256": LOCAL_PDF_SHA256,
                "repository_pdf_byte_identical": pdf_pin["sha256"] == LOCAL_PDF_SHA256,
                "revision_scope": (
                    "v2 adds three authors and affiliations; audited experimental text, "
                    "table, prompts, and six figure assets are unchanged from v1"
                ),
            }
        )
    return rows


def classify_paper_source(path: str) -> str:
    if path == "main.tex":
        return "manuscript"
    if path == "main.bib":
        return "bibliography"
    if path.startswith("fig/") and path.endswith(".pdf"):
        return "rendered_figure_asset"
    if path.endswith((".sty", ".bst")):
        return "latex_build_dependency"
    return "archive_metadata"


def paper_source_inventory(
    bundles: Mapping[str, Mapping[str, bytes]],
) -> list[dict[str, Any]]:
    rows = []
    for version, files in bundles.items():
        for path, payload in sorted(files.items()):
            rows.append(
                {
                    "canonical_work_id": WORK_ID,
                    "paper_version": version,
                    "source_path": path,
                    "bytes": len(payload),
                    "sha256": sha256_bytes(payload),
                    "source_kind": classify_paper_source(path),
                    "operational_system_code": False,
                    "raw_numeric_result_array": False,
                    "runtime_request_or_response": False,
                    "model_or_checkpoint": False,
                    "paper_result_reproduction_credit": False,
                }
            )
    if Counter(row["paper_version"] for row in rows) != {
        "2507.20474v1": 11,
        "2507.20474v2": 10,
    }:
        raise RuntimeError("paper source inventory boundary changed")
    return rows


def figure_inventory(source_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in source_rows:
        path = str(row["source_path"])
        if path not in FIGURE_KINDS:
            continue
        case_output = path == "fig/comp.pdf"
        rows.append(
            {
                "canonical_work_id": WORK_ID,
                "paper_version": row["paper_version"],
                "source_path": path,
                "sha256": row["sha256"],
                "figure_kind": FIGURE_KINDS[path],
                "author_rendered_output_correspondence": case_output,
                "underlying_inputs_shipped": False,
                "runtime_prompt_response_shipped": False,
                "faithfully_regenerated_from_native_pipeline": False,
                "paper_result_credit": False,
            }
        )
    if len(rows) != 12 or len({row["sha256"] for row in rows}) != 6:
        raise RuntimeError("versioned MountainLion figure boundary changed")
    return rows


def published_table_ledger() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for token, alpha, cv_score, mse_test, evaluation in TABLE_VALUES:
        for metric, value, cell_kind in (
            ("Alpha", alpha, "configuration"),
            ("CV Score (Best)", cv_score, "direct_result"),
            ("MSE (Test)", mse_test, "direct_result"),
        ):
            rows.append(
                {
                    "canonical_work_id": WORK_ID,
                    "paper_version": "2507.20474v1_v2_identical_table",
                    "paper_table": "Forecasting Results Across Tokens",
                    "token": token,
                    "metric": metric,
                    "paper_value_display": value,
                    "cell_kind": cell_kind,
                    "paper_evaluation_text": evaluation,
                    "primary_source_value_verified": True,
                    "native_reproduced_value": "",
                    "absolute_difference": "",
                    "status": (
                        "paper_configuration_only_semantics_ambiguous"
                        if cell_kind == "configuration"
                        else "unavailable_no_training_data_model_or_result_pipeline"
                    ),
                    "paper_result_credit": False,
                }
            )
    if len(rows) != 30:
        raise RuntimeError("MountainLion table denominator changed")
    return rows


def prompt_inventory(main_tex: str) -> list[dict[str, Any]]:
    prompt_section = main_tex.split("\\section{Prompt design}", maxsplit=1)
    if len(prompt_section) != 2:
        raise ValueError("prompt-design section not found")
    blocks = re.findall(
        r"\\begin\{lstlisting\}\s*(.*?)\s*\\end\{lstlisting\}",
        prompt_section[1],
        flags=re.DOTALL,
    )
    prompt_ids = [
        "general_report_improvement_1",
        "general_report_improvement_2",
        "perplexity_macro_search",
        "perplexity_bilingual_search",
        "short_term_0_to_24_hours",
        "mid_term_7_to_30_days",
        "long_term_3_to_12_months",
    ]
    if len(blocks) != len(prompt_ids):
        raise ValueError(f"expected 7 prompt templates, found {len(blocks)}")
    return [
        {
            "canonical_work_id": WORK_ID,
            "paper_version": "2507.20474v1_v2_identical_prompt_section",
            "prompt_id": prompt_id,
            "template_sha256": sha256_bytes(block.strip().encode("utf-8")),
            "template_character_count": len(block.strip()),
            "verbatim_template_shipped": True,
            "exact_runtime_model_id_shipped": False,
            "runtime_parameters_shipped": False,
            "immutable_request_shipped": False,
            "immutable_response_shipped": False,
            "prompt_execution_reproduced": False,
            "paper_result_credit": False,
        }
        for prompt_id, block in zip(prompt_ids, blocks)
    ]


def material_claims() -> list[dict[str, Any]]:
    claims = [
        ("abstract_return_improvement", "improves returns", "qualitative"),
        ("retrieval_efficiency", "over 40% versus manual processes", "quantitative"),
        ("whale_detection", ">= USD 10M with confidence > 0.85", "quantitative"),
        ("investment_decision_accuracy", "28% improvement", "quantitative"),
        ("short_term_price_accuracy", "15% improvement versus baseline", "quantitative"),
        ("user_engagement_duration", "35% increase", "quantitative"),
        ("liquidation_volume_case_study", "3.2% rise", "quantitative"),
        ("extensive_ablations", "extensive experiments and ablation studies", "qualitative"),
        ("medium_term_accuracy", "improved medium-term forecasting accuracy", "qualitative"),
        ("directional_correctness", "reliable directional correctness across tokens", "qualitative"),
    ]
    return [
        {
            "canonical_work_id": WORK_ID,
            "claim_id": claim_id,
            "published_claim": value,
            "claim_kind": kind,
            "sample_or_denominator_shipped": False,
            "raw_evidence_shipped": False,
            "native_reproduced_value": "",
            "status": "unsupported_by_replayable_public_result_lineage",
            "paper_result_credit": False,
        }
        for claim_id, value, kind in claims
    ]


def mechanism_conformance() -> list[dict[str, Any]]:
    checks = [
        ("four specialized agents", "specified", "roles described; exact orchestration absent", False),
        ("central reflection module", "partial", "named but no executable reflection contract", False),
        ("visual reflection", "missing", "claimed experimentally; no operational definition or ablation", False),
        ("GraphRAG", "partial", "paper equations and generic platform dependency only", False),
        ("Perplexity retrieval", "partial", "templates and generic client exist; paper requests absent", False),
        ("general prompts", "specified", "seven verbatim templates are recoverable", True),
        ("runtime prompts", "missing", "no substituted prompts or request records", False),
        ("LLM identities", "partial", "LLaMA2-13B and case-study model families named", False),
        ("LLM snapshots/parameters", "missing", "exact IDs, temperature, seed, and decoding absent", False),
        ("Web3 fine-tuning", "missing", "dataset, method, checkpoint, and evaluation absent", False),
        ("OHLCV schema", "specified", "fields o/h/l/c/v stated", True),
        ("14D and 48H input windows", "specified", "windows stated without exchange/date/sample", True),
        ("historical news", "missing", "source corpus and timestamps absent", False),
        ("real-time news", "missing", "source/query/response snapshot absent", False),
        ("sentiment embeddings", "missing", "model, vectors, and preprocessing absent", False),
        ("LLM forecast track", "partial", "conceptual multi-step output only", False),
        ("ML forecast track", "partial", "one-step vector stated; estimator and fit absent", False),
        ("fusion equation", "specified", "convex equation stated", True),
        ("adaptive alpha", "partial", "directional update stated; optimizer/window absent", False),
        ("accuracy equation", "specified", "point formula stated without aggregation safeguards", True),
        ("win-rate equation", "partial", "formula stated with undefined first lag", False),
        ("forecast horizon", "conflicting", "14D/48H inputs, two/24-step examples, BNB seven-day prose", False),
        ("token universe", "specified", "same ten tokens appear in paper and platform menu", True),
        ("forecast training panel", "missing", "no values, dates, frequency, exchange, or split", False),
        ("cross-validation", "missing", "score printed; folds, scorer, search, and preprocessing absent", False),
        ("test MSE", "partial", "values printed; test rows and scaling absent", False),
        ("news recency filtering", "partial", "paper equations only", False),
        ("sentiment threshold", "partial", "symbolic threshold only", False),
        ("entity extraction", "underspecified", "printed set does not depend operationally on article", False),
        ("recommendation graph", "partial", "conceptual graph construction only", False),
        ("feedback adaptation", "conflicting", "called policy gradient; equation is generic loss descent", False),
        ("agent caching", "partial", "A1-A3 TTLs specified; A4 omitted", False),
        ("signal scoring weights", "partial", "three weights named without normalization or cutoff", False),
        ("portfolio/trading rule", "missing", "no executable positions, fills, cash, or rebalancing", False),
        ("transaction costs", "missing", "no cost, spread, slippage, or fee treatment", False),
        ("return evaluation", "missing", "no return table, path, benchmark, or risk statistic", False),
        ("random seeds", "missing", "not reported", False),
        ("native result outputs", "missing", "no prediction/result array or fitted artifact", False),
    ]
    rows = [
        {
            "canonical_work_id": WORK_ID,
            "dimension": dimension,
            "status": status,
            "primary_source_evidence": evidence,
            "paper_specification_reconstructable": reconstructable,
            "exact_native_paper_mechanism_reproduced": False,
            "paper_result_credit": False,
        }
        for dimension, status, evidence, reconstructable in checks
    ]
    if len(rows) != 38:
        raise RuntimeError("MountainLion mechanism boundary changed")
    return rows


def specification_gaps() -> list[dict[str, Any]]:
    gaps = [
        "exchange, time range, candle frequency, and point-in-time OHLCV snapshot",
        "news/social/on-chain sources with release and retrieval timestamps",
        "sample sizes, exclusions, missing-value policy, scaling, and transformations",
        "train/validation/test split and leakage controls",
        "ML estimator family, feature pipeline, hyperparameter search, and fitted models",
        "meaning of Table 1 Alpha and relation to the fusion coefficient",
        "cross-validation folds, scorer, sign convention, and raw fold scores",
        "exact LLM model snapshots, system prompts, parameters, tools, and seeds",
        "substituted prompt requests and immutable model/retriever responses",
        "LLM/ML horizon-alignment and fusion implementation",
        "rolling-alpha optimization window, objective, bounds, and update schedule",
        "forecast predictions and aligned realized outcomes",
        "accuracy/win-rate aggregation and first-lag boundary handling",
        "four-agent orchestration, validation, conflict-resolution, and reflection code",
        "GraphRAG schema, graph snapshot, retrieval policy, and evidence provenance",
        "news recommendation input corpus, labels, ranking model, and feedback records",
        "policy-gradient objective, action policy, reward, and logging",
        "ablation configurations, baselines, repeated trials, and uncertainty",
        "portfolio construction, trade timing, execution, and cost model",
        "holdings, actions, fills, cash, fees, NAV, returns, and benchmark path",
        "raw arrays behind the case-study comparison figure",
        "private ml4gp modules, product plugin, database schema, and database contents",
        "service API keys and frozen external-service versions",
    ]
    return [
        {
            "canonical_work_id": WORK_ID,
            "missing_requirement": gap,
            "blocking_effect": "blocks_exact_native_paper_or_result_reproduction",
            "publicly_resolved": False,
        }
        for gap in gaps
    ]


def internal_consistency_checks() -> list[dict[str, Any]]:
    checks = [
        (
            "raw_mse_cross_token_ranking",
            "TRX is the best performer because it has the lowest MSE",
            "MSE is reported on token price scales differing by orders of magnitude; no normalization is disclosed",
            "invalid_cross_scale_inference",
        ),
        (
            "table_alpha_semantics",
            "Table 1 labels a column Alpha",
            "the same symbol denotes the LLM/ML fusion weight, but CV/MSE context could instead indicate regularization alpha",
            "ambiguous_configuration",
        ),
        (
            "bnb_horizon",
            "BNB is unstable in a 7-day window",
            "forecast inputs are specified as 14D/48H and examples mention two future candles or 24 five-minute steps",
            "horizon_not_reconciled",
        ),
        (
            "return_claim_without_return_result",
            "abstract says the framework improves returns",
            "the paper reports no return, P&L, holdings, benchmark, or transaction-cost result",
            "unsupported_outcome_claim",
        ),
        (
            "ablation_claim_without_ablation",
            "introduction says extensive experiments and ablation studies",
            "no ablation table, configuration, protocol, or raw output is present",
            "unsupported_experiment_claim",
        ),
        (
            "accuracy_lower_bound",
            "Accuracy = 1 - |predicted-actual|/actual",
            "the metric can be negative and no zero-price or aggregation convention is stated",
            "metric_boundary_underspecified",
        ),
        (
            "win_rate_first_lag",
            "sum runs from i=1 to T using predicted and actual values at i-1",
            "predicted c_0 and actual c_0 are not defined in the evaluation protocol",
            "metric_boundary_underspecified",
        ),
        (
            "forecast_shape_alignment",
            "LLM emits a multi-step sequence and ML emits a one-step vector before fusion",
            "no shape, horizon, timestamp, or resampling alignment rule is stated",
            "fusion_not_operationally_defined",
        ),
        (
            "cache_agent_four",
            "all four partial reports are cached",
            "expiration tau is defined only for agents 1, 2, and 3",
            "cache_policy_incomplete",
        ),
        (
            "entity_equation",
            "E(n_i) = {e | e in T_ent}",
            "the right side does not depend on n_i and denotes allowed types rather than extracted entities",
            "equation_not_operational",
        ),
        (
            "policy_gradient_label",
            "feedback uses a lightweight policy-gradient update",
            "the printed update is ordinary gradient descent on L(S_u,y), with no policy, log probability, or reward estimator",
            "algorithm_label_conflicts_with_equation",
        ),
        (
            "agent_three_subcomponents",
            "A3 unions four f_k(D_k) components",
            "the four D_k datasets/contracts are not defined sufficiently to execute",
            "submodule_inputs_underspecified",
        ),
        (
            "signal_score_weights",
            "scores combine relevance, recency, and credibility weights",
            "weight normalization, ranges, threshold, calibration, and tie handling are absent",
            "ranking_rule_underspecified",
        ),
        (
            "public_perplexity_version",
            "paper presents contemporary retrieval/case-study models",
            "paper-time public platform pins Perplexity mixtral-8x7b-instruct and contains none of the paper's seven exact templates",
            "public_component_version_mismatch",
        ),
        (
            "medium_term_accuracy_claim",
            "conclusion says medium-term forecasting accuracy improves",
            "Table 1 has no horizon or baseline and Figure 6 is a qualitative recommendation comparison",
            "claim_not_supported_by_reported_metric",
        ),
    ]
    return [
        {
            "canonical_work_id": WORK_ID,
            "check_id": check_id,
            "paper_statement": paper_statement,
            "audited_observation": observation,
            "status": status,
            "effect_on_reproduction": "requires_author_clarification_or_missing_lineage",
            "paper_result_credit": False,
        }
        for check_id, paper_statement, observation, status in checks
    ]


def classify_public_path(path: str) -> str:
    name = PurePosixPath(path).name
    if name in {"requirements.txt", "package.json", "package-lock.json", "setup.py"}:
        return "environment_or_dependency_manifest"
    if name in {"app.py", "vite.config.js"}:
        return "runner_or_build_configuration"
    if path.startswith("examples/") or path.startswith("tests/"):
        return "support_or_example"
    if path.endswith((".py", ".js", ".vue", ".ts", ".jsx", ".tsx")):
        return "source_code"
    if name.lower().startswith("readme") or name in {"LICENSE", ".env.example"}:
        return "documentation_or_configuration"
    return "asset_or_other"


def public_source_snapshots(
    audit_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, bytes]]]:
    summaries: list[dict[str, Any]] = []
    archives: dict[str, dict[str, bytes]] = {}
    for source_id, pin in PUBLIC_SOURCE_PINS.items():
        archive_path = pinned_path(
            audit_root, pin["archive"], pin["archive_sha256"]
        )
        if archive_path.stat().st_size != pin["archive_bytes"]:
            raise ValueError(f"{source_id} archive size changed")
        files = safe_tar_files(archive_path)
        if len(files) != pin["file_count"]:
            raise ValueError(f"{source_id} file count changed")
        archives[source_id] = files
        summaries.append(
            {
                "source_id": source_id,
                "repository": pin["repository"],
                "commit": pin["commit"],
                "commit_time": pin["commit_time"],
                "archive_sha256": pin["archive_sha256"],
                "archive_bytes": pin["archive_bytes"],
                "file_count": pin["file_count"],
                "license": pin["license"],
                "paper_time_relation": pin["paper_time_relation"],
                "attribution_basis": (
                    "MountainLionAi organization; repository documentation states mlion.ai "
                    "uses the platform; frontend author email matches paper v2 author Jinhao Wang"
                ),
                "paper_result_generation_source_found": False,
            }
        )
    return summaries, archives


def public_source_file_inventory(
    archives: Mapping[str, Mapping[str, bytes]],
) -> list[dict[str, Any]]:
    rows = []
    for source_id in ("frontend", "backend_paper_time"):
        for path, payload in sorted(archives[source_id].items()):
            rows.append(
                {
                    "source_id": source_id,
                    "commit": PUBLIC_SOURCE_PINS[source_id]["commit"],
                    "path": path,
                    "bytes": len(payload),
                    "sha256": sha256_bytes(payload),
                    "file_kind": classify_public_path(path),
                    "paper_table_result_generator": False,
                    "paper_result_array": False,
                    "fitted_paper_model": False,
                    "paper_result_credit": False,
                }
            )
    if Counter(row["source_id"] for row in rows) != {
        "frontend": 153,
        "backend_paper_time": 199,
    }:
        raise RuntimeError("public source inventory boundary changed")
    return rows


def runtime_evidence(audit_root: Path) -> dict[str, Any]:
    observed_hashes = {
        name: sha256(pinned_path(audit_root, name, digest))
        for name, digest in RUNTIME_FILE_PINS.items()
    }
    first_manifest = (audit_root / "frontend_build_repeat1.manifest").read_bytes()
    second_manifest = (audit_root / "frontend_build_repeat2.manifest").read_bytes()
    if first_manifest != second_manifest:
        raise ValueError("frontend repeated build manifests differ")
    if len(first_manifest.decode("utf-8").splitlines()) != 67:
        raise ValueError("frontend build output count changed")
    full_compile = (audit_root / "backend_compile_full.log").read_text(
        encoding="utf-8"
    )
    if "await' outside function" not in full_compile:
        raise ValueError("expected backend full-tree compile failure changed")
    return {
        "frontend": {
            "source_commit": PUBLIC_SOURCE_PINS["frontend"]["commit"],
            "environment": "Bouchet nodejs/20.13.1-GCCcore-13.3.0; Node v20.13.1; npm 10.5.2",
            "install_command": "npm ci --no-audit --no-fund",
            "install_outcome": "pass_added_561_packages_from_locked_package_lock_v2",
            "build_command": "npm run build",
            "build_outcome": "pass_twice_vite_4.3.9_2929_modules",
            "repeated_output_manifest_sha256": sha256_bytes(first_manifest),
            "repeated_outputs_byte_identical": True,
            "dist_file_count": 67,
            "dist_bytes": 4_836_274,
            "warnings": [
                "eval in src/App.vue is strongly discouraged",
                "one or more minified chunks exceed 500 kB",
            ],
            "paper_result_credit": False,
        },
        "backend_paper_time": {
            "source_commit": PUBLIC_SOURCE_PINS["backend_paper_time"]["commit"],
            "environment": "Bouchet Python 3.9.21",
            "core_compile_command": "python3 -m compileall -q genaipf app.py setup.py",
            "core_compile_exit": 0,
            "repository_compile_command": "python3 -m compileall -q .",
            "repository_compile_exit": 1,
            "repository_compile_failure": (
                "examples/utils/redis_t001.py:13 uses await outside an async function"
            ),
            "public_test_function_count": 0,
            "tests_directory_files": ["tests/__init__.py (empty)"],
            "full_service_started": False,
            "startup_blockers": [
                "unreleased ml4gp modules imported by product controllers/services",
                "private MySQL schema and data including kline_predictd",
                "Redis and external API credentials",
                "product plugin/service implementation",
            ],
            "paper_result_credit": False,
        },
        "runtime_evidence_file_sha256": observed_hashes,
    }


def check_row(
    check_id: str,
    surface: str,
    expected: str,
    observed: str,
    status: str,
    component_credit: bool,
    note: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "surface": surface,
        "expected": expected,
        "observed": observed,
        "status": status,
        "paper_corresponding_component_credit": component_credit,
        "exact_native_paper_mechanism_credit": False,
        "paper_result_credit": False,
        "note": note,
    }


def source_component_checks(
    archives: Mapping[str, Mapping[str, bytes]],
    execution: Mapping[str, Any],
) -> list[dict[str, Any]]:
    front = archives["frontend"]
    back = archives["backend_paper_time"]
    api_text = front["src/api/api.js"].decode("utf-8")
    exports = re.findall(r"^export const (\w+)", api_text, flags=re.MULTILINE)
    endpoints = {
        name: path
        for name, path in re.findall(
            r"export const (\w+).*?url:\s*['\"]([^'\"]+)",
            api_text,
            flags=re.DOTALL,
        )
    }
    expected_endpoints = {
        "getCoinList": "/v1/api/getCoinList",
        "getKlineInfo": "/v1/api/getKlineInfo",
        "sendchat": "/v1/api/sendChat",
        "getPredictInfo": "/v1/api/getPredictInfo",
    }
    lock = json.loads(front["package-lock.json"])

    price_path = "genaipf/bot/tg/client/price_predict_client.py"
    price_tree = ast.parse(back[price_path].decode("utf-8"))
    url_param: dict[str, tuple[str, str]] | None = None
    for node in price_tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "url_param"
            for target in node.targets
        ):
            url_param = ast.literal_eval(node.value)
    if url_param is None:
        raise ValueError("paper-time token menu not found")
    source_tokens = {pair[0] for pair in url_param.values()}
    paper_tokens = {row[0] for row in TABLE_VALUES}

    all_backend_text = "\n".join(
        payload.decode("utf-8", errors="ignore")
        for path, payload in back.items()
        if path.endswith((".py", ".md", ".txt"))
    )
    ml4gp_files = sorted(
        path
        for path, payload in back.items()
        if path.endswith(".py")
        and re.search(r"(?:from|import)\s+ml4gp", payload.decode("utf-8"))
    )
    test_defs = sum(
        len(re.findall(r"^(?:async\s+)?def\s+test_", payload.decode("utf-8"), re.MULTILINE))
        for path, payload in back.items()
        if path.endswith(".py")
    )
    gpt_service = back["genaipf/services/gpt_service.py"].decode("utf-8")
    setup_text = back["setup.py"].decode("utf-8")
    env_text = back[".env.example"].decode("utf-8")

    rows = [
        check_row(
            "frontend_exported_api_count",
            "frontend",
            "25",
            str(len(exports)),
            "pass",
            True,
            "real product API client surface, not a result generator",
        ),
        check_row(
            "frontend_appendix_endpoints",
            "frontend",
            json.dumps(expected_endpoints, sort_keys=True),
            json.dumps({key: endpoints.get(key) for key in expected_endpoints}, sort_keys=True),
            "pass" if all(endpoints.get(k) == v for k, v in expected_endpoints.items()) else "fail",
            True,
            "exact endpoint names and paths correspond to the paper appendix",
        ),
        check_row(
            "frontend_dependency_lock",
            "frontend",
            "package-lock lockfileVersion 2",
            f"lockfileVersion {lock.get('lockfileVersion')}",
            "pass" if lock.get("lockfileVersion") == 2 else "fail",
            True,
            "locked frontend dependency graph",
        ),
        check_row(
            "frontend_repeated_build",
            "frontend",
            "two successful byte-identical builds",
            (
                f"{execution['frontend']['dist_file_count']} files; manifest "
                f"{execution['frontend']['repeated_output_manifest_sha256']}"
            ),
            "pass",
            True,
            "documented UI build only; no table or trading-result credit",
        ),
        check_row(
            "paper_table_token_menu_match",
            "backend_paper_time",
            ",".join(sorted(paper_tokens)),
            ",".join(sorted(source_tokens)),
            "pass" if source_tokens == paper_tokens else "fail",
            True,
            "strong product correspondence; the menu does not train or evaluate forecasts",
        ),
        check_row(
            "prediction_database_reader",
            "backend_paper_time",
            "reader for kline_predictd records",
            "SELECT date, open, high, low, close ... order by date desc limit 3",
            "pass" if "FROM kline_predictd" in gpt_service else "fail",
            True,
            "reads three precomputed records; no forecast fitting or Table 1 evaluation",
        ),
        check_row(
            "backend_core_compile",
            "backend_paper_time",
            "exit 0",
            str(execution["backend_paper_time"]["core_compile_exit"]),
            "pass",
            True,
            "syntax-level component execution under Python 3.9.21",
        ),
        check_row(
            "backend_repository_compile",
            "backend_paper_time",
            "exit 0",
            str(execution["backend_paper_time"]["repository_compile_exit"]),
            "fail",
            False,
            execution["backend_paper_time"]["repository_compile_failure"],
        ),
        check_row(
            "backend_public_tests",
            "backend_paper_time",
            ">=1 executable test",
            f"{test_defs} test functions; tests/__init__.py is empty",
            "missing",
            False,
            "examples and debug scripts are not a paper-result test suite",
        ),
        check_row(
            "backend_private_module_boundary",
            "backend_paper_time",
            "all imported product modules public",
            f"ml4gp imported by {len(ml4gp_files)} files; no ml4gp package shipped",
            "blocked",
            False,
            "; ".join(ml4gp_files),
        ),
        check_row(
            "backend_install_contract",
            "backend_paper_time",
            "editable install declares complete dependencies/packages",
            "setup.py packages=['genaipf']; install_requires=[]; separate requirements.txt",
            "incomplete",
            False,
            "pip install -e . alone cannot instantiate the documented platform",
        ),
        check_row(
            "backend_private_runtime_state",
            "backend_paper_time",
            "frozen public data/services",
            "placeholder MySQL/Redis credentials and plugin4gp service; no database snapshot",
            "blocked",
            False,
            "private service state remains the decisive runtime boundary",
        ),
        check_row(
            "paper_prompt_templates_in_backend",
            "backend_paper_time",
            "7 exact paper templates",
            "0 exact paper-template prefix matches",
            "missing",
            False,
            "paper templates exist only in the TeX source",
        ),
        check_row(
            "perplexity_model_version",
            "backend_paper_time",
            "paper-reported runtime identity",
            "mixtral-8x7b-instruct",
            "version_mismatch_or_unresolved",
            False,
            "generic public platform client is not an immutable paper request",
        ),
        check_row(
            "result_generation_assets",
            "frontend_and_backend",
            "training panel, fitted model, predictions, scores, and table runner",
            "none found in 352 paper-relevant public source files",
            "missing",
            False,
            "there is no public path capable of regenerating any Table 1 performance cell",
        ),
        check_row(
            "frontend_live_api",
            "deployed_endpoint",
            "reachable frozen paper-era API",
            "api1-test.mountainlion.ai root and getCoinList timed out after 4s connect on 2026-08-12",
            "unreachable_observation",
            False,
            "bounded present-day observation; not proof of historical unavailability",
        ),
        check_row(
            "current_product_site",
            "deployed_endpoint",
            "paper-era application snapshot",
            "www.mountainlion.ai returned HTTP 200 but now serves a newer assistant landing page",
            "post_paper_drift",
            False,
            "live product is not an immutable experiment artifact",
        ),
    ]
    if "install_requires=[" not in re.sub(r"\s+", "", setup_text):
        raise ValueError("backend setup.py boundary changed")
    if "MYSQL_PASSWORD = \"xxx\"" not in env_text:
        raise ValueError("backend .env placeholder boundary changed")
    if "mixtral-8x7b-instruct" not in all_backend_text:
        raise ValueError("paper-time Perplexity model boundary changed")
    return rows


def paper_formula_component_checks() -> list[dict[str, Any]]:
    llm = [100.0, 110.0]
    ml = [96.0, 102.0]
    alpha = 0.25
    fused = [alpha * a + (1 - alpha) * b for a, b in zip(llm, ml)]
    accuracy = 1 - abs(110.0 - 100.0) / 100.0
    negative_accuracy = 1 - abs(300.0 - 100.0) / 100.0
    predicted = [100.0, 102.0, 101.0]
    actual = [100.0, 101.0, 99.0]
    matches = [
        math.copysign(1, predicted[i] - predicted[i - 1])
        == math.copysign(1, actual[i] - actual[i - 1])
        for i in range(1, len(predicted))
    ]
    win_rate = sum(matches) / len(matches)
    rows = [
        (
            "convex_fusion",
            "alpha*Y_LLM + (1-alpha)*Y_ML",
            '{"alpha":0.25,"llm":[100,110],"ml":[96,102]}',
            json.dumps(fused),
            "passes_declared_equation",
        ),
        (
            "point_accuracy",
            "1-|predicted-actual|/actual",
            '{"predicted":110,"actual":100}',
            f"{accuracy:.12g}",
            "passes_declared_equation",
        ),
        (
            "negative_accuracy_boundary",
            "1-|predicted-actual|/actual",
            '{"predicted":300,"actual":100}',
            f"{negative_accuracy:.12g}",
            "demonstrates_unstated_negative_range",
        ),
        (
            "directional_win_rate_defined_lags_only",
            "mean(sign(predicted change)==sign(actual change))",
            '{"predicted":[100,102,101],"actual":[100,101,99]}',
            f"{win_rate:.12g}",
            "passes_after_supplying_unreported_lag_boundary",
        ),
        (
            "cache_freshness",
            "reuse if now-cached < tau_i",
            '{"age_minutes":20,"agent":1,"tau_minutes":30}',
            "reuse=True",
            "passes_declared_equation",
        ),
    ]
    return [
        {
            "check_id": check_id,
            "paper_equation": equation,
            "synthetic_input": inputs,
            "synthetic_output": output,
            "status": status,
            "paper_specification_component_credit": True,
            "native_source_implementation_executed": False,
            "paper_result_credit": False,
        }
        for check_id, equation, inputs, output, status in rows
    ]


def discovery_evidence() -> list[dict[str, Any]]:
    checked = "2026-08-12T16:38:40Z"
    entries = [
        (
            "arxiv_v1_v2_pdf_and_source",
            "https://arxiv.org/abs/2507.20474",
            "primary_paper_source",
            "two 17-page versions; 11/10-file manuscript bundles; no operational code/data",
            True,
        ),
        (
            "mountainlion_frontend_repository",
            "https://github.com/MountainLionAi/MountainLion",
            "attributable_product_component",
            "153 files at pinned head; exact appendix endpoints; deterministic Node-20 build",
            True,
        ),
        (
            "genai_platform_paper_time_repository",
            "https://github.com/MountainLionAi/GenAI-Platform/tree/98b98d31dec6d29a5c518943d980300612030a40",
            "attributable_platform_component",
            "199 files at last public pre-v1 commit; exact ten-token menu and prediction DB reader",
            True,
        ),
        (
            "genai_platform_current_repository",
            "https://github.com/MountainLionAi/GenAI-Platform/tree/3f76de1fe4d8d423f7d4e46e45f19f5bd43992ec",
            "post_paper_boundary",
            "220 files; useful for drift checking, not evidence of paper-time execution",
            True,
        ),
        (
            "frontend_author_attribution",
            "https://github.com/MountainLionAi/MountainLion/commit/f7819f3537808d398f6c3da37e43b51ecebdbd42",
            "attribution_evidence",
            "committer WJH2023 uses jinhaow@mail.smu.edu; Jinhao Wang is a paper-v2 author",
            True,
        ),
        (
            "platform_product_statement",
            "https://github.com/MountainLionAi/GenAI-Platform",
            "attribution_evidence",
            "README states mlion.ai is built on this platform technology",
            True,
        ),
        (
            "paper_era_api",
            "https://api1-test.mountainlion.ai/v1/api/getCoinList",
            "deployment_observation",
            "connection timeout from Bouchet; present-day bounded observation only",
            False,
        ),
        (
            "current_product_site",
            "https://www.mountainlion.ai",
            "deployment_observation",
            "HTTP 200; current landing page is not a frozen paper-era application/result",
            False,
        ),
        (
            "missing_ml4gp_global_code_boundary",
            "https://github.com/search?q=ml4gp&type=code",
            "bounded_negative_search",
            "no attributable public ml4gp package found; imports remain in the platform source",
            False,
        ),
    ]
    return [
        {
            "search_or_source": name,
            "url": url,
            "evidence_kind": kind,
            "checked_at_utc": checked,
            "bounded_result": result,
            "attributable_primary_or_component_source": attributable,
            "native_paper_result_pipeline_found": False,
            "negative_inference_boundary": (
                "absence in checked public surfaces is not proof that private, deleted, "
                "historical, or unindexed artifacts never existed"
            ),
        }
        for name, url, kind, result, attributable in entries
    ]


def manuscript_rebuilds(audit_root: Path) -> list[dict[str, Any]]:
    rows = []
    for version, pin in REBUILD_PINS.items():
        first = unique_glob(audit_root, pin["first_glob"])
        repeat = unique_glob(audit_root, pin["repeat_glob"])
        first_hash = sha256(first)
        repeat_hash = sha256(repeat)
        if first_hash != pin["sha256"] or repeat_hash != pin["sha256"]:
            raise ValueError(f"{version} deterministic rebuild changed")
        pages = len(PdfReader(str(first)).pages)
        if pages != pin["pages"]:
            raise ValueError(f"{version} rebuilt page count changed")
        rows.append(
            {
                "paper_version": version,
                "build_method": "unmodified_primary_TeX_with_TeX_Live_2024",
                "build_sha256": first_hash,
                "repeat_build_sha256": repeat_hash,
                "same_hash_across_independent_build_directories": first_hash == repeat_hash,
                "page_count": pages,
                "published_page_count": PDF_PINS[version]["pages"],
                "normalized_extracted_word_set_jaccard": pin[
                    "normalized_text_word_set_jaccard"
                ],
                "normalized_100dpi_raster_mean_absolute_difference": pin[
                    "normalized_raster_mean_absolute_difference"
                ],
                "normalized_100dpi_raster_max_page_difference": pin[
                    "normalized_raster_max_page_difference"
                ],
                "full_contact_sheet_visual_qa": (
                    "passed_all_17_pages_readable_no_clipping_overlap_or_missing_content"
                ),
                "document_reconstruction_credit": True,
                "paper_result_reproduction": False,
            }
        )
    return rows


def readme_text(manifest: Mapping[str, Any]) -> str:
    return f"""# MountainLion primary-source replication audit

## Honest outcome

The MountainLion paper is **not faithfully reproduced**. The audit verifies the
primary manuscript, two attributable public codebases, several real product
components, and paper-declared formulas. It regenerates **0/{manifest['published_performance_result_units']}**
published forecasting-performance cells and none of the material return,
accuracy-improvement, retrieval-efficiency, whale-detection, engagement, or
ablation claims.

There is no defensible single percentage for overall paper faithfulness because
document reconstruction, component correspondence, and experimental replay are
not interchangeable. The auditable breakdown is:

- manuscript reconstruction: 2/2 arXiv versions build deterministically to all
  17 pages and pass full contact-sheet visual QA;
- prompt documentation: 7/7 verbatim templates are present, but 0/7 substituted
  requests, exact runtime configurations, or responses are released/replayed;
- public product components: the 153-file frontend builds twice to the same 67
  artifacts, and the 199-file paper-time platform core compiles;
- experimental reproduction: 0/20 Table 1 CV/MSE cells and 0 material outcome
  claims reproduce from a native paper pipeline.

## What the recovered repositories establish

The `MountainLionAi/MountainLion` frontend is strongly attributable: its author
email corresponds to paper-v2 author Jinhao Wang, and its API exports match the
appendix endpoints (`getCoinList`, `getKlineInfo`, `sendChat`, and
`getPredictInfo`). Under Node 20.13.1, its locked install and Vite build pass; two
builds have byte-identical file manifests.

The paper-time `MountainLionAi/GenAI-Platform` snapshot is also attributable.
Its README states that mlion.ai uses the platform; it contains RAG, Perplexity,
multi-agent infrastructure, a `kline_predictd` database reader, and exactly the
ten Table 1 tokens in its price-prediction menu. These are genuine component
correspondences, not a forecast experiment. The reader returns three already
computed database rows; it does not fit models or generate Table 1.

## Decisive reproduction boundary

The public package contains no paper training panel, exchange/date/frequency,
preprocessing, split, model specification, fitted model, cross-validation
protocol, prediction array, realized target array, or table-generation runner.
It also depends on unreleased `ml4gp` product modules, private MySQL/Redis state,
external credentials, and a product plugin. Public tests are absent (the sole
`tests/__init__.py` is empty). Installing more packages cannot recover those
private inputs or the missing experiment lineage.

The paper's only numeric result table has 30 numeric units: 10 ambiguous `Alpha`
configuration cells plus 20 CV/MSE performance cells. Raw MSE is compared across
tokens with radically different price scales, so the prose claim that TRX is the
best performer is not justified without a normalization convention. The paper
also claims improved returns and extensive ablations without reporting a return
path, transaction costs, an ablation table, or an ablation protocol.

The author-rendered comparison figure and six diagram assets are preserved in
both source versions. They establish what the authors placed in the paper, not
how the outputs were produced. No underlying prompt response, source panel, or
numeric array is shipped, so the figure receives no result-reproduction credit.

## Evidence files

- `paper_version_summary.csv`: pinned PDFs and source archives.
- `paper_source_inventory.csv`: every file in both primary TeX bundles.
- `published_table_numeric_ledger.csv`: all 30 Table 1 numeric units.
- `author_figure_inventory.csv`: all 12 versioned figure assets (6 unique).
- `prompt_inventory.csv`: all seven verbatim prompt templates and runtime gaps.
- `material_claims.csv`: central quantitative and qualitative outcome claims.
- `mechanism_conformance.csv`: 38 paper-mechanism dimensions.
- `specification_gaps.csv`: exact missing inputs needed for replay.
- `internal_consistency.csv`: ambiguities and paper-internal conflicts.
- `public_source_snapshot_summary.csv`: three pinned public-code snapshots.
- `public_source_file_inventory.csv`: every paper-relevant frontend/platform file.
- `source_component_checks.csv`: executed and source-semantic component checks.
- `paper_formula_component_checks.csv`: synthetic checks of declared equations.
- `source_component_execution.json`: build/compile evidence and runtime blockers.
- `manuscript_rebuilds.json`: deterministic builds and visual-QA record.
- `public_source_discovery.csv`: attributable-source and bounded-search record.

The negative search boundary is deliberately narrow: this audit does not prove
that private, deleted, historical, or unindexed artifacts never existed.
"""


def build_audit(audit_root: Path, output_dir: Path) -> dict[str, Any]:
    bundles = paper_sources(audit_root)
    versions = paper_version_summary(audit_root)
    paper_files = paper_source_inventory(bundles)
    figures = figure_inventory(paper_files)
    table = published_table_ledger()
    prompts = prompt_inventory(bundles["2507.20474v2"]["main.tex"].decode("utf-8"))
    claims = material_claims()
    mechanisms = mechanism_conformance()
    gaps = specification_gaps()
    consistency = internal_consistency_checks()
    source_summaries, source_archives = public_source_snapshots(audit_root)
    public_files = public_source_file_inventory(source_archives)
    execution = runtime_evidence(audit_root)
    components = source_component_checks(source_archives, execution)
    formulas = paper_formula_component_checks()
    discovery = discovery_evidence()
    rebuilds = manuscript_rebuilds(audit_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "paper_version_summary.csv", versions)
    write_csv(output_dir / "paper_source_inventory.csv", paper_files)
    write_csv(output_dir / "published_table_numeric_ledger.csv", table)
    write_csv(output_dir / "author_figure_inventory.csv", figures)
    write_csv(output_dir / "prompt_inventory.csv", prompts)
    write_csv(output_dir / "material_claims.csv", claims)
    write_csv(output_dir / "mechanism_conformance.csv", mechanisms)
    write_csv(output_dir / "specification_gaps.csv", gaps)
    write_csv(output_dir / "internal_consistency.csv", consistency)
    write_csv(output_dir / "public_source_snapshot_summary.csv", source_summaries)
    write_csv(output_dir / "public_source_file_inventory.csv", public_files)
    write_csv(output_dir / "source_component_checks.csv", components)
    write_csv(output_dir / "paper_formula_component_checks.csv", formulas)
    write_csv(output_dir / "public_source_discovery.csv", discovery)
    write_json(output_dir / "source_component_execution.json", execution)
    write_json(output_dir / "manuscript_rebuilds.json", rebuilds)

    table_kinds = Counter(row["cell_kind"] for row in table)
    quantitative_claims = sum(row["claim_kind"] == "quantitative" for row in claims)
    component_credits = sum(
        bool(row["paper_corresponding_component_credit"]) for row in components
    )
    manifest: dict[str, Any] = {
        "audit": "MountainLion primary-source and attributable-code replication audit",
        "canonical_work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "overall_status": "not_reproduced_public_components_only_no_result_lineage",
        "full_paper_reproduced": False,
        "paper_versions_pinned": len(versions),
        "paper_source_files": len(paper_files),
        "manuscripts_rebuilt_deterministically": len(rebuilds),
        "manuscript_rebuilds_receive_result_credit": False,
        "published_numeric_table_units": len(table),
        "published_configuration_units": table_kinds["configuration"],
        "published_performance_result_units": table_kinds["direct_result"],
        "published_performance_result_units_faithfully_regenerated": 0,
        "material_claims_inventoried": len(claims),
        "material_quantitative_claims_inventoried": quantitative_claims,
        "material_claims_faithfully_regenerated": 0,
        "verbatim_prompt_templates": len(prompts),
        "runtime_prompt_requests_replayed": 0,
        "versioned_author_figure_assets": len(figures),
        "unique_author_figure_assets": len({row["sha256"] for row in figures}),
        "versioned_author_case_study_outputs": sum(
            bool(row["author_rendered_output_correspondence"]) for row in figures
        ),
        "author_case_study_outputs_faithfully_regenerated": 0,
        "attributable_public_repositories": 2,
        "pinned_public_source_snapshots": len(source_summaries),
        "paper_relevant_public_source_files": len(public_files),
        "paper_corresponding_source_component_checks_passed": component_credits,
        "exact_native_paper_mechanism_dimensions_reproduced": 0,
        "paper_mechanism_dimensions_audited": len(mechanisms),
        "paper_formula_components_checked": len(formulas),
        "frontend_repeated_build_byte_identical": True,
        "frontend_dist_files": execution["frontend"]["dist_file_count"],
        "backend_paper_time_core_compiles": True,
        "backend_public_test_functions": 0,
        "native_result_generation_pipeline_found": False,
        "material_internal_or_specification_issues": len(consistency),
        "precise_blocker": (
            "attributable frontend/platform components are public, but the training panel, "
            "split, exact models, fitted artifacts, requests/responses, predictions, realized "
            "targets, result runner, private ml4gp modules, product database, portfolio path, "
            "and costs are not"
        ),
        "negative_inference_boundary": (
            "no native paper-result pipeline found in the pinned public sources and checked "
            "surfaces; not proof that private, deleted, historical, or unindexed artifacts "
            "never existed"
        ),
    }
    (output_dir / "README.md").write_text(readme_text(manifest), encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-root", type=Path, default=DEFAULT_AUDIT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return nonzero while the full paper remains unreproduced.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(args.audit_root, args.output_dir)
    print(json.dumps(manifest, indent=2))
    return 1 if args.strict and not manifest["full_paper_reproduced"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
