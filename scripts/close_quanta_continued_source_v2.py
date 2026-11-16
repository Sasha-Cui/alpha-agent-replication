"""Export/account the actually complete continued source, then gate economics."""
from pathlib import Path
import json,subprocess,sys,fcntl
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from alpha_evolve.openrouter_budget import sha256,atomic_json
from quanta_continued_source_admission_v2 import admission,evaluation_adapter
from quanta_paper_evaluation_evidence_v3 import SOURCE_RUN,source_gate

def main():
    private=ROOT/'artifacts/fidelity_completion_v2';run=private/SOURCE_RUN
    with (private/(SOURCE_RUN+'_export_accounts.lock')).open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);evaluation_adapter(ROOT)
        for name in ['used_programs','used_factor_manifest.json','independent_accounts','source_export_accounts_completion.json']:
            if (run/name).exists():raise ValueError('Existing export/account output needs diagnosis, not rerun: '+name)
        gate=admission(ROOT);atomic_json(run/'source_closure_gate.json',gate)
        for script in ['export_quantaalpha_used_factors_v2.py','validate_native_qlib_accounts_v2.py']:
            subprocess.run([sys.executable,str(ROOT/'scripts'/script),'--run-name',SOURCE_RUN],cwd=ROOT,check=True)
        evidence=source_gate(ROOT)
        atomic_json(run/'source_export_accounts_completion.json',{'status':'continued_source_full_replay_export_accounts_pass','source_evidence':evidence,'script_sha256':sha256(Path(__file__)),'new_model_calls':0,'new_native_backtests':0,'parameter_economics_complete':False})
        python='/nfs/roberts/project/pi_btk22/zc362/environments/venvs/alpha-agent-replication-py312-20260813/bin/python'
        subprocess.run([python,str(ROOT/'scripts/submit_quanta_paper_eval_v3.py'),'--submit'],cwd=ROOT,check=True)
        print('SOURCE_EXPORT_ACCOUNTS_PASS_ECONOMIC_JOBS_SUBMITTED_NOT_COMPLETED',flush=True)
if __name__=='__main__':main()
