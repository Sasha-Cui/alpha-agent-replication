# GuruAgents paper-level replication audit

This directory audits the only official arXiv version of
[GuruAgents](https://arxiv.org/abs/2510.01664) against the complete reachable history of the authors'
[source repository](https://github.com/yejining99/GuruAgents). It is deliberately fail-closed: reproducing
a public workbook is not the same as reproducing the paper.

## Verdict

**The paper is not faithfully reproduced.** Native execution of the released
notebook reproduces all seven shipped workbook paths to floating-point error,
but that workbook does not reproduce Table 1 or either paper figure. A separate,
source-grounded protocol reconstruction does recover both benchmark rows:
released QQQ and SPY prices from 2023-11-01 through 2025-08-01 regenerate all
20 benchmark cells at the paper's four-decimal precision. This is the only
perfect common window among 5985
windows searched across the paper-stated Q4 2023 start region and the Q2-to-
Figure-1 endpoint region. It proves that the table uses ETFs and extends into
Q3 2025, despite the paper caption saying Q2 2025.

The five agent rows remain unreproduced (0/50 cells), so the overall verdict
does not become a full replication. None of the 42 audited figure units receives
paper-result credit. To test whether the public alternatives can nevertheless
recover those rows,
the audit exhausts 640 coherent
agent protocols: every per-quarter choice between the two released portfolio
lineages, both source price columns, and both stated-cost and no-cost treatments
under the recovered window. No complete agent row appears; the best candidate
matches only 2/10 cells.

Separately, all 19 commits,
592 paths, four versions of the multi-agent
workbook, and three versions of the paper-relevant notebook were checked. No
historical workbook exceeds 2/70 Table 1 matches, none implements the missing
complete Table 1 generator, and none of six historical notebook plots matches
either paper figure.

The release nevertheless contains valuable component evidence: 95 archived
GPT-4o-2024-08-06 agent decisions (35 in the current collection and 60 in the
older collection), full tool observations, five prompt/tool implementations,
quarterly financial/market data, portfolios, workbooks, and notebook outputs.
Every archived run calls each declared tool exactly once. These are real
source-component achievements, not a paper reproduction. Twenty-five
agent-periods have two public portfolio variants; none of those files is
identical and only four ticker sets match. Because their input/code lineage is
incomplete, they are evidence of ambiguous run attribution, not controlled
repeat trials.

## Most consequential breaks

- The paper says Q4 2023 through Q2 2025, but the unique exact benchmark window
  is 2023-11-01 through 2025-08-01 and Figure 1 visibly reaches that later
  horizon. The public agent workbook instead runs 2024-01-01 through
  2025-08-12.
- The declared 1 bp gross-turnover cost is never applied.
- Agent paths contain forward-filled calendar days while QQQ/SPY contain
  trading days; 252-day annualization is then applied to both.
- The paper names the NASDAQ-100 and S&P 500 indices, while source code uses the
  QQQ and SPY ETFs.
- The claimed deterministic scorer is performed by GPT-4o, not Python. Three
  backend fingerprints occur, there is no seed/repeat study, only 16/95 raw
  portfolios sum to 100, 17/95 contain duplicates, and 0/95 satisfy the entire
  strict output contract. In the current 35-run collection, only 2/35 sum to
  100.
- Exact five-agent Table 1 input paths, complete Table 1 generation code,
  paper Figure 1 agent paths, and paper Figure 2
  portfolio distributions are not released in any public commit. The visible
  paper distributions differ from both same-period public portfolio variants.
- Quarter labels are used as if data were available the next day; filing dates
  and historical NASDAQ-100 membership dates are absent.

## Accounting boundary

- Table 1: **20/70 cells**, **2/7 full rows**
  (both benchmark rows; 0/5 agent rows and 0/50 agent cells).
- Figures: **0/42 audited units**.
- Exact appendix prompts: **0/5** (all are edited presentations of runtime templates).
- Native public-workbook reproduction: **7/7 series** (component/source-artifact evidence only).
- Public source history: **2/2 branches, 19/19 commits, 592/592 paths** audited.
- Effective benchmark protocol: **2023-11-01 through 2025-08-01, 20/20 cells**.
- Released agent protocol census: **640 variants,
  0 complete rows; best candidate 2/10 cells**.
- Full-paper reproduction: **no**.

See `manifest.json` for the machine-readable summary and the CSV ledgers for
cell-, run-, portfolio-, prompt-, mechanism-, figure-, and gap-level evidence.
