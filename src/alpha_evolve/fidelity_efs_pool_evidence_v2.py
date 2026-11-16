"""Intrinsic complete-source and exact-replay gates for EFS pool evaluations."""

import json
from alpha_evolve.openrouter_budget import sha256


def require_replay_binding(manifest, replay):
    if manifest["status"] != "complete" or manifest["llm_calls"] != 290:
        raise ValueError("Incomplete source trajectory")
    if replay["status"] != "pass" or replay["network_calls"] != 0 or not replay["holdings_byte_identical"]:
        raise ValueError("Full offline replay gate failed")
    if replay.get("ledger_mutations") != 0 and replay.get("authoritative_ledger_unchanged") is not True:
        raise ValueError("Replay has no unchanged-ledger evidence")
    if replay["exact_output_hashes"] != manifest["output_sha256"]:
        raise ValueError("Replay does not bind every completed source output")
    if any(r["status"] != "pass" for r in replay.get("transport_prefix_validation", [])):
        raise ValueError("Preserved source history failed replay")


def validate_efs_trial(root, trial):
    frozen = trial == "gpt41_1"
    if trial not in ["gpt41_1", "gpt41_2", "gpt41_3", "deepseek_v3_1", "deepseek_v3_2", "deepseek_v3_3"]:
        raise ValueError("Unplanned EFS trial")
    folder = (
        root / "paper_runs/economic_fidelity/efs_v1"
        if frozen
        else root / "paper_runs/fidelity_completion_v2/efs" / trial
    )
    private = (
        root / "artifacts/economic_fidelity/v1" if frozen else root / "artifacts/fidelity_completion_v2/efs" / trial
    )
    destination = private / ("network_disabled_replay" if frozen else "offline_replay")
    replay_path = folder / "validation_canonical_replay_llm.json" if frozen else destination / "validation.json"
    if not replay_path.exists():
        raise ValueError("Required completed full replay unavailable: " + trial)
    manifest_path = folder / "llm_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    replay = json.loads(replay_path.read_text())
    require_replay_binding(manifest, replay)
    if (frozen and replay["mode"] != "llm") or (not frozen and replay["trial"] != trial):
        raise ValueError("Replay trial identity substituted")
    recipe_path = folder / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    if sha256(recipe_path) != manifest["recipe_sha256"]:
        raise ValueError("Completed trial recipe changed")
    for name, digest in recipe["implementation_sha256"].items():
        if sha256(root / name) != digest:
            raise ValueError("Frozen original EFS engine changed")
    for name, digest in manifest["output_sha256"].items():
        if "/" in name or "\\" in name:
            raise ValueError("Unexpected source artifact path")
        if sha256(folder / name) != digest or sha256(destination / "results" / name) != digest:
            raise ValueError("Completed source or replay output bytes changed")
    weights = private / "llm_daily_weights.parquet"
    replayed_weights = destination / "private/llm_daily_weights.parquet"
    if (
        sha256(weights) != manifest["private_weights_sha256"]
        or sha256(replayed_weights) != manifest["private_weights_sha256"]
    ):
        raise ValueError("Completed source or replay holdings changed")
    proof = {
        "manifest_sha256": sha256(manifest_path),
        "recipe_sha256": sha256(recipe_path),
        "library_sha256": sha256(folder / "llm_factor_library.json"),
        "full_replay_path": str(replay_path.relative_to(root)),
        "full_replay_sha256": sha256(replay_path),
        "private_weights_sha256": manifest["private_weights_sha256"],
        "frozen_implementation_sha256": recipe["implementation_sha256"],
        "transport_prefixes": len(replay.get("transport_prefix_validation", [])),
    }
    return proof
