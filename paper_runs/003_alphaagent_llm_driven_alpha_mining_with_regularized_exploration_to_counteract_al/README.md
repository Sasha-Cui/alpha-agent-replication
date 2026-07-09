# AlphaAgent benchmark status

Source repo: `${ALPHA_EVOLVE_REPO}/external_repos/AlphaAgent`

AlphaAgent is a real public China A-share factor-mining framework. It includes DSL evaluation code, Tushare panel-building tools, FactorZoo ingestion, LLM factor-mining scripts, and Git-tracked delivered factor expressions.

Shipped usable artifacts inspected:

- `13` DSL factor expressions under `artifacts/factorzoo/stock_1d/expressions`.
- `mining_delivered_registry.json` with ingest/IC/MLS-style metrics for delivered factors.
- `mls_fmb_percentiles.json` benchmark percentiles for factor acceptance.

What is missing for the requested benchmark: no panel parquet, no factor memmap values, no portfolio weights, no dated candidate return stream, and no Sharpe/FF3/FF5Mom comparison. The repository itself notes that the factor memmap and panel data are not part of the Git checkout and must be rebuilt or downloaded separately.

Current status: not directly benchmarkable under the common FF3/FF5Mom protocol. To advance this paper, port one or more delivered DSL factors to the same US monthly universe used by the external-factor-data factor panel, form a long-short candidate portfolio, and then run `scripts/evaluate_candidate_returns.py`.
