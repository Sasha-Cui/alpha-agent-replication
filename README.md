# Alpha Agent Replication

This repository studies whether published LLM investment methods deliver useful
performance on U.S. equities beyond **actual FF5 + momentum + JKP132**. It keeps
source-code audits, component experiments, transferred methods, and full-paper
reproduction claims separate.

**Verified November 17, 2026; paper provisional.** Both paper-based monthly implementations completed source execution and exact offline replay. EFS completed 12 of 12 declared economic paths. Screening completed 12 of 30 paths; the other 18, including the designated LLM-screening primary and its equal-weight control, remain blocked by unpriced held month-end assets. Overall study and paper closure remain unfinished.

## What we have done

- Reviewed 69 papers and retained each paper's separate evidence and gaps. At least 24 have some released code; four have native monthly investment experiments.
- Verified the actual 138-factor benchmark and recovered unmodified CRSP monthly data and opening prices.
- Implemented two bounded paper-based central methods: EFS and Agentic AI Screening. All five primary source variants completed exact offline replay.
- Completed EFS's 12 conditional economic paths and actual-factor analysis. Screening's primary comparison remains unavailable; its 12 completed secondary paths cannot replace it.

## Current EFS finding

At 10bp per-side portfolio-unit costs, LLM search versus matched grammar has paired actual 138-factor alpha **+0.177pp/year**, pointwise99% CI **[−2.426,+2.780]**, raw HAC p **0.861**. This bounded experiment does not establish incremental LLM value. It is not proof that all LLM investment methods lack alpha.

## What remains unfinished

- Resolve or explicitly bound screening's held-asset payoff/price gaps, then admit its designated primary and equal-weight control in a separately versioned account if feasible.
- Recover and verify essential historical inputs for MarketSenseAI 2.0 and Signal or Noise, or retain their explicit unavailable status.
- Reconcile the results, failures, sensitivity cases and uncertainty into the provisional paper. No full-paper or pristine-holdout claim is made.

## Start here

1. [Project briefing](docs/PROJECT_BRIEFING.md): what we wanted, what we did and what is still missing.
2. [Beamer presentation](docs/presentations/LLM_INVESTMENT_STUDY_20261117_beamer.pdf), [LaTeX source](docs/presentations/LLM_INVESTMENT_STUDY_20261117_beamer.tex), [slide text and notes](docs/presentations/LLM_INVESTMENT_STUDY_20261117.md), and [editable deck](https://chatgpt.com/space/page_8240054152248191a27a0ae77e9bb674).
3. [Current study](docs/CURRENT_STUDY.md) and [v2 aggregate evidence](paper_runs/native_monthly_implementation_v2_20261116/README.md).
4. [Technical handoff](docs/RESEARCH_HANDOFF.md): exact locations, completed jobs and remaining checks.
5. [Documentation index](docs/README.md) and [development guide](docs/DEVELOPMENT.md).

The [69-paper inventory](docs/study/method_readiness.csv) and [status snapshot](docs/study/status.json) separate source admission from financial admission. Only native monthly methods are eligible; monthly aggregation of daily/quarterly trading does not create eligibility. The dated v1 empty-cohort gate is historical and superseded by the paper-based v2 review.

## Repository map

- `src/alpha_evolve/`: reusable Python utilities for paths, data preparation,
  portfolio construction, and evaluation.
- [`scripts/`](scripts/README.md): entry points grouped by purpose. Many are
  historical research runners; read their protocol before execution.
- `tests/`: software and evidence-contract checks. A passing test suite is not
  an investment-performance result.
- `literature_review/`: paper records, bibliography, and source provenance.
- [`paper_runs/`](paper_runs/README.md): versioned studies and compact evidence.
  Some newer or licensed material exists only in the authorized Bouchet checkout.
- `docs/`: reader guides, protocols, and historical manuscript sources.
- `environment_specs/` and [`environment.toml`](environment.toml): runtime
  specifications; installed environments live outside the checkout.
- `artifacts/`, `runs/`, `archives/`, `relocated_scratch/`, `slurm/`,
  `log/`, and `mlruns/`: private or generated local holdings, not a public
  distribution of research inputs.

Existing run paths are retained because manifests and source bindings refer to
them. The directory structure is a research record, not an invitation to execute
every runner.

## Check the reader documentation

From the repository root, with Python 3.9 or newer:

```bash
python scripts/check_repository_docs.py
```

This checks local navigation and the published readiness snapshot without
accessing WRDS, making model calls, rebuilding a manuscript, or rerunning a
study. See [development](docs/DEVELOPMENT.md) for package setup and the older
submission-validation workflow.

## Historical material

The [historical study index](paper_runs/README.md#historical-studies) explains the
scope of earlier audits, reconstructions, native runs, and manuscripts.
Statements such as “current” or “complete” inside a dated historical package
apply to that package and its stated scope.

The [previous root README](docs/history/README_before_20261116_cleanup.md) is
preserved for provenance. It is not the current project-status page.

## Data access and licensing

Licensed security-level data, holdings, private model responses, and accounting
stores are not public repository inputs. Authorized readers can follow the
Bouchet evidence links in the current-study guide. A source checkout alone
does not reproduce an input-dependent experiment.

Original software is Apache-2.0; original documentation and manuscript material
are CC BY 4.0. Third-party code, papers, and data retain their own terms. See
[the licensing map](LICENSES/README.md), [contribution guide](CONTRIBUTING.md),
and [security policy](SECURITY.md).
