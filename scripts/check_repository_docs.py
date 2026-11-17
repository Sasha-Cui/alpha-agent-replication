#!/usr/bin/env python3
"""Check current repository navigation and its compact study-status snapshot.

Read-only and offline: no study runners, network, Git commands, or data services.
Historical snapshot contents and private evidence payloads are outside this check.
"""

import argparse
import hashlib
import csv
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

DOCUMENTS = (
    "README.md",
    "COLLABORATOR_HANDOFF.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/CURRENT_STUDY.md",
    "docs/DEVELOPMENT.md",
    "docs/ci/README.md",
    "scripts/README.md",
    "paper_runs/README.md",
    "docs/PROJECT_BRIEFING.md",
    "docs/RESEARCH_HANDOFF.md",
    "docs/presentations/LLM_INVESTMENT_STUDY_20261117.md",
    "docs/presentations/README.md",
    "docs/presentations/BEAMER_README.md",
    "paper_runs/native_monthly_implementation_v2_20261116/README.md",
)
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def prose_lines(text):
    """Exclude fenced examples from navigation and heading checks."""
    fence = None
    result = []
    for line in text.splitlines():
        match = FENCE.match(line)
        if match:
            marker = match.group(1)[0]
            fence = None if fence == marker else marker
            continue
        if fence is None:
            result.append(line)
    return result


def heading_anchors(text):
    counts = {}
    anchors = set()
    for line in prose_lines(text):
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        base = re.sub(r"[^\w\- ]", "", match.group(1).lower()).replace(" ", "-")
        count = counts.get(base, 0)
        counts[base] = count + 1
        anchors.add(base if count == 0 else "{}-{}".format(base, count))
    return anchors


def validate_presentation_manifest(manifest_path):
    """Check delivered files and the Markdown-to-Beamer provenance link offline."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    directory = manifest_path.parent
    for name, item in manifest["files"].items():
        if Path(name).name != name:
            errors.append("Presentation manifest requires a local filename: " + name)
            continue
        path = directory / name
        if not path.is_file():
            errors.append("Missing presentation asset: " + name)
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            errors.append("Presentation asset hash changed: " + name)
        if len(data) != item["bytes"]:
            errors.append("Presentation asset size changed: " + name)
    source = manifest.get("source_markdown")
    if source:
        if Path(source).name != source or not (directory / source).is_file():
            errors.append("Missing presentation source Markdown: " + source)
        elif hashlib.sha256((directory / source).read_bytes()).hexdigest() != manifest["source_markdown_sha256"]:
            errors.append("Beamer source Markdown changed; rebuild and verify the presentation.")
    return errors


def validate_v2_admission(status, package, paths):
    """Check source versus financial admission without treating exit0 as success."""
    errors = []
    if len({(r["paper_id"], r["arm"], str(r["fee_bps"])) for r in paths}) != len(paths):
        errors.append("V2 economic path identities must be unique.")
    for case, record in package["cases"].items():
        own = [r for r in paths if r["paper_id"] == case]
        good = sum(r["status"] == "verified_conditional_account" for r in own)
        failed = sum(r["status"] == "blocked" for r in own)
        if (good, failed) != (record["verified_paths"], record["failed_paths"]):
            errors.append(case + ": economic path counts disagree with saved status.")
        if good + failed != len(own):
            errors.append(case + ": unrecognized economic path state.")
        primary = {"M023": {"LLM_pooled", "grammar_pooled"},
                   "M050": {"ratio_LLMS_nonhold", "ratio_universe_EW"}}.get(case, set())
        admitted_primary = {r["arm"] for r in own if str(r["fee_bps"]) == "10"
                            and r["status"] == "verified_conditional_account"}
        if record["primary_comparison_admitted"] and not primary.issubset(admitted_primary):
            errors.append(case + ": primary financial admission lacks complete primary/control paths.")
        if not record["source_complete"] or not record["exact_replay_complete"]:
            errors.append(case + ": admitted source lacks complete exact replay.")
    source = sorted(package["source_admitted_paper_ids"])
    if source != sorted(status["mechanism_inventory"]["monthly_admitted_paper_ids"]):
        errors.append("V2 source admission disagrees with the current inventory.")
    financial = sorted(k for k, v in package["cases"].items() if v["primary_comparison_admitted"])
    if financial != sorted(status["mechanism_inventory"]["primary_economic_comparison_admitted_paper_ids"]):
        errors.append("V2 financial admission disagrees with the current status.")
    if status["study_status"] == "complete" and financial != source:
        errors.append("Study cannot claim completion while a source-admitted primary remains blocked.")
    return errors


def check(root):
    errors = []
    checked_links = 0
    external_links = 0
    for relative in DOCUMENTS:
        document = root / relative
        if not document.is_file():
            errors.append("Missing reader document: " + relative)
            continue
        text = document.read_text(encoding="utf-8")
        for raw in LINK.findall("\n".join(prose_lines(text))):
            target = raw.strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                external_links += 1
                continue
            path = unquote(parsed.path)
            destination = (document.parent / path).resolve() if path else document
            try:
                destination.relative_to(root)
            except ValueError:
                errors.append("{}: link escapes repository: {}".format(relative, target))
                continue
            checked_links += 1
            if not destination.exists():
                errors.append("{}: missing target: {}".format(relative, target))
                continue
            if parsed.fragment and destination.is_file() and destination.suffix == ".md":
                anchors = heading_anchors(destination.read_text(encoding="utf-8"))
                if unquote(parsed.fragment) not in anchors:
                    errors.append("{}: missing heading: {}".format(relative, target))

    status_path = root / "docs/study/status.json"
    inventory_path = root / "docs/study/method_readiness.csv"
    rows = []
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
        with inventory_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        expected = ["M{:03d}".format(i) for i in range(1, 70)]
        if sorted(row["paper_id"] for row in rows) != expected:
            errors.append("Readiness inventory must retain each of M001..M069 exactly once.")
        executed = sorted(
            row["paper_id"]
            for row in rows
            if row["mechanism_readiness"].startswith(
                "Central_mechanism_has_actual_execution_evidence"
            )
        )
        if executed != status["mechanism_inventory"]["central_execution_evidence_paper_ids"]:
            errors.append("Execution-evidence IDs disagree between CSV and status snapshot.")
        admitted = sorted(
            row["paper_id"]
            for row in rows
            if row["monthly_transfer_admitted"].lower() == "true"
        )
        if admitted != status["mechanism_inventory"]["monthly_admitted_paper_ids"]:
            errors.append("Monthly-admission IDs disagree between CSV and status snapshot.")
        if status["mechanism_inventory"]["paper_count"] != len(rows):
            errors.append("Paper count disagrees between CSV and status snapshot.")
        expected_csv = status["mechanism_inventory"].get("csv_sha256")
        if expected_csv and hashlib.sha256(inventory_path.read_bytes()).hexdigest() != expected_csv:
            errors.append("Readiness CSV hash disagrees with the current snapshot.")
        current = status.get("native_monthly_study", {})
        if current.get("version") == 2:
            package_path = root / current["status_path"]
            package = json.loads(package_path.read_text(encoding="utf-8"))
            if hashlib.sha256(package_path.read_bytes()).hexdigest() != current["status_sha256"]:
                errors.append("V2 aggregate status hash disagrees with the current snapshot.")
            with (package_path.parent / "economic_path_status.csv").open(newline="", encoding="utf-8") as handle:
                paths = list(csv.DictReader(handle))
            errors.extend(validate_v2_admission(status, package, paths))
            verification = json.loads((package_path.parent / "verification.json").read_text())
            for relative, expected in verification["exports"].items():
                actual = hashlib.sha256((package_path.parent / relative).read_bytes()).hexdigest()
                if actual != expected:
                    errors.append("V2 export hash changed: " + relative)
            for name in ("presentation_assets.json", "beamer_manifest.json"):
                errors.extend(validate_presentation_manifest(root / "docs/presentations" / name))
        benchmark = status["benchmark"]
        if benchmark["factor_count"] != 5 + 1 + benchmark["jkp_factor_count"]:
            errors.append("Benchmark count must equal FF5 + momentum + JKP factors.")
        if benchmark["jkp_factor_count"] != 132 or benchmark["risk_free_is_separate"] is not True:
            errors.append("Current benchmark must retain JKP132 with RF separate.")
        if status["study_status"] not in {"provisional", "complete"}:
            errors.append("Study status is not recognized.")
        if status["study_status"] == "provisional":
            for relative in ("README.md", "docs/CURRENT_STUDY.md"):
                if "provisional" not in (root / relative).read_text(encoding="utf-8").lower():
                    errors.append(relative + ": provisional status is not visible.")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append("Cannot validate current study snapshot: {}".format(exc))

    return {
        "status": "PASS" if not errors else "FAIL",
        "documents_checked": len(DOCUMENTS),
        "local_links_checked": checked_links,
        "external_links_not_fetched": external_links,
        "paper_records_checked": len(rows),
        "historical_snapshot_contents_revalidated": False,
        "scientific_runs_or_private_data_read": False,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", help="Print the complete check report.")
    args = parser.parse_args()
    report = check(args.root.resolve())
    if args.json:
        print(json.dumps(report, indent=2))
    elif report["errors"]:
        print("\n".join(report["errors"]))
    else:
        print(
            "PASS: {} documents, {} local links, and {} paper records; offline/read-only.".format(
                report["documents_checked"],
                report["local_links_checked"],
                report["paper_records_checked"],
            )
        )
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
