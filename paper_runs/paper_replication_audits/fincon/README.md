# FinCon paper-replication audit

This audit uses the 36-page NeurIPS 2024 proceedings paper as the result authority and pins all three arXiv revisions, the official paper source, and the complete official Git history. It is deliberately fail-closed: paper LaTeX compilation, raster plot availability, a README, or a related project cannot substitute for executing FinCon and matching its published results.

## Honest result

- **Full paper reproduced:** no.
- **Displayed numeric table cells reproduced:** 0 / 306.
- **Unique numeric measurements reproduced:** 0 / 288.
- **Raster result series reproduced from native numeric data:** 0 / 106.
- **Paper mechanisms verified in released implementation:** 0 / 33.
- **Official FinCon implementation/data/model artifacts released:** none. Every one of the repository's 11 commits contains only `README.md`.

The current README explicitly says commercial APIs prevent release of the full system and associated data and promises a future code release. InvestorBench and Agent Market Arena are separate systems and receive no FinCon credit.

## Result census and revision drift

The final paper displays 306 numeric cells. Nine FinCon metric triplets are repeated in the main table and both ablation tables, leaving 288 unique measurements. It also contains 106 result series across 18 raster assets; no underlying series or plot-generation code is released.

The v1 and v2 arXiv releases have the same 201 result cells. In v3/final, 105 cells were added and 64 of the 201 shared cells changed. The release provides no raw trajectories or derivation explaining those changes. `paper_version_numeric_drift.csv` records every changed shared cell.

## What did run

The released arXiv v3 LaTeX source compiles to a 30-page paper. That validates paper packaging only. There is no FinCon source entrypoint, import, environment, model, prompt set, dataset, or checkpoint to execute. Accordingly, the compilation earns zero system or result credit.

## Principal blockers

Exact replication requires the FinCon implementation; complete prompts and parsing; frozen multimodal commercial/public data; model/API snapshots; memory and CVRF parameters; action/execution semantics; trading frictions; all seeds and raw trajectories; baseline revisions/adaptations; statistical-test samples; and underlying plot data. See `paper_specification_gaps.csv` for the full fail-closed list.

## Important paper-internal findings

The final paper contains material inconsistencies: Table numbering does not match the narrative; a figure caption says six stocks while showing eight; several captions claiming FinCon leads *all* metrics are contradicted by their own MDD cells; data dates and vendors disagree between adjacent sections; Wilcoxon claims omit test outputs; and the appendix says the reported setting was chosen for the highest test cumulative return. These do not prove the results wrong, but they materially increase the evidence needed for a faithful replication.
