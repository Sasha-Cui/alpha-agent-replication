# TradingGroup paper-level replication audit

Overall verdict: **paper document, exact test data, formulas, and 156/156
source-adjacent baseline cells reproduced; native TradingGroup experiment
not reproduced**.

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
  input files execute under the relevant versions from its requirements. All
  **156 numeric Table 1 baseline cells execute and 156/156 match** at paper
  display precision. The six deterministic strategies reproduce **120/120**.
  Removing only their unused outer `prior_period` guard exposes all 24 COIN cells;
  every cell matches while all 96 original control cells remain unchanged.
- The paper's numeric model-result lineage is also recovered: a historical
  two-year window matches all 32 ARIMA/XGBoost cells on the four control tickers,
  and one year matches all four COIN XGBoost cells. This is not a complete method
  replication: the uniform two-year profile matches only 16/20 XGBoost cells and
  the uniform one-year profile only 4/20. The paper omits this ticker-dependent
  selection rule, and FINSABER restored a three-year default before submission.
  The executions preserve strategy formulas, test data, commissions, dates, and
  metric code. This is source-adjacent result credit, not native TradingGroup
  reproduction.
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
- **156/156 numeric baseline cells regenerate exactly.** All 120 deterministic
  cells match. The 36 model cells require a mixed hidden window: two years for
  all 32 ARIMA/XGBoost control cells and one year for the four COIN XGBoost
  cells. No tested uniform window regenerates all 20 XGBoost cells, and the later
  three-year default produces 0/32 matches on the original four tickers. Because
  the paper never states this selection rule, method-lineage remains under-specified.
- The FINSABER repository's historical committed result CSVs match only 59/168
  comparable numeric paper cells and therefore are not the paper's result
  lineage.
- The advertised runner's unused deterministic history guard hid 24 exact COIN
  cells. Its XGBoost history guard hid a runnable two-year COIN diagnostic whose
  four values conflict with the paper even when every available pre-test
  observation is used; a one-year COIN run matches all four.
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
