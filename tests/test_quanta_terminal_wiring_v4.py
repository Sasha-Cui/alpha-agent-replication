"""Guard the one observed terminal telemetry extension; do not ignore its body."""
from pathlib import Path
import sys,copy
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from quanta_continued_source_admission_v4 import validate_terminal_parameter_wiring,exact

def fixture():
 old={'constructor_limits':{'base_features':6,'duplication':5,'symbol_length':250},'native_file_edits':0,'prompt_edits':[{'before_sha256':'old','after_sha256':'new','path':'fixed'}],'reference_zoo_reconstructed':False,'round_boundary_events':[]}
 part=copy.deepcopy(old);done=copy.deepcopy(old)
 done['round_boundary_events']=[{'phase_method':'_get_mutation_task','round':5,'round_limit':5}]
 state={'current_round':5,'current_phase':'mutation','config':{'max_rounds':5}}
 return old,part,done,state

def test_exact_terminal_extension_is_required_and_not_ignored():
 receipt=validate_terminal_parameter_wiring(*fixture());assert receipt['completed_events_ignored'] is False and receipt['full_replay_must_match_entire_completed_wiring'] is True

@pytest.mark.parametrize('field',['constructor_limits','native_file_edits','prompt_edits','reference_zoo_reconstructed'])
def test_any_static_parameter_change_refused(field):
 old,part,done,state=fixture();done[field]='altered'
 with pytest.raises(ValueError):validate_terminal_parameter_wiring(old,part,done,state)

@pytest.mark.parametrize('events',[[],[{'phase_method':'_get_crossover_task','round':5,'round_limit':5}],[{'phase_method':'_get_mutation_task','round':6,'round_limit':5}],[{'phase_method':'_get_mutation_task','round':5,'round_limit':6}],[{'phase_method':'_get_mutation_task','round':5,'round_limit':5}]*2])
def test_missing_altered_or_duplicate_boundary_refused(events):
 old,part,done,state=fixture();done['round_boundary_events']=events
 with pytest.raises(ValueError):validate_terminal_parameter_wiring(old,part,done,state)

@pytest.mark.parametrize('field,value',[('current_round',4),('current_phase','crossover'),('config',{'max_rounds':6})])
def test_event_requires_matching_saved_controller_state(field,value):
 old,part,done,state=fixture();state[field]=value
 with pytest.raises(ValueError):validate_terminal_parameter_wiring(old,part,done,state)

def test_partial_prefix_change_refused():
 old,part,done,state=fixture();part['round_boundary_events']=copy.deepcopy(done['round_boundary_events'])
 with pytest.raises(ValueError):validate_terminal_parameter_wiring(old,part,done,state)

def test_original_boundary_cannot_be_rewritten_as_empty():
 old,part,done,state=fixture();old['round_boundary_events']=copy.deepcopy(done['round_boundary_events']);part=copy.deepcopy(old)
 with pytest.raises(ValueError):validate_terminal_parameter_wiring(old,part,done,state)

def test_new_wiring_field_refused():
 old,part,done,state=fixture();done['unknown']='value'
 with pytest.raises(ValueError):validate_terminal_parameter_wiring(old,part,done,state)

def test_full_replay_still_compares_the_whole_completed_telemetry():
 old,part,done,state=fixture();validate_terminal_parameter_wiring(old,part,done,state)
 with pytest.raises(ValueError):exact(done,old,'completed_source_vs_incomplete_replay')
 exact(done,copy.deepcopy(done),'entire_completed_wiring')
