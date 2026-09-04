# M020: MASS in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native MASS replication.

The reconstruction preserves 16 investor types, 32 agents per type, deterministic 20-stock pools, five selections, alpha=0.5 signal aggregation, and 100-step simulated-annealing distribution updates. Each investor type is represented by a distinct JKP characteristic. Annealing uses only the preceding 60 monthly type RankIC histories, and all random choices are seeded by formation month. The unavailable LLM decisions, pool draws, optimizer state, and weekly holdings are not reproduced.

At 10 bp one-way costs, the 305-month path has CAGR -6.55%, annualized Sharpe -0.440, and maximum drawdown -87.30%. Mean monthly traded notional is 3.130, and minimum signal coverage is 1000 stocks. Mean accepted annealing proposals are 87.6 of 100.

Across the 185-month rolling JKP attribution window, residual mean return is -5.41% annually (HAC t=-1.611, p=0.1072, 95% interval [-12.00%, 1.17%]).

This result answers how one transparent MASS-inspired heterogeneous-agent simulation transfers to monthly U.S. stocks. It does not reproduce or validate the paper's native decision tensor, learned distribution, or results.
