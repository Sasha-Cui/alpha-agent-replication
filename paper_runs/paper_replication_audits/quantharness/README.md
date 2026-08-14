# QuantHarness paper-level conformance audit

Overall verdict: **not reproduced after auditing every official paper revision and
the complete public Git history**. The release provides substantial sampled inputs,
an inspectable multi-agent web framework, and author-rendered result images, but not
the experiment runner or native data paths needed to regenerate a published result.

## Primary-source boundary

- All four official revisions of [https://arxiv.org/abs/2509.09995](https://arxiv.org/abs/2509.09995) are pinned by PDF,
  source-archive, and `main.tex` SHA-256. v1/v2 have 30 pages, v3 has 30, and
  current v4 has 32. The v3/v4 `line_chart.pdf` assets are pinned separately;
  the exact submission dates and hashes are recorded in
  `official_paper_version_inventory.csv`.
- The official [https://github.com/Y-Research-SBU/QuantAgent](https://github.com/Y-Research-SBU/QuantAgent) source is pinned at current `main`
  commit `00a88cbbc3b946cbdf506038545d6b5c2df6a344`. The audited public surface contains both branch heads,
  **195 reachable commits**,
  **1870 unique historical paths**,
  **2228 blobs**, no tags, and no
  unreachable objects. Deleted paths and `gh-pages` are included.

## Paper-version evolution and rendered evidence

- v1 and v2 each contain the same **88-cell** random-baseline/Our 4-hour table.
  v3 replaces it with a **152-cell** Baseline/LR/XGBoost/Our table. v4 retains that
  table and adds a **120-cell** portfolio-performance table, for **272** v4 cells.
  The audit therefore enumerates **600 version-specific cells**, representing
  **360 distinct cells** after identical revision tables are deduplicated.
- A historical 1,545x952 author raster completely corresponds to the v1/v2 table.
  Three later author renderings contain the v3/v4 152-cell table; the current
  966x1032 raster is the canonical correspondence. That establishes rendered
  correspondence for **480/600 version-specific cells** and **240 distinct cells**.
  It independently regenerates **0/600**. The v4-only 120-cell table has no source
  raster correspondence.
- History also contains three distinct 1-hour result-chart blobs. Visual inspection
  establishes complete author-raster correspondence between one QuantAgent/DAX chart
  and the official v3 `line_chart.pdf`, and between the current QuantHarness/DAX chart
  and v4. The earlier VIX chart is an intermediate historical output, not an official
  paper figure. None ships plotted arrays, segment predictions, or exact point-level
  values, so all three receive zero numeric reproduction credit.

## Complete source-history finding

- The 1,870 historical paths include **1,800 benchmark CSVs** across 18 historical
  asset/horizon directories. Every directory contains 100 sampled 100-row segment
  paths. The current release retains 1,600 CSVs across 16 sets; historical GC/DXY
  directories do not supply the original 5,000-bar panels or result outputs.
- Across all commits there is no non-benchmark CSV, JSONL, NumPy array, Parquet/HDF,
  pickle, checkpoint, model, log, prediction, risk-ratio, return, equity, portfolio,
  split, or seed artifact attributable to a paper run. Four table-image blobs and
  three one-hour chart blobs are exhaustively pinned in
  `historical_result_image_inventory.csv`; none contains an underlying native path.

## What is genuinely established

- The repository ships all 1,600 advertised sampled CSVs: 16 asset/horizon sets,
  100 files per set, and 100 OHLCV rows per file. Every sampled union reaches the
  exact start and end dates printed in Tables 3--4. The overlapping samples expose
  4,082 distinct timestamps in 15 sets and 4,440 for 1-hour DAX, not the original
  5,000-bar panels, so segment sampling itself cannot be rerun.
- Reconstructing the stated LR baseline with the most recent 40 closes available
  after withholding rows 97--99 gives **0/8** Table 2 accuracy matches. A bounded
  exhaustive search finds one and only one alignment that matches all eight printed
  accuracies: feature rows 54--93, reference close row 96, outcomes rows 97--99.
  That leaves rows 94--96 as an undocumented three-bar feature gap.
- Using those inferred LR directions and the paper's best/worst OHLC formulas gives
  7/16 Rmax/Rmin display matches. The natural paper-described directions give 0/16.
  These are forensic diagnostics, not a native evaluator reproduction.
- 23/24 printed delta-accuracy cells are rounding-consistent with percentage change
  from the printed random-baseline accuracy. SPX "Our" reports +34.6%, while its
  displayed 63.7% and 47.3% accuracies imply +34.7%. Hidden unrounded values could
  explain this; either way, these are identities, not independently reproduced data.

## Why current v4 is not reproduced

- Every one of the 120 numeric Table 1 cells lacks a released return/equity path and
  metric evaluator. Table 1 includes AAPL and AMZN, for which no benchmark directory
  is released. The eight TradingAgent max-drawdown values are positive while every
  other numeric drawdown is non-positive; without the evaluator, the sign convention
  cannot be resolved.
- Of Table 2's 152 numeric cells, 104 have no reconstructible native result path.
  The public tree has no random or XGBoost evaluator, 50/50 split, model, predictions,
  random seed, LR code, Rcc implementation, agent predictions, or risk-ratio records.
  The remaining checked cells are either prose reconstructions, an inferred alignment,
  or identities among already printed values.
- The paper names Indicator, Pattern, Trend, and Risk agents. The source has Indicator,
  Pattern, Trend, and Decision modules and no `risk_agent.py`. Its Decision prompt does
  preserve LONG/SHORT and the 1.2--1.8 risk-ratio range.
- The paper does not disclose the trading-run LLM models or temperatures. Source defaults
  are GPT-4o-mini for agents, GPT-4o for graph/decision, and temperature 0.1 for both,
  but there is no evidence tying those mutable defaults to the published outputs.
- The active public `run_analysis` path uses `df.tail(45)`; the only slice excluding
  the final three rows is commented out. If a released 100-row benchmark segment is
  passed to that active path, the held-out outcome rows are exposed. The paper experiment
  path is absent, so this is a release-path leakage risk, not proof of how authors ran it.
- Figure 5 and the 8/10 SPX case study are released only as static images, without
  numeric predictions or selected segment identifiers. Dependencies are unpinned and
  the shipped tests cover provider integration rather than paper-benchmark behavior.

## Honest denominator

Across revisions, **0/600** version-specific result cells are independently regenerated.
The 480 author-rendered correspondences are tracked separately and never promoted to
native credit. Within current v4's **272** cells, there are 23 internally consistent
derived identities and one displayed mismatch, 8 LR accuracy mismatches under the
stated window, 16 inferred-gap extrema diagnostics (7 display matches), and 224
unavailable cells. No proxy, inferred alignment, author raster, or static figure is
promoted to a faithful end-to-end result.

Run `scripts/audit_quantharness_paper.py` to regenerate this package. Use `--strict`
when CI should fail until native predictions, evaluator paths, exact configuration,
seeds/splits, portfolio series, and numeric 1-hour outputs reproduce the paper.
