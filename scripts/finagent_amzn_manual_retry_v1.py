"""One user-authorized exact AMZN embedding retry. No generalized retry mechanism."""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import closing
import copy,fcntl,hashlib,json,math,os,sqlite3,subprocess,sys,urllib.request
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from alpha_evolve.openrouter_budget import atomic_json,sha256,read_key
from alpha_evolve.publication_llm import CohortOpenRouter
AUDIT=ROOT/'artifacts/fidelity_completion_v2/finagent_amzn_manual_retry_20260922'
OLD=ROOT/'artifacts/fidelity_completion_v2/finagent_amzn_http500_20260918'
KEY='c44d8e40b36db83ac14845cec8f78a20c0ca7fa7fbc9cf32ae93382489055604'
STUDY='fidelity_v2_finagent_source_settings';CAP=.00012324000000000002

def identity(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def retry_envelope(envelope):return {**envelope,'technical_recovery':{'original_request_hash':KEY,'attempt':1}}
def check_preflight(state,mapping,envelope,expected,approval,scheduler,cache_hits,journal_hits):
 require(approval.get('user_reply')=='yes' and approval.get('max_additional_attempts')==1 and approval.get('request_hash')==KEY and approval.get('retain_original_charge') is True and approval.get('max_retry_reservation_usd')==.00012324,'Exact user approval required')
 require(set(envelope)=={'endpoint','request'} and identity(envelope)==KEY,'Exact original envelope required')
 b=envelope['request'];require(envelope['endpoint']=='embeddings' and b['model']=='openai/text-embedding-3-large' and b['provider']=={'order':['OpenAI'],'allow_fallbacks':False} and b['encoding_format']=='float' and len(b['input'])==1 and len(b['input'][0])==164,'Original embedding scope changed')
 require(state['calls'].get(KEY)==expected and expected['status']=='reserved' and expected['pid']==2142178 and expected['study']==STUDY and expected['endpoint']=='embeddings' and expected['model']==b['model'] and expected['reserved_usd']==CAP,'Original reservation changed')
 require(KEY not in mapping,'Existing recovery mapping requires diagnosis')
 newkey=identity(retry_envelope(envelope));require(newkey not in state['calls'],'Retry already attempted; never repeat')
 require(not cache_hits and not journal_hits,'A durable response exists; do not retry')
 jobs={x.split('|')[0]:x.split('|') for x in scheduler.strip().splitlines() if x.strip()}
 require(jobs['26502485'][1:3]==['FAILED','1:0'] and jobs['26502485'][5]=='10:55:50','Failed terminal job identity changed')
 for j in ['26502919','26589541']:require(jobs[j][1]=='CANCELLED' and jobs[j][3]=='None' and jobs[j][5]=='00:00:00','Descendant was not cancelled unstarted')
 reserve=len(json.dumps(envelope,sort_keys=True,separators=(',',':')).encode())*.13/1e6
 require(reserve==CAP,'Same HTTP body reservation changed')
 project,study=CohortOpenRouter.totals(state,STUDY)
 require(project+reserve<450 and study+reserve<160 and project+reserve<500,'Existing budget exceeded')
 return {'retry_key':newkey,'new_reservation_usd':reserve,'project_before':project,'finagent_before':study}

def validate_vector(response):
 rows=response.get('data',[])
 require(not response.get('error') and len(rows)==1 and rows[0].get('index')==0,'Unusable embedding response')
 vector=rows[0].get('embedding',[])
 require(len(vector)==3072 and all(type(x) in [float,int] and math.isfinite(x) for x in vector) and sum(x*x for x in vector)>0,'Invalid embedding vector')
 cost=response.get('usage',{}).get('cost')
 require(cost is None or (type(cost) in [int,float] and math.isfinite(cost) and 0<=cost<=CAP+1e-12),'Reported cost exceeds approved reservation')
 return CAP if cost is None else float(cost)

def check_bindings():
 protocol=json.loads((AUDIT/'protocol.json').read_text())
 for row in protocol['bindings']:require(sha256(ROOT/row['path'])==row['sha256'],'Frozen retry dependency changed: '+row['path'])
 return protocol

def main():
 require(sys.argv[1:]==['--execute-approved-once'],'Explicit one-shot execution argument required')
 protocol=check_bindings();approval=json.loads((AUDIT/'approval.json').read_text());diagnosis=json.loads((OLD/'diagnosis.json').read_text());envelope=json.loads((OLD/'exact_failed_envelope.json').read_text());cache=ROOT/'runs/economic_fidelity/openrouter'
 with (ROOT/'artifacts/fidelity_completion_v2/finagent_AMZN.lock').open('a+') as case_lock:
  fcntl.flock(case_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  require(not (AUDIT/'attempt_intent.json').exists(),'Existing attempt intent: inspect; no second execution')
  scheduler=subprocess.check_output(['/opt/slurm/current/bin/sacct','-X','-j','26502485,26502919,26589541','-n','-P','-o','JobID,State,ExitCode,Start,End,Elapsed,JobName'],text=True)
  (AUDIT/'scheduler_before_retry.txt').write_text(scheduler)
  text=(ROOT/'artifacts/fidelity_completion_v2/finagent_AMZN.log').read_text();trace=text[text.rfind('Traceback (most recent call last):'):]
  require(hashlib.sha256(trace.encode()).hexdigest()==diagnosis['traceback_sha256'] and text.rstrip().endswith(diagnosis['terminal_error']),'Original terminal exception changed')
  source=ROOT/'artifacts/fidelity_completion_v2/finagent_AMZN';require(not (source/'completion.json').exists(),'Source already complete; no retry')
  records=[json.loads(x) for x in (source/'decisions.jsonl').read_text().splitlines()]
  require(len(records)==220 and records[-1]['date']=='2023-04-17','Original 220-record prefix changed')
  oldmanifest=json.loads((OLD/'preservation_manifest.json').read_text())
  for row in oldmanifest['files']:
   require(sha256(ROOT/row['copy'])==row['sha256'],'Preserved original evidence changed')
   if row['path'].startswith('artifacts/fidelity_completion_v2/finagent_AMZN/') or row['path'].startswith(('src/','scripts/','paper_runs/')):require(sha256(ROOT/row['path'])==row['sha256'],'Executed source/history changed')
  env2=retry_envelope(envelope);newkey=identity(env2);keys={KEY,newkey}
  with (cache/'project_spend.lock').open('a+') as ledger_lock:
   fcntl.flock(ledger_lock,fcntl.LOCK_EX)
   with (cache/'cohort_response_journal.lock').open('a+') as journal_lock:
    fcntl.flock(journal_lock,fcntl.LOCK_EX)
    raw=(cache/'project_spend.json').read_bytes();state=json.loads(raw);mp=cache/'technical_recoveries.json';mapping=json.loads(mp.read_text()) if mp.exists() else {}
    with closing(sqlite3.connect('file:'+str(cache/'response_cache.sqlite3')+'?mode=ro',uri=True)) as con:
     cache_hits=[k for k in keys if con.execute('SELECT 1 FROM responses WHERE request_hash=?',(k,)).fetchone()]
    journal_hits=[];digest=hashlib.sha256();length=0
    with (cache/'cohort_responses.jsonl').open('rb') as f:
     for line in f:
      digest.update(line);length+=len(line)
      if any(k.encode() in line for k in keys) and json.loads(line).get('request_hash') in keys:journal_hits.append(True)
    plan=check_preflight(state,mapping,envelope,diagnosis['selected_reservation'],approval,scheduler,cache_hits,journal_hits)
    stamp=datetime.now(timezone.utc).isoformat();oldentry=copy.deepcopy(state['calls'][KEY]);before_other=identity({k:v for k,v in state['calls'].items() if k!=KEY});oldmapping=copy.deepcopy(mapping)
    after={**oldentry,'status':'response_unavailable','reconciliation_reason':'Explicit user-approved one exact AMZN HTTP500 retry; failed original response absent from both stores and full original reservation retained.','reconciled_utc':stamp}
    newentry={'status':'reserved','study':STUDY,'model':envelope['request']['model'],'endpoint':'embeddings','reserved_usd':CAP,'created_utc':stamp,'pid':os.getpid(),'technical_recovery':env2['technical_recovery'],'manual_exception':'exact_AMZN_HTTP500_user_approved_v1','reservation_basis':'unchanged original HTTP envelope bytes at frozen0.13USD/M; recovery bookkeeping is not provider input'}
    maprow={'attempt':1,'cause':after['reconciliation_reason'],'recorded_utc':stamp,'reserved_usd_retained':CAP,'manual_exception_evidence':str((AUDIT/'approval.json').relative_to(ROOT))}
    body={k:envelope['request'][k] for k in ['model','input','encoding_format','provider']};http_body=json.dumps(body).encode()
    intent={**plan,'status':'single_attempt_reserved_no_automatic_retry','recorded_at_utc':stamp,'original_request_hash':KEY,'approval_sha256':sha256(AUDIT/'approval.json'),'protocol_sha256':sha256(AUDIT/'protocol.json'),'original_before':oldentry,'original_after':after,'retry_reserved_entry':newentry,'mapping_entry':maprow,'full_journal_bytes_scanned':length,'full_journal_sha256':digest.hexdigest(),'both_request_keys_absent_both_stores':True,'ledger_before_sha256':hashlib.sha256(raw).hexdigest(),'unrelated_calls_before_sha256':before_other,'mapping_before_sha256':identity(mapping),'http_body_sha256':hashlib.sha256(http_body).hexdigest(),'max_new_attempts':1,'original_charge_refunded':False}
    atomic_json(AUDIT/'attempt_intent.json',intent)
    state['calls'][KEY]=after;state['calls'][newkey]=newentry;mapping[KEY]=maprow
    require(identity({k:v for k,v in state['calls'].items() if k not in keys})==before_other,'Unrelated ledger entries changed')
    require({k:v for k,v in mapping.items() if k!=KEY}==oldmapping,'Unrelated recovery mappings changed')
    atomic_json(cache/'project_spend.json',state);atomic_json(mp,mapping)
    atomic_json(AUDIT/'reservation_committed.json',{'status':'reserved_before_network','retry_key':newkey,'ledger_sha256':sha256(cache/'project_spend.json'),'mapping_sha256':sha256(mp),'original_charge_retained':CAP,'new_reservation_usd':CAP,'other_entries_changed':0})
  key=read_key(ROOT.parent/'KnowledgeTemplate/.env')
  request=urllib.request.Request('https://openrouter.ai/api/v1/embeddings',data=http_body,method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','X-OpenRouter-Title':'Alpha Agent Replication publication upgrade'})
  del key
  atomic_json(AUDIT/'network_attempt_started.json',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'retry_key':newkey,'http_body_sha256':hashlib.sha256(http_body).hexdigest(),'attempt':1,'no_automatic_retry':True})
  try:
   with urllib.request.urlopen(request,timeout=180) as response_handle:response=json.loads(response_handle.read())
  except BaseException as e:
   atomic_json(AUDIT/'attempt_failure.json',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'error_type':type(e).__name__,'http_status':getattr(e,'code',None),'retry_key':newkey,'reservations_retained':True,'retry_permitted':False});raise
  # Persist returned raw response before vector parsing or accounting; never regenerate it.
  body_bytes=(json.dumps({'request_hash':newkey,**env2,'response':response},sort_keys=True)+'\n').encode()
  with (cache/'cohort_response_journal.lock').open('a+') as journal_lock:
   fcntl.flock(journal_lock,fcntl.LOCK_EX)
   with (cache/'cohort_responses.jsonl').open('ab') as f:offset=f.tell();f.write(body_bytes);f.flush();os.fsync(f.fileno())
  (AUDIT/'returned_response.jsonl').write_bytes(body_bytes)
  cost=validate_vector(response)
  with (cache/'project_spend.lock').open('a+') as ledger_lock:
   fcntl.flock(ledger_lock,fcntl.LOCK_EX);state=json.loads((cache/'project_spend.json').read_text());mapping=json.loads(mp.read_text())
   require(state['calls'][KEY]==after and state['calls'][newkey]==newentry and mapping[KEY]==maprow,'Selected state changed during single request')
   others=identity({k:v for k,v in state['calls'].items() if k!=newkey})
   state['calls'][newkey].update(status='complete',cost_usd=cost,cost_source='provider_usage' if response.get('usage',{}).get('cost') is not None else 'conservative_exact_body_reservation',response_id=response.get('id'),response_model=response.get('model'),provider=response.get('provider'),usage=response.get('usage',{}),response_journal_offset=offset,response_journal_sha256=hashlib.sha256(body_bytes).hexdigest())
   require(identity({k:v for k,v in state['calls'].items() if k!=newkey})==others,'Other rows changed at completion')
   atomic_json(cache/'project_spend.json',state);project,own=CohortOpenRouter.totals(state,STUDY)
   receipt={**plan,'status':'one_exact_retry_complete_original_charge_retained','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'original_before':oldentry,'original_after':after,'retry_completed_entry':state['calls'][newkey],'mapping_entry':maprow,'response_sha256':hashlib.sha256(body_bytes).hexdigest(),'response_journal_offset':offset,'cost_usd':cost,'original_reserved_usd_retained':CAP,'project_after':project,'finagent_after':own,'network_calls':1,'other_entries_changed':0,'approval_sha256':sha256(AUDIT/'approval.json'),'protocol_sha256':sha256(AUDIT/'protocol.json'),'full_source_completion':False}
   atomic_json(AUDIT/'retry_receipt.json',receipt)
  print(json.dumps({k:receipt[k] for k in ['status','retry_key','cost_usd','original_reserved_usd_retained','project_after','finagent_after','network_calls','other_entries_changed']}),flush=True)
if __name__=='__main__':main()
