from pathlib import Path
import sys,copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from quanta_paper_evaluation_evidence_v7 import validate_continued_proof

def fixture():
 program={'sha256':'code','uses':[{'experiment_index':3,'column':'factor'}]};receipt={'matrix_guard':'bound'}
 proof={'status':'pass','code_sha256':'code','driver_sha256':'driver','child_sha256':'child','continued_native_matrix_lineage':receipt,'comparisons':[{'cutoff':c,'status':'pass','rows':10} for c in ['2019-12-31','2020-12-31','2021-12-31','2024-12-31']],'native_matrix_checks':[{'experiment_index':3,'column':'factor','status':'pass','rows':5}],'network_calls_permitted':False,'raw_infinite_values_present':False}
 return proof,program,receipt

def test_current_complete_proof_accepted():
 proof,program,receipt=fixture();validate_continued_proof(proof,program,receipt,'driver','child')

@pytest.mark.parametrize('field',['driver_sha256','child_sha256','continued_native_matrix_lineage','code_sha256','status'])
def test_changed_proof_method_or_lineage_refused(field):
 proof,program,receipt=fixture();proof[field]='changed'
 with pytest.raises(ValueError):validate_continued_proof(proof,program,receipt,'driver','child')

def test_missing_cutoff_refused():
 proof,program,receipt=fixture();proof['comparisons'].pop()
 with pytest.raises(ValueError):validate_continued_proof(proof,program,receipt,'driver','child')

def test_missing_native_use_refused():
 proof,program,receipt=fixture();proof['native_matrix_checks']=[]
 with pytest.raises(ValueError):validate_continued_proof(proof,program,receipt,'driver','child')

def test_reassigned_matrix_use_refused():
 proof,program,receipt=fixture();proof['native_matrix_checks'][0]['experiment_index']=4
 with pytest.raises(ValueError):validate_continued_proof(proof,program,receipt,'driver','child')

def test_infinity_flag_retained_not_a_failure_by_itself():
 proof,program,receipt=fixture();proof['comparisons'][0]['infinite_values']=2;proof['raw_infinite_values_present']=True;validate_continued_proof(proof,program,receipt,'driver','child')
 proof['raw_infinite_values_present']=False
 with pytest.raises(ValueError):validate_continued_proof(proof,program,receipt,'driver','child')
