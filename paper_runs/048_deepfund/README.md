# DeepFund benchmark status

Source repo: `${ALPHA_EVOLVE_REPO}/external_repos/DeepFund`

DeepFund is a public multi-agent fund framework with portfolio and decision tables. The repository includes an example SQLite database at `src/example/deepfund.db`, so I inspected it as a possible source for a candidate return stream.

The example database is not a usable performance history. It has 45 portfolio rows across several experiment configs, but the longest config has only three distinct trading dates in April 2025 and `total_assets` stays fixed at 100,000. Other configs have one or two dates, also with no meaningful asset-value path. This cannot support monthly Sharpe, HAC alpha, or FF3/FF5Mom spanning tests.

Current status: blocked for common FF3/FF5Mom benchmarking. To advance this paper, run the framework chronologically over a fixed historical stock universe, persist daily portfolio total assets or weights, then convert the resulting path to monthly `candidate_returns.csv`.
