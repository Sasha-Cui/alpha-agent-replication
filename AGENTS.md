# Repository operating instructions

## Current scope

The repository's active research goal is to evaluate executable investment
mechanisms on monthly U.S. equities against actual FF5 + momentum + JKP132.
The study and paper remain provisional. Read
[the current study](docs/CURRENT_STUDY.md) and the newest private
`artifacts/native_monthly_implementation_v2_20261116/HANDOFF.md`.

The user has resolved scope: ONLY papers with an explicit native monthly
investment experiment are eligible. Drop daily, weekly and quarterly methods;
no retiming or monthly aggregation creates eligibility. Daily input data may
support a genuinely monthly decision process. Do not reopen this scope question.

Faithful paper-based central implementations are allowed without the authors'
exact runtime or every published result. The v2 review supersedes the historical
v1 empty-cohort rule. Both EFS and Agentic AI Screening completed source and exact
offline replay. EFS completed 12 conditional economic paths; screening has 12
completed secondary paths and 18 blocked paths, including its primary/control.
The study and paper remain provisional. Read the current v2 status package and
`artifacts/native_monthly_implementation_v2_20261116/HANDOFF.md`.
Do not rerun completed source or regenerate responses to update documentation.

## Work location and execution

- Work remotely in the existing checkout:
  `/nfs/roberts/project/pi_jss233/zc362/alpha_evolve`.
  The BTK project path is a compatibility alias. Do not create scratch aliases.
- Refresh with `~/bin/update-bouchet-dev`; use sparse SSH with
  `ControlMaster=no`, `ControlPath=none`, and strict host-key checking.
- Do not edit local project copies or access
  `/Users/cui/Documents/GitHub`.
- Use existing central environments and supported wrappers. No installs,
  environment mutation, subagents, or author contact are authorized.
- Git writes require an explicit user request. The user has authorized this
  cleanup's logically grouped commits and push; do not reset, force-push,
  create worktrees, or include unrelated concurrent edits.
- Inspect saved intents and scheduler IDs before submission. Never duplicate
  a live, queued, or completed job.

## Scientific and financial preservation

- Treat frozen protocols, source bindings, outputs, failed attempts, archives,
  and manuscripts as immutable. Preserve historical paths used by manifests.
- Keep all 69 papers and their separate gaps. A component, transfer, or
  researcher reconstruction is not a full-paper reproduction.
- Keep licensed inputs, private responses, holdings, and accounting stores
  out of public Git. Do not inspect credentials or dump ledgers.
- All historical and uncertain charges count toward the user's strict
  total of less than USD 1,000. The current bounded runtime route is stricter
  at USD 800; legacy study caps remain unchanged. Paid work requires an admitted native-monthly case and its
  validated runtime/data/budget bindings. Documentation work opens no new paid
  route and does not authorize retrying or regenerating completed source.
- Any subsequently authorized model calls must use the canonical accounting
  stores under `runs/economic_fidelity/openrouter`. Read only the permitted
  `OPENROUTER_API_KEY` from the designated parent KnowledgeTemplate
  environment file; never print or save it.
- Preserve the existing WRDS session while available. Do not initiate another
  login or ask for repeated authentication as part of cleanup.
- Do not regenerate responses, retry uncertain requests, refund charges, edit
  recovery maps, or rebuild completed archives. Do not claim external human
  review or repeat the completed PDF marker.

## Documentation and verification

Start readers at [README.md](README.md). Keep current status in
[docs/CURRENT_STUDY.md](docs/CURRENT_STUDY.md), with the dated machine-readable
snapshot under `docs/study/`. Link older evidence as historical.

Run `python scripts/check_repository_docs.py` after navigation changes.
Use focused checks for code changes; do not rerun experiments to validate prose.
Record what changed, the checks performed, and any remaining limitation.

Earlier operating instructions are preserved in the
[historical snapshot](docs/history/AGENTS_before_20261116_cleanup.md).
They are provenance, not current authorization or a current budget.
