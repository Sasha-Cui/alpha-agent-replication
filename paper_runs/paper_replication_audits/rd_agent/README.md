# R&D-Agent paper-replication audit

This audit uses the final 33-page arXiv v2 report as the result authority and pins both paper revisions, the official repository at the last commit before each revision, and its complete public branch/tag path history. It is fail-closed: source-code presence, paper compilation, isolated component execution, and unattributed developmental outputs do not substitute for the reported 75-competition, three-seed experiments.

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

## What ran

The v2 LaTeX source compiled twice to a 33-page PDF. All 233 paper-era Python files across the data-science and Kaggle MLE paths compiled, the native probabilistic scheduler's softmax helper executed, and the exact paper-era interaction-kernel methods executed with deterministic synthetic embeddings. These checks earn component-packaging credit only and zero published-result credit.

## Why the reported experiment did not run

An exact run is not presently specified or provisioned. The paper requires 75 Kaggle datasets, three 12-hour runs per main configuration plus ablations, Azure model deployments, a V100-class environment, and frozen MLE-Bench grading. The release's MLE-Bench Dockerfile performs an unpinned live clone; paper-era defaults also disable the planner and LLM selector, set one trace, and default holdout selection to 80/20 rather than the paper's 90/10. Both advertised result-trace links now redirect to generic Bing pages. Running a guessed modern configuration would be expensive but would not be a faithful replication.

## Material internal inconsistencies

The main text says ML-Master/GPT-5 achieves 16.9±2.0, while Table 2 and Figure 1 say 16.9±1.2. Figure 1 disagrees with Table 2 for MLAB, OpenHands, and AIDE/GPT-4o. The backend appendix gives the hybrid system 29.3%, versus 29.7±0.4 in Table 2. Table 9's hybrid medal counts also total 29.3%, whereas Table 7's raw rows imply 29.8%, demonstrating that unidentified run sets were mixed. The Lite figure plots AIRA Greedy at 47.7 even though its caption says AIRA is shown as zero. Rounded hybrid raw runs imply a 0.5 Valid-Submission SEM while the summary prints 0.4. Hidden precision may explain the SEM alone, but no provenance artifact resolves the broader differences.
