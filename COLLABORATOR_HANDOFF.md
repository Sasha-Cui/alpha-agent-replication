# Collaborator Handoff

This repository is the working research record for the Alpha Agent Replication
project and its ICAIF 2026 submission. It is organized so a collaborator can
audit the claims immediately, reproduce the compact derived artifacts without
licensed inputs, and identify which full empirical runs require separately
authorized data.

## Read this first

The repository really does contain 50 implemented and backtested strategy
mappings covering 40 retained papers. Those 50 rows must not be described as
50 native-agent replications:

- 0 are end-to-end native-agent replications.
- 1 is a released-code component adaptation.
- 12 are source-grounded paper components.
- 37 are researcher-authored, in-spirit reconstructions.

All 50 have executable formulas, frozen candidate identifiers, realized
common-task returns in the controlled research run, and a matched four-rung
benchmark evaluation. The Git repository publishes the resulting aggregate
tables and diagnostics, not the licensed security-level inputs, factor-panel
time series, or monthly strategy-return matrices.

The fastest audit entry point is
[`paper_runs/handoff/strategy_result_index.csv`](paper_runs/handoff/strategy_result_index.csv).
It is a 50-row, 58-column join of paper identity, mapping provenance,
attribution limits, CAPM/FF3/FF5+momentum/JKP132 derived estimates, inference
flags, and closest-factor diagnostics. Its hashes and scope boundary are in
[`paper_runs/handoff/manifest.json`](paper_runs/handoff/manifest.json).

## Current empirical status

The matched benchmark ladder evaluates the same 50 strategies over the same
126 out-of-sample months, from 2011-08-31 through 2022-01-31, at a 10-basis-
point one-way cost. The count of positive alpha estimates falls from 44 under
CAPM to 41 under FF3, 41 under FF5 plus momentum, and 17 under the market plus
132 JKP characteristics. Holm-positive counts are 6, 1, 2, and 0,
respectively. Forty-seven of 50 strategies have an absolute correlation of at
least 0.50 with their closest JKP characteristic factor.

These are retrospective, conditional spanning diagnostics. The mappings were
not frozen before U.S. outcomes were inspected and were not independently
second-coded. They do not prove what an unavailable native agent would have
earned, nor do they establish that model pretraining caused factor
rediscovery.

The separate 14-attempt public-code audit reproduces zero native agents. One
released QuantEvolver seed supports a component adaptation; the other attempts
retain explicit output, adapter, task, or executability blockers. Blocked
attempts are evidence failures, not zero-return observations.

A source-benchmark audit covers all 40 mapped papers. Thirty-eight had verified
full PDF or HTML text: 37 had no identified asset-pricing spanning regression,
and one reported Carhart-four and FF5 loadings without the factor-adjusted
intercept. None used JKP132. Two papers remain unresolved because only partial
records were accessible. This coding is descriptive, was not outcome-blind,
and should receive independent citation-level review before stronger use.

## Canonical paper

There is one tracked compiled manuscript:

- `output/pdf/icaif2026_submission.pdf`
- SHA-256: `183443caa9f773e7aca10141c2c057b0efb98cda8a28b46fa1b1f041f98e76a4`

Its corresponding source is:

- `docs/paper/icaif2026_submission.tex`
- SHA-256: `7f88792a69c3be2e78306daaa4e457dacaed583c18c29b3710de8aa574ab9d03`

The exact designated artifact is not yet submission-ready under the stricter
validators merged from `origin/main`: it passes 65 of 71 format checks, and the
newer locked-evidence wording gate stops at its first mismatch. The six format
issues and replacement checklist are recorded in
[`docs/VALIDATION_STATUS.md`](docs/VALIDATION_STATUS.md). Do not silently
replace the canonical PDF or describe it as validator-clean.

The other tracked PDFs under `docs/paper/figures/` are figures, not alternate
paper versions. `report.md` and `docs/alpha_agent_replication_report.tex` are
research reports, not competing ICAIF submission versions.

The matched benchmark ladder is a later tracked empirical extension. It is
useful for the next paper iteration, but the canonical PDF remains the rigorous
public-artifact evidence audit identified above.

## Repository map

- `src/alpha_evolve/`: reusable portfolio, path-policy, JKP adapter, and
  performance-evaluation code.
- `scripts/`: research runners, frozen-audit builders, paper builders, and
  validators.
- `tests/`: unit and artifact-consistency tests.
- `literature_review/`: 98-work corpus records, queries, canonical metadata,
  links, and screening rules.
- `paper_runs/submission_evidence/`: frozen aggregate estimates, manifests,
  mapping ledgers, robustness outputs, failure forensics, and benchmark ladder.
- `paper_runs/handoff/`: compact collaborator-facing result index.
- `docs/paper/`: canonical TeX, bibliography, generated tables/macros, figures,
  and vendored ACM 2.19 template.
- `output/pdf/icaif2026_submission.pdf`: canonical eight-page PDF.
- `LICENSES/`: code, documentation, and third-party licensing boundaries.

See [`docs/EXPERIMENT_INDEX.md`](docs/EXPERIMENT_INDEX.md) for the experiment-
to-code map and [`docs/DATA_AND_ARTIFACTS.md`](docs/DATA_AND_ARTIFACTS.md) for
the tracked/excluded data boundary.

## First-hour setup

Use Python 3.9 or newer:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/build_collaborator_handoff.py
git diff --exit-code -- paper_runs/handoff
```

On Bouchet, the maintained environment is outside the checkout:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/current/alpha-evolve/bin/python -m pytest -q
```

Do not install packages into a project-local `.venv` symlink on Bouchet. Use
the central environment policy described in the project instructions.

## Reproduction levels

### Level A: audit the frozen evidence

No external data are needed. Review the handoff index, mapping audit, source-
anchor packet, direct-code inventory, benchmark summaries, manifests, tests,
paper source, and PDF. Rebuild the collaborator index with:

```bash
python scripts/build_collaborator_handoff.py
```

### Level B: rebuild publication assets

The paper tables and figures are generated from tracked frozen summaries:

```bash
python scripts/build_icaif2026_submission_assets.py
python scripts/build_icaif2026_submission.py
python scripts/validate_icaif_submission.py --pdf output/pdf/icaif2026_submission.pdf
```

The PDF build additionally requires TeX Live and Poppler-compatible PDF tools.

### Level C: rerun portfolio construction and benchmark estimation

This level requires separately authorized JKP security-level data and the
factor panel. Configure the `ALPHA_EVOLVE_*` paths documented in `README.md`.
The repository intentionally does not export those data. The full runners
write high-volume monthly matrices that remain ignored; their compact results
and manifests are the publication artifacts.

## Recommended continuation order

1. Obtain an independent, outcome-blind second coder for the 50 mappings and
   record disagreements rather than silently changing formulas.
2. Prioritize native-agent releases that include dated signals, positions, or
   returns; do not count a repository as a replication merely because it has
   source code.
3. Freeze a prospective or genuinely untouched holdout before any new mapping
   or factor-choice iteration.
4. Revalidate the international security-level inputs before making any G7
   performance claim; the current international extension is excluded after a
   plausibility failure.
5. Add borrow, financing, capacity, and nonlinear-impact evidence if the claim
   moves from statistical alpha toward implementable trading performance.
6. Update the canonical manuscript only after the evidence tables, generated
   macros, validators, and PDF all agree.

## Non-negotiable interpretation rules

- Never call the 50-row mapping set “50 replicated agents.”
- Never turn an unavailable or blocked agent into a zero return.
- Never attribute an in-spirit reconstruction's performance to the source
  agent.
- Keep native execution, component adaptation, source-grounded reconstruction,
  and narrative reconstruction as separate provenance fields.
- Keep licensed and third-party inputs outside Git; publish hashes, paths,
  schemas, aggregate results, and regeneration code instead.
- Treat all mapping-based inference as descriptive until a clean outcome-blind
  reconstruction and holdout exist.
