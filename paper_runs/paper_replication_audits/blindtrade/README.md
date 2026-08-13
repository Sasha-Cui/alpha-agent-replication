# BlindTrade paper-level replication audit

This fail-closed audit rebuilds and visually checks the full arXiv source, inventories every active empirical table cell and figure panel, validates the four printed prompt schemas, replays directly testable passive benchmarks, and checks the signed OpenReview record plus bounded author-attributable release surfaces.

The manuscript is specification-rich but is not reproducible end to end from public artifacts. No BlindTrade code, input/output dataset, immutable model calls, checkpoints, seed-level paths, holdings, returns, or raw arrays is exposed. Thus 0/98 table cells and 0/9 empirical panels receive author-native result credit. A current public price snapshot matches 6/98 cells at printed precision, all passive benchmark components; this is not BlindTrade credit. All four verbatim output schemas fail JSON parsing as printed.

The strongest validity boundary is more serious than missing files: features are screened on the reported holdout, anonymization is not directly ablated, and score shuffling cannot distinguish genuine structure from structured leakage. The paper also misidentifies EQWL as an S&P 500 equal-weight ETF.
