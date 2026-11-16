"""Synthetic guard fixtures; no model/economic/replication evidence."""
import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fidelity_alpha_terminal_v2 import validate_alpha_five_attempts,FAILED_RUN,FAILED_KEY
from alpha_evolve.openrouter_budget import sha256

def save(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj))

def fixture(tmp_path):
    run=tmp_path/FAILED_RUN;run.mkdir()
    stages=[dict(loop_index=i,stage=s,completed=True) for i in range(4) for s in ['factor_propose','factor_construct','factor_calculate','factor_backtest','feedback']]
    stages += [dict(loop_index=4,stage='factor_propose',completed=True),dict(loop_index=4,stage='factor_construct',completed=False,error_type='MeteredStop',model_calls_after=110)]
    save(run/'stages.json',stages)
    for n in ['model_calls.json','embedding_calls.json','execution_recipe.json','trajectories.json','log/__session__/4/0_factor_propose']:save(run/n,{'SYNTHETIC_FIXTURE':True})
    files=list(run.glob('*.json'))+[run/'log/__session__/4/0_factor_propose']
    proof=dict(status='observed_final_attempt_failure_retained',failed_request_hash=FAILED_KEY,failed_round_index=4,native_loop_idx=4,native_step_idx=1,bindings=[dict(path=str(p.relative_to(tmp_path)),sha256=sha256(p)) for p in files])
    save(run/'terminal_failure_closure.json',proof)
    done=dict(status='native_final_attempt_failed',attempted_rounds=5,failed_round_indices=[4],completed_trajectories=4,model_calls=110,terminal_failure_closure_sha256=sha256(run/'terminal_failure_closure.json'))
    save(run/'execution_exit.json',done)
    return run,done,proof

def test_normal_five_but_not_four(tmp_path):
    run=tmp_path/'ordinary';save(run/'execution_exit.json',dict(status='native_round_budget_exhausted',attempted_rounds=5))
    validate_alpha_five_attempts(run,root=tmp_path)
    save(run/'execution_exit.json',dict(status='native_round_budget_exhausted',attempted_rounds=4))
    with pytest.raises(ValueError):validate_alpha_five_attempts(run,root=tmp_path)

def test_failure_requires_full_replay(tmp_path):
    run,_,_=fixture(tmp_path)
    validate_alpha_five_attempts(run,root=tmp_path,require_replay=False)
    with pytest.raises(FileNotFoundError):validate_alpha_five_attempts(run,root=tmp_path)

def test_failure_cannot_hide_early_abort(tmp_path):
    run,done,proof=fixture(tmp_path)
    proof['failed_round_index']=3
    save(run/'terminal_failure_closure.json',proof);done['terminal_failure_closure_sha256']=sha256(run/'terminal_failure_closure.json');save(run/'execution_exit.json',done)
    with pytest.raises(ValueError,match='mid-budget'):validate_alpha_five_attempts(run,root=tmp_path,require_replay=False)

def test_original_prefix_tamper_refused(tmp_path):
    run,_,_=fixture(tmp_path);save(run/'model_calls.json',[])
    with pytest.raises(ValueError,match='artifact changed'):validate_alpha_five_attempts(run,root=tmp_path,require_replay=False)

def test_omitted_binding_refused(tmp_path):
    run,done,proof=fixture(tmp_path);proof['bindings']=[]
    save(run/'terminal_failure_closure.json',proof);done['terminal_failure_closure_sha256']=sha256(run/'terminal_failure_closure.json');save(run/'execution_exit.json',done)
    with pytest.raises(ValueError,match='omits'):validate_alpha_five_attempts(run,root=tmp_path,require_replay=False)

def test_replay_substitution_refused(tmp_path):
    run,_,_=fixture(tmp_path)
    save(run/'full_replay_validation.json',dict(status='pass',terminal_failure_closure_sha256='fake'))
    with pytest.raises(ValueError,match='Exact full replay'):validate_alpha_five_attempts(run,root=tmp_path)
