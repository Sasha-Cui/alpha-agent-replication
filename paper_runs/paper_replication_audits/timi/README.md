# TiMi paper/source and public-release audit

This audit pins both official versions of arXiv `2510.04787`, both complete
source packages, the accepted OpenReview record, its listed supplement, and
bounded exact-title/arXiv release searches. The v1 and v2 sources rebuild to
the official 16- and 17-page counts. All 33 official and all 33 rebuilt pages
were visually checked side by side; no unreadable, clipped, overlapping,
blank, or missing research content was found. This is excellent manuscript
reproducibility, not experimental reproducibility.

The current v2 contains 349 printed empirical numeric units across six active
result tables and six author-rendered figure assets with ten total panels,
eight of them empirical. The source package contains those reported tables and
rendered PDFs, not their underlying arrays. It ships no TiMi implementation,
exact runtime prompts or model calls, generated bots, frozen K-lines/news,
point-in-time 213-pair universe, baseline configurations, fee/funding records,
simulation/live trade logs, seeds, portfolios, returns, or result generator.

The ICLR 2026 OpenReview record is first-party and CC BY 4.0. It explicitly
lists a supplementary ZIP at immutable path
`/attachment/a7f4111f00a10d307b4ee29926741553acafbb99.zip`.
At audit time the logical attachment endpoint returned HTTP 403 and that
immutable path returned HTTP 404, including through the signed-in visible UI.
The supplement therefore existed in metadata but is not currently recoverable;
it must not be treated as inspected or absent. The paper says real transaction
cost records are in that supplement, which makes the broken attachment a
material replication blocker.

Exact GitHub searches found no repository for the arXiv identifier and no
attributable author implementation. `qOeOp/vibe-trading` and the TiMi design
under `cajias/nautilus-trading` are later third-party adaptations whose commit
authors do not match any paper author. They may be useful engineering, but
neither can establish TiMi experiment lineage and both receive zero native
paper credit.

The strict paper-level result is **0/349 active empirical table units and 0/8
empirical figure panels regenerated**. The audit also finds material internal
or evidentiary weaknesses: Figure 6 reports 61 OM and 45 SIGN orders while v2
prose says 28 and 39; the printed ARR equation is an unannualized total return;
v2 acknowledges that LLM baselines may exploit potential posterior information;
several live baseline coverage values are estimates from partial experiments;
and the new v2 backtest/ablation results have no released raw lineage. TiMi is
well described conceptually and its paper is fully rebuildable, but it is not
currently a defensible true experimental replication package.
