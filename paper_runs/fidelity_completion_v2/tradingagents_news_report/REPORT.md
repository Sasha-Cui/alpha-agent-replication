# TradingAgents Alphabet-news repair — completed descriptive sensitivity

The larger issuer-news corpus changes every daily news report but leaves the portfolio unchanged. Both original and repaired runs issue **BUY on all 61 days**. Under the declared long-only cash/share account, repeated BUY instructions retain the fully invested position. Original, repaired and matched buy-and-hold paths are identical, including fees, wealth and shares, at every tested cost and clock. This is a completed null realized comparison, not evidence that news can never help.

## Same complete quarter and economic settings

| One-way fee, bp | Original GOOGL | Repaired GOOGL | Matched buy-and-hold | Repair minus original |
|---|---|---|---|---|
| 0 | 8.645% | 8.645% | 8.645% | +0.000pp |
| 10 | 8.537% | 8.537% | 8.537% | +0.000pp |
| 25 | 8.374% | 8.374% | 8.374% | +0.000pp |
| 50 | 8.105% | 8.105% | 8.105% | +0.000pp |

[Full audit table, including same-close diagnostics and the three-equity sensitivity](comparisons_full_audit.csv). Returns are cumulative for January 2–March 28, 2024, with next-close fills. Same-close results are infeasible diagnostics. No terminal forced liquidation is imposed.

The separate three-equity sensitivity retains the exact AAPL and AMZN accounts and changes only the GOOGL policy realization. Equal initial capital then drifts without daily rebalancing. At 10bp it returns 8.473%, identical to the original three-equity account. The original published result was not overwritten.

## Evidence and limitations

- The input corpus expands from 88 to 10,117 items, while all 373 price rows are preserved. The additional 10,029 news items use the verified issuer mapping. One complete company-news source is supplied; independent feeds are honestly unavailable. No article is truncated.
- All 61 news reports change. Fundamentals, market and sentiment reports remain identical. This confirms that the news repair was active even though the categorical trading actions stay BUY.
- Full cached replay matches all 61 records with zero differences, including the 23- and 27-record interruption prefixes. No new API call is made by replay or accounting.
- The independent cash/share reconstruction matches the target-weight account within 5.56e-16. [Policy diagnostics](policy_diagnostics.json) verify every fee/clock path.
- Current model/data snapshots, empty source experience banks, categorical sizing and a single issuer/quarter limit the inference. This is not a causal treatment-effect estimate over repeated LLM trajectories, a significant-alpha result, JKP132 attribution, or full-paper reproduction. The earlier failed five-day duplicated-feed variant remains separate.

[Account validation](../tradingagents_news_accounts/completion.json) · [Fixed descriptive protocol](../tradingagents_news_account_protocol.json) · [Source review](../SOURCE_REVIEW_PACKET.md) · [Report validation](validation.json)

Rebuild on Bouchet from the canonical checkout:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python scripts/build_tradingagents_news_report_v2.py
```
