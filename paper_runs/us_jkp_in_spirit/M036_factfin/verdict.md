# M036: FactFin in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native GPT-4o FactFin replication.

The reconstruction preserves explicit price/factor/factorized-news state, executable three-weight buy/hold/sell code, depth-10 UCB search with c=0.5, and a 50-scenario counterfactual audit. One hundred MCTS evaluations use only 96 pre-common training months. The ten strongest distinct programs then face 24 pre-common validation months and within-month state permutations scored by prediction consistency, confidence invariance, and input-dependency KL. The selected price/factor/news weights are [0.140740740741, 0.74074074074, 0.118518518519], with training RankIC 0.0219, validation RankIC 0.0237, PC 0.711, CI 0.819, and IDS 0.281. Missing prompts, runtime, evolved author code, and native counterfactuals are not recreated.

At 10 bp one-way costs, the 305-month path has CAGR 4.44%, annualized Sharpe 0.350, and maximum drawdown -39.26%. Mean monthly traded notional is 1.193, and minimum signal coverage is 720 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -0.32% annually (HAC t=-0.180, p=0.8572, 95% interval [-3.77%, 3.14%]).

This result answers how one transparent FactFin-inspired leakage-safe evolved program transfers to the common monthly U.S. universe. It does not reproduce FinLeak-Bench, the paper's GPT-4o code, native MCTS trajectory, six-asset execution, or reported performance claims.
