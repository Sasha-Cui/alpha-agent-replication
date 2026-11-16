# Candidate experiment: incremental value of LLM factor proposals

Status: design draft; economic/search execution is gated by the separately frozen feasibility protocol. This document is not a new performance result or a full-paper replication. The historical broad replication effort is closed at its bounded scope; its gaps and zero whole-paper certification remain recorded.

The question is whether LLM proposals add value beyond a credible non-LLM proposal engine when data, representable factors, selection and portfolio evaluation are held fixed.

## Controlled comparison

- Primary contrast: an LLM proposal engine versus an adaptive grammar/evolution proposal engine. A uniform-random grammar arm is a secondary diagnostic, not the sole challenger. All arms begin from the same independently pinned initial factor bank and operator grammar.
- One parser, allowed data fields, expression limits, information cutoffs, candidate evaluator, training/validation split, acceptance rule and portfolio construction for all arms. Any LLM-only human edits, tool calls or recovery attempts must be charged and recorded.
- Candidate opportunity budget: proposed default 256 unique candidate evaluations, at most 512 proposal attempts per arm and seed. Invalid and duplicate proposals consume attempts; they do not earn free additional search. Ten paired research seeds are a development design choice, not ten independent market histories. These proposed budgets must be fixed with actual input/code/model identities in an execution supplement if all gates pass.
- Record every proposal, failure, accepted/rejected factor, candidate evaluation, selection and model request. Measure wall time, candidate evaluations, computation and provider dollars separately. Equal candidate opportunity is the primary budget comparison; equal dollars is a distinct comparison and cannot be claimed from it.
- LLM/provider/model revision selection must precede new outcomes. Choose by a documented capability/availability/budget rule, never the best return among tried routes. No model or request is selected or launched by this planning phase.

## Evaluation and interpretation

Freeze a point-in-time investable universe, original data/provider/revisions, timestamps, adjustment rules, execution price/lag, training-only fit and selection, identical portfolio rules, trade-level turnover/cost treatment and risk constraints. A common risk policy must be set before evaluation; never shrink only the active difference to make a null easy to accept. The 10-bp-per-side cost setting is the proposed primary; financing, market impact and other missing costs limit any net interpretation.

Primary economic endpoint: 12 times the mean paired monthly net-return difference at identical capital. It measures incremental performance. A separate, adequately identified low-dimensional risk model and its precision assessment are required for an alpha claim; an unrestricted 134-regressor model on 72 months is not allowed. Prediction IC or implementation productivity may be useful secondary endpoints but cannot replace failed primary economic precision.

Use a prespecified 99% confidence interval and +2-pp/year worthwhile-improvement boundary. Lower bound above +2 pp supports a worthwhile improvement in the named scope. Upper bound below +2 pp rules out that positive improvement; it does not prove zero alpha or equivalence. All other outcomes remain inconclusive. Assess the complete prespecified family if additional primary arms are introduced. Retain small-sample calibration failures.

## Development versus confirmation

The inspected 2019-2024 EFS/US50 history is development-only and a noisy variance proxy for this new design. Other inspected periods cannot be relabelled unused. A new confirmation plan needs an actually unused evaluation period and an explicit assessment of model pretraining knowledge, point-in-time universe selection and data leakage. A prospective period after the fully specified policy is sealed provides a stronger information boundary, but it does not by itself supply enough observations. Fresh random seeds do not erase shared market uncertainty. No model, factor-search, fit, backtest or economic evaluation is executed by this feasibility phase.

## Execution gates

1. Statistical precision: the frozen feasibility protocol's 80% target must pass for the +2-pp decision under the defined planning scenarios; model-based success alone is insufficient to establish validity.
2. Data and information: exact licensed data access, original fields/universe, unused confirmation period and model-knowledge assessment.
3. Mechanism isolation: identical evaluator/allocator and credible adaptive non-LLM control, with independent financial checks.
4. Selection and inference: candidate search stays within development data; uncertainty and multiplicity reflect both search and shared market history.
5. Budget and provenance: a separately versioned execution supplement with live scalar budget locks, exact model/provider prices, bounded new study cap and saved submission intent. Global historical/uncertain commitment stays strictly below $1,000, and existing runtime/per-study caps are not silently changed. Current planning execution cap is $0.

If precision fails, stop search execution. Improve the design through a documented mechanism that can reduce noise without trivially reducing economic exposure, or acquire genuinely new validation information and rerun a separately versioned feasibility assessment. Do not run repeated paid pilots until a favorable backtest appears, and do not silently switch the primary question.
