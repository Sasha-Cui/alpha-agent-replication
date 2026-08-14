# ContestTrade paper-level conformance audit

Overall verdict: **not reproduced**. All four official arXiv versions and all
discovered public source refs have now been audited. The release provides useful
component and author-output evidence, but no public revision executes the claimed
system end to end or regenerates a paper result.

## Primary sources and chronology

- Official paper record: https://arxiv.org/abs/2508.00554. The v1--v4 PDFs and
  TeX source archives are hash-pinned (35
  PDF pages and 47 source files).
  Every version retains the same 49 table cells and 15 result-figure series.
- Public source: https://github.com/FinStep-AI/ContestTrade, current commit `22432f9bbba5f1d6862d3b6b5508d4d882b40b94`. Discovery covers main and
  dev, tags v1.0/v1.1/v2.0, no GitHub releases, 130
  reachable commits, 132 historical paths,
  720 objects, and no
  unreachable objects.
- Public forks: the 2026-08-14 REST snapshot listed
  157 repositories. Four stale listings
  returned 404/inaccessible Git endpoints; all 153
  git-accessible forks were exhausted across 186
  branch refs and 26 tag refs. Their
  52 unique heads include
  21 divergent heads, collectively adding
  88 commits,
  200 changed paths, and
  381 genuinely new blobs beyond
  the explicit official-history boundary.
- Paper v1 was submitted on 2025-08-01, before the public repository's first commit
  on 2025-08-08 and before its first code tree on 2025-08-11. At v2 and v3 submission,
  the public tree still contained neither the Data Contest nor Research Contest.
  Those first appeared on 2025-08-26 and 2025-08-27, respectively.
- Paper v4 (2026-07-08) postdates the current source head (2025-12-22), but the later
  paper date cannot turn absent execution paths, inputs, or results into a replication.

## What the release genuinely preserves

- `assets/performance_comparison.jpg` is byte-for-byte identical to the original v1
  paper's main-result raster. This corroborates the authorship and lineage of all nine
  visible curves, but the repository has no underlying dates/values and the revised
  v2--v4 raster and six-series ablation raster occur only in paper source archives.
- The isolated Data Contest contains five-day reward features and two serialized
  LightGBM models. This audit reads their bytes only (never unpickles them) and confirms
  the five feature names and L1-regression metadata. No training dates, split, daily
  rolling trainer, seed, or dataset accompanies them.
- The isolated Research weight optimizer implements positive-Sharpe normalization.
  This is a component match, not an executed paper portfolio.
- The paper's repeated Full/Ours table cells are internally identical across all
  versions. Repetition and author-rendered rasters are not independent reproductions.

## Why the claimed system is not replicated

- Exhaustive scanning of all 322 reachable blobs finds no CSV, Parquet, NumPy,
  checkpoint, notebook, JSONL, or other native structured result path and no text blob
  containing a complete paper result row. There are no raw numeric curves, contest
  scores, selected factors, actions, holdings, daily returns, or run logs.
- The fork-only blob scan likewise finds zero complete paper result rows. One fork adds
  a date-loop command called `backtest`, but its function only invokes
  `SimpleTradeCompany`, prints research-signal counts, and never calls either contest,
  constructs holdings/returns, or calculates Sharpe/drawdown. No fork head repairs the
  missing Research models/method or adds the facility-location allocator.
- One later personal fork commits two versions of `agents_workspace/portfolio.json`.
  They contain 16 mixed manual/AI trade records (nine manual, seven AI) and 21/25
  intraday snapshots from 2026-02-02 through 2026-02-04. They are useful evidence that
  a community auto-trading adaptation ran, but they are not the paper experiment panel,
  are manually intervened, contain no paper metrics, and receive zero paper credit.
- Three other fork paths are runtime failure diagnostics; the longest terminates in a
  LangGraph recursion error followed by a missing-`traceback` `NameError`. An exact
  paper-v3 PDF copy and U.S.-market news inputs are provenance/input evidence only.
- Static tracing of the actual CLI reaches `run_data_agents -> run_research_agents ->
  finalize`. Neither `DataContest` nor `ResearchContest` is called, and `finalize`
  exposes all research signals without constructing the paper portfolio.
- The isolated Research Contest requires two absent model files and calls
  `predict_signal_scores`, which `ResearchPredictor` does not define. Its default
  prediction horizon is three days, while paper v4 specifies five.
- The Data Contest sorts predicted scores and retains top three. No public revision
  implements the paper's 32k-to-16k token-budgeted facility-location/lazy-greedy
  allocator or embedding-cosine diversity objective.
- Paper Algorithm 1 sums signed rating x price change. The released evaluator ignores
  non-positive ratings, clips price changes to +/-20%, and averages observations. The
  synthetic diagnostic gives paper reward 20 versus released reward 5 for one correct
  bullish and one correct bearish observation.
- The release lacks the immutable experiment panel, backtester/metric evaluator,
  baseline and ablation runners, complete model/API snapshot, and run seeds. Its seven
  JSON caches are market metadata, not paper inputs or outputs.

## Honest denominator

The paper has **64 result display units**: 49 numeric table cells (27 main performance,
4 contest-score, 18 ablation) plus 15 raster-only return series (9 main, 6 ablation).
**0/64** are independently reproduced. The exact v1 raster is recorded separately as
an author-output correspondence for nine series and receives no result credit. All 49
table cells and all 15 numeric curves remain unavailable from native result paths.

Run `scripts/audit_contesttrade_paper.py` to regenerate this package. Use `--strict`
to fail until the released system executes both contests and reproduces the pinned
paper inputs, configurations, trajectories, portfolio, curves, and all 49 table cells.
