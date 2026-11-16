"""Discovery-time gating for pooled EFS libraries; no economic data or API calls."""
from __future__ import annotations
import copy
import hashlib


def merge_discoveries(libraries):
    merged = {}
    for trial, library in libraries.items():
        for key, row in library.items():
            if hashlib.sha256(row['code'].encode()).hexdigest() != key:
                raise ValueError('Factor identity mismatch')
            created = row['created_index']
            if not isinstance(created, int) or isinstance(created, bool):
                raise ValueError('Discovery cutoff must be an integer')
            if row['origin'] not in ['paper_seed_family','llm_generated']:
                raise ValueError('Unknown factor origin')
            if row['origin'] == 'llm_generated' and created < 0:
                raise ValueError('Generated factor missing discovery cutoff')
            if key not in merged:
                merged[key] = {**copy.deepcopy(row), 'discoveries': []}
            existing = merged[key]
            if existing['code'] != row['code'] or existing['origin'] != row['origin']:
                raise ValueError('Conflicting factor identity or provenance')
            existing['created_index'] = min(existing['created_index'],created)
            existing['discoveries'].append({'trial':trial,'created_index':created})
    return merged


def eligible_discoveries(library, decision_index, hindsight=False):
    return {key:row for key,row in library.items() if hindsight or row['created_index'] <= decision_index}
