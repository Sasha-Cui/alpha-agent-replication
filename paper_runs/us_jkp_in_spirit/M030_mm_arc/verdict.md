# M030: MM-ARC in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native Qwen3-VL/RL-router MM-ARC replication.

The reconstruction preserves aligned numerical, chart-proxy, and deterministic technical-summary views; four trend, reversal, breakout, and exposure-control experts; bull/sideways/bear pools; five-member RABO admission; and continuous simplex capital routing. Each monthly audit uses only the preceding 120 months and the paper's exact 0.30/0.30/0.15/0.15/-0.10 ranks for benchmark exceedance, lower tail, median, stability, and turnover. Regime counts were {'bear': 25, 'bull': 217, 'sideways': 63}; sparse-regime fallback was used in 19 months. Mean router weights were {'trend': 0.2661488805209934, 'reversal': 0.2597979139394125, 'breakout': 0.19426220937810207, 'exposure_control': 0.279790996161492}. Missing trained adapters, strategy tables, and actor-critic weights are not reconstructed.

At 10 bp one-way costs, the 305-month path has CAGR 3.60%, annualized Sharpe 0.266, and maximum drawdown -56.43%. Mean monthly traded notional is 2.106, and minimum signal coverage is 866 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -0.42% annually (HAC t=-0.124, p=0.9014, 95% interval [-7.14%, 6.29%]).

This result answers how one transparent MM-ARC-inspired robustness-audited capital router transfers to the common monthly U.S. universe. It does not reproduce the paper's model states, 60 native pools, 62-instrument execution, or published holdout claims.
