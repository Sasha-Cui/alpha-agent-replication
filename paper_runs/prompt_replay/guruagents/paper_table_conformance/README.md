# GuruAgents published-result conformance audit

This is a paper-level audit, not a JKP proxy test. It compares every value in
GuruAgents Table 1 with metrics recomputed from the daily paths in the authors'
pinned public workbook at commit
74ad2e6ce2e604c73a6fc2829d48ab58fe6be050.

The audit evaluates both plausible source windows:

- the paper-labeled window through 2025Q2; and
- the complete daily history stored in the pinned workbook.

Neither window reproduces Table 1 for any of the seven strategies. Across 140
strategy-window-metric comparisons, only four match to the paper's displayed
precision. Those four are the same benchmark maximum-drawdown values repeated
across the two windows. No agent row fully matches.

There is also a transaction-cost contradiction. Section 3.3 of the paper and
the public notebooks declare transaction_cost=0.0001, which is 0.01% or one
basis point. The source notebook's main calculate_agent_returns routine does
not use that variable, so the shipped workbook paths do not demonstrate that
the published cost was charged.

Run the audit with:

    /nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python \
      scripts/audit_guruagents_paper_table.py

Use --strict when a nonzero exit is desired until all published cells
reproduce. The non-strict command writes evidence while retaining the honest
not_reproduced status.

Outputs:

- paper_table_1_targets.csv: transcription of the published table.
- metric_conformance.csv: value-level comparisons and rounding tolerances.
- strategy_summary.csv: sample windows and match counts.
- manifest.json: pinned hashes, cost audit, and overall status.

The archived prompt replay remains useful evidence about model decisions, but
it must not be treated as reproduction of the paper's published performance.
