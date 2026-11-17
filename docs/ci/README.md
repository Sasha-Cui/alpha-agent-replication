# Public reproducibility CI

The workflow runs on Python 3.9 and 3.12 with the same hash-locked dependencies.
It checks current reader navigation, lints the configured Python source/script/test scope,
validates the public submission package and runs the test suite. A passing CI
run checks software and evidence contracts; it does not establish investment
performance or complete the provisional v2 study.

## Why historical lint needs a separate record

The November source-preservation commits added immutable research helpers and
bound regression files. Raw Ruff reports 4,878 pre-existing formatting and
unused-code diagnostics in 130 such files. Reformatting them would change the
bytes pinned by completed research and archive protocols.

[`check_frozen_lint.py`](../../scripts/check_frozen_lint.py) still runs pinned
Ruff 0.12.12 on the same `src`, `scripts` and `tests` scope as the original
workflow. The existing upstream-snapshot exclusion is unchanged. It compares
the result with
[the explicit frozen record](frozen_lint_baseline.json):

- Every recorded file must exist, remain a regular file and match its SHA-256.
- Its diagnostic counts must match exactly, by rule.
- Any finding in a new or unlisted file fails the gate.
- Unexpected safety/undefined-name rules cannot be added to the historical record.
- Ruff version and lint configuration must match the reviewed policy.

There is no automatic record refresh, new global rule suppression, new source
folder exclusion or `continue-on-error`. The reusable `src` modules currently have no
legacy entries and remain strict. The raw Ruff command still reports the known
historical diagnostics; the CI summary explicitly reports their count rather
than claiming that they were fixed.

Seven regression tests exercise byte drift, added diagnostics, new files,
missing files and unsupported legacy rules. An intentional change to a frozen
helper should normally use a new version with clean lint while preserving the
original. Policy changes need an explicit reviewed record update.

## Commands

Inside an existing environment with the locked Ruff version:

```bash
python scripts/check_repository_docs.py
python scripts/check_frozen_lint.py
python scripts/validate_submission_package.py
```

For local compatibility checks with another Python interpreter, an already
installed Ruff 0.12.12 binary can be supplied through `--ruff-binary`. This does
not install packages or change the policy. Existing central environments remain
immutable.

The package validator checks the historical canonical submission and synthetic
software tests. It is separate from current monthly source/economic admission.
No provider call or scientific source/model/account rerun is part of CI repair.

The original failure is preserved in [workflow run44053528445](https://github.com/Sasha-Cui/alpha-agent-replication/actions/runs/44053528445): both Python versions failed the raw lint step before package validation.
