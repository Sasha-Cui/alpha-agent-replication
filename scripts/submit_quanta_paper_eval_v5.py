#!/usr/bin/env python3
"""Submit only after the actual variant source/export/replay/accounts are complete."""
from pathlib import Path
import sys,json,subprocess,fcntl,argparse
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import sha256,atomic_json
from quanta_paper_evaluation_evidence_v5 import SCOPE,SOURCE_RUN,OUTPUT_PREFIX,source_gate,protocol
PRIVATE=ROOT/'artifacts/fidelity_completion_v2';SLURM=ROOT.parent/'slurm/slurm_scripts'

def planned_submissions(program_count):
    if type(program_count) is not int or program_count<=0:raise ValueError('No real source-used manifest/program count')
    return [('proof','0-'+str(program_count-1)+'%2'),('library',None),('models','0-1%2'),('opening','0-1%2'),('analysis',None)]

def main():
    p=argparse.ArgumentParser();p.add_argument('--submit',action='store_true');a=p.parse_args()
    manifest=PRIVATE/'quanta_paper_evaluation_jobs.json'
    if manifest.exists():raise ValueError('Existing submission manifest; inspect intents/IDs rather than duplicate')
    evidence=source_gate(ROOT);plan,_=protocol(ROOT)
    from analyze_native_oos_v2 import load_arm
    from native_secondary_evidence_v2 import validate_execution_identity
    for execution,key in [('native','common_baselines'),('opening_information','opening_common_baselines')]:
        for arm,name in plan[key].items():load_arm(name,'quantaalpha',arm,False);validate_execution_identity(name,execution,PRIVATE)
    for name in [OUTPUT_PREFIX+'_fixed_library',*[OUTPUT_PREFIX+'_oos_'+arm+s for arm in ['source4_plus_library','alpha158_plus_library'] for s in ['','_open_information']]]:
        if (PRIVATE/name).exists():raise ValueError('Existing variant output must be inspected')
    if not a.submit:print(json.dumps({'status':'ready_not_submitted','programs':evidence['program_count']}));return
    with (PRIVATE/'quanta_paper_eval_submission.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if manifest.exists():raise ValueError('Manifest appeared during lock acquisition')
        names=','.join('alpha_v2_quanta_parameter_'+r for r in ['proof','library','models','opening','analysis'])
        if subprocess.check_output(['/opt/slurm/current/bin/squeue','-h','-u','zc362','-n',names,'-o','%i|%j'],text=True).strip():raise ValueError('Existing matching jobs require inspection')
        record={'scope':SCOPE,'status':'submission_in_progress','created_utc':datetime.now(timezone.utc).isoformat(),'source_evidence':evidence,'jobs':{},'new_llm_calls':0,'baseline_refits':0,'submitter_sha256':sha256(Path(__file__))};atomic_json(manifest,record);previous=None
        for role,array in planned_submissions(evidence['program_count']):
            script=SLURM/('alpha_fidelity_v2_quanta_parameter_'+role+'_v5.sbatch');cmd=['/opt/slurm/current/bin/sbatch','--parsable']
            if array:cmd+=['--array='+array]
            if previous:cmd+=['--dependency=afterok:'+previous]
            cmd+=[str(script)];record['pending_submission']={'role':role,'command':cmd,'script_sha256':sha256(script)};atomic_json(manifest,record)
            job=subprocess.check_output(cmd,text=True).strip()
            if not job.isdigit():raise ValueError('Uncertain submission: inspect existing scheduler/manifest before retry')
            record['jobs'][role]=job;record.pop('pending_submission');atomic_json(manifest,record);previous=job
        record['status']='five_jobs_submitted_not_completed';atomic_json(manifest,record)
    print(json.dumps(record))
if __name__=='__main__':main()
