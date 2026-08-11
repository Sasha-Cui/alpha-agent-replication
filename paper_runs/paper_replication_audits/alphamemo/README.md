# AlphaMemo paper-level conformance audit

Overall verdict: **not reproduced**. The official release contains runnable,
deterministic search components, but none of the paper's native inputs,
trajectories, factor pools, predictions, returns, or table outputs.

## Primary sources

- Official paper: https://arxiv.org/pdf/2606.20625v1 (arXiv v1; SHA-256 `64dbd4558ec63a88bbf8fc8245b7eb43443878969531a9661e15c31f6fcedcd0`).
- Official source: https://github.com/jarrettyu/AlphaMemo, commit `412fee13d905bf5a25f0958aa572b7c668ccb925` (2026-05-26).

## What genuinely passes

- The release's one smoke test passes under a compatible Python 3.12 environment.
- Two identical native synthetic runs produce the same SHA-256 and the documented
  12-step summary. This validates a deterministic heuristic component only.
- All five Table 9 formulas execute in the released formula parser on synthetic
  arrays. Their paper metrics cannot be computed without the paper CSI500 panel.
- The active runner matches the two markets, 20-day label, date splits, model alias,
  and all four balanced operating-point values printed in Table 4.
- Sixty-nine pairwise cross-table identities agree exactly. These are repeated
  printed values, never independent empirical reproductions.

## Why the paper is not replicated

- Across Tables 2--9 there are **484 numeric experimental cells**: 474 results and
  10 configuration cells. **0/474 result cells** have a native released result path.
  Four balanced configuration cells match the official runner; configuration is
  not performance.
- No Qlib CSI500/S&P500 snapshot, exact universe history, LLM request/response log,
  search trajectory, admitted pool, selected-factor artifact, prediction, holding,
  daily return, Qlib recorder, baseline output, random seed run, or table CSV is
  tracked. The current-download data builders cannot recreate the authors' frozen
  data state.
- The advertised `run_main.sh` uses `SUCCESS_ICIR=0.02`, while the paper specifies
  an admission threshold of 0.10. It runs only one balanced AlphaMemo seed; no exact
  residual, fixed-budget, eight-baseline, or NoGate/AbsOLM/ManualMut/NoAPV runner is
  released. The paper does not disclose the numeric fixed discovery budget.
- The paper describes typed, canonical AST differencing with insert/delete/replace/
  move/parameter edit scripts. Released motif extraction uses regex-derived sets of
  operator names, windows, and features. The selected label is also supplied to the
  generator as a mutation command, contrary to the paper's claim that labels are
  observed after generation rather than hand-written commands.
- The paper context is `(category, quality bucket, depth bucket, retrieval bucket)`;
  released memory is keyed only by `(category, motif)`. Its residual baseline,
  confidence formula, warmup schedule, and balanced APV selection differ from the
  equations, and only admitted successes enter the DAG although the paper says all
  evaluated children enter the ledger.

## Honest boundary

The native synthetic smoke, parser execution, matching arguments, and internal
paper identities remain component evidence. They receive zero paper-result credit.
Run `scripts/audit_alphamemo_paper.py` to regenerate this package; use `--strict`
to fail until the exact paper inputs, trajectories, pools, outputs, mechanisms, and
all 474 result cells are independently reproduced.
