# GuruAgents paper-prompt replay

This experiment evaluates the public GuruAgents prompting pipeline directly; it
does not map the paper to a JKP formula. The source repository ships five agent
prompts, deterministic finance-tool observations, and archived portfolios, so
the replay can be scored against the authors' own outputs.

## Complete grid

- `results`: five agents × seven quarters (2023Q4–2025Q2) = 35 cells.
- `results_22_24`: five agents × twelve quarters (2022Q1–2024Q4) = 60 cells.
- Two modes per cell = 190 experiments.

`archived-final` reconstructs the completed source tool transcript and replays
the final ranking/allocation decision. `tool-routing` starts from the exact
system prompt and source user request, lets the model choose tools, and serves
the matching archived deterministic observations. The second mode tests tool
routing as well as final portfolio construction.

The paper code uses `gpt-4o` at temperature zero. The default replay therefore
uses `openai/gpt-4o` through OpenRouter with `temperature=0`.

## Source and provenance

The current unmodified public source checkout is:

```text
/nfs/roberts/scratch/pi_btk22/zc362/guruagents_prompt_replay_source
```

Each run freezes its Git commit plus SHA-256 hashes of the prompt, archived
analysis JSON, and archived portfolio CSV.

## Concurrent run and cost controls

Create a dedicated OpenRouter key capped at **$475** and expose it only in the
active Bouchet shell as `OPENROUTER_API_KEY`. Do not save it in the repository.
The runner also enforces a shared **$450** ceiling across all workers. Each
request reserves a conservative maximum cost before dispatch and then settles
against OpenRouter's returned usage and dollar cost.

For a detached run, `--api-key-file /absolute/path` accepts a secret file with
mode `600`; place it outside the repository. The key value and file path are not
copied into run outputs.

Dry-run the entire grid first:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python \
  scripts/run_guruagents_openrouter_replay.py \
  --dry-run \
  --workers 16 \
  --max-budget-usd 450
```

Then launch all 190 experiments concurrently through the bounded worker pool:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python \
  scripts/run_guruagents_openrouter_replay.py \
  --workers 16 \
  --max-budget-usd 450
```

Interrupted runs are resumable; completed experiment directories are reused
unless `--overwrite` is supplied.

## Outputs

Generated data live under `runs/prompt_replay/guruagents/<UTC-run-id>/` and are
git-ignored until reviewed:

- `manifest.json`: complete grid, hashes, source commit, pricing assumptions,
  key-limit metadata, conservative cost estimate, and final spend ledger.
- `usage.jsonl`: request-level tokens and OpenRouter cost.
- `summary.csv`: parse status, ticker-set Jaccard, exact-order agreement, weight
  error, score error, calls, tokens, and cost for every experiment.
- `experiments/<id>/`: exact request/transcript, raw responses, final markdown,
  provenance, and comparison with the authors' archived portfolio.

## Interpretation boundary

Agreement in `archived-final` tests whether the prompted LLM reconstructs the
authors' portfolio from identical finance signals. Agreement in `tool-routing`
also tests adherence to the public tool-use procedure. Neither validates the
underlying data engineering or the out-of-sample alpha claim. A second stage
must recompute all tools from formation-date data, convert portfolios to return
paths, and apply the same-universe market, primary-factor, and JKP132 panels.
