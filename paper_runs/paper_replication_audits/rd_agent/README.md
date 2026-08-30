# R&D-Agent paper-replication audit

This audit uses the final 33-page arXiv v2 report as the result authority and pins both paper revisions, the official repository at the last commit before each revision, its complete public branch/tag path history, and every accessible public-fork branch. It is fail-closed: source-code presence, paper compilation, isolated component execution, and unattributed developmental outputs do not substitute for the reported 75-competition, three-seed experiments.

## Honest result

- **Full paper reproduced:** no.
- **Displayed numeric table cells reproduced:** 0 / 534.
- **Unique numeric measurements reproduced:** 0 / 526.
- **Result-figure series/bars reproduced from native data:** 0 / 24.
- **Paper mechanisms with identifiable source implementations:** 21 / 21.
- **Paper mechanisms verified as used in a reported run:** 0 / 21.
- **Paper configurations verified for a reported run:** 0 / 30.

The repository contains meaningful paper-era MLE code, including the paper's interaction kernel, research DAG machinery, schedulers, coding/evaluation workflow, and selectors. That is implementation evidence, not result evidence: no frozen run configuration, prompts/responses, generated code, data snapshot, seeds, submissions, checkpoints, or traces link the released alternatives to the published tables.

## Scope correction

The cited primary record is the general **R&D-Agent** MLE-Bench report. It is not the separate R&D-Agent-Quant paper. The corpus system mapping describes a later quant application lineage, but quant code or the existing JKP factor proxy cannot validate this paper's MLE-Bench claims.

## Revision and release drift

The 7-page v1 paper reports 32 numeric cells from 24-hour runs using o1 and o3/GPT-4.1, with five or six seeds and standard deviations. The 33-page v2 is effectively a new experiment: 12-hour GPT-5/hybrid runs, three seeds, SEMs, ablations, raw runs, costs, and per-competition medal counts. Its 534 displayed numeric table cells represent 526 unique measurements. The current README still presents v1-era results and a hybrid value of 30.22±1.5, while v2 reports 29.7±0.4 and a new GPT-5 result of 35.1±0.4.

## Complete public-history boundary

The audit now walks 231 pinned remote refs, 3384 reachable commits, and 3188 unique historical paths. It inspects 329 paths whose names mention results, outputs, logs, traces, checkpoints, submissions, or scores and records fifteen bounded artifact candidates byte-for-byte.

That history corrects an earlier overstatement: developmental artifacts do exist. They include three pre-v1 competition CSVs, five between-version diagnostics with 39 competitions each, two debug-LLM pickles inventoried without deserialization, one example solution, pre-paper metadata, one post-v2 run command, and an unrelated post-v2 AutoRL result. None carries the paper's 75-competition manifest, three seeds, model/config lineage, or published table outputs. They receive zero paper-result credit, but their existence is now explicit rather than hidden behind a blanket “no outputs” claim.

## Complete public-fork boundary

GitHub reported 1862 forks on 2026-08-30. GraphQL exposed every branch for 1854 repositories and 33775 branch refs; the remaining 8 deleted, private, or otherwise unavailable repositories are not claimed as inspected. The accessible surface collapses to 1261 unique heads. Of those, 642 are already reachable from the pinned official history and 619 diverge, adding 4727 commits, 6383 paths, and 15752 changed blob versions.

The fork network materially expands attributable development history: 2896 extra commits use an exact name/e-mail identity already present in official history, and 2938 use an official-history e-mail. This is source-lineage evidence, not proof that any commit generated a paper result. A fail-closed content review inspects 65 high-relevance result/data blobs across 56 paths. It finds zero complete published result rows and no 75-competition, three-seed bundle.

One deleted `world_model` development head, preserved by 16 fork refs, carries descriptions for 74/75 paper competitions and 15 notebooks. Fourteen notebooks are unexecuted. The sole executed teacher-chain notebook uses a Qwen3 reward-model workflow, has 11 output objects, contains no medal or MLE-Bench result payload, and matches zero published rows. Its commit author name resembles paper coauthor Jingyuan Li, but the public profile/commit e-mail does not match the paper e-mail; identity is therefore left unresolved. These artifacts improve mechanism and task-universe provenance only and receive zero paper-result credit.

## What ran

The v2 LaTeX source compiled twice to a 33-page PDF. All 233 paper-era Python files across the data-science and Kaggle MLE paths compiled. A date-bounded Python 3.10 environment installs the exact paper-era R&D-Agent commit plus the Dockerfile's PyTorch 2.4.0 CPU-compatible build, passes `pip check`, and tracks a 243-line freeze. The authors' complete offline suite passes twice with real dependencies: 192/192 modules selected by their import test load, with no HTTP attempts after enabling LiteLLM's pinned local-cost-map switch. The native probabilistic scheduler's softmax helper and exact paper-era interaction-kernel methods also execute deterministically. These checks earn dependency/component execution credit only and zero published-result credit.

## Why the reported experiment did not run

An exact run is not presently specified or provisioned. The paper requires 75 Kaggle datasets, three 12-hour runs per main configuration plus ablations, Azure model deployments, a V100-class environment, and frozen MLE-Bench grading. The host environment above is compatible and source-pinned, not historically exact: requirements were unpinned. The separate MLE-Bench Dockerfile uses a PyTorch 2.4.0/CUDA 12.4 base but performs an unpinned live clone of MLE-Bench, so the paper container remains unreproduced. Paper-era defaults also disable the planner and LLM selector, set one trace, and default holdout selection to 80/20 rather than the paper's 90/10. Both advertised result-trace links now redirect to generic Bing pages. Running a guessed modern configuration would be expensive but would not be a faithful replication.

## Material internal inconsistencies

The main text says ML-Master/GPT-5 achieves 16.9±2.0, while Table 2 and Figure 1 say 16.9±1.2. Figure 1 disagrees with Table 2 for MLAB, OpenHands, and AIDE/GPT-4o. The backend appendix gives the hybrid system 29.3%, versus 29.7±0.4 in Table 2. Table 9's hybrid medal counts also total 29.3%, whereas Table 7's raw rows imply 29.8%, demonstrating that unidentified run sets were mixed. The Lite figure plots AIRA Greedy at 47.7 even though its caption says AIRA is shown as zero. Rounded hybrid raw runs imply a 0.5 Valid-Submission SEM while the summary prints 0.4. Hidden precision may explain the SEM alone, but no provenance artifact resolves the broader differences.
