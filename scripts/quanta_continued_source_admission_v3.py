"""Bind the continued source and full replay to its original observed history."""
from pathlib import Path
import json
from alpha_evolve.openrouter_budget import sha256
from validate_publication_replay import compare
from quanta_walltime_continuation_v3 import load_scope,validate_completed_source,verify_models,locked_budget_and_orphan,SETUP,PROTOCOL,LIVE,REPLAY,REQUIRED_FILES

def exact(left,right,label):
    errors=[];maximum=[0.0];compare(left,right,label,errors,maximum)
    if errors or maximum[0]:raise ValueError(label+' no longer matches exactly')

def evaluation_adapter(root):
    root=Path(root);public=root/'paper_runs/fidelity_completion_v2/quanta_continued_evaluation_adapter_v5.json'
    frozen=root/'artifacts/fidelity_completion_v2/quanta_continuation_setup_20260919_after_reset/v3/evaluation/frozen_protocol.json'
    if sha256(public)!=sha256(frozen):raise ValueError('Frozen economic lineage adapter changed')
    plan=json.loads(public.read_text())
    if plan['original_economic_protocol_changed'] or plan['financial_expressions_changed'] or plan['original_source_run']!='quantaalpha_paper_parameters' or plan['continued_source_run']!=LIVE:raise ValueError('Economic scope changed')
    for row in plan['bindings']:
        if sha256(root/row['path'])!=row['sha256']:raise ValueError('Economic adapter method binding changed: '+row['path'])
    return plan

def admission(root):
    root=Path(root);evaluation_adapter(root);p=root/'artifacts/fidelity_completion_v2';source=p/LIVE;replay=p/REPLAY
    plan,base,probe=load_scope();done=validate_completed_source(source)
    original=root/base['original_run'];oldpool=json.loads((original/'log/trajectory_pool.json').read_text())
    full=json.loads((source/'full_replay_validation.json').read_text())
    if full.get('status')!='pass' or full.get('difference_count')!=0 or full.get('differences')!=[] or full.get('network_calls')!=0 or full.get('ledger_mutations')!=0 or full.get('native_factor_or_backtest_execution')!=0:raise ValueError('Continued full replay is incomplete or changed')
    if full['continuation_protocol_sha256']!=sha256(PROTOCOL) or full['continuation_completion_sha256']!=sha256(source/'continuation_completion.json'):raise ValueError('Full replay/continuation ancestry changed')
    if set(full['artifact_hashes'])!=set(REQUIRED_FILES):raise ValueError('Missing full observed replay state')
    for name,row in full['artifact_hashes'].items():
        if sha256(source/name)!=row['original'] or sha256(replay/name)!=row['replay']:raise ValueError('Full replay bytes changed')
        a=json.loads((source/name).read_text());b=json.loads((replay/name).read_text())
        if name.endswith('trajectory_pool.json'):a.pop('saved_at',None);b.pop('saved_at',None)
        exact(a,b,name)
    for run,key in [(source,'source_prefix_gate_sha256'),(replay,'replay_prefix_gate_sha256')]:
        gate_path=run/'continuation_prefix_gate.json';gate=json.loads(gate_path.read_text())
        if full[key]!=sha256(gate_path) or gate.get('status')!='exact_original_state_and_actual_boundary_reconstructed_before_continuation' or gate['actual_probe_receipt_sha256']!=sha256(root/plan['reconstruction_receipt']) or gate['continuation_protocol_sha256']!=sha256(PROTOCOL):raise ValueError('Original boundary gate changed')
        if sha256(run/'reconstructed_rng_state.json')!=gate['rng_state_sha256'] or gate['boundary_details']!=probe['boundary_details'] or gate['rng_state_sha256']!=probe['rng_state_sha256']:raise ValueError('Actual witnessed boundary/RNG was not preserved')
    for name,count in [('model_calls.json',base['chat_count']),('embedding_calls.json',base['embedding_count']),('quality_gate_events.json',base['quality_event_count'])]:
        exact(json.loads((original/name).read_text()),json.loads((source/name).read_text())[:count],'original_prefix_'+name)
    calls=json.loads((source/'model_calls.json').read_text())
    if calls[base['chat_count']]['request_hash']!=base['orphan']['request_hash']:raise ValueError('Original durable response ordinal changed')
    partial=root/plan['interrupted_continuation_run']
    for filename in ['model_calls.json','embedding_calls.json','quality_gate_events.json']:
        old=json.loads((partial/filename).read_text());new=json.loads((source/filename).read_text());exact(old,new[:len(old)],'entire_interrupted_V2_prefix_'+filename)
    for run,key in [(source,'source_partial_prefix_gate_sha256'),(replay,'replay_partial_prefix_gate_sha256')]:
        path=run/'partial_continuation_prefix_gate.json';gate=json.loads(path.read_text())
        if full.get(key)!=sha256(path) or gate['status']!='all_interrupted_continuation_records_and_results_reused_before_first_unexecuted_model' or gate['counts']!=plan['partial_counts'] or gate['model_cache_key']!=plan['partial_model']['model_cache_key'] or gate['model_code_identity']!=plan['partial_model']['code_identity'] or gate['protocol_sha256']!=sha256(PROTOCOL):raise ValueError('Preserved partial continuation gate changed')
        if sha256(run/'partial_reconstructed_rng_state.json')!=gate['reconstructed_rng_state_sha256'] or gate['partial_diagnosis_sha256']!=sha256(root/plan['partial_diagnosis']) or gate['original_partial_boundary_RAM_snapshot_available'] is not False:raise ValueError('Partial failure ancestry or RNG claim changed')
    for name in ['loop_ids','pool_ids']:
        if any(done[name].get(k)!=v for k,v in base[name].items()) or len(set(done[name].values()))!=len(done[name]):raise ValueError('Original/new native identity lineage changed')
    for name in ['runtime.json','parameter_wiring.json']:
        exact(json.loads((original/name).read_text()),json.loads((source/name).read_text()),name)
    pool=json.loads((source/'log/trajectory_pool.json').read_text())['trajectories']
    for tid,row in oldpool['trajectories'].items():exact(row,pool[tid],'original_pool_entry_'+tid)
    verify_models(json.loads((SETUP/'native_artifact_lineage.json').read_text()));budget=locked_budget_and_orphan(base)
    return {'status':'pass','original_run':base['original_run'],'continued_source':LIVE,'continuation_protocol_sha256':sha256(PROTOCOL),'source_completion_sha256':sha256(source/'continuation_completion.json'),'full_replay_sha256':sha256(source/'full_replay_validation.json'),'original_native_artifact_lineage_sha256':sha256(SETUP/'native_artifact_lineage.json'),'original_loops_preserved':34,'original_pool_entries_preserved':33,'current_pool_entries':len(pool),'original_orphan_full_reservation_retained':budget['orphan_reserved_usd_retained'],'scope':'Source/replay ancestry and native artifact reuse only; no economic completion, strict-primary substitution or full-paper claim.'}
