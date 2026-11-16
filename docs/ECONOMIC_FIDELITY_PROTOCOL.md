# Economic fidelity repair

The September 6, 2026 user instruction activates the publication improvements
sequentially, beginning with economic fidelity and permitting metered OpenRouter
calls. PR #1 (`audit.md`, merged August 11) is the independent audit underlying
this repair. Existing strict and in-spirit studies remain frozen.

## Stage order

1. Economic fidelity: active. First executable pilot is EFS arXiv v1.
2. Matched agent/baseline comparisons: queued.
3. Economically meaningful effect bounds and power: queued.
4. Benchmark/inference calibration: queued.
5. Independent review and new evaluation separation: queued.
6. Controlled adaptation comparisons and manuscript synthesis: queued.

A completed pilot does not mean all six stages, the representative system cohort,
or an entire original paper has been reproduced. Do not advance a scientific
claim merely because software tests pass.

## First pilot: EFS v1

EFS is selected for its public system/user prompts, algorithm, daily close-only
inputs, explicit 50-ticker universe, and sparse long-only allocation. Selection
uses availability and economic mechanism, not its previous positive CAGR. V1 is
pinned separately from the materially revised v2. Implement the actual LLM
mutation/crossover-feedback loop, not a JKP factor-score substitute.

Preserve daily 30-observation factor inputs, the twelve disclosed seed families,
source-listed US50 names, weekly evolutionary feedback, factor normalization,
mean aggregation, and daily equal-weight top-m holdings. The paper conflicts on
m=5 versus m=10; fix m=10 from its main real-market table and disclose the choice.
Use current OpenRouter-served GPT-4.1, one of the named paper model families.
No text sent to the provider contains tickers, dates, or stock-level prices.

Unspecified choices must be fixed in the recipe before new returns: seed window
expansion, normalization, warmup, pool limits, validation/selection criteria,
retries, temperature, and numerical conventions. Store every proposed function,
its acceptance/rejection, source hash, request/response hash, and chronological
feedback cutoff. Reject code outside a restricted numerical function subset.

Execute on the existing licensed JKP daily stock panel. Map all fifty names by
security identity, explicitly disambiguating META and Berkshire class B. Use
split-adjusted close for price signals; do not insert prices before IPOs. Keep
price-return paper accounting separate from dividend-inclusive economic returns.
Formation never depends on next-period return availability. A held missing return
must fail the run rather than silently reweight holdings or manufacture returns.

The causal implementation observes a completed close, computes decisions, and
executes at the following close: a disclosed one-session execution delay. This
avoids assuming an LLM can observe a closing price and transact at that same
already-determined price. Record the signal, execution, and realization dates.
Monthly returns are compounded from the daily account, never substituted into
the factor lookbacks. Fees use traded notional including drift. Report paper
zero-cost and economic 10 bp one-way cases separately.

This is a fresh paper-guided implementation on an alternative daily data source,
not recovery of the author's unreleased code, generated pool, historical model,
three original search trajectories, or published performance. The paper's static
US50 universe was selected retrospectively and remains subject to survivorship
and selection concerns. Current-model replay of historical periods is not a
pristine holdout. Neither source conformance nor API execution proves absence of
model pretraining leakage. Human independent review remains pending.

## API accounting

Import all historical per-call journals by unique response ID. A run-final
in-memory counter is insufficient because resumed jobs may reset it. All new
calls share a durable project ledger with a $450 soft stop (below the existing
$500 hard limit), a $25 first-pilot cap, cached exact requests, and pessimistic
reservations retained after ambiguous failures. No credential is logged or
copied into the public package. No author contact, commits, pushes, or external
submission are part of this repair.

## First-pilot completion

The EFS v1 pilot now has 290 real generation steps, 535 admitted functions,
1,510 daily observations, independent accounting checks, and a complete cached
replay. All financial outputs match the live run byte for byte after a JSON-only
formation-index serialization repair. The 21 focused tests pass on both supported
Python versions. Results and metering have been promoted back to project storage.

Source review restored the m=25 non-sparse search heuristic and Recall@20, with
m=10 kept for actual trading. The pilot aggregates 60 completed outcomes for
feedback; the source pseudocode refers to recent performance records over a
search interval, so this numerical aggregation remains an explicit interpretation
for independent review. It must not be presented as uniquely source-specified.

An equal-weight reference was added after the pilot as a source-motivated
context check. It outperforms both active paths; no claim of incremental alpha
or confirmatory significance is licensed by this pilot. See the report and
outcome-free source-review packet. The broader point-1 cohort and points 2–6
remain open; human review is not fabricated or replaced by software tests.
