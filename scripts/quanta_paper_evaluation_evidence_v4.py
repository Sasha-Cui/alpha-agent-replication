"""Unchanged V3 financial gates plus actual all-native-backtest population admission."""
import json
from pathlib import Path
import quanta_paper_evaluation_evidence_v3 as prior
from quanta_native_population_v2 import validate_receipt
from alpha_evolve.openrouter_budget import sha256
SCOPE=prior.SCOPE;SOURCE_RUN=prior.SOURCE_RUN;OUTPUT_PREFIX=prior.OUTPUT_PREFIX

def adapter(root):
    root=Path(root);p=root/'paper_runs/fidelity_completion_v2/quanta_continued_evaluation_adapter_v4.json';f=root/'artifacts/fidelity_completion_v2/quanta_continuation_setup_20260919_after_reset/evaluation/v4/frozen_protocol.json'
    if sha256(p)!=sha256(f):raise ValueError('V4 native population adapter changed')
    d=json.loads(p.read_text())
    if d['financial_expressions_changed'] or d['new_primary_substitution']:raise ValueError('Financial scope changed')
    for row in d['bindings']:
        if sha256(root/row['path'])!=row['sha256']:raise ValueError('V4 population method changed')
    return d

def protocol(root):return prior.protocol(root)
def source_gate(root,*,require_causality=False):
    result=prior.source_gate(root,require_causality=require_causality);adapter(root);run=Path(root)/'artifacts/fidelity_completion_v2'/SOURCE_RUN
    result['native_population_gate']=validate_receipt(root,run,json.loads((run/'used_factor_manifest.json').read_text()));return result

def validate_fixed(path,root):
    library,evidence=prior.validate_fixed(path,root);adapter(root);run=Path(root)/'artifacts/fidelity_completion_v2'/SOURCE_RUN
    evidence['native_population_gate']=validate_receipt(root,run,json.loads((run/'used_factor_manifest.json').read_text()));return library,evidence
