#!/usr/bin/env python3
"""Settle only seven proven terminal responses, retaining every reserved dollar."""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import closing,ExitStack
import argparse,copy,fcntl,hashlib,json,os,sqlite3,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import sha256
from alpha_evolve.publication_llm import CohortOpenRouter
from finagent_walltime_evidence_v2 import load_scope,conservative_completed_entry,PRIVATE,AUDIT,PROTOCOL

def durable_json(path,value):
    data=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode();temp=path.with_suffix(path.suffix+'.settlement-tmp')
    with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    out=ROOT/AUDIT;scope=load_scope();ledger=ROOT/'runs/economic_fidelity/openrouter';selected=scope['settlements'];assert len(selected)==7
    if (out/'settlement_receipt.json').exists() or (out/'settlement_attempt.json').exists():raise ValueError('Existing settlement/attempt: inspect it and the ledger; never rerun blindly')
    source_ids=['26502484','26502486','26502488'];probe_ids=['26687106_0','26687106_1','26687106_2']
    scheduler=subprocess.check_output(['/opt/slurm/current/bin/sacct','-n','-X','-j',','.join(source_ids+probe_ids),'-o','JobID,State,ExitCode','-P'],text=True)
    states={x.split('|')[0]:x.split('|')[1:] for x in scheduler.splitlines() if x}
    if any(states.get(j)!=['TIMEOUT','0:0'] for j in source_ids) or any(states.get(j)!=['COMPLETED','0:0'] for j in probe_ids):raise ValueError('Own source/probe terminal identity changed')
    with ExitStack() as stack:
        for name in ['finagent_AAPL','finagent_MSFT','finagent_TSLA_schema_repair']:
            f=stack.enter_context((ROOT/PRIVATE/(name+'.lock')).open('a+'));fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        lock=stack.enter_context((ledger/'project_spend.lock').open('a+'));fcntl.flock(lock,fcntl.LOCK_EX)
        jlock=stack.enter_context((ledger/'cohort_response_journal.lock').open('a+'));fcntl.flock(jlock,fcntl.LOCK_EX)
        before_bytes=(ledger/'project_spend.json').read_bytes();state=json.loads(before_bytes);candidate=copy.deepcopy(state)
        mapping=json.loads((ledger/'technical_recoveries.json').read_text()) if (ledger/'technical_recoveries.json').exists() else {}
        if any(k in mapping for k in selected):raise ValueError('Unexpected retry mapping')
        for key,row in selected.items():
            if state['calls'].get(key)!=row['entry']:raise ValueError('Owner/status/model/study/charge changed: '+key)
        with closing(sqlite3.connect('file:'+str(ledger/'response_cache.sqlite3')+'?mode=ro',uri=True)) as con:
            if any(con.execute('SELECT body FROM responses WHERE request_hash=?',(k,)).fetchone() is not None for k in selected):raise ValueError('Unexpected SQLite response; diagnose duplicate before settlement')
        hits={k:[] for k in selected};needles={k:k.encode() for k in selected};journal_hash=hashlib.sha256();offset=0
        with (ledger/'cohort_responses.jsonl').open('rb') as f:
            for line in f:
                journal_hash.update(line)
                for key,needle in needles.items():
                    if needle in line:
                        body=json.loads(line)
                        if body.get('request_hash')==key:hits[key].append((offset,hashlib.sha256(line).hexdigest(),body))
                offset+=len(line)
        entries={}
        for key,row in selected.items():
            if len(hits[key])!=1:raise ValueError('Missing or duplicate durable response')
            position,digest,body=hits[key][0]
            if row['journal_matches']!=[{'offset':position,'sha256':digest}] or digest!=row['copy_sha256'] or sha256(ROOT/row['copy'])!=digest or body!=json.loads((ROOT/row['copy']).read_text()):raise ValueError('Durable response binding changed')
            after=conservative_completed_entry(row['entry'],body,position,digest);candidate['calls'][key]=after;entries[key]={'before':row['entry'],'after':after}
        project,finagent=CohortOpenRouter.totals(state,'fidelity_v2_finagent_source_settings');project_after,finagent_after=CohortOpenRouter.totals(candidate,'fidelity_v2_finagent_source_settings')
        if project>=450 or finagent>=160:raise ValueError('Budget stop; inspect before continuation')
        if (project,finagent)!=(project_after,finagent_after):raise ValueError('Conservative settlement changed project/study commitments')
        stripped_before=copy.deepcopy(state);stripped_after=copy.deepcopy(candidate)
        for key in selected:del stripped_before['calls'][key];del stripped_after['calls'][key]
        if stripped_before!=stripped_after:raise ValueError('Unrelated ledger content changed')
        receipt={'status':'seven_exact_durable_responses_settled_full_commitment_retained' if args.apply else 'dry_run_exact_seven_proposed_no_mutation','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha256(ROOT/PROTOCOL),'settler_sha256':sha256(Path(__file__)),'scheduler':scheduler,'entries':entries,'project_commitment_before':project,'project_commitment_after':project_after,'finagent_commitment_before':finagent,'finagent_commitment_after':finagent_after,'retained_seven_commitment_usd':sum(x['entry']['reserved_usd'] for x in selected.values()),'before_ledger_sha256':hashlib.sha256(before_bytes).hexdigest(),'journal_bytes_scanned':offset,'journal_sha256':journal_hash.hexdigest(),'network_calls':0,'cache_or_journal_mutations':0,'recovery_map_mutations':0,'other_entries_changed':0,'ledger_entries_changed':7 if args.apply else 0,'scope':'Exact existing responses become readable through the canonical journal index. Full original reserved commitments remain charged, explicitly conservative rather than provider-reported billing. AMZN, Quanta and Alpha entries unchanged.'}
        if not args.apply:
            if (out/'planned_settlement.json').exists():raise ValueError('Preserve previous dry run before another attempt')
            durable_json(out/'planned_settlement.json',receipt)
        else:
            if not (out/'planned_settlement.json').exists():raise ValueError('Concrete dry-run review required before applying')
            plan=json.loads((out/'planned_settlement.json').read_text())
            if plan['entries']!=entries or plan['protocol_sha256']!=receipt['protocol_sha256']:raise ValueError('Reviewed settlement plan changed')
            durable_json(out/'settlement_attempt.json',receipt)
            durable_json(ledger/'project_spend.json',candidate)
            if json.loads((ledger/'project_spend.json').read_text())!=candidate:raise ValueError('Ledger post-write mismatch; inspect saved attempt, do not retry')
            receipt['after_ledger_sha256']=sha256(ledger/'project_spend.json');durable_json(out/'settlement_receipt.json',receipt)
        print(json.dumps({k:receipt[k] for k in ['status','ledger_entries_changed','retained_seven_commitment_usd','project_commitment_after','finagent_commitment_after']}),flush=True)
if __name__=='__main__':main()
