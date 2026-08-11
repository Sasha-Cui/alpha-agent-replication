# GuruAgents paper-level replication audit

This directory audits [GuruAgents](https://arxiv.org/abs/2510.01664) against the authors' pinned
[source repository](https://github.com/yejining99/GuruAgents). It is deliberately fail-closed: reproducing
the public workbook is not the same as reproducing the paper.

## Verdict

**The paper is not faithfully reproduced.** Native execution of the released
notebook reproduces all seven shipped workbook paths to floating-point error,
but the workbook does not reproduce Table 1 or either paper figure. Only two of
the 70 Table 1 cells match at the paper's rounding precision, both benchmark
maximum-drawdown values; no complete table row matches. None of the 42 audited
figure units receives paper-result credit.

The release nevertheless contains valuable component evidence: 35 archived
GPT-4o-2024-08-06 agent decisions, full tool observations, five prompt/tool
implementations, quarterly financial/market data, portfolios, a workbook, and
notebook outputs. Every archived run calls each declared tool exactly once.
Those are real source-component achievements, not a paper reproduction.

## Most consequential breaks

- The paper says Q4 2023 through Q2 2025, while the public agent workbook runs
  from 2024-01-01 through 2025-08-12 and the paper's own Figure 1 visibly runs
  past Q2 2025.
- The declared 1 bp gross-turnover cost is never applied.
- Agent paths contain forward-filled calendar days while QQQ/SPY contain
  trading days; 252-day annualization is then applied to both.
- The paper names the NASDAQ-100 and S&P 500 indices, while source code uses the
  QQQ and SPY ETFs.
- The claimed deterministic scorer is performed by GPT-4o, not Python. Three
  backend fingerprints occur, there is no seed/repeat study, only 2/35 raw
  portfolios sum to 100, 9/35 contain duplicates, and 0/35 satisfy the entire
  strict output contract.
- Exact Table 1 generation code, paper Figure 1 paths, and paper Figure 2
  portfolio distributions are not released. The visible paper distributions
  differ from the public histories.
- Quarter labels are used as if data were available the next day; filing dates
  and historical NASDAQ-100 membership dates are absent.

## Accounting boundary

- Table 1: **2/70 cells**, **0/7 full rows**.
- Figures: **0/42 audited units**.
- Exact appendix prompts: **0/5** (all are edited presentations of runtime templates).
- Native public-workbook reproduction: **7/7 series** (component/source-artifact evidence only).
- Full-paper reproduction: **no**.

See `manifest.json` for the machine-readable summary and the CSV ledgers for
cell-, run-, portfolio-, prompt-, mechanism-, figure-, and gap-level evidence.
