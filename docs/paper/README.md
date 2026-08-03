# Paper build and evidence boundary

`alpha_agent_replication.tex` is the submission manuscript. Its quantitative
macros, tables, and figures are generated from the frozen ledgers and final run
directories by `scripts/build_paper_assets.py`; hand-editing generated assets is
not part of the workflow.

The paper has two deliberately separate empirical layers:

1. a 103-lineage public-system census and a 67-system artifact/native-output
   audit; and
2. a 62-candidate common-task analysis of mechanism-inspired characteristic
   proxies.

The second layer is not a native replication or ranking of the named agents.
Artifact unavailability is never encoded as a zero return. A proxy path whose
monthly total portfolio return reaches -100% is a limited-liability
implementation failure; it is not clipped or restarted and remains in the
planned Holm/BH/BY denominator with `p=1`. Paired maximum-statistic procedures
use the executable paths only because failures have no estimable statistic.

The current G7 evidence is geographically external but not a pristine
confirmatory holdout. The protocol records a post-outcome correctness repair
and a subsequent post-runtime limited-liability amendment. All superseded
attempts are excluded from the manuscript estimates and retained for provenance.
The post-hoc fixed-calendar country/LOO diagnostic is separately labeled and
hashed; it does not alter the primary pooled analysis.

## Build

On Bouchet, from the repository root:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_fixed_calendar_diagnostics.py
PYTHONPATH=src .venv/bin/python scripts/build_paper_assets.py
module load texlive/20240312-GCC-13.3.0
cd docs/paper
pdflatex -interaction=nonstopmode -halt-on-error alpha_agent_replication.tex
bibtex alpha_agent_replication
pdflatex -interaction=nonstopmode -halt-on-error alpha_agent_replication.tex
pdflatex -interaction=nonstopmode -halt-on-error alpha_agent_replication.tex
```

The verified submission copy is written to
`output/pdf/alpha_agent_replication_paper.pdf`. The author-review packet remains
`PENDING` until Sasha Cui explicitly vets the evidence, citations, licensing,
and rendered pages.
