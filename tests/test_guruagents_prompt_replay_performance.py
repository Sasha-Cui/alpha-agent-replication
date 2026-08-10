from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/evaluate_guruagents_prompt_replay_performance.py"
SPEC = importlib.util.spec_from_file_location("guru_performance", SCRIPT)
assert SPEC and SPEC.loader
guru = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = guru
SPEC.loader.exec_module(guru)


def formation(end: str, weights: dict[str, float], candidate_id: str = "replay__a__m__graham"):
    return guru.Formation(
        candidate_id=candidate_id,
        series_type="replay",
        archive="a",
        agent="graham",
        mode="m",
        formation_end=pd.Timestamp(end),
        target_weights=weights,
        raw_weight_sum=100.0,
        table_weight_sum=100.0,
        parsed_rows=len(weights),
        selected_table_index=0,
        selected_table_count=1,
        corrected_tickers="",
        dropped_labels="",
        dropped_unknown_tickers="",
        source_path="test",
        experiment_id="test",
    )


def test_select_portfolio_table_prefers_allocation_closest_to_100() -> None:
    text = """
| Ticker | Score | Weight (%) | Reason |
|---|---:|---:|---|
| AAA | 1 | 50 | diagnostic |
| BBB | 1 | 50 | diagnostic |

| Ticker | Score | Weight (%) | Reason |
|---|---:|---:|---|
| AAA | 1 | 3 | long table |
| BBB | 1 | 3 | long table |
| CCC | 1 | 3 | long table |
"""
    rows, meta = guru.select_portfolio_table(text)
    assert [row["Ticker"] for row in rows] == ["AAA", "BBB"]
    assert meta["selected_table_index"] == 0
    assert meta["selected_table_weight_sum"] == 100.0


def test_clean_portfolio_corrects_known_source_typos_and_normalizes() -> None:
    rows = [
        {"Ticker": "CPTR", "Weight (%)": 30},
        {"Ticker": "CHRT", "Weight (%)": 30},
        {"Ticker": "INTEL", "Weight (%)": 30},
        {"Ticker": "REMAINING", "Weight (%)": 10},
    ]
    weights, audit = guru.clean_portfolio_rows(rows, {"CPRT", "CHTR", "INTC"})
    assert set(weights) == {"CPRT", "CHTR", "INTC"}
    assert np.isclose(sum(weights.values()), 1.0)
    assert np.isclose(weights["CPRT"], 1 / 3)
    assert "CPTR->CPRT" in audit["corrected_tickers"]
    assert audit["dropped_labels"] == "REMAINING:10"


def test_backtest_uses_first_postformation_close_and_charges_traded_notional() -> None:
    index = pd.to_datetime(["2022-04-01", "2022-04-29", "2022-05-31", "2022-06-30", "2022-07-01"])
    prices = pd.DataFrame(
        {
            "AAA": [100.0, 110.0, 121.0, 121.0, 121.0],
            "BBB": [100.0, 100.0, 100.0, 100.0, 100.0],
        },
        index=index,
    )
    monthly, _, turnover = guru.backtest_candidate(
        [formation("2022-03-31", {"AAA": 1.0})], prices, cost_bps=10.0
    )
    april = monthly.loc[monthly["realization_month"].eq(pd.Timestamp("2022-04-30"))].iloc[0]
    assert np.isclose(april["gross_return"], 0.10)
    assert np.isclose(april["net_10bp_return"], 0.10 - 0.0011)
    assert np.isclose(april["traded_notional"], 1.0)
    assert bool(april["analysis_eligible"])
    assert np.isclose(turnover.iloc[0]["traded_notional"], 1.0)


def test_full_switch_has_two_units_of_traded_notional() -> None:
    index = pd.to_datetime(
        ["2022-04-01", "2022-04-29", "2022-05-31", "2022-06-30", "2022-07-01", "2022-07-29"]
    )
    prices = pd.DataFrame({"AAA": 100.0, "BBB": 100.0}, index=index)
    _, _, turnover = guru.backtest_candidate(
        [
            formation("2022-03-31", {"AAA": 1.0}),
            formation("2022-06-30", {"BBB": 1.0}),
        ],
        prices,
        cost_bps=10.0,
    )
    assert np.allclose(turnover["traded_notional"].to_numpy(), [1.0, 2.0])


def test_ols_reports_unidentified_when_parameters_exceed_sample() -> None:
    frame = pd.DataFrame(
        {
            "month": pd.date_range("2020-01-31", periods=12, freq="ME"),
            "y": np.linspace(0.0, 0.1, 12),
            **{f"f{i}": np.linspace(0.0, 0.1, 12) for i in range(10)},
        }
    )
    result, residuals, loadings = guru.ols_alpha(
        frame, "candidate", "too_many", [f"f{i}" for i in range(10)]
    )
    assert result["status"] == "unidentified_or_insufficient_degrees_of_freedom"
    assert residuals.empty
    assert loadings.empty


def test_nested_lomo_ridge_publishes_monthly_penalties_and_loadings() -> None:
    rng = np.random.default_rng(7)
    n = 12
    factors = rng.normal(0, 0.02, size=(n, 4))
    y = 0.002 + factors @ np.array([0.3, -0.1, 0.2, 0.0]) + rng.normal(0, 0.005, n)
    frame = pd.DataFrame(factors, columns=["f1", "f2", "f3", "f4"])
    frame.insert(0, "y", y)
    frame.insert(0, "month", pd.date_range("2022-01-31", periods=n, freq="ME"))
    result, residuals, loadings = guru.nested_lomo_ridge(
        frame,
        "candidate",
        ["f1", "f2", "f3", "f4"],
        pd.Series(1.0, index=["f1", "f2", "f3", "f4"]),
    )
    assert result["status"].startswith("exploratory")
    assert len(residuals) == n
    assert len(loadings) == n * 4
    assert residuals["selected_ridge_penalty"].isin(guru.RIDGE_GRID).all()


def test_common_sample_metrics_handles_same_return_column_name() -> None:
    months = pd.date_range("2022-04-30", periods=3, freq="ME")
    left = pd.DataFrame({"realization_month": months, "net_10bp_return": [0.01, 0.02, -0.01]})
    right = pd.DataFrame({"realization_month": months, "net_10bp_return": [0.00, 0.01, 0.01]})
    risk_free = pd.DataFrame({"month": months, "RF": 0.001})
    result = guru.common_sample_metrics(
        left, right, "net_10bp_return", "net_10bp_return", risk_free, False
    )
    assert result["common_months"] == 3
    assert np.isfinite(result["delta_annualized_return"])


def test_official_ff_columns_are_restricted_to_jkp_overlap() -> None:
    months = pd.to_datetime(["2024-12-31", "2025-01-31"])
    candidates = pd.DataFrame(
        {
            "candidate_id": "replay__a__m__graham",
            "series_type": "replay",
            "archive": "a",
            "agent": "graham",
            "mode": "m",
            "realization_month": months,
            "analysis_eligible": True,
            "gross_return": [0.02, 0.03],
            "net_10bp_return": [0.019, 0.029],
        }
    )
    factor_realization = pd.DataFrame(
        {"month": [months[0]], "capm_top1000_mkt": [0.01], guru.JKP_BAB_FACTOR: [0.002]}
    )
    nasdaq = pd.DataFrame(
        {"month": months, "nasdaq100_source_universe_market": [0.015, 0.025]}
    )
    ff = pd.DataFrame(
        {
            "month": months,
            "RF": [0.001, 0.001],
            **{factor: [0.01, 0.02] for factor in guru.OFFICIAL_FF_FACTOR_COLUMNS},
        }
    )
    pca = pd.DataFrame({"month": months})
    frame = guru.candidate_regression_frame(candidates, factor_realization, nasdaq, ff, pca)
    assert np.isclose(frame.loc[0, "Mkt-RF"], 0.01)
    assert np.isnan(frame.loc[1, "Mkt-RF"])
    assert np.allclose(frame["y"], [0.018, 0.028])


def test_replay_attribution_summary_keeps_signed_significance() -> None:
    rows = []
    for benchmark in guru.ATTRIBUTION_BENCHMARK_ORDER:
        rows.extend(
            [
                {
                    "candidate_id": "positive",
                    "series_type": "replay",
                    "benchmark": benchmark,
                    "status": "identified_ols",
                    "sample_start": pd.Timestamp("2022-04-30"),
                    "sample_end": pd.Timestamp("2024-12-31"),
                    "n_months": 33,
                    "alpha_annualized": 0.12,
                    "alpha_pvalue": 0.01,
                    "alpha_pvalue_holm_replay_family": 0.04,
                },
                {
                    "candidate_id": "negative",
                    "series_type": "replay",
                    "benchmark": benchmark,
                    "status": "identified_ols",
                    "sample_start": pd.Timestamp("2022-04-30"),
                    "sample_end": pd.Timestamp("2024-12-31"),
                    "n_months": 33,
                    "alpha_annualized": -0.06,
                    "alpha_pvalue": 0.02,
                    "alpha_pvalue_holm_replay_family": 0.08,
                },
            ]
        )
    summary, by_candidate = guru.build_replay_attribution_outputs(pd.DataFrame(rows))
    assert (summary["nominal_positive_count"] == 1).all()
    assert (summary["nominal_negative_count"] == 1).all()
    assert (summary["holm_positive_count"] == 1).all()
    assert len(by_candidate) == 2 * len(guru.ATTRIBUTION_BENCHMARK_ORDER)


def test_manifest_locator_is_portable(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    in_repo = repo_root / "data" / "panel.csv"
    in_repo.parent.mkdir()
    in_repo.write_text("x\n", encoding="utf-8")
    external = tmp_path / "licensed" / "source.csv"
    external.parent.mkdir()
    external.write_text("x\n", encoding="utf-8")

    assert guru.manifest_locator(in_repo, repo_root) == {
        "path": "data/panel.csv",
        "path_scope": "repository_relative",
    }
    assert guru.manifest_locator(external, repo_root) == {
        "path": "source.csv",
        "path_scope": "external_authorized_input",
    }


def test_portable_source_locator_removes_host_paths(tmp_path: Path) -> None:
    run_root = tmp_path / "runs" / "replay-1"
    source_root = tmp_path / "licensed-source"
    run_output = run_root / "results" / "final_output.md"
    source_file = source_root / "results" / "portfolio.csv"

    roots = (("replay_run", run_root), ("guruagents_source", source_root))
    assert guru.portable_source_locator(str(run_output), roots) == (
        "replay_run://results/final_output.md"
    )
    assert guru.portable_source_locator(str(source_file), roots) == (
        "guruagents_source://results/portfolio.csv"
    )
    assert guru.portable_source_locator("derived equal-weight portfolio", roots) == (
        "derived equal-weight portfolio"
    )
