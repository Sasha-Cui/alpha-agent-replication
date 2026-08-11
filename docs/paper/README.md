# Paper sources and evidence boundary

## Canonical ICAIF 2026 submission

`icaif2026_submission.tex` is the sole current submission manuscript. Its
headline macros, tables, and figures are generated from tracked aggregate
evidence by `scripts/build_icaif2026_submission_assets.py`; do not hand-edit
generated assets.

Build and validate from the repository root:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python scripts/validate_submission_package.py
```

That fresh-clone mode runs 62 source/PDF checks and never looks for ignored
build residue. For a release build, regenerate the assets and PDF and request
the nine additional log checks explicitly:

```bash
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python scripts/build_icaif2026_submission_assets.py
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python scripts/build_icaif2026_submission.py
/nfs/roberts/project/pi_btk22/zc362/environments/bin/alpha-evolve-python scripts/validate_icaif_submission.py \
  --pdf output/pdf/icaif2026_submission.pdf \
  --log docs/paper/icaif2026_submission.log \
  --bbl docs/paper/icaif2026_submission.bbl \
  --require-build-log
```

The build writes the single submission artifact to
`output/pdf/icaif2026_submission.pdf`. The current PDF is six pages and
its recorded release build passes all 71 checks plus the locked-evidence
wording gate.

The primary formula study exhaustively evaluates the three evaluator-valid seeds
in a pinned QuantEvolver release and passes 3/3 strict grade B (100%). It
preserves the released expressions, DSL semantics, pairwise missing-data rule,
forward return, and equal-mean top/bottom-quintile evaluator; only cadence,
universe, and horizon change. It does not reproduce the source discovery system
or published portfolio. The older 12-formula bundle is a mixed-fidelity
diagnostic outside this denominator. A strict audit separately grades the 50
legacy mappings A0/B0/C15/D33/U2; those mappings are construction diagnostics,
never performance evidence about the cited papers or their native agents.

The separate full-paper audit in
`paper_runs/paper_replication_audits/quantevolver/` confirms why this boundary
matters: the public release implements 38/67 audited mechanisms or meaningful
analogues, but reproduces 0/75 paper table results and 0/31 additional numeric
result claims. The 3/3 grade-B result is therefore component-only and carries no
credit for the private RFT experiment, benchmarks, mined factor library, or
published portfolio.

The fail-closed Alpha-R1 audit in
`paper_runs/paper_replication_audits/alpha_r1/` reaches a stricter boundary.
The paper says the full implementation and resources are available, but the
pre-submission repository revision is a two-line title README and the current
tree remains one README marking inference code and model weights Coming Soon.
All 124 table cells and 528 visible heatmap cells are enumerated; 0/652 results
and 0/70 implementation dimensions are reproduced. The local Alpha-R1 row is
only an M0 favorable narrative translation and receives no native mechanism or
paper-result credit.

The manuscript also reports a separate GuruAgents prompt-decision replay:
190/190 cells through a current 2026 OpenRouter-served `openai/gpt-4o` alias, 24
costed return paths, and matched Fama--French-to-JKP-BAB attribution. It does
not reconstruct the original model snapshot, provider, data engineering, or
native system, and its 33-month factor window does not identify unrestricted
JKP132 OLS.

Restricted security-level inputs and raw upstream market data remain outside
Git. The authorized GuruAgents collaborator bundle publishes the derived
monthly holdings, returns, traded notional, official Fama--French and extended
JKP factor panels, fitted values, residuals, penalties, loadings, schemas, and
hashes, subject to the licensing cautions in its manifest.

## Archived evidence-audit manuscript

`alpha_agent_replication.tex`, `generated_results.tex`, the owner-review
packet, and `scripts/build_paper_assets.py` document an earlier evidence-audit
manuscript and its G7 diagnostic history. They remain for research provenance,
not as alternate submission candidates. Their historical output path is not a
tracked canonical PDF, and the current repository validator does not require
that obsolete compiled artifact.
