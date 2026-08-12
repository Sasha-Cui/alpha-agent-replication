#!/usr/bin/env python3
"""Build a fail-closed primary-source audit for the MarketSenseAI lineage.

The audit treats the two arXiv papers as separate experiments even though they
describe the same commercial system. It validates every numeric result unit in
their published tables, inventories every empirical figure asset, rebuilds all
three manuscript versions from primary TeX, and checks identities recoverable
from displayed values. Manuscript reconstruction and author-rendered figures
receive document/output-correspondence credit only. They never receive native
system or paper-result reproduction credit.

No attributable operational implementation, signal panel, raw result array,
immutable live-output log, prompt set, or portfolio path is public in the
pinned evidence. Consequently this audit intentionally reports zero faithfully
regenerated MarketSenseAI result units.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

from pypdf import PdfReader
from scipy.stats import t as student_t


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_ROOT = Path("/nfs/roberts/scratch/pi_btk22/zc362/marketsense_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/marketsenseai"

WORK_2025 = "CensusArxiv250200415"
WORK_2026 = "CensusArxiv260417327"
SYSTEM_ID = "SYS-MARKET-SENSE-AI"

PDF_PINS = {
    "2502.00415v1": {
        "path": "downloads/2502.00415v1.pdf",
        "url": "https://arxiv.org/pdf/2502.00415v1",
        "sha256": "0e83d5f656da54fed88f95a8c2a1bce186a5e786fb7f05c1d73579154d450ed3",
        "pages": 25,
    },
    "2502.00415v2": {
        "path": "downloads/2502.00415v2.pdf",
        "url": "https://arxiv.org/pdf/2502.00415v2",
        "sha256": "3755b957dc366d0e9117fffb2ae6ddc241e682498bcd7b4ce1c830119d99db65",
        "pages": 10,
    },
    "2604.17327v1": {
        "path": "downloads/2604.17327v1.pdf",
        "url": "https://arxiv.org/pdf/2604.17327v1",
        "sha256": "a9ba1f0627708d9a766ce12d258733753153bc905e84fc856e5a291c0f8805ad",
        "pages": 22,
    },
}

SOURCE_PINS = {
    "2502.00415v1": {
        "archive": "downloads/2502.00415v1.tar",
        "archive_url": "https://export.arxiv.org/e-print/2502.00415v1",
        "archive_sha256": "5e79627752d1b87794f477a08b1808d2ff337333f0d83fac4965e01043cd403a",
        "source_dir": "source/2502.00415v1",
        "file_count": 18,
        "source_bytes": 6_298_390,
        "main": "sn-article-arxiv.tex",
        "main_sha256": "0fd5a099435028e019a694fe6b089915ccfcddb836447d93a17a39bb81fc61a2",
    },
    "2502.00415v2": {
        "archive": "downloads/2502.00415v2.tar",
        "archive_url": "https://export.arxiv.org/e-print/2502.00415v2",
        "archive_sha256": "b1192cf20f1ca743f50724c2c955626d26aa1b6ec50b726a0b2882a6133e9f74",
        "source_dir": "source/2502.00415v2",
        "file_count": 14,
        "source_bytes": 5_410_847,
        "main": "conference_101719.tex",
        "main_sha256": "6223e8dc7ff1412d0952030ca8a96b83d83964d190d5f9b2a53c21e473e92984",
    },
    "2604.17327v1": {
        "archive": "downloads/2604.17327v1.tar",
        "archive_url": "https://export.arxiv.org/e-print/2604.17327v1",
        "archive_sha256": "5670ddbb7f3db545e5d8aeeb6c9105da1818413fe8e1698ca6814f3ca89fd6f6",
        "source_dir": "source/2604.17327v1",
        "file_count": 13,
        "source_bytes": 307_099,
        "main": "main.tex",
        "main_sha256": "092ecfe6218f3cce14defcd7fdba1d2047606d471fa82e53a2d9f539c007cc04",
    },
}

REBUILD_PINS = {
    "2502.00415v1": {
        "path": "builds/2502.00415v1/sn-article-arxiv.pdf",
        "sha256": "6815514789bf3376d5c3d4c7d9731a550799195e2eea72ee41d182b2d3380d3c",
        "pages": 25,
        "source_date_epoch": 1_738_676_036,
        "normalized_text_similarity": 0.9996488854253196,
        "normalized_raster_mad": 0.00004460080624814958,
    },
    "2502.00415v2": {
        "path": "builds/2502.00415v2/conference_101719.pdf",
        "sha256": "3ddd65992934ba2e755c05a1228e06841d4f5ed99b040cd7fbbc60fb88c07e46",
        "pages": 10,
        "source_date_epoch": 1_759_739_015,
        "normalized_text_similarity": 0.9975975551590737,
        "normalized_raster_mad": 0.0001421772045716682,
    },
    "2604.17327v1": {
        "path": "builds/2604.17327v1/main.pdf",
        "sha256": "78d34396edfee92781e18ab4e72d427c974ddf033cf978ae0c4076361c004efd",
        "pages": 22,
        "source_date_epoch": 1_776_733_504,
        "normalized_text_similarity": 0.994016746605967,
        "normalized_raster_mad": 0.00012987600748702772,
    },
}

EMPIRICAL_2025 = {
    "fig-2024-spx500.png",
    "fig-fundamentals-hist.png",
    "fig-fundamentals-scatter.png",
    "fig-ms-hist.png",
    "fig-ms-scatter.png",
    "fig-spx100.png",
}
EMPIRICAL_2026 = {
    "figures/fig2.pdf",
    "figures/fig3.pdf",
    "figures/fig4.pdf",
    "figures/fig5.pdf",
    "figures/fig6.pdf",
    "figures/figA5.pdf",
    "figures/fig_beta_regression.pdf",
    "figures/fig_conditional_returns.pdf",
    "figures/fig_return_hist.pdf",
    "figures/fig_sector_strongbuy.pdf",
}


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


def result_row(
    work: str,
    version: str,
    table: str,
    cohort: str,
    method: str,
    metric: str,
    value: Any,
    unit: str,
    cell_kind: str = "direct_result",
) -> dict[str, Any]:
    is_result = cell_kind != "configuration"
    return {
        "canonical_work_id": work,
        "paper_version": version,
        "paper_table": table,
        "cohort": cohort,
        "method_or_row": method,
        "metric": metric,
        "paper_value": value,
        "unit": unit,
        "cell_kind": cell_kind,
        "primary_source_value_verified": True,
        "native_reproduced_value": "",
        "absolute_difference": "",
        "status": (
            "unavailable_no_native_result_inputs_or_pipeline"
            if is_result
            else "paper_configuration_only_no_native_pipeline"
        ),
        "paper_result_credit": False,
    }


def market_2025_table_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sentiment = {
        "Mean": (0.31, 0.36, 0.24),
        "Std. Dev.": (0.28, 0.40, 0.17),
        "Minimum": (-0.61, -0.85, 0.00),
        "25th Percentile": (0.12, 0.08, 0.10),
        "Median": (0.37, 0.44, 0.21),
        "75th Percentile": (0.53, 0.72, 0.33),
        "Maximum": (0.88, 1.00, 0.96),
    }
    for statistic, values in sentiment.items():
        for metric, value in zip(
            ("sentiment_full", "sentiment_basic", "reported_difference"),
            values,
        ):
            rows.append(
                result_row(
                    WORK_2025,
                    "arXiv:2502.00415v2",
                    "Sentiment statistics",
                    "stocks_and_dates_unspecified",
                    statistic,
                    metric,
                    value,
                    "sentiment_score",
                )
            )

    retrieval = {
        (3, "HyDE"): (0.77, 1.00, 0.76, 0.94, 0.87),
        (3, "Optimized"): (0.67, 1.00, 0.75, 0.89, 0.83),
        (3, "Simple"): (0.75, 1.00, 0.48, 0.86, 0.77),
        (5, "HyDE"): (0.79, 0.99, 0.66, 0.94, 0.85),
        (5, "Optimized"): (0.79, 0.99, 0.56, 0.96, 0.82),
        (5, "Simple"): (0.85, 0.99, 0.48, 0.93, 0.82),
        (7, "HyDE"): (0.91, 1.00, 0.66, 0.98, 0.89),
        (7, "Optimized"): (0.85, 1.00, 0.66, 0.97, 0.87),
        (7, "Simple"): (0.86, 0.99, 0.57, 0.95, 0.84),
    }
    for (top_n, method), values in retrieval.items():
        for metric, value in zip(
            ("recall", "precision", "relevancy", "faithfulness", "overall"),
            values,
        ):
            rows.append(
                result_row(
                    WORK_2025,
                    "arXiv:2502.00415v2",
                    "Retrieval performance",
                    f"top_n={top_n}",
                    method,
                    metric,
                    value,
                    "score",
                )
            )

    performance = {
        ("S&P100_2023_2024", "MS-Eq"): (55.7, 53.2, 2.13, 3.25, 15.6, 9.2, 65),
        ("S&P100_2023_2024", "S&P 100 Eq"): (42.3, 42.3, 1.89, 2.85, 14.1, 10.7, 92),
        ("S&P100_2023_2024", "MS-Cap"): (125.9, 123.0, 2.76, 4.43, 22.3, 13.8, 82),
        ("S&P100_2023_2024", "S&P 100"): (73.5, 73.5, 2.52, 3.82, 16.4, 9.7, 77),
        ("S&P500_2024", "MS-Eq"): (25.8, 24.5, 2.40, 3.68, 14.3, 6.7, 52),
        ("S&P500_2024", "S&P 500 Eq"): (12.8, 12.8, 1.33, 1.91, 13.8, 7.1, 73),
        ("S&P500_2024", "MS-Cap"): (48.7, 47.8, 2.87, 4.39, 20.8, 12.5, 53),
        ("S&P500_2024", "S&P 500"): (25.6, 25.6, 2.26, 3.28, 15.1, 8.4, 46),
    }
    performance_metrics = (
        ("total_return_gross", "percent"),
        ("total_return_after_reported_cost", "percent"),
        ("sharpe", "ratio"),
        ("sortino", "ratio"),
        ("volatility", "percent"),
        ("maximum_drawdown", "percent"),
        ("maximum_drawdown_duration", "days"),
    )
    for (cohort, method), values in performance.items():
        for (metric, unit), value in zip(performance_metrics, values):
            rows.append(
                result_row(
                    WORK_2025,
                    "arXiv:2502.00415v2",
                    "Performance metrics",
                    cohort,
                    method,
                    metric,
                    value,
                    unit,
                )
            )

    attribution = {
        ("S&P100_2023_2024", "MS-Eq"): (0.96, 8.0, 584, 77.1, 35.1, 7.95),
        ("S&P100_2023_2024", "MS-Cap"): (1.24, 10.6, 548, 77.0, 35.1, 7.95),
        ("S&P500_2024", "MS-Eq"): (0.92, 18.9, 1200, 78.0, 144.8, 30.8),
        ("S&P500_2024", "MS-Cap"): (1.27, 17.6, 1229, 77.0, 144.8, 30.8),
    }
    attribution_metrics = (
        ("beta", "coefficient"),
        ("alpha", "percent_unspecified_horizon"),
        ("total_trades", "count"),
        ("win_rate", "percent"),
        ("mean_buy_signals_per_month", "count"),
        ("std_buy_signals_per_month", "count"),
    )
    for (cohort, method), values in attribution.items():
        for (metric, unit), value in zip(attribution_metrics, values):
            rows.append(
                result_row(
                    WORK_2025,
                    "arXiv:2502.00415v2",
                    "Performance attribution",
                    cohort,
                    method,
                    metric,
                    value,
                    unit,
                )
            )

    factors = {
        "Carhart_4_factor": {
            "Mkt-RF": 0.936,
            "SMB": -0.131,
            "HML": 0.110,
            "Mom": 0.178,
            "R_squared": 0.884,
        },
        "Fama_French_5_factor": {
            "Mkt-RF": 0.958,
            "SMB": -0.221,
            "HML": 0.081,
            "RMW": -0.015,
            "CMA": 0.044,
            "R_squared": 0.854,
        },
    }
    for method, values in factors.items():
        for metric, value in values.items():
            rows.append(
                result_row(
                    WORK_2025,
                    "arXiv:2502.00415v2",
                    "Factor model results",
                    "portfolio_or_difference_series_ambiguous",
                    method,
                    metric,
                    value,
                    "coefficient_or_ratio",
                )
            )
    if len(rows) != 157:
        raise RuntimeError(f"expected 157 MarketSenseAI 2.0 result units, got {len(rows)}")
    if any(row["paper_result_credit"] for row in rows):
        raise RuntimeError("MarketSenseAI 2.0 unexpectedly received result credit")
    return rows


def validation_2026_table_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cohort, values in {
        "S&P500": (467, 19, 8873),
        "S&P100": (94, 35, 3290),
    }.items():
        for metric, value in zip(("stocks", "dates", "observation_rows"), values):
            rows.append(
                result_row(
                    WORK_2026,
                    "arXiv:2604.17327v1",
                    "Fixed-cohort design",
                    cohort,
                    "cohort_configuration",
                    metric,
                    value,
                    "count",
                    "configuration",
                )
            )

    signal = {
        "Strong sell": (180, 2.0, 48, 1.5),
        "Sell": (286, 3.2, 77, 2.3),
        "Hold": (6992, 78.8, 2508, 76.2),
        "Buy": (749, 8.4, 310, 9.4),
        "Strong buy": (666, 7.5, 347, 10.5),
        "Total": (8873, 100, 3290, 100),
    }
    for method, values in signal.items():
        for cohort, count, percent in (
            ("S&P500", values[0], values[1]),
            ("S&P100", values[2], values[3]),
        ):
            rows.extend(
                [
                    result_row(
                        WORK_2026,
                        "arXiv:2604.17327v1",
                        "Signal class distribution",
                        cohort,
                        method,
                        "count",
                        count,
                        "count",
                    ),
                    result_row(
                        WORK_2026,
                        "arXiv:2604.17327v1",
                        "Signal class distribution",
                        cohort,
                        method,
                        "share",
                        percent,
                        "percent",
                    ),
                ]
            )

    mc = {
        "avg_strong_buy_picks_per_month": (35.1, 9.9, "count"),
        "mean_monthly_strong_buy_return": (2.18, 2.02, "percent"),
        "mean_monthly_ew_benchmark": (1.15, 1.47, "percent"),
        "mean_monthly_mc_null_median": (1.15, 1.47, "percent"),
        "mean_monthly_excess_vs_ew": (1.02, 0.55, "percent"),
        "mean_monthly_percentile_rank": (99.7, 83.4, "percentile"),
        "mean_monthly_p_value": (0.003, 0.166, "probability"),
        "compound_strong_buy_return": (46.8, 93.2, "percent"),
        "compound_ew_benchmark": (21.6, 62.7, "percent"),
        "compound_mc_null_median": (21.4, 60.7, "percent"),
        "compound_excess_vs_ew": (25.2, 30.5, "percentage_points"),
        "compound_p_value": (0.003, 0.163, "probability"),
    }
    for metric, (sp500, sp100, unit) in mc.items():
        for cohort, value in (("S&P500", sp500), ("S&P100", sp100)):
            rows.append(
                result_row(
                    WORK_2026,
                    "arXiv:2604.17327v1",
                    "Monte Carlo results",
                    cohort,
                    "strong_buy_vs_null",
                    metric,
                    value,
                    unit,
                )
            )
    for cohort, wins, months, rate in (
        ("S&P500", 11, 19, 57.9),
        ("S&P100", 20, 35, 57.1),
    ):
        for metric, value, unit in (
            ("months_strong_buy_beats_ew", wins, "count"),
            ("months_observed", months, "count"),
            ("win_rate", rate, "percent"),
        ):
            rows.append(
                result_row(
                    WORK_2026,
                    "arXiv:2604.17327v1",
                    "Monte Carlo results",
                    cohort,
                    "win_rate",
                    metric,
                    value,
                    unit,
                )
            )

    cosine = {
        "News": (0.571, 8873, 0.534, 3290),
        "Fundamentals": (0.826, 8873, 0.795, 3290),
        "Dynamics": (0.724, 8873, 0.701, 3290),
        "Macro": (0.648, 8873, 0.631, 3290),
    }
    for method, values in cosine.items():
        for cohort, rho, count in (
            ("S&P500", values[0], values[1]),
            ("S&P100", values[2], values[3]),
        ):
            rows.extend(
                [
                    result_row(
                        WORK_2026,
                        "arXiv:2604.17327v1",
                        "Cosine-weight agreement",
                        cohort,
                        method,
                        "spearman_rho",
                        rho,
                        "correlation",
                    ),
                    result_row(
                        WORK_2026,
                        "arXiv:2604.17327v1",
                        "Cosine-weight agreement",
                        cohort,
                        method,
                        "observations",
                        count,
                        "count",
                    ),
                ]
            )
    for cohort, value in (("S&P500", 0.944), ("S&P100", 0.936)):
        rows.append(
            result_row(
                WORK_2026,
                "arXiv:2604.17327v1",
                "Cosine-weight agreement",
                cohort,
                "thesis_reconstruction",
                "mean_cosine",
                value,
                "cosine",
            )
        )

    risk = {
        "Strong buy": (6.39, -5.95, 58.4, 1.07, 0.17, -0.03, 0.37),
        "Buy": (5.93, -6.00, 52.1, 0.99, 0.09, -0.11, 0.28),
        "Hold": (5.27, -6.71, 53.4, 0.79),
    }
    risk_metrics = (
        ("upside_mean", "percent"),
        ("downside_mean", "percent"),
        ("hit_rate", "percent"),
        ("upside_downside_ratio", "ratio"),
        ("delta_upside_downside_vs_hold", "ratio"),
        ("ci95_lower", "ratio"),
        ("ci95_upper", "ratio"),
    )
    for method, values in risk.items():
        for (metric, unit), value in zip(risk_metrics, values):
            rows.append(
                result_row(
                    WORK_2026,
                    "arXiv:2604.17327v1",
                    "Signal risk profile",
                    "S&P500",
                    method,
                    metric,
                    value,
                    unit,
                )
            )

    agent_ic = {
        "S&P500": {
            "News": (0.004, 0.887, -0.035, -0.327, -1.42, 0.086),
            "Fundamentals": (0.052, 0.049, 0.012, 0.092, 0.40, 0.346),
            "Dynamics": (-0.069, 0.009, 0.019, 0.135, 0.59, 0.282),
            "Macro": (0.030, 0.257, 0.016, 0.113, 0.49, 0.314),
            "Score": (0.006, 0.822, 0.051, 0.489, 2.13, 0.024),
        },
        "S&P100": {
            "News": (0.016, 0.688, 0.047, 0.189, 1.12, 0.135),
            "Fundamentals": (-0.025, 0.529, -0.062, -0.218, -1.29, 0.103),
            "Dynamics": (-0.040, 0.311, -0.035, -0.150, -0.89, 0.191),
            "Macro": (0.079, 0.042, 0.033, 0.138, 0.82, 0.210),
            "Score": (0.013, 0.749, 0.018, 0.080, 0.48, 0.319),
        },
    }
    ic_metrics = (
        ("pooled_ic", "correlation"),
        ("pooled_p", "probability"),
        ("date_level_mean_ic", "correlation"),
        ("icir", "ratio"),
        ("t_statistic", "statistic"),
        ("reported_p_t", "probability"),
    )
    for cohort, methods in agent_ic.items():
        for method, values in methods.items():
            for (metric, unit), value in zip(ic_metrics, values):
                rows.append(
                    result_row(
                        WORK_2026,
                        "arXiv:2604.17327v1",
                        "Agent and score information coefficients",
                        cohort,
                        method,
                        metric,
                        value,
                        unit,
                    )
                )

    dates = (
        "2024-09",
        "2024-10",
        "2024-11",
        "2024-12",
        "2025-01",
        "2025-02",
        "2025-03",
        "2025-04",
        "2025-05",
        "2025-06",
        "2025-07",
        "2025-08",
        "2025-09",
        "2025-10",
        "2025-11",
        "2025-12",
        "2026-01",
        "2026-02",
        "2026-03",
        "Mean",
    )
    appendix_values = (
        (48, 5.93, 6.07, -0.14, "48"),
        (57, 0.16, -1.09, 1.25, "91"),
        (55, 8.40, 6.11, 2.28, "91"),
        (74, -3.99, -4.64, 0.65, "88"),
        (41, 6.23, 2.55, 3.68, ">99"),
        (55, -5.85, -2.16, -3.69, "<1"),
        (30, -8.30, -11.00, 2.70, "97"),
        (18, 7.30, 10.55, -3.25, "9"),
        (25, 2.99, 4.55, -1.55, "18"),
        (19, 1.98, 4.29, -2.31, "7"),
        (21, 1.87, -1.66, 3.53, "98"),
        (28, 1.13, 3.89, -2.76, "4"),
        (34, 5.53, 2.07, 3.45, "98"),
        (26, 2.71, -1.68, 4.40, ">99"),
        (32, 0.81, 2.55, -1.75, "6"),
        (25, 2.99, 0.92, 2.07, "97"),
        (20, 14.11, 4.89, 9.22, ">99"),
        (36, -4.70, -1.87, -2.83, "3"),
        (22, 2.07, -2.45, 4.51, ">99"),
        (35.1, 2.18, 1.15, 1.02, "60.7"),
    )
    appendix_metrics = (
        ("strong_buy_count", "count"),
        ("actual_return", "percent"),
        ("null_mean_return", "percent"),
        ("excess_return", "percent"),
        ("percentile_rank", "percentile"),
    )
    for date, values in zip(dates, appendix_values):
        for (metric, unit), value in zip(appendix_metrics, values):
            rows.append(
                result_row(
                    WORK_2026,
                    "arXiv:2604.17327v1",
                    "Appendix Monte Carlo results by date",
                    "S&P500",
                    date,
                    metric,
                    value,
                    unit,
                )
            )

    counts = Counter(row["cell_kind"] for row in rows)
    expected = Counter({"direct_result": 250, "configuration": 6})
    if counts != expected:
        raise RuntimeError(f"2026 table denominator changed: {counts}")
    if any(row["paper_result_credit"] for row in rows):
        raise RuntimeError("2026 validation unexpectedly received result credit")
    return rows


def source_inventory(audit_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for version, pin in SOURCE_PINS.items():
        archive = audit_root / str(pin["archive"])
        if sha256(archive) != pin["archive_sha256"]:
            raise ValueError(f"source archive hash changed for {version}")
        source_dir = audit_root / str(pin["source_dir"])
        main = source_dir / str(pin["main"])
        if sha256(main) != pin["main_sha256"]:
            raise ValueError(f"main TeX hash changed for {version}")
        files = sorted(path for path in source_dir.rglob("*") if path.is_file())
        if len(files) != pin["file_count"]:
            raise ValueError(f"source file count changed for {version}: {len(files)}")
        if sum(path.stat().st_size for path in files) != pin["source_bytes"]:
            raise ValueError(f"source byte count changed for {version}")
        main_text = main.read_text(encoding="utf-8", errors="replace")
        for path in files:
            relative = path.relative_to(source_dir).as_posix()
            if version.startswith("2502") and relative in EMPIRICAL_2025:
                role = "author_rendered_empirical_figure"
            elif version == "2604.17327v1" and relative in EMPIRICAL_2026:
                role = "author_rendered_empirical_figure"
            elif path.suffix.lower() in {".png", ".pdf"}:
                role = "manuscript_architecture_figure" if path.stem in main_text else "unreferenced_manuscript_asset"
            elif path.suffix.lower() in {".tex", ".bib", ".bbl", ".bst", ".cls"}:
                role = "manuscript_source"
            else:
                role = "manuscript_build_metadata"
            rows.append(
                {
                    "paper_version": version,
                    "path": relative,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "asset_role": role,
                    "operational_system_code": False,
                    "raw_numeric_result_array": False,
                    "native_signal_or_portfolio_output": False,
                }
            )
    if any(row["operational_system_code"] for row in rows):
        raise RuntimeError("manuscript archive unexpectedly received system-code credit")
    return rows


def figure_inventory(source_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for source in source_rows:
        if source["asset_role"] != "author_rendered_empirical_figure":
            continue
        rows.append(
            {
                "paper_version": source["paper_version"],
                "path": source["path"],
                "sha256": source["sha256"],
                "author_rendered_output_correspondence": True,
                "underlying_numeric_array_shipped": False,
                "faithfully_regenerated_from_native_pipeline": False,
                "paper_result_credit": False,
                "status": "author_rendered_paper_asset_only_no_raw_result_lineage",
            }
        )
    counts = Counter(row["paper_version"] for row in rows)
    expected = Counter({"2502.00415v1": 6, "2502.00415v2": 6, "2604.17327v1": 10})
    if counts != expected:
        raise RuntimeError(f"empirical figure inventory changed: {counts}")
    return rows


def version_summary(audit_root: Path) -> list[dict[str, Any]]:
    rows = []
    for version, pdf_pin in PDF_PINS.items():
        pdf_path = audit_root / str(pdf_pin["path"])
        observed = sha256(pdf_path)
        if observed != pdf_pin["sha256"]:
            raise ValueError(f"paper PDF hash changed for {version}: {observed}")
        pages = len(PdfReader(pdf_path).pages)
        if pages != pdf_pin["pages"]:
            raise ValueError(f"paper page count changed for {version}: {pages}")
        source = SOURCE_PINS[version]
        rows.append(
            {
                "paper_version": version,
                "paper_url": pdf_pin["url"],
                "paper_sha256": observed,
                "pages": pages,
                "source_archive_url": source["archive_url"],
                "source_archive_sha256": source["archive_sha256"],
                "source_files": source["file_count"],
                "experiment_scope": (
                    "S&P100_2023_2024_and_S&P500_2024"
                    if version.startswith("2502")
                    else "live_S&P500_19_month_and_S&P100_35_month_validation"
                ),
                "same_experiment_as_prior_row": version == "2502.00415v2",
                "paper_result_units_reproduced": 0,
            }
        )
    return rows


def rebuild_summary(audit_root: Path) -> list[dict[str, Any]]:
    rows = []
    for version, pin in REBUILD_PINS.items():
        path = audit_root / str(pin["path"])
        observed = sha256(path)
        if observed != pin["sha256"]:
            raise ValueError(f"deterministic rebuild hash changed for {version}: {observed}")
        pages = len(PdfReader(path).pages)
        if pages != pin["pages"]:
            raise ValueError(f"rebuild page count changed for {version}: {pages}")
        rows.append(
            {
                "paper_version": version,
                "source_date_epoch": pin["source_date_epoch"],
                "compiler": "pdflatex_TeX_Live_2024",
                "rebuilt_pdf_sha256": observed,
                "pages": pages,
                "same_hash_after_repeated_final_compile": True,
                "normalized_extracted_text_sequence_similarity": pin["normalized_text_similarity"],
                "normalized_100dpi_raster_mean_absolute_difference": pin["normalized_raster_mad"],
                "full_contact_sheet_visual_qa": "passed_no_clipping_overlap_or_unreadable_panels",
                "paper_result_reproduction": False,
            }
        )
    return rows


def consistency_row(
    work: str,
    check: str,
    paper_value: Any,
    reconstructed: Any,
    status: str,
    implication: str,
) -> dict[str, Any]:
    difference = ""
    if isinstance(paper_value, (int, float)) and isinstance(reconstructed, (int, float)):
        difference = reconstructed - paper_value
    return {
        "canonical_work_id": work,
        "check": check,
        "paper_value": paper_value,
        "reconstructed_from_displayed_values": reconstructed,
        "reconstructed_minus_paper": difference,
        "status": status,
        "implication": implication,
        "paper_result_credit": False,
    }


def internal_consistency_checks() -> list[dict[str, Any]]:
    rows = [
        consistency_row(
            WORK_2025,
            "S&P100 MS-Cap Sortino improvement over cap-weight benchmark",
            16.0,
            (4.43 / 3.82 - 1) * 100,
            "passes_display_precision",
            "The prose 16% improvement is recoverable from Table values.",
        ),
        consistency_row(
            WORK_2025,
            "S&P500 MS-Cap Sortino improvement in abstract",
            33.8,
            (4.39 / 3.28 - 1) * 100,
            "passes_display_precision",
            "The abstract claim is recoverable from Table values.",
        ),
        consistency_row(
            WORK_2025,
            "S&P500 equal-weight relative return outperformance",
            102.0,
            (25.8 / 12.8 - 1) * 100,
            "passes_display_precision",
            "The reported 102% relative outperformance is a rounded ratio.",
        ),
        consistency_row(
            WORK_2025,
            "Prose says S&P500 portfolios have beta 1.24--1.27",
            "1.24_to_1.27",
            "0.92_and_1.27",
            "fails_against_displayed_attribution_table",
            "1.24 belongs to S&P100 MS-Cap; S&P500 MS-Eq is 0.92.",
        ),
    ]

    retrieval = {
        (3, "HyDE"): (0.77, 1.00, 0.76, 0.94, 0.87),
        (3, "Optimized"): (0.67, 1.00, 0.75, 0.89, 0.83),
        (3, "Simple"): (0.75, 1.00, 0.48, 0.86, 0.77),
        (5, "HyDE"): (0.79, 0.99, 0.66, 0.94, 0.85),
        (5, "Optimized"): (0.79, 0.99, 0.56, 0.96, 0.82),
        (5, "Simple"): (0.85, 0.99, 0.48, 0.93, 0.82),
        (7, "HyDE"): (0.91, 1.00, 0.66, 0.98, 0.89),
        (7, "Optimized"): (0.85, 1.00, 0.66, 0.97, 0.87),
        (7, "Simple"): (0.86, 0.99, 0.57, 0.95, 0.84),
    }
    for (top_n, method), values in retrieval.items():
        rows.append(
            consistency_row(
                WORK_2025,
                f"Retrieval overall is mean of four metrics: top_n={top_n} {method}",
                values[-1],
                mean(values[:-1]),
                "passes_display_precision",
                "The Overall score is the rounded arithmetic mean of the four components.",
            )
        )

    counts_500 = [180, 286, 6992, 749, 666]
    counts_100 = [48, 77, 2508, 310, 347]
    rows.extend(
        [
            consistency_row(
                WORK_2026,
                "S&P500 fixed-cohort Cartesian row count",
                8873,
                467 * 19,
                "exact",
                "The cohort count identity holds.",
            ),
            consistency_row(
                WORK_2026,
                "S&P100 fixed-cohort Cartesian row count",
                3290,
                94 * 35,
                "exact",
                "The cohort count identity holds.",
            ),
            consistency_row(
                WORK_2026,
                "S&P500 signal counts sum to cohort rows",
                8873,
                sum(counts_500),
                "exact",
                "All signal observations are accounted for.",
            ),
            consistency_row(
                WORK_2026,
                "S&P100 signal counts sum to cohort rows",
                3290,
                sum(counts_100),
                "exact",
                "All signal observations are accounted for.",
            ),
            consistency_row(
                WORK_2026,
                "S&P500 average strong-buy count",
                35.1,
                666 / 19,
                "passes_display_precision",
                "The descriptive mean is recoverable.",
            ),
            consistency_row(
                WORK_2026,
                "S&P100 average strong-buy count",
                9.9,
                347 / 35,
                "passes_display_precision",
                "The descriptive mean is recoverable.",
            ),
            consistency_row(
                WORK_2026,
                "S&P500 win rate",
                57.9,
                11 / 19 * 100,
                "passes_display_precision",
                "The win-rate identity holds.",
            ),
            consistency_row(
                WORK_2026,
                "S&P100 win rate",
                57.1,
                20 / 35 * 100,
                "passes_display_precision",
                "The win-rate identity holds.",
            ),
            consistency_row(
                WORK_2026,
                "Strong-buy UpDn ratio from displayed upside/downside",
                1.07,
                6.39 / 5.95,
                "passes_display_precision",
                "The displayed strong-buy UpDn ratio is internally recoverable.",
            ),
            consistency_row(
                WORK_2026,
                "Buy UpDn ratio from displayed upside/downside",
                0.99,
                5.93 / 6.00,
                "passes_display_precision",
                "The displayed buy UpDn ratio is internally recoverable.",
            ),
            consistency_row(
                WORK_2026,
                "Hold UpDn ratio from displayed upside/downside",
                0.79,
                5.27 / 6.71,
                "passes_display_precision",
                "The displayed hold UpDn ratio is internally recoverable.",
            ),
            consistency_row(
                WORK_2026,
                "Strong-buy delta UpDn as defined versus displayed hold ratio",
                0.17,
                1.07 - 0.79,
                "fails_published_delta_definition",
                "The caption defines strong-buy minus hold, but displayed ratios imply 0.28, not 0.17.",
            ),
            consistency_row(
                WORK_2026,
                "Buy delta UpDn as defined versus displayed hold ratio",
                0.09,
                0.99 - 0.79,
                "fails_published_delta_definition",
                "The caption defines buy minus hold, but displayed ratios imply 0.20, not 0.09.",
            ),
        ]
    )

    actual = [
        5.93,
        0.16,
        8.40,
        -3.99,
        6.23,
        -5.85,
        -8.30,
        7.30,
        2.99,
        1.98,
        1.87,
        1.13,
        5.53,
        2.71,
        0.81,
        2.99,
        14.11,
        -4.70,
        2.07,
    ]
    null = [
        6.07,
        -1.09,
        6.11,
        -4.64,
        2.55,
        -2.16,
        -11.00,
        10.55,
        4.55,
        4.29,
        -1.66,
        3.89,
        2.07,
        -1.68,
        2.55,
        0.92,
        4.89,
        -1.87,
        -2.45,
    ]
    excess = [
        -0.14,
        1.25,
        2.28,
        0.65,
        3.68,
        -3.69,
        2.70,
        -3.25,
        -1.55,
        -2.31,
        3.53,
        -2.76,
        3.45,
        4.40,
        -1.75,
        2.07,
        9.22,
        -2.83,
        4.51,
    ]
    compound_actual = (math.prod(1 + value / 100 for value in actual) - 1) * 100
    compound_null = (math.prod(1 + value / 100 for value in null) - 1) * 100
    rows.extend(
        [
            consistency_row(
                WORK_2026,
                "Appendix S&P500 mean actual return",
                2.18,
                mean(actual),
                "passes_display_precision",
                "The main-table mean is recoverable from rounded appendix rows.",
            ),
            consistency_row(
                WORK_2026,
                "Appendix S&P500 mean null return",
                1.15,
                mean(null),
                "passes_display_precision",
                "The main-table mean is recoverable from rounded appendix rows.",
            ),
            consistency_row(
                WORK_2026,
                "Appendix S&P500 mean reported excess",
                1.02,
                mean(excess),
                "passes_display_precision",
                "The mean of displayed per-date excess values rounds to 1.02.",
            ),
            consistency_row(
                WORK_2026,
                "S&P500 compound actual from rounded appendix returns",
                46.8,
                compound_actual,
                "not_exact_at_display_precision_hidden_precision_could_explain",
                "Displayed rows compound to 46.87% (normally 46.9%), so raw values are required.",
            ),
            consistency_row(
                WORK_2026,
                "S&P500 compound EW/null from rounded appendix returns",
                21.6,
                compound_null,
                "not_exact_at_display_precision_hidden_precision_could_explain",
                "Displayed null means compound to 21.74%; raw EW returns are absent.",
            ),
            consistency_row(
                WORK_2026,
                "S&P500 compound excess from rounded appendix returns",
                25.2,
                compound_actual - compound_null,
                "passes_display_precision",
                "The rounded appendix paths imply about 25.13 percentage points.",
            ),
        ]
    )

    score_t_500 = 0.489 * math.sqrt(19)
    score_t_100 = 0.080 * math.sqrt(35)
    one_500 = float(student_t.sf(abs(score_t_500), 18))
    two_500 = 2 * one_500
    one_100 = float(student_t.sf(abs(score_t_100), 34))
    two_100 = 2 * one_100
    rows.extend(
        [
            consistency_row(
                WORK_2026,
                "S&P500 score t = ICIR * sqrt(T)",
                2.13,
                score_t_500,
                "passes_display_precision",
                "The t-statistic identity holds.",
            ),
            consistency_row(
                WORK_2026,
                "S&P500 reported p_t sidedness",
                0.024,
                one_500,
                "matches_one_sided_absolute_tail",
                f"The conventional two-sided p is {two_500:.6f}, not 0.024.",
            ),
            consistency_row(
                WORK_2026,
                "S&P100 score t = ICIR * sqrt(T)",
                0.48,
                score_t_100,
                "passes_display_precision",
                "The t-statistic identity holds.",
            ),
            consistency_row(
                WORK_2026,
                "S&P100 reported p_t sidedness",
                0.319,
                one_100,
                "matches_one_sided_absolute_tail",
                f"The conventional two-sided p is {two_100:.6f}, not 0.319.",
            ),
            consistency_row(
                WORK_2026,
                "Paper's |ICIR| threshold versus reported p_t convention",
                "absolute_two_sided_threshold_language",
                "one_sided_absolute_tail_p_values",
                "internally_inconsistent_test_sidedness",
                "The method uses |ICIR|/test-against-zero language but table p_t values are half two-sided p-values.",
            ),
            consistency_row(
                WORK_2026,
                "Beta-regression monthly alpha simple annualization",
                14.2,
                1.18 * 12,
                "passes_display_precision",
                "The reported annualized alpha is simple 12x annualization.",
            ),
            consistency_row(
                WORK_2026,
                "Up-market conditional excess",
                0.82,
                5.22 - 4.39,
                "hidden_precision_needed_for_last_basis_point",
                "Displayed values imply 0.83, not 0.82; raw returns could explain the difference.",
            ),
            consistency_row(
                WORK_2026,
                "Down-market conditional excess",
                1.31,
                -2.00 - (-3.32),
                "hidden_precision_needed_for_last_basis_point",
                "Displayed values imply 1.32, not 1.31; raw returns could explain the difference.",
            ),
        ]
    )
    return rows


def mechanism_conformance() -> list[dict[str, Any]]:
    checks = [
        (WORK_2025, "agent topology", "five named agents", "paper_specified", True),
        (WORK_2025, "primary LLM", "GPT-4o named; snapshot and parameters absent", "partial", False),
        (WORK_2025, "RAG evaluator LLM", "GPT-4o-mini named; snapshot absent", "partial", False),
        (WORK_2025, "prompts", "described only; no verbatim templates", "missing", False),
        (WORK_2025, "price input", "historical price data; vendor/field/snapshot absent", "missing", False),
        (WORK_2025, "news input", "news described; source list and snapshot absent", "missing", False),
        (WORK_2025, "SEC input", "EDGAR API named; exact filing set and timestamps absent", "partial", False),
        (WORK_2025, "earnings transcripts", "RapidAPI aggregation named; frozen corpus absent", "partial", False),
        (WORK_2025, "macro reports", "institutions named; complete corpus and hashes absent", "partial", False),
        (WORK_2025, "universe", "S&P100/S&P500 named; constituents and membership vintage absent", "partial", False),
        (WORK_2025, "signal timing", "monthly stated; decision/execution timestamps and lag absent", "partial", False),
        (
            WORK_2025,
            "portfolio rule",
            "equal/cap weighting stated; cap timing and cash handling absent",
            "partial",
            False,
        ),
        (WORK_2025, "transaction costs", "10 bps/trade stated; trade/turnover application absent", "partial", False),
        (WORK_2025, "backtester", "VectorBTPro named; version/config proprietary and absent", "partial", False),
        (WORK_2025, "metrics", "names supplied; formulas/frequency/risk-free conventions absent", "partial", False),
        (
            WORK_2025,
            "factor regressions",
            "models named; factor source/frequency/regression details absent",
            "partial",
            False,
        ),
        (WORK_2025, "seeds/repeated LLM trials", "not reported", "missing", False),
        (WORK_2025, "native result outputs", "no signal, return, trade, or NAV files", "missing", False),
        (WORK_2026, "agent topology", "four specialists plus synthesis stated", "paper_specified", True),
        (WORK_2026, "generation LLM", "underlying model names, snapshots, parameters absent", "missing", False),
        (WORK_2026, "prompts", "no specialist or synthesis prompt templates", "missing", False),
        (WORK_2026, "live-generation proof", "asserted; no immutable timestamped outputs/requests", "missing", False),
        (WORK_2026, "cohort design", "467x19 and 94x35 stated; tickers and formation vintage absent", "partial", False),
        (WORK_2026, "observation cadence", "first Friday monthly stated; exact timestamps absent", "partial", True),
        (
            WORK_2026,
            "forward return",
            "one-month buy-and-hold stated; price field/dividends/lag absent",
            "partial",
            False,
        ),
        (WORK_2026, "embedding model", "text-embedding-3-small, D=1536 named", "partial", True),
        (WORK_2026, "embedding requests", "texts, request dates, responses and hashes absent", "missing", False),
        (WORK_2026, "NNLS objective", "objective, normalization, and fallback specified", "paper_specified", True),
        (WORK_2026, "NNLS implementation", "solver/library/tolerance/version absent", "missing", False),
        (
            WORK_2026,
            "Monte Carlo sampling",
            "K=10000, same-size, without replacement specified",
            "paper_specified",
            True,
        ),
        (WORK_2026, "Monte Carlo seed", "fixed seed asserted but value not disclosed", "missing", False),
        (WORK_2026, "Monte Carlo p-value", "one-tailed empirical formula specified", "paper_specified", True),
        (WORK_2026, "IC scope", "buy+strong-buy scope and formulas specified", "paper_specified", True),
        (
            WORK_2026,
            "IC p-value sidedness",
            "reported values conflict with test-against-zero language",
            "conflicting",
            False,
        ),
        (WORK_2026, "transaction costs", "no turnover/cost/slippage treatment", "missing", False),
        (WORK_2026, "raw result panel", "agent text, labels, embeddings, returns all absent", "missing", False),
        (
            WORK_2026,
            "benchmark construction",
            "EW universe specified; ticker files and prices absent",
            "partial",
            False,
        ),
        (WORK_2026, "native execution path", "no attributable operational code or environment", "missing", False),
    ]
    rows = [
        {
            "canonical_work_id": work,
            "dimension": dimension,
            "primary_source_evidence": evidence,
            "status": status,
            "paper_specification_reconstructable": spec_credit,
            "native_mechanism_credit": False,
            "paper_result_credit": False,
        }
        for work, dimension, evidence, status, spec_credit in checks
    ]
    if len(rows) != 38 or any(row["native_mechanism_credit"] for row in rows):
        raise RuntimeError("MarketSenseAI mechanism boundary changed")
    return rows


def specification_gaps() -> list[dict[str, Any]]:
    gaps = {
        WORK_2025: [
            "verbatim prompts and parsing contracts",
            "exact GPT-4o/GPT-4o-mini snapshots and inference parameters",
            "point-in-time S&P constituent lists",
            "frozen price/news/filing/transcript/macro inputs",
            "release-time and decision-time timestamps with execution lag",
            "buy/hold/sell generation records",
            "portfolio holdings, trades, fills, cash, dividends, and NAV paths",
            "transaction-cost implementation and turnover definition",
            "metric and annualization formulas",
            "factor dataset, regression frequency, and alpha horizon",
            "Ragas query/reference set and evaluator configuration",
            "software versions, seeds, and repeated-run protocol",
        ],
        WORK_2026: [
            "specialist/synthesis model identities and verbatim prompts",
            "immutable live request/response timestamps",
            "467- and 94-stock cohort ticker lists and formation vintage",
            "agent summaries, synthesis theses, and ordinal labels",
            "embedding requests and 1536-dimensional response arrays",
            "one-month return prices, fields, dividends, and exact horizons",
            "Monte Carlo random seed and simulation outputs",
            "NNLS solver implementation, version, and tolerances",
            "date-level IC arrays and test-sidedness declaration",
            "portfolio holdings, turnover, transaction costs, and NAV paths",
            "author-generated raw figure arrays",
            "operational source, environment lock, and runnable evaluator",
        ],
    }
    return [
        {
            "canonical_work_id": work,
            "missing_requirement": gap,
            "blocking_effect": "blocks_native_paper_result_reproduction",
            "publicly_resolved": False,
        }
        for work, work_gaps in gaps.items()
        for gap in work_gaps
    ]


def discovery_evidence() -> list[dict[str, Any]]:
    checked = "2026-08-12T00:40:00Z"
    entries = [
        (
            "arxiv_2502_v1_v2_source",
            "https://arxiv.org/abs/2502.00415",
            "18-file v1 and 14-file v2 manuscript bundles; no operational code/data",
        ),
        (
            "arxiv_2604_v1_source",
            "https://arxiv.org/abs/2604.17327",
            "13-file manuscript bundle with ten rendered empirical figures; no raw panel/code",
        ),
        (
            "first_author_github_repositories",
            "https://github.com/giorgosfatouros",
            "16 public repositories returned; none named or described as MarketSenseAI",
        ),
        (
            "first_author_github_exact_code_queries",
            "https://api.github.com/search/code",
            "MarketSenseAI, 2502.00415, and 2604.17327 each returned zero in the author account",
        ),
        (
            "company_github_organization",
            "https://github.com/aTensorTechnologies",
            "zero public repositories returned; exact code queries returned zero",
        ),
        (
            "global_github_repository_query",
            "https://api.github.com/search/repositories?q=MarketSenseAI",
            "37 index/unaffiliated/name-collision matches; none attributable to the authors/company",
        ),
        (
            "global_github_arxiv_id_query",
            "https://api.github.com/search/code?q=2604.17327",
            "secondary indexes and derivative research notes only; no author implementation",
        ),
        (
            "official_product_site_bundle",
            "https://marketsense-ai.com",
            "commercial web app/API references; no public code, dataset, or result download",
        ),
        (
            "official_company_research_bundle",
            "https://alpha-tensor.ai/research",
            "research page links the two arXiv papers but exposes no source/data artifact",
        ),
        (
            "awesome_applied_agents_entry",
            "https://github.com/Sasha-Cui/Awesome-Applied-Agents-for-Investment",
            "the parenthetical source link is the arXiv record, not a code repository",
        ),
    ]
    return [
        {
            "search": name,
            "url_or_endpoint": url,
            "checked_at_utc": checked,
            "bounded_result": result,
            "attributable_operational_release_found": False,
            "negative_inference_boundary": (
                "no_public_attributable_release_found_in_checked_surfaces; "
                "not_proof_that_private_deleted_or_unindexed_artifacts_never_existed"
            ),
        }
        for name, url, result in entries
    ]


def material_non_table_claims() -> list[dict[str, Any]]:
    claims = [
        (WORK_2025, "signal changes after filings/calls", "approximately 5%"),
        (WORK_2025, "unexplained returns after factors", "12--15%"),
        (WORK_2025, "S&P500 equal-weight relative outperformance", "102%"),
        (WORK_2025, "S&P100 MS-Cap Sortino improvement", "16%"),
        (WORK_2025, "S&P500 MS-Cap Sortino improvement", "33.8%"),
        (WORK_2026, "pooled Financials strong-buy share", "21.8% vs 15.1%"),
        (WORK_2026, "pooled Information Technology share", "17.0% vs 14.2%"),
        (WORK_2026, "pooled Energy share", "1.8% vs 4.4%"),
        (WORK_2026, "pooled Materials share", "2.2% vs 5.1%"),
        (WORK_2026, "pooled Consumer Staples share", "4.7% vs 7.4%"),
        (WORK_2026, "early Financials share", "24.8% vs 15.1%"),
        (WORK_2026, "later Information Technology share", "21.7%"),
        (WORK_2026, "strong-buy vs buy mean return S&P500", "1.47% vs 1.35%"),
        (WORK_2026, "strong-buy vs buy mean return S&P100", "1.67% vs 1.39%"),
        (WORK_2026, "minus-10-percent left-tail exceedance", "7.5% vs 10.2%"),
        (WORK_2026, "beta regression", "beta 0.865; alpha 1.18%/month"),
        (WORK_2026, "beta regression inference", "t 1.45; p 0.17; R2 0.60"),
        (WORK_2026, "simple annualized beta-regression alpha", "14.2%"),
        (WORK_2026, "individual strong-buy beta", "1.06 vs universe 1.00"),
        (WORK_2026, "up-market conditional returns", "5.22% vs 4.39%; excess 0.82%"),
        (WORK_2026, "down-market conditional returns", "-2.00% vs -3.32%; excess 1.31%"),
        (WORK_2026, "down-market conditional test", "8 observations; p 0.28"),
        (WORK_2026, "information compression S&P500", "approximately 9x"),
        (WORK_2026, "information compression S&P100", "approximately 6x"),
    ]
    return [
        {
            "canonical_work_id": work,
            "claim": claim,
            "published_value": value,
            "claim_scope": "material_non_table_or_figure_annotation_not_exhaustive_repeated_prose",
            "native_reproduced_value": "",
            "status": "unavailable_no_native_result_inputs_or_pipeline",
            "paper_result_credit": False,
        }
        for work, claim, value in claims
    ]


def readme_text(manifest: Mapping[str, Any]) -> str:
    return f"""# MarketSenseAI paper-lineage replication audit

## Honest outcome

Neither paper is faithfully reproduced. The audit rebuilds the manuscripts and
checks arithmetic recoverable from printed values, but **0/{manifest["paper_2025_result_table_units"]}**
MarketSenseAI 2.0 result-table units and **0/{manifest["paper_2026_result_table_units"]}**
2026 validation result-table units are regenerated by the native system.

The distinction is deliberate:

- all three primary TeX bundles rebuild deterministically to the published page
  counts and pass full-page contact-sheet visual QA;
- the latest 2025 paper contains {manifest["paper_2025_empirical_figure_assets"]} empirical
  raster assets and the 2026 source contains {manifest["paper_2026_empirical_figure_assets"]}
  rendered empirical PDF assets;
- those are author-rendered paper outputs, not raw arrays or executions, and get
  no result-reproduction credit;
- no attributable MarketSenseAI implementation, exact input snapshot, prompts,
  live signal records, holdings/trades/NAV path, or result arrays were found.

## Paper-by-paper assessment

### MarketSenseAI 2.0 (arXiv:2502.00415)

Both v1 (25 pages) and v2 (10 pages) were inspected. The repository's local PDF
is byte-identical to arXiv v2. The revisions restyle/compress the same reported
experiment rather than provide independent result lineage. The exhaustive latest
result-table ledger contains {manifest["paper_2025_result_table_units"]} measurements:
21 sentiment statistics, 45 retrieval scores, 56 portfolio metrics, 24
attribution statistics, and 11 factor-model values. Zero reproduce natively.

The printed arithmetic supports the 16%, 33.8%, and 102% headline comparisons at
display precision. One prose statement does not: it says both S&P500 portfolios
have beta 1.24--1.27, while the corresponding table reports 0.92 and 1.27; 1.24
belongs to the S&P100 MS-Cap row. The factor-regression dependent series and alpha
horizon are also not specified tightly enough for exact reconstruction.

### Signal or Noise (arXiv:2604.17327v1)

The exhaustive table ledger has {manifest["paper_2026_numeric_table_units"]} numeric
units: {manifest["paper_2026_configuration_units"]} cohort configurations and
{manifest["paper_2026_result_table_units"]} descriptive/result measurements. The
cohort products, signal totals, selection averages, win rates, appendix means,
and ICIR-to-t identities mostly reconcile. The rounded monthly appendix path does
not exactly recover the printed compound figures; raw precision could explain the
small gaps, but the raw return panel is absent.

The date-level `p_t` values match one-sided absolute-tail probabilities. That is
not the conventional two-sided interpretation of a one-sample test "against zero"
or the paper's absolute-value threshold language. For the primary score result,
ICIR 0.489 and T=19 imply t=2.1315, one-sided p=0.02354 and two-sided p=0.04708.
The significance classification remains below 0.05 either way, but the reported
p=0.024 is not a two-sided p-value.

The risk table has a separate direct conflict. Its caption defines `DeltaUpDn`
as each long signal's UpDn ratio minus Hold. The displayed ratios imply 1.07 -
0.79 = 0.28 for Strong buy and 0.99 - 0.79 = 0.20 for Buy, while the table prints
0.17 and 0.09. Hidden precision cannot plausibly bridge either 0.11 gap.

The paper's strongest safeguard—live generation—is asserted, not independently
demonstrated by immutable dated requests/outputs. The fixed random seed is also
asserted but not disclosed. The cohort tickers/formation vintage, return inputs,
agent texts, embeddings, labels, solver details, and transaction-cost treatment
are missing. These omissions block replay of every central claim.

## Discovery boundary

The first author's public GitHub account, the company organization, exact-title
and arXiv-ID code searches, the official product/company sites, the arXiv bundles,
and the applied-agents index were checked. No attributable operational release
was found. This bounded result does **not** prove that private, deleted, or
unindexed artifacts never existed.

## Evidence files

- `paper_version_summary.csv`: pinned paper/source revisions.
- `paper_source_inventory.csv`: every file in all three source bundles.
- `published_2025_table_result_ledger.csv`: exhaustive latest 2025 result-table units.
- `published_2026_table_result_ledger.csv`: exhaustive 2026 numeric table units.
- `empirical_figure_inventory.csv`: every author-rendered empirical source asset.
- `paper_internal_consistency_checks.csv`: recoverable arithmetic and conflicts.
- `paper_mechanism_conformance.csv`: disclosed versus missing pipeline details.
- `paper_specification_gaps.csv`: exact blockers to native replay.
- `material_non_table_claims.csv`: material non-table/figure claims (not repeated-prose exhaustive).
- `public_source_discovery.csv`: bounded public-source search record.
- `manuscript_rebuilds.json`: deterministic build and visual-comparison evidence.

Local thematic proxies remain diagnostic adaptations only and receive no
MarketSenseAI mechanism or result credit.
"""


def build_audit(audit_root: Path, output_dir: Path) -> dict[str, Any]:
    versions = version_summary(audit_root)
    source_rows = source_inventory(audit_root)
    figures = figure_inventory(source_rows)
    rebuilds = rebuild_summary(audit_root)
    table_2025 = market_2025_table_rows()
    table_2026 = validation_2026_table_rows()
    checks = internal_consistency_checks()
    mechanisms = mechanism_conformance()
    gaps = specification_gaps()
    discovery = discovery_evidence()
    claims = material_non_table_claims()

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "paper_version_summary.csv", versions)
    write_csv(output_dir / "paper_source_inventory.csv", source_rows)
    write_csv(output_dir / "published_2025_table_result_ledger.csv", table_2025)
    write_csv(output_dir / "published_2026_table_result_ledger.csv", table_2026)
    write_csv(output_dir / "empirical_figure_inventory.csv", figures)
    write_csv(output_dir / "paper_internal_consistency_checks.csv", checks)
    write_csv(output_dir / "paper_mechanism_conformance.csv", mechanisms)
    write_csv(output_dir / "paper_specification_gaps.csv", gaps)
    write_csv(output_dir / "public_source_discovery.csv", discovery)
    write_csv(output_dir / "material_non_table_claims.csv", claims)
    write_json(output_dir / "manuscript_rebuilds.json", rebuilds)

    figure_counts = Counter(row["paper_version"] for row in figures)
    table_2026_counts = Counter(row["cell_kind"] for row in table_2026)
    issue_count = sum(
        row["status"]
        in {
            "fails_against_displayed_attribution_table",
            "fails_published_delta_definition",
            "internally_inconsistent_test_sidedness",
        }
        for row in checks
    )
    manifest: dict[str, Any] = {
        "audit": "MarketSenseAI two-paper primary-source replication audit",
        "system_id": SYSTEM_ID,
        "overall_status": "not_reproduced_manuscripts_only_no_operational_release",
        "full_papers_reproduced": 0,
        "papers_audited": 2,
        "paper_versions_pinned": 3,
        "paper_2025_result_table_units": len(table_2025),
        "paper_2025_result_table_units_faithfully_regenerated": 0,
        "paper_2025_empirical_figure_assets": figure_counts["2502.00415v2"],
        "paper_2025_empirical_figure_assets_faithfully_regenerated": 0,
        "paper_2026_numeric_table_units": len(table_2026),
        "paper_2026_configuration_units": table_2026_counts["configuration"],
        "paper_2026_result_table_units": table_2026_counts["direct_result"],
        "paper_2026_result_table_units_faithfully_regenerated": 0,
        "paper_2026_empirical_figure_assets": figure_counts["2604.17327v1"],
        "paper_2026_empirical_figure_assets_faithfully_regenerated": 0,
        "author_rendered_empirical_assets_verified": len(figures),
        "raw_empirical_figure_arrays_shipped": 0,
        "manuscripts_rebuilt_deterministically": len(rebuilds),
        "manuscript_rebuilds_receive_result_credit": False,
        "operational_system_source_found": False,
        "native_signal_or_portfolio_outputs_found": False,
        "paper_mechanism_dimensions": len(mechanisms),
        "native_mechanism_dimensions_reproduced": 0,
        "material_non_table_claims_inventoried": len(claims),
        "material_internal_conflicts": issue_count,
        "precise_blocker": (
            "no attributable operational code, input/output panel, prompts, immutable live logs, "
            "portfolio path, or raw result arrays"
        ),
        "negative_inference_boundary": (
            "no public attributable release found in bounded checked surfaces; not proof that "
            "private, deleted, or unindexed artifacts never existed"
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
        help="Return nonzero while full paper reproduction is unavailable.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(args.audit_root, args.output_dir)
    print(json.dumps(manifest, indent=2))
    return 1 if args.strict and manifest["full_papers_reproduced"] != 2 else 0


if __name__ == "__main__":
    raise SystemExit(main())
