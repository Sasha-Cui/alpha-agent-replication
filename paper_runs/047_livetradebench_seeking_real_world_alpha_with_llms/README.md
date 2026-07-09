# LiveTradeBench benchmark status

Source repo: `${ALPHA_EVOLVE_REPO}/external_repos/live-trade-bench`

LiveTradeBench is a public full-stack framework for evaluating LLM trading agents in live or replay-style market settings. The repository includes account abstractions, stock/Polymarket/BitMEX systems, data fetchers, a demo backtest script, frontend/backend code, and a small cached AAPL price JSON.

The cloned repository does not include stored model benchmark traces such as dated portfolio values, daily returns, monthly returns, or portfolio weights. The demo backtest script can write backend model data, but its summary result is a final return percentage over a chosen date interval, not a return path suitable for FF3/FF5Mom regressions. Running a faithful reproduction also requires LLM/provider calls and market/news fetches.

Current status: blocked for common FF3/FF5Mom benchmarking. To advance this paper, run the benchmark over a fixed stock universe with deterministic logging of dated portfolio values, then convert those values to monthly `candidate_returns.csv`. A single final return percentage is not enough for Sharpe, HAC alpha, or factor-spanning tests.
