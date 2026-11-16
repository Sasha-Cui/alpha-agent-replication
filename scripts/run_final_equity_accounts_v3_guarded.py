"""Fresh source admissions and the unchanged V3 account builder; no model/source replay."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,runpy,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import atomic_json,sha256
from fidelity_equity_evidence_v3 import validate_source,final_output_guard
from admit_finagent_amzn_manual_v1 import admit
SETUP=ROOT/'artifacts/fidelity_completion_v2/final_equity_launch_20260922'

def check(ok,message):
 if not ok:raise ValueError(message)
def preflight():
 protocol=json.loads((SETUP/'protocol.json').read_text())
 for row in protocol['bindings']:check(sha256(ROOT/row['path'])==row['sha256'],'Final-account dependency changed: '+row['path'])
 final_output_guard(ROOT/'paper_runs/fidelity_completion_v2/accounts',ROOT/'artifacts/fidelity_completion_v2/accounts')
 scheduler=subprocess.check_output(['/opt/slurm/current/bin/sacct','-X','-j','27062473,27062474','-n','-P','-o','JobID,State,ExitCode'],text=True)
 for job in ['27062473','27062474']:
  row=next((x.split('|') for x in scheduler.splitlines() if x.startswith(job+'|')),None);check(row is not None and row[1:3]==['COMPLETED','0:0'],'Actual completed source and full replay jobs required')
 manual=admit();public=ROOT/'paper_runs/fidelity_completion_v2';private=ROOT/'artifacts/fidelity_completion_v2';overrides=json.loads((public/'primary_run_overrides.json').read_text());rows=[]
 for case,symbols in [('finmem',['TSLA','NFLX','AMZN','MSFT','COIN']),('tradingagents',['AAPL','GOOGL','AMZN']),('finagent',['TSLA','AAPL','AMZN','GOOGL','MSFT'])]:
  for symbol in symbols:
   name=case+'_'+symbol;frozen=case=='finmem' and symbol=='TSLA';run=ROOT/'artifacts/publication_upgrade_v1/finmem_native' if frozen else private/name;recipe=ROOT/'paper_runs/publication_upgrade_v1/finmem_recipe.json' if frozen else public/'recipes'/(name+'.json')
   if name in overrides:run=private/overrides[name]['run_directory'];recipe=ROOT/overrides[name]['recipe']
   rows.append({'case':case,'symbol':symbol,'admission':validate_source(ROOT,run,recipe,case,frozen=frozen)})
 check(len(rows)==13 and all(row['admission']['status']=='pass' for row in rows),'All13 actual admissions required')
 return {'status':'pass_all13_sources_full_replays_before_final_accounts','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'manual_AMZN':manual,'source_admissions':rows,'source_count':13,'primary_run_overrides_sha256':sha256(public/'primary_run_overrides.json'),'builder_sha256':sha256(ROOT/'scripts/build_fidelity_accounts_v3.py'),'gate_sha256':sha256(ROOT/'scripts/fidelity_equity_evidence_v3.py'),'launch_protocol_sha256':sha256(SETUP/'protocol.json'),'scheduler':scheduler,'new_model_calls':0,'source_or_replay_jobs_rerun':0,'financial_calculations_by_preflight':0}

def main():
 check(sys.argv[1:]==[],'No partial or override arguments permitted');check(not (SETUP/'execution_started.json').exists(),'Existing final-account execution: inspect partial/completed output')
 result=preflight();atomic_json(SETUP/'runtime_preflight.json',result);atomic_json(SETUP/'execution_started.json',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'runtime_preflight_sha256':sha256(SETUP/'runtime_preflight.json'),'wrapper_sha256':sha256(Path(__file__))})
 sys.argv=[str(ROOT/'scripts/build_fidelity_accounts_v3.py')];runpy.run_path(sys.argv[0],run_name='__main__')
 validation=ROOT/'paper_runs/fidelity_completion_v2/accounts/validation.json';d=json.loads(validation.read_text());check(d['status']=='pass' and len(d['completed_runs'])==13 and not d['missing_runs'],'Final13 account builder did not pass')
 atomic_json(SETUP/'completion.json',{'status':'unchanged_V3_all13_final_accounts_complete','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'validation_sha256':sha256(validation),'runtime_preflight_sha256':sha256(SETUP/'runtime_preflight.json'),'builder_sha256':result['builder_sha256'],'source_gate_sha256':result['gate_sha256'],'new_model_calls':0,'original_study_results_changed':False});print('FINAL13_V3_ACCOUNTS_COMPLETE',flush=True)
if __name__=='__main__':main()
