#!/usr/bin/env python3
"""Build a fail-closed source and result audit for Agentic AI Screening.

The arXiv bundle contains the manuscript, one workflow image, and bibliography,
not the experiment.  The paper links one public news dataset and prints one
December-2023 LLM-S prompt/output example.  Those recoverable components are
audited without promoting a later unaffiliated implementation to native code or
crediting any printed portfolio result as reproduced.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import tarfile
from collections import Counter
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/agentic_ai_screening_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/agentic_ai_screening"
WORK_ID = "CensusArxiv260323300"
SYSTEM_ID = "SYS-AGENTIC-AI-SCREENING"
ARXIV_ID = "2603.23300"
INDEPENDENT_COMMIT = "f6d056fae10e1ff2e77bf092e125ba09e93560d0"

PINS = {
    "primary/2603.23300v1.pdf": "4bc3147d386ab882c4c5589e43c79abe4af8ebf1f11ffcdf6fc5f496ef57ff1d",
    "primary/arxiv-abs.html": "e10462bb7a20ca1cac6cc7d3cc4ba8cce2a13bf5fd43478404666c7e73708b19",
    "primary/arxiv-api.xml": "e7e4dac0bf677e437a5b223d184591b8dd890954957ee3e5baad7ab0c04cf3a8",
    "source/2603.23300v1.tar": "7798b193b252c64332250ade11f17321f7ac1a47c7dcbf69dd34a57cb93758b5",
    "build/00README.json": "6a78b93ed7710cb1d9db39bad6ebf483cea429865948b6a4e8a6ca2faee97937",
    "build/agentic.bib": "37020249083f2f7d7878664d5ff11174fef0a9a202fe8ec3f1492f3155ffbab2",
    "build/Figure_workflow_1.0.png": "74467cd1f6a4d4cee7f5dc2d4b2f96d4ad28fd864ae6c0859c6e01a374f98a9a",
    "build/main.bbl": "1c7624296c4dbfb04103e49ae0e7ecd309322a842e70d5affc2395625550b929",
    "build/main.tex": "288f45134b467121335b2554dc796f9d69e48743d999cb2e85e584f8551701f3",
    "build/main.pdf": "03e14b0fa15a048a7b02381a3e56098d2c4b44ba8404676c71ea51d3630c05a4",
    "build/pass2.log": "c6ef38ee6c843e4b5005858799822827fd36bf857047dec11f5b791cde63fad4",
    "primary/gemini-2-flash-release.html": "036e07ffa71d3fd6214771d26c35387c0f85c7fd47868c8ef68a84222f640b47",
    "primary/gemini-2-flash-model.html": "20159c85d2ab1177fd7afa81a63ac5d228a455e6c1c41653f622b580771a29fa",
    "discovery/hf-dataset-api.json": "0f5a9deb13ca761934d9a2d2c6e775ec2a9dc74fe886768310bb9792285b1500",
    "discovery/hf-readme.md": "7659faedbb17e6523b81d275bf64e3158df6e222115a9ff4a7cacccf4294d065",
    "discovery/hf-news.jsonl": "c1585588777ef9be792aa4aac23f54b6ada7e469086e7887c95a31bb0cbbcae2",
    "discovery/github-arxiv-id.json": "3a79cd4f0865f2a78dde892ee39cf14345ae2b0b2781e9aa9204638cacb6901f",
    "discovery/github-authors.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-exact-title.json": "86dd4cb2c457c67cd10379b7f76cde29ad24f0a4e07cf8e7e60d9c70e073fd48",
    "discovery/alanhsieh2000_agentic_portfolio-repo.json": "7bb6bce65c066de6a643ff5215b8bcc84c9a3045750c10243abeb67ef8048705",
    "discovery/alanhsieh2000_agentic_portfolio-commits.json": "301ba4676478c16996873e36a4b08dcd951760a82374394f4af8335a6b1e8471",
    "discovery/independent-commit.txt": "5a06392a3f58e99ebaf4cb895dec746b3eccd5dc94ad8abfc2d1f73526c60c9c",
    "discovery/independent-pin/agentic_portfolio-f6d056f.tar.gz": "3ec98a054d0cd8ece3ef25c5f0130d529ce61f665cf9f9d65b7f3c97766d632b",
    "discovery/independent-pytest-isolated.log": "d23e186237171c67fd50d405fe0ced7425c9a805796dca6e5073c6356fa90af7",
    "discovery/lewisbakkero_sparsis-repo.json": "8a56c660eccb33ebb92ed5f922085e8adffe29466e3ad30b1076814302bd5e32",
    "discovery/lewisbakkero_sparsis-commits.json": "b9cdc50bfc2dd36615be8c177e6ff7c54e23d3e61397257c070a48f7720a4251",
}

V2_PINS = {
    "primary_v2/2603.23300v2.pdf": "cb708a65339640c7958bf602f67e3f0d6547071974074770e4b529553c6ab00f",
    "primary_v2/arxiv-abs.html": "b9bcae330519a1d937962f097ba8f5aab7ae7f6b672d7c875b83d952b6bdbee3",
    "primary_v2/arxiv-api.xml": "4109d56fa5d8cab159a14265e6a85c3553e425ae8b3028833c9724ab5adf498e",
    "primary_v2/openai-gpt35-model.html": "9081d659b916a76d6ead8893f810d9910357da1b9fd9449042573e41333859c1",
    "primary_v2/openai-gpt4o-system-card.pdf": "e2579ecb185cbc13bac39f9dbf25e1917f78e1ea5a3a5023165c6614fb5db724",
    "primary_v2/openai-gpt4o-system-card.txt": "a1f08a288a1cbbadec9c369f10e4d6d09d33aded6875885d19d1dd1930ddf14f",
    "source_v2/2603.23300v2.tar": "11b2d0ccee0a607546cfd0a10c385ce2e4d217caec07ba175e123d5bc92de889",
    "build_v2/00README.json": "66c9abaff5a94fa23abc26fa6e719859780a0c6aaadd9daec72fb19e64372170",
    "build_v2/agentic.bib": "9393405d7a1d8a9aa02da841a596e4f732f4a42f92eead1f533d7fd85ce1a81d",
    "build_v2/Figure_workflow_1.0.png": "74467cd1f6a4d4cee7f5dc2d4b2f96d4ad28fd864ae6c0859c6e01a374f98a9a",
    "build_v2/main.bbl": "d355aed89ccf5d4da8f1b6d36a5cb57260e9f2452cf5f4b69104f621c0ad2de0",
    "build_v2/main.tex": "003d001f0d2e72331e93bb68e437eea79edf28917411b3d21e8a777e0cdfbe33",
    "build_v2/main.pdf": "fb79fa20638c51b1da778eb5dfeb997aa801eab3c898d37309bfade809ca4c95",
    "build_v2/pass3.log": "84fa5021426082c294c1bc0e62cbe89016ed0905072ed6f54c1469d2f98ff9cc",
    "render_v2/pixel_comparison.csv": "5e5c3ab3c28e45209bbe2b985cfeb9b1c72cd974db96e149accb29e15189009d",
    "discovery_v2/github-repos-arxiv-id.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "discovery_v2/github-repos-title.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
}

SOURCE_MEMBERS = {
    "00README.json": 374,
    "agentic.bib": 37077,
    "Figure_workflow_1.0.png": 133920,
    "main.bbl": 13113,
    "main.tex": 210461,
}
V2_SOURCE_MEMBERS = {
    "00README.json": 295,
    "Figure_workflow_1.0.png": 133920,
    "agentic.bib": 38683,
    "main.tex": 283353,
}
METHODS = ("NW", "Residual NW", "Deep learning", "POET", "NLS")
V2_METHODS = METHODS + ("Sample Cov",)
OBJECTIVES = ("GMV", "MV", "MSR")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_tar(path: Path) -> dict[str, int]:
    members: dict[str, int] = {}
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe archive member: {member.name}")
            if member.isfile():
                members[member.name] = member.size
    return members


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty ledger: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_inputs(scratch: Path) -> dict[str, Any]:
    for relative, expected in PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pin mismatch for {relative}: {actual} != {expected}")
    for relative, expected in V2_PINS.items():
        path = scratch / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"v2 pin mismatch for {relative}: {actual} != {expected}")
    if safe_tar(scratch / "source/2603.23300v1.tar") != SOURCE_MEMBERS:
        raise ValueError("official source archive member inventory changed")
    if safe_tar(scratch / "source_v2/2603.23300v2.tar") != V2_SOURCE_MEMBERS:
        raise ValueError("official v2 source archive member inventory changed")
    independent = safe_tar(scratch / "discovery/independent-pin/agentic_portfolio-f6d056f.tar.gz")
    if not any(name.endswith("/README.md") for name in independent):
        raise ValueError("independent archive no longer contains README.md")
    html = (scratch / "primary/arxiv-abs.html").read_text(errors="replace")
    for marker in ("Submitted on 24 Mar 2026", "2603.23300v1", "Mehmet Caner"):
        if marker not in html:
            raise ValueError(f"arXiv marker changed: {marker}")
    log = (scratch / "build/pass2.log").read_text(errors="replace")
    if "Output written on main.pdf (67 pages" not in log:
        raise ValueError("official source rebuild did not finish at 67 pages")
    release = (scratch / "primary/gemini-2-flash-release.html").read_text(errors="replace")
    if 'article:published_time" content="2024-12-11"' not in release:
        raise ValueError("Gemini 2.0 Flash release date marker changed")
    model = (scratch / "primary/gemini-2-flash-model.html").read_text(errors="replace")
    for marker in ("Knowledge cutoff</td>", "August 2024", "shut down June 1, 2026"):
        if marker not in model:
            raise ValueError(f"Gemini model marker changed: {marker}")
    pytest_log = (scratch / "discovery/independent-pytest-isolated.log").read_text()
    if "114 passed" not in pytest_log:
        raise ValueError("pinned independent test suite no longer records 114 passed")
    repo = json.loads((scratch / "discovery/alanhsieh2000_agentic_portfolio-repo.json").read_text())
    if repo["full_name"] != "alanhsieh2000/agentic_portfolio" or repo["created_at"] != "2026-08-05T10:10:23Z":
        raise ValueError("independent repository identity changed")
    if INDEPENDENT_COMMIT not in (scratch / "discovery/independent-commit.txt").read_text():
        raise ValueError("independent implementation commit marker changed")
    v2_html = (scratch / "primary_v2/arxiv-abs.html").read_text(errors="replace")
    for marker in (
        "Submitted on 24 Mar 2026",
        "last revised 11 Aug 2026",
        "2603.23300v2",
        "Mehmet Caner",
    ):
        if marker not in v2_html:
            raise ValueError(f"arXiv v2 marker changed: {marker}")
    v2_api = (scratch / "primary_v2/arxiv-api.xml").read_text(errors="replace")
    for marker in ("2603.23300v2", "2026-08-11T18:39:26Z"):
        if marker not in v2_api:
            raise ValueError(f"arXiv v2 API marker changed: {marker}")
    v2_log = (scratch / "build_v2/pass3.log").read_text(errors="replace")
    if "Output written on main.pdf (82 pages" not in v2_log:
        raise ValueError("official v2 source rebuild did not finish at 82 pages")
    gpt35 = (scratch / "primary_v2/openai-gpt35-model.html").read_text(errors="replace")
    if "Sep 01, 2021 knowledge cutoff" not in gpt35:
        raise ValueError("OpenAI GPT-3.5 cutoff marker changed")
    gpt4o = (scratch / "primary_v2/openai-gpt4o-system-card.txt").read_text(errors="replace")
    if "pre-trained using data up to October 2023" not in " ".join(gpt4o.split()):
        raise ValueError("OpenAI GPT-4o cutoff marker changed")
    with (scratch / "render_v2/pixel_comparison.csv").open(newline="", encoding="utf-8") as stream:
        pixel_rows = list(csv.DictReader(stream))
    if len(pixel_rows) != 82:
        raise ValueError("v2 visual comparison page count changed")
    maximum_difference = max(float(row["different_pixel_fraction"]) for row in pixel_rows)
    if maximum_difference > 0.006:
        raise ValueError("v2 official/rebuilt page difference exceeds audit bound")
    for kind in ("official", "rebuilt"):
        rendered = list((scratch / f"render_v2/{kind}").glob("page-*.png"))
        if len(rendered) != 82:
            raise ValueError(f"v2 {kind} render page count changed")
    for name in ("github-repos-arxiv-id.json", "github-repos-title.json"):
        if json.loads((scratch / f"discovery_v2/{name}").read_text()) != []:
            raise ValueError(f"v2 bounded repository search changed: {name}")
    return {
        "v1_official_source_files": len(SOURCE_MEMBERS),
        "v2_official_source_files": len(V2_SOURCE_MEMBERS),
        "v2_maximum_render_pixel_difference_fraction": maximum_difference,
    }


def latex_number(cell: str) -> tuple[str, float]:
    rendered = re.sub(r"\\(?:textbf|bf)\s*\{([^{}]+)\}", r"\1", cell)
    rendered = rendered.replace("{", "").replace("}", "")
    rendered = rendered.split(r"\\", 1)[0].strip()
    match = re.search(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", rendered)
    if not match:
        raise ValueError(f"numeric value missing: {cell!r}")
    return match.group(), float(match.group())


def period_for(label: str) -> str:
    if label == "tab:long short":
        return "mixed_2020-01_to_2024-04_and_2015-01_to_2024-04"
    if label.endswith(" 10"):
        return "2015-01_to_2024-04"
    return "2020-01_to_2024-04"


def table_screen(label: str) -> str:
    return label.removeprefix("tab:").rsplit(" ", 1)[0] if label.endswith((" 5", " 10")) else label.removeprefix("tab:")


def version_rows(rows: Iterable[Mapping[str, Any]], version: str) -> list[dict[str, Any]]:
    return [{"paper_version": version, **row} for row in rows]


def strip_latex_comments(text: str) -> str:
    active_lines = []
    for original in text.splitlines():
        line = original
        for index, character in enumerate(original):
            if character != "%":
                continue
            slashes = 0
            cursor = index - 1
            while cursor >= 0 and original[cursor] == "\\":
                slashes += 1
                cursor -= 1
            if slashes % 2 == 0:
                line = original[:index]
                break
        active_lines.append(line)
    return "\n".join(active_lines)


def remove_iffalse_blocks(tex: str) -> str:
    pattern = re.compile(r"\\iffalse\b.*?\\fi\b", re.S)
    blocks = pattern.findall(tex)
    if len(blocks) != 1 or blocks[0].count(r"\begin{table}") != 8:
        raise ValueError("v2 inactive conditional-table inventory changed")
    return pattern.sub("", tex)


def command_argument(text: str, command: str) -> str | None:
    match = re.search(rf"\\{re.escape(command)}\s*\{{", text)
    if not match:
        return None
    start = match.end()
    depth = 1
    for index in range(start, len(text)):
        escaped = index > 0 and text[index - 1] == "\\"
        if text[index] == "{" and not escaped:
            depth += 1
        elif text[index] == "}" and not escaped:
            depth -= 1
            if depth == 0:
                return text[start:index]
    raise ValueError(f"unterminated {command} argument")


V2_SCREEN_NAMES = {
    "tab35-1": "baseline",
    "tab35-2": "llm_s",
    "tab35-3": "logistic",
    "tab35-4": "human_analysts",
    "tab35-5": "finbert",
    "tab35-6": "llm_s_plus_human_analysts",
    "tab35-7": "finbert_plus_human_analysts",
    "tab35-8": "llm_s_plus_finbert_agentic_ai",
    "tab35-9": "llm_s_plus_finbert_plus_human_analysts",
    "tab1": "baseline",
    "tab2": "llm_s",
    "tab3": "logistic",
    "tab4": "human_analysts",
    "tab5": "finbert",
    "tab6": "llm_s_plus_human_analysts",
    "tab7": "finbert_plus_human_analysts",
    "tab8": "llm_s_plus_finbert_agentic_ai",
    "tab9": "llm_s_plus_finbert_plus_human_analysts",
    "tab:default finbert 4o": "agentic_ai_default_to_finbert",
    "tab:default finbert 3.5": "agentic_ai_default_to_finbert",
    "tab:small cap finbert 4o": "agentic_ai_small_cap",
    "tab:small cap finbert 3.5": "agentic_ai_small_cap",
    "tab:novy marx + finbert 4o": "novy_marx_plus_finbert",
    "tab:novy marx + finbert 3.5": "novy_marx_plus_finbert",
}


def v2_period(label: str) -> str:
    if label.startswith("tab35-") or label.endswith("3.5"):
        return "2021-10_to_2024-04"
    if label.startswith("tab") and label[3:].isdigit() or label.endswith("4o"):
        return "2023-11_to_2024-04"
    if "additional metrics" in label:
        return "2021-10_to_2024-04"
    raise ValueError(f"unmapped v2 table period: {label}")


def parse_v2_tables(
    tex: str,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, list[float]]],
]:
    if len(list(re.finditer(r"\\begin\{table\}(.*?)\\end\{table\}", tex, re.S))) != 37:
        raise ValueError("expected 37 raw v2 table environments")
    active_tex = remove_iffalse_blocks(tex)
    blocks = list(re.finditer(r"\\begin\{table\}(.*?)\\end\{table\}", active_tex, re.S))
    if len(blocks) != 29:
        raise ValueError(f"expected 29 conditionally active v2 table environments, found {len(blocks)}")
    results: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    sharpe_tables: dict[str, dict[str, list[float]]] = {}
    method_counts: Counter[int] = Counter()
    auxiliary_cells = 0
    for match in blocks:
        block = strip_latex_comments(match.group(1))
        label = command_argument(block, "label")
        caption = command_argument(block, "caption")
        standard_rows: dict[str, list[tuple[str, float]]] = {}
        for line in block.splitlines():
            cells = line.split("&")
            method = cells[0].strip()
            if method not in V2_METHODS:
                continue
            values = [latex_number(cell) for cell in cells[1:]]
            if len(values) == 9:
                standard_rows[method] = values
        if standard_rows:
            if not label or not caption:
                raise ValueError("active v2 result table is missing label or caption")
            table_number = len(inventory) + 1
            period = v2_period(label)
            screen = V2_SCREEN_NAMES[label]
            fields = tuple(
                (group, objective) for group in ("Sharpe Ratio", "Returns", "Variance") for objective in OBJECTIVES
            )
            for method, values in standard_rows.items():
                for (rendered, numeric), (group, objective) in zip(values, fields):
                    row = result_cell(
                        table_number,
                        label,
                        method,
                        group,
                        objective,
                        period,
                        rendered,
                        numeric,
                    )
                    row["screen_or_comparison"] = screen
                    results.append(row)
            sharpe_tables[label] = {
                method: [numeric for _, numeric in values] for method, values in standard_rows.items()
            }
            method_counts[len(standard_rows)] += 1
            inventory.append(
                {
                    "table_number": table_number,
                    "label": label,
                    "screen_or_comparison": screen,
                    "period": period,
                    "printed_numeric_cells": len(standard_rows) * 9,
                    "native_cells_regenerated": 0,
                    "caption": " ".join(caption.split()),
                }
            )
            continue

        panel = ""
        auxiliary_rows: list[tuple[str, str, list[tuple[str, float]]]] = []
        for line in block.splitlines():
            if "Panel A:" in line:
                panel = "GMV"
            elif "Panel B:" in line:
                panel = "MV"
            elif "Panel C:" in line:
                panel = "MSR"
            cells = line.split("&")
            method = cells[0].strip()
            if method in METHODS and panel:
                values = [latex_number(cell) for cell in cells[1:]]
                if len(values) == 4:
                    auxiliary_rows.append((panel, method, values))
        if not auxiliary_rows:
            continue
        if not caption:
            raise ValueError("v2 additional-metric table is missing caption")
        if "BASELINE QUANTITATIVE" in block:
            label = "tab:medium additional metrics baseline"
            screen = "baseline"
        elif "LLM-S + FINBERT WITH QUANTITATIVE" in block:
            label = "tab:medium additional metrics agentic_ai"
            screen = "llm_s_plus_finbert_agentic_ai"
        else:
            raise ValueError("v2 additional-metric table title changed")
        table_number = len(inventory) + 1
        metrics = ("Turnover", "Leverage", "Concentration", "Drawdown")
        for panel, method, values in auxiliary_rows:
            for (rendered, numeric), metric in zip(values, metrics):
                row = result_cell(
                    table_number,
                    label,
                    method,
                    metric,
                    panel,
                    "2021-10_to_2024-04",
                    rendered,
                    numeric,
                )
                row["screen_or_comparison"] = screen
                results.append(row)
                auxiliary_cells += 1
        inventory.append(
            {
                "table_number": table_number,
                "label": label,
                "screen_or_comparison": screen,
                "period": "2021-10_to_2024-04",
                "printed_numeric_cells": len(auxiliary_rows) * 4,
                "native_cells_regenerated": 0,
                "caption": " ".join(caption.split()),
            }
        )
    if (
        len(inventory) != 26
        or len(results) != 1344
        or len(sharpe_tables) != 24
        or auxiliary_cells != 120
        or method_counts != Counter({6: 16, 5: 8})
    ):
        raise ValueError(
            "v2 visible table denominator changed: "
            f"tables={len(inventory)}, cells={len(results)}, "
            f"Sharpe tables={len(sharpe_tables)}, auxiliary={auxiliary_cells}, "
            f"method counts={method_counts}"
        )
    return results, inventory, sharpe_tables


def figure_rows_v1() -> list[dict[str, Any]]:
    return [
        {
            "figure_number": 1,
            "label": "fig:algorithm",
            "source_kind": "released_png",
            "source_asset": "Figure_workflow_1.0.png",
            "empirical_result_figure": False,
            "official_and_rebuilt_visually_checked": True,
            "caption": "An illustration of the algorithm.",
        }
    ]


def figure_rows_v2(tex: str) -> list[dict[str, Any]]:
    active_tex = remove_iffalse_blocks(tex)
    blocks = list(re.finditer(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", active_tex, re.S))
    rows = []
    for number, match in enumerate(blocks, 1):
        block = strip_latex_comments(match.group(1))
        label = command_argument(block, "label") or f"unlabeled_figure_{number}"
        caption = command_argument(block, "caption")
        if label == "fig:agentic-pic" and not caption:
            caption = "Human and Agentic AI information-capacity optima (manual source caption)."
        if not caption:
            raise ValueError(f"v2 figure caption changed: {label}")
        image_match = re.search(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", block)
        rows.append(
            {
                "figure_number": number,
                "label": label,
                "source_kind": "released_png" if image_match else "embedded_tikz",
                "source_asset": image_match.group(1) if image_match else "main.tex",
                "empirical_result_figure": False,
                "official_and_rebuilt_visually_checked": True,
                "caption": " ".join(caption.split()),
            }
        )
    if len(rows) != 6:
        raise ValueError(f"expected six active v2 figures, found {len(rows)}")
    return rows


def prompt_listing_hashes(tex: str) -> list[str]:
    section = re.search(
        r"\\subsection\{LLM-S Prompts and Outputs\}(.*?)"
        r"(?=\\subsection\{|\\section\{|\\end\{document\})",
        tex,
        re.S,
    )
    if not section:
        raise ValueError("LLM-S prompt appendix changed")
    bodies = re.findall(
        r"\\begin\{lstlisting\}(?:\[[^]]*\])?\s*(.*?)\\end\{lstlisting\}",
        section.group(1),
        re.S,
    )
    hashes = []
    for body in bodies:
        normalized = "\n".join(line.rstrip() for line in body.strip().splitlines()) + "\n"
        hashes.append(hashlib.sha256(normalized.encode()).hexdigest())
    if len(hashes) != 3:
        raise ValueError(f"expected three prompt listings, found {len(hashes)}")
    return hashes


def parse_tables(tex: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, list[float]]]]:
    blocks = list(re.finditer(r"\\begin\{table\}(.*?)\\end\{table\}", tex, re.S))
    if len(blocks) != 22:
        raise ValueError(f"expected 22 tables, found {len(blocks)}")
    results: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    sharpe_tables: dict[str, dict[str, list[float]]] = {}
    for table_number, match in enumerate(blocks, 1):
        block = match.group(1)
        label_match = re.search(r"\\label\{([^}]+)\}", block)
        caption_match = re.search(r"\\caption\{([^}]+)\}", block)
        if not label_match or not caption_match:
            raise ValueError(f"table {table_number} is missing label or caption")
        label = label_match.group(1)
        table_rows: dict[str, list[float]] = {}
        before = len(results)
        accepted = set(METHODS) | {"LLM-S", "Best 2 stage model"}
        for line in block.splitlines():
            cells = line.split("&")
            method = cells[0].strip()
            if method not in accepted:
                continue
            values = [latex_number(cell) for cell in cells[1:]]
            if label == "tab:long short":
                if len(values) != 4:
                    raise ValueError("long-short table width changed")
                fields = (
                    ("5_year", "Equal-Weighted"),
                    ("5_year", "Value-Weighted"),
                    ("10_year", "Equal-Weighted"),
                    ("10_year", "Value-Weighted"),
                )
                for (rendered, numeric), (horizon, weighting) in zip(values, fields):
                    results.append(
                        result_cell(table_number, label, method, "Sharpe Ratio", weighting, horizon, rendered, numeric)
                    )
            else:
                if method not in METHODS or len(values) != 9:
                    raise ValueError(f"standard result table width changed: {label}/{method}")
                table_rows[method] = [numeric for _, numeric in values]
                fields = tuple(
                    (group, objective) for group in ("Sharpe Ratio", "Returns", "Variance") for objective in OBJECTIVES
                )
                for (rendered, numeric), (group, objective) in zip(values, fields):
                    results.append(
                        result_cell(table_number, label, method, group, objective, period_for(label), rendered, numeric)
                    )
        count = len(results) - before
        expected = 8 if label == "tab:long short" else 45
        if count != expected:
            raise ValueError(f"expected {expected} cells in {label}, found {count}")
        if table_rows:
            sharpe_tables[label] = table_rows
        inventory.append(
            {
                "table_number": table_number,
                "label": label,
                "screen_or_comparison": table_screen(label),
                "period": period_for(label),
                "printed_numeric_cells": count,
                "native_cells_regenerated": 0,
                "caption": " ".join(caption_match.group(1).split()),
            }
        )
    if len(results) != 953 or len(sharpe_tables) != 21:
        raise ValueError(
            f"expected 953 result cells and 21 standard tables; found {len(results)}, {len(sharpe_tables)}"
        )
    return results, inventory, sharpe_tables


def result_cell(
    table_number: int,
    label: str,
    method: str,
    metric_group: str,
    objective: str,
    period: str,
    rendered: str,
    numeric: float,
) -> dict[str, Any]:
    return {
        "table_number": table_number,
        "table_label": label,
        "screen_or_comparison": table_screen(label),
        "period_or_horizon": period,
        "method_or_model": method,
        "metric_group": metric_group,
        "objective_or_weighting": objective,
        "rendered_value": rendered,
        "numeric_value": numeric,
        "author_native_pipeline_executed": False,
        "native_result_regenerated": False,
        "paper_result_credit": False,
    }


def arithmetic_rows(
    tables: Mapping[str, Mapping[str, list[float]]],
    expected_count: int = 315,
    expected_failures: set[tuple[str, str, str]] | None = None,
) -> list[dict[str, Any]]:
    if expected_failures is None:
        expected_failures = {
            ("tab:llm 10", "NLS", "MSR"),
            ("tab:finbert+llm 10", "POET", "MV"),
        }
    rows = []
    for label, methods in tables.items():
        for method, values in methods.items():
            for index, objective in enumerate(OBJECTIVES):
                reported = values[index]
                annual_return = values[3 + index]
                variance = values[6 + index]
                implied = annual_return / math.sqrt(variance)
                difference = abs(reported - implied)
                half_unit = 0.00005
                interval_values = (
                    (annual_return - half_unit) / math.sqrt(variance - half_unit),
                    (annual_return - half_unit) / math.sqrt(variance + half_unit),
                    (annual_return + half_unit) / math.sqrt(variance - half_unit),
                    (annual_return + half_unit) / math.sqrt(variance + half_unit),
                )
                implied_low = min(interval_values)
                implied_high = max(interval_values)
                consistent = not (reported + half_unit < implied_low or reported - half_unit > implied_high)
                rows.append(
                    {
                        "table_label": label,
                        "method": method,
                        "objective": objective,
                        "reported_sharpe": reported,
                        "reported_annual_return": annual_return,
                        "reported_variance": variance,
                        "implied_return_over_sqrt_variance": implied,
                        "absolute_difference": difference,
                        "within_0_002_tolerance": difference <= 0.002,
                        "implied_interval_from_four_decimal_rounding_low": implied_low,
                        "implied_interval_from_four_decimal_rounding_high": implied_high,
                        "rounding_interval_consistent": consistent,
                    }
                )
    if len(rows) != expected_count:
        raise ValueError(f"expected {expected_count} Sharpe arithmetic checks, found {len(rows)}")
    failures = [row for row in rows if not row["rounding_interval_consistent"]]
    keys = {(row["table_label"], row["method"], row["objective"]) for row in failures}
    if keys != expected_failures:
        raise ValueError(f"printed arithmetic mismatch set changed: {keys}")
    return rows


def sharpe(tables: Mapping[str, Mapping[str, list[float]]], label: str) -> list[float]:
    return [value for method in METHODS for value in tables[label][method][:3]]


def wins(tables: Mapping[str, Mapping[str, list[float]]], left: str, right: str) -> int:
    return sum(a > b for a, b in zip(sharpe(tables, left), sharpe(tables, right)))


def consistency_rows(tables: Mapping[str, Mapping[str, list[float]]]) -> list[dict[str, str]]:
    comparisons = {
        "llm_vs_baseline_5y": wins(tables, "tab:llm 5", "tab:baseline 5"),
        "logistic_vs_baseline_5y": wins(tables, "tab:logistic 5", "tab:baseline 5"),
        "llm_vs_analyst_5y": wins(tables, "tab:llm 5", "tab:analyst 5"),
        "llm_vs_novy_marx_5y": wins(tables, "tab:llm 5", "tab:novy marx 5"),
        "finbert_vs_baseline_5y": wins(tables, "tab:finbert 5", "tab:baseline 5"),
        "finbert_vs_logistic_5y": wins(tables, "tab:finbert 5", "tab:logistic 5"),
        "finbert_vs_analyst_5y": wins(tables, "tab:finbert 5", "tab:analyst 5"),
        "agentic_vs_baseline_5y": wins(tables, "tab:finbert+llm 5", "tab:baseline 5"),
        "agentic_vs_finbert_5y": wins(tables, "tab:finbert+llm 5", "tab:finbert 5"),
        "agentic_vs_llm_5y": wins(tables, "tab:finbert+llm 5", "tab:llm 5"),
        "finbert_vs_logistic_10y": wins(tables, "tab:finbert 10", "tab:logistic 10"),
        "finbert_vs_baseline_10y": wins(tables, "tab:finbert 10", "tab:baseline 10"),
    }
    expected = {
        "llm_vs_baseline_5y": 13,
        "logistic_vs_baseline_5y": 13,
        "llm_vs_analyst_5y": 15,
        "llm_vs_novy_marx_5y": 15,
        "finbert_vs_baseline_5y": 14,
        "finbert_vs_logistic_5y": 14,
        "finbert_vs_analyst_5y": 15,
        "agentic_vs_baseline_5y": 14,
        "agentic_vs_finbert_5y": 14,
        "agentic_vs_llm_5y": 15,
        "finbert_vs_logistic_10y": 15,
        "finbert_vs_baseline_10y": 15,
    }
    if comparisons != expected:
        raise ValueError(f"printed cross-table comparisons changed: {comparisons}")
    finbert_market = sum(value > 0.6324 for value in sharpe(tables, "tab:finbert 5"))
    agentic_market = sum(value > 0.6324 for value in sharpe(tables, "tab:finbert+llm 5"))
    triple_market = sum(value > 0.6324 for value in sharpe(tables, "tab:llm+finbert+analyst 5"))
    values = (
        (
            "printed_sharpe_identity",
            "two_mismatches",
            "313/315 printed triples satisfy Sharpe = annual return / sqrt(annual variance) within 0.002; LLM-S 10y NLS/MSR differs by 0.0084 and Agentic 10y POET/MV contains malformed return 01092",
        ),
        (
            "agentic_10y_poet_mv_return",
            "missing_decimal_typographical_error",
            "source prints 01092; 0.1092 would imply Sharpe 0.2357 and reconcile with printed 0.2358 at displayed precision",
        ),
        ("llm_10y_nls_msr", "printed_triple_conflict", "0.0740 / sqrt(0.0258) = 0.4607, not the printed Sharpe 0.4691"),
        (
            "llm_vs_baseline_5y",
            "claim_matches_printed_tables",
            f"LLM-S is higher in {comparisons['llm_vs_baseline_5y']}/15 cells; exceptions are POET/MSR and NLS/MSR",
        ),
        (
            "logistic_vs_baseline_5y",
            "claim_matches_printed_tables",
            f"logistic is higher in {comparisons['logistic_vs_baseline_5y']}/15 cells",
        ),
        (
            "llm_vs_analyst_and_novy_marx_5y",
            "claim_matches_printed_tables",
            "LLM-S is higher in all 15/15 cells against each comparator",
        ),
        (
            "finbert_5y_comparisons",
            "claim_matches_printed_tables",
            "FinBERT is higher in 14/15 cells versus baseline and logistic, 15/15 versus analysts, and 11/15 exceed market Sharpe 0.6324",
        ),
        (
            "agentic_5y_comparisons",
            "claim_matches_printed_tables",
            f"Agentic is higher in 14/15 versus baseline, 14/15 versus FinBERT, 15/15 versus LLM-S, and {agentic_market}/15 exceed market Sharpe 0.6324",
        ),
        (
            "three_agent_5y",
            "claim_matches_printed_tables",
            f"all 15 three-agent Sharpe ratios are lower than two-agent Agentic and {triple_market}/15 exceed market",
        ),
        (
            "finbert_10y_comparisons",
            "claim_matches_printed_tables",
            "FinBERT is higher in all 15/15 cells versus logistic and baseline",
        ),
        (
            "subsequent_return_leakage_check",
            "asserted_without_released_statistic",
            "paper says signals do not systematically align with subsequent returns but releases no test statistic, sample, code, or signal ledger",
        ),
        (
            "intersection_attribution",
            "asserted_without_released_lineage",
            "claims 1.037 of 1.187 Sharpe is attributable to intersection and union fallback has 0.545, but releases no dated decomposition or output arrays",
        ),
        (
            "selected_stock_count",
            "asserted_without_released_lineage",
            "average 22 selected stocks and 50% trivial-intersection dates cannot be checked without annual rules and monthly signal sets",
        ),
        (
            "screen_label_direction",
            "methodological_interpretation_boundary",
            "Stage 2 pools all non-hold buy and sell names and explicitly may assign either weight sign, so Stage-1 buy/sell labels do not constrain final position direction",
        ),
        (
            "causal_masking",
            "prompt_instruction_not_model_control",
            "the released text asks Gemini to use causal masking; it is not evidence of an enforced attention mask, timestamped request, or training-data cutoff",
        ),
        (
            "theory_to_empirics",
            "conditional_not_empirically_verified",
            "the sensible-screening theory assumes an oracle-like subset relation; public artifacts do not establish that LLM-S or FinBERT satisfies it",
        ),
    )
    if finbert_market != 11 or agentic_market != 14 or triple_market != 0:
        raise ValueError("market comparison counts changed")
    return [{"check": a, "status": b, "detail": c} for a, b, c in values]


def metric_map(
    tables: Mapping[str, Mapping[str, list[float]]], label: str, offset: int = 0
) -> dict[tuple[str, str], float]:
    return {
        (method, objective): values[offset + index]
        for method, values in tables[label].items()
        for index, objective in enumerate(OBJECTIVES)
    }


def common_wins(
    tables: Mapping[str, Mapping[str, list[float]]],
    left: str,
    right: str,
    offset: int = 0,
) -> tuple[int, int]:
    left_values = metric_map(tables, left, offset)
    right_values = metric_map(tables, right, offset)
    keys = left_values.keys() & right_values.keys()
    return sum(left_values[key] > right_values[key] for key in keys), len(keys)


def maximum_sharpe(tables: Mapping[str, Mapping[str, list[float]]], label: str) -> tuple[float, str, str]:
    return max((value, method, objective) for (method, objective), value in metric_map(tables, label).items())


def v2_consistency_rows(
    tables: Mapping[str, Mapping[str, list[float]]],
) -> list[dict[str, str]]:
    comparisons = {
        "medium_llm_vs_baseline": common_wins(tables, "tab35-2", "tab35-1"),
        "medium_logistic_vs_baseline": common_wins(tables, "tab35-3", "tab35-1"),
        "medium_llm_vs_humans": common_wins(tables, "tab35-2", "tab35-4"),
        "medium_finbert_vs_baseline": common_wins(tables, "tab35-5", "tab35-1"),
        "medium_finbert_vs_llm": common_wins(tables, "tab35-5", "tab35-2"),
        "medium_finbert_vs_logistic": common_wins(tables, "tab35-5", "tab35-3"),
        "medium_finbert_vs_humans": common_wins(tables, "tab35-5", "tab35-4"),
        "medium_hybrid_vs_llm": common_wins(tables, "tab35-6", "tab35-2"),
        "medium_agentic_vs_baseline": common_wins(tables, "tab35-8", "tab35-1"),
        "medium_agentic_vs_finbert": common_wins(tables, "tab35-8", "tab35-5"),
        "medium_agentic_vs_llm": common_wins(tables, "tab35-8", "tab35-2"),
        "medium_agentic_vs_humans_added": common_wins(tables, "tab35-8", "tab35-9"),
        "short_llm_vs_baseline": common_wins(tables, "tab2", "tab1"),
        "short_logistic_vs_llm": common_wins(tables, "tab3", "tab2"),
        "short_humans_vs_llm": common_wins(tables, "tab4", "tab2"),
        "short_logistic_vs_baseline": common_wins(tables, "tab3", "tab1"),
        "short_humans_vs_baseline": common_wins(tables, "tab4", "tab1"),
        "short_finbert_vs_baseline": common_wins(tables, "tab5", "tab1"),
        "short_finbert_vs_llm": common_wins(tables, "tab5", "tab2"),
        "short_finbert_vs_logistic": common_wins(tables, "tab5", "tab3"),
        "short_finbert_vs_humans": common_wins(tables, "tab5", "tab4"),
        "short_hybrid_vs_llm": common_wins(tables, "tab6", "tab2"),
        "short_hybrid_vs_humans": common_wins(tables, "tab6", "tab4"),
        "short_agentic_vs_baseline": common_wins(tables, "tab8", "tab1"),
        "short_agentic_vs_finbert": common_wins(tables, "tab8", "tab5"),
        "short_agentic_vs_llm": common_wins(tables, "tab8", "tab2"),
        "short_agentic_vs_humans_added": common_wins(tables, "tab8", "tab9"),
        "short_default_finbert_vs_main": common_wins(tables, "tab:default finbert 4o", "tab8"),
        "medium_main_vs_default_finbert": common_wins(tables, "tab35-8", "tab:default finbert 3.5"),
        "short_agentic_vs_novy_finbert": common_wins(tables, "tab8", "tab:novy marx + finbert 4o"),
        "medium_agentic_vs_novy_finbert": common_wins(tables, "tab35-8", "tab:novy marx + finbert 3.5"),
    }
    expected = {
        "medium_llm_vs_baseline": (11, 15),
        "medium_logistic_vs_baseline": (10, 15),
        "medium_llm_vs_humans": (17, 18),
        "medium_finbert_vs_baseline": (12, 15),
        "medium_finbert_vs_llm": (14, 18),
        "medium_finbert_vs_logistic": (10, 18),
        "medium_finbert_vs_humans": (18, 18),
        "medium_hybrid_vs_llm": (6, 18),
        "medium_agentic_vs_baseline": (9, 15),
        "medium_agentic_vs_finbert": (10, 18),
        "medium_agentic_vs_llm": (11, 18),
        "medium_agentic_vs_humans_added": (17, 18),
        "short_llm_vs_baseline": (3, 15),
        "short_logistic_vs_llm": (18, 18),
        "short_humans_vs_llm": (18, 18),
        "short_logistic_vs_baseline": (7, 15),
        "short_humans_vs_baseline": (11, 15),
        "short_finbert_vs_baseline": (10, 15),
        "short_finbert_vs_llm": (18, 18),
        "short_finbert_vs_logistic": (15, 18),
        "short_finbert_vs_humans": (10, 18),
        "short_hybrid_vs_llm": (12, 18),
        "short_hybrid_vs_humans": (1, 18),
        "short_agentic_vs_baseline": (11, 15),
        "short_agentic_vs_finbert": (15, 18),
        "short_agentic_vs_llm": (18, 18),
        "short_agentic_vs_humans_added": (18, 18),
        "short_default_finbert_vs_main": (13, 15),
        "medium_main_vs_default_finbert": (14, 15),
        "short_agentic_vs_novy_finbert": (15, 15),
        "medium_agentic_vs_novy_finbert": (10, 15),
    }
    if comparisons != expected:
        raise ValueError(f"v2 printed comparison counts changed: {comparisons}")

    market_counts = {
        label: sum(value > market for value in metric_map(tables, label).values())
        for label, market in (
            ("tab35-1", 0.2685),
            ("tab35-2", 0.2685),
            ("tab35-4", 0.2685),
            ("tab35-5", 0.2685),
            ("tab35-8", 0.2685),
            ("tab35-9", 0.2685),
            ("tab1", 2.0857),
            ("tab2", 2.0857),
            ("tab3", 2.0857),
            ("tab4", 2.0857),
            ("tab9", 2.0857),
        )
    }
    if market_counts != {
        "tab35-1": 3,
        "tab35-2": 12,
        "tab35-4": 0,
        "tab35-5": 18,
        "tab35-8": 12,
        "tab35-9": 0,
        "tab1": 2,
        "tab2": 0,
        "tab3": 6,
        "tab4": 10,
        "tab9": 0,
    }:
        raise ValueError(f"v2 market comparison counts changed: {market_counts}")
    short_return_wins = common_wins(tables, "tab8", "tab1", 3)
    if short_return_wins != (15, 15):
        raise ValueError(f"v2 short return comparison changed: {short_return_wins}")
    short_equal_weight = sum(
        value > 1.5147 for (method, _), value in metric_map(tables, "tab8").items() if method != "Sample Cov"
    )
    medium_equal_weight = sum(
        value > 0.1633 for (method, _), value in metric_map(tables, "tab35-8").items() if method != "Sample Cov"
    )
    if (short_equal_weight, medium_equal_weight) != (11, 10):
        raise ValueError("v2 equal-weight comparison counts changed")
    finbert_gain = (7.2046 / 3.3540 - 1.0) * 100.0
    values = (
        (
            "visible_table_denominator",
            "inactive_source_tables_excluded",
            "26 rendered tables and 1,344 numeric cells; eight legacy tables inside \\iffalse and three fully commented table shells receive no published denominator credit",
        ),
        (
            "printed_sharpe_identity",
            "two_rounding_interval_conflicts",
            "406/408 rendered Sharpe/return/variance triples reconcile after propagating four-decimal rounding intervals",
        ),
        (
            "short_llm_nw_mv",
            "printed_triple_conflict",
            "Table tab2 prints Sharpe 0.5941, but 0.1240/sqrt(0.0546) is about 0.5307 and cannot reconcile by four-decimal rounding",
        ),
        (
            "short_llm_nw_msr",
            "printed_triple_conflict",
            "Table tab2 prints Sharpe 0.5708, but 0.1388/sqrt(0.0472) is about 0.6389 and cannot reconcile by four-decimal rounding",
        ),
        (
            "medium_baseline_and_market",
            "claim_matches_printed_tables",
            "baseline maximum is 1.0088 and 3/15 configurations exceed market 0.2685",
        ),
        (
            "medium_llm_table_maximum",
            "claim_conflicts_with_printed_table",
            "prose names Deep learning/MSR 0.6108 as best, while the rendered Sample Cov/GMV cell is 0.6194",
        ),
        (
            "medium_llm_vs_baseline",
            "claim_count_conflict",
            "prose says 12/15 improve; the printed common cells show 11/15",
        ),
        (
            "medium_logistic_market",
            "claim_matches_printed_tables",
            "10 cells exceed and one equals 0.2685, matching the stated 11 beat-or-match count",
        ),
        (
            "medium_llm_vs_humans",
            "claim_matches_printed_tables",
            "LLM-S exceeds human screening in 17/18 cells; NW/MV is the sole exception",
        ),
        (
            "medium_logistic_vs_baseline",
            "claim_denominator_and_count_conflict",
            "prose says 14/18 although baseline has no Sample Cov; among 15 common cells logistic wins 10",
        ),
        (
            "medium_finbert_comparisons",
            "claims_match_printed_tables",
            "FinBERT wins 12/15 versus baseline, 14/18 versus LLM-S, 10/18 versus logistic, and 18/18 versus humans",
        ),
        (
            "medium_hybrid_mv",
            "claim_matches_printed_tables",
            "LLM-S plus humans beats LLM-S in all six MV cells and only those 6/18 cells",
        ),
        (
            "medium_agentic_comparisons",
            "claims_match_printed_tables",
            "Agentic wins 9/15 versus baseline, 10/18 versus FinBERT, and 11/18 versus LLM-S; its 1.0946 maximum is the largest medium main-table value",
        ),
        (
            "medium_humans_added",
            "claim_matches_printed_tables_with_one_cell_exception",
            "adding humans lowers 17/18 Agentic cells; NW/MV is slightly less negative with humans, while all three-agent cells remain below market",
        ),
        (
            "short_baseline_llm_logistic_humans",
            "claims_match_printed_tables",
            "baseline has 2 market-beating cells; LLM-S has zero and wins 3/15 versus baseline; logistic wins 18/18 and humans 18/18 versus LLM-S",
        ),
        (
            "short_logistic_table_reference",
            "claim_value_misattributed",
            "prose calls 3.5374 the best value in Table tab3; tab3 peaks at 3.3540 and 3.5374 belongs to human-screening Table tab4",
        ),
        (
            "short_finbert_comparisons",
            "counts_match_printed_tables",
            "FinBERT wins 10/15 versus baseline, 18/18 versus LLM-S, 15/18 versus logistic, and 10/18 versus humans",
        ),
        (
            "short_finbert_percentage",
            "printed_percentage_conflict",
            f"the increase from 3.3540 to 7.2046 is {finbert_gain:.1f}%, not the stated 99%",
        ),
        (
            "short_hybrid_vs_humans",
            "claim_count_conflict",
            "prose says two hybrid cells beat humans; the printed tables show 1/18",
        ),
        (
            "short_agentic_comparisons",
            "claims_match_printed_tables",
            "Agentic wins 11/15 versus baseline, 15/18 versus FinBERT, 18/18 versus LLM-S, and 18/18 versus the three-agent human ensemble",
        ),
        (
            "short_agentic_returns",
            "claim_matches_printed_tables",
            "all 15 common Agentic annual-return cells exceed baseline counterparts",
        ),
        (
            "short_baseline_minimum_variance_label",
            "prose_label_conflict",
            "the printed 0.0025 minimum is Residual NW/MV, not Residual NW/GMV as one later paragraph states",
        ),
        (
            "consensus_robustness",
            "claims_match_printed_tables",
            "short default-to-FinBERT wins 13/15 versus union and has the larger maximum; medium union wins 14/15 versus default-to-FinBERT",
        ),
        (
            "small_cap_robustness",
            "claims_match_printed_tables",
            "printed maxima fall from 8.1612 to 2.1316 short-term and from 1.0946 to 0.4722 medium-term",
        ),
        (
            "novy_marx_robustness",
            "topline_matches_not_uniform_medium_dominance",
            "Agentic maxima exceed Novy-Marx+FinBERT in both windows; it wins 15/15 common short cells but only 10/15 medium cells",
        ),
        (
            "equal_weight_counts",
            "claim_matches_printed_tables_given_unreleased_benchmark",
            "using the prose-only 1/N values, 11/15 short and 10/15 medium Agentic cells exceed them; underlying benchmark returns are absent",
        ),
        (
            "equal_weight_significance",
            "asserted_without_released_lineage",
            "p-values 0.067 and 0.062 cannot be recomputed without paired return series and test implementation",
        ),
        (
            "two_rerun_robustness",
            "asserted_without_released_outputs",
            "v2 says the Agentic screen was rerun twice with similar medium results but releases neither runs nor a similarity statistic",
        ),
        (
            "selected_stock_count",
            "asserted_without_released_lineage",
            "the average of 20 selected stocks cannot be checked without dated signals and ensemble sets",
        ),
        (
            "model_cutoff_boundary",
            "family_cutoffs_corroborated_execution_unverified",
            "OpenAI sources support September 2021 for GPT-3.5 Turbo and pretraining through October 2023 for GPT-4o, but no exact author model IDs, snapshots, request dates, responses, or tool payloads are released",
        ),
        (
            "additional_portfolio_metrics",
            "printed_only",
            "120 turnover/leverage/concentration/drawdown cells are rendered, but no weights, returns, liquidation events, or calculation outputs are released",
        ),
        (
            "theory_to_empirics",
            "conditional_not_empirically_verified",
            "the new screening and information-acquisition results depend on assumptions; public artifacts do not establish that the empirical agents satisfy them",
        ),
    )
    return [{"check": check, "status": status, "detail": detail} for check, status, detail in values]


def news_audit(scratch: Path) -> dict[str, Any]:
    records = [
        json.loads(line) for line in (scratch / "discovery/hf-news.jsonl").read_text().splitlines() if line.strip()
    ]
    schema = {"id_", "links", "symbol", "company", "Title", "Text", "Publishdate"}
    if len(records) != 4589 or any(set(record) != schema for record in records):
        raise ValueError("linked Hugging Face JSONL row count or schema changed")
    ids = [record["id_"] for record in records]
    dates = [date.fromisoformat(record["Publishdate"]) for record in records]
    years = Counter(item.year for item in dates)
    expected_years = {
        2006: 3,
        2007: 55,
        2008: 73,
        2009: 66,
        2010: 131,
        2011: 98,
        2012: 208,
        2013: 90,
        2014: 97,
        2015: 116,
        2016: 145,
        2017: 248,
        2018: 284,
        2019: 354,
        2020: 278,
        2021: 348,
        2022: 476,
        2023: 918,
        2024: 601,
    }
    if years != Counter(expected_years) or len(set(ids)) != len(ids):
        raise ValueError("linked news distribution or identifier uniqueness changed")
    api = json.loads((scratch / "discovery/hf-dataset-api.json").read_text())
    if api["sha"] != "d3e37035640bc90830ee8741dfa52815b719a26a" or api["lastModified"] != "2024-11-14T15:16:41.000Z":
        raise ValueError("Hugging Face dataset revision marker changed")
    return {
        "repository": "KrossKinetic/SP500-Financial-News-Articles-Time-Series",
        "revision": api["sha"],
        "last_modified": api["lastModified"],
        "license": "MIT",
        "rows": len(records),
        "unique_ids": len(set(ids)),
        "unique_symbols": len({record["symbol"] for record in records}),
        "minimum_publish_date": min(dates).isoformat(),
        "maximum_publish_date": max(dates).isoformat(),
        "rows_2015_through_2024_04": sum(item >= date(2015, 1, 1) for item in dates),
        "rows_2020_through_2024_04": sum(item >= date(2020, 1, 1) for item in dates),
        "rows_by_year": {str(year): count for year, count in sorted(years.items())},
        "schema": sorted(schema),
        "exact_linked_input_recovered": True,
        "finbert_model_identifier_recovered": False,
        "paper_sentiment_scores_or_signals_recovered": False,
        "paper_result_credit": False,
    }


def method_rows() -> list[dict[str, str]]:
    values = (
        (
            "official_document_source",
            "complete_document_only",
            "v1 TeX, bibliography, workflow PNG, and generated bibliography are released; no experiment source is present",
        ),
        (
            "author_native_runtime",
            "missing",
            "no attributable data, LLM, FinBERT, estimator, optimizer, or backtest runtime was recovered",
        ),
        (
            "equity_universe",
            "partial",
            "full S&P 500 including delisted firms is stated, but point-in-time memberships, identifiers, eligibility rules, and vintages are absent",
        ),
        (
            "crsp_compustat_data",
            "missing_proprietary",
            "monthly January 2005--April 2024 CRSP/Compustat panel is not released",
        ),
        (
            "characteristics",
            "mostly_specified",
            "log market equity, book-to-market, and 12-month momentum; 1/99 winsorization, cross-sectional z-scores, and missing-to-zero are stated",
        ),
        (
            "accounting_lag",
            "specified",
            "annual accounting data are assumed available six months after fiscal-year end",
        ),
        (
            "linked_news_dataset",
            "exact_link_recovered",
            "pinned Hugging Face revision has 4,589 rows, 469 symbols, and dates 2006-12-04 through 2024-04-20",
        ),
        (
            "ibes_recommendations",
            "missing_proprietary",
            "IBES/WRDS recommendation snapshot, analyst mappings, and derived monthly signals are absent",
        ),
        (
            "fama_french_factors",
            "missing_snapshot",
            "three-factor model is named for residual nodewise estimation but exact factor file and vintage are absent",
        ),
        (
            "llm_s_prompt",
            "partial_one_date",
            "agent/task prompt is printed only for December 2023; earlier annual prompts, injected data, tool traces, and outputs are absent",
        ),
        (
            "llm_s_model",
            "family_only_retired",
            "Gemini 2.0 Flash is named without immutable model ID/revision; service shut down 2026-06-01",
        ),
        (
            "llm_s_generation_parameters",
            "missing",
            "temperature, top-p, token limit, seed, retries, safety settings, and response metadata are absent",
        ),
        (
            "crewai_runtime_and_tools",
            "names_only",
            "four tool names and snippets are printed; implementations, CrewAI version, database schema, and tool-call records are absent",
        ),
        (
            "annual_llm_rules",
            "one_of_required_years",
            "one 2024 rule from December 2023 is printed; the full annual rule ledger for both evaluation windows is absent",
        ),
        (
            "finbert_model",
            "missing_identifier",
            "FinBERT is named generically; checkpoint/revision, tokenizer, batching, truncation, inference code, and probabilities are absent",
        ),
        (
            "finbert_aggregation",
            "partial",
            "positive-minus-negative probability, seven-day exponential weighting, and +/-0.1 thresholds are stated; exact timestamp and aggregation edge cases are absent",
        ),
        (
            "ensemble_rule",
            "specified_prose",
            "two-agent intersection with union fallback at cardinality <=1 and three-agent majority vote are described",
        ),
        (
            "ensemble_signal_ledger",
            "missing",
            "no dated buy/sell/hold sets, intersection/union flags, or selected-stock counts are released",
        ),
        (
            "logistic_benchmark",
            "partial",
            "annual 15-year rolling cross-sectional logistic and top/bottom deciles are stated; target definition, features, solver, regularization, ties, and outputs are absent",
        ),
        (
            "novy_marx_benchmark",
            "partial",
            "top/bottom 150 profitability-plus-value ranks are stated; exact construction, data fields, ties, and outputs are absent",
        ),
        (
            "precision_estimators",
            "partial",
            "nodewise, residual nodewise, POET, deep learning, and NLS are described mathematically but implementation choices and fitted artifacts are absent",
        ),
        (
            "deep_learning_estimator",
            "underspecified",
            "architecture, loss, optimizer, hyperparameters, validation, seeds, checkpoints, and training traces are absent",
        ),
        (
            "portfolio_objectives",
            "mostly_specified",
            "GMV, 1% monthly target MV, and MSR formulas are printed; solver details, constraints, risk-free convention, and edge cases are absent",
        ),
        (
            "formation_and_test_windows",
            "specified_dates_only",
            "180-month rolling formation and 2020-01--2024-04 plus 2015-01--2024-04 tests are stated; exact return matrix is absent",
        ),
        (
            "transaction_cost",
            "formula_specified",
            "10 bp net-return formula is printed; corporate-action/execution conventions and generated turnover are absent",
        ),
        ("random_seeds", "missing", "no seeds for LLM calls, deep learning, baselines, or repeated runs are released"),
        (
            "runtime_environment",
            "missing",
            "no author lockfile, versions, hardware description, or executable configuration is released",
        ),
        (
            "raw_results",
            "missing",
            "no model requests/responses, signals, scores, weights, returns, fitted matrices, tables, or decomposition arrays are released",
        ),
        (
            "published_result_lineage",
            "missing",
            "0/953 printed numeric table cells can be linked to an author-native executable output",
        ),
    )
    return [{"dimension": a, "status": b, "evidence": c} for a, b, c in values]


def v2_method_rows() -> list[dict[str, str]]:
    values = (
        (
            "official_document_source",
            "complete_document_only",
            "v2 releases TeX, bibliography, and one workflow PNG; the generated bibliography is no longer in the source archive and no experiment source is present",
        ),
        (
            "author_native_runtime",
            "missing",
            "no attributable data, LLM, FinBERT, estimator, optimizer, or backtest runtime was recovered",
        ),
        (
            "equity_universe",
            "partial",
            "full S&P 500 including delisted firms is stated, but point-in-time memberships, identifiers, eligibility rules, and vintages are absent",
        ),
        (
            "crsp_compustat_data",
            "missing_proprietary",
            "monthly January 2005--April 2024 CRSP/Compustat panel is not released",
        ),
        (
            "characteristics",
            "mostly_specified",
            "log market equity, book-to-market, and 12-month momentum; 1/99 winsorization, cross-sectional z-scores, and missing-to-zero are stated",
        ),
        (
            "accounting_lag",
            "specified",
            "annual accounting data are assumed available six months after fiscal-year end",
        ),
        (
            "linked_news_dataset",
            "exact_link_recovered",
            "the same pinned Hugging Face revision has 4,589 rows, 469 symbols, and dates 2006-12-04 through 2024-04-20",
        ),
        (
            "ibes_recommendations",
            "missing_proprietary",
            "IBES/WRDS recommendation snapshot, analyst mappings, and derived monthly signals are absent",
        ),
        (
            "fama_french_factors",
            "missing_snapshot",
            "the three-factor model is named for residual nodewise estimation but exact factor file and vintage are absent",
        ),
        (
            "llm_s_prompt",
            "partial_one_date",
            "the same three December-2023 prompt/output listings survive verbatim; medium-horizon prompts and all other annual executions are absent",
        ),
        (
            "llm_s_models",
            "family_cutoffs_only",
            "GPT-3.5 Turbo September-2021 and GPT-4o October-2023 family cutoff claims are corroborated by OpenAI sources, but author model IDs, snapshots, request dates, and responses are absent",
        ),
        (
            "llm_s_generation_parameters",
            "missing",
            "temperature, top-p, token limit, seed, retries, safety settings, and response metadata are absent",
        ),
        (
            "crewai_runtime_and_tools",
            "names_only",
            "tool names and prompt snippets are printed; implementations, CrewAI version, database schema, payloads, and tool-call records are absent",
        ),
        (
            "annual_llm_rules",
            "one_date_only",
            "one 2024 rule from December 2023 is printed; the medium- and short-window annual rule ledgers are absent",
        ),
        (
            "finbert_model",
            "missing_identifier",
            "FinBERT is named generically; checkpoint/revision, tokenizer, batching, truncation, inference code, and probabilities are absent",
        ),
        (
            "finbert_cutoff_claim",
            "fine_tuning_date_not_full_lineage",
            "a pre-2020 fine-tuning dataset claim does not identify the checkpoint or establish all underlying pretraining and inference inputs",
        ),
        (
            "finbert_aggregation",
            "partial",
            "positive-minus-negative probability, seven-day exponential weighting, and +/-0.1 thresholds are stated; exact timestamp and aggregation edge cases are absent",
        ),
        (
            "ensemble_rule",
            "specified_prose",
            "intersection with a union fallback and a default-to-FinBERT robustness rule are described",
        ),
        (
            "ensemble_signal_ledger",
            "missing",
            "no dated buy/sell/hold sets, intersection/union flags, fallback events, or selected-stock counts are released",
        ),
        (
            "logistic_benchmark",
            "partial",
            "rolling cross-sectional logistic and top/bottom deciles are stated; target definition, features, solver, regularization, ties, and outputs are absent",
        ),
        (
            "novy_marx_benchmark",
            "partial",
            "top/bottom 150 profitability-plus-value ranks are stated; exact construction, data fields, ties, and outputs are absent",
        ),
        (
            "precision_estimators",
            "partial",
            "nodewise, residual nodewise, POET, deep learning, NLS, and screened-sample covariance are described but implementations and fitted artifacts are absent",
        ),
        (
            "sample_covariance",
            "conditional_method_only",
            "Sample Cov appears only after screening when dimension permits inversion; exact matrices and selection-dependent dimensions are absent",
        ),
        (
            "deep_learning_estimator",
            "underspecified",
            "architecture, loss, optimizer, hyperparameters, validation, seeds, checkpoints, and training traces are absent",
        ),
        (
            "portfolio_objectives",
            "mostly_specified",
            "GMV, 1% monthly target MV, and MSR formulas are printed; solver details, constraints, risk-free convention, and edge cases are absent",
        ),
        (
            "formation_and_test_windows",
            "specified_dates_only",
            "180-month formation with October 2021--April 2024 medium and November 2023--April 2024 short tests is stated; exact return matrices are absent",
        ),
        (
            "transaction_cost",
            "formula_specified",
            "10 bp net-return treatment is stated; corporate-action/execution conventions and generated turnover are absent",
        ),
        (
            "additional_portfolio_metrics",
            "definitions_only",
            "turnover, leverage, HHI concentration, drawdown, and empty-portfolio liquidation behavior are described, but weights and calculation arrays are absent",
        ),
        (
            "equal_weight_benchmarks",
            "printed_values_only",
            "1/N Sharpe values and comparison counts are printed without benchmark return series",
        ),
        (
            "paired_sharpe_tests",
            "printed_p_values_only",
            "0.067 and 0.062 are printed without paired samples, implementation, or resampling details sufficient for replay",
        ),
        (
            "llm_reruns",
            "asserted_only",
            "two medium-horizon reruns are described as similar without prompts, outputs, seeds, tables, or a similarity statistic",
        ),
        ("random_seeds", "missing", "no seeds for LLM calls, deep learning, baselines, or repeated runs are released"),
        (
            "runtime_environment",
            "missing",
            "no author lockfile, versions, hardware description, or executable configuration is released",
        ),
        (
            "raw_results",
            "missing",
            "no model requests/responses, signals, scores, weights, returns, fitted matrices, tables, or decomposition arrays are released",
        ),
        (
            "published_result_lineage",
            "missing",
            "0/1,344 rendered v2 numeric table cells can be linked to an author-native executable output",
        ),
    )
    return [{"dimension": a, "status": b, "evidence": c} for a, b, c in values]


def prompt_rows() -> list[dict[str, Any]]:
    return [
        {
            "component": "LLM-S agent backstory/system-like prompt",
            "date_scope": "December 2023 for 2024 rules",
            "exact_text_printed": True,
            "all_evaluation_dates_recovered": False,
            "input_cross_section_recovered": False,
            "tool_implementations_recovered": False,
            "author_model_request_replayable": False,
            "paper_result_credit": False,
        },
        {
            "component": "LLM-S CrewAI task prompt",
            "date_scope": "December 2023 for 2024 rules",
            "exact_text_printed": True,
            "all_evaluation_dates_recovered": False,
            "input_cross_section_recovered": False,
            "tool_implementations_recovered": False,
            "author_model_request_replayable": False,
            "paper_result_credit": False,
        },
        {
            "component": "LLM-S example model output/rule",
            "date_scope": "December 2023 for 2024 rules",
            "exact_text_printed": True,
            "all_evaluation_dates_recovered": False,
            "input_cross_section_recovered": False,
            "tool_implementations_recovered": False,
            "author_model_request_replayable": False,
            "paper_result_credit": False,
        },
    ]


def discovery_rows(scratch: Path) -> list[dict[str, Any]]:
    arxiv = json.loads((scratch / "discovery/github-arxiv-id.json").read_text())
    authors = json.loads((scratch / "discovery/github-authors.json").read_text())
    title = json.loads((scratch / "discovery/github-exact-title.json").read_text())
    if (arxiv["total_count"], authors["total_count"], title["total_count"]) != (30, 0, 4):
        raise ValueError("bounded GitHub search counts changed")
    return [
        {
            "route": "arxiv_v1_source",
            "result_count": 5,
            "finding": "manuscript TeX, bibliography, workflow image, and generated bibliography only; no experiment runtime/data/results",
            "attributable_native_implementation_recovered": False,
            "negative_search_limit": "describes pinned v1 archive only",
        },
        {
            "route": "arxiv_v2_source",
            "result_count": 4,
            "finding": "expanded manuscript TeX, bibliography, and unchanged workflow image only; no experiment runtime/data/results",
            "attributable_native_implementation_recovered": False,
            "negative_search_limit": "describes pinned v2 archive only",
        },
        {
            "route": "github_repository_arxiv_id_2026-08-14",
            "result_count": 0,
            "finding": "no repository-level match for 2603.23300",
            "attributable_native_implementation_recovered": False,
            "negative_search_limit": "bounded current public repository search; not proof about code search, private, deleted, moved, or unindexed material",
        },
        {
            "route": "github_repository_exact_title_2026-08-14",
            "result_count": 0,
            "finding": "no repository-level exact-title match",
            "attributable_native_implementation_recovered": False,
            "negative_search_limit": "bounded current public repository search; not proof about code search, private, deleted, moved, or unindexed material",
        },
        {
            "route": "github_code_arxiv_id",
            "result_count": arxiv["total_count"],
            "finding": "visible matches are citations, indexes, review material, or later interpretations",
            "attributable_native_implementation_recovered": False,
            "negative_search_limit": "bounded current indexed search; not proof about private, deleted, moved, or unindexed material",
        },
        {
            "route": "github_code_exact_title",
            "result_count": title["total_count"],
            "finding": "no affirmative author-attributable runtime recovered",
            "attributable_native_implementation_recovered": False,
            "negative_search_limit": "bounded current indexed search only",
        },
        {
            "route": "github_author_names",
            "result_count": authors["total_count"],
            "finding": "no matching author-attributable code result",
            "attributable_native_implementation_recovered": False,
            "negative_search_limit": "name search cannot rule out aliases, organizations, private repositories, or different accounts",
        },
        {
            "route": "alanhsieh2000_agentic_portfolio",
            "result_count": 1,
            "finding": "created 2026-08-05, uses Claude Sonnet 4.5, custom LLM-F, PyPortfolioOpt, 60/24-month returns, and current SEC/Yahoo data; materially divergent unaffiliated implementation",
            "attributable_native_implementation_recovered": False,
            "negative_search_limit": "no affirmative author relationship was recovered; absence of a link is not proof of identity",
        },
        {
            "route": "lewisbakkero_sparsis",
            "result_count": 1,
            "finding": "academic-review repository containing paper material, not an implementation of the experiment",
            "attributable_native_implementation_recovered": False,
            "negative_search_limit": "classification is limited to the pinned public repository snapshot",
        },
    ]


def build(scratch: Path, output: Path) -> dict[str, Any]:
    validated = validate_inputs(scratch)
    output.mkdir(parents=True, exist_ok=True)
    v1_tex = (scratch / "build/main.tex").read_text(encoding="utf-8")
    v2_tex = (scratch / "build_v2/main.tex").read_text(encoding="utf-8")
    v1_results, v1_tables, v1_sharpe_tables = parse_tables(v1_tex)
    v2_results, v2_tables, v2_sharpe_tables = parse_v2_tables(v2_tex)
    v1_arithmetic = arithmetic_rows(v1_sharpe_tables)
    v2_arithmetic = arithmetic_rows(
        v2_sharpe_tables,
        expected_count=408,
        expected_failures={
            ("tab2", "NW", "MV"),
            ("tab2", "NW", "MSR"),
        },
    )
    v1_consistency = consistency_rows(v1_sharpe_tables)
    v2_consistency = v2_consistency_rows(v2_sharpe_tables)
    news = news_audit(scratch)
    v1_methods = method_rows()
    v2_methods = v2_method_rows()
    v1_prompts = prompt_rows()
    v2_prompts = prompt_rows()
    v1_figures = figure_rows_v1()
    v2_figures = figure_rows_v2(v2_tex)
    discovery = discovery_rows(scratch)

    results = version_rows(v1_results, "v1") + version_rows(v2_results, "v2")
    tables = version_rows(v1_tables, "v1") + version_rows(v2_tables, "v2")
    arithmetic = version_rows(v1_arithmetic, "v1") + version_rows(v2_arithmetic, "v2")
    consistency = version_rows(v1_consistency, "v1") + version_rows(v2_consistency, "v2")
    methods = version_rows(v1_methods, "v1") + version_rows(v2_methods, "v2")
    prompts = version_rows(v1_prompts, "v1") + version_rows(v2_prompts, "v2")
    figures = version_rows(v1_figures, "v1") + version_rows(v2_figures, "v2")

    write_csv(output / "published_result_ledger.csv", results)
    write_csv(output / "table_inventory.csv", tables)
    write_csv(output / "sharpe_arithmetic_audit.csv", arithmetic)
    write_csv(output / "internal_consistency_audit.csv", consistency)
    write_csv(output / "method_specification_audit.csv", methods)
    write_csv(output / "prompt_component_inventory.csv", prompts)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "discovery_evidence.csv", discovery)
    write_json(output / "linked_news_dataset_audit.json", news)

    revision_rows = [
        {"dimension": "submission_date", "v1": "2026-03-24", "v2": "2026-08-11", "assessment": "new official revision"},
        {"dimension": "official_pages", "v1": 67, "v2": 82, "assessment": "15-page expansion"},
        {
            "dimension": "source_archive_files",
            "v1": 5,
            "v2": 4,
            "assessment": "v2 omits generated main.bbl; both remain document-only",
        },
        {"dimension": "main_tex_bytes", "v1": 210461, "v2": 283353, "assessment": "substantial manuscript rewrite"},
        {
            "dimension": "rendered_result_tables",
            "v1": 22,
            "v2": 26,
            "assessment": "v2 excludes eight iffalse tables and three commented shells",
        },
        {
            "dimension": "rendered_numeric_cells",
            "v1": 953,
            "v2": 1344,
            "assessment": "separate version denominators; no cross-version credit",
        },
        {
            "dimension": "sharpe_return_variance_triples",
            "v1": 315,
            "v2": 408,
            "assessment": "two non-rounding conflicts in each version",
        },
        {
            "dimension": "active_figures",
            "v1": 1,
            "v2": 6,
            "assessment": "v2 adds five theory/concept figures; no empirical result plot",
        },
        {
            "dimension": "main_test_windows",
            "v1": "2020-01_to_2024-04 and 2015-01_to_2024-04",
            "v2": "2021-10_to_2024-04 and 2023-11_to_2024-04",
            "assessment": "main empirical windows replaced",
        },
        {
            "dimension": "llm_s_family",
            "v1": "Gemini 2.0 Flash",
            "v2": "GPT-3.5 Turbo medium; GPT-4o short",
            "assessment": "model family and chronology argument replaced",
        },
        {
            "dimension": "screened_sample_covariance",
            "v1": "not in main result rows",
            "v2": "added to 16 screened tables",
            "assessment": "new method cells change several prose maxima and denominators",
        },
        {
            "dimension": "additional_portfolio_metrics",
            "v1": 0,
            "v2": 120,
            "assessment": "turnover/leverage/concentration/drawdown printed without raw lineage",
        },
        {
            "dimension": "prompt_listing_bodies",
            "v1": 3,
            "v2": 3,
            "assessment": "all three normalized listing bodies are byte-for-byte unchanged",
        },
        {
            "dimension": "workflow_png",
            "v1": PINS["build/Figure_workflow_1.0.png"],
            "v2": V2_PINS["build_v2/Figure_workflow_1.0.png"],
            "assessment": "byte-identical",
        },
        {
            "dimension": "linked_news_revision",
            "v1": news["revision"],
            "v2": news["revision"],
            "assessment": "same exact linked input component",
        },
        {
            "dimension": "author_native_experiment_release",
            "v1": "not recovered",
            "v2": "not recovered",
            "assessment": "no empirical lineage improvement",
        },
    ]
    write_csv(output / "version_revision_audit.csv", revision_rows)

    v1_prompt_hashes = prompt_listing_hashes(v1_tex)
    v2_prompt_hashes = prompt_listing_hashes(v2_tex)
    expected_prompt_hashes = [
        "6e330990c2c98c551231b68c6662e64557673c3cc93332e76953e6d40536ca65",
        "d3e52e4217f9464cc8cb98a63df59f4354577b3dc30b874a8f748f08ca7410a2",
        "133cc3a8a8801e00baad0ac1921e4594ed2f967b27f2e9ad28582f715878c32b",
    ]
    if v1_prompt_hashes != expected_prompt_hashes or v2_prompt_hashes != expected_prompt_hashes:
        raise ValueError("versioned prompt listing bodies changed")
    write_json(
        output / "prompt_version_comparison.json",
        {
            "components": [
                "LLM-S agent backstory/system-like prompt",
                "LLM-S CrewAI task prompt",
                "LLM-S example model output/rule",
            ],
            "v1_normalized_sha256": v1_prompt_hashes,
            "v2_normalized_sha256": v2_prompt_hashes,
            "all_three_bodies_verbatim_equal_across_versions": True,
            "formatting_options_changed": True,
            "paper_result_credit": False,
        },
    )

    chronology = {
        "v1": {
            "paper_test_windows_end": "2024-04-30",
            "model_family": "Gemini 2.0 Flash",
            "first_public_date": "2024-12-11",
            "months_after_test_window_end_at_first_public_release": 7,
            "documented_knowledge_cutoff": "2024-08",
            "knowledge_cutoff_after_test_window_end": True,
            "service_shutdown_date": "2026-06-01",
            "literal_model_available_during_test_windows": False,
            "retrospective_data_layer_holdout_possible": True,
            "retrospective_model_knowledge_holdout_established": False,
        },
        "v2": {
            "medium": {
                "paper_model_family": "ChatGPT-3.5",
                "paper_test_window": "2021-10_to_2024-04",
                "official_family_cutoff": "2021-09-01",
                "official_source": "https://developers.openai.com/api/docs/models/gpt-3.5-turbo",
                "family_cutoff_claim_corroborated": True,
            },
            "short": {
                "paper_model_family": "ChatGPT-4o",
                "paper_test_window": "2023-11_to_2024-04",
                "official_family_pretraining_data_through": "2023-10",
                "official_source": "https://cdn.openai.com/gpt-4o-system-card.pdf",
                "family_cutoff_claim_corroborated": True,
            },
            "exact_author_model_ids_or_snapshots_recovered": False,
            "timestamped_author_requests_recovered": False,
            "author_responses_recovered": False,
            "tool_payload_history_recovered": False,
            "retrospective_model_knowledge_holdout_established": False,
        },
        "assessment": "The v2 family-level cutoff statements are corroborated by OpenAI primary sources, but family cutoffs do not identify the model snapshots or establish the missing author requests, responses, tool inputs, and execution lineage.",
    }
    write_json(output / "model_release_chronology.json", chronology)

    independent = {
        "repository": "alanhsieh2000/agentic_portfolio",
        "pinned_commit": INDEPENDENT_COMMIT,
        "repository_created": "2026-08-05",
        "paper_submitted": "2026-03-24",
        "author_attribution_evidence_recovered": False,
        "classification": "unaffiliated_post_paper_interpretation",
        "isolated_test_suite": "114 passed",
        "internal_component_execution_credit": True,
        "author_native_execution_credit": False,
        "paper_result_credit": False,
        "published_result_cells_regenerated": 0,
        "material_divergences": [
            "Claude Sonnet 4.5 replaces Gemini 2.0 Flash",
            "custom LLM-F replaces FinBERT",
            "PyPortfolioOpt replaces the five paper precision estimators",
            "60-month history with 24-month fallback replaces the paper's 180-month window",
            "12% annual MV target is not the literal 1% monthly target",
            "a configurable 2% risk-free default is added without paper lineage",
            "current SEC EDGAR and Yahoo reconstruction replaces exact CRSP/Compustat/IBES/WRDS snapshots",
        ],
    }
    write_json(output / "independent_implementation_audit.json", independent)

    provenance = {
        "arxiv_id": ARXIV_ID,
        "current_version": "v2",
        "versions": [
            {
                "version": "v1",
                "submitted": "2026-03-24",
                "pages": 67,
                "source_files": validated["v1_official_source_files"],
                "source_archive_sha256": PINS["source/2603.23300v1.tar"],
                "official_pdf_sha256": PINS["primary/2603.23300v1.pdf"],
                "rebuilt_pdf_sha256": PINS["build/main.pdf"],
                "rebuild_extracted_token_multiset_jaccard": 0.9936239193083574,
                "visual_qa": {
                    "official_pages_inspected": 67,
                    "rebuilt_pages_inspected": 67,
                    "unreadable_clipped_or_overlapping_pages": 0,
                },
            },
            {
                "version": "v2",
                "submitted": "2026-08-11",
                "pages": 82,
                "source_files": validated["v2_official_source_files"],
                "source_archive_sha256": V2_PINS["source_v2/2603.23300v2.tar"],
                "official_pdf_sha256": V2_PINS["primary_v2/2603.23300v2.pdf"],
                "rebuilt_pdf_sha256": V2_PINS["build_v2/main.pdf"],
                "rebuild_extracted_token_multiset_jaccard": 0.9947977554360533,
                "visual_qa": {
                    "official_pages_inspected": 82,
                    "rebuilt_pages_inspected": 82,
                    "unreadable_clipped_or_overlapping_pages": 0,
                    "maximum_different_pixel_fraction_at_72_dpi": validated[
                        "v2_maximum_render_pixel_difference_fraction"
                    ],
                },
            },
        ],
        "linked_news_dataset": {
            "repository": news["repository"],
            "revision": news["revision"],
            "jsonl_sha256": PINS["discovery/hf-news.jsonl"],
        },
        "release_boundary": {
            "attributable_native_implementation_recovered": False,
            "complete_author_prompt_history_recovered": False,
            "three_prompt_output_listings_recovered_but_only_one_date": True,
            "prompt_listing_bodies_unchanged_across_versions": True,
            "exact_linked_news_input_recovered": True,
            "complete_paper_data_recovered": False,
            "paper_result_output_recovered": False,
            "bounded_negative_search_is_proof_of_nonexistence": False,
        },
    }
    write_json(output / "source_provenance.json", provenance)

    readme = """# Agentic AI Screening paper/source audit

This audit now covers both official arXiv versions of `2603.23300`.  It rebuilds
and visually checks all 67 v1 and 82 v2 pages.  The ledgers separately count
**953 v1 numeric cells** and **1,344 v2 numeric cells** across 22 and 26 rendered
tables, respectively.  Across both versions, **0/2,297 cells regenerate through
an author-native experiment**.  The expanded v2 archive is still document-only.

## What changed in v2

V2 is a major empirical rewrite, not a cosmetic revision.  It replaces the main
2020--2024/2015--2024 story with an October 2021--April 2024 medium window using
ChatGPT-3.5 and a November 2023--April 2024 short window using GPT-4o.  It adds
sample-covariance rows after screening, 120 turnover/leverage/concentration/
drawdown cells, five theory/concept figures, robustness tables, and new headline
Sharpe ratios of 1.0946 and 8.1612.  Eight legacy tables remain inside an
inactive `\\iffalse ... \\fi` block and three table shells are fully commented;
none are counted as rendered results.

## What is genuinely recoverable

- The linked Hugging Face news revision is pinned and inspected: 4,589 rows,
  469 symbols, and dates from 2006-12-04 through 2024-04-20.
- The three December-2023 LLM-S prompt/output listing bodies are byte-for-byte
  unchanged between v1 and v2.  They cover one date, not either full execution.
- OpenAI primary sources corroborate a September 2021 GPT-3.5 Turbo knowledge
  cutoff and GPT-4o pretraining data through October 2023.  The paper still does
  not identify the exact author snapshots or release requests and responses.
- Both documents and all released figures are reproducible from source.  This
  is document reproducibility, not empirical-result reproduction.

## Printed-record findings

V1 retains two non-rounding arithmetic conflicts, including the literal `01092`
return.  V2 has two new conflicts in the short LLM-S NW row: the MV and MSR
Sharpe values cannot reconcile with their printed returns and variances even
after propagating four-decimal rounding.  V2 prose also overlooks a larger
Sample Cov value when naming the medium LLM-S maximum, says 12/15 LLM-S cells
beat baseline when the tables show 11/15, says logistic wins 14/18 against a
15-cell baseline and actually wins 10/15, attributes 3.5374 to the wrong short
table, calls a 114.8% increase 99%, and says two LLM-plus-human cells beat humans
when the tables show one.  Matching claims are recorded too; internal agreement
never receives replication credit.

## Why this is still not a true replication

The public record omits point-in-time S&P membership and identifiers; exact
CRSP/Compustat, IBES/WRDS, and factor snapshots; the FinBERT checkpoint and
scores; full prompts, tool payloads, model calls, responses, and annual rules;
monthly signals and ensemble sets; all estimator and optimizer code; deep-
learning hyperparameters; seeds and environment; fitted matrices, weights,
returns, costs, paired Sharpe-test samples, rerun outputs, and table-generating
arrays.  Family-level knowledge cutoffs do not establish this missing execution
lineage.  Claims about 20 selected stocks, two similar reruns, 1/N returns, and
p-values 0.067/0.062 cannot be independently replayed.

A pinned later repository passes **114 tests**, useful only for its own
components.  It is unaffiliated and materially changes the model, sentiment
agent, estimators, return window, conventions, and data.  It receives no
author-native or paper-result credit.

The honest assessment is strong two-version document reproducibility, one exact
linked input component, one-date prompt/output specification, and **zero
end-to-end empirical replication**.  Full paper faithfulness remains impossible
without author data/runtime/output lineage; the audit records that boundary
instead of filling it with proxies.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")

    manifest: dict[str, Any] = {
        "work_id": WORK_ID,
        "system_id": SYSTEM_ID,
        "arxiv_id": ARXIV_ID,
        "official_versions_audited": ["v1", "v2"],
        "current_official_version": "v2",
        "official_pdf_and_source_recovered": True,
        "official_document_rebuild_completed": True,
        "official_pages_visually_checked": 149,
        "rebuilt_pages_visually_checked": 149,
        "official_pages_visually_checked_by_version": {"v1": 67, "v2": 82},
        "rebuilt_pages_visually_checked_by_version": {"v1": 67, "v2": 82},
        "published_result_tables": len(tables),
        "published_result_tables_by_version": {"v1": 22, "v2": 26},
        "published_numeric_table_cells": len(results),
        "published_numeric_table_cells_by_version": {"v1": 953, "v2": 1344},
        "native_numeric_table_cells_regenerated": 0,
        "sharpe_arithmetic_checks": len(arithmetic),
        "sharpe_arithmetic_checks_by_version": {"v1": 315, "v2": 408},
        "sharpe_arithmetic_mismatches": sum(not row["rounding_interval_consistent"] for row in arithmetic),
        "sharpe_arithmetic_mismatches_by_version": {"v1": 2, "v2": 2},
        "active_figures_by_version": {"v1": 1, "v2": 6},
        "linked_news_rows_recovered": news["rows"],
        "linked_news_symbols_recovered": news["unique_symbols"],
        "unique_printed_llm_prompt_or_output_components_recovered": 3,
        "complete_annual_prompt_and_output_sets_recovered": 0,
        "independent_component_tests_passed": 114,
        "attributable_native_implementation_recovered": False,
        "full_end_to_end_pipeline_reproduced": False,
        "paper_evidence_route": "paper_only_two_versions_one_linked_input_one_date_prompt_no_native_results",
        "output_sha256": {},
    }
    output_files = sorted(path for path in output.iterdir() if path.is_file() and path.name != "manifest.json")
    manifest["output_sha256"] = {path.name: sha256(path) for path in output_files}
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = build(args.scratch, args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if args.strict and not manifest["full_end_to_end_pipeline_reproduced"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
