# Authorized Collaborator Bundle

The public repository does not redistribute monthly strategy or factor-return
matrices derived from separately licensed research data. Collaborators who are
independently authorized for every input can build a complete inspection
bundle outside Git with `scripts/build_authorized_collaborator_bundle.py`.
The authorization flag is an explicit safeguard, not a license grant.

## Contents

The builder selects exactly the 50 candidate IDs in
`paper_runs/handoff/strategy_result_index.csv` and writes:

- long monthly candidate paths with gross return, traded notional, 10-bp net
  return, eligibility, failure event/status fields, and candidate ID;
- wide gross-return, traded-notional, net-return, eligibility, and failure-event
  matrices for all 50 retained strategies;
- same-universe market and five primary characteristic-factor returns;
- the external market-plus-132-JKP return panel in the exact order used by the
  broad benchmark, excluding unrelated columns such as `newsfactor`;
- monthly factor-only fitted values, residuals, validation-selected ridge
  penalties, and raw-scale rolling factor loadings for all four rungs; and
- a JSON manifest containing input and output SHA-256 hashes, row/column
  inventories, factor order, both date clocks, sample dates, costs, rolling
  windows, ridge grids, software versions, and licensing terms.

Every monthly table uses explicit `formation_month` and/or
`realization_month` labels. The external broad panel records next-month returns
against its formation key; the analysis therefore sets
`realization_month = formation_month + one month-end`. Candidate net return is

\[
r^{\mathrm{net}}_{i,t}
= r^{\mathrm{gross}}_{i,t} - 0.001\,\mathrm{traded\_notional}_{i,t}.
\]

The rolling fits use 120 training months, reserve the final 24 months of each
window for penalty validation, and evaluate the next month. Loadings and fitted
values deliberately exclude the training-period intercept, matching the
published residual estimand.

## Prompt-replay performance bundle

The separate GuruAgents replay experiment writes a second, self-auditing
collaborator package under
`paper_runs/prompt_replay/guruagents/performance/`. It is distinct from the
50-strategy motif-proxy bundle above: the holdings come from 190 actual GPT-4o
prompt replays through OpenRouter, in archived-final and tool-routing modes,
rather than from a deterministic JKP formula. The package contains:

- 24 replay, 12 archived-author, and six JKP-proxy monthly return paths, with
  explicit formation and realization months, gross and 10-bp net returns,
  traded notional, cost, completeness, eligibility, and failure fields;
- formation holdings, parsing/correction audit fields, execution dates,
  rebalance-level traded notional, and turnover summaries;
- the same-universe Nasdaq market return, the official Fama--French and
  momentum panel, and the aligned market-plus-132-JKP formation and
  realization panels;
- 498 alpha-regression records covering same-universe CAPM, official CAPM,
  FF3, FF5 plus momentum, FF5 plus momentum plus JKP BAB, a seven-factor JKP
  low-risk block, the primary six JKP factors, compressed pre-2022 JKP, and an
  exploratory leave-one-month-out JKP132 ridge diagnostic;
- monthly factor fitted values and residuals, selected ridge penalties, static
  loadings, 107,730 monthly rolling loading records, and both aggregate and
  candidate-level attribution ladders; and
- a nine-sheet audit workbook plus a manifest with portable input locators,
  SHA-256 hashes, factor order, date clocks, sample restrictions, costs,
  software versions, and licensing cautions.

Run `scripts/evaluate_guruagents_prompt_replay_performance.py` to rebuild this
package from the authorized replay archive and factor inputs. The evaluator
does not publish host-specific absolute paths. Its manifest identifies external
inputs by basename and hash, and repository inputs by relative path.

## Build sequence

First regenerate the frozen candidate and same-universe factor matrices with
the authorized security-level input. Then run the retained benchmark ladder
against the exact external factor panel. Finally package those outputs:

```bash
python scripts/run_submission_evidence.py \
  --markets USA \
  --tag authorized_collaborator \
  --out-root /authorized/scratch/usa_monthly_matrices

python scripts/run_retained_benchmark_ladder.py \
  --factor-panel /authorized/path/benchmark_factor_panel.csv \
  --usa-results /authorized/scratch/usa_monthly_matrices/authorized_collaborator \
  --output-dir /authorized/scratch/retained_benchmark_ladder

python scripts/build_authorized_collaborator_bundle.py \
  --candidate-monthly /authorized/scratch/usa_monthly_matrices/authorized_collaborator/candidate_monthly_USA.csv \
  --primary-factor-monthly /authorized/scratch/usa_monthly_matrices/authorized_collaborator/factor_monthly_USA.csv \
  --broad-factor-panel /authorized/path/benchmark_factor_panel.csv \
  --reconstruction-dir /authorized/scratch/retained_benchmark_ladder \
  --output-dir /authorized/scratch/alpha_agent_collaborator_bundle \
  --authorized-data-use-acknowledged
```

The builder refuses to overwrite an existing output. It creates both a bundle
directory and a `.tar.gz` archive with a sibling SHA-256 file. Keep all three
outside the public checkout and transfer them only through an approved channel.

## Licensing boundary

The bundle contains aggregate strategy and factor-return paths, not
security-level observations. Even so, underlying JKP, market-data,
institutional, and third-party terms continue to apply. Neither the repository
license nor possession of the bundle authorizes redistribution. Each recipient
must confirm independent authorization with the data owner or institution.
The GuruAgents package likewise contains derived audit outputs only; raw source
data and third-party prompts remain subject to their original terms.
