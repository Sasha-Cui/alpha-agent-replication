# Bounded LLM discovery-process pilot

**The pilot ran to completion: 12 paid model calls, three paired search seeds, 48 emitted proposal slots per arm/seed, plus a stronger grammar-control sensitivity.** Total LLM cost was $0.036072. The LLM did not beat either grammar control on mean later-period predictive IC. Run-level outcomes were mixed, and the shared initial-bank factor had a higher assessment IC than every arm's mean. This is a small development benchmark, not a significance result or evidence that LLMs/papers contain no alpha.

## Predictive quality



| Seed | Original grammar IC | LLM IC | Stronger grammar IC | Initial-bank IC |
| --- | ---: | ---: | ---: | ---: |
| 101 | 0.0070 | **0.0074** | 0.0047 | 0.0071 |
| 102 | 0.0027 | -0.0032 | 0.0057 | **0.0071** |
| 103 | **0.0071** | 0.0026 | -0.0019 | **0.0071** |

Higher IC is better; bold marks the best within each seed row, including ties. The shared initial-bank baseline is 0.007065 IC. Seeds vary search generation on one shared market history; they are not independent market samples. [All paired results](visual_tables/paired_results.csv).

## Discovery yield and cost



| Arm | Assessment IC ↑ | Valid/distinct ↑ | Validation hits ↑ | Model dollars ↓ | Wall seconds ↓ |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original grammar | **0.0056** | 70 | 20 | **$0.000000** | 2.70 |
| LLM | 0.0023 | 110 | 19 | $0.036072 | 127.53 |
| Stronger grammar | 0.0028 | **130** | **54** | **$0.000000** | **1.79** |

Arrows specify better directions; bold marks column-best values, including ties. Novelty counts are unique within each arm/seed, not globally unique factors. Validation hits require validation meanIC>=0.01 and coverage>=95%; this is an operational threshold, not economic alpha. Model dollars exclude unpriced CPU/labor; wall times include generation, evaluation and API latency, with common data preparation excluded. Constructor effort differs and is preserved for the stronger grammar control. [Complete arm summary](visual_tables/arm_summary.csv), [all per-run results and selected expressions](visual_tables/all_arm_results.csv).

## What was actually tested

All arms used the same twelve close-price-derived terminals, restricted neg/rank/add/sub/mul syntax, maximum depth4/nodes15, training-sign orientation, five-session forward total-return labels, missingness/coverage rules, and evaluator. Forecast inputs are trailing only. Labels crossing split endpoints are purged. Search feedback uses 2019-2020 training scores only; 2021 validation chooses one factor; 2022-2024 assessment is scored after that choice. The initial factor bank is identical for every arm and seed. No new investment backtest, alpha regression or return claim was produced.

The model was openai/gpt-4.1 through the OpenAI provider with fallback disabled, temperature0.3, 2048maximum output tokens and distinct recorded request seeds. Actual response model IDs are ['openai/gpt-4.1']. The endpoint catalog and tariffs were captured before execution. This records the serving route, not immutable historical model weights or deterministic vendor behavior. Raw request/response envelopes and source-level data remain private.

## Control-quality sensitivity

The initial adaptive grammar controller wastes some slots on known equivalent standalone neg/rank expressions and initial-bank terminals. It remains fully reported. After inspecting first-seed proposal counts, but before the assistant inspected new assessment IC values, a separately recorded stronger-control protocol removed those constructor handicaps. It emits48proposals per seed with bounded syntax-only rejection before evaluation; all attempts and times are retained. It receives no extra scoring feedback and no paid calls. It is an exploratory post-launch sensitivity, not a retroactive preregistered primary or a control selected by favorable assessment returns. No other control was tried and discarded.

The stronger control's definition and all original records remain in the private `strengthened_control` directory. Because grammar has bounded constructor retries while LLM reasoning is internal, the fair statement is equal emitted proposal-slot/evaluation ceilings. This is not a claim of equal compute, equal dollars, or exhaustive optimization of either engine.

## Validation and claim limits

Seventeen preflight checks tested safe parsing, constant rejection, training orientation/duplicate equivalence, exact five-session labels, split purging, future-prefix invariance, and assessment-label isolation from feedback. They found and fixed a numerical constant-factor guard before any calls. A migration-related key-location binding was corrected to use only OPENROUTER_API_KEY from the original shared KnowledgeTemplate owner checkout; no secret was copied, printed or saved.

All nine selected-factor assessment ICs were independently recomputed with scipy.stats.spearmanr and direct five-day return products, agreeing within1e-12. Every emitted slot and selected factor was checked. All12request bodies match the canonical durable journal, have complete own-study accounting, and retain provider constraints. A full-state fingerprint excluding only this new study confirms every earlier ledger entry/import—including reservations—unchanged. No recovery-map change or old-request settlement occurred. [Numeric checks](visual_tables/independent_numeric_checks.csv).

All source history was already inspected in previous work. The US50 universe is a static legacy selection, and the current model may have historical knowledge. Assessment is a chronology-separated development score, not an untouched confirmation test. Positive results here would need a fresh validation design; these mixed/negative comparisons cannot establish absence of economic alpha. The primary research question explicitly changed with user approval from the prior2-pp economic-alpha test to useful predictive discovery per bounded search budget.

## Actual conclusion and next use

This pilot does not supply a reason to scale LLM search. A weak grammar comparator would have overstated the LLM's proposal-productivity advantage; the stronger comparator eliminates that advantage in this setup. More distinct expressions did not translate into better mean assessment quality, and validation-selected complexity often trailed the simple initial-bank baseline. Those are observed local process results, not a universal LLM verdict.

Preserve the complete pilot. Any follow-up should explain a specific mechanism or evaluator change before another model call and retain both adaptive controls and the simple initial-bank baseline. Do not scale merely to find a favorable seed or replace the failed economic-alpha question with an unstated success claim.

## Artifacts and lineage

- [protocol.json](protocol.json): original bounded pilot contract, fixed before any calls.
- [execution_completion.json](execution_completion.json): actual12-call completion and study cost.
- [arm_results.csv](arm_results.csv): original six per-arm/seed outputs, preserved.
- `visual_tables/`: combined results, pairings and independent readback metrics.
- `visual_figures/`: actual prediction and proposal dispositions.

Private evidence lives under `artifacts/llm_discovery_process_pilot_v1_20261102`: input hashes/copies, frozen helper/test hashes, saved once-only launch intents, raw receipts, original and strengthened controls, progress, account fingerprints and review records. No old source/replay/model/account/analysis/archive job was restarted. Project committed usage is now $371.10199757, including historical uncertainty, below the exclusive$1,000 authorization and unchanged450runtime ceiling. The new study stayed below its$5cap.

Provider metadata: [OpenRouter model page](https://openrouter.ai/openai/gpt-4.1), [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection). All scientific work was remote in the existing checkout. To inspect, use saved outputs/receipts. Do not rerun the live pilot or overwrite this completed version; its start/intent guards deliberately reject that action.
