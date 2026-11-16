> Historical snapshot captured on November 16, 2026. Its status labels and
> instructions apply to the earlier study. Start at [the current overview](../../README.md).
> Relative links were adjusted for this location; the original bytes are preserved in the private cleanup record.

# Alpha Evolve Paper Runs

This directory tracks paper-by-paper execution against the configured external same-universe FF3 and FF5Mom benchmark definitions.

Each paper run must produce a dated monthly return series before benchmark metrics are reported:

```text
paper_runs/<run_id>/candidate_returns.csv
columns: month,candidate_return
```

Then run:

```bash
.venv/bin/python scripts/evaluate_candidate_returns.py \
  --candidate-id <run_id> \
  --candidate-csv paper_runs/<run_id>/candidate_returns.csv \
  --out-dir paper_runs/<run_id>/results
```

The evaluator reports CAPM, FF3, and FF5Mom rows. A paper is not marked relevant until it has real candidate returns and survives the FF3/FF5Mom rows with positive alpha/appraisal evidence and no obvious leakage.
