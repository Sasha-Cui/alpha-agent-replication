# M060: MetaPS in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native MetaPS Qwen router or action path.

The reconstruction preserves ten named strategy programs, ranked candidate context, counterfactual V1/V2 rollouts, V3 return-aware label balancing, strategy-level routing, and coarse exposure buckets. The rolling ridge router selected strategies with counts {'macro_rotation': 72, 'mean_revert_fade': 47, 'momentum_follow': 46, 'risk_reset': 43, 'cross_asset_hedge': 39, 'small_cap_breakout': 30, 'news_impulse': 11, 'liquidity_rebate': 11, 'earnings_drift': 4, 'volatility_breakout': 2}, exposure counts {'small': 267, 'medium': 35, 'large': 3}, mean confidence 0.142, mean top-two margin 0.023, and a 21.3% match to the current lightweight relevance leader. Every decision used 120 fully realized historical labels with a six-month purge. No current forward return or final common result selected the router action.

At 10 bp one-way costs, the 305-month path has CAGR -5.02%, annualized Sharpe -0.055, and maximum drawdown -91.38%. Mean monthly traded notional is 2.630, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -6.40% annually (HAC t=-1.219, p=0.2227, 95% interval [-16.70%, 3.89%]).

This result answers how one transparent MetaPS-inspired V3 strategy router transfers to the common monthly U.S. universe. It does not reproduce the six-asset daily state, native strategy helpers, simulator rewards, teacher rationales, Qwen fine-tuning, checkpoint, single-ticker actions, fills, or paper empirical claims.
