#!/usr/bin/env python3
"""Concurrent, cost-capped OpenRouter replay of the public GuruAgents prompts."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import os
import random
import re
import stat
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


DEFAULT_SOURCE = Path(
    "/nfs/roberts/scratch/pi_btk22/zc362/guruagents_prompt_replay_source"
)
ARCHIVES = ("results", "results_22_24")
MODES = ("archived-final", "tool-routing")
AGENT_FILES = {
    "altman": "EdwardAltman_agent.py",
    "buffett": "WarrenBuffett_agent.py",
    "graham": "BenjaminGraham_agent.py",
    "greenblatt": "JoelGreenblatt_agent.py",
    "piotroski": "JosephPiotroski_agent.py",
}


class ReplayError(RuntimeError):
    pass


class BudgetExceeded(ReplayError):
    pass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str


@dataclass(frozen=True)
class Cell:
    archive: str
    agent: str
    analysis_path: Path
    portfolio_path: Path
    start_date: str
    end_date: str
    quarter: str
    available_tickers: int
    historical_comparison: bool


@dataclass(frozen=True)
class Experiment:
    cell: Cell
    mode: str
    replicate: int

    @property
    def experiment_id(self) -> str:
        c = self.cell
        return (
            f"{c.archive}__{c.agent}__{c.start_date}__{c.end_date}"
            f"__{self.mode}__r{self.replicate:02d}"
        )


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def csv_option(value: str) -> Tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    os.replace(str(temporary), str(path))


def source_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def quarter_label(value: str) -> str:
    value = str(value).strip()
    if re.fullmatch(r"\d{4}Q[1-4]", value):
        return value
    parsed = datetime.strptime(value[:10], "%Y-%m-%d")
    return f"{parsed.year}Q{(parsed.month - 1) // 3 + 1}"


def extract_prompt_and_tools(path: Path) -> Tuple[str, List[ToolSpec]]:
    """Statically copy the source template and Tool name/description strings."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    prompt: Optional[str] = None
    tools: List[ToolSpec] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if value is None:
            continue
        if any(isinstance(target, ast.Name) and target.id == "template" for target in targets):
            prompt = ast.literal_eval(value)
        if not any(
            isinstance(target, ast.Attribute) and target.attr == "tools"
            for target in targets
        ) or not isinstance(value, (ast.List, ast.Tuple)):
            continue
        for element in value.elts:
            if not isinstance(element, ast.Call):
                continue
            func = element.func.id if isinstance(element.func, ast.Name) else ""
            if func != "Tool":
                continue
            keywords = {kw.arg: kw.value for kw in element.keywords if kw.arg}
            try:
                tools.append(
                    ToolSpec(
                        name=str(ast.literal_eval(keywords["name"])),
                        description=str(ast.literal_eval(keywords["description"])),
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                raise ReplayError(f"nonliteral Tool declaration in {path}") from exc
    if not isinstance(prompt, str) or not tools:
        raise ReplayError(f"could not extract prompt/tools from {path}")
    return prompt, tools


def quarter_counts(root: Path) -> Dict[str, int]:
    path = root / "data" / "nasdaq100_bs_cf_is.csv"
    counts: Dict[str, int] = {}
    if not path.exists():
        return counts
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            quarter = str(row.get("QUARTER", "")).strip()
            if quarter:
                counts[quarter] = counts.get(quarter, 0) + 1
    return counts


def discover_cells(root: Path, archives: Sequence[str], agents: Sequence[str]) -> List[Cell]:
    counts = quarter_counts(root)
    wanted = set(agents)
    cells: List[Cell] = []
    for archive in archives:
        archive_root = root / archive
        if not archive_root.is_dir():
            raise ReplayError(f"missing archive {archive_root}")
        for analysis_path in sorted(archive_root.glob("*_agent/*_analysis_*.json")):
            agent = analysis_path.parent.name.removesuffix("_agent")
            if agent not in wanted:
                continue
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            start, end = str(analysis["start_date"]), str(analysis["end_date"])
            quarter = quarter_label(end)
            portfolio = analysis_path.with_name(
                analysis_path.name.replace("_analysis_", "_portfolio_").replace(
                    ".json", ".csv"
                )
            )
            if not portfolio.exists():
                raise ReplayError(f"missing portfolio {portfolio}")
            prior = f"{int(quarter[:4]) - 1}Q{quarter[-1]}"
            cells.append(
                Cell(
                    archive,
                    agent,
                    analysis_path,
                    portfolio,
                    start,
                    end,
                    quarter,
                    counts.get(quarter, 0),
                    counts.get(prior, 0) > 0,
                )
            )
    if not cells:
        raise ReplayError("no cells matched the requested grid")
    return cells


def source_request(cell: Cell) -> str:
    """Recreate each analyzer's f-string request, including source whitespace."""
    if cell.agent == "graham":
        return f"""
    Analyze these stocks using Graham's principles:
    - Period start: {cell.start_date}
    - Period end: {cell.quarter}
    """
    if cell.agent == "altman":
        return f"""
Analyze these stocks using Altman's Z-Score family:
- Period start: {cell.start_date}
- Period end: {cell.quarter}
- Available tickers: {cell.available_tickers}
"""
    if cell.agent == "greenblatt":
        return f"""
Analyze these stocks using Greenblatt's Magic Formula:
- Period start: {cell.start_date}
- Period end: {cell.quarter}
"""
    if cell.agent == "piotroski":
        prior = f"{int(cell.quarter[:4]) - 1}Q{cell.quarter[-1]}"
        return f"""
Analyze these stocks using Piotroski's F-Score (Data-Constrained Version):
- Period start: {cell.start_date}
- Period end: {cell.quarter} (previous: {prior})
- Available tickers: {cell.available_tickers}
- Historical comparison enabled: {cell.historical_comparison}
- Note: Using Net Income as CFO proxy due to data limitations
"""
    if cell.agent == "buffett":
        return f"""
Analyze these stocks as Warren Buffett (rules in system prompt):
- Period start: {cell.start_date}
- Period end: {cell.quarter}
"""
    raise ReplayError(f"unsupported agent {cell.agent}")


def tool_definitions(specs: Sequence[ToolSpec]) -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": {
                    "type": "object",
                    "properties": {"input": {"type": "string"}},
                    "required": ["input"],
                    "additionalProperties": False,
                },
            },
        }
        for spec in specs
    ]


def load_analysis(cell: Cell) -> Dict[str, Any]:
    analysis = json.loads(cell.analysis_path.read_text(encoding="utf-8"))
    steps = analysis.get("intermediate_steps")
    if not isinstance(steps, list) or not steps:
        raise ReplayError(f"missing intermediate_steps in {cell.analysis_path}")
    return analysis


def archived_messages(
    prompt: str, request: str, steps: Sequence[Mapping[str, Any]]
) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": request},
    ]
    for index, step in enumerate(steps, 1):
        call_id = f"archived_call_{index:02d}"
        name = str(step["tool_name"])
        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(
                                {"input": step.get("tool_input", "")},
                                ensure_ascii=False,
                            ),
                        },
                    }
                ],
            }
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": name,
                "content": str(step.get("observation", "")),
            }
        )
    return messages


def payload(
    model: str,
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]],
    max_tokens: int,
) -> Dict[str, Any]:
    return {
        "model": model,
        "messages": list(messages),
        "tools": list(tools),
        "temperature": 0,
        "max_tokens": max_tokens,
    }


def conservative_cost(
    request_payload: Mapping[str, Any], input_price: float, output_price: float
) -> float:
    encoded = json.dumps(
        request_payload, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    prompt_tokens = math.ceil(len(encoded) / 2)  # deliberately conservative
    output_tokens = int(request_payload.get("max_tokens", 0))
    return (prompt_tokens * input_price + output_tokens * output_price) / 1_000_000


def estimate_experiment(
    experiment: Experiment,
    prompt: str,
    tools: Sequence[Mapping[str, Any]],
    analysis: Mapping[str, Any],
    model: str,
    max_tokens: int,
    input_price: float,
    output_price: float,
) -> float:
    steps = analysis["intermediate_steps"]
    request = source_request(experiment.cell)
    if experiment.mode == "archived-final":
        return conservative_cost(
            payload(model, archived_messages(prompt, request, steps), tools, max_tokens),
            input_price,
            output_price,
        )
    transcript: List[Dict[str, Any]] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": request},
    ]
    total = 0.0
    for step in steps:
        total += conservative_cost(
            payload(model, transcript, tools, max_tokens), input_price, output_price
        )
        transcript.extend(archived_messages("", "", [step])[2:])
    return total + conservative_cost(
        payload(model, transcript, tools, max_tokens), input_price, output_price
    )


class BudgetLedger:
    def __init__(self, cap_usd: float) -> None:
        if cap_usd <= 0:
            raise ValueError("cap must be positive")
        self.cap_usd, self.spent_usd, self.reserved_usd = cap_usd, 0.0, 0.0
        self.lock = threading.Lock()

    def reserve(self, amount: float) -> float:
        amount = max(0.0, float(amount))
        with self.lock:
            committed = self.spent_usd + self.reserved_usd + amount
            if committed > self.cap_usd + 1e-12:
                raise BudgetExceeded(
                    f"${committed:.4f} committed would exceed ${self.cap_usd:.2f} cap"
                )
            self.reserved_usd += amount
        return amount

    def settle(self, reservation: float, actual: float) -> None:
        with self.lock:
            self.reserved_usd = max(0.0, self.reserved_usd - reservation)
            self.spent_usd += max(0.0, float(actual))
            if self.spent_usd + self.reserved_usd > self.cap_usd + 1e-9:
                raise BudgetExceeded("reported API cost exceeded conservative reservation")

    def release(self, reservation: float) -> None:
        with self.lock:
            self.reserved_usd = max(0.0, self.reserved_usd - reservation)

    def snapshot(self) -> Dict[str, float]:
        with self.lock:
            return {
                "cap_usd": self.cap_usd,
                "spent_usd": self.spent_usd,
                "reserved_usd": self.reserved_usd,
                "remaining_usd": max(
                    0.0, self.cap_usd - self.spent_usd - self.reserved_usd
                ),
            }


class Journal:
    def __init__(self, path: Path) -> None:
        self.path, self.lock = path, threading.Lock()

    def append(self, value: Mapping[str, Any]) -> None:
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n")


def usage_cost(
    response: Mapping[str, Any], input_price: float, output_price: float
) -> Tuple[float, Dict[str, Any]]:
    raw = response.get("usage", {})
    usage = dict(raw) if isinstance(raw, Mapping) else {}
    if isinstance(usage.get("cost"), (int, float)):
        return float(usage["cost"]), usage
    calculated = (
        int(usage.get("prompt_tokens", 0) or 0) * input_price
        + int(usage.get("completion_tokens", 0) or 0) * output_price
    ) / 1_000_000
    usage["cost_fallback_usd"] = calculated
    return calculated, usage


class OpenRouter:
    def __init__(
        self,
        key: str,
        ledger: BudgetLedger,
        journal: Journal,
        input_price: float,
        output_price: float,
        timeout: float,
        retries: int,
        referer: str,
    ) -> None:
        self.key, self.ledger, self.journal = key, ledger, journal
        self.input_price, self.output_price = input_price, output_price
        self.timeout, self.retries, self.referer = timeout, retries, referer

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referer,
            "X-OpenRouter-Title": "GuruAgents paper prompt replay",
        }

    def key_metadata(self) -> Dict[str, Any]:
        request = urllib.request.Request(
            "https://openrouter.ai/api/v1/key", headers=self.headers
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as handle:
            result = json.loads(handle.read().decode())
        return dict(result.get("data", result))

    def complete(
        self, request_payload: Mapping[str, Any], experiment_id: str, turn: int
    ) -> Dict[str, Any]:
        reservation = self.ledger.reserve(
            conservative_cost(request_payload, self.input_price, self.output_price)
        )
        body = json.dumps(request_payload, ensure_ascii=False).encode()
        started, settled = time.monotonic(), False
        try:
            for attempt in range(self.retries + 1):
                request = urllib.request.Request(
                    "https://openrouter.ai/api/v1/chat/completions",
                    data=body,
                    headers=self.headers,
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(request, timeout=self.timeout) as handle:
                        response = json.loads(handle.read().decode())
                    break
                except urllib.error.HTTPError as exc:
                    message = exc.read().decode(errors="replace")
                    if (exc.code != 429 and not 500 <= exc.code < 600) or attempt == self.retries:
                        raise ReplayError(f"OpenRouter HTTP {exc.code}: {message[:1500]}")
                except urllib.error.URLError as exc:
                    if attempt == self.retries:
                        raise ReplayError(f"OpenRouter request failed: {exc}")
                time.sleep(min(30, 2**attempt + random.random()))
            else:  # pragma: no cover
                raise ReplayError("retry loop exhausted")
            if response.get("error"):
                raise ReplayError(f"OpenRouter error: {response['error']}")
            cost, usage = usage_cost(response, self.input_price, self.output_price)
            self.ledger.settle(reservation, cost)
            settled = True
            self.journal.append(
                {
                    "timestamp_utc": now(),
                    "experiment_id": experiment_id,
                    "turn": turn,
                    "response_id": response.get("id"),
                    "model": response.get("model"),
                    "usage": usage,
                    "cost_usd": cost,
                    "elapsed_seconds": time.monotonic() - started,
                    "ledger": self.ledger.snapshot(),
                }
            )
            return response
        finally:
            if not settled:
                self.ledger.release(reservation)


def assistant_message(response: Mapping[str, Any]) -> Dict[str, Any]:
    try:
        raw = response["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ReplayError(f"response has no assistant message: {response}") from exc
    message: Dict[str, Any] = {
        "role": str(raw.get("role", "assistant")),
        "content": raw.get("content"),
    }
    if raw.get("tool_calls"):
        message["tool_calls"] = raw["tool_calls"]
    return message


def parse_portfolio(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) < 4:
            continue
        ticker = re.sub(r"[*`]", "", parts[0]).upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,14}", ticker) or ticker == "TICKER":
            continue
        try:
            score = float(re.sub(r"[^0-9eE+\-.]", "", parts[1]))
            weight = float(re.sub(r"[^0-9eE+\-.]", "", parts[2]))
        except ValueError:
            continue
        rows.append(
            {"Ticker": ticker, "Score": score, "Weight (%)": weight, "Reason": parts[3]}
        )
    return rows


def archived_portfolio(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    result: List[Dict[str, Any]] = []
    for row in rows:
        ticker = row["Ticker"].strip().upper()
        # One published Altman CSV contains a blank-ticker remainder row. It is
        # an allocation note rather than a security and must not enter fidelity
        # metrics as a synthetic holding.
        if not ticker:
            continue
        result.append(
            {
                "Ticker": ticker,
                "Score": float(row["Score"]),
                "Weight (%)": float(row["Weight (%)"]),
                "Reason": row.get("Reason", ""),
            }
        )
    return result


def compare_portfolios(
    replayed: Sequence[Mapping[str, Any]], archived: Sequence[Mapping[str, Any]]
) -> Dict[str, Any]:
    left = {str(row["Ticker"]): row for row in replayed}
    right = {str(row["Ticker"]): row for row in archived}
    intersection, union = set(left) & set(right), set(left) | set(right)
    weight_errors = [
        abs(
            float(left.get(ticker, {}).get("Weight (%)", 0))
            - float(right.get(ticker, {}).get("Weight (%)", 0))
        )
        for ticker in union
    ]
    score_errors = [
        abs(float(left[ticker]["Score"]) - float(right[ticker]["Score"]))
        for ticker in intersection
    ]
    return {
        "parse_success": bool(replayed),
        "replayed_rows": len(replayed),
        "archived_rows": len(archived),
        "ticker_intersection": len(intersection),
        "ticker_union": len(union),
        "ticker_jaccard": len(intersection) / len(union) if union else 1.0,
        "exact_ticker_order": [row["Ticker"] for row in replayed]
        == [row["Ticker"] for row in archived],
        "weight_l1_percentage_points": sum(weight_errors),
        "weight_mae_percentage_points": (
            sum(weight_errors) / len(weight_errors) if weight_errors else 0.0
        ),
        "matched_score_mae": (
            sum(score_errors) / len(score_errors) if score_errors else None
        ),
        "replayed_weight_sum": sum(float(row["Weight (%)"]) for row in replayed),
        "archived_weight_sum": sum(float(row["Weight (%)"]) for row in archived),
    }


def select_observation(
    steps: Sequence[Mapping[str, Any]], used: set[int], name: str
) -> Tuple[int, Mapping[str, Any]]:
    for index, step in enumerate(steps):
        if index not in used and step.get("tool_name") == name:
            return index, step
    remaining = [step.get("tool_name") for i, step in enumerate(steps) if i not in used]
    raise ReplayError(f"requested unavailable/repeated tool {name}; remaining={remaining}")


def run_one(
    experiment: Experiment,
    source_root: Path,
    output_root: Path,
    model: str,
    max_tokens: int,
    max_tool_rounds: int,
    client: OpenRouter,
    prompts: Mapping[str, Tuple[str, Sequence[ToolSpec]]],
    overwrite: bool,
) -> Dict[str, Any]:
    cell = experiment.cell
    directory = output_root / "experiments" / experiment.experiment_id
    result_path = directory / "result.json"
    if result_path.exists() and not overwrite:
        prior = json.loads(result_path.read_text(encoding="utf-8"))
        if prior.get("status") == "success":
            return prior
    directory.mkdir(parents=True, exist_ok=True)
    prompt, specs = prompts[cell.agent]
    tools = tool_definitions(specs)
    analysis = load_analysis(cell)
    steps = analysis["intermediate_steps"]
    provenance = {
        "experiment_id": experiment.experiment_id,
        "archive": cell.archive,
        "agent": cell.agent,
        "mode": experiment.mode,
        "replicate": experiment.replicate,
        "model": model,
        "temperature": 0,
        "start_date": cell.start_date,
        "end_date": cell.end_date,
        "formation_quarter": cell.quarter,
        "source_commit": source_commit(source_root),
        "agent_source": str(source_root / "agents" / AGENT_FILES[cell.agent]),
        "analysis_path": str(cell.analysis_path),
        "portfolio_path": str(cell.portfolio_path),
        "prompt_sha256": sha_text(prompt),
        "analysis_sha256": sha_file(cell.analysis_path),
        "portfolio_sha256": sha_file(cell.portfolio_path),
        "tool_order_archived": [step["tool_name"] for step in steps],
        "created_utc": now(),
    }
    atomic_json(directory / "provenance.json", provenance)
    responses: List[Dict[str, Any]] = []
    used_tools: List[str] = []
    started = time.monotonic()

    if experiment.mode == "archived-final":
        messages = archived_messages(prompt, source_request(cell), steps)
        request_payload = payload(model, messages, tools, max_tokens)
        atomic_json(directory / "request.json", request_payload)
        response = client.complete(request_payload, experiment.experiment_id, 1)
        responses.append(response)
        final_message = assistant_message(response)
        messages.append(final_message)
        final_text = str(final_message.get("content") or "")
        used_tools = [str(step["tool_name"]) for step in steps]
    elif experiment.mode == "tool-routing":
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": source_request(cell)},
        ]
        atomic_json(directory / "initial_request.json", payload(model, messages, tools, max_tokens))
        used_indices: set[int] = set()
        final_text = ""
        for turn in range(1, max_tool_rounds + 2):
            response = client.complete(
                payload(model, messages, tools, max_tokens), experiment.experiment_id, turn
            )
            responses.append(response)
            message = assistant_message(response)
            messages.append(message)
            calls = message.get("tool_calls")
            if not calls:
                final_text = str(message.get("content") or "")
                break
            if turn > max_tool_rounds:
                raise ReplayError("tool-routing exceeded maximum rounds")
            for call in calls:
                name = str(call.get("function", {}).get("name", ""))
                index, step = select_observation(steps, used_indices, name)
                used_indices.add(index)
                used_tools.append(name)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(call.get("id", f"call_{turn}_{index}")),
                        "name": name,
                        "content": str(step.get("observation", "")),
                    }
                )
        else:  # pragma: no cover
            raise ReplayError("no final answer")
    else:
        raise ReplayError(f"unsupported mode {experiment.mode}")

    atomic_json(directory / "responses.json", responses)
    atomic_json(directory / "transcript.json", messages)
    (directory / "final_output.md").write_text(final_text + "\n", encoding="utf-8")
    comparison = compare_portfolios(
        parse_portfolio(final_text), archived_portfolio(cell.portfolio_path)
    )
    costs, prompt_tokens, completion_tokens = 0.0, 0, 0
    for response in responses:
        cost, usage = usage_cost(response, client.input_price, client.output_price)
        costs += cost
        prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens += int(usage.get("completion_tokens", 0) or 0)
    result = {
        **provenance,
        "status": "success",
        "completed_utc": now(),
        "elapsed_seconds": time.monotonic() - started,
        "api_calls": len(responses),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": costs,
        "tool_order_replayed": used_tools,
        "unused_archived_tools": [
            step["tool_name"] for step in steps if step["tool_name"] not in used_tools
        ],
        "final_output_sha256": sha_text(final_text),
        "comparison": comparison,
    }
    atomic_json(result_path, result)
    return result


def summary_row(result: Mapping[str, Any]) -> Dict[str, Any]:
    comparison = result.get("comparison", {})
    return {
        "experiment_id": result.get("experiment_id"),
        "status": result.get("status"),
        "archive": result.get("archive"),
        "agent": result.get("agent"),
        "start_date": result.get("start_date"),
        "end_date": result.get("end_date"),
        "mode": result.get("mode"),
        "model": result.get("model"),
        "api_calls": result.get("api_calls"),
        "prompt_tokens": result.get("prompt_tokens"),
        "completion_tokens": result.get("completion_tokens"),
        "cost_usd": result.get("cost_usd"),
        "parse_success": comparison.get("parse_success"),
        "ticker_jaccard": comparison.get("ticker_jaccard"),
        "exact_ticker_order": comparison.get("exact_ticker_order"),
        "weight_mae_percentage_points": comparison.get("weight_mae_percentage_points"),
        "matched_score_mae": comparison.get("matched_score_mae"),
        "error": result.get("error"),
    }


def write_summary(path: Path, results: Sequence[Mapping[str, Any]]) -> None:
    rows = [summary_row(result) for result in results]
    fields = list(rows[0]) if rows else list(summary_row({}))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".csv.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(str(temporary), str(path))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    result.add_argument("--archives", default=",".join(ARCHIVES))
    result.add_argument("--agents", default=",".join(AGENT_FILES))
    result.add_argument("--modes", default=",".join(MODES))
    result.add_argument("--replicates", type=int, default=1)
    result.add_argument("--model", default="openai/gpt-4o")
    result.add_argument("--workers", type=int, default=16)
    result.add_argument("--max-budget-usd", type=float, default=450.0)
    result.add_argument("--max-tokens", type=int, default=4096)
    result.add_argument("--max-tool-rounds", type=int, default=12)
    result.add_argument("--input-price-per-million", type=float, default=2.5)
    result.add_argument("--output-price-per-million", type=float, default=10.0)
    result.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    result.add_argument(
        "--api-key-file",
        type=Path,
        help="optional chmod-600 secret file; the key is never copied into outputs",
    )
    result.add_argument("--request-timeout", type=float, default=240.0)
    result.add_argument("--retries", type=int, default=5)
    result.add_argument(
        "--http-referer",
        default="https://github.com/Sasha-Cui/alpha-agent-replication",
    )
    result.add_argument("--output-root", type=Path)
    result.add_argument("--run-id")
    result.add_argument("--dry-run", action="store_true")
    result.add_argument("--overwrite", action="store_true")
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parser().parse_args(argv)
    archives, agents, modes = map(csv_option, (args.archives, args.agents, args.modes))
    if set(agents) - set(AGENT_FILES) or set(modes) - set(MODES):
        raise ReplayError("unknown agent or mode")
    if args.workers < 1 or args.replicates < 1:
        raise ReplayError("workers and replicates must be positive")
    root = args.source_root.resolve()
    repo_root = Path(__file__).resolve().parents[1]
    base = args.output_root.resolve() if args.output_root else repo_root / "runs" / "prompt_replay" / "guruagents"
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = base / run_id
    output.mkdir(parents=True, exist_ok=True)

    prompts = {
        agent: extract_prompt_and_tools(root / "agents" / AGENT_FILES[agent])
        for agent in agents
    }
    cells = discover_cells(root, archives, agents)
    experiments = [
        Experiment(cell, mode, replicate)
        for cell in cells
        for mode in modes
        for replicate in range(1, args.replicates + 1)
    ]
    estimates = {}
    for experiment in experiments:
        prompt, specs = prompts[experiment.cell.agent]
        estimates[experiment.experiment_id] = estimate_experiment(
            experiment,
            prompt,
            tool_definitions(specs),
            load_analysis(experiment.cell),
            args.model,
            args.max_tokens,
            args.input_price_per_million,
            args.output_price_per_million,
        )
    estimate = sum(estimates.values())
    manifest: Dict[str, Any] = {
        "created_utc": now(),
        "dry_run": args.dry_run,
        "source_root": str(root),
        "source_commit": source_commit(root),
        "archives": list(archives),
        "agents": list(agents),
        "modes": list(modes),
        "cell_count": len(cells),
        "experiment_count": len(experiments),
        "model": args.model,
        "temperature": 0,
        "workers": args.workers,
        "max_budget_usd": args.max_budget_usd,
        "pricing_usd_per_million": {
            "input": args.input_price_per_million,
            "output": args.output_price_per_million,
        },
        "estimated_conservative_ceiling_usd": estimate,
        "experiments": [
            {
                "experiment_id": experiment.experiment_id,
                "estimated_ceiling_usd": estimates[experiment.experiment_id],
                "cell": {**asdict(experiment.cell), "analysis_path": str(experiment.cell.analysis_path), "portfolio_path": str(experiment.cell.portfolio_path)},
                "analysis_sha256": sha_file(experiment.cell.analysis_path),
                "portfolio_sha256": sha_file(experiment.cell.portfolio_path),
            }
            for experiment in experiments
        ],
    }
    atomic_json(output / "manifest.json", manifest)
    print(
        json.dumps(
            {
                "output_root": str(output),
                "cells": len(cells),
                "experiments": len(experiments),
                "workers": args.workers,
                "estimated_conservative_ceiling_usd": round(estimate, 6),
                "hard_budget_usd": args.max_budget_usd,
                "dry_run": args.dry_run,
            },
            indent=2,
        )
    )
    if estimate > args.max_budget_usd:
        raise BudgetExceeded(f"estimate ${estimate:.2f} exceeds cap ${args.max_budget_usd:.2f}")
    if args.dry_run:
        return 0

    key = os.environ.get(args.api_key_env, "").strip()
    if not key and args.api_key_file:
        key_path = args.api_key_file.expanduser().resolve()
        permissions = stat.S_IMODE(key_path.stat().st_mode)
        if permissions & 0o077:
            raise ReplayError(
                f"refusing API key file with group/other permissions {permissions:o}: {key_path}"
            )
        key = key_path.read_text(encoding="utf-8").strip()
    if not key:
        raise ReplayError(
            f"live replay requires {args.api_key_env} or --api-key-file; "
            "configure the credential as a Bouchet secret"
        )
    ledger = BudgetLedger(args.max_budget_usd)
    client = OpenRouter(
        key,
        ledger,
        Journal(output / "usage.jsonl"),
        args.input_price_per_million,
        args.output_price_per_million,
        args.request_timeout,
        args.retries,
        args.http_referer,
    )
    manifest["openrouter_key_before"] = client.key_metadata()
    remaining = manifest["openrouter_key_before"].get("limit_remaining")
    if isinstance(remaining, (int, float)) and remaining < estimate:
        raise BudgetExceeded(f"key has ${remaining:.2f}, below ${estimate:.2f} estimate")
    atomic_json(output / "manifest.json", manifest)

    completed: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(args.workers, len(experiments))) as pool:
        futures = {
            pool.submit(
                run_one,
                experiment,
                root,
                output,
                args.model,
                args.max_tokens,
                args.max_tool_rounds,
                client,
                prompts,
                args.overwrite,
            ): experiment
            for experiment in experiments
        }
        for future in as_completed(futures):
            experiment = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "experiment_id": experiment.experiment_id,
                    "archive": experiment.cell.archive,
                    "agent": experiment.cell.agent,
                    "start_date": experiment.cell.start_date,
                    "end_date": experiment.cell.end_date,
                    "mode": experiment.mode,
                    "model": args.model,
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            completed.append(result)
            write_summary(output / "summary.csv", sorted(completed, key=lambda row: row["experiment_id"]))
            print(
                json.dumps(
                    {
                        "completed": len(completed),
                        "total": len(experiments),
                        "experiment_id": experiment.experiment_id,
                        "status": result["status"],
                        "ledger": ledger.snapshot(),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    manifest.update(
        {
            "completed_utc": now(),
            "openrouter_key_after": client.key_metadata(),
            "ledger_final": ledger.snapshot(),
            "successful_experiments": sum(row["status"] == "success" for row in completed),
            "failed_experiments": sum(row["status"] != "success" for row in completed),
        }
    )
    atomic_json(output / "manifest.json", manifest)
    return 0 if all(row["status"] == "success" for row in completed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
