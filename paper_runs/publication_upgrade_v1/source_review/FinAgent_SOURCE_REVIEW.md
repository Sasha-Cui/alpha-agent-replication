# FinAgent: outcome-free source-fidelity review packet

This packet contains no new strategy return, alpha, ranking, or significance result.

Paper: https://arxiv.org/abs/2402.18485
Source: https://github.com/DVampire/FinAgent

Claimed scope: Released five-stage actor and complete prompt variant, with causal validation/account repairs.

Preserved elements: Actual vision calls; source train/valid full-tool templates; source diverse queries and FAISS memory; source text-embedding-3-large3072-dimensional provider; original whole-share buy/sell rules.

Declared substitutions/repairs: Current GPT4o and study temperature0.1 replace unavailable historical model IDs and the release provider temperature default1.0; alternative data; Matplotlib charts; missing guidance/economics; current-close accounting repair.

Reviewer focus: Verify full-tool template selection, source embedding model/dimensions/token-ID path, training price cutoff, no future validation chart, fills before current-account observation, and retrieval ablation scope.

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
| `scripts/run_finagent_economic_fidelity.py` | `65102c4998fe4cacf746ed0843babae64bc1b92142682a5cb1c2e2bb7ee45a2c` |
| `scripts/resume_finagent_after_transport_failure.py` | `d52f075ca824d854573b3a8cd01aa48ccb0d5c52c8a6510de33960e7cda00d0e` |
| `scripts/run_finmem_fidelity_python.sh` | `279571fcd57f9095a59222db87ad78d91112b97de5d3ae1c41aa2549afb9add2` |
| `environment_specs/tokenizer_cache.json` | `ae58862ab2efc9e90a5f28e96d7ef1ab1d2ea73307e76e01a485fa2c80034136` |
| `src/alpha_evolve/publication_embeddings.py` | `a97e364a3f024d747aeefd5e35a9db50e4e4c0ad9cfbea0db44b0bcf8553f140` |
| `scripts/prepare_publication_dated_inputs.py` | `630ea58e599e79898a57828f6ee15ff582f512d410ce578b4af1d5b0815408cd` |
| `paper_runs/publication_upgrade_v1/finagent_recipe.json` | `3d737fab67164449b6621c6f6cec91c40c7be1646eb9c6e3c265d30ca9d26f60` |

## Human review record

Use the accompanying JSON template and record it with `scripts/record_publication_human_review.py`. Automated tests are separate evidence and do not fill any human review field. A review of a changed packet must be renewed.
