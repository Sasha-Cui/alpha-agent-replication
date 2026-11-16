"""Intrinsic evidence for the one witnessed GOOGL markup adaptation."""
from pathlib import Path
import fcntl,json,threading
from alpha_evolve.openrouter_budget import sha256,atomic_json
from alpha_evolve.publication_replay import ReadOnlyReplay
from finagent_googl_xml_alias_v2 import load_witness,validate_prefixes
from validate_publication_replay import compare,read
ROOT=Path(__file__).resolve().parents[1]
PRIVATE='artifacts/fidelity_completion_v2'
PROTOCOL='paper_runs/fidelity_completion_v2/finagent_googl_xml_continuation_protocol.json'
FROZEN=PRIVATE+'/finagent_googl_xml_continuation_20260919_0135/frozen_protocol.json'
REPAIR='finagent_GOOGL_company_news_xml_repair'
REPLAY=REPAIR+'_offline_replay'
MARKER='exact_93820f59_lossless_analysis_summary_tags'

def assert_probe_header(proof):
    if proof.get('probe_status')!='pass_expected_stop_before_new_request_not_full_replay' or proof.get('status')!='all_original_completed_prefixes_and_single_alias_match':raise ValueError('Actual prefix probe has not passed')
    if proof.get('records')!=282 or proof.get('network_calls')!=0 or proof.get('ledger_mutations')!=0 or proof.get('full_source_completion_claim') is not False:raise ValueError('Invalid probe scope or population')
    if sorted((p['arm'],p['records'],p['difference_count'],p['maximum_numeric_difference']) for p in proof['prefixes'])!=[('native_causal',32,0,0.0),('shared_training',250,0,0.0)]:raise ValueError('Invalid probe prefix populations')

def check_new_request(state,key,expected,recovery_map):
    if key!=expected:raise ValueError('First missing request differs from the witnessed offline stop')
    if key in state['calls']:raise ValueError('Existing request cannot be admitted as a new future request')
    if key in recovery_map or any(x.get('original_request_hash')==key for x in recovery_map.values()):raise ValueError('Unexpected retry mapping for future request')

def load_scope(root=ROOT):
    root=Path(root)
    if sha256(root/PROTOCOL)!=sha256(root/FROZEN):raise ValueError('Frozen continuation protocol changed')
    scope=json.loads((root/PROTOCOL).read_text())
    for row in scope['bindings']:
        if sha256(root/row['path'])!=row['sha256']:raise ValueError('Continuation dependency changed: '+row['path'])
    witness=load_witness(root)
    probe=json.loads((root/scope['probe_path']).read_text());assert_probe_header(probe)
    actual=validate_prefixes(root/PRIVATE/witness['probe_run'],witness,root=root)
    if any(actual[k]!=probe[k] for k in ['prefixes','alias_events_sha256','records']):raise ValueError('Actual offline probe evidence changed')
    if probe['adapter_sha256']!=sha256(root/'scripts/finagent_googl_xml_alias_v2.py') or probe['wrapper_sha256']!=sha256(root/'scripts/probe_finagent_googl_xml_v2.py') or probe['protocol_sha256']!=sha256(root/'paper_runs/fidelity_completion_v2/finagent_googl_xml_alias_protocol.json'):raise ValueError('Probe method binding changed')
    return scope,witness,probe

def validate_ancestry(out,scope,*,root=ROOT):
    root=Path(root);new=read(out/'decisions.jsonl');rows=[]
    old_proof=json.loads((root/scope['ancestry_path']).read_text())
    for row in old_proof['prefixes']:
        path=root/row['path']
        if sha256(path)!=row['sha256']:raise ValueError('Earlier transport prefix changed')
        prior=read(path)
        if len(prior)!=row['records'] or len(new)<len(prior):raise ValueError('Earlier transport prefix records absent')
        errors,delta=compare(prior,new[:len(prior)])
        if errors:raise ValueError('Earlier transport prefix differs')
        rows.append({'path':row['path'],'sha256':row['sha256'],'records':len(prior),'difference_count':0,'maximum_numeric_difference':delta[0]})
    if sum(x['records'] for x in rows)!=76:raise ValueError('Required 76-record ancestry missing')
    return rows

def validate_all_prefixes(out,scope,witness,*,root=ROOT):
    proof=validate_prefixes(out,witness,root=root)
    proof['earlier_ancestry']=validate_ancestry(out,scope,root=root)
    return proof

def make_gated_meter(live_type,out,scope,witness,probe):
    """All prefix calls use ReadOnlyReplay. No live constructor before the gate."""
    class GatedMeter(ReadOnlyReplay):
        def __init__(self,*args,**kwargs):
            self._live_args=args;self._live_kwargs=dict(kwargs);self._live=None;self._transition_lock=threading.RLock()
            super().__init__(*args,**kwargs)
        def request(self,*args,**kwargs):
            with self._transition_lock:
                if self._live is not None:return self._live.request(*args,**kwargs)
                try:return super().request(*args,**kwargs)
                except RuntimeError as error:
                    if not str(error).startswith('Offline response is not complete in the frozen cache: '):raise
                    key=str(error).rsplit(' ',1)[-1]
                    check_new_request(self.frozen_state,key,probe['first_absent_future_request_hash'],self.recovery_map)
                    proof=validate_all_prefixes(out,scope,witness)
                    with (self.root/'project_spend.lock').open('a+') as lock:
                        fcntl.flock(lock,fcntl.LOCK_EX)
                        state=json.loads(self.ledger_path.read_text())
                        recovery=json.loads(self.recoveries.read_text()) if self.recoveries.exists() else {}
                        check_new_request(state,key,probe['first_absent_future_request_hash'],recovery)
                    gate=out/'live_prefix_gate.json'
                    if gate.exists():raise ValueError('Preserve existing live transition evidence before restarting')
                    proof.update(status='pass_before_first_new_future_request',first_new_request_hash=key,probe_sha256=sha256(ROOT/scope['probe_path']),continuation_protocol_sha256=sha256(ROOT/PROTOCOL),network_calls_before_gate=0,ledger_mutations_before_gate=0,only_ordinary_future_requests_authorized=True)
                    atomic_json(gate,proof)
                    self._live=live_type(*self._live_args,**self._live_kwargs)
                    self._live.request_trace=self.request_trace
                    self._live.initial_cache.request_trace=self.request_trace
                    return self._live.request(*args,**kwargs)
        def snapshot(self):
            if self._live is not None:return self._live.snapshot()
            # Child performs the live transition; parent must report fresh costs.
            if (out/'live_prefix_gate.json').exists():
                with (self.root/'project_spend.lock').open('a+') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX);state=json.loads(self.ledger_path.read_text())
                project,own=self.totals(state,self.study)
                return {'project_committed_usd':project,'study_committed_usd':own,'study_cap_usd':self.study_cap,'project_soft_cap_usd':self.project_cap,'read_only_replay':False,'prefix_gate_passed_in_validation_child':True}
            return super().snapshot()
    return GatedMeter

def receipt(out,scope,witness,*,offline,root=ROOT):
    root=Path(root);done=out/'completion.json';d=json.loads(done.read_text())
    if d.get('status')!='complete' or d.get('offline') is not offline or d.get('script_sha256')!=witness['original_driver_sha256']:raise ValueError('Source has not completed under the frozen driver')
    if d['recipe_sha256']!=witness['recipe_sha256'] or d['input_sha256']!=witness['input_sha256'] or d['decision_sha256']!=sha256(out/'decisions.jsonl'):raise ValueError('Completion binding changed')
    if d.get('arm_counts')!=scope['expected_arm_counts']:raise ValueError('Full original calendar/arm population missing')
    w=json.loads((out/'wrapper.json').read_text())
    expected={'xml_format_adaptation':MARKER,'protocol_sha256':sha256(root/PROTOCOL),'wrapper_sha256':sha256(root/'scripts/run_finagent_googl_xml_continuation_v2.py'),'adapter_sha256':sha256(root/'scripts/finagent_googl_xml_alias_v2.py'),'evidence_sha256':sha256(Path(__file__)),'original_failed_source':witness['source_run'],'offline':offline}
    if any(w.get(k)!=v for k,v in expected.items()):raise ValueError('Exact wrapper provenance missing or changed')
    prefixes=validate_all_prefixes(out,scope,witness,root=root)
    files=['completion.json','decisions.jsonl','wrapper.json','xml_alias_events.jsonl','validation_arms/native_causal/decisions.jsonl','validation_arms/native_causal/completion.json']
    if not offline:
        gate=json.loads((out/'live_prefix_gate.json').read_text())
        if gate.get('status')!='pass_before_first_new_future_request' or gate.get('network_calls_before_gate')!=0 or gate.get('ledger_mutations_before_gate')!=0 or gate.get('continuation_protocol_sha256')!=sha256(root/PROTOCOL):raise ValueError('Live transition gate missing or changed')
        if gate.get('first_new_request_hash')!=json.loads((root/scope['probe_path']).read_text())['first_absent_future_request_hash'] or gate.get('records')!=282:raise ValueError('Wrong live transition point')
        files.append('live_prefix_gate.json')
    return {'status':'pass','offline':offline,'records':d['steps'],'prefixes':prefixes,'protocol_sha256':sha256(root/PROTOCOL),'bindings':[{ 'path':str((out/f).relative_to(root)),'sha256':sha256(out/f)} for f in files],'scope':'Completed disclosed single-response markup adaptation with full preserved-prefix binding; not full-paper reproduction.'}

def validate_admission(root,run,proof,replay):
    scope,witness,probe=load_scope(root)
    if run.name!=REPAIR or replay.name!=REPLAY:raise ValueError('Unplanned XML repair/replay identity')
    if proof.get('xml_format_adaptation')!=MARKER or proof.get('replay_wrapper_sha256')!=sha256(Path(root)/'scripts/run_finagent_googl_xml_continuation_v2.py'):raise ValueError('XML replay method binding absent')
    for path,offline,key in [(run,False,'xml_source_receipt_sha256'),(replay,True,'xml_replay_receipt_sha256')]:
        w=json.loads((path/'wrapper.json').read_text())
        if w.get('xml_format_adaptation')!=MARKER or w.get('protocol_sha256')!=sha256(Path(root)/PROTOCOL):raise ValueError('XML wrapper declaration missing')
        saved=path/'xml_completion_validation.json'
        if sha256(saved)!=proof.get(key):raise ValueError('XML completion receipt changed')
        if json.loads(saved.read_text())!=receipt(path,scope,witness,offline=offline,root=root):raise ValueError('XML source/replay evidence no longer matches')
    return {'status':'pass','format_adaptation':MARKER,'source_records':proof['records'],'protocol_sha256':sha256(Path(root)/PROTOCOL),'all_282_and_76_prefixes_rechecked':True}
