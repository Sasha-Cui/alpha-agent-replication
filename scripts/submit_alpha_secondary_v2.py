#!/usr/bin/env python3
"""Submit all20 prespecified Alpha secondary units only after the complete parent exists."""
from pathlib import Path
import argparse,json,sys,subprocess,fcntl,re
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import atomic_json,sha256
PRIVATE=ROOT/'artifacts/fidelity_completion_v2'
PUBLIC=ROOT/'paper_runs/fidelity_completion_v2'
SLURM=ROOT.parent/'slurm/slurm_scripts'
ARMS=('source4_plus_library','alpha158_plus_library')


def planned_units():
    return [dict(trial=i,source=f'alphaagent_rounds_paper_gpt35_{i:02d}',
                 library=f'alphaagent_rounds_paper_gpt35_{i:02d}_fixed_library',
                 arms={a:f'alphaagent_rounds_paper_gpt35_{i:02d}_oos_{a}' for a in ARMS})
            for i in range(1,21)]


def require_no_outputs(private,public):
    for unit in planned_units():
        names=[unit['library'],*unit['arms'].values(),*[n+'_open_information' for n in unit['arms'].values()]]
        for name in names:
            if (private/name).exists():raise ValueError('Existing secondary output requires inspection, not a new submission: '+name)
    if (public/'native_secondary_oos_all').exists():raise ValueError('Preserve existing full secondary analysis')


def preflight(root=ROOT):
    root=Path(root);private=root/'artifacts/fidelity_completion_v2';public=root/'paper_runs/fidelity_completion_v2'
    parent_path=private/'alphaagent_pooled20_fixed_library/library_manifest.json'
    if not parent_path.is_file():raise ValueError('Complete pooled20 columns are not yet available; submit nothing')
    from native_secondary_evidence_v2 import validate_library
    from analyze_native_oos_v2 import require_primary_library,load_arm
    if root!=ROOT:raise ValueError('Real submission requires canonical root')
    parent,evidence=validate_library(parent_path,root,private)
    require_primary_library('alphaagent',parent)
    if parent.get('alpha_terminal_gate_source_sha256')!=sha256(root/'scripts/fidelity_alpha_terminal_v2.py'):
        raise ValueError('Parent terminal-failure gate version is not pinned/current')
    for unit in planned_units():
        if parent['source_trial_completion_hashes'].get(unit['source'])!=sha256(private/unit['source']/'execution_exit.json'):
            raise ValueError('Parent source-trial closure hash changed')
    require_no_outputs(private,public)
    # The fixed common baselines are fitted by the already-existing primary job.
    # No secondary baseline model is submitted. If ready, validate actual saved
    # native/opening accounts; otherwise retain the existing scheduler dependency.
    baseline_evidence={};baselines_ready=True
    for arm in ('source4','alpha158'):
        for suffix in ('','_open_information'):
            name='alphaagent_pooled20_oos_'+arm+suffix
            if not (private/name/'independent_accounts/validation.json').is_file():
                baselines_ready=False
            else:
                _,proof=load_arm(name,'alphaagent',arm,False)
                baseline_evidence[name]={k:v for k,v in proof.items() if k!='core_settings'}
    primary_open_job=None
    if not baselines_ready:
        jobs=json.loads((private/'open_execution_jobs.json').read_text())
        primary_open_job=jobs['alphaagent_primary']
        raw=subprocess.run(['/opt/slurm/current/bin/scontrol','show','job',primary_open_job],capture_output=True,text=True)
        states=re.findall(r'JobState=(\w+)',raw.stdout)
        if raw.returncode or not states or any(s not in ['PENDING','RUNNING','COMPLETING'] for s in states):
            raise ValueError('Common baseline accounts incomplete and original opening job cannot be resolved')
    return {'status':'complete_parent_gates_pass','parent_manifest_sha256':sha256(parent_path),
            'parent_evidence':evidence,'units':planned_units(),'common_baseline_evidence':baseline_evidence,
            'existing_primary_opening_dependency':primary_open_job,
            'new_baseline_fits':0,'new_augmented_model_fits':40,'new_llm_api_calls':0,
            'secondary_protocol_sha256':sha256(public/'native_secondary_analysis_protocol.json')}


def submit_steps(record,submit,save):
    # Persist intent BEFORE each call. If transport or parsing is uncertain, the
    # manifest is deliberately non-restartable until a human/agent inspects Slurm.
    def one(role,script,args=(),dependencies=()):
        record['pending_submission']={'role':role,'script':script,'arguments':list(args),'dependencies':list(dependencies)};save(record)
        job=submit(role,script,list(args),list(dependencies))
        if not isinstance(job,str) or not job.isdigit():raise ValueError('Uncertain scheduler job ID; inspect existing submission before retry')
        record['jobs'][role]=job;record.pop('pending_submission');save(record);return job
    lib=one('trial_libraries','alpha_fidelity_v2_alpha_secondary_libraries.sbatch')
    opening=[]
    for arm in ARMS:
        fit=one(arm,'alpha_fidelity_v2_alpha_secondary_models.sbatch',[arm],[lib])
        opening.append(one(arm+'_open_information','alpha_fidelity_v2_alpha_secondary_opening.sbatch',[arm],[fit]))
    if record['preflight']['existing_primary_opening_dependency']:
        opening.append(record['preflight']['existing_primary_opening_dependency'])
    one('full54_secondary_analysis','alpha_fidelity_v2_alpha_secondary_analysis.sbatch',dependencies=opening)
    record['status']='all_six_jobs_submitted_not_completed';save(record)
    return record


def main():
    p=argparse.ArgumentParser();p.add_argument('--submit',action='store_true');args=p.parse_args()
    manifest=PRIVATE/'alpha_secondary_jobs.json'
    if manifest.exists():raise ValueError('Existing submission manifest: inspect/reconcile it, never duplicate')
    proof=preflight()
    if not args.submit:
        print(json.dumps(proof));return
    names=['alpha_v2_alpha_secondary_libraries','alpha_v2_alpha_secondary_models','alpha_v2_alpha_secondary_opening','alpha_v2_alpha_secondary_analysis']
    queue=subprocess.check_output(['/opt/slurm/current/bin/squeue','-h','-u','zc362','-n',','.join(names),'-o','%i|%j'],text=True)
    if queue.strip():raise ValueError('Existing secondary jobs without this manifest require inspection')
    with (PRIVATE/'alpha_secondary_submission.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if manifest.exists():raise ValueError('Submission manifest appeared while waiting')
        record={'status':'submission_in_progress','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
                'preflight':proof,'jobs':{},'submitter_sha256':sha256(Path(__file__)),
                'template_sha256':{n:sha256(SLURM/n) for n in ['alpha_fidelity_v2_alpha_secondary_'+k+'.sbatch' for k in ['libraries','models','opening','analysis']]},
                'stage_dependencies':'Whole-array afterok barriers; every unit retained. Existing common baseline fits are reused explicitly.'}
        def save(x):atomic_json(manifest,x)
        def submit(role,script,arguments,dependencies):
            if sha256(SLURM/script)!=record['template_sha256'][script]:raise ValueError('Submission template changed')
            cmd=['/opt/slurm/current/bin/sbatch','--parsable']
            if dependencies:cmd+=['--dependency=afterok:'+':'.join(dependencies)]
            cmd+=[str(SLURM/script),*arguments]
            return subprocess.check_output(cmd,text=True).strip()
        submit_steps(record,submit,save)
    print(json.dumps(record))
if __name__=='__main__':main()
