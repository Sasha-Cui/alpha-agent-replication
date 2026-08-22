# TradingGroup paper-level replication audit

Overall verdict: **paper document, exact test data, formulas, and all eligible
source-adjacent baselines reproduced; native TradingGroup experiment not
reproduced**.

## What is faithfully recovered

- The official nine-page arXiv v1 PDF/source are byte-pinned, repeat-download
  identical, source-rebuilt, and visually checked on every page. The rebuild has
  99.75% extracted-token multiset overlap with the official PDF.
- All **360 displayed numeric table cells** are transcribed: 240 in Table 1, 40
  in Table 2, and 80 in Table 3. The 20 all-enabled Table 3 cells are exact
  duplicates of the Table 1 TradingGroup row, leaving 340 unique table cells.
- The hash-pinned author-linked FINSABER aggregate data exactly confirms all
  stated test-set facts: 127 dated price observations for every ticker; daily
  TSLA/MSFT news, 22 AMZN news dates, no NFLX/COIN news; MSFT quarterly-only
  filings; and both filing types for the other four tickers.
- The exact historical pre-submission FINSABER commit and both author-linked
  input files execute under the relevant versions from its requirements. Eight
  Table 1 strategies yield 128 eligible cells and reproduce **128/128** at paper
  display precision. The six deterministic strategies account for 96/96. A
  historical two-year training window exactly recovers the remaining 16/16
  ARIMA and 16/16 XGBoost cells. The paper omits this parameter, and FINSABER
  restored a three-year default before the paper's submission. The audited
  runner omits COIN; even the recovered two-year model window lacks enough prior
  COIN history.
- All 13 printed formula units execute on a declared synthetic fixture. This is
  formula-component evidence only. Figure 2 contains useful but truncated
  runtime-shaped examples for all five agents.

## Why native faithfulness remains zero

The paper publishes 140 displayed native TradingGroup table cells, of which 120
are unique after Table 3 duplicates. **0/120 unique native table cells** and
**0/15 native cumulative-return series** are regenerated. No attributable
TradingGroup implementation, Qwen3-Trader-8B-PEFT checkpoint, 1,080 training
trajectories, complete prompts/model calls, actions, orders, fills, NAVs, daily
returns, or raw figure/table arrays are public. FINSABER is the cited baseline
framework and data source; it is not the missing TradingGroup system.

## Important consistency and lineage findings

- The recovered data confirms the paper's detailed test-set claims exactly.
- All 128 eligible baseline cells regenerate exactly. The model cells require
  the source repository's historical two-year training window; its later
  three-year default produces 0/32 model-cell matches. Because the paper never
  states this parameter, result lineage is recovered but the method remains
  under-specified.
- The FINSABER repository's historical committed result CSVs match only 59/168
  comparable numeric paper cells and therefore are not the paper's result
  lineage.
- The advertised historical runner omits COIN because its three-year prior-data
  guard fails, while the paper prints COIN values for those baselines.
- Table 2 supports the claim that PEFT improves SPR and CR on all five tickers
  and improves both MDD and AV for MSFT.
- Only 58/60 Table 3 percentage annotations round from the displayed values.
  TSLA RM+PC SPR should round to -62%, not -61%; CR should round to -76%, not
  -77% as printed and repeated in prose.
- The paper's “globally optimal overall performance” language is not tied to a
  defined aggregate metric and is overbroad if read as dominance on every metric.

The bounded public search found no attributable implementation or checkpoint.
That is not proof that private, deleted, inaccessible, or unindexed artifacts
never existed. Run `scripts/audit_tradinggroup_paper.py` to regenerate the
ledgers. `--strict` intentionally exits nonzero while the native end-to-end
experiment remains unreproduced.
