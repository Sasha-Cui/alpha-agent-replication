#!/usr/bin/env python3
"""Audit every numeric/EMCL table result in the final MASS primary record.

The audit inventories the released market panel and safely decodes the pinned
agent-distribution snapshot after enforcing a narrow pickle-opcode allowlist.
It never calls an LLM endpoint and never treats internal optimizer state as a
published signal, portfolio, cost measurement, or result reproduction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import pickle
import pickletools
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import pandas as pd


SOURCE_COMMIT = "68edcaae9e6ac099d28eed90513219495b0852b7"
SOURCE_ROOT_COMMIT = "b358fe9241abc213d1c7560afbda74dd51ce2c39"
ANONYMOUS_SOURCE_COMMIT = "67f80e88c6af3124d6821d8a1682c5a787cf45bb"
PAPER_V1_SHA256 = "19a1845c9f199a532143957ef205c68843078a5290bb647ecb47db35d2ee20bd"
PAPER_SHA256 = "c31e68b722b6c4d33dd69833b48a34de8fc29ec4171498f320307ede554e6135"
PAPER_URL = "https://arxiv.org/pdf/2505.10278"
SOURCE_URL = "https://github.com/gta0804/MASS"
ANONYMOUS_SOURCE_URL = "https://github.com/anonymous3728/MASS_anonoymous"
OPENREVIEW_URL = "https://openreview.net/forum?id=NNpE9iiPNR"
OPENREVIEW_ARCHIVE_URL = "https://anonymous.4open.science/r/MASS-AC96"
OPENREVIEW_FINAL_PDF_SHA256 = "92697642e0f68afb3679a47ed32be46e705fbe3e670a78b2930a691d1425d385"
SNAPSHOT_SHA256 = "be7d40a8f0191bb6ee246b3a8537851b088be685afb52b51d823dde587f1a895"

SOURCE_HISTORY_COMMITS = (
    "b358fe9241abc213d1c7560afbda74dd51ce2c39",
    "b12c11246d514ec937e6208714f3795880425b2a",
    "a42db433a69704170d6b3105e63f8fe02f36121c",
    "9c68b4bb0328be3199b1b84376dffa0f7215aab6",
    "b1272d2803528751ce0d80510eabed2b4e48c659",
    "7e35bb9678379fcfdd5559201280d863fa42e64a",
    "f6d9caf5628fa55924def65d0adf83cb81b12975",
    "98f07a816e574cc2c2ca9a2db0f74c5a57f034dd",
    "b0c69982d7ebfd4e87c56c06669a42d8f3e8ebd0",
    "b4dc29535a5761e217e38ca8cd1846e83814b295",
    "c6af13ae0e61b2a0a5dd1539ab0206ada788c093",
    "10ee192bee84ce4791496c44132f4a5b7702f189",
    SOURCE_COMMIT,
)

HISTORICAL_DELETED_CODE_PATHS = (
    "README.en.md",
    "stock_disagreement/main_dtml.py",
    "stock_disagreement/model/DTML.py",
    "stock_disagreement/model/__init__.py",
    "stock_disagreement/utils/clean_news.py",
    "stock_disagreement/utils/industry_index.py",
)

IGNORED_OUTPUT_PATHS = (
    "stock_disagreement/all_dataset",
    "stock_disagreement/lightgbm_disagreement_res",
    "stock_disagreement/backtest_res",
    "stock_disagreement/res",
    "stock_disagreement/notebooks",
)

TABLE_1_METRICS = ("rank_ic_pct", "rank_icir_pct", "ic_pct", "icir_pct")
TABLE_2_METRICS = TABLE_1_METRICS
TABLE_3_METRICS = ("average_daily_time_seconds", "average_daily_api_cost_usd")
TABLE_4_METRICS = ("annualized_return_pct", "sharpe_ratio", "max_drawdown_pct")


# Transcribed from Tables 1--4 of pinned arXiv v2. Each line is
# section|pool|method|the metrics for that table in the order declared above.
TABLE_1_TEXT = """
main_2023|SSE50|proxy_indicator|3.82|19.73|2.89|16.63
main_2023|CSI_300|proxy_indicator|3.84|30.44|3.60|27.03
main_2023|ChiNext_100|proxy_indicator|-0.94|-7.05|0.16|1.29
main_2023|SSE50|lightgbm|3.25|21.78|4.51|27.30
main_2023|CSI_300|lightgbm|5.20|36.06|3.19|23.62
main_2023|ChiNext_100|lightgbm|2.94|30.69|0.88|8.70
main_2023|SSE50|dtml|5.04|28.15|4.93|26.71
main_2023|CSI_300|dtml|4.91|35.72|4.17|31.10
main_2023|ChiNext_100|dtml|3.45|26.55|3.21|21.97
main_2023|SSE50|master|5.13|28.37|4.97|27.01
main_2023|CSI_300|master|5.01|35.47|4.23|30.78
main_2023|ChiNext_100|master|3.92|31.03|4.07|28.62
main_2023|SSE50|sep|4.79|27.56|4.16|26.40
main_2023|CSI_300|sep|3.83|5.42|0.61|7.65
main_2023|ChiNext_100|sep|4.81|34.88|5.29|36.98
main_2023|SSE50|fincon|4.88|26.18|4.35|25.67
main_2023|CSI_300|fincon|0.70|9.57|0.96|13.42
main_2023|ChiNext_100|fincon|5.01|37.18|5.53|40.54
main_2023|SSE50|tradingagents|4.92|27.71|4.33|25.69
main_2023|CSI_300|tradingagents|3.01|10.14|1.02|14.80
main_2023|ChiNext_100|tradingagents|5.37|38.15|5.60|41.06
main_2023|SSE50|mass|8.16|41.74|5.90|33.43
main_2023|CSI_300|mass|6.50|43.49|4.65|33.32
main_2023|ChiNext_100|mass|7.62|62.87|6.28|55.88
leakage_2025_q1|SSE50|mass|4.50|24.41|6.12|38.33
leakage_2025_q1|CSI_300|mass|3.91|37.44|3.36|34.56
leakage_2025_q1|CSI_A500|mass|5.19|56.17|4.66|48.82
"""

TABLE_2_TEXT = """
ablation_2023|SSE50|without_csp|1.65|11.19|1.67|11.73
ablation_2023|CSI_300|without_csp|EMCL|EMCL|EMCL|EMCL
ablation_2023|ChiNext_100|without_csp|EMCL|EMCL|EMCL|EMCL
ablation_2023|SSE50|without_pmd|5.25|29.75|3.43|21.10
ablation_2023|CSI_300|without_pmd|2.57|33.38|2.23|30.64
ablation_2023|ChiNext_100|without_pmd|2.26|17.16|2.99|22.70
ablation_2023|SSE50|without_bo|0.76|4.75|-0.13|-8.44
ablation_2023|CSI_300|without_bo|0.36|5.36|0.41|6.69
ablation_2023|ChiNext_100|without_bo|2.88|19.43|3.12|22.03
ablation_2023|SSE50|without_mdh|6.28|32.68|3.85|25.39
ablation_2023|CSI_300|without_mdh|4.65|31.03|2.98|27.86
ablation_2023|ChiNext_100|without_mdh|-3.12|-28.93|-2.46|-26.44
ablation_2023|SSE50|mass_daily_updated_pool|8.03|41.68|5.79|33.52
ablation_2023|CSI_300|mass_daily_updated_pool|6.48|42.86|4.52|32.95
ablation_2023|ChiNext_100|mass_daily_updated_pool|7.65|63.02|6.29|55.91
ablation_2023|SSE50|mass|8.16|41.74|5.90|33.43
ablation_2023|CSI_300|mass|6.50|43.49|4.65|33.32
ablation_2023|ChiNext_100|mass|7.62|62.87|6.28|55.88
"""

TABLE_3_TEXT = """
cost_512_agents|SSE50|mass|125|0.679
cost_512_agents|CSI_300|mass|378|2.265
cost_512_agents|ChiNext_100|mass|227|1.192
"""

TABLE_4_TEXT = """
main_2023|SSE50|proxy_indicator|-2.39|-1.22|14.04
main_2023|CSI_300|proxy_indicator|-3.60|-1.62|20.57
main_2023|ChiNext_100|proxy_indicator|-20.01|-3.24|24.15
main_2023|SSE50|lightgbm|-1.88|-1.14|13.16
main_2023|CSI_300|lightgbm|-4.55|-2.12|18.57
main_2023|ChiNext_100|lightgbm|-19.32|-3.01|23.96
main_2023|SSE50|dtml|-1.69|-1.08|12.99
main_2023|CSI_300|dtml|-0.33|-0.14|22.34
main_2023|ChiNext_100|dtml|-8.23|-3.20|24.55
main_2023|SSE50|master|-1.67|-0.92|12.91
main_2023|CSI_300|master|0.79|0.33|22.05
main_2023|ChiNext_100|master|-7.88|-3.17|24.06
main_2023|SSE50|sep|-2.01|-1.07|13.12
main_2023|CSI_300|sep|-10.24|-4.32|22.67
main_2023|ChiNext_100|sep|-6.84|-3.14|24.01
main_2023|SSE50|fincon|-1.82|-0.98|13.05
main_2023|CSI_300|fincon|-9.25|-3.28|23.74
main_2023|ChiNext_100|fincon|-6.01|-2.80|23.75
main_2023|SSE50|tradingagents|-2.44|-1.71|13.15
main_2023|CSI_300|tradingagents|-7.19|-3.02|19.61
main_2023|ChiNext_100|tradingagents|-4.65|-2.82|23.84
main_2023|SSE50|mass|2.16|1.98|11.98
main_2023|CSI_300|mass|4.95|2.23|14.04
main_2023|ChiNext_100|mass|1.17|0.99|19.06
main_2023|SSE50|stock_pool_index|-9.98|-2.37|21.62
main_2023|CSI_300|stock_pool_index|-9.75|-2.92|21.44
main_2023|ChiNext_100|stock_pool_index|-19.18|-3.17|32.26
leakage_2025_q1|SSE50|mass|9.74|2.42|2.91
leakage_2025_q1|CSI_300|mass|9.36|2.66|2.99
leakage_2025_q1|CSI_A500|mass|11.34|2.93|4.08
leakage_2025_q1|SSE50|stock_pool_index|-1.88|-2.97|5.63
leakage_2025_q1|CSI_300|stock_pool_index|-3.88|-3.15|5.86
leakage_2025_q1|CSI_A500|stock_pool_index|-1.28|-3.26|6.04
"""


# Final ICLR-2026 revision deltas versus arXiv v2. The unchanged arXiv-v2
# values stay in TABLE_1/2/3/4_TEXT; these lines contain only added or changed
# numeric result rows in final Tables 1, 4--8. Table 3 is descriptive metadata.
FINAL_TABLE_1_ADDITIONS = """
main_2023|SSE50|factorvae|5.05|38.27|4.89|26.56
main_2023|CSI_300|factorvae|4.95|34.89|4.16|31.13
main_2023|ChiNext_100|factorvae|3.98|28.69|4.03|29.35
main_2023|SSE50|hirevae|5.17|29.06|5.02|29.93
main_2023|CSI_300|hirevae|5.23|36.21|4.22|31.08
main_2023|ChiNext_100|hirevae|4.03|32.25|4.14|30.08
main_2023|SSE50|mass_gpt_oss_120b|8.24|41.96|5.91|33.28
main_2023|CSI_300|mass_gpt_oss_120b|6.62|41.96|4.63|30.19
main_2023|ChiNext_100|mass_gpt_oss_120b|7.66|61.56|6.43|54.29
leakage_2025_q1|SSE50|proxy_indicator|1.46|10.60|1.51|9.89
leakage_2025_q1|CSI_300|proxy_indicator|1.52|10.37|2.01|14.28
leakage_2025_q1|CSI_A500|proxy_indicator|1.04|9.75|0.98|9.97
leakage_2025_q1|SSE50|lightgbm|1.66|12.35|1.58|11.73
leakage_2025_q1|CSI_300|lightgbm|1.59|8.79|1.85|11.97
leakage_2025_q1|CSI_A500|lightgbm|1.77|12.84|1.58|12.60
leakage_2025_q1|SSE50|factorvae|3.59|21.61|5.41|31.14
leakage_2025_q1|CSI_300|factorvae|3.37|29.67|2.65|26.96
leakage_2025_q1|CSI_A500|factorvae|4.32|40.87|4.01|36.70
leakage_2025_q1|SSE50|hirevae|3.68|21.52|5.44|30.15
leakage_2025_q1|CSI_300|hirevae|3.47|31.58|2.61|27.93
leakage_2025_q1|CSI_A500|hirevae|4.24|42.69|3.91|36.94
leakage_2025_q1|SSE50|dtml|3.53|20.94|5.28|28.77
leakage_2025_q1|CSI_300|dtml|3.39|28.86|2.54|27.78
leakage_2025_q1|CSI_A500|dtml|4.06|41.80|3.75|35.22
leakage_2025_q1|SSE50|master|3.70|21.38|5.49|30.26
leakage_2025_q1|CSI_300|master|3.46|29.74|2.58|28.47
leakage_2025_q1|CSI_A500|master|4.13|45.52|3.89|36.67
leakage_2025_q1|SSE50|sep|3.65|20.92|5.47|29.99
leakage_2025_q1|CSI_300|sep|1.45|10.06|0.84|9.76
leakage_2025_q1|CSI_A500|sep|4.25|46.31|3.96|38.75
leakage_2025_q1|SSE50|fincon|3.97|22.03|5.68|31.42
leakage_2025_q1|CSI_300|fincon|1.54|13.98|0.80|10.72
leakage_2025_q1|CSI_A500|fincon|4.81|48.25|4.34|43.96
leakage_2025_q1|SSE50|tradingagents|4.02|21.94|5.71|31.99
leakage_2025_q1|CSI_300|tradingagents|3.63|29.80|2.97|30.63
leakage_2025_q1|CSI_A500|tradingagents|4.86|48.95|4.20|43.94
leakage_2025_q1|SSE50|mass_gpt_oss_120b|4.56|24.56|6.31|37.98
leakage_2025_q1|CSI_300|mass_gpt_oss_120b|3.75|35.86|3.31|33.80
leakage_2025_q1|CSI_A500|mass_gpt_oss_120b|5.27|54.72|4.68|46.05
"""

FINAL_TABLE_4_TEXT = """
cooling_rate|CSI_300|1.00|-0.16|-3.58|-0.27|-4.99
cooling_rate|CSI_300|0.98|5.79|39.68|4.21|30.81
cooling_rate|CSI_300|0.95|6.50|43.49|4.65|33.32
cooling_rate|CSI_300|0.90|6.53|44.82|4.77|34.06
cooling_rate|CSI_300|0.85|5.81|40.12|4.16|31.13
cooling_rate|CSI_300|0.80|4.12|31.90|3.89|24.58
iteration_times|CSI_300|0|0.36|5.36|0.41|6.69
iteration_times|CSI_300|25|3.04|23.55|2.94|21.89
iteration_times|CSI_300|50|4.69|31.80|3.73|26.66
iteration_times|CSI_300|100|6.50|43.49|4.65|33.32
iteration_times|CSI_300|200|6.53|42.76|4.66|32.91
"""

FINAL_TABLE_5_TEXT = """
scaling|SSE50|512|8.16|41.74|5.90|33.43
scaling|SSE50|1024|9.25|43.02|6.27|34.19
scaling|SSE50|1536|9.22|43.11|6.29|34.05
"""

FINAL_TABLE_7_ADDITIONS = """
main_2023|SSE50|factorvae|-1.60|-0.87|13.02
main_2023|CSI_300|factorvae|-0.27|-0.09|21.85
main_2023|ChiNext_100|factorvae|-7.24|-2.74|23.92
main_2023|SSE50|hirevae|-1.42|-0.95|12.48
main_2023|CSI_300|hirevae|0.96|0.35|21.70
main_2023|ChiNext_100|hirevae|-7.15|-2.69|23.30
main_2023|SSE50|mass_gpt_oss_120b|2.14|1.99|11.36
main_2023|CSI_300|mass_gpt_oss_120b|4.87|2.06|14.87
main_2023|ChiNext_100|mass_gpt_oss_120b|1.26|0.97|22.67
leakage_2025_q1|SSE50|proxy_indicator|0.65|0.16|5.47
leakage_2025_q1|CSI_300|proxy_indicator|1.98|0.23|5.94
leakage_2025_q1|CSI_A500|proxy_indicator|1.44|0.20|6.05
leakage_2025_q1|SSE50|lightgbm|0.84|0.17|5.48
leakage_2025_q1|CSI_300|lightgbm|1.97|0.19|6.02
leakage_2025_q1|CSI_A500|lightgbm|1.74|0.25|5.89
leakage_2025_q1|SSE50|factorvae|4.60|1.87|4.04
leakage_2025_q1|CSI_300|factorvae|4.53|1.85|5.60
leakage_2025_q1|CSI_A500|factorvae|6.83|2.04|5.32
leakage_2025_q1|SSE50|hirevae|4.78|1.92|4.06
leakage_2025_q1|CSI_300|hirevae|4.81|2.05|5.01
leakage_2025_q1|CSI_A500|hirevae|7.08|2.20|5.28
leakage_2025_q1|SSE50|dtml|4.49|1.70|4.35
leakage_2025_q1|CSI_300|dtml|4.55|1.79|6.06
leakage_2025_q1|CSI_A500|dtml|6.85|1.93|6.27
leakage_2025_q1|SSE50|master|5.01|1.98|3.97
leakage_2025_q1|CSI_300|master|4.78|1.87|5.45
leakage_2025_q1|CSI_A500|master|6.76|1.97|4.96
leakage_2025_q1|SSE50|sep|4.99|1.84|4.70
leakage_2025_q1|CSI_300|sep|1.12|0.19|5.90
leakage_2025_q1|CSI_A500|sep|1.21|0.21|6.02
leakage_2025_q1|SSE50|fincon|5.12|2.09|3.38
leakage_2025_q1|CSI_300|fincon|1.22|0.18|6.08
leakage_2025_q1|CSI_A500|fincon|0.98|0.26|5.86
leakage_2025_q1|SSE50|tradingagents|5.27|2.14|3.27
leakage_2025_q1|CSI_300|tradingagents|5.58|2.26|2.97
leakage_2025_q1|CSI_A500|tradingagents|8.87|2.68|4.12
leakage_2025_q1|SSE50|mass_gpt_oss_120b|9.81|2.38|3.04
leakage_2025_q1|CSI_300|mass_gpt_oss_120b|8.42|2.49|3.04
leakage_2025_q1|CSI_A500|mass_gpt_oss_120b|11.51|2.88|4.17
"""

FINAL_TABLE_8_TEXT = """
main_2023|Nasdaq_100|proxy_indicator|1.94|15.37|1.82|13.91
main_2023|SP_500|proxy_indicator|1.85|16.02|1.93|14.31
main_2023|Nasdaq_100|lightgbm|2.71|19.90|2.56|19.34
main_2023|SP_500|lightgbm|2.06|19.84|2.19|17.83
main_2023|Nasdaq_100|factorvae|3.49|26.05|3.62|28.95
main_2023|SP_500|factorvae|3.96|28.34|3.77|29.64
main_2023|Nasdaq_100|hirevae|3.52|25.30|3.79|27.98
main_2023|SP_500|hirevae|4.12|27.86|3.83|28.39
main_2023|Nasdaq_100|dtml|3.15|22.90|2.83|21.56
main_2023|SP_500|dtml|3.52|24.65|2.96|20.10
main_2023|Nasdaq_100|master|3.38|23.62|2.98|21.49
main_2023|SP_500|master|3.27|25.93|3.09|22.53
main_2023|Nasdaq_100|sep|3.40|22.99|3.26|23.85
main_2023|SP_500|sep|1.38|11.82|0.82|7.81
main_2023|Nasdaq_100|fincon|3.46|23.81|3.24|24.77
main_2023|SP_500|fincon|1.24|10.27|0.68|8.64
main_2023|Nasdaq_100|tradingagents|3.63|27.36|3.85|28.29
main_2023|SP_500|tradingagents|4.07|31.28|3.89|27.94
main_2023|Nasdaq_100|mass|4.27|31.05|3.94|28.90
main_2023|SP_500|mass|4.31|31.45|3.95|28.68
leakage_2025_q1|Nasdaq_100|proxy_indicator|1.98|17.26|1.47|14.83
leakage_2025_q1|SP_500|proxy_indicator|2.06|16.39|2.34|15.81
leakage_2025_q1|Nasdaq_100|lightgbm|2.40|18.75|2.38|19.36
leakage_2025_q1|SP_500|lightgbm|2.64|19.42|2.47|17.38
leakage_2025_q1|Nasdaq_100|factorvae|3.42|27.86|3.29|27.05
leakage_2025_q1|SP_500|factorvae|3.55|24.60|3.49|27.85
leakage_2025_q1|Nasdaq_100|hirevae|3.58|24.97|3.63|26.37
leakage_2025_q1|SP_500|hirevae|3.67|24.54|3.72|27.63
leakage_2025_q1|Nasdaq_100|dtml|3.21|23.59|2.93|21.40
leakage_2025_q1|SP_500|dtml|3.37|22.35|3.26|21.84
leakage_2025_q1|Nasdaq_100|master|3.52|25.98|3.20|25.84
leakage_2025_q1|SP_500|master|3.61|26.54|3.48|25.70
leakage_2025_q1|Nasdaq_100|sep|3.43|26.35|3.19|25.76
leakage_2025_q1|SP_500|sep|0.62|6.35|0.74|5.89
leakage_2025_q1|Nasdaq_100|fincon|3.48|25.82|3.63|25.97
leakage_2025_q1|SP_500|fincon|1.13|8.56|0.97|6.75
leakage_2025_q1|Nasdaq_100|tradingagents|3.50|26.76|3.71|26.99
leakage_2025_q1|SP_500|tradingagents|3.78|28.04|3.92|29.31
leakage_2025_q1|Nasdaq_100|mass|3.96|29.84|4.01|27.53
leakage_2025_q1|SP_500|mass|4.05|29.73|3.99|29.67
"""

FINAL_TABLE_3_TEXT = """
Value|600036|China Merchants Bank Co., Ltd.
Value|601857|PetroChina Company Limited
Value|601088|China Shenhua Energy Company Limited
Growth|600519|Kweichow Moutai Co., Ltd.
Growth|600276|Jiangsu Hengrui Pharmaceuticals Co., Ltd.
Growth|600309|Wanhua Chemical Group Co., Ltd.
Beta|601888|China Tourism Group Duty Free Corporation Limited
Beta|603288|Foshan Haitian Flavouring & Food Co., Ltd.
Beta|603259|WuXi AppTec Co., Ltd.
"""


PINNED_SOURCE_SHA256 = {
    "README.md": "1b036a4dd5cfd87b24335609f11ba0a9a61ac49f53eb5578f57fe49d57f2bc5e",
    "ih_dist": SNAPSHOT_SHA256,
    "pdm.lock": "2c675b29b7b7ffaeba3f7bd52199ba6f1f71035a5172ef6e43c5e10cee25f838",
    "pyproject.toml": "45a6bffa2005a4728554cecc0ea096fb17f2801fc7eeaf82a63083d891243ac2",
    "stock_disagreement/agent/agent_distribution.py": "b53a2af0c97054e9db7be0aaaea2b41fbbd5a94f3fe2f62c5dd8d5397690c87c",
    "stock_disagreement/agent/basic_agent.py": "c9dd13fa10e040f85be843af07403e9d46e53ba9fed028ee32a51473cfff4c2b",
    "stock_disagreement/agent/investment_analyzer.py": "394daf70b5ac6bd965555ed66d0fd4fdd65502645c63408c300f8e666ee547d4",
    "stock_disagreement/agent/stock_selector.py": "ee58ea681a86e3d29f0cc6d7c101002618c3629b75d540881d0da330dc2f6fdc",
    "stock_disagreement/exp/trainer.py": "534845b4033cb3851a0442573b8319914d7ec0462e7882ba54c4ab900eda2033",
    "stock_disagreement/main.py": "c9f5984002d0de6a1c856bee88df0723a1a91f0806d630454b37dba19a74d6de",
    "stock_disagreement/utils/llm.py": "1f284173e84a99321ea70088a0deb93da98cdbf9b201959ea12f622d778a6069",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def git_head(root: Path) -> str:
    return git_text(root, "rev-parse", "HEAD")


def source_history_audit(source_root: Path) -> Dict[str, Any]:
    commits = []
    for line in git_text(
        source_root,
        "log",
        "--reverse",
        "--all",
        "--format=%H|%aI|%an|%s",
    ).splitlines():
        commit, date, author, subject = line.split("|", 3)
        commits.append({"commit": commit, "author_date": date, "author": author, "subject": subject})

    roots = git_text(source_root, "rev-list", "--max-parents=0", "--all").splitlines()
    refs = git_text(
        source_root,
        "for-each-ref",
        "--format=%(refname)|%(objectname)",
        "refs/heads",
        "refs/remotes",
        "refs/tags",
    ).splitlines()
    tags = [line for line in refs if line.startswith("refs/tags/")]
    tracked_head = git_text(source_root, "ls-tree", "-r", "--name-only", SOURCE_COMMIT).splitlines()
    unique_historical_paths = {
        path
        for path in git_text(source_root, "log", "--all", "--pretty=format:", "--name-only").splitlines()
        if path
    }
    deleted_paths = {
        line.split("\t", 1)[1]
        for line in git_text(source_root, "log", "--all", "--diff-filter=D", "--name-status", "--format=").splitlines()
        if line.startswith("D\t")
    }
    ignored_objects = {
        path: git_text(source_root, "rev-list", "--objects", "--all", "--", path).splitlines()
        for path in IGNORED_OUTPUT_PATHS
    }
    fsck = subprocess.run(
        ["git", "-C", str(source_root), "fsck", "--full", "--no-reflogs", "--unreachable"],
        check=True,
        capture_output=True,
        text=True,
    )

    if [item["commit"] for item in commits] != list(SOURCE_HISTORY_COMMITS):
        raise RuntimeError("Pinned MASS official history changed")
    if roots != [SOURCE_ROOT_COMMIT] or tags:
        raise RuntimeError("Pinned MASS official source topology changed")
    expected_ref_suffixes = {
        f"refs/heads/main|{SOURCE_COMMIT}",
        f"refs/remotes/origin/HEAD|{SOURCE_COMMIT}",
        f"refs/remotes/origin/main|{SOURCE_COMMIT}",
        f"refs/remotes/origin/master|{SOURCE_COMMIT}",
    }
    if set(refs) != expected_ref_suffixes:
        raise RuntimeError(f"Pinned MASS official refs changed: {refs}")
    if len(tracked_head) != 38 or len(unique_historical_paths) != 58:
        raise RuntimeError("Pinned MASS source tree/history size changed")
    if not set(HISTORICAL_DELETED_CODE_PATHS).issubset(deleted_paths):
        raise RuntimeError("Pinned MASS deleted-source set changed")
    if any(ignored_objects.values()):
        raise RuntimeError("A formerly ignored MASS result path is now present in reachable history")
    if fsck.stdout.strip() or fsck.stderr.strip():
        raise RuntimeError("Unexpected unreachable or corrupt objects in pinned MASS clone")

    deleted_code = []
    for path in HISTORICAL_DELETED_CODE_PATHS:
        commit = git_text(source_root, "log", "--all", "--format=%H", "--", path).splitlines()[-1]
        blob = git_text(source_root, "rev-parse", f"{commit}:{path}")
        deleted_code.append(
            {
                "path": path,
                "oldest_reachable_commit": commit,
                "blob": blob,
                "bytes": int(git_text(source_root, "cat-file", "-s", blob)),
                "paper_result_artifact": False,
                "interpretation": (
                    "abandoned DTML/private-data precursor or input-cleaning utility; "
                    "not a MASS decision, signal, portfolio, or published result"
                ),
            }
        )

    return {
        "scope": "all locally reachable official-clone refs and objects",
        "remote_url": git_text(source_root, "remote", "get-url", "origin"),
        "is_shallow_repository": git_text(source_root, "rev-parse", "--is-shallow-repository") == "true",
        "reachable_commit_count": len(commits),
        "root_commit_count": len(roots),
        "branch_and_remote_refs": refs,
        "tag_count": len(tags),
        "unreachable_object_output_empty": True,
        "commits": commits,
        "head_tree_file_count": len(tracked_head),
        "unique_historical_path_count": len(unique_historical_paths),
        "deleted_code_recovered": deleted_code,
        "ignored_result_paths": [
            {"path": path, "reachable_objects": len(objects)} for path, objects in ignored_objects.items()
        ],
        "historical_native_decision_signal_portfolio_or_result_artifacts_found": False,
    }


def release_lineage_audit(source_root: Path, anonymous_source_root: Path) -> Dict[str, Any]:
    if git_head(anonymous_source_root) != ANONYMOUS_SOURCE_COMMIT:
        raise RuntimeError("Pinned anonymous MASS backup commit changed")
    if git_text(anonymous_source_root, "rev-parse", "--is-shallow-repository") == "true":
        raise RuntimeError("Anonymous MASS backup must be a full clone")

    official_paths = set(git_text(source_root, "ls-tree", "-r", "--name-only", SOURCE_COMMIT).splitlines())
    anonymous_paths = set(
        git_text(anonymous_source_root, "ls-tree", "-r", "--name-only", ANONYMOUS_SOURCE_COMMIT).splitlines()
    )
    shared_paths = official_paths & anonymous_paths
    different_shared_blobs = []
    for path in sorted(shared_paths):
        official_blob = git_text(source_root, "rev-parse", f"{SOURCE_COMMIT}:{path}")
        anonymous_blob = git_text(anonymous_source_root, "rev-parse", f"{ANONYMOUS_SOURCE_COMMIT}:{path}")
        if official_blob != anonymous_blob:
            different_shared_blobs.append(path)
    if anonymous_paths - official_paths != {".README"} or official_paths - anonymous_paths:
        raise RuntimeError("Pinned MASS anonymous backup path set changed")
    if different_shared_blobs != ["README.md"]:
        raise RuntimeError(f"Pinned MASS anonymous backup blob equivalence changed: {different_shared_blobs}")
    if sha256(anonymous_source_root / "ih_dist") != SNAPSHOT_SHA256:
        raise RuntimeError("Anonymous MASS backup optimizer snapshot changed")

    return {
        "arxiv_primary_record": {
            "v1_pdf_sha256": PAPER_V1_SHA256,
            "v2_pdf_sha256": PAPER_SHA256,
            "v2_is_audited_result_record": True,
        },
        "openreview_primary_record": {
            "url": OPENREVIEW_URL,
            "submission_number": 3728,
            "final_pdf_sha256": OPENREVIEW_FINAL_PDF_SHA256,
            "final_pdf_pages": 26,
            "decision": "reject",
            "archive_url": OPENREVIEW_ARCHIVE_URL,
            "archive_status_as_checked_2026_08_13": "expired",
            "backup_url_named_in_paper": ANONYMOUS_SOURCE_URL,
        },
        "anonymous_backup_commit": ANONYMOUS_SOURCE_COMMIT,
        "anonymous_backup_root_commit_count": len(
            git_text(anonymous_source_root, "rev-list", "--max-parents=0", "--all").splitlines()
        ),
        "anonymous_backup_file_count": len(anonymous_paths),
        "official_release_file_count": len(official_paths),
        "shared_file_count": len(shared_paths),
        "anonymous_only_paths": sorted(anonymous_paths - official_paths),
        "different_shared_blobs": different_shared_blobs,
        "all_non_readme_shared_blobs_identical": True,
        "same_optimizer_snapshot_sha256": SNAPSHOT_SHA256,
        "additional_decisions_signals_portfolios_results_or_stock_pools_in_backup": False,
        "paper_and_release_claim_boundary": (
            "arXiv v2 says one dataset was open-sourced; both the later anonymous backup and "
            "named release contain the same SSE50 example panel and ih_dist optimizer state"
        ),
    }


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_table(
    table: int,
    text: str,
    metrics: Sequence[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in text.strip().splitlines():
        if not line:
            continue
        values = line.split("|")
        if len(values) != 3 + len(metrics):
            raise ValueError(f"Malformed Table {table} row: {line}")
        section, pool, method = values[:3]
        for metric, value in zip(metrics, values[3:]):
            numeric = value != "EMCL"
            rows.append(
                {
                    "paper_table": table,
                    "section": section,
                    "stock_pool": pool,
                    "method": method,
                    "metric": metric,
                    "paper_value": float(value) if numeric else value,
                    "paper_value_is_numeric": numeric,
                }
            )
    return rows


def arxiv_v2_result_rows() -> List[Dict[str, Any]]:
    return [
        *parse_table(1, TABLE_1_TEXT, TABLE_1_METRICS),
        *parse_table(2, TABLE_2_TEXT, TABLE_2_METRICS),
        *parse_table(3, TABLE_3_TEXT, TABLE_3_METRICS),
        *parse_table(4, TABLE_4_TEXT, TABLE_4_METRICS),
    ]


def paper_result_rows() -> List[Dict[str, Any]]:
    """Enumerate every numeric/EMCL result cell in the final OpenReview PDF."""

    return [
        *parse_table(1, TABLE_1_TEXT + FINAL_TABLE_1_ADDITIONS, TABLE_1_METRICS),
        *parse_table(2, TABLE_2_TEXT, TABLE_2_METRICS),
        *parse_table(4, FINAL_TABLE_4_TEXT, TABLE_1_METRICS),
        *parse_table(5, FINAL_TABLE_5_TEXT, TABLE_1_METRICS),
        *parse_table(6, TABLE_3_TEXT, TABLE_3_METRICS),
        *parse_table(7, TABLE_4_TEXT + FINAL_TABLE_7_ADDITIONS, TABLE_4_METRICS),
        *parse_table(8, FINAL_TABLE_8_TEXT, TABLE_1_METRICS),
    ]


def result_conformance() -> List[Dict[str, Any]]:
    rows = []
    for target in paper_result_rows():
        if target["paper_value_is_numeric"]:
            status = "unverifiable_no_shipped_native_signal_output_or_result_path"
            evidence = (
                "paper_value_only; release has native aggregation source but no dated "
                "agent-decision cache, signal output, baseline output, backtest output, "
                "cost log, or result table"
            )
        else:
            status = "paper_non_numeric_emcl"
            evidence = "paper reports maximum-context-length failure rather than a numeric result"
        rows.append(
            {
                **target,
                "source_recomputed_value": "",
                "status": status,
                "evidence": evidence,
            }
        )
    return rows


def final_table_3_stock_inventory() -> List[Dict[str, Any]]:
    """Inventory the final paper's descriptive examples without result credit."""

    rows = []
    for line in FINAL_TABLE_3_TEXT.strip().splitlines():
        style, ticker, company = line.split("|", 2)
        rows.append(
            {
                "paper_table": 3,
                "style": style,
                "ticker": ticker,
                "company": company,
                "empirical_result_cell": False,
                "replication_credit": False,
                "evidence": "descriptive paper metadata only",
            }
        )
    if len(rows) != 9 or Counter(row["style"] for row in rows) != {
        "Value": 3,
        "Growth": 3,
        "Beta": 3,
    }:
        raise RuntimeError("Pinned MASS final Table 3 inventory changed")
    return rows


def final_empirical_figure_inventory() -> List[Dict[str, Any]]:
    """Inventory empirical figures and the missing native evidence for each."""

    return [
        {
            "paper_figure": 2,
            "paper_content": "CSI 300 cumulative-return backtest curves",
            "required_native_evidence": "dated signals, weekly portfolios, costs, and return series",
            "released_evidence": "aggregation source only; no dated decisions, signals, portfolios, or returns",
            "status": "unverifiable_no_shipped_native_output",
        },
        {
            "paper_figure": 3,
            "paper_content": "score-alpha and optimizer-lookback sensitivity curves",
            "required_native_evidence": "pinned sweep configs, seeds, decisions, and evaluated outputs",
            "released_evidence": "adjustable source parameters only; no sweep configs, seeds, decisions, or outputs",
            "status": "unverifiable_no_shipped_native_output",
        },
        {
            "paper_figure": 4,
            "paper_content": "performance and cost across agent-ensemble scales",
            "required_native_evidence": "pinned scale runs, decisions, timing logs, and evaluated outputs",
            "released_evidence": "adjustable agent counts only; no run configs, decisions, timing logs, or outputs",
            "status": "unverifiable_no_shipped_native_output",
        },
        {
            "paper_figure": 5,
            "paper_content": "investor-type distributions and MASS/index/excess return trajectories",
            "required_native_evidence": "exact plotted distributions plus dated signals, portfolios, and returns",
            "released_evidence": "a dated 16-type ih_dist internal state exists, but its plotted provenance and all return inputs are absent",
            "status": "partial_internal_state_only_figure_not_reproduced",
        },
        {
            "paper_figure": 6,
            "paper_content": "two independent SSE 50 stock-popularity inference trajectories",
            "required_native_evidence": "both run configs, seeds, cached decisions, and popularity series",
            "released_evidence": "no run config, seed, decision cache, or popularity-series output",
            "status": "unverifiable_no_shipped_native_output",
        },
    ]


SAFE_PICKLE_OPCODES = {
    "PROTO",
    "FRAME",
    "EMPTY_DICT",
    "MEMOIZE",
    "MARK",
    "BININT",
    "BININT1",
    "BININT2",
    "SHORT_BINUNICODE",
    "STACK_GLOBAL",
    "TUPLE1",
    "REDUCE",
    "BINFLOAT",
    "BINGET",
    "SETITEMS",
    "STOP",
}


class DistributionSnapshotUnpickler(pickle.Unpickler):
    """Allow only the pinned Modality enum constructor, mapped to plain int."""

    def find_class(self, module: str, name: str) -> Any:
        if (module, name) == ("stock_disagreement.agent.basic_agent", "Modality"):
            return int
        raise pickle.UnpicklingError(f"forbidden global: {module}.{name}")


def safe_distribution_snapshot(path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SNAPSHOT_SHA256:
        raise RuntimeError("MASS ih_dist hash changed")
    opcodes = list(pickletools.genops(raw))
    observed = {opcode.name for opcode, _, _ in opcodes}
    unexpected = observed - SAFE_PICKLE_OPCODES
    if unexpected:
        raise RuntimeError(f"MASS ih_dist contains forbidden pickle opcodes: {sorted(unexpected)}")
    if Counter(opcode.name for opcode, _, _ in opcodes)["STACK_GLOBAL"] != 1:
        raise RuntimeError("MASS ih_dist global-constructor count changed")

    data = DistributionSnapshotUnpickler(io.BytesIO(raw)).load()
    if not isinstance(data, dict):
        raise RuntimeError("MASS ih_dist is not a date-keyed dictionary")
    rows = []
    previous: Tuple[Tuple[int, float], ...] | None = None
    for date in sorted(data):
        distribution = data[date]
        if not isinstance(date, int) or not isinstance(distribution, dict):
            raise RuntimeError("MASS ih_dist contains a non-primitive date/distribution")
        if not all(isinstance(key, int) and isinstance(value, float) for key, value in distribution.items()):
            raise RuntimeError("MASS ih_dist contains a non-primitive distribution entry")
        fingerprint = tuple(sorted(distribution.items()))
        raw_sum = math.fsum(distribution.values())
        rows.append(
            {
                "date": date,
                "investor_type_masks": len(distribution),
                "raw_weight_sum": raw_sum,
                "normalized_weight_sum": math.fsum(value / raw_sum for value in distribution.values()),
                "minimum_raw_weight": min(distribution.values()),
                "maximum_raw_weight": max(distribution.values()),
                "changed_from_previous_trading_date": previous is not None and fingerprint != previous,
                "interpretation": "native dated optimizer state; not an agent decision, signal, or return",
            }
        )
        previous = fingerprint
    summary = {
        "pickle_opcodes_total": len(opcodes),
        "pickle_opcode_names": sorted(observed),
        "pickle_global_policy": ["stock_disagreement.agent.basic_agent.Modality mapped to built-in int"],
        "dates": len(rows),
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
        "investor_type_masks_per_date": sorted({row["investor_type_masks"] for row in rows}),
        "changed_transitions": sum(row["changed_from_previous_trading_date"] for row in rows),
        "raw_weight_sum_min": min(row["raw_weight_sum"] for row in rows),
        "raw_weight_sum_max": max(row["raw_weight_sum"] for row in rows),
        "all_weights_positive": all(row["minimum_raw_weight"] > 0 for row in rows),
        "safe_decode_boundary": (
            "pinned hash plus opcode allowlist; sole Modality constructor mapped to built-in int; "
            "all decoded keys and values validated as primitive int/float"
        ),
    }
    if (
        summary["dates"] != 263
        or summary["first_date"] != 20221202
        or summary["last_date"] != 20231229
        or summary["investor_type_masks_per_date"] != [16]
        or summary["changed_transitions"] != 216
        or not summary["all_weights_positive"]
    ):
        raise RuntimeError(f"Pinned MASS distribution snapshot findings changed: {summary}")
    return rows, summary


def native_signal_nonidentifiability(source_root: Path, snapshot_path: Path) -> Dict[str, Any]:
    """Prove that the released distribution state cannot identify a MASS signal."""

    _, snapshot_summary = safe_distribution_snapshot(snapshot_path)
    distributions = DistributionSnapshotUnpickler(io.BytesIO(snapshot_path.read_bytes())).load()
    date = snapshot_summary["first_date"]
    weights = distributions[date]

    module_path = source_root / "stock_disagreement/agent/investment_analyzer.py"
    spec = importlib.util.spec_from_file_location("mass_native_investment_analyzer", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load pinned native MASS InvestmentAnalyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    analyzer_class = module.InvestmentAnalyzer

    base = pd.read_parquet(source_root / "stock_disagreement/dataset/base_data.parq")
    stock_pool = sorted(map(str, base.loc[base["Date"] == date, "Stock"].unique()))
    if len(stock_pool) != 50:
        raise RuntimeError(f"Expected 50 released stocks for counterexample date {date}, got {len(stock_pool)}")
    candidate_pool = stock_pool[:20]
    selected_a = candidate_pool[:5]
    selected_b = candidate_pool[5:10]

    def execute(selected: Sequence[str]) -> Dict[str, List[float]]:
        analyzer = analyzer_class()
        analyzer.data = {}
        decisions = {stock: int(stock in selected) for stock in candidate_pool}
        for investor_type in weights:
            for investor_id in range(32):
                analyzer.record_score(date, investor_type, investor_id, decisions)
        return analyzer.calculate_stock_disagreement_score(
            date=date,
            stock_pool=stock_pool,
            agent_distributions=weights,
            alpha=0.5,
        )

    signal_a = execute(selected_a)
    signal_b = execute(selected_b)
    changed = sorted(stock for stock in stock_pool if signal_a[stock] != signal_b[stock])
    if changed != sorted(selected_a + selected_b):
        raise RuntimeError(f"Pinned native MASS non-identifiability result changed: {changed}")
    for stock in selected_a:
        if not math.isclose(signal_a[stock][0], 0.5) or not math.isclose(signal_b[stock][0], 0.0):
            raise RuntimeError("Pinned native MASS scenario-A signal changed")
    for stock in selected_b:
        if not math.isclose(signal_a[stock][0], 0.0) or not math.isclose(signal_b[stock][0], 0.5):
            raise RuntimeError("Pinned native MASS scenario-B signal changed")

    canonical_weights = json.dumps(sorted(weights.items()), separators=(",", ":"))
    return {
        "purpose": "constructive native-code proof that released ih_dist does not determine signals",
        "native_module": "stock_disagreement/agent/investment_analyzer.py",
        "native_module_sha256": sha256(module_path),
        "snapshot_sha256": sha256(snapshot_path),
        "date": date,
        "investor_types": len(weights),
        "agents_per_type": 32,
        "candidate_pool_size": len(candidate_pool),
        "selected_stocks_per_agent": 5,
        "same_released_distribution_in_both_scenarios": True,
        "distribution_fingerprint_sha256": hashlib.sha256(canonical_weights.encode()).hexdigest(),
        "scenario_a_selected_stocks": selected_a,
        "scenario_b_selected_stocks": selected_b,
        "scenario_a_selected_signal": {stock: signal_a[stock] for stock in selected_a},
        "scenario_b_selected_signal": {stock: signal_b[stock] for stock in selected_b},
        "changed_signal_stock_count": len(changed),
        "changed_signal_stocks": changed,
        "released_state_identifies_unique_signal": False,
        "interpretation": (
            "Both valid 16-type x 32-agent decision assignments use the identical released dated "
            "distribution, 20-stock candidate size, five selections per agent, and native alpha=0.5 "
            "aggregation. They produce different signals and rankings, so ih_dist cannot reconstruct "
            "the absent decisions or any Table 1--4 output."
        ),
    }


DATASET_FILES = (
    "stock_disagreement/dataset/base_data.parq",
    "stock_disagreement/dataset/ih_label.parq",
    "stock_disagreement/dataset/sub_fudamental_data.parq",
    "stock_disagreement/dataset/industry_ret.parq",
    "stock_disagreement/dataset/stock_basic_data.parq",
    "stock_disagreement/dataset/financial-news-info.parq",
    "stock_disagreement/dataset/financial-news-relationship.parq",
    "stock_disagreement/dataset/macro_data/China_1-Year_Loan_Prime_Rate_LPR.csv",
    "stock_disagreement/dataset/macro_data/China_CPI_YoY_Current_Month.csv",
    "stock_disagreement/dataset/macro_data/Market_Sentiment_Index.csv",
    "stock_disagreement/dataset/macro_data/csi_300_pe_ttm.csv",
    "stock_disagreement/dataset/macro_data/yield_on_China_10_year_government_bonds.csv",
)


def dataset_inventory(source_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows = []
    for relative in DATASET_FILES:
        path = source_root / relative
        record: Dict[str, Any] = {
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "format_status": "",
            "rows": "",
            "columns": "",
            "minimum_date": "",
            "maximum_date": "",
            "distinct_dates": "",
            "distinct_stocks": "",
        }
        try:
            frame = pd.read_parquet(path) if path.suffix == ".parq" else pd.read_csv(path)
            record["format_status"] = "readable"
            record["rows"] = len(frame)
            record["columns"] = ";".join(map(str, frame.columns))
            if "Date" in frame:
                record["minimum_date"] = str(frame["Date"].min())
                record["maximum_date"] = str(frame["Date"].max())
                record["distinct_dates"] = int(frame["Date"].nunique())
            if "Stock" in frame:
                record["distinct_stocks"] = int(frame["Stock"].nunique())
        except Exception as error:
            record["format_status"] = f"unreadable_{type(error).__name__}"
        rows.append(record)

    base = pd.read_parquet(source_root / "stock_disagreement/dataset/base_data.parq")
    labels = pd.read_parquet(source_root / "stock_disagreement/dataset/ih_label.parq")
    features = pd.read_parquet(source_root / "stock_disagreement/dataset/sub_fudamental_data.parq")
    base_2023 = base[base["Date"].between(20230101, 20231231)]
    label_2023 = labels[labels["Date"].between(20230101, 20231231)]
    feature_2023 = features[features["Date"].between(20230101, 20231231)]
    daily_counts = base_2023.groupby("Date")["Stock"].nunique()
    summary = {
        "released_2023_sse_like_trading_dates": int(base_2023["Date"].nunique()),
        "released_2023_sse_like_distinct_stocks_across_year": int(base_2023["Stock"].nunique()),
        "released_2023_cross_section_size_min": int(daily_counts.min()),
        "released_2023_cross_section_size_max": int(daily_counts.max()),
        "base_label_key_rows_equal": len(base_2023) == len(label_2023),
        "base_feature_key_rows_equal": len(base_2023) == len(feature_2023),
        "paper_stock_pools": [
            "SSE50",
            "CSI_300",
            "ChiNext_100",
            "CSI_A500",
            "Nasdaq_100",
            "SP_500",
        ],
        "released_stock_pool_panels": ["SSE50_like_only"],
        "invalid_news_placeholders": 2,
        "invalid_news_placeholder_bytes_each": 2,
    }
    if summary != {
        "released_2023_sse_like_trading_dates": 242,
        "released_2023_sse_like_distinct_stocks_across_year": 59,
        "released_2023_cross_section_size_min": 50,
        "released_2023_cross_section_size_max": 50,
        "base_label_key_rows_equal": True,
        "base_feature_key_rows_equal": True,
        "paper_stock_pools": [
            "SSE50",
            "CSI_300",
            "ChiNext_100",
            "CSI_A500",
            "Nasdaq_100",
            "SP_500",
        ],
        "released_stock_pool_panels": ["SSE50_like_only"],
        "invalid_news_placeholders": 2,
        "invalid_news_placeholder_bytes_each": 2,
    }:
        raise RuntimeError(f"Pinned MASS dataset findings changed: {summary}")
    return rows, summary


def source_config_audit(source_root: Path) -> List[Dict[str, str]]:
    main = (source_root / "stock_disagreement/main.py").read_text(encoding="utf-8")
    trainer = (source_root / "stock_disagreement/exp/trainer.py").read_text(encoding="utf-8")
    agent = (source_root / "stock_disagreement/agent/basic_agent.py").read_text(encoding="utf-8")
    optimizer = (source_root / "stock_disagreement/agent/agent_distribution.py").read_text(encoding="utf-8")
    selector = (source_root / "stock_disagreement/agent/stock_selector.py").read_text(encoding="utf-8")
    pyproject = (source_root / "pyproject.toml").read_text(encoding="utf-8")

    findings = {
        "model": 'model_name: str = "Qwen2.5-72B-Instruct"' in agent,
        "types": '"--num_investor_type", type=int, default= 16' in main,
        "agents_per_type": '"--num_agents_per_investor", type=int, default= 32' in main,
        "source_alpha": "alpha:float = 0.5" in optimizer
        or "alpha:float = 0.5"
        in (source_root / "stock_disagreement/agent/investment_analyzer.py").read_text(encoding="utf-8"),
        "alpha_not_forwarded": "alpha=" not in trainer,
        "source_sa_temperature": "init_temp: float = 0.5" in optimizer,
        "source_sa_iterations": "max_iter:int = 20" in optimizer,
        "source_cooling": "cooling_rate: float = 0.95" in optimizer,
        "daily_candidate_sampling": "random.choices" in selector and "date=date" in agent,
        "daily_strategy_generation": "self.generate_strategy_and_stock_selector(date)" in agent,
        "missing_f_string_paths": 'pd.read_parquet("{ROOT_PATH}/' in main,
        "empty_root_path_count": sum(text.count('ROOT_PATH = ""') for text in (main, trainer, agent)) == 3,
        "undeclared_pandas": re.search(r'"pandas(?:[<=>]|\")', pyproject) is None,
        "undeclared_numpy": re.search(r'"numpy(?:[<=>]|\")', pyproject) is None,
        "undeclared_scipy": re.search(r'"scipy(?:[<=>]|\")', pyproject) is None,
    }
    if not all(findings.values()):
        raise RuntimeError(f"Pinned MASS source findings changed: {findings}")

    return [
        {
            "dimension": "foundation_model",
            "paper": "Qwen2.5-72B-Instruct primary backbone",
            "released": "Qwen2.5-72B-Instruct",
            "status": "match",
        },
        {
            "dimension": "final_revision_second_foundation_model",
            "paper": "GPT-OSS-120B sensitivity experiment in final OpenReview Tables 1 and 7",
            "released": "no GPT-OSS model config, prompt/response cache, signal, or output",
            "status": "missing",
        },
        {
            "dimension": "main_agent_scale",
            "paper": "16 types x 32 agents = 512",
            "released": "CLI defaults 16 x 32",
            "status": "match",
        },
        {
            "dimension": "sse50_candidate_pool_size",
            "paper": "20",
            "released": "CLI default stock_num=20",
            "status": "match",
        },
        {
            "dimension": "csi300_candidate_pool_size",
            "paper": "30",
            "released": "supported only by manual --stock_num override; no experiment command/config",
            "status": "not_pinned",
        },
        {"dimension": "score_alpha_sse50_csi300", "paper": "0.5", "released": "0.5 default", "status": "match"},
        {
            "dimension": "score_alpha_chinext100",
            "paper": "0.2",
            "released": "0.5 hard default; trainer never forwards a pool-specific alpha",
            "status": "mismatch",
        },
        {"dimension": "sa_initial_temperature", "paper": "40", "released": "0.5 active default", "status": "mismatch"},
        {"dimension": "sa_max_iterations", "paper": "100", "released": "20 active default", "status": "mismatch"},
        {"dimension": "sa_cooling_rate", "paper": "0.95", "released": "0.95", "status": "match"},
        {"dimension": "optimizer_lookback", "paper": "5", "released": "CLI default 5", "status": "match"},
        {
            "dimension": "main_candidate_pool_update",
            "paper": "static per agent; daily update is separate MASS(DU) ablation",
            "released": "resampled daily with random.choices (with replacement)",
            "status": "mismatch",
        },
        {
            "dimension": "daily_type_strategy",
            "paper": "one daily strategy per investor type",
            "released": "each agent generates its own strategy on every trading day",
            "status": "mismatch",
        },
        {
            "dimension": "randomness_control",
            "paper": "no seed protocol disclosed",
            "released": "Python and NumPy RNG used without a run-level seed",
            "status": "missing",
        },
        {
            "dimension": "paper_stock_pool_inputs",
            "paper": "SSE50, CSI 300, ChiNext 100, CSI A500, Nasdaq 100, S&P 500",
            "released": "SSE50-like base/label/feature panel only",
            "status": "incomplete",
        },
        {
            "dimension": "final_revision_us_market_inputs",
            "paper": "Microsoft Qlib and Yahoo Finance panels for Nasdaq 100 and S&P 500, 2023 and Q1 2025",
            "released": "no US-market data builder, pinned response, universe, panel, or labels",
            "status": "missing",
        },
        {
            "dimension": "paper_news_inputs",
            "paper": "financial news for the released multimodal panel",
            "released": "two 2-byte invalid Parquet placeholders under different filenames",
            "status": "missing",
        },
        {
            "dimension": "native_entrypoint_paths",
            "paper": "runnable experiment",
            "released": "three empty ROOT_PATH constants, two literal non-f-string paths, and required filenames absent",
            "status": "not_operational",
        },
        {
            "dimension": "direct_runtime_dependencies",
            "paper": "runnable environment",
            "released": "pandas, numpy, and scipy imported but not direct project dependencies",
            "status": "incomplete",
        },
        {
            "dimension": "metric_horizon",
            "paper": "one Table 1 result set; return horizon not identified",
            "released": "prints separate 1-, 5-, and 10-day label metrics",
            "status": "paper_underspecified",
        },
        {
            "dimension": "portfolio_backtest",
            "paper": "weekly top-20%, 0.1% round-trip cost, Table 7/Figure 2",
            "released": "no backtest, annualized-return, Sharpe, drawdown, or transaction-cost implementation",
            "status": "missing",
        },
        {
            "dimension": "cost_measurement",
            "paper": "final Table 6 time and API fees",
            "released": "no request/token/cost logs or measurement script",
            "status": "missing",
        },
        {
            "dimension": "published_result_paths",
            "paper": "final OpenReview Tables 1--8 and Figures 2--6",
            "released": "no signals, portfolios, baseline outputs, result tables, or cached LLM decisions",
            "status": "missing",
        },
        {
            "dimension": "paper_claimed_cached_individual_decisions",
            "paper": "Appendix A.3.7 says individual decisions are cached for backward optimization",
            "released": "no cache is tracked in either official release or any reachable official commit",
            "status": "missing",
        },
        {
            "dimension": "final_revision_scaling_1024_1536",
            "paper": "Table 5 reports 512, 1024, and 1536 agents",
            "released": "CLI scale is adjustable, but no commands, seeds, decisions, distributions, or results are pinned",
            "status": "not_pinned",
        },
    ]


def build_audit(
    source_root: Path,
    anonymous_source_root: Path,
    paper_v1_path: Path,
    paper_path: Path,
    openreview_final_paper_path: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    commit = git_head(source_root)
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"Expected MASS source commit {SOURCE_COMMIT}, found {commit}")
    if sha256(paper_path) != PAPER_SHA256:
        raise RuntimeError("Official MASS paper PDF hash does not match the pinned primary source")
    if sha256(paper_v1_path) != PAPER_V1_SHA256:
        raise RuntimeError("Official MASS arXiv-v1 PDF hash does not match the pinned primary source")
    if sha256(openreview_final_paper_path) != OPENREVIEW_FINAL_PDF_SHA256:
        raise RuntimeError("Final MASS OpenReview PDF hash does not match the pinned primary source")
    for relative, expected in PINNED_SOURCE_SHA256.items():
        actual = sha256(source_root / relative)
        if actual != expected:
            raise RuntimeError(f"Pinned MASS source hash changed for {relative}: {actual}")

    conformance = result_conformance()
    history = source_history_audit(source_root)
    release_lineage = release_lineage_audit(source_root, anonymous_source_root)
    snapshot_rows, snapshot_summary = safe_distribution_snapshot(source_root / "ih_dist")
    signal_counterexample = native_signal_nonidentifiability(source_root, source_root / "ih_dist")
    datasets, dataset_summary = dataset_inventory(source_root)
    config = source_config_audit(source_root)
    descriptive_table_3 = final_table_3_stock_inventory()
    empirical_figures = final_empirical_figure_inventory()

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "final_table_result_conformance.csv", conformance, list(conformance[0]))
    write_csv(
        output_dir / "final_table_3_stock_inventory.csv",
        descriptive_table_3,
        list(descriptive_table_3[0]),
    )
    write_csv(
        output_dir / "final_empirical_figure_inventory.csv",
        empirical_figures,
        list(empirical_figures[0]),
    )
    write_csv(output_dir / "distribution_snapshot_audit.csv", snapshot_rows, list(snapshot_rows[0]))
    write_csv(output_dir / "released_dataset_inventory.csv", datasets, list(datasets[0]))
    write_csv(output_dir / "source_config_conformance.csv", config, list(config[0]))
    (output_dir / "official_source_history.json").write_text(
        json.dumps(history, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "official_release_lineage.json").write_text(
        json.dumps(release_lineage, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "native_signal_nonidentifiability.json").write_text(
        json.dumps(signal_counterexample, indent=2) + "\n", encoding="utf-8"
    )

    status_counts = Counter(row["status"] for row in conformance)
    table_counts = Counter(row["paper_table"] for row in conformance)
    numeric_table_counts = Counter(row["paper_table"] for row in conformance if row["paper_value_is_numeric"])
    row_groups = {(row["paper_table"], row["section"], row["stock_pool"], row["method"]) for row in conformance}
    if status_counts != {
        "unverifiable_no_shipped_native_signal_output_or_result_path": 766,
        "paper_non_numeric_emcl": 8,
    }:
        raise RuntimeError(f"Pinned MASS status counts changed: {status_counts}")
    if table_counts != {1: 264, 2: 72, 4: 44, 5: 12, 6: 6, 7: 216, 8: 160}:
        raise RuntimeError(f"Pinned MASS table-cell counts changed: {table_counts}")
    if numeric_table_counts != {1: 264, 2: 64, 4: 44, 5: 12, 6: 6, 7: 216, 8: 160}:
        raise RuntimeError(f"Pinned MASS numeric table-cell counts changed: {numeric_table_counts}")
    if len(row_groups) != 213:
        raise RuntimeError(f"Expected 213 MASS final-paper result rows, got {len(row_groups)}")

    manifest: Dict[str, Any] = {
        "audit": "MASS arXiv v1/v2, final rejected OpenReview revision, Tables 1--8, and all official source history",
        "overall_status": "not_reproduced_partial_internal_state_only",
        "full_paper_reproduced": False,
        "paper_url": PAPER_URL,
        "paper_v1_sha256": PAPER_V1_SHA256,
        "paper_sha256": PAPER_SHA256,
        "source_url": SOURCE_URL,
        "source_commit": commit,
        "anonymous_source_url": ANONYMOUS_SOURCE_URL,
        "anonymous_source_commit": ANONYMOUS_SOURCE_COMMIT,
        "openreview_url": OPENREVIEW_URL,
        "openreview_final_pdf_sha256": OPENREVIEW_FINAL_PDF_SHA256,
        "openreview_final_pdf_pages": 26,
        "openreview_final_decision": "reject",
        "openreview_archive_url": OPENREVIEW_ARCHIVE_URL,
        "openreview_archive_status_as_checked_2026_08_13": "expired",
        "official_release_lineage_audited": True,
        "anonymous_backup_all_non_readme_shared_blobs_identical": True,
        "anonymous_backup_additional_native_result_artifacts_found": False,
        "source_history_reachable_commits": history["reachable_commit_count"],
        "source_history_root_commits": history["root_commit_count"],
        "source_history_tags": history["tag_count"],
        "source_history_unique_paths": history["unique_historical_path_count"],
        "source_history_native_result_artifacts_found": False,
        "paper_numeric_tables_audited": [1, 2, 4, 5, 6, 7, 8],
        "paper_descriptive_tables_audited": [3],
        "paper_descriptive_table_3_rows": len(descriptive_table_3),
        "paper_empirical_figures_audited": len(empirical_figures),
        "paper_empirical_figures_reproduced": 0,
        "paper_empirical_figures_partial_internal_state_only": 1,
        "paper_result_rows_total": len(row_groups),
        "paper_result_cells_total_including_emcl": len(conformance),
        "paper_numeric_result_cells_total": status_counts[
            "unverifiable_no_shipped_native_signal_output_or_result_path"
        ],
        "paper_non_numeric_emcl_cells": status_counts["paper_non_numeric_emcl"],
        "paper_numeric_result_cells_reproduced": 0,
        "paper_numeric_result_cells_unverifiable": status_counts[
            "unverifiable_no_shipped_native_signal_output_or_result_path"
        ],
        "native_agent_decision_cache_shipped": False,
        "native_signal_aggregation_source_shipped": True,
        "native_dated_signal_output_shipped": False,
        "native_portfolio_or_return_path_shipped": False,
        "native_baseline_outputs_shipped": False,
        "native_cost_or_timing_logs_shipped": False,
        "native_dated_distribution_snapshot_shipped": True,
        "distribution_snapshot_is_published_result": False,
        "native_signal_nonidentifiability_proved": True,
        "same_released_distribution_produces_distinct_native_signals": True,
        "native_counterexample_changed_signal_stock_count": signal_counterexample["changed_signal_stock_count"],
        "distribution_snapshot": snapshot_summary,
        "released_dataset": dataset_summary,
        "released_full_four_chinese_pool_dataset": False,
        "released_full_six_pool_dataset": False,
        "released_sse50_like_2023_base_and_labels": True,
        "released_entrypoint_operational_without_source_and_data_repairs": False,
        "paper_main_hyperparameters_match_active_source_defaults": False,
        "paper_metric_horizon_identified": False,
        "paper_risk_free_rate_identified": False,
        "paper_random_seed_protocol_identified": False,
        "audit_called_llm_or_external_api": False,
        "interpretation": (
            "The named release and author-provided anonymous backup provide meaningful component "
            "evidence: a complete 242-day 2023 "
            "SSE50-like base/label panel and a safely decoded 263-date, 16-type optimizer-state "
            "trajectory. All non-README files common to both releases are blob-identical, and all "
            "13 official commits, 58 historical paths, ignored result paths, and unreachable objects "
            "were audited. A native two-scenario counterexample proves the released distribution "
            "does not determine signals. It does not reproduce any published result or empirical figure. "
            "All 766 numeric cells in "
            "the final Tables 1--2 and 4--8 lack native decisions/signals/baseline outputs/backtests/cost logs, the "
            "other paper pools are absent, and active source defaults differ from paper settings."
        ),
        "source_file_sha256": {relative: sha256(source_root / relative) for relative in PINNED_SOURCE_SHA256},
    }

    report = f"""# MASS paper-level conformance audit

Overall verdict: **not reproduced**. The public release contains real SSE50-like
input/label data and a dated learned agent-distribution snapshot, but it contains
none of the agent decisions, signals, baseline outputs, portfolios, backtests,
timing logs, or API accounting needed to reproduce final Tables 1--2 and 4--8.

## Primary sources

- Official paper: {PAPER_URL} (SHA-256 `{PAPER_SHA256}`).
- Public source: {SOURCE_URL}, commit `{commit}`.
- Earlier arXiv v1: SHA-256 `{PAPER_V1_SHA256}`.
- ICLR 2026 submission: {OPENREVIEW_URL}. Its 4open.science archive at
  {OPENREVIEW_ARCHIVE_URL} was expired when checked on 2026-08-13; the paper's
  author-provided backup survives at {ANONYMOUS_SOURCE_URL}, commit
  `{ANONYMOUS_SOURCE_COMMIT}`.
- Final OpenReview PDF: SHA-256 `{OPENREVIEW_FINAL_PDF_SHA256}`, 26 pages,
  rejected by ICLR 2026. It adds GPT-OSS-120B, FactorVAE/HireVAE, 1024/1536-agent
  scaling, full Q1-2025 baselines, and Nasdaq-100/S&P-500 results beyond arXiv v2.

## What the release genuinely establishes

- The base, label, and feature panels contain 242 trading dates during 2023 and
  exactly 50 stocks per date (59 distinct identifiers across constituent changes).
- `ih_dist` is a real native internal-state artifact. After checking its pinned
  hash and every pickle opcode before a restricted primitive-only decode, it has
  {snapshot_summary["dates"]} dates from {snapshot_summary["first_date"]} through
  {snapshot_summary["last_date"]}, 16 investor-type masks per date, positive weights
  with invariant raw sum 16, and {snapshot_summary["changed_transitions"]} changed
  transitions. This is optimizer state, not an action, signal, or return path.
- The entire named-release history has 13 reachable commits, one root, no tags,
  38 files at HEAD, and 58 unique historical paths. Recovered deleted files are
  an abandoned DTML/private-data precursor and cleaning utilities, not MASS
  decisions or results. The five ignored output directories have no reachable
  objects, and `git fsck --no-reflogs --unreachable` is empty.
- The anonymous backup has 39 files. Its only extra path is an empty `.README`;
  every shared non-README blob is identical to the named release. Its README says
  the full dataset will be released after review, so it does not add the missing
  pools, decisions, signals, portfolios, or results.
- The released model name, 16-by-32 agent scale, SSE50 candidate count, score
  weight for SSE50/CSI 300, cooling rate, and optimizer lookback agree with the
  corresponding paper declarations.

## Why no published result is reproduced

- The audit enumerates {len(conformance)} final-paper table cells: 766 numeric
  claims and eight Table 2 EMCL markers across Tables 1--2 and 4--8 (Table 3 is
  descriptive stock metadata, separately inventoried without replication credit).
  It also inventories empirical Figures 2--6; none is reproduced. Figure 5 has only
  a partial upstream `ih_dist` state. All 766 numeric claims are unverifiable from
  the release. No cached individual decisions are present, so the distribution
  state cannot be converted into the paper's signals.
- This is now demonstrated constructively through the released native
  `InvestmentAnalyzer`: two valid 16-type x 32-agent decision assignments reuse
  the identical first dated distribution, candidate-pool size 20, five selections,
  and alpha=0.5, yet change {signal_counterexample["changed_signal_stock_count"]}
  stock signals (selected signals swap between 0.5 and 0.0). Therefore the missing
  decision tensor is not inferable from `ih_dist`.
- Only an SSE50-like panel is released. CSI 300, ChiNext 100, CSI A500, and the
  paper's full multimodal inputs are absent. The final revision's Nasdaq-100 and
  S&P-500 Qlib/Yahoo panels are also absent. The two news files are two-byte CRLF
  placeholders and invalid Parquet.
- The entry point cannot run as released: it has three empty `ROOT_PATH` constants,
  two literal paths missing f-string interpolation, and references absent pool,
  label, news, price-feature, and result paths.
- The paper specifies simulated-annealing initial temperature 40 and 100 iterations;
  the active source constructs defaults 0.5 and 20. The paper uses alpha=0.2 for
  ChiNext, while the source always uses the 0.5 default.
- The paper's main candidate pools are static per agent and treats daily updating as
  a separate MASS(DU) ablation. The active source resamples with replacement every
  day. It also generates one strategy per agent/day rather than one per type/day.
- Random modality, candidate-pool, and optimizer draws have no run-level seed. The
  paper does not identify which released 1/5/10-day label horizon produced Table 1,
  nor the risk-free rate behind Table 7 Sharpe ratios.
- Table 7/Figure 2 specify weekly top-20% portfolios and 0.1% round-trip costs, but
  the release has no portfolio/backtest/cost implementation. Table 6 has no timing,
  request, token, or fee logs.
- `InvestmentAnalyzer` is genuine native signal-aggregation source, and the audit
  executes it for the non-identifiability proof. This is source-path evidence only:
  neither official release contains a dated signal output or a published-result path.

Run `scripts/audit_mass_paper.py` to regenerate this package. Use `--strict` when
a CI failure is desired until the native decisions, complete inputs, experiment
configs/seeds, and result paths are released and reproduce at least one paper row.
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "MASS_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/mass_source",
            )
        ),
    )
    parser.add_argument(
        "--anonymous-source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "MASS_ANONYMOUS_SOURCE_ROOT",
                "/nfs/roberts/scratch/pi_btk22/zc362/mass_anonymous_source",
            )
        ),
    )
    parser.add_argument(
        "--paper-v1-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "MASS_PAPER_V1_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/mass_paper_v1.pdf",
            )
        ),
    )
    parser.add_argument(
        "--paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "MASS_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/mass_paper.pdf",
            )
        ),
    )
    parser.add_argument(
        "--openreview-final-paper-pdf",
        type=Path,
        default=Path(
            os.environ.get(
                "MASS_OPENREVIEW_FINAL_PAPER_PDF",
                "/nfs/roberts/scratch/pi_btk22/zc362/mass_openreview_final.pdf",
            )
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "paper_runs/paper_replication_audits/mass",
    )
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_audit(
        args.source_root.resolve(),
        args.anonymous_source_root.resolve(),
        args.paper_v1_pdf.resolve(),
        args.paper_pdf.resolve(),
        args.openreview_final_paper_pdf.resolve(),
        args.output_dir.resolve(),
    )
    print(json.dumps(manifest, indent=2))
    return int(args.strict and not manifest["full_paper_reproduced"])


if __name__ == "__main__":
    sys.exit(main())
