"""Durable, cached OpenRouter calls with project-wide spend accounting.

A failed/ambiguous request remains charged at its reservation bound. It is not
silently retried. Credentials never enter the journal, cache, or command line.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import urllib.request


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    os.replace(temp, path)


def read_key(env_file: Path | None = None) -> str:
    key = os.environ.get('OPENROUTER_API_KEY', '').strip()
    if not key and env_file:
        for line in env_file.read_text().splitlines():
            match = re.match(r'^\s*(?:export\s+)?OPENROUTER_API_KEY\s*=\s*(.*?)\s*$', line)
            if match:
                key = match.group(1).strip().strip('\"\'')
                break
    if not key:
        raise ValueError('OPENROUTER_API_KEY is unavailable')
    return key


class MeteredOpenRouter:
    def __init__(self, root: Path, key: str, model: str, *, study: str,
                 study_cap: float = 25.0, project_cap: float = 450.0,
                 input_price: float = 2.0, output_price: float = 8.0,
                 transport=None):
        if not 0 < study_cap <= project_cap <= 450.0:
            raise ValueError('invalid spend caps')
        self.root, self.key, self.model = root, key, model
        self.study, self.study_cap, self.project_cap = study, study_cap, project_cap
        self.input_price, self.output_price = input_price, output_price
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger_path = root / 'project_spend.json'
        self.cache = root / 'response_cache.sqlite3'
        with sqlite3.connect(self.cache) as connection:
            connection.execute('PRAGMA journal_mode=PERSIST')
            connection.execute('CREATE TABLE IF NOT EXISTS responses (request_hash TEXT PRIMARY KEY, body TEXT NOT NULL)')
        self.transport = transport or self._request

    @contextmanager
    def ledger(self):
        with (self.root / 'project_spend.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = json.loads(self.ledger_path.read_text()) if self.ledger_path.exists() else {'version': 1, 'imports': {}, 'calls': {}}
            try:
                yield state
            finally:
                atomic_json(self.ledger_path, state)
                fcntl.flock(lock, fcntl.LOCK_UN)

    def import_usage(self, path: Path) -> None:
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        by_id = {}
        for row in rows:
            key = row.get('response_id')
            if not key:
                raise ValueError('historical usage requires response IDs')
            value = float(row['cost_usd'])
            if key in by_id and by_id[key] != value:
                raise ValueError('conflicting historical response cost')
            by_id[key] = value
        with self.ledger() as state:
            state['imports'][str(path.resolve())] = {'sha256': sha256(path), 'responses': by_id}

    @staticmethod
    def totals(state: dict, study: str) -> tuple[float, float]:
        historical = {}
        for source in state['imports'].values():
            for key, cost in source['responses'].items():
                if key in historical and historical[key] != cost:
                    raise ValueError('conflicting import')
                historical[key] = cost
        project = sum(historical.values())
        own = 0.0
        for call in state['calls'].values():
            cost = call['cost_usd'] if call['status'] == 'complete' else call['reserved_usd']
            project += cost
            if call['study'] == study:
                own += cost
        return project, own

    def snapshot(self) -> dict:
        with self.ledger() as state:
            project, own = self.totals(state, self.study)
            return {'project_committed_usd': project, 'study_committed_usd': own,
                    'project_soft_cap_usd': self.project_cap, 'study_cap_usd': self.study_cap,
                    'complete_calls': sum(c['status'] == 'complete' and c['study'] == self.study for c in state['calls'].values()),
                    'uncertain_calls': sum(c['status'] != 'complete' and c['study'] == self.study for c in state['calls'].values())}

    def cached_response(self, request_hash: str) -> dict:
        with sqlite3.connect(self.cache) as connection:
            row = connection.execute('SELECT body FROM responses WHERE request_hash=?', (request_hash,)).fetchone()
        if row is None:
            raise ValueError('paid response missing from durable cache')
        return json.loads(row[0])

    def save_response(self, request_hash: str, request: dict, response: dict) -> None:
        body = json.dumps({'request': request, 'response': response}, sort_keys=True)
        with sqlite3.connect(self.cache) as connection:
            connection.execute('PRAGMA journal_mode=PERSIST')
            connection.execute('PRAGMA synchronous=FULL')
            connection.execute('INSERT INTO responses VALUES (?, ?)', (request_hash, body))

    def _request(self, payload: dict) -> dict:
        request = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
            data=json.dumps(payload).encode(), method='POST', headers={
                'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json',
                'X-OpenRouter-Title': 'Alpha Agent Replication economic fidelity'})
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read())

    def complete(self, messages: list[dict], *, max_tokens: int = 2048,
                 temperature: float = 0.3, seed: int = 20260907) -> tuple[dict, str]:
        payload = {'model': self.model, 'messages': messages, 'max_tokens': max_tokens,
                   'temperature': temperature, 'seed': seed,
                   'provider': {'order': ['OpenAI'], 'allow_fallbacks': False}}
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
        key = hashlib.sha256(encoded).hexdigest()
        # One token per UTF-8 byte is a conservative input bound for this text-only request.
        reserved = (len(encoded) * self.input_price + max_tokens * self.output_price) / 1e6
        if not math.isfinite(reserved) or reserved <= 0:
            raise ValueError('invalid reservation')
        with self.ledger() as state:
            if key in state['calls']:
                call = state['calls'][key]
                if call['status'] != 'complete':
                    raise RuntimeError('ambiguous prior call; reconcile before retrying ' + key)
                cached = self.cached_response(key)
                if hashlib.sha256(json.dumps(cached['request'], sort_keys=True, separators=(',', ':')).encode()).hexdigest() != key:
                    raise ValueError('cache request mismatch')
                return cached['response'], key
            project, own = self.totals(state, self.study)
            if project + reserved >= self.project_cap or own + reserved >= self.study_cap:
                raise RuntimeError('OpenRouter budget exhausted before request')
            state['calls'][key] = {'status': 'reserved', 'study': self.study, 'model': self.model,
                'reserved_usd': reserved, 'created_utc': datetime.now(timezone.utc).isoformat()}
        # Deliberately no automatic network retries: timeouts can still be billed.
        response = self.transport(payload)
        if response.get('error') or not response.get('choices'):
            raise RuntimeError('OpenRouter returned no completion; reservation retained')
        usage = response.get('usage', {})
        cost = usage.get('cost')
        if not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
            raise RuntimeError('OpenRouter omitted valid cost; reservation retained')
        self.save_response(key, payload, response)
        with self.ledger() as state:
            state['calls'][key].update(status='complete', cost_usd=cost,
                response_id=response.get('id'), response_model=response.get('model'),
                provider=response.get('provider'), usage=usage)
        if cost > reserved + 1e-9:
            raise RuntimeError('Actual cost exceeded reservation; stop and review prices')
        return response, key
