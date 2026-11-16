"""Copy the missing sealed archive after verified JSS migration and cache cleanup."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,os,hashlib,fcntl,subprocess,traceback
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'scripts'),str(R/'src')]
from fidelity_package_core_v2 import digest,copy_durable
from alpha_evolve.publication_llm import CohortOpenRouter
S=R/'artifacts/fidelity_completion_v2/final_package_setup_20260922'
D=R/'artifacts/fidelity_completion_v2/archive_copy_after_migration_v2_20260926'
U=R/'paper_runs/fidelity_completion_v2'
def read(p):return json.loads(p.read_text())
def save(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def allocation(path):
 p=Path(path).resolve();base=Path('/nfs/roberts/project')
 assert base in p.parents,'Archive copy must remain in a project allocation'
 return p.relative_to(base).parts[0]
def unchanged_ledger(expected):
 cache=R/'runs/economic_fidelity/openrouter'
 with (cache/'project_spend.lock').open('r+') as f:
  fcntl.flock(f,fcntl.LOCK_EX);raw=(cache/'project_spend.json').read_bytes()
  assert hashlib.sha256(raw).hexdigest()==expected,'Canonical ledger changed'
  total,_=CohortOpenRouter.totals(json.loads(raw),'final_archive_copy')
  assert total<1000
 return total
def main():
 os.umask(0o077);plan=read(D/'copy_protocol.json');job=read(D/'copy_job.json')
 assert os.environ.get('SLURM_JOB_ID')==job['job'],'Wrong continuation job'
 assert not (D/'copy_started.json').exists(),'Preserve existing continuation; never overwrite/restart'
 for row in plan['bindings']:assert digest(Path(row['path']))==row['sha256'],'Copy continuation binding changed'
 text=subprocess.check_output(['/opt/slurm/current/bin/sacct','-X','-n','-j','27159153','-o','JobIDRaw,State,ExitCode','-P'],text=True)
 rows=[x.split('|') for x in text.splitlines() if x];assert len(rows)==1 and rows[0][:3]==['27159153','FAILED','1:0'],'Original archive writer must be terminal in the preserved capacity-failure state'
 public=read(S/'public_archive_readback.json');private=read(S/'private_archive_readback.json');gate=read(S/'own_snapshot_gate.json')
 assert public['status']==private['status']=='pass'
 for record in plan['primary_archive_stats']:
  p=Path(record['path']);st=p.stat()
  assert not p.is_symlink() and st.st_ino==record['inode'] and st.st_size==record['size'] and st.st_mode&0o777==record['mode'] and st.st_mtime_ns==record['mtime_ns'],'Primary archive identity or metadata changed'

 migration=read(Path(plan['migration_verification']))
 cleanup=read(Path(plan['cleanup_completion']))
 assert migration['status']=='pass_independent_postmigration_verification'
 assert cleanup['status']=='complete_seven_authorized_installer_build_caches'
 for jid in ['27480268','27527518']:
  state=subprocess.check_output(['/opt/slurm/current/bin/sacct','-X','-n','-j',jid,'-o','JobIDRaw,State,ExitCode','-P'],text=True)
  assert jid+'|COMPLETED|0:0' in state,'Required storage predecessor not complete'
 assert unchanged_ledger(gate['ledger_sha256'])<1000

 for row in [public,private]:
  p=Path(row['path']);assert p.stat().st_size==row['archive_bytes'] and p.stat().st_mode&0o222==0,'Verified archive size/mode changed'
 pubcopy=Path(plan['existing_public_second_copy']);assert digest(pubcopy)==digest(Path(public['path']))==public['sha256'],'Existing completed public copy changed'
 assert (pubcopy.stat().st_dev,pubcopy.stat().st_ino)!=(Path(public['path']).stat().st_dev,Path(public['path']).stat().st_ino)
 assert not pubcopy.is_symlink() and pubcopy.stat().st_mode&0o222==0,'Existing public copy must remain a readonly regular file'
 target=Path(plan['private_second_copy']);assert target.resolve()!=Path(private['path']).resolve() and not target.exists() and not target.is_symlink()
 assert allocation(Path(public['path']))==allocation(pubcopy)=='pi_jss233'
 assert allocation(Path(private['path']))==allocation(target)=='pi_jss233'
 assert plan['public_copy_different_project_allocation'] is False and plan['private_copy_different_project_allocation'] is False
 source_identity=(Path(private['path']).stat().st_dev,Path(private['path']).stat().st_ino,Path(private['path']).stat().st_size,Path(private['path']).stat().st_mtime_ns)

 target.parent.mkdir(mode=0o700,parents=True,exist_ok=False)
 save(D/'copy_started.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),'job':job['job'],'source_archive_sha256':private['sha256'],'target':str(target),'authorization_sha256':digest(D/'destination_selection.json')})
 copied=copy_durable(Path(private['path']),target,private['sha256'])
 assert target.stat().st_size==private['archive_bytes'] and target.stat().st_mode&0o222==0
 assert Path(private['path']).stat().st_mode&0o222==0 and pubcopy.stat().st_mode&0o222==0,'Archive copy readonly mode changed'
 assert source_identity==(Path(private['path']).stat().st_dev,Path(private['path']).stat().st_ino,Path(private['path']).stat().st_size,Path(private['path']).stat().st_mtime_ns),'Source archive identity changed'

 cache=R/'runs/economic_fidelity/openrouter'
 with (cache/'project_spend.lock').open('r+') as f:
  fcntl.flock(f,fcntl.LOCK_EX);raw=(cache/'project_spend.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==gate['ledger_sha256'],'Ledger changed since the preserved archive snapshot';state=json.loads(raw);total,_=CohortOpenRouter.totals(state,'final_archive_copy')
 assert total<1000
 result={'status':'complete_archives_with_verified_durable_file_copies','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'original_package_job':'27159153','original_package_job_state_preserved':'FAILED_1:0_private_second_copy_capacity_only','copy_continuation_job':job['job'],'archive_rebuilds':0,'scientific_jobs_rerun':0,'new_model_calls':0,'ledger_mutations':0,'prior_own_snapshot_gate':str((S/'own_snapshot_gate.json').relative_to(R)),'prior_own_snapshot_gate_sha256':digest(S/'own_snapshot_gate.json'),'member_readbacks_reused_verified_not_reexecuted':True,'migration_verification_sha256':digest(Path(plan['migration_verification'])),'cleanup_completion_sha256':digest(Path(plan['cleanup_completion'])),'archive_records':[{'kind':'public','path':public['path'],'sha256':public['sha256'],'bytes':public['archive_bytes'],'members':public['members'],'second_copy':str(pubcopy),'second_copy_sha256_verified':True,'different_inode':True,'different_project_allocation':plan['public_copy_different_project_allocation']},{'kind':'private','path':private['path'],'sha256':private['sha256'],'bytes':private['archive_bytes'],'members':private['members'],'logical_files':private['logical_files'],'logical_bytes':private['logical_bytes'],'second_copy':copied['path'],'second_copy_sha256_verified':True,'different_inode':copied['independent_inode'],'different_project_allocation':plan['private_copy_different_project_allocation']}],'private_copy_failure_domain_note':plan['failure_domain_note'],'copy_destination_selection':str((D/'destination_selection.json').relative_to(R)),'copy_destination_selection_sha256':digest(D/'destination_selection.json'),'source_snapshot_ledger_unchanged':True,'project_committed_usd_including_uncertainty':total,'independent_human_review':False,'full_original_paper_reproductions':0,'original_strict_Alpha_primary_unavailable':True,'original_v2_primary_available':3,'original_v2_primary_denominator':4,'scope':'Completed byte archives and durable file copies under the recorded destination choice. No off-cluster resilience or independent human-review claim. Original scientific scopes and missing primary remain unchanged.'}
 save(D/'copy_completion.json',result);save(U/'publication_bundle_manifest_v2.json',result)
 print(json.dumps({'status':result['status'],'private_bytes':private['archive_bytes'],'copy_target':str(target),'different_project_allocation':plan['private_copy_different_project_allocation'],'project_committed_usd':total}),flush=True)
if __name__=='__main__':
 try:main()
 except Exception:
  if not (D/'failure.json').exists():save(D/'failure.json',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'traceback':traceback.format_exc(),'preserve_any_partial_copy_and_do_not_blindly_restart':True})
  raise

