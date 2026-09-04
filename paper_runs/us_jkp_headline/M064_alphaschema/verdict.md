# M064: AlphaSchema example factor on monthly U.S./JKP data

Status: **completed partial monthly U.S./JKP evaluation**, not the AlphaSchema search or pooled strategy.

The complete appendix factor `effort_result_reference_cooldown_memory` is evaluated at its source-selected period 20 and positive Rank-IC direction. It preserves price-volume synergy, same-date cross-sectional normalization, moving-average reference distance, event cooldown, direction, and EWMA memory. One source day becomes one month; the common U.S. top-1,000 and value-weighted deciles replace CSI300 and the unreleased pool/LightGBM/Top-50-drop-5 path. Prior outcomes were seen, so inference is exploratory.

At 10 bp one-way costs, the 305-month path has CAGR 0.70%, annualized Sharpe 0.127, and maximum drawdown -62.63%. Mean monthly traded notional is 1.169; minimum signal coverage is 1000 stocks.

Across the 185-month rolling attribution window, the JKP133 residual mean is 1.88% annually (HAC t=0.627, p=0.5305, 95% interval [-3.99%, 7.75%]; descriptive 69-test bound=1.0000).

This result applies only to one materially cadence-adapted paper factor. It does not reproduce semantic search, LLM realization/repair, reward navigation, production pools, LightGBM combination, Qlib execution, or paper performance.
