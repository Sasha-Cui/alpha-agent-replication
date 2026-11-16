#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Recompute and display the complete Quanta native case without model selection."""

from pathlib import Path
import json
import re
import sys
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.text import Text
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.publication_inference import grouped_t_effect
from alpha_evolve.fidelity_inference_v2 import adjust_grouped_family

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"
OUT = PUBLIC / "quantaalpha_later_period_report"
FG = "#172B4D"
BG = "#FFFFFF"
PRIMARY = "#17456B"
SECONDARY = "#596579"
GOLD = "#925000"


def read(path):
    return json.loads(path.read_text())


def source_snapshot(path, digest):
    candidates = [path]
    for folder in ["oos_export_recovery_20260917", "secondary_analysis_20260917"]:
        candidates.extend((PRIVATE / folder).rglob("*.py"))
    for p in candidates:
        if p.is_file() and sha256(p) == digest:
            return str(p.relative_to(ROOT))
    raise ValueError("Exact executed analyzer source unavailable: " + str(path))


def load_analysis(name, kind):
    folder = PUBLIC / name
    completion = read(folder / "completion.json")
    expected = "partial_case_analysis" if kind == "pooled" else "complete_case_partial_secondary_family"
    if completion["status"] != expected:
        raise ValueError("Unexpected analysis status")
    for filename, digest in completion["outputs"].items():
        if sha256(folder / filename) != digest:
            raise ValueError("Completed economic artifact changed")
    if kind == "pooled":
        snapshots = [source_snapshot(ROOT / "scripts/analyze_native_grouped_oos_v2.py", completion["script_sha256"])]
    else:
        snapshots = [source_snapshot(ROOT / path, digest) for path, digest in completion["source_files"].items()]
    frame = pd.read_csv(folder / "daily_net_returns.csv", parse_dates=["date"])
    rows = read(folder / "comparisons.json")
    expected_rows = 4 if kind == "pooled" else 28
    if len(rows) != expected_rows:
        raise ValueError("Incomplete comparison table")
    for row in rows:
        if kind == "pooled":
            selected = frame.loc[(frame.case == "quantaalpha") & (frame.execution == row["execution"])]
            left = selected.loc[selected.arm == row["baseline"] + "_plus_library"].set_index("date").net_return
            right = selected.loc[selected.arm == row["baseline"]].set_index("date").net_return
        else:
            left = frame.loc[frame.run == row["run"]].set_index("date").net_return
            right = frame.loc[frame.run == row["reused_baseline"]].set_index("date").net_return
        if not left.index.equals(right.index) or left.index.has_duplicates or len(left) != 963:
            raise ValueError("Paired comparison calendar changed")
        result = grouped_t_effect(
            left.to_numpy(), right.to_numpy(), frequency=252, groups=4, threshold=0.02, confidence=0.99
        )
        for key in [
            "full_sample_annualized_effect",
            "annualized_arithmetic_effect",
            "primary_ci_low",
            "primary_ci_high",
            "group_t_p_two_sided",
        ]:
            if not np.isclose(result[key], row[key], rtol=0, atol=1e-12):
                raise ValueError("Reported economic statistic fails recomputation: " + key)
        row.update(
            library_kind=kind,
            display_name="Pooled library" if kind == "pooled" else "Task " + str(row["unit"]),
            analysis_source=str(folder.relative_to(ROOT)),
            analysis_completion_sha256=sha256(folder / "completion.json"),
            first_date=str(left.index.min().date()),
            last_date=str(left.index.max().date()),
            sessions=len(left),
        )
    economic = [
        r for r in rows if r["execution"] == "opening_information" and (kind != "pooled" or r["baseline"] == "alpha158")
    ]
    _, adjusted = adjust_grouped_family(economic, 2 if kind == "pooled" else 54, False)
    key = "family_adjusted_p" if kind == "pooled" else "secondary_family_adjusted_p"
    if any(not np.isclose(r[key], p, rtol=0, atol=1e-12) for r, p in zip(economic, adjusted)):
        raise ValueError("Multiplicity correction differs from completed analysis")
    return rows, {
        "folder": str(folder.relative_to(ROOT)),
        "completion_sha256": sha256(folder / "completion.json"),
        "exact_executed_source_snapshots": snapshots,
    }


def layout_check(fig):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    for item in fig.findobj(Text):
        if item.get_visible() and item.get_text():
            bb = item.get_window_extent(renderer)
            if bb.x0 < bounds.x0 - 2 or bb.x1 > bounds.x1 + 2 or bb.y0 < bounds.y0 - 2 or bb.y1 > bounds.y1 + 2:
                raise ValueError("Clipped figure text: " + item.get_text())


def save_figure(fig, name):
    # Fixed in-range ticks prevent checking locator labels that Matplotlib
    # would never draw beyond the displayed axis limits.
    for axis in fig.axes:
        low, high = axis.get_xlim()
        axis.set_xticks([tick for tick in axis.get_xticks() if low <= tick <= high])
    layout_check(fig)
    for suffix, dpi in [(".png", 160), ("_preview.png", 80), (".pdf", 160)]:
        fig.savefig(OUT / "visual_figures" / (name + suffix), dpi=dpi, facecolor=BG, edgecolor=BG)
    plt.close(fig)


def md_table(rows, columns):
    return [
        "| " + " | ".join(label for label, key in columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
        *["| " + " | ".join(str(row[key]) for label, key in columns) + " |" for row in rows],
    ]


def main():
    pooled, p1 = load_analysis("native_grouped_oos_quantaalpha", "pooled")
    tasks, p2 = load_analysis("native_secondary_oos_quantaalpha", "individual")
    allrows = pooled + tasks
    for execution in ["native", "opening_information"]:
        for base in ["source4", "alpha158"]:
            if sorted(r["unit"] for r in tasks if r["execution"] == execution and r["baseline"] == base) != list(
                range(7)
            ):
                raise ValueError("Cannot omit or duplicate a native task")
    for sub in ["visual_figures", "visual_tables"]:
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    pd.DataFrame(allrows).to_csv(OUT / "visual_tables/comparisons_full_audit.csv", index=False)
    primary = next(r for r in pooled if r["role"] == "primary_economic")
    open_rows = [
        primary,
        *sorted(
            [r for r in tasks if r["execution"] == "opening_information" and r["baseline"] == "alpha158"],
            key=lambda r: r["unit"],
        ),
    ]
    native = [
        next(r for r in pooled if r["execution"] == "native" and r["baseline"] == "alpha158"),
        *sorted(
            [r for r in tasks if r["execution"] == "native" and r["baseline"] == "alpha158"], key=lambda r: r["unit"]
        ),
    ]
    plt.rcParams.update(
        {
            "text.color": FG,
            "axes.labelcolor": FG,
            "axes.edgecolor": FG,
            "xtick.color": FG,
            "ytick.color": FG,
            "axes.facecolor": BG,
            "figure.facecolor": BG,
            "savefig.facecolor": BG,
            "font.size": 11,
            "font.family": "DejaVu Sans",
            "legend.labelcolor": FG,
            "legend.facecolor": BG,
            "legend.edgecolor": "#B5C2D2",
        }
    )
    labels = [r["display_name"] + (" (primary)" if i == 0 else "") for i, r in enumerate(open_rows)]
    fig, ax = plt.subplots(figsize=(10, 6.4))
    fig.subplots_adjust(left=0.27, right=0.97, top=0.84, bottom=0.19)
    for i, row in enumerate(open_rows):
        color = PRIMARY if i == 0 else SECONDARY
        value = 100 * row["annualized_arithmetic_effect"]
        lo = 100 * row["primary_ci_low"]
        hi = 100 * row["primary_ci_high"]
        ax.errorbar(
            value,
            i,
            xerr=[[value - lo], [hi - value]],
            fmt="o",
            color=color,
            ecolor=color,
            capsize=4,
            markersize=7 if i == 0 else 5,
            lw=2 if i == 0 else 1.5,
        )
    ax.set_yticks(range(8), labels)
    ax.invert_yaxis()
    ax.axvline(0, color=FG, ls="--", lw=1, label="Zero increment")
    ax.axvline(2, color=GOLD, ls=":", lw=1.5, label="+2 pp economic margin")
    ax.set_xlabel("Grouped annualized mean net-return increment over Alpha158 (pp/year)")
    ax.grid(axis="x", color="#D8E0EA", lw=0.6)
    ax.set_axisbelow(True)
    fig.suptitle("QuantaAlpha: pooled and all seven task libraries", fontsize=15, color=FG, x=0.53, y=0.965)
    fig.text(
        0.53,
        0.905,
        "Opening-information fills · 963 sessions · pointwise 99% intervals",
        ha="center",
        color=FG,
        fontsize=11,
    )
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.29), ncol=2, frameon=True)
    save_figure(fig, "all_library_intervals")
    fig, ax = plt.subplots(figsize=(10, 6.4))
    fig.subplots_adjust(left=0.27, right=0.97, top=0.84, bottom=0.19)
    for i, (old, new) in enumerate(zip(native, open_rows)):
        x, y = 100 * old["full_sample_annualized_effect"], 100 * new["full_sample_annualized_effect"]
        ax.plot([x, y], [i, i], color="#A8B5C6", lw=1.5)
        ax.scatter(
            x, i, color=SECONDARY, marker="s", s=40, label="Source-native eligibility" if i == 0 else None, zorder=3
        )
        ax.scatter(
            y, i, color=PRIMARY, marker="o", s=48, label="Opening-information eligibility" if i == 0 else None, zorder=3
        )
    ax.set_yticks(range(8), labels)
    ax.invert_yaxis()
    ax.axvline(0, color=FG, ls="--", lw=1)
    ax.set_xlabel("Full-sample annualized mean net-return increment over Alpha158 (pp/year)")
    ax.grid(axis="x", color="#D8E0EA", lw=0.6)
    ax.set_axisbelow(True)
    fig.suptitle("Eligibility timing changes the measured increment", fontsize=15, color=FG, x=0.53, y=0.965)
    fig.text(
        0.53,
        0.905,
        "Same saved predictions, fees, lots and dates; native outputs remain diagnostic",
        ha="center",
        color=FG,
        fontsize=10.5,
    )
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.29), ncol=2, frameon=True)
    save_figure(fig, "execution_information")
    table = []
    timing = []
    for r, n in zip(open_rows, native):
        p = r.get("family_adjusted_p", r.get("secondary_family_adjusted_p"))
        table.append(
            {
                "library": r["display_name"],
                "mean": f"{100 * r['full_sample_annualized_effect']:+.2f}",
                "interval": f"[{100 * r['primary_ci_low']:+.2f}, {100 * r['primary_ci_high']:+.2f}]",
                "adjusted_p": f"{p:.3f}",
            }
        )
        timing.append(
            {
                "library": r["display_name"],
                "native": f"{100 * n['full_sample_annualized_effect']:+.2f}",
                "opening": f"{100 * r['full_sample_annualized_effect']:+.2f}",
                "change": f"{100 * (r['full_sample_annualized_effect'] - n['full_sample_annualized_effect']):+.2f}",
            }
        )
    pd.DataFrame(table).to_csv(OUT / "visual_tables/opening_presentation.csv", index=False)
    pd.DataFrame(timing).to_csv(OUT / "visual_tables/timing_presentation.csv", index=False)
    task_effects = np.asarray([r["full_sample_annualized_effect"] for r in open_rows[1:]])
    audit = "[Full comparison audit](visual_tables/comparisons_full_audit.csv)"
    lines = [
        "# QuantaAlpha later-period results — completed case, exploratory study",
        "",
        f"No significant incremental alpha is established. The pooled library adds **{100 * primary['full_sample_annualized_effect']:.2f} percentage points/year** over Alpha158 under opening-information eligibility, but its grouped 99% interval spans **{100 * primary['primary_ci_low']:.2f} to {100 * primary['primary_ci_high']:.2f} points**. The two-case conservative adjusted p-value is {primary['family_adjusted_p']:.3f}.",
        "",
        f"Across all seven individual task libraries, **{int((task_effects < 0).sum())}/7 underperform** Alpha158. Their median full-sample increment is **{100 * np.median(task_effects):+.2f} points/year**; none has a positive interval and a corrected p-value below 1%. These are dependent source tasks on one market history, not seven independent market replications. The pooled feature union is a different fitted model, not an average of task portfolios.",
        "",
        "## Fixed comparison contract",
        "",
        "| Choice | Main analysis | Alternative and status |",
        "|---|---|---|",
        "| Features | Complete source-used pooled library over Alpha158 | All seven individual task libraries completed; secondary |",
        "| Execution | Opening-information eligibility with uniform 9.5% proxy | Source-native eligibility retained as diagnostic |",
        "| Portfolio | Released native Top50/drop5, source fees and lots | Same saved predictions across execution rules; no refit |",
        "| Sample | CSI300 dated universe; 963 sessions, "
        + primary["first_date"]
        + " to "
        + primary["last_date"]
        + " | China comparison; no JKP132 attribution |",
        "| Model/data lineage | Current served model and alternative archived data | Historical snapshots and pristine confirmation unavailable |",
        "| Study completion | This pooled and seven-task Quanta case complete | Alpha20, separate Quanta paper-parameter sensitivity and final families pending |",
        "",
        "## All libraries, retained without selecting a winner",
        "",
        "![All pooled and task confidence intervals](visual_figures/all_library_intervals.png)",
        "",
        *md_table(
            table,
            [
                ("Library", "library"),
                ("Full-sample mean, pp/year", "mean"),
                ("Grouped 99% interval, pp", "interval"),
                ("Adjusted p*", "adjusted_p"),
            ],
        ),
        "",
        audit
        + ". The plot centers each interval on its grouped estimate; the table reports the distinct full-sample mean. *The pooled row uses a conservative two-primary-contrast bound; task rows use the separate 54-contrast secondary-family bound. Those families remain partial while AlphaAgent is incomplete. Intervals are pointwise, not simultaneous.",
        "",
        "## Opening information versus native eligibility",
        "",
        "![Effect of the eligibility information set](visual_figures/execution_information.png)",
        "",
        *md_table(
            timing,
            [
                ("Library", "library"),
                ("Native diagnostic, pp/year", "native"),
                ("Opening information, pp/year", "opening"),
                ("Change, pp/year", "change"),
            ],
        ),
        "",
        audit
        + ". These are arithmetic-mean differences after costs. Source-native Qlib uses same-day change and closing-price missingness to gate open fills. The opening variant uses finite positive current open and prior close, with byte-identical saved predictions/labels and identical portfolio rules. It remains a uniform proxy, not exact board-specific auctions, liquidity, impact or point-in-time adjustment history.",
        "",
        "## Source4 and inference boundaries",
        "",
        "Both Source4-baseline contrasts are retained in the full audit table. They are secondary and do not substitute for Alpha158 attribution. The economic primary is the pooled opening-information increment over Alpha158; no task is promoted after seeing returns.",
        "",
        "Inference uses four contiguous time blocks, 99% pointwise intervals and a 1% family threshold. The original stationary-bootstrap results remain diagnostic after synthetic short-sample undercoverage. Grouped-method calibration covered eight specified data-generating/sample cells, not every financial process; approximate independence and normality of block estimates remain assumptions. Degenerate comparisons contribute p=1 to family adjustment. Current library/endpoint/data choices make this exploratory historical analysis.",
        "",
        "The annualized mean equals 252 times a daily arithmetic mean. Grouped intervals cover that estimand, not geometric growth. Any underlying `cagr` field denotes 252-session geometric annualization, not calendar-time CAGR. Finite model inputs do not erase separately flagged raw-factor infinities. Information boundaries and full-universe factor checks establish specific causal-input properties, not historical model-knowledge purity.",
        "",
        "## Replication and publication status",
        "",
        "The bounded released-default Quanta source, full cached replay, seven source accounts, sixteen source-used program proofs, eight pooled later-period accounts and twenty-eight task-level later-period accounts have completed their respective checks. These counts are execution evidence, not full-paper reproduction. The factor YAML was inactive; actual constructor/prompt settings and the separately pending paper-parameter variant are documented in the source review packet. Missing historical model/data/seed/zoo lineage and structured segment splicing remain gaps.",
        "",
        "All 69 papers keep distinct evidence and limitations. No significant JKP132 alpha, pristine confirmatory result, independent human review, final full-study archive, or full-paper reproduction is claimed by this report.",
        "",
        "## Evidence and reproduction",
        "",
        "[Report verification](validation.json) · [Source lineage](lineage.json) · [Source review packet](../SOURCE_REVIEW_PACKET.md) · [Current project status](../STATUS.md) · "
        + audit,
        "",
        "The builder verifies source output hashes, resolves exact executed analyzer snapshots, and recomputes all 32 comparison means, intervals and p-values from their paired daily net returns before drawing figures. It never trains a model or makes an API call.",
        "",
        "From the canonical Bouchet checkout:",
        "",
        "```bash",
        "/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python scripts/build_quanta_results_report_v2.py",
        "```",
        "",
    ]
    text = "\n".join(lines)
    (OUT / "VISUAL_REPORT.md").write_text(text)
    (OUT / "REPORT.md").write_text(re.sub(r"!\[[^]]*\]\([^)]*\)\n?", "", text))
    atomic_json(
        OUT / "lineage.json",
        {
            "analysis_inputs": [p1, p2],
            "builder_sha256": sha256(Path(__file__)),
            "all_compared_statistics_recomputed": 32,
            "new_model_calls": 0,
            "source_results_overwritten": False,
        },
    )
    images = []
    for name in ["all_library_intervals", "execution_information"]:
        path = OUT / "visual_figures" / (name + ".png")
        array = np.asarray(Image.open(path).convert("RGB"))
        if array.std() < 10:
            raise ValueError("Blank figure")
        images.append(
            {
                "path": str(path.relative_to(OUT)),
                "sha256": sha256(path),
                "shape": list(array.shape),
                "pixel_std": float(array.std()),
            }
        )

    # Explicit palette luminance; every text-bearing figure element uses FG/BG.
    def lum(color):
        v = np.asarray([int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)])
        v = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
        return float(v @ np.array([0.2126, 0.7152, 0.0722]))

    contrast = (lum(BG) + 0.05) / (lum(FG) + 0.05)
    if contrast < 7:
        raise ValueError("Insufficient figure text contrast")
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if target == "validation.json":
            continue
        if not (OUT / target).is_file():
            raise ValueError("Broken report link: " + target)
    for match in re.finditer(r"!\[[^]]*\]\([^)]*\)", text):
        if not text[match.end() :].lstrip().startswith("|"):
            raise ValueError("Every figure must immediately precede a table")
    if "![" in (OUT / "REPORT.md").read_text():
        raise ValueError("No-image counterpart contains image")
    atomic_json(
        OUT / "validation.json",
        {
            "status": "numeric_and_layout_checks_pass_visual_review_pending",
            "comparisons_recomputed": 32,
            "all7tasks_retained": True,
            "figures": images,
            "text_contrast_ratio": contrast,
            "figure_text_within_canvas": True,
            "links_exist": True,
            "each_figure_followed_by_table": True,
            "no_image_counterpart_pass": True,
            "scope": "Completed single-case report; no complete primary or secondary family, significant-alpha or full-paper claim.",
            "outputs": {
                str(p.relative_to(OUT)): sha256(p)
                for p in OUT.rglob("*")
                if p.is_file() and p.name != "validation.json"
            },
        },
    )
    print("QUANTA_CASE_REPORT_NUMERIC_LAYOUT_PASS", 32, contrast, flush=True)


if __name__ == "__main__":
    main()
