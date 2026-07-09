# AlphaForgeBench benchmark status

Source repo: `${ALPHA_EVOLVE_REPO}/external_repos/AlphaForgeBench`

AlphaForgeBench is a public benchmark and does report Sharpe and related financial metrics. The cloned repository contains reference result JSON files under `AlphaForgeBench/benchmark_results/bench_t=0` and `bench_t=0.7`, but those files store aggregate per-model and per-level metrics rather than dated portfolio returns, weights, or a candidate return series.

The benchmark configuration uses seven assets (`BTCUSDT`, `ETHUSDT`, `AAPL`, `GOOGL`, `MSFT`, `NVDA`, `TSLA`) over 2021-01-01 to 2026-01-01. It is therefore not directly comparable to the same-universe FF3/FF5Mom factor benchmark without an additional adapter. The repository also does not include the configured `datasets/market` data directory in the clone, so the standalone re-backtest path cannot yet be run locally to produce dated return streams.

Current status: blocked for common FF3/FF5Mom benchmarking. To advance this paper, either download/build the AlphaForgeBench market dataset and run `AlphaForgeBench.run_backtest` to capture dated returns, or port the generated alpha-factor strategy code into the common monthly candidate-return contract.
