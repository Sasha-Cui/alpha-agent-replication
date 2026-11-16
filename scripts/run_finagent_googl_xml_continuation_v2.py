#!/usr/bin/env python3
"""Guarded GOOGL continuation and full socket-blocked replay; no generic parser edit."""
from pathlib import Path
import argparse,importlib.util,json,socket,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import sha256,atomic_json
from alpha_evolve.publication_replay import ReadOnlyReplay
from finagent_googl_xml_alias_v2 import install
from finagent_googl_xml_continuation_evidence_v2 import load_scope,make_gated_meter,receipt,PRIVATE,PROTOCOL,REPAIR,REPLAY,MARKER
from validate_publication_replay import compare,read

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--replay',action='store_true');args=parser.parse_args()
    scope,witness,probe=load_scope();name=REPLAY if args.replay else REPAIR;out=ROOT/PRIVATE/name
    if out.exists():raise ValueError('Existing continuation or replay output must be preserved/diagnosed, never overwritten')
    source=ROOT/PRIVATE/REPAIR
    if args.replay:
        saved=json.loads((source/'xml_completion_validation.json').read_text())
        if saved!=receipt(source,scope,witness,offline=False):raise ValueError('Complete live source is not verified')
        def deny(*a,**k):raise RuntimeError('Full GOOGL replay networking disabled')
        socket.socket.connect=deny;socket.create_connection=deny
    driver_path=ROOT/'scripts/run_finagent_fidelity_v2.py'
    spec=importlib.util.spec_from_file_location('unchanged_finagent_xml_continuation_driver',driver_path);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    install(driver,out,witness)
    driver.WaitingMeter=ReadOnlyReplay if args.replay else make_gated_meter(driver.WaitingMeter,out,scope,witness,probe)
    out.mkdir()
    atomic_json(out/'wrapper.json',{'xml_format_adaptation':MARKER,'protocol_sha256':sha256(ROOT/PROTOCOL),'wrapper_sha256':sha256(Path(__file__)),'adapter_sha256':sha256(ROOT/'scripts/finagent_googl_xml_alias_v2.py'),'evidence_sha256':sha256(ROOT/'scripts/finagent_googl_xml_continuation_evidence_v2.py'),'original_failed_source':witness['source_run'],'offline':args.replay,'scope':'Only exact cached response markup normalized; full words, strategy, inputs, native source and original failure preserved.'})
    sys.argv=[str(driver_path),'--output-name',name,'--recipe',str(ROOT/witness['recipe_path'])]+(['--offline'] if args.replay else [])
    driver.main()
    result=receipt(out,scope,witness,offline=args.replay);atomic_json(out/'xml_completion_validation.json',result)
    if args.replay:
        original_path=source/'decisions.jsonl';target=out/'decisions.jsonl'
        original,other=read(original_path),read(target);errors,delta=compare(original,other)
        proof={'status':'fail' if errors else 'pass','case':'FinAgent','original':REPAIR,'replay':REPLAY,'records':len(original),'replay_records':len(other),'difference_count':len(errors),'differences':errors[:50],'maximum_numeric_difference':delta[0],'original_sha256':sha256(original_path),'replay_sha256':sha256(target),'recipe_sha256':witness['recipe_sha256'],'original_script_sha256':witness['original_driver_sha256'],'replayed_script_sha256':sha256(driver_path),'replay_wrapper_sha256':sha256(Path(__file__)),'network_allowed':False,'ledger_mutations_allowed':False,'xml_format_adaptation':MARKER,'xml_source_receipt_sha256':sha256(source/'xml_completion_validation.json'),'xml_replay_receipt_sha256':sha256(out/'xml_completion_validation.json'),'ignored':'Only cached flags and independent transport ordering; all request identities/economics/reasoning/memory preserved.'}
        atomic_json(ROOT/PRIVATE/(REPAIR+'_full_replay_validation.json'),proof)
        if errors:raise ValueError('Full repaired source replay differs')
    print('GOOGL_XML_STAGE_COMPLETE',name,result['records'],flush=True)
if __name__=='__main__':main()
