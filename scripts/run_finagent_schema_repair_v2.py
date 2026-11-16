#!/usr/bin/env python3
# ruff: noqa: E402 - original driver bootstrap
"""Resume source FinAgent with its literal prompt typo mapped to the parser's key."""

from pathlib import Path
import sys
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.finagent_schema_repair_v2 import install_schema_repair

spec = importlib.util.spec_from_file_location("native_finagent_driver", ROOT / "scripts/run_finagent_fidelity_v2.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
name = sys.argv[sys.argv.index("--output-name") + 1]
output = ROOT / "artifacts/fidelity_completion_v2" / name
install_schema_repair(output)
atomic_json(
    output / "wrapper.json",
    {
        "wrapper_sha256": sha256(Path(__file__)),
        "source_driver_sha256": sha256(ROOT / "scripts/run_finagent_fidelity_v2.py"),
        "schema_repair": "released_long_term_reasonig_alias",
        "schema_repair_implementation_sha256": sha256(ROOT / "src/alpha_evolve/finagent_schema_repair_v2.py"),
        "preserved_prefix_path": str(ROOT / "artifacts/fidelity_completion_v2/finagent_TSLA/decisions.jsonl"),
        "scope": "The released HTML requests long_term_reasonig, but its parser requires long_term_reasoning. Preserve raw API/HTML and every word; canonicalize only that explicit key in the derived parsed dictionary. No new model response is selected.",
    },
)
driver.main()
