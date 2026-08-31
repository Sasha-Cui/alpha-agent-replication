# AlphaMemo paper-level conformance audit

Overall verdict: **not reproduced**. The official release contains runnable,
deterministic search components, but none of the paper's native inputs,
trajectories, factor pools, predictions, returns, or table outputs.

## Primary sources

- Official paper: https://arxiv.org/pdf/2606.20625v1 (arXiv v1; SHA-256 `64dbd4558ec63a88bbf8fc8245b7eb43443878969531a9661e15c31f6fcedcd0`).
- Official source: https://github.com/jarrettyu/AlphaMemo, commit `412fee13d905bf5a25f0958aa572b7c668ccb925` (2026-05-26).

## Complete public-fork census

- GitHub reported one fork on 2026-08-14, accessible through GraphQL with one
  branch and one unique divergent head. The single extra commit was authored by
  paper coauthor Fengxiang He minutes after the official head.
- That commit changes only `README.md`, replacing `author={...}` with the six
  named paper authors. All 49 tree paths otherwise match the official head. This
  is useful author-provenance corroboration, but it adds no paper input, search
  trajectory, factor pool, prediction, return, metric, table, or figure artifact
  and therefore receives zero paper-result credit.

## Complete reachable source history

- The non-shallow official clone contains exactly two reachable commits, one root,
  one `main` lineage, no tags, and no unreachable objects. Both trees contain 49
  files; only `README.md` changed. There is no hidden paper-result tree analogous
  to AlphaAgent's public legacy branch.
- The root README (SHA-256 `d87aee04c794447755eb5f861834ea0b39bbd01476b08cbb7130be163b83ec79`) recovers the source's
  declared current-draft configuration: budget 500, batch size 10, label horizon
  20, warmup 200, memory weight 0.05, motif sample 4, random motif probability
  0.35, and maximum factor pool 50. It also explicitly calls the Yahoo builders
  approximate and says final numbers require a stable snapshot. Configuration
  provenance is valuable, but it cannot substitute for the absent snapshot.

## What genuinely passes

- The release's one smoke test passes under a compatible Python 3.12 environment.
  Separately, a central Python 3.11.11 environment imports the paper's exact
  declared `pyqlib==0.9.7`, `lightgbm==4.6.0`, `mlflow==3.12.0`, and
  `baostock==0.9.1` pins and passes the author test.
- Two identical native synthetic runs produce the same SHA-256 and the documented
  12-step summary. That smoke has warmup 30, so its last batch starts at step 8 and
  never exercises AlphaMemo's memory-policy branch.
- Two runs of each of all seven released CLI strategy names are deterministic in a
  bounded 32-step synthetic diagnostic with warmup shortened to 8. Instrumentation
  observes AlphaMemo motif-prior, SSPM positive-lambda, and veto APV-resampling
  branches. This validates released control flow only. The configuration is not a
  paper setting, and every diagnostic receives zero paper-result credit.
- `structured` and `graph` produce the same normalized trajectory because both
  names instantiate `StructuredSearchStrategy`; they are aliases, not separate
  replicated methods.
- All five Table 9 formulas execute in the released formula parser on synthetic
  arrays. Their paper metrics cannot be computed without the paper CSI500 panel.
- The active runner matches the two markets, 20-day label, date splits, model alias,
  and all four balanced operating-point values printed in Table 4.
- Sixty-nine pairwise cross-table identities agree exactly. These are repeated
  printed values, never independent empirical reproductions.

## Native current-data pipeline probe

- The released Yahoo builder was run on 2026-08-31 from a pinned official Qlib
  U.S. instrument file. Its first 20 sorted historical symbols yielded 14 market
  assets plus `^GSPC`; `ABC`, `ABK`, `ABMD`, `ABS`, `ACAS`, and `ADS` were no
  longer downloadable. The frozen probe contains 2,511 trading days from
  2016-01-04 through 2025-12-26 and 93 hash-pinned files.
- On that panel, raw `main-table` execution evaluates 12/12 factors, then fails
  during export because `qlib_data.py` defines `SELF_EVO_ROOT` as `parents[3]`,
  one level above the repository. The released qrun wrapper is also tracked as
  mode `100644`, so direct backtest execution raises `PermissionError`.
- A scratch-only template symlink and an executable copy of the byte-identical
  qrun wrapper let the otherwise unchanged source complete twice: factor export,
  LightGBM training, prediction, Top-k/drop portfolio simulation, costs, and all
  19 exported metrics. Search JSON and selected formulas are byte-identical; the
  maximum metric difference across repeats is below `1e-12`. Replay makes zero
  LLM calls and zero network attempts.
- This is not a paper configuration. It uses only 14 current-source stocks, a
  heuristic generator, budget 12, warmup 4, and no CSI500. Zero factors pass the
  released 0.10 admission threshold, yet `main-table` still exports and backtests
  all 12 merely valid candidates because `include_all_ok_candidates=True`.
  Therefore all current-input search, prediction, portfolio, and metric outputs
  receive **zero paper-result credit**.

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
- The bounded real-data replay proves the native downstream pipeline can run only
  after two compatibility repairs; it cannot recover the missing full universe,
  paper-time rows, DeepSeek calls, admitted factor pool, five seeds, or reported
  outputs. Its 19 metrics are diagnostic values, not matches to Tables 2--9.
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

The native synthetic smoke, current-data real-pipeline replay, parser execution,
matching arguments, and internal paper identities remain component evidence. They
receive zero paper-result credit.
Run `scripts/audit_alphamemo_paper.py` to regenerate this package; use `--strict`
to fail until the exact paper inputs, trajectories, pools, outputs, mechanisms, and
all 474 result cells are independently reproduced.
