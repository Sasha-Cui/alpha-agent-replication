#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Generate the manuscript, visual report and compact audit presentations together."""

from pathlib import Path
import sys
import json
import re
import html
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import argparse
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from alpha_evolve.openrouter_budget import sha256, atomic_json

PUBLIC = ROOT / "paper_runs/publication_upgrade_v1"
PRIVATE = ROOT / "artifacts/publication_upgrade_v1"
INK = "#172033"
BLUE = "#145da0"
ORANGE = "#b45309"
GRAY = "#64748b"
BG = "#ffffff"
PALE = "#eef3f9"
ORDER = ["EFS", "GuruAgents", "QuantaAlpha", "FinMem", "TradingAgents", "FinAgent"]
PRIMARY = {
    "EFS": ("llm", "grammar_seed_mean"),
    "GuruAgents": ("tool-routing__ensemble", "archived-final__ensemble"),
    "QuantaAlpha": ("released_170", "alpha158_20"),
    "FinMem": ("native", "semantic_only"),
    "TradingAgents": ("native", "no_risk_debate"),
    "FinAgent": ("native_causal", "no_retrieval"),
}
LABELS = {
    "EFS": "EFS",
    "GuruAgents": "GuruAgents",
    "QuantaAlpha": "QuantaAlpha library",
    "FinMem": "FinMem",
    "TradingAgents": "TradingAgents",
    "FinAgent": "FinAgent",
}
REFERENCES = [
    (
        "EFS",
        "EFS: Evolutionary Factor Searching for Sparse Portfolio Optimization Using Large Language Models, v1.",
        "https://arxiv.org/abs/2507.17211v1",
    ),
    (
        "FinMem",
        "FinMem: A Performance-Enhanced LLM Trading Agent with Layered Memory and Character Design.",
        "https://arxiv.org/abs/2311.13743",
    ),
    (
        "FinAgent",
        "A Multimodal Foundation Agent for Financial Trading: Tool-Augmented, Diversified, and Generalist.",
        "https://arxiv.org/abs/2402.18485",
    ),
    (
        "TradingAgents",
        "TradingAgents: Multi-Agents LLM Financial Trading Framework, v7.",
        "https://arxiv.org/abs/2412.20138v7",
    ),
    (
        "GuruAgents",
        "GuruAgents: Emulating Wise Investors with Prompt-Guided LLM Agents.",
        "https://arxiv.org/abs/2510.01664",
    ),
    ("QuantaAlpha", "QuantaAlpha, v3.", "https://arxiv.org/abs/2602.07085v3"),
    ("FINSABER", "FINSABER benchmark and released alternative data.", "https://arxiv.org/html/2505.07078v6"),
    (
        "Stationary bootstrap",
        "Politis and Romano (1994), The Stationary Bootstrap.",
        "https://doi.org/10.1080/01621459.1994.10476870",
    ),
    (
        "HAC",
        "Newey and West (1987), A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix.",
        "https://www.jstor.org/stable/1913610",
    ),
    (
        "Grouped t",
        "Ibragimov and Muller (2010), t-Statistic Based Correlation and Heterogeneity Robust Inference.",
        "https://www.princeton.edu/~umueller/tstat.pdf",
    ),
    (
        "Equivalence",
        "Schuirmann (1987), A comparison of the two one-sided tests procedure and the power approach for assessing equivalence.",
        "https://pubmed.ncbi.nlm.nih.gov/3450848/",
    ),
]


def fmt(x, digits=2, percent=False):
    if x is None:
        return "-"
    if isinstance(x, (float, np.floating)) and not np.isfinite(x):
        return "-"
    if isinstance(x, (int, np.integer)):
        return str(x)
    if isinstance(x, (float, np.floating)):
        return f"{x * 100 if percent else x:.{digits}f}"
    return str(x)


def mdtable(headers, rows):
    def esc(s):
        return str(s).replace("|", "/").replace("\n", " ")

    return "\n".join(
        ["| " + " | ".join(map(esc, headers)) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        + ["| " + " | ".join(map(esc, row)) + " |" for row in rows]
    )


def style_axes(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=INK, labelsize=10)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)
    ax.title.set_color(INK)
    ax.grid(color="#dce3ec", linewidth=0.6, alpha=0.8)
    for spine in ax.spines.values():
        spine.set_color("#8b99ad")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    analysis = PUBLIC / ("analysis_preview" if args.preview else "analysis")
    status = json.loads((analysis / "status.json").read_text())
    if not args.preview and status["status"] != "complete":
        raise ValueError("A final report requires all completed cases")
    suffix = "_preview" if args.preview else ""
    figdir = PUBLIC / ("visual_figures" + suffix)
    tabledir = PUBLIC / ("visual_tables" + suffix)
    figdir.mkdir(exist_ok=True)
    tabledir.mkdir(exist_ok=True)
    effects = pd.read_csv(analysis / "paired_effects.csv")
    performance = pd.read_csv(analysis / "economic_performance.csv")
    stress = pd.read_csv(analysis / "controlled_adaptations.csv")
    daily = pd.read_parquet(
        PRIVATE / ("analysis_preview_returns.parquet" if args.preview else "analysis_returns.parquet")
    )
    daily["date"] = pd.to_datetime(daily.date)
    primary = (
        effects[effects.role == "primary"]
        .set_index("case")
        .reindex([c for c in ORDER if c in status["complete_cases"]])
    )
    blocks = []
    figures = []
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "savefig.facecolor": BG,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "axes.edgecolor": "#8b99ad",
            "legend.facecolor": BG,
            "legend.edgecolor": "#dce3ec",
            "legend.labelcolor": INK,
            "font.family": "DejaVu Sans",
            "font.size": 10,
        }
    )

    def paragraph(text):
        blocks.append({"type": "p", "text": text})

    def heading(text):
        blocks.append({"type": "h", "text": text})

    def equation(text):
        blocks.append({"type": "math", "text": text})

    def table(headers, rows, audit=None):
        blocks.append({"type": "table", "headers": headers, "rows": rows, "audit": audit})

    def figure(name, fig, title, caption, headers, rows, audit):
        fig.savefig(figdir / (name + ".png"), dpi=220, facecolor=BG, bbox_inches="tight")
        plt.close(fig)
        pd.DataFrame(rows, columns=headers).to_csv(tabledir / (name + ".csv"), index=False)
        blocks.append(
            {
                "type": "figure",
                "path": str((figdir / (name + ".png")).relative_to(PUBLIC)),
                "title": title,
                "caption": caption,
            }
        )
        table(headers, rows, audit)
        figures.append(
            {
                "name": name,
                "image": str((figdir / (name + ".png")).relative_to(PUBLIC)),
                "presentation_table": str((tabledir / (name + ".csv")).relative_to(PUBLIC)),
                "audit": audit,
            }
        )

    analysis_rel = analysis.name
    title = "Economic Fidelity Before Alpha"
    subtitle = "Source-based financial LLM mechanisms, matched controls, calibrated inference, and a prospective research pilot"
    blocks.append({"type": "title", "text": title, "subtitle": subtitle})
    banner = (
        "Working draft: " + str(len(status["complete_cases"])) + " of 6 case studies complete."
        if args.preview
        else "Research draft: all six case studies executed; independent human review and future pilot outcomes remain pending."
    )
    blocks.append({"type": "banner", "text": banner})
    paragraph(
        "This study separates three questions: whether a released mechanism can be executed, whether it improves a matched economic outcome, and whether the observations identify incremental alpha relative to a specified benchmark. The historical experiments use modern model endpoints and disclosed data/execution adapters. They do not reproduce the original papers in full."
    )
    heading("Abstract")
    paragraph(
        "We extend an existing 69-paper availability audit and 62 common U.S. transfer paths with six source-specific case studies: EFS, FinMem, FinAgent, TradingAgents, GuruAgents, and QuantaAlpha. The implementations restore native decision cadence and substantive mechanisms, use real model calls where applicable, and distinguish source scores from self-financing portfolio returns. Controls isolate search, memory retrieval, risk discussion, tool routing, and released-factor inclusion. We also examine trading costs, execution timing, trading cadence and information latency. A calibration exercise rejects standard short-sample bootstrap intervals as overly optimistic and motivates conservative grouped-estimator bounds, validated on a separate simulation seed. Short native histories are not treated as identified unrestricted JKP132 regressions. Finally, an immutable local forecast record begins a prospective development pilot. The resulting evidence is conditional on the disclosed implementations and realized model trajectories; insignificant results are not interpreted as proof of no economically meaningful alpha."
    )
    positive_count = int(primary.familywise_positive_primary.eq(True).sum())
    unresolved_count = int((primary.verdict == "inconclusive_at_2pp_margin").sum())
    paragraph(
        f"Across {len(primary)} completed primary comparisons, the number meeting the declared Holm-adjusted positive-effect criterion is {positive_count}; the number unresolved against the 2 percentage-point annual economic margin is {unresolved_count}. EFS illustrates an accounting-sensitive result: the LLM path trails its initial library before fees but leads it after 10-basis-point trading costs. FinMem's positive directional log score coexists with a negative cash-adapter return. These observations support an audit of economic definitions and identification limits, rather than a universal absence-of-alpha conclusion."
    )
    heading("1. Research question and evidence boundaries")
    paragraph(
        "The previous study evaluated 62 common JKP transfer paths: 17 carried evaluations and 45 explicitly researcher-authored reconstructions, with seven structural exclusions from the 69-paper census. Its manifest records zero full native systems reproduced end to end. Those artifacts remain frozen. A transfer result cannot by itself adjudicate a paper whose original information, cadence, action semantics or portfolio was replaced."
    )
    paragraph(
        "The new cohort is selected for recoverable mechanisms and useful contrasts, not as a random sample of all financial-agent papers. EFS is a paper-guided numerical reimplementation. FinMem, FinAgent and TradingAgents execute released core code with explicit adapters. GuruAgents reuses 190 actual source-prompt/tool replays. QuantaAlpha reexecutes a released factor library, predictor and portfolio; it does not rerun the original LLM search. FINSABER provides an alternative dated input source and an important neighboring benchmark, so the contribution here is the source-to-accounting audit and controlled economic attribution rather than a generic claim that LLM trading underperforms."
    )
    table(
        ["Case", "Executed object", "Primary contrast"],
        [
            [
                c,
                {
                    "EFS": "Paper-guided search",
                    "FinMem": "Released actor and memory",
                    "FinAgent": "Released multimodal pipeline",
                    "TradingAgents": "Released role graph",
                    "GuruAgents": "Actual source-prompt replays",
                    "QuantaAlpha": "Released factors + native predictor",
                }[c],
                {
                    "EFS": "LLM vs 10 grammar seeds",
                    "FinMem": "Layered vs semantic retrieval",
                    "FinAgent": "Full vs no retrieval",
                    "TradingAgents": "Full vs no risk discussion",
                    "GuruAgents": "Tool routing vs one final call",
                    "QuantaAlpha": "170 vs 20 factors",
                }[c],
            ]
            for c in ORDER
        ],
        "source_review/packet_manifest.json",
    )
    heading("2. Economic contracts")
    paragraph(
        "For source actors without a complete investable account, the research adapter maps BUY to a fully invested long position, SELL to cash, and HOLD to retaining the target. The primary signal uses completed information and executes at the next close. FinAgent instead retains the released whole-share buy/sell methods, while repairing the account clock: the prior order fills and NAV is marked at the current close before the actor observes its account. Date-only news and filings become available on the strictly next trading session. These are explicit assumptions, not recovered original execution logs."
    )
    table(
        ["Case", "Primary trading cost", "Execution rule"],
        [
            ["EFS", "10 bps per traded notional", "Next close"],
            ["FinMem", "10 bps research account", "Next close; source score separate"],
            ["FinAgent", "10 bps; whole shares", "Prior order fills before current decision"],
            ["TradingAgents", "10 bps research account", "Next close"],
            ["GuruAgents", "1 bp source convention", "First close after quarter end"],
            ["QuantaAlpha", "5 bps buys / 15 bps sells", "Native Qlib open execution"],
        ],
        "source_review/packet_manifest.json",
    )
    paragraph(
        "Cash earns zero interest in the source-style accounts. The reported costs cover the stated security-trading fees; market impact, taxes and unavailable vendor or financing costs are not manufactured. The exact code and input assumptions determine each comparison."
    )
    equation(r"G_t=C_{t-1}+\sum_i D_{i,t-1}(1+r_{i,t})")
    equation(r"N_t=G_t-c\sum_i\left|N_t w_{i,t}-D_{i,t-1}(1+r_{i,t})\right|")
    paragraph(
        "Here G is pretrade marked capital, N is post-fee capital, D is security value, C is cash and c is cost per traded notional. Cash itself is not charged as a second security trade. The implementation solves the self-financing fee equation and permits uninvested cash. Between scheduled rebalances, positions drift. Reported trade notional is the sum of absolute security trades divided by pretrade NAV; it is not half-L1 turnover."
    )
    paragraph(
        "Native conventions remain visible. FinMem's published signed-log score, its cumulative one-share feedback state, and the researcher's cash/stock account are different objects. QuantaAlpha's native annualized return is benchmark-relative after costs, not standalone CAGR. GuruAgents' released notebook explicitly renormalizes percentage-weight totals to 100, so that source convention is preserved. A 90-day information-lag stress is reported separately and does not certify point-in-time fundamentals or eliminate restatements."
    )
    equation(r"S_{\rm FinMem}=\sum_t a_t\log(P_{t+1}/P_t)")
    paragraph(
        "The source score above is not cumulative portfolio return. HOLD contributes zero to this score, while a held portfolio can still earn or lose money. Source metric reproduction and economic portfolio reproduction are therefore reported separately."
    )
    if "FinMem" in status["complete_cases"]:
        scores = json.loads((analysis / "finmem_source_scores.json").read_text())
        finmem_rows = []
        for arm, label in [("native", "Layered retrieval"), ("semantic_only", "Semantic retrieval")]:
            row = performance[(performance["case"] == "FinMem") & (performance.arm == arm)].iloc[0]
            finmem_rows.append(
                [
                    label,
                    f"{100 * scores[arm]['signed_log_return_sum']:+.2f}",
                    f"{100 * (row.ending_wealth - 1):+.2f}",
                    f"{100 * row.max_drawdown:.2f}",
                ]
            )
        table(
            ["FinMem path", "Directional log score x100", "Cash-adapter total return (%)", "Cash-adapter drawdown (%)"],
            finmem_rows,
            f"{analysis_rel}/economic_performance.csv",
        )
        paragraph(
            "The FinMem comparison above changes the measured economic object. A positive directional score and a negative long-only cash-account return can coexist because SELL and HOLD have different meanings in the score and the funded account. The cash mapping is an explicit research adapter, not a recovered original financing policy. Neither its loss nor the source score alone adjudicates every possible implementation of the paper."
        )
        guard_path = PRIVATE / "finmem_offline_replay/guardrail_validation_events.json"
        if guard_path.exists():
            guard = json.loads(guard_path.read_text())
            paragraph(
                f"Read-only instrumentation of the native guardrail records {guard['training_validation_failures']} training validation failures and {guard['test_validation_failures']} test validation failures. Source fallback behavior remains part of the executed system; these events are not relabelled as successful language-model reasoning. Both evaluation arms share the same trained state."
            )
    heading("3. Matched design and statistical estimands")
    paragraph(
        "EFS controls use the same 290 search dates and 870 returned-code proposal slots, evaluator, trailing information, pruning, portfolio size and execution clock. All ten grammar seeds are retained; they are randomization replicates over one shared market history, not ten independent histories. The grammar is narrower than unrestricted model-generated Python. Other primary comparisons preserve their stated external information and account constraints while removing the relevant mechanism. The GuruAgents ensemble averages all five source roles as a research aggregation; every role is also reported separately."
    )
    paragraph(
        "The economic margin is fixed at 2 percentage points of annualized arithmetic return advantage. CAGR and drawdown are descriptive portfolio metrics. The uncertainty interval targets an annualized paired mean, or an intercept conditional on an explicitly specified factor model; it is not a CAGR interval. All factor coefficients are refitted when the estimator is resampled or estimated by block."
    )
    equation(
        r"\widehat{\Delta}_{\rm ann}=f\,\frac{1}{q}\sum_{b=1}^{q}\widehat{\Delta}_b,\qquad s=\frac{\operatorname{sd}(\widehat{\Delta}_1,\ldots,\widehat{\Delta}_q)}{\sqrt{q}}"
    )
    equation(r"\mathrm{CI}_{\rm primary}=f\left[\overline{\Delta}\ \pm\ t_{q-1,0.995}\,s\right]")
    paragraph(
        "Primary bounds use contiguous-group estimator t inference with nominal 99% intervals. Four groups are used for paired means; a low-dimensional factor regression uses three when four would leave inadequate block-level residual degrees of freedom. The estimator requires approximately independent, approximately normal block estimates. Simulation checks support its behavior only on the tested designs, not every financial process. Primary zero-effect p-values receive Holm family adjustment; bounds remain explicitly casewise. Identical or degenerate observed paths do not establish population equivalence. Time-series uncertainty is conditional on these realized model trajectories and does not estimate variation across model generations."
    )
    heading("4. Paired economic effects")
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.0), gridspec_kw={"hspace": 0.7})
    for ax, group, label in zip(
        axes, [ORDER[:3], ORDER[3:]], ["Multi-year windows: monthly inference", "Short native windows: daily inference"]
    ):
        names = [c for c in group if c in primary.index]
        style_axes(ax)
        ax.axvspan(-2, 2, color="#e5edf8", zorder=0)
        ax.axvline(0, color=GRAY, linewidth=0.9)
        ax.axvline(2, color=ORANGE, linestyle="--", linewidth=1)
        if not names:
            ax.text(0.5, 0.5, "Runs pending", transform=ax.transAxes, ha="center", color=GRAY)
        for i, case in enumerate(names):
            row = primary.loc[case]
            effect = 100 * row.annualized_arithmetic_effect
            lo = row.primary_ci_low
            hi = row.primary_ci_high
            if pd.notna(lo) and pd.notna(hi):
                ax.errorbar(
                    effect,
                    i,
                    xerr=[[effect - 100 * lo], [100 * hi - effect]],
                    fmt="o",
                    color=BLUE,
                    ecolor=BLUE,
                    capsize=4,
                    linewidth=2,
                )
            else:
                ax.plot(effect, i, "o", markerfacecolor=BG, markeredgecolor=GRAY)
                ax.annotate(
                    "No population bound",
                    (effect, i),
                    xytext=(8, 0),
                    textcoords="offset points",
                    color=GRAY,
                    fontsize=8,
                )
        ax.set_yticks(range(len(names)), [LABELS[c] for c in names])
        ax.invert_yaxis()
        ax.set_title(label, loc="left", fontsize=11)
        ax.set_xlabel("Annualized paired mean difference (percentage points)")
        ax.set_ylim(len(names) - 0.5, -0.5)
    rows = []
    for case, row in primary.iterrows():
        ci = (
            f"[{100 * row.primary_ci_low:.1f}, {100 * row.primary_ci_high:.1f}]"
            if pd.notna(row.primary_ci_low)
            else "Not estimable"
        )
        rows.append(
            [
                case,
                str(int(row.observations)) + (" months" if row.frequency == 12 else " days"),
                f"{100 * row.annualized_arithmetic_effect:+.2f}",
                ci,
            ]
        )
    figure(
        "paired_effects",
        fig,
        "Figure 1. Effects relative to matched controls",
        "Panels use different horizontal scales. Shading marks the +/-2 percentage-point margin. Intervals are nominal 99% grouped-t bounds, conditional on the stated study and model-trajectory assumptions.",
        ["Case", "Paired observations", "Effect (pp/year)", "Primary interval"],
        rows,
        f"{analysis_rel}/paired_effects.csv",
    )
    paragraph(
        "A confidence interval overlapping the economic margin leaves the claim unresolved. A negative point estimate or a conventional nonsignificant test is insufficient to establish absence of useful alpha. Conversely, an apparent gain in raw portfolio return can reflect market exposure, turnover, cost or the account adapter. The matched contrasts and factor-model boundaries limit the interpretation."
    )
    table(
        ["Case", "Approx. 80% power effect (pp/year)", "Holm-adjusted zero-effect p"],
        [
            [
                case,
                "Not estimable"
                if row.degenerate_sampling_variation
                else fmt(row.mde80_t_normal_approx_annualized, 1, percent=True),
                fmt(row.holm_p_primary_family, 3),
            ]
            for case, row in primary.iterrows()
        ],
        f"{analysis_rel}/paired_effects.csv",
    )
    paragraph(
        "The power column is a planning approximation: the estimated grouped standard error multiplied by the nominal 99% t critical value plus the normal 80% power quantile. It is casewise, does not incorporate Holm adjustment or model-generation variability, and is not a guaranteed detection threshold. Large values show why these windows cannot settle a 2 percentage-point economic question. A degenerate realized difference is labelled not estimable rather than assigned zero population uncertainty."
    )
    for group, name, title_text in [
        (ORDER[:3], "paths_long", "Figure 2. Portfolio paths over multi-year windows"),
        (ORDER[3:], "paths_short", "Figure 3. Portfolio paths over short native windows"),
    ]:
        available = [c for c in group if c in status["complete_cases"]]
        if not available:
            continue
        fig, axes = plt.subplots(len(available), 1, figsize=(7.2, 2.15 * len(available) + 0.4), squeeze=False)
        rows = []
        for ax, case in zip(axes[:, 0], available):
            style_axes(ax)
            left, right = PRIMARY[case]
            for arm, color in [(left, BLUE), (right, ORANGE)]:
                x = daily[(daily["case"] == case) & (daily.arm == arm)].sort_values("date")
                ax.plot(x.date, 100 * (1 + x["return"]).cumprod(), color=color, linewidth=1.4)
            reference = "equal_weight" if case == "EFS" else "buy_hold_matched_clock"
            x = daily[(daily["case"] == case) & (daily.arm == reference)].sort_values("date")
            if len(x):
                ax.plot(x.date, 100 * (1 + x["return"]).cumprod(), color=GRAY, linewidth=1, linestyle="--")
            ax.set_title(LABELS[case], loc="left", fontsize=11)
            ax.set_ylabel("Wealth index")
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=6))
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
            a = performance[(performance["case"] == case) & (performance.arm == left)].iloc[0]
            b = performance[(performance["case"] == case) & (performance.arm == right)].iloc[0]
            rows.append(
                [
                    case,
                    fmt(a.ending_wealth - 1, percent=True),
                    fmt(b.ending_wealth - 1, percent=True),
                    fmt(a.max_drawdown, percent=True),
                ]
            )
        fig.legend(
            [
                plt.Line2D([], [], color=BLUE),
                plt.Line2D([], [], color=ORANGE),
                plt.Line2D([], [], color=GRAY, linestyle="--"),
            ],
            ["Tested path", "Matched control", "Simple reference, where shown"],
            loc="upper center",
            ncol=3,
            fontsize=10.5,
            frameon=False,
        )
        fig.tight_layout(rect=[0, 0, 1, 0.94])
        figure(
            name,
            fig,
            title_text,
            "Initial capital is normalized to 100. Native windows and source fee conventions differ across cases; the relevant comparisons are within panels. Tables show cumulative changes in wealth; annualized metrics remain in the audit.",
            ["Case", "Tested total return (%)", "Control total return (%)", "Tested max DD (%)"],
            rows,
            f"{analysis_rel}/economic_performance.csv",
        )
    if "FinAgent" in status["complete_cases"]:
        fa = performance[performance["case"] == "FinAgent"].set_index("arm")
        effect = primary.loc["FinAgent"]
        paragraph(
            f"Over June–December 2023, the FinAgent whole-share account returns {100 * (fa.loc['native_causal', 'ending_wealth'] - 1):+.2f}%, versus {100 * (fa.loc['no_retrieval', 'ending_wealth'] - 1):+.2f}% without retrieval and {100 * (fa.loc['buy_hold_matched_clock', 'ending_wealth'] - 1):+.2f}% for the matched-clock buy-and-hold reference. The annualized paired mean difference is {100 * effect.annualized_arithmetic_effect:+.2f} percentage points, with primary bounds [{100 * effect.primary_ci_low:.1f}, {100 * effect.primary_ci_high:.1f}]. Retrieval does not improve this realized trajectory; the wide bounds and one TSLA/model trajectory leave its general economic effect unresolved."
        )
    heading("5. Costs and controlled adaptations")
    e = stress[(stress["case"] == "EFS")]
    fig, (ax, heat) = plt.subplots(2, 1, figsize=(7.2, 6.3), gridspec_kw={"height_ratios": [1.2, 1], "hspace": 0.6})
    style_axes(ax)
    for arm, color, label in [
        ("llm", BLUE, "LLM"),
        ("initial", ORANGE, "Initial library"),
        ("equal_weight", GRAY, "Equal weight"),
    ]:
        x = e[(e.arm == arm) & (e.adapter == "daily")].sort_values("cost_bps")
        ax.plot(x.cost_bps, 100 * x.cagr, "o-", color=color, label=label)
    ax.set_xlabel("Cost per traded notional (basis points)")
    ax.set_ylabel("CAGR (%)")
    ax.legend(ncol=3, fontsize=9)
    ax.set_title("Daily trading cost sensitivity", loc="left", fontsize=11)
    order = ["llm", "initial", "equal_weight"]
    cadences = ["daily", "weekly", "monthly"]
    matrix = np.array(
        [
            [
                float(e[(e.arm == arm) & (e.adapter == cadence) & (e.cost_bps == 10)].cagr.iloc[0]) * 100
                for cadence in cadences
            ]
            for arm in order
        ]
    )
    norm = matplotlib.colors.Normalize(vmin=matrix.min() - 1, vmax=matrix.max() + 1)
    cmap = plt.get_cmap("Blues")
    heat.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")
    heat.set_xticks(range(3), cadences)
    heat.set_yticks(range(3), ["LLM", "Initial library", "Equal weight"])
    heat.tick_params(colors=INK)
    heat.set_title("Net CAGR at 10 bps with holdings allowed to drift between trades", loc="left", fontsize=10)
    for i in range(3):
        for j in range(3):
            rgb = cmap(norm(matrix[i, j]))[:3]
            linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
            luminance = sum(a * b for a, b in zip(linear, [0.2126, 0.7152, 0.0722]))
            color = BG if (1.05 / (luminance + 0.05)) > ((luminance + 0.05) / 0.05) else "#000000"
            heat.text(j, i, f"{matrix[i, j]:.1f}%", ha="center", va="center", color=color, fontsize=12)
    rows = [
        [label, *[f"{v:.2f}" for v in matrix[i]]] for i, label in enumerate(["LLM", "Initial library", "Equal weight"])
    ]
    figure(
        "efs_cost_and_cadence",
        fig,
        "Figure 4. EFS trading costs and cadence",
        "All paths use the fixed generated factors and the same information. Weekly/monthly variants alter trading times and allow weights to drift; they do not manufacture daily rebalancing between those dates.",
        ["Path", "Daily CAGR (%)", "Weekly CAGR (%)", "Monthly CAGR (%)"],
        rows,
        f"{analysis_rel}/controlled_adaptations.csv",
    )
    paragraph(
        "In the completed EFS pilot, gross CAGR is 30.42% for the initial library and 26.57% for the LLM path; at 10 bps, the ordering reverses to 13.96% and 15.95%. This is a cost-channel reversal at fixed signal paths, not evidence that LLM factor generation improves gross returns. The equal-weight reference is 28.90% net at 10 bps. These previously completed paths are preserved, while the new grammar controls address the additional value of model search more directly."
    )
    g = stress[(stress["case"] == "GuruAgents") & (stress.cost_bps == 1) & stress.arm.str.startswith("replay__")]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    style_axes(ax)
    rows = []
    for i, (mode, label, color) in enumerate(
        [("tool-routing", "Tool routing", BLUE), ("archived-final", "One final call", ORANGE)]
    ):
        vals = []
        for delay in [0, 90]:
            row = g[
                (g.arm == f"replay__results_22_24__{mode}__ensemble") & (g.adapter == f"extra_information_lag_{delay}d")
            ].iloc[0]
            vals.append(row.cagr * 100)
            rows.append([label, delay, fmt(row.cagr, percent=True)])
        ax.bar(np.arange(2) + (i - 0.5) * 0.32, vals, 0.32, color=color, label=label)
    ax.set_xticks([0, 1], ["Next-quarter execution", "Additional 90-day lag"])
    ax.set_ylabel("CAGR at 1 bp (%)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    figure(
        "guru_information_lag",
        fig,
        "Figure 5. GuruAgents information-lag stress",
        "The fixed evaluation window is April 2022 through March 2025. Delayed paths remain in cash until their first eligible formation. The lag is a sensitivity analysis, not a certification of original filing timestamps.",
        ["Mode", "Extra lag (days)", "Net CAGR (%)"],
        rows,
        f"{analysis_rel}/controlled_adaptations.csv",
    )
    paragraph(
        "The extra 90-day lag changes which market conditions each recommendation encounters. In this historical window it raises both ensemble point returns; that does not establish that a delayed rule is preferable. Both timing variants are retained, and neither supplies the missing original publication-vintage evidence. This sensitivity shows why the mapping from a financial statement period to a tradable holding period must be explicit."
    )
    q = json.loads((PRIVATE / "quantaalpha_native/completion.json").read_text())["metrics"]
    atomic_json(
        PUBLIC / "quantaalpha_native_metrics.json",
        {"metrics": q, "scope": "Released library/predictor native metrics; no fresh LLM search."},
    )
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.3))
    rows = []
    for ax, key, label, scale in [
        (axes[0], "IC", "Native IC", 1),
        (axes[1], "annualized_return", "Annual net return above CSI300 (%)", 100),
    ]:
        style_axes(ax)
        values = [q[arm][key] * scale for arm in ["alpha158_20", "released_170"]]
        ax.bar(["20 factors", "170 factors"], values, color=[ORANGE, BLUE])
        ax.set_ylabel(label)
        for i, value in enumerate(values):
            ax.text(
                i,
                value,
                f"{value:.4f}" if scale == 1 else f"{value:.2f}",
                ha="center",
                va="bottom",
                color=INK,
                fontsize=10,
            )
        ax.margins(y=0.2)
    fig.tight_layout()
    for arm, label in [("alpha158_20", "20 core factors"), ("released_170", "170 released factors")]:
        rows.append(
            [
                label,
                fmt(q[arm]["IC"], 4),
                fmt(q[arm]["annualized_return"], percent=True),
                fmt(q[arm]["max_drawdown"], percent=True),
            ]
        )
    figure(
        "quanta_predictive_economic",
        fig,
        "Figure 6. Predictive and economic outcomes differ",
        "The two panels have different metrics and scales. Native annual return is benchmark-relative after source fees; drawdown is also the native benchmark-relative metric. This comparison conditions on the released factor pool and does not establish the causal value of fresh LLM discovery.",
        ["Library", "IC", "Net above benchmark (%/yr)", "Native drawdown (%)"],
        rows,
        "quantaalpha_native_metrics.json",
    )
    paragraph(
        "Adding the released custom factors improves the native predictive correlations and reduces the native benchmark-relative drawdown, while the fixed portfolio earns a lower annual benchmark-relative return. These are different economic dimensions. The result supports a component-level comparison of this predictor and portfolio, not a general statement that predictive accuracy cannot create value or that the original search process has been reproduced."
    )
    heading("6. Calibration and factor identification")
    methods = []
    for folder, label in [
        ("inference_calibration_basic_bootstrap_diagnostic", "Basic SB 95%"),
        ("inference_calibration", "Bootstrap-t 95%"),
    ]:
        x = pd.read_csv(PUBLIC / folder / "calibration_summary.csv")
        r = x[(x.mean_block == 6) & (x.true_annual_alpha == 0)].iloc[0]
        methods.append(
            {
                "method": label,
                "replications": int(r.replications),
                "rejection": r.rejects_zero_two_sided,
                "low": r.rejects_zero_two_sided_mc_ci95_low,
                "high": r.rejects_zero_two_sided_mc_ci95_high,
            }
        )
    for folder, label in [
        ("grouped_inference_calibration", "Grouped t 95%"),
        ("grouped_inference_validation_v2", "Primary grouped t 99%"),
    ]:
        x = pd.read_csv(PUBLIC / folder / "calibration_summary.csv")
        r = x[
            (x.observations == 72)
            & (x.rho == 0.3)
            & (x.noise_type == "normal")
            & (x.factor_count == 6)
            & (x.true_annual_alpha == 0)
        ].iloc[0]
        methods.append(
            {
                "method": label,
                "replications": int(r.replications),
                "rejection": r.reject,
                "low": r.reject_mc_ci95_low,
                "high": r.reject_mc_ci95_high,
            }
        )
    md = pd.DataFrame(methods)
    md.to_csv(tabledir / "calibration_full_audit.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    style_axes(ax)
    ax.bar(range(4), md.rejection * 100, color=[ORANGE, ORANGE, GRAY, BLUE])
    ax.errorbar(
        range(4),
        md.rejection * 100,
        yerr=[(md.rejection - md.low) * 100, (md.high - md.rejection) * 100],
        fmt="none",
        ecolor=INK,
        capsize=4,
    )
    ax.axhline(5, color=INK, linestyle="--", linewidth=1)
    ax.set_xticks(range(4), md.method, rotation=10, ha="right")
    ax.set_ylabel("False rejection of true zero alpha (%)")
    fig.tight_layout()
    rows = [
        [
            r["method"],
            r["replications"],
            f"{100 * r['rejection']:.2f}",
            f"[{100 * r['low']:.2f}, {100 * r['high']:.2f}]",
        ]
        for r in methods
    ]
    figure(
        "inference_calibration",
        fig,
        "Figure 7. Calibration rejects optimistic short-sample intervals",
        "Representative design: 72 monthly observations, six factors, AR(0.3) noise. Error bars are 95% Monte Carlo intervals for rejection rates. The dashed 5% line is an operating target, not the nominal size of the deliberately conservative 99% interval.",
        ["Method", "MC replications", "False rejection (%)", "MC interval (%)"],
        rows,
        str((tabledir / "calibration_full_audit.csv").relative_to(PUBLIC)),
    )
    validation_table = pd.read_csv(PUBLIC / "grouped_inference_validation_v2/calibration_summary.csv")
    null = validation_table[validation_table.true_annual_alpha == 0]
    minimum = float(null.cover.min())
    maximum = float(null.cover.max())
    paragraph(
        f"Independent-seed validation spans 36, 72 and 144 observations; AR coefficients 0, 0.3 and 0.6; Gaussian, Student-t(5) and deterministic heteroskedastic noise; and paired means or six-factor intercepts. There are 54 design cells, each with 2,000 replications. Primary nominal 99% bounds cover the true zero effect in {100 * minimum:.2f}% to {100 * maximum:.2f}% of these simulated samples. This supports conservative use on this grid, not an unconditional guarantee for arbitrary financial dependence or model-generation variation."
    )
    paragraph(
        "A known static 132-factor span is recovered to numerical precision when the sample identifies it. The short 72-by-132 regression is refused. A candidate constructed entirely from the observed JKP factors still produces nonzero chronological ridge/PCA reconstruction errors. Such errors reflect regularization and estimation as well as any omitted payoff; their mean is not automatically independent alpha."
    )
    table(
        ["Issue", "Treatment"],
        [
            ["Unrestricted JKP132 + market", "Report not identified when sample/rank is insufficient"],
            ["Six-factor projection", "Explicit conditional model; coefficients refit within groups"],
            ["Chronological ridge/PCA residual", "Reconstruction diagnostic, with no spanning-alpha p-value"],
            ["2pp materiality", "Bounds/equivalence; no inference from nonsignificance alone"],
            ["Identical observed paths", "No population equivalence claim from zero sampled variation"],
        ],
        f"{analysis_rel}/factor_attribution.csv",
    )
    heading("7. JKP-only versus agent-augmented allocation")
    ap = PUBLIC / "jkp_allocation_diagnostic"
    paths = pd.read_csv(ap / "monthly_returns.csv", parse_dates=["month"])
    exposures = pd.read_csv(ap / "monthly_sleeve_exposures.csv", parse_dates=["month"])
    am = pd.read_csv(ap / "metrics.csv")
    fig, (ax, weight_ax) = plt.subplots(2, 1, figsize=(7.2, 5.1), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    style_axes(ax)
    style_axes(weight_ax)
    for name, color, label in [("jkp_only", ORANGE, "JKP only"), ("jkp_plus_efs", BLUE, "JKP + EFS")]:
        ax.plot(paths.month, 100 * (1 + paths[name]).cumprod(), label=label, color=color)
    ax.set_ylabel("Wealth index")
    ax.legend(fontsize=9)
    w = exposures[(exposures.arm == "jkp_plus_efs") & (exposures.sleeve == "efs_agent")]
    weight_ax.plot(w.month, w.weight_in_input_return_units, color=BLUE)
    weight_ax.set_ylabel("EFS coefficient")
    weight_ax.set_xlim(paths.month.min(), paths.month.max())
    weight_ax.xaxis.set_major_locator(mdates.YearLocator())
    weight_ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    rows = [
        [
            "JKP only" if r.arm == "jkp_only" else "JKP + EFS",
            fmt(r.cagr, percent=True),
            fmt(r.vol_annualized, percent=True),
            fmt(r.certainty_equivalent_gamma10_annualized, percent=True),
        ]
        for r in am.itertuples()
    ]
    figure(
        "jkp_allocation",
        fig,
        "Figure 8. A fixed chronological allocation diagnostic",
        "Both versions use the same past-only scaling, diagonal covariance shrinkage and utility rule. Training starts with 36 months and evaluation covers the subsequent 36 months. Factor internal turnover, financing and allocation costs are unavailable; this is not a deployable net fund or a test of the best factor frontier.",
        ["Allocator", "CAGR (%)", "Volatility (%)", "CE, gamma=10 (%/yr)"],
        rows,
        "jkp_allocation_diagnostic/metrics.csv",
    )
    paragraph(
        "The allocation comparison answers a narrower question than factor spanning: whether this fixed past-only regularized rule benefits from being offered the EFS return stream. It does not identify the best attainable JKP frontier. The implementation is invariant to constant factor-unit rescalings and sign conventions, and a future-data perturbation test leaves earlier allocations unchanged. Exposures are coefficients on the supplied return series; their interpretation depends on the underlying factor portfolios and omitted financing costs."
    )
    heading("8. Prospective record and independent review")
    forward = json.loads((PRIVATE / "prospective_efs_v1/latest_forecast_summary.json").read_text())
    times = pd.to_datetime(
        [forward["recorded_at_utc"], forward["execution_at_utc"], forward["evaluation_at_utc"]],
        format="mixed",
        utc=True,
    )
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    ax.set_facecolor(BG)
    ax.plot(times, [0, 0, 0], color="#b5c2d3", linewidth=2)
    ax.scatter(times, [0, 0, 0], s=85, facecolors=[BLUE, BG, BG], edgecolors=[BLUE, GRAY, GRAY], linewidths=2, zorder=3)
    labels = ["Committed", "Simulated execution", "Future evaluation"]
    for i, (time, label) in enumerate(zip(times, labels)):
        ax.annotate(
            label + "\n" + time.strftime("%b%d %H:%M UTC"),
            (time, 0),
            xytext=(0, 18 if i % 2 == 0 else -40),
            textcoords="offset points",
            ha="center",
            color=INK,
            fontsize=10,
        )
    ax.set_ylim(-1, 1)
    ax.set_yticks([])
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b%d"))
    ax.tick_params(colors=INK)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    rows = [
        ["Forecast recorded", forward["recorded_at_utc"]],
        ["Execution close", forward["execution_at_utc"]],
        ["Evaluation close", forward["evaluation_at_utc"]],
        ["Eligible assets", forward["eligible_assets"]],
        ["Human review / public registration", "Pending"],
    ]
    # A compact public summary is derived from the already committed private ledger.
    atomic_json(PUBLIC / "prospective_summary.json", forward)
    figure(
        "prospective_timeline",
        fig,
        "Figure 9. A prospective development pilot has begun",
        "Four targets were committed together: LLM search, grammar search, the initial seed library and equal weight. This is a local development-pilot seal, not public preregistration or confirmatory evidence. No future return is supplied or invented.",
        ["Record", "Value"],
        rows,
        "prospective_summary.json",
    )
    paragraph(
        "Forecast digest: "
        + forward["forecast_sha256"]
        + ". The harness checks timezone-aware information availability, requires recording before execution and evaluation, links records by hashes, rejects replacement forecasts, and refuses to record outcomes before their evaluation close is observable. Settlement makes no new model calls. Future observations remain pending until the evaluation close."
    )
    paragraph(
        "Six outcome-free source-review packets and a code review bundle are available. The human-review ledger is empty unless an actual independent reviewer supplies an attested, hash-matched review. Automated compilation, tests, source checks and cached replay do not count as human review. A changed packet invalidates prior approval for that packet; unresolved reviewer objections remain visible."
    )
    heading("9. Reproducibility, limitations and publication readiness")
    spend = json.loads((PUBLIC / "spend_summary.json").read_text())
    paragraph(
        f"At this report's ledger snapshot, project research spending is {spend['project_committed_usd']:.2f} USD committed: {spend['known_or_tariff_cost_usd']:.2f} USD in known or tariff-accounted charges and {spend['unresolved_reservations_usd']:.2f} USD in conservative unresolved reservations. There are {spend['in_flight_requests']} in-flight requests. This includes prior imported usage, setup attempts, summaries, embeddings, recoveries and the prospective pilot; it is not a production-cost estimate."
    )
    replay_rows = []
    replay_summary = {}
    for case in ["finmem", "finagent", "tradingagents"]:
        path = PRIVATE / f"{case}_full_replay_validation.json"
        if not path.exists():
            if not args.preview:
                raise ValueError("Final replay validation is absent: " + case)
            continue
        record = json.loads(path.read_text())
        if record["status"] != "pass":
            raise ValueError("A full source replay has not passed: " + case)
        replay_summary[case] = record
        replay_rows.append(
            [
                {"finmem": "FinMem", "finagent": "FinAgent", "tradingagents": "TradingAgents"}[case],
                record["records"],
                record["difference_count"],
                fmt(record["maximum_numeric_difference"], 6),
            ]
        )
    atomic_json(PUBLIC / ("replay_summary_preview.json" if args.preview else "replay_summary.json"), replay_summary)
    table(
        ["Cached source trace", "Compared records", "Differences", "Maximum numeric difference"],
        replay_rows,
        "replay_summary_preview.json" if args.preview else "replay_summary.json",
    )
    paragraph(
        "Full cached replay compares decisions, economic state, timing, reasoning, memory fields and request/response identities. Only transport-cache flags and the order of independent transport events are ignored. It verifies deterministic reconstruction of the saved trajectory without new paid calls; it does not estimate uncertainty across fresh model generations or validate unavailable historical endpoints. The original EFS replay and independent account checks remain separately frozen."
    )

    paragraph(
        "All earlier studies remain intact. Paid requests share a project ledger with a soft spending stop of 450 USD below the 500 USD ceiling. Complete responses are persisted before accounting settlement, and unavailable responses retain conservative reservations. A shared SQLite write-lock failure, a development-allocation rollover and provider HTTP 500/read timeouts and compute-node network failures were recorded and reconciled; missing responses and their conservative charge bounds were not erased. Independent source embedding providers replace the early generic embedding adapters. An attempted batching optimization failed a full-prefix equivalence check and was retired; its responses and diagnostic failures remain available."
    )
    paragraph(
        "The source settings and modern substitutions limit external validity. Original vendor vintages and model snapshots are generally unavailable. Source universes can carry selection concerns. Current models may contain historical market information in pretraining even when supplied inputs are correctly timed. Short native windows and one realized model trajectory per arm constrain power and generalization. QuantaAlpha's released factor pool can contain selection informed by its historical test, so its comparison conditions on that pool. API/data/engineering costs are distinct from security trading costs; factor-sleeve financing and internal costs are not manufactured where holdings are missing."
    )
    paragraph(
        "The material deliverable is an auditable source-to-economic-account experiment and a calibrated statement of what the evidence identifies. The manuscript is a research draft for independent review. A claim of universal absence of alpha, original-paper reproduction, or prospective investment value would exceed this evidence. Independent source review and a substantially larger forward record are the remaining scientific conditions for stronger publication claims."
    )
    table(
        ["Case", "Study model / numerical route", "Declared scope"],
        [
            ["EFS", "GPT-4.1, temperature 0.3", "Paper-guided factor search; current model"],
            ["FinMem", "GPT-4-Turbo, temperature 0.7; native Ada002 wrapper", "Paper K=5; one TSLA trajectory per arm"],
            [
                "FinAgent",
                "GPT-4o, temperature 0.1; native 3-large/3072 embedding provider",
                "Historical chat IDs unavailable; explicit current decoding choice",
            ],
            ["TradingAgents", "GPT-4o, temperature 0.1", "Original v0.1.0 role graph; model-role substitution"],
            ["GuruAgents", "GPT-4o, temperature 0", "Actual source-prompt/tool replay"],
            ["QuantaAlpha", "Native LightGBM, seed 42; released factor library", "No new LLM-search execution"],
        ],
        "source_review/packet_manifest.json",
    )
    paragraph(
        "The final embedding computations are source-specific. FinMem delegates tokenization, document batching and normalization to its released wrapper. FinAgent executes the released provider configured for text-embedding-3-large with 3,072 dimensions, while prefetching independent per-document requests concurrently. The attempted generic Ada batching optimization did not preserve a saved training prefix and was rejected. These checks limit implementation drift; they do not establish equivalence to unavailable historical model services."
    )
    heading("10. Artifact index and reproduction")
    table(
        ["Artifact", "Role"],
        [
            ["analysis/paired_effects.csv", "Primary/secondary effects, bounds and Holm family fields"],
            ["analysis/controlled_adaptations.csv", "All declared cost/cadence/latency account variants"],
            ["source_review/", "Outcome-free packets, templates and real review ledger"],
            ["grouped_inference_validation_v2/", "Independent simulation validation"],
            ["jkp_allocation_diagnostic/", "Past-only conditional allocation comparison"],
            ["artifacts/publication_upgrade_v1/", "Private inputs, responses, accounts and recovery evidence"],
        ],
    )
    paragraph(
        "The private execution inputs and response cache are separate from public presentation tables. Individual-security data, raw news and API responses remain private. File hashes, source pins, central environment paths and documented adapters are part of the reproducibility record. Reproduction requires the listed central environments or equivalent reconstructed dependencies and access to the appropriately licensed data."
    )
    blocks.append(
        {
            "type": "code",
            "text": 'cd /nfs/roberts/project/pi_btk22/zc362/alpha_evolve\n# See docs/PUBLICATION_UPGRADE_RUNBOOK.md for complete cached replays.\nENV_ROOT=/nfs/roberts/project/pi_btk22/zc362/environments\nPUBLICATION_PY="$ENV_ROOT/venvs/alpha-agent-replication-py312-20260813/bin/python"\n"$PUBLICATION_PY" scripts/analyze_publication_upgrade.py\n"$ENV_ROOT/bin/kt-python" scripts/build_publication_report.py\n"$ENV_ROOT/bin/kt-python" scripts/validate_publication_report.py\n# After the committed future evaluation close is observable:\nscripts/run_finmem_fidelity_python.sh scripts/run_efs_prospective.py --settle-only',
        }
    )
    heading("References")
    for i, (label, text, url) in enumerate(REFERENCES, 1):
        paragraph(f"[{i}] {text} {url}")
    # Generate all prose formats from one block sequence.
    visual = []
    plain = []
    for block in blocks:
        kind = block["type"]
        if kind == "title":
            text = "# " + block["text"] + "\n\n" + block["subtitle"]
            visual.append(text)
            plain.append(text)
        elif kind == "h":
            visual.append("## " + block["text"])
            plain.append("## " + block["text"])
        elif kind in ["p", "banner"]:
            visual.append(block["text"])
            plain.append(block["text"])
        elif kind == "math":
            text = "$$\n" + block["text"] + "\n$$"
            visual.append(text)
            plain.append(text)
        elif kind == "figure":
            visual.append(
                "### "
                + block["title"]
                + "\n\n"
                + block["caption"]
                + "\n\n!["
                + block["title"]
                + "]("
                + block["path"]
                + ")"
            )
            plain.append("### " + block["title"] + "\n\n" + block["caption"])
        elif kind == "table":
            text = mdtable(block["headers"], block["rows"])
            audit = block.get("audit")
            if audit:
                text += "\n\n[Full audit](" + audit + ")"
            visual.append(text)
            plain.append(text)
        elif kind == "code":
            text = "```bash\n" + block["text"] + "\n```"
            visual.append(text)
            plain.append(text)
    visual_name = "PREVIEW_VISUAL_REPORT.md" if args.preview else "VISUAL_REPORT.md"
    plain_name = "PREVIEW_REPORT.md" if args.preview else "REPORT.md"
    (PUBLIC / visual_name).write_text("\n\n".join(visual) + "\n")
    (PUBLIC / plain_name).write_text("\n\n".join(plain) + "\n")
    # PDF authoring via ReportLab; fonts, backgrounds and foregrounds are explicit.
    font_path = Path(font_manager.findfont("DejaVu Serif")).parent
    pdfmetrics.registerFont(TTFont("Body", str(font_path / "DejaVuSerif.ttf")))
    pdfmetrics.registerFont(TTFont("BodyBold", str(font_path / "DejaVuSerif-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Mono", str(font_path / "DejaVuSansMono.ttf")))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="BodyBold", italic="Body", boldItalic="BodyBold")
    body = ParagraphStyle(
        "BodyStyle", fontName="Body", fontSize=10.1, leading=14.2, textColor=colors.HexColor(INK), spaceAfter=9
    )
    small = ParagraphStyle("Small", parent=body, fontSize=8.7, leading=11.3, spaceAfter=6)
    heading_style = ParagraphStyle(
        "Heading",
        parent=body,
        fontName="BodyBold",
        fontSize=13.5,
        leading=17,
        textColor=colors.HexColor("#123f69"),
        spaceBefore=14,
        spaceAfter=9,
        keepWithNext=True,
    )
    table_style = ParagraphStyle("Cell", parent=body, fontSize=8.4, leading=10.6, spaceAfter=0)
    mono = ParagraphStyle(
        "MonoStyle",
        parent=small,
        fontName="Mono",
        fontSize=7.7,
        leading=10.8,
        backColor=colors.HexColor(PALE),
        borderPadding=8,
        wordWrap="CJK",
    )
    pdf_path = PUBLIC / ("manuscript_preview.pdf" if args.preview else "manuscript.pdf")
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=(612, 792),
        rightMargin=48,
        leftMargin=48,
        topMargin=46,
        bottomMargin=48,
        title=title,
        author="Research draft - author details to be supplied",
        pageCompression=1,
    )
    story = []

    def para(text, style=body):
        escaped = html.escape(text)
        escaped = re.sub(
            r"(https://[^\s]+)",
            lambda m: '<link href="' + m.group(1) + '" color="#145da0">' + m.group(1) + "</link>",
            escaped,
        )
        return Paragraph(escaped, style)

    def pdf_table(block):
        cells = [[para(str(x), table_style) for x in block["headers"]]] + [
            [para(str(x), table_style) for x in row] for row in block["rows"]
        ]
        count = len(block["headers"])
        widths = [516 / count] * count
        if count == 2:
            widths = [170, 346]
        value = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        value.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6eef8")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(INK)),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fb")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#8b99ad")),
                    ("LINEBELOW", (0, -1), (-1, -1), 0.3, colors.HexColor("#d3dce8")),
                ]
            )
        )
        result = [value, Spacer(1, 7)]
        if block.get("audit"):
            result.append(para("Full audit: " + block["audit"], small))
        return result

    skip_index = -1
    for index, block in enumerate(blocks):
        if index == skip_index:
            continue
        kind = block["type"]
        if kind == "title":
            story.extend(
                [
                    Paragraph(
                        html.escape(block["text"]),
                        ParagraphStyle("Title", parent=heading_style, fontSize=24, leading=28, spaceAfter=12),
                    ),
                    para(block["subtitle"]),
                    para(
                        "Working manuscript | " + datetime.now(timezone.utc).strftime("%Y-%m-%d") + "",
                        small,
                    ),
                    Spacer(1, 10),
                ]
            )
        elif kind == "banner":
            story.append(
                Paragraph(
                    html.escape(block["text"]),
                    ParagraphStyle(
                        "Banner",
                        parent=body,
                        backColor=colors.HexColor("#fff2cc"),
                        textColor=colors.HexColor("#503700"),
                        borderPadding=8,
                        spaceAfter=16,
                    ),
                )
            )
        elif kind == "h":
            story.append(Paragraph(html.escape(block["text"]), heading_style))
        elif kind == "p":
            story.append(para(block["text"]))
        elif kind == "math":
            f = plt.figure(figsize=(7.2, 0.7), facecolor=BG)
            f.text(0.5, 0.5, "$" + block["text"] + "$", ha="center", va="center", color=INK, fontsize=15)
            math_path = figdir / f"equation_{index}.png"
            f.savefig(math_path, dpi=260, facecolor=BG, bbox_inches="tight")
            plt.close(f)
            w, h = ImageReader(str(math_path)).getSize()
            scale = min(72 / 260, 500 / w)
            story.extend([Image(str(math_path), width=w * scale, height=h * scale), Spacer(1, 7)])
        elif kind == "figure":
            path = PUBLIC / block["path"]
            w, h = ImageReader(str(path)).getSize()
            maximum = 350 if "paired_effects" in block["path"] or "efs_cost" in block["path"] else 400
            scale = min(510 / w, maximum / h)
            group = [
                Paragraph(html.escape(block["title"]), heading_style),
                para(block["caption"], small),
                Image(str(path), width=w * scale, height=h * scale),
                Spacer(1, 7),
            ]
            if index + 1 < len(blocks) and blocks[index + 1]["type"] == "table":
                group.extend(pdf_table(blocks[index + 1]))
                skip_index = index + 1
            if index > 0 and blocks[index - 1]["type"] == "h":
                group.insert(0, story.pop())
            story.append(KeepTogether(group))
        elif kind == "table":
            story.append(KeepTogether(pdf_table(block)))
        elif kind == "code":
            story.append(Paragraph("<br/>".join(html.escape(line) for line in block["text"].splitlines()), mono))

    def page(canvas, document):
        canvas.saveState()
        canvas.setFillColor(colors.white)
        canvas.rect(0, 0, 612, 792, fill=1, stroke=0)
        canvas.setFont("Body", 8)
        canvas.setFillColor(colors.HexColor("#42526b"))
        canvas.drawString(48, 26, "Economic Fidelity Before Alpha | Research draft")
        canvas.drawRightString(564, 26, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=page, onLaterPages=page)
    atomic_json(
        PUBLIC / ("report_preview_manifest.json" if args.preview else "report_manifest.json"),
        {
            "status": status["status"],
            "analysis_status": status,
            "figures": figures,
            "visual_report": visual_name,
            "no_image_report": plain_name,
            "pdf": pdf_path.name,
            "pdf_sha256": sha256(pdf_path),
            "builder_sha256": sha256(Path(__file__)),
            "analysis_file_sha256": {p.name: sha256(p) for p in sorted(analysis.glob("*")) if p.is_file()},
            "spend_summary_sha256": sha256(PUBLIC / "spend_summary.json"),
            "explicit_colors": {"foreground": INK, "background": BG, "tested": BLUE, "control": ORANGE},
            "primary_calibration_minimum_coverage": minimum,
            "primary_calibration_maximum_coverage": maximum,
            "human_review_complete": json.loads((PUBLIC / "source_review/human_review_ledger.json").read_text())[
                "independent_human_review_complete"
            ],
        },
    )
    print("REPORT_BUILT", pdf_path, flush=True)


if __name__ == "__main__":
    main()
