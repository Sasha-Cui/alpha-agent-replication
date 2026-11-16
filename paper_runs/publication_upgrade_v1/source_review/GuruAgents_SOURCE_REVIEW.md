# GuruAgents: outcome-free source-fidelity review packet

This packet contains no new strategy return, alpha, ranking, or significance result.

Paper: https://arxiv.org/abs/2510.01664
Source: https://github.com/yejining99/GuruAgents/tree/74ad2e6ce2e604c73a6fc2829d48ab58fe6be050

Claimed scope: Actual source-prompt/tool replays with corrected quarterly execution accounts.

Preserved elements: Five investor roles, original prompts and archived financial tool observations, GPT4o/temperature0, source normalization of percentage weights.

Declared substitutions/repairs: Archived inputs lack full publication-vintage evidence; source ticker repairs retained; first post-quarter close and90-day lag stress; researcher equal-weight role ensemble is not a paper headline portfolio.

Reviewer focus: Check relative-weight normalization in the original notebook, formation/filing availability, drift between quarters, same-information one-call control, and price/fee conventions.

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
| `scripts/run_guruagents_openrouter_replay.py` | `714c77f360d6013f7c7a2047dd869d9331db66a869168e7e56df19bcc1afd112` |
| `scripts/build_publication_control_accounts.py` | `e65b895df69e95c7b0370738d3ef14a6e42fa6678dd4b7b12adab67d0e6e7b15` |
| `scripts/evaluate_guruagents_prompt_replay_performance.py` | `b02057a7782f98e494f7a2839f5f3f4e62ddb1194b588a99dee3185c4c0c560e` |
| `paper_runs/publication_upgrade_v1/guruagents_recipe.json` | `965c4612d05fad4f7ca3c8b1a82682df6a04d02b08a0ce51273d33e1375a0f37` |

## Human review record

Use the accompanying JSON template and record it with `scripts/record_publication_human_review.py`. Automated tests are separate evidence and do not fill any human review field. A review of a changed packet must be renewed.
