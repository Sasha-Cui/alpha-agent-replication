# QuantaAlpha paper-level conformance audit

Overall verdict: **one complete published baseline row independently regenerated; the
headline QuantaAlpha result does not reproduce**.

## Primary-source boundary

- All three arXiv revisions of [2602.07085](https://arxiv.org/abs/2602.07085) are pinned by PDF and source-archive SHA-256. The current audit targets v3, submitted 2026-05-18T16:57:08Z.
- The current official heads are pinned to `b7ceb27b1001261d7a95b209a963664ae1f8ab23`, but their **61-commit/259-path** surface is not the complete public history.
- Public PR/fork refs preserve an author-attributed **28-commit, 851-path** QuantaAlpha-specific lineage beginning `3c21b90abc88d5ece9359940b3993db25c71e2ad`. Its explicit release commit `04df1a96adfdb26c8bf3c3ec4bfb3aca6aa08ede` predates v1 by **209.90 hours**. Inherited RD-Agent ancestors are excluded from these counts.
- A dated GitHub census enumerated **267 accessible forks and 357 branch refs**, collapsing to **77 unique heads**. GitHub REST reported 279 forks; the 12 deleted/private/otherwise unavailable repositories are explicitly not claimed as inspected. All 64 divergent unique heads were reviewed.
- Nine author-attributed post-v1 fork heads add 28 unique commits and 259 changed paths, but **zero native result artifacts**. Eight of their nine image blobs were already in the official/prepublication line; the only new blob is the documentation image `docs/images/WeChat.jpg`. One unaffiliated post-v1 fork adds a derived five-strategy JSON summary with different factors/metrics and no raw lineage; it receives zero paper-result credit.
- The official public [Hugging Face dataset](https://huggingface.co/datasets/QuantaAlpha/qlib_csi300) is pinned to `d63bf5ba30d1d169023110377cbbe93a90a74e07`. It provides a Qlib package and daily HDF files, but no paper result arrays.
- The official pre-publication Git-LFS HDF object is pinned to `19ed8ee62db6a1fbd1e0f58e76b65dadd9991d666e3b0b8d3faab257fd81f53f`. A fork-preserved Qlib provider is separately pinned and receives no official-author credit; a 2,679x6 security slice is bit-identical between them.

## Result evidence

- The v3 paper contains **344 numeric table cells**. The README raster corroborates all 196 main-table cells as author output, but only the seven v3 Alpha158(20) cells are independently regenerated.
- The identical v1/v2 main tables contain 224 cells each. Native aggregate JSONs give rounded correspondence for **74/88 examined cells** across 11 rows. These are author-output lineage, not independent regeneration; filename/model conflicts are retained in the ledger.
- The native Alpha158(20) run reproduces all **8/8** v1/v2 metrics, including training, prediction, IC/RankIC evaluation, and the Top50/drop5 portfolio. Across version-specific tables this is **23/644** regenerated cells (8 in v1, 8 in v2, 7 in v3).
- The paper-configured QuantaAlpha/GPT diagnostic recomputes 148/150 public custom factors plus Alpha158(20), but does not reproduce the claim: IC **0.04170 vs 0.15008**, ARR **6.05% vs 27.75%**, IR **0.87738 vs 3.32512**, and MDD **11.93% vs 7.98%**.
- Numeric result figures add **40 visible labels**, **47 discrete unlabeled central markers**, and **10 raster return curves**. The README ships the 17-label case-study raster and byte-identical copies of the paper-source Figure 3--5 assets, corroborating **17 labels, 47 markers, and 10 curves**. Their underlying arrays are absent; **0/40**, **0/47**, and **0/10** are regenerated.

## What really works

- The release is not pseudocode: **135/135** current Python files and **135/135** initial-release Python files compile. The audit executes native expression parsing/complexity/subtree matching, trajectory JSON round-trip, lineage round-trip, and performance/diversity-aware crossover selection without calling an LLM or market API.
- Public prompt/config/source paths implement meaningful planning, full trajectory records, mutation/crossover generation, semantic consistency, AST complexity/redundancy checks, Qlib evaluation, and TopkDropout backtesting. **15/34** audited mechanism dimensions are implementation matches.
- The recovered `backtest_v2` profile matches the paper split, label, LightGBM seed, Top-50/drop-5 portfolio, open execution, and 0.05%/0.15% costs closely enough to reproduce Alpha158(20) exactly at displayed precision.
- Pre-publication pools preserve IDs, formulas, descriptions, implementation code, backtest feedback, and cache lineage for the LLM-generated factors.

## Why it is not faithful yet

- The actual checked-in `configs/experiment.yaml` is a demo profile: 2 rather than 10 directions, 3 rounds rather than the paper's five mutation/crossover cycles, 2 rather than the documented 10 crossover combinations, 1 rather than 3 factors per hypothesis, lower complexity limits, and the consistency gate disabled.
- Paper prose describes mutation as targeted failed-segment repair and crossover as reuse/splicing of validated trajectory segments. The source generates new hypotheses from truncated textual summaries; it does not localize, preserve, or splice structured trajectory segments.
- The current-source upstream test still fails because `template_debug.jinjia2` is missing. The released custom loader also refuses factors whose author cache paths are gone; two public expressions remain invalid under the released operator library.
- Exact LLM snapshots, prompts/responses, retry traces, parent selections, seeds, predictions, holdings, raw daily returns, and plot arrays are absent. Package versions beyond directly evidenced Python 3.12/Qlib 0.9.7 are time-bounded inference.
- v1/v2 reported IC 0.1501, ARR 27.75%, MDD 7.98%, and transfer returns 160%/137%; v3 reports 0.0472, 4.68%, 11.80%, and 40.28%/19.1%. No released result lineage explains the revision. In v3, Figure 1's visible endpoints do not agree with its prose, Figure 4 omits 2021 despite the text's 2021--2025 claim, and Appendix C labels the same offspring Round 10 and Round 8.

## Honest interpretation

The public record now supports a strong native baseline replication and much better source/data lineage than the current official heads reveal. It does **not** support the headline QuantaAlpha numbers end-to-end. The exact baseline success and the headline failure are both retained. `--strict` remains nonzero until the full reported study—not merely its framework, screenshots, or aggregate JSONs—is independently reproduced within declared tolerances.
