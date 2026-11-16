#!/usr/bin/env python3
"""Retain trial08's observed failed fifth attempt; never make a replacement call."""
from pathlib import Path
import sys,json,pickle,socket,os
ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'artifacts/fidelity_completion_v2'
SOURCE=PRIVATE/'dependencies/alphaagent_95e478'
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts'),str(SOURCE)]
from alpha_evolve.openrouter_budget import atomic_json,sha256
from fidelity_alpha_terminal_v2 import FAILED_KEY,FAILED_RUN,validate_alpha_five_attempts

def trajectories(instance):
    return [{
        'hypothesis':str(hypothesis),
        'factors':[task.get_task_information_and_implementation_result() for task in experiment.sub_tasks],
        'feedback':str(feedback),
        'metrics':{str(k):float(v) for k,v in experiment.result.items()} if experiment.result is not None else None,
        'workspace':str(experiment.experiment_workspace.workspace_path),
        'factor_workspaces':[str(workspace.workspace_path) for workspace in experiment.sub_workspace_list],
    } for hypothesis,experiment,feedback in instance.trace.hist]

def main():
    run=PRIVATE/FAILED_RUN; audit=PRIVATE/'alpha_trial08_failure_20260918'
    if (run/'execution_exit.json').exists() or (run/'trajectories.json').exists():
        raise ValueError('Preserve existing closure outputs')
    diagnosis=json.loads((audit/'diagnosis.json').read_text())
    assert diagnosis['status']=='exact_failed_request_reconstructed_without_network'
    assert diagnosis['failed_request_hash']==FAILED_KEY and len(diagnosis['exact_cached_prefix_requests'])==72
    manifest=json.loads((audit/'preservation_manifest.json').read_text())
    for row in manifest['files']:
        assert row['sha256']==sha256(ROOT/row['copy'])
        if row['path'].startswith('artifacts/') or row['path'] in ['scripts/run_alphaagent_rounds_v2.py','scripts/replay_alphaagent_rounds_v2.py','src/alpha_evolve/publication_llm.py']:
            assert sha256(ROOT/row['path'])==row['sha256']
    recipe=json.loads((run/'execution_recipe.json').read_text())
    for name,digest in recipe['source_python_hashes'].items():
        assert sha256(SOURCE/name)==digest
    terminal=(audit/'terminal_job.txt').read_text()
    assert '26544035|FAILED|1:0|' in terminal
    assert '26502926_8|26544035|FAILED|1:0' in (audit/'terminal_job_identity.txt').read_text()
    os.environ.update(OPENAI_API_KEY='unused-offline',CHAT_OPENAI_API_KEY='unused-offline')
    def forbidden(*a,**kw):raise RuntimeError('Finalization forbids network')
    socket.create_connection=forbidden;socket.socket.connect=forbidden
    checkpoint=run/'log/__session__/4/0_factor_propose'
    with checkpoint.open('rb') as f:instance=pickle.load(f)
    assert (instance.loop_idx,instance.step_idx,len(instance.trace.hist))==(4,1,4)
    rows=trajectories(instance)
    atomic_json(run/'trajectories.json',rows)
    binding_paths=[run/n for n in ['model_calls.json','embedding_calls.json','stages.json','execution_recipe.json','trajectories.json']]
    binding_paths += [checkpoint,audit/'diagnosis.json',audit/'failed_request.json',audit/'terminal_job.txt',audit/'preservation_manifest.json',audit/'response_absence.json',audit/'openrouter_gpt35_endpoints.json',audit/'terminal_job_identity.txt',audit/'diagnostic.log',audit/'diagnostic_executed_source.py',ROOT/'scripts/complete_alphaagent_failure_diagnosis_v2.py']
    binding_paths += [ROOT/'scripts'/n for n in ['finalize_alphaagent_terminal_v2.py','diagnose_alphaagent_final_http400_v2.py']]
    binding_paths += [ROOT/r['copy'] for r in manifest['files']]
    proof={'status':'observed_final_attempt_failure_retained','run':FAILED_RUN,'failed_round_index':4,
        'native_loop_idx':4,'native_step_idx':1,'failed_request_hash':FAILED_KEY,
        'binding_scope':'Original completed requests, embeddings, stages, checkpoint, original source/log copies and exact offline failed-request reconstruction. No native fifth-round completion is invented.',
        'bindings':[{'path':str(p.relative_to(ROOT)),'sha256':sha256(p)} for p in binding_paths],
        'provider_error_body_available':False,'observed_http_status':400,
        'additional_paid_calls':0,'replacement_rounds':0,'reservation_retained_usd':.030346,
        'completion_scope':'Five rounds were attempted; four produced native trajectories. Final attempt stopped at its observed HTTP400. This closure is evidence extraction, not a successful native return.'}
    atomic_json(run/'terminal_failure_closure.json',proof)
    stages=json.loads((run/'stages.json').read_text())
    atomic_json(run/'execution_exit.json',{
        'status':'native_final_attempt_failed','attempted_rounds':5,'failed_round_indices':[4],
        'completed_trajectories':4,'model_calls':110,'finished_stages':sum(r['completed'] for r in stages),
        'native_loop_idx_at_failure':4,'native_step_idx_at_failure':1,
        'terminal_failure_closure_sha256':sha256(run/'terminal_failure_closure.json'),
        'round_rule':'Retain all five attempted rounds, including the terminal failed fifth. No sixth proposal, replacement call, truncated prompt or trial omission.',
        'requires_independent_trajectory_causality_and_account_validation':True,'full_original_paper_reproduced':False})
    validate_alpha_five_attempts(run,require_replay=False)
    print('TERMINAL_ATTEMPT_CLOSED_WITH_FAILURE',len(rows))
if __name__=='__main__':main()
