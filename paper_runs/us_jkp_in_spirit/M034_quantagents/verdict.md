# M034: QuantAgents in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native GPT-4o QuantAgents replication.

The reconstruction preserves Otto, Bob, Dave, and Emily; market-analysis and strategy-development meetings; three memory types; ten similar-case retrievals; a ten-member strategy pool; simulated strategy testing; adaptive simulated/real reward blending; and the paper's 0.75 risk-alert trigger. Each month Bob proposes three strategies from past similar-state RankIC utility, Otto blends them with the previously deployed set and Emily's report, and Dave contributes a defensive policy when the equal-weight risk score triggers. Mean simulated-reward weight was 0.418; risk meetings triggered in 57 of 305 months. Strategy proposal counts were {'momentum_short': 75, 'momentum_medium': 52, 'momentum_long': 65, 'breakout': 64, 'reversal': 76, 'value_quality': 193, 'sentiment_surprise': 76, 'low_risk': 57, 'financial_safety': 119, 'balanced_multi_factor': 138}. Missing LLM meetings, tools, raw memories, strategy traces, and learned policy parameters are not recreated.

At 10 bp one-way costs, the 305-month path has CAGR 0.64%, annualized Sharpe 0.132, and maximum drawdown -53.83%. Mean monthly traded notional is 2.208, and minimum signal coverage is 645 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -5.97% annually (HAC t=-1.559, p=0.1189, 95% interval [-13.47%, 1.53%]).

This result answers how one transparent QuantAgents-inspired meeting and dual-reward policy transfers to the common monthly U.S. universe. It does not reproduce the paper's weekly prompts, NASDAQ-100 histories, GPT-4o calls, action parser, or native performance claims.
