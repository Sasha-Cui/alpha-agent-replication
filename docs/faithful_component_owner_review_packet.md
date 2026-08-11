# Owner Review Packet: Primary Faithful-Component Census

**Prepared for:** Sasha Cui, decision owner named in D07
**Review state:** complete; Sasha Cui approved all three rows on 2026-08-11
**Scope:** the three counted QuantEvolver seed components only

This packet implements the independent owner-review step requested in PR #1 and
required by D07 of docs/current_project_execution_decisions.md. It deliberately
contains no empirical returns, alphas, p-values, or candidate ranking by
performance. The automated upstream conformance check is supporting evidence,
not a substitute for Sasha's review.

## Frozen source record

Review commit 4eb0e78842138ada5334349585b114ad923564e8 of
https://github.com/QuantLLM/QuantEvolver. Exact MIT-licensed snapshots are
checked in under tests/upstream_snapshots/quantevolver/:

| File | SHA-256 |
| --- | --- |
| examples/seed_candidates.yaml | c8a20de0850156b8c831547a58239bb88b5d6486da50d6f9ecbaa2df0d13d718 |
| quant_evolver/dsl/evaluator.py | 8c6e8201b8794bb2166a118cb753231bca1379c8aff115c6d29799ce8400516c |
| quant_evolver/evaluation/cross_sectional_rankic.py | b38066082453d58295e45467fad662b33c1a1ef97232d3575348e2cfade56295 |
| LICENSE | f8e25686c7e519aa7edac74d4f826d0f52ea711c0a8a3aafd0773b81ff7e6561 |

The source-defined census contains three evaluator-valid seeds. Its fourth row,
seed_0004 / bad_unknown_op, is deliberately invalid and is rejected by the
source evaluator; it is not an empirical candidate.

## Rows to adjudicate

| Candidate | Source seed | Exact released expression | Proposed strict grade |
| --- | --- | --- | --- |
| quantevolver_return_sharpe_60 | seed_0001 | div(ts_mean(returns(60)), ts_std(returns(60))) | B |
| quantevolver_price_zscore_reversal_120 | seed_0002 | neg(zscore(last(close(120)), close(120))) | B |
| quantevolver_return_log_volume_corr_60 | seed_0003 | corr(returns(60), log_arr(volume(60))) | B |

Grade B means a faithful disclosed component under explicitly disclosed,
mechanical task adaptations. It does not mean that the native agent, search
trajectory, reinforcement training, or a published performance table was
replicated.

## Five checks per row

1. **Source expression.** Compare the row above and PRIMARY_COMPONENTS in
   scripts/run_faithful_component_replications.py with the seed snapshot. They
   must match character-for-character.
2. **DSL semantics.** Check evaluate_released_seeds against the pinned
   evaluator.py: returns use the preceding close plus 10^-8, standard deviation
   uses population ddof=0, division adds the source stabilizers, z-score uses
   the last 120 closes, correlation uses 60 returns and 60 log-volumes, and
   warmup begins at zero-based bar 239.
3. **Input mapping.** Decide whether absolute CRSP prc is an acceptable monthly
   close and absolute tvol is an acceptable monthly volume for this
   disclosed-component adaptation. No other signal input is used.
4. **Evaluator.** Check released_cross_sectional_path against the pinned
   cross-sectional evaluator: pair score and forward return, drop missing
   pairs, require at least eight symbols, require finite Spearman rank IC, use
   q = max(1, floor(0.2n)), and subtract the equal-mean bottom quintile return
   from the equal-mean top quintile return.
5. **Mechanical changes only.** Confirm that the only changes are cadence
   (5-minute bars to monthly bars), universe (configured symbols to the
   top-1,000 U.S. equities), and holding horizon (six released bars to the next
   available monthly bar). Weights are unchanged and the counted evaluator
   return adds no transaction cost or imputation rule.

## Outcome-blind executable cross-check

Run:

    python scripts/check_upstream_conformance.py

This executes the exact pinned evaluator and cross-sectional source on a
deterministic 12-symbol, 275-bar synthetic OHLCV fixture. It compares 1,296
candidate-score values and 105 portfolio timestamps without reading market
outcomes. A mismatch in a snapshot hash, score, eligible timestamp, or
long-short return fails the check.

Then run:

    python scripts/validate_faithful_component_replications.py

The second command checks the strict A/B census, compact artifact hashes,
conformance evidence, and the separate review record.

## Attestation procedure

Edit paper_runs/faithful_component_replications/owner_review_attestation.csv
only after completing the five checks above.

For each row:

- enter reviewer exactly as Sasha Cui;
- enter an ISO date such as 2026-08-11;
- enter yes or no for every check;
- enter the independently assigned grade;
- set review_status to complete;
- explain every no, ambiguity, or non-B grade in notes.

The tracked attestation now records all five checks as yes and grade B for each
of the three rows. The validator reports the review as complete only when every
required field is consistent; a fabricated or malformed completion fails closed.
