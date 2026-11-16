"""Witnessed incomplete trial evidence; never a five-attempt eligibility gate."""
from pathlib import Path
import json
from alpha_evolve.openrouter_budget import sha256
RUN_NAME='alphaagent_rounds_paper_gpt35_12'
FAILED_KEY='c8061be5982779ddeff6c1fbc67d773a431b2e2f6228817d8837094373988a9b'

def validate_early_abort(run,*,require_replay=True,root=None):
    run=Path(run);root=Path(root) if root is not None else Path(__file__).resolve().parents[1]
    done=json.loads((run/'execution_exit.json').read_text())
    expected={'status':'native_early_abort','planned_rounds':5,'attempted_rounds':3,'completed_trajectories':2,
              'failed_round_indices':[2],'unattempted_round_indices':[3,4],'model_calls':215,
              'native_five_attempt_budget_complete':False,'strict_primary_eligibility':False}
    if run.name!=RUN_NAME or any(done.get(k)!=v for k,v in expected.items()):
        raise ValueError('Early-abort identity/count/scope changed')
    p=run/'early_abort_evidence.json'
    if sha256(p)!=done.get('early_abort_evidence_sha256'):raise ValueError('Early-abort evidence changed')
    proof=json.loads(p.read_text())
    if proof.get('failed_request_hash')!=FAILED_KEY:raise ValueError('Different abort request')
    required={str((run/n).relative_to(root)) for n in ['model_calls.json','embedding_calls.json','stages.json','execution_recipe.json','trajectories.json','log/__session__/2/0_factor_propose']}
    if not required.issubset({r['path'] for r in proof['bindings']}):raise ValueError('Missing observed-prefix binding')
    for r in proof['bindings']:
        if sha256(root/r['path'])!=r['sha256']:raise ValueError('Observed prefix changed: '+r['path'])
    stages=json.loads((run/'stages.json').read_text())
    seq=[(i,s) for i in range(2) for s in ['factor_propose','factor_construct','factor_calculate','factor_backtest','feedback']]+[(2,'factor_propose'),(2,'factor_construct')]
    if [(r['loop_index'],r['stage']) for r in stages]!=seq or not all(r['completed'] for r in stages[:-1]):raise ValueError('Unexpected observed stage sequence')
    last=stages[-1]
    if last['completed'] or last['error_type']!='MeteredStop' or last['model_calls_before']!=73 or last['model_calls_after']!=215:raise ValueError('Abort stage changed')
    if require_replay:
        replay=json.loads((run/'observed_abort_replay_validation.json').read_text())
        if replay.get('status')!='pass' or replay.get('early_abort_evidence_sha256')!=sha256(p):raise ValueError('Exact observed-abort replay required')
        if replay.get('attempted_rounds')!=3 or replay.get('native_five_attempt_budget_complete') is not False or replay.get('strict_primary_eligibility') is not False:raise ValueError('Replay overclaims planned-round completion')
        if replay.get('network_calls')!=0 or replay.get('ledger_mutations')!=0 or replay.get('difference_count')!=0:raise ValueError('Abort replay is not exact and read-only')
        if set(replay.get('artifact_hashes',{})) != {'model_calls.json','embedding_calls.json','stages.json','trajectories.json'}:
            raise ValueError('Observed replay artifact set incomplete')
        for name,r in replay['artifact_hashes'].items():
            if sha256(run/name)!=r['original_sha256']:raise ValueError('Replayed early-abort artifact changed')
            if sha256(run.parent/(run.name+'_observed_abort_replay')/name)!=r['replay_sha256']:raise ValueError('Observed replay output changed')
    return done
