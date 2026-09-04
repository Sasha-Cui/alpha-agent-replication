# M042: Alpha-R1 common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy because the trained semantic gate and every signal-defining artifact are unreleased**.

The original paper's central policy is clear: weekly market memory and factor profiles are combined with daily price/news state; a GRPO-trained Qwen3-8B model selects factors from an 82-factor Alpha101 zoo; fixed four-year betas turn the selected factor values into stock scores; and equal-weight top-10 holdings rotate through five daily slots with 30-minute VWAP execution and 10 bp on each buy and sell. Original pages for semantic gating, reward/GRPO, portfolio/VWAP mechanics, and the main results were text-checked and visually inspected.

No actual signal can be reconstructed. The release omits the identities and conventions of the 82 retained and 40 test factors, every beta, memory, semantic profile, daily state, prompt, trained checkpoint, judge/structural reward, GRPO configuration, point-in-time data, selection, score, fill, holding, return, and NAV. The official repository remains one 1,101-byte README at the same three-commit head on 2026-09-04, with inference code and model weights still marked Coming Soon. This directly conflicts with the paper's statement that full implementation and resources are available.

The old JKP quality/momentum score is rejected as a researcher motif. Lasso and IC Momentum are baselines and also lack the factor set. Training a fresh gate or running base Qwen3-8B would define another policy; the paper itself reports the unaligned base model as a losing ablation.

No monthly return is assigned. Alpha-R1 is unresolved/non-evaluable, not shown false or below JKP. Zero of 652 displayed table/heatmap cells and zero of 70 implementation dimensions has a native public reproduction path.
