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

Two official snapshots are pinned. The 2026-08-14 refresh changes only
`DATA_CARD.md` and `MODEL_CARD.md` relative to 2026-08-12; all 105 code and
artifact paths are byte-identical. The newer cards remove two explicit
"Limitations" sections, but the README and remaining card text still identify
the short replay as an acceptance fixture rather than the complete benchmark,
place the private experiment-controller history outside the release, and package
only trained seed 42 although the paper reports five seeds.

The latest official archive is still not deployment-complete. Nine registered
files are 133-byte Git LFS pointers, covering 340,563,208 expected bytes: three
adapters, three tokenizers, one router, and two large strategy-pool tables. The
official public single-file endpoints returned `404 file_not_found` for all nine.
One generic tokenizer content address, repeated in three adapter directories, was
recovered byte-exactly from an independent public GitHub blob. It validates under
the declared Transformers 5.11.0 / Tokenizers 0.22.2 / Protobuf 7.35.0 contract
and raises registry verification from 26/35 to 29/35 files. This is exact byte
recovery, not MM-ARC author provenance. The three trained adapters, router, and
two historical strategy tables remain unavailable: six files and 306,295,258
registered bytes. Artifact verification and model execution therefore fail
closed.

Accordingly, the honest paper-level score remains **zero regenerated published
numeric table units and zero regenerated empirical figure series for every
version**. The release materially improves implementation and deployment
faithfulness for v3, but it cannot reproduce the v3 training, five-seed holdout,
statistical tests, tables, or figures; it does not reproduce the legacy v1/v2
MM-DREX experiment at all. No proxy, source-document rebuild, test double, or
acceptance replay receives native paper-result credit.
