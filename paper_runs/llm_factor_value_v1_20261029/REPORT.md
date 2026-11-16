# Incremental LLM factor value: design and feasibility

**Decision: do not launch the proposed economic/search experiment on the current evidence design.** The 80% precision target fails under both frozen planning references at historical noise levels. This decision spends $0 on models and preserves every earlier study. It concerns this design and endpoint; it is not a conclusion that LLMs have no alpha or that every possible design is infeasible.

The user-approved pivot is now a separately versioned research question: does an LLM proposal engine improve economic performance beyond a credible adaptive non-LLM search, under one evaluator? Broad replication remains a closed bounded attempt with its previously recorded gaps, not a completed faithful reproduction of 69 papers.

## Precision gate

The +2-pp/year boundary is evaluated using a 99% interval. To rule out a worthwhile gain when the true increment is zero, or establish one when the true increment is +4 pp, the estimate must resolve a 2-pp separation from the boundary with 80% probability. The table reports the separation required for 80% power. The old report's approximate t+z MDE is not substituted for this new exact conditional noncentral-t calculation.



| Historical noise reference | Normal reference MDE (pp/year) | Four-block MDE (pp/year) |
| --- | ---: | ---: |
| GPT-4.1 proxy | **12.63** | 27.50 |
| DeepSeek proxy | **35.65** | 77.63 |

Lower detectable separation is better for precision; bold is the lower numerical value within each row. The normal calculation assumes known standard error and is an optimistic reference, not an inference-method recommendation. Four-block power assumes independent normal block estimates. These assumptions are not established for a future financial process. [Full power grid](visual_tables/power_grid.csv).

## How much design improvement would be required?



| Historical noise reference | Normal reference power | Four-block power |
| --- | ---: | ---: |
| GPT-4.1 proxy | **2.09%** | 1.25% |
| DeepSeek proxy | **0.86%** | 0.70% |

Higher power is better; bold marks the larger numerical value in each row. These are probabilities under planning models, not observed strategy success rates. At 72 months, the standard error must be at most 0.585 pp/year under the normal reference or 0.269 pp/year under the four-group reference. The historical GPT-4.1 proxy has SE 3.696 pp/year; the DeepSeek proxy has SE 10.433 pp/year. [Baseline numbers](visual_tables/baseline_power.csv), [all scenarios](visual_tables/power_grid.csv).

## Candidate design

[EXPERIMENT_DESIGN.md](EXPERIMENT_DESIGN.md) fixes the proposed mechanism comparison and names the execution gates. One initial bank/operator grammar, one adaptive selection/evaluator/allocator, and equal candidate-evaluation opportunities isolate the proposal engine. Dollars, wall time and evaluations are measured separately. Ten paired seeds are proposed to measure search variation, never ten independent market histories. Historical differences in pool size/search budgets do not themselves identify an LLM causal effect.

The primary endpoint is incremental net performance, not unrestricted risk-adjusted alpha. A separately pinned low-dimensional factor model and adequate precision would be required for an alpha claim. Shrinking the active difference just to pass a precision gate would change the economic question. Replacing the primary return endpoint with IC/productivity after this failure is not allowed.

## Validation and limitations

The independent-normal four-group calculation is checked against 50,000 simulations per reference and effect point. Monthly Gaussian, AR(0.3), t5 and variance-shift stress cases are retained with their actual coverage and classification rates. They illustrate conditional behavior and cannot validate all dependent market processes. [Simulation audit](visual_tables/simulation_diagnostics.csv).

No model weights, factor searches, fits, backtests, source/replay/proof helpers or old economic-analysis drivers ran. Three copied aggregate-return files have identical complete 1,510-session calendars and finite primary cost columns. The published four-group standard errors supply the planning noise scale; a new return mean is not credited as an independent result. The protected files and canonical spending ledger are unchanged. More seeds may reduce search randomness, but they do not remove common market-path uncertainty.

All inspected 2019-2024 history is development-only. An actually unused confirmation period, point-in-time universe/data and model-knowledge assessment remain unestablished. Even a prospective period sealed now would still need adequate duration/precision. Known survival, implementation and historical-model limitations cannot be fixed by renaming an old test window.

## Next action

Stop the new economic/search launch at this gate. A continuation must demonstrate a concrete change that can deliver adequate paired precision without trivially reducing exposure, or obtain genuinely new validation information. Assess that proposal in a new version before paying for another search. No alpha-null claim or automatic pivot to a different primary endpoint follows from this planning failure. Implementation/productivity can be studied as an explicitly separate question if the user chooses that scope.

## Lineage and budget

The [feasibility protocol](feasibility_protocol.json) records the analytic preview already seen before the full simulations; this is not retroactively called a pre-outcome preregistration. The [decision receipt](feasibility_decision.json) binds the actual no-go decision. Inputs and helper hashes are recorded privately beside the saved protocol and calculation checks. Current project commitment remains $371.06592557, including uncertainty, below the exclusive $1,000 authorization. This phase has a $0 model-execution cap; old runtime and study caps remain unchanged.

Method sources: [SciPy noncentral t](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.nct.html), [Ibragimov-Mueller grouped inference](https://doi.org/10.1198/jbes.2009.08046), [multiple testing in factor research](https://www.nber.org/papers/w20592.pdf).

## Artifact index and reproduction

- `EXPERIMENT_DESIGN.md`: proposed controlled comparison and execution conditions.
- `feasibility_protocol.json`: fixed full-grid/simulation plan and inspected preview disclosure.
- `feasibility_decision.json`: actual statistical/data/launch status.
- `visual_tables/`: complete conditional power and simulation tables.
- `visual_figures/`: precision and noise tradeoff figures.

All work is remote in the existing JSS checkout. The builder is `artifacts/llm_factor_value_v1_20261029/build_feasibility.py` with the central `environments/bin/alpha-evolve-python` wrapper. It refuses existing start evidence; do not rerun into completed output. To reproduce later, preserve this version, create a new version with the same bound input copies/protocol and an explicitly recorded amendment, and execute only the new planning builder. Original scientific and archive helpers remain frozen.
