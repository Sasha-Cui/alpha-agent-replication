# M050: agentic AI portfolio screening

Status: **closed not evaluable on monthly U.S./JKP data**.

The paper's central strategy is a dated ensemble screen: an annually generated LLM-S fundamental rule and a FinBERT news rule determine the candidate universe, after which one of several high-dimensional precision estimators and portfolio objectives produces weights. The public record does not contain the annual rules, FinBERT checkpoint/scores, monthly buy/sell/hold sets, ensemble fallback events, fitted matrices, optimizer configuration, weights, or returns.

The linked 4,589-row news dataset is a useful input component, but it contains no paper sentiment scores and cannot reconstruct the missing fundamental/IBES screen. The single December-2023 LLM prompt/output listing identifies one 2024 rule, not the full medium/short-window annual rule history. JKP can replace the numeric return/characteristic panel, but it cannot infer these missing decisions or the selected covariance/optimization implementation.

The later `agentic_portfolio` repository passes its own component tests but replaces both screening models, every paper precision estimator, the 180-month window, risk-free convention, and the data. It is not author-attributed and receives no paper-result credit. A fresh exact search found no first-party implementation.

No return path is fabricated. This closure does not prove the paper's revised Sharpe claims false; it records that the source does not identify an executable headline screen or portfolio. Reopen for author monthly signal ledgers/runtime and fitted portfolio outputs.
