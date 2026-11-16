"""Synthetic software checks; no source/market execution credit."""
from pathlib import Path
import sys,copy
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_alpha_observed_history_v2 import exploratory_result
from submit_alpha_observed_history_v2 import submit_chain,planned_outputs

def test_paired_calendar_mismatch_refused():
    a=pd.Series(np.arange(16)/1000,index=pd.date_range('2025-01-01',periods=16))
    with pytest.raises(ValueError,match='calendars'):exploratory_result(a,a.iloc[:-1])

def test_degenerate_effect_never_becomes_project_significance():
    a=pd.Series(np.zeros(238));b=pd.Series(np.full(238,.001))
    r=exploratory_result(b,a)
    assert r['project_family_significance_claim'] is False and r['strict_primary_eligibility'] is False
    assert r['original_four_case_family_complete'] is False and r['original54_secondary_family_complete'] is False
    assert r['degenerate_sampling_variation'] is True

def test_four_job_scope_and_persisted_intent():
    r={'jobs':{}};calls=[];saved=[]
    def submit(role,script,prev):calls.append((role,prev));return str(800+len(calls))
    submit_chain(r,submit,lambda x:saved.append(copy.deepcopy(x)))
    assert calls==[('library',None),('models','801'),('opening','802'),('analysis','803')]
    assert r['status']=='four_jobs_submitted_not_completed'
    assert all('pending_submission' in saved[i] for i in [0,2,4,6])
    assert len(planned_outputs())==5 and all('observed20' in n for n in planned_outputs())

def test_uncertain_job_does_not_launch_descendants():
    r={'jobs':{}};calls=[]
    def submit(role,script,prev):calls.append(role);return '801' if len(calls)==1 else 'uncertain'
    with pytest.raises(ValueError,match='Uncertain'):submit_chain(r,submit,lambda x:None)
    assert calls==['library','models'] and r['jobs']=={'library':'801'} and r['pending_submission']['role']=='models'
