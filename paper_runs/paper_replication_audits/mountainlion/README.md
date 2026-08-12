# MountainLion primary-source replication audit

## Honest outcome

The MountainLion paper is **not faithfully reproduced**. The audit verifies the
primary manuscript, two attributable public codebases, several real product
components, and paper-declared formulas. It regenerates **0/20**
published forecasting-performance cells and none of the material return,
accuracy-improvement, retrieval-efficiency, whale-detection, engagement, or
ablation claims.

There is no defensible single percentage for overall paper faithfulness because
document reconstruction, component correspondence, and experimental replay are
not interchangeable. The auditable breakdown is:

- manuscript reconstruction: 2/2 arXiv versions build deterministically to all
  17 pages and pass full contact-sheet visual QA;
- prompt documentation: 7/7 verbatim templates are present, but 0/7 substituted
  requests, exact runtime configurations, or responses are released/replayed;
- public product components: the 153-file frontend builds twice to the same 67
  artifacts, and the 199-file paper-time platform core compiles;
- experimental reproduction: 0/20 Table 1 CV/MSE cells and 0 material outcome
  claims reproduce from a native paper pipeline.

## What the recovered repositories establish

The `MountainLionAi/MountainLion` frontend is strongly attributable: its author
email corresponds to paper-v2 author Jinhao Wang, and its API exports match the
appendix endpoints (`getCoinList`, `getKlineInfo`, `sendChat`, and
`getPredictInfo`). Under Node 20.13.1, its locked install and Vite build pass; two
builds have byte-identical file manifests.

The paper-time `MountainLionAi/GenAI-Platform` snapshot is also attributable.
Its README states that mlion.ai uses the platform; it contains RAG, Perplexity,
multi-agent infrastructure, a `kline_predictd` database reader, and exactly the
ten Table 1 tokens in its price-prediction menu. These are genuine component
correspondences, not a forecast experiment. The reader returns three already
computed database rows; it does not fit models or generate Table 1.

## Decisive reproduction boundary

The public package contains no paper training panel, exchange/date/frequency,
preprocessing, split, model specification, fitted model, cross-validation
protocol, prediction array, realized target array, or table-generation runner.
It also depends on unreleased `ml4gp` product modules, private MySQL/Redis state,
external credentials, and a product plugin. Public tests are absent (the sole
`tests/__init__.py` is empty). Installing more packages cannot recover those
private inputs or the missing experiment lineage.

The paper's only numeric result table has 30 numeric units: 10 ambiguous `Alpha`
configuration cells plus 20 CV/MSE performance cells. Raw MSE is compared across
tokens with radically different price scales, so the prose claim that TRX is the
best performer is not justified without a normalization convention. The paper
also claims improved returns and extensive ablations without reporting a return
path, transaction costs, an ablation table, or an ablation protocol.

The author-rendered comparison figure and six diagram assets are preserved in
both source versions. They establish what the authors placed in the paper, not
how the outputs were produced. No underlying prompt response, source panel, or
numeric array is shipped, so the figure receives no result-reproduction credit.

## Evidence files

- `paper_version_summary.csv`: pinned PDFs and source archives.
- `paper_source_inventory.csv`: every file in both primary TeX bundles.
- `published_table_numeric_ledger.csv`: all 30 Table 1 numeric units.
- `author_figure_inventory.csv`: all 12 versioned figure assets (6 unique).
- `prompt_inventory.csv`: all seven verbatim prompt templates and runtime gaps.
- `material_claims.csv`: central quantitative and qualitative outcome claims.
- `mechanism_conformance.csv`: 38 paper-mechanism dimensions.
- `specification_gaps.csv`: exact missing inputs needed for replay.
- `internal_consistency.csv`: ambiguities and paper-internal conflicts.
- `public_source_snapshot_summary.csv`: three pinned public-code snapshots.
- `public_source_file_inventory.csv`: every paper-relevant frontend/platform file.
- `source_component_checks.csv`: executed and source-semantic component checks.
- `paper_formula_component_checks.csv`: synthetic checks of declared equations.
- `source_component_execution.json`: build/compile evidence and runtime blockers.
- `manuscript_rebuilds.json`: deterministic builds and visual-QA record.
- `public_source_discovery.csv`: attributable-source and bounded-search record.

The negative search boundary is deliberately narrow: this audit does not prove
that private, deleted, historical, or unindexed artifacts never existed.
