# M038: P1GPT in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native private-service P1GPT replication.

The reconstruction preserves the Input, Planning, Analysis, Integration, and Decision layers; Controller routing; four domain agents; dependent Search, Revenue, Trend, and Recommendation agents; standardized reports; conflict-aware integration; confidence; and risk assessment. Seven analytic reports are combined by 75% median and 25% mean, then blended 80/20 with a defensive risk report. Confidence below 0.35 forces HOLD. Aggregate decisions were {'buy': 119664, 'hold': 55938, 'sell': 118659}, including 4755 confidence-forced holds; mean confidence was 0.647. The future-contaminated author report and 2025 position arrays are never used.

At 10 bp one-way costs, the 305-month path has CAGR 0.28%, annualized Sharpe 0.111, and maximum drawdown -54.34%. Mean monthly traded notional is 1.664, and minimum signal coverage is 930 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -0.60% annually (HAC t=-0.252, p=0.8012, 95% interval [-5.24%, 4.05%]).

This result answers how one transparent P1GPT-inspired layered multi-agent workflow transfers to the common monthly U.S. universe. It does not reproduce the private model service, prompts, same-day-close long-only state machine, three-asset run, or native claims.
