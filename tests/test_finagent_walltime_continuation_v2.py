"""Fail-closed tests for returned-response accounting and continuation boundaries."""
from pathlib import Path
import sys,copy,json
import pytest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parents[1]/'scripts')]
import finagent_walltime_evidence_v2 as e

def body():
    x={'endpoint':'embeddings','request':{'model':'openai/text-embedding-3-large','input':[[1,2]],'provider':{'order':['OpenAI'],'allow_fallbacks':False}},'response':{'data':[{'index':0,'embedding':[0.1]*3072}],'usage':{'cost':0.00001}}}
    x['request_hash']=e.identity({k:x[k] for k in ['endpoint','request']});return x

def before():return {'status':'reserved','study':'fidelity_v2_finagent_source_settings','endpoint':'embeddings','model':'openai/text-embedding-3-large','pid':123,'reserved_usd':0.0001}

def test_full_reserved_charge_retained():
    b=before();a=e.conservative_completed_entry(b,body(),12,'digest')
    assert a['cost_usd']==b['reserved_usd'] and a['reserved_usd']==b['reserved_usd'] and a['reported_usage_cost_usd']==0.00001 and b['status']=='reserved'
    assert a['pid']==b['pid'] and a['response_journal_offset']==12

@pytest.mark.parametrize('field,value',[('status','complete'),('status','unknown'),('study','finagent_native_v1'),('study','fidelity_v2_quantaalpha_fresh_search'),('endpoint','chat/completions'),('model','another')])
def test_unrelated_requests_refused(field,value):
    b=before();b[field]=value
    with pytest.raises(ValueError):e.conservative_completed_entry(b,body(),12,'digest')

def test_changed_request_identity_refused():
    x=body();x['request']['input']=[[3,4]]
    with pytest.raises(ValueError):e.conservative_completed_entry(before(),x,12,'digest')

def test_wrong_vector_dimensions_refused():
    x=body();x['response']['data'][0]['embedding'].pop()
    with pytest.raises(ValueError):e.conservative_completed_entry(before(),x,12,'digest')

def test_price_over_reservation_refused():
    x=body();x['response']['usage']['cost']=0.001
    with pytest.raises(ValueError):e.conservative_completed_entry(before(),x,12,'digest')

def test_retry_envelope_refused():
    x=body();x['technical_recovery']={'attempt':1}
    with pytest.raises(ValueError):e.conservative_completed_entry(before(),x,12,'digest')

@pytest.mark.parametrize('status',['reserved','complete','response_unavailable','unsupported'])
def test_existing_future_request_refused(status):
    with pytest.raises(ValueError):e.assert_future_request({'calls':{'k':{'status':status}}},'k',{'future_envelopes':[{'key':'k'}]}, {})

def test_unknown_future_body_refused():
    with pytest.raises(ValueError):e.assert_future_request({'calls':{}},'other',{'future_envelopes':[{'key':'k'}]}, {})

def test_actual_concurrent_stop_set_accepted():
    e.assert_future_request({'calls':{}},'k2',{'future_envelopes':[{'key':'k1'},{'key':'k2'}]}, {})

def test_retry_mapping_blocks_new_request():
    with pytest.raises(ValueError):e.assert_future_request({'calls':{}},'k',{'future_envelopes':[{'key':'k'}]}, {'k':{'attempt':1}})

def test_no_live_constructor_when_prefix_fails(tmp_path,monkeypatch):
    root=tmp_path/'ledger';root.mkdir();(root/'project_spend.json').write_text('{"calls":{}}');out=tmp_path/'out';out.mkdir();constructed=[]
    def live(*a,**k):constructed.append(True);raise AssertionError('Premature live meter')
    def missing(self,*a,**k):raise RuntimeError('Offline response is not complete in the frozen cache: k')
    def reject(*a,**k):raise ValueError('Changed prefix')
    monkeypatch.setattr(e.ReadOnlyReplay,'request',missing);monkeypatch.setattr(e,'prefix_check',reject)
    cls=e.gated_meter(live,out,{'future_envelopes':[{'key':'k'}]},{});meter=cls(root,'unused','model',study='fixture')
    with pytest.raises(ValueError,match='Changed prefix'):meter.request('embeddings',{})
    assert not constructed and not (out/'live_prefix_gate.json').exists()
