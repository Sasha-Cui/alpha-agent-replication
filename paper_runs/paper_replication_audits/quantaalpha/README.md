# QuantaAlpha paper-level conformance audit

Overall verdict: **substantial native implementation; zero published paper results reproduced**.

## Primary-source boundary

- All three arXiv revisions of [2602.07085](https://arxiv.org/abs/2602.07085) are pinned by PDF and source-archive SHA-256. The current audit targets v3, submitted 2026-05-18T16:57:08Z.
- The official source is pinned to `b7ceb27b1001261d7a95b209a963664ae1f8ab23` (2026-06-29T12:55:11-04:00). Its initial substantial revision was committed 56.91 hours after v1 submission, so the source is useful but not a pre-submission snapshot.
- The official public [Hugging Face dataset](https://huggingface.co/datasets/QuantaAlpha/qlib_csi300) is pinned to `d63bf5ba30d1d169023110377cbbe93a90a74e07`. It provides a Qlib package and daily HDF files, but no paper result arrays.

## Complete numeric-result boundary

- The v3 paper contains **344 numeric result table cells**: 196 main-table cells, 28 evolution-ablation values/deltas, 56 seed/daily-statistic cells, and 64 case-study/factor-analysis cells. **0/344** has a released native derivation.
- Numeric result figures add **40 visible labels**, **47 discrete unlabeled central markers**, and **10 raster return curves**. Their underlying arrays are absent; **0/40**, **0/47**, and **0/10** are reproduced.
- The paper says approximately 150 validated factors feed a common LightGBM model. No such factor pool, run trajectory, prediction, portfolio, return, or metric artifact is shipped.

## What really works

- The release is not pseudocode: **135/135** current Python files and **135/135** initial-release Python files compile. The audit executes native expression parsing/complexity/subtree matching, trajectory JSON round-trip, lineage round-trip, and performance/diversity-aware crossover selection without calling an LLM or market API.
- Public prompt/config/source paths implement meaningful planning, full trajectory records, mutation/crossover generation, semantic consistency, AST complexity/redundancy checks, Qlib evaluation, and TopkDropout backtesting. **15/34** audited mechanism dimensions are implementation matches.
- `configs/backtest.yaml` substantially matches the paper's date split, target, preprocessing, Top-50/drop-5 portfolio, open execution, limit, and 0.05%/0.15% costs.

## Why it is not faithful yet

- The actual checked-in `configs/experiment.yaml` is a demo profile: 2 rather than 10 directions, 3 rounds rather than the paper's five mutation/crossover cycles, 2 rather than the documented 10 crossover combinations, 1 rather than 3 factors per hypothesis, lower complexity limits, and the consistency gate disabled.
- The mining runner selects `quantaalpha/factors/factor_template/conf_baseline.yaml`, whose train/validation/test split is 2016--2019/2020/2021 and whose backtest ends in 2021. The paper reports 2016--2020/2021/2022--2025. The matching standalone backtest config does not repair the mining-loop mismatch.
- Paper prose describes mutation as targeted failed-segment repair and crossover as reuse/splicing of validated trajectory segments. The source generates new hypotheses from truncated textual summaries; it does not localize, preserve, or splice structured trajectory segments.
- The only tracked upstream test fails because `template_debug.jinjia2` is missing. The full dependency/runtime stack is not reproduced here.
- v1/v2 reported IC 0.1501, ARR 27.75%, MDD 7.98%, and transfer returns 160%/137%; v3 reports 0.0472, 4.68%, 11.80%, and 40.28%/19.1%. No released result lineage explains the revision. In v3, Figure 1's visible endpoints do not agree with its prose, Figure 4 omits 2021 despite the text's 2021--2025 claim, and Appendix C labels the same offspring Round 10 and Round 8.

## Honest interpretation

This repository is close to a credible clean-room *implementation framework*, but far from a verifiable replication of the reported study. Running it with newly chosen APIs/data would produce a new experiment, not establish any published value. Public data and runnable components improve tractability; they do not justify paper-result credit. `--strict` intentionally remains nonzero until an end-to-end pinned paper profile reproduces every claimed artifact and result within declared tolerances.
