"""Focused identity, cache and exact-boundary guards; no economic/runtime fixtures."""
from pathlib import Path
import hashlib,sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from quanta_walltime_reconstruction_v3 import select_identity,checked_cache_bytes,assert_recorded_request,assert_boundary_counts

def test_loop_and_pool_ids_are_not_substituted():
    assert select_identity('loop','k',{'k':'loop'},{'k':'pool'})=='loop'
    assert select_identity('pool','k',{'k':'loop'},{'k':'pool'})=='pool'

def test_unfinished_loop_never_invents_pool_id():
    with pytest.raises(ValueError):select_identity('pool','unfinished',{'unfinished':'known'}, {})

def test_identity_outside_native_context_refused():
    with pytest.raises(ValueError):select_identity(None,'k',{'k':'a'},{'k':'b'})

def test_cache_bytes_are_hash_bound(tmp_path):
    p=tmp_path/'cache.pkl';p.write_bytes(b'known');row={'copy':'cache.pkl','bytes':5,'sha256':hashlib.sha256(b'known').hexdigest()}
    assert checked_cache_bytes(row,tmp_path)==b'known'
    p.write_bytes(b'other')
    with pytest.raises(ValueError):checked_cache_bytes(row,tmp_path)

def test_cache_size_change_refused(tmp_path):
    (tmp_path/'cache.pkl').write_bytes(b'known')
    with pytest.raises(ValueError):checked_cache_bytes({'copy':'cache.pkl','bytes':4,'sha256':hashlib.sha256(b'known').hexdigest()},tmp_path)

def test_recorded_chat_sequence_exact():
    assert assert_recorded_request('chat/completions',0,'c',['c'],['e'],'o')=='recorded'
    with pytest.raises(ValueError):assert_recorded_request('chat/completions',0,'different',['c'],['e'],'o')

def test_orphan_must_be_exact_next_chat():
    assert assert_recorded_request('chat/completions',1,'o',['c'],['e'],'o')=='orphan'
    with pytest.raises(ValueError):assert_recorded_request('chat/completions',1,'new',['c'],['e'],'o')

def test_embedding_sequence_and_future_stop():
    assert assert_recorded_request('embeddings',0,'e',['c'],['e'],'o')=='recorded'
    assert assert_recorded_request('embeddings',1,'future',['c'],['e'],'o')=='future_boundary'
    with pytest.raises(ValueError):assert_recorded_request('embeddings',0,'wrong',['c'],['e'],'o')

def test_chat_after_orphan_is_stopped():assert assert_recorded_request('chat/completions',2,'future',['c'],['e'],'o')=='future_boundary'

def test_unknown_endpoint_refused():
    with pytest.raises(ValueError):assert_recorded_request('other',0,'x',[],[],'o')

@pytest.mark.parametrize('counts',[(2259,373,419,33,34),(2260,372,419,33,34),(2260,373,418,33,34),(2260,373,419,32,34),(2260,373,419,33,33)])
def test_no_boundary_credit_before_entire_recorded_state(counts):
    with pytest.raises(ValueError):assert_boundary_counts(*counts,{'chat_count':2259,'embedding_count':373,'quality_event_count':419,'pool_count':33,'loop_count':34})

def test_complete_observed_prefix_boundary_is_admissible():assert_boundary_counts(2260,373,419,33,34,{'chat_count':2259,'embedding_count':373,'quality_event_count':419,'pool_count':33,'loop_count':34})

from quanta_walltime_reconstruction_v3 import permit_library_process

def test_real_ctypes_blosc2_link_trace_shape_allowed():
    assert permit_library_process(['/bin/gcc','-Wl,-t','-o','/tmp/probe','-lblosc2'],stdlib_verified=True,function='_findLib_gcc',library='blosc2',temporary_output='/tmp/probe')

def test_compiler_without_verified_ctypes_stack_refused():
    assert not permit_library_process(['/bin/gcc','-Wl,-t','-o','/tmp/probe','-lblosc2'],function='_findLib_gcc',library='blosc2',temporary_output='/tmp/probe')

def test_factor_and_native_model_commands_refused():
    assert not permit_library_process(['python','factor.py'],stdlib_verified=True,function='_findLib_gcc',library='blosc2')
    assert not permit_library_process(['python','run_quantaalpha_child_v2.py','conf.yaml'])

def test_shell_and_executable_overrides_refused():
    assert not permit_library_process(['/sbin/ldconfig','-p'],shell=True)
    assert not permit_library_process(['/sbin/ldconfig','-p'],executable='python')

def test_ld_metadata_requires_only_library_search_arguments():
    assert permit_library_process(['ld','-t','-L','/known/lib','-o','/dev/null','-lblosc2'],stdlib_verified=True,function='_findLib_ld',library='blosc2')
    assert not permit_library_process(['ld','-t','factor.o','-o','/dev/null','-lblosc2'],stdlib_verified=True,function='_findLib_ld',library='blosc2')

def test_unrelated_library_or_output_refused():
    assert not permit_library_process(['/bin/gcc','-Wl,-t','-o','/tmp/other','-lblosc2'],stdlib_verified=True,function='_findLib_gcc',library='blosc2',temporary_output='/tmp/probe')
    assert not permit_library_process(['/bin/gcc','-Wl,-t','-o','/tmp/probe','-lother'],stdlib_verified=True,function='_findLib_gcc',library='other',temporary_output='/tmp/probe')
