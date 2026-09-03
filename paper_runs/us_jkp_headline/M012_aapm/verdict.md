# M012: Empirical Asset Pricing with LLM Agents common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy from the released paper/source**.

AAPM’s headline strategy iteratively retrieves and refines stock and macro reports from WSJ news, embeds those reports, combines them with asset embeddings and manually constructed financial factors in a historically pretrained pricing network, predicts returns, and forms TP/EW/VW long-short portfolios.

The release contains genuine components: four source modules import, native Chroma memory and controlled model-forward fixtures run deterministically, all 65,733 metadata date/path rows were reconstructed, and a 1.34 GB paper-era-compatible BGE snapshot loads offline. But `analysis.py` immediately reaches an unavailable private `news_analysis` record whose `Tickers`, `Topics`, and `Content` fields are absent. There is no article corpus, return/factor input, report embedding, training entrypoint, pretraining path, trained checkpoint, prediction array, portfolio builder, or evaluation output.

The released model also omits the paper’s manual financial factors; the macro-note and SKIP paths are defective; evaluation mode and best-checkpoint handling are incorrect; and the code has no demonstrated lineage to v2’s GPT-4o/O1 results. Random fixture outputs, metadata paths, JKP factors alone, synthetic reports, or transcribed paper deciles would not preserve the hybrid strategy.

No monthly return is assigned. AAPM reports positive empirical performance, but 0 of 162 v2 result cells has been reproduced end to end. The claims remain unresolved—not shown false and not shown merely to underperform JKP.

M012 is closed without a return. M013, FinVision, is now active.
