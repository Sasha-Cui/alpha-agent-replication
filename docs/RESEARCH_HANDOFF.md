# Native monthly study technical handoff

**Verified November 17, 2026. Study and paper remain provisional.** This handoff
supersedes the stale running-job status in the earlier briefing. Read the
[project briefing](PROJECT_BRIEFING.md) for the question, results and limits.

## Current completion and failure state

| Job | Work | Verified state |
| --- | --- | --- |
| 33614757 array 0–2 | Primary EFS monthly source, seeds101–103 | COMPLETED exit0; 286 months each; exact offline replay |
| 33614758 array 0–1 | Primary screening, ratio/log BM | COMPLETED exit0; 20 annual policies each; exact offline replay |
| 33615291 | EFS economic evaluation v2 | COMPLETED exit0; 12 conditional paths pass, zero failed |
| 33615292 | Screening economic evaluation v2 | COMPLETED exit0; 12 secondary paths pass, 18 paths blocked |

**A zero process exit is insufficient for financial completion.** Screening's
LLM non-hold, combined non-hold and universe-EW arms fail held month-end pricing.
The LLM-screened/combined paths first block in September 2008; the equal-weight
control first blocks in February 2007. Its completed FinBERT and buy-only paths
must not replace the designated primary or matched control.

The [public v2 package](../paper_runs/native_monthly_implementation_v2_20261116/README.md)
contains every path disposition and aggregate result. Exact security-level
witnesses stay private. No missing path is zero-alpha data.

## Paths and receipt chain

Canonical checkout:

```text
/nfs/roberts/project/pi_jss233/zc362/alpha_evolve
```

Current working evidence, relative to the checkout:

```text
artifacts/native_monthly_implementation_v2_20261116/
```

| File or directory in that workspace | Role |
| --- | --- |
| `native_timing_amendment.json` | Native completed-month information clock, fixed before primary portfolio outcomes |
| `case_protocol_M023_native_clock.json` | EFS implementation and input bindings |
| `case_protocol_M050_native_clock.json` | Screening implementation, tool and input bindings |
| `M023_native_clock/{101,102,103}/` | Full source/grammar states, replies and exact replay checks |
| `M050_native_clock/{ratio,log}/` | Annual policy/tool states and exact replay checks |
| `native_evaluation_protocol_v2.json` | Frozen funding, costs, controls, inference and code hashes |
| `evaluation_native_clock_v2/{M023,M050}/completion.json` | Economic path counts and retained failures |
| `reporting_snapshot_verified_20261117.json` | Fresh saved-evidence readback, no research rerun |
| `reader_docs_before_v2_status_20261117/` | Before-copies of mutable reader documents |

The public [verification record](../paper_runs/native_monthly_implementation_v2_20261116/verification.json)
checks saved source/replay equality, source/helper bindings and economic output
hashes. It is a reporting readback, not new source/replay/model/account execution.
The v1 audit and every failed or partial run remain unchanged.

## Remaining research work

1. Diagnose and verify the held-asset quote or terminal-payoff evidence needed
   for the screening primary and equal-weight control. Preserve both original
   failures and the full intended232-month calendar.
2. If a correction is justified, create a separately versioned account contract
   and meaningful financial checks using the completed frozen policies. Do not
   regenerate replies, pick a favorable truncation, silently write off a holding,
   or zero-fill its missing return.
3. Resolve or explicitly bound the essential dated qualitative/macro input gaps
   for MarketSenseAI 2.0 and Signal or Noise. Reasonable reconstructed prompts are
   allowed; exact author runtime is not a blanket gate.
4. Reconcile all current outcomes, sensitivity cases and unavailable paths into
   the provisional paper. Do not claim full-paper reproduction, an untouched
   historical holdout, or external human review.

No model, data extraction, account or scientific job is launched by this
reporting update. Inspect saved intents and scheduler state before any later
execution; never duplicate completed source jobs.

## Interpretation and implementation choices

EFS is a bounded base-search implementation on monthly preformed FF25 portfolios:
42 seed factors,30 input bars,60 months of completed feedback, three slots/month,
pool cap60 and ten selected factors/assets. It omits some revised-paper redundancy
and weight-optimization refinements. Three trajectories share one market path.
The unit turnover charge does not establish net underlying-stock implementability.

Screening uses annual printed LLM-S role/task prompts, four real descriptive
tools, frozen FinBERT and stated screen combinations. Raw/log BM and buy/non-hold
variants are fixed separately. The historical extension uses current model and
accounting vintage; the sparse news archive is not exhaustive.

The primary cost is10bp per side;0/25bp are sensitivities. Cash distributions and
CIZ terminal values are conditional vendor valuations, not certified historical
payment-date settlement or merger exchange ratios. Unpriced held endpoints block
a path. Actual138-factor attribution,2pp/year margin and multiplicity boundaries
remain mandatory. Pointwise approximate99% intervals are not simultaneous bounds.

## Repository and presentation maintenance

Update `docs/study/status.json`, the 69-paper CSV and reader prose together. Keep
source admission separate from primary financial admission. Preserve the status
schema expected by `scripts/check_repository_docs.py`; run that offline check
after changes. The v1 empty-cohort checkpoint is historical and superseded for
current source admission.

The [presentation](presentations/LLM_INVESTMENT_STUDY_20261117.pdf) and
[speaking notes](presentations/LLM_INVESTMENT_STUDY_20261117.md) are the portable
management summary. Live editable versions are linked there. Public documents
exclude licensed stock inputs, holdings and private responses.
