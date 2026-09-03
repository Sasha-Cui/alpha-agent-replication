# M017: FinRL-DeepSeek common-task verdict

Status: **closed—not evaluable on the fixed monthly U.S./JKP task despite executable released checkpoints**.

The headline strategy is the 100-epoch CPPO-DeepSeek 10% variant: LLM sentiment/risk scores enter a daily Nasdaq-100 state, recommendation strength scales continuous actions, and a purported CVaR-sensitive actor-critic trades with 0.1% costs on each side. The release is unusually substantial—15 checkpoints, 12 frozen dataset files, and all eight paper-relevant checkpoints execute through the author environments.

Those checkpoints are fixed to an 84-stock daily survivor universe and 2019-2023 DeepSeek-derived columns. They cannot accept the 1999-2024 monthly top-1,000 JKP state. Resampling that short path would violate the common calendar and universe; direct inference is dimensionally and semantically invalid; retraining with generic characteristics would replace the LLM news mechanism and policy dynamics.

The native package also does not identify the exact headline training run. The 100-epoch 10% CPPO entrypoint is absent, only 5 of 8 relevant checkpoints have exact log-name lineage, evaluation samples Gaussian actions without a seed, and the implemented CPPO adjustment does not match the paper’s displayed CVaR objective or alpha=0.05 tail. Historical scores and stale notebook values are outputs rather than a transferable signal rule.

No common monthly return is assigned. Zero of 36 displayed table cells, 0 of 32 return series, and 0 of 4 figure IR labels is reproduced with paper lineage; 30/30 community-supplied cells also disagree. This raises substantive concern but remains an unresolved replication failure—not proof of falsehood and not a JKP-underperformance result.

M017 is closed without a common-task return. M018, HedgeAgents, is now active.
