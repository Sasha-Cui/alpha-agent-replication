# AlphaAgent legacy common-task status

The authoritative paper-level audit is
`paper_runs/paper_replication_audits/alphaagent/README.md`. It pins arXiv v2 and
official source commit `b42cb397025510da44355db9dcf278304321f589`, enumerates
all 100 Table 2 result cells plus the paper's non-table quantitative claims, and
recovers seven preprint-era Qlib/MLflow run records. One native S&P500 record
corroborates all five AlphaAgent cells at display precision; zero cells are
independently regenerated because its inputs, predictions, returns, and holdings
are absent. The audit also records why the July 2026 source/data release is not
the June 2025 experiment.

Source repo: `${ALPHA_EVOLVE_REPO}/external_repos/AlphaAgent`

AlphaAgent is a real public China A-share factor-mining framework. It includes DSL evaluation code, Tushare panel-building tools, FactorZoo ingestion, LLM factor-mining scripts, and Git-tracked delivered factor expressions.

Shipped usable artifacts inspected:

- `13` DSL factor expressions under `artifacts/factorzoo/stock_1d/expressions`.
- `mining_delivered_registry.json` with ingest/IC/MLS-style metrics for delivered factors.
- `mls_fmb_percentiles.json` benchmark percentiles for factor acceptance.

What is missing for the requested benchmark: no panel parquet, no factor memmap values, no portfolio weights, no dated candidate return stream, and no Sharpe/FF3/FF5Mom comparison. The repository itself notes that the factor memmap and panel data are not part of the Git checkout and must be rebuilt or downloaded separately. Its externally linked 2026 CSI1000/Tushare package is available, but it is not the paper's CSI500/Baostock and S&P500/Yahoo input.

Current status: not directly benchmarkable under the common FF3/FF5Mom protocol,
and not an end-to-end paper replication. Five paper cells have native author-output
corroboration, while any port of the delivered DSL factors is explicitly a
post-paper, in-spirit proxy and receives no native-paper credit.
