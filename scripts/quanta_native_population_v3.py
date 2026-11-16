"""Reject economic export if a native backtest is missing from its task population."""
from pathlib import Path
import json
from alpha_evolve.openrouter_budget import sha256

def assert_population(backtested,pool_workspaces,baseline_workspaces):
    actual=set(backtested);pooled=set(pool_workspaces);baselines=set(baseline_workspaces)
    if actual!=pooled|baselines or pooled&baselines:raise ValueError('Native backtest population differs from exported pool plus explicit baseline; preserve and diagnose, never silently omit a task')
    if len(pool_workspaces)!=len(pooled):raise ValueError('Multiple task identities reuse one model workspace; diagnose lineage')

def validate_receipt(root,run,used):
    p=Path(run)/'native_model_population_validation.json';d=json.loads(p.read_text())
    if d['status']!='all_native_backtests_accounted_for_in_pool_or_explicit_baseline' or d['source_completion_sha256']!=sha256(Path(run)/'continuation_completion.json'):raise ValueError('Actual native backtest population gate absent or changed')
    if d['auditor_sha256']!=sha256(Path(root)/'scripts/audit_quanta_native_population_v3.py') or d['guard_sha256']!=sha256(Path(__file__)):raise ValueError('Population audit method changed')
    for row in d['checkpoint_bindings']+d['cache_bindings']:
        if sha256(Path(root)/row['path'])!=row['sha256']:raise ValueError('Native population evidence bytes changed')
    assert_population(d['backtested_workspaces'],d['pool_workspaces'],d['baseline_workspaces'])
    if {str(Path(x['workspace']).relative_to(root)) for x in used['experiments']}!=set(d['pool_workspaces']):raise ValueError('Used-program export omits or replaces a native pool backtest')
    return {'path':str(p.relative_to(root)),'sha256':sha256(p),'backtested_workspaces':len(d['backtested_workspaces']),'pool_workspaces':len(d['pool_workspaces']),'baseline_workspaces':len(d['baseline_workspaces'])}
