# M026: Chain-of-Alpha disclosed formula on monthly U.S./JKP data

Status: **completed partial evaluation**, not either LLM chain or the native factor portfolio.

The exact showcased `Volume_Adjusted_Mean_Corr` formula is preserved as five-period time-series ranks of close and amount followed by their five-period correlation. It was selected because it alone avoids unavailable VWAP, not because of JKP performance. JKP `abs(prc)` and source-defined USD `dolvol`, monthly cadence, the top-1,000 U.S. universe, and common value-weighted deciles are disclosed adaptations.

At 10 bp one-way costs, the 305-month path has CAGR -3.61%, annualized Sharpe -0.236, and maximum drawdown -75.26%. The 185-month rolling JKP133 residual mean is -2.28% annually (HAC t=-0.910, p=0.3626; descriptive 69-test bound=1.0000).

This result does not reproduce the withdrawn paper's native parser, dual-chain prompts/models, search, selected 100-factor pool, LightGBM, Qlib portfolio, or reported RankIC. Prior project outcomes were known, so inference is exploratory.
