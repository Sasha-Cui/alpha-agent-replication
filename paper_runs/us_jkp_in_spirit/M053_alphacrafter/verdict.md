# M053: AlphaCrafter in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native AlphaCrafter LLM factor/trader path.

The reconstruction preserves three miner clusters, a maintained 48-factor library, purged multi-horizon validation, recent-RankIC suitability, diversity filtering, regime-aware screening, normalized directional weights, and a top-K long-short trader. Five factors are reselected monthly from at least two miners; 44 distinct candidates entered the ensemble, and regime counts were {'uptrend': 261, 'downtrend': 44}.

At 10 bp one-way costs, the 305-month path has CAGR -6.49%, annualized Sharpe -0.076, and maximum drawdown -94.41%. Mean monthly traded notional is 1.949, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -7.81% annually (HAC t=-1.909, p=0.0562, 95% interval [-15.82%, 0.21%]).

This result answers how one transparent AlphaCrafter-inspired workflow transfers to the common monthly U.S. universe. It does not reproduce paper-time LLM calls, mined factor artifacts, daily tools, trader hyperparameter trials, actions, or native claims.
