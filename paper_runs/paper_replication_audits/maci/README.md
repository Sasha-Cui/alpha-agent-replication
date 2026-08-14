# MACI multi-version paper-level replication audit

Overall verdict: **not reproduced end to end**.

The same arXiv identifier contains two materially different experiments.
Versions 1--2 describe a four-expert, fine-tuned GPT-4o system over 2023--2024.
Version 3 replaces it with three multi-agent architectures, four capability
variants, three model families, and calendar-2025 data. Evidence is kept
strictly within its own lineage.

## Versions 1--2

The complete 164-commit, 7,997-object history of the first-author repository
is audited. The pre-submission source is genuine and substantial, and all 16
compiled manuscript figures have author-output correspondence, covering 21
plotted quantitative units. Complete history also recovers three deleted
fine-tuning-format JSONL files containing 962 system/user/assistant message
records, including 930 unique image URLs spanning weeks 2023-W22--W52. This is
materially better training-input provenance than the current tree exposes.

It is still not a paper-result reproduction. The exact fine-tuning upload,
job, selected checkpoint, test predictions, raw/processed inputs, weekly
universe, inference request/response logs, and portfolio arrays are absent.
**Zero of 321** table units and **zero of 21** plotted result units regenerate
from released inputs. The raw pre-submission source also fails its declared
Python 3.9 contract; a labelled later-constant overlay reaches deterministic
component checks but stops at missing blockchain data.

## Version 3

The paper's anonymous artifact was not absent: its public README API is
hash-pinned and byte-identical to the README in the first author's public
`cryptoMAS` repository. The complete 20-commit, 209-object history recovers 42
tracked files, including 24 Python files, all three claimed architectures,
rolling memory, skill indicators, portfolio execution, baselines, evaluation,
tables, and figures.

Author-output correspondence is strong but not regeneration. **394 of 442**
printed table units match the pinned repository tables: all 28 ablation units
and 366 of 414 performance units. The 48 differences are confined to LSTM,
Informer, and Autoformer. **136 of 142** plotted bars/paths/points have author
output correspondence: both 48-bar model-comparison PDFs are byte-identical,
and 20 of 23 portfolio paths plus 20 of 23 risk/return points match. **Zero of
442** table units and **zero of 142** plotted units regenerate from released
inputs.

The strict boundary is source incompleteness. `environ.data.coingecko`,
`environ.data.cointelegraph`, and `environ.data.rag_store` are absent from every
commit, so the raw runner fails before even displaying `--help`, RAG cannot
construct, and no frozen input or processed result record exists. The README
names a nonexistent fetch script, and `anthropic` is imported but undeclared.
The single-agent wrapper maps both RAG and Skill to zero-shot despite distinct
paper results, and source has no compulsory ReAct observation/action loop.

All nine non-RAG architecture/capability orchestration paths execute with
deterministic fixture agent outputs and no API calls. A labelled in-memory data
overlay also runs one dry-run week, and synthetic evaluation metrics execute.
These checks establish component behavior only and receive no paper-result
credit. The table-implied risk-free rate remains approximately zero rather than
the cited Fama--French series, and 20/23 bear rows remain inconsistent with the
printed cumulative-return/MDD definitions.

## Manuscript reconstruction

All three official PDFs and source archives are hash-pinned. Two independent
builds per version are byte-identical (14 pages for v1/v2 and 10 for v3), final
logs have no unresolved citations/references or TeX errors, and every official
and rebuilt page passed full-document visual review. These checks establish
faithful document reconstruction only; they do not fill any missing
experimental data, model records, or native result lineage.
