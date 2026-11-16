"""Software-only parameter-sensitivity planning and inference guards."""
from pathlib import Path
import sys,json,hashlib,shutil
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from submit_quanta_paper_eval_v2 import planned_submissions
from quanta_paper_evaluation_evidence_v2 import protocol,source_gate,SCOPE,SOURCE_RUN
from analyze_quanta_paper_parameter_v2 import paired_exploratory

def save_protocol(tmp_path):
    pub=tmp_path/'paper_runs/fidelity_completion_v2/quanta_paper_parameter_evaluation_protocol.json';pub.parent.mkdir(parents=True)
    doc={'scope':SCOPE,'source_run':SOURCE_RUN,'new_primary_substitution':False,'new_llm_api_calls':0,'frozen_context':{}};pub.write_text(json.dumps(doc))
    frozen=tmp_path/'artifacts/fidelity_completion_v2/quanta_paper_eval_setup_20260918'/pub.name;frozen.parent.mkdir(parents=True);shutil.copy2(pub,frozen)
    return pub

def test_causality_uses_actual_program_population():
    plan=planned_submissions(37);assert plan[0]==('proof','0-36%2');assert [x[0] for x in plan]==['proof','library','models','opening','analysis']
    assert plan[2][1]==plan[3][1]=='0-1%2'

def test_no_invented_empty_program_run():
    for n in [0,-1,True,3.5]:
        with pytest.raises(ValueError):planned_submissions(n)

def test_incomplete_source_never_becomes_economic_job(tmp_path):
    save_protocol(tmp_path)
    with pytest.raises(ValueError,match='source gates incomplete'):source_gate(tmp_path)

def test_mutated_protocol_is_rejected(tmp_path):
    p=save_protocol(tmp_path);protocol(tmp_path);d=json.loads(p.read_text());d['new_primary_substitution']=True;p.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='Frozen'):protocol(tmp_path)

def test_calendar_intersection_refused():
    a=pd.Series(np.zeros(963));b=pd.Series(np.zeros(962))
    with pytest.raises(ValueError,match='calendars'):paired_exploratory(a,b)

def test_degenerate_comparison_cannot_promote_primary():
    result=paired_exploratory(pd.Series(np.full(963,.001)),pd.Series(np.zeros(963)))
    assert result['degenerate_sampling_variation'] and result['project_family_significance_claim'] is False
    assert result['original_primary_replaced'] is False and result['original54_family_complete'] is False
