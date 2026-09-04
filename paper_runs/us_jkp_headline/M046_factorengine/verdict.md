# M046: FactorEngine showcased evolved factor on monthly U.S./JKP data

Status: **completed central partial adaptation**, not the FactorEngine evolution system or headline factor pool.

The representative factor printed after 40 evolution iterations is retained with default 0.25/0.25/0.50 component weights, five-period EWM, and positive source direction. Its sole execution defect is repaired by restoring `daily_range_expr = high - low`, exactly as the seed program directly above defines it. Monthly JKP bars, the prior-close-implied open, and common value-weighted deciles are disclosed adaptations.

At 10 bp one-way costs, the 305-month path has CAGR -3.67%, annualized Sharpe -0.155, and maximum drawdown -69.57%. The 185-month JKP133 residual mean is -1.67% annually (HAC t=-0.703, p=0.4820; descriptive 69-test bound=1.0000).

This evaluates the strongest concrete evolved program, not the unreleased report corpus, LLM search, factor pool, LightGBM synthesis, native Qlib backtest, or paper metrics. Prior outcomes were known, so inference is exploratory.
