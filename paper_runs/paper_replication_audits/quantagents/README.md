# QuantAgents paper-level replication audit

Overall verdict: **not reproduced**. This package pins arXiv `2510.04643v1`,
the complete 16-file manuscript bundle, the authors' first-party project site
repository at `a1d0d56d`, official GPT-4o provenance, and bounded
repository searches. The 27-page source rebuild and every official/rebuilt page
passed visual review. Document recovery is not system execution.

## What is genuinely recovered

- The manuscript specifies four agents, 26 named tools, three memory types,
  ten claimed actions, three meetings, five example/simplified prompt templates,
  top-10 `text-embedding-3-large` retrieval, `gpt-4o-2024-05-13` at temperature
  0.7, a 2010--2020/2021--2023 temporal split, formulas, metrics, profiles, and
  qualitative strategy-pool/risk workflows.
- The 41-file MIT project repository contains the exact title, 90 exact
  duplicates of main-table cells, four rendered meeting algorithms, four
  XML-like profile images, 15 QuantAgents images, and three dated 1080p meeting
  demonstrations. These are valuable R1 author documentation, not executable
  QuantAgents source or raw runtime traces.
- All **238** displayed numeric table cells are inventoried: 115 in the main
  table, 63 in the meeting ablation, 54 in the LLM table, and 6 in live trading.
  The ten published figures contain 14 empirical panels. **Zero of 238 cells and
  zero of 14 empirical panels are natively regenerated.**

## Release and template boundary

The repository has no Python/system source, package manifest, environment,
runner, tests, configuration, market/news data, prompts with runtime fills,
LLM requests/responses, memory store, strategy pool, action log, orders, fills,
portfolio path, or result arrays. Its Paper/Code/Dataset buttons are commented
and point to HedgeAgents. The bundled 6,141-record MathVista/VQA visualizer is
unrelated template residue and receives no QuantAgents evidence credit.

The complete official Git history is also exhausted as of
2026-08-14: seven commits, one branch, zero tags, and 41 unique
paths. The history is append-only, so its full path union exactly equals the
current static-site tree; there are no deleted or history-only payloads. Every
revision predates the paper by more than a year, and GitHub reports zero public
forks. Thus neither official history nor a fork surface conceals a runnable
QuantAgents implementation or raw result array.

## Material specification conflicts

- Full-system volatility is 1.43% in the main and LLM tables but 1.23% in the
  all-meetings ablation row.
- The appendix prints both an eight-action list and a ten-action list.
- The site describes an older Bitcoin/FX/DJIA 2015--2023 dataset while the paper
  specifies NASDAQ-100 constituents for 2010--2023.
- Live-trading table/prose/plot say Q3 2024--Q1 2025, but the appendix overview
  says Q1--Q3 2024.
- The printed ARR equation annualizes `(terminal/initial - 1)` rather than the
  terminal/initial ratio, and key execution, risk-weight, prompt/parser, strategy
  pool, baseline, seed, and repeated-run details remain absent.

## Temporal-validity boundary

The reported historical test spans 2021--2023, while OpenAI's official system
card says GPT-4o was pretrained using data through October 2023. Most of the
test window is therefore inside the model's knowledge horizon. This is a
material contamination risk, **not** proof that any reported result is false.
The exact `gpt-4o-2024-05-13` snapshot is now deprecated; substituting another
model would be an adaptation rather than exact replication.

A defensible full reproduction requires the actual implementation, point-in-time
NASDAQ-100 membership and frozen Yahoo/Alpaca inputs, complete prompts/tools,
strategy pool, model traces, seeds, execution/cost rules, orders/fills, dated
portfolio paths, baseline lineage, and result-generation code. The local M0
narrative portfolio remains a proxy and receives no QuantAgents mechanism or
result credit. `--strict` intentionally exits nonzero while these boundaries
remain.
