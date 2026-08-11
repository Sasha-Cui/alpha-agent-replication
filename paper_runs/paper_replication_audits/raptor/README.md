# RAPTOR paper/source replication audit

This package audits the 11-page published CEUR paper, its hidden author-repository
link, the expired 4open endpoint, a high-confidence public double-blind GitHub
mirror, the author-attributed repository, all 825 tracked source objects, every
released daily portfolio snapshot, and all 42 scalar empirical result assertions
or table cells in the paper. The two repositories share 815 byte-identical files;
the result snapshots and candidate runners are identical.

## Honest verdict

- **End-to-end RAPTOR result cells reproduced: 0/42.**
- **Published scalar units independently verified from author-shipped output:
  16/42.**
  The released 166 daily snapshots recover the initial/final value, return,
  annualized return, volatility, Sharpe, Sortino, maximum drawdown, coverage, and
  two Figure 3 extrema. This is output verification, not a rerun of the agent and
  portfolio pipeline.
- The native snapshot visualizer executes and emits six CSV/PNG artifacts. The
  candidate backtest runner fails immediately because `testing/stock_prices.csv`
  is not released. The S&P 500 series is also absent, so Figure 2 cannot be
  regenerated in full.
- The paper's 20-day Sharpe descriptions conflict. Released sample-SD code gives
  min -5.2675, max 10.3435,
  mean 2.1509, and final
  3.7899. Population SD gives the reported final
  3.89 but not the reported extrema; no single disclosed convention yields all
  caption values.

## Why the full paper is not reproduced

- The offline price, SPY benchmark, Finnhub, Reddit, SimFin, and Perplexity
  snapshots are missing, as are exact API request/response logs and experiment
  seeds. The tracked dependency lock does not replace those inputs.
- The paper alternately specifies biweekly, daily/no-cadence, and every-ten-
  trading-day execution. The output-associated log instead records 17 rebalances
  beginning 2025-01-06 at a >=14-calendar-day cadence.
- The output runner uses at most 60 observations, risk aversion 5, tau .05, a
  top-50/top-10 universe, and recent-return or GPT-predicted daily views. The
  paper specifies 252 observations, risk aversion 3, tau .025, and categorical
  agent views mapped to annualized +/-2%/0.
- Transaction fees and slippage claimed in the paper are not deducted by the
  candidate execution paths. The WAB September 1 trace/table, benchmark values,
  full blackboard trace, Deflated Sharpe, and promised diagnostics are absent.
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
- `snapshot_metric_reproduction.csv`, `rolling_sharpe_reproduction.csv`, and
  `displayed_result_conformance.csv`: output-derived calculations and the
  fail-closed 42-unit empirical denominator.
- `figure_series_conformance.csv`, `method_specification_audit.csv`,
  `paper_internal_consistency_audit.csv`, and `decision_trace_audit.csv`: series,
  method, paper, and released-decision boundaries.
- `native_execution.csv`, `native_execution.json`, and `manifest.json`: exact
  commands/outcomes and machine-readable verdict.
