# M040: FINRS in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native FINRS replication.

The reconstruction preserves hierarchical market analysis, separate direction and quantity/risk decisions, carried position state, delayed multi-timescale reflection, scaled Kelly sizing, CVaR downside control, volatility adjustment, and an account-exposure ceiling. It first computes the frozen FinPos-inspired base position, using only 60 reward months ending six months earlier, then shrinks rather than reverses that position by the minimum of base magnitude, half Kelly times volatility adjustment, a 5% CVaR cap, and 0.75. Mean absolute exposure fell from 0.275 to 0.044; the risk layer shrank 256775 stock-months and zeroed 93887. The exact LLM analyses, native probability estimates, daily account ledger, and integer-share execution are not recreated.

At 10 bp one-way costs, the 305-month path has CAGR -0.93%, annualized Sharpe -0.042, and maximum drawdown -48.60%. Mean monthly traded notional is 0.588, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -1.31% annually (HAC t=-0.778, p=0.4363, 95% interval [-4.61%, 1.99%]).

This result answers how one transparent FINRS-inspired risk layer transfers to the common monthly U.S. universe. The paper's displayed empirical cells are overwhelmingly reused from FinPos, so they were not treated as independent FINRS evidence or replayed as formation inputs. This result does not reproduce the paper's LLM decisions, account path, daily five-stock experiment, or native claims.
