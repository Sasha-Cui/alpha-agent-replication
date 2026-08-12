# MACI multi-version paper-level replication audit

Overall verdict: **not reproduced end to end**.

The same arXiv identifier contains two different experiments. Versions 1--2
describe a four-expert GPT-4o system over 2023--2024. Version 3 replaces it
with three architectures, four capability variants, three model families, and
calendar-2025 data. Evidence is therefore never transferred across lineages.

## Versions 1--2

An author-owned repository and a pre-submission commit are recovered. The
source is genuine and substantial, and all 16 compiled manuscript figure
assets have author-output correspondence: 12 are byte-identical, one is
pixel-identical, and the remaining result plots preserve their vector geometry
through label or horizontal-layout changes. The published quantitative figure
content is therefore strongly verified as author output. It is **not
regenerated**: raw/processed data, exact weekly universe, checkpoints, fine-
tuned model IDs, instantiated requests/responses, prediction records, and
portfolio arrays are absent. **Zero of 321** table units and **zero of 21**
plotted quantitative result units regenerate from released inputs.

The untouched source also fails closed. Its declared Python >=3.9.15 contract
cannot parse two `match` statements on 3.9. A compatible 3.11 environment
compiles, but the raw import stops on the gitignored `environ/constants.py`.
A clearly labelled reconstruction using the later author version of that one
file permits deterministic source-component checks only; it cannot execute the
paper runner because data, records, and checkpoints are missing.

## Version 3

The author repository contains no implementation of the v3 hierarchical,
collaborative, or debate systems and no memory/RAG/skill runtime. **Zero of
442** table units and **zero of 142** plotted bars/lines/points regenerate.
The table-implied risk-free rate is approximately zero rather than the cited
Fama--French T-bill series; 20/23 bear rows also cannot be computed from the
same regime-conditioned path under the printed cumulative-return/MDD
definitions. Provider release dates and cutoffs do not support the blanket
claim that every calendar-2025 observation is strictly outside every model's
training distribution.

Arithmetic checks, manuscript rebuilds, prompt inspection, source compilation,
component execution, and figure correspondence receive no end-to-end result
credit.

## Manuscript reconstruction

All three official PDFs and source archives are hash-pinned. Two independent
builds per version are byte-identical (14 pages for v1/v2 and 10 for v3), final
logs have no unresolved citations/references or TeX errors, and every official
and rebuilt page passed a full-document visual contact-sheet review. Normalized
official/rebuilt token-multiset overlap is above 99.7% for every version. These
checks establish faithful document reconstruction only; they do not recover
any missing experimental data, model records, or result lineage.
