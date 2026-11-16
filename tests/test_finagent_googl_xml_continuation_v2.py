"""Focused fail-closed transition tests; no native/financial runtime fixtures."""
from pathlib import Path
import sys,json
import pytest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parents[1]/'scripts')]
import finagent_googl_xml_continuation_evidence_v2 as e

def probe():
    return dict(status='all_original_completed_prefixes_and_single_alias_match',probe_status='pass_expected_stop_before_new_request_not_full_replay',records=282,network_calls=0,ledger_mutations=0,full_source_completion_claim=False,prefixes=[dict(arm='shared_training',records=250,difference_count=0,maximum_numeric_difference=0),dict(arm='native_causal',records=32,difference_count=0,maximum_numeric_difference=0)])

def test_real_population_header_accepted():e.assert_probe_header(probe())

def test_pending_probe_rejected():
    p=probe();p['probe_status']='pending'
    with pytest.raises(ValueError):e.assert_probe_header(p)

def test_only_training_prefix_rejected():
    p=probe();p['prefixes']=p['prefixes'][:1]
    with pytest.raises(ValueError):e.assert_probe_header(p)

def test_economic_difference_rejected():
    p=probe();p['prefixes'][1]['maximum_numeric_difference']=0.01
    with pytest.raises(ValueError):e.assert_probe_header(p)

def test_probe_cannot_claim_full_completion():
    p=probe();p['full_source_completion_claim']=True
    with pytest.raises(ValueError):e.assert_probe_header(p)

def test_wrong_next_request_refused():
    with pytest.raises(ValueError):e.check_new_request({'calls':{}},'other','expected',{})

@pytest.mark.parametrize('status',['reserved','complete','response_unavailable','unknown'])
def test_existing_request_never_admitted_as_new(status):
    with pytest.raises(ValueError):e.check_new_request({'calls':{'expected':{'status':status}}},'expected','expected',{})

def test_retry_mapping_refused():
    with pytest.raises(ValueError):e.check_new_request({'calls':{}},'expected','expected',{'expected':{'attempt':1}})

def test_absent_exact_next_request_allowed():e.check_new_request({'calls':{}},'expected','expected',{})

def test_no_live_constructor_before_prefix_match(tmp_path,monkeypatch):
    ledger=tmp_path/'ledger';ledger.mkdir();(ledger/'project_spend.json').write_text(json.dumps({'calls':{}}))
    out=tmp_path/'run';out.mkdir();constructed=[]
    def live(*a,**k):constructed.append(True);raise AssertionError('Premature paid-meter construction')
    def missing(self,*a,**k):raise RuntimeError('Offline response is not complete in the frozen cache: expected')
    def reject(*a,**k):raise ValueError('Prefix differs')
    monkeypatch.setattr(e.ReadOnlyReplay,'request',missing);monkeypatch.setattr(e,'validate_all_prefixes',reject)
    cls=e.make_gated_meter(live,out,{}, {}, {'first_absent_future_request_hash':'expected'})
    meter=cls(ledger,'unused','model',study='fixture')
    with pytest.raises(ValueError,match='Prefix differs'):meter.request('chat/completions',{})
    assert constructed==[] and not (out/'live_prefix_gate.json').exists()

def test_fresh_reservation_appearing_after_snapshot_refused(tmp_path,monkeypatch):
    ledger=tmp_path/'ledger';ledger.mkdir();p=ledger/'project_spend.json';p.write_text(json.dumps({'calls':{}}))
    out=tmp_path/'run';out.mkdir();constructed=[]
    def live(*a,**k):constructed.append(True);raise AssertionError('Premature paid-meter construction')
    def missing(self,*a,**k):raise RuntimeError('Offline response is not complete in the frozen cache: expected')
    monkeypatch.setattr(e.ReadOnlyReplay,'request',missing);monkeypatch.setattr(e,'validate_all_prefixes',lambda *a,**k:{})
    meter=e.make_gated_meter(live,out,{}, {}, {'first_absent_future_request_hash':'expected'})(ledger,'unused','model',study='fixture')
    p.write_text(json.dumps({'calls':{'expected':{'status':'reserved'}}}))
    with pytest.raises(ValueError,match='Existing request'):meter.request('chat/completions',{})
    assert constructed==[] and not (out/'live_prefix_gate.json').exists()

def test_live_meter_created_only_after_persisted_gate_and_trace_preserved(tmp_path,monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(e,'ROOT',tmp_path)
    ledger=tmp_path/'ledger';ledger.mkdir();(ledger/'project_spend.json').write_text(json.dumps({'calls':{}}))
    (tmp_path/'probe.json').write_text('{}');(tmp_path/e.PROTOCOL).parent.mkdir(parents=True);(tmp_path/e.PROTOCOL).write_text('{}')
    out=tmp_path/'run';out.mkdir();seen=[]
    class Live:
        def __init__(self,*a,**k):
            assert json.loads((out/'live_prefix_gate.json').read_text())['records']==282
            self.initial_cache=SimpleNamespace(request_trace=[]);seen.append((a,k))
        def request(self,*a,**k):
            assert self.initial_cache.request_trace is self.request_trace
            self.request_trace.append({'request_hash':'expected'});return {'id':'new'},'expected'
    def missing(self,*a,**k):raise RuntimeError('Offline response is not complete in the frozen cache: expected')
    monkeypatch.setattr(e.ReadOnlyReplay,'request',missing);monkeypatch.setattr(e,'validate_all_prefixes',lambda *a,**k:{'records':282})
    meter=e.make_gated_meter(Live,out,{'probe_path':'probe.json'}, {}, {'first_absent_future_request_hash':'expected'})(ledger,'unused','model',study='fixture',offline=False)
    meter.request_trace.append({'request_hash':'cached'})
    assert meter.request('chat/completions',{})==({'id':'new'},'expected')
    assert len(seen)==1 and [x['request_hash'] for x in meter.request_trace]==['cached','expected']
