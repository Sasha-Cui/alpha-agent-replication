# Expanded equity accounts: all 13 cohorts validated

All 13 source histories and full cached replays passed admission before the unchanged V3 account builder ran. Independent account error is at most 5.56e-16. At the declared 10 bp next-close setting, FinMem and TradingAgents finish modestly above their matched buy-and-hold controls, while FinAgent finishes below. These are descriptive paths, not significance or LLM-specific claims.

| Setting | Recorded choice |
| --- | --- |
| Default | Next-close execution; 10 bp transaction fees |
| Pooling | Equal initial capital in independent accounts; no daily cross-account rebalancing |
| Variation retained | 0/10/25/50 bp and next-close / infeasible same-close diagnostic |
| Population | FinMem 5, TradingAgents 3, FinAgent 5; TA news repair separate |
| Reproduction claim | Adapted source executions, not full-paper reproduction |

## Matched aggregate paths

| Study / assets / sessions | Native wealth | Matched control | Native - control |
| --- | --- | --- | --- |
| FinMem / 5 / 127 | **1.101298** | 1.090175 | +0.011123 |
| TradingAgents / 3 / 61 | **1.084726** | 1.076676 | +0.008050 |
| FinAgent / 5 / 147 | 1.009548 | **1.136907** | -0.127358 |

Comparison is within each row: higher terminal wealth is better; bold marks the larger of the two wealth values, including ties. The difference is wealth per initial $1, not annualized percentage points. No comparison is made between different study windows.

[Full aggregate audit](visual_tables/aggregate_performance_full.csv) | [Comparison values](visual_tables/aggregate_comparisons.csv)

The annualized arithmetic mean and geometric terminal wealth measure different aspects of the path. FinMem has higher terminal wealth but a lower annualized arithmetic return than its control; this is retained, not reconciled by changing the metric.

## Every asset retained

| Study / asset / sessions | Native wealth | Matched control |
| --- | --- | --- |
| FinMem / TSLA / 127 | **0.837121** | 0.826313 |
| FinMem / NFLX / 127 | **1.506791** | **1.506791** |
| FinMem / AMZN / 127 | **0.890956** | **0.890956** |
| FinMem / MSFT / 127 | **1.271622** | 1.240786 |
| FinMem / COIN / 127 | **1.000000** | 0.986029 |

| Study / asset / sessions | Native wealth | Matched control |
| --- | --- | --- |
| TradingAgents / AAPL / 61 | **0.930949** | **0.930949** |
| TradingAgents / GOOGL / 61 | **1.085367** | **1.085367** |
| TradingAgents / AMZN / 61 | **1.237863** | 1.213712 |

| Study / asset / sessions | Native wealth | Matched control |
| --- | --- | --- |
| FinAgent / TSLA / 147 | 0.773582 | **1.157762** |
| FinAgent / AAPL / 147 | **1.096044** | 1.064736 |
| FinAgent / AMZN / 147 | 1.194172 | **1.220526** |
| FinAgent / GOOGL / 147 | 0.910818 | **1.118269** |
| FinAgent / MSFT / 147 | 1.073127 | **1.123240** |

Within each row, higher wealth is better; both values are bold when tied. Rows are grouped by study, not sorted by realized performance. The full 13-asset population is retained.

[All asset comparison values](visual_tables/asset_comparisons.csv) | [All 208 arm/clock/fee paths](visual_tables/all_208_account_paths_metrics.csv)

## Fidelity and inference limits

FinMem has 126 decisions and 127 valuation days per asset; TradingAgents has 61 recorded days per asset; FinAgent has 147 validation records/valuation days per asset. Different periods, assets, models and account rules preclude a cross-study leaderboard. Assets share market histories and each has one trajectory.

FinMem training Guard failures (259) and the one test Guard failure remain in the evidence. Zero-volatility account paths retain an undefined Sharpe value (null in canonical JSON, blank in the audit CSV), not a fabricated zero ratio. Its signed-log-return source score is not a self-financing portfolio return. The separate TradingAgents news repair changed all 61 news reports but had identical policy/return paths here; it is not pooled into the main three-asset aggregate.

FinAgent AMZN preserves the failed original HTTP500 request and full original charge, the one user-approved exact recovery, and every 220/49/134-record historical prefix. All five FinAgent sources now have 397-record full replays. These overlapping histories are not additive observations.

The new validated-equity workflow-record headline is 3,877 = prior 1,892 + 5 x 397. The main 13-cohort source records total 4,354 and include the original FinMem TSLA 538 records; the separate TA news 61 records enter the new-work headline. Neither number is an independent economic sample size.

Frozen v1 six primary comparisons remain inconclusive at the 2 pp annual margin. The separate v2 primary family still has only three available members of four; strict Alpha remains unavailable. These expanded equity results do not replace any original primary, project-four or secondary-54 comparison, and are not JKP132 attribution or a pristine/untouched-holdout experiment.

## Provenance and reproduction

[Account checks](visual_tables/account_checks.csv) | [Actual final account completion](../final_equity_accounts_completion_v3.json) | [AMZN full replay](../finagent_amzn_full_replay_completion.json) | [Canonical account validation](../accounts/validation.json)

Figures use only saved aggregate return paths; audit tables are copies of completed metrics. No source, model, replay or account engine is executed by this presentation. Builder: `scripts/build_final_equity_report_v1.py`; validator: `scripts/validate_final_equity_report_v1.py`, using the immutable central kt-python runtime.

This case report and assistant visual QA do not constitute independent human review, final project manuscript integration or final archive verification.
