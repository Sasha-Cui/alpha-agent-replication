#!/usr/bin/env python3
"""Preserve the exact third-party source/input dependencies in durable project storage."""

from pathlib import Path
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/publication_upgrade_v1/dependency_archives"
OUT.mkdir(parents=True, exist_ok=True)
SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362")
SOURCES = {
    "finmem_source": SCRATCH / "finmem_source",
    "finagent_source": SCRATCH / "finagent_source",
    "tradingagents_v010": SCRATCH / "tradingagents_v010",
    "guruagents_source": SCRATCH / "guruagents_prompt_replay_source",
    "quantaalpha_source": SCRATCH / "quantaalpha_recovery/source_8a0343",
    "quantaalpha_provider": SCRATCH / "quantaalpha_recovery/provider/cn_data",
    "quantaalpha_computed_factor_cache": SCRATCH / "quantaalpha_recovery/factor_cache_gpt_complete",
}
EXCLUDED = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(4 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


manifest = []
for name, source in SOURCES.items():
    archive = OUT / (name + ".tar.gz")
    inventory = OUT / (name + "_inventory.json")
    if archive.exists() and inventory.exists():
        row = json.loads(inventory.read_text())
        manifest.append(row)
        continue
    if not source.is_dir():
        raise FileNotFoundError(source)
    files = []
    omitted = []
    with tarfile.open(archive, "w:gz", compresslevel=3) as tar:
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if any(part in EXCLUDED or part.startswith(".env") for part in relative.parts):
                continue
            if path.is_symlink():
                omitted.append({"path": str(relative), "reason": "symlink, not dereferenced"})
                continue
            if not path.is_file() or path.suffix in [".pyc", ".pyo", ".mp4"]:
                continue
            tar.add(path, arcname=str(relative), recursive=False)
            files.append({"path": str(relative), "bytes": path.stat().st_size, "sha256": sha(path)})
    row = {
        "name": name,
        "source_path": str(source),
        "archive_path": str(archive.relative_to(ROOT)),
        "archive_sha256": sha(archive),
        "archive_bytes": archive.stat().st_size,
        "files": files,
        "omitted": omitted,
        "scope": "Private durable dependency snapshot; excludes credentials/environment files, Git metadata, bytecode and unneeded video. This is not a new working checkout.",
    }
    inventory.write_text(json.dumps(row, indent=2) + "\n")
    manifest.append(row)
    print("ARCHIVED", name, len(files), archive.stat().st_size, flush=True)
(OUT / "manifest.json").write_text(
    json.dumps(
        {"dependencies": [{k: v for k, v in row.items() if k not in ["files", "omitted"]} for row in manifest]},
        indent=2,
    )
    + "\n"
)
print("DEPENDENCY_ARCHIVES_COMPLETE", flush=True)
