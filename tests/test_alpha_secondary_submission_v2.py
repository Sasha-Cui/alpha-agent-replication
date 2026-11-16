"""Synthetic scheduler/preflight guards; no submission or economic credit."""
import sys,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from submit_alpha_secondary_v2 import planned_units,require_no_outputs,preflight,submit_steps

def test_missing_parent_refuses_before_submission(tmp_path):
    with pytest.raises(ValueError,match='submit nothing'):preflight(tmp_path)
    assert not (tmp_path/'artifacts/fidelity_completion_v2/alpha_secondary_jobs.json').exists()

def test_all20_trials_no_baseline_refits():
    units=planned_units();assert [r['trial'] for r in units]==list(range(1,21))
    assert len({r['library'] for r in units})==20
    assert sum(len(r['arms']) for r in units)==40
    assert all(set(r['arms'])=={'source4_plus_library','alpha158_plus_library'} for r in units)

def test_existing_partial_output_refused(tmp_path):
    private=tmp_path/'private';public=tmp_path/'public';require_no_outputs(private,public)
    (private/'alphaagent_rounds_paper_gpt35_08_oos_alpha158_plus_library_open_information').mkdir(parents=True)
    with pytest.raises(ValueError,match='inspection'):require_no_outputs(private,public)

def test_whole_array_dependencies_and_common_baseline():
    calls=[];saved=[];record={'jobs':{},'preflight':{'existing_primary_opening_dependency':'777'}}
    def submit(role,script,args,deps):
        calls.append((role,script,args,deps));return str(101+len(calls)-1)
    submit_steps(record,submit,lambda x:saved.append(copy.deepcopy(x)))
    assert len(calls)==6 and record['status']=='all_six_jobs_submitted_not_completed'
    assert calls[1][3]==['101'] and calls[3][3]==['101']
    assert calls[2][3]==['102'] and calls[4][3]==['104']
    assert calls[5][3]==['103','105','777']
    assert all('pending_submission' in saved[i] for i in [0,2,4,6,8,10])
    assert 'pending_submission' not in saved[-1]

def test_uncertain_submission_does_not_continue():
    calls=[];saved=[];record={'jobs':{},'preflight':{'existing_primary_opening_dependency':None}}
    def submit(role,script,args,deps):
        calls.append(role);return '101' if len(calls)==1 else 'ambiguous'
    with pytest.raises(ValueError,match='Uncertain'):submit_steps(record,submit,lambda x:saved.append(copy.deepcopy(x)))
    assert len(calls)==2 and record['jobs']=={'trial_libraries':'101'}
    assert record['pending_submission']['role']=='source4_plus_library'
    assert saved[-1]['pending_submission']['role']=='source4_plus_library'
