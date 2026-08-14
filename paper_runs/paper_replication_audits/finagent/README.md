# FinAgent paper replication audit

This is a fail-closed audit of the original KDD 2024 paper, all three official
arXiv versions and source archives, and the repository linked by the lead
author's homepage.  The release is substantial—142 Python
files, prompts, configs, agent modules, and rule-strategy records—but it is not
an executable experimental package for the published claims.

## Honest outcome

- Paper document: reproduced from pinned source at 43 pages.
- Official-version lineage: v1 and v2 contain 768 identical table cells; v3
  contains 959. Relative to v1/v2, v3 numerically revises
  27 shared cells, changes display precision for
  55, adds 198 cell IDs, and removes
  7. The 31 result-figure source assets are byte-identical across all
  three versions.
- Public source timing: v1 and v2 predate the repository; v3 has the six-commit
  paper-era tree available. Only v3 is evaluated against public implementation.
- Static released-source mechanisms matching the paper: 13 of 31 audited claims.
- Published result units: **0 of 1061 reproduced** (959 table cells and 102 figure units).
- Overall tier: **R2 / substantial static implementation evidence, no paper-result reproduction**.

No paper-result credit is assigned to values transcribed from LaTeX, plot-only
graphics, rule-strategy parameter records, static compilation, or document
compilation.  The repository contains no exact dataset snapshot, FinAgent
memories, trajectories, action/equity paths, checkpoints, or native result
tables. All 7 reachable commits, 1955 historical paths, and
1902 blobs were checked; no unreachable object or native agent-output path
exists. The only discovered branch is `main`, with no tags or releases. The 90
shipped rule records yield 288 default/trained comparisons against the
corresponding high-precision Appendix Table 7 cells, with
0 display-precision matches; no released code path writes those opaque
`best_*` records.

A dated GitHub census covers all 26
reported and accessible public forks and 30
branch refs, collapsing to 7 unique heads.
Both official-history heads and all 5
divergent heads were checked. The divergent surface contains
27 unique extra commits,
93 changed paths, and
24 new final-tree blobs. It is
limited to unaffiliated post-paper function-calling, prompt/news, and FTSE MIB
source/data-pipeline adaptations. No divergent commit matches an official-source
author identity, and no native agent result or exact paper table/figure artifact
was found; all fork evidence receives zero paper-result credit.

## Material protocol conflicts

The full validation runner renders the k-line chart with the plotting default
`mode="train"`, while state construction includes 14 future days.  This
exposes future prices to the vision reflection path despite the paper's
no-lookahead claim.  The environment is long-only despite the paper's TSLA
short-position explanation.  Optimized rule parameters are loaded and then
their signals are overwritten by a default-parameter call.  OPTUNA and six
ML/RL baselines are absent.  Released SR/CR/SOR code disagrees with the paper's
equations.  Twenty-one asset-list references (including all eighteen downloader
references), sixty training-prompt references, and three processor/downloader
routes are broken.

The detailed CSVs and `native_execution.json` are the evidence ledger.  A
modern substitute model or reconstructed dataset would be an adaptation, not
an exact reproduction, and must remain labeled accordingly.
