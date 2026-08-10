# Contributing

Contributions that improve correctness, auditability, or documentation are
welcome. Keep each change narrow and make its evidentiary effect explicit.

## Development setup

Use Python 3.9 or 3.12 and install `requirements-lock.txt` as shown in the
README. Run before proposing a change:

```bash
python -m ruff check src scripts tests
python -m pytest -q
python scripts/validate_submission_package.py
```

Changes to paper claims, mappings, sample construction, benchmarks, inference,
or frozen outputs must include the relevant source citation, tests, a regenerated
manifest, and an explanation of whether existing numerical results change.
Never commit licensed security-level data, credentials, local environments, or
unreviewed large artifacts. Keep raw inputs read-only and outside the checkout.

Do not rewrite a frozen result in place. Write a versioned run directory,
compare it with the prior run, and update the public artifact only after the
difference has been reviewed. Mapping changes must follow
`docs/INDEPENDENT_MAPPING_REVIEW_PLAN.md` when presented as confirmatory.
