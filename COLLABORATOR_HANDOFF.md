# Collaborator Handoff

This repository contains the research record for the Alpha Agent Replication
project and its ICAIF 2026 submission. It supports immediate claim auditing,
rebuilding compact public artifacts, and identifying runs that require
separately authorized data. Start from the current claim boundary in
[`docs/FIDELITY_AUDIT.md`](docs/FIDELITY_AUDIT.md).
The repository favors machine-readable evidence and deterministic checks over
narrative claims, so each headline number has a traceable artifact.

## Read this first

Begin with [`docs/FIDELITY_AUDIT.md`](docs/FIDELITY_AUDIT.md). It is the current
claim-boundary document for the strict legacy-mapping audit and the new
component evidence.

The prior 50 common-task mappings are not a canonical agent-replication set. The
strict object-level audit assigns A0/B0/C15/D33/U2. None is a faithful system
replication or faithful disclosed component. Their matched benchmark ladder is
retained only as a legacy construction diagnostic.

The current main evidence has two source-anchored layers: an exhaustive census
of the three evaluator-valid seeds in a pinned QuantEvolver release, which passes
3/3 strict grade B (100%); and a GuruAgents prompt-decision replay. The replay
executes all 190 disclosed prompt cells, constructs 24 costed paths, and reports
matched factor attribution for 12 long-archive paths over 33 common months.
The older 12-formula bundle is a mixed-fidelity diagnostic outside the primary
denominator. None of these components is a full native system or discovery pipeline.

Primary machine-readable evidence:

- `paper_runs/submission_evidence/strict_proxy_fidelity_audit/`: strict grades for the legacy 50 mappings.
- `paper_runs/faithful_component_replications/`: primary three-seed fidelity ledger and attribution outputs.
- `paper_runs/fidelity_formula_components/`: non-primary mixed-fidelity formula diagnostic.
- `paper_runs/prompt_replay/guruagents/performance/`: replay paths, holdings, costs, and factor attribution.

The native-fidelity ledger and cutoff-bounded artifact audit under
`paper_runs/submission_evidence/` provide broader repository and corpus context.
The historical `paper_runs/handoff/strategy_result_index.csv` is now only a
legacy ladder-construction diagnostic. Paper-level evidence routing remains in
[`docs/EVIDENCE_ROUTE_POLICY.md`](docs/EVIDENCE_ROUTE_POLICY.md) and the
replication-scope ledgers.

## Current empirical status

The strict audit, not the historical return ladder, determines the status of the
50 prior mappings: A0/B0/C15/D33/U2. None is a faithful system replication or
faithful disclosed component; 46 combine ranked JKP characteristics, 47 share
essentially the same monthly long-short construction, and at least 39 had a
closer public formula, prompt, algorithm, or execution rule. The ladder therefore
tests researcher-authored construction geometry only.

The primary formula study exhaustively implements the three evaluator-valid
example seeds at QuantEvolver commit
`4eb0e78842138ada5334349585b114ad923564e8`. It preserves each expression, the
released DSL numerics, pairwise score/forward-return deletion, next-available
close return, and equal-mean top/bottom-quintile portfolio. Only cadence,
universe, and holding horizon change. A fail-closed validator rejects conditional
grades, source-hash drift, imputation, or altered evaluator mechanics.

Each component has 305 observations (915 total) and the full evidence contains
184,596 formation holdings. Six holdings use a nonconsecutive next available bar,
as the released evaluator requires. Across CAPM, FF3, FF5 plus momentum, and the
broad JKP benchmark, median annualized residuals are +1.2250%, +0.2549%,
-0.4009%, and +0.6713%; Holm-positive counts are 0, 1, 0, and 0. Q2 is
Holm-positive only under FF3 (6.9508%, HAC t=2.6009, Holm p=0.0279); its broad
nominal result does not survive the three-component correction.

The separate 12-formula diagnostic retains five current-EFS renderings, the
three QuantEvolver seeds, three VWAP-independent Alpha-Jungle formulas, and
QuantAgent's normalized volatility-breakout rendering. Its grades are B3,
B-conditional5, and C-conditional4. The nine conditional rows, their imputed
returns, and their researcher-selected portfolio rules are excluded from the
100% primary denominator.

The GuruAgents study executes all 190 disclosed prompt cells and forms 24 costed
paths. For the 12 long-archive paths sharing 33 factor months, adding JKP BAB to
official FF5 plus momentum reduces median annualized alpha from 5.80% to 2.59%
and attenuates 11 paths; one Buffett path remains Holm-positive. The histories
are short, and this is a prompt-decision component replay rather than a native
system reconstruction.

The broader artifact and native-fidelity ledgers record public-evidence limits;
the 67-lineage native ledger has no shipped output compatible with the
prespecified monthly common task. Missing evidence is not encoded as zero return.

## Canonical paper

| Artifact | Role |
| --- | --- |
| [`docs/FIDELITY_AUDIT.md`](docs/FIDELITY_AUDIT.md) | Current claim and fidelity boundary |
| [`docs/paper/icaif2026_submission.tex`](docs/paper/icaif2026_submission.tex) | Canonical submission source |
| [`output/pdf/icaif2026_submission.pdf`](output/pdf/icaif2026_submission.pdf) | Current compiled submission artifact |

Do not copy a fixed page count or hash from this handoff. The submission
validation commands regenerate or check the current source/PDF artifacts,
hashes, and page count; rerun them after the final build and consult
[`docs/VALIDATION_STATUS.md`](docs/VALIDATION_STATUS.md). PDFs under
`docs/paper/figures/` are figures; reports marked SUPERSEDED / INVALIDATED are
provenance, not alternate submissions. The legacy matched ladder is the final
construction-diagnostic section; the faithful three-seed formula census and
GuruAgents replay are the current main empirical evidence.

## Repository map

- `src/alpha_evolve/`: reusable portfolio and evaluation code.
- `scripts/`: runners, builders, and validators.
- `tests/`: unit and artifact-consistency tests.
- `literature_review/`: 98-work corpus, metadata, and screening rules.
- `paper_runs/submission_evidence/`: strict proxy, artifact, native-fidelity, scope, and robustness evidence.
- `paper_runs/faithful_component_replications/`: primary faithful-component census.
- `paper_runs/fidelity_formula_components/`: non-primary mixed-fidelity formula diagnostic.
- `paper_runs/prompt_replay/guruagents/performance/`: GuruAgents replay performance and attribution study.
- `paper_runs/handoff/`: legacy ladder-construction index.
- `docs/FIDELITY_AUDIT.md`: current claim and fidelity boundary.
- `docs/paper/`: canonical source, tables, figures, and ACM template.
- `output/pdf/icaif2026_submission.pdf`: canonical compiled paper.
- `LICENSES/`: publication and third-party boundaries.

See [`docs/EXPERIMENT_INDEX.md`](docs/EXPERIMENT_INDEX.md) and
[`docs/DATA_AND_ARTIFACTS.md`](docs/DATA_AND_ARTIFACTS.md).

## First-hour setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/validate_submission_package.py
```

On Bouchet, use the central environment rather than installing into a local
`.venv` symlink:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/current/alpha-evolve/bin/python -m pytest -q
```

## Reproduction levels

### Level A: audit frozen evidence

No external data are required. Review `docs/FIDELITY_AUDIT.md`, the strict
legacy-mapping audit, the formula-component and GuruAgents replay packages,
supporting artifact/native ledgers, tests, paper source, and PDF. Rebuild the
legacy handoff index only when specifically auditing the old construction ladder.

### Level B: rebuild publication assets

Validate tracked summaries and the prebuilt PDF with:

```bash
python scripts/validate_submission_package.py
```

For an explicit release build:

```bash
python scripts/build_icaif2026_submission_assets.py
python scripts/build_icaif2026_submission.py
python scripts/validate_icaif_submission.py \
  --pdf output/pdf/icaif2026_submission.pdf \
  --log docs/paper/icaif2026_submission.log \
  --bbl docs/paper/icaif2026_submission.bbl \
  --require-build-log
```

Compilation requires TeX Live and Poppler-compatible tools.

### Level C: rerun empirical estimation

This requires authorized JKP security-level data and the factor panel. Configure
the `ALPHA_EVOLVE_*` paths in `README.md`. Full runners write ignored monthly
matrices; compact results and manifests are the publication artifacts. The
repository intentionally does not export the licensed inputs.

For collaborators independently authorized to use those inputs,
[`docs/AUTHORIZED_COLLABORATOR_BUNDLE.md`](docs/AUTHORIZED_COLLABORATOR_BUNDLE.md)
documents the license-gated builder for the 50 monthly candidate paths, both
factor panels, fitted values, residuals, monthly ridge choices, rolling
loadings, and a hash-pinned manifest. The generated directory and archive must
remain outside Git and travel only through an approved transfer channel.
