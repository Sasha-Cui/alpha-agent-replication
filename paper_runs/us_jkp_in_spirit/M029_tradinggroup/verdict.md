# M029: TradingGroup in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native Qwen3-Trader/TradingGroup replication.

The reconstruction preserves a five-role chain: news-sentiment, financial-report, stock-forecasting, style-preference, and final trading-decision agents. The forecasting role reflects on the preceding 60 monthly outcome-labelled RankIC records to reliability-weight sentiment, reports, and technical signals. The style role chooses aggressive, balanced, or conservative transforms from the preceding 20 months, after which the decision role applies a style-specific volatility hard intercept. Style selections were {'aggressive': 96, 'balanced': 26, 'conservative': 183}; 18755 positive stock recommendations were intercepted across all formation months. The unavailable language trajectories, PEFT checkpoint, and daily position PnL cases are not recreated.

At 10 bp one-way costs, the 305-month path has CAGR -2.18%, annualized Sharpe 0.034, and maximum drawdown -79.83%. Mean monthly traded notional is 1.937, and minimum signal coverage is 677 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -4.65% annually (HAC t=-1.946, p=0.0517, 95% interval [-9.34%, 0.03%]).

This result answers how one transparent TradingGroup-inspired reflective agent chain transfers to the common monthly U.S. universe. It does not reproduce the paper's LLM calls, synthesized chain-of-thought data, fine-tuned model, five-ticker actions, or native performance claims.
