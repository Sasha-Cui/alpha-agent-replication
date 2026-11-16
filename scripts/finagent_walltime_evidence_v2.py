"""Exact returned-response settlement and prefix-bound FinAgent continuation."""
from pathlib import Path
import hashlib,json,math,fcntl,threading
from alpha_evolve.openrouter_budget import sha256,atomic_json
from alpha_evolve.publication_replay import ReadOnlyReplay
from validate_publication_replay import compare,read
ROOT=Path(__file__).resolve().parents[1]
PRIVATE='artifacts/fidelity_completion_v2'
AUDIT=PRIVATE+'/finagent_walltime_continuation_20260919_0237'
PROTOCOL='paper_runs/fidelity_completion_v2/finagent_walltime_continuation_protocol.json'
MARKER='seven_exact_returned_finagent_walltime_responses_v2'

def identity(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def conservative_completed_entry(before,body,offset,digest):
    if before.get('status')!='reserved' or before.get('study')!='fidelity_v2_finagent_source_settings' or before.get('endpoint')!='embeddings' or before.get('model')!='openai/text-embedding-3-large':raise ValueError('Outside the seven embedding-response settlement scope')
    request={k:body[k] for k in ['endpoint','request']}
    if 'technical_recovery' in body or identity(request)!=body['request_hash']:raise ValueError('Original envelope identity changed')
    if body['endpoint']!=before['endpoint'] or body['request']['model']!=before['model']:raise ValueError('Response request model/endpoint changed')
    if body['request'].get('provider')!={'order':['OpenAI'],'allow_fallbacks':False}:raise ValueError('Frozen FinAgent provider binding changed')
    response=body['response'];vectors=response.get('data',[])
    if response.get('error') or len(vectors)!=1 or len(vectors[0].get('embedding',[]))!=3072 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in vectors[0]['embedding']):raise ValueError('Durable embedding is unusable')
    reserve=before['reserved_usd'];reported=response.get('usage',{}).get('cost')
    if not isinstance(reserve,(float,int)) or not math.isfinite(reserve) or reserve<0:raise ValueError('Invalid retained commitment')
    if isinstance(reported,(float,int)) and (not math.isfinite(reported) or reported<0 or reported>reserve+1e-9):raise ValueError('Provider cost requires separate diagnosis')
    after=dict(before);after.update(status='complete',cost_usd=reserve,cost_source='conservative_original_reservation_retained_durable_response_reconciliation',response_id=response.get('id'),response_model=response.get('model'),provider=response.get('provider'),usage=response.get('usage',{}),response_journal_offset=offset,response_journal_sha256=digest,durable_response_reconciliation=MARKER,reported_usage_cost_usd=reported,original_reservation_charge_retained=True)
    return after

def assert_probe(proof,case):
    if proof.get('probe_status')!='pass_expected_stop_not_full_source_replay' or proof.get('status')!='all_preserved_prefixes_match_stopped_before_new_request' or proof.get('source_run')!=case['source_run']:raise ValueError('Actual source-specific prefix probe missing')
    if any(proof.get(k)!=0 for k in ['network_calls','ledger_mutations','cache_mutations']) or proof.get('full_source_completion_claim') is not False:raise ValueError('Probe overclaims completion or read-only execution')
    if proof.get('distinct_orphan_responses_used')!=case['orphan_count']:raise ValueError('Required returned responses not exercised')
    old=[(x['kind'],x['records'],x['sha256']) for x in case['prefixes']]
    new=[(x['kind'],x['records'],x['sha256']) for x in proof['prefixes']]
    if old!=new or any(x.get('difference_count')!=0 or x.get('maximum_numeric_difference')!=0 for x in proof['prefixes']):raise ValueError('Prefix population or comparisons changed')

def prefix_check(out,case,root=ROOT):
    rows=[]
    for row in case['prefixes']:
        original=Path(root)/row['path'];target=out/row['target']
        if sha256(original)!=row['sha256']:raise ValueError('Preserved prefix bytes changed')
        old=read(original);new=read(target)
        if len(old)!=row['records'] or len(new)<len(old):raise ValueError('Preserved prefix population missing')
        errors,delta=compare(old,new[:len(old)])
        if errors:raise ValueError('Preserved economic/request/reasoning prefix differs')
        rows.append({'kind':row['kind'],'path':row['path'],'sha256':row['sha256'],'records':len(old),'target':str(target.relative_to(root)),'target_sha256':sha256(target),'difference_count':0,'maximum_numeric_difference':delta[0]})
    return rows

def load_scope(root=ROOT,require_settlement=False):
    root=Path(root)
    if sha256(root/PROTOCOL)!=sha256(root/AUDIT/'frozen_protocol.json'):raise ValueError('Frozen continuation protocol changed')
    scope=json.loads((root/PROTOCOL).read_text())
    for row in scope['bindings']:
        if sha256(root/row['path'])!=row['sha256']:raise ValueError('Frozen continuation dependency changed: '+row['path'])
    for symbol,case in scope['cases'].items():
        proof=json.loads((root/case['probe_path']).read_text());assert_probe(proof,case)
        actual=prefix_check(root/PRIVATE/case['probe_name'],case,root)
        if actual!=proof['prefixes']:raise ValueError('Actual probe record hashes changed')
        uses=root/PRIVATE/case['probe_name']/'orphan_response_uses.jsonl'
        if sha256(uses)!=proof['orphan_response_uses_sha256']:raise ValueError('Actual orphan-use evidence changed')
        used={json.loads(x)['request_hash'] for x in uses.read_text().splitlines()}
        if used!=set(case['orphan_keys']):raise ValueError('Unexpected orphan request population')
        for row in case['future_envelopes']:
            path=root/row['path']
            if sha256(path)!=row['sha256'] or identity(json.loads(path.read_text()))!=row['key']:raise ValueError('Future stop envelope changed')
    if require_settlement:validate_settlement(scope,root)
    return scope

def validate_settlement(scope,root=ROOT):
    root=Path(root);p=root/AUDIT/'settlement_receipt.json';receipt=json.loads(p.read_text())
    if receipt.get('status')!='seven_exact_durable_responses_settled_full_commitment_retained' or receipt.get('protocol_sha256')!=sha256(root/PROTOCOL):raise ValueError('Exact settlement receipt absent')
    if receipt.get('project_commitment_before')!=receipt.get('project_commitment_after') or receipt.get('finagent_commitment_before')!=receipt.get('finagent_commitment_after') or receipt.get('network_calls')!=0 or receipt.get('other_entries_changed')!=0:raise ValueError('Settlement changed charges or unrelated requests')
    state=json.loads((root/'runs/economic_fidelity/openrouter/project_spend.json').read_text())
    if set(receipt['entries'])!=set(scope['settlements']):raise ValueError('Settlement selection changed')
    for key,row in scope['settlements'].items():
        body_path=root/row['copy'];body=json.loads(body_path.read_text());hit=row['journal_matches'][0]
        if sha256(body_path)!=row['copy_sha256']:raise ValueError('Preserved returned response changed')
        expected=conservative_completed_entry(row['entry'],body,hit['offset'],hit['sha256'])
        if receipt['entries'][key]!={'before':row['entry'],'after':expected} or state['calls'].get(key)!=expected:raise ValueError('Selected settlement identity/status/charge changed')
        with (root/'runs/economic_fidelity/openrouter/cohort_responses.jsonl').open('rb') as f:f.seek(hit['offset']);line=f.readline()
        if hashlib.sha256(line).hexdigest()!=hit['sha256']:raise ValueError('Durable journal changed')
    return receipt

def assert_future_request(state,key,case,mapping):
    if key not in {x['key'] for x in case['future_envelopes']}:raise ValueError('First uncached request outside actual probe boundary')
    if key in state['calls'] or key in mapping:raise ValueError('Existing request/mapping cannot be a new continuation')

def gated_meter(live_type,out,case,scope):
    class Meter(ReadOnlyReplay):
        def __init__(self,*a,**k):
            self._args=a;self._kwargs=dict(k);self._live=None;self._gate_lock=threading.RLock();super().__init__(*a,**k)
        def request(self,*a,**k):
            with self._gate_lock:
                if self._live is not None:return self._live.request(*a,**k)
                try:return super().request(*a,**k)
                except RuntimeError as error:
                    if not str(error).startswith('Offline response is not complete in the frozen cache: '):raise
                    key=str(error).rsplit(' ',1)[-1];assert_future_request(self.frozen_state,key,case,self.recovery_map)
                    rows=prefix_check(out,case)
                    validate_settlement(scope)
                    with (self.root/'project_spend.lock').open('a+') as lock:
                        fcntl.flock(lock,fcntl.LOCK_EX);state=json.loads(self.ledger_path.read_text());mapping=json.loads(self.recoveries.read_text()) if self.recoveries.exists() else {};assert_future_request(state,key,case,mapping)
                    path=out/'live_prefix_gate.json'
                    if path.exists():raise ValueError('Existing transition evidence must not be overwritten')
                    atomic_json(path,{'status':'pass_before_first_new_request','source_run':case['source_run'],'prefixes':rows,'future_request_hash':key,'protocol_sha256':sha256(ROOT/PROTOCOL),'settlement_receipt_sha256':sha256(ROOT/AUDIT/'settlement_receipt.json'),'network_calls_before_gate':0,'ledger_mutations_before_gate':0})
                    self._live=live_type(*self._args,**self._kwargs);self._live.request_trace=self.request_trace;self._live.initial_cache.request_trace=self.request_trace
                    return self._live.request(*a,**k)
        def snapshot(self):
            if self._live is not None:return self._live.snapshot()
            if (out/'live_prefix_gate.json').exists():
                with (self.root/'project_spend.lock').open('a+') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX);state=json.loads(self.ledger_path.read_text())
                project,study=self.totals(state,self.study);return {'project_committed_usd':project,'study_committed_usd':study,'project_soft_cap_usd':self.project_cap,'study_cap_usd':self.study_cap,'read_only_replay':False,'prefix_gate_passed_in_child':True}
            return super().snapshot()
    return Meter

def completion_receipt(out,case,scope,*,offline,root=ROOT):
    root=Path(root);done=json.loads((out/'completion.json').read_text());wrapper=json.loads((out/'wrapper.json').read_text())
    if done.get('status')!='complete' or done.get('offline') is not offline or done.get('arm_counts')!=scope['expected_arm_counts'] or done.get('steps')!=397:raise ValueError('Full planned source calendar missing')
    for k,v in [('script_sha256',scope['driver_sha256']),('recipe_sha256',case['recipe_sha256']),('input_sha256',case['input_sha256']),('decision_sha256',sha256(out/'decisions.jsonl'))]:
        if done.get(k)!=v:raise ValueError('Completed source binding changed')
    if wrapper.get('walltime_continuation')!=MARKER or wrapper.get('protocol_sha256')!=sha256(root/PROTOCOL) or wrapper.get('wrapper_sha256')!=sha256(root/'scripts/run_finagent_walltime_continuation_v2.py') or wrapper.get('source_run')!=case['source_run'] or wrapper.get('offline') is not offline:raise ValueError('Wrapper provenance missing')
    files=['completion.json','decisions.jsonl','wrapper.json','validation_arms/native_causal/decisions.jsonl','validation_arms/native_causal/completion.json']
    if case['symbol']=='TSLA':files.append('schema_repair_events.json')
    if not offline:
        gate=json.loads((out/'live_prefix_gate.json').read_text())
        if gate.get('status')!='pass_before_first_new_request' or gate.get('network_calls_before_gate')!=0 or gate.get('ledger_mutations_before_gate')!=0 or gate.get('protocol_sha256')!=sha256(root/PROTOCOL) or gate.get('settlement_receipt_sha256')!=sha256(root/AUDIT/'settlement_receipt.json') or gate.get('future_request_hash') not in {x['key'] for x in case['future_envelopes']}:raise ValueError('Live transition not verified')
        files.append('live_prefix_gate.json')
    return {'status':'pass','source_run':case['source_run'],'records':397,'offline':offline,'protocol_sha256':sha256(root/PROTOCOL),'settlement_receipt_sha256':sha256(root/AUDIT/'settlement_receipt.json'),'prefixes':prefix_check(out,case,root),'files':[{ 'path':str((out/f).relative_to(root)),'sha256':sha256(out/f)} for f in files]}

def validate_admission(root,run,proof,replay):
    scope=load_scope(root,require_settlement=True);matches=[x for x in scope['cases'].values() if x['continuation_name']==run.name]
    if len(matches)!=1 or replay.name!=matches[0]['replay_name'] or proof.get('walltime_continuation')!=MARKER:raise ValueError('Wrong walltime continuation/replay identity')
    case=matches[0]
    if proof.get('replay_wrapper_sha256')!=sha256(Path(root)/'scripts/run_finagent_walltime_continuation_v2.py'):raise ValueError('Replay method changed')
    for out,offline,key in [(run,False,'source_walltime_receipt_sha256'),(replay,True,'replay_walltime_receipt_sha256')]:
        path=out/'walltime_completion_validation.json'
        if sha256(path)!=proof.get(key) or json.loads(path.read_text())!=completion_receipt(out,case,scope,offline=offline,root=root):raise ValueError('Walltime source/replay receipts changed')
    return {'status':'pass','source_run':case['source_run'],'records':397,'all_preserved_prefixes_rechecked':True,'reserved_commitment_retained':True,'protocol_sha256':sha256(Path(root)/PROTOCOL)}
