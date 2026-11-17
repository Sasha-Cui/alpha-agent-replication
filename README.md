# Alpha Agent Replication

This repository studies whether published LLM investment methods deliver useful
performance on U.S. equities beyond **actual FF5 + momentum + JKP132**. It keeps
source-code audits, component experiments, transferred methods, and full-paper
reproduction claims separate.

**Status on November 16, 2026: provisional.** The actual 138-factor benchmark is
verified. Native-monthly scope and the admission/U.S.contract are fixed.
The current executable cohort is empty after source admission, so financial
evaluation is blocked and the investment study is not complete. Earlier manuscripts
and completed studies remain historical evidence.

## Start here

1. [Current study](docs/CURRENT_STUDY.md): the research question, completed work,
   remaining decisions, and evidence locations.
2. [Collaborator handoff](COLLABORATOR_HANDOFF.md): a short route from a paper
   record to its implementation, input checks, and results.
3. [Documentation index](docs/README.md): current guides and dated historical
   studies.
4. [Development guide](docs/DEVELOPMENT.md): environments and checks that do not
   launch experiments.

The [69-paper mechanism inventory](docs/study/method_readiness.csv) is a dated
readiness record, not a list of 69 runnable strategies. Its
[status snapshot](docs/study/status.json) records provenance and the distinction
between executed mechanisms and methods admitted to a monthly evaluation.

## Current claim boundaries

- A repository link, prompt collection, scoring script, or web demonstration is
  not automatically an executable investment method.
- A working source mechanism is not automatically a financially valid result.
  Inputs, trading clocks, funding, costs, and corporate actions need separate
  checks.
- Only paper-native monthly investment experiments are eligible. Daily, weekly,
  and quarterly methods are excluded; monthly inputs or charts do not make a
  strategy eligible. The scope is settled.
- The benchmark uses the five actual French factors, actual momentum, and the
  fixed 132 actual JKP factor-return series. RF is separate. Characteristic
  proxies and reduced factor models do not replace that benchmark.
- Inconclusive evidence is not proof of no alpha. No full-paper reproduction or
  external human review is asserted by the current readiness inventory.

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
