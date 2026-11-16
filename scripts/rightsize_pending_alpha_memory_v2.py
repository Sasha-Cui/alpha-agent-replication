#!/usr/bin/env python3
# ruff: noqa: E402 - source bootstrap
"""Adjust only unstarted Alpha trial memory from measured completed-trial demand."""

from pathlib import Path
from datetime import datetime, timezone
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256


def main():
    out = ROOT / "artifacts/fidelity_completion_v2/alpha_pending_memory_20260917.json"
    if out.exists():
        raise ValueError("Preserve the existing operational audit")
    history = subprocess.check_output(
        [
            "/opt/slurm/current/bin/sacct",
            "-n",
            "-j",
            ",".join(f"26502926_{i}" for i in range(2, 8)),
            "--format=JobID,State,MaxRSS",
            "-P",
        ],
        text=True,
    )
    measured = []
    for line in history.splitlines():
        fields = line.strip().split("|")
        if len(fields) == 3 and fields[0].endswith(".batch"):
            if fields[1] != "COMPLETED" or not re.fullmatch(r"\d+K", fields[2]):
                raise ValueError("Incomplete/unavailable empirical memory evidence")
            measured.append({"job": fields[0], "maximum_rss_kib": int(fields[2][:-1])})
    if len(measured) != 6:
        raise ValueError("All six completed trial observations required")
    maximum = max(r["maximum_rss_kib"] for r in measured)
    target_mib = 32768
    if target_mib * 1024 < 2.4 * maximum:
        raise ValueError("Insufficient margin over observed peak")
    audit = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "basis": "Scheduler MaxRSS from six completed five-attempt trials; no evaluation-return selection. Request32GiB instead of64GiB only for unstarted tasks, retaining over2.4x measured peak. This is operational headroom evidence, not a guarantee on every generated program.",
        "observations": measured,
        "observed_peak_gib": maximum / 1024 / 1024,
        "new_requested_gib": 32,
        "unchanged": [
            "20CPUs",
            "3hour limit",
            "array throttle2",
            "model/data/code/seed/attempt/cost settings",
            "all running tasks",
        ],
        "actions": [],
    }
    atomic_json(out, audit)
    for i in range(8, 21):
        job = f"26502926_{i}"
        read = subprocess.run(
            ["/opt/slurm/current/bin/scontrol", "show", "job", job, "-o"], text=True, capture_output=True
        )
        if read.returncode:
            continue
        before = read.stdout.strip()
        if "JobState=PENDING" not in before:
            continue
        if not all(
            x in before
            for x in [
                "ArrayJobId=26502926",
                "ArrayTaskThrottle=2",
                "NumCPUs=20 ",
                "TimeLimit=03:00:00",
                "MinMemoryNode=64G",
            ]
        ):
            raise ValueError("Unexpected pending trial configuration")
        row = {"job": job, "before": before}
        audit["actions"].append(row)
        atomic_json(out, audit)
        update = subprocess.run(
            ["/opt/slurm/current/bin/scontrol", "update", "JobId=" + job, "MinMemoryNode=" + str(target_mib)],
            text=True,
            capture_output=True,
        )
        row["update"] = {"returncode": update.returncode, "stdout": update.stdout, "stderr": update.stderr}
        atomic_json(out, audit)
        if update.returncode:
            raise RuntimeError("Memory update failed; inspect audit before another action")
        after = subprocess.check_output(
            ["/opt/slurm/current/bin/scontrol", "show", "job", job, "-o"], text=True
        ).strip()
        row["after"] = after
        if "MinMemoryNode=32G" not in after or not all(
            x in after for x in ["NumCPUs=20 ", "TimeLimit=03:00:00", "ArrayTaskThrottle=2"]
        ):
            raise ValueError("Resource update changed unintended settings")
        atomic_json(out, audit)
    audit.update(status="complete", script_sha256=sha256(Path(__file__)))
    atomic_json(out, audit)
    print("PENDING_ALPHA_MEMORY_AUDIT_COMPLETE", len(audit["actions"]), audit["observed_peak_gib"])


if __name__ == "__main__":
    main()
