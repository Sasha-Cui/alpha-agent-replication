#!/usr/bin/env python3
# ruff: noqa: E402 - original driver bootstrap
"""Run the unchanged source-role driver under a separate capped input-repair study."""

from pathlib import Path
import sys
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.publication_llm import canonical_meter
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.alphabet_news_view_v2 import install_news_view
from alpha_evolve.alphabet_news_sources_v2 import install_single_news_source

spec = importlib.util.spec_from_file_location("source_role_driver", ROOT / "scripts/run_tradingagents_fidelity_v2.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def metered(root, key, *, model, study, cap, input_price, output_price, offline=False):
    return canonical_meter(
        root,
        key,
        model=model,
        study="fidelity_v2_tradingagents_alphabet_news_repair",
        cap=5,
        input_price=input_price,
        output_price=output_price,
        offline=offline,
    )


driver.canonical_meter = metered
install_news_view(driver.DatedTools)
install_single_news_source(driver.DatedTools)
name = sys.argv[sys.argv.index("--output-name") + 1]
atomic_json(
    ROOT / "artifacts/fidelity_completion_v2" / name / "wrapper.json",
    {
        "wrapper_sha256": sha256(Path(__file__)),
        "original_driver_sha256": sha256(ROOT / "scripts/run_tradingagents_fidelity_v2.py"),
        "scope": "Original graph/model/account settings, new issuer-news input; separate5USD study cap",
        "frozen_original_results_unchanged": True,
        "news_source_policy": "single_frozen_company_corpus",
        "news_source_policy_implementation_sha256": sha256(ROOT / "src/alpha_evolve/alphabet_news_sources_v2.py"),
        "prior_partial_attempt": "tradingagents_GOOGL_company_news",
        "news_view": "source_style_full_text",
        "news_view_implementation_sha256": sha256(ROOT / "src/alpha_evolve/alphabet_news_view_v2.py"),
    },
)
driver.main()
