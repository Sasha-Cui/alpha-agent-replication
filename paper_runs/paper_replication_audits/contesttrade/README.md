# ContestTrade paper-level conformance audit

Overall verdict: **not reproduced**. The current paper (arXiv v4) and public
source contain meaningful component-level evidence, but the released CLI does
not execute either contest described as the core contribution.

## Primary sources

- Official paper: https://arxiv.org/pdf/2508.00554v4 (SHA-256 `a2fd14e7e9074c535ab238a4a9028365c860169743e06223bd20302de549a15c`).
- Public source: https://github.com/FinStep-AI/ContestTrade, commit `22432f9bbba5f1d6862d3b6b5508d4d882b40b94` (2025-12-22).

The source snapshot predates paper v4 (2026-07-08). This timing may explain some
formalism/source drift, but it cannot make absent public execution paths or data
count as reproduced.

## What the release genuinely preserves

- A public CLI constructs `SimpleTradeCompany`; its data and research agent paths
  are inspectable, and selected search tools bound requests to dates before the
  trigger date.
- The isolated Data Contest contains five-day reward features and two serialized
  LightGBM models. This audit reads their bytes only (never unpickles them) and
  confirms the five feature names and L1-regression metadata. No training dates,
  split, daily rolling trainer, seed, or dataset accompanies them.
- The isolated Research weight optimizer implements the paper's positive-Sharpe
  normalization rule. This is a component match, not an executed paper portfolio.
- The paper is internally consistent where Table 3 Full repeats the three Table 1
  ContestTrade metrics. Those identities are not independent results.

## Why the claimed system is not replicated

- Static tracing of the actual CLI reaches a three-node graph:
  `run_data_agents -> run_research_agents -> finalize`. Neither `DataContest` nor
  `ResearchContest` is imported or called. `finalize` simply exposes all research
  signals; it does not construct the paper portfolio.
- The isolated Research Contest requires two model files that are not released and
  calls `predict_signal_scores`, which `ResearchPredictor` does not define. Its
  default prediction horizon is three days, while paper v4 specifies five.
- The Data Contest sorts predicted scores and retains top three. It does not implement
  the paper's 32k-to-16k token-budgeted facility-location/lazy-greedy allocation or
  embedding cosine diversity objective.
- Paper Algorithm 1 sums signed rating x price change for ratings -2 through 2. The
  released evaluator ignores every non-positive rating, clips changes to +/-20%, and
  averages over valid observations. The committed synthetic diagnostic shows, for
  example, paper reward 20 versus released reward 5 for a correct bullish and a
  correct bearish observation.
- The release has no immutable paper input panel, contest scores, selected factors,
  actions, holdings, daily returns, experiment/backtest evaluator, baseline runner,
  ablation driver, or paper-run seeds. The seven JSON caches are market metadata,
  not the paper's news/financial/price inputs or outputs.

## Honest denominator

All **49** numeric cells in Tables 1--3 are enumerated: 27 main performance cells,
4 contest-score cells, and 18 ablation cells. **0/49** are native reproductions and
49/49 are unavailable from released result paths. The three repeated Full/Ours
cells agree internally but are counted only as identities. Static figures, code
presence, model strings, and architectural proxies never receive result credit.

Run `scripts/audit_contesttrade_paper.py` to regenerate this evidence package. Use
`--strict` to fail until the released system executes both contests and reproduces
the native paper data, configurations, trajectories, portfolio, and all 49 values.
