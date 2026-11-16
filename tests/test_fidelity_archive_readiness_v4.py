"""Synthetic request classification guards; never change the actual ledger."""
from pathlib import Path
from unittest.mock import patch
import unittest,json,hashlib,copy,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import fidelity_archive_readiness_v4 as m
class ReturnedReservationGuards(unittest.TestCase):
 def setUp(self):
  self.body={'endpoint':'chat/completions','request':{'model':'openai/gpt-5.2','provider':{'order':['openai'],'allow_fallbacks':False},'messages':[{'role':'user','content':'synthetic request'}]},'response':{'choices':[{'message':{'role':'assistant','content':'synthetic response'},'finish_reason':'stop'}],'usage':{'cost':0.01}}}
  self.key=m.identity({k:self.body[k] for k in ['endpoint','request']});self.body['request_hash']=self.key;self.patcher=patch.object(m,'QUANTA_KEY',self.key);self.patcher.start();self.addCleanup(self.patcher.stop)
  self.entry={'status':'reserved','study':m.QUANTA_STUDY,'pid':115150,'endpoint':'chat/completions','model':'openai/gpt-5.2','reserved_usd':0.0556885};self.calls={self.key:dict(self.entry)}
  self.line=(json.dumps(self.body,sort_keys=True)+'\n').encode();digest=hashlib.sha256(self.line).hexdigest();self.w={'request_hash':self.key,'source_gate_status':'pass','entry':self.entry,'journal_matches':[{'offset':7,'sha256':digest}],'copy_sha256':digest}
 def validate(self,**kw):
  args={'calls':self.calls,'mapping':{},'witness':self.w,'sqlite_body':None,'journal_matches':[(7,self.line)],'sources_closed':True,'fresh':True};args.update(kw);return m.validate_returned_reservation(**args)
 def test_valid_return_keeps_full_charge_and_input_unchanged(self):
  before=copy.deepcopy(self.calls);r=self.validate();self.assertEqual(r['reserved_usd'],0.0556885);self.assertEqual(before,self.calls);self.assertEqual(r['status_unchanged'],'reserved')
 def test_source_only_or_stale_checks_cannot_qualify(self):
  for arg in ['sources_closed','fresh']:
   with self.subTest(arg=arg),self.assertRaises(ValueError):self.validate(**{arg:False})
 def test_changed_owner_status_model_charge_or_study_refused(self):
  for field,value in [('pid',123),('status','complete'),('model','other'),('reserved_usd',0.02),('study','other'),('endpoint','embeddings')]:
   with self.subTest(field=field),self.assertRaises(ValueError):self.validate(calls={self.key:{**self.entry,field:value}})
 def test_unqualified_source_witness_refused(self):
  with self.assertRaises(ValueError):self.validate(witness={**self.w,'source_gate_status':'source_only'})
 def test_other_request_never_allowed(self):
  with self.assertRaises(ValueError):self.validate(witness={**self.w,'request_hash':'other'})
 def test_recovery_mapping_refused(self):
  with self.assertRaises(ValueError):self.validate(mapping={self.key:{'attempt':1}})
 def test_new_sqlite_duplicate_refused(self):
  with self.assertRaises(ValueError):self.validate(sqlite_body=self.line)
 def test_absent_and_duplicate_journal_body_refused(self):
  for rows in [[],[(7,self.line),(999,self.line)]]:
   with self.subTest(rows=len(rows)),self.assertRaises(ValueError):self.validate(journal_matches=rows)
 def test_changed_journal_offset_or_bytes_refused(self):
  for rows in [[(8,self.line)],[(7,self.line+b' ')]]:
   with self.subTest(rows=rows[0][0]),self.assertRaises(ValueError):self.validate(journal_matches=rows)
 def changed_body(self,body):
  line=(json.dumps(body,sort_keys=True)+'\n').encode();h=hashlib.sha256(line).hexdigest();return {'journal_matches':[(7,line)],'witness':{**self.w,'copy_sha256':h,'journal_matches':[{'offset':7,'sha256':h}]}}
 def test_envelope_identity_cannot_be_replaced(self):
  b=copy.deepcopy(self.body);b['request']['messages'][0]['content']='different'
  with self.assertRaises(ValueError):self.validate(**self.changed_body(b))
 def test_usage_cost_above_reservation_needs_diagnosis(self):
  b=copy.deepcopy(self.body);b['response']['usage']['cost']=1
  with self.assertRaises(ValueError):self.validate(**self.changed_body(b))
 def test_unusable_body_refused(self):
  b=copy.deepcopy(self.body);b['response']['choices']=[]
  with self.assertRaises(ValueError):self.validate(**self.changed_body(b))
 def fixture_terminal(self):
  e={'status':'reserved','reserved_usd':0.03,'study':'synthetic_alpha'};return {'alpha':e},{'alpha':{'expected_entry':e,'trial':8}}
 def assess(self,extra=None,returned=True):
  a,w=self.fixture_terminal();calls={**a,**self.calls,**(extra or {})};r=self.validate() if returned else None
  return m.assess_snapshot(calls,w,{},set(),set(),sources_closed=True,fresh=True,returned=r)
 def test_known_return_and_terminal_charges_remain_separate(self):
  r=self.assess();self.assertTrue(r['cache_snapshot_request_gate_pass']);self.assertEqual(r['retained_terminal_reservation_usd'],0.03);self.assertEqual(r['retained_returned_reservation_usd'],0.0556885);self.assertFalse(r['archive_created']);self.assertEqual(r['ledger_mutations'],0)
 def test_amzn_or_active_reservation_still_blocks(self):
  r=self.assess({'amzn':{'status':'reserved','reserved_usd':0.00012324,'study':'synthetic_finagent'}});self.assertFalse(r['cache_snapshot_request_gate_pass']);self.assertEqual(r['unclassified_reserved_count'],1)
 def test_unqualified_return_is_still_unknown(self):self.assertEqual(self.assess(returned=False)['unclassified_reserved_count'],1)
 def test_stale_entry_after_validation_refused(self):
  r=self.validate();a,w=self.fixture_terminal()
  with self.assertRaises(ValueError):m.assess_snapshot({**a,self.key:{**self.entry,'pid':17}},w,{},set(),set(),sources_closed=True,fresh=True,returned=r)
 def test_new_response_for_terminal_failure_still_refused(self):
  a,w=self.fixture_terminal()
  with self.assertRaises(ValueError):m.assess_snapshot({**a,**self.calls},w,{},set(),{'alpha'},sources_closed=True,fresh=True,returned=self.validate())
 def test_classification_does_not_authorize_archive(self):
  r=self.assess();self.assertFalse(r['final_publication_ready_claim']);self.assertEqual(r['refunds'],0);self.assertEqual(r['retry_authorizations'],0)
if __name__=='__main__':unittest.main()
