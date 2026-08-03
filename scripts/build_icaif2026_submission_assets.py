#!/usr/bin/env python3
"""Build U.S.-first ICAIF submission macros and figures from locked outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


WHITE = "#FFFFFF"
INK = "#17212B"
NAVY = "#16324F"
BLUE = "#276FBF"
TEAL = "#1B7F79"
GOLD = "#9A6700"
RULE = "#C7D2DE"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: pd.Series, q: float) -> float:
    ordered = np.sort(values.to_numpy(dtype=float))
    position = (len(ordered) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    if lo == hi:
        return float(ordered[lo])
    return float(ordered[lo] * (hi - position) + ordered[hi] * (position - lo))


def fmt_pct(value: float) -> str:
    return f"{100.0 * value:.2f}\\%"


def command(name: str, value: str | int) -> str:
    return f"\\newcommand{{\\{name}}}{{{value}}}"


def verify_run(run_dir: Path) -> dict:
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    for filename in (
        "candidate_primary_results.csv",
        "candidate_cost_alpha_results.csv",
        "hac_lag_sensitivity.csv",
        "turnover_summary.csv",
    ):
        actual = sha256(run_dir / filename)
        expected = manifest["output_sha256"][filename]
        if actual != expected:
            raise RuntimeError(f"hash mismatch for {run_dir.name}/{filename}")
    return manifest


def verify_broad_run(run_dir: Path) -> dict:
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    for filename, expected in manifest["output_sha256"].items():
        actual = sha256(run_dir / filename)
        if actual != expected:
            raise RuntimeError(f"hash mismatch for {run_dir.name}/{filename}")
    if manifest.get("analysis_label") != "post_hoc_exploratory_broad_jkp_crossfit":
        raise RuntimeError("broad-JKP run is not labeled post-hoc exploratory")
    if float(manifest.get("market_alignment_correlation", 0.0)) < 0.99:
        raise RuntimeError("broad-JKP factor panel failed month-alignment validation")
    return manifest


def style_axis(ax) -> None:
    ax.set_facecolor(WHITE)
    ax.tick_params(colors=INK, labelcolor=INK)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)
    ax.title.set_color(NAVY)
    for spine in ax.spines.values():
        spine.set_color(RULE)


def save_figure(fig, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.patch.set_facecolor(WHITE)
    fig.savefig(destination, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)


def candidate_label(row: pd.Series | dict[str, Any]) -> str:
    candidate_id = str(row.get("candidate_id", "unnamed")).strip()
    proxy_code = "P-" + hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:6].upper()
    paper_ref = str(row.get("paper_ref", "")).strip()
    return f"{proxy_code} {paper_ref}" if paper_ref and paper_ref != "nan" else proxy_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    run_dir = root / "paper_runs/submission_evidence/usa_retrospective_corrected"
    international_dir = root / "paper_runs/submission_evidence/g7_ex_us_corrected"
    broad_dir = root / "paper_runs/submission_evidence/usa_broad_jkp_crossfit"
    paper_dir = root / "docs/paper"
    manifest = verify_run(run_dir)
    verify_run(international_dir)
    broad_manifest = verify_broad_run(broad_dir)

    primary = pd.read_csv(run_dir / "candidate_primary_results.csv")
    costs = pd.read_csv(run_dir / "candidate_cost_alpha_results.csv")
    turnover = pd.read_csv(run_dir / "turnover_summary.csv")
    hac = pd.read_csv(run_dir / "hac_lag_sensitivity.csv")
    ok = primary.loc[primary["status"] == "ok"].copy()
    if len(primary) != 62 or len(ok) != 62:
        raise RuntimeError("U.S. primary family is not 62/62 executable")

    alpha = ok["alpha_annualized"].astype(float)
    cost_ok = costs.loc[costs["status"] == "ok"].copy()
    wide = cost_ok.pivot(index="candidate_id", columns="cost_bps_one_way", values="alpha_annualized")
    schedule = [0, 5, 10, 25, 50]
    wide = wide.reindex(columns=schedule)
    if wide.shape != (62, 5) or wide.isna().any().any():
        raise RuntimeError("U.S. cost panel is not a complete 62 by 5 family")
    turnover_values = turnover.loc[turnover["valid_months"] > 0, "median_monthly_traded_notional"].astype(float)
    broad = pd.read_csv(broad_dir / "broad_jkp_crossfit_results.csv")
    if len(broad) != 62 or int(broad["n_benchmark_factors"].iloc[0]) != 133:
        raise RuntimeError("broad-JKP result is not a complete 62 by 133-factor audit")
    broad_best = broad.sort_values("alpha_annualized", ascending=False).iloc[0]

    lag_counts = []
    for lag in (0, 3, 6, 12):
        group = hac.loc[hac["fixed_hac_lags"] == lag]
        nominal = int(((group["alpha_annualized"] > 0) & (group["p_value_two_sided"] <= 0.05)).sum())
        p = group["p_value_two_sided"].where(group["alpha_annualized"] > 0, 1.0).sort_values().to_numpy()
        rejected = 0
        for index, value in enumerate(p):
            if value <= 0.05 / (len(p) - index):
                rejected += 1
            else:
                break
        lag_counts.append((lag, nominal, rejected))

    macros = [
        "% Generated by scripts/build_icaif2026_submission_assets.py; do not edit by hand.",
        "% U.S.-primary values are computed from hash-verified frozen outputs.",
        command("USRegressionMonthCount", int(ok["n_months"].iloc[0])),
        command("USRegressionStartMonth", "August 2001"),
        command("USRegressionEndMonth", "December 2024"),
        command("USMedianAlphaPct", fmt_pct(float(alpha.median()))),
        command("USAlphaIQRPct", f"[{fmt_pct(percentile(alpha, 0.25))}, {fmt_pct(percentile(alpha, 0.75))}]"),
        command("USPositiveAlphaCount", int((alpha > 0).sum())),
        command("USNominalCount", int(((ok["alpha_annualized"] > 0) & (ok["p_value_two_sided"] <= 0.05)).sum())),
        command("USHolmPositiveCount", int(((ok["alpha_annualized"] > 0) & (ok["holm_p_value"] <= 0.05)).sum())),
        command("USMaxTPositiveCount", int(((ok["alpha_annualized"] > 0) & (ok["max_abs_t_p_value"] <= 0.05)).sum())),
        command("USEconomicConfirmedCount", int((ok["simultaneous_ci_low_annualized"] >= 0.02).sum())),
        command("USRealityCheckP", f"{manifest['bootstrap']['white_reality_check_style_p_value']:.4f}"),
        command("USBestAlphaPct", fmt_pct(float(alpha.max()))),
        command("USBestSimultaneousLowerPct", fmt_pct(float(ok.loc[ok["alpha_annualized"].idxmax(), "simultaneous_ci_low_annualized"]))),
        command("USMedianTurnover", f"{float(turnover_values.median()):.2f}"),
        command("USTurnoverIQR", f"{percentile(turnover_values, 0.25):.2f}--{percentile(turnover_values, 0.75):.2f}"),
        command("USMedianCostDragPct", fmt_pct(float((wide[0] - wide[10]).median()))),
        command("USCrossSectionMedianCostShiftPct", fmt_pct(float(wide[0].median() - wide[10].median()))),
        command("USPositiveAtZero", int((wide[0] > 0).sum())),
        command("USPositiveAtFive", int((wide[5] > 0).sum())),
        command("USPositiveAtTen", int((wide[10] > 0).sum())),
        command("USPositiveAtTwentyFive", int((wide[25] > 0).sum())),
        command("USPositiveAtFifty", int((wide[50] > 0).sum())),
        command("USMedianGrossAlphaPct", fmt_pct(float(wide[0].median()))),
        command("USHACLagNominalCounts", "/".join(str(row[1]) for row in lag_counts)),
        command("USHACLagHolmCounts", "/".join(str(row[2]) for row in lag_counts)),
        command("BroadEvaluationMonthCount", int(broad["n_evaluation_months"].iloc[0])),
        command("BroadEvaluationStartMonth", "August 2011"),
        command("BroadEvaluationEndMonth", "January 2022"),
        command("BroadPositiveAlphaCount", int((broad["alpha_annualized"] > 0).sum())),
        command("BroadNominalPositiveCount", int(((broad["alpha_annualized"] > 0) & (broad["p_value_two_sided"] <= 0.05)).sum())),
        command("BroadHolmPositiveCount", int(((broad["alpha_annualized"] > 0) & (broad["holm_p_value"] <= 0.05)).sum())),
        command("BroadMaxTPositiveCount", int(((broad["alpha_annualized"] > 0) & (broad["max_abs_t_p_value"] <= 0.05)).sum())),
        command("BroadEconomicConfirmedCount", int((broad["simultaneous_ci_low_annualized"] >= 0.02).sum())),
        command("BroadBestAlphaPct", fmt_pct(float(broad_best["alpha_annualized"]))),
        command("BroadBestRawP", f"{float(broad_best['p_value_two_sided']):.4f}"),
        command("BroadBestHolmP", f"{float(broad_best['holm_p_value']):.3f}"),
        command("BroadBestMaxTP", f"{float(broad_best['max_abs_t_p_value']):.3f}"),
        command("BroadBestSimultaneousLowerPct", fmt_pct(float(broad_best["simultaneous_ci_low_annualized"]))),
        command("BroadMarketAlignmentCorrelation", f"{float(broad_manifest['market_alignment_correlation']):.3f}"),
    ]
    paper_dir.mkdir(parents=True, exist_ok=True)
    result_path = paper_dir / "icaif2026_results.tex"
    with tempfile.NamedTemporaryFile("w", dir=paper_dir, delete=False, encoding="utf-8") as handle:
        handle.write("\n".join(macros) + "\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, result_path)

    plt.rcParams.update({
        "font.size": 10,
        "axes.labelcolor": INK,
        "axes.edgecolor": RULE,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "figure.facecolor": WHITE,
        "savefig.facecolor": WHITE,
    })
    fig, ax = plt.subplots(figsize=(11.2, 4.8), facecolor=WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.axis("off")

    def box(x, y, width, height, title, detail, color):
        from matplotlib.patches import FancyBboxPatch
        patch = FancyBboxPatch(
            (x, y), width, height,
            boxstyle="round,pad=0.04,rounding_size=0.08",
            linewidth=1.4, edgecolor=color, facecolor=WHITE,
        )
        ax.add_patch(patch)
        ax.text(x + width / 2, y + height * 0.64, title, ha="center", va="center", color=color, fontsize=11, fontweight="bold")
        ax.text(x + width / 2, y + height * 0.30, detail, ha="center", va="center", color=INK, fontsize=8.5)

    box(0.2, 1.75, 2.05, 1.5, "Reported alpha claims", "103 lineages; 67 methods\nin the primary census", NAVY)
    box(3.0, 3.15, 2.15, 1.3, "Direct-code route", "14 public implementations\nattempted", BLUE)
    box(5.9, 3.15, 2.15, 1.3, "Code-backed test", "1 valid U.S. JKP path", BLUE)
    box(8.8, 3.15, 2.75, 1.3, "Direct result", "0 paths beat FF5+Mom", TEAL)
    box(3.0, 0.55, 2.15, 1.3, "Reconstruction route", "51 of 55 source ideas\ntranslated", GOLD)
    box(5.9, 0.55, 2.15, 1.3, "Common U.S. test", "62 frozen proxy portfolios", GOLD)
    box(8.8, 0.55, 2.75, 1.3, "Robust result", "1 six-factor FWE survivor;\n0 broad-JKP FWE survivors", TEAL)
    arrow = dict(arrowstyle="-|>", color="#53677A", lw=1.5, mutation_scale=12)
    ax.annotate("", xy=(3.0, 3.8), xytext=(2.25, 2.7), arrowprops=arrow)
    ax.annotate("", xy=(3.0, 1.2), xytext=(2.25, 2.3), arrowprops=arrow)
    ax.annotate("", xy=(5.9, 3.8), xytext=(5.15, 3.8), arrowprops=arrow)
    ax.annotate("", xy=(8.8, 3.8), xytext=(8.05, 3.8), arrowprops=arrow)
    ax.annotate("", xy=(5.9, 1.2), xytext=(5.15, 1.2), arrowprops=arrow)
    ax.annotate("", xy=(8.8, 1.2), xytext=(8.05, 1.2), arrowprops=arrow)
    ax.text(6.0, 4.78, "Two routes from a reported alpha claim to testable evidence", ha="center", va="top", fontsize=13, fontweight="bold", color=NAVY)
    save_figure(fig, paper_dir / "figures/claim_to_test_pipeline.pdf")

    fig, ax = plt.subplots(figsize=(9.6, 5.6), facecolor=WHITE)
    style_axis(ax)
    x = np.asarray(schedule, dtype=float)
    for _, row in wide.iterrows():
        ax.plot(x, 100.0 * row.to_numpy(dtype=float), color=BLUE, alpha=0.10, linewidth=0.75, zorder=1)
    quantiles = wide.quantile([0.25, 0.5, 0.75], axis=0)
    q1 = 100.0 * quantiles.loc[0.25].to_numpy(dtype=float)
    median = 100.0 * quantiles.loc[0.5].to_numpy(dtype=float)
    q3 = 100.0 * quantiles.loc[0.75].to_numpy(dtype=float)
    ax.fill_between(x, q1, q3, color=TEAL, alpha=0.20, label="Interquartile range", zorder=2)
    ax.plot(x, median, color=NAVY, linewidth=2.4, marker="o", label="Median", zorder=3)
    ax.axvline(10, color=GOLD, linewidth=1.5, linestyle="--", label="Primary 10 bp", zorder=2)
    ax.axhline(0, color=INK, linewidth=0.9, zorder=1)
    ax.set_xticks(x)
    ax.set_xlabel("One-way transaction cost (basis points)")
    ax.set_ylabel("Annualized U.S. factor alpha (%)")
    ax.set_title("Primary U.S. benchmark: alpha sensitivity to trading costs", pad=12)
    ax.grid(alpha=0.42)
    ax.set_axisbelow(True)
    legend = ax.legend(loc="best", facecolor=WHITE, edgecolor=RULE, framealpha=1.0)
    for label in legend.get_texts():
        label.set_color(INK)
    save_figure(fig, paper_dir / "figures/usa_cost_sensitivity.pdf")

    international = pd.read_csv(international_dir / "candidate_primary_results.csv")
    international_ok = (
        international.loc[international["status"] == "ok"]
        .assign(_alpha=lambda frame: pd.to_numeric(frame["alpha_annualized"]))
        .sort_values("_alpha", ascending=False)
        .reset_index(drop=True)
    )
    international_failed = international.loc[international["status"] != "ok"]
    if len(international) != 62 or len(international_ok) != 27 or len(international_failed) != 35:
        raise RuntimeError("international family is not 62 planned / 27 executable / 35 failed")

    display = {
        "paper_factormad_debate_interpretable": ("FactorMAD", "value + profitability + safety + momentum - leverage - volatility"),
        "guru_graham_deep_value_defensive": ("GuruAgents--Graham", "value + cash + profitability - leverage - volatility - beta"),
        "code_ai_trader_value_quality": ("AI-Trader", "value + quality + profitability + cash - leverage - volatility"),
        "paper_alpha_gpt_interactive_formula": ("Alpha-GPT", "value + momentum + profitability + gross profits - leverage"),
        "guru_greenblatt_magic_formula": ("GuruAgents--Greenblatt", "earnings yield + profitability + gross profits + value"),
        "fama_value_momentum_interpretable": ("FAMA", "value + momentum + profitability - size"),
        "paper_factorminer_memory_diverse_library": ("FactorMiner", "momentum + value + profitability + safety + turnover - risk"),
        "alphaagents_risk_averse_quality_lowrisk": ("AlphaAgents", "quality + profitability + value - volatility - beta - leverage"),
        "paper_factorengine_program_knowledge": ("FactorEngine", "value + profitability + cash flow - accruals - leverage - investment"),
        "repo_alphaprobe_dag_diverse_factor_blend": ("AlphaPROBE", "momentum + value + profitability + safety + turnover - risk"),
        "repo_deepfund_prudent_fund_manager": ("DeepFund", "long-only quality + profitability + cash + momentum - risk"),
    }
    survivors = international_ok.loc[
        (international_ok["alpha_annualized"] > 0) & (international_ok["holm_p_value"] <= 0.05)
    ].copy()
    if len(survivors) != 11 or set(survivors["candidate_id"]) != set(display):
        raise RuntimeError("international Holm-survivor registry changed")
    table_path = paper_dir / "tables/international_holm_survivors.tex"
    table_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for _, row in survivors.sort_values("alpha_annualized", ascending=False).iterrows():
        label, mechanism = display[row["candidate_id"]]
        p_value = float(row["holm_p_value"])
        p_text = "$<.001$" if p_value < 0.001 else f"{p_value:.3f}"
        lines.append(
            f"{label} & {mechanism} & {100*float(row['alpha_annualized']):.2f} & {p_text} & {100*float(row['simultaneous_ci_low_annualized']):.2f}"
        )
    with tempfile.NamedTemporaryFile("w", dir=table_path.parent, delete=False, encoding="utf-8") as handle:
        row_separator = " " + r"\\" + "\n"
        handle.write(row_separator.join(lines) + "\n")
        temp_table = Path(handle.name)
    os.replace(temp_table, table_path)
    y = np.arange(len(international_ok))
    fig, ax = plt.subplots(figsize=(8.0, max(7.4, 0.31 * len(international_ok))), facecolor=WHITE)
    style_axis(ax)
    for index, row in international_ok.iterrows():
        alpha_value = 100.0 * float(row["alpha_annualized"])
        low = 100.0 * float(row["ci_low_annualized"])
        high = 100.0 * float(row["ci_high_annualized"])
        positive = alpha_value > 0
        ax.errorbar(
            alpha_value,
            index,
            xerr=np.array([[alpha_value - low], [high - alpha_value]]),
            fmt="o",
            markersize=4.6,
            markerfacecolor=TEAL if positive else WHITE,
            markeredgecolor=TEAL if positive else BLUE,
            ecolor="#53677A",
            elinewidth=1.0,
            capsize=1.8,
            zorder=3,
        )
    ax.axvline(0.0, color=INK, linewidth=1.0, zorder=1)
    ax.axvline(2.0, color=GOLD, linewidth=1.1, linestyle="--", zorder=1)
    ax.set_yticks(y, [candidate_label(row) for _, row in international_ok.iterrows()], fontsize=7.2)
    ax.invert_yaxis()
    for label in ax.get_yticklabels():
        label.set_color(INK)
    finite_ci = pd.concat(
        [international_ok["ci_low_annualized"], international_ok["ci_high_annualized"]]
    ).astype(float)
    x_low = min(-1.0, 100.0 * float(finite_ci.min()))
    x_high = max(3.0, 100.0 * float(finite_ci.max()))
    margin = 0.08 * (x_high - x_low)
    ax.set_xlim(x_low - margin, x_high + margin)
    ax.set_xlabel("Annualized factor alpha (%)")
    ax.set_title("International extension: 27 executable paths", pad=12)
    ax.grid(axis="x", alpha=0.45)
    ax.set_axisbelow(True)
    ax.text(
        0.01,
        1.005,
        "Dashed gold line: 2 pp threshold; 35 additional family members have no return estimate",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        color=INK,
    )
    save_figure(fig, paper_dir / "figures/g7_alpha_forest.pdf")

    fixed = pd.read_csv(
        root / "paper_runs/submission_evidence/fixed_calendar_diagnostics/fixed_calendar_country_loo.csv"
    )
    paired = fixed.loc[fixed["diagnostic"] == "g7_usa_common_calendar", ["candidate_id", "alpha_annualized"]]
    paired = paired.rename(columns={"alpha_annualized": "alpha_international"}).merge(
        ok[["candidate_id", "alpha_annualized", "paper_ref"]].rename(
            columns={"alpha_annualized": "alpha_usa"}
        ),
        on="candidate_id",
        how="inner",
        validate="one_to_one",
    )
    if len(paired) != 27:
        raise RuntimeError("transport panel does not contain 27 jointly estimable paths")
    x_values = 100.0 * paired["alpha_usa"].to_numpy(dtype=float)
    y_values = 100.0 * paired["alpha_international"].to_numpy(dtype=float)
    correlation = float(pd.Series(x_values).corr(pd.Series(y_values), method="spearman"))
    fig, ax = plt.subplots(figsize=(7.5, 6.7), facecolor=WHITE)
    style_axis(ax)
    ax.scatter(
        x_values,
        y_values,
        s=42,
        c=TEAL,
        edgecolors=WHITE,
        linewidths=0.7,
        alpha=0.90,
        zorder=3,
    )
    low = min(float(x_values.min()), float(y_values.min()))
    high = max(float(x_values.max()), float(y_values.max()))
    margin = 0.08 * max(1.0, high - low)
    low, high = low - margin, high + margin
    ax.plot([low, high], [low, high], color="#53677A", linewidth=1.2, linestyle="--", zorder=1)
    ax.axhline(0, color=INK, linewidth=0.8, alpha=0.7)
    ax.axvline(0, color=INK, linewidth=0.8, alpha=0.7)
    disagreement = np.abs(y_values - x_values)
    for index in np.argsort(disagreement)[-min(8, len(paired)):]:
        ax.annotate(
            candidate_label(paired.iloc[index]),
            (x_values[index], y_values[index]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=7,
            color=INK,
        )
    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_xlabel("Primary U.S. annualized alpha (%)")
    ax.set_ylabel("International-extension annualized alpha (%)")
    ax.set_title(f"Transport among 27 jointly estimable proxies (Spearman {correlation:.3f})", pad=12)
    ax.grid(alpha=0.42)
    ax.set_axisbelow(True)
    save_figure(fig, paper_dir / "figures/usa_g7_transfer.pdf")

    print(f"wrote {result_path}")
    print(f"wrote {paper_dir / 'figures/usa_cost_sensitivity.pdf'}")
    print(f"wrote {paper_dir / 'figures/claim_to_test_pipeline.pdf'}")
    print(f"wrote {paper_dir / 'figures/g7_alpha_forest.pdf'}")
    print(f"wrote {paper_dir / 'figures/usa_g7_transfer.pdf'}")
    print(f"wrote {table_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
