# FinAgent paper replication audit

This is a fail-closed audit of the original KDD 2024 paper, its arXiv v3
source, and the repository linked by the lead author's homepage.  The release
is substantial—142 Python files, prompts,
configs, agent modules, and rule-strategy records—but it is not an executable
experimental package for the published claims.

## Honest outcome

- Paper document: reproduced from pinned source at 43 pages.
- Static released-source mechanisms matching the paper: 13 of 31 audited claims.
- Published result units: **0 of 1061 reproduced** (959 table cells and 102 figure units).
- Overall tier: **R2 / substantial static implementation evidence, no paper-result reproduction**.

No paper-result credit is assigned to values transcribed from LaTeX, plot-only
graphics, rule-strategy parameter records, static compilation, or document
compilation.  The repository contains no exact dataset snapshot, FinAgent
memories, trajectories, action/equity paths, checkpoints, or native result
tables.  All 7 reachable commits
were checked and none contains an agent-output path.  The 90 shipped rule
records yield 288
default/trained comparisons against the corresponding high-precision Appendix
Table 7 cells, with 0
display-precision matches; no released code path writes those opaque `best_*`
records.

## Material protocol conflicts

The full validation runner renders the k-line chart with the plotting default
`mode="train"`, while state construction includes 14 future days.  This
exposes future prices to the vision reflection path despite the paper's
no-lookahead claim.  The environment is long-only despite the paper's TSLA
short-position explanation.  Optimized rule parameters are loaded and then
their signals are overwritten by a default-parameter call.  OPTUNA and six
ML/RL baselines are absent.  Released SR/CR/SOR code disagrees with the paper's
equations.  Twenty-one asset-list references (including all eighteen downloader
references), sixty training-prompt references,
and three processor/downloader routes are broken.

The detailed CSVs and `native_execution.json` are the evidence ledger.  A
modern substitute model or reconstructed dataset would be an adaptation, not
an exact reproduction, and must remain labeled accordingly.
