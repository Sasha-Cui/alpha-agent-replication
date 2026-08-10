from pathlib import Path

import pytest

from scripts.build_metric_correlation_heatmap import SENTINELS, build_correlation


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper_runs/performance_analysis/textbenchmark/alpha_evolve_textbenchmark_candidate_summary.csv"


def test_metric_correlation_contract() -> None:
    correlation = build_correlation(SOURCE)
    assert correlation.shape == (14, 14)
    for (row, column), expected in SENTINELS.items():
        assert correlation.loc[row, column] == pytest.approx(expected, abs=0.005)
