#!/usr/bin/env python3
"""Build a fail-closed original-source audit for arXiv:2607.12233v1."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import subprocess
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRATCH = Path("/nfs/roberts/scratch/pi_btk22/zc362/fin_analyst_audit")
DEFAULT_OUTPUT = ROOT / "paper_runs/paper_replication_audits/fin_analyst"
NATIVE_ENV = Path(
    "/nfs/roberts/project/pi_btk22/zc362/environments/venvs/"
    "alpha-fin-analyst-native-py312-20260813"
)
WORK_ID = "CensusArxiv260712233"
SYSTEM_ID = "SYS-FIN-ANALYST"
ARXIV_ID = "2607.12233"
AUTHOR_SPACE = "https://huggingface.co/spaces/Mohotarema/Fin_Analyst"
DATASET_URL = "https://huggingface.co/datasets/TheFinAI/CLEF_Task3_Trading"
ARENA_SPACE = "https://huggingface.co/spaces/TheFinAI/Agent-Market-Arena"
AUTHOR_COMMIT = "85ab4781e74ed3deb9a7ef49bca3fa23b1ed9738"
DATASET_COMMIT = "3ae0b896ed02e882c362f8edc90fd276159f5c5e"
ARENA_COMMIT = "70c388c317b22322145ca8c2a5fe7aa5fe89dba3"

PINS = {
    "primary/arxiv-abs.html": "95bdb9c6838813a55180f04675179f29d988d99555418ffb2767304f57380875",
    "primary/arxiv-api.xml": "a9ae0cdc05b10433dbfda5af323fd7a3bc6a3672f8d59a218e1c5d7243177065",
    "primary/official-v1.pdf": "8b03c2ae99aff919be41757bb465fb958d69a3b0ccc4ceb35aef1706e2e46a79",
    "primary/official-v1.txt": "4d2b454b7cb41ba886668ed1a45ccc6ce152e58a62fe82f18a167bf0910ed9fe",
    "primary/rebuilt-v1.pdf": "3af9106916268664dba4800f52e7c90289d935c97f0dd0397bff5006258443bf",
    "primary/rebuilt-v1.txt": "46db4283ad7a0ab6bfe73af5836ee3fb93a991735b23d92b815a9b7ddf56f37b",
    "primary/source-v1.tar": "6f8d42ec5c5aec1855c5e6db096949e96e40a3b469f68c9a5d25b68bf62470c9",
    "discovery/github-code-arxiv.json": "12d4a95746967e8f197f7552ed15cc3af36c5d3f37ba4f3dc9b3f3dde2b193a5",
    "discovery/github-code-title.json": "b43041bf98ae4e66d68a1211a90bed8005416e36bdc8debe25415ce3558d64dc",
    "discovery/github-repositories-arxiv.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/github-repositories-title.json": "4af480b8ee5b87b369a76c49bd22c9a783908272ebffbe97898f8ab0f0772a5f",
    "discovery/huggingface-spaces-arxiv.json": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "discovery/huggingface-spaces-title.json": "1691349b81cd6b6a73915f117a33029c79f4a2f9774302a5459f6b1ce95af033",
    "discovery/huggingface-space-author-api.json": "6d5bafec6f69da4271f37be84f27c5e7c627d905df5223fec37a0a55e96842f2",
    "discovery/huggingface-dataset-api.json": "a5860736eddc0950658c8d381fb135a5176752da11fd47094906503c13e223de",
    "discovery/arena-fin-analyst-rows.json": "8817fd68587630ab5eff44e93dfa3135399ad135c40e913963bee2c0c81a4a06",
    "dataset-may11/TSLA.parquet": "7f7493e8e94e92ac2ebd4cc0626fa23be8f331ddab1e61e4ff8bc03e8aa5fe98",
    "dataset-may11/BTC.parquet": "718cf95e62d1a035375630387b2b38b044d9bde71aa8b75ba6739ac53dc1aa2f",
    "replay/TSLA.json": "0b4574340b8c987eb3c67732b73f22cf7f080a5483c5bce988dccad400ba4728",
    "replay/BTC.json": "09462f433ecd282abcdd699181ba75f4450a1a45f7068e97fc78716ba14712d8",
    "replay/perf.mjs": "62e6e637900d6e5d84c6671df19ab7d17641d7ebc4dce8127930b7f1d65315b5",
    "native/Fin_Analyst/app.py": "85ca91dd10ae9009093fc7b113d7347f6fd0a6d240281e609a0b9443b366eef1",
    "native/Fin_Analyst/requirements.txt": "96617c24565c1d5528cbca62730ad85e0d3c9c92d1c23a23c4c1daa0e008e88a",
    "native/Fin_Analyst/Dockerfile": "ede3a50786b8b29726bc5f284c4548542633bc63e6192ac32066c03c2a82f3d1",
}

TABLE_SPECS = {
    "tab:results": ({"TSLA", "BTC"}, 10),
    "tab:tsla": ({"Buy & Hold", "Always HOLD", "Random (sigma=42)", "Momentum", "NewsOnly", "Fin-Analyst"}, 42),
    "tab:btc": ({"Buy & Hold", "Always HOLD", "Random", "Momentum", "Fin-Analyst (rule-based)"}, 35),
    "tab:ablation": ({"Event (8-K)", "Quarterly (10-Q)", "News (daily bundle)", "Annual (10-K)", "Fundamentals (Compustat)"}, 20),
    "tab:error_attribution": ({"Final return (net of fees)", "Acted days / exposure", "Hit rate (acted days)", "Long days: hit / total PnL", "Short days: hit / total PnL", "Max equity drawdown"}, 12),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    values = list(rows)
    if not values:
        raise ValueError(f"refusing to write empty ledger: {path}")
    fieldnames = list(values[0])
    fieldnames.extend(
        key for row in values for key in row if key not in fieldnames
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def token_jaccard(left: str, right: str) -> float:
    a = Counter(re.findall(r"\w+", left.lower()))
    b = Counter(re.findall(r"\w+", right.lower()))
    return sum((a & b).values()) / sum((a | b).values())


def verify_pins(scratch: Path) -> None:
    for relative, expected in PINS.items():
        observed = sha256(scratch / relative)
        if observed != expected:
            raise ValueError(f"pin mismatch: {relative}={observed}; expected {expected}")
    repos = {
        "native/Fin_Analyst": AUTHOR_COMMIT,
        "native/CLEF_Task3_Trading": "eae085ce5b82fa3ca852e10372882b5ef2644705",
        "native/Agent-Market-Arena": ARENA_COMMIT,
    }
    for relative, expected in repos.items():
        observed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=scratch / relative, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        if observed != expected:
            raise ValueError(f"repository pin mismatch: {relative}={observed}")
    ancestor = subprocess.run(
        ["git", "cat-file", "-e", f"{DATASET_COMMIT}^{{commit}}"],
        cwd=scratch / "native/CLEF_Task3_Trading", check=False,
    )
    if ancestor.returncode:
        raise ValueError("pinned pre-live dataset revision is absent")


def paper_sources(scratch: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(scratch / "primary/source-v1.tar", "r:*") as archive:
        for member in archive.getmembers():
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
                raise ValueError(f"unsafe source member: {member.name}")
            if member.isfile():
                handle = archive.extractfile(member)
                if handle is None:
                    raise ValueError(f"unreadable source member: {member.name}")
                files[member.name] = handle.read()
    if len(files) != 9:
        raise ValueError(f"paper source file count changed: {len(files)}")
    return files


def strip_comments(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("%"))


def table_environment(source: str, label: str) -> str:
    source = strip_comments(source)
    location = source.index(rf"\label{{{label}}}")
    begin = source.rfind(r"\begin{table", 0, location)
    end = source.find(r"\end{table", location)
    if begin < 0 or end < 0:
        raise ValueError(f"table boundary missing: {label}")
    return source[begin:end]


def clean_tex(value: str) -> str:
    value = value.replace(r"\&", "&").replace(r"\%", "%").replace(r"\,", "")
    value = value.replace(r"\textsc", r"\textbf").replace(r"\sigma", "sigma")
    value = re.sub(r"\\(?:textbf|textit|emph|mathbf|boldsymbol)\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\text\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\(?:alpha|Delta)_\{[^{}]*\}", "", value)
    value = re.sub(r"\\(?:alpha|Delta)", "", value)
    value = re.sub(r"\\(?:toprule|midrule|bottomrule|small)", "", value)
    value = value.replace("~", " ")
    value = re.sub(r"[{}$]", "", value)
    value = value.replace("\\", "")
    return " ".join(value.split()).strip()


def table_rows(environment: str) -> list[list[str]]:
    match = re.search(r"\\begin\{tabular\}\{.*?\}(.*?)\\end\{tabular\}", environment, re.S)
    if match is None:
        raise ValueError("tabular body missing")
    values = []
    for chunk in re.split(r"\\\\", match.group(1)):
        if "&" in chunk:
            values.append([clean_tex(cell) for cell in re.split(r"(?<!\\)&", chunk)])
    return values


def result_rows(source: str) -> list[dict[str, Any]]:
    all_rows: list[dict[str, Any]] = []
    for label, (expected_labels, expected_count) in TABLE_SPECS.items():
        selected: list[dict[str, Any]] = []
        for row_index, cells in enumerate(table_rows(table_environment(source, label)), 1):
            row_label = cells[0]
            match_label = next((name for name in expected_labels if row_label == name), None)
            if match_label is None:
                continue
            value_cells = cells[1:]
            if label == "tab:ablation":
                value_cells = value_cells[:4]
            for column_index, cell in enumerate(value_cells, 1):
                if not re.search(r"\d", cell):
                    continue
                recovered = label == "tab:results" and column_index <= 4
                selected.append({
                    "table_label": label,
                    "row_index": row_index,
                    "row_label": match_label,
                    "quantitative_column_index": column_index,
                    "printed_cell": cell,
                    "unit_definition": "one populated displayed empirical quantitative table cell",
                    "source_document_recovered": True,
                    "official_input_or_result_record_recovered": recovered,
                    "author_native_decision_pipeline_reexecuted": False,
                    "organizer_postprocessor_replayed": recovered,
                    "published_result_regenerated_at_display_precision": False,
                    "paper_result_credit": False,
                    "blocking_reason": (
                        "live: official actions and current organizer scorer disagree with the printed cell"
                        if recovered else
                        "offline: no author actions, model calls, seed, raw path, or result generator was released"
                    ),
                })
        if len(selected) != expected_count:
            raise ValueError(f"denominator changed for {label}: {len(selected)} != {expected_count}")
        all_rows.extend(selected)
    if len(all_rows) != 119:
        raise ValueError(f"published table denominator changed: {len(all_rows)}")
    return all_rows


def parse_prompt_constants(app_source: str) -> dict[str, str]:
    tree = ast.parse(app_source)
    result: dict[str, str] = {}
    names = {
        "NEWS_PROMPT": "News", "EVENT_PROMPT": "Event", "EARNINGS_PROMPT": "Earnings",
        "STRATEGY_PROMPT": "Strategy", "FUNDAMENTALS_PROMPT": "Fundamentals",
        "ANALYST_PROMPT": "Analyst", "TECHNICAL_PROMPT": "Technical",
        "SOCIAL_PROMPT": "Social", "META_PROMPT": "Meta agent",
    }
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            key = node.targets[0].id
            if key in names and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                result[names[key]] = node.value.value
    if set(result) != set(names.values()):
        raise ValueError("native prompt constant inventory changed")
    return result


def prompt_rows(source: str, app_source: str) -> list[dict[str, Any]]:
    native = parse_prompt_constants(app_source)
    prompt_table = source[source.index(r"\label{tab:prompts}"):source.index(r"\end{longtable}")]
    rows = []
    for name, text in native.items():
        printed_marker = rf"\textbf{{{name.replace('Meta agent', 'Meta agent')}}}"
        if printed_marker not in prompt_table:
            raise ValueError(f"paper prompt row missing: {name}")
        rows.append({
            "agent": name,
            "native_system_prompt_sha256": sha256_bytes(text.encode()),
            "native_system_prompt_characters": len(text),
            "paper_labels_prompts_full": True,
            "paper_row_present": True,
            "paper_row_is_byte_identical_to_native_prompt": False,
            "correspondence": "same role/rules but materially abridged prose",
            "result_credit": False,
        })
    return rows


def corpus_rows(scratch: Path) -> list[dict[str, Any]]:
    import pandas as pd

    base = scratch / "native/Fin_Analyst"
    specs = {
        "TSLA_10k_signals.jsonl": (2, "filed_date", "2025-01-30", "2026-01-29"),
        "TSLA_10q_signals.jsonl": (3, "date", "2025-04-23", "2025-10-23"),
        "TSLA_8k_signals.jsonl": (12, "date", "2025-01-02", "2025-11-07"),
        "TSLA_compustat_signals.jsonl": (29, "rdq", "2019-04-24", "2026-04-22"),
        "TSLA_ibes_signals.jsonl": (14, "date", "2025-01-16", "2026-02-19"),
        "TSLA_wsb_2025.jsonl": (5721, "date", "2025-01-01", "2026-04-12"),
        "TSLA_TA_2025.csv": (249, "date", "2025-01-02", "2025-12-30"),
    }
    rows = []
    for name, (expected_count, field, expected_min, expected_max) in specs.items():
        path = base / name
        if path.suffix == ".csv":
            records = pd.read_csv(path).to_dict("records")
        else:
            records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        values = [str(record.get(field, ""))[:10] for record in records]
        observed = (len(records), min(values), max(values))
        if observed != (expected_count, expected_min, expected_max):
            raise ValueError(f"native corpus inventory changed: {name}={observed}")
        rows.append({
            "file": name, "records": len(records), "date_field": field,
            "minimum_date": min(values), "maximum_date": max(values),
            "sha256": sha256(path), "loaded_by_native_startup": True,
            "paper_window_boundary": (
                "technical rows stop 2025-12-30 and are stale for the entire May-June 2026 live window"
                if name == "TSLA_TA_2025.csv" else
                "no 7-day WSB records exist after 2026-04-12, so Social defaults HOLD throughout live window"
                if name == "TSLA_wsb_2025.jsonl" else "most-recent record is carried forward"
            ),
        })
    return rows


def dataset_rows(scratch: Path) -> list[dict[str, Any]]:
    import pandas as pd

    rows = []
    expected = {
        "TSLA": (283, 194, 302.6300048828125, 489.8800048828125, 41.542477346020505, 0.379),
        "BTC": (283, 283, 62754.09, 124797.86, -27.517082642510637, -0.315),
    }
    for asset, values in expected.items():
        frame = pd.read_parquet(scratch / f"dataset-may11/{asset}.parquet")
        row_count, distinct_days, low, high, raw_return, printed_bh = values
        changes = int(frame["prices"].diff().fillna(1).ne(0).sum())
        observed_return = 100 * (frame["prices"].iloc[-1] / frame["prices"].iloc[0] - 1)
        if len(frame) != row_count or changes != distinct_days:
            raise ValueError(f"dataset row/trading-day count changed for {asset}")
        if abs(float(frame["prices"].min()) - low) > 1e-9 or abs(float(frame["prices"].max()) - high) > 1e-9:
            raise ValueError(f"dataset range changed for {asset}")
        rows.append({
            "asset": asset, "revision": DATASET_COMMIT, "calendar_rows": len(frame),
            "distinct_price_observations_including_initial": changes,
            "start_date": frame["date"].iloc[0], "end_date": frame["date"].iloc[-1],
            "minimum_price": float(frame["prices"].min()), "maximum_price": float(frame["prices"].max()),
            "raw_start_to_end_return_pct": observed_return,
            "paper_buy_hold_return_pct": 100 * printed_bh,
            "paper_buy_hold_matches_raw_dataset": abs(observed_return - 100 * printed_bh) < 0.05,
            "boundary": "paper range/count matches pinned pre-live dataset; printed B&H return does not",
        })
        if abs(observed_return - raw_return) > 1e-10:
            raise ValueError(f"dataset return changed for {asset}")
    return rows


def replay_rows(scratch: Path) -> list[dict[str, Any]]:
    paper = {
        "TSLA": {"return": 13.51, "alpha": 28.33, "sharpe": 4.10, "win": 88.0, "rank": "1st / gold"},
        "BTC": {"return": -5.30, "alpha": 17.63, "sharpe": -1.09, "win": 36.0, "rank": "13th"},
    }
    rows = []
    for asset in ("TSLA", "BTC"):
        value = json.loads((scratch / f"replay/{asset}.json").read_text())
        decisions = value["rows"][:50] if asset == "BTC" else value["rows"]
        expected = 50 if asset == "BTC" else 47
        if len(decisions) != expected:
            raise ValueError(f"live decision window changed for {asset}")
        metrics = value["metrics"]
        bh = 100 * (value["bh"][-1] / value["bh"][0] - 1)
        alpha = metrics["total_return"] - bh
        wr = value["wr"]
        rows.append({
            "asset": asset, "decision_rows": len(decisions),
            "window_start": decisions[0]["date"], "window_end": decisions[-1]["date"],
            "paper_return_pct": paper[asset]["return"], "organizer_replay_return_pct": metrics["total_return"],
            "paper_vs_buy_hold_pp": paper[asset]["alpha"], "organizer_replay_vs_buy_hold_pp": alpha,
            "paper_sharpe": paper[asset]["sharpe"], "organizer_replay_sharpe": metrics["sharpe_ratio"],
            "paper_win_rate_pct": paper[asset]["win"], "organizer_replay_win_rate_pct": wr["winRate"],
            "organizer_replay_trade_count": wr["trades"], "paper_rank": paper[asset]["rank"],
            "historical_rank_reproducible": False,
            "all_printed_live_metrics_match": False,
            "boundary": "official decisions + pinned organizer scorer replay; action-generation LLM calls not rerun",
        })
    return rows


def figure_rows(scratch: Path) -> list[dict[str, Any]]:
    values = {
        "TSLA": (113326.0, 85313.0, 104623.48455502151, 85313.17459058214),
        "BTC": (99906.0, 73708.0, 99742.76385138858, 73707.63369556762),
    }
    rows = [{
        "figure": "Figure 1", "panel": "architecture", "empirical": False,
        "source_asset_sha256": "7498eb4bb7139482bca56df56f0b5efb19b3adbb2b057f0e13199a24225f04a0",
        "full_panel_regenerated": False, "exact_displayed_endpoint_annotations_verified": "not_applicable",
        "boundary": "conceptual diagram",
    }]
    for asset, (paper_agent, paper_bh, replay_agent, raw_bh) in values.items():
        rows.append({
            "figure": "Figure 2", "panel": asset, "empirical": True,
            "source_asset_sha256": "394e57057eaee99b2002a8dea8438c8df9ce31ddc2bfdfc43362727de7e50baf",
            "paper_agent_endpoint": paper_agent, "organizer_replay_agent_endpoint": replay_agent,
            "paper_buy_hold_endpoint": paper_bh, "raw_price_ratio_buy_hold_endpoint": raw_bh,
            "agent_endpoint_matches": abs(paper_agent - replay_agent) < 0.5,
            "buy_hold_endpoint_matches_rounding": round(raw_bh) == round(paper_bh),
            "full_panel_regenerated": False,
            "exact_displayed_endpoint_annotations_verified": "1/2",
            "boundary": "raw Buy-and-Hold endpoint verifies; agent curve/end does not reproduce from current official actions/scorer",
        })
    return rows


def native_execution(scratch: Path) -> dict[str, Any]:
    source = scratch / "native/Fin_Analyst"
    if not NATIVE_ENV.exists():
        raise ValueError(f"native audit environment absent: {NATIVE_ENV}")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update({"DATA_DIR": str(source), "OPENAI_API_KEY": "audit-dummy-never-called"})
    check = subprocess.run(
        [str(NATIVE_ENV / "bin/python"), "-m", "pip", "check"],
        env=env, check=True, capture_output=True, text=True,
    )
    compile_result = subprocess.run(
        [str(NATIVE_ENV / "bin/python"), "-m", "py_compile", "app.py"],
        cwd=source, env=env, check=True, capture_output=True, text=True,
    )
    harness = r'''
import asyncio, json
import app
app.load_all()
def btc(score, momentum, history):
    app.get_fear_greed = (lambda: (score, "fixture")) if score is not None else (lambda: (None, None))
    return app.decide_btc(momentum, {"BTC": [{"price": x} for x in history]})
result = {
    "btc_three_hold_case": btc(50, "neutral", [100, 100]),
    "btc_missing_fear_greed_case": btc(None, "bearish", [100, 100]),
    "btc_unanimous_buy_control": btc(70, "bullish", [100, 101]),
}
calls = []
def fake(system, user, max_tokens=120, use_cache=True):
    calls.append({"max_tokens": max_tokens, "use_cache": use_cache})
    return {"action": "SELL", "confidence": 0.7, "reasoning": "fixture"}
app.call_llm = fake
response = asyncio.run(app.predict({
    "symbol": ["TSLA"], "date": "2026-05-11", "price": {"TSLA": 445.08},
    "news": {"TSLA": "negative fixture"}, "momentum": {"TSLA": "bearish"},
    "history_price": {"TSLA": [{"price": 445.08}]}, "10k": ["ignored"], "10q": ["ignored"],
}))
result["tsla_endpoint"] = {
    "response": response, "llm_call_seams_exercised": len(calls),
    "token_caps": [item["max_tokens"] for item in calls],
    "memory_counts": {key: len(value) for key, value in app.sigs.items()},
    "ta_rows": len(app.ta_data),
}
print(json.dumps(result, sort_keys=True))
'''
    run = subprocess.run(
        [str(NATIVE_ENV / "bin/python"), "-c", harness], cwd=source, env=env,
        check=True, capture_output=True, text=True,
    )
    result = json.loads(run.stdout.strip().splitlines()[-1])
    expected_memory = {"8k": 12, "10q": 3, "10k": 2, "compustat": 29, "ibes": 14, "wsb": 5721}
    if result["tsla_endpoint"]["memory_counts"] != expected_memory:
        raise ValueError("native startup memory counts changed")
    if result["tsla_endpoint"]["llm_call_seams_exercised"] != 8:
        raise ValueError("native TSLA controlled call count changed")
    if result["btc_three_hold_case"][0] != "BUY" or "H=3" not in result["btc_three_hold_case"][1]:
        raise ValueError("documented BTC all-HOLD defect changed")
    if "S=2" not in result["btc_missing_fear_greed_case"][1]:
        raise ValueError("documented BTC duplicate-momentum defect changed")
    return {
        "author_commit": AUTHOR_COMMIT,
        "native_environment_python": "3.12 audit reconstruction; author Dockerfile specifies mutable python:3.11-slim",
        "author_requirements_are_lower_bounds_not_a_lock": True,
        "pip_check_passed": check.stdout.strip() == "No broken requirements found.",
        "app_py_compiles": compile_result.returncode == 0,
        "paid_or_external_model_calls": 0,
        "external_fear_greed_calls": 0,
        "controlled_execution": result,
        "native_components_executed": ["startup loaders", "seven corpus paths", "TSLA /predict router", "eight LLM call seams", "BTC voting", "endpoint exception boundary"],
        "author_native_paper_actions_regenerated": 0,
        "published_table_cells_regenerated": 0,
        "strict_success": False,
    }


def method_rows() -> list[dict[str, str]]:
    values = (
        ("official paper and source", "complete", "single 13-page arXiv-v1 PDF and nine-file source archive pinned; all official/rebuilt pages visually checked"),
        ("author implementation", "substantial_pre_live_R3", "first-author Hugging Face Space, 13 files, Docker runner, requirements, seven corpora, commit 85ab478 on 2026-05-04"),
        ("license", "absent", "no license file or declared license observed in author Space"),
        ("dependency environment", "unlocked", "python:3.11-slim plus six lower-bounded requirements; no exact lock or image digest"),
        ("model", "mutable_alias", "gpt-4o-mini, temperature .1, JSON mode, token caps; no dated snapshot, seed, request IDs, or responses"),
        ("paper prompts", "abridged", "nine paper rows correspond to source constants but are not the full byte-identical prompts despite the full-prompts label"),
        ("TSLA runtime", "native_controlled", "startup, lookups, router, and eight call seams execute under deterministic model stubs; no paid model call"),
        ("BTC runtime", "native_controlled_with_defects", "native vote runs; three HOLD votes become BUY and missing Fear & Greed duplicates momentum"),
        ("persistent corpora", "complete_static_snapshot", "7/7 files load, 6,030 JSONL records plus 249 TA rows"),
        ("live freshness", "partial", "TA stops 2025-12-30 and WSB stops 2026-04-12 before May-June live evaluation"),
        ("official live decisions", "recovered", "97 paper-window rows: 47 TSLA and 50 BTC, from organizer public database snapshot"),
        ("organizer scoring", "replayed_current", "pinned May-22 organizer scorer with 6-bp fees and 10-bp execution slippage"),
        ("live result reproduction", "failed", "current official actions/scorer match none of ten printed live table cells"),
        ("offline dataset", "recovered_pre_live", "May-11 revision has exact paper date span, price ranges, and 194/283 distinct observations"),
        ("offline actions", "missing", "no immutable gpt-4o-mini calls/responses, historical Fear & Greed series, action path, seed, or cache state"),
        ("offline results", "missing", "no raw paths, baseline actions, ablation runs, result arrays, or generator"),
        ("cost model", "paper_partial_source_current", "paper says net of fees but omits full implementation; current organizer source uses 6-bp fees plus 10-bp slippage"),
        ("rank provenance", "not_recoverable", "current dynamic leaderboard cannot prove historical ranks as displayed on 2026-07-05"),
        ("statistical inference", "absent", "paper explicitly reports no significance testing"),
    )
    return [{"dimension": a, "status": b, "evidence": c} for a, b, c in values]


def consistency_rows() -> list[dict[str, str]]:
    values = (
        ("btc_live_table_vs_figure", "major_numeric_conflict", "table reports -5.30%, but Figure 2 ends at $99,906 (~-0.09%) and prose says essentially flat"),
        ("btc_live_table_vs_discussion", "major_numeric_conflict", "table alpha is +17.63pp, while discussion reports +26.2pp and B&H down 26.3%, consistent with the figure/raw price ratio"),
        ("btc_live_table_vs_official_replay", "major_numeric_conflict", "97-row official-log window plus pinned organizer scorer yields -0.0976%, Sharpe 0.108, win rate 40%, not -5.30%, -1.09, 36%"),
        ("tsla_live_table_vs_official_replay", "major_numeric_conflict", "official actions plus pinned scorer yield +4.791%, Sharpe 1.578, win rate 45%, not +13.51%, 4.10, 88%"),
        ("figure_buy_hold_lineage", "verified_component", "raw first/last price ratios round exactly to $85,313 TSLA and $73,708 BTC figure endpoints"),
        ("figure_agent_lineage", "not_reproduced", "official actions/current scorer end at $104,623 TSLA and $99,743 BTC rather than $113,326 and $99,906"),
        ("offline_buy_hold_tsla", "major_numeric_conflict", "pinned pre-live dataset raw return is +41.542%, not printed +37.9%"),
        ("offline_buy_hold_btc", "major_numeric_conflict", "pinned pre-live dataset raw return is -27.517%, not printed -31.5%"),
        ("btc_all_hold_majority", "source_method_conflict", "paper says final action is majority of three votes; source converts B=0,S=0,H=3 to BUY because it tests B==S only"),
        ("btc_missing_fear_greed", "source_method_conflict", "when endpoint fails, source adds the momentum vote in the fallback and then adds it again unconditionally"),
        ("fear_greed_interpretation", "narrative_rule_tension", "paper calls extreme fear a long opportunity but maps scores <=40 to SELL"),
        ("full_prompts_claim", "specification_conflict", "appendix says full prompts, but all nine rows are abridged versions of the released native constants"),
        ("live_error_attribution_denominators", "accounting_conflict", "paper counts TSLA 19/33 and BTC 31/50 acted days while the public rows and next-move availability require different denominator conventions"),
        ("mutable_model_replay", "irrecoverable_exactness", "gpt-4o-mini alias, SDK/image dependencies, requests/responses, cache state, and API seed are not frozen"),
    )
    return [{"check": a, "status": b, "detail": c} for a, b, c in values]


def release_rows() -> list[dict[str, Any]]:
    values = (
        ("paper/arXiv exact GitHub search", "no repository", "bounded search result pinned; negative search is not proof of absence", False),
        ("first-author Hugging Face Space", AUTHOR_SPACE, f"strong attribution; created before live window; pinned {AUTHOR_COMMIT}", True),
        ("organizer dataset", DATASET_URL, f"103-revision history; pre-live dataset pinned {DATASET_COMMIT}", True),
        ("organizer arena", ARENA_SPACE, f"public scorer repository pinned {ARENA_COMMIT}; public database snapshot separately hashed", True),
    )
    return [{"search_or_artifact": a, "result": b, "boundary": c, "attributable_or_official": d} for a, b, c, d in values]


def build(scratch: Path, output: Path) -> None:
    verify_pins(scratch)
    files = paper_sources(scratch)
    source = files["fin_mm_eval_working_notes.tex"].decode()
    app_source = (scratch / "native/Fin_Analyst/app.py").read_text()
    overlap = token_jaccard(
        (scratch / "primary/official-v1.txt").read_text(errors="replace"),
        (scratch / "primary/rebuilt-v1.txt").read_text(errors="replace"),
    )
    if overlap < 0.999:
        raise ValueError(f"source rebuild overlap regressed: {overlap}")
    tables = result_rows(source)
    prompts = prompt_rows(source, app_source)
    corpora = corpus_rows(scratch)
    datasets = dataset_rows(scratch)
    replays = replay_rows(scratch)
    figures = figure_rows(scratch)
    execution = native_execution(scratch)
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "published_result_ledger.csv", tables)
    write_csv(output / "prompt_correspondence.csv", prompts)
    write_csv(output / "native_corpus_inventory.csv", corpora)
    write_csv(output / "offline_dataset_audit.csv", datasets)
    write_csv(output / "live_result_replay.csv", replays)
    write_csv(output / "figure_inventory.csv", figures)
    write_csv(output / "method_specification_audit.csv", method_rows())
    write_csv(output / "internal_consistency_audit.csv", consistency_rows())
    write_csv(output / "release_search_audit.csv", release_rows())
    write_json(output / "native_execution.json", execution)
    provenance = {
        "work_id": WORK_ID, "system_id": SYSTEM_ID, "arxiv_id": ARXIV_ID,
        "paper_version": "v1 (2026-07-14)", "official_pages": 13, "rebuilt_pages": 13,
        "source_files": len(files), "official_rebuilt_token_jaccard": overlap,
        "all_official_and_rebuilt_pages_visually_checked": True,
        "paper_source_sha256": {name: sha256_bytes(value) for name, value in sorted(files.items())},
        "author_space": {"url": AUTHOR_SPACE, "commit": AUTHOR_COMMIT, "tracked_files": 13, "license": "NOASSERTION"},
        "dataset": {"url": DATASET_URL, "pre_live_commit": DATASET_COMMIT},
        "organizer": {"url": ARENA_SPACE, "source_commit": ARENA_COMMIT, "decision_snapshot_sha256": PINS["discovery/arena-fin-analyst-rows.json"]},
        "negative_search_boundary": "bounded searches do not prove private, deleted, moved, renamed, or unindexed artifacts never existed",
    }
    write_json(output / "source_provenance.json", provenance)
    readme = """# Fin-Analyst paper-faithfulness audit

This audit uses the official 13-page arXiv-v1 paper, its complete nine-file source archive, a pre-live first-author Hugging Face deployment, the official organizer dataset and scorer, and a pinned snapshot of the organizer's public per-day decision log. The unmodified source rebuild reaches 99.96% extracted-token overlap; all official and rebuilt pages were visually checked.

The paper has **119 displayed empirical table cells** and **two empirical figure panels**. The attributable R3 deployment materially improves source-level fidelity: its Docker/FastAPI runner, nine native prompts, seven corpora, TSLA routing, BTC vote and failure behavior are inspectable. A dependency-isolated controlled run loads all corpora and exercises the native endpoint and voting paths without paid or external model calls. The public organizer log recovers 97 paper-window decisions, and the pinned organizer scorer replays them.

That evidence does **not** reproduce the paper's empirical claims. Zero of 119 printed table cells and zero of two full empirical panels regenerate at display precision. The raw price series does verify the two plotted Buy-and-Hold endpoints, but not the agent curves. Current official decisions plus the organizer scorer yield TSLA +4.79%/Sharpe 1.58/45% win rate rather than +13.51%/4.10/88%. BTC replays essentially flat (-0.10%), which agrees with the paper's figure and prose but conflicts with its table (-5.30%); the table's BTC alpha, Sharpe and win rate are likewise stale or inconsistent. The pinned pre-live dataset matches the paper's windows, counts and price ranges, yet its raw Buy-and-Hold returns do not match either offline table.

Native inspection also finds method-level defects. Three BTC HOLD votes become BUY because the code compares only BUY and SELL counts; a failed Fear & Greed request double-counts momentum. All nine appendix prompt rows are abridged relative to the released constants despite being labeled full prompts. The model alias, API calls, cache state, image, SDK and dependencies are not immutably frozen, the released TA and WSB corpora are stale before the live window ends, and no offline action/ablation paths or result generator are shipped.

Therefore `strict_success` is false. This is strong native source and output-lineage recovery, not an end-to-end regeneration. The honest result is substantially closer than a paper-only proxy, while still far from 100% paper-result faithfulness.
"""
    (output / "README.md").write_text(readme)
    generated_names = [path.name for path in output.iterdir() if path.name != "manifest.json"]
    manifest = {
        "work_id": WORK_ID, "system_id": SYSTEM_ID, "arxiv_id": ARXIV_ID,
        "active_empirical_table_cells": 119, "empirical_figure_panels": 2,
        "attributable_pre_live_native_implementation_found": True,
        "native_controlled_execution_passed": True,
        "paper_window_official_decision_rows_recovered": 97,
        "paper_window_official_rows_replayed_with_organizer_scorer": 97,
        "published_table_cells_regenerated": 0,
        "full_empirical_figure_panels_regenerated": 0,
        "displayed_figure_endpoints_verified": 2,
        "paper_appendix_prompt_rows": 9,
        "byte_identical_full_native_prompts_in_paper": 0,
        "full_end_to_end_pipeline_reproduced": False,
        "strict_success": False,
        "generated_file_sha256": {name: sha256(output / name) for name in sorted(generated_names)},
    }
    write_json(output / "manifest.json", manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.scratch.resolve(), args.output.resolve())
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
