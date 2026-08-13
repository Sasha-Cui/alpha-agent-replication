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

The pinned repository predates ATLAS v1 and contains no ATLAS identifier,
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
