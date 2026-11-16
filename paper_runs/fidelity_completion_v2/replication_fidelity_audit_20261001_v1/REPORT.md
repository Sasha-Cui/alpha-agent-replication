# Replication fidelity and effort audit

As of 2026-10-01. All 69 papers retain separate records. **Zero full original-paper reproductions are established.** The completed bounded experiments, manuscript and verified archives remain completed at their recorded scope. The conditional move to LLM improvement remains on hold.

[69-paper matrix](paper_fidelity_matrix.csv) · [structured evidence](paper_fidelity_matrix.json) · [acceptance criteria](ACCEPTANCE_CRITERIA.md) · [42-paper availability refresh](source_availability_refresh.csv) · [effort audit](effort_by_paper.csv) · [job timing](selected_job_timing.csv)

| Existing evidence category | Papers |
| --- | ---: |
| Evaluated component; full mechanism unreproduced | 13 |
| Excluded from common monthly U.S./JKP task | 7 |
| Missing artifacts or underidentified policy | 42 |
| Selected bounded/adapted or preserved cases | 6 |
| Observed-history Alpha; strict original unavailable | 1 |

The historical categories partition 69 papers; they are not a ranking or a new count of native components. The matrix includes both the native audit findings and the earlier common-benchmark outcome. The seven common-task exclusions do not prove impossibility of original-task replication. Baseline, author-output, component and version-specific coverage fields are retained in [published-result coverage](published_result_coverage.csv) with their original source/denominator; they are not summed into a full-paper success count.

## What the refresh changes

Alpha-R1 is the concrete new release candidate. The old one-file placeholder finding is dated, and the official September paper/code/model release warrants a new version-specific audit. Raw input and training/result lineage requirements remain open. See [the pinned change record](Alpha_R1_release_change.md).

Seventeen named GitHub default heads were fetched directly: 13 were already present in prior audit evidence; four were not (R&D-Agent, MountainLion platform, FINSABER and Alpha-R1). Only Alpha-R1 was verified here as a material paper implementation release. The other three are metadata leads requiring relevant-file comparison and author/paper attribution. Two Hugging Face metadata endpoints were checked. Exact-name searches cover all 42 historically missing/underidentified papers. This is a bounded refresh of default heads and search results, not another exhaustive fork/history census; non-results do not prove absence.

## What the effort records can support

34 existing per-paper effort records were found. The old effort records describe bounded checks and outcomes, without numeric labor/audit/debugging hours. No such hours were imputed.

The timing table contains 205 distinct selected allocations from saved job lineage. Execution includes source/replay/proof/account/analysis work and retained failures; archive/storage allocations are separate shared rows. These records cover selected work, not all historical execution. In particular, M019 timing covers selected exploratory economics, not its full source-search attempt, and M006 omits earlier preserved TSLA and separate replay jobs. Eligible-to-start waits and submission-to-start intervals are retained separately; the latter includes dependency/hold time. An additive job-time total measures selected allocation exposure and cannot be presented as calendar time or human effort.

| Paper | Selected allocations | Allocation wall hours, partial |
| --- | ---: | ---: |
| M006 | 4 | 25.68 |
| M009 | 14 | 153.75 |
| M014 | 6 | 17.58 |
| M019 | 6 | 2.33 |
| M023 | 17 | 38.56 |
| M043 | 152 | 48.97 |

Hours are resource accounting, with no better/worse direction or performance ranking. All 69 time-to-faithful-replication fields remain unavailable. The original archive/hash/package jobs retain their actual historical states; creating this metadata supplement rebuilds no archive.

## Next replication work

1. Start with Alpha-R1 v2 source/data/checkpoint conformance because a concrete official release changed its availability.
2. Inspect only relevant changes at the three other newly observed heads; broad framework or product changes may leave paper gaps unresolved.
3. Resolve per-paper native requirements, published-output inventories and acceptance scope. Preserve unresolved items and source access/licensing/model constraints; propose scientific execution only after a concrete protocol is reviewable.

The canonical spend ledger still matches the sealed release hash; recorded commitment is $371.06592557, under the exclusive $1,000 authorization. New model calls/scientific runs/ledger changes: zero. Earlier results and the release/manuscript remain unchanged.

## Paper-by-paper requirements

### M001 — GPT-Signal: Generative AI for Semi-automated Feature Engineering in the Alpha Research Process

Historical native audit: partial_1549_of_1554_published_quantitative_units_replayed_from_author_data_no_end_to_end_LLM_replication_monthly_lookahead_present

Remaining native requirements:

- missing_input_rule: Do not fill across time or introduce arbitrary epsilon/absolute-value transforms. Record convention differences as adaptations when economically defensible.
- not_claimed: fresh GPT-4-1106-preview signal generation
- not_claimed: reproduction of original FactSet inputs or all published tables
- not_claimed: replication of the paper's Fama-MacBeth experiment
- not_claimed: an exact original-paper trading portfolio

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [gpt_signal](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/gpt_signal/manifest.json)

### M002 — CryptoTrade: A Reflective LLM-based Agent to Guide Zero-shot Cryptocurrency Trading

Historical native audit reproduces 174/180 traditional-baseline cells and corroborates part of the coauthor LLM traces. LSTM look-ahead and model/asset/period conflicts prevent full native result credit.

Remaining native requirements:

- Resolve original paper model identity and asset/regime alignment for the LLM and ablation rows; historical author actions are partial corroboration, not regenerated decisions.
- Resolve LSTM future-input and validation/tie-selection defects and remaining traditional-baseline discrepancies under the original native data/protocol.
- Recover original repeated-run/request lineage and remaining table/figure outputs; preserve already verified native baselines.

Common-task transfer limitations (not prerequisites for original-task replication):

- missing_common_inputs: point-in-time stock news text
- missing_common_inputs: stock analogues with source-defined semantics for unique addresses, transferred value, gas, transaction success, and gas price
- missing_common_inputs: an immutable GPT-4o snapshot/fingerprint
- missing_common_inputs: a source-defined mapping from 1,000 isolated cash/asset states to one cross-sectional portfolio
- source_execution_conflicts: The active source prompts and state are cryptocurrency-specific and often hard-code ETH.
- source_execution_conflicts: The source default is GPT-3.5 while paper-labelled GPT-4o output lineage is incomplete or model-conflicted.
- source_execution_conflicts: The source loop is daily and stateful per one asset; batching or normalizing 1,000 actions changes both memory and portfolio semantics.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Reassess on the original task and input universe; common-monthly/JKP exclusion does not settle native replication.

Evidence: [cryptotrade](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/cryptotrade/manifest.json)

### M003 — Can Large Language Models Mine Interpretable Financial Factors More Effectively? A Neural-Symbolic Factor Mining Agent Model

Historical native audit: zero_of_65_table_results_and_zero_of_38_figure_markers_reproduced_no_native_pipeline

Remaining native requirements:

- missing_executable_objects: author-linked FAMA implementation
- missing_executable_objects: runtime function definitions required by the recovered prompt
- missing_executable_objects: the actual initial factor pool (38 claimed versus 71 Appendix identifiers)
- missing_executable_objects: final mined factor expressions or checkpoint
- missing_executable_objects: search/experience trace and factor evaluation data
- missing_executable_objects: portfolio construction, cost treatment and random seeds

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [fama](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/fama/manifest.json)

### M004 — FLAG-TRADER: Fusion LLM-Agent with Gradient-based Reinforcement Learning for Financial Trading

Historical native audit: partial_6_of_360_author_linked_buy_hold_baseline_cells_reproduced_4_current_response_verified_zero_flag_trader_native_results

Remaining native requirements:

- missing_executable_objects: author-linked FLAG-Trader source
- missing_executable_objects: base-model revision and trainable-layer split
- missing_executable_objects: optimizer, initialization, seed count and checkpoint-selection procedure
- missing_executable_objects: learned policy/value checkpoint
- missing_executable_objects: training and test action trajectories
- missing_executable_objects: paper-time market/news/macro inputs and exact adjustment conventions
- missing_executable_objects: native result/PnL paths

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [flag_trader](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/flag_trader/manifest.json)

### M005 — AlphaQuanter: An End-to-End Tool-Augmented Agentic Reinforcement Learning Framework for Stock Trading

Historical native audit: not_reproduced_prompt_label_component_and_buy_hold_reconstruction_only

Remaining native requirements:

- missing_headline_objects: the paper's 2025 test prompts and original multimodal inputs
- missing_headline_objects: paper-test actions and portfolio paths
- missing_headline_objects: complete VERL training/runtime modules
- missing_headline_objects: trained policy checkpoint and model/API snapshot
- missing_headline_objects: three-seed identities and outputs
- missing_headline_objects: token/cost logs and individual human ratings

Availability: Current public default head is already documented; availability does not resolve the recorded original-input/result gaps. Other branches/forks were not refreshed.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [alphaquanter](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alphaquanter/manifest.json)

### M006 — FinMem: A Performance-Enhanced LLM Trading Agent with Layered Memory and Character Design

Four added native FinMem asset trajectories and exact cached replay are complete; five-account descriptive aggregation includes preserved TSLA. Guard failures and adapted profiles/inputs retained.

Remaining native requirements:

- Original paper-time inputs/model revision and original character profiles are not established for every asset.
- All original repeated trials, trained memories and published result tables remain unreproduced.
- Our cross-asset aggregation is a disclosed adapter; native paper comparisons need their original conventions.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [finmem](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/finmem/manifest.json)

### M007 — QuantAgent: Seeking Holy Grail in Trading by Self-Improving Large Language Model

Historical native audit: source_document_rebuilt_but_zero_of_17_line_series_and_zero_of_400_heatmap_cells_reproduced_no_native_agent_pipeline

Remaining native requirements:

- not_claimed: self-improving agent
- not_claimed: LLM idea generation
- not_claimed: mentor process
- not_claimed: native data/evaluator
- not_claimed: paper result

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_adapter.missing_returns: fixed holdings re-accounted under common zero and adverse-100 policies without reranking

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [quantagent_self_improving](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/quantagent_self_improving/manifest.json)

### M008 — Alpha-GPT 2.0: Human-in-the-Loop AI for Quantitative Investment

Historical native audit: three_official_documents_rebuilt_and_lineage_audited_zero_native_alpha_gpt_results_alpha_gpt2_is_unevaluated_draft

Remaining native requirements:

- missing_headline_objects: an implemented Alpha Mining, Alpha Modeling, or Alpha Analysis agent
- missing_headline_objects: the agents' system-of-procedure prompts and model configuration
- missing_headline_objects: tool implementations and API contracts
- missing_headline_objects: memory contents, retrieval state, and financial knowledge graph
- missing_headline_objects: a generated alpha set or selected final alpha
- missing_headline_objects: a causal score-to-position or portfolio construction rule
- missing_headline_objects: any native evaluation, return path, checkpoint, trace, or output

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [alpha_gpt_lineage](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alpha_gpt_lineage/manifest.json)

### M009 — A Multimodal Foundation Agent for Financial Trading: Tool-Augmented, Diversified, and Generalist

Five FinAgent assets each have 250 training + 147 native causal records and exact full replay; 1,985 new records. All 13 equity accounts complete. Original interruptions and overlapping prefixes retained.

Remaining native requirements:

- Exact original Financial Modeling Prep/multimodal input and historical model endpoint lineage remain unavailable.
- Original repeated trials and all reported model, ablation and portfolio comparisons remain unreproduced.
- Modern input preparation and response-schema adaptations remain disclosed; exact replay validates our recorded execution.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [finagent](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/finagent/manifest.json)

### M010 — LLMFactor: Extracting Profitable Factors through Prompts for Explainable Stock Movement Prediction

Historical native audit: official_documents_and_prompt_metric_components_audited_zero_of_82_native_and_zero_of_206_total_result_cells_reproduced

Remaining native requirements:

- missing_headline_objects: author-linked implementation or executable pipeline
- missing_headline_objects: the exact point-in-time price/text snapshots and stock-universe membership
- missing_headline_objects: train, validation, and test splits plus preprocessing and news aggregation
- missing_headline_objects: complete request envelopes, generation settings, timestamps, and request/response logs
- missing_headline_objects: the company matcher, response parser, invalid-response policy, and flat-price label
- missing_headline_objects: raw daily predictions, confusion matrices, repeated runs, and uncertainty
- missing_headline_objects: a paper-defined portfolio converting binary predictions into cross-sectional holdings

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [llmfactor](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/llmfactor/manifest.json)

### M011 — FinCon: A Synthesized LLM Multi-Agent System with Conceptual Verbal Reinforcement for Enhanced Financial Decision Making

Historical native audit: paper_specification_audited_but_official_code_and_data_not_released

Remaining native requirements:

- missing_headline_objects: FinCon source code, complete prompts, configurations, environment, and tests
- missing_headline_objects: frozen multimodal commercial/public inputs and exact 42-stock membership
- missing_headline_objects: paper-time GPT-4-Turbo and Whisper snapshots plus sampling and parsing rules
- missing_headline_objects: working, procedural, and episodic memory state and decay parameters
- missing_headline_objects: CVaR estimator, alert, reflection, and conceptual verbal reinforcement implementation
- missing_headline_objects: manager actions, analyst outputs, raw trajectories, beliefs, and checkpoints
- missing_headline_objects: the complete direction-constrained mean-variance objective, covariance estimator, solver and bounds
- missing_headline_objects: execution timing, position persistence, leverage/short rules and trading frictions

Availability: Current public default head is not in prior audit; only its metadata has been refreshed, so inspect relevant changes before execution.

Next: Inspect changed default-head files for specific missing native artifacts; metadata change alone is not recovery.

Evidence: [fincon](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/fincon/manifest.json)

### M012 — Empirical Asset Pricing with Large Language Model Agents

Historical native audit: official_papers_sources_code_and_metadata_audited_zero_of_162_v2_result_cells_reproduced

Remaining native requirements:

- missing_headline_objects: the filtered WSJ article bodies and derived Tickers, Topics, and Content records
- missing_headline_objects: CRSP daily returns, Jensen-et-al. characteristic inputs, imputation, and mappings
- missing_headline_objects: generated report embeddings and continuously updated macro-note outputs
- missing_headline_objects: historical-factor pretraining code, training entrypoint, sweep history, and trained checkpoint
- missing_headline_objects: v2 GPT-4o/O1 request-response traces, exact generation settings, and parser
- missing_headline_objects: native return predictions, decile assignments, portfolio returns, baselines, and result arrays
- missing_headline_objects: TP/EW/VW long-short portfolio and asset-pricing test implementation

Availability: Current public default head is already documented; availability does not resolve the recorded original-input/result gaps. Other branches/forks were not refreshed.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [aapm](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/aapm/manifest.json)

### M013 — FinVision: A Multi-Agent Framework for Stock Market Prediction

Historical native audit: not_reproduced_no_public_system_source_frozen_inputs_or_trajectories

Remaining native requirements:

- missing_headline_objects: LangGraph implementation, dependency lock, runnable configuration and data pipeline
- missing_headline_objects: the original Yahoo/EODHD news rows, query parameters, timestamps, timezone and deduplication
- missing_headline_objects: the exact price snapshot, adjusted/unadjusted field, chart inputs and indicator implementation
- missing_headline_objects: immutable GPT-4o-mini/o1-mini snapshots, seeds, request IDs, requests and responses
- missing_headline_objects: daily BUY/SELL/HOLD actions, position sizes, fills, rewards, cash ledger and equity trajectory
- missing_headline_objects: trade timing, share rounding, long/short constraints, costs, slippage and cash equations

Common-task transfer limitations (not prerequisites for original-task replication):

- missing_headline_objects: a paper-defined cross-sectional portfolio adapter for the monthly top-1,000 JKP universe

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [finvision](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/finvision/manifest.json)

### M014 — TradingAgents: Multi-Agents LLM Financial Trading Framework

Three native 61-day equity trajectories plus separate 61-record news sensitivity are complete; exact replay and independent accounts verified. News sensitivity is distinct from original paper replication.

Remaining native requirements:

- Exact historical executable revision, paper-time point-in-time inputs/model snapshots and full published trajectory lineage remain incomplete.
- Original portfolio execution, baselines, repeated trials and all published results need native conformance.
- Current release execution and descriptive account clock/fee variants do not establish the original paper result.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [tradingagents](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/tradingagents/manifest.json)

### M015 — LLM-Powered Multi-Agent System for Automated Crypto Portfolio Management

Historical native audit recovers author data and fine-tuning-format/image records and exercises bounded component procedures. Remote fine-tuning/checkpoint/result lineage remains incomplete in both paper lineages.

Remaining native requirements:

- Keep v1/v2 and v3 experiment identities separate; recover exact remote fine-tuning job, uploaded training set and selected checkpoint lineage.
- Recover original market/blockchain panels, news/RAG modules, predictions, weekly native universe, requests/responses and portfolio/result arrays.
- Align each native configuration, repeated run and published table/figure with its own revision; component fixtures and author rasters are limited evidence.

Common-task transfer limitations (not prerequisites for original-task replication):

- missing_headline_objects: the actual uploaded fine-tuning file ID, job ID, active selected checkpoint, and paper-run linkage
- missing_headline_objects: paper-time coin prices, blockchain factors, market/news records, processed inputs, and weekly top-30 memberships
- missing_headline_objects: immutable inference requests/responses, predictions, token/logprob records, retries, and API-cost ledger
- missing_headline_objects: released expert checkpoint pickles and prediction JSON records required by the runner
- missing_headline_objects: paper portfolio arrays, holdings, costs/slippage, and result tables
- missing_headline_objects: a source-defined transfer from crypto/blockchain/image inputs to monthly U.S. stock characteristics

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Reassess on the original task and input universe; common-monthly/JKP exclusion does not settle native replication.

Evidence: [maci](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/maci/manifest.json)

### M016 — MarketSenseAI 2.0: Enhancing Stock Analysis through LLM Agents

Historical native audit: not_reproduced_manuscripts_only_no_operational_release

Remaining native requirements:

- missing_headline_objects: attributable operational code, dependency/runtime configuration, and exact five-agent graph
- missing_headline_objects: verbatim prompts, parser, GPT snapshots, inference parameters, seeds and repeated-run protocol
- missing_headline_objects: point-in-time S&P constituents and frozen price, news, SEC, transcript, and macro inputs
- missing_headline_objects: release-time/decision-time timestamps and execution lag
- missing_headline_objects: monthly buy/hold/sell generation records and confidence/explanation outputs
- missing_headline_objects: portfolio holdings, cap weights, trades, fills, cash, dividends, costs and NAV paths
- missing_headline_objects: VectorBTPro version/configuration, metric formulas, and factor-regression inputs/horizon

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [marketsenseai](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/marketsenseai/manifest.json)

### M017 — FinRL-DeepSeek: LLM-Infused Risk-Sensitive Reinforcement Learning for Trading Agents

Historical native audit executes all eight paper-relevant released checkpoints and substantial frozen data. Recomputed paper metrics disagree; benchmark alignment, training lineage and stochastic protocol remain unresolved.

Remaining native requirements:

- Resolve the paper-time benchmark/date alignment, stochastic evaluation seeds, metric conventions and disagreements with published values.
- Establish the exact 100-epoch DeepSeek risk-sensitive training/checkpoint lineage and paper figure/result arrays.
- Preserve the executed checkpoint diagnostics and changed-objective community variants with their original limited scope.

Common-task transfer limitations (not prerequisites for original-task replication):

- missing_or_conflicting_headline_objects: the exact 100-epoch DeepSeek 10% CPPO training entrypoint and checkpoint-to-run manifest
- missing_or_conflicting_headline_objects: the random article sample, selected FNSPID subset, request/response logs, and paper-era DeepSeek snapshot
- missing_or_conflicting_headline_objects: paper evaluation RNG seeds/states and table-generating notebook/output
- missing_or_conflicting_headline_objects: the paper-time Nasdaq benchmark and a non-lookahead constituent/reconstitution record
- missing_or_conflicting_headline_objects: a CPPO implementation matching the displayed CVaR Lagrangian and alpha=0.05 tail
- missing_or_conflicting_headline_objects: a model/input adapter from the fixed 84-stock daily state to monthly top-1,000 JKP securities
- missing_or_conflicting_headline_objects: full-calendar 1999-2024 LLM recommendation scores required by the policy

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Reassess on the original task and input universe; common-monthly/JKP exclusion does not settle native replication.

Evidence: [finrl_deepseek](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/finrl_deepseek/manifest.json)

### M018 — HedgeAgents: A Balanced-aware Multi-agent Financial Trading System

Historical native audit: not_reproduced_no_public_system_source_frozen_inputs_runtime_traces_or_portfolio_path

Remaining native requirements:

- missing_headline_objects: HedgeAgents code, runtime environment, agent/profile serialization, tool implementations, and runner
- missing_headline_objects: exact DJ30/FX/crypto universe and constituent vintage plus frozen Yahoo/Alpaca inputs
- missing_headline_objects: the 60 indicators, full prompts, model/embedding snapshots, memory database, seeds and repeated-run policy
- missing_headline_objects: budget-allocation lambdas, CVaR alpha, covariance window, solver, constraints and failure handling
- missing_headline_objects: experience-sharing cadence/rounds and extreme-market definition/execution logic
- missing_headline_objects: initial capital, sizing, fill timing, cash, short/leverage, costs and slippage
- missing_headline_objects: native actions, orders, fills, holdings, cash ledger, NAV/return paths and plot arrays

Availability: Current public default head is already documented; availability does not resolve the recorded original-input/result gaps. Other branches/forks were not refreshed.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [hedgeagents](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/hedgeagents/manifest.json)

### M019 — AlphaAgent: LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay

All 20 observed histories preserved: 96 attempts, 4 unattempted rounds, 86 histories. Exploratory library, four accounts and analysis complete. Original 20 x 5 strict experiment remains unavailable.

Remaining native requirements:

- Four unattempted rounds prevent the original 20-trial, five-round strict experiment; retain the observed aborts.
- Historical original factor identities/model/data lineage and conflicting source/paper conventions remain unresolved.
- Observed-history sensitivity cannot substitute for the missing original primary or four/54 inference families.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [alphaagent](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alphaagent/manifest.json)

### M020 — MASS: Muli-agent simulation scaling for portfolio construction

Historical native audit: not_reproduced_partial_internal_state_only

Remaining native requirements:

- missing_headline_objects: all per-agent prompts, multimodal inputs, decisions and candidate-pool assignments
- missing_headline_objects: dated aggregated signals and security rankings
- missing_headline_objects: Nasdaq-100/S&P-500 and other paper input panels, point-in-time memberships, and news
- missing_headline_objects: paper hyperparameter execution, run seeds, random draws, and metric horizon
- missing_headline_objects: weekly portfolio/backtest/cost code, baseline outputs, timing logs and API accounting
- missing_headline_objects: holdings, returns, risk-free rate, NAV paths and table/figure arrays

Availability: Current public default head is already documented; availability does not resolve the recorded original-input/result gaps. Other branches/forks were not refreshed.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [mass](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/mass/manifest.json)

### M021 — Navigating the Alpha Jungle: An LLM-Powered MCTS Framework for Formulaic Factor Mining

Historical native audit: zero_of_64_published_cells_reproduced_zero_native_results_three_of_six_formula_trees_conditionally_adapted

Remaining native requirements:

- not_claimed: MCTS search
- not_claimed: LLM prompts/responses
- not_claimed: native model
- not_claimed: native portfolio
- not_claimed: paper result

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_adapter.missing_returns: fixed holdings re-accounted under common zero and adverse-100 policies without reranking

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [alpha_jungle](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alpha_jungle/manifest.json)

### M022 — R&D-Agent: An LLM-Agent Framework Towards Autonomous Data Science

Historical native audit: paper_specification_source_official_history_and_1854_forks_audited_zero_native_results_missing_attributable_run_artifacts

Remaining native requirements:

- missing_paper_result_objects: the frozen 75-competition dataset/container manifest and grading revision
- missing_paper_result_objects: paper run configurations, prompts/responses, generated code, seeds and traces
- missing_paper_result_objects: three complete 12-hour runs for every main and ablation configuration
- missing_paper_result_objects: Azure deployment snapshots, credentials and exact historical package/container state
- missing_paper_result_objects: submissions, checkpoints, medal outcomes and complete published result rows
- scope_finding: The primary paper contains no stock signal, trading action, asset universe, portfolio construction, or investment return. It is the general MLE-Bench R&D-Agent report, not the separate R&D-Agent-Quant lineage.

Availability: Current public default head is not in prior audit; only its metadata has been refreshed, so inspect relevant changes before execution.

Next: Inspect changed default-head files for specific missing native artifacts; metadata change alone is not recovery.

Evidence: [rd_agent](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/rd_agent/manifest.json)

### M023 — EFS: Evolutionary Factor Searching for Sparse Portfolio Optimization Using Large Language Models

Paper-guided EFS engine, three trajectories per LLM pool, matched grammar, pooled accounts and economic analysis complete. Attributable original EFS author implementation was not recovered.

Remaining native requirements:

- Attributable original author EFS search/portfolio implementation and its exact original inputs/model snapshots remain unavailable.
- Paper-guided implementation choices, factor discovery timing and unmatched published experiments remain explicit.
- Current bounded pooled comparisons and JKP diagnostics do not reproduce every native result or establish net fund/frontier performance.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [efs](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/efs/manifest.json)

### M024 — MountainLion: A Multi-Modal LLM-Based Agent System for Interpretable and Adaptive Financial Trading

Historical native audit: not_reproduced_public_components_only_no_result_lineage

Remaining native requirements:

- missing_headline_objects: forecast training panel, exchange, dates, candle frequency, preprocessing and split
- missing_headline_objects: ML estimator, fitted model, cross-validation folds/scores and prediction arrays
- missing_headline_objects: exact LLM snapshots, substituted prompts, requests/responses, tools, parameters and seeds
- missing_headline_objects: GraphRAG graph/data, retrieval provenance, sentiment embeddings and news recommendation records
- missing_headline_objects: adaptive-alpha optimizer, LLM/ML horizon alignment, reflection and feedback implementation
- missing_headline_objects: private ml4gp modules, plugin, MySQL/Redis schemas/state and service credentials
- missing_headline_objects: portfolio rule, actions, holdings, fills, cash, fees, returns and benchmark path

Availability: Current public default head is not in prior audit; only its metadata has been refreshed, so inspect relevant changes before execution.

Next: Inspect changed default-head files for specific missing native artifacts; metadata change alone is not recovery.

Evidence: [mountainlion](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/mountainlion/manifest.json)

### M025 — ContestTrade: A Multi-Agent Trading System Based on Internal Contest Mechanism

Historical native audit: not_reproduced_public_entrypoint_omits_contests

Remaining native requirements:

- missing_or_conflicting_headline_objects: an active entrypoint connecting Data Contest, Research Contest and portfolio construction
- missing_or_conflicting_headline_objects: the paper's facility-location/lazy-greedy token allocator and embedding-cosine diversity implementation
- missing_or_conflicting_headline_objects: rolling Data Contest training data, dates, split, seed and model provenance
- missing_or_conflicting_headline_objects: the two Research Contest models and its called predict_signal_scores method
- missing_or_conflicting_headline_objects: paper input snapshot, point-in-time universe, model/API snapshots, prompts/responses and seeds
- missing_or_conflicting_headline_objects: portfolio/backtester, baselines, ablation runner, metrics, holdings, returns and result logs
- missing_or_conflicting_headline_objects: paper-consistent signed ZI reward and five-day research horizon

Availability: Current public default head is already documented; availability does not resolve the recorded original-input/result gaps. Other branches/forks were not refreshed.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [contesttrade](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/contesttrade/manifest.json)

### M026 — Chain-of-Alpha: Unleashing the Power of Large Language Models for Alpha Mining in Quantitative Trading

Historical native audit: not_reproduced_withdrawn_primary_record_no_attributable_system_or_native_experiment_lineage

Remaining native requirements:

- not_claimed: native parser semantics
- not_claimed: generation or optimization chain
- not_claimed: 1,000-candidate search
- not_claimed: selected 100-factor pool
- not_claimed: LightGBM
- not_claimed: native Qlib portfolio
- not_claimed: paper result

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_adapter.missing_returns: common zero primary and adverse-100 sensitivity without reranking

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [chain_of_alpha](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/chain_of_alpha/manifest.json)

### M027 — AlphaAgents: Large Language Model based Multi-Agents for Equity Portfolio Constructions

Historical native audit: source_document_rebuilt_and_7_portfolios_recovered_but_zero_of_20_plotted_performance_series_reproduced_no_native_agent_pipeline

Remaining native requirements:

- missing_headline_objects: author-linked implementation, AutoGen version, group-chat termination and complete scheduling
- missing_headline_objects: risk-neutral/risk-averse persona prompts, model snapshot, sampling settings, seeds and retries
- missing_headline_objects: Bloomberg news, filing accessions, Yahoo price snapshot, tool code and RAG state
- missing_headline_objects: agent recommendations, debate histories, human review, Phoenix evaluations and repeated trials
- missing_headline_objects: a point-in-time repeatable rule producing memberships before February 2024
- missing_headline_objects: execution timing, prices, corporate actions, costs/slippage and portfolio return arrays

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [alphaagents](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alphaagents/manifest.json)

### M028 — From Flat to Hierarchical: Evolving Tree-structured Thoughts for Fine-grained Alpha Mining

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- missing_headline_objects: TreEvo implementation, dependency environment, execution sandbox and runner
- missing_headline_objects: actual seed trees, filled prompts, model snapshots, responses, seeds and search trajectories
- missing_headline_objects: the thought-tree-to-executable-code prompt, schema, parser and correction policy
- missing_headline_objects: generated factor expressions/code, factor scores, selected population and five-run outputs
- missing_headline_objects: point-in-time universe memberships, market-data snapshot, adjustment and calendar rules
- missing_headline_objects: portfolio weights, holdings, costs, daily returns and raw table/figure arrays

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [treevo](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/treevo/manifest.json)

### M029 — TradingGroup: A Multi-Agent Trading System with Self-Reflection and Data-Synthesis

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- missing_headline_objects: attributable TradingGroup implementation and exact runtime dependency/configuration
- missing_headline_objects: Qwen3-Trader-8B-PEFT checkpoint and complete LoRA hyperparameters
- missing_headline_objects: the 1,080 training trajectories, teacher traces, full prompts and immutable requests/responses
- missing_headline_objects: complete news/RAG/forecast/style/reflection tool implementations and model snapshots
- missing_headline_objects: paper actions, quantities, fills, commissions, cash, NAV, daily returns and figure arrays
- missing_headline_objects: run seeds, repeated trials and a policy transferable beyond the five test tickers

Availability: Current public default head is not in prior audit; only its metadata has been refreshed, so inspect relevant changes before execution.

Next: Inspect changed default-head files for specific missing native artifacts; metadata change alone is not recovery.

Evidence: [tradinggroup](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/tradinggroup/manifest.json)

### M030 — MM-ARC: Multimodal Adaptive Routing of Capital with Robustness-Audited Strategy Pools

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- missing_headline_objects: three trained adapter_model.safetensors payloads
- missing_headline_objects: the seed-42 reinforcement-learning router best_model.pt payload
- missing_headline_objects: the full strategy-signal and robustness-history tables
- missing_headline_objects: full benchmark market data beyond the 120-observation acceptance fixture
- missing_headline_objects: the training/experiment controller and private model history
- missing_headline_objects: trained seeds 43-46, full decision cycles, result arrays and report generator

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [mm_arc](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/mm_arc/manifest.json)

### M031 — QuantHarness: Price-Driven Multi-Agent LLMs for High-Frequency Trading

Historical native audit recovers substantial source, sampled inputs and author result rasters across four revisions. The native fixed-segment evaluator and underlying result paths remain unreproduced.

Remaining native requirements:

- Recover the native fixed 100-segment experiment runner, frozen segment/universe/model/config protocol and prediction/return/risk-ratio arrays.
- Bind native output generation to each paper revision; author table/chart rasters and community/live databases cannot supply missing original result paths.
- Resolve native time-series/execution, repeated-trial and portfolio-performance target coverage.

Common-task transfer limitations (not prerequisites for original-task replication):

- Use the linked native audit requirement inventory; no complete end-to-end published-result certificate exists.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Reassess on the original task and input universe; common-monthly/JKP exclusion does not settle native replication.

Evidence: [quantharness](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/quantharness/manifest.json)

### M032 — Trading-R1: Financial Trading with LLM Reasoning via Reinforcement Learning

Historical native audit: paper_spec_mechanisms_reconstructed_but_zero_of_348_published_result_units_reproduced_official_release_still_placeholder

Remaining native requirements:

- Original trained Trading-R1 model, Tauric-TR1-DB inputs, training/decoding recipe, native trajectories and published result arrays remain unreproduced; official default head is README-only.

Availability: Current public default head is not in prior audit; only its metadata has been refreshed, so inspect relevant changes before execution.

Next: Inspect changed default-head files for specific missing native artifacts; metadata change alone is not recovery.

Evidence: [trading_r1](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/trading_r1/manifest.json)

### M033 — GuruAgents: Emulating Wise Investors with Prompt-Guided LLM Agents

Preserved earlier GuruAgents source/prompt/component case; current six-case categorization does not certify all published experiments.

Remaining native requirements:

- Verify the original paper experiment inventory against native model, prompt/input, portfolio and repeated-trial records; earlier prompt/component replay is insufficient.
- Preserve disclosed missing metric and source-rule adaptations from the prior audit.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [guruagents](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/guruagents/manifest.json)

### M034 — QuantAgents: Towards Multi-agent Financial System via Simulated Trading

Historical native audit: not_reproduced_no_public_system_source_frozen_inputs_runtime_traces_or_portfolio_path

Remaining native requirements:

- missing_headline_objects: the complete runtime prompts, fills, response schema and action parser
- missing_headline_objects: the 26 callable tools and 60 indicator implementations
- missing_headline_objects: the three memory stores, update rules and retrieved records
- missing_headline_objects: the finite strategy-pool grammar, parameter grid and realized strategies
- missing_headline_objects: the four risk-score weights, component normalizations and risk-reward function
- missing_headline_objects: the policy parameterization, optimizer, simulated and real reward histories
- missing_headline_objects: point-in-time NASDAQ-100 membership, frozen Yahoo/Alpaca rows and news identifiers
- missing_headline_objects: capital, order, fill, cost, slippage, constraint, rebalance and corporate-action rules
- missing_headline_objects: actions, orders, fills, dated holdings, portfolio paths, seeds and repeated runs

Availability: Current public default head is already documented; availability does not resolve the recorded original-input/result gaps. Other branches/forks were not refreshed.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [quantagents](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/quantagents/manifest.json)

### M035 — Trade in Minutes! Rationality-Driven Agentic System for Quantitative Financial Trading

Historical native audit rebuilds both manuscripts. Native trading code, data/outputs and the listed but inaccessible supplement remain unresolved; no experimental reproduction is established.

Remaining native requirements:

- Recheck and recover the officially listed supplementary ZIP containing cost records; historical 403/404 access is not proof the artifact never existed.
- Recover native prompts/model traces, generated bots, point-in-time 213-pair K-line/news inputs, seeds, fees/funding and live/simulation trades.
- Resolve contradictory order counts and return/annualization/coverage conventions, and regenerate native tables and figure arrays.

Common-task transfer limitations (not prerequisites for original-task replication):

- Use the linked native audit requirement inventory; no complete end-to-end published-result certificate exists.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Reassess on the original task and input universe; common-monthly/JKP exclusion does not settle native replication.

Evidence: [timi](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/timi/manifest.json)

### M036 — Profit Mirage: Revisiting Information Leakage in LLM-based Financial Agents

Historical native audit: not_reproduced_no_public_system_or_benchmark_release_and_missing_runtime_data_strategy_trade_lineage

Remaining native requirements:

- missing_headline_objects: the executable SCG language, function signature, package surface, sandbox and parser
- missing_headline_objects: all runtime prompts beyond one explicitly simplified template and all immutable model requests/responses
- missing_headline_objects: the RAG corpus, chunks, index, query construction, distances and retrieved records
- missing_headline_objects: the initial strategy code, MCTS node/action/branch definitions and every evolved strategy
- missing_headline_objects: the strategy evaluator, rollouts, reward, budget, convergence/stopping rule and random seeds
- missing_headline_objects: counterfactual generators, perturbation magnitudes, constraints, scenarios and alpha/beta/gamma objective weights
- missing_headline_objects: the original Yahoo/Alpaca price/news snapshots, exact factors, lookbacks and point-in-time rules
- missing_headline_objects: position quantities/weights, capital, inventory, shorting/leverage and signal-to-fill timing
- missing_headline_objects: numeric transaction costs, slippage, orders, fills, cash ledger and dated NAV
- missing_headline_objects: the train/validation split, repetitions, uncertainty, baseline snapshots and environment lock

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [factfin](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/factfin/manifest.json)

### M037 — ATLAS: Adaptive Trading with LLM AgentS Through Dynamic Prompt Optimization and Multi-Agent Coordination

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- missing_atlas_objects: the fixed baseline Central Trading Agent instruction and exact filled runtime prompts
- missing_atlas_objects: the Adaptive-OPRO optimizer implementation, meta-prompt, model requests/responses and edit history
- missing_atlas_objects: the complete optimization history of prompts, five-day outcome summaries and scores
- missing_atlas_objects: the paper's promised o4-mini Adaptive-OPRO sample configuration
- missing_atlas_objects: the exact three-asset experiment matrix, seeds and three-run artifacts
- missing_atlas_objects: frozen Massive/Polygon market data plus aligned news and fundamental inputs
- missing_atlas_objects: the paper's CTA actions, orders, fills, cash, positions and portfolio trajectories
- missing_atlas_objects: provider snapshot/decoding parameters for all seven backbones
- missing_atlas_objects: paper result arrays and report-generation lineage

Availability: Current public default head is already documented; availability does not resolve the recorded original-input/result gaps. Other branches/forks were not refreshed.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [atlas](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/atlas/manifest.json)

### M038 — P1GPT: a multi-agent LLM workflow module for multi-modal financial information analysis

Historical native audit: not_reproduced_author_output_and_baseline_verification_only

Remaining native requirements:

- missing_headline_objects: all paper agent implementations and orchestration code
- missing_headline_objects: LLM/provider/model identities, checkpoints, temperatures, decoding and seeds
- missing_headline_objects: system, developer, tool and daily prompts for each role
- missing_headline_objects: structured message schemas, routing, fusion weights, confidence and conflict/retry rules
- missing_headline_objects: exact market/news/fundamental/search endpoints, query timestamps and frozen responses
- missing_headline_objects: decision time relative to market close and information publication
- missing_headline_objects: initial capital, Buy quantity, repeated-Buy behavior, cash/inventory and position constraints
- missing_headline_objects: daily requests, responses, independent decisions, positions and equity arrays
- missing_headline_objects: the result runner and metric/formatting implementation
- missing_headline_objects: replicates, uncertainty, significance and selection protocol

Availability: Current public default head is not in prior audit; only its metadata has been refreshed, so inspect relevant changes before execution.

Next: Inspect changed default-head files for specific missing native artifacts; metadata change alone is not recovery.

Evidence: [p1gpt](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/p1gpt/manifest.json)

### M039 — FinPos: A Position-Aware Trading Agent System for Real Financial Markets

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- missing_headline_objects: the signal-filtering and analyst implementations and domain heuristics
- missing_headline_objects: hierarchical-memory allocation, retrieval, scoring, migration and persistence
- missing_headline_objects: the Direction Agent and Quantity/Risk Agent runtime prompts, responses and parser
- missing_headline_objects: the GPT-4o revision/API configuration, seeds and repeated trajectories
- missing_headline_objects: a dimensionally defined conversion from CVaR return/PnL to integer share quantity
- missing_headline_objects: initial cash/positions, account-value definition, leverage/shorting limits and liquidation
- missing_headline_objects: decision/fill timing, price, fees, spread, slippage and borrowing rules
- missing_headline_objects: immutable Yahoo/Finnhub/EDGAR rows, query timestamps and point-in-time alignment
- missing_headline_objects: daily actions, quantities, orders, fills, positions, PnL and account paths
- missing_headline_objects: the result generator, CR-percent mapping, metric conventions and uncertainty protocol

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [finpos](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/finpos/manifest.json)

### M040 — FINRS: A Risk-Sensitive Trading Framework for Real Financial Markets

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- missing_headline_objects: all domain filtering/analysis implementations and risk-focused prompts
- missing_headline_objects: hierarchical-memory allocation, retrieval, promotion/discard and persistence
- missing_headline_objects: the direction and quantity/risk agent runtime prompts, responses and parser
- missing_headline_objects: the scaled-Kelly equation, scale, probability/odds inputs and portfolio constraints
- missing_headline_objects: the CVaR confidence level, horizon, estimator, units and conversion to quantity
- missing_headline_objects: the volatility-adjustment formula, window, units and interaction with exposure
- missing_headline_objects: the GPT-4o immutable snapshot, decoding configuration, seeds and repetitions
- missing_headline_objects: initial account state, trade units, timing, fills, costs, slippage, borrowing and liquidation
- missing_headline_objects: immutable provider rows, publication timestamps, actions, positions, PnL and account paths
- missing_headline_objects: metric definitions, result generator, raw arrays and uncertainty protocol

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [finrs](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/finrs/manifest.json)

### M041 — Cognitive Alpha Mining via LLM-Driven Code-Based Evolution

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- full_system_not_reproduced: the 21-agent seven-level hierarchy and random selection of 13 agents
- full_system_not_reproduced: the approximately 80-factor initial pool and 32-factor parent pool
- full_system_not_reproduced: the 96-child multi-operator evolution cycles and selection thresholds
- full_system_not_reproduced: gpt-oss-120b serving/checkpoint, sampling, requests and seeds
- full_system_not_reproduced: quality-checker judgments, repairs, leakage checks and adaptive memory
- full_system_not_reproduced: LightGBM/Ridge multifactor learner and top-50/drop-5 Qlib portfolio
- full_system_not_reproduced: paper datasets, memberships, daily open execution, fees, holdings and results

Common-task transfer limitations (not prerequisites for original-task replication):

- common_task_adaptations.missing_return_policy: zero without reweighting

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [cogalpha](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/cogalpha/manifest.json)

### M042 — Alpha-R1: Alpha Screening with LLM Reasoning via Reinforcement Learning

No new Alpha-R1 official code/model execution was performed. Preserved v1 audit and adapted common-benchmark reconstruction retain their old scope; current v2/code/model availability is a separate new candidate.

Remaining native requirements:

- Align v1 and v2 target inventories before awarding any reproduction credit.
- Pin exact native data/universe and market/news descriptions; source data contract omits raw inputs.
- Verify model/tokenizer bytes and their training/result lineage; metadata listing is not validation.
- Audit factor pool, GRPO reward/judge, date/calendar, VWAP/limit rules, baselines, ablations and repeated-trial outputs against v2.
- Preserve original v1 zero-result verdict; new release has not been executed in this audit.

Availability: Original v1 audit is preserved. arXiv v2 dated 2026-09-07 and repository head dated 2026-09-08 provide a new version to audit. Tree lists 32 Python files and official model metadata lists four weight shards. Raw market/news inputs are omitted; training has a reference reward with optional judge stub. No weights were downloaded, loaded or tested; historical output equivalence is unverified.

Next: Audit Alpha-R1 v2 static conformance and exact data/checkpoint lineage first; stop before model or economic execution.

Evidence: [alpha_r1](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alpha_r1/manifest.json)

### M043 — QuantaAlpha: An Evolutionary Framework for LLM-Driven Alpha Mining

Released-default Quanta and separate paper-parameter continuation, exact replay, 142 program proofs, native population and four parameter economic accounts complete. Historical pools/versions and failures preserved.

Remaining native requirements:

- Fresh declared source runs are complete; they do not recover the exact historical published factor pool, request/model snapshots or all native results.
- Source/paper version and configuration conflicts, reconstructed seeded control flow, data vintage and market microstructure gaps remain.
- Opening proxy and exploratory parameter sensitivity are separate results; all relevant comparisons remain inconclusive at 2 pp.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [quantaalpha](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/quantaalpha/manifest.json)

### M044 — FactorMiner: A Self-Evolving Agent with Skills and Experience Memory for Financial Alpha Discovery

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- full_system_not_reproduced: The Gemini 3.0 Flash Ralph Loop, prompts, memory states, candidates, admission trajectory, and exact model calls.
- full_system_not_reproduced: The unreleased author-native 60+ operator runtime; an explicitly unaffiliated interpreter supplies semantics.
- full_system_not_reproduced: The 10-minute A-share/Binance panels, point-in-time constituents, and 2024/2025 arrays.
- full_system_not_reproduced: The exact reported IC/ICIR or the claimed 40-worker GPU/C backend.
- full_system_not_reproduced: An author-specified portfolio and trading return, because the paper reports only predictive scores.
- full_system_not_reproduced: A pristine confirmatory test; prior project and JKP outcomes were already visible.

Common-task transfer limitations (not prerequisites for original-task replication):

- portfolio_adapter.missing_returns: zero primary and -100% adverse sensitivity

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [factorminer](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/factorminer/manifest.json)

### M045 — Janus-Q: End-to-End Event-Driven Trading via Hierarchical-Gated Reward Modeling

Historical native audit verifies released event-data integrity and author static outputs, including 61/130 corroborated displayed cells. These do not regenerate Janus-Q training, predictions or native portfolios.

Remaining native requirements:

- Recover original base model/checkpoint, selected GRPO/reward settings, executable gates and native training/prediction/backtest code.
- Recover raw price/benchmark/CNE5 input and regression lineage, seeds, orders, costs and missing ablation/figure arrays.
- Preserve author static-output corroboration and its contradictions separately from native regeneration.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The named base model, immutable checkpoint, tokenizer, SFT output, and GRPO output.
- monthly_jkp_assessment.required_but_missing: Executable prompt parsing, prediction, reward, event aggregation, portfolio, and backtest code.
- monthly_jkp_assessment.required_but_missing: Selected reward constants and weights, inference decoding, seeds, and model responses.
- monthly_jkp_assessment.required_but_missing: Point-in-time U.S. news events aligned to the JKP top-1,000 formation universe.
- monthly_jkp_assessment.required_but_missing: An event-overlap/conflict rule, capital budget, leverage, fills, costs, and missing-price policy.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Reassess on the original task and input universe; common-monthly/JKP exclusion does not settle native replication.

Evidence: [janus_q](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/janus_q/manifest.json)

### M046 — FactorEngine: A Program-level Knowledge-Infused Factor Mining Framework for Quantitative Investment

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- full_system_not_reproduced: The program-level LLM evolution, research-report ingestion, prompts/responses, and 40-iteration trajectory.
- full_system_not_reproduced: The unreleased generated factor pool and LightGBM synthesis behind headline tables.
- full_system_not_reproduced: The original Qlib A-share data, point-in-time constituents, predictions, holdings, and returns.
- full_system_not_reproduced: The author runtime and environment; the listing is translated directly into pandas arithmetic.
- full_system_not_reproduced: Any original-paper metric or figure.
- full_system_not_reproduced: A pristine confirmatory test; prior project and JKP outcomes were already visible.

Common-task transfer limitations (not prerequisites for original-task replication):

- common_task_adaptations.missing_returns: zero primary and -100% adverse sensitivity

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [factorengine](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/factorengine/manifest.json)

### M047 — Can Blindfolded LLMs Still Trade? An Anonymization-First Framework for Portfolio Optimization

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: Point-in-time anonymized U.S. headlines, sentiment inputs, batch assignments, and proper-noun replacement outputs.
- monthly_jkp_assessment.required_but_missing: Immutable Gemini request settings and the 1,403-day four-agent output/reasoning dataset.
- monthly_jkp_assessment.required_but_missing: The GATv2 implementation, all loss weights/targets, trained weights, semantic graph edges, and predictions.
- monthly_jkp_assessment.required_but_missing: The PPO-DSR implementation, trained seed checkpoints, exact state/action construction, and Optuna search history.
- monthly_jkp_assessment.required_but_missing: Daily holdings, intent paths, turnover, returns, and seed-level output arrays.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [blindtrade](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/blindtrade/manifest.json)

### M048 — AlphaLogics: A Market Logic-Driven Multi-Agent System for Scalable and Interpretable Alpha Factor Generation

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The initial and evolved market-logic libraries and the deterministic H-to-structured-H-to-Gamma compilation mapping.
- monthly_jkp_assessment.required_but_missing: Filled LLM requests/responses, model revisions/settings, selection objective J, budgets, and seeds.
- monthly_jkp_assessment.required_but_missing: The generated factor formulas, trial trajectories, accepted pool, signs, and LightGBM configuration/weights.
- monthly_jkp_assessment.required_but_missing: Frozen data/universe snapshots, Qlib handler, predictions, holdings, returns, and execution settings.
- monthly_jkp_assessment.required_but_missing: A resolved Top-50/drop-5 portfolio definition consistent with the claimed source implementation.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [alphalogics](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alphalogics/manifest.json)

### M049 — TrustTrade: Human-Inspired Selective Consensus Reduces Decision Uncertainty in LLM Trading Agents

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: Consensus agent count, exact models/revisions/prompts/settings, filled reports, and claim extraction schema.
- monthly_jkp_assessment.required_but_missing: Embedding model and the sigma/lambda/tau/alpha/high-consensus parameters that define filtering and weighting.
- monthly_jkp_assessment.required_but_missing: Temporal polynomial degree/fit, trend-score formula, forecast intervals, signal-combination weights, and action thresholds.
- monthly_jkp_assessment.required_but_missing: Reflective-memory window, retrieval rule, prompts/models, prior decisions, and risk-preference update logic.
- monthly_jkp_assessment.required_but_missing: 2026 forward-run inputs/calls/timestamps, participant decisions, strategy actions, fills, costs, holdings, and NAV paths.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [trusttrade](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/trusttrade/manifest.json)

### M050 — Designing Agentic AI-Based Screening for Portfolio Investment

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: Point-in-time S&P 500 membership/identifiers and exact CRSP/Compustat, IBES/WRDS, factor, and news-to-security snapshots.
- monthly_jkp_assessment.required_but_missing: The FinBERT checkpoint/revision, tokenizer/inference settings, monthly probabilities, and sentiment signal ledger.
- monthly_jkp_assessment.required_but_missing: All annual LLM-S prompts, injected cross-sections/tool payloads, exact model snapshots/settings, responses, and buy/sell/hold rules.
- monthly_jkp_assessment.required_but_missing: Dated ensemble sets/fallback events and the full precision-estimator, optimizer, solver, deep-model, and seed configuration.
- monthly_jkp_assessment.required_but_missing: Fitted matrices, weights, returns, turnover, costs, paired-test samples, rerun outputs, and table-generating arrays.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [agentic_ai_screening](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/agentic_ai_screening/manifest.json)

### M051 — Hubble: An LLM-Driven Agentic Framework for Safe, Diverse, and Reproducible Alpha Factor Discovery

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The five winning formulas, exact hyperparameters, candidate identities, signs, and family-selection records.
- monthly_jkp_assessment.required_but_missing: The operator registry/executor, prompts, positive/negative RAG corpora and indexes, model requests/responses, and scoring constants.
- monthly_jkp_assessment.required_but_missing: Frozen U.S. universe/data snapshots, included-date arrays, missing-data rules, and formula values.
- monthly_jkp_assessment.required_but_missing: Candidate/error records, seeds, runtime environment, raw IC/return/turnover arrays, and persisted diagnostics.
- monthly_jkp_assessment.required_but_missing: A transaction-cost-aware investable portfolio rule; v2 reports simple factor diagnostics without costs.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [hubble](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/hubble/manifest.json)

### M052 — Signal or Noise in Multi-Agent LLM-based Stock Recommendations?

Historical native audit: not_reproduced_manuscripts_only_no_operational_release

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The 467- and 94-stock cohort ticker lists, formation vintage, exact first-Friday timestamps, and price/return fields.
- monthly_jkp_assessment.required_but_missing: Specialist/synthesis model identities, snapshots, prompts, parameters, live request timestamps, and raw responses.
- monthly_jkp_assessment.required_but_missing: All 12,163 specialist summaries, synthesis theses, five-class recommendation labels, and strong-buy membership by date.
- monthly_jkp_assessment.required_but_missing: The text-embedding-3-small requests and 1,536-dimensional thesis/agent embedding arrays.
- monthly_jkp_assessment.required_but_missing: The fixed Monte Carlo seed/arrays, NNLS implementation/tolerances, dated IC arrays, costs, holdings, and NAV paths.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [marketsenseai](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/marketsenseai/manifest.json)

### M053 — AlphaCrafter: Harnessing Multi-Agent Workflows for Cross-Sectional Quantitative Trading

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The paper's point-in-time S&P 500 memberships and stock, fundamental, statement, and news research snapshots.
- monthly_jkp_assessment.required_but_missing: Paper-time GPT, Claude, and Gemini requests/responses, model parameters, seeds, and ten-trial records.
- monthly_jkp_assessment.required_but_missing: The mined candidate and selected factor pools, factor values, screener decisions, and trader state.
- monthly_jkp_assessment.required_but_missing: Security-date actions, orders, fills, holdings, NAV/return arrays, brokerage records, and result generators.
- monthly_jkp_assessment.required_but_missing: Baseline implementations and the complete U.S. routing/configuration needed to identify the reported comparison.

Availability: Current public default head is already documented; availability does not resolve the recorded original-input/result gaps. Other branches/forks were not refreshed.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [alphacrafter](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alphacrafter/manifest.json)

### M054 — Strat-LLM: Stratified Strategy Alignment for LLM-based Stock Trading with Real-time Multi-Source Signals

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: A source-selected model and interaction mode, exact prompts, structured response schema, sampling configuration, retries, and immutable model requests/responses.
- monthly_jkp_assessment.required_but_missing: The stock lists, exact short-window dates, point-in-time minute prices, real-time news, annual reports, timestamps, preprocessing, and data snapshots.
- monthly_jkp_assessment.required_but_missing: Complete S1-S4 operational rules; only S2 supplies one numeric entry condition, while exits, sizes, thresholds, tie rules, and the other three strategy definitions remain incomplete.
- monthly_jkp_assessment.required_but_missing: The buy-volume rule, transaction-cost schedule, slippage, shorting/leverage, corporate actions, portfolio aggregation, and broker implementation.
- monthly_jkp_assessment.required_but_missing: Security-date actions, orders, fills, cash, holdings, NAV/return arrays, metric formulas, seeds, and raw result arrays.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [stratllm](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/stratllm/manifest.json)

### M055 — SHARP: A Self-Evolving Human-Auditable Rubric Policy for Financial Trading Agents

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The final evolved rubrics and complete evolution histories for every model, sector, and walk-forward window; only representative diffs are printed.
- monthly_jkp_assessment.required_but_missing: Exact analyst, attribution, and evolution prompts; schemas; temperatures; immutable requests/responses; and activated-rule traces.
- monthly_jkp_assessment.required_but_missing: The Yahoo rows and download/adjustment settings, Finnhub article cache, exact three split calendars, and all point-in-time market/news inputs.
- monthly_jkp_assessment.required_but_missing: The claimed 1-4 sector-specific initial rules, whose released-code location is unavailable, plus reconciliation of the paper's six-versus-seven shared-rule conflict.
- monthly_jkp_assessment.required_but_missing: Daily predicted returns/confidences, scores, weights, trades, turnover/cost events, returns, seeds, baselines, and result generator.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [sharp](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/sharp/manifest.json)

### M056 — From Feedback Loops to Policy Updates: Reinforcement Fine-Tuning for LLM-Based Alpha Factor Discovery

Historical native audit: not_reproduced_substantial_public_framework_zero_paper_results

Remaining native requirements:

- not_claimed: reinforcement fine-tuning
- not_claimed: trained miner checkpoint
- not_claimed: paper seed/task bank
- not_claimed: LLM factor search
- not_claimed: DiCo/archive reward learning
- not_claimed: mined factor library or fusion
- not_claimed: native benchmark data
- not_claimed: paper result

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_adapter.missing_returns: Fixed holdings re-accounted under zero and adverse-100 policies without reranking or reweighting.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [quantevolver](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/quantevolver/manifest.json)

### M057 — MadEvolve: Evolutionary Optimization of Trading Systems with Large Language Models

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The BTCUSD/Polygon OHLCV adapter, frozen market snapshot, alpha forecaster, trading-system implementation, and complete simulator/evaluator.
- monthly_jkp_assessment.required_but_missing: The five paper configurations, initial programs, random seeds, model routing probabilities, prompts, requests/responses, candidates, lineages, and run reports.
- monthly_jkp_assessment.required_but_missing: The best evolved strategy code, feature programs, 200-proposal Claude Code trees, successful candidates, and selection traces.
- monthly_jkp_assessment.required_but_missing: The two 120-trial Optuna studies, trial tables, parameters, objective arrays, and chosen settings.
- monthly_jkp_assessment.required_but_missing: Orders, fills, inventory, fees, market-impact states, holdings, returns, baselines, table arrays, and plot arrays.

Availability: Current public default head is already documented; availability does not resolve the recorded original-input/result gaps. Other branches/forks were not refreshed.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [madevolve_trading](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/madevolve_trading/manifest.json)

### M058 — Macro Economists in the Machine: A Multi-Agent LLM Framework for Commodity-Related ETF Portfolio Construction

Historical native audit executes paper-derived equation components with 18 mechanics checks and four ambiguous operations. No author-native empirical table/figure output was regenerated.

Remaining native requirements:

- Recover the original weekly Yahoo/FRED panel, dates, cached LLM contracts/requests, model revision and portfolio paths.
- Resolve ambiguous regime probabilities, caps/projection ordering, risk ranges and JSON contract, plus table/figure inconsistencies.
- Recover original costs/turnover and bootstrap seeds/draws/result-generation lineage; paper-derived equation checks alone are partial.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The processed weekly Yahoo/FRED panel with exact dates, adjusted-price and calendar rules, vintages, release alignment, and macro/narrative inputs.
- monthly_jkp_assessment.required_but_missing: The dated gpt-4o-mini snapshot, complete common/role/dynamic prompts, required JSON schema, request settings, retries, and cached model contracts.
- monthly_jkp_assessment.required_but_missing: The generated narratives, agent probabilities/tilts/confidences, debate messages, revisions, terminations, and validation records.
- monthly_jkp_assessment.required_but_missing: The cyclical ETF set, regime-probability constants/ordering, risk-cap values, and unique ordering/projection algorithm for cyclical, name, and turnover constraints.
- monthly_jkp_assessment.required_but_missing: Portfolio weights, trades, turnovers, returns, NAVs, bootstrap implementation/seed/draws, figure arrays, and result generator.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Reassess on the original task and input universe; common-monthly/JKP exclusion does not settle native replication.

Evidence: [macro_economists_machine](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/macro_economists_machine/manifest.json)

### M059 — AlphaMemo: Structured Search-Process Memory for Self-Evolving Alpha Mining Agents

Historical native audit: not_reproduced_native_current_data_pipeline_component_only

Remaining native requirements:

- not_claimed: AlphaMemo search-process memory
- not_claimed: paper search trajectory or admitted pool
- not_claimed: source-confirmed factor sign
- not_claimed: LightGBM factor fusion
- not_claimed: Top-k/drop portfolio
- not_claimed: paper CSI500 or S&P500 data
- not_claimed: paper result

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_adapter.missing_returns: Fixed holdings re-accounted under zero and adverse-100 policies without reranking or reweighting.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [alphamemo](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alphamemo/manifest.json)

### M060 — MetaPS: Adaptive Programmatic Strategy Selection for Market Agents

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The immutable six-asset price/news/order-flow panel, strategy registry helpers/metadata, ranking coefficients and priors, and complete simulator rewards.
- monthly_jkp_assessment.required_but_missing: All 528 records per V1/V2/V3 view, labels, sample weights, rationales, split lineage, teacher model requests/responses, and validation records.
- monthly_jkp_assessment.required_but_missing: Fine-tuning hyperparameters, exact Qwen revisions, adapters/checkpoints, decoding settings, seeds, predictions, and parser logs.
- monthly_jkp_assessment.required_but_missing: Mappings from eight raw size modes to four exposure buckets, transaction costs/slippage, position limits, invalid-action behavior, orders, and fills.
- monthly_jkp_assessment.required_but_missing: Portfolio paths, daily returns, sandbox transitions/rewards/actions, random runs, table arrays, figure arrays, and result generator.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [metaps](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/metaps/manifest.json)

### M061 — AI Trading's Alpha Singularity: Emergent Market Reasoning through Agent-to-Agent Self-Evolution

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The dynamic CSI1000/RiceQuant snapshot, memberships, OHLCV/VWAP, trading masks, and immutable date arrays.
- monthly_jkp_assessment.required_but_missing: All role prompts, nine-client model snapshots and calls, skill stores, per-round registries, rejected trials, and promotion histories.
- monthly_jkp_assessment.required_but_missing: The 94 AlphaGen programs, their scores and factor panels, source-selected top-30 pool, signs, and combination records.
- monthly_jkp_assessment.required_but_missing: PPO environments, 15,000-step trajectories, checkpoints, policy actions, and relay state.
- monthly_jkp_assessment.required_but_missing: Backtester, weights, orders, fills, daily returns, baseline outputs, full seeds, table arrays, figure arrays, and result generator.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [agora](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/agora/manifest.json)

### M062 — XALPHA: A Memory-Driven AI Quant Researcher for Hypothesis-to-Code Alpha Discovery

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- not_claimed: XALPHA memory routing
- not_claimed: hypothesis generation or factor evolution
- not_claimed: complete selected factor library
- not_claimed: Ridge fusion
- not_claimed: Qlib Top-50/drop-5 execution
- not_claimed: native CSI300 data
- not_claimed: paper result

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_adapter.missing_returns: Fixed holdings re-accounted under zero and adverse-100 policies without reranking or reweighting.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [xalpha](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/xalpha/manifest.json)

### M063 — Fin-Analyst at FinMMEval 2026 Task 3: A Live Hybrid Trading Agent with LLM Specialists and Rule-Based Signals

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: Immutable gpt-4o-mini model/API state, requests/responses, cache, images, dependency lock, and full paper-time specialist outputs.
- monthly_jkp_assessment.required_but_missing: A causal security-level policy or dated recommendation panel beyond the two native TSLA/BTC assets.
- monthly_jkp_assessment.required_but_missing: Random and Momentum baseline generators, seeds, action paths, and the missing agent/ablation result lineages.
- monthly_jkp_assessment.required_but_missing: A consistent single declared-period price snapshot; the printed deterministic rows require asset-specific endpoints that contradict the paper's common May-10 endpoint.
- monthly_jkp_assessment.required_but_missing: A cross-sectional portfolio or mapping from the single-asset vote to monthly U.S. stocks, including formation-time inputs and weights.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence. Author-space metadata was fetched separately; organizer data and benchmark examples do not certify the author LLM trajectory.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [fin_analyst](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/fin_analyst/manifest.json)

### M064 — AlphaSchema: Exploring the Space of Trading Semantics for LLM-Based Alpha Mining

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- not_claimed: AlphaSchema semantic search
- not_claimed: LLM code generation/repair
- not_claimed: reward-model exploitation or mutation
- not_claimed: 120/150-factor pools
- not_claimed: LightGBM combination
- not_claimed: Qlib Top-50/drop-5 strategy
- not_claimed: paper result

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_adapter.missing_returns: Fixed holdings re-accounted under zero and adverse-100 policies without reranking or reweighting.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [alphaschema](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alphaschema/manifest.json)

### M065 — FactorMAD: A Multi-Agent Debate Framework Based on Large Language Models for Interpretable Stock Alpha Factor Mining

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The initial factor library, debate examples, p_seed, acceptance thresholds, comparison factors, sampling policy, seeds, and all prompts/responses.
- monthly_jkp_assessment.required_but_missing: Every generated factor program, debate/correction trace, validator implementation, maximum retries, accepted 100-factor pools, and signs.
- monthly_jkp_assessment.required_but_missing: The 5,255-stock A-share snapshot, memberships, daily price/VWAP/amount/volume rows, provider, adjustments, and calendar.
- monthly_jkp_assessment.required_but_missing: LR/MLP/LightGBM hyperparameters, fitted models, predictions, baseline configurations, and trial records.
- monthly_jkp_assessment.required_but_missing: Overlapping Top-50 sleeve treatment, transaction-cost timing, holdings, returns, metric definitions, plot arrays, and result generator.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [factormad](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/factormad/manifest.json)

### M066 — AlphaAgentEvo: Evolution-Oriented Alpha Mining via Self-Evolving Agentic Reinforcement Learning

Historical native audit: see linked source/component and published-output inventories; no full original-paper certificate is established.

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: The listed supplementary ZIP containing the promised dataset and training/evaluation source; current immutable access is 404 and API access is 403.
- monthly_jkp_assessment.required_but_missing: AlphaEvo500/Alpha158 inputs, HS300/CSI500 point-in-time market data, exact splits, evaluator, parser, and backtest server.
- monthly_jkp_assessment.required_but_missing: Paper prompts, Qwen3 checkpoints, multi-turn trajectories, native tool calls, reward components, offspring factors, signs, and selected alpha pool.
- monthly_jkp_assessment.required_but_missing: Training environment, complete Verl/GRPO configuration, seeds, repeated runs, baselines, validation/test outputs, and result arrays.
- monthly_jkp_assessment.required_but_missing: Portfolio weighting, costs/slippage, holdings, returns, figure arrays, and result generator.

Availability: Exact-name public discovery completed; no new author-attributed implementation is verified by this search alone. Absence from search is not proof of nonexistence.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [alphaagentevo](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alphaagentevo/manifest.json)

### M067 — RAPTOR: Reasoned Agentic Portfolio Trading with Orchestrated Rebalancing

Historical native audit: full_author_history_and_166_output_snapshots_audited_36_of_42_scalar_units_checked_29_verified_18_author_output_3_current_public_8_paper_internal_5_conflicts_2_underspecified_6_unavailable_zero_end_to_end_result_cells_reproduced

Remaining native requirements:

- Complete the original-task target inventory and linked native audit requirements; transferred-task limitations alone do not settle native replication.

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_jkp_assessment.required_but_missing: Paper-time equity prices and benchmark, Finnhub, Reddit, SimFin, Perplexity, point-in-time memberships, and exact API requests/responses.
- monthly_jkp_assessment.required_but_missing: Full blackboard messages/tool calls, per-date security decisions beyond January 1, prompts/model state, seeds, and agent rerun records.
- monthly_jkp_assessment.required_but_missing: A consistent cadence and configuration: the paper and runners conflict on frequency, lookback, risk aversion, tau, universe, and view construction.
- monthly_jkp_assessment.required_but_missing: The missing stock_prices.csv required by the candidate backtest, transaction fee/slippage deductions, WAB trace, and complete result generator.
- monthly_jkp_assessment.required_but_missing: A transferable rule for producing monthly top-1,000 U.S. security views and weights over 1999-2024.

Availability: Current public default head is already documented; availability does not resolve the recorded original-input/result gaps. Other branches/forks were not refreshed.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [raptor](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/raptor/manifest.json)

### M068 — Alpha-GPT: Human-AI Interactive Alpha Mining for Quantitative Investment

Historical native audit: three_official_documents_rebuilt_and_lineage_audited_zero_native_alpha_gpt_results_alpha_gpt2_is_unevaluated_draft

Remaining native requirements:

- not_claimed: Alpha-GPT human interaction
- not_claimed: LLM alpha generation
- not_claimed: genetic-program search
- not_claimed: complete generated alpha set
- not_claimed: native market data/evaluator
- not_claimed: paper result

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_adapter.missing_returns: Fixed holdings re-accounted under zero and adverse-100 policies without reranking or reweighting.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [alpha_gpt_lineage](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/alpha_gpt_lineage/manifest.json)

### M069 — Automate Strategy Finding with LLM in Quant Investment

Historical native audit: not_reproduced_missing_integrated_native_output

Remaining native requirements:

- not_claimed: GPT-4o factor comparison
- not_claimed: complete 100-alpha SAF
- not_claimed: 12-alpha learned weights or combined IC
- not_claimed: DNN prediction
- not_claimed: top-13/drop-5 portfolio
- not_claimed: paper integrated return

Common-task transfer limitations (not prerequisites for original-task replication):

- monthly_adapter.missing_returns: Fixed holdings re-accounted under zero and adverse-100 policies without reranking or reweighting.

Availability: Historical source audit retained; this bounded refresh targets the 42 missing/underidentified entries.

Next: Resolve the listed native requirements and enumerate pending published outputs; define a bounded native protocol before any experiment.

Evidence: [automate_strategy_finding](https://ood-bouchet.ycrc.yale.edu/pun/sys/dashboard/files/fs//nfs/roberts/project/pi_jss233/zc362/alpha_evolve/paper_runs/paper_replication_audits/automate_strategy_finding/manifest.json)

