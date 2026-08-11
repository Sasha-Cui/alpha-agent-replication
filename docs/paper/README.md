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
