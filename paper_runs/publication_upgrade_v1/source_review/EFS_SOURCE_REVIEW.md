# EFS: outcome-free source-fidelity review packet

This packet contains no new strategy return, alpha, ranking, or significance result.

Paper: https://arxiv.org/abs/2507.17211v1
Source: Paper appendix prompts and numerical descriptions; author executable EFS source unavailable

Claimed scope: Paper-guided price-factor evolution at daily cadence, not recovered author code.

Preserved elements: US50 identities,12 seed families, weekly mutation/crossover requests, m25 search feedback, m10 sparse equal-weight trading.

Declared substitutions/repairs: JKP daily prices replace vendor snapshot; current GPT4.1; explicit60-session feedback and warmup, pool/pruning conventions and next-close execution; one LLM trajectory.

Reviewer focus: Assess the m10/m25 interpretation, source equations, signal formation versus executable return horizon, and whether the fixed grammar is a fair bounded control.

A reviewer should assess the conditional mechanism comparison represented here. Full original-paper reproduction, original-vintage inputs, and historical model equivalence are not claimed.

| Review dimension | Required judgment |
|---|---|
| Information | Is all supplied information available by the decision time under the disclosed data assumptions? |
| Mechanism | Does the claimed critical mechanism actually execute, including model calls where required? |
| Economics | Are action, position, cash, execution, turnover and fee definitions coherent? |
| Control | Is the primary comparison matched on the information/constraints it claims to match? |
| Claim boundary | Are the substitutions and missing source elements compatible with the stated conditional claim? |

## Files and hashes

| File | SHA-256 |
|---|---|
| `scripts/run_efs_economic_fidelity.py` | `9e5ee3d283633e7902343bb67da85a0393e990e648ed5f7642960afb55f7dc32` |
| `src/alpha_evolve/economic_fidelity.py` | `f7c82633f618dcf59da27ff24b54d8c17524efe6989d15e2f43e688c3020eb5b` |
| `scripts/run_efs_matched_search.py` | `d4b9b110f8570f0777a48c7a5a9bc3e491aa9917a4c88ddb0b0cc1a8ebda5d34` |
| `paper_runs/economic_fidelity/efs_v1/recipe.json` | `e1ed69a4c1fea2ae0647e225be77a991ae15c8d3a38c6433988f5d07e6853904` |
| `paper_runs/publication_upgrade_v1/efs_matched_recipe.json` | `b67c3cf4ccc7257e2d5aba29c6260923cc2f3f504afacfd8160f00543919bffa` |

## Human review record

Use the accompanying JSON template and record it with `scripts/record_publication_human_review.py`. Automated tests are separate evidence and do not fill any human review field. A review of a changed packet must be renewed.
