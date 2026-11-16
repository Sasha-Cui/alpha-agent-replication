"""Extra exact-AMZN recovery/transition admission before the unchanged V3 final accounts."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from alpha_evolve.openrouter_budget import sha256,atomic_json
from finagent_amzn_manual_retry_v1 import AUDIT,require,identity
from run_finagent_amzn_continuation_v1 import scope,recovery_receipt,validate_completion,SOURCE,REPLAY
from fidelity_equity_evidence_v3 import validate_source

def admit():
 s=scope();receipt=recovery_receipt();source=validate_completion(SOURCE,s,False);replay=validate_completion(REPLAY,s,True)
 for out,actual in [(SOURCE,source),(REPLAY,replay)]:require(json.loads((out/'manual_continuation_validation.json').read_text())==actual,'Manual source/replay validation changed')
 gate=json.loads((SOURCE/'live_prefix_gate.json').read_text());w=json.loads((SOURCE/'wrapper.json').read_text());proof=json.loads((ROOT/'artifacts/fidelity_completion_v2/finagent_AMZN_full_replay_validation.json').read_text())
 require(gate['status']=='all_three_preserved_prefixes_exact_before_first_new_request' and gate['network_calls_during_prefix_reconstruction']==gate['ledger_mutations_during_prefix_reconstruction']==0,'Actual live transition gate required')
 require([(r['kind'],r['records'],r['sha256']) for r in gate['prefixes']]==[(r['kind'],r['records'],r['sha256']) for r in s['prefixes']] and all(r['difference_count']==r['maximum_numeric_difference']==0 for r in gate['prefixes']),'Transition prefix population changed')
 for x in [gate,w,source,replay]:require(x['protocol_sha256']==sha256(AUDIT/'continuation_protocol.json') and x['retry_receipt_sha256']==sha256(AUDIT/'retry_receipt.json'),'Manual continuation protocol/receipt binding')
 require(w['wrapper_sha256']==proof['replay_wrapper_sha256']==sha256(ROOT/'scripts/run_finagent_amzn_continuation_v1.py'),'Manual wrapper changed')
 envelope=AUDIT/'first_unattempted_envelope.json';require(sha256(envelope)==gate['future_envelope_sha256'] and identity(json.loads(envelope.read_text()))==gate['future_request_hash'],'First future envelope binding changed')
 for k,p in [('source_manual_validation_sha256',SOURCE/'manual_continuation_validation.json'),('replay_manual_validation_sha256',REPLAY/'manual_continuation_validation.json'),('retry_receipt_sha256',AUDIT/'retry_receipt.json')]:require(proof[k]==sha256(p),'Full replay manual binding changed')
 v3=validate_source(ROOT,SOURCE,ROOT/s['recipe'],'finagent')
 return {'status':'pass','records':397,'actual_v3_admission':v3,'manual_transition_gate_sha256':sha256(SOURCE/'live_prefix_gate.json'),'protocol_sha256':sha256(AUDIT/'continuation_protocol.json'),'retry_receipt_sha256':sha256(AUDIT/'retry_receipt.json'),'original_failed_charge_retained':receipt['original_reserved_usd_retained'],'no_new_requests_or_financial_calculations':True,'validator_sha256':sha256(Path(__file__))}
if __name__=='__main__':
 require(sys.argv[1:]==[],'No overrides permitted');out=AUDIT/'final_account_preflight_admission.json';require(not out.exists(),'Preserve previous account preflight admission; inspect rather than overwrite');atomic_json(out,admit());print('AMZN_MANUAL_AND_V3_ADMISSION_PASS')
