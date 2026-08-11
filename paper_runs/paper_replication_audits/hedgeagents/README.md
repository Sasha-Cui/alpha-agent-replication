# HedgeAgents paper-level replication audit

Overall verdict: **not reproduced**. This package pins the original paper, its
complete arXiv v1 manuscript bundle, the authors' public project repository,
bounded archival searches, official model provenance, and a later warning from
the same authors about temporal leakage in financial-agent backtests. It gives
zero result credit to typesetting, duplicated tables, screenshots, or plots.

## What is genuinely recovered

- The official 10-page paper is pinned at SHA-256 `d51a97df37c27936ea69c3c951c7ac514c4dddd76bf509f866f2c647cd50505e`.
  The 20-file arXiv bundle contains the TeX, bibliography and
  typesetting support, plus 14 figure PDFs. It contains no HedgeAgents program,
  data, environment, or runner.
- Two clean three-pass LaTeX builds have identical extracted text and differ in
  raw bytes only at the generated PDF trailer ID; this audit does **not** call
  them byte-identical. All original/rebuilt pages and all source figures passed
  visual inspection.
- The author repository is pinned at `329c5cc8613d91e517de4fbdb0dbc8476a356db5`. Its leaderboard repeats 90
  method cells from Table 1 exactly. Four profile screenshots name 23 unique
  tool labels system-wide, ten unique action labels, and market scopes. Four
  workflow images and three general-experience snapshots provide qualitative
  author evidence. None is an executable trace.
- All 236 displayed numeric table cells are transcribed: 119 in the main table,
  63 in the conference ablation, and 54 in the LLM-backbone table. Of these,
  126 are HedgeAgents/full-system variants or backbones. **Zero of 236** are
  regenerated from a native execution.

## Public-site contamination boundary

The site repository is an R1 static documentation artifact, not released system
code. Its 5.2 MB `visualizer/data/data_public.js`, `filters*.json`,
`data-composition.png`, `tease_scores_gpt4v.png`, and MathVista logos belong to a
6,141-record MathVista/VQA website template. They are unrelated to HedgeAgents
and are explicitly excluded from data, implementation, and result evidence.
The visible Code and Dataset controls are commented placeholders that self-link
to the page. Git history contains only website assets. Software Heritage found
the same site and its single fork, not a separate implementation.

## Material internal conflicts

- The full system's MDD is 14.21% in the main table, LLM table, and prose, but
  8.68% in the all-conferences ablation row. The ablation narrative's 24.44%
  calculation uses 14.21%, reinforcing that 8.68% is inconsistent.
- The paper says each agent has 23 tools and eight actions. The author profiles
  instead list 5-7 tools per agent (23 unique system-wide) and 4-6 actions per
  agent (ten unique system-wide). No released mapping reconciles the counts.
- Table 1 prints a 24.49% Sharpe improvement, while its displayed 2.41 and 1.93
  imply 24.8705%. The conference prose's 41.29%, 60.65%, and 19.72% Sharpe
  improvements also do not follow from the displayed ablation rows.
- The claim of optimal performance on all metrics conflicts with the table:
  HedgeAgents volatility is 1.30, while MV is 1.13 and several methods are lower.
- The budget objective leaves lambda values, confidence level, covariance
  estimator/window, and solver absent; it also switches between `I_ij` and
  `sigma_ij` and writes CVaR bounds in an unresolved order.

## Why the empirical result remains unreproducible

The exact asset universe and constituent vintage, currency pairs, frozen Yahoo
and Alpaca responses, 60 indicator definitions, prompts, tool implementations,
risk parameters, starting capital, fill price/timing, order sizing, transaction
costs, slippage, constraints, metric formulas, Optuna spaces/trials, baseline
commits, seeds, dependency lock, and repeated-run policy are absent. No LLM
request/response, memory database, action record, order, fill, cash ledger, or
dated equity series is released. Curve images cannot regenerate exact metrics.
The historical `gpt-4-1106-preview` dependency is now deprecated; using a current
model would be an adaptation, not exact replication.

## Temporal-leakage validity warning

OpenAI documented an April 2023 knowledge cutoff for `gpt-4-1106-preview`, while
the reported HedgeAgents test spans January 2021 through December 2023. Most of
that test window is therefore inside the model's stated knowledge horizon. A
later paper by the same five authors cites HedgeAgents while arguing that
historical financial-agent backtests can suffer a "profit mirage" after the
model's knowledge cutoff. Its direct pre/post decay experiment covers FinMem,
FinAgent, QuantAgent, FinCON, and TradingAgents—not HedgeAgents—so this audit
treats it as a material contamination risk, **not** proof that a particular
HedgeAgents cell is false.

Regenerate with `scripts/audit_hedgeagents_paper.py`. `--strict` intentionally
exits nonzero while the paper remains unreproduced.
