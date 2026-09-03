# M010: LLMFactor common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy from the released paper/source**.

LLMFactor’s headline method has three prompt stages: infer a related stock, extract the top five price-relevant factors from news, then combine those factors, the relation, and five prior price movements to predict whether the target stock rises or falls. The paper evaluates daily binary classification on StockNet, CMIN-US, CMIN-CN, and EDT with three GPT model aliases.

The prompt skeletons and ACC/MCC equations are narrow, deterministic components, but no author-linked implementation, exact text/price snapshot, split, preprocessing, company matcher, request envelope, response parser, generation settings, predictions, confusion matrices, or portfolio rule is released. JKP does not supply the point-in-time news and related-company text required by the mechanism.

Two later non-author implementations cannot fill the gap. One changes the model/prompts and omits the relation stage; the other changes the five-period window to 30, changes every prompt, and contains a saved result with target leakage. Neither reproduces a paper result. The existing local characteristic portfolio is explicitly an M0 narrative translation, not LLMFactor.

No monthly return is manufactured. LLMFactor reports positive classification results, but zero of 82 native LLMFactor cells—and zero of 206 total displayed cells including baselines—has been reproduced. Those claims remain unresolved: this is not evidence that they are false, and no executed common-benchmark strategy exists that can be said merely to underperform JKP.

M010 is closed without a return. The ten-milestone batch release gate runs before M011 is activated.
