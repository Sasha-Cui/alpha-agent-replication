# Repository In-Spirit JKP Replications

Scope: one selected valid JKP-USA row per cloned repository. If the repository had no approved-input executable strategy return stream, the associated paper was read and translated into a clearly labeled monthly USA JKP proxy. These are in-spirit tests, not faithful code executions.

Input policy: returns are built only from read-only `${ALPHA_EVOLVE_JKP_ROOT}` inputs; no China, no yfinance, no paper-shipped return paths, and no external return data.

| repo | ref | replication type | selected candidate | Sharpe | alpha ann | alpha t | IR | GRS p | span lift | beats FF5Mom? |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| AlphaAgent | 3 | repo_in_spirit_proxy | repo_alphaagent_decay_resistant_quality | 0.796 | 3.86% | 4.264 | 0.890 | 0.0000 | 0.325 | yes |
| GuruAgents | 42 | repo_in_spirit_proxy_existing | guru_buffett_quality_compounder | 0.658 | 2.69% | 2.702 | 0.534 | 0.0113 | 0.127 | yes |
| Trading-R1 | 33 | repo_in_spirit_proxy | repo_trading_r1_risk_adjusted_reasoning | 0.305 | 1.13% | 1.461 | 0.275 | 0.1908 | 0.035 | no |
| AlphaForgeBench | 45 | repo_in_spirit_proxy | repo_alphaforgebench_executable_multifactor | 0.317 | 0.88% | 1.384 | 0.264 | 0.2079 | 0.033 | no |
| AlphaPROBE | 21 | repo_in_spirit_proxy | repo_alphaprobe_dag_diverse_factor_blend | 0.450 | 1.52% | 1.379 | 0.276 | 0.1880 | 0.036 | no |
| TradeTrap | 51 | repo_in_spirit_proxy_robustness_not_alpha_claim | repo_tradetrap_robust_safety_proxy | 0.166 | 0.92% | 1.297 | 0.267 | 0.2034 | 0.033 | no |
| DeepFund | 48 | repo_in_spirit_proxy | repo_deepfund_prudent_fund_manager | 0.784 | 0.67% | 0.956 | 0.196 | 0.3494 | 0.018 | no |
| QuantEvolver | 5 | repo_seed_jkp_proxy | quantevolver_return_sharpe_60_proxy | 0.316 | 0.33% | 0.651 | 0.149 | 0.4778 | 0.010 | no |
| ContestTrade | 24 | repo_in_spirit_proxy_existing | contesttrade_internal_contest_trailing_sharpe | 0.351 | 0.27% | 0.202 | 0.046 | 0.8337 | 0.001 | no |
| QuantAgent | 25 | repo_in_spirit_proxy_monthly_hft_approximation | repo_quantagent_hft_price_pattern | 0.029 | -0.65% | -0.545 | -0.117 | 0.5756 | 0.007 | no |
| RD-Agent | 6 | repo_in_spirit_proxy | repo_rd_agent_factor_model_compact_ensemble | -0.027 | -0.64% | -0.789 | -0.180 | 0.3903 | 0.015 | no |
| FAgent | 29 | repo_in_spirit_proxy | repo_fincon_cvar_risk_controlled_allocator | 0.599 | -0.66% | -0.870 | -0.189 | 0.3670 | 0.017 | no |
| live-trade-bench | 47 | repo_in_spirit_proxy | repo_livetradebench_live_allocation_proxy | 0.606 | -0.54% | -0.933 | -0.201 | 0.3388 | 0.019 | no |
| AlphaBench | 1 | repo_in_spirit_proxy | repo_alphabench_formulaic_price_volume | -0.029 | -1.51% | -2.183 | -0.454 | 0.0309 | 0.094 | no |

Interpretation: the expanded repo-level pass adds in-spirit coverage for every cloned repo. Only AlphaAgent and GuruAgents beat FF5Mom under the strict positive-alpha rule. QuantEvolver remains the only direct repo-derived JKP seed test, and it does not beat FF5Mom.

Important caveat: the AlphaAgent in-spirit proxy is an accounting-quality/accruals/safety/turnover composite. It is a plausible translation of the paper claim about decay-resistant, non-crowded factors, but it is not evidence that the public AlphaAgent code can discover this signal on JKP data without this hand mapping.

Files:

- `paper_runs/idea_replications/repository_in_spirit_ff5mom_summary.csv`
- `paper_runs/idea_replications/jkp_paper_idea_proxies/paper_idea_proxy_ff5mom_summary.csv`
- `scripts/run_paper_idea_jkp_proxies.py`
