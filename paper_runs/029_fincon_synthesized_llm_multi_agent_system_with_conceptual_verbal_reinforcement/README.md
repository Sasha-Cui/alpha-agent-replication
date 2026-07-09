# FinCon / FAgent JKP/USA scope decision

## Decision

Blocked under the current experiment scope. I did not run FAgent/FinCon as a valid candidate-return experiment because the repo does not provide a reproducible candidate return stream or a faithful factor expression that can be evaluated using only the approved read-only return-data folders:

- `${ALPHA_EVOLVE_JKP_ROOT}`
- `${ALPHA_EVOLVE_RETURN_DATA_ROOT}`

## Evidence inspected

- `external_repos/FAgent/README.md` describes single-stock trading and portfolio management over user-supplied ticker symbols, with outputs saved to a local `results/` directory after running the agent.
- `external_repos/FAgent/utils/data_utils.py` loads stock prices with `yfinance.download(...)` when cache files are absent. It also generates synthetic news, SEC filing, and earnings-call data.
- `external_repos/FAgent/main.py` runs daily agent decisions over those loaded datasets and reports cumulative return and Sharpe ratio.
- `external_repos/FAgent/evaluation/metrics.py` calculates Sharpe and other metrics from strategy returns, but it does not include FF3/FF5Mom benchmark regression.
- `external_repos/FAgent/agents/manager_agent.py` makes LLM-driven BUY/SELL/HOLD decisions and uses dummy random expected returns in the portfolio optimizer.

## Why no JKP proxy was constructed

The allowed JKP USA parquet supports monthly cross-sectional factor tests. FinCon's implementation is an agent decision loop over daily prices plus multimodal text inputs. Replacing that with a monthly JKP characteristic sort would not be a test of FinCon's published idea; it would be a new strategy designed by us.

A valid run would require a new adapter that builds the market-data and auxiliary-information stream entirely from the approved folders, logs dated portfolio weights, and then feeds those generated returns to the JKP FF3/FF5Mom evaluator. That adapter is not present in the public repo.
