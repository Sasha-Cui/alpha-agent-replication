#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Release only verified completed Quanta task dependencies, preserving every job."""

from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from alpha_evolve.openrouter_budget import atomic_json, sha256
from analyze_native_oos_v2 import load_arm


def main():
    out = ROOT / "artifacts/fidelity_completion_v2/secondary_analysis_20260917/dependency_release_verified.json"
    if out.exists():
        raise ValueError("Preserve prior repair; inspect its exact job states before a new action")
    evidence = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "reason": "Existing aftercorr edges remain unfulfilled for tasks already COMPLETED. Validate source completion/account and remove only that already-satisfied task edge after the exact-task afterok update was rejected by Slurm (archived). No new job/training.",
        "actions": [],
    }
    for target, source, arm in [
        ("26525365", "26515242", "source4_plus_library"),
        ("26525373", "26515243", "alpha158_plus_library"),
    ]:
        for i in range(7):
            result = subprocess.run(
                ["/opt/slurm/current/bin/scontrol", "show", "job", f"{target}_{i}", "-o"],
                text=True,
                capture_output=True,
            )
            if result.returncode:
                continue
            before = result.stdout.strip()
            if (
                "JobState=PENDING" not in before
                or "Reason=Dependency " not in before
                or f"Dependency=aftercorr:{source}_*(unfulfilled)" not in before
            ):
                continue
            state = subprocess.run(
                [
                    "/opt/slurm/current/bin/sacct",
                    "-n",
                    "-X",
                    "-j",
                    f"{source}_{i}",
                    "--format=JobID,State,ExitCode",
                    "-P",
                ],
                check=True,
                text=True,
                capture_output=True,
            ).stdout
            if [f"{source}_{i}", "COMPLETED", "0:0"] not in [line.strip().split("|") for line in state.splitlines()]:
                continue
            name = f"quantaalpha_bounded_task_{i:02d}_oos_{arm}"
            _, proof = load_arm(name, "quantaalpha", arm, False, secondary_unit=i)
            proof.pop("core_settings")
            row = {
                "source": f"{source}_{i}",
                "target": f"{target}_{i}",
                "before": before,
                "terminal_source_state": state.strip(),
                "validated_source": proof,
            }
            evidence["actions"].append(row)
            atomic_json(out, evidence)
            action = subprocess.run(
                [
                    "/opt/slurm/current/bin/scontrol",
                    "update",
                    f"JobId={target}_{i}",
                    "Dependency=",
                ],
                text=True,
                capture_output=True,
            )
            row["update"] = {"returncode": action.returncode, "stdout": action.stdout, "stderr": action.stderr}
            atomic_json(out, evidence)
            if action.returncode:
                raise RuntimeError("Verified dependency release failed; no duplicate job was issued")
            row["after"] = subprocess.run(
                ["/opt/slurm/current/bin/scontrol", "show", "job", f"{target}_{i}", "-o"],
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            atomic_json(out, evidence)
    evidence["script_sha256"] = sha256(Path(__file__))
    evidence["status"] = "complete"
    atomic_json(out, evidence)
    print("VERIFIED_EXISTING_DEPENDENCIES_REPAIRED", len(evidence["actions"]))


if __name__ == "__main__":
    main()
