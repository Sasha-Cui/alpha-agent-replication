# TradingAgents paper-level conformance audit

Overall verdict: **not reproduced**. All seven official revisions and every
reachable public source object were audited. The nearest release implements a
meaningful architecture subset, but not the experiment that produced the paper.

## Primary-source pins

- Official paper record: all seven revisions of arXiv:2412.20138. The current
  revision is https://arxiv.org/pdf/2412.20138v7 (arXiv:2412.20138v7, 2025-06-03T05:45:06Z; PDF SHA-256
  `431d0c39365b4c46b43162371fa15b3dcf8d142b377d642b3e5925dc81f3487b`; source archive SHA-256 `17bc9ebe6c7379ed832ec9915eb147feccda3c8c582a84d93f1f87dfbaf3ed65`).
- The seven pinned PDFs contain 27, 27, 27, 27, 27, 27, and 38 pages. Their
  source archives contain 25--26 files. All preserve the same 77 Table 1 values
  and 42 plotted result series. The comparison plots call the final series
  `StockGPTStrategy` in v1--v6 and `TradingAgents` in v7; the raw comparison
  PDFs were re-encoded for v7, while all three detail PDFs are byte-identical.
- Official source: https://github.com/TauricResearch/TradingAgents, tag `v0.1.0`, commit `cc97cb6d5deb10eac370db0c6678e2796a62eba8`
  (2025-06-05T03:08:28-07:00). It is the first public code release, about 52.4 hours
  after v7. Its parent `635e91ac75f68e5a48eaf0c07760252f73326118` contains only the README and two
  project-site HTML files. The pinned `index_complete.html` (SHA-256
  `7f38e893195179f58364ea760ca61440a791acd6205cb1c12ba5c62909c6e9bf`) contains all 77 Table 1 values in paper order,
  but no paper-date implementation is present in history.

## What genuinely passes

- All 39 tagged Python files compile in a clean Python 3.10 environment resolving
  all 24 release-declared requirements. All 33 source modules import, and the
  actual OpenAI clients, Chroma memories, LangGraph, ToolNodes, source factories,
  and graph compiler deterministically construct a 22-node, 30-edge graph with
  16 tools. HTTP sends are blocked and the constructor makes zero attempts. The
  release did not pin package versions, so this reconstructs a compatible
  declared-dependency environment, not the exact historical environment, LLM
  calls, data, backtest, or paper results. A narrower route/state/signal check
  also remains deterministic with inert audit inputs.
- `reconstructed_environment_freeze.txt` records all 247 resolved package lines;
  its SHA-256 is checked before every dependency-backed audit execution.
- The release contains four analyst roles, structured shared reports, bull/bear
  debate, a research manager, trader, three risk perspectives, role prompts,
  memories/reflection hooks, categorical BUY/SELL/HOLD extraction, and runtime
  state logging. These are substantive mechanism matches or analogues.
- Six of the eleven unique tool names in the published AAPL appendix transcript
  exist exactly in v0.1.0. The arXiv source also ships six vector performance
  figures, whose hashes and visible annotations are inventoried.
- All 77 Table 1 values are present in the official pre-release project-site HTML
  in exactly the paper's order. This corroborates an author-rendered output; it
  does not independently regenerate any cell or expose the underlying arrays.
- The exact 77-value table first appears at `db9f63fa54059ec8ae262ef10557c853b6a011a7`
  (2024-12-28T11:56:38+08:00), before v1. It persists through 15 distinct
  HTML blobs on `index.html` and `index_complete.html`.

## Why the paper is not replicated

- Table 1 has **77 numeric cells**: 68 direct method results and nine derived
  improvements. **77/77** have exact author-output correspondence, but **0/77**
  independently regenerate through the released pipeline. The six result PDFs
  contain **42 plotted series/event groups**; **0/42** regenerate from native
  numeric arrays. Twelve additional quantitative result claims in prose/figures
  also have zero reproductions. Thus all **131 presentation-level empirical
  audit units** have zero independent native reproductions.
- No frozen multimodal dataset, 60-indicator definition, experiment config,
  backtest runner, baseline implementation, metric code, portfolio state,
  position sizing, execution engine, commission/slippage rules, action history,
  order/fill log, NAV/return path, plot array, trial seed, or API-cost ledger is
  released. Offline mode points to an author-local directory that is not shipped.
- The source executes analysts sequentially although the paper says concurrently;
  assigns the quick model to analysts/researchers/trader although the paper says
  deep; conflates the fund manager with the terminal risk judge; outputs only a
  categorical action; and does not wire configured debate/risk/recursion limits
  into the corresponding routing objects.
- Five of eleven appendix tool names are absent from the nearest release. The
  exact AAPL 2024-11-19 transcript and BUY cannot be replayed without its frozen
  inputs, model snapshots, prompts/tool schemas, and trace.
- Full public-history exhaustion found 257 commits, 189 historical paths, 1,009
  blobs, 918 trees, 257 commit objects, seven annotated-tag objects, and no
  unreachable objects. The discovered two branches, ten tags, and eight GitHub
  releases contain no CSV/Parquet/NumPy/notebook/checkpoint/log result path and
  no numeric curve/event arrays. Later source adds tests and a separate Portfolio
  Manager, and another public ref contains a lockfile, but current main has no
  dependency lock and the project still has no paper backtester, baselines,
  metrics, frozen paper data, portfolio execution ledger, or paper outputs.

## Paper-internal barriers

- All 17 displayed CR/AR pairs fail the paper's literal annualized-return formula
  for the stated 89-day period; for example, AAPL TradingAgents CR=26.62% implies
  about 163.43% annualized, not the reported 30.5%.
- GOOGL TradingAgents SR 6.39 minus the best displayed baseline 2.31 is 4.08,
  not the reported 4.26. The improvement row is otherwise mostly absolute metric
  differences despite its percent label.
- GOOGL ZMR has negative CR but positive AR, impossible under the two published
  return formulas for positive N. The prose says MDD never exceeds 2%, while
  Table 1 reports 2.11% for AMZN.
- The setup names AAPL/NVDA/MSFT/META/GOOGL, while the result table reports
  AAPL/GOOGL/AMZN. The exact experiment universe is therefore internally unclear.

## Honest boundary

The architecture and the historical rendered table are real and useful, but a
current one-day run would use mutable data, substantially later source, and
changed model endpoints and would not reproduce the 2024 paper. The vector
figures expose curves, events, and annotations, not their daily numeric arrays.
Run
`scripts/audit_tradingagents_paper.py` to regenerate this package; `--strict`
fails until the native paper data, exact experiment source/configuration, models,
traces, portfolio/execution rules, baselines, daily outputs, and published values
are reproduced.
