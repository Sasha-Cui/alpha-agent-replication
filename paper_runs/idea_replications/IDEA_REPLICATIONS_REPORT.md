# Alpha Evolve Paper-Idea Proxy Replications


Date: 2026-07-04

This section is separate from the repository-code audit above. It asks a different question: among papers that may not provide usable public code, are any described trading ideas concrete enough to test honestly on the approved JKP USA equity data?

I tested 23 paper-idea proxy candidates from these paper references: 002 EFS, 007 Alpha-Jungle, 010 FAMA, 015 AlphaLogics, 018 AlphaCrafter, 024 ContestTrade, 026 QuantAgent Holy Grail, 032 MM-DREX, 036 AlphaAgents, 037 MarketSenseAI 2.0, 040 FinVision, 042 GuruAgents, 044 HedgeAgents. These are not public-code reproductions. They are JKP-only, USA-equity, monthly cross-sectional proxy replications of ideas described in the papers. Candidate and benchmark returns were built only from `${ALPHA_EVOLVE_JKP_ROOT}/data/processed/characteristics/USA.parquet`; no China data, yfinance data, paper-shipped return files, official French downloads, or external return streams were used.

### Headline Result

- Proxy candidates tested: 23
- Sample: 305 monthly observations for most candidates, 1999-07-31 to 2024-11-30; ContestTrade meta-selection has 281 observations because it needs trailing history.
- Universe: top 1000 USA stocks by JKP `me` each month.
- Portfolio construction: value-weighted top-vs-bottom decile long-short unless otherwise noted.
- Benchmark: JKP-built FF5Mom (`jkp_topn_mkt`, `char__be_me`, `char__market_equity`, `char__at_gr1`, `char__ope_be`, `char__ret_12_1`).
- Beat rule: positive annualized alpha, positive appraisal/information ratio, HAC alpha t-statistic greater than 1.96, positive FF5Mom span Sharpe lift, and GRS rejection at 5%.
- Result: 2 of 23 proxy candidates beat FF5Mom under that strict rule.

### Ideas That Beat FF5Mom

| candidate | paper | Sharpe | alpha ann | alpha t | appraisal/IR | GRS F | GRS p | span lift |
|---|---|---|---|---|---|---|---|---|
| guru_buffett_quality_compounder | 042 GuruAgents | 0.658 | 2.69% | 2.702 | 0.534 | 6.490 | 0.0113 | 0.127 |
| guru_equal_weight_style_ensemble | 042 GuruAgents | 0.392 | 1.57% | 2.112 | 0.424 | 4.095 | 0.0439 | 0.082 |

The strongest result is `guru_buffett_quality_compounder`: annualized FF5Mom alpha 2.69%, HAC alpha t-stat 2.702, appraisal/information ratio 0.534, GRS F 6.490 with p-value 0.0113, and FF5Mom span Sharpe lift 0.127. The broader `guru_equal_weight_style_ensemble` also passes, with annualized alpha 1.57%, t-stat 2.112, appraisal/information ratio 0.424, GRS p-value 0.0439, and span lift 0.082.

### Positive But Not Strictly Beating

These had positive annualized FF5Mom alpha but failed at least one required threshold, usually alpha t-statistic or GRS p-value.

| candidate | paper | alpha ann | alpha t | appraisal/IR | GRS p | span lift |
|---|---|---|---|---|---|---|
| guru_altman_distress_avoidance | 042 GuruAgents | 1.58% | 2.167 | 0.403 | 0.0550 | 0.075 |
| efs_short_reversal_low_noise | 002 EFS | 1.71% | 1.756 | 0.336 | 0.1102 | 0.052 |
| efs_sparse_top5_momentum_low_vol | 002 EFS | 1.66% | 1.666 | 0.307 | 0.1432 | 0.044 |
| guru_piotroski_fscore_proxy | 042 GuruAgents | 1.88% | 1.663 | 0.331 | 0.1154 | 0.051 |
| guru_graham_deep_value_defensive | 042 GuruAgents | 1.09% | 1.512 | 0.292 | 0.1638 | 0.040 |
| finvision_trend_dip_risk_control | 040 FinVision | 1.24% | 1.491 | 0.278 | 0.1861 | 0.036 |
| quantagent_three_soldiers_trend | 026 QuantAgent Holy Grail | 0.87% | 0.830 | 0.167 | 0.4246 | 0.013 |
| alpha_jungle_volatility_compression_trend | 007 Alpha-Jungle | 0.38% | 0.593 | 0.109 | 0.6044 | 0.006 |

The best near miss is `guru_altman_distress_avoidance`: annualized alpha 1.58% and HAC t-stat 2.167, but its GRS p-value is 0.0550, just outside the 5% threshold. EFS has interesting positive proxies, especially short-term reversal plus low-noise quality and sparse top-5 momentum/low-volatility selection, but neither clears both the HAC and GRS hurdles.

### Full FF5Mom Metrics

| candidate | paper | T | Sharpe | alpha ann | alpha t | appraisal | IR | GRS F | GRS p | GRS 5% | span lift | beats FF5Mom |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| guru_buffett_quality_compounder | 042 GuruAgents | 305 | 0.658 | 2.69% | 2.702 | 0.534 | 0.534 | 6.490 | 0.0113 | yes | 0.127 | yes |
| guru_equal_weight_style_ensemble | 042 GuruAgents | 305 | 0.392 | 1.57% | 2.112 | 0.424 | 0.424 | 4.095 | 0.0439 | yes | 0.082 | yes |
| guru_altman_distress_avoidance | 042 GuruAgents | 305 | 0.329 | 1.58% | 2.167 | 0.403 | 0.403 | 3.710 | 0.0550 | no | 0.075 | no |
| efs_short_reversal_low_noise | 002 EFS | 305 | 0.188 | 1.71% | 1.756 | 0.336 | 0.336 | 2.566 | 0.1102 | no | 0.052 | no |
| efs_sparse_top5_momentum_low_vol | 002 EFS | 305 | 0.775 | 1.66% | 1.666 | 0.307 | 0.307 | 2.154 | 0.1432 | no | 0.044 | no |
| guru_piotroski_fscore_proxy | 042 GuruAgents | 305 | 0.453 | 1.88% | 1.663 | 0.331 | 0.331 | 2.494 | 0.1154 | no | 0.051 | no |
| guru_graham_deep_value_defensive | 042 GuruAgents | 305 | 0.205 | 1.09% | 1.512 | 0.292 | 0.292 | 1.948 | 0.1638 | no | 0.040 | no |
| finvision_trend_dip_risk_control | 040 FinVision | 305 | 0.340 | 1.24% | 1.491 | 0.278 | 0.278 | 1.756 | 0.1861 | no | 0.036 | no |
| quantagent_three_soldiers_trend | 026 QuantAgent Holy Grail | 305 | 0.215 | 0.87% | 0.830 | 0.167 | 0.167 | 0.639 | 0.4246 | no | 0.013 | no |
| alpha_jungle_volatility_compression_trend | 007 Alpha-Jungle | 305 | 0.249 | 0.38% | 0.593 | 0.109 | 0.109 | 0.269 | 0.6044 | no | 0.006 | no |
| guru_greenblatt_magic_formula | 042 GuruAgents | 305 | 0.175 | 0.34% | 0.482 | 0.105 | 0.105 | 0.251 | 0.6166 | no | 0.005 | no |
| alphalogics_value_quality_growth | 015 AlphaLogics | 305 | 0.192 | 0.49% | 0.468 | 0.098 | 0.098 | 0.220 | 0.6394 | no | 0.005 | no |
| marketsense_value_momentum_quality | 037 MarketSenseAI 2.0 | 305 | 0.256 | 0.29% | 0.353 | 0.068 | 0.068 | 0.107 | 0.7442 | no | 0.002 | no |
| alphacrafter_full_stack_multifactor | 018 AlphaCrafter | 305 | 0.237 | 0.25% | 0.336 | 0.070 | 0.070 | 0.113 | 0.7367 | no | 0.002 | no |
| mm_drex_dynamic_router_proxy | 032 MM-DREX | 305 | 0.185 | 0.15% | 0.216 | 0.038 | 0.038 | 0.033 | 0.8550 | no | 0.001 | no |
| alphaagents_risk_averse_quality_lowrisk | 036 AlphaAgents | 305 | 0.065 | 0.13% | 0.172 | 0.035 | 0.035 | 0.028 | 0.8677 | no | 0.001 | no |
| hedgeagents_balanced_lowrisk_alpha | 044 HedgeAgents | 305 | 0.015 | 0.12% | 0.160 | 0.032 | 0.032 | 0.023 | 0.8793 | no | 0.000 | no |
| contesttrade_internal_contest_trailing_sharpe | 024 ContestTrade | 281 | 0.158 | 0.17% | 0.133 | 0.030 | 0.030 | 0.020 | 0.8890 | no | 0.000 | no |
| alphaagents_risk_neutral_fundamental_momentum | 036 AlphaAgents | 305 | 0.405 | 0.11% | 0.131 | 0.026 | 0.026 | 0.015 | 0.9016 | no | 0.000 | no |
| fama_value_momentum_interpretable | 010 FAMA | 305 | 0.433 | -0.13% | -0.184 | -0.035 | -0.035 | 0.028 | 0.8676 | no | 0.001 | no |
| alpha_jungle_price_volume_momentum | 007 Alpha-Jungle | 305 | 0.044 | -0.38% | -0.428 | -0.079 | -0.079 | 0.142 | 0.7070 | no | 0.003 | no |
| quantagent_volatility_breakout | 026 QuantAgent Holy Grail | 305 | 0.048 | -0.58% | -0.576 | -0.126 | -0.126 | 0.364 | 0.5466 | no | 0.008 | no |
| efs_momentum_low_vol_breakout | 002 EFS | 305 | 0.163 | -0.55% | -0.784 | -0.167 | -0.167 | 0.637 | 0.4254 | no | 0.013 | no |

### Proxy Mapping

| candidate | paper | strategy | JKP proxy formula | paper idea mapped |
|---|---|---|---|---|
| guru_buffett_quality_compounder | 042 GuruAgents | long_short_decile_value_weighted | rank(qmj)+rank(qmj_growth)+rank(qmj_prof)+rank(ope_be)+rank(gp_me)-rank(debt_at) | Warren Buffett-style quality compounder: durable quality/profitability/growth with low leverage. |
| guru_equal_weight_style_ensemble | 042 GuruAgents | long_short_decile_value_weighted | average Graham, Buffett, Greenblatt, Piotroski, Altman proxy scores | GuruAgents combines multiple investment-guru sleeves; this is an equal-weight score ensemble of the five guru proxies. |
| guru_altman_distress_avoidance | 042 GuruAgents | long_short_decile_value_weighted | rank(ebitda_debt)+rank(cash_at)+rank(ni_me)-rank(debt_at)-rank(rvol_252d)-rank(betadown_252d) | Edward Altman-style distress avoidance: earnings/cash/debt coverage and downside-risk control. |
| efs_short_reversal_low_noise | 002 EFS | long_short_decile_value_weighted | -rank(ret_1_0)-rank(rvol_21d)+rank(qmj_safety) | EFS discusses regime shifts toward mean reversion and downside/noise filtering in sideways markets. |
| efs_sparse_top5_momentum_low_vol | 002 EFS | long_only_top5_equal_weighted | top5 equal-weight long-only excess return from efs_momentum_low_vol_breakout score | EFS uses sparse top scoring asset selection; this tests a literal sparse top-5 proxy using the momentum/low-volatility score. |
| guru_piotroski_fscore_proxy | 042 GuruAgents | long_short_decile_value_weighted | rank(ni_me)+rank(ocf_me)-rank(oaccruals_at)-rank(debt_gr1)-rank(eqnetis_me)+rank(at_turnover)+rank(sale_gr1) | Joseph Piotroski-style F-score: profitability, operating cash flow, accrual quality, leverage, issuance, and asset turnover. |
| guru_graham_deep_value_defensive | 042 GuruAgents | long_short_decile_value_weighted | rank(be_me)+rank(cash_at)+rank(ope_be)-rank(debt_at)-rank(rvol_252d)-rank(beta_252d) | Benjamin Graham-style defensive value: cheap, liquid, profitable, low leverage, low risk. |
| finvision_trend_dip_risk_control | 040 FinVision | long_short_decile_value_weighted | rank(ret_12_1)-rank(ret_1_0)-rank(rvol_21d)+rank(qmj_safety) | FinVision prompts prioritize holding strong upward trends, buying dips within uptrends, and risk management. |
| quantagent_three_soldiers_trend | 026 QuantAgent Holy Grail | long_short_decile_value_weighted | rank(ret_1_0)+rank(ret_3_1)+rank(turnover_126d)-rank(rvol_21d) | QuantAgent appendix includes ThreeSoldier candlestick-style trend continuation signals with volume/body-size confirmation. |
| alpha_jungle_volatility_compression_trend | 007 Alpha-Jungle | long_short_decile_value_weighted | rank(ret_3_1)+rank(ret_12_1)-rank(rvol_21d)-rank(ivol_capm_21d) | Alpha-Jungle examples include moving-average price changes and standard-deviation operators; this proxy tests trend after volatility compression. |
| guru_greenblatt_magic_formula | 042 GuruAgents | long_short_decile_value_weighted | rank(ebit_mev)+rank(ope_be)+rank(gp_mev)+rank(be_me) | Joel Greenblatt-style magic formula: earnings yield plus business quality/return on capital. |
| alphalogics_value_quality_growth | 015 AlphaLogics | long_short_decile_value_weighted | rank(be_me)+rank(ope_be)+rank(gp_me)+rank(sale_gr1)-rank(debt_at) | AlphaLogics emphasizes market-logic-driven, interpretable factor generation; this proxy tests value, quality, growth, and leverage logic. |
| marketsense_value_momentum_quality | 037 MarketSenseAI 2.0 | long_short_decile_value_weighted | rank(be_me)+rank(ret_12_1)+rank(qmj)+rank(sale_gr1) | MarketSenseAI factor analysis discusses value and momentum loadings, with fundamentals and price dynamics reinforcing selection. |
| alphacrafter_full_stack_multifactor | 018 AlphaCrafter | long_short_decile_value_weighted | rank(be_me)+rank(ope_be)+rank(ret_12_1)+rank(qmj)-rank(at_gr1)-rank(rvol_252d) | AlphaCrafter combines mined factors, regime screening, and risk-constrained trading; this proxy tests a diversified value-quality-momentum-low-risk factor ensemble. |
| mm_drex_dynamic_router_proxy | 032 MM-DREX | long_short_decile_value_weighted | rank(ret_12_1)-rank(ret_1_0)+rank(rmax5_rvol_21d)-rank(rvol_21d)+rank(qmj_safety) | MM-DREX dynamically routes trend, reversal, breakout, and risk/positioning experts. |
| alphaagents_risk_averse_quality_lowrisk | 036 AlphaAgents | long_short_decile_value_weighted | rank(qmj)+rank(ope_be)+rank(be_me)-rank(rvol_252d)-rank(beta_252d)-rank(debt_at) | AlphaAgents risk-averse portfolios emphasize lower volatility and stable fundamentals. |
| hedgeagents_balanced_lowrisk_alpha | 044 HedgeAgents | long_short_decile_value_weighted | rank(qmj)+rank(be_me)+rank(ope_be)-rank(rvol_252d)-rank(beta_252d)-rank(betadown_252d) | HedgeAgents is framed as balanced-aware trading; this proxy tests quality/value alpha with explicit low beta/downside-risk control. |
| contesttrade_internal_contest_trailing_sharpe | 024 ContestTrade | meta_sleeve_selection_trailing_sharpe | monthly winner among idea sleeves by trailing 36m Sharpe, min 24m history | ContestTrade uses an internal contest/ranking mechanism among agents. This proxy selects the JKP idea sleeve with the best trailing 36-month realized Sharpe using only past generated JKP returns. |
| alphaagents_risk_neutral_fundamental_momentum | 036 AlphaAgents | long_short_decile_value_weighted | rank(ret_12_1)+rank(sale_gr1)+rank(ope_be)+rank(be_me) | AlphaAgents risk-neutral portfolios emphasize valuation plus fundamentals/growth/momentum. |
| fama_value_momentum_interpretable | 010 FAMA | long_short_decile_value_weighted | rank(be_me)+rank(ret_12_1)+rank(ope_be)-rank(market_equity) | FAMA mines interpretable financial factors and cites momentum-style financial principles; this proxy tests a simple interpretable value/momentum/profitability factor. |
| alpha_jungle_price_volume_momentum | 007 Alpha-Jungle | long_short_decile_value_weighted | rank(ret_3_1)+rank(turnover_126d)+rank(dolvol_126d)-rank(turnover_var_126d) | Alpha-Jungle examples combine price percentage change, volume, volatility, and formula diversity in an MCTS alpha search. |
| quantagent_volatility_breakout | 026 QuantAgent Holy Grail | long_short_decile_value_weighted | rank(rmax5_rvol_21d)+rank(ret_1_0)+rank(ret_3_1)-rank(rvol_21d) | QuantAgent appendix includes a VolatilityBreakoutSignal based on high breaking above a threshold relative to ATR. |
| efs_momentum_low_vol_breakout | 002 EFS | long_short_decile_value_weighted | rank(ret_3_1)+rank(ret_6_1)+rank(ret_12_1)-rank(rvol_21d)-rank(rvol_252d)+rank(rmax5_rvol_21d) | EFS appendix describes evolved factors combining momentum, mean return, low volatility/stability, and breakout logic. |

### Interpretation

The useful signal in this exploratory layer is concentrated in simple quality/profitability/low-leverage style ideas, especially the GuruAgents Buffett-style and multi-guru ensemble proxies. Those are not novel machine-discovered formulas, but they are relevant because the paper idea can be mapped to observable USA JKP characteristics and still leaves positive residual alpha after the JKP FF5Mom span.

Most agentic trading papers do not survive this translation as alpha. The trend/breakout/price-volume candidates from Alpha-Jungle, QuantAgent, FinVision, MM-DREX, and related papers generally produce small or statistically weak FF5Mom alpha once expressed with monthly JKP characteristics. This does not prove the original papers are false; it means their described idea, when reduced to an honest JKP-only USA monthly proxy, does not add enough beyond FF5Mom to pass the rule here.

### Reproducibility

Run from the Bouchet canonical directory:

```bash
cd ${ALPHA_EVOLVE_REPO}
.venv/bin/python scripts/run_paper_idea_jkp_proxies.py
```

Main artifacts:

- `paper_runs/idea_replications/jkp_paper_idea_proxies/paper_idea_proxy_ff5mom_summary.csv`
- `paper_runs/idea_replications/jkp_paper_idea_proxies/paper_idea_proxy_all_benchmark_metrics.csv`
- `paper_runs/idea_replications/jkp_paper_idea_proxies/paper_idea_proxy_metadata.json`
- `scripts/run_paper_idea_jkp_proxies.py`

<!-- PAPER_IDEA_PROXY_REPLICATIONS_END -->
