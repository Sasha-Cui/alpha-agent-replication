#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Recover fixed control libraries from archived evidence; no model/search rerun."""

from pathlib import Path
import hashlib
import json
import sys
import tarfile
import subprocess
import os
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from alpha_evolve.economic_fidelity import Factor, seed_factors
from alpha_evolve.publication_economics import cash_account
from alpha_evolve.fidelity_efs_grammar_pool_v2 import merge_grammar_discoveries
from run_efs_matched_search import proposal

PUBLIC = ROOT / "paper_runs/fidelity_completion_v2"
PRIVATE = ROOT / "artifacts/fidelity_completion_v2"


def main():
    protocol_path = PUBLIC / "efs_final_analysis_protocol.json"
    plan = json.loads(protocol_path.read_text())
    seeds = plan["matched_grammar_pool_seeds"]
    if seeds != [101, 102, 103]:
        raise ValueError("Fixed control seed IDs changed")
    out = PRIVATE / "efs_grammar_pool_inputs"
    out.mkdir(exist_ok=True)
    if (out / "completion.json").exists():
        raise ValueError("Preserve prepared control evidence")
    package_path = ROOT / "paper_runs/publication_upgrade_v1/package_manifest.json"
    if sha256(package_path) != plan["frozen_v1_package_manifest_sha256"]:
        raise ValueError("Frozen v1 package manifest changed")
    package = next(r for r in json.loads(package_path.read_text())["packages"] if "execution" in r["path"])
    archive = Path(package["path"])
    if sha256(archive) != package["sha256"]:
        raise ValueError("Frozen execution archive checksum failed")
    names = {
        f"artifacts/publication_upgrade_v1/efs_matched/seed_{s}/{f}"
        for s in seeds
        for f in ["completion.json", "daily_returns.csv", "proposals.json", "selections.json", "weights.parquet"]
    }
    names.update(["scripts/run_efs_matched_search.py", "paper_runs/publication_upgrade_v1/efs_matched_recipe.json"])
    names.update(
        [
            "artifacts/publication_upgrade_v1/prospective_efs_v1/seal.json",
            "artifacts/publication_upgrade_v1/preformat_semantic_hashes.json",
        ]
    )
    archived = {}
    with tarfile.open(archive, "r|gz") as tar:
        for member in tar:
            if member.name in names:
                if not member.isfile():
                    raise ValueError("Expected archived regular file")
                stream = tar.extractfile(member)
                h = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(chunk)
                archived[member.name] = h.hexdigest()
    if set(archived) != names:
        raise ValueError("Frozen archive omits required control evidence")
    for name, digest in archived.items():
        if sha256(ROOT / name) != digest:
            raise ValueError("Live control differs from immutable v1 archive: " + name)
    seal = json.loads((ROOT / "artifacts/publication_upgrade_v1/prospective_efs_v1/seal.json").read_text())
    semantic = subprocess.check_output(
        [
            str(ROOT / "scripts/run_finmem_fidelity_python.sh"),
            "-c",
            "from alpha_evolve.prospective import code_digest; print(code_digest('scripts/run_efs_matched_search.py'))",
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT / "src")},
        text=True,
    ).strip()
    if semantic != seal["semantic_code_sha256"][str(ROOT / "scripts/run_efs_matched_search.py")]:
        raise ValueError("Sealed control generator semantics changed")
    atomic_json(
        out / "archive_binding.json",
        {"archive_path": str(archive), "archive_sha256": package["sha256"], "members": archived, "status": "pass"},
    )
    recipe_path = ROOT / "paper_runs/economic_fidelity/efs_v1/recipe.json"
    recipe = json.loads(recipe_path.read_text())
    if sha256(recipe_path) != plan["frozen_source_recipe_sha256"]:
        raise ValueError("Frozen EFS recipe changed")
    for path, digest in recipe["implementation_sha256"].items():
        if sha256(ROOT / path) != digest:
            raise ValueError("Frozen original EFS implementation changed")
    data = ROOT / "artifacts/economic_fidelity/v1/efs_us50_daily.parquet"
    manifest_path = data.with_name("data_manifest.json")
    manifest = json.loads(manifest_path.read_text())
    if sha256(data) != manifest["daily_extract_sha256"]:
        raise ValueError("Frozen market input changed")
    frame = pd.read_parquet(data)
    tickers = sorted(frame.ticker.unique())
    returns = frame.pivot(index="date", columns="ticker", values="ret").reindex(columns=tickers).sort_index()
    dates = pd.DatetimeIndex(returns.index)
    expected = dates[(dates >= recipe["start"]) & (dates <= recipe["end"])]
    libraries = {}
    proofs = {}
    for seed in seeds:
        source = ROOT / f"artifacts/publication_upgrade_v1/efs_matched/seed_{seed}"
        done = json.loads((source / "completion.json").read_text())
        proposals = json.loads((source / "proposals.json").read_text())
        selections = json.loads((source / "selections.json").read_text())
        if (
            done["seed"] != seed
            or done["scheduled_rounds"] != 290
            or done["candidate_count"] != 870
            or done["days"] != 1510
            or len(proposals) != 870
        ):
            raise ValueError("Original control search budget differs")
        if done["recipe_sha256"] != plan["matched_grammar_recipe_sha256"]:
            raise ValueError("Original control recipe changed")
        rng = np.random.default_rng(seed)
        for number, recorded in enumerate(proposals, 1):
            round_no = (number - 1) // 3 + 1
            execution_index = int(
                dates.get_loc(expected[recipe["warmup_days"] + (round_no - 1) * recipe["search_interval_days"]])
            )
            if (
                recorded["code"] != proposal(rng, number)
                or recorded["number"] != number
                or recorded["round"] != round_no
                or recorded["decision_date"] != str(dates[execution_index - 1].date())
            ):
                raise ValueError("Archived control candidates differ from sealed generator or causal schedule")
        pool = {}
        for factor in seed_factors():
            pool[factor.sha256] = {
                "code": factor.code,
                "origin": factor.origin,
                "created_index": int(factor.created_index),
            }
        accepted = 0
        for row in proposals:
            if row["status"] != "accepted":
                continue
            index = int(dates.get_loc(pd.Timestamp(row["decision_date"])))
            factor = Factor(row["code"], "programmatic_grammar", index)
            if factor.sha256 in pool:
                raise ValueError("Duplicate accepted control code")
            pool[factor.sha256] = {"code": factor.code, "origin": factor.origin, "created_index": index}
            accepted += 1
        if accepted != done["accepted"]:
            raise ValueError("Accepted control library count differs")
        weights = pd.read_parquet(source / "weights.parquet")
        daily = pd.read_csv(source / "daily_returns.csv", parse_dates=["date"])
        if (
            not weights.index.equals(expected)
            or list(weights.columns) != tickers
            or not pd.DatetimeIndex(daily.date).equals(expected)
        ):
            raise ValueError("Exact full control calendar/universe changed")
        if [r["date"] for r in selections] != [str(d.date()) for d in expected]:
            raise ValueError("Control selections calendar changed")
        for date, row in zip(expected, selections):
            cutoff = int(dates.get_loc(date)) - 1
            if any(key not in pool or pool[key]["created_index"] > cutoff for key in row["factor_hashes"]):
                raise ValueError("Control uses unavailable/future factor")
        maximum = 0.0
        for cost in [0, 10, 25, 50]:
            result, turn, _ = cash_account(weights.to_numpy(float), returns.loc[expected].to_numpy(float), cost)
            error = max(
                float(np.max(np.abs(result - daily[f"total_cost_{cost}"]))),
                float(np.max(np.abs(turn - daily[f"turnover_cost_{cost}"]))),
            )
            maximum = max(maximum, error)
            if error > 1e-12:
                raise ValueError("Independent archived control accounting mismatch")
        libraries[str(seed)] = pool
        atomic_json(out / f"grammar_{seed}_library.json", pool)
        proofs[str(seed)] = {
            "source": str(source.relative_to(ROOT)),
            "completion_sha256": sha256(source / "completion.json"),
            "accepted": accepted,
            "factors_including_initial": len(pool),
            "maximum_independent_account_difference": maximum,
            "recorded_selection_discovery_dates_pass": True,
            "source_files_match_frozen_archive": True,
            "recorded_execution_driver_sha256": done["script_sha256"],
            "archived_formatted_driver_sha256": sha256(ROOT / "scripts/run_efs_matched_search.py"),
            "raw_driver_bytes_identical_to_execution": done["script_sha256"]
            == sha256(ROOT / "scripts/run_efs_matched_search.py"),
            "sealed_semantic_driver_sha256_python310": semantic,
            "all870_candidate_codes_and_discovery_dates_match_sealed_generator": True,
            "scope_of_replay": "Generator/schedule conformance and independent saved-weight accounting; no full search/model rerun. Historical raw execution script hash differs after formatting. Exact archive and sealed AST are verified, not mislabelled byte-identical historical source.",
            "new_search_or_model_run": False,
        }
    merged = merge_grammar_discoveries(libraries)
    atomic_json(out / "discovery_library.json", merged)
    atomic_json(
        out / "completion.json",
        {
            "status": "archive_bound_control_libraries_and_accounts_pass",
            "seeds": seeds,
            "source_proofs": proofs,
            "library_sha256": sha256(out / "discovery_library.json"),
            "archive_binding_sha256": sha256(out / "archive_binding.json"),
            "data_sha256": sha256(data),
            "protocol_sha256": sha256(protocol_path),
            "script_sha256": sha256(Path(__file__)),
            "new_model_calls": 0,
            "new_search_runs": 0,
            "pooled_financial_evaluation_complete": False,
        },
    )
    print("ARCHIVED_CONTROL_LIBRARIES_AND_ACCOUNTS_PASS", len(merged), flush=True)


if __name__ == "__main__":
    main()
