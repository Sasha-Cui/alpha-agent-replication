# FinMem: outcome-free source-fidelity review packet

This packet contains no new strategy return, alpha, ranking, or significance result.

Paper: https://arxiv.org/abs/2311.13743
Source: https://github.com/pipiku915/finmem-llm-stocktrading/tree/be814aa47970de9bf2fdd6a1d5a60ae5cf361b46

Claimed scope: Released actor, layered memory, portfolio feedback and embedding wrapper, with alternative dated inputs.

Preserved elements: Four memory stores, native ranking/decay/promotions/access feedback, paper topK5 and temperature0.7, GPT4Turbo route, source Ada002 embedding path.

Declared substitutions/repairs: TSLA-only/one seed; missing replacement news beforeMay2022; source profile and alternative filings/news; paper score is not NAV; a separate cash/stock economic adapter is explicit.

Reviewer focus: Check terminal-date handling, no test future label, source score versus cumulative one-share feedback versus investable portfolio, and cardinality-matched semantic retrieval.

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
| `scripts/run_finmem_economic_fidelity.py` | `e335a5a439dc50c6ebc023b22bde1b003822806b5cc43a62d02f65eb885515e7` |
| `scripts/prepare_finmem_fidelity_inputs.py` | `28fb428653e858b359ac3d9238911441de1787df9dd56518e81c9fd26a67e125` |
| `scripts/run_finmem_fidelity_python.sh` | `279571fcd57f9095a59222db87ad78d91112b97de5d3ae1c41aa2549afb9add2` |
| `environment_specs/tokenizer_cache.json` | `ae58862ab2efc9e90a5f28e96d7ef1ab1d2ea73307e76e01a485fa2c80034136` |
| `paper_runs/publication_upgrade_v1/finmem_recipe.json` | `8d88cb0a89e0996f90dc75332215351d5d0fd024e2b5f3dbc92bc2de448df0bd` |

## Human review record

Use the accompanying JSON template and record it with `scripts/record_publication_human_review.py`. Automated tests are separate evidence and do not fill any human review field. A review of a changed packet must be renewed.
