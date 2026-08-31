# RAPTOR paper/source replication audit

This package audits the 11-page published CEUR paper, its hidden author-repository
link, the expired 4open endpoint, a high-confidence public double-blind GitHub
mirror, the author-attributed repository, all 825 tracked source objects, every
released daily portfolio snapshot, and all 42 scalar empirical result assertions
or table cells in the paper. The two repositories share 815 byte-identical files;
the result snapshots and candidate runners are identical. The full four-commit
author history is also inventoried, including the later `validation_fixes` branch.

## Honest verdict

- **End-to-end RAPTOR result cells reproduced: 0/42.**
- **Published scalar units independently verified from author-shipped output:
  18/42.**
  The released 166 daily snapshots recover the initial/final value, return,
  annualized return, volatility, Sharpe, Sortino, maximum drawdown, coverage, two
  Figure 3 extrema, and the extended-validation rolling mean/SD. This is output
  verification, not a rerun of the agent and portfolio pipeline.
- **Additional displayed scalar units independently checked from a pinned current
  public response: 3/42.**
  Yahoo's 165-session adjusted-close path from 2025-01-02 through 2025-08-29
  yields 10.08272879% for the S&P 500, which rounds
  to 10.08%; subtracting it from the released RAPTOR endpoint yields 3.35 percentage
  points. These three are not paper-time input lineage.
- **Paper-internal arithmetic or exact repetition checks:
  8/42.**
  Three Table 1 deltas equal perturbed minus base weights, and five explanation
  values exactly repeat their table cells. These are document-consistency checks,
  not author-output or native-agent results.
- Across author output, the current benchmark response, and paper-internal checks,
  29/42 units verify. Including five
  checked rolling conflicts and two underspecified longer-window claims,
  36/42 units are checked and
  6/42 remain unavailable.
- **Published raster-curve correspondences verified:
  3/3.**
  Figure 2's portfolio line regenerates all 7,313 exact blue pixels from the 166
  author snapshots. Its benchmark line regenerates all 3,132 published orange
  pixels from the pinned current Yahoo response; the regenerated image adds only
  15 orange pixels at the final segment. Across the complete 1500x600 chart,
  899,953/900,000 RGB pixels are identical. The author-executed notebook independently
  preserves both curves at display resolution and maps to the paper within two
  pixels after the documented 1.5x axes transform.
- Figure 3's released snapshot postprocessor regenerates the 20-day rolling-Sharpe
  curve with every exact-color pixel in both directions within two pixels. These
  are strong raster/output correspondences, not native-agent reruns: the paper
  publishes no raw figure arrays, the paper-time benchmark CSV remains absent,
  and exact published raw-series credit stays 0/3.
- The native snapshot visualizer executes and emits six CSV/PNG artifacts. The
  candidate backtest runner fails immediately because `testing/stock_prices.csv`
  is not released. The current public response verifies the historical benchmark
  raster and endpoint but does not supply paper-time provenance.
- The exact native `testing/mvo/metrics.py` module executes twice and deterministically
  emits 495 values across rolling Sharpe,
  Sortino, and Calmar. Its 165
  Sharpe values match the independent audit series to a maximum absolute error of
  1.78e-15. Sortino and
  Calmar have no exact published target, so this is native postprocessor evidence
  and earns no end-to-end agent or paper-result credit.
- The extended-validation rolling mean and SD are reproducible: requiring a full
  20-return window, subtracting 2%/252 daily, using sample SD, and annualizing by
  sqrt(252) gives 1.5994 and
  3.2760, which round to 1.60 and 3.28.
  All 8 standard sample/population,
  expanding/full-window, and 0%/2% risk-free conventions match 0/4 cells in the
  Section 4.3 -2.42/5.27/1.41/2.63 quartet. Across every integer longer window
  from 21 to 165, 290 of
  1160 conventions hit at least one
  rounded 1.1/1.4 endpoint and 11
  hit both, so the unspecified longer-window statement does not identify a
  reproducible protocol.

## Why the full paper is not reproduced

- The offline equity prices and paper-time SPY benchmark, Finnhub, Reddit, SimFin,
  and Perplexity snapshots are missing, as are exact API request/response logs and
  experiment seeds. The tracked dependency lock does not replace those inputs.
- The paper alternately specifies biweekly, daily/no-cadence, and every-ten-
  trading-day execution. The output-associated log instead records 17 rebalances
  beginning 2025-01-06 at a >=14-calendar-day cadence.
- The output runner uses at most 60 observations, risk aversion 5, tau .05, a
  top-50/top-10 universe, and recent-return or GPT-predicted daily views. The
  paper specifies 252 observations, risk aversion 3, tau .025, and categorical
  agent views mapped to annualized +/-2%/0.
- Transaction fees and slippage claimed in the paper are not deducted by the
  candidate execution paths. The WAB September 1 trace/table,
  full blackboard trace, Deflated Sharpe, and promised diagnostics are absent.
- The later `validation_fixes` branch adds no missing prices, benchmark input, or
  run outputs. Its generic statistics module has an `aligned_benchmarkay` NameError
  and an unseeded bootstrap; its enhancement template asserts unsupported 12.49%
  and 2020-2024 results that conflict with the final paper, so neither earns credit.
- Only January 1 has per-ticker decision files. Their headers contain 417 BUY,
  86 HOLD, and zero SELL decisions after long-only rewriting. AAPL and WAB are
  manually confirmed examples where a BUY header/final conflicts with a rationale
  recommending sale or reduced exposure.

## Files

- `source_provenance.json`, `artifact_access_audit.csv`,
  `source_search_inventory.csv`, and `fouropen_access_audit.csv`: pinned paper,
  repository, discovery, and access evidence.
- `source_file_inventory.csv` and `repository_relationship.csv`: complete
  anonymous-source inventory and anonymous/author byte relationship.
- `source_history_inventory.csv` and `validation_branch_inventory.csv`: every
  reachable author revision and the 20-file later-branch delta.
- `benchmark_snapshot_reproduction.csv`: the hash-pinned current Yahoo benchmark
  response, its 165 adjusted closes, and the explicit non-lineage boundary.
- `snapshot_metric_reproduction.csv`, `rolling_sharpe_reproduction.csv`,
  `rolling_claim_convention_forensics.csv`, `paper_internal_scalar_checks.csv`,
  and `displayed_result_conformance.csv`: output-derived calculations and the
  fail-closed 42-unit empirical denominator.
- `figure_series_conformance.csv` and `figure_raster_forensics.csv`: numeric-series
  availability and exact-color raster correspondence without raw-series inflation.
- `method_specification_audit.csv`, `paper_internal_consistency_audit.csv`, and
  `decision_trace_audit.csv`: method, paper, and released-decision boundaries.
- `native_execution.csv`, `native_execution.json`, and `manifest.json`: exact
  commands/outcomes and machine-readable verdict.
