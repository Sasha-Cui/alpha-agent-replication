"""Guarded continuation evidence; original source, replies and models stay frozen."""
from pathlib import Path
import hashlib,json,fcntl
from alpha_evolve.openrouter_budget import sha256,atomic_json
from alpha_evolve.publication_llm import CohortOpenRouter
from quanta_walltime_reconstruction_v2 import identity
ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'artifacts/fidelity_completion_v2'
SETUP=PRIVATE/'quanta_continuation_setup_20260919_after_reset/v3'
PROTOCOL=ROOT/'paper_runs/fidelity_completion_v2/quanta_walltime_continuation_protocol_v3.json'
LIVE='quantaalpha_paper_parameters_walltime_continuation_v3'
REPLAY=LIVE+'_offline_replay'
REQUIRED_FILES=['model_calls.json','embedding_calls.json','parameter_wiring.json','quality_gate_events.json','log/evolution_state.json','log/trajectory_pool.json']

def read(p):return json.loads(Path(p).read_text())

def load_scope():
    if sha256(PROTOCOL)!=sha256(SETUP/'frozen_protocol.json'):raise ValueError('Continuation protocol changed')
    plan=read(PROTOCOL)
    if plan['orphan_settlement_allowed'] or plan['replacement_response_allowed'] or plan['completed_model_rerun_allowed']:raise ValueError('Continuation scope broadened')
    for row in plan['bindings']:
        if sha256(ROOT/row['path'])!=row['sha256']:raise ValueError('Frozen continuation binding changed: '+row['path'])
    base=read(ROOT/plan['reconstruction_protocol'])
    for row in base['bindings']:
        if sha256(ROOT/row['path'])!=row['sha256']:raise ValueError('Original reconstruction dependency changed: '+row['path'])
    proof=read(ROOT/plan['reconstruction_receipt'])
    if proof['status']!='observed_state_reconstructed_stopped_before_uncached_future_work' or proof['boundary_details']['cache_key']!=plan['boundary']['cache_key']:raise ValueError('Actual observed boundary missing')
    for field,name in [('model_calls_sha256','model_calls.json'),('embedding_calls_sha256','embedding_calls.json'),('quality_events_sha256','quality_gate_events.json'),('pool_sha256','log/trajectory_pool.json'),('rng_state_sha256','reconstructed_rng_state.json')]:
        if sha256(ROOT/base['probe_run']/name)!=proof[field]:raise ValueError('Actual probe output changed')
    partial=read(ROOT/plan['interrupted_continuation_run']/'model_calls.json')
    if len(partial)!=plan['partial_counts']['chat']:raise ValueError('Interrupted continuation response population changed')
    for key,row in plan['partial_cache_artifacts'].items():
        if key in base['cache_artifacts'] or sha256(ROOT/row['copy'])!=row['sha256']:raise ValueError('Partial native result substituted')
        base['cache_artifacts'][key]=row
    ledger=ROOT/'runs/economic_fidelity/openrouter'
    with (ledger/'project_spend.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);state=read(ledger/'project_spend.json')
        if any(state['calls'].get(k)!=v for k,v in plan['partial_request_entries'].items()):raise ValueError('Partial returned request identity/status/charge changed')
    return plan,base,proof

def assert_boundary(kind,details,plan,rng_digest,proof):
    if kind!='uncached_quantaalpha.factors.coder.factor.execute' or details!={'cache_key':plan['boundary']['cache_key']}:raise ValueError('First future operation is not the witnessed factor calculation')
    if rng_digest!=proof['rng_state_sha256']:raise ValueError('Reconstructed Python/NumPy RNG differs from the actual successful probe')

def assert_cached_code(exp,cached):
    def codes(e):return [getattr(w,'code_dict',{}).get('factor.py') if w is not None else None for w in getattr(e,'sub_workspace_list',[])]
    if codes(exp)!=codes(cached):raise ValueError('Model cache task key matched but current factor code differs')
    if len(exp.based_experiments)!=len(cached.based_experiments):raise ValueError('Model cache ancestor population changed')
    for a,b in zip(exp.based_experiments,cached.based_experiments):
        if codes(a)!=codes(b):raise ValueError('Model cache ancestor factor code differs')

def assert_native_work(gate,replay,cache_key,old_keys,workspace,out):
    if not gate or replay:raise ValueError('Native work forbidden before gate or during replay')
    if cache_key in old_keys:raise ValueError('Original cached computation cannot execute again')
    path=Path(workspace).resolve();roots=[(Path(out)/'results').resolve(),(Path(out)/'git_ignore_folder/RD-Agent_workspace').resolve()]
    if not any(path.is_relative_to(root) for root in roots):raise ValueError('Native work must use a verified factor or native model root inside this new continuation')

def locked_budget_and_orphan(base):
    ledger=ROOT/'runs/economic_fidelity/openrouter'
    with (ledger/'project_spend.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);state=read(ledger/'project_spend.json')
        orphan=base['orphan']
        if state['calls'].get(orphan['request_hash'])!=orphan['entry']:raise ValueError('Exact orphan status/owner/retained charge changed')
        mapping=read(ledger/'technical_recoveries.json') if (ledger/'technical_recoveries.json').exists() else {}
        if orphan['request_hash'] in mapping:raise ValueError('Original durable orphan acquired a retry mapping')
        project,own=CohortOpenRouter.totals(state,'fidelity_v2_quantaalpha_fresh_search')
    if project>=450 or own>=75:raise ValueError('Original project/study budget stop')
    return {'project_committed_usd':project,'quanta_committed_usd':own,'project_soft_stop':450,'project_hard_ceiling':500,'quanta_cap':75,'orphan_reserved_usd_retained':orphan['entry']['reserved_usd']}

def verify_models(lineage):
    for row in lineage['original_model_cache_entries']:
        for f in row['files']:
            if sha256(ROOT/f['path'])!=f['sha256'] or sha256(ROOT/f['copy'])!=f['sha256']:raise ValueError('Preserved native model bytes changed')

def finish_source(out,base,loop_ids,pool_ids,cache_root,model_events):
    if read(out/'execution_exit.json')['status']!='native_pipeline_returned':raise ValueError('Native source did not return')
    if not (out/'continuation_prefix_gate.json').exists() or not (out/'partial_continuation_prefix_gate.json').exists():raise ValueError('Missing exact original and partial continuation boundary gates')
    index=dict(base['cache_artifacts'])
    for p in sorted(cache_root.rglob('*.pkl')):
        key=str(p.relative_to(cache_root))
        if key in index:raise ValueError('Continuation wrote a replacement for original computation')
        index[key]={'copy':str(p.relative_to(ROOT)),'sha256':sha256(p),'bytes':p.stat().st_size,'lineage':'new_native_result_after_exact_observed_prefix_gate'}
    artifacts={}
    for event in model_events:
        w=ROOT/event['workspace']
        if event['lineage']=='new_native_execution':
            for p in sorted(w.rglob('*')):
                if p.is_file() and not p.is_symlink():artifacts[str(p.relative_to(ROOT))]=sha256(p)
    source_hashes={n:sha256(out/n) for n in REQUIRED_FILES+['recipe.json','runtime.json','execution_exit.json','continuation_prefix_gate.json','partial_continuation_prefix_gate.json']}
    atomic_json(out/'continuation_completion.json',{'status':'complete_native_source_with_original_and_new_result_lineage','protocol_sha256':sha256(PROTOCOL),'original_run':base['original_run'],'source_run':out.name,'source_hashes':source_hashes,'loop_ids':loop_ids,'pool_ids':pool_ids,'cache_artifacts':index,'new_native_model_artifacts':artifacts,'model_result_lineage':model_events,'original_orphan_still_reserved':True,'original_orphan_reservation_retained':base['orphan']['entry']['reserved_usd'],'full_replay_complete':False,'economic_completion_claim':False})

def validate_completed_source(source):
    done=read(source/'continuation_completion.json')
    if done['status']!='complete_native_source_with_original_and_new_result_lineage' or done['protocol_sha256']!=sha256(PROTOCOL):raise ValueError('Continued source receipt missing/changed')
    for name,h in done['source_hashes'].items():
        if sha256(source/name)!=h:raise ValueError('Completed source bytes changed')
    for name,h in done['new_native_model_artifacts'].items():
        if sha256(ROOT/name)!=h:raise ValueError('New native model artifact changed')
    return done

def code_identity(exp):
    def codes(e):return [None if w is None or 'factor.py' not in getattr(w,'code_dict',{}) else hashlib.sha256(w.code_dict['factor.py'].encode()).hexdigest() for w in getattr(e,'sub_workspace_list',[])]
    return {'codes':codes(exp),'parents':[codes(b) for b in exp.based_experiments]}

def assert_partial_boundary(cache_key,counts,code,plan):
    if cache_key!=plan['partial_model']['model_cache_key']:raise ValueError('Wrong previously unexecuted model boundary')
    if counts!=plan['partial_counts']:raise ValueError('Incomplete interrupted continuation history')
    if code!=plan['partial_model']['code_identity']:raise ValueError('Pending model code/ancestor identity changed')
