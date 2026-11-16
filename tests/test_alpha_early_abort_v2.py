"""Software-only incomplete-trial guards; no economic or replication credit."""
import sys,json,shutil
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from alpha_evolve.openrouter_budget import sha256
from fidelity_alpha_early_abort_v2 import validate_early_abort,RUN_NAME,FAILED_KEY
from fidelity_alpha_terminal_v2 import validate_alpha_five_attempts

def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x))
def fixture(tmp_path):
    r=tmp_path/RUN_NAME;r.mkdir()
    stages=[dict(loop_index=i,stage=s,completed=True) for i in range(2) for s in ['factor_propose','factor_construct','factor_calculate','factor_backtest','feedback']]
    stages += [dict(loop_index=2,stage='factor_propose',completed=True),dict(loop_index=2,stage='factor_construct',completed=False,error_type='MeteredStop',model_calls_before=73,model_calls_after=215)]
    save(r/'stages.json',stages)
    for n in ['model_calls.json','embedding_calls.json','execution_recipe.json','trajectories.json','log/__session__/2/0_factor_propose']:save(r/n,{'SYNTHETIC_SOFTWARE_FIXTURE':True})
    files=list(r.glob('*.json'))+[r/'log/__session__/2/0_factor_propose']
    proof={'failed_request_hash':FAILED_KEY,'bindings':[{'path':str(p.relative_to(tmp_path)),'sha256':sha256(p)} for p in files]};save(r/'early_abort_evidence.json',proof)
    done={'status':'native_early_abort','planned_rounds':5,'attempted_rounds':3,'completed_trajectories':2,'failed_round_indices':[2],'unattempted_round_indices':[3,4],'model_calls':215,'native_five_attempt_budget_complete':False,'strict_primary_eligibility':False,'early_abort_evidence_sha256':sha256(r/'early_abort_evidence.json')};save(r/'execution_exit.json',done)
    return r,done

def test_observed_abort_does_not_satisfy_primary(tmp_path):
    r,_=fixture(tmp_path);validate_early_abort(r,root=tmp_path,require_replay=False)
    with pytest.raises(ValueError,match='all five'):validate_alpha_five_attempts(r,root=tmp_path)

def test_unattempted_rounds_cannot_be_hidden(tmp_path):
    r,d=fixture(tmp_path);d['unattempted_round_indices']=[];save(r/'execution_exit.json',d)
    with pytest.raises(ValueError,match='identity/count/scope'):validate_early_abort(r,root=tmp_path,require_replay=False)

def test_five_round_relabel_refused(tmp_path):
    r,d=fixture(tmp_path);d['attempted_rounds']=5;save(r/'execution_exit.json',d)
    with pytest.raises(ValueError):validate_alpha_five_attempts(r,root=tmp_path)
    with pytest.raises(ValueError):validate_early_abort(r,root=tmp_path,require_replay=False)

def test_altered_prefix_refused(tmp_path):
    r,_=fixture(tmp_path);save(r/'model_calls.json',[])
    with pytest.raises(ValueError,match='prefix changed'):validate_early_abort(r,root=tmp_path,require_replay=False)

def test_diagnostic_replay_cannot_claim_primary_credit(tmp_path):
    r,_=fixture(tmp_path)
    v={'status':'pass','early_abort_evidence_sha256':sha256(r/'early_abort_evidence.json'),'attempted_rounds':3,'native_five_attempt_budget_complete':False,'strict_primary_eligibility':False,'network_calls':0,'ledger_mutations':0,'difference_count':0,'artifact_hashes':{}}
    target=r.parent/(r.name+'_observed_abort_replay');target.mkdir()
    for name in ['model_calls.json','embedding_calls.json','stages.json','trajectories.json']:
        shutil.copy2(r/name,target/name)
        v['artifact_hashes'][name]={'original_sha256':sha256(r/name),'replay_sha256':sha256(target/name)}
    save(r/'observed_abort_replay_validation.json',v);validate_early_abort(r,root=tmp_path)
    v['strict_primary_eligibility']=True;save(r/'observed_abort_replay_validation.json',v)
    with pytest.raises(ValueError,match='overclaims'):validate_early_abort(r,root=tmp_path)


def test_empty_replay_artifact_set_refused(tmp_path):
    r,_=fixture(tmp_path)
    v={'status':'pass','early_abort_evidence_sha256':sha256(r/'early_abort_evidence.json'),'attempted_rounds':3,'native_five_attempt_budget_complete':False,'strict_primary_eligibility':False,'network_calls':0,'ledger_mutations':0,'difference_count':0,'artifact_hashes':{}}
    save(r/'observed_abort_replay_validation.json',v)
    with pytest.raises(ValueError,match='artifact set incomplete'):validate_early_abort(r,root=tmp_path)
