# M016: MarketSenseAI 2.0 in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native MarketSenseAI replication.

The reconstruction preserves monthly News, Fundamentals, Dynamics, and Macroeconomic specialists followed by one Buy/Hold/Sell signal agent. JKP earnings/attention, accounting, price, and formation-time market states replace unavailable text and RAG inputs. The signal agent weights specialists using only their preceding 60 RankIC observations. Continuous confidence feeds the common capitalization-weighted long/short deciles; the paper's long-only Buy subset, GPT outputs, and VectorBTPro path are not reproduced.

At 10 bp one-way costs, the 305-month path has CAGR -1.26%, annualized Sharpe 0.055, and maximum drawdown -81.53%. Mean monthly traded notional is 2.067, and minimum signal coverage is 748 stocks. Diagnostic actions total Buy=110658, Sell=104687, Hold=64397.

Across the 185-month rolling JKP attribution window, residual mean return is -3.35% annually (HAC t=-1.241, p=0.2145, 95% interval [-8.65%, 1.94%]).

This result answers how one transparent MarketSenseAI-inspired five-agent score transfers to the common task. It does not reproduce or validate its private signals, native long-only holdings, or published results.
