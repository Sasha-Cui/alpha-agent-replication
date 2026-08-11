# Current Fidelity Audit

This is the current claim boundary for the Alpha Agent Replication project. It
supersedes the historical proxy framing preserved in `report.md`,
`docs/alpha_agent_replication_report.tex`, and `docs/SCIENTIFIC_AUDIT.md`.

## Bottom line

A strict formula-level review of the 50 legacy common-task mappings finds no
faithful system replication and no faithful disclosed component:

| Grade | Empirical object | Count | Allowed use |
| --- | --- | ---: | --- |
| A | Faithful paper/system replication | 0 | Paper/system performance |
| B | Faithful disclosed component | 0 | Component performance only |
| C | Recognizable idea, materially changed | 15 | Theme-level sensitivity only |
| D | Materially inconsistent with source | 33 | Construction diagnostic only |
| U | Source unavailable | 2 | No source-specific inference |

Of these mappings, 46 combine ranked JKP characteristics and 47 use essentially
the same monthly portfolio construction. Their attenuation under JKP132 is
therefore evidence about researcher-authored JKP-like constructions, not about
the source papers' native agents. The row-level audit and hash-pinned manifest
are in `paper_runs/submission_evidence/strict_proxy_fidelity_audit/`.

## Primary counted replication sample: 3/3 strict B

The primary sample is an exhaustive census of the three evaluator-valid seeds
in QuantEvolver's released `examples/seed_candidates.yaml` at pinned commit
`4eb0e78842138ada5334349585b114ad923564e8`. The fourth example is explicitly
named `bad_unknown_op` and is rejected by the source evaluator, so it is not an
empirical candidate. Selection is source-defined and does not use return outcomes.

Each counted row preserves the released expression, executable DSL numerics,
240-bar warmup, pairwise score/forward-return `dropna`, next-bar close return,
floor-20% top/bottom legs, and equal-mean long-minus-short rule. The permitted
mechanical changes are cadence (released bars to monthly bars), universe
(configured symbols to top-1000 U.S. equities), and horizon (released six bars to
the next available monthly bar). The counted path adds no researcher cost or
imputation rule. Six of 184,596 selected holding observations use a nonconsecutive
next available monthly bar because the licensed panel has a gap.

The fail-closed validator checks source commit and file hashes, the exhaustive
candidate set, exact expressions, A/B-only grades, source-rule identifiers, leg
sizes, costs, output hashes, and (when access-gated holdings are present) exact
return reconstruction. It reports **3/3 strict grade B, or 100%**. This is 100%
faithfulness for the counted disclosed components only—not a claim that any
native agent, search trajectory, reinforcement training run, or paper performance
table has been replicated. Evidence is in
`paper_runs/faithful_component_replications/`.

Across the 150 matched evaluation months, median annualized alpha for these three
components is +1.2250% under CAPM, +0.2549% under FF3, -0.4009% under FF5 plus
momentum, and +0.6713% under FF5-plus-momentum-plus-JKP132. Holm-positive counts
are 0, 1, 0, and 0, respectively.

## Supporting component evidence

The revision uses two separate component studies.

### Mixed-fidelity formula diagnostic

The non-primary monthly diagnostic implements 12 source-anchored components through
compact normalized renderings and declared conventions:

- five current EFS v2 Table VI expressions, including executed monthly
  cross-sectional `cs_zscore`/`cs_rank` roots under declared numerics because
  the paper does not pin every specialized operator's semantics;
- three released QuantEvolver seeds using its public evaluator semantics and
  top/bottom-quintile equal-mean rule;
- Alpha-Jungle Table 7 formulas 4--6, which do not require unavailable VWAP;
- QuantAgent's printed ATR14 breakout in a normalized rendering, retaining its
  double-lag `pre_close.shift(1)` ambiguity.

Frequency and universe change to monthly U.S. data. EFS uses a disclosed
long-only top-m form with researcher-set m=10; Alpha-Jungle's raw formulas are
evaluated without its downstream learned model; QuantAgent uses a
researcher-supplied long-only portfolio of up to ten strictly positive signals
and holds cash when none qualify. These are formula-component tests, never
discovery-pipeline, trained-model, or native-agent replications. The executable
runner, fidelity ledger, holdings, return paths, attribution results, and
manifest are under `paper_runs/fidelity_formula_components/`.

Formation names and weights are fixed ex ante from the full scored universe.
If either a selected holding's one-month-ahead excess or total return is missing
or nonconsecutive, both are imputed to the contemporaneous mean among observed
holdings in the same leg on their common excess-and-total-return mask. Full
ex-ante weights remain in gross return, NAV drift, turnover, and cost
calculations; there is no reranking, substitution, weight change, or zero-return
imputation. A candidate-month would be omitted if an entire required leg had no
observed holding, but the manifest records zero such nonterminal omissions. The
terminal formation month is excluded because it has no consecutive realization
month.

The tracked bundle contains 305 path months per component from August 1999
through December 2024 and 3,660 candidate-month rows. It imputes 1,782 holdings
across 1,040 candidate-months; 2,620 candidate-months need no imputation, and
aggregate imputed absolute target weight is 46.4566. Because every leg is equal
weighted, gross returns equal those from observed-leg renormalization, but full
weights change coherent NAV drift, turnover, costs, and net paths. QuantEvolver
Q1, Q2, and Q3 have only 92, 98, and 36 complete-case months, respectively. The
same-leg mean can be optimistic when missingness reflects nonrandom disappearance
or delisting. Attribution is an analytical component diagnostic, not observed
implementable source performance.

Across the 150 matched evaluation months, median annualized alpha is +0.8783%
under CAPM, -1.1259% under FF3, -0.5932% under FF5 plus momentum, and +0.9777%
under FF5-plus-momentum-plus-JKP132. Positive-alpha counts are 7, 4, 5, and 9;
Holm-positive counts are 1, 0, 0, and 0. The sole familywise-positive estimate
is the conditional EFS regime-switched row under CAPM (7.4402%, HAC t=2.9028,
Holm p=0.0444); it is not Holm-positive under the other benchmarks. Thus the
source-anchored formula layer does not reproduce the legacy proxy layer's
monotonic JKP-absorption pattern. Holm correction is across 12 formulas
separately within each benchmark and not across benchmark specifications.
These 12 mixed-fidelity rows are not included in the 100% primary denominator.

### GuruAgents prompt-decision replay

The GuruAgents study replays all 190 disclosed prompt cells through a current
OpenRouter-served `openai/gpt-4o` endpoint at temperature zero, using archived
deterministic tool observations and a compiled Nasdaq source universe. It
produces 24 costed paths. This is a 2026 current-endpoint replay of the disclosed
prompt-decision component, not an end-to-end reproduction of source data
engineering or the original model snapshot/provider.

For the 12 paths with 33 common factor months, adding JKP
betting-against-beta to official FF5 plus momentum reduces median annualized
alpha from 5.80% to 2.59% and attenuates 11 paths. One path remains
Holm-positive when correction is performed across 12 paths within that
benchmark. There is no multiplicity adjustment across benchmark
specifications, and unrestricted JKP132 OLS is unidentified with 33 months.

The complete replay evidence is under
`paper_runs/prompt_replay/guruagents/performance/`.

## Reproduce the tracked audits

From the canonical Bouchet checkout:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python \
  scripts/run_faithful_component_replications.py --verify-upstream

/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python \
  scripts/validate_faithful_component_replications.py --require-full-evidence --verify-upstream

/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python \
  scripts/build_strict_proxy_fidelity_audit.py

/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python \
  scripts/run_fidelity_formula_components.py

/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python \
  scripts/analyze_fidelity_formula_components.py
```

The current paper is `docs/paper/icaif2026_submission.tex`. Its build and
release validators fail closed on the strict grade distribution, component
counts, evidence boundaries, anonymity, page limit, bibliography, and rendered
claims.

