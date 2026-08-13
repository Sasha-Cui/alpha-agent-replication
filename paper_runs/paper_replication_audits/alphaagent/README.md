# AlphaAgent paper-level conformance audit

Overall verdict: **the paper results are not reproduced, but the paper-era
implementation is substantially recovered**. The previous audit looked only at
the rewritten default branch and was materially too pessimistic about mechanism
availability.

## Primary-source pins

- Final paper: https://arxiv.org/pdf/2502.16789v2 (arXiv v2, 2025-06-09; SHA-256 `cf620c3b33a98edd4124230458b65741e1767fa37a3a180828de1035ded52ab1`).
- Original preprint: https://arxiv.org/pdf/2502.16789v1 (10 pages; SHA-256 `943b286b40186ce03b8e39fc0dbd2f268807042c6192e9200e68972cb45ab890`).
- Official repository: https://github.com/RndmVariableQ/AlphaAgent. It has two unrelated Git roots, not one
  continuous history: 8 commits on rewritten `main` and 485 on public
  `legacy-main`, 493 reachable commits in total.
- Mechanism snapshot: `95e47882cbed3ba0cafd42e812fe0032a8ae0681` (2025-02-12), before arXiv v1.
  It contains 856 tracked files, including 331 Python modules and 15 factor CSVs.
- The 2025-02-17 preprint-cutoff commit `0bc7a34ed9701a0149ae990b6484e7c73b347ea0` removed the
  factor zoo. The audit intentionally pins the earlier mechanism-complete tree
  and records that deletion instead of pretending the cutoff head is runnable.
- Rewritten main: `b42cb397025510da44355db9dcf278304321f589` (2026-07-03). Its first commit is
  `7debd15ca98309a8df9c1d50aca3831f320687cf` (2026-07-01T20:17:13+08:00) and has no common ancestor with the
  paper-era branch.

## What genuinely passes

- All 331 Python modules in the paper-era snapshot compile under Python 3.12.
- The paper-era AST parser executes twice deterministically. Identical,
  commutative, and partially shared expressions return largest-common-subtree
  sizes 4, 3, and 3. An exact Alpha101 probe matches itself with size 23.
- The loaded `alpha101.csv` has 116 rows: 101 named Alpha101 references plus 15
  appended generated expressions. That supports the paper's originality path but
  also exposes reference-zoo contamination that must be reported, not hidden.
- The historical source implements the structured hypothesis fields, multi-stage
  proposal/construct/calculate/backtest/feedback loop, factor-expression parser,
  prose description-expression alignment critic, failed/successful implementation
  memory, multi-candidate generation, and metric feedback into later rounds.
- Historical CN/US Qlib configs recover the four OHLCV feature formulas,
  next-day label, train/validation/test segments, full LightGBM kwargs, Qlib
  signal/portfolio records, top-50/drop-5 combined strategies, and stated fees.
- Fifteen historical factor CSVs contain 268 expression rows. Names identify CN,
  US, GP, o1, and DeepSeek candidate pools, but no released lineage proves which
  file or row produced any published metric.
- Separately, all 80 tests in the 2026 rewrite pass with import-only Tushare and
  AgentScope stubs, and its four synthetic base factors are deterministic. Those
  checks receive no paper-result credit.

## Why the paper is still not replicated

- Table 2 has **100 numeric result cells**. **0/100** has a released native result
  path. Eighteen more quantitative result claims in figures/text are also 0/18.
  No prediction, holding, daily return, Qlib recorder, baseline output, figure
  array, token log, trial sample, or p-value sample survives.
- The exact Baostock CSI500 and Yahoo S&P500 panels, constituent histories, and
  data transformations are absent. The US config points only to unversioned local
  `us_data`; it does not establish Yahoo provenance or frozen panel identity.
- The code defaults to GPT-4-turbo, while the paper reports GPT-3.5-turbo. The
  executed model/API snapshot, temperature, seeds, token limits, initial research
  directions, and 20 independent trial trajectories are not pinned.
- The paper's displayed regularizer is not faithfully implemented. The source has
  AST largest-subtree matching and a hard retry at duplicated size >=5, but no
  symbolic-length term, free-parameter count, numeric c1/c2 alignment scores,
  alpha=0.5 combination, beta-weighted ER function, normalization, or disclosed
  objective weights/acceptance thresholds.
- The paper says lower ER is better while adding an alignment term described as
  higher-is-better. That sign ambiguity, plus undisclosed alpha/beta weights and
  thresholds, prevents an exact objective even with recovered source.
- Historical configs substantially recover model/backtest settings, but no
  executed-config hash, trained LightGBM state, seed, recorder, or mapping from a
  factor CSV to Table 2 exists. Configuration presence is not result reproduction.

## Honest boundary

The official historical source is much closer to the paper than the rewritten
default branch: this is a **substantial mechanism implementation**, not merely an
analogue. It is still not an end-to-end replication of the published experiments.
The 2026 CSI1000/Tushare data package, DSL expressions, and registry metrics belong
to a disjoint rewrite and receive zero paper credit. Run
`scripts/audit_alphaagent_paper.py` to regenerate the package; `--strict` remains
fail-closed until paper-era inputs, executed trials, models, portfolios, and every
published result are reproduced.
