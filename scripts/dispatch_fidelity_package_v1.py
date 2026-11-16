"""Verify the recorded single package dispatch and actual predecessor completion."""
from pathlib import Path
import json,hashlib,os,subprocess,sys
R=Path(__file__).resolve().parents[1];S=R/'artifacts/fidelity_completion_v2/final_package_setup_20260922'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 protocol=read(S/'package_protocol.json');job=read(S/'package_job.json');assert os.environ.get('SLURM_JOB_ID')==job['job'],'Wrong package execution identity'
 for row in protocol['bindings']:assert sha(Path(row['path']))==row['sha256'],'Frozen package binding changed'
 actual=read(S/'actual_readonly_gate_validation_v2.json');assert actual['status']=='pass_actual_read_only_source_economic_bindings_under_owned_locks'
 assert actual['core_sha256']==sha(R/'scripts/fidelity_package_core_v2.py') and actual['packager_sha256']==sha(R/'scripts/package_fidelity_completion_v2.py')
 text=subprocess.check_output(['/opt/slurm/current/bin/sacct','-X','-n','-j',protocol['hash_job'],'-o','JobIDRaw,State,ExitCode','-P'],text=True)
 rows=[x.split('|') for x in text.splitlines() if x.strip()];assert len(rows)==1 and rows[0][:3]==[protocol['hash_job'],'COMPLETED','0:0'],'Hash predecessor not actually complete'
 inventory=read(S/'inventory.json');expected={r['path'] for r in inventory['files'] if r['bytes']>=1000000};rows=[json.loads(x) for x in (S/'large_payload_hashes.jsonl').read_text().splitlines()]
 assert len(rows)==len(expected) and {r['path'] for r in rows}==expected and all(r['credential_pattern_scan']=='pass' for r in rows)
 subprocess.run([sys.executable,str(R/'scripts/package_fidelity_completion_v2.py')],cwd=R,check=True)
if __name__=='__main__':main()
