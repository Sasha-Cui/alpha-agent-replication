#!/usr/bin/env python3
"""Build the 62-proxy performance-metric correlation matrix and heatmap."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap


METRICS = {
    "Standalone\nSharpe": "candidate_standalone_oos_sharpe",
    "FF5Mom\nalpha": "ff5mom_alpha_annualized",
    "FF5Mom\nt-stat": "ff5mom_alpha_tstat_hac",
    "FF5Mom\nIR": "ff5mom_appraisal_ratio",
    "FF5Mom\nGRS p": "ff5mom_grs_p_value",
    "FF5Mom\nspan lift": "ff5mom_combined_minus_old_sharpe",
    "TextBench\nt-stat": "textbenchmark_alpha_tstat_hac",
    "TextBench\nIR": "textbenchmark_information_ratio",
    "Full span\nt-stat": "full_alpha_tstat_hac",
    "Full span\nIR": "full_information_ratio",
    "Full span\nGRS p": "full_grs_p_value",
    "Full span\nlift": "full_combined_minus_old_sharpe",
    "Book\nweight": "longonly_all_mvo_candidate_weight",
    "Book\ndelta SR": "longonly_delta_sharpe",
}

SENTINELS = {
    ("Standalone\nSharpe", "TextBench\nIR"): 0.97,
    ("FF5Mom\nt-stat", "FF5Mom\nIR"): 1.00,
    ("Full span\nGRS p", "Full span\nlift"): -0.86,
    ("Book\nweight", "Book\ndelta SR"): 0.93,
}


def build_correlation(source: Path) -> pd.DataFrame:
    frame = pd.read_csv(source)
    if len(frame) != 62:
        raise AssertionError(f"expected 62 candidate proxies, found {len(frame)}")
    missing = sorted(set(METRICS.values()) - set(frame.columns))
    if missing:
        raise KeyError(f"missing metric columns: {missing}")
    correlation = frame[list(METRICS.values())].apply(pd.to_numeric, errors="coerce").corr()
    correlation.index = list(METRICS)
    correlation.columns = list(METRICS)
    for (row, column), expected in SENTINELS.items():
        observed = float(correlation.loc[row, column])
        if not np.isclose(observed, expected, atol=0.005):
            raise AssertionError(f"unexpected {row}/{column} correlation: {observed:.4f}")
    return correlation


def render(correlation: pd.DataFrame, output: Path) -> None:
    background = "#FFFFFF"
    foreground = "#172033"
    grid = "#FFFFFF"
    cmap = LinearSegmentedColormap.from_list("alpha_evolve_diverging", ["#2C6DB7", "#F7F4F3", "#B13238"])
    plt.rcParams.update(
        {
            "figure.facecolor": background,
            "axes.facecolor": background,
            "axes.edgecolor": foreground,
            "axes.labelcolor": foreground,
            "xtick.color": foreground,
            "ytick.color": foreground,
            "text.color": foreground,
            "font.family": "DejaVu Sans",
        }
    )
    fig, axis = plt.subplots(figsize=(17.3667, 15.14), dpi=150)
    image = axis.imshow(correlation.to_numpy(), cmap=cmap, vmin=-1, vmax=1, aspect="auto")

    labels = list(correlation.columns)
    axis.set_xticks(range(len(labels)), labels=labels, rotation=45, ha="right", fontsize=12)
    axis.set_yticks(range(len(labels)), labels=labels, fontsize=12)
    axis.set_xticks(np.arange(-0.5, len(labels), 1), minor=True)
    axis.set_yticks(np.arange(-0.5, len(labels), 1), minor=True)
    axis.grid(which="minor", color=grid, linewidth=1.5)
    axis.tick_params(which="minor", bottom=False, left=False)
    for spine in axis.spines.values():
        spine.set_visible(False)

    values = correlation.to_numpy()
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            value = values[row, column]
            text_color = "#FFFFFF" if abs(value) >= 0.68 else foreground
            axis.text(
                column,
                row,
                f"{value:.2f}",
                ha="center",
                va="center",
                color=text_color,
                fontsize=10,
            )

    colorbar = fig.colorbar(image, ax=axis, fraction=0.045, pad=0.05)
    colorbar.set_label("Correlation", color=foreground, fontsize=12, labelpad=16)
    colorbar.ax.tick_params(colors=foreground, labelsize=11)
    colorbar.outline.set_edgecolor(background)

    fig.suptitle(
        "How the Performance Metrics Co-Move Across Candidate Proxies\n"
        "High correlations show that most apparent positives are the same factor composite geometry",
        color=foreground,
        fontsize=20,
        fontweight="bold",
        y=0.985,
    )
    fig.subplots_adjust(left=0.14, right=0.91, bottom=0.13, top=0.90)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, facecolor=background, edgecolor=background)
    plt.close(fig)


def main() -> None:
    root_default = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root_default)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("paper_runs/performance_analysis/textbenchmark/alpha_evolve_textbenchmark_candidate_summary.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("paper_runs/performance_analysis/figures/metric_correlation_heatmap.png"),
    )
    parser.add_argument(
        "--matrix-output",
        type=Path,
        default=Path("paper_runs/performance_analysis/figures/metric_correlation_matrix.csv"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    source = args.source if args.source.is_absolute() else root / args.source
    output = args.output if args.output.is_absolute() else root / args.output
    matrix_output = args.matrix_output if args.matrix_output.is_absolute() else root / args.matrix_output
    correlation = build_correlation(source)
    matrix_output.parent.mkdir(parents=True, exist_ok=True)
    correlation.to_csv(matrix_output, float_format="%.12f")
    render(correlation, output)
    print(matrix_output)
    print(output)


if __name__ == "__main__":
    main()
