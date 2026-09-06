# M057: MadEvolve in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native MadEvolve BTCUSD program or execution path.

The reconstruction preserves Run 5's joint feature-and-strategy search, training-only term fitting, validation-return fitness, five MAP-Elites islands, a global elite vault, 70/30 patch-rewrite mutation, and ring migration every five generations. Across 13 blocks it evaluated 1950 proposals (1379 patches and 571 rewrites), found 602 parent improvements, executed 195 migration transfers, and froze 13 distinct programs with wrapper counts {'quality_confirm': 5, 'defensive_regime_switch': 4, 'identity': 3, 'risk_dampen': 1}. Test returns never selected a program, and no common-result retuning occurred.

At 10 bp one-way costs, the 305-month path has CAGR 6.05%, annualized Sharpe 0.402, and maximum drawdown -50.48%. Mean monthly traded notional is 1.982, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is 5.49% annually (HAC t=1.390, p=0.1647, 95% interval [-2.25%, 13.22%]).

This result answers how one transparent MadEvolve-inspired joint program search transfers to the common monthly U.S. universe. It does not reproduce the paper's BTCUSD data, frontier-LLM mutations, best evolved source code, limit orders, fills, nonlinear impact, candidate lineage, or native empirical claims.
