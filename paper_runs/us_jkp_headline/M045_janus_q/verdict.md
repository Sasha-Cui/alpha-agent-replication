# M045: Janus-Q event-driven trading

Status: **closed not evaluable on monthly U.S./JKP data**.

Janus-Q's central strategy is the learned event policy, not the CAR label equations or the released NAV arrays. An unnamed base model is SFT- and GRPO-tuned to read point-in-time news and emit event type, predicted CAR, direction, and trade strength; strong decisions drive next-open event trades. The current v2 paper and author-linked release still provide no model/checkpoint, inference or training code, complete reward constants, predictions, orders, or portfolio engine. The current repository's `main` branch remains a one-byte README, while its historical `gh-page` contains only static site outputs.

The released 64,326 Chinese event-stock rows and 31,999 JSONL examples are useful data-integrity evidence. They do not identify a causal U.S. strategy: their direction and strength labels are deterministic functions of realized future CAR. Replaying those labels as trades would be lookahead. JKP has monthly characteristics and returns but no point-in-time news/event input, so a numerical proxy would discard the defining Janus-Q mechanism.

Accordingly, this milestone has no fabricated zero-return path and no common-benchmark metrics. The result does not show that the paper's profitability claim is false; it shows that the public record cannot generate new causal decisions needed to test that claim or transfer it to the common U.S. task. Static NAV arithmetic and dataset checks remain preserved in the paper audit, separate from strategy replication.

Reopen only if the authors release the trained policy or sufficient causal inference/training and portfolio code, or if an attributable implementation exposes a fixed decision rule that can consume point-in-time U.S. events.
