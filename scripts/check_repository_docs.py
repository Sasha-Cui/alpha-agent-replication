#!/usr/bin/env python3
"""Check current repository navigation and its compact study-status snapshot.

Read-only and offline: no study runners, network, Git commands, or data services.
Historical snapshot contents and private evidence payloads are outside this check.
"""

import argparse
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
    "scripts/README.md",
    "paper_runs/README.md",
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
