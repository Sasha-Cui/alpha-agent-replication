# M004: FLAG-Trader common-task verdict

Status: **closed—not evaluable on the monthly U.S./JKP common task without creating a new learned policy**.

The central method is the fusion LLM trading agent trained with a PPO-like policy/value objective. It is not Buy-and-Hold, an InvestorBench baseline, or generic PPO. The paper provides a prompt and 22 settings, but no author-linked implementation, base-model revision, trainable-layer split, optimizer/initialization, seeds, checkpoint, action trajectory, PnL path, or native result output.

The missing objects cannot be filled mechanically from JKP. The state and action mask are underspecified; reward initialization and costs conflict; KL and value-clipping descriptions do not determine one loss; and neither checkpoint nor run-selection semantics are disclosed. Training a new LLM/PPO agent would make the decisive strategy choices ours. The unaffiliated exact-name repository implements a different method. The six reproduced InvestorBench/Buy-and-Hold cells are baseline evidence only.

Accordingly M004 records no return rather than a zero or a researcher-designed PPO result. This is a common-task non-evaluability finding, not evidence that the paper's private results are false. M005 is now active.
