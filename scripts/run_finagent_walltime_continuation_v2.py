#!/usr/bin/env python3
"""Reconstruct each interrupted prefix read-only, then continue ordinary future calls."""
from pathlib import Path
import argparse,importlib.util,json,socket,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import sha256,atomic_json
from alpha_evolve.publication_replay import ReadOnlyReplay
from finagent_walltime_evidence_v2 import load_scope,gated_meter,completion_receipt,PRIVATE,PROTOCOL,AUDIT,MARKER
from validate_publication_replay import compare,read

def main():
    p=argparse.ArgumentParser();p.add_argument('--symbol',choices=['AAPL','MSFT','TSLA'],required=True);p.add_argument('--replay',action='store_true');args=p.parse_args()
    scope=load_scope(require_settlement=True);case=scope['cases'][args.symbol];name=case['replay_name'] if args.replay else case['continuation_name'];out=ROOT/PRIVATE/name;source=ROOT/PRIVATE/case['continuation_name']
    if out.exists():raise ValueError('Preserve/diagnose existing continuation or replay output; never overwrite')
    if args.replay:
        if json.loads((source/'walltime_completion_validation.json').read_text())!=completion_receipt(source,case,scope,offline=False):raise ValueError('Verified complete source required')
        def deny(*a,**k):raise RuntimeError('Full walltime replay networking disabled')
        socket.socket.connect=deny;socket.create_connection=deny
    driver_path=ROOT/'scripts/run_finagent_fidelity_v2.py';spec=importlib.util.spec_from_file_location('unchanged_finagent_walltime_driver',driver_path);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    if args.symbol=='TSLA':
        from alpha_evolve.finagent_schema_repair_v2 import install_schema_repair
        install_schema_repair(out)
    out.mkdir(exist_ok=True)
    atomic_json(out/'wrapper.json',{'walltime_continuation':MARKER,'source_run':case['source_run'],'protocol_sha256':sha256(ROOT/PROTOCOL),'wrapper_sha256':sha256(Path(__file__)),'settlement_receipt_sha256':sha256(ROOT/AUDIT/'settlement_receipt.json'),'offline':args.replay,'TSLA_schema_alias_only':args.symbol=='TSLA'})
    driver.WaitingMeter=ReadOnlyReplay if args.replay else gated_meter(driver.WaitingMeter,out,case,scope)
    sys.argv=[str(driver_path),'--output-name',name,'--recipe',str(ROOT/case['recipe_path'])]+(['--offline'] if args.replay else [])
    driver.main();receipt=completion_receipt(out,case,scope,offline=args.replay);atomic_json(out/'walltime_completion_validation.json',receipt)
    if args.replay:
        a=source/'decisions.jsonl';b=out/'decisions.jsonl';original,other=read(a),read(b);errors,delta=compare(original,other)
        proof={'status':'fail' if errors else 'pass','case':'FinAgent','original':case['continuation_name'],'replay':case['replay_name'],'records':len(original),'replay_records':len(other),'difference_count':len(errors),'differences':errors[:50],'maximum_numeric_difference':delta[0],'original_sha256':sha256(a),'replay_sha256':sha256(b),'recipe_sha256':case['recipe_sha256'],'original_script_sha256':scope['driver_sha256'],'replayed_script_sha256':sha256(driver_path),'replay_wrapper_sha256':sha256(Path(__file__)),'network_allowed':False,'ledger_mutations_allowed':False,'walltime_continuation':MARKER,'source_walltime_receipt_sha256':sha256(source/'walltime_completion_validation.json'),'replay_walltime_receipt_sha256':sha256(out/'walltime_completion_validation.json')}
        atomic_json(ROOT/PRIVATE/(case['continuation_name']+'_full_replay_validation.json'),proof)
        if errors:raise ValueError('Full source replay differs')
    print('WALLTIME_STAGE_COMPLETE',name,397,flush=True)
if __name__=='__main__':main()
