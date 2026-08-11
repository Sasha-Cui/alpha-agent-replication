# TradingAgents paper-level conformance audit

Overall verdict: **not reproduced**. The nearest official release implements a
meaningful architecture subset, but not the experiment that produced the paper.

## Primary-source pins

- Official paper: https://arxiv.org/pdf/2412.20138v7 (arXiv:2412.20138v7, 2025-06-03T05:45:06Z; PDF SHA-256
  `431d0c39365b4c46b43162371fa15b3dcf8d142b377d642b3e5925dc81f3487b`; source archive SHA-256 `17bc9ebe6c7379ed832ec9915eb147feccda3c8c582a84d93f1f87dfbaf3ed65`).
- Official source: https://github.com/TauricResearch/TradingAgents, tag `v0.1.0`, commit `cc97cb6d5deb10eac370db0c6678e2796a62eba8`
  (2025-06-05T03:08:28-07:00). It is the first public code release, about 52.4 hours
  after v7. Its parent `635e91ac75f68e5a48eaf0c07760252f73326118` contains only the README and two
  project-site HTML files, so no paper-date implementation is present in history.

## What genuinely passes

- All 39 tagged Python files compile under Python 3.12. The actual tagged graph
  setup, routing, state initialization, and signal extraction execute twice with
  identical output when unavailable framework imports are replaced by import-only
  fakes. This validates deterministic topology components, not the dependency
  environment, LLM calls, data, backtest, or paper results.
- The release contains four analyst roles, structured shared reports, bull/bear
  debate, a research manager, trader, three risk perspectives, role prompts,
  memories/reflection hooks, categorical BUY/SELL/HOLD extraction, and runtime
  state logging. These are substantive mechanism matches or analogues.
- Six of the eleven unique tool names in the published AAPL appendix transcript
  exist exactly in v0.1.0. The arXiv source also ships six vector performance
  figures, whose hashes and visible annotations are inventoried.

## Why the paper is not replicated

- Table 1 has **77 numeric cells**: 68 direct method results and nine derived
  improvements. **0/77** has a native released result path. Twelve additional
  quantitative result claims in prose/figures also have zero reproductions.
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

The architecture is real and useful, but a current one-day run would use mutable
data and changed model endpoints and would not reproduce the 2024 paper. The
vector figures expose annotations, not their daily numeric arrays. Run
`scripts/audit_tradingagents_paper.py` to regenerate this package; `--strict`
fails until the native paper data, exact experiment source/configuration, models,
traces, portfolio/execution rules, baselines, daily outputs, and published values
are reproduced.
