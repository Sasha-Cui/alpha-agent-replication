# EFS v1 economic-fidelity source review

Status: human review pending. No strategy performance is included in this packet.

The implementation addresses the mismatches identified in PR #1 for EFS by
restoring a daily price-input strategy, actual LLM-generated Python factors,
rolling evolutionary feedback, and a sparse long-only portfolio. It targets
arXiv:2507.17211v1, not the substantially different v2. The original code, factor
pool, historical provider snapshot, and complete original run specifications
remain unavailable. This is a fresh paper-guided implementation, not a reproduced
published performance table.

| Dimension | Primary source | Implemented treatment | Review boundary |
|---|---|---|---|
| Price inputs | v1 experiments; appendix dataset definitions | 30 completed daily split-adjusted closes, internally derived returns, normalized price path | Alternative JKP/CRSP daily source and explicit adjustment convention |
| Universe | v1 appendix US50 constituent table | All 50 listed companies/security classes, including correct META and BRK-B identities | Fixed paper-selected universe, not a point-in-time census |
| Initial factors | v1 appendix factor library table | Twelve disclosed families; ten expanded over 3,7,14,21; RSI14 and one-day log return | Exact executable seed library is researcher supplied |
| Generation | v1 methodology and system/user prompts | Real current GPT-4.1 API calls, Python function mutation/crossover | Current endpoint and source-format prompt transcription, not original responses |
| Provider information | v1 anonymized prompt description | Code and aggregate past metrics only; no stock-level prices, tickers, or dates | Does not establish absence of pretraining information |
| Search cadence | v1 methodology, typically weekly | Every five trading sessions after 60-session warmup | Exact schedule/warmup were unspecified |
| Search feedback | v1 experiments ablation paragraph | m=25 non-sparse heuristic, performance plus RankIC and Recall@20 | 60-session feedback window and numeric admission thresholds are explicit assumptions |
| Version retention | v1 appendix filter_factor_versions | Keep latest and best version per base factor, then bounded pool | Pool cap 64 and ranking/tie rules are explicit assumptions |
| Aggregation | v1 methodology | Per-factor min-max normalization to [-1,1], arithmetic mean of five selected factors | Normalization implementation and five-factor choice not uniquely pinned by source |
| Traded portfolio | v1 main real-market table | Ten equally weighted stocks, selected daily | Main table m=10 chosen over contradictory m=5 setup prose |
| Execution | v1 next-day outcome description | Observe close t; execute close t+1; first earn t+1 to t+2 | One-session decision/execution delay is a causal feasibility adaptation |
| Accounting | v1 price-return/no-cost setup and cost sensitivity | Separate price-only and dividend-inclusive daily accounts at 0 and 10 bp one way | Self-financing fees and missing-return failure rule are researcher-defined |
| Failed LLM call | v1 algorithm logs failure and keeps pool | No automatic duplicate request after uncertain response; preserve all recorded failures/cost bounds | Retired setup lost one response at project inode quota; response is not fabricated |
| Trials | v1 three repeated/pooled searches | One complete chronological trajectory for this first pilot | No seed-robustness or original three-run claim |

Review each row as supported, acceptable declared adaptation, or needing repair.
Check the code against the source independently of whether the result is
profitable. In particular, inspect the m=25 search/m=10 trading distinction,
price adjustment, time cutoffs, normalization, and portfolio accounting.
Do not sign off an exact native-system or paper-number reproduction claim.

Source locations in the canonical Bouchet evidence:
- `audit.md` (merged PR #1).
- `paper_runs/paper_replication_audits/efs/paper_prompt_v1.tex.txt`.
- `paper_runs/paper_replication_audits/efs/method_specification_audit.csv`.
- Pinned v1 source: `efs_paper_audit/source_v1/sections/{methodology,experiments,appendix}.tex` in the existing scratch source archive.
- Primary paper: https://arxiv.org/abs/2507.17211v1

Additional review note: the source pseudocode collects recent performance
records over the last search interval. The pilot uses a 60-completed-outcome
summary with five-session updates. This is a declared interpretation requiring
review, not source-exact numerical equivalence.
