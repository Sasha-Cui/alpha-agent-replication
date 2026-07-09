# QuantAgent-HFT JKP/USA scope decision

## Decision

Blocked under the current experiment scope. I did not run QuantAgent-HFT as a valid candidate-return experiment because its native implementation requires intraday OHLCV/candlestick data and technical-indicator state that is not available from the two allowed read-only return-data locations:

- `${ALPHA_EVOLVE_JKP_ROOT}`
- `${ALPHA_EVOLVE_RETURN_DATA_ROOT}`

The repo includes benchmark CSVs for instruments such as BTC, CL, DJI, DAX, and other non-JKP/non-USA-equity data. Those files are deliberately not used for valid returns under the user's current rule.

## Evidence inspected

- `external_repos/QuantAgent/README.md` describes asset selection across stocks, crypto, commodities, and indices; timeframe selection from 1-minute to daily intervals; real-time market data through yfinance; and recent 30 candlesticks.
- `external_repos/QuantAgent/decision_agent.py` forecasts the next N candlesticks and explicitly reasons over MACD, ROC, RSI, Stochastic, Williams %R, and other short-horizon technical signals.
- `external_repos/QuantAgent/graph_util.py`, `indicator_agent.py`, `pattern_agent.py`, and `trend_agent.py` compute and analyze candlestick charts, RSI, MACD, Stochastic oscillator, pattern recognition, and trendlines.
- `external_repos/QuantAgent/web_interface.py` fetches yfinance OHLCV data and defines intraday intervals including 1m, 2m, 5m, 15m, 30m, 60m/1h, and 4h.

## Why no proxy return was constructed

The allowed JKP USA parquet has monthly security-level characteristics and monthly return fields. It can support cross-sectional monthly factor proxies, but it cannot faithfully replay QuantAgent-HFT's core idea: multi-agent interpretation of recent intraday candles, chart images, support/resistance lines, and indicator crossovers over the next few candlesticks.

Creating a monthly JKP proxy from unrelated monthly characteristics would be an invented strategy rather than a test of this paper. Under the current scope, this paper needs either a new adapter backed by allowed USA OHLCV data in the approved folders or it remains out of scope for valid FF3/FF5Mom benchmarking.
