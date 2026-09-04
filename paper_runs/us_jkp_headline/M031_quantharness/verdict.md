# M031: QuantHarness common-task verdict

Status: **closed—not evaluable as a monthly U.S./JKP strategy without inventing its inputs and policy**.

The paper's central method is clear. For each 1-hour or 4-hour event, Indicator, Pattern, and Trend agents reason over a recent OHLC candlestick path and chart images; a final agent must choose LONG or SHORT, forecasts three candles, and supplies a 1.2–1.8 risk-reward ratio. The official source exposes this prompt/graph mechanism and 1,600 sampled 100-row benchmark CSVs, so this is not a no-code paper.

The common JKP panel is nonetheless the wrong state space for the method. Its 444 columns contain monthly `prc`, `prc_high`, and `prc_low` observations but no exact Open/High/Low/Close sequence and no opening-price field. Converting 45 intraday bars into 45 months, fabricating opens, and converting a three-candle risk-constrained trade into a monthly holding would change the strategy rather than adapt its portfolio wrapper. The released source also lacks the paper experiment/evaluator, does not enforce the stated three-bar holdout in its active path, substitutes a Decision module for the paper's RiskAgent, and does not identify the published LLM configuration or outputs.

The earlier favorable JKP characteristic score is rejected because its characteristics and signs were chosen by the researcher, not by QuantHarness. The paper's 40-close linear regression is also rejected as the headline result because it is an explicit baseline and its published alignment is undocumented. Current-model reruns on synthetic charts and the non-JKP released segments fail the same attribution boundary.

No monthly return is assigned. This does **not** show that QuantHarness's positive claims are false or that it merely loses against JKP; it means those claims cannot be placed on the common monthly U.S.-stock benchmark from the disclosed method and approved inputs. The prior audit still records 0/272 current-v4 and 0/600 version-specific native result cells regenerated.
