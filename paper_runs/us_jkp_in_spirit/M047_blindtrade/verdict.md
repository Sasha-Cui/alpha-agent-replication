# M047: BlindTrade in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native Gemini/SemGAT/PPO-DSR BlindTrade system.

The reconstruction preserves identity-blind inputs; Momentum, News-Event, Mean-Reversion, and Risk-Regime roles; causal IC validation; a two-layer similarity graph; defensive, neutral, and aggressive intents; trailing risk-adjusted market feedback; 10 bp turnover cost; and 0.10 execution inertia. Deterministic JKP role scores replace unreleased LLM outputs, their four-score vector replaces reasoning embeddings, cosine-neighbor averaging replaces learned GATv2, and the best trailing 60-month net Sharpe among three fixed intent sleeves replaces PPO-DSR. Intent counts were {'defensive': 163, 'neutral': 33, 'aggressive': 109}; mean semantic neighbors per stock were 10.00; mean absolute score moved from 0.375 before inertia to 0.268 after inertia.

At 10 bp one-way costs, the 305-month path has CAGR -8.03%, annualized Sharpe -0.174, and maximum drawdown -88.07%. Mean monthly traded notional is 0.811, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -0.77% annually (HAC t=-0.257, p=0.7969, 95% interval [-6.64%, 5.10%]).

This result answers how one transparent BlindTrade-inspired graph-intent policy transfers to the common monthly U.S. universe. It does not reproduce Gemini calls, anonymized headlines, MiniLM reasoning, sectors, learned SemGAT or PPO-DSR weights, the equity-only Dirichlet Top-20 allocation, daily S&P 500 membership, or the paper's native claims. No paper holdout selections or return curves were used as formation inputs.
