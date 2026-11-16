#!/usr/bin/env python3
"""Read-only v2 cache-snapshot preflight; no archive, retry or ledger mutation."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from contextlib import closing
import argparse,fcntl,json,math,sqlite3,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import sha256,atomic_json
STUDY='fidelity_v2_alphaagent_source_search'


def assess_requests(calls,witnesses,recovery_map,cache_hits,journal_hits,*,sources_closed,fresh_dual_store_check):
    """Pure decision. A reservation is never classified terminal from age alone."""
    if not witnesses:raise ValueError('Explicit verified terminal evidence required')
    retained=[]
    for key,witness in witnesses.items():
        expected=witness['expected_entry'];entry=calls.get(key)
        if expected.get('status')!='reserved' or not math.isfinite(expected.get('reserved_usd',float('nan'))) or expected['reserved_usd']<=0:
            raise ValueError('Invalid retained reservation witness')
        if entry!=expected:raise ValueError('Witnessed reservation identity/status/charge changed')
        if key in recovery_map:raise ValueError('Retained terminal failure has an unexpected retry mapping')
        if key in cache_hits or key in journal_hits:raise ValueError('A response exists; retained-failure witness needs diagnosis, never silent reconciliation')
        retained.append({'request_hash':key,'trial':witness['trial'],'reserved_usd':entry['reserved_usd'],'classification':'documented_terminal_charge_retained_unchanged'})
    unknown=[v for k,v in calls.items() if v.get('status')=='reserved' and k not in witnesses]
    unsupported=Counter(str(v.get('status')) for v in calls.values() if v.get('status') not in {'reserved','complete','response_unavailable'})
    reasons=[]
    if unsupported:reasons.append('Unsupported request statuses require explicit diagnosis')
    if not sources_closed:reasons.append('Required final equity/Quanta source-and-analysis closures are absent or invalid')
    if unknown:reasons.append('Other reservations remain unclassified; they may be live or need separate evidence')
    if not fresh_dual_store_check:reasons.append('Fresh locked dual-response-store absence check is required before a cache snapshot')
    return {'cache_snapshot_request_gate_pass':not reasons,'blockers':reasons,'unsupported_request_statuses':dict(unsupported),'documented_terminal_reservations':retained,'retained_terminal_reservation_usd':math.fsum(x['reserved_usd'] for x in retained),'unclassified_reserved_count':len(unknown),'unclassified_reserved_by_study':dict(sorted(Counter(x['study'] for x in unknown).items())),'unclassified_reserved_usd':math.fsum(x['reserved_usd'] for x in unknown),'source_closures_pass':sources_closed,'fresh_dual_store_check':fresh_dual_store_check,'ledger_mutations':0,'refunds':0,'retry_authorizations':0,'archive_created':False,'final_publication_ready_claim':False}


def terminal_witnesses(root):
    from alpha_constructor_abort_v3 import validate_five,validate_early
    from alpha_observed_history_evidence_v2 import require_additional_witness
    private=root/'artifacts/fidelity_completion_v2';public=root/'paper_runs/fidelity_completion_v2'
    cost_path=public/'alpha_observed_cost_attribution.json';cost=json.loads(cost_path.read_text())
    if cost['status']!='all20_observed_source_costs_bound_no_ledger_mutation':raise ValueError('Completed original cost audit required')
    if sha256(private/'alpha_observed_launch_20260918/complete20_source_catalogue_at_submission.json')!=cost['source_catalogue_sha256']:raise ValueError('Original source catalogue changed')
    completed=json.loads((public/'alpha_observed_history_sensitivity/completion.json').read_text())
    if completed['status']!='exploratory_observed_history_sensitivity_complete_not_primary':raise ValueError('Observed source population is not closed')
    witnesses={}
    for trial in [8,12,14,15]:
        run=private/('alphaagent_rounds_paper_gpt35_%02d'%trial)
        done=(validate_early if trial in [12,14] else validate_five)(run,root=root,require_replay=True)
        if trial in [14,15]:require_additional_witness(root,trial,run)
        folder=private/('alpha_trial08_failure_20260918' if trial==8 else 'alpha_trial12_early_abort_20260918' if trial==12 else 'alpha_constructor_abort_v3_20260918/trial'+str(trial))
        diagnosis_path=folder/'diagnosis.json';diagnosis=json.loads(diagnosis_path.read_text())
        key=diagnosis['failed_request_hash'];entry=diagnosis['failed_reservation']
        if entry['study']!=STUDY or entry['endpoint']!='chat/completions':raise ValueError('Wrong source reservation scope')
        record=next(x for x in cost['trials'] if x['trial']==trial)
        if record['failed_response_reservations']!=[{'request_hash':key,'retained_reserved_usd':entry['reserved_usd']}]:raise ValueError('Retained charge differs from original source-cost audit')
        binding=next(x for x in cost['source_bindings'] if x['run']==run.name)
        for name,field in [('model_calls.json','chat_sha256'),('embedding_calls.json','embedding_sha256'),('execution_exit.json','exit_sha256')]:
            if sha256(run/name)!=binding[field]:raise ValueError('Original recorded-response cost binding changed')
        if trial==8:
            absence=json.loads((folder/'response_absence.json').read_text())
            if absence['request_hash']!=key or absence['sqlite_matching_rows'] or absence['journal_matching_envelopes']:raise ValueError('Original response-absence witness failed')
        elif trial==12:
            if diagnosis['sqlite_failed_response_rows'] or diagnosis['journal_failed_response_envelopes']:raise ValueError('Original response-absence witness failed')
        elif diagnosis['sqlite_matches'] or diagnosis['journal_matches']:raise ValueError('Original response-absence witness failed')
        witnesses[key]={'trial':trial,'expected_entry':entry,'diagnosis_path':str(diagnosis_path.relative_to(root)),'diagnosis_sha256':sha256(diagnosis_path),'execution_exit_sha256':sha256(run/'execution_exit.json'),'native_status':done['status'],'actual_attempts':done['attempted_rounds'],'no_new_five_attempt_credit':True}
    if len(witnesses)!=4 or not math.isclose(math.fsum(x['expected_entry']['reserved_usd'] for x in witnesses.values()),cost['observed_missing_response_reservations_usd'],rel_tol=0,abs_tol=1e-12):raise ValueError('Missing terminal reservation or changed total')
    return witnesses


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
                valid=valid and d['script_sha256']==sha256(root/'scripts/build_fidelity_accounts_v2.py') and d['source_gate_sha256']==sha256(root/'scripts/fidelity_equity_evidence_v2.py')
                hashes=[(p.parent/k,v) for k,v in d['public_outputs'].items()]+[(root/k,v) for k,v in d['private_account_outputs'].items()]
            else:
                valid=valid and not d['primary_replaced'] and d['baseline_models_refitted']==0
                hashes=[(p.parent/k,v) for k,v in d['outputs'].items()]+[(root/k,v) for k,v in d['source_files'].items()]
            valid=valid and all(x.is_file() and sha256(x)==digest for x,digest in hashes)
            row.update(status=d.get('status'),pass_=valid,sha256=sha256(p));row['pass']=row.pop('pass_')
        rows.append(row)
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Preserve existing readiness audit')
    root=ROOT;witnesses=terminal_witnesses(root);closures=closure_artifacts(root);closed=all(x['pass'] for x in closures)
    ledger=root/'runs/economic_fidelity/openrouter';cache_hits=set();journal_hits=set();fresh=False
    # No long journal lock while known paid-source closures are missing. This
    # dry-run cannot pass until a fresh dual-store audit is performed below.
    with (ledger/'project_spend.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);raw=(ledger/'project_spend.json').read_bytes();state=json.loads(raw);mapping_path=ledger/'technical_recoveries.json';mapping=json.loads(mapping_path.read_text()) if mapping_path.exists() else {}
        with closing(sqlite3.connect('file:'+str(ledger/'response_cache.sqlite3')+'?mode=ro',uri=True)) as con:
            cache_hits={k for k in witnesses if con.execute('SELECT 1 FROM responses WHERE request_hash=?',(k,)).fetchone()}
        unknown=[k for k,v in state['calls'].items() if v['status']=='reserved' and k not in witnesses]
        if closed and not unknown:
            with (ledger/'cohort_response_journal.lock').open('a+') as journal_lock:
                fcntl.flock(journal_lock,fcntl.LOCK_EX)
                with (ledger/'cohort_responses.jsonl').open('rb') as stream:
                    needles=[k.encode() for k in witnesses]
                    for line in stream:
                        if any(k in line for k in needles):
                            item=json.loads(line)
                            if item['request_hash'] in witnesses:journal_hits.add(item['request_hash'])
                fresh=True
        result=assess_requests(state['calls'],witnesses,mapping,cache_hits,journal_hits,sources_closed=closed,fresh_dual_store_check=fresh)
        if (ledger/'project_spend.json').read_bytes()!=raw:raise ValueError('Ledger changed under its lock')
    result.update(status='read_only_archive_request_preflight_pass' if result['cache_snapshot_request_gate_pass'] else 'read_only_archive_request_preflight_blocked',recorded_at_utc=datetime.now(timezone.utc).isoformat(),ledger_snapshot_sha256=hashlib.sha256(raw).hexdigest(),closure_artifacts=closures,witness_bindings=witnesses,script_sha256=sha256(Path(__file__)),not_a_final_bundle_or_publication_gate='This is only cache-request eligibility at a locked instant; final source/economic/report/bundle/privacy/archive checks remain mandatory. A later packager must repeat this check inside its own ledger+journal snapshot transaction.',AMZN_retry_permission='This probe grants no HTTP500 exception and does not change the pending user question.')
    atomic_json(args.output,result)
    print(json.dumps({k:result[k] for k in ['status','retained_terminal_reservation_usd','unclassified_reserved_count','unclassified_reserved_by_study','source_closures_pass','fresh_dual_store_check','archive_created']}))
if __name__=='__main__':main()
