# M032: Trading-R1 common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy because the learned policy is unreleased and materially underidentified**.

The original paper makes the central object unambiguous: Trading-R1 is a Qwen3-4B model trained on 100,000 daily multimodal Tauric-TR1-DB records through three interleaved SFT, reinforcement-fine-tuning, and self-distillation stages. It emits five recommendations, reportedly mapped to portfolio weights for roughly one-week holdings. Original-paper pages for the policy, daily backtest, Algorithm S1, and decision reward matrix were text-checked and visually inspected.

The official source does not implement that object. A live 2026-09-04 UTC check still finds the same single 49-byte `README.md`, one commit, no source code, tags, or releases, and zero TauricResearch models or datasets on Hugging Face. The paper and release omit the 100k-sample corpus, checkpoint, training code/config/seeds, reward parsers, action weights, portfolio rules, per-date decisions, split manifest, and equity paths. The prior census also found no Trading-R1 pipeline in any of 29 accessible public forks.

Algorithm S1 and the reward matrix receive specification credit only. S1 creates training labels—not policy predictions—and its printed formula uses trailing returns while the prose says forward returns; its full-sample quantiles are also future-dependent. The reward matrix assigns training rewards but produces no action. Neither can be relabeled as the headline strategy. The earlier JKP trend/quality/volatility score is likewise rejected as an unsupported researcher proxy.

No monthly return is assigned. This does **not** show that the paper's positive claims are false or that Trading-R1 merely loses against JKP; its 348 numeric display units remain unresolved because no disclosed policy can generate the trades. One paper inconsistency is material: NVDA Trading-R1 Sharpe is 2.72 in Table 3, 1.881 in Figure 5, and 1.88 in prose.
