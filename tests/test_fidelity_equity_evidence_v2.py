"""Guard tests for final account admission, without financial fixture duplication."""
from pathlib import Path
import sys,copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fidelity_equity_evidence_v2 import assert_replay_header,final_output_guard

def base():return dict(status='pass',difference_count=0,differences=[],records=412,replay_records=412,case='FinMem',network_allowed=False,ledger_mutations_allowed=False)

def test_pending_replay_rejected():
    p=base();p['status']='pending'
    with pytest.raises(ValueError,match='not passed'):assert_replay_header(p,'finmem',412)

def test_dropped_records_rejected():
    p=base();p['replay_records']=411
    with pytest.raises(ValueError,match='population'):assert_replay_header(p,'finmem',412)

def test_unresolved_difference_rejected():
    p=base();p['difference_count']=1
    with pytest.raises(ValueError):assert_replay_header(p,'finmem',412)

def test_network_permission_rejected():
    p=base();p['network_allowed']=True
    with pytest.raises(ValueError,match='read-only'):assert_replay_header(p,'finmem',412)

def test_case_substitution_rejected():
    p=base();p['case']='FinAgent'
    with pytest.raises(ValueError,match='substituted'):assert_replay_header(p,'finmem',412)

def test_frozen_schema_does_not_invent_missing_network_fields():
    p=base();p['case']='finmem';del p['network_allowed'];del p['ledger_mutations_allowed']
    assert_replay_header(p,'finmem',412,frozen=True)
    with pytest.raises(ValueError):assert_replay_header(p,'finmem',412)

def test_partial_or_complete_final_outputs_are_not_overwritten(tmp_path):
    public=tmp_path/'public';private=tmp_path/'private';final_output_guard(public,private)
    private.mkdir()
    with pytest.raises(ValueError,match='Preserve'):final_output_guard(public,private)
