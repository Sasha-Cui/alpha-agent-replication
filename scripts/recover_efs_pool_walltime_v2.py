#!/usr/bin/env python3
"""Operational-only repair after observed terminal timeout; no financial/source edit."""
from pathlib import Path
import json,subprocess,sys,shutil,re
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from alpha_evolve.openrouter_budget import atomic_json,sha256
from alpha_evolve.fidelity_efs_pool_evidence_v2 import validate_efs_trial
PRIVATE=ROOT/'artifacts/fidelity_completion_v2';PUBLIC=ROOT/'paper_runs/fidelity_completion_v2';SLURM=ROOT.parent/'slurm/slurm_scripts';OUT=PRIVATE/'efs_pool_walltime_recovery_20260918'

def call(args):return subprocess.check_output(args,text=True)
def state(job):return call(['/opt/slurm/current/bin/scontrol','show','job',job])
def main():
    path=OUT/'jobs.json'
    if path.exists():raise ValueError('Recovery already recorded; inspect intents/IDs, never repeat')
    terminal=call(['/opt/slurm/current/bin/sacct','-j','26503312_0,26540172,26589769,26540174','-X','--format=JobID%30,State,Elapsed','--parsable2','--noheader'])
    if '26503312_0|TIMEOUT|02:00:16' not in terminal:raise ValueError('Original pool is not the verified terminal timeout')
    for job in ['26540172','26589769','26540174']:
        if job+'|CANCELLED|00:00:00' not in terminal:raise ValueError('Dependent old analysis is not cancelled/unstarted: '+job)
    deep=state('26519342_1')
    if 'JobState=PENDING' not in deep or 'RunTime=00:00:00' not in deep or 'TimeLimit=02:00:00' not in deep:raise ValueError('Deep pool state changed; no blind resource mutation')
    if any(x not in deep for x in ['26503310_3(unfulfilled)','26503311_4(unfulfilled)']):raise ValueError('Unexpected Deep replay dependencies')
    public=PUBLIC/'efs_pooled/gpt41';private=PRIVATE/'efs_pooled/gpt41'
    if sorted(p.name for p in public.iterdir())!=['input_replay_gates.json'] or any(private.iterdir()):raise ValueError('Partial financial mode exists; inspect it before choosing full deterministic rerun')
    proofs={t:validate_efs_trial(ROOT,t) for t in ['gpt41_1','gpt41_2','gpt41_3']}
    before_gate=json.loads((public/'input_replay_gates.json').read_text())
    if before_gate['status']!='pass' or before_gate['trials']!=proofs:raise ValueError('Source input gates changed since timed-out attempt')
    doc=json.loads((PUBLIC/'source_review_evidence_manifest.json').read_text())
    current=ROOT/'scripts/evaluate_efs_pool_v2.py';row=next(r for r in doc['evidence'] if r['path']=='scripts/evaluate_efs_pool_v2.py')
    if row['sha256']!=sha256(current) or sha256(ROOT/row['snapshot_path'])!=row['sha256']:raise ValueError('Evaluator differs from pre-timeout archive')
    record={'status':'recovery_intent','created_utc':datetime.now(timezone.utc).isoformat(),'old_terminal_states':terminal,'old_deep_pool_state':deep,'source_gates':proofs,'evaluator_sha256':sha256(current),'jobs':{},'new_llm_calls':0,'source_searches_rerun':0,'financial_modes_completed_before_timeout':0,'financial_settings_changed':False,'strict_full_family_recreated':False,'scope':'Same deterministic financial evaluator and source libraries. No completed financial mode exists to resume; repeat only the unfinished pool evaluation with original24h template allowance. Preserve all timeout artifacts and repair cancelled analysis dependencies.'}
    atomic_json(path,record)
    sources=[current,ROOT/'src/alpha_evolve/fidelity_efs_pool_evidence_v2.py',ROOT/'scripts/analyze_efs_pooled_v2.py',ROOT/'scripts/collect_v2_project_primary_family.py',SLURM/'alpha_fidelity_v2_efs_pool.sbatch',SLURM/'alpha_v2_efs_pooled_analysis.sbatch',SLURM/'alpha_v2_project_primary_partial.sbatch',Path(__file__)]
    for p in sources:
        dest=OUT/'sources'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(p,dest)
        if sha256(p)!=sha256(dest):raise ValueError('Archive copy differs')
    for ext in ['out','err']:
        p=ROOT.parent/'slurm/slurm_logs'/('alpha_fidelity_v2_efs_pool_26503312_0.'+ext)
        shutil.copy2(p,OUT/p.name)
    (OUT/'terminal_states.txt').write_text(terminal)
    partial=OUT/'timed_out_outputs';partial.mkdir()
    before_hash=sha256(public/'input_replay_gates.json')
    public.rename(partial/'public_gpt41');private.rename(partial/'private_gpt41')
    if sha256(partial/'public_gpt41/input_replay_gates.json')!=before_hash:raise ValueError('Preserved timeout gate changed')
    record['partial_gate_preserved_sha256']=before_hash;atomic_json(path,record)
    def submit(role,args):
        record['pending_submission']={'role':role,'command':args};atomic_json(path,record)
        job=call(['/opt/slurm/current/bin/sbatch','--parsable',*args]).strip()
        if not job.isdigit():raise ValueError('Uncertain submission; inspect scheduler before retry')
        record['jobs'][role]=job;record.pop('pending_submission');atomic_json(path,record);return job
    gpt=submit('gpt_pool',['--array=0','--time=24:00:00',str(SLURM/'alpha_fidelity_v2_efs_pool.sbatch')])
    # Pending, never-started resource change first; no live task interruption.
    fresh=state('26519342_1')
    if 'JobState=PENDING' not in fresh or 'RunTime=00:00:00' not in fresh:raise ValueError('Deep pool started; leave it alone and inspect remaining recovery')
    result=subprocess.run(['/opt/slurm/current/bin/scontrol','update','JobId=26519342_1','TimeLimit=24:00:00'],capture_output=True,text=True)
    record['deep_pending_update_result']={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr};atomic_json(path,record)
    if result.returncode==0 and 'TimeLimit=1-00:00:00' in state('26519342_1'):
        deep_job='26519342';record['jobs']['deep_pool']=deep_job;record['deep_pool_action']='original_pending_job_extended_in_place';atomic_json(path,record)
    else:
        fresh=state('26519342_1')
        if 'JobState=PENDING' not in fresh or 'RunTime=00:00:00' not in fresh:raise ValueError('Cannot replace a started Deep pool')
        record['deep_pool_action']='cancel_unstarted_two_hour_job_then_replace_with_identical24h_pool';atomic_json(path,record)
        subprocess.run(['/opt/slurm/current/bin/scancel','26519342_1'],check=True)
        cancelled=state('26519342_1');record['cancelled_deep_pool_state']=cancelled;atomic_json(path,record)
        if 'JobState=CANCELLED' not in cancelled or 'RunTime=00:00:00' not in cancelled:raise ValueError('Old Deep pool not proven cancelled/unstarted')
        deep_job=submit('deep_pool',['--array=1','--time=24:00:00','--dependency=afterok:26503310_3:26503311_4',str(SLURM/'alpha_fidelity_v2_efs_pool.sbatch')])
    analysis=submit('efs_pooled_analysis',['--dependency=afterok:'+gpt+':'+deep_job,str(SLURM/'alpha_v2_efs_pooled_analysis.sbatch')])
    submit('project_partial_family_after_efs',['--dependency=afterok:'+analysis,str(SLURM/'alpha_v2_project_primary_partial.sbatch')])
    record['status']='replacement_financial_chain_submitted_not_completed';atomic_json(path,record)
    p=PRIVATE/'efs_analysis_jobs.json';old=json.loads(p.read_text());shutil.copy2(p,OUT/'original_efs_analysis_jobs.json')
    old['previous_cancelled_jobs']={k:old[k] for k in ['efs_pooled_analysis','project_partial_family_after_efs','project_four_case_primary']}
    old['llm_pools']=[gpt+'_0',deep_job+'_1'];old['efs_pooled_analysis']=analysis;old['project_partial_family_after_efs']=record['jobs']['project_partial_family_after_efs'];old['project_four_case_primary_status']='old26540174cancelled_by_timeout_dependency_not_recreated_because_strictAlpha_still_blocked';old['walltime_recovery_manifest']=str(path.relative_to(ROOT));atomic_json(p,old)
    p=PRIVATE/'efs_transport_recovery_jobs.json';old=json.loads(p.read_text());shutil.copy2(p,OUT/'original_efs_transport_recovery_jobs.json');old['previous_pool_jobs_before_walltime_recovery']=old['pools'];old['pools']={'gpt41':gpt,'deepseek_v3':deep_job};old['pool_walltime_recovery_manifest']=str(path.relative_to(ROOT));atomic_json(p,old)
    print(json.dumps({'status':record['status'],'jobs':record['jobs'],'deep_action':record['deep_pool_action']}))
if __name__=='__main__':main()
