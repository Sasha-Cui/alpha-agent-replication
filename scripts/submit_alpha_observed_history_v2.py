#!/usr/bin/env python3
"""Schedule a separate observed-history sensitivity after all20 source outcomes pass."""
from pathlib import Path
import sys,json,argparse,fcntl,subprocess
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import atomic_json,sha256
from alpha_observed_history_evidence_v2 import complete_catalogue,SCOPE
PRIVATE=ROOT/'artifacts/fidelity_completion_v2';PUBLIC=ROOT/'paper_runs/fidelity_completion_v2';SLURM=ROOT.parent/'slurm/slurm_scripts'

def planned_outputs():
    return ['alphaagent_observed20_fixed_library',*['alphaagent_observed20_oos_'+a+s for a in ['alpha158','alpha158_plus_library'] for s in ['','_open_information']]]

def preflight():
    catalogue=complete_catalogue(ROOT)
    for name in planned_outputs():
        if (PRIVATE/name).exists():raise ValueError('Existing observed-history output; inspect rather than duplicate: '+name)
    if (PUBLIC/'alpha_observed_history_sensitivity').exists():raise ValueError('Preserve prior exploratory result')
    if (PRIVATE/'alpha_observed_history_jobs.json').exists():raise ValueError('Submission already recorded; inspect existing IDs/intent')
    held=subprocess.run(['/opt/slurm/current/bin/scontrol','show','job','26515245'],text=True,capture_output=True)
    if held.returncode or 'Priority=0' not in held.stdout or 'JobState=PENDING' not in held.stdout:raise ValueError('Original strict primary must remain held; this does not replace it')
    return catalogue,held.stdout

def submit_chain(record,submit,save):
    previous=None
    for role in ['library','models','opening','analysis']:
        script='alpha_fidelity_v2_observed_'+role+'.sbatch'
        record['pending_submission']={'role':role,'script':script,'afterok':previous};save(record)
        job=submit(role,script,previous)
        if not isinstance(job,str) or not job.isdigit():raise ValueError('Uncertain submission: inspect Slurm/record before any retry')
        record['jobs'][role]=job;record.pop('pending_submission');save(record);previous=job
    record['status']='four_jobs_submitted_not_completed';save(record)

def main():
    p=argparse.ArgumentParser();p.add_argument('--submit',action='store_true');args=p.parse_args()
    catalogue,held=preflight()
    if not args.submit:print(json.dumps({'scope':SCOPE,'status':'ready_not_submitted','trials':len(catalogue['trials'])}));return
    manifest=PRIVATE/'alpha_observed_history_jobs.json'
    with (PRIVATE/'alpha_observed_history_submission.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if manifest.exists():raise ValueError('Submission manifest appeared; do not duplicate')
        names=','.join('alpha_v2_observed_'+r for r in ['library','models','opening','analysis'])
        if subprocess.check_output(['/opt/slurm/current/bin/squeue','-h','-u','zc362','-n',names,'-o','%i|%j'],text=True).strip():raise ValueError('Existing matching jobs require inspection')
        record={'scope':SCOPE,'status':'submission_in_progress','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'jobs':{},'strict_primary_state_at_submission':held,'strict_primary_eligibility':False,'new_llm_calls':0,'new_native_model_fits':2,'new_opening_replays':2,'source_catalogue':catalogue,'submitter_sha256':sha256(Path(__file__)),'template_sha256':{n:sha256(SLURM/n) for n in ['alpha_fidelity_v2_observed_'+r+'.sbatch' for r in ['library','models','opening','analysis']]}}
        def save(x):atomic_json(manifest,x)
        def submit(role,script,previous):
            if sha256(SLURM/script)!=record['template_sha256'][script]:raise ValueError('Submission template changed')
            command=['/opt/slurm/current/bin/sbatch','--parsable']
            if previous:command+=['--dependency=afterok:'+previous]
            command+=[str(SLURM/script)]
            return subprocess.check_output(command,text=True).strip()
        submit_chain(record,submit,save)
    print(json.dumps({'scope':SCOPE,'status':record['status'],'jobs':record['jobs']}))
if __name__=='__main__':main()
