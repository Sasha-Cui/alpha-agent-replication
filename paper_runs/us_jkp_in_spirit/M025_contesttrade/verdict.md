# M025: ContestTrade in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native ContestTrade China A-share replication.

The reconstruction preserves two delayed-feedback Quantify-Predict-Allocate contests. The Data Contest scores 16 signed characteristics from the preceding 24 months, predicts short-run utility from recent persistence, and greedily selects up to eight positive-utility, cross-sectionally diverse factors through a facility-location objective. Five paper-motivated Research Agents blend that context with momentum, reversal, fundamental, event, or risk-control beliefs. The Research Contest uses the preceding 24 months of realized RankIC Sharpe proxies, excludes negative predictions, applies the frozen bounded judge complement, and normalizes positive weights. Mean Data Contest selection was 7.48 agents; no-positive-utility fallbacks occurred in 0 Data Contest and 8 Research Contest months.

At 10 bp one-way costs, the 305-month path has CAGR 0.17%, annualized Sharpe 0.128, and maximum drawdown -77.26%. Mean monthly traded notional is 2.183, and minimum signal coverage is 844 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -6.96% annually (HAC t=-1.658, p=0.0973, 95% interval [-15.18%, 1.27%]).

This result answers how one transparent ContestTrade-inspired dual-contest policy transfers to monthly U.S. stocks. It does not reproduce the paper's textual factors, LLM calls, LightGBM models, daily A-share execution, or native performance claims.
