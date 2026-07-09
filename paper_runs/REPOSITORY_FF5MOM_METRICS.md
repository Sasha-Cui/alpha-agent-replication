# Repository FF5Mom Metrics Summary

Scope: valid numeric metrics are computed only from approved JKP/USA inputs. Repositories without a valid approved-input candidate return stream are shown as `NA`, not backfilled from paper-shipped returns, yfinance, China data, or official French factors.

Beat rule: `beats_ff5mom_at_5pct` requires positive annualized alpha, positive appraisal/information ratio, HAC alpha t-stat > 1.96, positive FF5Mom span Sharpe lift, and GRS rejection at 5%. Negative-alpha candidates may still have span value if inverted, but they do not beat FF5Mom in the declared direction.

| repo | ref | metric status | selected candidate | Sharpe | alpha t | appraisal/IR | GRS F | GRS p | span lift | beats FF5Mom? | verdict |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|
| AlphaAgent | 3 | not_computable_from_approved_inputs:not_serious_no_strategy_return_series | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| AlphaBench | 1 | not_computable_from_approved_inputs:not_serious_no_strategy_return_series | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| AlphaForgeBench | 45 | not_computable_from_approved_inputs:blocked_aggregate_metrics_only_no_dated_jkp_return_stream | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| AlphaPROBE | 21 | not_computable_from_approved_inputs:blocked_no_usa_jkp_candidate_returns_requires_expression_adapter | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| ContestTrade | 24 | not_computable_from_approved_inputs:blocked_no_jkp_replay_return_stream | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| DeepFund | 48 | not_computable_from_approved_inputs:blocked_no_approved_historical_return_stream_reproduction_path | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| FAgent | 29 | not_computable_from_approved_inputs:blocked_no_jkp_candidate_returns_yfinance_synthetic_inputs | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| GuruAgents | 42 | not_computable_from_approved_inputs:legacy_non_jkp_paper_shipped_returns | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| QuantAgent | 25 | not_computable_from_approved_inputs:blocked_hft_not_representable_with_monthly_jkp | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| QuantEvolver | 5 | computed_jkp_only | quantevolver_return_sharpe_60_proxy | 0.316 | 0.651 | 0.149 | 0.505 | 0.4778 | 0.010 | no | no_positive_but_not_statistically_significant_vs_ff5mom |
| RD-Agent | 6 | not_computable_from_approved_inputs:blocked_requires_jkp_adapter_no_shipped_usa_candidate | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| TradeTrap | 51 | not_computable_from_approved_inputs:legacy_non_jkp_paper_shipped_returns | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| Trading-R1 | 33 | not_computable_from_approved_inputs:blocked_placeholder_repo_no_executable_code | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |
| live-trade-bench | 47 | not_computable_from_approved_inputs:blocked_no_jkp_live_or_replay_return_path_logging | NA | NA | NA | NA | NA | NA | NA | no | not_computable_from_approved_inputs |

Files:

- `repository_ff5mom_metrics_summary.csv`: one selected row per cloned repository.
- `repository_candidate_ff5mom_metrics.csv`: all FF5Mom candidate rows for cloned/code repositories.
- `paper_ff5mom_metrics_summary.csv`: all registry paper rows, including no-code rows with NA metrics.
