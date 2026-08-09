#!/usr/bin/env python3
"""Build a page-anchored audit packet for the 13 closest source mappings."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


SOURCE_META = {
    2: {
        "source_url": "https://arxiv.org/abs/2507.17211",
        "source_locator": "PDF pp. 8 and 19-21; Section 5.1 and Appendix D",
        "original_task_and_metric": (
            "Evolutionary factor search with sparse top-m portfolios on Fama-French "
            "and US50/HSI45/CSI300 datasets; evaluated with native portfolio metrics."
        ),
    },
    5: {
        "source_url": "https://arxiv.org/abs/2605.15412",
        "source_locator": (
            "Paper pp. 2-5; pinned repository 4eb0e78842138ada5334349585b114ad923564e8, "
            "examples/seed_candidates.yaml, seed_0001"
        ),
        "original_task_and_metric": (
            "Executable factor-expression generation and reinforcement fine-tuning; "
            "the released seed is evaluated inside the paper's factor-discovery tasks."
        ),
    },
    7: {
        "source_url": "https://arxiv.org/abs/2505.11122",
        "source_locator": "PDF p. 22, Table 7; factor examples in the appendix",
        "original_task_and_metric": (
            "LLM-guided Monte Carlo tree search for symbolic factors on China A-shares; "
            "evaluated with factor and portfolio metrics in the native market."
        ),
    },
    10: {
        "source_url": "https://aclanthology.org/2024.findings-acl.233/",
        "source_locator": "PDF pp. 3 and 8; Sections 2.2-2.3 and 5",
        "original_task_and_metric": (
            "Neural-symbolic factor mining on S&P 500 stocks; evaluated with RankIC, "
            "RankICIR, and a native investment simulation."
        ),
    },
    42: {
        "source_url": "https://arxiv.org/abs/2510.01664",
        "source_locator": "PDF pp. 2-3 and 6-7; Section 2.2 and Appendix A, Figures 3-7",
        "original_task_and_metric": (
            "Prompt-guided investor-persona agents form Nasdaq-100 portfolios on a "
            "quarterly schedule; evaluated with CAGR and Sharpe against market benchmarks."
        ),
    },
}


CANDIDATE_META = {
    "efs_momentum_low_vol_breakout": (
        "Momentum, stability/low-volatility, and breakout motifs appear in documented evolved examples.",
        "The exact multi-horizon JKP sum, characteristic substitutions, monthly deciles, and value weights are researcher supplied.",
    ),
    "efs_short_reversal_low_noise": (
        "Mean-reversion and noise-filtering motifs appear in documented regime-specific examples.",
        "The exact reversal, volatility, and safety score, its signs, monthly deciles, and value weights are researcher supplied.",
    ),
    "efs_sparse_top5_momentum_low_vol": (
        "The source uses sparse top-five equal-weight selection and documents momentum/low-volatility motifs.",
        "The JKP score, U.S. top-1,000 universe, monthly timing, and excess-return implementation are researcher supplied.",
    ),
    "repo_quantevolver_return_sharpe_proxy": (
        "The pinned repository seed divides a 60-bar mean return by its 60-bar return standard deviation.",
        "The evaluator changes the horizons to 12-month return and 252-day volatility, then adds monthly U.S. deciles and value weights; it is not the literal released expression.",
    ),
    "alpha_jungle_price_volume_momentum": (
        "Documented examples combine price changes, volume/liquidity quantities, and symbolic operators.",
        "The four-term JKP score, its exact signs and horizons, monthly U.S. universe, deciles, and weights are researcher supplied.",
    ),
    "alpha_jungle_volatility_compression_trend": (
        "Documented examples include moving-average price changes and volatility operators.",
        "The trend-after-compression interpretation and exact JKP score, horizons, deciles, and weights are researcher supplied.",
    ),
    "fama_value_momentum_interpretable": (
        "The source supports interpretable factor mining and discusses momentum/trend principles.",
        "Book-to-market, profitability, and size terms, equal score weights, monthly deciles, and the common task are researcher supplied.",
    ),
    "guru_altman_distress_avoidance": (
        "The published Altman prompt emphasizes bankruptcy risk, profitability, leverage, liquidity, and operating efficiency.",
        "JKP characteristic proxies, score weights, risk terms, monthly long-short deciles, and value weights are researcher supplied.",
    ),
    "guru_buffett_quality_compounder": (
        "The published Buffett prompt emphasizes durable quality, profitability, growth, cash generation, and leverage.",
        "JKP characteristic proxies, equal score weights, monthly long-short deciles, and value weights are researcher supplied.",
    ),
    "guru_equal_weight_style_ensemble": (
        "The source evaluates several named investor personas in one framework.",
        "A score-level equal-weight ensemble, all JKP proxies, monthly long-short deciles, and value weights are researcher supplied.",
    ),
    "guru_graham_deep_value_defensive": (
        "The published Graham prompt emphasizes valuation, financial strength, earnings stability, and conservative selection.",
        "JKP characteristic proxies, score weights, monthly long-short deciles, and value weights are researcher supplied.",
    ),
    "guru_greenblatt_magic_formula": (
        "The published Greenblatt prompt emphasizes earnings yield and return on capital/business quality.",
        "The four JKP terms, equal score weights, monthly long-short deciles, and value weights are researcher supplied.",
    ),
    "guru_piotroski_fscore_proxy": (
        "The published Piotroski prompt uses profitability, cash flow, leverage/liquidity, dilution, and efficiency signals.",
        "Continuous JKP ranks replace the discrete accounting score; monthly long-short deciles and value weights are researcher supplied.",
    ),
}


FIELDS = [
    "source_index",
    "source_name",
    "candidate_id",
    "source_url",
    "source_locator",
    "original_task_and_metric",
    "source_supported_content",
    "common_task_implementation",
    "researcher_supplied_changes",
    "exact_original_claim_match",
    "mapping_frozen_before_returns",
    "independent_outcome_blind_review",
    "audit_status",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    source = root / "paper_runs/submission_evidence/mapping_audit/mapping_audit.csv"
    output = root / "paper_runs/submission_evidence/mapping_audit/source_anchor_review_packet.csv"

    with source.open(newline="", encoding="utf-8-sig") as stream:
        mappings = [
            row for row in csv.DictReader(stream)
            if row["good_faith_empirical_role"] == "source_grounded_component_test"
        ]
    if len(mappings) != 13:
        raise ValueError(f"expected 13 source-anchored mappings, found {len(mappings)}")
    if set(CANDIDATE_META) != {row["candidate_id"] for row in mappings}:
        raise ValueError("candidate metadata does not exactly cover the 13 source-anchored mappings")

    packet = []
    for row in sorted(mappings, key=lambda value: (int(value["source_index"]), value["candidate_id"])):
        source_index = int(row["source_index"])
        supported, supplied = CANDIDATE_META[row["candidate_id"]]
        packet.append({
            "source_index": source_index,
            "source_name": row["source_name"],
            "candidate_id": row["candidate_id"],
            **SOURCE_META[source_index],
            "source_supported_content": supported,
            "common_task_implementation": f"{row['proxy_formula']} | {row['strategy']}",
            "researcher_supplied_changes": supplied,
            "exact_original_claim_match": "no",
            "mapping_frozen_before_returns": row["mapping_frozen_before_us_returns_inspected"],
            "independent_outcome_blind_review": row["independent_second_coder"],
            "audit_status": "post_hoc_source_anchor_audit; independent review pending",
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(packet)

    lines = [
        "# Source-anchor review packet",
        "",
        "This packet lets an independent reviewer adjudicate the 13 closest source mappings",
        "without seeing portfolio outcomes. It is a post-hoc source audit, not evidence that",
        "the original mappings were outcome-blind or independently coded. Every row is a",
        "partial component mapping; none matches the source's original task, portfolio, metric,",
        "and the paper's monthly U.S. six-factor estimand simultaneously.",
        "",
        "The review question is deliberately narrow: does the cited locator support the content",
        "listed in `source_supported_content`, and are all changes in",
        "`researcher_supplied_changes` complete? Reviewers should record corrections as versioned",
        "alternatives before inspecting returns. `independent review pending` is not an approval.",
        "",
        "| Source | Candidate | Locator | Exact common-task claim | Review status |",
        "|---|---|---|---|---|",
    ]
    for row in packet:
        lines.append(
            f"| [{row['source_name']}]({row['source_url']}) | `{row['candidate_id']}` | "
            f"{row['source_locator']} | {row['exact_original_claim_match']} | "
            f"{row['audit_status']} |"
        )
    (root / "docs/source_anchor_review_packet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print({"rows": len(packet), "sources": len({row['source_index'] for row in packet}),
           "output": str(output)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
