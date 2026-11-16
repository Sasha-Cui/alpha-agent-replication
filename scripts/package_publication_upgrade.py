#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Create private execution and review bundles only after the final evidence checks."""

from pathlib import Path
import sys
import json
import ast
import re
import posixpath
import tarfile
import shutil
import sqlite3
import fcntl
from contextlib import closing
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256
import subprocess

PUBLIC = ROOT / "paper_runs/publication_upgrade_v1"
PRIVATE = ROOT / "artifacts/publication_upgrade_v1"


def main():
    subprocess.run(
        [str(ROOT / "scripts/run_finmem_fidelity_python.sh"), str(ROOT / "scripts/validate_publication_integrity.py")],
        check=True,
        cwd=ROOT,
    )
    required = [
        PUBLIC / "analysis/status.json",
        PUBLIC / "report_validation.json",
        PRIVATE / "finmem_full_replay_validation.json",
        PRIVATE / "finagent_full_replay_validation.json",
        PRIVATE / "tradingagents_full_replay_validation.json",
        PRIVATE / "full_test_status.json",
        PRIVATE / "transport_recovery_test_status.json",
        PRIVATE / "execution_contract_validation.json",
        PRIVATE / "frozen_evidence_integrity.json",
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError("Required final validation is absent: " + str(path))
        record = json.loads(path.read_text())
        if path.name == "full_test_status.json":
            if record["python312_exit"] or record["python39_exit"]:
                raise ValueError("Full test run did not pass")
        elif record.get("status") not in ["complete", "pass"]:
            raise ValueError("Required check is not complete: " + str(path))
    if (
        not (PUBLIC / "visual_qa.json").exists()
        or json.loads((PUBLIC / "visual_qa.json").read_text()).get("status") != "pass"
    ):
        raise ValueError("Final visual QA has not been recorded")
    report = json.loads((PUBLIC / "report_manifest.json").read_text())
    pdf_digest = sha256(PUBLIC / report["pdf"])
    for name in ["report_validation.json", "visual_qa.json"]:
        if json.loads((PUBLIC / name).read_text()).get("pdf_sha256") != pdf_digest:
            raise ValueError("Stale PDF validation: " + name)
    if report["pdf_sha256"] != pdf_digest or report["builder_sha256"] != sha256(
        ROOT / "scripts/build_publication_report.py"
    ):
        raise ValueError("Rendered report or builder changed after validation")
    for name, digest in report["analysis_file_sha256"].items():
        if sha256(PUBLIC / "analysis" / name) != digest:
            raise ValueError("Analysis changed after report validation: " + name)
    if report["spend_summary_sha256"] != sha256(PUBLIC / "spend_summary.json"):
        raise ValueError("Spending summary changed after rendering")
    transport_tests = json.loads((PRIVATE / "transport_recovery_test_status.json").read_text())
    if transport_tests["python312_exit"] or transport_tests["python39_exit"]:
        raise ValueError("Transport recovery checks failed")
    for name, digest in transport_tests["implementation_sha256"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError("Transport recovery implementation changed after its checks")
    sys.path.insert(0, str(ROOT / "scripts"))
    from resume_finagent_after_transport_failure import compare_preserved_prefixes

    for recovery in PRIVATE.glob("finagent_transport_supervisor_*/recovery_*"):
        validation = recovery / "prefix_validation.json"
        resolved = compare_preserved_prefixes(recovery, PRIVATE / "finagent_native")
        resolved["original_validation_sha256"] = sha256(validation) if validation.exists() else None
        resolved["final_native_sha256"] = sha256(PRIVATE / "finagent_native/decisions.jsonl")
        atomic_json(recovery / "prefix_resolution.json", resolved)
        if resolved["status"] != "pass":
            raise ValueError("A supervised recovery prefix is unverified: " + str(recovery))
    package_root = PRIVATE / "packages"
    package_root.mkdir(exist_ok=True)
    snapshot = package_root / "model_cache_snapshot"
    snapshot.mkdir(exist_ok=True)
    cache = ROOT / "runs/economic_fidelity/openrouter"
    # Copy the ledger and append journal consistently; compression happens after
    # releasing the locks. No source model request is issued by this operation.
    with (cache / "project_spend.lock").open("a+") as ledger_lock:
        fcntl.flock(ledger_lock, fcntl.LOCK_EX)
        with (cache / "cohort_response_journal.lock").open("a+") as journal_lock:
            fcntl.flock(journal_lock, fcntl.LOCK_EX)
            state = json.loads((cache / "project_spend.json").read_text())
            if json.loads((PUBLIC / "spend_summary.json").read_text())["ledger_sha256_at_snapshot"] != sha256(
                cache / "project_spend.json"
            ):
                raise ValueError("Live spending changed after the final report snapshot")
            if any(c["status"] == "reserved" for c in state["calls"].values()):
                raise ValueError("A paid request is still in flight; snapshot after it settles")
            for name in ["project_spend.json", "cohort_responses.jsonl", "technical_recoveries.json"]:
                if (cache / name).exists():
                    shutil.copyfile(cache / name, snapshot / name)
            with (
                closing(
                    sqlite3.connect("file:" + str(cache / "response_cache.sqlite3") + "?mode=ro", uri=True)
                ) as source,
                closing(sqlite3.connect(snapshot / "response_cache.sqlite3")) as destination,
            ):
                source.backup(destination)
            fcntl.flock(journal_lock, fcntl.LOCK_UN)
        fcntl.flock(ledger_lock, fcntl.LOCK_UN)
    names = json.loads((PRIVATE / "new_code_files.json").read_text())
    names += list(
        json.loads((ROOT / "paper_runs/economic_fidelity/efs_v1/recipe.json").read_text())["implementation_sha256"]
    )
    names += [
        "scripts/validate_publication_report.py",
        "scripts/summarize_publication_spend.py",
        "scripts/archive_publication_dependencies.py",
        "scripts/replay_publication_native.py",
        "scripts/package_publication_upgrade.py",
        "src/alpha_evolve/publication_replay.py",
        "tests/test_publication_replay.py",
        "environment.toml",
        "README.md",
        "AGENTS.md",
        "docs/PUBLICATION_UPGRADE_PROTOCOL.md",
        "docs/PUBLICATION_UPGRADE_RUNBOOK.md",
    ]
    names += [
        "scripts/run_finmem_fidelity_python.sh",
        "scripts/run_finagent_paper_python.sh",
        "scripts/run_tradingagents_v010_python.sh",
        "scripts/run_quantaalpha_fidelity_python.sh",
        "scripts/run_efs_economic_fidelity.py",
        "scripts/replay_efs_economic_fidelity.py",
        "scripts/validate_efs_economic_fidelity.py",
        "scripts/evaluate_efs_equal_weight.py",
        "src/alpha_evolve/economic_fidelity.py",
        "src/alpha_evolve/openrouter_budget.py",
    ]
    names += [str(p.relative_to(ROOT)) for p in (ROOT / "environment_specs").glob("*.json")]
    for packet in json.loads((PUBLIC / "source_review/packet_manifest.json").read_text())["packets"]:
        for name, digest in packet["implementation_sha256"].items():
            if sha256(ROOT / name) != digest:
                raise ValueError("Source-review packet is stale: " + name)
        names.extend(packet["implementation_sha256"])
    # Bundle project modules imported by the listed entry points. Native upstream
    # repositories are preserved separately in the private dependency archives.
    pending = list(dict.fromkeys(names))
    included = set()
    while pending:
        name = pending.pop()
        path = ROOT / name
        if name in included or not path.is_file():
            continue
        included.add(name)
        if path.suffix != ".py":
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            )
            for module in modules:
                pending.append("scripts/" + module.replace(".", "/") + ".py")
                if module == "alpha_evolve" or module.startswith("alpha_evolve."):
                    base = "src/" + module.replace(".", "/")
                    pending.extend([base + ".py", base + "/__init__.py", "src/alpha_evolve/__init__.py"])
    code_files = sorted(included)
    review = package_root / "alpha_agent_publication_review_20260907.tar.gz"

    def add_public(tar):
        for name in code_files:
            if not name.startswith("paper_runs/publication_upgrade_v1/"):
                tar.add(ROOT / name, arcname=name, recursive=False)
        for path in sorted(PUBLIC.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(PUBLIC)
            if (
                any(part.endswith("_preview") or part == "analysis_preview" for part in relative.parts)
                or path.name.startswith("PREVIEW_")
                or "preview" in path.name
                or path.name == "package_manifest.json"
            ):
                continue
            tar.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)

    with tarfile.open(review, "w:gz", compresslevel=6) as tar:
        add_public(tar)
    # Check links inside the actual review archive, not only in the live checkout.
    with tarfile.open(review, "r:gz") as tar:
        members = set(tar.getnames())
        for report_name in ["REPORT.md", "VISUAL_REPORT.md"]:
            base = "paper_runs/publication_upgrade_v1/" + report_name
            body = tar.extractfile(base).read().decode()
            for link in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", body):
                if link.startswith(("http://", "https://", "#")):
                    continue
                target = posixpath.normpath(posixpath.join(posixpath.dirname(base), link))
                if target not in members:
                    raise ValueError("Review archive has a broken report link: " + link)
    private = package_root / "alpha_agent_publication_execution_20260907.tar.gz"
    excluded = {"packages", "finsaber_data", "sources"}
    with tarfile.open(private, "w:gz", compresslevel=3) as tar:
        add_public(tar)
        for path in sorted(PRIVATE.rglob("*")):
            relative = path.relative_to(PRIVATE)
            if any(part in excluded for part in relative.parts) or not path.is_file() or path.is_symlink():
                continue
            if path.name.endswith(".lock") or path.name.startswith("PAUSE_"):
                continue
            tar.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
        for path in snapshot.iterdir():
            tar.add(path, arcname="runs/economic_fidelity/openrouter/" + path.name, recursive=False)
        for directory in [
            "artifacts/economic_fidelity/v1",
            "paper_runs/economic_fidelity/efs_v1",
            "runs/prompt_replay/guruagents/guruagents_full_20260809T010651Z",
            "paper_runs/prompt_replay/guruagents/performance",
        ]:
            source = ROOT / directory
            if source.exists():
                tar.add(source, arcname=directory)
        for case in ["finmem", "finagent", "tradingagents", "guruagents", "quantaalpha"]:
            source = ROOT / "paper_runs/paper_replication_audits" / case
            for name in [
                "README.md",
                "manifest.json",
                "source_config_conformance.csv",
                "source_mechanism_conformance.csv",
                "paper_mechanism_conformance.csv",
                "complete_pool_native_result.json",
            ]:
                if (source / name).exists():
                    tar.add(source / name, arcname=str((source / name).relative_to(ROOT)), recursive=False)
        tokenizer = json.loads((ROOT / "environment_specs/tokenizer_cache.json").read_text())
        if sha256(Path(tokenizer["path"])) != tokenizer["sha256"]:
            raise ValueError("Pinned tokenizer cache changed")
        tar.add(
            tokenizer["path"], arcname="environment_assets/tiktoken/" + Path(tokenizer["path"]).name, recursive=False
        )
        slurm = ROOT.parent / "slurm/slurm_scripts"
        for path in slurm.glob("alpha_*fidelity*.sbatch"):
            tar.add(path, arcname="slurm_reference/" + path.name, recursive=False)
        for path in slurm.glob("alpha_*source_embedding.sbatch"):
            tar.add(path, arcname="slurm_reference/" + path.name, recursive=False)
        tar.add(
            slurm / "alpha_publication_final_evidence.sbatch",
            arcname="slurm_reference/alpha_publication_final_evidence.sbatch",
            recursive=False,
        )
    backup = Path("/nfs/roberts/scratch/pi_btk22/zc362/publication_upgrade_backup_20260907")
    backup.mkdir(parents=True, exist_ok=True)
    records = []
    for path in [review, private]:
        digest = sha256(path)
        target = backup / path.name
        shutil.copy2(path, target)
        if sha256(target) != digest:
            raise ValueError("Second-copy checksum mismatch")
        records.append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": digest,
                "second_copy": str(target),
                "second_copy_verified": True,
            }
        )
    atomic_json(
        PUBLIC / "package_manifest.json",
        {
            "status": "complete",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "packages": records,
            "durable_primary_location": "Roberts project allocation",
            "second_copy_retention": "Scratch is temporary and subject to purge; it is not the durable archive",
            "private_bundle_scope": "Execution inputs, exact source dependency archives, caches, outputs, tests and provenance. Full multi-company FINSABER download files are excluded; used prepared views and pinned download manifests are included. Central Python environments are represented by versioned manifests, not vendored installed packages.",
        },
    )
    print("PUBLICATION_BUNDLES_COMPLETE", json.dumps(records), flush=True)


if __name__ == "__main__":
    main()
