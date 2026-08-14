# FinRL-DeepSeek paper-level replication audit

## Verdict

The release is a substantial and unusually useful component package: the paper-era Hugging Face release contains 15 checkpoints, the dataset release contains frozen train/trade CSVs, the Git repository contains paper-era environments/training logs, and all eight checkpoints relevant to Tables 1--3 load and execute through the authors' environment code. The complete official graph has also been audited behind an explicit provenance boundary: 36 commits, 48 historical paths, 145 reachable objects, no tags or releases, and no unreachable objects. Fork refs cannot widen those author-source claims. That materially improves reproducibility, but it does not reproduce the paper.

The paper contains **36 displayed table cells representing 24 unique measurements**, **32 raster-only return series**, and **4 numeric IR labels in Figure 1**. The released notebook has stored values for 27/36 table cells, but **0 match the paper**; 9 cells have no stored output. Worse, its two stored evaluations of the same PPO and PPO-DeepSeek 10% series disagree on all six corresponding metrics. Every one of the nine historical notebook blobs—including two malformed revisions—contains the same 24 stored metric entries and none contains a paper table value. Three native protocols (stochastic seeds 0 and 42, plus policy means) executed all eight released checkpoints on hash-pinned released CSVs, but no table value earns paper-result credit. Information Ratio remains uncheckable from frozen inputs because the notebook downloads the benchmark live.

The public-fork census exhausted all **80 accessible repositories, 82 refs, 10 unique heads, 69 divergent commits, 84 changed paths, and 159 genuinely new blobs** returned by the pinned listing snapshot; one stale listing was inaccessible. One post-paper community notebook downloads the authors' `benstaf/Trading_agents` checkpoint snapshot, repairs paths/device placement and return alignment, and stores 33 metric entries. It supplies correspondence for 30/36 paper table cells, but **all 30 supplied cells disagree at displayed precision** and 6 remain absent. This is adverse community evidence against the released-checkpoint backtest correspondence, not an author result, a retraining replication, or proof that the paper is false.

A later divergent adaptation contributes 82 syntax-valid Python files, including a bundled Spinning Up tree, Differential-Sharpe reward paths, Ray Tune/Optuna optimization, MLflow, Redis/ParamStore, and ClickHouse integration. It commits no new checkpoint, dataset, training log, or metric output; it also depends on `pkg` and `utils.env_manager` code absent from the fork. Because it changes the objective and evaluation protocol and requires uncommitted runtime state, it cannot receive native-paper credit.

## Decisive fidelity gaps

- The paper does not fix evaluation seeds, while the notebook samples Gaussian actions.
- Figures 2--6 visibly start in 2020 despite the stated 2019--2023 trading interval.
- The exact 100-epoch DeepSeek 10% CPPO training lineage is absent. The only committed 0.9--1.1 risk script is an older 25-epoch local-Qwen path; the 100-epoch DeepSeek scripts use smaller weights and unmatched output names.
- Fifteen historical training logs establish partial checkpoint provenance, but they contain no paper evaluation metrics. Ten logs name a released checkpoint exactly; only 5/8 paper-relevant checkpoint names have exact log lineage.
- The source's CPPO update is not the displayed CVaR-PPO Lagrangian: it applies a clipped per-step value adjustment to GAE, uses alpha=0.85, and repeatedly subtracts its full update buffer during trajectory finalization.
- The one-article-per-stock/day sample, selection seed/IDs, raw selected inputs, LLM responses, frozen Yahoo benchmark, and table-generating result paths are absent.
- The installation script invokes a nonexistent training file; the post-paper risk API script does not parse.

## Honest proximity

This is close to a runnable **artifact-level reconstruction** of the authors' code path and far better than a paper-only release. It is not a faithful result replication: 0/36 displayed table cells, 0/32 figure series, and 0/4 raster metric labels are reproduced with defensible paper lineage. The community mismatch raises concern but does not convert an unidentifiable native training/evaluation protocol into a falsified claim. `--strict` remains nonzero until the pinned original protocol reproduces every claimed result within declared tolerances.
