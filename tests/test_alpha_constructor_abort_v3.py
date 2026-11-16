"""Synthetic witnesses test identity gates; no economic/source execution credit."""
import sys,json,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from alpha_evolve.openrouter_budget import sha256
from alpha_constructor_abort_v3 import CASES,run_name,verify_stages,validate,validate_five,replay_filename

def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x))
def fixture(tmp_path,trial):
    c=CASES[trial];r=tmp_path/run_name(trial);r.mkdir()
    stages=[dict(loop_index=i,stage=s,completed=True) for i in range(c['round']) for s in ['factor_propose','factor_construct','factor_calculate','factor_backtest','feedback']]+[dict(loop_index=c['round'],stage='factor_propose',completed=True),dict(loop_index=c['round'],stage='factor_construct',completed=False,error_type='MeteredStop',model_calls_before=c['before'],model_calls_after=c['calls'])]
    save(r/'stages.json',stages)
    names=['model_calls.json','embedding_calls.json','execution_recipe.json','trajectories.json',f"log/__session__/{c['round']}/0_factor_propose"]
    for n in names:save(r/n,{'SYNTHETIC_FIXTURE':True})
    names+=['stages.json'];e={'trial':trial,'witness':c,'bindings':[{'path':str((r/n).relative_to(tmp_path)),'sha256':sha256(r/n)} for n in names]};save(r/'constructor_abort_evidence_v3.json',e)
    attempts=c['round']+1;d={'status':'native_final_attempt_failed' if attempts==5 else 'native_early_abort','planned_rounds':5,'attempted_rounds':attempts,'completed_trajectories':c['round'],'model_calls':c['calls'],'failed_round_indices':[c['round']],'unattempted_round_indices':list(range(attempts,5)),'native_five_attempt_budget_complete':attempts==5,'constructor_abort_evidence_sha256':sha256(r/'constructor_abort_evidence_v3.json')};save(r/'execution_exit.json',d)
    return r,d,e,stages

def test_early14_is_not_five(tmp_path):
    r,_,_,_=fixture(tmp_path,14);validate(r,root=tmp_path,require_replay=False)
    with pytest.raises(ValueError,match='all five'):validate_five(r,root=tmp_path,require_replay=False)

def test_final15_requires_replay_before_full_gate(tmp_path):
    r,_,_,_=fixture(tmp_path,15);assert validate_five(r,root=tmp_path,require_replay=False)['attempted_rounds']==5
    with pytest.raises(FileNotFoundError):validate_five(r,root=tmp_path)

def test_early_cannot_be_relabelled_final(tmp_path):
    r,d,_,_=fixture(tmp_path,14);d['attempted_rounds']=5;d['status']='native_final_attempt_failed';save(r/'execution_exit.json',d)
    with pytest.raises(ValueError,match='counts'):validate(r,root=tmp_path,require_replay=False)

def test_wrong_witness_key_rejected(tmp_path):
    r,d,e,_=fixture(tmp_path,14);e=copy.deepcopy(e);e['witness']['key']=CASES[15]['key'];save(r/'constructor_abort_evidence_v3.json',e);d['constructor_abort_evidence_sha256']=sha256(r/'constructor_abort_evidence_v3.json');save(r/'execution_exit.json',d)
    with pytest.raises(ValueError,match='identity'):validate(r,root=tmp_path,require_replay=False)

def test_missing_prior_stage_rejected(tmp_path):
    _,_,_,stages=fixture(tmp_path,15)
    with pytest.raises(ValueError,match='stage prefix'):verify_stages(stages[1:],CASES[15])

def test_prefix_tamper_rejected(tmp_path):
    r,_,_,_=fixture(tmp_path,14);save(r/'model_calls.json',[])
    with pytest.raises(ValueError,match='artifact changed'):validate(r,root=tmp_path,require_replay=False)

def test_empty_replay_proof_rejected(tmp_path):
    r,d,_,_=fixture(tmp_path,15)
    save(r/replay_filename(15),{'status':'pass','difference_count':0,'network_calls':0,'ledger_mutations':0,'attempted_rounds':5,'failed_round_indices':[4],'constructor_abort_evidence_sha256':d['constructor_abort_evidence_sha256'],'artifact_hashes':{}})
    with pytest.raises(ValueError,match='artifact set'):validate(r,root=tmp_path)
