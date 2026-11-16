#!/usr/bin/env python3
"""Stage wrapper with exact source/library gates; no native-source mutation."""
from pathlib import Path
import sys,argparse,subprocess,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from quanta_paper_evaluation_evidence_v5 import SOURCE_RUN,OUTPUT_PREFIX,source_gate,validate_fixed,protocol
from alpha_evolve.openrouter_budget import atomic_json,sha256
PRIVATE=ROOT/'artifacts/fidelity_completion_v2'

def invoke(*args):subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,check=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['proof','library','model','opening']);p.add_argument('--index',type=int);a=p.parse_args()
    source=PRIVATE/SOURCE_RUN;library=PRIVATE/(OUTPUT_PREFIX+'_fixed_library')
    if a.stage=='proof':
        evidence=source_gate(ROOT);assert a.index is not None and 0<=a.index<evidence['program_count']
        invoke(ROOT/'scripts/check_fidelity_factor_causality_v2.py','--case','quantaalpha','--run-dir',source,'--factor-manifest',source/'used_factor_manifest.json','--program-index',a.index)
    elif a.stage=='library':
        evidence=source_gate(ROOT,require_causality=True)
        invoke(ROOT/'scripts/check_fidelity_factor_causality_v2.py','--case','quantaalpha','--run-dir',source,'--factor-manifest',source/'used_factor_manifest.json','--collect-only')
        if library.exists():raise ValueError('Preserve partial/completed variant library')
        invoke(ROOT/'scripts/prepare_native_oos_library_v2.py','--case','quantaalpha','--run-names',SOURCE_RUN,'--output-name',library.name)
        atomic_json(library/'parameter_sensitivity_evidence.json',{'source':evidence,'library_manifest_sha256':sha256(library/'library_manifest.json'),'strict_primary_eligibility':False})
    else:
        validate_fixed(library/'library_manifest.json',ROOT)
        if a.index not in [0,1]:raise ValueError('Only both planned augmented arms are allowed')
        arm=['source4_plus_library','alpha158_plus_library'][a.index];name=OUTPUT_PREFIX+'_oos_'+arm
        if a.stage=='model':
            if (PRIVATE/name).exists():raise ValueError('Preserve existing model attempt')
            invoke(ROOT/'scripts/run_native_oos_arm_v2.py','--library',library,'--arm',arm,'--output-name',name)
            invoke(ROOT/'scripts/validate_native_oos_arm_v2.py','--run-name',name)
        else:
            invoke(ROOT/'scripts/replay_native_open_execution_v2.py','--source-run',name,'--output-name',name+'_open_information')
            invoke(ROOT/'scripts/validate_native_oos_arm_v2.py','--run-name',name+'_open_information')
if __name__=='__main__':main()
