# Paper Evidence-Route Policy

Code availability, paper specification, and mapping fidelity are different
questions. Every retained canonical work is therefore assigned exactly one
paper-level evidence route before any common-task proxy is interpreted.
Row-level mapping fidelity remains a separate field.

## Route priority

1. **Public code available.** Inspect or attempt the native pipeline first. If
   the native system cannot produce the required dated return path, record the
   exact output, input/adapter, task, licensing, access, or executability
   blocker. A researcher-authored proxy may then appear only as a secondary,
   clearly labeled diagnostic; it is never a native replication.
2. **Paper-only and sufficiently specified.** Reproduce the stated rule,
   prompt, search, or training procedure only to the scope supported by the
   paper. Do not silently replace omitted language, data, timing, optimization,
   or execution choices.
3. **Paper-only and underspecified.** Use a favorable, clearly labeled motif or
   component proxy only when the source supports a defensible mapping. If even
   that mapping would be too speculative, retain the work as availability-only
   and make no performance inference.

The priority is important: public code takes precedence over paper-level
mapping fidelity. A source-grounded rule from a public-code paper remains a
secondary component diagnostic until the native pipeline has been reproduced
or precisely blocked.

## Current partition

The generated
`paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv`
assigns all 69 retained works as follows:

| Paper-level route | Works | Current disposition |
| --- | ---: | --- |
| Public code available | 18 | Eight have targeted execution-audit records; ten have static common-task blockers but were not execution targets. Thirteen also have common-task proxies, all labeled secondary; five remain availability-only. |
| Paper-only and sufficiently specified | 0 | No paper-only work is currently claimed as an end-to-end prompt/search/training reproduction. |
| Paper-only and underspecified or only partially specified | 51 | Three support source-grounded component tests, 24 support favorable motif proxies, and 24 remain availability-only. |

Across all routes, the mapping-level partition remains five works with 13
source-grounded component mappings, 35 works with 37 narrative mappings, and 29
availability-only works. Those mapping labels do not imply native prompt,
search, training, allocation, or execution reproduction.

## Required fields and interpretation

The paper-level ledger records the route, linked systems, reachable-code
status, static fidelity tier, native-pipeline disposition, precise blocker,
mapping disposition, proxy role, and negative-inference boundary. It explicitly
records that no full prompt/search/training pipeline has been reproduced.

The source ledgers remain authoritative for details:

- `native_fidelity_ledger.csv` gives a blocker for every retained F/T system;
- `direct_code_attempt_inventory.csv` gives the selected targeted execution
  attempts and their exact outcomes;
- `mapping_scope_ledger.csv` and `mapping_audit.csv` give row-level proxy
  provenance; and
- `work_level_evidence_waterfall.csv` records reconstructed versus
  availability-only disposition.

Rebuild and verify the route ledger with:

```bash
python scripts/build_native_fidelity_ledger.py
python scripts/build_paper_evidence_routes.py
git diff --exit-code -- \
  paper_runs/submission_evidence/native_fidelity_ledger.csv \
  paper_runs/submission_evidence/replication_scope/paper_evidence_route_ledger.csv
python -m pytest -q tests/test_paper_evidence_routes.py
```
