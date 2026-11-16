"""Validate five attempted rounds, including one exactly witnessed terminal failure."""
import json
from pathlib import Path
from alpha_evolve.openrouter_budget import sha256
FAILED_KEY='aa8d6503fc69f4c4f42d5561fc1c6110baeb88181c4d033efb85fe0fe7d64b91'
FAILED_RUN='alphaagent_rounds_paper_gpt35_08'

def validate_alpha_five_attempts(run, *, root=None, require_replay=True):
    run=Path(run)
    root=Path(root) if root is not None else Path(__file__).resolve().parents[1]
    done=json.loads((run/'execution_exit.json').read_text())
    if done.get('attempted_rounds')!=5:
        raise ValueError('Alpha trial lacks all five attempted rounds')
    if done.get('status')=='native_round_budget_exhausted':
        return done
    if done.get('status')!='native_final_attempt_failed' or run.name!=FAILED_RUN:
        raise ValueError('Unapproved incomplete Alpha source trial')
    p=run/'terminal_failure_closure.json'
    if sha256(p)!=done.get('terminal_failure_closure_sha256'):
        raise ValueError('Terminal failure evidence changed')
    proof=json.loads(p.read_text())
    if proof.get('status')!='observed_final_attempt_failure_retained' or proof.get('failed_request_hash')!=FAILED_KEY:
        raise ValueError('Terminal failure identity changed')
    if proof.get('failed_round_index')!=4 or proof.get('native_loop_idx')!=4 or proof.get('native_step_idx')!=1:
        raise ValueError('A mid-budget failure cannot be relabelled as five attempted rounds')
    if done.get('failed_round_indices')!=[4] or done.get('completed_trajectories')!=4 or done.get('model_calls')!=110:
        raise ValueError('Final failed attempt or completed history changed')
    required={str((run/n).relative_to(root)) for n in ['model_calls.json','embedding_calls.json','stages.json','execution_recipe.json','trajectories.json','log/__session__/4/0_factor_propose']}
    if not required.issubset({r['path'] for r in proof['bindings']}):
        raise ValueError('Terminal evidence omits required original artifacts')
    for row in proof['bindings']:
        if sha256(root/row['path'])!=row['sha256']:
            raise ValueError('Bound terminal artifact changed: '+row['path'])
    stages=json.loads((run/'stages.json').read_text())
    expected=[(i,s) for i in range(4) for s in ['factor_propose','factor_construct','factor_calculate','factor_backtest','feedback']]+[(4,'factor_propose'),(4,'factor_construct')]
    if [(r['loop_index'],r['stage']) for r in stages]!=expected or not all(r['completed'] for r in stages[:-1]):
        raise ValueError('Terminal trial source stage sequence changed')
    last=stages[-1]
    if last['completed'] or last['error_type']!='MeteredStop' or last['model_calls_after']!=110:
        raise ValueError('Observed terminal failure changed')
    if require_replay:
        replay=json.loads((run/'full_replay_validation.json').read_text())
        if replay.get('status')!='pass' or replay.get('terminal_failure_closure_sha256')!=sha256(p):
            raise ValueError('Exact full replay of terminal-failed trial required')
        if replay.get('network_calls')!=0 or replay.get('ledger_mutations')!=0 or replay.get('difference_count')!=0:
            raise ValueError('Terminal failure replay is not exact/read-only')
        for name,row in replay['artifact_hashes'].items():
            if sha256(run/name)!=row['original_sha256']:
                raise ValueError('Replayed source artifact changed')
    return done
