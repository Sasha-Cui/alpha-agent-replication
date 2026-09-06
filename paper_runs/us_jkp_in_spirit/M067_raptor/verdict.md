# M067: RAPTOR in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native RAPTOR multimodal LLM runtime or reported 2025 portfolio.

The reconstruction preserves six analyst threads, bull/bear synthesis, research management, three risk stances, a final risk judgment, synchronized categorical views, and the released Black-Litterman constants. Across 305 monthly cross sections the final judge produced {'BUY': 86532, 'HOLD': 131550, 'SELL': 86918}; every view used only contemporaneous JKP characteristics and lagged return variance.

At 10 bp one-way costs, the 305-month common path has CAGR 2.10%, annualized Sharpe 0.209, and maximum drawdown -43.39%. Mean monthly traded notional is 1.107, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -2.15% annually (HAC t=-1.540, p=0.1237, 95% interval [-4.89%, 0.59%]).

This result answers how one transparent RAPTOR-inspired hierarchy and allocator transfers to the common monthly U.S. universe. It does not reproduce Finnhub, SimFin, Reddit, Perplexity, LLM prompts/messages, unreleased request logs, full daily covariance, native holdings, or the paper's empirical claims. The 166 released snapshots provide historical-output evidence only; none supplies the missing causal cross-sectional formation lineage.
