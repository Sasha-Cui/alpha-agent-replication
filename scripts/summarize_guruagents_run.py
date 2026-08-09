#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    root = Path("paper_runs/042_guruagents")
    frames = []
    for path in sorted(root.glob("results*/ff_official_benchmark_metrics.csv")):
        frame = pd.read_csv(path)
        frame.insert(0, "result_dir", str(path.parent))
        frames.append(frame)
    if not frames:
        raise SystemExit("No GuruAgents metrics files found")
    summary = pd.concat(frames, ignore_index=True)
    cols = [
        "candidate_id",
        "benchmark_set",
        "n_overlap_months",
        "overlap_start",
        "overlap_end",
        "candidate_standalone_oos_sharpe_excess",
        "alpha_annualized",
        "alpha_tstat_hac",
        "appraisal_ratio",
        "combined_minus_old_sharpe",
        "r_squared",
    ]
    summary[cols].to_csv(root / "guruagents_ff_summary.csv", index=False)
    ff5 = summary[summary["benchmark_set"] == "FF5MOM_OFFICIAL"].copy()
    best = ff5.sort_values("alpha_tstat_hac", ascending=False).iloc[0]
    equal_weight = ff5[ff5["candidate_id"].str.contains("equal_weight")].iloc[0]
    verdict = """# GuruAgents FF3 / FF5Mom benchmark verdict

Status: completed provisional benchmark pass.

Candidate construction:

- Source workbook: external_repos/GuruAgents/results_22_24/multi_agent_backtest_results.xlsx.
- Paper-level candidate: equal-weight average of the five shipped daily agent return streams, compounded to monthly returns.
- Additional diagnostics: each individual guru-agent sleeve was also benchmarked.
- Factor source: official Kenneth French monthly FF3, FF5, and momentum factors via pandas_datareader, not the external factor-data project same-universe factor panel. This was necessary because the shipped GuruAgents returns run from 2022-04 through 2025-03, while the external factor panel ends in 2021-12.

Paper-level equal-weight result:

- Months: {eq_months}, {eq_start} to {eq_end}.
- Excess Sharpe after 7 pct vol scaling: {eq_sharpe:.3f}.
- FF5+Mom annualized alpha: {eq_alpha:.3%}.
- FF5+Mom HAC alpha t-stat: {eq_tstat:.3f}.
- FF5+Mom appraisal ratio: {eq_appraisal:.3f}.

Best individual sleeve:

- Candidate: {best_candidate}.
- FF5+Mom annualized alpha: {best_alpha:.3%}.
- FF5+Mom HAC alpha t-stat: {best_tstat:.3f}.
- FF5+Mom appraisal ratio: {best_appraisal:.3f}.

Verdict:

GuruAgents contains something potentially relevant, but only provisionally. The paper-level equal-weight candidate is positive after FF5+Mom controls but does not clear a t-stat above 2. The Warren Buffett sleeve does clear that threshold on the shipped 36-month sample. This is not enough to call the paper serious under the original strict standard because the sample is short, the candidate returns are post-2021, and the run uses official FF factors rather than the external same-universe benchmark span. It is worth a second pass using reconstructed holdings on a longer point-in-time universe.
""".format(
        eq_months=int(equal_weight["n_overlap_months"]),
        eq_start=equal_weight["overlap_start"],
        eq_end=equal_weight["overlap_end"],
        eq_sharpe=float(equal_weight["candidate_standalone_oos_sharpe_excess"]),
        eq_alpha=float(equal_weight["alpha_annualized"]),
        eq_tstat=float(equal_weight["alpha_tstat_hac"]),
        eq_appraisal=float(equal_weight["appraisal_ratio"]),
        best_candidate=best["candidate_id"],
        best_alpha=float(best["alpha_annualized"]),
        best_tstat=float(best["alpha_tstat_hac"]),
        best_appraisal=float(best["appraisal_ratio"]),
    )
    (root / "verdict.md").write_text(verdict, encoding="utf-8")
    print(summary[cols].to_string(index=False))


if __name__ == "__main__":
    main()
