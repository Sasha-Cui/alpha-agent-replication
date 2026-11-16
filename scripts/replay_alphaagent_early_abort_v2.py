#!/usr/bin/env python3
"""Replay every observed trial12 response; unattempted rounds remain unattempted."""
from pathlib import Path
import sys,json,fcntl,importlib.util,urllib.error,urllib.request,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import atomic_json,sha256
from alpha_evolve.publication_replay import ReadOnlyReplay
from alpha_evolve.fidelity_transport_v2 import retry_stale_read
from fidelity_alpha_early_abort_v2 import FAILED_KEY,RUN_NAME as FAILED_RUN,validate_early_abort
from finalize_alphaagent_terminal_v2 import trajectories
from validate_publication_replay import compare
PRIVATE=ROOT/'artifacts/fidelity_completion_v2'

def main():
    original=PRIVATE/FAILED_RUN; replay=PRIVATE/(FAILED_RUN+'_observed_abort_replay')
    reference=validate_early_abort(original,require_replay=False)
    if replay.exists():raise ValueError('Preserve existing replay directory')
    audit=PRIVATE/'alpha_trial12_early_abort_20260918'
    failed=json.loads((audit/'failed_request.json').read_text())
    driver_path=ROOT/'scripts/run_alphaagent_rounds_v2.py'
    assert sha256(driver_path)==json.loads((original/'execution_recipe.json').read_text())['wrapper_sha256']
    spec=importlib.util.spec_from_file_location('alpha_terminal_original_driver',driver_path)
    driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    witness=[]
    class WitnessReplay(ReadOnlyReplay):
        def __init__(self,root,*a,**kw):
            def initialize():
                with (Path(root)/'project_spend.lock').open('a+') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX)
                    super(WitnessReplay,self).__init__(root,*a,**kw)
            retry_stale_read(initialize)
        def request(self,endpoint,payload,**kw):
            body={**payload,'provider':{'order':[self.provider],'allow_fallbacks':False}}
            envelope={'endpoint':endpoint,'request':body}
            key=hashlib.sha256(json.dumps(envelope,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if key==FAILED_KEY:
                assert envelope==failed
                assert len([r for r in self.request_trace if r['endpoint']=='chat/completions'])==215
                entry=self.frozen_state['calls'][key]
                assert entry['pid']==3887669 and entry['status']=='reserved' and entry['reserved_usd']==.028655
                witness.append({'request_hash':key,'exact_envelope_match':True,'status_replayed_from_observation':400,'network_retry':False})
                raise urllib.error.HTTPError('https://openrouter.ai/api/v1/chat/completions',400,'Bad Request',None,None)
            return super().request(endpoint,payload,**kw)
    driver.ReadOnlyReplay=WitnessReplay
    def forbidden(*a,**kw):raise RuntimeError('Replay cannot send an HTTP request')
    urllib.request.urlopen=forbidden
    sys.argv=[str(driver_path),'--offline','--trial','paper_gpt35','--replicate','12','--output-name',replay.name]
    try:driver.main()
    except BaseException as error:
        if type(error).__name__!='MeteredStop' or not isinstance(error.__cause__,urllib.error.HTTPError) or error.__cause__.code!=400 or len(witness)!=1:
            raise
        frame=error.__traceback__
        instance=None
        while frame:
            if frame.tb_frame.f_code.co_filename==str(driver_path) and frame.tb_frame.f_code.co_name=='main':
                instance=frame.tb_frame.f_locals['instance']
            frame=frame.tb_next
        assert instance is not None and (instance.loop_idx,instance.step_idx,len(instance.trace.hist))==(2,1,2)
        atomic_json(replay/'trajectories.json',trajectories(instance))
    else:raise AssertionError('Expected exact witnessed failure did not occur')
    errors=[]; maximum=[0.0];proofs={}
    for name in ['model_calls.json','embedding_calls.json','trajectories.json','stages.json']:
        left=json.loads((original/name).read_text());right=json.loads((replay/name).read_text())
        if name=='trajectories.json':
            left=[{k:v for k,v in r.items() if k not in ['workspace','factor_workspaces']} for r in left]
            right=[{k:v for k,v in r.items() if k not in ['workspace','factor_workspaces']} for r in right]
        elif name=='stages.json':
            left=[{k:v for k,v in r.items() if k!='started_utc'} for r in left]
            right=[{k:v for k,v in r.items() if k!='started_utc'} for r in right]
        compare(left,right,name,errors,maximum)
        proofs[name]={'original_sha256':sha256(original/name),'replay_sha256':sha256(replay/name)}
    atomic_json(replay/'execution_exit.json',{'status':'observed_early_abort_replayed','attempted_rounds':3,'planned_rounds':5,'unattempted_round_indices':[3,4],'witness':witness,'new_network_calls':0})
    result={'status':'pass' if not errors else 'fail','trial':'paper_gpt35','replicate':12,'trajectories':2,
        'attempted_rounds':3,'planned_rounds':5,'failed_round_indices':[2],'unattempted_round_indices':[3,4],'native_five_attempt_budget_complete':False,'strict_primary_eligibility':False,'finished_stages':reference['finished_stages'],
        'scope':'Full observed-source replay of all215 returned chat responses and embeddings, both financial trajectories and exact third-attempt failure request. The fourth and fifth rounds were NOT attempted; this is not a complete five-attempt trial. The terminal HTTP400 is replayed as an observed failure stimulus, not reissued or independently explained.',
        'early_abort_evidence_sha256':sha256(original/'early_abort_evidence.json'),
        'terminal_failure_witness':witness,'maximum_numeric_difference':maximum[0],
        'differences':errors[:50],'difference_count':len(errors),'artifact_hashes':proofs,
        'network_calls':0,'ledger_mutations':0,'replay_driver_sha256':sha256(Path(__file__)),
        'executed_native_wrapper_sha256':sha256(driver_path),'full_original_paper_reproduced':False,
        'ignored':'Only workspace paths and stage timestamps. No factor, financial value, response identity, or failed attempt is omitted.'}
    atomic_json(original/'observed_abort_replay_validation.json',result)
    if errors:raise SystemExit(1)
    validate_early_abort(original)
    print('OBSERVED_EARLY_ABORT_REPLAY_PASS_NO_FIVE_ATTEMPT_CREDIT',json.dumps(result),flush=True)
if __name__=='__main__':main()
