#!/usr/bin/env python3
"""Extract the observed three attempts, retaining two explicitly unattempted rounds."""
from pathlib import Path
import sys,json,pickle,os,socket
ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT/'artifacts/fidelity_completion_v2';SOURCE=PRIVATE/'dependencies/alphaagent_95e478'
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts'),str(SOURCE)]
from alpha_evolve.openrouter_budget import atomic_json,sha256
from fidelity_alpha_early_abort_v2 import RUN_NAME,FAILED_KEY,validate_early_abort
from finalize_alphaagent_terminal_v2 import trajectories

def main():
    run=PRIVATE/RUN_NAME;audit=PRIVATE/'alpha_trial12_early_abort_20260918'
    if (run/'execution_exit.json').exists() or (run/'trajectories.json').exists():raise ValueError('Preserve existing abort extraction')
    diagnosis=json.loads((audit/'diagnosis.json').read_text())
    assert diagnosis['failed_request_hash']==FAILED_KEY and diagnosis['attempted_rounds']==3
    preservation=json.loads((audit/'preservation_manifest.json').read_text())
    for r in preservation['files']:
        assert sha256(ROOT/r['path'])==r['sha256']==sha256(ROOT/r['copy'])
    recipe=json.loads((run/'execution_recipe.json').read_text())
    for n,h in recipe['source_python_hashes'].items():assert sha256(SOURCE/n)==h
    os.environ.update(OPENAI_API_KEY='unused-offline',CHAT_OPENAI_API_KEY='unused-offline')
    def forbidden(*a,**kw):raise RuntimeError('Extraction cannot access the network')
    socket.create_connection=forbidden;socket.socket.connect=forbidden
    checkpoint=run/'log/__session__/2/0_factor_propose'
    with checkpoint.open('rb') as f:instance=pickle.load(f)
    assert (instance.loop_idx,instance.step_idx,len(instance.trace.hist))==(2,1,2)
    atomic_json(run/'trajectories.json',trajectories(instance))
    files=[run/n for n in ['model_calls.json','embedding_calls.json','stages.json','execution_recipe.json','trajectories.json']]+[checkpoint]
    files += [audit/n for n in ['diagnosis.json','failed_request.json','preservation_manifest.json','terminal_job.txt']]
    files += [ROOT/r['copy'] for r in preservation['files']]
    files += [Path(__file__),ROOT/'scripts/diagnose_alphaagent_early_abort_v2.py',ROOT/'scripts/finalize_alphaagent_terminal_v2.py']
    atomic_json(run/'early_abort_evidence.json',{'status':'observed_early_abort_preserved','failed_request_hash':FAILED_KEY,
        'bindings':[{'path':str(p.relative_to(ROOT)),'sha256':sha256(p)} for p in files],
        'native_five_attempt_budget_complete':False,'strict_primary_eligibility':False,
        'no_replacement_rounds':True,'no_changed_model_or_prompt':True,'original_failure_reservation_retained_usd':.028655})
    atomic_json(run/'execution_exit.json',{'status':'native_early_abort','planned_rounds':5,'attempted_rounds':3,
        'completed_trajectories':2,'failed_round_indices':[2],'unattempted_round_indices':[3,4],'model_calls':215,
        'native_loop_idx_at_failure':2,'native_step_idx_at_failure':1,'finished_stages':11,
        'early_abort_evidence_sha256':sha256(run/'early_abort_evidence.json'),
        'native_five_attempt_budget_complete':False,'strict_primary_eligibility':False,
        'claim_boundary':'This observed incomplete trial cannot satisfy the frozen five-attempt primary or secondary library gates. A complete observed-prefix replay is diagnostic only.',
        'full_original_paper_reproduced':False})
    validate_early_abort(run,require_replay=False)
    print('OBSERVED_THREE_ATTEMPT_ABORT_EXTRACTED_FIVE_ATTEMPT_PRIMARY_REMAINS_BLOCKED')
if __name__=='__main__':main()
