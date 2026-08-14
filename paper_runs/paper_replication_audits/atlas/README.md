# ATLAS paper and cited StockSim component audit

This audit pins all five official revisions of arXiv `2510.15949`, every
source package, and the cited same-author StockSim repository at `c1a25c1`.
Each source revision rebuilds to the official page count: 37 pages for v1 and
43 pages for v2-v5. All 209 official and all 209 rebuilt pages were visually
checked side by side. No unreadable, clipped, overlapping, blank, or missing
research content was found. This establishes excellent document-source
reproducibility, not experimental reproducibility.

The current v5 source contains 1,784 printed empirical scalar units across 11
result tables. It also contains 10 figures with 12 total panels, of which five
panels plot empirical results. The source exposes the author-rendered tables,
plot coordinates, architecture diagrams, prompt templates, evolved-prompt
examples, and detailed method prose. Rebuilding those author-authored assets
does not independently regenerate an ATLAS result.

StockSim is a genuine first-party precursor component: repository owner
Charidimos Papadakis is the paper's first author, and the paper cites StockSim.
The pinned release has 81 files and 43 Python modules, but no author tests. Its
declared environment installs an obsolete PyPI `asyncio` backport whose
`tasks.async` syntax is invalid on Python 3.12. After removing only that
backport in an isolated audit environment, dependency checking and bytecode
compilation pass, all 43/43 modules import, and four controlled checks cover
config validation, metrics, order matching, and candle-trigger semantics.
Those are StockSim component checks only and receive no ATLAS result credit.

The complete public StockSim history comprises 20 commits across `main` and
`website`, with zero tags, zero releases, 107 unique historical paths, and no
unreachable objects. The initial commit contained four later-deleted Plotly
charts. Three are market-analysis-only LLY/NVDA charts. `charts/XOM.html`
contains a native precursor run with 20 dated, explained orders and a 43-point
portfolio path over the paper's exact XOM window; it ends at $105,015.64, or
+5.01564% from the stated $100,000 cash. This value matches none of the 26
published ATLAS XOM ROI means, and the artifact has no ATLAS, prompting-strategy,
model, seed, or paper-run identifier. It is recoverable StockSim native-output
evidence, not an attributable ATLAS run or a regenerated paper result.

A 2026-08-14 census also exhausts all five public forks: 11 branch refs resolve
to eight unique heads. Four refs exactly match the official `main` head. The
remaining seven heads belong to one active fork and collectively add 12 commits,
26 trees, 22 blobs, and 13 changed paths after ATLAS v5. Those are genuine
StockSim engineering changes covering AML agents, portfolio accounting,
timestamp handling, synchronization, market microstructure, and two
self-trade-prevention tests. No changed or reachable file contains an ATLAS,
Adaptive-OPRO, paper-ID, promised-config, checkpoint, trajectory, action,
rating, or result payload. None of the 12 commit author display names exactly
matches a paper author. The work therefore improves StockSim but supplies no
attributable ATLAS experiment or result evidence.

The StockSim demo config is also closer to the method than a generic example:
it exactly matches XOM, 2025-04-28 through 2025-06-28, daily decisions,
$100,000 initial cash, and the market/news/fundamental analyst roles. It does
not contain the ATLAS central-agent implementation, Baseline/Reflection/
Adaptive-OPRO strategy logic, LLY/NVDA experiment configs, seven-model matrix,
or three-run design. Ten later JSON files contain 191,015 AAPL orders from
2025-03-01 for order-book replay and are unrelated to the ATLAS daily study.

Every official revision predates ATLAS v1 and contains no ATLAS identifier,
Adaptive-OPRO implementation, promised
`configs/o4-mini-adaptive-opro-config.yaml`, exact three-asset experiment
configuration, frozen Massive/Polygon data, news or fundamental inputs, model
requests/responses, filled runtime prompts, optimizer trajectory, seeds, run
artifacts, or result arrays. Its demo launcher validates an XOM configuration
but then correctly stops without RabbitMQ, a log directory, and a market-data
API key. Supplying those services would run a StockSim demo, not the paper.

The strict paper-level result is therefore **0/1,784 empirical numeric table units
and 0/5 empirical panels regenerated**. The table-derived correlations
reported in the paper can be recomputed from rounded published values, but
that is only an internal-consistency check. ATLAS is richly specified and its
manuscript is fully rebuildable, but not currently a true experimental replication
package. The short two-month, three-asset study and deterministic
execution abstraction also limit claims about generalization or live trading.
