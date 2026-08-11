# LLM Alpha-Agent Replication Report

> [!CAUTION]
> **SUPERSEDED / INVALIDATED — DO NOT USE FOR CURRENT CLAIMS OR RESULTS.**
> This legacy document predates the current artifact-audit and fidelity framing and is retained only for provenance. Use the current claim-boundary document (`docs/FIDELITY_AUDIT.md`), the current manuscript (`docs/paper/icaif2026_submission.tex`; built PDF `output/pdf/icaif2026_submission.pdf`), and current fidelity evidence (`paper_runs/submission_evidence/native_fidelity_ledger.csv` and `paper_runs/submission_evidence/artifact_audit/`) instead. Claims, counts, and interpretations below are not authoritative for the current submission.

Date: 2026-07-09

## Abstract

This report evaluates whether recent LLM- and agent-based alpha-mining papers and public repositories contain reproducible, economically meaningful equity return signals once they are placed into a common monthly USA-equity asset-pricing benchmark. I audit the source universe in two layers. First, I ask whether each public repository can itself produce a dated return stream from approved local inputs. Second, when direct code is absent or unusable, I translate the stated economic idea into an explicit JKP-USA proxy and test it against FF5+Mom, JKP132, and TextBenchmark/NewsFactor-style benchmarks. The conclusion is negative for repo-level alpha discovery: direct public code does not produce a valid FF5+Mom-beating JKP return stream, and the few in-spirit survivors are overwhelmingly classic value, quality, profitability, momentum, and low-risk composites. The positive residuals that remain after strong controls are small and are best interpreted as implementation geometry, nonlinear composite sorts, and multiple-testing artifacts rather than evidence that agentic repositories discovered new financial anomalies.

## Executive Summary

I audited the alpha-agent literature/repository set in two layers:

1. **Direct-code audit:** whether the public repository itself could produce a dated monthly USA-equity return stream using only approved local return inputs.
2. **In-spirit JKP replication:** when direct code was absent or unusable, whether the paper/repo idea could be translated into an explicit USA-equity JKP proxy, then backtested and performance-tested against JKP benchmarks.

The final conclusion is negative on repo-level alpha discovery. The public repositories do not provide convincing new alpha ideas that add economically meaningful value beyond JKP and TextBenchmark. The few statistically positive rows are almost entirely traditional value/quality/profitability/momentum/low-risk composites. Those are mostly captured by the existing JKP factor span; the residual appears to come from nonlinear composite sorts, implementation geometry, and multiple testing rather than a new LLM/agentic trading idea.

This is a replication and benchmarking report, not a claim that LLMs are useless for financial research. The stronger interpretation is narrower: public finance-agent alpha claims should not be treated as economically meaningful until the claimed strategy is converted into dated returns and survives common-task-style baselines.

Headline counts:

- Literature inventory: **42 paper rows**, **31 code-link rows**, **55 unique source refs**.
- Direct cloned/repo audit: **14 repos**; **12 real public-code repos**, **1 ambiguous unofficial repo**, **1 placeholder/empty repo**.
- Code-link repo evidence pass: **28 GitHub repos cloned/read** from the broader code-link table.
- Direct repo-code rows with valid JKP-only numeric returns: **1** (`QuantEvolver` seed proxies).
- Direct repo-code rows beating FF5Mom: **0**.
- Source refs translated into JKP-USA in-spirit proxies: **51 / 55**.
- JKP-USA candidate proxies backtested: **62**.
- Strict FF5Mom beaters among in-spirit proxies: **8 / 62**.
- Strict additive candidates after adding TextBenchmark and JKP132: **3 / 62**.
- Non-mappable source refs: **4**.

## Return-Data Scope

Valid candidate and benchmark returns were constructed only from these read-only local inputs:

- `${ALPHA_EVOLVE_JKP_ROOT}`
- `${ALPHA_EVOLVE_RETURN_DATA_ROOT}`

I did **not** use China/A-share returns, yfinance/live downloads, paper-shipped return streams, official Kenneth French downloads, or external return CSVs for valid metrics. Legacy GuruAgents/TradeTrap paper-shipped-return diagnostics remain on disk for auditability but are not counted as valid results.

The reason for this restriction is methodological. Most agent papers report performance in incomparable environments: different countries, frequencies, backtest engines, transaction-cost assumptions, data vendors, live-trading adapters, and sometimes no return stream at all. A common USA-equity monthly panel is a lossy but disciplined benchmark. It turns heterogeneous claims into the same object: a dated candidate excess return \(r_t\) evaluated against the same factor span \(f_t\).

## Performance Tests

For the JKP FF5Mom pass, monthly candidate returns were tested against JKP-built USA factor returns. The main FF5Mom benchmark is:

`jkp_topn_mkt + char__be_me + char__market_equity + char__at_gr1 + char__ope_be + char__ret_12_1`

For the TextBenchmark/additive pass, I reused the same performance-analysis contract as the STATE/TextBenchmark work: fixed window `1999-07-31` to `2021-12-31`, candidate and benchmark streams scaled to 7% annualized volatility on the overlap, and additive-book diagnostics against `JKP132 + Didisheim/TextBenchmark` using the cached factor panel:

`${ALPHA_EVOLVE_FACTOR_PANEL}`

The regression test is:

$$
r_t = \alpha + \beta^\top f_t + \epsilon_t.
$$

Reported metrics are annualized Sharpe, annualized alpha, HAC/Newey-West alpha t-statistic, appraisal/information ratio, GRS statistic/p-value, and factor-span Sharpe lift:

$$
IR = AR = \sqrt{12}\,\frac{\hat\alpha}{\sigma(\hat\epsilon)},
\qquad
\Delta SR = \sqrt{SR_{old}^2 + AR^2} - SR_{old}.
$$

The strict FF5Mom beat rule requires positive annualized alpha, positive appraisal/IR, HAC t-stat greater than 1.96, positive span lift, and GRS rejection at 5%. The strict TextBenchmark additive rule further requires survival against `CAPM + JKP132 + TextBenchmark`, GRS rejection, positive long-only delta Sharpe versus `JKP132 + TextBenchmark`, and at least a 1% optimized candidate weight.

Thus the report separates three questions:

1. **Replicability:** can a public repo generate dated returns from approved data?
2. **Benchmark survival:** does the candidate beat FF5+Mom and broader JKP controls?
3. **Portfolio usefulness:** does the candidate improve an already strong benchmark book after optimization?

## Source Universe

The tested universe is the de-duplicated union of `literature_review/paper_links.csv` and `literature_review/code_links.csv`. Paper text was extracted for 39 source refs and repo README/source evidence was available for 14 source refs in the source ledger. The broader code-link pass cloned/read 28 GitHub repos.

| status | count |
| --- | --- |
| jkp_proxy_tested | 51 |
| not_mappable_benchmark_no_strategy | 1 |
| not_mappable_crypto_not_usa_equity | 1 |
| not_mappable_no_alpha_strategy | 1 |
| not_mappable_tooling_no_strategy | 1 |

Candidate evidence basis:

| source basis | candidates |
| --- | --- |
| paper_text | 48 |
| repo_readme_or_source_notes | 11 |
| source_table_or_repo_notes_missing_extracted_paper_text | 2 |
| repo_readme_missing_extracted_paper_text | 1 |

Candidate construction types:

| strategy | candidates |
| --- | --- |
| long_short_decile_value_weighted | 56 |
| long_only_top_decile_value_weighted | 4 |
| long_only_top5_equal_weighted | 1 |
| meta_sleeve_selection_trailing_sharpe | 1 |

Evidence categories in the mapped candidate rows:

| evidence category | candidate rows |
| --- | --- |
| agent_trading_workflow | 57 |
| risk_control | 54 |
| reported_performance_claim | 46 |
| sparse_or_cross_sectional_portfolio | 38 |
| factor_mining | 29 |

The `reported_performance_claim` category is the closest ledger count to "reports Sharpe/performance": 46 mapped candidate rows had paper/repo evidence of reported performance claims, but those claims were not counted as valid metrics unless I could reconstruct dated monthly returns from the approved local data.

Original-paper content that could not be faithfully reproduced on the approved monthly USA-equity JKP universe:

| unavailable original content | candidate rows |
| --- | --- |
| live_or_llm_execution | 61 |
| news_or_text_signal | 52 |
| image_or_multimodal_signal | 48 |
| non_usa_or_crypto_scope | 45 |
| intraday_or_hft_signal | 40 |

### Non-Mappable Sources

| ref | source | status | reason |
| --- | --- | --- | --- |
| 41 | Xtra-Computing/CryptoTrade | not_mappable_crypto_not_usa_equity | CryptoTrade is crypto-only and outside the USA-equity JKP universe. |
| 46 | LimexAILab/QuantCode-Bench | not_mappable_benchmark_no_strategy | QuantCode-Bench evaluates code generation, not a dated alpha strategy. |
| 54 | moss-site/moss-trade-bot-skills | not_mappable_tooling_no_strategy | moss-trade-bot-skills is tooling, not a standalone USA-equity alpha strategy. |
| 55 | Reported Alpha from LLM Trading Agents Should Not Be ... | not_mappable_no_alpha_strategy | The Alpha Illusion is a critique/reporting protocol paper, not an alpha strategy. |

## Direct Public-Code Audit

This audit answers a narrow question: can the repo itself generate an approved-input dated return stream? Most repositories fail this narrow test because they provide framework code, aggregate benchmark numbers, live/yfinance workflows, China/crypto/HFT scope, or no persisted historical strategy returns. I left those direct-code metric fields as unavailable rather than inventing a return stream and attributing it to the repo.

| repo | ref | code status | state | direct metric status | candidate | alpha t | beats |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AlphaAgent | 3 | real_public_code | completed_no_direct_strategy_returns | not_computable_from_approved_inputs:not_serious_no_strategy_return_... |  |  | no |
| AlphaBench | 1 | real_public_code | completed_no_direct_strategy_returns | not_computable_from_approved_inputs:not_serious_no_strategy_return_... |  |  | no |
| AlphaForgeBench | 45 | real_public_code | blocked_on_return_path_adapter | not_computable_from_approved_inputs:blocked_aggregate_metrics_only_... |  |  | no |
| AlphaPROBE | 21 | real_public_code | blocked_on_data_adapter | not_computable_from_approved_inputs:blocked_no_usa_jkp_candidate_re... |  |  | no |
| ContestTrade | 24 | real_public_code | blocked_on_replay_adapter | not_computable_from_approved_inputs:blocked_no_jkp_replay_return_st... |  |  | no |
| DeepFund | 48 | real_public_code | blocked_on_historical_run | not_computable_from_approved_inputs:blocked_no_approved_historical_... |  |  | no |
| FAgent | 29 | ambiguous_unofficial_code | blocked_jkp_scope_incompatible | not_computable_from_approved_inputs:blocked_no_jkp_candidate_return... |  |  | no |
| GuruAgents | 42 | real_public_code | legacy_non_jkp_diagnostic | not_computable_from_approved_inputs:legacy_non_jkp_paper_shipped_re... |  |  | no |
| QuantAgent | 25 | real_public_code | blocked_jkp_scope_incompatible | not_computable_from_approved_inputs:blocked_hft_not_representable_w... |  |  | no |
| QuantEvolver | 5 | real_public_code | completed_jkp_proxy_test | computed_jkp_only | quantevolver_return_sharpe_60_proxy | 0.651 | no |
| RD-Agent | 6 | real_public_code | blocked_on_jkp_adapter | not_computable_from_approved_inputs:blocked_requires_jkp_adapter_no... |  |  | no |
| TradeTrap | 51 | real_public_code | legacy_non_jkp_diagnostic | not_computable_from_approved_inputs:legacy_non_jkp_paper_shipped_re... |  |  | no |
| Trading-R1 | 33 | placeholder_or_empty_repo | blocked_no_public_codebase | not_computable_from_approved_inputs:blocked_placeholder_repo_no_exe... |  |  | no |
| live-trade-bench | 47 | real_public_code | blocked_on_return_path_adapter | not_computable_from_approved_inputs:blocked_no_jkp_live_or_replay_r... |  |  | no |

Direct-code conclusion: `QuantEvolver` is the only repo with valid JKP-only numeric seed-proxy metrics. Its selected declared-direction seed, `quantevolver_return_sharpe_60_proxy`, has Sharpe 0.316, annualized alpha 0.33%, HAC t-stat 0.651, IR 0.149, GRS p-value 0.4778, and span lift 0.010. It does not beat FF5Mom. No direct public-code repository produced a valid JKP-USA return stream that beats FF5Mom.

## In-Spirit JKP-USA Replication

For papers/repos without direct usable code, I read the paper text and/or repository evidence, extracted the economic idea, and built an explicit monthly USA-equity proxy from JKP characteristics. This is not a faithful execution of the original agent; it is an honest test of whether the idea survives when translated into the approved JKP universe.

The 8 strict FF5Mom beaters were:

| candidate | source | Sharpe | alpha ann | t | IR | GRS p | span lift | proxy formula |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| repo_alphaagent_decay_resistant_quality | 003 AlphaAgent | 0.796 | 3.86% | 4.264 | 0.890 | 0.0000 | 0.325 | rank(ope_be)+rank(ocf_me)+rank(qmj_safety)+rank(at_turnover)-rank(oaccruals_at)-rank(... |
| code_ai_trader_value_quality | 049 AI-Trader | 0.436 | 2.28% | 2.705 | 0.498 | 0.0181 | 0.112 | rank(be_me)+rank(qmj)+rank(ope_be)+rank(cash_at)-rank(debt_at)-rank(rvol_252d) |
| guru_buffett_quality_compounder | 042 GuruAgents | 0.658 | 2.69% | 2.702 | 0.534 | 0.0113 | 0.127 | rank(qmj)+rank(qmj_growth)+rank(qmj_prof)+rank(ope_be)+rank(gp_me)-rank(debt_at) |
| code_alpha_r1_reasoning_screen | 017 Alpha-R1 | 0.437 | 1.69% | 2.628 | 0.541 | 0.0103 | 0.131 | rank(qmj)+rank(ope_be)+rank(ret_12_1)-rank(debt_at)-rank(rvol_252d) |
| paper_quantagents_risk_controlled_system | 043 QuantAgents | 0.303 | 1.66% | 2.593 | 0.512 | 0.0151 | 0.118 | rank(ret_12_1)+rank(qmj_safety)+rank(dolvol_126d)+rank(cash_at)-rank(rvol_252d)-rank(... |
| code_ai_hedge_fund_buffett_munger | 052 ai-hedge-fund | 0.550 | 3.00% | 2.419 | 0.538 | 0.0106 | 0.130 | rank(qmj)+rank(qmj_prof)+rank(ope_be)+rank(gp_me)+rank(cash_at)-rank(debt_at) |
| code_quantaalpha_self_evolving_factor | 004 QuantaAlpha | 0.463 | 1.71% | 2.357 | 0.495 | 0.0187 | 0.110 | rank(ret_12_1)+rank(ope_be)+rank(gp_me)+rank(qmj)-rank(rvol_252d)-rank(debt_at) |
| guru_equal_weight_style_ensemble | 042 GuruAgents | 0.392 | 1.57% | 2.112 | 0.424 | 0.0439 | 0.082 | average Graham, Buffett, Greenblatt, Piotroski, Altman proxy scores |

These 8 results should not be read as 8 new discoveries. They are mostly value, quality, profitability, safety, momentum, low-leverage, and low-volatility composites. Several are code-link or paper-in-spirit mappings rather than outputs of repo code. At 62 tests, roughly 3 false positives would be expected at a 5% level even before accounting for correlated signals and researcher degrees of freedom.

## TextBenchmark and JKP132 Additive Analysis

I then ran the same candidates through the TextBenchmark performance-analysis loop used for the STATE/TextBenchmark work. This is stricter because it asks whether the proxy adds value after the existing JKP132 factor span and TextBenchmark/NewsFactor sleeve are already present.

Headline TextBenchmark counts:

- Candidates evaluated: **62**.
- Positive/significant alpha versus TextBenchmark alone: **10**.
- Positive/significant alpha versus `CAPM + JKP132 + TextBenchmark`: **3**.
- Positive long-only delta Sharpe versus `JKP132 + TextBenchmark`: **51**.
- Positive long-only delta and candidate weight at least 1%: **41**.
- Strict additive candidates: **3**.

Strict additive rows:

| candidate | source | full alpha | t | IR | GRS p | book dSR | cand wt | proxy formula |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| guru_greenblatt_magic_formula | 042 GuruAgents | 1.55% | 3.358 | 1.071 | 0.0310 | 0.0037 | 3.7% | rank(ebit_mev)+rank(ope_be)+rank(gp_mev)+rank(be_me) |
| guru_equal_weight_style_ensemble | 042 GuruAgents | 1.93% | 3.258 | 1.138 | 0.0220 | 0.0063 | 4.9% | average Graham, Buffett, Greenblatt, Piotroski, Altman proxy scores |
| alphacrafter_full_stack_multifactor | 018 AlphaCrafter | 2.02% | 3.105 | 1.129 | 0.0230 | 0.0092 | 5.8% | rank(be_me)+rank(ope_be)+rank(ret_12_1)+rank(qmj)-rank(at_gr1)-rank(rvol_252d) |

The strict survivors are not new AI/agentic insights. They are classic factor composites: Greenblatt-style value/profitability, a multi-guru value/quality/distress ensemble, and a value/profitability/momentum/quality-minus-risk composite. This is why I do not interpret the result as evidence that these papers contain new alpha.

### Are the Surviving Composites Already Captured by JKP?

Mostly yes. The full `CAPM + JKP132 + TextBenchmark` span explains 93.5% to 95.8% of the monthly return variance of the strict survivors. Closest JKP subsets alone explain about 79.6% to 84.2%.

| candidate | closest JKP subset R2 | full span R2 | closest factors |
| --- | --- | --- | --- |
| guru_greenblatt_magic_formula | 0.842 | 0.958 | be_me, ope_be, ebitda_mev/ebit_bev, gp_at/gp_atl1 |
| guru_equal_weight_style_ensemble | 0.796 | 0.941 | be_me, ope_be, f_score, o_score, z_score, qmj_prof/qmj_safety |
| alphacrafter_full_stack_multifactor | 0.812 | 0.935 | be_me, ope_be, ret_12_1, qmj_prof/qmj_safety, at_gr1, volatility/beta |

The residual exists because a composite top-decile sort is not exactly the same as a linear combination of standalone JKP factor returns:

$$
1\{value_i + quality_i > q\} \neq a\,1\{value_i > q_v\} + b\,1\{quality_i > q_q\}.
$$

So the residual can reflect nonlinear ranks, thresholding, missingness, decile selection, and weighting differences. That is an implementation/construction effect, not a new anomaly discovered by the repositories.

## Full Source Universe Table

This table lists every unique source ref in the final ledger. `best alpha t` and `best IR` are FF5Mom metrics for the best mapped candidate for that source; blank values mean the source was not mappable to a valid USA-equity JKP strategy.

| ref | source | status | n proxies | best candidate | best alpha t | best IR | beats FF5Mom |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | AlphaBench — Benchmarking Large Language Models in Formulaic Alpha Factor M... | jkp_proxy_tested | 1 | repo_alphabench_formulaic_price_volume | -2.183 | -0.454 | no |
| 2 | EFS — Evolutionary Factor Searching for Sparse Portfolio Optimization Using... | jkp_proxy_tested | 3 | efs_short_reversal_low_noise | 1.756 | 0.336 | no |
| 3 | AlphaAgent — LLM-Driven Alpha Mining with Regularized Exploration to Counte... | jkp_proxy_tested | 1 | repo_alphaagent_decay_resistant_quality | 4.264 | 0.890 | yes |
| 4 | QuantaAlpha/QuantaAlpha | jkp_proxy_tested | 1 | code_quantaalpha_self_evolving_factor | 2.357 | 0.495 | yes |
| 5 | QuantEvolver — Reinforcement Fine-Tuning for LLM-Based Alpha Factor Discovery | jkp_proxy_tested | 1 | repo_quantevolver_return_sharpe_proxy | 0.651 | 0.149 | no |
| 6 | R&D-Agent-Quant — Multi-Agent Framework for Data-Centric Factors and Model ... | jkp_proxy_tested | 1 | repo_rd_agent_factor_model_compact_ensemble | -0.789 | -0.180 | no |
| 7 | Alpha-Jungle — LLM-Powered MCTS for Formulaic Factor Mining | jkp_proxy_tested | 2 | alpha_jungle_volatility_compression_trend | 0.593 | 0.109 | no |
| 8 | FactorMiner — Self-Evolving Agent with Skills and Experience Memory for Fin... | jkp_proxy_tested | 1 | paper_factorminer_memory_diverse_library | 1.731 | 0.377 | no |
| 9 | CogAlpha — Cognitive Alpha Mining via LLM-Driven Code-Based Evolution | jkp_proxy_tested | 1 | paper_cogalpha_code_evolved_hybrid | 1.319 | 0.272 | no |
| 10 | FAMA — Factor Mining Agent | jkp_proxy_tested | 1 | fama_value_momentum_interpretable | -0.184 | -0.035 | no |
| 11 | Alpha-GPT — Human-AI Interactive Alpha Mining for Quantitative Investment | jkp_proxy_tested | 1 | paper_alpha_gpt_interactive_formula | 0.147 | 0.029 | no |
| 12 | Alpha-GPT 2.0 | jkp_proxy_tested | 1 | paper_alpha_gpt2_full_pipeline | 0.054 | 0.011 | no |
| 13 | Chain-of-Alpha | jkp_proxy_tested | 1 | paper_chain_of_alpha_formula_chain | -0.780 | -0.176 | no |
| 14 | FactorMAD — Multi-Agent Debate for Interpretable Stock Alpha Factor Mining | jkp_proxy_tested | 1 | paper_factormad_debate_interpretable | 0.711 | 0.156 | no |
| 15 | AlphaLogics — Market Logic-Driven Multi-Agent System for Alpha Factor Gener... | jkp_proxy_tested | 1 | alphalogics_value_quality_growth | 0.468 | 0.098 | no |
| 16 | AlphaAgentEvo — Evolution-Oriented Alpha Mining via Self-Evolving Agentic RL | jkp_proxy_tested | 1 | paper_alphaagentevo_evolved_seed | 1.655 | 0.350 | no |
| 17 | FinStep-AI/Alpha-R1 | jkp_proxy_tested | 1 | code_alpha_r1_reasoning_screen | 2.628 | 0.541 | yes |
| 18 | AlphaCrafter — Full-Stack Multi-Agent Framework for Cross-Sectional Quantit... | jkp_proxy_tested | 1 | alphacrafter_full_stack_multifactor | 0.336 | 0.070 | no |
| 19 | LLMFactor — Extracting Profitable Factors through Prompts | jkp_proxy_tested | 1 | paper_llmfactor_explainable_price_news | -0.305 | -0.057 | no |
| 20 | FactorEngine — Program-Level Knowledge-Infused Factor Discovery | jkp_proxy_tested | 1 | paper_factorengine_program_knowledge | 1.437 | 0.313 | no |
| 21 | AlphaPROBE | jkp_proxy_tested | 1 | repo_alphaprobe_dag_diverse_factor_blend | 1.379 | 0.276 | no |
| 22 | DulyHao/AlphaForge, RL-MLDM/alphagen, bettyguo/awesome-llm-trading-agents | jkp_proxy_tested | 2 | code_alphaforge_program_factor | -0.754 | -0.144 | no |
| 23 | TauricResearch/TradingAgents | jkp_proxy_tested | 1 | code_tradingagents_multi_agent | 1.307 | 0.238 | no |
| 24 | ContestTrade — Multi-Agent Trading System Based on Internal Contest Mechanism | jkp_proxy_tested | 1 | contesttrade_internal_contest_trailing_sharpe | 1.111 | 0.247 | no |
| 25 | QuantAgent — Price-Driven Multi-Agent LLMs for High-Frequency Trading | jkp_proxy_tested | 1 | repo_quantagent_hft_price_pattern | -0.545 | -0.117 | no |
| 26 | QuantAgent — Seeking Holy Grail in Trading by Self-Improving LLM | jkp_proxy_tested | 2 | quantagent_three_soldiers_trend | 0.830 | 0.167 | no |
| 27 | AlphaQuanter/AlphaQuanter | jkp_proxy_tested | 1 | code_alphaquanter_tool_orchestrated_rl | 0.298 | 0.058 | no |
| 28 | pipiku915/finmem-llm-stocktrading | jkp_proxy_tested | 1 | code_finmem_memory_trend | 1.175 | 0.212 | no |
| 29 | FinCon — Synthesized LLM Multi-Agent System with Conceptual Verbal Reinforc... | jkp_proxy_tested | 1 | repo_fincon_cvar_risk_controlled_allocator | -0.870 | -0.189 | no |
| 30 | FinAgent — Multimodal Foundation Agent for Financial Trading | jkp_proxy_tested | 1 | paper_finagent_multimodal_generalist | 0.275 | 0.051 | no |
| 31 | FLAG-Trader | jkp_proxy_tested | 1 | paper_flag_trader_gradient_policy | 1.068 | 0.211 | no |
| 32 | MM-DREX — Multimodal-Driven Dynamic Routing of LLM Experts for Financial Tr... | jkp_proxy_tested | 1 | mm_drex_dynamic_router_proxy | 0.216 | 0.038 | no |
| 33 | Trading-R1 — Financial Trading with LLM Reasoning via RL | jkp_proxy_tested | 1 | repo_trading_r1_risk_adjusted_reasoning | 1.461 | 0.275 | no |
| 34 | Janus-Q — Event-Driven Trading via Hierarchical-Gated Reward Modeling | jkp_proxy_tested | 1 | paper_janus_q_event_driven_proxy | -0.480 | -0.096 | no |
| 35 | Trade in Minutes! Rationality-Driven Agentic System for Quantitative Financ... | jkp_proxy_tested | 1 | paper_timi_minutes_technical_proxy | 0.564 | 0.121 | no |
| 36 | AlphaAgents — LLM Multi-Agents for Equity Portfolio Construction | jkp_proxy_tested | 2 | alphaagents_risk_averse_quality_lowrisk | 0.172 | 0.035 | no |
| 37 | MarketSenseAI 2.0 | jkp_proxy_tested | 1 | marketsense_value_momentum_quality | 0.353 | 0.068 | no |
| 38 | MountainLion | jkp_proxy_tested | 1 | paper_mountainlion_multimodal_allocation | 0.511 | 0.092 | no |
| 39 | P1GPT | jkp_proxy_tested | 1 | paper_p1gpt_structured_workflow | 1.433 | 0.290 | no |
| 40 | FinVision | jkp_proxy_tested | 1 | finvision_trend_dip_risk_control | 1.491 | 0.278 | no |
| 41 | Xtra-Computing/CryptoTrade | not_mappable_crypto_not_usa_equity | 0 |  |  |  | no |
| 42 | GuruAgents | jkp_proxy_tested | 6 | guru_buffett_quality_compounder | 2.702 | 0.534 | yes |
| 43 | QuantAgents | jkp_proxy_tested | 1 | paper_quantagents_risk_controlled_system | 2.593 | 0.512 | yes |
| 44 | HedgeAgents | jkp_proxy_tested | 1 | hedgeagents_balanced_lowrisk_alpha | 0.160 | 0.032 | no |
| 45 | AlphaForgeBench — Benchmarking End-to-End Trading Strategy Design with LLMs | jkp_proxy_tested | 1 | repo_alphaforgebench_executable_multifactor | 1.384 | 0.264 | no |
| 46 | LimexAILab/QuantCode-Bench | not_mappable_benchmark_no_strategy | 0 |  |  |  | no |
| 47 | LiveTradeBench — Seeking Real-World Alpha with LLMs | jkp_proxy_tested | 1 | repo_livetradebench_live_allocation_proxy | -0.933 | -0.201 | no |
| 48 | DeepFund | jkp_proxy_tested | 1 | repo_deepfund_prudent_fund_manager | 0.956 | 0.196 | no |
| 49 | HKUDS/AI-Trader | jkp_proxy_tested | 1 | code_ai_trader_value_quality | 2.705 | 0.498 | yes |
| 50 | Open-Finance-Lab/AgenticTrading | jkp_proxy_tested | 1 | code_agentictrading_lab_allocation | 1.762 | 0.355 | no |
| 51 | TradeTrap | jkp_proxy_tested | 1 | repo_tradetrap_robust_safety_proxy | 1.297 | 0.267 | no |
| 52 | virattt/ai-hedge-fund | jkp_proxy_tested | 1 | code_ai_hedge_fund_buffett_munger | 2.419 | 0.538 | yes |
| 53 | HKUDS/Vibe-Trading | jkp_proxy_tested | 1 | code_vibe_trading_prompt_allocation | 1.337 | 0.266 | no |
| 54 | moss-site/moss-trade-bot-skills | not_mappable_tooling_no_strategy | 0 |  |  |  | no |
| 55 | Reported Alpha from LLM Trading Agents Should Not Be ... | not_mappable_no_alpha_strategy | 0 |  |  |  | no |

## What Is Worth Carrying Forward

The papers/repos do not provide convincing new alpha. The pieces worth carrying forward are research-process or portfolio-construction ideas:

1. **Composite sorts before factor construction.** Pre-declared nonlinear combinations such as value + profitability + momentum - risk/investment may be worth testing as portfolio-rule candidates. The null should be that they are just nonlinear repackagings of existing JKP factors.
2. **Dynamic sleeve selection.** Contest-style trailing winner rules are worth testing only with strict walk-forward implementation, turnover accounting, and multiple-testing/reality-check penalties.
3. **LLM-assisted research hygiene.** Some papers describe useful workflow machinery: hypothesis logging, redundancy checks, complexity penalties, decay checks, and reproducible candidate tracking. That is more credible than treating the LLM as an alpha source.
4. **True new text/news construction.** Nothing here beat the existing TextBenchmark in a compelling way. A future paper would need genuinely new firm-month text signals, not agent role-play around old factors.

This evidence is directly relevant for STATE. It supports a hedge-fund-oriented argument that the useful role of LLMs is not unverified strategy invention, but scalable construction of structured, auditable information objects from economically rich source material. In other words, the alpha has to come from a new information set and a disciplined portfolio test, not from giving an agent a familiar factor zoo and asking it to rediscover value-quality-momentum composites.

## Final Conclusion

The tested repositories and papers do **not** contain strong evidence of a new, economically meaningful alpha source for the JKP/TextBenchmark setting. Direct public code did not produce a valid FF5Mom-beating JKP return stream. The in-spirit proxies that looked good against FF5Mom are overwhelmingly traditional characteristic composites. After adding the full JKP132 span and TextBenchmark, only 3 of 62 remain strict positives, which is approximately the number one would expect from 62 tests at a 5% threshold. Even those 3 are highly explained by JKP factors.

The most accurate interpretation is: **these papers are useful as a scan of old factor-combination and research-automation ideas, not as evidence that LLM/agentic repositories discovered new alpha.**

## Reproducibility and Artifacts

Canonical working directory:

```bash
cd ${ALPHA_EVOLVE_REPO}
```

Main rebuild commands:

```bash
.venv/bin/python scripts/build_repository_metrics_report.py
.venv/bin/python scripts/run_paper_idea_jkp_proxies.py
.venv/bin/python scripts/build_paper_derived_replication_ledger.py
.venv/bin/python scripts/run_textbenchmark_performance_analysis.py
```

Main artifacts:

- `paper_runs/REPOSITORY_FF5MOM_METRICS.md`
- `paper_runs/repository_ff5mom_metrics_summary.csv`
- `paper_runs/idea_replications/PAPER_DERIVED_REPLICATION_LEDGER.md`
- `paper_runs/idea_replications/paper_derived_source_replication_ledger.csv`
- `paper_runs/idea_replications/paper_derived_candidate_replication_ledger.csv`
- `paper_runs/idea_replications/jkp_paper_idea_proxies/paper_idea_proxy_ff5mom_summary.csv`
- `paper_runs/idea_replications/jkp_paper_idea_proxies/paper_idea_proxy_all_benchmark_metrics.csv`
- `paper_runs/performance_analysis/textbenchmark/TEXTBENCHMARK_PERFORMANCE_REPORT.md`
- `paper_runs/performance_analysis/textbenchmark/alpha_evolve_textbenchmark_candidate_summary.csv`
- `paper_runs/performance_analysis/textbenchmark/alpha_evolve_textbenchmark_benchmark_metrics.csv`
- `paper_runs/performance_analysis/textbenchmark/alpha_evolve_textbenchmark_book_delta_mvo.csv`
- `paper_runs/RETURN_DATA_SCOPE.md`

## References

- Carhart, Mark M. 1997. "On Persistence in Mutual Fund Performance." *Journal of Finance* 52(1), 57-82.
- Cochrane, John H. 2005. *Asset Pricing*. Revised edition. Princeton University Press.
- Donoho, David. 2024. "Data Science at the Singularity." *Harvard Data Science Review*. arXiv:2310.00865.
- Fama, Eugene F., and Kenneth R. French. 2015. "A Five-Factor Asset Pricing Model." *Journal of Financial Economics* 116(1), 1-22.
- Hellum, Oliver, Theis Ingerslev Jensen, Bryan T. Kelly, and Lasse Heje Pedersen. 2025. "The Power of the Common Task Framework." SSRN 5242901.
- Jensen, Theis Ingerslev, Bryan T. Kelly, and Lasse Heje Pedersen. 2023. "Is There a Replication Crisis in Finance?" *Journal of Finance* 78(5), 2465-2518.
- JKP Factors. 2026. "Global Factor Data." https://jkpfactors.com/.
- Karpathy, Andrej. 2026. "autoresearch: AI agents running research on single-GPU nanochat training automatically." https://github.com/karpathy/autoresearch.
- Kelly, Bryan T., and Dacheng Xiu. 2023. "Financial Machine Learning." NBER Working Paper 31502.
- Kelly, Bryan T., Semyon Malamud, Mohammad Pourmohammadi, and Fabio Trojani. 2023, revised 2025. "Universal Portfolio Shrinkage." NBER Working Paper 32004.
- Markowitz, Harry. 1952. "Portfolio Selection." *Journal of Finance* 7(1), 77-91.
- OpenAI. 2024. "OpenAI o1 System Card." https://openai.com/index/openai-o1-system-card/.
- Google DeepMind. 2026. "Gemini 3.1 Pro Model Card." https://deepmind.google/models/model-cards/gemini-3-1-pro/.
- xAI. 2025. "Grok 4.1 Model Card." https://data.x.ai/2025-11-17-grok-4-1-model-card.pdf.
- Yang, An, et al. 2025. "Qwen3 Technical Report." arXiv:2505.09388.
