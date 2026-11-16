# TradingAgents: outcome-free source-fidelity review packet

This packet contains no new strategy return, alpha, ranking, or significance result.

Paper: https://arxiv.org/abs/2412.20138v7
Source: https://github.com/TauricResearch/TradingAgents/tree/cc97cb6d5deb10eac370db0c6678e2796a62eba8

Claimed scope: Released graph and roles with frozen historical tools and an explicit economic account.

Preserved elements: Four analyst factories, bull/bear discussion, research manager, trader, risk discussion/judge, categorical signal extraction and original graph routing.

Declared substitutions/repairs: Current GPT4o/.1 for both model roles; AAPL-only paper quarter; absent Reddit/insider data; SEC summaries replace SimFin; release has no executable portfolio sizing/fills; empty memories remain empty.

Reviewer focus: Assess dated tool clamps, information equality across controls, and source investment_plan wiring. It is the research-manager plan, despite the source judge calling it the trader plan.

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
| `scripts/run_tradingagents_economic_fidelity.py` | `f7c537c8ed67bf53efc9fff050d6196c09d259f0e3354252c3016028543c2d0d` |
| `scripts/prepare_publication_dated_inputs.py` | `630ea58e599e79898a57828f6ee15ff582f512d410ce578b4af1d5b0815408cd` |
| `paper_runs/publication_upgrade_v1/tradingagents_recipe.json` | `a2b96bf6b8f7bc214c78e4aab0f333261264ad676a22f7f8a48503420114263b` |

## Human review record

Use the accompanying JSON template and record it with `scripts/record_publication_human_review.py`. Automated tests are separate evidence and do not fill any human review field. A review of a changed packet must be renewed.
