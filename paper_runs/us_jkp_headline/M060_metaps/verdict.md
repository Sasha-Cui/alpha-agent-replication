# M060: MetaPS adaptive programmatic strategy selection

Status: **closed not evaluable on monthly U.S./JKP data**.

MetaPS's headline strategy is a trained selector, not any one printed technical rule. It ranks ten programmatic strategies against price, news, and order-flow state; uses simulator rollouts to build V1/V2/V3 supervision; has a teacher rewrite 528 examples per view; and fine-tunes a Qwen3.5 policy that selects the dated strategy, action, and size bucket.

The paper prints unusually compact strategy snippets and label equations. Twelve independently implemented components pass controlled checks, but they consume supplied inputs and receive no native-result credit. The momentum branch is only one library ingredient; it selects one maximum-absolute mover from six native assets and emits an unmapped `scalable` size mode. Turning it into JKP deciles would replace both MetaPS selection and execution. The printed volatility breakout is not a fallback: because `current` is inside the window defining `high` and `low`, both branches are mathematically unreachable unless the rule is repaired.

No implementation, dataset, model, or checkpoint URL is provided, and fresh exact repository searches remain empty. Missing artifacts include the market/news/order-flow panel, rankings, rollouts, SFT records and weights, teacher calls, fine-tuning configuration, checkpoint, model outputs, size mapping, fills, holdings, and return arrays. JKP cannot infer a trained selector from these omissions.

No return path is fabricated. None of 492 table cells or 20 empirical panels was regenerated through an author-native pipeline. This closure does not establish that MetaPS's reported results are false; it records that isolated input programs and supplied-input equations cannot identify the headline policy.
