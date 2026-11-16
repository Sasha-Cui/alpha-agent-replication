#!/usr/bin/env python3
"""Attribute unique recorded-response costs without repricing or refunding failures."""
from pathlib import Path
import sys,json,fcntl
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from alpha_evolve.openrouter_budget import atomic_json,sha256
from alpha_evolve.publication_llm import CohortOpenRouter
PRIVATE=ROOT/'artifacts/fidelity_completion_v2';STUDY='fidelity_v2_alphaagent_source_search'

def main():
    out=ROOT/'paper_runs/fidelity_completion_v2/alpha_observed_cost_attribution.json'
    if out.exists():raise ValueError('Preserve completed source-cost attribution')
    jobs=json.loads((PRIVATE/'alpha_observed_history_jobs.json').read_text());catalogue=jobs['source_catalogue']
    if [r['trial'] for r in catalogue['trials']]!=list(range(1,21)):raise ValueError('All20 verified source outcomes required')
    l=ROOT/'runs/economic_fidelity/openrouter'
    with (l/'project_spend.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);raw=(l/'project_spend.json').read_bytes();state=json.loads(raw)
    all_chat=set();all_embedding=set();all_failed=set();rows=[];bindings=[]
    for trial in catalogue['trials']:
        run=PRIVATE/trial['run'];done=json.loads((run/'execution_exit.json').read_text())
        if sha256(run/'execution_exit.json')!=trial['execution_exit_sha256']:raise ValueError('Verified source exit changed')
        chat=json.loads((run/'model_calls.json').read_text());embedding=json.loads((run/'embedding_calls.json').read_text())
        ckeys=[r['request_hash'] for r in chat];ekeys=[r['request_hash'] for r in embedding]
        if len(ckeys)!=len(set(ckeys)) or all_chat.intersection(ckeys):raise ValueError('Chat request reused across planned trial indices; inspect attribution')
        cost=0.0
        for r in chat:
            entry=state['calls'][r['request_hash']]
            if entry['status']!='complete' or entry['study']!=STUDY or entry['response_id']!=r['response_id']:raise ValueError('Returned chat/ledger mismatch')
            cost+=entry['cost_usd']
        for key in ekeys:
            entry=state['calls'][key]
            if entry['status']!='complete' or entry['study']!=STUDY or entry['endpoint']!='embeddings':raise ValueError('Embedding/ledger mismatch')
        failed=[]
        if done['status']!='native_round_budget_exhausted':
            if (run/'constructor_abort_evidence_v3.json').exists():key=json.loads((run/'constructor_abort_evidence_v3.json').read_text())['witness']['key']
            elif (run/'early_abort_evidence.json').exists():key=json.loads((run/'early_abort_evidence.json').read_text())['failed_request_hash']
            else:key=json.loads((run/'terminal_failure_closure.json').read_text())['failed_request_hash']
            entry=state['calls'][key]
            if entry['status']!='reserved' or entry['study']!=STUDY or key in all_failed:raise ValueError('Observed missing-response reservation changed')
            failed=[{'request_hash':key,'retained_reserved_usd':entry['reserved_usd']}];all_failed.add(key)
        all_chat.update(ckeys);all_embedding.update(ekeys)
        rows.append({'trial':trial['trial'],'native_status':done['status'],'attempted_rounds':done['attempted_rounds'],'unattempted_rounds':done.get('unattempted_round_indices',[]),'returned_chat_records':len(chat),'unique_embedding_requests_used':len(set(ekeys)),'returned_chat_response_cost_usd':cost,'failed_response_reservations':failed,'chat_cost_plus_failed_reservations_usd':cost+sum(r['retained_reserved_usd'] for r in failed),'cost_basis':'Canonical historical cost of the recorded chat responses used by this trial, plus its full missing-response reservation. This is not necessarily incremental spending since the five-attempt correction; trial01 reuses its recorded bounded prefix. Embeddings are shared and accounted once below.'})
        bindings.append({'run':trial['run'],'chat_sha256':sha256(run/'model_calls.json'),'embedding_sha256':sha256(run/'embedding_calls.json'),'exit_sha256':sha256(run/'execution_exit.json')})
    chat_cost=sum(state['calls'][k]['cost_usd'] for k in all_chat);embedding_cost=sum(state['calls'][k]['cost_usd'] for k in all_embedding);failed_cost=sum(state['calls'][k]['reserved_usd'] for k in all_failed)
    own=CohortOpenRouter.totals(state,STUDY)[1];total=chat_cost+embedding_cost+failed_cost
    if total>own+1e-9:raise ValueError('Subset attributed costs exceed canonical shared-study commitment')
    import hashlib
    atomic_json(out,{'status':'all20_observed_source_costs_bound_no_ledger_mutation','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'ledger_snapshot_sha256':hashlib.sha256(raw).hexdigest(),'source_catalogue_sha256':sha256(PRIVATE/'alpha_observed_launch_20260918/complete20_source_catalogue_at_submission.json'),'trials':rows,'source_bindings':bindings,'unique_returned_chat_requests':len(all_chat),'unique_embedding_requests_shared_across_trials':len(all_embedding),'returned_chat_cost_usd':chat_cost,'shared_unique_embedding_cost_usd':embedding_cost,'observed_missing_response_reservations_usd':failed_cost,'attributed_unique_response_cost_and_reservations_usd':total,'canonical_shared_alpha_study_commitment_usd':own,'other_original_pilot_or_route_commitment_usd':own-total,'no_refunds_or_repricing':True,'incremental_new_spend_claim':False,'llm_trials_are_independent_market_histories':False,'private_ledger_exposed':False,'source_sha256':sha256(Path(__file__))})
    print('ALL20_COST_ATTRIBUTION',len(all_chat),len(all_embedding),chat_cost,embedding_cost,failed_cost,total,own)
if __name__=='__main__':main()
