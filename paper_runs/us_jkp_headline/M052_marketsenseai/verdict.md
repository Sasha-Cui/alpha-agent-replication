# M052: MarketSenseAI multi-agent stock recommendations

Status: **closed not evaluable on monthly U.S./JKP data**.

The paper's central trading strategy is clear: on each monthly first Friday, equal-weight the stocks assigned the system's strongest-buy class for the following month. What is missing is the signal itself. The paper reports aggregate class counts, average selection sizes, returns, and Monte Carlo summaries, but releases none of the 12,163 stock-date recommendations, specialist/synthesis texts, embeddings, cohort tickers, or price/return rows.

Aggregate counts cannot reconstruct holdings: many incompatible portfolios can contain 35.1 or 9.9 names per month and match the same class distribution. NNLS is an attribution of already-generated thesis embeddings, not a recommendation generator. JKP supplies monthly security data but no deployed MarketSenseAI multimodal inputs or outputs; applying the reported 7.5% strong-buy rate to arbitrary stocks would fabricate decisions.

A fresh exact search found no author implementation. A same-day `HCH725/alpha-strategy-research` record adds a careful paper summary but explicitly marks itself research-only and not implemented; it contains no signal or portfolio artifacts.

No return path is fabricated. This closure does not prove the paper's reported strong-buy excess return false; it records that the identities required to reproduce or transfer that portfolio are absent. Reopen for the dated recommendation panel or an attributable operational release.
