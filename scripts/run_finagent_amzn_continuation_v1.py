"""Resume only unfinished AMZN after its one exact approved recovery; gate every old prefix."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,fcntl,hashlib,importlib.util,json,socket,sys,threading
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import atomic_json,sha256
from alpha_evolve.publication_replay import ReadOnlyReplay
from validate_publication_replay import compare,read
from finagent_amzn_manual_retry_v1 import AUDIT,KEY,STUDY,identity,require,check_bindings
PRIVATE=ROOT/'artifacts/fidelity_completion_v2';SOURCE=PRIVATE/'finagent_AMZN';REPLAY=PRIVATE/'finagent_AMZN_offline_replay'

def scope():
 s=json.loads((AUDIT/'continuation_protocol.json').read_text())
 for row in s['bindings']:require(sha256(ROOT/row['path'])==row['sha256'],'Frozen continuation dependency changed: '+row['path'])
 check_bindings();return s

def recovery_receipt():
 r=json.loads((AUDIT/'retry_receipt.json').read_text());require(r['status']=='one_exact_retry_complete_original_charge_retained' and r['network_calls']==1 and r['other_entries_changed']==0,'Actual single retry completion required')
 cache=ROOT/'runs/economic_fidelity/openrouter'
 with (cache/'project_spend.lock').open('r') as lock:
  fcntl.flock(lock,fcntl.LOCK_SH);ledger=json.loads((cache/'project_spend.json').read_text());mapping=json.loads((cache/'technical_recoveries.json').read_text())
 require(ledger['calls'].get(KEY)==r['original_after'] and ledger['calls'].get(r['retry_key'])==r['retry_completed_entry'] and mapping.get(KEY)==r['mapping_entry'],'Approved recovery identity/retained charge changed')
 p=AUDIT/'returned_response.jsonl';require(sha256(p)==r['response_sha256'],'Preserved retry response changed')
 with (cache/'cohort_responses.jsonl').open('rb') as f:f.seek(r['response_journal_offset']);line=f.readline()
 require(hashlib.sha256(line).hexdigest()==r['response_sha256'],'Canonical retry response changed')
 return r

def prefixes(out,s):
 results=[]
 for row in s['prefixes']:
  p=ROOT/row['path'];require(sha256(p)==row['sha256'],'Old prefix bytes changed');old=read(p);new=read(out/'decisions.jsonl');require(len(old)==row['records'] and len(new)>=len(old),'Original prefix not reconstructed')
  errors,delta=compare(old,new[:len(old)]);require(not errors and delta[0]==0,'Original reasoning/request/account prefix differs')
  results.append({**row,'difference_count':0,'maximum_numeric_difference':0,'target_sha256':sha256(out/'decisions.jsonl')})
 return results

def assert_future(state,mapping,key):
 require(key not in state['calls'] and key not in mapping,'Existing unresolved request cannot become a new request')

def validate_completion(out,s,offline):
 d=json.loads((out/'completion.json').read_text());require(d['status']=='complete' and d['offline'] is offline and d['steps']==397 and d['arm_counts']=={'shared_training':250,'native_causal':147} and d['validation_future_chart_count']==0,'Complete original planned calendar required')
 for k,v in [('script_sha256',s['driver_sha256']),('recipe_sha256',s['recipe_sha256']),('input_sha256',s['input_sha256']),('decision_sha256',sha256(out/'decisions.jsonl'))]:require(d[k]==v,'Completion binding changed: '+k)
 actual={str(Path(k)):v for k,v in d['source_sha256'].items()};require(actual==s['native_python_sha256'],'Native Python source changed during continuation')
 return {'status':'pass','offline':offline,'records':397,'prefixes':prefixes(out,s),'protocol_sha256':sha256(AUDIT/'continuation_protocol.json'),'retry_receipt_sha256':sha256(AUDIT/'retry_receipt.json'),'decision_sha256':sha256(out/'decisions.jsonl'),'completion_sha256':sha256(out/'completion.json'),'source_completion_is_not_full_paper_claim':True}

def main():
 p=argparse.ArgumentParser();p.add_argument('--replay',action='store_true');a=p.parse_args();s=scope();receipt=recovery_receipt();out=REPLAY if a.replay else SOURCE
 with (PRIVATE/'finagent_AMZN.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if a.replay:
   require(not REPLAY.exists(),'Existing replay/partial output: inspect, never overwrite')
   require(json.loads((SOURCE/'manual_continuation_validation.json').read_text())==validate_completion(SOURCE,s,False),'Source completion receipt missing or changed')
   def deny(*args,**kwargs):raise RuntimeError('AMZN full replay network disabled')
   socket.socket.connect=deny;socket.create_connection=deny
  else:
   require(not (SOURCE/'completion.json').exists() and not (AUDIT/'live_started.json').exists(),'Existing source start/completion: inspect, never duplicate')
   for row in s['original_source_files']:require(sha256(ROOT/row['path'])==sha256(ROOT/row['copy'])==row['sha256'],'Original source preservation changed')
   require(len(read(SOURCE/'decisions.jsonl'))==220,'Original partial population changed')
  driverpath=ROOT/'scripts/run_finagent_fidelity_v2.py';spec=importlib.util.spec_from_file_location('amzn_unchanged_native_driver',driverpath);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
  live_type=driver.WaitingMeter
  class Gate(ReadOnlyReplay):
   def __init__(self,*args,**kwargs):
    self._args=args;self._kwargs=kwargs;self._live=None;self._lock=threading.RLock();super().__init__(*args,**kwargs)
   def request(self,endpoint,payload,**kwargs):
    with self._lock:
     if self._live is not None:return self._live.request(endpoint,payload,**kwargs)
     try:return super().request(endpoint,payload,**kwargs)
     except RuntimeError as e:
      if not str(e).startswith('Offline response is not complete in the frozen cache: '):raise
      key=str(e).rsplit(' ',1)[-1];assert_future(self.frozen_state,self.recovery_map,key)
      old=prefixes(SOURCE,s);recovery_receipt();scope()
      envelope={'endpoint':endpoint,'request':{**payload,'provider':{'order':[self.provider],'allow_fallbacks':False}}};require(identity(envelope)==key,'Unexpected mapped boundary identity')
      with (self.root/'project_spend.lock').open('r') as ledger_lock:
       fcntl.flock(ledger_lock,fcntl.LOCK_SH);state=json.loads(self.ledger_path.read_text());mapping=json.loads(self.recoveries.read_text());assert_future(state,mapping,key)
      require(not (SOURCE/'live_prefix_gate.json').exists(),'Existing prefix transition receipt')
      atomic_json(AUDIT/'first_unattempted_envelope.json',envelope)
      atomic_json(SOURCE/'live_prefix_gate.json',{'status':'all_three_preserved_prefixes_exact_before_first_new_request','prefixes':old,'future_request_hash':key,'future_envelope_sha256':sha256(AUDIT/'first_unattempted_envelope.json'),'protocol_sha256':sha256(AUDIT/'continuation_protocol.json'),'retry_receipt_sha256':sha256(AUDIT/'retry_receipt.json'),'network_calls_during_prefix_reconstruction':0,'ledger_mutations_during_prefix_reconstruction':0})
      self._live=live_type(*self._args,**self._kwargs);self._live.request_trace=self.request_trace;self._live.initial_cache.request_trace=self.request_trace
      print('AMZN_ALL_PRESERVED_PREFIXES_PASS_BEFORE_NEW_REQUEST',[(x['kind'],x['records']) for x in old],flush=True)
      return self._live.request(endpoint,payload,**kwargs)
   def snapshot(self):return self._live.snapshot() if self._live is not None else super().snapshot()
  if not a.replay:
   atomic_json(AUDIT/'live_started.json',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'source':'finagent_AMZN','protocol_sha256':sha256(AUDIT/'continuation_protocol.json'),'retry_receipt_sha256':sha256(AUDIT/'retry_receipt.json')})
   atomic_json(SOURCE/'wrapper.json',{'manual_http500_continuation':'exact_AMZN_user_approved_v1','preserved_prefix_path':str(ROOT/s['prefixes'][0]['path']),'protocol_sha256':sha256(AUDIT/'continuation_protocol.json'),'retry_receipt_sha256':sha256(AUDIT/'retry_receipt.json'),'wrapper_sha256':sha256(Path(__file__))})
  driver.WaitingMeter=ReadOnlyReplay if a.replay else Gate
  sys.argv=[str(driverpath),'--output-name',out.name,'--recipe',str(ROOT/s['recipe'])]+(['--offline'] if a.replay else [])
  driver.main();done=validate_completion(out,s,a.replay);atomic_json(out/'manual_continuation_validation.json',done)
  if a.replay:
   original=read(SOURCE/'decisions.jsonl');other=read(REPLAY/'decisions.jsonl');errors,delta=compare(original,other);require(not errors and delta[0]==0 and len(original)==len(other)==397,'Full replay differs')
   proof={'status':'pass','case':'FinAgent','original':SOURCE.name,'replay':REPLAY.name,'records':397,'replay_records':397,'difference_count':0,'differences':[],'maximum_numeric_difference':0,'original_sha256':sha256(SOURCE/'decisions.jsonl'),'replay_sha256':sha256(REPLAY/'decisions.jsonl'),'recipe_sha256':s['recipe_sha256'],'original_script_sha256':s['driver_sha256'],'replayed_script_sha256':sha256(driverpath),'network_allowed':False,'ledger_mutations_allowed':False,'manual_http500_continuation':'exact_AMZN_user_approved_v1','retry_receipt_sha256':sha256(AUDIT/'retry_receipt.json'),'source_manual_validation_sha256':sha256(SOURCE/'manual_continuation_validation.json'),'replay_manual_validation_sha256':sha256(REPLAY/'manual_continuation_validation.json'),'replay_wrapper_sha256':sha256(Path(__file__))}
   atomic_json(PRIVATE/'finagent_AMZN_full_replay_validation.json',proof)
   from fidelity_equity_evidence_v3 import validate_source
   admission=validate_source(ROOT,SOURCE,ROOT/s['recipe'],'finagent');atomic_json(AUDIT/'actual_v3_admission.json',admission)
  print('AMZN_STAGE_COMPLETE',out.name,397,flush=True)
if __name__=='__main__':main()
