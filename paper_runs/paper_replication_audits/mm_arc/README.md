# MM-DREX / MM-ARC paper and release audit

This audit treats arXiv `2509.05080` as a versioned lineage, not a single stable
paper. Versions 1 and 2 are the legacy 32-page **MM-DREX** manuscript; their
`main.tex` files are byte-identical. Version 3 is a wholesale 17-page replacement
named **MM-ARC**, with a different backbone, method, experiment period, baseline
set, statistical protocol, author list, results, and official anonymous release.

The v3 release is substantial: 107 files, 19 pipeline modules, 60 pools, 300
active members, a 62-instrument universe, a 7,440-row acceptance replay, tests,
deployment contracts, and a content-addressed artifact registry. In the pinned
Python 3.12 environment, Ruff and compilation pass and the release's CI-style
`python -m pytest -q` command passes all 111 tests. These are real code-contract
results, not paper-result reproductions: CI checks out with LFS disabled and the
model-facing tests use doubles.

The retrieved official archive is not deployment-complete. Nine registered files
are 133-byte Git LFS pointers, covering 340,563,208 expected bytes: three adapters,
three tokenizers, one router, and two large strategy-pool tables. Artifact
verification therefore fails closed. The data and model cards also explicitly say
that the replay is an acceptance fixture, the full benchmark/training corpus is
not included, the full private training and experiment-controller history is
outside the release, and only trained seed 42 is packaged although the paper
reports five seeds.

Accordingly, the honest paper-level score remains **zero regenerated published
numeric table units and zero regenerated empirical figure series for every
version**. The release materially improves implementation and deployment
faithfulness for v3, but it cannot reproduce the v3 training, five-seed holdout,
statistical tests, tables, or figures; it does not reproduce the legacy v1/v2
MM-DREX experiment at all. No proxy, source-document rebuild, test double, or
acceptance replay receives native paper-result credit.
