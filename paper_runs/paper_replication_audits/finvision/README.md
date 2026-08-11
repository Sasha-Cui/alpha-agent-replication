# FinVision paper-level replication audit

Overall verdict: **not reproduced**. This package pins the original paper, its
complete arXiv manuscript source, the author's thesis, public artifact searches,
official model documentation, and current Yahoo price responses. It faithfully
reconstructs the paper as a document and recovers all five printed prompt templates,
but it does not recover or execute the FinVision system.

## What is recovered

- The official 9-page paper is pinned at SHA-256 `8483714696f009ffecd5e818ce2b8937e88be03343476bb23344b4f38b080921`.
- The 22-file arXiv v1 bundle is byte-checked against its exact
  extraction. Two clean, three-pass LaTeX builds produce the same rendered content
  and identical extracted text. Their raw PDFs differ only in the generated trailer
  ID, so this audit explicitly does **not** call them byte-identical. All original
  and rebuilt pages passed visual inspection.
- The author's 133-page thesis is pinned at SHA-256 `868da394c7fcf3a84de5351aef3b9a8b781c132db0803335bef2103d3b79ab8a`.
  Its FinVision chapter repeats all 72 displayed result cells and the same method
  and prompts. This is author-side corroboration, not an independent replication.
- All five Appendix prompt templates are recovered. Their runtime values, actual
  API requests/responses, model request IDs, and generated daily traces are absent.
- The nine displayed FinAgent cells trace to FinAgent Appendix Table 7. Eight are
  conventional two-decimal roundings; AAPL ARR is printed as 31.89 from 31.8972,
  a truncation/nonstandard transcription. This lineage does not reproduce FinVision.

## Why zero of 72 result cells receive reproduction credit

- The arXiv bundle contains manuscript/typesetting files and figures only—no
  LangGraph implementation, dependency lock, runnable configuration, or data code.
- No original news rows, price snapshot, chart inputs, LLM requests/responses,
  BUY/SELL/HOLD actions, position sizes, fills, rewards, cash ledger, or equity
  trajectory are released. The commented `result.png` is a picture, not an exact
  action/portfolio record from which the metrics can be regenerated.
- Core execution choices are unspecified: initial capital; price field and
  adjustment; fill timing; share rounding; long/short constraints; costs and
  slippage; reward and cash equations; seeds; dependency versions; and baseline
  hyperparameters. ARR omits numeric C, while Sharpe omits risk-free rate,
  frequency, annualization, and variance convention.
- The paper names mutable model aliases (`gpt-4o-mini`, `o1-mini`) rather than
  immutable snapshots. Official documentation now marks o1-mini deprecated.
  The paper's historical run therefore cannot be identified from the alias alone.

## Dataset and current-price diagnostic

The stated seven months is the **testing** window inside a nine-month overall
window; those statements are consistent. The unresolved count issue is different:
the paper reports 42 warm-up and 145 test trading days for every ticker, while the
pinned Yahoo responses contain 41 and 147 literal exchange sessions over the
printed inclusive dates. The paper does not state a transformation or endpoint
convention that resolves those counts.

A deliberately separate diagnostic applies one plausible metric convention to
current, hash-pinned Yahoo adjusted closes. 3/9 Market cells match
at the paper's displayed precision. This receives **zero faithful-replication
credit** because the original price snapshot/field and metric conventions are not
specified; matches against a later historical feed cannot stand in for the missing
original input and portfolio path.

## Public-artifact search boundary

Current author GitHub and Hugging Face inventories, exact-title/arXiv searches,
Software Heritage, Wayback, and value/model code searches did not recover an
attributable implementation or dataset. The paper itself prints no code URL and
makes no release promise. This is evidence that no public artifact was recovered,
not proof that private or deleted artifacts never existed.

Regenerate with `scripts/audit_finvision_paper.py`. `--strict` intentionally exits
nonzero while the paper remains unreproduced.
