# AlphaCrafter paper and attributable-release audit

This audit treats arXiv `2605.05580` as a two-version lineage. Version 1 is the
26-page **Full-Stack Multi-Agent Framework** submission; version 2 is a substantial
22-page **Harnessing Multi-Agent Workflows** revision with changed framing,
algorithms, live window, results, figures, and ablations. The official v1 source
rebuilds to 26 visually sound pages. The unmodified official v2 source also builds:
four pdfLaTeX passes plus BibTeX converge to 22 pages after allowing roughly 45
seconds for the CJK package to initialize on Bouchet's shared TeX installation.
All 22 rebuilt pages match the official layout, tables, figures, and pagination.
Tokenized manuscript text is identical after excluding the official PDF's arXiv
side stamp and the expected build-date header difference.

The pinned 79-file MIT repository is strongly attributable: it belongs to the
authors' NJU-LINK organization, cites the exact arXiv paper and author list, and
matches the three-role architecture. The paper does not directly link it, so this
audit does not overstate the provenance. The source contains real miner, screener,
trader, data-tool, A-share exchange, U.S. exchange, and evaluation components.
Native controlled checks verify A-share buy/T+1/sell behavior, U.S. short/cover
behavior, the paper-stated 2-bp and 1-bp fees, and the return/drawdown metric
contract. These are component-conformance results on synthetic fixtures.

The checked-in full launcher is not operational as released: `config.yaml` asks
for `gpt-5.3-codex`, while every shipped `models.json` registers only `gpt-5` and
`gpt-5.2`; execution therefore fails before any API call. More fundamentally, the
paper evaluates GPT, Claude, and Gemini, while the runtime initializes only the
OpenAI Responses client. The launcher always injects the A-share instruction and
constructs its trading tools in their default A-share mode, so the released main
path does not select the paper's U.S. workflow even though U.S. components exist.

The release ships index series and empty/template schemas, not the paper's stock,
fundamental, statement, or news corpus. Its calendars end on 2026-03-31, before
the revised live period ends on 2026-06-12. Baseline implementations, point-in-time
memberships, model requests/responses, trial seeds, factor pools, actions, orders,
fills, brokerage integration, NAV/return arrays, and table/figure generators are
absent. There are no tracked tests; compilation and CLI help pass, while Ruff's
520 findings are recorded only as a modern static diagnostic.

The complete non-shallow repository history has 13 commits, one branch, no tags,
and no releases. Every revision is inventoried. The only structured payloads are
configuration/schema templates and, after the second commit, two index series;
no revision contains an agent result/run artifact, checkpoint, mined factor pool,
decision, prediction, signal, holding, order/fill record, or result array.
Seven distinctive v2 result literals also have zero occurrences outside the two
index input series.

Accordingly, the honest paper-level score is **0/176 v1 and 0/304 v2 published
numeric result units, and 0/16 v1 and 0/14 v2 empirical panels regenerated**.
The native component checks materially improve implementation faithfulness, but
no source rebuild, synthetic fixture, or local narrative proxy receives paper-result
credit. The older `alphacrafter_full_stack_multifactor` portfolio remains a clearly
labeled secondary motif translation, not an AlphaCrafter replication.
