# Development and validation

This repository combines reusable software with versioned research evidence.
Choose a validation scope before running a command.

## Documentation only

Python 3.9 or newer is sufficient:

```bash
python scripts/check_repository_docs.py
```

The check uses the standard library. It checks current relative links and the
compact readiness snapshot, without network access, model calls, WRDS,
financial recomputation, manuscript rebuilding, or archive extraction.

## Existing Bouchet checkout

Work in the canonical physical checkout:

```text
/nfs/roberts/project/pi_jss233/zc362/alpha_evolve
```

Refresh the development target with `~/bin/update-bouchet-dev`, then connect
with strict host-key checking and SSH multiplexing disabled. Keep SSH usage
sparse. See [operating instructions](../AGENTS.md).

Use existing central environments and source-specific wrappers. The
[environment manifest](../environment.toml) and
[storage guide](STORAGE_LAYOUT_20260925.md) explain retained BTK aliases and
JSS physical locations. Do not install through a project-local environment
alias or mutate a central environment.

## Isolated setup outside Bouchet

For a separately authorized development machine, use an environment outside
the checkout. The hash-pinned lock is the tested package dependency set:

```bash
python -m venv /path/to/isolated-environment
. /path/to/isolated-environment/bin/activate
python -m pip install --require-hashes -r requirements-lock.txt
python -m pip install --no-deps -e .
```

This installs the reusable package, not every third-party paper environment.
It does not acquire licensed inputs or authorize model calls. The cleanup
does not perform these installation commands.

## Software and historical artifact checks

Use focused tests for changed code and lint only the relevant files during a
small maintenance pass:

```bash
python -m ruff check scripts/check_repository_docs.py
```

The CI workflow runs full-scope lint through
[`check_frozen_lint.py`](../scripts/check_frozen_lint.py), followed by
`scripts/validate_submission_package.py`. All Python files are linted. A
[hash-bound historical record](ci/README.md) preserves 4,878 exact diagnostics in
130 unchanged frozen helpers/regression files; new findings or changed frozen
bytes fail. This is not a claim that raw Ruff has no historical findings.

The package validator concerns the older tracked submission and compact
evidence. It is not a certificate for the reopened economic study. The dated
[validation status](VALIDATION_STATUS.md) retains its original scope. Historical
453-test/36-subtest and 4,929-lint-finding records are dated snapshots, not the
current CI outcome.

A full test suite may inspect many frozen evidence packages and external
runtime assumptions. Do not rerun source jobs, simulations, accounts, paper
builders, or completed archive readbacks to validate a documentation edit.

## Input-dependent research

Before execution, read the exact study protocol and inspect saved intents,
job IDs, input hashes, output locations, budget gates, and model/policy
bindings. Do not infer that a `--help`, `validate`, or `replay` entry point
is harmless without inspecting it.

Data path overrides for the reusable package use `ALPHA_EVOLVE_*` variables;
the historical [data guide](DATA_AND_ARTIFACTS.md) describes that interface.
Those defaults do not replace the current study's explicit raw-CRSP and
actual-factor contracts.

## Maintaining status

Update `docs/study/status.json`, its readiness CSV, and the current-study prose
together when verified evidence changes. Retain the source receipt hashes and
the date of the snapshot. Do not promote a readiness status to a result or
silently alter a frozen study.
