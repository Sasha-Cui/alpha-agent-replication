# Paper sources and evidence boundary

## Canonical ICAIF 2026 submission

`icaif2026_submission.tex` is the sole current submission manuscript. Its
headline macros, tables, and figures are generated from tracked aggregate
evidence by `scripts/build_icaif2026_submission_assets.py`; do not hand-edit
generated assets.

Build and validate from the repository root:

```bash
python scripts/validate_submission_package.py
```

That fresh-clone mode runs 62 source/PDF checks and never looks for ignored
build residue. For a release build, regenerate the assets and PDF and request
the nine additional log checks explicitly:

```bash
python scripts/build_icaif2026_submission_assets.py
python scripts/build_icaif2026_submission.py
python scripts/validate_icaif_submission.py \
  --pdf output/pdf/icaif2026_submission.pdf \
  --log docs/paper/icaif2026_submission.log \
  --bbl docs/paper/icaif2026_submission.bbl \
  --require-build-log
```

The build writes the single submission artifact to
`output/pdf/icaif2026_submission.pdf`. The current PDF is eight pages and
its recorded release build passes all 71 checks plus the locked-evidence
wording gate.

The empirical results are retrospective factor-spanning diagnostics for 50
good-faith strategy mappings from 40 papers. They are not 50 native-agent
replications. Unavailable artifacts are never encoded as zero returns, and the
paper does not claim that model pretraining causally produced factor
rediscovery.

The manuscript also reports a separate, fully executed GuruAgents prompt
replay: 190/190 GPT-4o agent-quarter-mode cells, 24 costed return paths, and a
matched official Fama--French-to-JKP-BAB attribution ladder. That experiment is
not counted among the 50 formula/component mappings or the 14-target code
audit, and its 33-month factor window does not identify unrestricted JKP132
OLS.

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
