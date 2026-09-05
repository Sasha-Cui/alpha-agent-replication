# M037: ATLAS in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not a native LLM/Adaptive-OPRO ATLAS replication.

The reconstruction preserves three market, news, and fundamental analysts, a Central Trading Agent, fixed dynamic inputs and output schema, five-decision delayed windows, the exact `clip(50 + 250*ROI, 0, 100)` score, scored prompt history, and forward-only instruction updates. The editable static instruction is represented by three analyst weights and a buy/hold/sell threshold. After each completed five-month window, a deterministic meta-optimizer updates weights from standalone analyst ROI attribution and adjusts selectivity from the bounded feedback score. No earlier window is replayed. Mean feedback was 51.45; the final used prompt weights were market=0.012, news=0.013, fundamental=0.975, with hold threshold 0.40. Missing optimizer-LLM calls, natural-language edits, order trajectories, and native StockSim feedback are not recreated.

At 10 bp one-way costs, the 305-month path has CAGR 1.33%, annualized Sharpe 0.164, and maximum drawdown -47.78%. Mean monthly traded notional is 0.793, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -4.11% annually (HAC t=-2.288, p=0.0221, 95% interval [-7.63%, -0.59%]).

This result answers how one transparent ATLAS-inspired Adaptive-OPRO policy transfers to the common monthly U.S. universe. It does not reproduce the paper's prompt text, optimizer requests, order-level execution, three-asset study, or native claims.
