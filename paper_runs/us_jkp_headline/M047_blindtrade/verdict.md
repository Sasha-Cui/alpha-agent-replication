# M047: BlindTrade anonymization-first portfolio policy

Status: **closed not evaluable on monthly U.S./JKP data**.

BlindTrade's central strategy is the whole learned stack: anonymized point-in-time S&P 500 news and numeric inputs, four Gemini 2.5 Flash agents, reasoning embeddings, a dynamic semantic/sector GATv2, and a PPO-DSR Dirichlet Top-20 allocation policy with intent and execution inertia. It is not the paper's Momentum or RAW Top-20 benchmark.

The paper is unusually detailed about roles, headline windows, selected output fields, embedding model, graph thresholds, PPO settings, costs, and headline hyperparameters. That still does not determine a runnable policy. No attributable code, historical input/output feature data, Gemini responses, graph edges, GNN/RL weights, predictions, holdings, or seed paths are public. The paper says the feature datasets are planned for release upon publication. A fresh exact GitHub search found only paper indexes/digests and no native release.

JKP has monthly security characteristics and returns but none of the defining point-in-time news, anonymized reasoning, graph, or learned policy state. Rebuilding the method would require a new historical-news acquisition/anonymization project, about 1.22 million agent-stock evaluations for the common panel, and newly designed/trained GNN and PPO implementations. Substituting the disclosed RAW Top-20 benchmark would discard the central mechanism.

No fabricated return path is recorded. This closure does not prove the reported Sharpe is false; it means the public artifacts cannot generate the causal monthly U.S. decisions required to test or transfer the claim. Reopen if the promised feature data and trained policy become available.
