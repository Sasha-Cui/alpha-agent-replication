#!/usr/bin/env python3
"""Read-only interruption diagnosis, including exact returned-but-unsettled bodies."""
from pathlib import Path
import argparse,fcntl,hashlib,importlib.util,json,socket,sys,threading
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import sha256,atomic_json
from alpha_evolve.publication_replay import ReadOnlyReplay
from validate_publication_replay import compare,read
AUDIT=ROOT/'artifacts/fidelity_completion_v2/walltime_interruptions_20260919_0135'
class DiagnosticStop(BaseException):pass

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--symbol',choices=['AAPL','MSFT','TSLA'],required=True);args=parser.parse_args()
    scope=json.loads((AUDIT/'finagent_probe_protocol.json').read_text())
    for row in scope['bindings']:
        if sha256(ROOT/row['path'])!=row['sha256']:raise ValueError('Frozen diagnostic source/input changed: '+row['path'])
    case=scope['cases'][args.symbol];out=ROOT/'artifacts/fidelity_completion_v2'/case['probe_name']
    if out.exists():raise ValueError('Preserve and diagnose existing partial probe; never overwrite')
    diagnosis=json.loads((AUDIT/'orphan_response_diagnosis.json').read_text());orphans={x['request_hash']:x for x in diagnosis['reservations']}
    def deny(*a,**k):raise RuntimeError('Walltime prefix diagnosis network disabled')
    socket.socket.connect=deny;socket.create_connection=deny
    source=ROOT/'scripts/run_finagent_fidelity_v2.py';spec=importlib.util.spec_from_file_location('unchanged_finagent_walltime_probe',source);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    if args.symbol=='TSLA':
        from alpha_evolve.finagent_schema_repair_v2 import install_schema_repair
        install_schema_repair(out)
    out.mkdir(exist_ok=True)
    guard=threading.RLock()
    class Meter(ReadOnlyReplay):
        def cached_response(self,key):
            if key not in orphans:return super().cached_response(key)
            row=orphans[key]
            if self.frozen_state['calls'].get(key)!=row['entry']:raise ValueError('Selected orphan ledger identity changed; inspect before diagnosis')
            path=ROOT/row['copy']
            if sha256(path)!=row['copy_sha256']:raise ValueError('Frozen durable response changed')
            body=json.loads(path.read_text())
            with self.journal.open('rb') as f:f.seek(row['journal_matches'][0]['offset']);line=f.readline()
            if hashlib.sha256(line).hexdigest()!=row['copy_sha256'] or json.loads(line)!=body:raise ValueError('Original durable response changed')
            with guard:
                with (out/'orphan_response_uses.jsonl').open('a') as f:f.write(json.dumps({'request_hash':key,'response_copy_sha256':row['copy_sha256'],'ledger_mutated':False},sort_keys=True)+'\n')
            return body
        def request(self,endpoint,payload,**kwargs):
            try:return super().request(endpoint,payload,**kwargs)
            except RuntimeError as error:
                if not str(error).startswith('Offline response is not complete in the frozen cache: '):raise
                key=str(error).rsplit(' ',1)[-1]
                if key in self.frozen_state['calls']:raise ValueError('Unknown existing unresolved request: '+key) from error
                envelope={'endpoint':endpoint,'request':{**payload,'provider':{'order':[self.provider],'allow_fallbacks':False}}}
                if hashlib.sha256(json.dumps(envelope,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=key:raise ValueError('Unrecognized future request mapping')
                with guard:
                    prefix_rows=[]
                    for row in case['prefixes']:
                        old=read(ROOT/row['path']);target=out/row['target'];new=read(target)
                        if sha256(ROOT/row['path'])!=row['sha256'] or len(old)!=row['records'] or len(new)<len(old):raise ValueError('Original prefix missing or changed')
                        errors,delta=compare(old,new[:len(old)])
                        if errors:raise ValueError('Original prefix differs: '+str(errors[:3]))
                        prefix_rows.append({'kind':row['kind'],'path':row['path'],'sha256':row['sha256'],'records':len(old),'target':str(target.relative_to(ROOT)),'target_sha256':sha256(target),'difference_count':0,'maximum_numeric_difference':delta[0]})
                    future=out/'unattempted_future_envelopes';future.mkdir(exist_ok=True);atomic_json(future/(key+'.json'),envelope)
                    atomic_json(out/'prefix_probe_validation.json',{'status':'all_preserved_prefixes_match_stopped_before_new_request','source_run':case['source_run'],'prefixes':prefix_rows,'network_calls':0,'ledger_mutations':0,'cache_mutations':0,'full_source_completion_claim':False,'future_request_hash':key,'probe_script_sha256':sha256(Path(__file__)),'protocol_sha256':sha256(AUDIT/'finagent_probe_protocol.json'),'orphan_diagnosis_sha256':sha256(AUDIT/'orphan_response_diagnosis.json')})
                raise DiagnosticStop('Verified interrupted prefix; stop before any new request') from error
    driver.WaitingMeter=Meter
    sys.argv=[str(source),'--offline','--output-name',case['probe_name'],'--recipe',str(ROOT/case['recipe_path'])]
    try:driver.main()
    except (DiagnosticStop,RuntimeError) as error:
        if isinstance(error,RuntimeError) and str(error)!="Validation worker failed; others were allowed to finish: {'native_causal': 1}":raise
        proof=out/'prefix_probe_validation.json'
        if not proof.exists() or (out/'completion.json').exists():raise ValueError('Expected bounded read-only prefix stop not certified') from error
        data=json.loads(proof.read_text());data['probe_status']='pass_expected_stop_not_full_source_replay'
        uses=out/'orphan_response_uses.jsonl';data['orphan_response_uses_sha256']=sha256(uses) if uses.exists() else None
        data['distinct_orphan_responses_used']=len(set(json.loads(x)['request_hash'] for x in uses.read_text().splitlines())) if uses.exists() else 0
        atomic_json(proof,data);print('WALLTIME_PREFIX_PROBE_PASS',args.symbol,data['distinct_orphan_responses_used'],flush=True)
    else:raise ValueError('Unexpected complete driver return; inspect instead of certifying partial diagnosis')
if __name__=='__main__':main()
