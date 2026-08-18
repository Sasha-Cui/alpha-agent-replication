# P1GPT primary-source replication audit

## Honest outcome

P1GPT is **not faithfully reproduced end to end**. The manuscript is fully and
deterministically reconstructed, and 46/72 displayed Table 2
cells can be checked exactly. Those checks are not the same as regenerating the
multi-agent experiment:

- document reconstruction: 1/1 arXiv version rebuilds twice to byte-identical
  17-page PDFs; normalized extracted text is identical to the published PDF and
  all 34 author/rebuilt pages plus seven embedded assets pass visual QA;
- native P1GPT output verification: 11/12 P1GPT cells match after recovering the
  author-rendered daily position bars and applying them to the pinned present-day
  Yahoo response; AAPL Sharpe computes to 3.3877, normally 3.39 rather than the
  printed 3.38. All three P1GPT Sharpe cells conditionally round as printed with
  251-day annualization, while all nine recomputed rule-baseline Sharpe cells
  jointly require 252 days; no single convention recovers all 12;
- rule baselines: 35/36 cells for B&H, MACD, and SMA independently match; the
  same GOOGL close series that recovers B&H CR, AR, and SR gives 6.14% MDD,
  rather than the printed 6.41%;
- unsupported baselines: 0/24 KDJ+RSI and ZMR cells can be regenerated because
  their windows, thresholds, equilibrium definition, and action rules are absent;
- actual agent replay: 0/12 P1GPT cells regenerate from agent code, prompts,
  requests, responses, and paper-time data, because those inputs are not public.

The 46 exact matches are therefore **result verification**, not full-system
replication. The Yahoo response was pinned during this audit, not by the paper.
The plotted positions are author-rendered outputs, not independently generated
agent decisions.

## Material lookahead finding

The embedded report dated March 24, 2025 discusses iPhone Air preorders and eSIM
approval. Apple did not introduce iPhone Air until September 9 and did not open
preorders until September 12. The same report prints a $3.68T market cap alongside
a $220.73 price; using Apple's then-public 15.022073B share count gives about
$3.316T. This is direct counterevidence to the paper's statement that the
simulation "strictly avoids lookahead bias." It does not prove every daily signal
uses future data, but it prevents unqualified faithfulness or causal-performance
credit.

## Recovered metric conventions

The plots and pinned close series reveal conventions omitted or misstated in the
paper: $1,000 initial capital; unadjusted close; previous-day position applied to
close-to-close P&L; 252/166 annualization; annualized Sharpe with zero risk-free
rate and population standard deviation; and integer positions as high as seven.
The zero risk-free rate conflicts with the paper's 3-month-Treasury statement,
and multi-unit accumulation needs clarification against the "no leverage" claim.
Rounding inversion further rules out a single Sharpe convention: the P1GPT cells'
joint admissible annualization interval is 250.542--251.596 days, while the rule
baselines require 251.857--252.614 days. The same pinned GOOGL close path also
requires starting capital in $998.09--$1,000.48 to round to the reported 4.19%
return but $956.35--$957.85 to round to the reported 6.41% drawdown. These
disjoint intervals preserve both cells as an unresolved data/code-path conflict,
not an extra reproduction.

## Public component boundary

`P1GPT/web_demo` is attributable: the P1GPT GitHub organization owns it and its
commits use Neurowatt identities/emails. Its 38 tracked files include 22 Python
files that compile, a dependency manifest, Docker/Compose/Kubernetes runners,
five Chinese finance prompt cards, and a multimodal request client. It is genuine
R3 static/component evidence. It is not the paper experiment: the paper's daily
prompt is absent, the source sends requests to an unreleased `main-llm` service,
and the database, agents, backtest, and outputs are not shipped. Committed
plaintext credentials were neither used nor reproduced here.

The checked archive is not the only revision inspected. A complete non-shallow
clone contains 36 reachable commits across `main`, `develop`, and `gke/test`.
Every revision was searched for paper-specific content and backtest, result,
metric, position, portfolio, and trade paths; none contains the P1GPT experiment.
The complete public-fork census on 2026-08-14 finds one accessible fork and one
branch ref. Its head is byte-identical to the already-audited official `main`
head, so it adds no commits, paths, prompts, outputs, or result evidence.

## Cited baseline-protocol boundary

The paper says its baselines follow TradingAgents. The cited TradingAgents v7
appendix also describes KDJ+RSI and ZMR only qualitatively, and the nearest
official v0.1.0 source ships no baseline implementation, metric code, or paper
backtest. A later unaffiliated repository guesses 14/9-day KDJ+RSI and 50-day,
1.5-z-score ZMR rules, but it postdates P1GPT, leaves KDJ J as a placeholder,
and contradicts P1GPT's stated SMA windows. It is recorded and explicitly
excluded from native-method or result credit.

## Evidence files

- `paper_version_summary.csv`: pinned primary PDF/source and local identity.
- `paper_source_inventory.csv`: all 12 arXiv source files.
- `author_figure_inventory.csv`: all seven embedded assets.
- `published_result_ledger.csv`: all 72 Table 2 cells.
- `result_recovery_checks.csv`: 48 exact displayed-cell checks and boundaries.
- `recovered_author_plot_positions.csv`: 498 author-rendered daily bar values.
- `market_snapshot_checks.csv`: three pinned present-day Yahoo responses.
- `metric_convention_forensics.json`: Sharpe annualization and GOOGL capital-interval bounds.
- `prompt_inventory.csv`: the sole paper prompt and missing runtime evidence.
- `mechanism_conformance.csv`: 36 mechanism dimensions.
- `specification_gaps.csv`: inputs required for exact replay.
- `internal_consistency.csv`: lookahead, metric, execution, and claim conflicts.
- `public_source_file_inventory.csv`: all 38 web-client files.
- `source_history_inventory.csv`: all 36 reachable web-client revisions.
- `public_fork_branch_ref_snapshot.csv`: the complete dated accessible fork/branch surface.
- `public_fork_unique_head_inventory.csv`: the sole fork head and zero-divergence boundary.
- `public_fork_census.json`: fork completeness, head equivalence, and zero-credit verdict.
- `cited_protocol_lineage.csv`: cited official sources and rejected later guess.
- `public_component_execution.json`: attribution, compile, and private-service boundary.
- `manuscript_rebuilds.json`: deterministic reconstruction and visual-QA record.
- `public_source_discovery.csv`: bounded primary-source and GitHub search record.

Installing additional packages cannot recover the private model service, exact
prompts, paper-time source snapshots, or missing requests/responses. The bounded
search does not prove that private, deleted, historical, or unindexed artifacts
never existed.
