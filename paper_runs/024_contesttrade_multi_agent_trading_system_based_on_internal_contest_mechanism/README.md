# ContestTrade benchmark status

Source repo: `${ALPHA_EVOLVE_REPO}/external_repos/ContestTrade`

ContestTrade has a public codebase and describes an internal contest mechanism for selecting among LLM trading agents. The cloned repository is an interactive research/trading framework with market data connectors, LLM calls, prompts, reports, and screenshots. It does not ship a reproducible portfolio return stream, generated signal panel, or backtest output that can be directly converted to the common monthly `candidate_returns.csv` contract.

Current status: blocked for FF3/FF5Mom benchmarking until an adapter can replay its decisions over a fixed historical universe. A usable adapter should either:

1. run the framework over a fixed US stock universe and persist dated portfolio weights or daily returns, or
2. extract already generated files from `contest_trade/agents_workspace/results` if a full paper reproduction run is available.

Required output for the common evaluator:

```csv
month,candidate_return
2022-01-31,0.0123
```

Because no shipped return stream exists, no Sharpe or FF benchmark metrics were recomputed for this paper yet. Its paper-reported Sharpe remains unverified under the common benchmark protocol.
