# Proxy-Fidelity Audit

## Bottom Line

The 50 backtested strategies are **not faithful replications of the 40 source
papers**. They are researcher-authored mappings into a common monthly U.S. JKP
framework.

This audit grades only the frozen 50-strategy common-task ladder. The separate
GuruAgents prompt-replay experiment added later is outside this table.

| Grade | Meaning                                   | Strategies |
| ----- | ----------------------------------------- | ---------: |
| A     | Faithful paper/system replication         |          0 |
| B     | Faithful disclosed component              |          0 |
| C     | Recognizable idea, but materially changed |         15 |
| D     | Materially inconsistent with the paper    |         33 |
| U     | Source unavailable                        |          2 |

No strategy reproduces a native-agent output or supports a paper-level
performance claim. Even the 13 mappings labeled highest-fidelity grade C=8 and
D=5 under a strict formula-level review.

## Why This Matters

- 46 of 50 strategies combine ranked JKP characteristics.
- 47 of 50 use essentially the same monthly long-short portfolio construction.
- At least 39 of 50 had a closer public formula, algorithm, prompt, or execution
  rule that was not used.
- The mappings were selected after U.S. outcomes were inspected and were not
  independently second-coded.

The current result shows that **JKP factors span researcher-created JKP
composites**. It does not show that JKP factors span the papers' native agents
or that the agents merely rediscovered known factors.

## Paper-by-Paper Review

C means theme/component only. D means the result should not be attributed to
the paper. “Mechanical only” requires the same underlying signal; permitted
differences are limited to frequency, universe, holding period, weights, and
transaction costs. **No row meets that standard.**

| Paper                     |                 Grade | What the paper does                                                                                           | What we do                                                                                                             |                           Mechanical only? |
| ------------------------- | --------------------: | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | -----------------------------------------: |
| EFS (3 strategies)        |             C / D / C | Evolves exact daily close/return formulas and holds a long-only top-*m* portfolio.                          | Build three monthly momentum/volatility or safety scores; use decile long-short or top-five long-only.                 |                         No—signals differ |
| AlphaAgent                |                     D | Generates OHLCV alphas, combines them with a learned model, and selects top stocks.                           | Use a monthly accounting-quality, momentum, and low-risk blend.                                                        |                No—inputs and model differ |
| QuantaAlpha               |                     D | Evolves printed OHLCV/VWAP formulas and combines the validated factor library with LightGBM.                  | Use a monthly profitability, QMJ, momentum, leverage, and volatility score.                                            |                No—signal and model differ |
| QuantEvolver              |                     C | Starts from a released 60-bar mean-return/volatility seed and evolves factors with reinforcement fine-tuning. | Replace the seed with 12-1-month return divided by 252-day volatility and form U.S. deciles.                           |            No—lookbacks and output differ |
| R&D-Agent-Quant           |                     C | Jointly optimizes daily factors and predictive models, then holds a China top-50 portfolio.                   | Use a static monthly value, profitability, momentum, and low-risk blend.                                               |                No—signal and model differ |
| Alpha-Jungle (2)          |                 C / C | Mines printed OHLCV/VWAP formulas and feeds factor sets into daily prediction models.                         | Use two monthly price-volume/momentum and trend/low-volatility scores.                                                 |              No—formulas and model differ |
| FactorMiner               |                     D | Mines and combines a released library of 110 intraday DSL formulas.                                           | Use a monthly value, profitability, quality, momentum, and leverage blend.                                             |             No—inputs and formulas differ |
| CogAlpha                  |                     D | Evolves executable OHLCV code and combines generated alphas with LightGBM.                                    | Use monthly momentum, liquidity, QMJ, spread, and volatility characteristics.                                          |               No—formula and model differ |
| FAMA                      |                     D | Mines OHLCV-only Alpha101-style formulas and applies daily RankIC/top-quintile selection.                     | Use monthly value, profitability, momentum, and size characteristics.                                                  |               No—inputs and signal differ |
| Alpha-GPT                 |                     D | Uses human-AI interaction and genetic search to produce printed intraday OHLCV formulas.                      | Use a monthly value and profitability accounting screen.                                                               |              No—inputs and formula differ |
| Alpha-GPT 2.0             |                     D | Describes a dynamic human-in-the-loop alpha-development pipeline.                                             | Invent a monthly value, momentum, QMJ, growth, and low-volatility blend.                                               |              No—no matching source signal |
| Chain-of-Alpha            |                     U | Describes iterative formula generation in the abstract; the paper is withdrawn.                               | Use a monthly momentum, reversal, breakout, turnover, and volatility score.                                            |                Unknown—source unavailable |
| FactorMAD                 |                     U | Describes debate-based factor generation in the abstract; full text is unavailable.                           | Use a monthly value, profitability, QMJ, momentum, leverage, and volatility score.                                     |                Unknown—source unavailable |
| AlphaLogics               |                     D | Mines interpretable technical market logic from OHLCV and explicitly excludes fundamentals.                   | Use only value, profitability, growth, and leverage accounting variables.                                              |           No—input set contradicts source |
| AlphaAgentEvo             |                     D | Evolves printed price-based seed expressions and holds daily/top-decile factor portfolios.                    | Use monthly momentum, profitability, safety, growth, issuance, and volatility characteristics.                         |              No—formula and inputs differ |
| Alpha-R1                  |                     D | Screens 82 Alpha101 factors daily using market context and trades five-day staggered portfolios.              | Use a monthly QMJ, profitability, momentum, leverage, and volatility score.                                            |                No—signal and model differ |
| AlphaCrafter              |                     C | Generates, screens, and dynamically selects ranked strategies with regime and exposure controls.              | Use one static monthly value, profitability, momentum, QMJ, growth, and volatility blend.                              | No—generated strategy and controls differ |
| LLMFactor                 |                     D | Predicts next-day stock movement from text and news.                                                          | Create a monthly characteristic long-short portfolio without text or news.                                             |                 No—task and inputs differ |
| FactorEngine              |                     D | Generates and evolves exact executable OHLCV factor programs.                                                 | Use monthly value, profitability, cash-flow, accrual, leverage, and growth variables.                                  |              No—inputs and formula differ |
| TradingAgents             |                     D | Uses multimodal agents to make dynamic firm-level Buy/Hold/Sell decisions.                                    | Use a static monthly momentum, quality, growth, liquidity, and low-risk blend.                                         |        No—decision rule and inputs differ |
| ContestTrade              |                     D | Predicts five-day Sharpe and allocates across all agents with positive forecasts.                             | Select one factor sleeve using trailing 36-month realized Sharpe.                                                      |         No—forecast and allocation differ |
| QuantHarness              |                     D | Uses 1-hour/4-hour OHLC agents for three-bar Long/Short decisions across multiple assets.                     | Sort U.S. stocks monthly on returns, turnover, spreads, and volatility.                                                |                 No—signal and task differ |
| QuantAgent Holy Grail (2) |                 C / C | Provides exact Three Soldiers and ATR14 breakout trading examples.                                            | Replace them with two monthly trend and volatility factor scores.                                                      |                           No—rules differ |
| AlphaQuanter              |                     D | Uses a daily tool-augmented reinforcement-learning agent for stock decisions.                                 | Use a static monthly momentum, value, profitability, safety, and risk score.                                           |               No—policy and inputs differ |
| FinMem                    |                     D | Trades daily using news, layered memory, and character-based reasoning.                                       | Use a long-only monthly momentum, quality, liquidity, and low-risk score.                                              |          No—information and policy differ |
| FinCon                    |                     D | Uses daily multi-agent forecasts, mean-variance allocation, and a 1% CVaR monitor.                            | Use a monthly momentum, profitability, safety, liquidity, and low-risk decile.                                         |                No—allocation rule differs |
| FinAgent                  |                     D | Makes multimodal, tool-augmented single-asset trading decisions.                                              | Use a monthly long-only quality, momentum, liquidity, cash, leverage, and risk score.                                  |                 No—task and inputs differ |
| FLAG-Trader               |                     D | Learns a daily PPO Buy/Hold/Sell policy from market, news, and macro information.                             | Use a static monthly momentum, reversal, safety, beta, and volatility score.                                           |               No—policy and inputs differ |
| MM-ARC                    |                     D | Dynamically routes capital across multimodal strategy pools with robustness admission.                        | Use a static monthly combination of trend, reversal, breakout, volatility, and safety motifs.                          |             No—routing and signals differ |
| Trading-R1                |                     D | Applies an exact 3/7/15-day volatility-scaled labeling rule and a learned five-action policy.                 | Use monthly momentum, reversal, safety, volatility, and maximum-return characteristics.                                |                 No—exact rule is not used |
| Janus-Q                   |                     D | Converts news events into Long/Short/Hold trades from next open through the next two days.                    | Use a monthly numeric score with no news or event conditioning.                                                        |                  No—signal source differs |
| Trade in Minutes          |                     D | Designs and runs minute-level futures/crypto grid bots.                                                       | Sort U.S. stocks monthly on returns, turnover, spread, and volatility.                                                 |                 No—strategy class differs |
| AlphaAgents (2)           |                 D / D | Uses agent debate for one-time equal-weight selection from 15 technology stocks.                              | Build two monthly continuous style-factor long-short portfolios.                                                       |                 No—selection rule differs |
| MarketSenseAI 2.0         |                     C | Uses agent Buy signals to form monthly long-only equal- or value-weighted portfolios.                         | Treat ex-post value/momentum exposures as a score and form a long-short portfolio.                                     |            No—signal and direction differ |
| MountainLion              |                     D | Produces multimodal cryptocurrency forecasts and recommendation reports.                                      | Use a monthly U.S. equity momentum, quality, growth, and low-risk strategy.                                            |                  No—asset and task differ |
| P1GPT                     |                     C | Makes daily multimodal Buy/Sell/Hold decisions for three stocks.                                              | Use a static monthly value, momentum, profitability, growth, safety, and risk blend.                                   |                  No—decision rule differs |
| FinVision                 |                     C | Uses an explicit prompt to choose actions, positions, and cash from trend/dip/risk evidence.                  | Translate only the trend, dip-buying, and risk-control motifs into a monthly score.                                    |                    No—action rule differs |
| GuruAgents (6)            | D / C / D / C / D / C | Implements five exact quarterly Nasdaq-100 guru scoring and long-only weighting rules; no ensemble is tested. | Use six monthly JKP style scores, including an invented equal-weight ensemble, mostly as decile long-short portfolios. |            No—rules and portfolios differ |
| QuantAgents               |                     D | Uses daily Nasdaq-100 agents, meetings, memory, simulation, and dynamic risk controls.                        | Use a static monthly momentum, safety, liquidity, cash, leverage, and low-risk score.                                  |               No—system and policy differ |
| HedgeAgents               |                     D | Dynamically hedges across BTC, the Dow, and foreign exchange using multiple agents.                           | Use a monthly U.S. equity quality, momentum, value, and low-beta strategy.                                             |              No—asset and strategy differ |

## Source Problems

- The tracked EFS PDF is older than the current arXiv version.
- Old extracted text still calls QuantHarness "QuantAgent."
- Old extracted text still calls MM-ARC "MM-DREX."
- AlphaAgentEvo is still marked unresolved in part of the audit despite a
  tracked full PDF.

## Recommended Fix

1. Keep the current 50-strategy analysis only as a secondary thematic exercise.
2. Build a smaller primary sample from exact formulas, released return streams,
   or executable code.
3. Preserve each paper's inputs, frequency, universe, holding period, weights,
   and costs.
4. Leave systems without recoverable outputs as availability-only.
5. Complete an outcome-blind, independent double-coding review before running
   the new backtests.
