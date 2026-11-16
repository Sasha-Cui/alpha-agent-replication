# Publication upgrade runbook

All substantive execution takes place in the existing Bouchet checkout at
`/nfs/roberts/project/pi_btk22/zc362/alpha_evolve`. Refresh the development target
with `~/bin/update-bouchet-dev` before connecting. Long API jobs have their own
CPU-only Slurm allocations and do not depend on the development allocation.

## What this study contains

The six cases are EFS, FinMem, FinAgent, TradingAgents, GuruAgents, and QuantaAlpha.
Their evidence levels differ: paper-guided reimplementation, released-source
execution with adapters, actual source-prompt replay, and released-factor
reexecution. None is presented as a full original-paper reproduction. Preserve
`paper_runs/us_jkp_headline`, `paper_runs/us_jkp_in_spirit`, and the completed
`paper_runs/economic_fidelity/efs_v1` financial paths.

The new public-facing evidence lives in `paper_runs/publication_upgrade_v1`.
Raw text, security-level inputs, model responses, holdings, source dependency
archives and intermediate records live privately under `artifacts/publication_upgrade_v1`
and `runs/economic_fidelity/openrouter`.

## Environments

- Main analysis/test interpreter:
  `/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python`.
- Python 3.9 compatibility interpreter:
  `/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py39-20260809/bin/python`.
- FinMem and FinAgent: `scripts/run_finmem_fidelity_python.sh`, backed by the
  validated `environments/current/alpha-economic-fidelity` central alias.
- TradingAgents: `scripts/run_tradingagents_v010_python.sh`.
- QuantaAlpha: `scripts/run_quantaalpha_fidelity_python.sh`.
- ReportLab manuscript rendering: `environments/bin/kt-python`.

`environment.toml` and `environment_specs/` describe the existing native and
report runtimes. Do not install packages into project-local environment links.
Use `PYTHONDONTWRITEBYTECODE=1` and `pytest -p no:cacheprovider` to avoid refilling
shared file-count quotas.

PDF-dependent source audits need the cluster's installed Poppler module. In a
plain noninteractive shell, initialize modules without `errexit`/`nounset`, then
load the module:

```bash
set +e
set +u
source /etc/profile.d/modules.sh
module load poppler/25.07.0-GCC-13.3.0
```

## Model calls and pause behavior

All paid operations share `runs/economic_fidelity/openrouter/project_spend.json`.
The soft stop is 450 USD, below the 500 USD hard ceiling, including historical
usage, summaries, embeddings, setup runs, retries and unresolved reservations.
Credentials are read only from the authorized project-specific key assignment
and are never stored in outputs.

New complete responses are fsynced to `cohort_responses.jsonl` before accounting
settlement. Legacy EFS responses remain in the original SQLite cache. A listed
technical recovery retains the original bound and records a new charged attempt;
there is no silent retry. The original unavailable EFS setup request is never
retried. Do not interrupt a worker during a paid request. `PAUSE_FINMEM` and
`PAUSE_FINAGENT` in the private artifact directory stop the corresponding driver
after a completed day. Case-specific lock files prevent duplicate execution.

The final FinMem path uses the released Ada002 embedding wrapper. The final
FinAgent path uses its distinct released `text-embedding-3-large` provider with
3,072 dimensions, original token-ID chunking/normalization, and concurrent
independent document calls. A generic Ada adapter and a failed batching
optimization remain archived as setup evidence; their paths are not substituted
for final primary results.

## Reproduction sequence

```bash
cd /nfs/roberts/project/pi_btk22/zc362/alpha_evolve
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
PUBLICATION_PY=/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python

# No new paid calls. These require the completed cache and the pinned sources.
scripts/run_finmem_fidelity_python.sh scripts/replay_publication_native.py --case FinMem --output-name finmem_offline_replay
scripts/run_finmem_fidelity_python.sh scripts/replay_publication_native.py --case FinAgent --output-name finagent_offline_replay
scripts/run_tradingagents_v010_python.sh scripts/replay_publication_native.py --case TradingAgents --output-name tradingagents_offline_replay

# Source/control accounts and final analytical tables.
"$PUBLICATION_PY" scripts/build_publication_control_accounts.py
"$PUBLICATION_PY" scripts/evaluate_publication_jkp_augmentation.py
"$PUBLICATION_PY" scripts/analyze_publication_upgrade.py

# Snapshot spending before rendering; the report records that snapshot hash.
"$PUBLICATION_PY" scripts/summarize_publication_spend.py

# Generated report, manuscript, and structural validation.
/nfs/roberts/project/pi_btk22/zc362/environments/bin/kt-python scripts/build_publication_report.py
/nfs/roberts/project/pi_btk22/zc362/environments/bin/kt-python scripts/validate_publication_report.py
```

The native replay wrapper indexes a frozen ledger once, verifies every response checksum and request hash, and has no network or ledger-write path. It avoids repeatedly rewriting or parsing the live accounting ledger during cached reconstruction.

The EFS source-guided run has a separate cached reproduction driver,
`scripts/replay_efs_economic_fidelity.py`; keep its frozen code and inputs intact.
The ten matched grammar runs are regenerated by `scripts/run_efs_matched_search.py`
with seeds 101 through 110. QuantaAlpha source predictor/account export is
`scripts/export_quantaalpha_economic_fidelity.py`; it makes no model or market API
call and checks its 170-factor result against the previously repeated native path.

All comparisons retain their own clocks, fees, windows and scope. The full
JKP132-plus-market regression is refused when unidentified. Regularized
reconstruction and synthetic factor-sleeve allocation remain diagnostics, not
claims about unrestricted spanning or an all-in deployable portfolio.

## Independent review

`source_review/` contains outcome-free packets and blank human-review templates.
A human reviewer must personally assess the cited source and implementation
changes. `scripts/record_publication_human_review.py` records an actual completed
review and checks its packet hash and attestation. No human review is inferred
from tests, automatic code inspection, or model-generated text.

## Prospective pilot

`artifacts/publication_upgrade_v1/prospective_efs_v1` contains a local code/protocol
seal and immutable chained forecast records. The first four-arm research forecast
was committed on September 7, 2026, for simulated execution at the September 8
close and evaluation at the September 9 close. It is a development pilot with
human review and external registration pending. It is not a historical result
relabelled as prospective, and no real orders are submitted.

After the evaluation close is observable, run:

```bash
scripts/run_finmem_fidelity_python.sh scripts/run_efs_prospective.py --settle-only
```

Settlement makes no new LLM call and cannot replace an earlier forecast or
outcome. Per-forecast holding-period payoffs are not automatically concatenated
into a continuously rebalanced portfolio. Changes to sealed algorithm semantics
require a declared new study version; do not rewrite the existing commitment.

## Storage and publication boundary

`dependency_archives/` preserves source code and essential QuantaAlpha dependencies
in durable project storage. Original scratch paths remain runtime pointers; do
not rely on scratch retention. The private reproducibility bundle includes data
and model responses needed for the completed executions. Public presentation
artifacts exclude raw security-level data, raw news and credentials.

No commits, pushes, pull requests, author contact, external preregistration or
manuscript submission are performed by this workflow. Those are distinct actions,
and independent human review and unobserved future returns cannot be manufactured
by completing code.

## Final integrity, review bundle and packaging

Before final delivery, run `scripts/run_finmem_fidelity_python.sh
scripts/validate_publication_integrity.py`. The original semantic seal is an
AST digest generated by Python 3.10, so use that central runtime for this check.
The checker verifies the communicated seal/forecast, chain clocks and every
original EFS implementation pin without changing any commitment.

`build_publication_review_packets.py` also rebuilds the separate outcome-free
source/code review bundle and its file manifest. Final packaging requires current
source-packet hashes, all three full native trace replays, execution contracts,
full test results, an unchanged frozen record, complete six-case analysis and
visual QA matching the final PDF SHA-256. It checks links inside the review
archive and refuses a spending ledger that changed after the report snapshot.
Record visual QA only after inspecting the actual final rendered PDF.

## Bounded FinAgent transport recovery

The September8 resume runs `scripts/resume_finagent_after_transport_failure.py`
under the existing case lock. It recognizes only a terminal HTTP500/502/503/504
or read timeout/network-unreachable error after the native process exits. A
validation-worker wrapper qualifies only when every failed worker is explained
by a recognized transport error or a peer waiting on that same unresolved
request; account/budget/unknown-worker errors still require inspection. Each unavailable response keeps
its original charge reservation; a separate recorded attempt receives its own
request identity and is metered under the unchanged project/study caps. A saved
journal/SQLite response instead requires reconciliation and is never retried by
this supervisor. It permits at most four recovery batches per invocation and
two additional attempts per request, pauses thirty seconds between attempts,
and refuses algorithm, budget, explicit-pause or unknown failures.

The supervisor archives every failed log and completed prefix, including saved
validation-arm records. Rebuilt records must match exactly under the existing
full-replay comparator. Packaging refuses any unverified supervised prefix.
This is an operational wrapper; the FinAgent source actor, embedding provider,
request bodies, clock, controls and portfolio rules are unchanged.

## September8 network outage and cached resume

YCRC's system-status page confirms significant network disruptions affecting
Bouchet. The last restart could not download the tokenizer on a fresh node and
produced zero records; its length-only failed check remains archived. Saved
250-row training and both23-row validation prefixes were restored byte-for-byte.
This is an interrupted bootstrap, not an observed change in an economic value.
The supervisor now distinguishes incomplete reconstruction from a changed record.
Final packaging rechecks every saved prefix against the final completed run and
retains the original failure reports alongside the resolution checks.

The exact cl100k vocabulary is now in durable central cache, pinned in
`environment_specs/tokenizer_cache.json`. It loads with network access disabled;
its100256 mergeable ranks and original SHA256 are unchanged. The private bundle
includes this asset. The source Python wrapper sets its `TIKTOKEN_CACHE_DIR`.
No original tokenizer or embedding provider is replaced.

Before another paid run, the supervisor checks the unauthenticated OpenRouter
metadata endpoint. During the confirmed outage, do not keep submitting jobs.
Once connectivity is restored, submit the supervised CPU script with
`--resume-cached` (all previous unavailable requests are already reconciled).
This option refuses any newly unresolved reservation and creates no recovery
mapping. It still uses the same metered native driver and verifies saved prefixes.

The previous tmux finalizer was stopped while idle because the development
allocation was near expiry. Submit `alpha_publication_final_evidence.sbatch`
with an `afterok` dependency on the new native Slurm job. That separate CPU job
runs the full read-only replay, numerical validation, six-case analysis and report
assembly independently of the development-node lifetime. Final manual visual
inspection, documentation closure and packaging remain required afterward.

## Final historical evidence (September9)

Native FinAgent execution completed250 training records plus147 valuation/decision
records in each validation arm. Its full544-record offline replay matches exactly;
FinMem538 and TradingAgents61 also match. The final execution validator correctly
decodes the source runner's serialized numpy boolean literals without modifying
saved records. Six-case analysis and the18-page manuscript pass numeric/structural
checks and all-page visual review. All six primary comparisons remain inconclusive
at the2pp annual economic margin. Project API commitments are100.8075647USD,
including0.60387354USD retained reservations; no request remains in flight.

The current-data research is complete. Do not restart paid jobs. Archive hashes
and verified second copies are recorded in `package_manifest.json`. Independent
human review and the first prospective outcome remain external conditions.
