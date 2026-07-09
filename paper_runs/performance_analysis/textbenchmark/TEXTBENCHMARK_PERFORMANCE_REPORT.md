# TextBenchmark Performance Analysis

Generated: `2026-07-05T05:03:13.229455+00:00`

## Scope

- Candidate set: `62` alpha_evolve JKP-USA in-spirit paper proxies from `${ALPHA_EVOLVE_REPO}/paper_runs/idea_replications/jkp_paper_idea_proxies`.
- Benchmark factor panel: `${ALPHA_EVOLVE_FACTOR_PANEL}`.
- TextBenchmark column: `newsfactor_top1000_unit_gross`.
- Fixed analysis window: `1999-07-31_to_2021-12-31_270m`.
- Scaling: all candidate and benchmark return streams are scaled to `7%` annualized volatility on the overlap sample before alpha/appraisal/GRS and MVO diagnostics.
- Existing book diagnostic: long-only max-Sharpe allocation over `JKP132 + TextBenchmark`, then over `JKP132 + TextBenchmark + candidate`.
- Input policy: no external returns were used; this reads only alpha_evolve JKP proxy candidate returns and the external-factor-data STATE factor panel.

## Headline Counts

| Test | Count |
| --- | ---: |
| Candidates evaluated | 62 |
| Positive/significant alpha vs TextBenchmark alone | 10 |
| Positive/significant alpha vs CAPM + JKP132 + TextBenchmark | 3 |
| Positive long-only delta Sharpe vs JKP132 + TextBenchmark | 51 |
| Positive long-only delta and candidate weight >= 1% | 41 |
| Strict additive to JKP132 + TextBenchmark book | 3 |

## Top Alpha Versus TextBenchmark Alone

| candidate_id | textbenchmark_alpha_annualized | textbenchmark_alpha_tstat_hac | textbenchmark_information_ratio | textbenchmark_grs_f | textbenchmark_grs_p_value | textbenchmark_combined_minus_old_sharpe |
| --- | --- | --- | --- | --- | --- | --- |
| repo_deepfund_prudent_fund_manager | 6.44% | 4.644 | 0.923 | 18.351 | 0.000 | 0.462 |
| efs_sparse_top5_momentum_low_vol | 6.03% | 4.088 | 0.863 | 16.047 | 0.000 | 0.415 |
| paper_finagent_multimodal_generalist | 4.97% | 3.358 | 0.711 | 10.893 | 0.001 | 0.301 |
| repo_livetradebench_live_allocation_proxy | 4.70% | 3.272 | 0.671 | 9.721 | 0.002 | 0.273 |
| repo_fincon_cvar_risk_controlled_allocator | 4.80% | 3.173 | 0.686 | 10.155 | 0.002 | 0.283 |
| repo_alphaagent_decay_resistant_quality | 5.16% | 3.163 | 0.751 | 12.164 | 0.001 | 0.330 |
| contesttrade_internal_contest_trailing_sharpe | 4.02% | 2.590 | 0.578 | 6.442 | 0.012 | 0.178 |
| guru_buffett_quality_compounder | 3.82% | 2.585 | 0.559 | 6.731 | 0.010 | 0.198 |
| fama_value_momentum_interpretable | 3.75% | 2.322 | 0.539 | 6.265 | 0.013 | 0.186 |
| paper_alphaagentevo_evolved_seed | 3.03% | 2.102 | 0.436 | 4.095 | 0.044 | 0.126 |
| guru_piotroski_fscore_proxy | 3.03% | 1.935 | 0.437 | 4.121 | 0.043 | 0.127 |
| alphaagents_risk_neutral_fundamental_momentum | 2.73% | 1.878 | 0.391 | 3.291 | 0.071 | 0.103 |
| code_quantaalpha_self_evolving_factor | 2.80% | 1.873 | 0.406 | 3.554 | 0.060 | 0.111 |
| code_ai_hedge_fund_buffett_munger | 2.50% | 1.729 | 0.366 | 2.887 | 0.090 | 0.091 |
| repo_alphaprobe_dag_diverse_factor_blend | 2.79% | 1.707 | 0.400 | 3.453 | 0.064 | 0.108 |

## Top Alpha Versus CAPM + JKP132 + TextBenchmark

| candidate_id | full_alpha_annualized | full_alpha_tstat_hac | full_information_ratio | full_grs_f | full_grs_p_value | full_combined_minus_old_sharpe |
| --- | --- | --- | --- | --- | --- | --- |
| guru_greenblatt_magic_formula | 1.55% | 3.358 | 1.071 | 4.751 | 0.031 | 0.125 |
| guru_equal_weight_style_ensemble | 1.93% | 3.258 | 1.138 | 5.369 | 0.022 | 0.140 |
| guru_graham_deep_value_defensive | 1.45% | 3.245 | 0.961 | 3.831 | 0.052 | 0.101 |
| alphacrafter_full_stack_multifactor | 2.02% | 3.105 | 1.129 | 5.285 | 0.023 | 0.138 |
| alphaagents_risk_averse_quality_lowrisk | 1.52% | 2.909 | 0.931 | 3.593 | 0.060 | 0.094 |
| code_ai_trader_value_quality | 2.17% | 2.681 | 0.941 | 3.670 | 0.058 | 0.096 |
| code_quantaalpha_self_evolving_factor | 1.75% | 2.580 | 0.865 | 3.099 | 0.081 | 0.082 |
| hedgeagents_balanced_lowrisk_alpha | 1.09% | 2.489 | 0.744 | 2.291 | 0.132 | 0.060 |
| paper_alpha_gpt_interactive_formula | 1.69% | 2.485 | 0.777 | 2.504 | 0.116 | 0.066 |
| repo_alphaagent_decay_resistant_quality | 1.99% | 2.483 | 0.836 | 2.897 | 0.091 | 0.076 |
| paper_alphaagentevo_evolved_seed | 1.37% | 2.428 | 0.842 | 2.941 | 0.089 | 0.077 |
| code_vibe_trading_prompt_allocation | 1.26% | 2.203 | 0.860 | 3.067 | 0.082 | 0.081 |
| paper_quantagents_risk_controlled_system | 1.11% | 2.020 | 0.759 | 2.385 | 0.125 | 0.063 |
| code_ai_hedge_fund_buffett_munger | 2.43% | 2.015 | 0.771 | 2.461 | 0.119 | 0.065 |
| repo_alphaforgebench_executable_multifactor | 1.25% | 1.993 | 0.668 | 1.849 | 0.176 | 0.049 |

## Top Book Delta Versus JKP132 + TextBenchmark

| candidate_id | longonly_delta_sharpe | longonly_all_mvo_candidate_weight | longonly_original_mvo_annualized_sharpe | longonly_all_mvo_annualized_sharpe | full_alpha_tstat_hac | full_information_ratio |
| --- | --- | --- | --- | --- | --- | --- |
| repo_deepfund_prudent_fund_manager | 0.083 | 0.154 | 4.249 | 4.332 | 0.823 | 0.275 |
| repo_fincon_cvar_risk_controlled_allocator | 0.067 | 0.140 | 4.249 | 4.316 | -0.509 | -0.165 |
| paper_finagent_multimodal_generalist | 0.051 | 0.125 | 4.249 | 4.300 | -0.664 | -0.233 |
| repo_livetradebench_live_allocation_proxy | 0.050 | 0.124 | 4.249 | 4.299 | -1.721 | -0.601 |
| efs_sparse_top5_momentum_low_vol | 0.040 | 0.113 | 4.249 | 4.289 | -0.377 | -0.135 |
| contesttrade_internal_contest_trailing_sharpe | 0.024 | 0.088 | 4.489 | 4.513 | 0.816 | 0.320 |
| alphacrafter_full_stack_multifactor | 0.009 | 0.058 | 4.249 | 4.258 | 3.105 | 1.129 |
| repo_alphaagent_decay_resistant_quality | 0.007 | 0.052 | 4.249 | 4.256 | 2.483 | 0.836 |
| guru_equal_weight_style_ensemble | 0.006 | 0.049 | 4.249 | 4.255 | 3.258 | 1.138 |
| code_ai_trader_value_quality | 0.006 | 0.050 | 4.249 | 4.255 | 2.681 | 0.941 |
| code_ai_hedge_fund_buffett_munger | 0.006 | 0.049 | 4.249 | 4.255 | 2.015 | 0.771 |
| code_quantaalpha_self_evolving_factor | 0.006 | 0.048 | 4.249 | 4.255 | 2.580 | 0.865 |
| alphaagents_risk_neutral_fundamental_momentum | 0.006 | 0.046 | 4.249 | 4.255 | 1.800 | 0.670 |
| paper_p1gpt_structured_workflow | 0.004 | 0.040 | 4.249 | 4.253 | 1.529 | 0.655 |
| paper_alpha_gpt_interactive_formula | 0.004 | 0.039 | 4.249 | 4.253 | 2.485 | 0.777 |

## Output Files

- `${ALPHA_EVOLVE_REPO}/paper_runs/performance_analysis/textbenchmark/alpha_evolve_textbenchmark_candidate_summary.csv`
- `${ALPHA_EVOLVE_REPO}/paper_runs/performance_analysis/textbenchmark/alpha_evolve_textbenchmark_benchmark_metrics.csv`
- `${ALPHA_EVOLVE_REPO}/paper_runs/performance_analysis/textbenchmark/alpha_evolve_textbenchmark_book_delta_mvo.csv`
- `${ALPHA_EVOLVE_REPO}/paper_runs/performance_analysis/textbenchmark/run_metadata.json`

## Interpretation

The TextBenchmark-only test answers whether a candidate is different from the NewsFactor/TextBenchmark sleeve. The full-span and long-only book tests are the stricter tests: they ask whether the candidate still adds anything after the JKP132 factor book and TextBenchmark are already in the book.
