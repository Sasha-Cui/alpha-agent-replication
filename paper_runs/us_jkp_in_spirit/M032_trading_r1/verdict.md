# M032: Trading-R1 in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native Qwen3-4B Trading-R1 replication.

The reconstruction preserves structured technical/fundamental/sentiment thesis sections, an eight-dimensional evidence scaffold, five ordered actions, volatility-normalized multi-horizon labels, and the paper's complete asymmetric decision matrix. Each month fits five action-reward regressions from 60 formation months whose longest six-month outcome has already realized, estimates the 3/15/53/85% thresholds inside that past window, and chooses the maximum group-relative reward. Aggregate stock-month action counts were {'STRONG SELL': 0, 'SELL': 0, 'HOLD': 322, 'BUY': 304678, 'STRONG BUY': 0}; mean chosen group-relative advantage was 0.5357. The missing 100,000-sample corpus, Qwen checkpoint, natural-language theses, and token-level GRPO run are not recreated.

At 10 bp one-way costs, the 305-month path has CAGR -6.82%, annualized Sharpe -0.341, and maximum drawdown -92.13%. Mean monthly traded notional is 2.569, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -8.32% annually (HAC t=-2.484, p=0.0130, 95% interval [-14.88%, -1.76%]).

This result answers how one transparent Trading-R1-inspired reward policy transfers to the common monthly U.S. universe. It does not reproduce the paper's trained language policy, one-week execution, per-date actions, or native performance claims.
