#!/usr/bin/env python3
"""Run exploratory paper-idea proxy replications on JKP USA data.

These are not public-code reproductions. They map paper-described trading ideas
onto available monthly JKP USA characteristics, then build candidate returns from
approved read-only data only.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from alpha_evolve.jkp import DEFAULT_FF5MOM, DEFAULT_JKP_USA, long_short_one_month, validate_columns, weighted_mean

DEFAULT_START = "1999-07-31"
DEFAULT_END = "2024-12-31"
BENCHMARK_COLS = DEFAULT_FF5MOM
BASE_COLS = [
    "permno", "eom", "ret_exc_lead1m", "me",
    *BENCHMARK_COLS,
    "ret_1_0", "ret_3_1", "ret_6_1", "ret_12_1", "ret_18_1",
    "rvol_21d", "rvol_252d", "ivol_capm_21d", "rmax5_21d", "rmax1_21d", "rmax5_rvol_21d",
    "dolvol_126d", "turnover_126d", "turnover_var_126d", "bidaskhl_21d",
    "beta_252d", "betadown_252d",
    "be_me", "market_equity", "at_gr1", "ope_be", "qmj", "qmj_growth", "qmj_prof", "qmj_safety",
    "gp_me", "gp_mev", "ebit_mev", "ebitda_debt", "ni_me", "ocf_me", "oaccruals_at", "at_turnover",
    "debt_at", "debt_me", "debt_gr1", "cash_at", "eqnetis_me", "sale_gr1", "sale_me",
    "iskew_capm_21d", "rskew_21d",
]
BASE_COLS = list(dict.fromkeys(BASE_COLS))

IDEA_DEFINITIONS: dict[str, dict[str, Any]] = {
    "repo_alphabench_formulaic_price_volume": {
        "paper_ref": "001 AlphaBench",
        "paper_idea": "AlphaBench frames LLM alpha mining as formula generation from price and volume operators, then portfolio evaluation by Sharpe and related metrics.",
        "proxy_formula": "rank(ret_12_1)+rank(ret_6_1)+rank(rmax5_rvol_21d)+rank(dolvol_126d)-rank(rvol_252d)-rank(turnover_var_126d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "repo_in_spirit_proxy",
    },
    "repo_alphaagent_decay_resistant_quality": {
        "paper_ref": "003 AlphaAgent",
        "paper_idea": "AlphaAgent regularizes LLM factor search for originality, hypothesis consistency, and complexity control to counter alpha decay and crowding.",
        "proxy_formula": "rank(ope_be)+rank(ocf_me)+rank(qmj_safety)+rank(at_turnover)-rank(oaccruals_at)-rank(eqnetis_me)-rank(debt_gr1)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "repo_in_spirit_proxy",
    },
    "repo_rd_agent_factor_model_compact_ensemble": {
        "paper_ref": "006 R&D-Agent-Quant",
        "paper_idea": "R&D-Agent-Quant presents a data-centric factor/model co-optimization loop aiming for compact, robust factor sets rather than one-off generated alphas.",
        "proxy_formula": "rank(be_me)+rank(ope_be)+rank(gp_me)+rank(ret_12_1)-rank(rvol_252d)-rank(beta_252d)-rank(at_gr1)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "repo_in_spirit_proxy",
    },
    "repo_alphaprobe_dag_diverse_factor_blend": {
        "paper_ref": "021 AlphaPROBE",
        "paper_idea": "AlphaPROBE treats alpha mining as DAG-guided factor evolution, selecting promising parents while preserving factor-pool diversity and stability.",
        "proxy_formula": "rank(ret_12_1)-rank(ret_1_0)+rank(be_me)+rank(ope_be)+rank(qmj_safety)+rank(turnover_126d)-rank(rvol_252d)-rank(debt_at)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "repo_in_spirit_proxy",
    },
    "repo_quantagent_hft_price_pattern": {
        "paper_ref": "025 QuantAgent HFT",
        "paper_idea": "QuantAgent is a price-driven multi-agent HFT system centered on short-horizon technical indicators, chart patterns, trend state, and risk-aware execution.",
        "proxy_formula": "rank(ret_1_0)+rank(ret_3_1)+rank(rmax1_21d)+rank(rmax5_rvol_21d)+rank(turnover_126d)-rank(bidaskhl_21d)-rank(rvol_21d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "repo_in_spirit_proxy_monthly_hft_approximation",
    },
    "repo_fincon_cvar_risk_controlled_allocator": {
        "paper_ref": "029 FinCon",
        "paper_idea": "FinCon uses manager/analyst hierarchy plus dual-level risk control, including CVaR-style monitoring, for portfolio decisions.",
        "proxy_formula": "long-only top decile by rank(ret_12_1)+rank(ope_be)+rank(qmj_safety)+rank(dolvol_126d)-rank(rvol_252d)-rank(beta_252d)-rank(betadown_252d)",
        "strategy": "long_only_top_decile_value_weighted",
        "replication_scope": "repo_in_spirit_proxy",
    },
    "repo_trading_r1_risk_adjusted_reasoning": {
        "paper_ref": "033 Trading-R1",
        "paper_idea": "Trading-R1 frames trading as reasoning/RL over market state and rewards; the JKP proxy tests a risk-adjusted trend/reversal reward signal.",
        "proxy_formula": "rank(ret_3_1)+rank(ret_12_1)-rank(ret_1_0)+rank(qmj_safety)-rank(rvol_21d)-rank(rmax5_21d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "repo_in_spirit_proxy",
    },
    "repo_alphaforgebench_executable_multifactor": {
        "paper_ref": "045 AlphaForgeBench",
        "paper_idea": "AlphaForgeBench evaluates LLMs as quantitative researchers generating executable alpha factors and factor-based trading strategies.",
        "proxy_formula": "rank(be_me)+rank(ope_be)+rank(ret_12_1)+rank(qmj)+rank(dolvol_126d)-rank(rvol_252d)-rank(debt_at)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "repo_in_spirit_proxy",
    },
    "repo_livetradebench_live_allocation_proxy": {
        "paper_ref": "047 LiveTradeBench",
        "paper_idea": "LiveTradeBench evaluates live multi-asset portfolio allocation under price/news uncertainty with explicit risk-return allocation decisions.",
        "proxy_formula": "long-only top decile by rank(ret_12_1)+rank(qmj)+rank(qmj_safety)+rank(dolvol_126d)-rank(rvol_252d)-rank(beta_252d)",
        "strategy": "long_only_top_decile_value_weighted",
        "replication_scope": "repo_in_spirit_proxy",
    },
    "repo_deepfund_prudent_fund_manager": {
        "paper_ref": "048 DeepFund",
        "paper_idea": "DeepFund models a multi-agent fund workflow with fundamental, technical, policy/news, insider-style analysts, portfolio management, and risk control.",
        "proxy_formula": "long-only top decile by rank(qmj)+rank(ope_be)+rank(gp_me)+rank(cash_at)+rank(ret_12_1)-rank(debt_at)-rank(rvol_252d)-rank(beta_252d)",
        "strategy": "long_only_top_decile_value_weighted",
        "replication_scope": "repo_in_spirit_proxy",
    },
    "repo_tradetrap_robust_safety_proxy": {
        "paper_ref": "051 TradeTrap",
        "paper_idea": "TradeTrap is primarily a robustness/stress-test framework; the in-spirit proxy tests the conservative safety/liquidity posture implied by its mitigation concerns.",
        "proxy_formula": "rank(qmj_safety)+rank(dolvol_126d)+rank(cash_at)-rank(rvol_252d)-rank(beta_252d)-rank(bidaskhl_21d)-rank(debt_at)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "repo_in_spirit_proxy_robustness_not_alpha_claim",
    },
    "repo_quantevolver_return_sharpe_proxy": {
        "paper_ref": "005 QuantEvolver",
        "paper_idea": "QuantEvolver uses executable seed expressions and reinforcement fine-tuning; this row repeats its risk-adjusted momentum seed in the unified in-spirit table.",
        "proxy_formula": "ret_12_1 / abs(rvol_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "repo_seed_jkp_proxy_unified",
    },
    "paper_factorminer_memory_diverse_library": {
        "paper_ref": "008 FactorMiner",
        "paper_idea": "FactorMiner uses modular skills and experience memory to build a diverse low-redundancy library of formulaic alpha factors.",
        "proxy_formula": "rank(ret_12_1)+rank(be_me)+rank(ope_be)+rank(qmj_safety)+rank(at_turnover)-rank(rvol_252d)-rank(debt_at)-rank(eqnetis_me)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy",
    },
    "paper_cogalpha_code_evolved_hybrid": {
        "paper_ref": "009 CogAlpha",
        "paper_idea": "CogAlpha represents alphas as executable code and evolves diverse economically interpretable signals through a multi-agent quality-checking hierarchy.",
        "proxy_formula": "rank(ret_12_1)+rank(ret_3_1)+rank(dolvol_126d)+rank(qmj)-rank(bidaskhl_21d)-rank(rvol_252d)-rank(turnover_var_126d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy",
    },
    "paper_alpha_gpt_interactive_formula": {
        "paper_ref": "011 Alpha-GPT",
        "paper_idea": "Alpha-GPT is a human-AI interactive formulaic alpha mining system that summarizes and modifies top-performing symbolic alphas.",
        "proxy_formula": "rank(be_me)+rank(ret_12_1)+rank(ope_be)+rank(gp_me)-rank(debt_at)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy",
    },
    "paper_alpha_gpt2_full_pipeline": {
        "paper_ref": "012 Alpha-GPT 2.0",
        "paper_idea": "Alpha-GPT 2.0 expands interactive alpha mining into alpha modeling and analysis over a full quantitative investment workflow.",
        "proxy_formula": "rank(be_me)+rank(ret_12_1)+rank(qmj)+rank(sale_gr1)-rank(rvol_252d)-rank(beta_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy",
    },
    "paper_chain_of_alpha_formula_chain": {
        "paper_ref": "013 Chain-of-Alpha",
        "paper_idea": "Chain-of-Alpha is described as chained formula generation and optimization using market data and backtest feedback.",
        "proxy_formula": "rank(ret_12_1)-rank(ret_1_0)+rank(rmax5_rvol_21d)+rank(turnover_126d)-rank(rvol_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy_from_title_and_source_summary",
    },
    "paper_factormad_debate_interpretable": {
        "paper_ref": "014 FactorMAD",
        "paper_idea": "FactorMAD is a multi-agent debate framework for interpretable stock alpha factor mining.",
        "proxy_formula": "rank(be_me)+rank(ope_be)+rank(qmj_safety)+rank(ret_12_1)-rank(debt_at)-rank(rvol_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy_from_title_and_source_summary",
    },
    "paper_alphaagentevo_evolved_seed": {
        "paper_ref": "016 AlphaAgentEvo",
        "paper_idea": "AlphaAgentEvo frames alpha mining as self-evolving agentic reinforcement learning that refines seed alphas through reward-guided trajectories.",
        "proxy_formula": "rank(ret_12_1)+rank(ret_6_1)+rank(ope_be)+rank(qmj_safety)-rank(rvol_252d)-rank(at_gr1)-rank(eqnetis_me)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy",
    },
    "paper_llmfactor_explainable_price_news": {
        "paper_ref": "019 LLMFactor",
        "paper_idea": "LLMFactor extracts explainable factors from text/news and historical prices to predict stock movement.",
        "proxy_formula": "rank(ret_12_1)+rank(sale_gr1)+rank(gp_me)+rank(dolvol_126d)-rank(rvol_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy_no_news_available",
    },
    "paper_factorengine_program_knowledge": {
        "paper_ref": "020 FactorEngine",
        "paper_idea": "FactorEngine turns domain knowledge and reports into executable factor programs, with closed-loop verification and portfolio feedback.",
        "proxy_formula": "rank(be_me)+rank(ope_be)+rank(gp_me)+rank(ocf_me)-rank(oaccruals_at)-rank(debt_at)-rank(at_gr1)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy",
    },
    "paper_finagent_multimodal_generalist": {
        "paper_ref": "030 FinAgent",
        "paper_idea": "FinAgent is a multimodal, tool-augmented generalist trading agent with diversified trading and risk-aware tool use.",
        "proxy_formula": "long-only top decile by rank(qmj)+rank(ret_12_1)+rank(dolvol_126d)+rank(cash_at)-rank(rvol_252d)-rank(beta_252d)-rank(debt_at)",
        "strategy": "long_only_top_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy",
    },
    "paper_flag_trader_gradient_policy": {
        "paper_ref": "031 FLAG-Trader",
        "paper_idea": "FLAG-Trader fuses LLM agents with gradient/RL-style policy optimization for sequential trading decisions.",
        "proxy_formula": "rank(ret_3_1)+rank(ret_12_1)-rank(ret_1_0)+rank(qmj_safety)-rank(rvol_21d)-rank(beta_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy",
    },
    "paper_janus_q_event_driven_proxy": {
        "paper_ref": "034 Janus-Q",
        "paper_idea": "Janus-Q is an event-driven trading framework that models heterogeneous event impact and optimizes reward-gated trading decisions.",
        "proxy_formula": "rank(rmax5_rvol_21d)+rank(ret_1_0)+rank(turnover_126d)+rank(qmj_safety)-rank(rvol_21d)-rank(bidaskhl_21d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy_no_news_events_available",
    },
    "paper_timi_minutes_technical_proxy": {
        "paper_ref": "035 Trade in Minutes",
        "paper_idea": "Trade in Minutes decouples strategy development from rapid execution, using technical indicators, strategy adaptation, and risk control in volatile markets.",
        "proxy_formula": "rank(ret_1_0)+rank(ret_3_1)+rank(rmax1_21d)+rank(turnover_126d)-rank(rvol_21d)-rank(bidaskhl_21d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy_monthly_minutes_approximation",
    },
    "paper_mountainlion_multimodal_allocation": {
        "paper_ref": "038 MountainLion",
        "paper_idea": "MountainLion coordinates multimodal RAG agents for price forecasting, news-driven reasoning, risk evaluation, and strategic allocation.",
        "proxy_formula": "rank(ret_12_1)+rank(qmj)+rank(qmj_safety)+rank(sale_gr1)-rank(rvol_252d)-rank(beta_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy_no_news_available",
    },
    "paper_p1gpt_structured_workflow": {
        "paper_ref": "039 P1GPT",
        "paper_idea": "P1GPT fuses technical, fundamental, news, and sectoral analysis through a layered multi-agent workflow with embedded risk assessment.",
        "proxy_formula": "rank(ret_12_1)+rank(be_me)+rank(ope_be)+rank(sale_gr1)+rank(qmj_safety)-rank(rvol_252d)-rank(debt_at)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy_no_news_available",
    },
    "paper_quantagents_risk_controlled_system": {
        "paper_ref": "043 QuantAgents",
        "paper_idea": "QuantAgents combines market/news/risk/strategy agents, memory, event-impact optimization, and risk-control meetings for simulated trading.",
        "proxy_formula": "rank(ret_12_1)+rank(qmj_safety)+rank(dolvol_126d)+rank(cash_at)-rank(rvol_252d)-rank(beta_252d)-rank(debt_at)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "paper_in_spirit_proxy_no_news_available",
    },
    "code_quantaalpha_self_evolving_factor": {
        "paper_ref": "004 QuantaAlpha",
        "paper_idea": "QuantaAlpha is listed as an LLM-driven self-evolving framework for factor mining.",
        "proxy_formula": "rank(ret_12_1)+rank(ope_be)+rank(gp_me)+rank(qmj)-rank(rvol_252d)-rank(debt_at)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "code_link_in_spirit_proxy",
    },
    "code_alpha_r1_reasoning_screen": {
        "paper_ref": "017 Alpha-R1",
        "paper_idea": "Alpha-R1 is listed as alpha screening with LLM reasoning via reinforcement learning.",
        "proxy_formula": "rank(qmj)+rank(ope_be)+rank(ret_12_1)-rank(debt_at)-rank(rvol_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "code_link_in_spirit_proxy",
    },
    "code_alphaforge_program_factor": {
        "paper_ref": "022 AlphaForge",
        "paper_idea": "AlphaForge is listed as an implementation repo for LLM-assisted factor/strategy generation.",
        "proxy_formula": "rank(be_me)+rank(ret_12_1)+rank(ope_be)+rank(dolvol_126d)-rank(rvol_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "code_link_in_spirit_proxy",
    },
    "code_alphagen_symbolic_factor": {
        "paper_ref": "022 AlphaGen",
        "paper_idea": "AlphaGen is a symbolic alpha generation/search repo listed in the source table.",
        "proxy_formula": "rank(ret_12_1)-rank(ret_1_0)+rank(be_me)+rank(ope_be)-rank(rvol_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "code_link_in_spirit_proxy",
    },
    "code_tradingagents_multi_agent": {
        "paper_ref": "023 TradingAgents",
        "paper_idea": "TradingAgents is a multi-agent LLM financial trading framework with analyst/trader/risk-style roles.",
        "proxy_formula": "rank(ret_12_1)+rank(dolvol_126d)+rank(qmj_safety)+rank(sale_gr1)-rank(rvol_252d)-rank(beta_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "code_link_in_spirit_proxy",
    },
    "code_alphaquanter_tool_orchestrated_rl": {
        "paper_ref": "027 AlphaQuanter",
        "paper_idea": "AlphaQuanter is listed as an end-to-end tool-orchestrated agentic RL stock trading system.",
        "proxy_formula": "rank(ret_3_1)+rank(ret_12_1)+rank(turnover_126d)-rank(rvol_21d)-rank(beta_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "code_link_in_spirit_proxy",
    },
    "code_finmem_memory_trend": {
        "paper_ref": "028 FinMem",
        "paper_idea": "FinMem is listed as an LLM trading agent with layered memory and character design.",
        "proxy_formula": "rank(ret_12_1)-rank(ret_1_0)+rank(qmj_safety)+rank(cash_at)-rank(rvol_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "code_link_in_spirit_proxy",
    },
    "code_ai_trader_value_quality": {
        "paper_ref": "049 AI-Trader",
        "paper_idea": "AI-Trader is a practitioner LLM trading repo listed as implementation evidence.",
        "proxy_formula": "rank(be_me)+rank(qmj)+rank(ope_be)+rank(cash_at)-rank(debt_at)-rank(rvol_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "code_link_in_spirit_proxy",
    },
    "code_agentictrading_lab_allocation": {
        "paper_ref": "050 AgenticTrading",
        "paper_idea": "AgenticTrading is listed as an agentic trading lab/infrastructure repo.",
        "proxy_formula": "rank(ret_12_1)+rank(qmj)+rank(dolvol_126d)-rank(rvol_252d)-rank(beta_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "code_link_in_spirit_proxy",
    },
    "code_ai_hedge_fund_buffett_munger": {
        "paper_ref": "052 ai-hedge-fund",
        "paper_idea": "virattt/ai-hedge-fund is a practitioner multi-agent hedge-fund style repo with value/quality investor personas.",
        "proxy_formula": "rank(qmj)+rank(qmj_prof)+rank(ope_be)+rank(gp_me)+rank(cash_at)-rank(debt_at)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "code_link_in_spirit_proxy",
    },
    "code_vibe_trading_prompt_allocation": {
        "paper_ref": "053 Vibe-Trading",
        "paper_idea": "Vibe-Trading is a practitioner prompt-driven trading repo listed in the source table.",
        "proxy_formula": "rank(ret_12_1)+rank(qmj)+rank(dolvol_126d)-rank(rvol_252d)",
        "strategy": "long_short_decile_value_weighted",
        "replication_scope": "code_link_in_spirit_proxy_low_evidence",
    },
    "efs_momentum_low_vol_breakout": {
        "paper_ref": "002 EFS",
        "paper_idea": "EFS appendix describes evolved factors combining momentum, mean return, low volatility/stability, and breakout logic.",
        "proxy_formula": "rank(ret_3_1)+rank(ret_6_1)+rank(ret_12_1)-rank(rvol_21d)-rank(rvol_252d)+rank(rmax5_rvol_21d)",
        "strategy": "long_short_decile_value_weighted",
    },
    "efs_short_reversal_low_noise": {
        "paper_ref": "002 EFS",
        "paper_idea": "EFS discusses regime shifts toward mean reversion and downside/noise filtering in sideways markets.",
        "proxy_formula": "-rank(ret_1_0)-rank(rvol_21d)+rank(qmj_safety)",
        "strategy": "long_short_decile_value_weighted",
    },
    "efs_sparse_top5_momentum_low_vol": {
        "paper_ref": "002 EFS",
        "paper_idea": "EFS uses sparse top scoring asset selection; this tests a literal sparse top-5 proxy using the momentum/low-volatility score.",
        "proxy_formula": "top5 equal-weight long-only excess return from efs_momentum_low_vol_breakout score",
        "strategy": "long_only_top5_equal_weighted",
    },
    "alpha_jungle_price_volume_momentum": {
        "paper_ref": "007 Alpha-Jungle",
        "paper_idea": "Alpha-Jungle examples combine price percentage change, volume, volatility, and formula diversity in an MCTS alpha search.",
        "proxy_formula": "rank(ret_3_1)+rank(turnover_126d)+rank(dolvol_126d)-rank(turnover_var_126d)",
        "strategy": "long_short_decile_value_weighted",
    },
    "alpha_jungle_volatility_compression_trend": {
        "paper_ref": "007 Alpha-Jungle",
        "paper_idea": "Alpha-Jungle examples include moving-average price changes and standard-deviation operators; this proxy tests trend after volatility compression.",
        "proxy_formula": "rank(ret_3_1)+rank(ret_12_1)-rank(rvol_21d)-rank(ivol_capm_21d)",
        "strategy": "long_short_decile_value_weighted",
    },
    "fama_value_momentum_interpretable": {
        "paper_ref": "010 FAMA",
        "paper_idea": "FAMA mines interpretable financial factors and cites momentum-style financial principles; this proxy tests a simple interpretable value/momentum/profitability factor.",
        "proxy_formula": "rank(be_me)+rank(ret_12_1)+rank(ope_be)-rank(market_equity)",
        "strategy": "long_short_decile_value_weighted",
    },
    "alphalogics_value_quality_growth": {
        "paper_ref": "015 AlphaLogics",
        "paper_idea": "AlphaLogics emphasizes market-logic-driven, interpretable factor generation; this proxy tests value, quality, growth, and leverage logic.",
        "proxy_formula": "rank(be_me)+rank(ope_be)+rank(gp_me)+rank(sale_gr1)-rank(debt_at)",
        "strategy": "long_short_decile_value_weighted",
    },
    "alphacrafter_full_stack_multifactor": {
        "paper_ref": "018 AlphaCrafter",
        "paper_idea": "AlphaCrafter combines mined factors, regime screening, and risk-constrained trading; this proxy tests a diversified value-quality-momentum-low-risk factor ensemble.",
        "proxy_formula": "rank(be_me)+rank(ope_be)+rank(ret_12_1)+rank(qmj)-rank(at_gr1)-rank(rvol_252d)",
        "strategy": "long_short_decile_value_weighted",
    },
    "alphaagents_risk_neutral_fundamental_momentum": {
        "paper_ref": "036 AlphaAgents",
        "paper_idea": "AlphaAgents risk-neutral portfolios emphasize valuation plus fundamentals/growth/momentum.",
        "proxy_formula": "rank(ret_12_1)+rank(sale_gr1)+rank(ope_be)+rank(be_me)",
        "strategy": "long_short_decile_value_weighted",
    },
    "alphaagents_risk_averse_quality_lowrisk": {
        "paper_ref": "036 AlphaAgents",
        "paper_idea": "AlphaAgents risk-averse portfolios emphasize lower volatility and stable fundamentals.",
        "proxy_formula": "rank(qmj)+rank(ope_be)+rank(be_me)-rank(rvol_252d)-rank(beta_252d)-rank(debt_at)",
        "strategy": "long_short_decile_value_weighted",
    },
    "marketsense_value_momentum_quality": {
        "paper_ref": "037 MarketSenseAI 2.0",
        "paper_idea": "MarketSenseAI factor analysis discusses value and momentum loadings, with fundamentals and price dynamics reinforcing selection.",
        "proxy_formula": "rank(be_me)+rank(ret_12_1)+rank(qmj)+rank(sale_gr1)",
        "strategy": "long_short_decile_value_weighted",
    },
    "finvision_trend_dip_risk_control": {
        "paper_ref": "040 FinVision",
        "paper_idea": "FinVision prompts prioritize holding strong upward trends, buying dips within uptrends, and risk management.",
        "proxy_formula": "rank(ret_12_1)-rank(ret_1_0)-rank(rvol_21d)+rank(qmj_safety)",
        "strategy": "long_short_decile_value_weighted",
    },
    "quantagent_volatility_breakout": {
        "paper_ref": "026 QuantAgent Holy Grail",
        "paper_idea": "QuantAgent appendix includes a VolatilityBreakoutSignal based on high breaking above a threshold relative to ATR.",
        "proxy_formula": "rank(rmax5_rvol_21d)+rank(ret_1_0)+rank(ret_3_1)-rank(rvol_21d)",
        "strategy": "long_short_decile_value_weighted",
    },
    "quantagent_three_soldiers_trend": {
        "paper_ref": "026 QuantAgent Holy Grail",
        "paper_idea": "QuantAgent appendix includes ThreeSoldier candlestick-style trend continuation signals with volume/body-size confirmation.",
        "proxy_formula": "rank(ret_1_0)+rank(ret_3_1)+rank(turnover_126d)-rank(rvol_21d)",
        "strategy": "long_short_decile_value_weighted",
    },
    "mm_drex_dynamic_router_proxy": {
        "paper_ref": "032 MM-DREX",
        "paper_idea": "MM-DREX dynamically routes trend, reversal, breakout, and risk/positioning experts.",
        "proxy_formula": "rank(ret_12_1)-rank(ret_1_0)+rank(rmax5_rvol_21d)-rank(rvol_21d)+rank(qmj_safety)",
        "strategy": "long_short_decile_value_weighted",
    },
    "guru_graham_deep_value_defensive": {
        "paper_ref": "042 GuruAgents",
        "paper_idea": "Benjamin Graham-style defensive value: cheap, liquid, profitable, low leverage, low risk.",
        "proxy_formula": "rank(be_me)+rank(cash_at)+rank(ope_be)-rank(debt_at)-rank(rvol_252d)-rank(beta_252d)",
        "strategy": "long_short_decile_value_weighted",
    },
    "guru_buffett_quality_compounder": {
        "paper_ref": "042 GuruAgents",
        "paper_idea": "Warren Buffett-style quality compounder: durable quality/profitability/growth with low leverage.",
        "proxy_formula": "rank(qmj)+rank(qmj_growth)+rank(qmj_prof)+rank(ope_be)+rank(gp_me)-rank(debt_at)",
        "strategy": "long_short_decile_value_weighted",
    },
    "guru_greenblatt_magic_formula": {
        "paper_ref": "042 GuruAgents",
        "paper_idea": "Joel Greenblatt-style magic formula: earnings yield plus business quality/return on capital.",
        "proxy_formula": "rank(ebit_mev)+rank(ope_be)+rank(gp_mev)+rank(be_me)",
        "strategy": "long_short_decile_value_weighted",
    },
    "guru_piotroski_fscore_proxy": {
        "paper_ref": "042 GuruAgents",
        "paper_idea": "Joseph Piotroski-style F-score: profitability, operating cash flow, accrual quality, leverage, issuance, and asset turnover.",
        "proxy_formula": "rank(ni_me)+rank(ocf_me)-rank(oaccruals_at)-rank(debt_gr1)-rank(eqnetis_me)+rank(at_turnover)+rank(sale_gr1)",
        "strategy": "long_short_decile_value_weighted",
    },
    "guru_altman_distress_avoidance": {
        "paper_ref": "042 GuruAgents",
        "paper_idea": "Edward Altman-style distress avoidance: earnings/cash/debt coverage and downside-risk control.",
        "proxy_formula": "rank(ebitda_debt)+rank(cash_at)+rank(ni_me)-rank(debt_at)-rank(rvol_252d)-rank(betadown_252d)",
        "strategy": "long_short_decile_value_weighted",
    },
    "guru_equal_weight_style_ensemble": {
        "paper_ref": "042 GuruAgents",
        "paper_idea": "GuruAgents combines multiple investment-guru sleeves; this is an equal-weight score ensemble of the five guru proxies.",
        "proxy_formula": "average Graham, Buffett, Greenblatt, Piotroski, Altman proxy scores",
        "strategy": "long_short_decile_value_weighted",
    },
    "hedgeagents_balanced_lowrisk_alpha": {
        "paper_ref": "044 HedgeAgents",
        "paper_idea": "HedgeAgents is framed as balanced-aware trading; this proxy tests quality/value alpha with explicit low beta/downside-risk control.",
        "proxy_formula": "rank(qmj)+rank(be_me)+rank(ope_be)-rank(rvol_252d)-rank(beta_252d)-rank(betadown_252d)",
        "strategy": "long_short_decile_value_weighted",
    },
}


def cs_rank(frame: pd.DataFrame, col: str) -> pd.Series:
    vals = pd.to_numeric(frame[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
    ranks = vals.rank(method="average", pct=True)
    return 2.0 * (ranks - 0.5)


def add_rank(frame: pd.DataFrame, out: str, col: str, sign: float = 1.0) -> None:
    frame[out] = sign * cs_rank(frame, col)


def build_scores_for_month(frame: pd.DataFrame) -> pd.DataFrame:
    f = frame.copy()
    # Atomic centered cross-sectional ranks. Positive means better on the named characteristic.
    for col in [
        "ret_1_0", "ret_3_1", "ret_6_1", "ret_12_1", "rvol_21d", "rvol_252d", "ivol_capm_21d",
        "rmax1_21d", "rmax5_21d", "rmax5_rvol_21d", "turnover_126d", "dolvol_126d", "turnover_var_126d",
        "bidaskhl_21d", "beta_252d", "betadown_252d",
        "be_me", "market_equity", "at_gr1", "ope_be", "qmj", "qmj_growth", "qmj_prof", "qmj_safety", "gp_me", "gp_mev",
        "ebit_mev", "ebitda_debt", "ni_me", "ocf_me", "oaccruals_at", "at_turnover", "debt_at", "debt_gr1",
        "cash_at", "eqnetis_me", "sale_gr1",
    ]:
        f[f"z_{col}"] = cs_rank(f, col)

    f["repo_alphabench_formulaic_price_volume"] = f["z_ret_12_1"] + f["z_ret_6_1"] + f["z_rmax5_rvol_21d"] + f["z_dolvol_126d"] - f["z_rvol_252d"] - f["z_turnover_var_126d"]
    f["repo_alphaagent_decay_resistant_quality"] = f["z_ope_be"] + f["z_ocf_me"] + f["z_qmj_safety"] + f["z_at_turnover"] - f["z_oaccruals_at"] - f["z_eqnetis_me"] - f["z_debt_gr1"]
    f["repo_rd_agent_factor_model_compact_ensemble"] = f["z_be_me"] + f["z_ope_be"] + f["z_gp_me"] + f["z_ret_12_1"] - f["z_rvol_252d"] - f["z_beta_252d"] - f["z_at_gr1"]
    f["repo_alphaprobe_dag_diverse_factor_blend"] = f["z_ret_12_1"] - f["z_ret_1_0"] + f["z_be_me"] + f["z_ope_be"] + f["z_qmj_safety"] + f["z_turnover_126d"] - f["z_rvol_252d"] - f["z_debt_at"]
    f["repo_quantagent_hft_price_pattern"] = f["z_ret_1_0"] + f["z_ret_3_1"] + f["z_rmax1_21d"] + f["z_rmax5_rvol_21d"] + f["z_turnover_126d"] - f["z_bidaskhl_21d"] - f["z_rvol_21d"]
    f["repo_fincon_cvar_risk_controlled_allocator"] = f["z_ret_12_1"] + f["z_ope_be"] + f["z_qmj_safety"] + f["z_dolvol_126d"] - f["z_rvol_252d"] - f["z_beta_252d"] - f["z_betadown_252d"]
    f["repo_trading_r1_risk_adjusted_reasoning"] = f["z_ret_3_1"] + f["z_ret_12_1"] - f["z_ret_1_0"] + f["z_qmj_safety"] - f["z_rvol_21d"] - f["z_rmax5_21d"]
    f["repo_alphaforgebench_executable_multifactor"] = f["z_be_me"] + f["z_ope_be"] + f["z_ret_12_1"] + f["z_qmj"] + f["z_dolvol_126d"] - f["z_rvol_252d"] - f["z_debt_at"]
    f["repo_livetradebench_live_allocation_proxy"] = f["z_ret_12_1"] + f["z_qmj"] + f["z_qmj_safety"] + f["z_dolvol_126d"] - f["z_rvol_252d"] - f["z_beta_252d"]
    f["repo_deepfund_prudent_fund_manager"] = f["z_qmj"] + f["z_ope_be"] + f["z_gp_me"] + f["z_cash_at"] + f["z_ret_12_1"] - f["z_debt_at"] - f["z_rvol_252d"] - f["z_beta_252d"]
    f["repo_tradetrap_robust_safety_proxy"] = f["z_qmj_safety"] + f["z_dolvol_126d"] + f["z_cash_at"] - f["z_rvol_252d"] - f["z_beta_252d"] - f["z_bidaskhl_21d"] - f["z_debt_at"]
    f["repo_quantevolver_return_sharpe_proxy"] = pd.to_numeric(f["ret_12_1"], errors="coerce") / (pd.to_numeric(f["rvol_252d"], errors="coerce").abs() + 1e-8)
    f["paper_factorminer_memory_diverse_library"] = f["z_ret_12_1"] + f["z_be_me"] + f["z_ope_be"] + f["z_qmj_safety"] + f["z_at_turnover"] - f["z_rvol_252d"] - f["z_debt_at"] - f["z_eqnetis_me"]
    f["paper_cogalpha_code_evolved_hybrid"] = f["z_ret_12_1"] + f["z_ret_3_1"] + f["z_dolvol_126d"] + f["z_qmj"] - f["z_bidaskhl_21d"] - f["z_rvol_252d"] - f["z_turnover_var_126d"]
    f["paper_alpha_gpt_interactive_formula"] = f["z_be_me"] + f["z_ret_12_1"] + f["z_ope_be"] + f["z_gp_me"] - f["z_debt_at"]
    f["paper_alpha_gpt2_full_pipeline"] = f["z_be_me"] + f["z_ret_12_1"] + f["z_qmj"] + f["z_sale_gr1"] - f["z_rvol_252d"] - f["z_beta_252d"]
    f["paper_chain_of_alpha_formula_chain"] = f["z_ret_12_1"] - f["z_ret_1_0"] + f["z_rmax5_rvol_21d"] + f["z_turnover_126d"] - f["z_rvol_252d"]
    f["paper_factormad_debate_interpretable"] = f["z_be_me"] + f["z_ope_be"] + f["z_qmj_safety"] + f["z_ret_12_1"] - f["z_debt_at"] - f["z_rvol_252d"]
    f["paper_alphaagentevo_evolved_seed"] = f["z_ret_12_1"] + f["z_ret_6_1"] + f["z_ope_be"] + f["z_qmj_safety"] - f["z_rvol_252d"] - f["z_at_gr1"] - f["z_eqnetis_me"]
    f["paper_llmfactor_explainable_price_news"] = f["z_ret_12_1"] + f["z_sale_gr1"] + f["z_gp_me"] + f["z_dolvol_126d"] - f["z_rvol_252d"]
    f["paper_factorengine_program_knowledge"] = f["z_be_me"] + f["z_ope_be"] + f["z_gp_me"] + f["z_ocf_me"] - f["z_oaccruals_at"] - f["z_debt_at"] - f["z_at_gr1"]
    f["paper_finagent_multimodal_generalist"] = f["z_qmj"] + f["z_ret_12_1"] + f["z_dolvol_126d"] + f["z_cash_at"] - f["z_rvol_252d"] - f["z_beta_252d"] - f["z_debt_at"]
    f["paper_flag_trader_gradient_policy"] = f["z_ret_3_1"] + f["z_ret_12_1"] - f["z_ret_1_0"] + f["z_qmj_safety"] - f["z_rvol_21d"] - f["z_beta_252d"]
    f["paper_janus_q_event_driven_proxy"] = f["z_rmax5_rvol_21d"] + f["z_ret_1_0"] + f["z_turnover_126d"] + f["z_qmj_safety"] - f["z_rvol_21d"] - f["z_bidaskhl_21d"]
    f["paper_timi_minutes_technical_proxy"] = f["z_ret_1_0"] + f["z_ret_3_1"] + f["z_rmax1_21d"] + f["z_turnover_126d"] - f["z_rvol_21d"] - f["z_bidaskhl_21d"]
    f["paper_mountainlion_multimodal_allocation"] = f["z_ret_12_1"] + f["z_qmj"] + f["z_qmj_safety"] + f["z_sale_gr1"] - f["z_rvol_252d"] - f["z_beta_252d"]
    f["paper_p1gpt_structured_workflow"] = f["z_ret_12_1"] + f["z_be_me"] + f["z_ope_be"] + f["z_sale_gr1"] + f["z_qmj_safety"] - f["z_rvol_252d"] - f["z_debt_at"]
    f["paper_quantagents_risk_controlled_system"] = f["z_ret_12_1"] + f["z_qmj_safety"] + f["z_dolvol_126d"] + f["z_cash_at"] - f["z_rvol_252d"] - f["z_beta_252d"] - f["z_debt_at"]
    f["code_quantaalpha_self_evolving_factor"] = f["z_ret_12_1"] + f["z_ope_be"] + f["z_gp_me"] + f["z_qmj"] - f["z_rvol_252d"] - f["z_debt_at"]
    f["code_alpha_r1_reasoning_screen"] = f["z_qmj"] + f["z_ope_be"] + f["z_ret_12_1"] - f["z_debt_at"] - f["z_rvol_252d"]
    f["code_alphaforge_program_factor"] = f["z_be_me"] + f["z_ret_12_1"] + f["z_ope_be"] + f["z_dolvol_126d"] - f["z_rvol_252d"]
    f["code_alphagen_symbolic_factor"] = f["z_ret_12_1"] - f["z_ret_1_0"] + f["z_be_me"] + f["z_ope_be"] - f["z_rvol_252d"]
    f["code_tradingagents_multi_agent"] = f["z_ret_12_1"] + f["z_dolvol_126d"] + f["z_qmj_safety"] + f["z_sale_gr1"] - f["z_rvol_252d"] - f["z_beta_252d"]
    f["code_alphaquanter_tool_orchestrated_rl"] = f["z_ret_3_1"] + f["z_ret_12_1"] + f["z_turnover_126d"] - f["z_rvol_21d"] - f["z_beta_252d"]
    f["code_finmem_memory_trend"] = f["z_ret_12_1"] - f["z_ret_1_0"] + f["z_qmj_safety"] + f["z_cash_at"] - f["z_rvol_252d"]
    f["code_ai_trader_value_quality"] = f["z_be_me"] + f["z_qmj"] + f["z_ope_be"] + f["z_cash_at"] - f["z_debt_at"] - f["z_rvol_252d"]
    f["code_agentictrading_lab_allocation"] = f["z_ret_12_1"] + f["z_qmj"] + f["z_dolvol_126d"] - f["z_rvol_252d"] - f["z_beta_252d"]
    f["code_ai_hedge_fund_buffett_munger"] = f["z_qmj"] + f["z_qmj_prof"] + f["z_ope_be"] + f["z_gp_me"] + f["z_cash_at"] - f["z_debt_at"]
    f["code_vibe_trading_prompt_allocation"] = f["z_ret_12_1"] + f["z_qmj"] + f["z_dolvol_126d"] - f["z_rvol_252d"]
    f["efs_momentum_low_vol_breakout"] = f["z_ret_3_1"] + f["z_ret_6_1"] + f["z_ret_12_1"] - f["z_rvol_21d"] - f["z_rvol_252d"] + f["z_rmax5_rvol_21d"]
    f["efs_short_reversal_low_noise"] = -f["z_ret_1_0"] - f["z_rvol_21d"] + f["z_qmj_safety"]
    f["efs_sparse_top5_momentum_low_vol"] = f["efs_momentum_low_vol_breakout"]
    f["alpha_jungle_price_volume_momentum"] = f["z_ret_3_1"] + f["z_turnover_126d"] + f["z_dolvol_126d"] - f["z_turnover_var_126d"]
    f["alpha_jungle_volatility_compression_trend"] = f["z_ret_3_1"] + f["z_ret_12_1"] - f["z_rvol_21d"] - f["z_ivol_capm_21d"]
    f["fama_value_momentum_interpretable"] = f["z_be_me"] + f["z_ret_12_1"] + f["z_ope_be"] - f["z_market_equity"]
    f["alphalogics_value_quality_growth"] = f["z_be_me"] + f["z_ope_be"] + f["z_gp_me"] + f["z_sale_gr1"] - f["z_debt_at"]
    f["alphacrafter_full_stack_multifactor"] = f["z_be_me"] + f["z_ope_be"] + f["z_ret_12_1"] + f["z_qmj"] - f["z_at_gr1"] - f["z_rvol_252d"]
    f["alphaagents_risk_neutral_fundamental_momentum"] = f["z_ret_12_1"] + f["z_sale_gr1"] + f["z_ope_be"] + f["z_be_me"]
    f["alphaagents_risk_averse_quality_lowrisk"] = f["z_qmj"] + f["z_ope_be"] + f["z_be_me"] - f["z_rvol_252d"] - f["z_beta_252d"] - f["z_debt_at"]
    f["marketsense_value_momentum_quality"] = f["z_be_me"] + f["z_ret_12_1"] + f["z_qmj"] + f["z_sale_gr1"]
    f["finvision_trend_dip_risk_control"] = f["z_ret_12_1"] - f["z_ret_1_0"] - f["z_rvol_21d"] + f["z_qmj_safety"]
    f["quantagent_volatility_breakout"] = f["z_rmax5_rvol_21d"] + f["z_ret_1_0"] + f["z_ret_3_1"] - f["z_rvol_21d"]
    f["quantagent_three_soldiers_trend"] = f["z_ret_1_0"] + f["z_ret_3_1"] + f["z_turnover_126d"] - f["z_rvol_21d"]
    f["mm_drex_dynamic_router_proxy"] = f["z_ret_12_1"] - f["z_ret_1_0"] + f["z_rmax5_rvol_21d"] - f["z_rvol_21d"] + f["z_qmj_safety"]
    f["guru_graham_deep_value_defensive"] = f["z_be_me"] + f["z_cash_at"] + f["z_ope_be"] - f["z_debt_at"] - f["z_rvol_252d"] - f["z_beta_252d"]
    f["guru_buffett_quality_compounder"] = f["z_qmj"] + f["z_qmj_growth"] + f["z_qmj_prof"] + f["z_ope_be"] + f["z_gp_me"] - f["z_debt_at"]
    f["guru_greenblatt_magic_formula"] = f["z_ebit_mev"] + f["z_ope_be"] + f["z_gp_mev"] + f["z_be_me"]
    f["guru_piotroski_fscore_proxy"] = f["z_ni_me"] + f["z_ocf_me"] - f["z_oaccruals_at"] - f["z_debt_gr1"] - f["z_eqnetis_me"] + f["z_at_turnover"] + f["z_sale_gr1"]
    f["guru_altman_distress_avoidance"] = f["z_ebitda_debt"] + f["z_cash_at"] + f["z_ni_me"] - f["z_debt_at"] - f["z_rvol_252d"] - f["z_betadown_252d"]
    f["guru_equal_weight_style_ensemble"] = f[[
        "guru_graham_deep_value_defensive", "guru_buffett_quality_compounder", "guru_greenblatt_magic_formula",
        "guru_piotroski_fscore_proxy", "guru_altman_distress_avoidance"
    ]].mean(axis=1)
    f["hedgeagents_balanced_lowrisk_alpha"] = f["z_qmj"] + f["z_be_me"] + f["z_ope_be"] - f["z_rvol_252d"] - f["z_beta_252d"] - f["z_betadown_252d"]
    return f


def equal_weight_top_n(frame: pd.DataFrame, score_col: str, n_top: int, min_side: int) -> float:
    x = frame[[score_col, "ret_exc_lead1m"]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < max(n_top, min_side):
        return float("nan")
    top = x.sort_values(score_col, ascending=False).head(n_top)
    if len(top) < min_side:
        return float("nan")
    return float(pd.to_numeric(top["ret_exc_lead1m"], errors="coerce").mean())

def value_weight_top_quantile(frame: pd.DataFrame, score_col: str, quantile: float, min_side: int) -> float:
    x = frame[[score_col, "ret_exc_lead1m", "weight"]].replace([np.inf, -np.inf], np.nan).dropna()
    x = x[x["weight"] > 0]
    if len(x) < max(min_side, 10):
        return float("nan")
    threshold = x[score_col].quantile(quantile)
    top = x[x[score_col] >= threshold]
    if len(top) < min_side:
        return float("nan")
    return weighted_mean(top["ret_exc_lead1m"], top["weight"])


def build_factor_panel(raw: pd.DataFrame, months: list[pd.Timestamp], quantile: float, min_side: int) -> pd.DataFrame:
    rows = []
    for month in months:
        frame = raw[raw["month"] == month]
        row = {"month": pd.Timestamp(month) + pd.offsets.MonthEnd(0)}
        row["jkp_topn_mkt"] = weighted_mean(frame["ret_exc_lead1m"], frame["weight"])
        row["n_stocks"] = int(frame["permno"].nunique())
        for col in BENCHMARK_COLS:
            row[f"char__{col}"] = long_short_one_month(frame, col, quantile, min_side)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("month")


def build_candidate_returns(raw: pd.DataFrame, months: list[pd.Timestamp], quantile: float, min_side: int) -> dict[str, pd.DataFrame]:
    rows = {name: [] for name in IDEA_DEFINITIONS}
    score_snapshots = []
    for month in months:
        scored = build_scores_for_month(raw[raw["month"] == month])
        score_snapshots.append(scored[["month", "permno", "weight", *IDEA_DEFINITIONS.keys()]])
        for name, meta in IDEA_DEFINITIONS.items():
            if meta["strategy"] == "long_only_top5_equal_weighted":
                ret = equal_weight_top_n(scored, name, n_top=5, min_side=5)
            elif meta["strategy"] == "long_only_top_decile_value_weighted":
                ret = value_weight_top_quantile(scored, name, quantile=0.9, min_side=min_side)
            else:
                ret = long_short_one_month(scored, name, quantile, min_side)
            rows[name].append({"month": pd.Timestamp(month) + pd.offsets.MonthEnd(0), "candidate_return": ret})
    return {name: pd.DataFrame(vals).sort_values("month") for name, vals in rows.items()}


def build_contest_candidate(out_dir: Path, base_returns: dict[str, pd.DataFrame], lookback: int = 36, min_history: int = 24) -> pd.DataFrame:
    sleeve_names = [n for n, meta in IDEA_DEFINITIONS.items() if meta["strategy"] != "long_only_top5_equal_weighted"]
    wide = None
    for name in sleeve_names:
        df = base_returns[name].rename(columns={"candidate_return": name})
        wide = df if wide is None else wide.merge(df, on="month", how="outer")
    wide = wide.sort_values("month").reset_index(drop=True)
    choices = []
    out_rows = []
    for i, row in wide.iterrows():
        if i < min_history:
            out_rows.append({"month": row["month"], "candidate_return": np.nan})
            choices.append({"month": row["month"], "selected_sleeve": "insufficient_history", "trailing_sharpe": np.nan})
            continue
        hist = wide.iloc[max(0, i - lookback):i][sleeve_names].astype("float64")
        mean = hist.mean(skipna=True)
        std = hist.std(skipna=True, ddof=1)
        sr = np.sqrt(12.0) * mean / std.replace(0.0, np.nan)
        selected = sr.replace([np.inf, -np.inf], np.nan).dropna().sort_values(ascending=False)
        if selected.empty:
            out_rows.append({"month": row["month"], "candidate_return": np.nan})
            choices.append({"month": row["month"], "selected_sleeve": "no_valid_sleeve", "trailing_sharpe": np.nan})
            continue
        sleeve = selected.index[0]
        out_rows.append({"month": row["month"], "candidate_return": row[sleeve]})
        choices.append({"month": row["month"], "selected_sleeve": sleeve, "trailing_sharpe": float(selected.iloc[0])})
    choices_df = pd.DataFrame(choices)
    choices_df.to_csv(out_dir / "contesttrade_internal_contest_choices.csv", index=False)
    return pd.DataFrame(out_rows)


def evaluate_candidate(candidate_csv: Path, factor_panel_csv: Path, candidate_id: str, out_dir: Path) -> None:
    subprocess.run([
        ".venv/bin/python", "scripts/evaluate_candidate_returns_jkp.py",
        "--candidate-csv", str(candidate_csv),
        "--factor-panel-csv", str(factor_panel_csv),
        "--candidate-id", candidate_id,
        "--out-dir", str(out_dir),
    ], check=True, stdout=subprocess.DEVNULL)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("paper_runs/idea_replications/jkp_paper_idea_proxies"))
    parser.add_argument("--usa-path", type=Path, default=DEFAULT_JKP_USA)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--top-n", type=int, default=1000)
    parser.add_argument("--quantile", type=float, default=0.1)
    parser.add_argument("--min-side", type=int, default=20)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    validate_columns(args.usa_path, BASE_COLS)
    raw = pd.read_parquet(args.usa_path, columns=BASE_COLS)
    raw["month"] = pd.to_datetime(raw["eom"], errors="coerce") + pd.offsets.MonthEnd(0)
    raw["ret_exc_lead1m"] = pd.to_numeric(raw["ret_exc_lead1m"], errors="coerce")
    raw["weight"] = pd.to_numeric(raw["me"], errors="coerce")
    raw = raw[(raw["month"] >= pd.Timestamp(args.start)) & (raw["month"] <= pd.Timestamp(args.end))].copy()
    raw = raw.replace([np.inf, -np.inf], np.nan).dropna(subset=["month", "permno", "ret_exc_lead1m", "weight"])
    raw = raw[raw["weight"] > 0]
    if args.top_n > 0:
        raw["_size_rank"] = raw.groupby("month")["weight"].rank(method="first", ascending=False)
        raw = raw[raw["_size_rank"] <= args.top_n].drop(columns=["_size_rank"]).copy()

    months = sorted(raw["month"].dropna().unique())
    factor_panel = build_factor_panel(raw, months, args.quantile, args.min_side)
    factor_panel_path = args.out_dir / "jkp_benchmark_factor_panel.csv"
    factor_panel.to_csv(factor_panel_path, index=False)

    candidate_returns = build_candidate_returns(raw, months, args.quantile, args.min_side)
    candidate_paths = {}
    for name, df in candidate_returns.items():
        path = args.out_dir / f"candidate_returns_{name}.csv"
        df.to_csv(path, index=False)
        candidate_paths[name] = str(path)

    contest_name = "contesttrade_internal_contest_trailing_sharpe"
    contest_df = build_contest_candidate(args.out_dir, candidate_returns)
    contest_path = args.out_dir / f"candidate_returns_{contest_name}.csv"
    contest_df.to_csv(contest_path, index=False)
    candidate_paths[contest_name] = str(contest_path)
    contest_meta = {
        "paper_ref": "024 ContestTrade",
        "paper_idea": "ContestTrade uses an internal contest/ranking mechanism among agents. This proxy selects the JKP idea sleeve with the best trailing 36-month realized Sharpe using only past generated JKP returns.",
        "proxy_formula": "monthly winner among idea sleeves by trailing 36m Sharpe, min 24m history",
        "strategy": "meta_sleeve_selection_trailing_sharpe",
    }

    all_definitions = {**IDEA_DEFINITIONS, contest_name: contest_meta}
    summary_frames = []
    for name, path in candidate_paths.items():
        out = args.out_dir / f"results_{name}"
        evaluate_candidate(Path(path), factor_panel_path, name, out)
        metrics = pd.read_csv(out / "jkp_ff_benchmark_metrics.csv")
        summary_frames.append(metrics)

    summary = pd.concat(summary_frames, ignore_index=True)
    summary.to_csv(args.out_dir / "paper_idea_proxy_all_benchmark_metrics.csv", index=False)
    ff5 = summary[summary["benchmark_set"].eq("FF5MOM_JKP")].copy()
    for key, meta in all_definitions.items():
        ff5.loc[ff5["candidate_id"].eq(key), "paper_ref"] = meta["paper_ref"]
        ff5.loc[ff5["candidate_id"].eq(key), "paper_idea"] = meta["paper_idea"]
        ff5.loc[ff5["candidate_id"].eq(key), "proxy_formula"] = meta["proxy_formula"]
        ff5.loc[ff5["candidate_id"].eq(key), "strategy"] = meta["strategy"]
    ff5["beats_ff5mom_positive_alpha_5pct"] = (
        (pd.to_numeric(ff5["alpha_annualized"], errors="coerce") > 0)
        & (pd.to_numeric(ff5["appraisal_ratio"], errors="coerce") > 0)
        & (pd.to_numeric(ff5["alpha_tstat_hac"], errors="coerce") > 1.96)
        & (pd.to_numeric(ff5["combined_minus_old_sharpe"], errors="coerce") > 0)
        & (ff5["grs_reject_5pct"].astype(str).str.lower().eq("true"))
    )
    ff5 = ff5.sort_values(["beats_ff5mom_positive_alpha_5pct", "alpha_tstat_hac", "appraisal_ratio"], ascending=[False, False, False])
    ff5.to_csv(args.out_dir / "paper_idea_proxy_ff5mom_summary.csv", index=False)

    metadata = {
        "input_policy": "candidate and benchmark returns built only from read-only JKP USA.parquet; no China, yfinance, paper-shipped returns, official French factors, or external return files",
        "usa_path": str(args.usa_path),
        "start": args.start,
        "end": args.end,
        "top_n_by_me_per_month": args.top_n,
        "quantile": args.quantile,
        "min_side": args.min_side,
        "n_months": int(len(factor_panel)),
        "n_rows_loaded_after_filters": int(len(raw)),
        "factor_panel_csv": str(factor_panel_path),
        "candidate_paths": candidate_paths,
        "candidate_definitions": all_definitions,
        "ff5mom_summary_csv": str(args.out_dir / "paper_idea_proxy_ff5mom_summary.csv"),
        "all_metrics_csv": str(args.out_dir / "paper_idea_proxy_all_benchmark_metrics.csv"),
    }
    (args.out_dir / "paper_idea_proxy_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "n_candidates": len(candidate_paths),
        "n_ff5_rows": int(len(ff5)),
        "n_beating_ff5mom": int(ff5["beats_ff5mom_positive_alpha_5pct"].sum()),
        "ff5mom_summary_csv": str(args.out_dir / "paper_idea_proxy_ff5mom_summary.csv"),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
