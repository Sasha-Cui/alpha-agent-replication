"""Software scope guards, never source/market evidence."""
import json,sys,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from alpha_observed_history_evidence_v2 import SCOPE,expected_runs,verify_protocol,complete_catalogue,source_evidence
from fidelity_alpha_terminal_v2 import validate_alpha_five_attempts

def protocol():
    return {'scope':SCOPE,'planned_trials':list(range(1,21)),'run_names':expected_runs(),'existing_early_abort_witnesses':[12],'frozen_context':{},**{k:True for k in ['no_new_llm_calls','no_changed_generation_or_failure_handling','does_not_replace_strict_primary','does_not_complete_original_four_case_family','does_not_enter_original54_secondary_family','original_primary_gates_unchanged']}}

def test_all20_population_refuses_survivor_subset():
    p=protocol();verify_protocol(p);p['planned_trials'].remove(12);p['run_names'].remove(expected_runs()[11])
    with pytest.raises(ValueError,match='population'):verify_protocol(p)

def test_primary_replacement_scope_refused():
    p=protocol();p['does_not_replace_strict_primary']=False
    with pytest.raises(ValueError,match='boundary'):verify_protocol(p)

def test_unwitnessed_new_early_abort_refused():
    p=protocol();p['existing_early_abort_witnesses']=[12,14]
    with pytest.raises(ValueError,match='separate witnessed'):verify_protocol(p)

def test_missing_sources_refuses_catalogue_without_output(tmp_path):
    p=tmp_path/'paper_runs/fidelity_completion_v2';p.mkdir(parents=True)
    (p/'alpha_observed_history_sensitivity_protocol.json').write_text(json.dumps(protocol()))
    with pytest.raises(ValueError,match='All20'):complete_catalogue(tmp_path)
    assert not (tmp_path/'artifacts/fidelity_completion_v2/alpha_observed_history_catalogue').exists()

def test_original_five_round_gate_is_not_relaxed(tmp_path):
    r=tmp_path/'alphaagent_rounds_paper_gpt35_12';r.mkdir()
    (r/'execution_exit.json').write_text(json.dumps({'status':'native_early_abort','attempted_rounds':3}))
    with pytest.raises(ValueError,match='all five'):validate_alpha_five_attempts(r,root=tmp_path)

def test_off_cohort_source_refused_before_reads(tmp_path):
    with pytest.raises(ValueError,match='Unplanned'):source_evidence(tmp_path,tmp_path,'alphaagent_unbounded_pilot',protocol(),'unused','unused')
