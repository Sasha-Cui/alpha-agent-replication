# Profit Mirage / FactFin paper-level replication audit

Overall verdict: **not reproduced**. The paper document is strongly recoverable;
the claimed FactFin experiment and FinLake/FinLeak benchmark are not. This audit
pins the original arXiv v1 PDF/source, author-side public inventory, bounded hub
and archive searches, every displayed empirical result cell, every figure, and a
current Yahoo diagnostic. It gives zero result credit to typesetting, arithmetic,
raster values, current-provider substitutions, or printed example responses.

## What is genuinely recovered

- The official 12-page PDF is pinned at `1024f16ced8e9b12c6a4f0c7bf56551a92da0d621507da621ee82ae68355aba5`. Its complete
  14-file source bundle contains TeX, appendix, bibliography and
  typesetting files, and seven figures—**no FactFin or benchmark program/data**.
- Two independent three-pass builds converge to 12 pages with identical extracted
  layout text. After removing only arXiv's injected margin stamp and whitespace,
  the official PDF and both builds share content hash
  `29538331baccad835fa8b0b54007d184d5dc6252c4fbe9aec03a0c4fb9aa853e`. Their raw PDF hashes differ, so
  this audit does not call them byte-identical. All 24 official/rebuilt pages and
  all seven embedded figures passed visual inspection.
- The paper's six Yahoo ticker mappings are recoverable from labels and exact day
  counts. A pinned current response matches all six reported counts: 1380 each
  for AAPL/NVDA/TSLA, 1329 for 002594.SZ, 1350 for 0700.HK, and 2008 for BTC-USD
  through June 30, 2025. This validates a provider/schema fragment, not the
  original snapshot or experiment.
- All **525** displayed empirical or derived numeric table cells are transcribed:
  489 direct results and 36 derived improvement cells. **120** are direct FactFin
  full-system, ablation, or backbone outputs (108 unique measurements after the
  full AAPL/TSLA row duplicated across tables). **Zero of 525** are faithfully
  regenerated from the paper pipeline.
- Seven figures contain 82 exact numeric result labels and 112 plotted bars/series.
  Nine of ten Figure-1 decay labels round exactly from printed bars; the FinCON
  TR label differs by 0.02 percentage points and is compatible with hidden source
  precision. The exact dated arrays behind the curves are not released.

## Artifact search and claimed release

The abstract says the authors "release FinLake-Bench," while the body mostly calls
it FinLeak-Bench. Neither the arXiv record/source nor the pinned first-author
homepage links code or data. The author's stable GitHub account ID—renamed from
`OrangeCat0616` to `XiangyuLi616`—has one public repository, the homepage. Exact
title/arXiv/name searches on GitHub, Hugging Face dataset/model/space searches,
Software Heritage, and two guessed Wayback repository URLs recover no attributable
FactFin implementation or benchmark. A paper index's GitHub button resolves to
the unrelated 2023 `Bavest/fin-llama` baseline. These are bounded public searches,
**not proof** that private, deleted, or unindexed artifacts never existed.

The source contains an open-source promise only as a commented-out TeX bullet.
The only verbatim strategy prompt is explicitly "simplified"; its footnote says
changing templates are fully disclosed in the appendix, but the appendix contains
none. A second footnote promises baseline details in the appendix; those are also
absent.

## Result and arithmetic findings

- Twelve of 18 leakage-improvement cells round exactly from displayed cells; all
  18 are within 0.01 percentage points, so the other six are compatible with
  unreported source precision. The 31.91%/22.74%/9.23% mean performance
  improvements recompute. This verifies printed arithmetic only.
- Seventeen of 18 performance-improvement cells follow literal best-baseline
  ranking. The exception is decisive: FinAgent's TSLA MDD is printed as -9.36%,
  but FactFin 31.54% is marked best, InvestLM 36.88% second, and the 14.48%
  improvement is calculated from 36.88%. The prose separately changes FinRobot's
  TSLA MDD from +49.99% in the table to -49.99%.
- FactFin's mean Sharpe is only 1.2394x the mean per-asset best-baseline Sharpe;
  the paper's "1.4x higher" headline is unsupported by its table.
- Figure 3's +20.55%/+21.79% labels are percentage-point differences. Relative
  accuracy gains are 39.82% and 39.81%.
- A direct current-Yahoo endpoint calculation reproduces **0/6** Buy-and-Hold
  cells at two-decimal display precision under both close and adjusted close.
  Bitcoin is near, but still not exact. Provider revision is possible; more
  importantly, the paper omits the field, timestamp, adjustment, and execution
  rules needed to decide the target.

## Why the experiment remains unreproducible

FactFin lacks its executable code contract, RAG corpus/index/query, MCTS node and
reward definitions, counterfactual generators/weights/seeds, training split,
starting capital, quantities/weights, timing/fill price, numerical transaction
costs and slippage, risk-free rate/metric conventions, baseline forks/configs,
seeds/repetitions, and environment lock. The public record has no frozen Yahoo or
Alpaca rows, 2,000 benchmark questions, immutable model requests, generated
strategies, tree, actions, orders, fills, cash ledger, or dated NAV.

The benchmark scorer is internally unresolved: its equation requires exact answer
equality, while examples award interval, partial, magnitude, and qualitative
credit. Fine-tuning data cover Jan 2020-Dec 2022 while the stated test period lies
inside that range (Jan-Jun 2022), with no held-out-row definition. The two-period
agent decay test changes calendar regimes and treats similar aggregate market
returns as isolating memorization; that is a contamination warning, not a causal
identification strategy. PC/CI/IDS measure constructed sensitivity but are not,
without validation, unique measures of memorization, leakage, or causal learning.

Regenerate with `scripts/audit_factfin_paper.py`. `--strict` intentionally exits
nonzero while the end-to-end paper remains unreproduced.
