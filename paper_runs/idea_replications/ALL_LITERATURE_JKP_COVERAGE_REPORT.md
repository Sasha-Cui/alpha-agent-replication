# All-Literature JKP-USA Coverage and In-Spirit Replication Report

Run completed on 2026-07-04 using only the approved USA-equity data surfaces: `${ALPHA_EVOLVE_JKP_ROOT}` and `${ALPHA_EVOLVE_RETURN_DATA_ROOT}`. No China/A-share returns, external downloaded returns, yfinance data, or paper-shipped equity curves are used for the metrics below.

## Bottom line

- Source inventory: `42` paper rows, `31` code-link rows, `55` unique source reference indices, and `14` cloned repos under `external_repos/`.
- Numeric JKP-USA proxy coverage: `51` of `55` unique source references. The untested unique refs are `41, 46, 54, 55` because they are not mappable to a USA-equity alpha strategy.
- Strategy/proxy evaluations: `62` candidate rows. This exceeds the number of source refs because several papers/repos imply multiple sleeves, and some code-only repos are separate entries.
- Strict FF5Mom beaters: `8` candidates have positive annualized alpha with the configured FF5Mom benchmark test flag.
- Interpretation: this is comprehensive coverage of the local literature/code-link universe in spirit, not a claim that every GitHub repo has a runnable JKP-compatible code path. Many repos are benchmark harnesses, agent scaffolds, or papers without executable stock-selection logic, so the honest replication is an explicitly documented proxy.

## Status counts

| status | rows |
| --- | --- |
| jkp_proxy_tested | 67 |
| supporting_repo_not_strategy | 2 |
| not_mappable_no_alpha_strategy | 1 |
| not_mappable_crypto_not_usa_equity | 1 |
| not_mappable_benchmark_no_strategy | 1 |
| not_mappable_tooling_no_strategy | 1 |

## FF5Mom beaters

| candidate | source ref | Sharpe | alpha ann. | alpha t | IR | appraisal | GRS F | GRS p | span lift |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| repo_alphaagent_decay_resistant_quality | 003 AlphaAgent | 0.796 | 3.86% | 4.264 | 0.890 | 0.890 | 18.044 | 0.0000 | 0.325 |
| code_alpha_r1_reasoning_screen | 017 Alpha-R1 | 0.437 | 1.69% | 2.628 | 0.541 | 0.541 | 6.669 | 0.0103 | 0.131 |
| code_ai_hedge_fund_buffett_munger | 052 ai-hedge-fund | 0.550 | 3.00% | 2.419 | 0.538 | 0.538 | 6.608 | 0.0106 | 0.130 |
| guru_buffett_quality_compounder | 042 GuruAgents | 0.658 | 2.69% | 2.702 | 0.534 | 0.534 | 6.490 | 0.0113 | 0.127 |
| paper_quantagents_risk_controlled_system | 043 QuantAgents | 0.303 | 1.66% | 2.593 | 0.512 | 0.512 | 5.971 | 0.0151 | 0.118 |
| code_ai_trader_value_quality | 049 AI-Trader | 0.436 | 2.28% | 2.705 | 0.498 | 0.498 | 5.644 | 0.0181 | 0.112 |
| code_quantaalpha_self_evolving_factor | 004 QuantaAlpha | 0.463 | 1.71% | 2.357 | 0.495 | 0.495 | 5.587 | 0.0187 | 0.110 |
| guru_equal_weight_style_ensemble | 042 GuruAgents | 0.392 | 1.57% | 2.112 | 0.424 | 0.424 | 4.095 | 0.0439 | 0.082 |

These are mechanical proxy results. The strongest row, `repo_alphaagent_decay_resistant_quality`, is a hand-built accounting-quality/accruals/safety/turnover proxy inspired by AlphaAgent, not a direct execution of that repo discovering the signal on JKP data.

## Non-mappable unique references

- `41`: `not_mappable_crypto_not_usa_equity`. CryptoTrade is crypto-only and outside the user-approved USA-equity JKP universe.
- `46`: `not_mappable_benchmark_no_strategy`. QuantCode-Bench is benchmark/evaluation infrastructure, not a dated stock-selection strategy.
- `54`: `not_mappable_tooling_no_strategy`. moss-trade-bot-skills is bot/tooling skill content, not a standalone alpha strategy.
- `55`: `not_mappable_no_alpha_strategy`. This is a critique of reported LLM-agent alpha, not a proposed alpha strategy.

## Cloned repos checked

`AlphaAgent`, `AlphaBench`, `AlphaForgeBench`, `AlphaPROBE`, `ContestTrade`, `DeepFund`, `FAgent`, `GuruAgents`, `QuantAgent`, `QuantEvolver`, `RD-Agent`, `TradeTrap`, `Trading-R1`, `live-trade-bench`

## Output files

- Coverage CSV: `paper_runs/idea_replications/all_literature_jkp_coverage_summary.csv`
- Candidate FF5Mom summary: `paper_runs/idea_replications/jkp_paper_idea_proxies/paper_idea_proxy_ff5mom_summary.csv`
- Full benchmark metrics: `paper_runs/idea_replications/jkp_paper_idea_proxies/paper_idea_proxy_all_benchmark_metrics.csv`
- Candidate metadata: `paper_runs/idea_replications/jkp_paper_idea_proxies/paper_idea_proxy_metadata.json`

## Paper-link coverage

| source | row | ref | project | repo | status | n | best candidate | Sharpe | alpha ann. | alpha t | IR | GRS F | GRS p | span lift | beats FF5Mom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| paper_links | 1 | 1 | AlphaBench — Benchmarking Large Language Models in Formulaic Alpha Factor Mining |  | jkp_proxy_tested | 1 | repo_alphabench_formulaic_price_volume | -0.029 | -1.51% | -2.183 | -0.454 | 4.704 | 0.0309 | 0.094 | False |
| paper_links | 2 | 2 | EFS — Evolutionary Factor Searching for Sparse Portfolio Optimization Using LLMs |  | jkp_proxy_tested | 3 | efs_short_reversal_low_noise | 0.188 | 1.71% | 1.756 | 0.336 | 2.566 | 0.1102 | 0.052 | False |
| paper_links | 3 | 3 | AlphaAgent — LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay |  | jkp_proxy_tested | 1 | repo_alphaagent_decay_resistant_quality | 0.796 | 3.86% | 4.264 | 0.890 | 18.044 | 0.0000 | 0.325 | True |
| paper_links | 5 | 5 | QuantEvolver — Reinforcement Fine-Tuning for LLM-Based Alpha Factor Discovery |  | jkp_proxy_tested | 1 | repo_quantevolver_return_sharpe_proxy | 0.316 | 0.33% | 0.651 | 0.149 | 0.505 | 0.4778 | 0.010 | False |
| paper_links | 6 | 6 | R&D-Agent-Quant — Multi-Agent Framework for Data-Centric Factors and Model Joint Optimization |  | jkp_proxy_tested | 1 | repo_rd_agent_factor_model_compact_ensemble | -0.027 | -0.64% | -0.789 | -0.180 | 0.740 | 0.3903 | 0.015 | False |
| paper_links | 7 | 7 | Alpha-Jungle — LLM-Powered MCTS for Formulaic Factor Mining |  | jkp_proxy_tested | 2 | alpha_jungle_volatility_compression_trend | 0.249 | 0.38% | 0.593 | 0.109 | 0.269 | 0.6044 | 0.006 | False |
| paper_links | 8 | 8 | FactorMiner — Self-Evolving Agent with Skills and Experience Memory for Financial Alpha Discovery |  | jkp_proxy_tested | 1 | paper_factorminer_memory_diverse_library | 0.422 | 1.32% | 1.731 | 0.377 | 3.242 | 0.0728 | 0.065 | False |
| paper_links | 9 | 9 | CogAlpha — Cognitive Alpha Mining via LLM-Driven Code-Based Evolution |  | jkp_proxy_tested | 1 | paper_cogalpha_code_evolved_hybrid | 0.296 | 0.89% | 1.319 | 0.272 | 1.683 | 0.1955 | 0.034 | False |
| paper_links | 10 | 10 | FAMA — Factor Mining Agent |  | jkp_proxy_tested | 1 | fama_value_momentum_interpretable | 0.433 | -0.13% | -0.184 | -0.035 | 0.028 | 0.8676 | 0.001 | False |
| paper_links | 11 | 11 | Alpha-GPT — Human-AI Interactive Alpha Mining for Quantitative Investment |  | jkp_proxy_tested | 1 | paper_alpha_gpt_interactive_formula | 0.365 | 0.13% | 0.147 | 0.029 | 0.019 | 0.8905 | 0.000 | False |
| paper_links | 12 | 12 | Alpha-GPT 2.0 |  | jkp_proxy_tested | 1 | paper_alpha_gpt2_full_pipeline | 0.161 | 0.04% | 0.054 | 0.011 | 0.003 | 0.9582 | 0.000 | False |
| paper_links | 13 | 13 | Chain-of-Alpha |  | jkp_proxy_tested | 1 | paper_chain_of_alpha_formula_chain | 0.050 | -0.84% | -0.780 | -0.176 | 0.707 | 0.4011 | 0.015 | False |
| paper_links | 14 | 14 | FactorMAD — Multi-Agent Debate for Interpretable Stock Alpha Factor Mining |  | jkp_proxy_tested | 1 | paper_factormad_debate_interpretable | 0.305 | 0.59% | 0.711 | 0.156 | 0.557 | 0.4562 | 0.012 | False |
| paper_links | 15 | 15 | AlphaLogics — Market Logic-Driven Multi-Agent System for Alpha Factor Generation |  | jkp_proxy_tested | 1 | alphalogics_value_quality_growth | 0.192 | 0.49% | 0.468 | 0.098 | 0.220 | 0.6394 | 0.005 | False |
| paper_links | 16 | 16 | AlphaAgentEvo — Evolution-Oriented Alpha Mining via Self-Evolving Agentic RL |  | jkp_proxy_tested | 1 | paper_alphaagentevo_evolved_seed | 0.425 | 1.14% | 1.655 | 0.350 | 2.793 | 0.0957 | 0.057 | False |
| paper_links | 18 | 18 | AlphaCrafter — Full-Stack Multi-Agent Framework for Cross-Sectional Quantitative Trading |  | jkp_proxy_tested | 1 | alphacrafter_full_stack_multifactor | 0.237 | 0.25% | 0.336 | 0.070 | 0.113 | 0.7367 | 0.002 | False |
| paper_links | 19 | 19 | LLMFactor — Extracting Profitable Factors through Prompts |  | jkp_proxy_tested | 1 | paper_llmfactor_explainable_price_news | 0.137 | -0.24% | -0.305 | -0.057 | 0.075 | 0.7844 | 0.002 | False |
| paper_links | 20 | 20 | FactorEngine — Program-Level Knowledge-Infused Factor Discovery |  | jkp_proxy_tested | 1 | paper_factorengine_program_knowledge | 0.183 | 1.10% | 1.437 | 0.313 | 2.231 | 0.1363 | 0.045 | False |
| paper_links | 21 | 21 | AlphaPROBE |  | jkp_proxy_tested | 1 | repo_alphaprobe_dag_diverse_factor_blend | 0.450 | 1.52% | 1.379 | 0.276 | 1.741 | 0.1880 | 0.036 | False |
| paper_links | 24 | 24 | ContestTrade — Multi-Agent Trading System Based on Internal Contest Mechanism |  | jkp_proxy_tested | 1 | contesttrade_internal_contest_trailing_sharpe | 0.548 | 1.43% | 1.111 | 0.247 | 1.285 | 0.2579 | 0.029 | False |
| paper_links | 25 | 25 | QuantAgent — Price-Driven Multi-Agent LLMs for High-Frequency Trading |  | jkp_proxy_tested | 1 | repo_quantagent_hft_price_pattern | 0.029 | -0.65% | -0.545 | -0.117 | 0.314 | 0.5756 | 0.007 | False |
| paper_links | 26 | 26 | QuantAgent — Seeking Holy Grail in Trading by Self-Improving LLM |  | jkp_proxy_tested | 2 | quantagent_three_soldiers_trend | 0.215 | 0.87% | 0.830 | 0.167 | 0.639 | 0.4246 | 0.013 | False |
| paper_links | 29 | 29 | FinCon — Synthesized LLM Multi-Agent System with Conceptual Verbal Reinforcement |  | jkp_proxy_tested | 1 | repo_fincon_cvar_risk_controlled_allocator | 0.599 | -0.66% | -0.870 | -0.189 | 0.816 | 0.3670 | 0.017 | False |
| paper_links | 30 | 30 | FinAgent — Multimodal Foundation Agent for Financial Trading |  | jkp_proxy_tested | 1 | paper_finagent_multimodal_generalist | 0.650 | 0.12% | 0.275 | 0.051 | 0.060 | 0.8065 | 0.001 | False |
| paper_links | 31 | 31 | FLAG-Trader |  | jkp_proxy_tested | 1 | paper_flag_trader_gradient_policy | 0.235 | 0.79% | 1.068 | 0.211 | 1.017 | 0.3141 | 0.021 | False |
| paper_links | 32 | 32 | MM-DREX — Multimodal-Driven Dynamic Routing of LLM Experts for Financial Trading |  | jkp_proxy_tested | 1 | mm_drex_dynamic_router_proxy | 0.185 | 0.15% | 0.216 | 0.038 | 0.033 | 0.8550 | 0.001 | False |
| paper_links | 33 | 33 | Trading-R1 — Financial Trading with LLM Reasoning via RL |  | jkp_proxy_tested | 1 | repo_trading_r1_risk_adjusted_reasoning | 0.305 | 1.13% | 1.461 | 0.275 | 1.719 | 0.1908 | 0.035 | False |
| paper_links | 34 | 34 | Janus-Q — Event-Driven Trading via Hierarchical-Gated Reward Modeling |  | jkp_proxy_tested | 1 | paper_janus_q_event_driven_proxy | 0.011 | -0.48% | -0.480 | -0.096 | 0.211 | 0.6460 | 0.004 | False |
| paper_links | 35 | 35 | Trade in Minutes! Rationality-Driven Agentic System for Quantitative Financial Trading |  | jkp_proxy_tested | 1 | paper_timi_minutes_technical_proxy | 0.229 | 0.63% | 0.564 | 0.121 | 0.333 | 0.5643 | 0.007 | False |
| paper_links | 36 | 36 | AlphaAgents — LLM Multi-Agents for Equity Portfolio Construction |  | jkp_proxy_tested | 2 | alphaagents_risk_averse_quality_lowrisk | 0.065 | 0.13% | 0.172 | 0.035 | 0.028 | 0.8677 | 0.001 | False |
| paper_links | 37 | 37 | MarketSenseAI 2.0 |  | jkp_proxy_tested | 1 | marketsense_value_momentum_quality | 0.256 | 0.29% | 0.353 | 0.068 | 0.107 | 0.7442 | 0.002 | False |
| paper_links | 38 | 38 | MountainLion |  | jkp_proxy_tested | 1 | paper_mountainlion_multimodal_allocation | 0.211 | 0.33% | 0.511 | 0.092 | 0.194 | 0.6603 | 0.004 | False |
| paper_links | 39 | 39 | P1GPT |  | jkp_proxy_tested | 1 | paper_p1gpt_structured_workflow | 0.395 | 1.15% | 1.433 | 0.290 | 1.912 | 0.1678 | 0.039 | False |
| paper_links | 40 | 40 | FinVision |  | jkp_proxy_tested | 1 | finvision_trend_dip_risk_control | 0.340 | 1.24% | 1.491 | 0.278 | 1.756 | 0.1861 | 0.036 | False |
| paper_links | 42 | 42 | GuruAgents |  | jkp_proxy_tested | 6 | guru_buffett_quality_compounder | 0.658 | 2.69% | 2.702 | 0.534 | 6.490 | 0.0113 | 0.127 | True |
| paper_links | 43 | 43 | QuantAgents |  | jkp_proxy_tested | 1 | paper_quantagents_risk_controlled_system | 0.303 | 1.66% | 2.593 | 0.512 | 5.971 | 0.0151 | 0.118 | True |
| paper_links | 44 | 44 | HedgeAgents |  | jkp_proxy_tested | 1 | hedgeagents_balanced_lowrisk_alpha | 0.015 | 0.12% | 0.160 | 0.032 | 0.023 | 0.8793 | 0.000 | False |
| paper_links | 45 | 45 | AlphaForgeBench — Benchmarking End-to-End Trading Strategy Design with LLMs |  | jkp_proxy_tested | 1 | repo_alphaforgebench_executable_multifactor | 0.317 | 0.88% | 1.384 | 0.264 | 1.593 | 0.2079 | 0.033 | False |
| paper_links | 47 | 47 | LiveTradeBench — Seeking Real-World Alpha with LLMs |  | jkp_proxy_tested | 1 | repo_livetradebench_live_allocation_proxy | 0.606 | -0.54% | -0.933 | -0.201 | 0.918 | 0.3388 | 0.019 | False |
| paper_links | 48 | 48 | DeepFund |  | jkp_proxy_tested | 1 | repo_deepfund_prudent_fund_manager | 0.784 | 0.67% | 0.956 | 0.196 | 0.878 | 0.3494 | 0.018 | False |
| paper_links | 51 | 51 | TradeTrap |  | jkp_proxy_tested | 1 | repo_tradetrap_robust_safety_proxy | 0.166 | 0.92% | 1.297 | 0.267 | 1.625 | 0.2034 | 0.033 | False |
| paper_links | 55 | 55 | Reported Alpha from LLM Trading Agents Should Not Be ... |  | not_mappable_no_alpha_strategy | 0 |  |  |  |  |  |  |  |  | False |

## Code-link coverage

| source | row | ref | project | repo | status | n | best candidate | Sharpe | alpha ann. | alpha t | IR | GRS F | GRS p | span lift | beats FF5Mom |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| code_links | 1 | 17 | Alpha-R1 — Alpha Screening with LLM Reasoning via Reinforcement Learning | FinStep-AI/Alpha-R1 | jkp_proxy_tested | 1 | code_alpha_r1_reasoning_screen | 0.437 | 1.69% | 2.628 | 0.541 | 6.669 | 0.0103 | 0.131 | True |
| code_links | 2 |  | AlphaAgent — LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay | RndmVariableQ/AlphaAgent | jkp_proxy_tested | 1 | repo_alphaagent_decay_resistant_quality | 0.796 | 3.86% | 4.264 | 0.890 | 18.044 | 0.0000 | 0.325 | True |
| code_links | 3 |  | AlphaBench — Benchmarking Large Language Models in Formulaic Alpha Factor Mining | CityU-MLO/AlphaBench | jkp_proxy_tested | 1 | repo_alphabench_formulaic_price_volume | -0.029 | -1.51% | -2.183 | -0.454 | 4.704 | 0.0309 | 0.094 | False |
| code_links | 4 | 22 | AlphaForge | bettyguo/awesome-llm-trading-agents | supporting_repo_not_strategy | 0 |  |  |  |  |  |  |  |  | False |
| code_links | 5 |  | AlphaForge | DulyHao/AlphaForge | jkp_proxy_tested | 1 | code_alphaforge_program_factor | 0.169 | -0.48% | -0.754 | -0.144 | 0.473 | 0.4923 | 0.010 | False |
| code_links | 6 | 22 | AlphaGen | bettyguo/awesome-llm-trading-agents | supporting_repo_not_strategy | 0 |  |  |  |  |  |  |  |  | False |
| code_links | 7 |  | AlphaGen | RL-MLDM/alphagen | jkp_proxy_tested | 1 | code_alphagen_symbolic_factor | 0.170 | 0.14% | 0.144 | 0.032 | 0.024 | 0.8771 | 0.000 | False |
| code_links | 8 |  | AlphaPROBE | gta0804/AlphaPROBE | jkp_proxy_tested | 1 | repo_alphaprobe_dag_diverse_factor_blend | 0.450 | 1.52% | 1.379 | 0.276 | 1.741 | 0.1880 | 0.036 | False |
| code_links | 9 | 4 | QuantaAlpha — LLM-Driven Self-Evolving Framework for Factor Mining | QuantaAlpha/QuantaAlpha | jkp_proxy_tested | 1 | code_quantaalpha_self_evolving_factor | 0.463 | 1.71% | 2.357 | 0.495 | 5.587 | 0.0187 | 0.110 | True |
| code_links | 10 |  | QuantEvolver — Reinforcement Fine-Tuning for LLM-Based Alpha Factor Discovery | QuantLLM/QuantEvolver | jkp_proxy_tested | 1 | repo_quantevolver_return_sharpe_proxy | 0.316 | 0.33% | 0.651 | 0.149 | 0.505 | 0.4778 | 0.010 | False |
| code_links | 11 |  | R&D-Agent-Quant — Multi-Agent Framework for Data-Centric Factors and Model Joint Optimization | microsoft/RD-Agent | jkp_proxy_tested | 1 | repo_rd_agent_factor_model_compact_ensemble | -0.027 | -0.64% | -0.789 | -0.180 | 0.740 | 0.3903 | 0.015 | False |
| code_links | 12 | 27 | AlphaQuanter — End-to-End Tool-Orchestrated Agentic RL for Stock Trading | AlphaQuanter/AlphaQuanter | jkp_proxy_tested | 1 | code_alphaquanter_tool_orchestrated_rl | 0.217 | 0.22% | 0.298 | 0.058 | 0.077 | 0.7809 | 0.002 | False |
| code_links | 13 |  | ContestTrade — Multi-Agent Trading System Based on Internal Contest Mechanism | FinStep-AI/ContestTrade | jkp_proxy_tested | 1 | contesttrade_internal_contest_trailing_sharpe | 0.548 | 1.43% | 1.111 | 0.247 | 1.285 | 0.2579 | 0.029 | False |
| code_links | 14 | 41 | CryptoTrade | Xtra-Computing/CryptoTrade | not_mappable_crypto_not_usa_equity | 0 |  |  |  |  |  |  |  |  | False |
| code_links | 15 |  | FinCon — Synthesized LLM Multi-Agent System with Conceptual Verbal Reinforcement | MXGao-A/FAgent | jkp_proxy_tested | 1 | repo_fincon_cvar_risk_controlled_allocator | 0.599 | -0.66% | -0.870 | -0.189 | 0.816 | 0.3670 | 0.017 | False |
| code_links | 16 |  | FinCon — Synthesized LLM Multi-Agent System with Conceptual Verbal Reinforcement | The-FinAI/FinCon | jkp_proxy_tested | 1 | repo_fincon_cvar_risk_controlled_allocator | 0.599 | -0.66% | -0.870 | -0.189 | 0.816 | 0.3670 | 0.017 | False |
| code_links | 17 | 28 | FinMem — LLM Trading Agent with Layered Memory and Character Design | pipiku915/finmem-llm-stocktrading | jkp_proxy_tested | 1 | code_finmem_memory_trend | 0.270 | 0.93% | 1.175 | 0.212 | 1.021 | 0.3130 | 0.021 | False |
| code_links | 18 |  | GuruAgents | yejining99/GuruAgents | jkp_proxy_tested | 6 | guru_buffett_quality_compounder | 0.658 | 2.69% | 2.702 | 0.534 | 6.490 | 0.0113 | 0.127 | True |
| code_links | 19 |  | QuantAgent — Price-Driven Multi-Agent LLMs for High-Frequency Trading | Y-Research-SBU/QuantAgent | jkp_proxy_tested | 1 | repo_quantagent_hft_price_pattern | 0.029 | -0.65% | -0.545 | -0.117 | 0.314 | 0.5756 | 0.007 | False |
| code_links | 20 | 23 | TradingAgents — Multi-Agents LLM Financial Trading Framework | TauricResearch/TradingAgents | jkp_proxy_tested | 1 | code_tradingagents_multi_agent | 0.236 | 0.78% | 1.307 | 0.238 | 1.295 | 0.2561 | 0.027 | False |
| code_links | 21 | 50 | AgenticTrading Lab | Open-Finance-Lab/AgenticTrading | jkp_proxy_tested | 1 | code_agentictrading_lab_allocation | 0.308 | 1.12% | 1.762 | 0.355 | 2.876 | 0.0909 | 0.058 | False |
| code_links | 22 | 49 | AI-Trader | HKUDS/AI-Trader | jkp_proxy_tested | 1 | code_ai_trader_value_quality | 0.436 | 2.28% | 2.705 | 0.498 | 5.644 | 0.0181 | 0.112 | True |
| code_links | 23 |  | AlphaForgeBench — Benchmarking End-to-End Trading Strategy Design with LLMs | finbrain-lab-hkustgz/AlphaForgeBench | jkp_proxy_tested | 1 | repo_alphaforgebench_executable_multifactor | 0.317 | 0.88% | 1.384 | 0.264 | 1.593 | 0.2079 | 0.033 | False |
| code_links | 24 |  | DeepFund | HKUSTDial/DeepFund | jkp_proxy_tested | 1 | repo_deepfund_prudent_fund_manager | 0.784 | 0.67% | 0.956 | 0.196 | 0.878 | 0.3494 | 0.018 | False |
| code_links | 25 |  | LiveTradeBench — Seeking Real-World Alpha with LLMs | ulab-uiuc/live-trade-bench | jkp_proxy_tested | 1 | repo_livetradebench_live_allocation_proxy | 0.606 | -0.54% | -0.933 | -0.201 | 0.918 | 0.3388 | 0.019 | False |
| code_links | 26 | 46 | QuantCode-Bench | LimexAILab/QuantCode-Bench | not_mappable_benchmark_no_strategy | 0 |  |  |  |  |  |  |  |  | False |
| code_links | 27 |  | TradeTrap | Yanlewen/TradeTrap | jkp_proxy_tested | 1 | repo_tradetrap_robust_safety_proxy | 0.166 | 0.92% | 1.297 | 0.267 | 1.625 | 0.2034 | 0.033 | False |
| code_links | 28 | 53 | HKUDS/Vibe-Trading | HKUDS/Vibe-Trading | jkp_proxy_tested | 1 | code_vibe_trading_prompt_allocation | 0.254 | 0.80% | 1.337 | 0.266 | 1.618 | 0.2043 | 0.033 | False |
| code_links | 29 | 54 | moss-site/moss-trade-bot-skills | moss-site/moss-trade-bot-skills | not_mappable_tooling_no_strategy | 0 |  |  |  |  |  |  |  |  | False |
| code_links | 30 | 50 | Open-Finance-Lab/AgenticTrading | Open-Finance-Lab/AgenticTrading | jkp_proxy_tested | 1 | code_agentictrading_lab_allocation | 0.308 | 1.12% | 1.762 | 0.355 | 2.876 | 0.0909 | 0.058 | False |
| code_links | 31 | 52 | virattt/ai-hedge-fund | virattt/ai-hedge-fund | jkp_proxy_tested | 1 | code_ai_hedge_fund_buffett_munger | 0.550 | 3.00% | 2.419 | 0.538 | 6.608 | 0.0106 | 0.130 | True |

## Candidate formulas

| candidate | source ref | strategy | proxy formula | idea |
| --- | --- | --- | --- | --- |
| repo_alphabench_formulaic_price_volume | 001 AlphaBench | long_short_decile_value_weighted | rank(ret_12_1)+rank(ret_6_1)+rank(rmax5_rvol_21d)+rank(dolvol_126d)-rank(rvol_252d)-rank(turnover_var_126d) | AlphaBench frames LLM alpha mining as formula generation from price and volume operators, then portfolio evaluation by Sharpe and related metrics. |
| efs_momentum_low_vol_breakout | 002 EFS | long_short_decile_value_weighted | rank(ret_3_1)+rank(ret_6_1)+rank(ret_12_1)-rank(rvol_21d)-rank(rvol_252d)+rank(rmax5_rvol_21d) | EFS appendix describes evolved factors combining momentum, mean return, low volatility/stability, and breakout logic. |
| efs_short_reversal_low_noise | 002 EFS | long_short_decile_value_weighted | -rank(ret_1_0)-rank(rvol_21d)+rank(qmj_safety) | EFS discusses regime shifts toward mean reversion and downside/noise filtering in sideways markets. |
| efs_sparse_top5_momentum_low_vol | 002 EFS | long_only_top5_equal_weighted | top5 equal-weight long-only excess return from efs_momentum_low_vol_breakout score | EFS uses sparse top scoring asset selection; this tests a literal sparse top-5 proxy using the momentum/low-volatility score. |
| repo_alphaagent_decay_resistant_quality | 003 AlphaAgent | long_short_decile_value_weighted | rank(ope_be)+rank(ocf_me)+rank(qmj_safety)+rank(at_turnover)-rank(oaccruals_at)-rank(eqnetis_me)-rank(debt_gr1) | AlphaAgent regularizes LLM factor search for originality, hypothesis consistency, and complexity control to counter alpha decay and crowding. |
| code_quantaalpha_self_evolving_factor | 004 QuantaAlpha | long_short_decile_value_weighted | rank(ret_12_1)+rank(ope_be)+rank(gp_me)+rank(qmj)-rank(rvol_252d)-rank(debt_at) | QuantaAlpha is listed as an LLM-driven self-evolving framework for factor mining. |
| repo_quantevolver_return_sharpe_proxy | 005 QuantEvolver | long_short_decile_value_weighted | ret_12_1 / abs(rvol_252d) | QuantEvolver uses executable seed expressions and reinforcement fine-tuning; this row repeats its risk-adjusted momentum seed in the unified in-spirit table. |
| repo_rd_agent_factor_model_compact_ensemble | 006 R&D-Agent-Quant | long_short_decile_value_weighted | rank(be_me)+rank(ope_be)+rank(gp_me)+rank(ret_12_1)-rank(rvol_252d)-rank(beta_252d)-rank(at_gr1) | R&D-Agent-Quant presents a data-centric factor/model co-optimization loop aiming for compact, robust factor sets rather than one-off generated alphas. |
| alpha_jungle_price_volume_momentum | 007 Alpha-Jungle | long_short_decile_value_weighted | rank(ret_3_1)+rank(turnover_126d)+rank(dolvol_126d)-rank(turnover_var_126d) | Alpha-Jungle examples combine price percentage change, volume, volatility, and formula diversity in an MCTS alpha search. |
| alpha_jungle_volatility_compression_trend | 007 Alpha-Jungle | long_short_decile_value_weighted | rank(ret_3_1)+rank(ret_12_1)-rank(rvol_21d)-rank(ivol_capm_21d) | Alpha-Jungle examples include moving-average price changes and standard-deviation operators; this proxy tests trend after volatility compression. |
| paper_factorminer_memory_diverse_library | 008 FactorMiner | long_short_decile_value_weighted | rank(ret_12_1)+rank(be_me)+rank(ope_be)+rank(qmj_safety)+rank(at_turnover)-rank(rvol_252d)-rank(debt_at)-rank(eqnetis_me) | FactorMiner uses modular skills and experience memory to build a diverse low-redundancy library of formulaic alpha factors. |
| paper_cogalpha_code_evolved_hybrid | 009 CogAlpha | long_short_decile_value_weighted | rank(ret_12_1)+rank(ret_3_1)+rank(dolvol_126d)+rank(qmj)-rank(bidaskhl_21d)-rank(rvol_252d)-rank(turnover_var_126d) | CogAlpha represents alphas as executable code and evolves diverse economically interpretable signals through a multi-agent quality-checking hierarchy. |
| fama_value_momentum_interpretable | 010 FAMA | long_short_decile_value_weighted | rank(be_me)+rank(ret_12_1)+rank(ope_be)-rank(market_equity) | FAMA mines interpretable financial factors and cites momentum-style financial principles; this proxy tests a simple interpretable value/momentum/profitability factor. |
| paper_alpha_gpt_interactive_formula | 011 Alpha-GPT | long_short_decile_value_weighted | rank(be_me)+rank(ret_12_1)+rank(ope_be)+rank(gp_me)-rank(debt_at) | Alpha-GPT is a human-AI interactive formulaic alpha mining system that summarizes and modifies top-performing symbolic alphas. |
| paper_alpha_gpt2_full_pipeline | 012 Alpha-GPT 2.0 | long_short_decile_value_weighted | rank(be_me)+rank(ret_12_1)+rank(qmj)+rank(sale_gr1)-rank(rvol_252d)-rank(beta_252d) | Alpha-GPT 2.0 expands interactive alpha mining into alpha modeling and analysis over a full quantitative investment workflow. |
| paper_chain_of_alpha_formula_chain | 013 Chain-of-Alpha | long_short_decile_value_weighted | rank(ret_12_1)-rank(ret_1_0)+rank(rmax5_rvol_21d)+rank(turnover_126d)-rank(rvol_252d) | Chain-of-Alpha is described as chained formula generation and optimization using market data and backtest feedback. |
| paper_factormad_debate_interpretable | 014 FactorMAD | long_short_decile_value_weighted | rank(be_me)+rank(ope_be)+rank(qmj_safety)+rank(ret_12_1)-rank(debt_at)-rank(rvol_252d) | FactorMAD is a multi-agent debate framework for interpretable stock alpha factor mining. |
| alphalogics_value_quality_growth | 015 AlphaLogics | long_short_decile_value_weighted | rank(be_me)+rank(ope_be)+rank(gp_me)+rank(sale_gr1)-rank(debt_at) | AlphaLogics emphasizes market-logic-driven, interpretable factor generation; this proxy tests value, quality, growth, and leverage logic. |
| paper_alphaagentevo_evolved_seed | 016 AlphaAgentEvo | long_short_decile_value_weighted | rank(ret_12_1)+rank(ret_6_1)+rank(ope_be)+rank(qmj_safety)-rank(rvol_252d)-rank(at_gr1)-rank(eqnetis_me) | AlphaAgentEvo frames alpha mining as self-evolving agentic reinforcement learning that refines seed alphas through reward-guided trajectories. |
| code_alpha_r1_reasoning_screen | 017 Alpha-R1 | long_short_decile_value_weighted | rank(qmj)+rank(ope_be)+rank(ret_12_1)-rank(debt_at)-rank(rvol_252d) | Alpha-R1 is listed as alpha screening with LLM reasoning via reinforcement learning. |
| alphacrafter_full_stack_multifactor | 018 AlphaCrafter | long_short_decile_value_weighted | rank(be_me)+rank(ope_be)+rank(ret_12_1)+rank(qmj)-rank(at_gr1)-rank(rvol_252d) | AlphaCrafter combines mined factors, regime screening, and risk-constrained trading; this proxy tests a diversified value-quality-momentum-low-risk factor ensemble. |
| paper_llmfactor_explainable_price_news | 019 LLMFactor | long_short_decile_value_weighted | rank(ret_12_1)+rank(sale_gr1)+rank(gp_me)+rank(dolvol_126d)-rank(rvol_252d) | LLMFactor extracts explainable factors from text/news and historical prices to predict stock movement. |
| paper_factorengine_program_knowledge | 020 FactorEngine | long_short_decile_value_weighted | rank(be_me)+rank(ope_be)+rank(gp_me)+rank(ocf_me)-rank(oaccruals_at)-rank(debt_at)-rank(at_gr1) | FactorEngine turns domain knowledge and reports into executable factor programs, with closed-loop verification and portfolio feedback. |
| repo_alphaprobe_dag_diverse_factor_blend | 021 AlphaPROBE | long_short_decile_value_weighted | rank(ret_12_1)-rank(ret_1_0)+rank(be_me)+rank(ope_be)+rank(qmj_safety)+rank(turnover_126d)-rank(rvol_252d)-rank(debt_at) | AlphaPROBE treats alpha mining as DAG-guided factor evolution, selecting promising parents while preserving factor-pool diversity and stability. |
| code_alphaforge_program_factor | 022 AlphaForge | long_short_decile_value_weighted | rank(be_me)+rank(ret_12_1)+rank(ope_be)+rank(dolvol_126d)-rank(rvol_252d) | AlphaForge is listed as an implementation repo for LLM-assisted factor/strategy generation. |
| code_alphagen_symbolic_factor | 022 AlphaGen | long_short_decile_value_weighted | rank(ret_12_1)-rank(ret_1_0)+rank(be_me)+rank(ope_be)-rank(rvol_252d) | AlphaGen is a symbolic alpha generation/search repo listed in the source table. |
| code_tradingagents_multi_agent | 023 TradingAgents | long_short_decile_value_weighted | rank(ret_12_1)+rank(dolvol_126d)+rank(qmj_safety)+rank(sale_gr1)-rank(rvol_252d)-rank(beta_252d) | TradingAgents is a multi-agent LLM financial trading framework with analyst/trader/risk-style roles. |
| contesttrade_internal_contest_trailing_sharpe | 024 ContestTrade | meta_sleeve_selection_trailing_sharpe | monthly winner among idea sleeves by trailing 36m Sharpe, min 24m history | ContestTrade uses an internal contest/ranking mechanism among agents. This proxy selects the JKP idea sleeve with the best trailing 36-month realized Sharpe using only past generated JKP returns. |
| repo_quantagent_hft_price_pattern | 025 QuantAgent HFT | long_short_decile_value_weighted | rank(ret_1_0)+rank(ret_3_1)+rank(rmax1_21d)+rank(rmax5_rvol_21d)+rank(turnover_126d)-rank(bidaskhl_21d)-rank(rvol_21d) | QuantAgent is a price-driven multi-agent HFT system centered on short-horizon technical indicators, chart patterns, trend state, and risk-aware execution. |
| quantagent_three_soldiers_trend | 026 QuantAgent Holy Grail | long_short_decile_value_weighted | rank(ret_1_0)+rank(ret_3_1)+rank(turnover_126d)-rank(rvol_21d) | QuantAgent appendix includes ThreeSoldier candlestick-style trend continuation signals with volume/body-size confirmation. |
| quantagent_volatility_breakout | 026 QuantAgent Holy Grail | long_short_decile_value_weighted | rank(rmax5_rvol_21d)+rank(ret_1_0)+rank(ret_3_1)-rank(rvol_21d) | QuantAgent appendix includes a VolatilityBreakoutSignal based on high breaking above a threshold relative to ATR. |
| code_alphaquanter_tool_orchestrated_rl | 027 AlphaQuanter | long_short_decile_value_weighted | rank(ret_3_1)+rank(ret_12_1)+rank(turnover_126d)-rank(rvol_21d)-rank(beta_252d) | AlphaQuanter is listed as an end-to-end tool-orchestrated agentic RL stock trading system. |
| code_finmem_memory_trend | 028 FinMem | long_short_decile_value_weighted | rank(ret_12_1)-rank(ret_1_0)+rank(qmj_safety)+rank(cash_at)-rank(rvol_252d) | FinMem is listed as an LLM trading agent with layered memory and character design. |
| repo_fincon_cvar_risk_controlled_allocator | 029 FinCon | long_only_top_decile_value_weighted | long-only top decile by rank(ret_12_1)+rank(ope_be)+rank(qmj_safety)+rank(dolvol_126d)-rank(rvol_252d)-rank(beta_252d)-rank(betadown_252d) | FinCon uses manager/analyst hierarchy plus dual-level risk control, including CVaR-style monitoring, for portfolio decisions. |
| paper_finagent_multimodal_generalist | 030 FinAgent | long_only_top_decile_value_weighted | long-only top decile by rank(qmj)+rank(ret_12_1)+rank(dolvol_126d)+rank(cash_at)-rank(rvol_252d)-rank(beta_252d)-rank(debt_at) | FinAgent is a multimodal, tool-augmented generalist trading agent with diversified trading and risk-aware tool use. |
| paper_flag_trader_gradient_policy | 031 FLAG-Trader | long_short_decile_value_weighted | rank(ret_3_1)+rank(ret_12_1)-rank(ret_1_0)+rank(qmj_safety)-rank(rvol_21d)-rank(beta_252d) | FLAG-Trader fuses LLM agents with gradient/RL-style policy optimization for sequential trading decisions. |
| mm_drex_dynamic_router_proxy | 032 MM-DREX | long_short_decile_value_weighted | rank(ret_12_1)-rank(ret_1_0)+rank(rmax5_rvol_21d)-rank(rvol_21d)+rank(qmj_safety) | MM-DREX dynamically routes trend, reversal, breakout, and risk/positioning experts. |
| repo_trading_r1_risk_adjusted_reasoning | 033 Trading-R1 | long_short_decile_value_weighted | rank(ret_3_1)+rank(ret_12_1)-rank(ret_1_0)+rank(qmj_safety)-rank(rvol_21d)-rank(rmax5_21d) | Trading-R1 frames trading as reasoning/RL over market state and rewards; the JKP proxy tests a risk-adjusted trend/reversal reward signal. |
| paper_janus_q_event_driven_proxy | 034 Janus-Q | long_short_decile_value_weighted | rank(rmax5_rvol_21d)+rank(ret_1_0)+rank(turnover_126d)+rank(qmj_safety)-rank(rvol_21d)-rank(bidaskhl_21d) | Janus-Q is an event-driven trading framework that models heterogeneous event impact and optimizes reward-gated trading decisions. |
| paper_timi_minutes_technical_proxy | 035 Trade in Minutes | long_short_decile_value_weighted | rank(ret_1_0)+rank(ret_3_1)+rank(rmax1_21d)+rank(turnover_126d)-rank(rvol_21d)-rank(bidaskhl_21d) | Trade in Minutes decouples strategy development from rapid execution, using technical indicators, strategy adaptation, and risk control in volatile markets. |
| alphaagents_risk_averse_quality_lowrisk | 036 AlphaAgents | long_short_decile_value_weighted | rank(qmj)+rank(ope_be)+rank(be_me)-rank(rvol_252d)-rank(beta_252d)-rank(debt_at) | AlphaAgents risk-averse portfolios emphasize lower volatility and stable fundamentals. |
| alphaagents_risk_neutral_fundamental_momentum | 036 AlphaAgents | long_short_decile_value_weighted | rank(ret_12_1)+rank(sale_gr1)+rank(ope_be)+rank(be_me) | AlphaAgents risk-neutral portfolios emphasize valuation plus fundamentals/growth/momentum. |
| marketsense_value_momentum_quality | 037 MarketSenseAI 2.0 | long_short_decile_value_weighted | rank(be_me)+rank(ret_12_1)+rank(qmj)+rank(sale_gr1) | MarketSenseAI factor analysis discusses value and momentum loadings, with fundamentals and price dynamics reinforcing selection. |
| paper_mountainlion_multimodal_allocation | 038 MountainLion | long_short_decile_value_weighted | rank(ret_12_1)+rank(qmj)+rank(qmj_safety)+rank(sale_gr1)-rank(rvol_252d)-rank(beta_252d) | MountainLion coordinates multimodal RAG agents for price forecasting, news-driven reasoning, risk evaluation, and strategic allocation. |
| paper_p1gpt_structured_workflow | 039 P1GPT | long_short_decile_value_weighted | rank(ret_12_1)+rank(be_me)+rank(ope_be)+rank(sale_gr1)+rank(qmj_safety)-rank(rvol_252d)-rank(debt_at) | P1GPT fuses technical, fundamental, news, and sectoral analysis through a layered multi-agent workflow with embedded risk assessment. |
| finvision_trend_dip_risk_control | 040 FinVision | long_short_decile_value_weighted | rank(ret_12_1)-rank(ret_1_0)-rank(rvol_21d)+rank(qmj_safety) | FinVision prompts prioritize holding strong upward trends, buying dips within uptrends, and risk management. |
| guru_altman_distress_avoidance | 042 GuruAgents | long_short_decile_value_weighted | rank(ebitda_debt)+rank(cash_at)+rank(ni_me)-rank(debt_at)-rank(rvol_252d)-rank(betadown_252d) | Edward Altman-style distress avoidance: earnings/cash/debt coverage and downside-risk control. |
| guru_buffett_quality_compounder | 042 GuruAgents | long_short_decile_value_weighted | rank(qmj)+rank(qmj_growth)+rank(qmj_prof)+rank(ope_be)+rank(gp_me)-rank(debt_at) | Warren Buffett-style quality compounder: durable quality/profitability/growth with low leverage. |
| guru_equal_weight_style_ensemble | 042 GuruAgents | long_short_decile_value_weighted | average Graham, Buffett, Greenblatt, Piotroski, Altman proxy scores | GuruAgents combines multiple investment-guru sleeves; this is an equal-weight score ensemble of the five guru proxies. |
| guru_graham_deep_value_defensive | 042 GuruAgents | long_short_decile_value_weighted | rank(be_me)+rank(cash_at)+rank(ope_be)-rank(debt_at)-rank(rvol_252d)-rank(beta_252d) | Benjamin Graham-style defensive value: cheap, liquid, profitable, low leverage, low risk. |
| guru_greenblatt_magic_formula | 042 GuruAgents | long_short_decile_value_weighted | rank(ebit_mev)+rank(ope_be)+rank(gp_mev)+rank(be_me) | Joel Greenblatt-style magic formula: earnings yield plus business quality/return on capital. |
| guru_piotroski_fscore_proxy | 042 GuruAgents | long_short_decile_value_weighted | rank(ni_me)+rank(ocf_me)-rank(oaccruals_at)-rank(debt_gr1)-rank(eqnetis_me)+rank(at_turnover)+rank(sale_gr1) | Joseph Piotroski-style F-score: profitability, operating cash flow, accrual quality, leverage, issuance, and asset turnover. |
| paper_quantagents_risk_controlled_system | 043 QuantAgents | long_short_decile_value_weighted | rank(ret_12_1)+rank(qmj_safety)+rank(dolvol_126d)+rank(cash_at)-rank(rvol_252d)-rank(beta_252d)-rank(debt_at) | QuantAgents combines market/news/risk/strategy agents, memory, event-impact optimization, and risk-control meetings for simulated trading. |
| hedgeagents_balanced_lowrisk_alpha | 044 HedgeAgents | long_short_decile_value_weighted | rank(qmj)+rank(be_me)+rank(ope_be)-rank(rvol_252d)-rank(beta_252d)-rank(betadown_252d) | HedgeAgents is framed as balanced-aware trading; this proxy tests quality/value alpha with explicit low beta/downside-risk control. |
| repo_alphaforgebench_executable_multifactor | 045 AlphaForgeBench | long_short_decile_value_weighted | rank(be_me)+rank(ope_be)+rank(ret_12_1)+rank(qmj)+rank(dolvol_126d)-rank(rvol_252d)-rank(debt_at) | AlphaForgeBench evaluates LLMs as quantitative researchers generating executable alpha factors and factor-based trading strategies. |
| repo_livetradebench_live_allocation_proxy | 047 LiveTradeBench | long_only_top_decile_value_weighted | long-only top decile by rank(ret_12_1)+rank(qmj)+rank(qmj_safety)+rank(dolvol_126d)-rank(rvol_252d)-rank(beta_252d) | LiveTradeBench evaluates live multi-asset portfolio allocation under price/news uncertainty with explicit risk-return allocation decisions. |
| repo_deepfund_prudent_fund_manager | 048 DeepFund | long_only_top_decile_value_weighted | long-only top decile by rank(qmj)+rank(ope_be)+rank(gp_me)+rank(cash_at)+rank(ret_12_1)-rank(debt_at)-rank(rvol_252d)-rank(beta_252d) | DeepFund models a multi-agent fund workflow with fundamental, technical, policy/news, insider-style analysts, portfolio management, and risk control. |
| code_ai_trader_value_quality | 049 AI-Trader | long_short_decile_value_weighted | rank(be_me)+rank(qmj)+rank(ope_be)+rank(cash_at)-rank(debt_at)-rank(rvol_252d) | AI-Trader is a practitioner LLM trading repo listed as implementation evidence. |
| code_agentictrading_lab_allocation | 050 AgenticTrading | long_short_decile_value_weighted | rank(ret_12_1)+rank(qmj)+rank(dolvol_126d)-rank(rvol_252d)-rank(beta_252d) | AgenticTrading is listed as an agentic trading lab/infrastructure repo. |
| repo_tradetrap_robust_safety_proxy | 051 TradeTrap | long_short_decile_value_weighted | rank(qmj_safety)+rank(dolvol_126d)+rank(cash_at)-rank(rvol_252d)-rank(beta_252d)-rank(bidaskhl_21d)-rank(debt_at) | TradeTrap is primarily a robustness/stress-test framework; the in-spirit proxy tests the conservative safety/liquidity posture implied by its mitigation concerns. |
| code_ai_hedge_fund_buffett_munger | 052 ai-hedge-fund | long_short_decile_value_weighted | rank(qmj)+rank(qmj_prof)+rank(ope_be)+rank(gp_me)+rank(cash_at)-rank(debt_at) | virattt/ai-hedge-fund is a practitioner multi-agent hedge-fund style repo with value/quality investor personas. |
| code_vibe_trading_prompt_allocation | 053 Vibe-Trading | long_short_decile_value_weighted | rank(ret_12_1)+rank(qmj)+rank(dolvol_126d)-rank(rvol_252d) | Vibe-Trading is a practitioner prompt-driven trading repo listed in the source table. |
