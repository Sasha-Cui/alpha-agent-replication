# M056: QuantEvolver first released seed on monthly U.S./JKP data

Status: **completed partial monthly U.S./JKP evaluation**, not the reinforcement-fine-tuned QuantEvolver miner.

The source-first valid example seed `return_sharpe_60` is evaluated with its complete DSL tree `div(ts_mean(returns(60)), ts_std(returns(60)))`. Close-derived simple returns, the 60-return mean/volatility ratio, positive direction, and released epsilon semantics are preserved. Each source bar becomes one month; the common largest-1,000 U.S. universe and value-weighted long/short deciles replace the example symbols and the evaluator's equal-mean quintile diagnostic. This source-order choice was fixed before the new common run, but earlier QuantEvolver proxy/component outcomes were already observed, so the result is exploratory.

At 10 bp one-way costs, the 305-month path has CAGR -0.80%, annualized Sharpe 0.056, and maximum drawdown -73.79%. Mean monthly traded notional is 0.778, implying 0.93% annualized linear fee drag. The minimum formation-month signal coverage is 653 stocks.

Across the 185-month rolling attribution window, the JKP133 residual mean is -0.70% annually (HAC t=-0.227, p=0.8205, 95% interval [-6.74%, 5.34%]; descriptive 69-test bound=1.0000).

This is performance of one author-released seed after a material monthly adapter. It does not reproduce the RFT policy, trained checkpoint, seed/task bank, generated factor search, diversity shaping, mined library, fusion, native benchmarks, or any paper result. A negative or insignificant result therefore bears only on this disclosed component transfer, not on the paper's withheld headline system.
