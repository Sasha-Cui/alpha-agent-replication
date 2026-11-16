# EFS v1 economic-fidelity pilot

The first repair is complete: a fresh EFS v1 implementation executes real GPT-4.1 factor mutation/crossover on daily prices for all 50 source-listed U.S. securities. It uses the published prompt, twelve disclosed seed families, weekly evolutionary updates, m=25 search feedback, Recall@20, and a daily m=10 equal-weight long-only portfolio.

The 2019–2024 path contains **1,510 trading days and 72 compounded months**. There were **290 weekly generation steps**, **535 admitted LLM functions**, and **1438 days using LLM-generated functions** in the selected ensemble. These are function counts, not independent alpha discoveries.

## Descriptive results

All rows use the same daily data, dates, past-only eligibility and close execution. The table uses dividend-inclusive returns and 10 bp per one-way traded notional for the net cases. Sharpe uses zero risk-free rate. The equal-weight reference was added after inspection of the pilot, following the paper’s baseline motivation; it is explicitly a descriptive diagnostic.

| Strategy | Gross CAGR | Net CAGR | Net Sharpe | Net maximum drawdown |
|---|---:|---:|---:|---:|
| Initial-library control | 30.42% | 13.96% | 0.592 | -45.48% |
| LLM evolution | 26.57% | 15.95% | 0.604 | -50.33% |
| Daily equal-weight reference | 29.31% | 28.90% | 1.130 | -34.09% |

The LLM path has lower gross CAGR but higher net CAGR than the initial-library control. Average daily one-way traded notional falls from 53.52% to 34.77%; it is 1.27% for the equal-weight reference. The simple equal-weight reference outperforms both. The current evidence therefore does not establish incremental agent alpha. In particular, the apparent net advantage over the initial library should not be attributed to novel information without turnover-matched controls.

## Fidelity and verification

- Restored daily price/return inputs and 30-observation factor histories; monthly returns are compounded from the daily account.
- Retained all fifty source identities, including correctly resolved META and Berkshire class B; IPO histories are not backfilled.
- Actual LLM calls use source-prompt content, code, and anonymized historical metrics. No tickers, dates, or stock-level prices are sent.
- Decisions observe close t, execute at close t+1, and first earn the following close-to-close return. This one-session execution delay is disclosed.
- Preserved separate price-only/dividend-inclusive accounts, zero-cost/10 bp cases, drift-aware turnover and self-financing fees.
- Both 1,510-day account reconstructions pass an independent bracketed fee-equation solver, with maximum daily discrepancies below 1e-15.
- A full network-disabled replay reproduces the live financial paths, decisions, proposals and private holdings byte for byte, without additional charges.
- A JSON-only NumPy-index serialization error was repaired after the live financial paths completed. The pre-fix paths and source snapshot were retained; no financial parameter was changed for that repair.
- Twenty-one focused tests pass on Python 3.9 and 3.12; the scoped lint check and preserved 62-path study validator pass.

## Claim boundary and review

This is a paper-guided native-cadence reimplementation, not recovery of the author’s unreleased code, historical endpoint, generated pool, three original search trajectories or published result tables. It targets v1, not the substantially revised v2. The alternative daily dataset, retrospective static universe, current model, one trajectory, and researcher-defined numerical and selection conventions remain limitations. No pristine holdout or JKP132 significance claim is made.

The source algorithm refers to recent performance records from the last search interval. This pilot summarizes 60 completed outcomes with five-session search updates; that aggregation is an explicit implementation interpretation for review, not a claim of source-exact feedback numerics. Independent human review remains pending. Start with SOURCE_REVIEW_PACKET.md, which excludes performance outcomes.

## Cost and persistence

The project-wide ledger imports $9.9103025 of prior GuruAgents calls from its per-call journal, rather than the misleading reset run-final counter. This repair incurred $5.808226 in known API charges, including the retired setup, plus a $0.036876 conservative reservation for one response lost at the file-count quota. The corrected run and cached replays did not retry that identical lost request. Project commitment is $15.7554045, below the $450 soft stop.

Project file-count capacity was recovered by removing 5,723 and 6,348 regenerable bytecode files with paired source files from the two project environments. Package source and versions were retained. The results, private holdings, and authoritative SQLite response cache/ledger are now back in the canonical project tree; the temporary scratch copy is retained as a second copy.

## Reproduction

From the canonical checkout, using the central project interpreter:

```bash
python scripts/validate_efs_economic_fidelity.py --mode initial
python scripts/validate_efs_economic_fidelity.py --mode llm
python scripts/replay_efs_economic_fidelity.py
```

The canonical replay entry point passed the complete LLM trajectory, including all seven aggregate/metadata files and the private holdings, byte for byte. It requires the authorized private data/cache bundle, disables model-network requests and never requires an API key. Full reconstruction from source inputs is in scripts/prepare_efs_economic_fidelity.py. Aggregate cases are in the *_metrics.csv and *_monthly_returns.csv files; code, recipes, proposal decisions, model traces, runtime versions, source hashes and storage lineage accompany them.

## Remaining program

This completes the first executable pilot within point 1. The broader economically faithful cohort, independent human source review, matched-budget agent comparisons, economic-effect bounds, inference calibration, new evaluation separation, and manuscript synthesis are not complete. The existing strict and in-spirit studies remain frozen.

Primary paper: https://arxiv.org/abs/2507.17211v1
Independent audit: https://github.com/Sasha-Cui/alpha-agent-replication/pull/1
