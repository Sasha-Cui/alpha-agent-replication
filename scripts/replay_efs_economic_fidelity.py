#!/usr/bin/env python3
"""Replay the complete EFS pilot from cached responses, with paid calls disabled."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'paper_runs/economic_fidelity/efs_v1'
PRIVATE = ROOT / 'artifacts/economic_fidelity/v1'
METER = ROOT / 'runs/economic_fidelity/openrouter'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['llm', 'initial'], default='llm')
    parser.add_argument('--destination', type=Path, default=PRIVATE/'network_disabled_replay')
    args = parser.parse_args()
    reference = json.loads((SOURCE/f'{args.mode}_manifest.json').read_text())
    if reference['status'] != 'complete':
        raise ValueError('reference run is incomplete')
    destination = args.destination.resolve()
    if destination == SOURCE.resolve() or destination == PRIVATE.resolve():
        raise ValueError('replay must not overwrite reference artifacts')
    for subdir in ['results', 'private', 'meter']:
        (destination/subdir).mkdir(parents=True, exist_ok=True)
    for name in ['recipe.json', 'system_prompt.txt']:
        shutil.copyfile(SOURCE/name, destination/'results'/name)
    for name in ['efs_us50_daily.parquet', 'data_manifest.json']:
        shutil.copyfile(PRIVATE/name, destination/'private'/name)
    before = json.loads((METER/'project_spend.json').read_text())
    for name in ['project_spend.json', 'response_cache.sqlite3']:
        shutil.copyfile(METER/name, destination/'meter'/name)
    spec = importlib.util.spec_from_file_location('efs_offline_runner', ROOT/'scripts/run_efs_economic_fidelity.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_meter = module.MeteredOpenRouter

    class OfflineMeter(original_meter):
        def __init__(self, _root, *arguments, **options):
            options['transport'] = self.forbid_network
            super().__init__(destination/'meter', *arguments, **options)

        @staticmethod
        def forbid_network(_request):
            raise RuntimeError('Uncached request: offline replay cannot call the API')

    module.MeteredOpenRouter = OfflineMeter
    module.read_key = lambda _path: 'offline-placeholder-never-sent'
    module.OUT = destination/'results'
    module.PRIVATE = destination/'private'
    module.run(argparse.Namespace(mode=args.mode, key_env_file=None))
    if before != json.loads((METER/'project_spend.json').read_text()):
        raise ValueError('authoritative accounting changed during replay')
    if before != json.loads((destination/'meter/project_spend.json').read_text()):
        raise ValueError('replay attempted a new request or changed accounting')
    matches = {}
    for suffix in ['daily_returns.csv', 'monthly_returns.csv', 'metrics.csv', 'decisions.csv',
                   'factor_library.json', 'proposals.json', 'llm_trace.json']:
        name = args.mode+'_'+suffix
        actual = digest(destination/'results'/name)
        if digest(SOURCE/name) != actual:
            raise ValueError('non-identical replay: '+name)
        matches[name] = actual
    if digest(PRIVATE/f'{args.mode}_daily_weights.parquet') != digest(destination/'private'/f'{args.mode}_daily_weights.parquet'):
        raise ValueError('replay holdings differ')
    result = {'status': 'pass', 'mode': args.mode, 'network_calls': 0,
              'authoritative_ledger_unchanged': True, 'exact_output_hashes': matches,
              'holdings_byte_identical': True}
    (SOURCE/f'validation_canonical_replay_{args.mode}.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Canonical network-disabled replay passed; no additional API charges')


if __name__ == '__main__':
    main()
