# QuantHarness paper-level conformance audit

Overall verdict: **not reproduced**. The release provides unusually substantial
sampled benchmark inputs and an inspectable multi-agent web framework, but not the
paper experiment runner, predictions, risk-ratio paths, baseline implementations,
portfolio paths, random splits/seeds, or numeric one-hour result paths.

## Primary sources

- Official paper: https://arxiv.org/pdf/2509.09995v4 (arXiv v4; SHA-256 `751e6e7274bbf1fd5179153a28d2d29817c704b5d9b714b04ba57bd739cafda2`).
- Public source: https://github.com/Y-Research-SBU/QuantAgent, commit `00a88cbbc3b946cbdf506038545d6b5c2df6a344`.

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

## Why QuantHarness is not reproduced

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

The audit enumerates all **272** numeric cells in Tables 1--2. **Zero** is counted as
a native paper-result reproduction. There are 23 internally consistent derived cells
and one displayed derived-cell mismatch, 8 LR accuracy mismatches under the stated
window, 16 inferred-gap extrema diagnostics
(7 display matches), and 224 unavailable cells. No proxy, inferred alignment, or static
figure is promoted to a faithful end-to-end result.

Run `scripts/audit_quantharness_paper.py` to regenerate this package. Use `--strict`
when CI should fail until native predictions, evaluator paths, exact configuration,
seeds/splits, portfolio series, and numeric 1-hour outputs reproduce the paper.
