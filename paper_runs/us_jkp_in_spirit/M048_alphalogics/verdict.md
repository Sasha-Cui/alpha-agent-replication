# M048: AlphaLogics in-spirit reconstruction on monthly U.S./JKP data

Status: **completed researcher-authored in-spirit reconstruction**, not the native LLM-generated AlphaLogics factor pool or LightGBM model.

The reconstruction preserves explicit market logics, deterministic compilation into an executable DSL, validation-only factor feedback, three-strike inner-loop stopping, logic-level evidence, five persistent outer rounds, and a final multi-factor scorer. Six technical logics use 17 JKP primitives. Each round adds one frozen operation family; candidates are selected only on July 1994-June 1999 RankIC information ratio, then a ridge scorer is fitted on the complete pre-common calibration period. The selected expressions were trend_persistence: pair_product__ret_6_1__turnover_126d; short_horizon_reversal: identity__ret_1_0; price_volume_confirmation: identity__dolvol_126d; breakout_quality: pair_product__prc_highprc_252d__rvol_21d; residual_momentum: triple_mean__resff3_12_1__ret_12_7__seas_1_1an; volatility_compression: pair_product__ivol_capm_252d__ret_6_1. Across 30 logic-rounds, 108 candidates were evaluated and 24 searches stopped after three non-improvements.

At 10 bp one-way costs, the 305-month path has CAGR 2.99%, annualized Sharpe 0.250, and maximum drawdown -52.95%. Mean monthly traded notional is 2.754, and minimum signal coverage is 1000 stocks.

Across the 185-month rolling JKP attribution window, residual mean return is -3.81% annually (HAC t=-1.650, p=0.0990, 95% interval [-8.34%, 0.72%]).

This result answers how one transparent AlphaLogics-inspired logic-evolution process transfers to the common monthly U.S. universe. It does not reproduce the authors' mined logic library, filled LLM traces, 59-operation daily DSL, generated factor pool, LightGBM fit, or Qlib Top-50/drop-5 path. The full July 1999-November 2024 formation period remained outside factor search and model fitting.
