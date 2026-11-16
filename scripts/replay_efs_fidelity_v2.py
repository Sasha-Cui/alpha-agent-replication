#!/usr/bin/env python3
# ruff: noqa: E402 - standalone bootstrap
"""Strict read-only full trajectory replay for additional EFS searches."""
from pathlib import Path
import sys
import json
import argparse
import importlib.util
import os
import fcntl
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from alpha_evolve.publication_replay import ReadOnlyReplay
from alpha_evolve.fidelity_transport_v2 import retry_stale_read
from alpha_evolve.openrouter_budget import sha256, atomic_json
from validate_publication_replay import compare


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trial', required=True)
    args = parser.parse_args()
    public = ROOT/'paper_runs/fidelity_completion_v2/efs'/args.trial
    private = ROOT/'artifacts/fidelity_completion_v2/efs'/args.trial
    reference = json.loads((public/'llm_manifest.json').read_text())
    if reference['status'] != 'complete':
        raise ValueError('Source trajectory incomplete')
    destination = private/'offline_replay'
    output = destination/'results'
    data = destination/'private'
    if (destination/'validation.json').exists():
        raise ValueError('Replay already validated; preserve evidence')
    output.mkdir(parents=True,exist_ok=True)
    data.mkdir(exist_ok=True)
    for source,target in [(public/'recipe.json',output/'recipe.json'),(public/'system_prompt.txt',output/'system_prompt.txt'),(private/'efs_us50_daily.parquet',data/'efs_us50_daily.parquet'),(private/'data_manifest.json',data/'data_manifest.json')]:
        if not target.exists():
            os.link(source,target)
        if sha256(source) != sha256(target):
            raise ValueError('Replay input mismatch')
    recipe = json.loads((output/'recipe.json').read_text())
    if recipe['historical_usage_journals']:
        raise ValueError('V2 replay must never reimport usage')
    spec = importlib.util.spec_from_file_location('frozen_efs_replay', ROOT/'scripts/run_efs_economic_fidelity.py')
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    driver.OUT,driver.PRIVATE = output,data
    driver.read_key = lambda _path:'unused-read-only'
    class Adapter:
        def __init__(self, root, key, model, **kwargs):
            def initialize():
                with (Path(root)/'project_spend.lock').open('a+') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX)
                    return ReadOnlyReplay(root,key,model,study='fidelity_v2_efs_trials',study_cap=35,provider=recipe['provider_name'],input_price=recipe['input_usd_per_million'],output_price=recipe['output_usd_per_million'])
            self.meter = retry_stale_read(initialize)
        def complete(self,messages,**kwargs):
            return self.meter.chat(messages,seed=recipe['api_seed'],**kwargs)
        def snapshot(self):
            return self.meter.snapshot()
    driver.MeteredOpenRouter = Adapter
    driver.run(SimpleNamespace(mode='llm',key_env_file=None))
    matched = {}
    for name,expected in reference['output_sha256'].items():
        actual = sha256(output/name)
        if sha256(public/name) != expected or actual != expected:
            raise ValueError('Nonidentical replay: '+name)
        matched[name] = actual
    if sha256(data/'llm_daily_weights.parquet') != reference['private_weights_sha256']:
        raise ValueError('Replay holdings differ')
    recovery_prefixes = []
    current_proposals = json.loads((public/'llm_proposals.json').read_text())
    for recovery_path in sorted((ROOT/'artifacts/fidelity_completion_v2').glob('transport_recovery*/recovery.json')):
        recovery = json.loads(recovery_path.read_text())
        for row in recovery['runs']:
            if row['name'] != 'efs_' + args.trial:
                continue
            path = recovery_path.parent / row['name'] / 'artifacts/fidelity_completion_v2/efs' / args.trial / 'proposals_live.json'
            if not path.exists():
                raise ValueError('Missing preserved EFS proposal history')
            prefix = json.loads(path.read_text())
            errors, maximum = compare(prefix, current_proposals[:len(prefix)])
            proof = {'status':'fail' if errors else 'pass','records':len(prefix),'maximum_numeric_difference':maximum[0],'differences':errors[:50],'preserved_sha256':sha256(path),'recovery_manifest_sha256':sha256(recovery_path)}
            recovery_prefixes.append(proof)
            if errors:
                raise ValueError('EFS transport resume changed completed proposal history')
    atomic_json(private/'transport_prefix_validation.json', recovery_prefixes)
    atomic_json(destination/'validation.json',{'status':'pass','trial':args.trial,'network_calls':0,'ledger_mutations':0,'exact_output_hashes':matched,'holdings_byte_identical':True,'transport_prefix_validation':recovery_prefixes,'script_sha256':sha256(Path(__file__))})
    print('FULL_EFS_REPLAY_PASS',args.trial)


if __name__ == '__main__':
    main()
