# M013: FinVision in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native FinVision replication.

The reconstruction preserves distinct news-summary, technical-chart, short-reflection, and medium-reflection agents followed by a reliability-weighted prediction agent. Numeric earnings/attention and price characteristics replace unavailable news and images; trailing security outcomes replace reflection text. Agent reliabilities use only the preceding 60 RankIC observations. Buy/Sell/Hold and 1-10 confidence sizing are retained as diagnostics, while continuous consensus feeds the common portfolio. The unavailable LangGraph runtime and GPT/o1 responses are not reproduced.

At 10 bp one-way costs, the 305-month path has CAGR -0.65%, annualized Sharpe 0.123, and maximum drawdown -87.55%. Mean monthly traded notional is 2.103, and minimum signal coverage is 923 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is 1.48% annually (HAC t=0.543, p=0.5870, 95% interval [-3.86%, 6.82%]).

This result answers how one transparent FinVision-inspired multi-agent consensus transfers to the common task. It does not reproduce or validate the paper's actions, position trajectory, explanations, or native results.
