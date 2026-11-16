#!/usr/bin/env python3
"""Read-only request preflight for V3 equity accounts and the exact retained Quanta reply."""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import closing
import argparse,fcntl,hashlib,json,math,sqlite3,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import atomic_json,sha256
from fidelity_archive_readiness_v2 import assess_requests,terminal_witnesses
QUANTA_KEY='cd8a6845189771842cfebdf3a361779f49ae31f45fcd494ecac75f0bcaa4cc5a'
QUANTA_STUDY='fidelity_v2_quantaalpha_fresh_search'

def identity(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate_returned_reservation(calls,mapping,witness,sqlite_body,journal_matches,*,sources_closed,fresh):
    if not sources_closed or not fresh:raise ValueError('Actual closures and fresh locked dual-store checks are required')
    if witness['request_hash']!=QUANTA_KEY or witness.get('source_gate_status')!='pass':raise ValueError('No exact completed-source returned-response witness')
    expected=witness['entry'];entry=calls.get(QUANTA_KEY)
    if entry!=expected or expected.get('status')!='reserved' or expected.get('study')!=QUANTA_STUDY or expected.get('pid')!=115150 or expected.get('endpoint')!='chat/completions' or expected.get('model')!='openai/gpt-5.2' or expected.get('reserved_usd')!=0.0556885:raise ValueError('Original returned reservation identity/status/charge changed')
    if QUANTA_KEY in mapping:raise ValueError('Exact returned response has an unexpected recovery mapping')
    if sqlite_body is not None:raise ValueError('Unexpected SQLite response; diagnose changed duplicate-store population')
    if len(journal_matches)!=1:raise ValueError('Missing or duplicate exact returned response in full journal scan')
    offset,line=journal_matches[0];digest=hashlib.sha256(line).hexdigest()
    if witness['journal_matches']!=[{'offset':offset,'sha256':digest}] or digest!=witness['copy_sha256']:raise ValueError('Original durable response bytes/offset changed')
    body=json.loads(line)
    if body.get('request_hash')!=QUANTA_KEY or 'technical_recovery' in body or identity({k:body[k] for k in ['endpoint','request']})!=QUANTA_KEY:raise ValueError('Returned request envelope changed')
    if body['endpoint']!=expected['endpoint'] or body['request'].get('model')!=expected['model'] or body['request'].get('provider')!={'order':['openai'],'allow_fallbacks':False}:raise ValueError('Returned model/provider/endpoint changed')
    response=body['response'];choices=response.get('choices',[])
    if response.get('error') or len(choices)!=1 or not isinstance(choices[0].get('message',{}).get('content'),str):raise ValueError('Preserved response is not a complete usable chat body')
    cost=response.get('usage',{}).get('cost')
    if isinstance(cost,(int,float)) and (not math.isfinite(cost) or cost<0 or cost>expected['reserved_usd']+1e-12):raise ValueError('Reported cost requires separate diagnosis, not silent repricing')
    return {'request_hash':QUANTA_KEY,'classification':'exact_original_durable_response_reused_with_full_reserved_charge_retained','reserved_usd':expected['reserved_usd'],'status_unchanged':'reserved','journal_offset':offset,'journal_sha256':digest,'sqlite_present':False,'fresh_dual_store_check':True,'source_gate_status':'pass','entry_sha256':identity(entry),'reported_cost_is_not_the_conservative_commitment':True}

def assess_snapshot(calls,witnesses,mapping,cache_hits,journal_hits,*,sources_closed,fresh,returned=None):
    projected=dict(calls)
    if returned is not None:
        if not sources_closed or not fresh or returned.get('request_hash')!=QUANTA_KEY or returned.get('classification')!='exact_original_durable_response_reused_with_full_reserved_charge_retained' or returned.get('fresh_dual_store_check') is not True or returned.get('reserved_usd')!=0.0556885 or calls.get(QUANTA_KEY,{}).get('status')!='reserved' or returned.get('source_gate_status')!='pass' or returned.get('entry_sha256')!=identity(calls.get(QUANTA_KEY,{})) or QUANTA_KEY in mapping:raise ValueError('Unverified returned reservation cannot be excluded from unclassified requests')
        del projected[QUANTA_KEY]
    result=assess_requests(projected,witnesses,mapping,cache_hits,journal_hits,sources_closed=sources_closed,fresh_dual_store_check=fresh)
    result['documented_returned_reservations']=[] if returned is None else [returned]
    result['retained_returned_reservation_usd']=0.0 if returned is None else returned['reserved_usd']
    result['classification_projection_only_no_ledger_entry_deleted']=True
    return result
def closure_artifacts(root):
    public=root/'paper_runs/fidelity_completion_v2';rows=[]
    requirements=[('accounts/validation.json','pass'),('quanta_paper_parameter_sensitivity/completion.json','separate_exploratory_parameter_sensitivity_complete_not_primary')]
    for name,status in requirements:
        p=public/name;row={'path':str(p.relative_to(root)),'status':'missing','pass':False}
        if p.exists():
            d=json.loads(p.read_text());valid=d.get('status')==status
            if name.startswith('accounts/'):
                expected={('finmem',x) for x in ['TSLA','NFLX','AMZN','MSFT','COIN']}|{('tradingagents',x) for x in ['AAPL','GOOGL','AMZN']}|{('finagent',x) for x in ['TSLA','AAPL','AMZN','GOOGL','MSFT']}
                valid=valid and not d['missing_runs'] and {(x['case'],x['symbol']) for x in d['completed_runs']}==expected and len(d['completed_runs'])==13
                valid=valid and d['script_sha256']==sha256(root/'scripts/build_fidelity_accounts_v3.py') and d['source_gate_sha256']==sha256(root/'scripts/fidelity_equity_evidence_v3.py')
                hashes=[(p.parent/k,v) for k,v in d['public_outputs'].items()]+[(root/k,v) for k,v in d['private_account_outputs'].items()]
            else:
                valid=valid and not d['primary_replaced'] and d['baseline_models_refitted']==0
                hashes=[(p.parent/k,v) for k,v in d['outputs'].items()]+[(root/k,v) for k,v in d['source_files'].items()]
            valid=valid and all(x.is_file() and sha256(x)==digest for x,digest in hashes)
            row.update(status=d.get('status'),pass_=valid,sha256=sha256(p));row['pass']=row.pop('pass_')
        rows.append(row)
    return rows

def current_source_gates(root):
    from fidelity_equity_evidence_v3 import validate_source
    from quanta_paper_evaluation_evidence_v5 import source_gate
    from quanta_walltime_continuation_v3 import load_scope
    public=root/'paper_runs/fidelity_completion_v2';private=root/'artifacts/fidelity_completion_v2';account=json.loads((public/'accounts/validation.json').read_text());overrides=json.loads((public/'primary_run_overrides.json').read_text())
    if account['primary_run_overrides_sha256']!=sha256(public/'primary_run_overrides.json'):raise ValueError('Final account source selection changed')
    equity=[]
    for row in account['completed_runs']:
        case,symbol=row['case'],row['symbol'];name=case+'_'+symbol;frozen=case=='finmem' and symbol=='TSLA'
        run=root/'artifacts/publication_upgrade_v1/finmem_native' if frozen else private/name
        recipe=root/'paper_runs/publication_upgrade_v1/finmem_recipe.json' if frozen else public/'recipes'/(name+'.json')
        if name in overrides:run=private/overrides[name]['run_directory'];recipe=root/overrides[name]['recipe']
        equity.append(validate_source(root,run,recipe,case,frozen=frozen))
    if len(equity)!=13:raise ValueError('Incomplete final equity admission')
    quanta=source_gate(root,require_causality=True);plan,base,proof=load_scope();orphan=dict(base['orphan'])
    if sha256(root/orphan['copy'])!=orphan['copy_sha256']:raise ValueError('Preserved original returned body changed')
    orphan['source_gate_status']='pass'
    return {'equity':equity,'quanta':quanta},orphan

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Preserve existing readiness attempt')
    root=ROOT;witnesses=terminal_witnesses(root);closures=closure_artifacts(root);closed=all(row['pass'] for row in closures)
    source_gates=None;orphan=None
    if closed:source_gates,orphan=current_source_gates(root)
    ledger=root/'runs/economic_fidelity/openrouter';cache_hits=set();journal_hits=set();fresh=False;returned=None;journal_bytes=None;journal_digest=None
    with (ledger/'project_spend.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);raw=(ledger/'project_spend.json').read_bytes();state=json.loads(raw)
        mapping_path=ledger/'technical_recoveries.json';mapping=json.loads(mapping_path.read_text()) if mapping_path.exists() else {}
        allowed=set(witnesses)|({QUANTA_KEY} if orphan is not None else set())
        unknown=[k for k,v in state['calls'].items() if v['status']=='reserved' and k not in allowed]
        with closing(sqlite3.connect('file:'+str(ledger/'response_cache.sqlite3')+'?mode=ro',uri=True)) as con:
            cache_hits={k for k in witnesses if con.execute('SELECT 1 FROM responses WHERE request_hash=?',(k,)).fetchone()}
            if closed and not unknown:
                with (ledger/'cohort_response_journal.lock').open('a+') as jlock:
                    fcntl.flock(jlock,fcntl.LOCK_EX)
                    matches=[];offset=0;digest=hashlib.sha256();needles=[k.encode() for k in allowed]
                    with (ledger/'cohort_responses.jsonl').open('rb') as stream:
                        for line in stream:
                            digest.update(line)
                            if any(key in line for key in needles):
                                body=json.loads(line);key=body.get('request_hash')
                                if key in witnesses:journal_hits.add(key)
                                if key==QUANTA_KEY:matches.append((offset,line))
                            offset+=len(line)
                    sqlite_row=con.execute('SELECT body FROM responses WHERE request_hash=?',(QUANTA_KEY,)).fetchone()
                    fresh=True;journal_bytes=offset;journal_digest=digest.hexdigest()
                    returned=validate_returned_reservation(state['calls'],mapping,orphan,None if sqlite_row is None else sqlite_row[0],matches,sources_closed=True,fresh=True)
        result=assess_snapshot(state['calls'],witnesses,mapping,cache_hits,journal_hits,sources_closed=closed,fresh=fresh,returned=returned)
        if (ledger/'project_spend.json').read_bytes()!=raw:raise ValueError('Ledger changed under lock')
    result.update(status='read_only_archive_request_preflight_pass' if result['cache_snapshot_request_gate_pass'] else 'read_only_archive_request_preflight_blocked',recorded_at_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha256(Path(__file__)),unchanged_v2_terminal_rules_sha256=sha256(root/'scripts/fidelity_archive_readiness_v2.py'),ledger_snapshot_sha256=hashlib.sha256(raw).hexdigest(),closure_artifacts=closures,current_source_gates=source_gates,terminal_witness_bindings=witnesses,returned_witness=None if orphan is None else {k:orphan[k] for k in ['request_hash','entry','copy_sha256','journal_matches','source_gate_status']},journal_bytes_scanned=journal_bytes,journal_sha256=journal_digest,required_equity_builder='scripts/build_fidelity_accounts_v3.py',required_equity_gate='scripts/fidelity_equity_evidence_v3.py',required_quanta_gate='scripts/quanta_paper_evaluation_evidence_v5.py',AMZN_retry_authorized=False,not_a_final_publication_or_archive_gate='Request classification at a locked instant only. No settlement, refund, API call, archive or final-publication authorization. Final packager must repeat fresh source/closure/witness checks under its own consistent ledger+journal snapshot transaction and independently verify content/privacy/durable copies.')
    atomic_json(args.output,result)
    print(json.dumps({k:result[k] for k in ['status','source_closures_pass','fresh_dual_store_check','retained_terminal_reservation_usd','retained_returned_reservation_usd','unclassified_reserved_count','unclassified_reserved_by_study','ledger_mutations','archive_created']}),flush=True)
if __name__=='__main__':main()
