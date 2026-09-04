# M005: AlphaQuanter in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native AlphaQuanter replication.

The reconstruction preserves four separately formed market, fundamental, sentiment-proxy, and macro-proxy tool categories; selective acquisition of the two most useful tools; and the paper's exponentially blended multi-horizon reward idea. Each monthly policy is fitted on 60 formation months whose one-, three-, and six-month outcomes are fully realized behind a six-month gap. The 1.5% Buy/Sell/Hold threshold is reported diagnostically while continuous confidence feeds the common rank portfolio. The unavailable Qwen/GRPO policy, natural-language ReAct trace, API inputs, and native actions are not reproduced.

At 10 bp one-way costs, the 305-month path has CAGR -9.85%, annualized Sharpe -0.298, and maximum drawdown -97.61%. Mean monthly traded notional is 2.558, and minimum signal coverage is 660 stocks. Across two selected tools per month, selection counts are sentiment_proxy=191, macro_proxy=172, market_technical=168, fundamental=79.

Across the 185-month rolling JKP attribution window, residual mean return is -4.04% annually (HAC t=-1.009, p=0.3129, 95% interval [-11.88%, 3.81%]).

This result answers how one transparent AlphaQuanter-inspired selective-tool policy transfers to the common task. It does not reproduce or validate the paper's private checkpoint, test prompts, action trajectories, reported returns, or model-comparison claims.
