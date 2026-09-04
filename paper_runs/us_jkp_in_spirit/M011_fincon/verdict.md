# M011: FinCon in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native FinCon replication.

The reconstruction preserves a manager synthesizing market, fundamental, attention, and risk analysts; procedural memory of analyst effectiveness; episodic belief updates; selective propagation through changing weights; and downside-tail risk control. Each month, trailing RankIC updates numerical beliefs and each stock's past 60 returns determine a 5% monthly CVaR safety rank. JKP characteristics replace unavailable news, filings, audio, and analyst text; softmax belief updates replace CVRF prompt editing; and common deciles replace the underspecified native optimizer.

At 10 bp one-way costs, the 305-month path has CAGR 2.59%, annualized Sharpe 0.230, and maximum drawdown -64.66%. Mean monthly traded notional is 1.248, and minimum signal coverage is 534 stocks. Final numerical beliefs are market=0.250, fundamental=0.253, attention=0.242, risk=0.255.

Across the 185-month rolling JKP attribution window, residual mean return is 0.32% annually (HAC t=0.140, p=0.8889, 95% interval [-4.15%, 4.79%]).

This result answers how one transparent FinCon-inspired hierarchy and dual-risk-control policy transfers to the common task. It does not reproduce or validate FinCon's private manager/analyst trajectories, CVRF text, native portfolios, or paper results.
